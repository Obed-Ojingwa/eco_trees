import hmac
import json
from datetime import date, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.errors import ApiError
from app.db.pool import connection
from app.modules.monitoring.assessment import (
    AssessmentParameters,
    Observation,
    assess_monitoring,
)
from app.modules.monitoring.schemas import NdviObservationInput
from app.modules.points import award_points, create_notification


router = APIRouter(prefix="/api", tags=["monitoring"])


def _parameters() -> AssessmentParameters:
    return AssessmentParameters(
        min_observations=settings.monitoring_min_observations,
        rolling_n=settings.monitoring_rolling_n,
        reference_window_days=settings.monitoring_reference_window_days,
        watch_drop=settings.monitoring_watch_drop,
        freeze_drop=settings.monitoring_freeze_drop,
        freeze_consecutive=settings.monitoring_freeze_consecutive,
        recover_consecutive=settings.monitoring_recover_consecutive,
        min_valid_pixels=settings.monitoring_min_valid_pixels,
    )


def _verify_ingest_token(token: str | None) -> None:
    if not settings.ingest_token:
        raise ApiError(503, "INGEST_DISABLED", "Satellite data ingestion is not configured.")
    if not token or not hmac.compare_digest(token, settings.ingest_token):
        raise ApiError(401, "INVALID_INGEST_TOKEN", "The satellite ingestion token is invalid.")


def _observation(row: dict) -> Observation:
    return Observation(
        observed_on=row["observed_on"],
        ndvi_plot=float(row["ndvi_plot"]),
        ndvi_control=float(row["ndvi_control"]),
        valid_px_plot=row["valid_px_plot"],
        valid_px_control=row["valid_px_control"],
        source=row["source"],
    )


def _store_baseline_flag(conn, plot_id: UUID, planted_on: date) -> bool:
    cutoff = planted_on - timedelta(days=365)
    baseline = conn.execute(
        """
        SELECT avg(ndvi_plot) AS mean_ndvi, count(*) AS total
        FROM ndvi_observations
        WHERE plot_id = %s
          AND observed_on >= %s AND observed_on < %s
          AND valid_px_plot >= %s
        """,
        (plot_id, cutoff, planted_on, settings.monitoring_min_valid_pixels),
    ).fetchone()
    if baseline["total"] == 0 or baseline["mean_ndvi"] is None:
        return False
    if float(baseline["mean_ndvi"]) <= settings.existing_forest_ndvi:
        return False
    conn.execute(
        """
        UPDATE plots
        SET flags = CASE
            WHEN 'POSSIBLE_EXISTING_FOREST' = ANY(flags) THEN flags
            ELSE array_append(flags, 'POSSIBLE_EXISTING_FOREST')
        END,
        updated_at = now()
        WHERE id = %s
        """,
        (plot_id,),
    )
    return True


