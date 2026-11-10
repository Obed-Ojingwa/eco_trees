from decimal import Decimal, ROUND_DOWN
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query
from psycopg.errors import UniqueViolation

from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.modules.carbon.batches import allocate_batch_units
from app.modules.carbon.schemas import BatchCreateRequest
from app.modules.carbon.serialization import decimal_string


router = APIRouter(prefix="/api", tags=["carbon batches"])


def _batch_summary(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "batch_number": row.get("batch_number"),
        "vintage": row.get("vintage"),
        "status": row["status"],
        "registry_source": row.get("registry_source"),
        "total_claimed_tonnes": (
            decimal_string(row["total_claimed_tonnes"])
            if row.get("total_claimed_tonnes") is not None
            else None
        ),
        "units": row.get("units"),
        "price_per_tonne_kobo": row.get("price_per_tonne_kobo"),
        "package_sha256": row.get("package_sha256"),
        "plot_count": row.get("plot_count", 0),
        "created_at": row.get("created_at"),
        "submitted_at": row.get("submitted_at"),
        "decided_at": row.get("decided_at"),
        "issued_at": row.get("issued_at"),
        "listed_at": row.get("listed_at"),
    }


@router.post("/admin/batches", status_code=201)
def create_batch(
    payload: BatchCreateRequest,
    admin: dict = Depends(require_roles("admin")),
) -> dict:
    batch_id = uuid4()
    with connection() as conn, conn.transaction():
        estimates = conn.execute(
            """
            WITH latest_estimates AS (
                SELECT DISTINCT ON (plot_id)
                       id, plot_id, issuable_t, already_issued_t, batch_id
                FROM carbon_estimates
                ORDER BY plot_id, created_at DESC, id DESC
            )
            SELECT e.id, e.plot_id, e.issuable_t, e.already_issued_t
            FROM latest_estimates e
            JOIN plots p ON p.id = e.plot_id
            WHERE (%s::uuid[] IS NULL OR e.id = ANY(%s::uuid[]))
              AND e.batch_id IS NULL
              AND e.issuable_t > 0
              AND p.status = 'verified'
              AND p.monitoring_state IN ('ok', 'watch')
            ORDER BY e.plot_id
            """,
            (payload.estimate_ids, payload.estimate_ids),
        ).fetchall()
        if payload.estimate_ids:
            found = {row["id"] for row in estimates}
            missing = sorted(str(item) for item in set(payload.estimate_ids) - found)
            if missing:
                raise ApiError(
                    409,
                    "ESTIMATES_NOT_BATCHABLE",
                    "Some estimates are missing, already assigned, or their plots are not eligible.",
                    {"estimate_ids": missing},
                )
        if not estimates:
            raise ApiError(409, "NO_ELIGIBLE_ESTIMATES", "There are no unbatched estimates eligible for a batch.")
        plot_ids = sorted({item["plot_id"] for item in estimates})
        conn.execute(
            "SELECT id FROM plots WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
            (plot_ids,),
        ).fetchall()
        issued_rows = conn.execute(
            """
            SELECT be.plot_id, sum(be.tonnes_attributed) AS total
            FROM batch_estimates be
            JOIN carbon_batches b ON b.id = be.batch_id
            WHERE be.plot_id = ANY(%s)
              AND b.status IN ('approved', 'issued', 'listed', 'sold_out')
            GROUP BY be.plot_id
            """,
            (plot_ids,),
        ).fetchall()
        current_issued = {item["plot_id"]: Decimal(item["total"]) for item in issued_rows}
        stale = [
            str(item["id"])
            for item in estimates
            if Decimal(item["already_issued_t"])
            != current_issued.get(item["plot_id"], Decimal(0))
        ]
        if stale:
            raise ApiError(
                409,
                "ESTIMATES_REQUIRE_RECALCULATION",
                "Some estimates predate credits issued for their plots; recalculate before batching.",
                {"estimate_ids": stale},
            )
        active_batches = conn.execute(
            """
            SELECT DISTINCT b.id
            FROM batch_estimates be
            JOIN carbon_batches b ON b.id = be.batch_id
            WHERE be.plot_id = ANY(%s)
              AND b.status IN ('forming', 'submitted')
            ORDER BY b.id
            """,
            (plot_ids,),
        ).fetchall()
        if active_batches:
            raise ApiError(
                409,
                "PLOT_IN_ACTIVE_BATCH",
                "A plot cannot be added to another batch while its current batch is under review.",
                {"batch_ids": [str(item["id"]) for item in active_batches]},
            )
        claimed_total = sum(
            (Decimal(item["issuable_t"]) for item in estimates),
            Decimal(0),
        ).quantize(Decimal("0.0001"))
        vintage = max(
            conn.execute(
                "SELECT EXTRACT(YEAR FROM CURRENT_DATE)::integer AS year"
            ).fetchone()["year"],
            1,
        )
        try:
            batch = conn.execute(
                """
                INSERT INTO carbon_batches
                    (id, vintage, registry_source, total_claimed_tonnes, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, batch_number, vintage, status, registry_source,
                          total_claimed_tonnes, units, price_per_tonne_kobo,
                          package_sha256, created_at, submitted_at, decided_at,
                          issued_at, listed_at
                """,
                (
                    batch_id,
                    vintage,
                    settings.registry_backend,
                    claimed_total,
                    admin["id"],
                ),
            ).fetchone()
            for estimate in estimates:
                conn.execute(
                    """
                    INSERT INTO batch_estimates
                        (batch_id, estimate_id, plot_id, tonnes_claimed)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        batch_id,
                        estimate["id"],
                        estimate["plot_id"],
                        estimate["issuable_t"],
                    ),
                )
                conn.execute(
                    "UPDATE carbon_estimates SET batch_id = %s WHERE id = %s",
                    (batch_id, estimate["id"]),
                )
        except UniqueViolation as exc:
            raise ApiError(409, "ESTIMATE_ALREADY_BATCHED", "An estimate was added to another batch concurrently.") from exc
        batch["plot_count"] = len(estimates)
    return _batch_summary(batch)


@router.get("/admin/batches")
def list_admin_batches(
    limit: int = Query(default=100, ge=1, le=500),
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT b.*, count(be.plot_id) AS plot_count
            FROM carbon_batches b
            LEFT JOIN batch_estimates be ON be.batch_id = b.id
            GROUP BY b.id
            ORDER BY b.created_at DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return {"items": [_batch_summary(row) for row in rows]}


@router.post("/admin/batches/{batch_id}/submit")
def submit_batch(
    batch_id: UUID,
    admin: dict = Depends(require_roles("admin")),
) -> dict:
    with connection() as conn, conn.transaction():
        batch = conn.execute(
            """
            SELECT id, status, total_claimed_tonnes
            FROM carbon_batches WHERE id = %s FOR UPDATE
            """,
            (batch_id,),
        ).fetchone()
        if not batch:
            raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found.")
        if batch["status"] != "forming":
            raise ApiError(409, "BATCH_NOT_FORMING", "Only a forming batch can be submitted.")
        total = Decimal(batch["total_claimed_tonnes"])
        units = int(total.to_integral_value(rounding=ROUND_DOWN))
        minimum = Decimal(settings.carbon_batch_min_tonnes)
        if total < minimum or units < 1:
            raise ApiError(
                409,
                "BATCH_BELOW_MINIMUM",
                "The batch must contain enough eligible tonnes to issue at least one whole credit.",
                {"total_claimed_tonnes": str(total), "minimum_tonnes": str(minimum)},
            )
        claims = conn.execute(
            """
            SELECT estimate_id, tonnes_claimed
            FROM batch_estimates
            WHERE batch_id = %s
            ORDER BY estimate_id
            """,
            (batch_id,),
        ).fetchall()
        allocations = allocate_batch_units(
            [(str(item["estimate_id"]), Decimal(item["tonnes_claimed"])) for item in claims],
            units,
        )
        for estimate_id, attributed in allocations.items():
            conn.execute(
                """
                UPDATE batch_estimates
                SET tonnes_attributed = %s
                WHERE batch_id = %s AND estimate_id = %s
                """,
                (attributed, batch_id, UUID(estimate_id)),
            )
        conn.execute(
            """
            UPDATE carbon_batches
            SET status = 'submitted', units = %s, submitted_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (units, batch_id),
        )
        conn.execute(
            """
            INSERT INTO audit_log (id, actor_id, action, entity_type, entity_id, details)
            VALUES (%s, %s, 'batch_submitted', 'carbon_batch', %s, %s)
            """,
            (
                uuid4(),
                admin["id"],
                batch_id,
                {
                    "units": units,
                    "total_claimed_tonnes": str(total),
                    "estimate_count": len(claims),
                },
            ),
        )
        updated = conn.execute(
            """
            SELECT b.*, count(be.plot_id) AS plot_count
            FROM carbon_batches b
            LEFT JOIN batch_estimates be ON be.batch_id = b.id
            WHERE b.id = %s
            GROUP BY b.id
            """,
            (batch_id,),
        ).fetchone()
    return _batch_summary(updated)


