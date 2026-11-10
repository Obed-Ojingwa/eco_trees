from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from psycopg.types.json import Jsonb

from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.modules.carbon.schemas import PlotVerificationRequest, SurvivalOverrideRequest


router = APIRouter(prefix="/api/auditor/plots", tags=["auditor plot review"])


@router.post("/{plot_id}/verification")
def verify_plot(
    plot_id: UUID,
    payload: PlotVerificationRequest,
    auditor: dict = Depends(require_roles("auditor")),
) -> dict:
    target_status = payload.decision
    with connection() as conn, conn.transaction():
        plot = conn.execute(
            "SELECT id, status FROM plots WHERE id = %s FOR UPDATE",
            (plot_id,),
        ).fetchone()
        if not plot:
            raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
        if plot["status"] not in {"submitted", "flagged"}:
            raise ApiError(
                409,
                "PLOT_NOT_REVIEWABLE",
                "Only submitted or flagged plots can be verified or rejected.",
                {"status": plot["status"]},
            )
        conn.execute(
            "UPDATE plots SET status = %s, updated_at = now() WHERE id = %s",
            (target_status, plot_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log
                (id, actor_id, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, 'plot', %s, %s)
            """,
            (
                uuid4(),
                auditor["id"],
                f"plot_{target_status}",
                plot_id,
                Jsonb(
                    {
                        "previous_status": plot["status"],
                        "status": target_status,
                        "note": payload.note,
                    }
                ),
            ),
        )
    return {"plot_id": str(plot_id), "status": target_status}


@router.put("/{plot_id}/survival-override")
def set_survival_override(
    plot_id: UUID,
    payload: SurvivalOverrideRequest,
    auditor: dict = Depends(require_roles("auditor")),
) -> dict:
    with connection() as conn, conn.transaction():
        plot = conn.execute(
            "SELECT id, status FROM plots WHERE id = %s FOR UPDATE",
            (plot_id,),
        ).fetchone()
        if not plot:
            raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
        if plot["status"] != "verified":
            raise ApiError(
                409,
                "PLOT_NOT_VERIFIED",
                "Survival overrides can only be set for verified plots.",
            )
        previous = conn.execute(
            "SELECT survival, note FROM plot_survival_overrides WHERE plot_id = %s",
            (plot_id,),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO plot_survival_overrides
                (plot_id, auditor_id, survival, note)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (plot_id) DO UPDATE
            SET auditor_id = EXCLUDED.auditor_id,
                survival = EXCLUDED.survival,
                note = EXCLUDED.note,
                created_at = now()
            """,
            (plot_id, auditor["id"], payload.survival, payload.note),
        )
        conn.execute(
            """
            INSERT INTO audit_log
                (id, actor_id, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'survival_override_set', 'plot', %s, %s)
            """,
            (
                uuid4(),
                auditor["id"],
                plot_id,
                Jsonb(
                    {
                        "previous": previous,
                        "survival": str(payload.survival),
                        "note": payload.note,
                    }
                ),
            ),
        )
    return {
        "plot_id": str(plot_id),
        "survival": str(payload.survival),
        "note": payload.note,
    }
