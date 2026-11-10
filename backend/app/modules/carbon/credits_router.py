from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.modules.carbon.schemas import ListingPriceRequest


router = APIRouter(prefix="/api", tags=["carbon credits"])


@router.post("/admin/batches/{batch_id}/listing")
def list_batch_credits(
    batch_id: UUID,
    payload: ListingPriceRequest,
    _admin: dict = Depends(require_roles("admin")),
) -> dict:
    with connection() as conn, conn.transaction():
        batch = conn.execute(
            "SELECT id, status, units FROM carbon_batches WHERE id = %s FOR UPDATE",
            (batch_id,),
        ).fetchone()
        if not batch:
            raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found.")
        if batch["status"] == "listed":
            raise ApiError(409, "BATCH_ALREADY_LISTED", "This batch is already listed.")
        if batch["status"] != "issued":
            raise ApiError(409, "BATCH_NOT_ISSUED", "Only an issued batch can be listed.")
        count = conn.execute(
            "SELECT count(*) AS total FROM credits WHERE batch_id = %s AND status = 'issued'",
            (batch_id,),
        ).fetchone()["total"]
        if count != batch["units"]:
            raise ApiError(
                409,
                "CREDIT_INVENTORY_MISMATCH",
                "The issued credit inventory does not match the batch unit count.",
                {"expected": batch["units"], "actual": count},
            )
        conn.execute(
            """
            UPDATE credits SET status = 'listed'
            WHERE batch_id = %s AND status = 'issued'
            """,
            (batch_id,),
        )
        conn.execute(
            """
            UPDATE carbon_batches
            SET status = 'listed', price_per_tonne_kobo = %s,
                listed_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (payload.price_per_tonne_kobo, batch_id),
        )
    return {
        "batch_id": str(batch_id),
        "status": "listed",
        "units": batch["units"],
        "price_per_tonne_kobo": payload.price_per_tonne_kobo,
    }


@router.get("/public/credits")
def list_public_credits(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.serial, c.status, c.registry_source, c.registry_credit_ref,
                   b.batch_number, b.vintage, b.price_per_tonne_kobo, b.package_sha256
            FROM credits c
            JOIN carbon_batches b ON b.id = c.batch_id
            WHERE c.status IN ('listed', 'sold', 'retired')
            ORDER BY b.vintage DESC, c.serial
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return {"items": rows, "limit": limit, "offset": offset}


@router.get("/public/credits/{serial}")
def get_public_credit(serial: str) -> dict:
    with connection() as conn:
        credit = conn.execute(
            """
            SELECT c.serial, c.status, c.registry_source, c.registry_credit_ref,
                   c.retirement_ref, c.retired_for, c.retired_at, c.created_at,
                   b.batch_number, b.vintage, b.units, b.price_per_tonne_kobo,
                   b.package_sha256, b.registry_project_ref, b.registry_mrv_ref
            FROM credits c
            JOIN carbon_batches b ON b.id = c.batch_id
            WHERE c.serial = %s
            """,
            (serial,),
        ).fetchone()
    if not credit:
        raise ApiError(404, "CREDIT_NOT_FOUND", "Credit serial not found.")
    return credit
