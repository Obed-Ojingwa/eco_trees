import hashlib
import hmac
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.integrations.registry import get_registry_adapter
from app.modules.carbon.batch_router import load_auditor_batch
from app.modules.carbon.schemas import AuditorDecisionRequest
from app.modules.carbon.serialization import canonical_json, canonical_value


router = APIRouter(prefix="/api/auditor/batches", tags=["auditor batch review"])
BLOCKING_FLAGS = {
    "DENSITY_BELOW_MIN",
    "DENSITY_ABOVE_MAX",
    "POSSIBLE_EXISTING_FOREST",
    "NO_GPS_MATCHED_PHOTO",
    "PHOTO_ACCURACY_POOR",
    "PHOTO_REUSED",
    "FEW_VALID_PIXELS",
    "SATELLITE_PENDING",
    "SATELLITE_FROZEN",
    "REVERSAL_RISK",
    "PLOT_NOT_VERIFIED",
}


def _insert_audit_log(conn, auditor_id: UUID, batch_id: UUID, action: str, details: dict) -> None:
    conn.execute(
        """
        INSERT INTO audit_log
            (id, actor_id, action, entity_type, entity_id, details)
        VALUES (%s, %s, %s, 'carbon_batch', %s, %s)
        """,
        (uuid4(), auditor_id, action, batch_id, Jsonb(details)),
    )


