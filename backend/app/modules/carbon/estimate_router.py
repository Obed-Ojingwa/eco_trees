from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_roles
from app.db.pool import connection
from app.modules.carbon.schemas import EstimateRunRequest
from app.modules.carbon.serialization import decimal_string
from app.modules.carbon.service import load_active_parameters, run_estimates


router = APIRouter(prefix="/api", tags=["carbon estimates"])


@router.get("/carbon/parameters")
def get_carbon_parameters() -> dict:
    with connection() as conn:
        public, _, _ = load_active_parameters(conn)
    return {
        "version": public["version"],
        "is_placeholder": public["is_placeholder"],
        "buffer_pct": str(public["buffer_pct"]),
        "satellite_multipliers": {
            key: str(value)
            for key, value in public["satellite_multipliers"].items()
        },
        "source_citation": public["source_citation"],
        "notes": public["notes"],
        "species": [
            {
                "species_code": item["species_code"],
                "growth_curve": item["growth_curve"],
                "root_shoot_ratio": str(item["root_shoot_ratio"]),
                "carbon_fraction": str(item["carbon_fraction"]),
                "target_density_per_ha": str(item["target_density_per_ha"]),
                "min_density_per_ha": str(item["min_density_per_ha"]),
                "max_density_per_ha": str(item["max_density_per_ha"]),
                "default_survival": str(item["default_survival"]),
                "source_citation": item["source_citation"],
                "notes": item["notes"],
            }
            for item in public["species"]
        ],
    }


@router.post("/admin/estimates/run")
def run_carbon_estimates(
    payload: EstimateRunRequest,
    admin: dict = Depends(require_roles("admin")),
) -> dict:
    as_of = payload.as_of or date.today()
    with connection() as conn, conn.transaction():
        estimates = run_estimates(
            conn,
            actor_id=admin["id"],
            as_of=as_of,
            plot_ids=payload.plot_ids,
        )
    return {
        "as_of": as_of.isoformat(),
        "count": len(estimates),
        "items": estimates,
    }


@router.get("/admin/estimates")
def list_estimates(
    plot_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT e.id, e.plot_id, e.param_set_id, e.as_of, e.area_ha,
                   e.co2e_gross_t, e.buffer_t, e.co2e_net_cum_t,
                   e.already_issued_t, e.issuable_t, e.flags, e.batch_id,
                   e.inputs, e.created_at, p.status AS plot_status,
                   p.monitoring_state, ps.version, ps.is_placeholder
            FROM carbon_estimates e
            JOIN plots p ON p.id = e.plot_id
            JOIN carbon_param_sets ps ON ps.id = e.param_set_id
            WHERE (%s::uuid IS NULL OR e.plot_id = %s::uuid)
            ORDER BY e.created_at DESC, e.id
            LIMIT %s
            """,
            (plot_id, plot_id, limit),
        ).fetchall()
    return {
        "items": [
            {
                "id": str(row["id"]),
                "plot_id": str(row["plot_id"]),
                "parameter_version": row["version"],
                "is_placeholder": row["is_placeholder"],
                "as_of": row["as_of"],
                "area_ha": decimal_string(row["area_ha"]),
                "plot_status": row["plot_status"],
                "monitoring_state": row["monitoring_state"],
                "co2e_gross_t": decimal_string(row["co2e_gross_t"]),
                "buffer_t": decimal_string(row["buffer_t"]),
                "co2e_net_cum_t": decimal_string(row["co2e_net_cum_t"]),
                "already_issued_t": decimal_string(row["already_issued_t"]),
                "issuable_t": decimal_string(row["issuable_t"]),
                "flags": row["flags"],
                "batch_id": str(row["batch_id"]) if row["batch_id"] else None,
                "inputs": row["inputs"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }
