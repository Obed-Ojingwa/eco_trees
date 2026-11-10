from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.dependencies import require_roles
from app.db.pool import connection


router = APIRouter(prefix="/api", tags=["farmer activity"])


class SeenRequest(BaseModel):
    notification_ids: list[UUID] = Field(default_factory=list, max_length=100)


@router.get("/farmer/points")
def get_points(
    user: dict = Depends(require_roles("farmer")),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    with connection() as conn:
        total = conn.execute(
            "SELECT COALESCE(sum(points), 0) AS total FROM xp_events WHERE farmer_id = %s",
            (user["id"],),
        ).fetchone()["total"]
        events = conn.execute(
            """
            SELECT id, reason, ref_id, points, created_at
            FROM xp_events
            WHERE farmer_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user["id"], limit),
        ).fetchall()
    return {
        "total_points": total,
        "events": [
            {
                "id": str(item["id"]),
                "reason": item["reason"],
                "ref_id": str(item["ref_id"]),
                "points": item["points"],
                "created_at": item["created_at"],
            }
            for item in events
        ],
    }


@router.get("/notifications")
def get_notifications(
    user: dict = Depends(require_roles("farmer")),
    unseen_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    with connection() as conn:
        items = conn.execute(
            """
            SELECT id, kind, ref_id, message, points, celebrate, seen_at, created_at
            FROM notifications
            WHERE farmer_id = %s AND (%s = false OR seen_at IS NULL)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user["id"], unseen_only, limit),
        ).fetchall()
    return {
        "items": [
            {
                "id": str(item["id"]),
                "kind": item["kind"],
                "ref_id": str(item["ref_id"]),
                "message": item["message"],
                "points": item["points"],
                "celebrate": item["celebrate"],
                "seen_at": item["seen_at"],
                "created_at": item["created_at"],
            }
            for item in items
        ]
    }


@router.post("/farmer/seen")
def mark_notifications_seen(
    payload: SeenRequest | None = None,
    user: dict = Depends(require_roles("farmer")),
) -> dict:
    notification_ids = payload.notification_ids if payload else []
    with connection() as conn:
        if notification_ids:
            result = conn.execute(
                """
                UPDATE notifications
                SET seen_at = COALESCE(seen_at, now())
                WHERE farmer_id = %s AND id = ANY(%s)
                """,
                (user["id"], notification_ids),
            )
        else:
            result = conn.execute(
                """
                UPDATE notifications
                SET seen_at = now()
                WHERE farmer_id = %s AND seen_at IS NULL
                """,
                (user["id"],),
            )
    return {"marked_seen": result.rowcount}