def _run_assessment(conn, plot_id: UUID) -> dict:
    plot = conn.execute(
        """
        SELECT p.monitoring_state, p.status, planting.planted_on,
               u.id AS farmer_id
        FROM plots p
        CROSS JOIN LATERAL (
            SELECT min(planted_on) AS planted_on
            FROM plantings
            WHERE plot_id = p.id
        ) AS planting
        JOIN users u ON u.id = p.farmer_id
        WHERE p.id = %s
        FOR UPDATE OF p
        """,
        (plot_id,),
    ).fetchone()
    if not plot:
        raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
    rows = conn.execute(
        """
        SELECT observed_on, ndvi_plot, ndvi_control, valid_px_plot,
               valid_px_control, source
        FROM ndvi_observations
        WHERE plot_id = %s AND observed_on >= %s
        ORDER BY observed_on, scene_id
        """,
        (plot_id, plot["planted_on"]),
    ).fetchall()
    assessment = assess_monitoring(
        (_observation(row) for row in rows),
        _parameters(),
    )
    previous_state = plot["monitoring_state"]
    assessment_id = uuid4()
    created = conn.execute(
        """
        INSERT INTO monitoring_assessments
            (id, plot_id, state, previous_state, reason, reference_delta,
             latest_delta, drop_value, observation_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING created_at
        """,
        (
            assessment_id,
            plot_id,
            assessment.state,
            previous_state,
            assessment.reason,
            assessment.reference_delta,
            assessment.latest_delta,
            assessment.drop,
            assessment.observation_count,
        ),
    )
    new_status = "monitoring" if plot["status"] == "submitted" else plot["status"]
    conn.execute(
        """
        UPDATE plots
        SET monitoring_state = %s, status = %s, updated_at = now()
        WHERE id = %s
        """,
        (assessment.state, new_status, plot_id),
    )
    if previous_state == "pending" and assessment.state == "ok":
        points = award_points(
            conn,
            plot["farmer_id"],
            "satellite_check_passed",
            assessment_id,
            150,
        )
        create_notification(
            conn,
            plot["farmer_id"],
            "satellite_check_passed",
            assessment_id,
            "Your first satellite check passed.",
            points=points,
            celebrate=True,
        )
    elif assessment.state == "watch" and previous_state != "watch":
        create_notification(
            conn,
            plot["farmer_id"],
            "satellite_watch",
            assessment_id,
            "Satellite data suggests a change in plot greenness. Add a fresh photo.",
        )
    elif assessment.state == "frozen" and previous_state != "frozen":
        create_notification(
            conn,
            plot["farmer_id"],
            "satellite_frozen",
            assessment_id,
            "The plot needs review because satellite data shows a sustained decline.",
        )
    elif previous_state == "frozen" and assessment.state == "ok":
        create_notification(
            conn,
            plot["farmer_id"],
            "satellite_recovered",
            assessment_id,
            "The plot has recovered after repeated satellite checks.",
        )
    return {
        "id": str(assessment_id),
        "state": assessment.state,
        "previous_state": previous_state,
        "reason": assessment.reason,
        "reference_delta": assessment.reference_delta,
        "latest_delta": assessment.latest_delta,
        "drop": assessment.drop,
        "observation_count": assessment.observation_count,
        "created_at": created["created_at"],
    }


