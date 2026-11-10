from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.db.pool import connection


router = APIRouter(prefix="/api", tags=["impact and farmer dashboard"])

def _level(points: int) -> tuple[str, int | None]:
    levels = settings.farmer_level_thresholds
    current = levels[0]
    next_threshold = None
    for index, threshold in enumerate(levels):
        if points >= threshold[0]:
            current = threshold
            next_threshold = levels[index + 1][0] if index + 1 < len(levels) else None
    return current[1], next_threshold


@router.get("/farmer/home")
def farmer_home(farmer: dict = Depends(require_roles("farmer"))) -> dict:
    with connection() as conn:
        points = conn.execute(
            "SELECT COALESCE(sum(points), 0)::integer AS total FROM xp_events WHERE farmer_id = %s",
            (farmer["id"],),
        ).fetchone()["total"]
        visit = conn.execute(
            "SELECT last_seen_at FROM farmer_dashboard_visits WHERE farmer_id = %s",
            (farmer["id"],),
        ).fetchone()
        since_last_visit = conn.execute(
            """
            SELECT kind, message, points, celebrate, created_at
            FROM notifications
            WHERE farmer_id = %s
              AND (%s::timestamptz IS NULL OR created_at > %s)
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (farmer["id"], visit["last_seen_at"] if visit else None,
             visit["last_seen_at"] if visit else None),
        ).fetchall()
        plot_summary = conn.execute(
            """
            SELECT count(*)::integer AS total,
                   count(*) FILTER (WHERE status = 'verified')::integer AS verified,
                   count(*) FILTER (WHERE monitoring_state IN ('pending', 'watch', 'frozen'))::integer AS needs_attention,
                   COALESCE(sum(area_ha) FILTER (WHERE status = 'verified'), 0) AS verified_hectares
            FROM plots WHERE farmer_id = %s
            """,
            (farmer["id"],),
        ).fetchone()
        greenness = conn.execute(
            """
            WITH ranked AS (
                SELECT n.plot_id, n.observed_on,
                       n.ndvi_plot - n.ndvi_control AS relative_ndvi,
                       row_number() OVER (PARTITION BY n.plot_id ORDER BY n.observed_on DESC, n.created_at DESC) AS position
                FROM ndvi_observations n
                JOIN plots p ON p.id = n.plot_id
                WHERE p.farmer_id = %s
            )
            SELECT avg(relative_ndvi) FILTER (WHERE position = 1) AS latest,
                   avg(relative_ndvi) FILTER (WHERE position = 2) AS previous,
                   count(DISTINCT plot_id) FILTER (WHERE position = 1)::integer AS monitored_plots
            FROM ranked WHERE position <= 2
            """,
            (farmer["id"],),
        ).fetchone()
        market_price = conn.execute(
            """
            SELECT avg(b.price_per_tonne_kobo) AS average_price
            FROM carbon_batches b
            WHERE b.status IN ('listed', 'sold_out') AND b.price_per_tonne_kobo IS NOT NULL
            """
        ).fetchone()["average_price"]
        potential = conn.execute(
            """
            WITH latest AS (
                SELECT DISTINCT ON (ce.plot_id) ce.plot_id, ce.issuable_t
                FROM carbon_estimates ce
                JOIN plots p ON p.id = ce.plot_id
                WHERE p.farmer_id = %s
                ORDER BY ce.plot_id, ce.created_at DESC, ce.id DESC
            )
            SELECT COALESCE(sum(issuable_t), 0) AS tonnes FROM latest
            """,
            (farmer["id"],),
        ).fetchone()["tonnes"]
        paid_out = conn.execute(
            """
            SELECT COALESCE(sum(amount_kobo), 0)::bigint AS total
            FROM payouts WHERE farmer_id = %s AND status = 'successful'
            """,
            (farmer["id"],),
        ).fetchone()["total"]
        payout_account = conn.execute(
            """
            SELECT confirmed_at FROM farmer_payout_accounts WHERE farmer_id = %s
            """,
            (farmer["id"],),
        ).fetchone()

    level, next_level_points = _level(points)
    latest = greenness["latest"]
    previous = greenness["previous"]
    if latest is None:
        trend = "unavailable"
    elif previous is None:
        trend = "starting"
    elif latest - previous > 0.03:
        trend = "improving"
    elif latest - previous < -0.03:
        trend = "declining"
    else:
        trend = "stable"

    potential_value = (
        int((potential * market_price).to_integral_value())
        if market_price is not None
        else 0
    )
    next_actions: list[dict[str, str]] = []
    if not plot_summary["total"]:
        next_actions.append({"action": "register_plot", "message": "Register your first tree plot."})
    elif plot_summary["verified"] == 0:
        next_actions.append({"action": "complete_verification", "message": "Submit plot evidence for review."})
    if plot_summary["needs_attention"]:
        next_actions.append({"action": "check_monitoring", "message": "Check your latest plot monitoring update."})
    if not payout_account or not payout_account["confirmed_at"]:
        next_actions.append({"action": "confirm_payout_account", "message": "Confirm a payout account to receive sale proceeds."})
    if not next_actions:
        next_actions.append({"action": "keep_monitoring", "message": "Keep your plot evidence and monitoring up to date."})

    return {
        "points": points,
        "level": level,
        "next_level_points": next_level_points,
        "since_last_visit": [
            {
                "kind": item["kind"],
                "message": item["message"],
                "points": item["points"],
                "celebrate": item["celebrate"],
                "created_at": item["created_at"],
            }
            for item in since_last_visit
        ],
        "plots": {
            "total": plot_summary["total"],
            "verified": plot_summary["verified"],
            "verified_hectares": str(plot_summary["verified_hectares"]),
        },
        "greenness": {
            "relative_ndvi": str(latest) if latest is not None else None,
            "trend": trend,
            "monitored_plots": greenness["monitored_plots"],
        },
        "potential_value": {
            "amount_kobo": potential_value,
            "basis": "latest incremental carbon estimate multiplied by current listed-credit average price; not guaranteed",
        },
        "paid_out": {"amount_kobo": paid_out},
        "next_actions": next_actions,
    }


@router.get("/public/impact")
def public_impact() -> dict:
    with connection() as conn:
        result = conn.execute(
            """
            SELECT
                (SELECT count(*) FROM users WHERE role = 'farmer' AND disabled_at IS NULL)::integer AS farmers,
                (SELECT COALESCE(sum(area_ha), 0) FROM plots WHERE status = 'verified') AS verified_hectares,
                (SELECT count(*) FROM credits WHERE status IN ('issued', 'listed', 'reserved', 'sold', 'retired'))::integer AS credits_issued,
                (SELECT count(*) FROM credits WHERE status = 'retired')::integer AS credits_retired,
                (SELECT COALESCE(sum(amount_kobo), 0)::bigint FROM payouts WHERE status = 'successful') AS farmer_payouts_kobo
            """
        ).fetchone()
    return {
        "farmers": result["farmers"],
        "verified_hectares": str(result["verified_hectares"]),
        "credits_issued": result["credits_issued"],
        "credits_retired": result["credits_retired"],
        "farmer_payouts_kobo": result["farmer_payouts_kobo"],
        "registry_notice": "Prototype and sandbox data may be included.",
    }


@router.get("/admin/batches/{batch_id}/impact-pack")
def batch_impact_pack(
    batch_id: UUID,
    _actor: dict = Depends(require_roles("admin", "auditor")),
) -> dict:
    with connection() as conn:
        batch = conn.execute(
            """
            SELECT id, batch_number, vintage, status, registry_source, units,
                   total_claimed_tonnes, package_sha256, price_per_tonne_kobo,
                   issued_at, listed_at
            FROM carbon_batches WHERE id = %s
            """,
            (batch_id,),
        ).fetchone()
        if not batch:
            raise ApiError(404, "BATCH_NOT_FOUND", "Batch not found.")
        plots = conn.execute(
            """
            SELECT p.id AS plot_id, ST_AsGeoJSON(p.geom)::jsonb AS geometry,
                   p.area_ha, p.monitoring_state, be.tonnes_claimed,
                   be.tonnes_attributed, ce.flags, ce.as_of
            FROM batch_estimates be
            JOIN plots p ON p.id = be.plot_id
            JOIN carbon_estimates ce ON ce.id = be.estimate_id
            WHERE be.batch_id = %s ORDER BY p.id
            """,
            (batch_id,),
        ).fetchall()
        observations = conn.execute(
            """
            SELECT n.plot_id, n.observed_on,
                   n.ndvi_plot - n.ndvi_control AS relative_ndvi,
                   n.source, n.valid_px_plot, n.valid_px_control
            FROM ndvi_observations n
            JOIN batch_estimates be ON be.plot_id = n.plot_id
            WHERE be.batch_id = %s
            ORDER BY n.plot_id, n.observed_on
            """,
            (batch_id,),
        ).fetchall()
        payout_totals = conn.execute(
            """
            SELECT p.status, COALESCE(sum(pa.amount_kobo), 0)::bigint AS amount_kobo
            FROM payout_allocations pa
            JOIN payouts p ON p.id = pa.payout_id
            WHERE pa.batch_id = %s
            GROUP BY p.status ORDER BY p.status
            """,
            (batch_id,),
        ).fetchall()
        review = conn.execute(
            """
            SELECT package_sha256, signing_key_id, created_at
            FROM audit_reviews WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()
    return {
        "batch": batch,
        "auditor": {
            "package_sha256": review["package_sha256"] if review else batch["package_sha256"],
            "signing_key_id": review["signing_key_id"] if review else None,
            "reviewed_at": review["created_at"] if review else None,
        },
        "plots": plots,
        "monitoring_history": observations,
        "payout_totals": payout_totals,
    }