@router.get("/auditor/batches")
def auditor_batch_queue(
    limit: int = Query(default=100, ge=1, le=500),
    _auditor: dict = Depends(require_roles("auditor")),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT b.id, b.batch_number, b.vintage, b.status,
                   b.registry_source, b.total_claimed_tonnes, b.units,
                   b.price_per_tonne_kobo, b.package_sha256, b.created_at,
                   b.submitted_at, b.decided_at, b.issued_at, b.listed_at,
                   count(be.plot_id) AS plot_count,
                   count(*) FILTER (
                       WHERE cardinality(e.flags) > 0
                         AND e.flags <> ARRAY['PLACEHOLDER_PARAMS']::text[]
                   ) AS flagged_estimate_count
            FROM carbon_batches b
            JOIN batch_estimates be ON be.batch_id = b.id
            JOIN carbon_estimates e ON e.id = be.estimate_id
            WHERE b.status = 'submitted'
            GROUP BY b.id
            ORDER BY b.submitted_at, b.batch_number
            LIMIT %s
            """,
            (limit,),
        ).fetchall()
    return {
        "items": [
            {
                **_batch_summary(row),
                "flagged_estimate_count": row["flagged_estimate_count"],
            }
            for row in rows
        ]
    }


def load_auditor_batch(conn, batch_id: UUID) -> dict:
    batch = conn.execute(
        "SELECT * FROM carbon_batches WHERE id = %s",
        (batch_id,),
    ).fetchone()
    if not batch:
        raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found.")
    items = conn.execute(
        """
        SELECT be.estimate_id, be.plot_id, be.tonnes_claimed,
               be.tonnes_attributed, e.as_of, e.area_ha, e.inputs,
               e.co2e_gross_t, e.buffer_t, e.co2e_net_cum_t,
               e.already_issued_t, e.issuable_t, e.flags,
               p.monitoring_state, ST_AsGeoJSON(p.geom) AS geometry,
               u.display_name AS farmer_display_name,
               review.signature AS previous_signature
        FROM batch_estimates be
        JOIN carbon_estimates e ON e.id = be.estimate_id
        JOIN plots p ON p.id = be.plot_id
        JOIN users u ON u.id = p.farmer_id
        LEFT JOIN audit_reviews review ON review.batch_id = be.batch_id
        WHERE be.batch_id = %s
        ORDER BY be.plot_id
        """,
        (batch_id,),
    ).fetchall()
    review = conn.execute(
        """
        SELECT id, auditor_id, decision, note, overrides, package_sha256,
               signature, signing_key_id, created_at
        FROM audit_reviews
        WHERE batch_id = %s
        """,
        (batch_id,),
    ).fetchone()
    return {
        "batch": _batch_summary({**batch, "plot_count": len(items)}),
        "plots": [
            {
                "plot_id": str(item["plot_id"]),
                "farmer_display_name": item["farmer_display_name"],
                "geometry": item["geometry"],
                "area_ha": decimal_string(item["area_ha"]),
                "monitoring_state": item["monitoring_state"],
                "estimate_id": str(item["estimate_id"]),
                "as_of": item["as_of"],
                "co2e_gross_t": decimal_string(item["co2e_gross_t"]),
                "buffer_t": decimal_string(item["buffer_t"]),
                "co2e_net_cum_t": decimal_string(item["co2e_net_cum_t"]),
                "already_issued_t": decimal_string(item["already_issued_t"]),
                "issuable_t": decimal_string(item["issuable_t"]),
                "tonnes_claimed": decimal_string(item["tonnes_claimed"]),
                "tonnes_attributed": decimal_string(item["tonnes_attributed"]),
                "flags": item["flags"],
                "inputs": item["inputs"],
            }
            for item in items
        ],
        "review": review,
    }


@router.get("/auditor/batches/{batch_id}")
def get_auditor_batch(
    batch_id: UUID,
    _auditor: dict = Depends(require_roles("auditor")),
) -> dict:
    with connection() as conn:
        return load_auditor_batch(conn, batch_id)