@router.get("/internal/plots")
def list_plots_for_ingest(
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> dict:
    _verify_ingest_token(x_ingest_token)
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, ST_AsGeoJSON(p.geom) AS geometry,
                   min(pl.planted_on) AS planted_on
            FROM plots p
            JOIN plantings pl ON pl.plot_id = p.id
            WHERE p.status IN ('submitted', 'monitoring', 'eligible', 'in_batch', 'verified', 'flagged', 'frozen')
            GROUP BY p.id
            ORDER BY p.created_at
            LIMIT 1000
            """
        ).fetchall()
    return {
        "items": [
            {
                "id": str(row["id"]),
                "geometry": json.loads(row["geometry"]),
                "planted_on": row["planted_on"],
            }
            for row in rows
        ]
    }


@router.post("/internal/ndvi", status_code=200)
def ingest_ndvi(
    payload: NdviObservationInput,
    x_ingest_token: str | None = Header(default=None, alias="X-Ingest-Token"),
) -> dict:
    _verify_ingest_token(x_ingest_token)
    try:
        plot_id = UUID(payload.plot_id)
    except ValueError:
        raise ApiError(422, "INVALID_PLOT_ID", "plot_id must be a UUID.")

    with connection() as conn, conn.transaction():
        existing = conn.execute(
            "SELECT id FROM plots WHERE id = %s",
            (plot_id,),
        ).fetchone()
        if not existing:
            raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
        stored = conn.execute(
            """
            INSERT INTO ndvi_observations
                (id, plot_id, scene_id, observed_on, ndvi_plot, ndvi_control,
                 valid_px_plot, valid_px_control, source, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (plot_id, scene_id) DO UPDATE SET
                observed_on = EXCLUDED.observed_on,
                ndvi_plot = EXCLUDED.ndvi_plot,
                ndvi_control = EXCLUDED.ndvi_control,
                valid_px_plot = EXCLUDED.valid_px_plot,
                valid_px_control = EXCLUDED.valid_px_control,
                source = EXCLUDED.source,
                metadata = EXCLUDED.metadata
            WHERE (ndvi_observations.observed_on, ndvi_observations.ndvi_plot,
                   ndvi_observations.ndvi_control, ndvi_observations.valid_px_plot,
                   ndvi_observations.valid_px_control, ndvi_observations.source,
                   ndvi_observations.metadata)
                IS DISTINCT FROM
                  (EXCLUDED.observed_on, EXCLUDED.ndvi_plot, EXCLUDED.ndvi_control,
                   EXCLUDED.valid_px_plot, EXCLUDED.valid_px_control, EXCLUDED.source,
                   EXCLUDED.metadata)
            RETURNING id
            """,
            (
                uuid4(),
                plot_id,
                payload.scene_id,
                payload.observed_on,
                payload.ndvi_plot,
                payload.ndvi_control,
                payload.valid_px_plot,
                payload.valid_px_control,
                payload.source,
                Jsonb(payload.metadata),
            ),
        ).fetchone()
        if stored is None:
            stored = conn.execute(
                """
                SELECT id FROM ndvi_observations
                WHERE plot_id = %s AND scene_id = %s
                """,
                (plot_id, payload.scene_id),
            ).fetchone()
            return {
                "observation_id": str(stored["id"]),
                "plot_id": str(plot_id),
                "inserted_or_updated": False,
                "assessment": None,
            }
        plot = conn.execute(
            "SELECT min(planted_on) AS planted_on FROM plantings WHERE plot_id = %s",
            (plot_id,),
        ).fetchone()
        if not plot or not plot["planted_on"]:
            raise ApiError(409, "PLANTING_REQUIRED", "Add planting details before satellite observations.")
        _store_baseline_flag(conn, plot_id, plot["planted_on"])
        assessment = _run_assessment(conn, plot_id)

    return {
        "observation_id": str(stored["id"]),
        "plot_id": str(plot_id),
        "inserted_or_updated": True,
        "assessment": assessment,
    }


@router.get("/plots/{plot_id}/monitoring")
def get_monitoring(
    plot_id: UUID,
    user: dict = Depends(get_current_user),
) -> dict:
    with connection() as conn:
        plot = conn.execute(
            """
            SELECT id, farmer_id, monitoring_state, status, flags
            FROM plots
            WHERE id = %s AND (farmer_id = %s OR %s)
            """,
            (plot_id, user["id"], user["role"] in {"auditor", "admin"}),
        ).fetchone()
        if not plot:
            raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
        observations = conn.execute(
            """
            SELECT scene_id, observed_on, ndvi_plot, ndvi_control,
                   valid_px_plot, valid_px_control, source
            FROM ndvi_observations
            WHERE plot_id = %s
            ORDER BY observed_on, scene_id
            """,
            (plot_id,),
        ).fetchall()
        assessments = conn.execute(
            """
            SELECT id, state, previous_state, reason, reference_delta,
                   latest_delta, drop_value, observation_count, created_at
            FROM monitoring_assessments
            WHERE plot_id = %s
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (plot_id,),
        ).fetchall()
    return {
        "plot_id": str(plot_id),
        "monitoring_state": plot["monitoring_state"],
        "plot_status": plot["status"],
        "flags": plot["flags"],
        "observations": [
            {
                "scene_id": item["scene_id"],
                "observed_on": item["observed_on"],
                "ndvi_plot": item["ndvi_plot"],
                "ndvi_control": item["ndvi_control"],
                "relative_ndvi": item["ndvi_plot"] - item["ndvi_control"],
                "valid_px_plot": item["valid_px_plot"],
                "valid_px_control": item["valid_px_control"],
                "source": item["source"],
            }
            for item in observations
        ],
        "assessments": assessments,
    }
