from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field, field_validator
from psycopg.types.json import Jsonb

from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.integrations.registry import Retirement, get_registry_adapter


router = APIRouter(prefix="/api/buyer", tags=["buyer credits"])


class CreditRetirementRequest(BaseModel):
    serials: list[str] = Field(min_length=1, max_length=500)
    beneficiary: str = Field(min_length=2, max_length=160)

    @field_validator("serials")
    @classmethod
    def unique_serials(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("A retirement cannot include duplicate serials.")
        return value


def _retirement_result(retirement: dict[str, Any]) -> dict[str, Any]:
    return {
        "retirement_reference": retirement["retirement_reference"],
        "serials": retirement["serials"],
        "beneficiary": retirement["beneficiary"],
        "batch_id": str(retirement["batch_id"]),
        "created_at": retirement["created_at"],
    }


@router.get("/credits")
def list_owned_credits(
    buyer: dict = Depends(require_roles("buyer")),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.serial, c.status, c.registry_source, c.retirement_ref,
                   c.retired_for, c.retired_at, b.batch_number, b.vintage,
                   b.package_sha256, b.price_per_tonne_kobo, o.acquired_at
            FROM credit_ownership o
            JOIN credits c ON c.id = o.credit_id
            JOIN carbon_batches b ON b.id = c.batch_id
            WHERE o.owner_id = %s
            ORDER BY o.acquired_at DESC, c.serial
            LIMIT %s
            """,
            (buyer["id"], limit),
        ).fetchall()
    return {"items": rows}


@router.post("/credits/retire", status_code=201)
def retire_credits(
    payload: CreditRetirementRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    buyer: dict = Depends(require_roles("buyer")),
) -> dict:
    with connection() as conn, conn.transaction():
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"{buyer['id']}:{idempotency_key}",),
        )
        previous = conn.execute(
            """
            SELECT * FROM credit_retirements
            WHERE buyer_id = %s AND idempotency_key = %s
            """,
            (buyer["id"], idempotency_key),
        ).fetchone()
        if previous:
            if sorted(previous["serials"]) != sorted(payload.serials) or previous["beneficiary"] != payload.beneficiary:
                raise ApiError(
                    409,
                    "IDEMPOTENCY_KEY_REUSED",
                    "This idempotency key was already used for a different retirement.",
                )
            return _retirement_result(previous)

        credits = conn.execute(
            """
            SELECT c.id, c.serial, c.status, c.batch_id, c.registry_source
            FROM credits c
            JOIN credit_ownership o ON o.credit_id = c.id
            WHERE o.owner_id = %s AND c.serial = ANY(%s)
            ORDER BY c.id
            FOR UPDATE OF c
            """,
            (buyer["id"], payload.serials),
        ).fetchall()
        if len(credits) != len(payload.serials):
            raise ApiError(404, "OWNED_CREDIT_NOT_FOUND", "One or more selected credits are not owned by you.")
        if any(item["status"] != "sold" for item in credits):
            raise ApiError(409, "CREDIT_NOT_RETIRABLE", "Only owned, unretired credits can be retired.")
        batch_ids = {item["batch_id"] for item in credits}
        registry_sources = {item["registry_source"] for item in credits}
        if len(batch_ids) != 1 or len(registry_sources) != 1:
            raise ApiError(
                422,
                "RETIREMENT_BATCH_MISMATCH",
                "A single retirement must contain credits from one batch and registry.",
            )
        batch_id = next(iter(batch_ids))
        adapter = get_registry_adapter()
        if adapter.source not in registry_sources:
            raise ApiError(
                503,
                "RETIREMENT_ADAPTER_MISMATCH",
                "The configured registry adapter does not match these credits.",
            )
        registry_retirement = adapter.retire(payload.serials, payload.beneficiary.strip())
        if set(registry_retirement.serials) != set(payload.serials):
            raise ApiError(502, "REGISTRY_INVALID_RESPONSE", "The registry retirement did not match the requested serials.")
        retirement_id = uuid4()
        retirement = conn.execute(
            """
            INSERT INTO credit_retirements
                (id, batch_id, buyer_id, idempotency_key, retirement_reference,
                 beneficiary, serials)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                retirement_id,
                batch_id,
                buyer["id"],
                idempotency_key,
                registry_retirement.reference,
                payload.beneficiary.strip(),
                Jsonb(sorted(payload.serials)),
            ),
        ).fetchone()
        conn.execute(
            """
            UPDATE credits
            SET status = 'retired', retirement_ref = %s, retired_for = %s, retired_at = now()
            WHERE id = ANY(%s) AND status = 'sold'
            """,
            (registry_retirement.reference, payload.beneficiary.strip(), [item["id"] for item in credits]),
        )
        return _retirement_result(retirement)


@router.get("/retirements/{reference}/certificate")
def retirement_certificate(
    reference: str,
    buyer: dict = Depends(require_roles("buyer")),
) -> dict:
    with connection() as conn:
        retirement = conn.execute(
            """
            SELECT cr.*, b.batch_number, b.vintage, b.package_sha256,
                   b.registry_source
            FROM credit_retirements cr
            JOIN carbon_batches b ON b.id = cr.batch_id
            WHERE cr.retirement_reference = %s AND cr.buyer_id = %s
            """,
            (reference, buyer["id"]),
        ).fetchone()
    if not retirement:
        raise ApiError(404, "RETIREMENT_NOT_FOUND", "Retirement certificate not found.")
    adapter = get_registry_adapter()
    certificate = adapter.certificate(
        Retirement(
            reference=retirement["retirement_reference"],
            serials=tuple(retirement["serials"]),
            beneficiary=retirement["beneficiary"],
            registry_source=retirement["registry_source"],
        )
    )
    return {
        "retirement_reference": certificate.retirement_reference,
        "serials": list(certificate.serials),
        "beneficiary": certificate.beneficiary,
        "registry_source": certificate.registry_source,
        "batch_number": retirement["batch_number"],
        "vintage": retirement["vintage"],
        "auditor_package_sha256": retirement["package_sha256"],
        "issued_at": retirement["created_at"],
    }
