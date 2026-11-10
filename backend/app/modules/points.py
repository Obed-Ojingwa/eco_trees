from uuid import UUID, uuid4

from psycopg import Connection

from app.core.config import settings


def award_points(
    conn: Connection,
    farmer_id: UUID,
    reason: str,
    ref_id: UUID,
    points: int,
) -> int:
    awarded = points
    if reason == "photo_uploaded":
        earned_this_week = conn.execute(
            """
            SELECT COALESCE(sum(points), 0) AS total
            FROM xp_events
            WHERE farmer_id = %s AND reason = 'photo_uploaded'
              AND created_at >= date_trunc('week', now())
            """,
            (farmer_id,),
        ).fetchone()["total"]
        awarded = min(points, max(0, settings.photo_points_weekly_cap - earned_this_week))

    if awarded == 0:
        return 0
    inserted = conn.execute(
        """
        INSERT INTO xp_events (id, farmer_id, reason, ref_id, points)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (farmer_id, reason, ref_id) DO NOTHING
        RETURNING points
        """,
        (uuid4(), farmer_id, reason, ref_id, awarded),
    ).fetchone()
    return inserted["points"] if inserted else 0


def create_notification(
    conn: Connection,
    farmer_id: UUID,
    kind: str,
    ref_id: UUID,
    message: str,
    points: int = 0,
    celebrate: bool = False,
) -> None:
    conn.execute(
        """
        INSERT INTO notifications (id, farmer_id, kind, ref_id, message, points, celebrate)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (farmer_id, kind, ref_id) DO NOTHING
        """,
        (uuid4(), farmer_id, kind, ref_id, message, points, celebrate),
    )