@router.post("/{batch_id}/decision")
def decide_batch(
    batch_id: UUID,
    payload: AuditorDecisionRequest,
    auditor: dict = Depends(require_roles("auditor")),
) -> dict:
    if not settings.carbon_signing_key:
        raise ApiError(
            503,
            "CARBON_SIGNING_KEY_UNAVAILABLE",
            "Batch review signing is not configured.",
        )
    with connection() as conn, conn.transaction():
        batch = conn.execute(
            "SELECT id, status FROM carbon_batches WHERE id = %s FOR UPDATE",
            (batch_id,),
        ).fetchone()
        if not batch:
            raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found.")
        previous = conn.execute(
            """
            SELECT decision, note, overrides, package_sha256, signature,
                   signing_key_id, created_at
            FROM audit_reviews
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()
        if previous:
            if previous["decision"] != payload.decision:
                raise ApiError(409, "BATCH_ALREADY_REVIEWED", "This batch already has a final auditor decision.")
            return {
                "batch_id": str(batch_id),
                "status": batch["status"],
                "decision": previous["decision"],
                "package_sha256": previous["package_sha256"],
                "signature": previous["signature"],
                "signing_key_id": previous["signing_key_id"],
                "created_at": previous["created_at"],
            }
        if batch["status"] != "submitted":
            raise ApiError(409, "BATCH_NOT_SUBMITTED", "Only a submitted batch can be reviewed.")

        data = load_auditor_batch(conn, batch_id)
        plot_ids = sorted(UUID(plot["plot_id"]) for plot in data["plots"])
        conn.execute(
            "SELECT id FROM plots WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
            (plot_ids,),
        ).fetchall()
        overrides_by_plot = {str(item.plot_id): item for item in payload.overrides}
        plot_ids = {plot["plot_id"] for plot in data["plots"]}
        unknown_override_ids = sorted(set(overrides_by_plot) - plot_ids)
        if unknown_override_ids:
            raise ApiError(
                422,
                "OVERRIDE_PLOT_NOT_IN_BATCH",
                "Every override must refer to a plot in this batch.",
                {"plot_ids": unknown_override_ids},
            )
        missing_overrides: list[dict] = []
        normalized_overrides: list[dict] = []
        for plot in data["plots"]:
            blocking_flags = set(plot["flags"]) & BLOCKING_FLAGS
            requested = overrides_by_plot.get(plot["plot_id"])
            if payload.decision == "approved" and blocking_flags:
                if requested is None:
                    missing_overrides.append(
                        {"plot_id": plot["plot_id"], "flags": sorted(blocking_flags)}
                    )
                    continue
                requested_flags = set(requested.flags)
                if requested_flags != blocking_flags:
                    raise ApiError(
                        422,
                        "OVERRIDE_FLAGS_MISMATCH",
                        "Overrides must cover exactly the blocking flags on their plot.",
                        {
                            "plot_id": plot["plot_id"],
                            "blocking_flags": sorted(blocking_flags),
                            "provided_flags": sorted(requested_flags),
                        },
                    )
                normalized_overrides.append(
                    {
                        "plot_id": plot["plot_id"],
                        "flags": sorted(requested_flags),
                        "note": requested.note,
                    }
                )
            elif requested is not None:
                raise ApiError(
                    422,
                    "OVERRIDE_NOT_REQUIRED",
                    "Overrides are only valid for plots with blocking flags in an approval.",
                    {"plot_id": plot["plot_id"]},
                )
        if missing_overrides:
            raise ApiError(
                409,
                "BLOCKING_FLAGS_REQUIRE_OVERRIDE",
                "Every blocking flag requires an auditor override with a note before approval.",
                {"plots": missing_overrides},
            )

        package = canonical_value(
            {
                "schema_version": 1,
                "batch": data["batch"],
                "plots": [
                    {key: value for key, value in plot.items() if key != "geometry"}
                    | {"geometry": json.loads(plot["geometry"])}
                    for plot in data["plots"]
                ],
                "decision": payload.decision,
                "decision_note": payload.note,
                "overrides": sorted(normalized_overrides, key=lambda item: item["plot_id"]),
            }
        )
        package_bytes = canonical_json(package)
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        signature = hmac.new(
            settings.carbon_signing_key.encode("utf-8"),
            package_sha256.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        conn.execute(
            """
            INSERT INTO audit_reviews
                (id, batch_id, auditor_id, decision, note, overrides, package,
                 package_sha256, signature, signing_key_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                uuid4(),
                batch_id,
                auditor["id"],
                payload.decision,
                payload.note,
                Jsonb(normalized_overrides),
                Jsonb(package),
                package_sha256,
                signature,
                settings.carbon_signing_key_id,
            ),
        )
        conn.execute(
            """
            UPDATE carbon_batches
            SET status = %s, package_sha256 = %s, decided_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (payload.decision, package_sha256, batch_id),
        )
        _insert_audit_log(
            conn,
            auditor["id"],
            batch_id,
            f"batch_{payload.decision}",
            {
                "note": payload.note,
                "package_sha256": package_sha256,
                "signature": signature,
                "signing_key_id": settings.carbon_signing_key_id,
                "overrides": normalized_overrides,
            },
        )
        for override in normalized_overrides:
            _insert_audit_log(
                conn,
                auditor["id"],
                batch_id,
                "batch_flag_override",
                override,
            )

        issuance = None
        if payload.decision == "approved":
            adapter = get_registry_adapter()
            project = adapter.register_project(data["batch"])
            mrv = adapter.submit_mrv(
                project,
                {"package": package, "package_sha256": package_sha256},
            )
            mrv = adapter.review_mrv(mrv, "approved", payload.note)
            operation_key = f"issue:{batch_id}"
            conn.execute(
                """
                INSERT INTO registry_operations
                    (id, batch_id, operation, idempotency_key, request, status)
                VALUES (%s, %s, 'issue', %s, %s, 'pending')
                """,
                (
                    uuid4(),
                    batch_id,
                    operation_key,
                    Jsonb(
                        {
                            "mrv_reference": mrv.reference,
                            "units": data["batch"]["units"],
                            "vintage": data["batch"]["vintage"],
                        }
                    ),
                ),
            )
            credits = adapter.issue(
                mrv,
                data["batch"]["units"],
                data["batch"]["vintage"],
                data["batch"]["batch_number"],
            )
            if len(credits) != data["batch"]["units"]:
                raise ApiError(
                    502,
                    "REGISTRY_ISSUANCE_COUNT_MISMATCH",
                    "The registry returned a different number of credits than requested.",
                )
            serials = [credit.serial for credit in credits]
            indexes = [credit.unit_index for credit in credits]
            if len(set(serials)) != len(serials) or sorted(indexes) != list(
                range(1, data["batch"]["units"] + 1)
            ):
                raise ApiError(
                    502,
                    "REGISTRY_ISSUANCE_INVALID",
                    "The registry returned duplicate serials or invalid unit indexes.",
                )
            for credit in credits:
                conn.execute(
                    """
                    INSERT INTO credits
                        (id, batch_id, unit_index, serial, registry_source, registry_credit_ref)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4(),
                        batch_id,
                        credit.unit_index,
                        credit.serial,
                        adapter.source,
                        credit.registry_credit_ref,
                    ),
                )
            operation_response = {
                "project_reference": project.reference,
                "mrv_reference": mrv.reference,
                "serials": serials,
            }
            conn.execute(
                """
                UPDATE registry_operations
                SET status = 'succeeded', response = %s, completed_at = now()
                WHERE idempotency_key = %s
                """,
                (Jsonb(operation_response), operation_key),
            )
            conn.execute(
                """
                UPDATE carbon_batches
                SET status = 'issued', registry_source = %s,
                    registry_project_ref = %s, registry_mrv_ref = %s,
                    issued_at = now(), updated_at = now()
                WHERE id = %s
                """,
                (adapter.source, project.reference, mrv.reference, batch_id),
            )
            issuance = operation_response
    return {
        "batch_id": str(batch_id),
        "status": "issued" if issuance else payload.decision,
        "decision": payload.decision,
        "package_sha256": package_sha256,
        "signature": signature,
        "signing_key_id": settings.carbon_signing_key_id,
        "issuance": issuance,
    }
