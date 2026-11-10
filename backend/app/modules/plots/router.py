import hashlib
import json
import logging
from collections import defaultdict
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from psycopg.errors import DataException, RaiseException, UniqueViolation

from app.core.config import settings
from app.core.dependencies import get_current_user, require_roles
from app.core.errors import ApiError
from app.db.pool import connection
from app.modules.points import award_points, create_notification
from app.modules.plots.catalog import SPECIES
from app.modules.plots.schemas import PlotCreate, PlotPreflight


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["plots"])

DB_GEOMETRY_ERRORS = {
    "PLOT_OVERLAP": (409, "PLOT_OVERLAP", "This plot overlaps an existing registered plot."),
    "INVALID_GEOMETRY": (422, "INVALID_GEOMETRY", "The plot outline is not a valid polygon."),
    "AREA_OUT_OF_RANGE": (422, "AREA_OUT_OF_RANGE", "The plot area is outside the allowed range."),
}


def _map_geometry_error(exc: RaiseException) -> ApiError:
    message = exc.diag.message_primary or ""
    error = DB_GEOMETRY_ERRORS.get(message)
    if error:
        return ApiError(error[0], error[1], error[2])
    logger.exception("Unexpected plot geometry database error")
    return ApiError(422, "INVALID_GEOMETRY", "The plot outline could not be validated.")


def _plot_access(plot_id: UUID, user: dict) -> dict:
    with connection() as conn:
        plot = conn.execute(
            """
            SELECT p.id, p.farmer_id, p.area_ha, p.status,
                   p.monitoring_state, p.flags, p.created_at, p.updated_at,
                   u.display_name AS farmer_display_name
            FROM plots p
            JOIN users u ON u.id = p.farmer_id
            WHERE p.id = %s
              AND (p.farmer_id = %s OR %s)
            """,
            (
                plot_id,
                user["id"],
                user["role"] in {"auditor", "admin"},
            ),
        ).fetchone()
    if not plot:
        raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
    return plot


def _serialize_plot(
    row: dict,
    plantings: list[dict],
    photos: list[dict],
) -> dict:
    return {
        "id": str(row["id"]),
        "farmer_id": str(row["farmer_id"]),
        "farmer_display_name": row.get("farmer_display_name"),
        "geometry": json.loads(row["geometry"]) if isinstance(row.get("geometry"), str) else row.get("geometry"),
        "area_ha": float(row["area_ha"]),
        "status": row["status"],
        "monitoring_state": row["monitoring_state"],
        "flags": row["flags"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "plantings": [
            {
                "id": str(planting["id"]),
                "species_code": planting["species_code"],
                "trees_planted": planting["trees_planted"],
                "planted_on": planting["planted_on"],
            }
            for planting in plantings
        ],
        "photos": [
            {
                "id": str(photo["id"]),
                "captured_at": photo["captured_at"],
                "accuracy_m": float(photo["accuracy_m"]),
                "distance_m": float(photo["distance_m"]),
                "gps_match": photo["gps_match"],
                "flags": photo["flags"],
                "content_url": f"/api/plots/{row['id']}/photos/{photo['id']}",
            }
            for photo in photos
        ],
    }


@router.get("/species")
def list_species() -> dict:
    return {"items": list(SPECIES)}


@router.post(
    "/plots/preflight",
    dependencies=[Depends(require_roles("farmer", "admin"))],
)
def preflight_plot(
    payload: PlotPreflight,
) -> dict:
    geojson = json.dumps(payload.geometry.as_geojson(), separators=(",", ":"))
    try:
        with connection() as conn:
            result = conn.execute(
                """
                WITH candidate AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) AS geom
                )
                SELECT
                    ST_IsValid(candidate.geom) AS valid,
                    ST_Area(candidate.geom::geography) / 10000.0 AS area_ha
                FROM candidate
                """,
                (geojson,),
            ).fetchone()
            if not result["valid"]:
                raise ApiError(422, "INVALID_GEOMETRY", "The plot outline is not a valid polygon.")
            area_ha = float(result["area_ha"])
            if not settings.min_plot_area_ha <= area_ha <= settings.max_plot_area_ha:
                raise ApiError(
                    422,
                    "AREA_OUT_OF_RANGE",
                    "The plot area is outside the allowed range.",
                    {"area_ha": round(area_ha, 6)},
                )
            overlap = conn.execute(
                """
                WITH candidate AS (
                    SELECT ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) AS geom
                )
                SELECT COALESCE(
                    sum(ST_Area(ST_Intersection(existing.geom::geography, candidate.geom::geography))),
                    0
                ) AS overlap_area_m2
                FROM candidate
                JOIN plots AS existing
                  ON existing.geom && candidate.geom
                 AND ST_Intersects(existing.geom, candidate.geom)
                 AND ST_Area(ST_Intersection(existing.geom::geography, candidate.geom::geography)) > 0.01
                WHERE existing.status <> 'rejected'
                """,
                (geojson,),
            ).fetchone()
    except (DataException, RaiseException) as exc:
        raise _map_geometry_error(exc)

    overlap_m2 = float(overlap["overlap_area_m2"])
    overlap_percent = min(100.0, overlap_m2 / (area_ha * 10_000) * 100) if area_ha else 0
    return {
        "ok": overlap_m2 <= 0.01,
        "area_ha": round(area_ha, 6),
        "overlap_area_m2": round(overlap_m2, 2),
        "overlap_percent": round(overlap_percent, 2),
        "warnings": [],
    }


@router.post("/plots", status_code=201)
def create_plot(
    payload: PlotCreate,
    user: dict = Depends(require_roles("farmer")),
) -> dict:
    plot_id = uuid4()
    geojson = json.dumps(payload.geometry.as_geojson(), separators=(",", ":"))
    planted_count = sum(item.trees_planted for item in payload.plantings)
    warning_flags: list[str] = []
    try:
        with connection() as conn, conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(71024019)")
            plot = conn.execute(
                """
                INSERT INTO plots (id, farmer_id, geom)
                VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                RETURNING id, farmer_id, ST_AsGeoJSON(geom) AS geometry,
                          area_ha, status, monitoring_state, flags,
                          created_at, updated_at
                """,
                (plot_id, user["id"], geojson),
            ).fetchone()
            density = planted_count / float(plot["area_ha"])
            if density < settings.density_min_per_ha:
                warning_flags.append("DENSITY_BELOW_MIN")
            elif density > settings.density_max_per_ha:
                warning_flags.append("DENSITY_ABOVE_MAX")
            if warning_flags:
                plot = conn.execute(
                    """
                    UPDATE plots SET flags = %s, updated_at = now()
                    WHERE id = %s
                    RETURNING id, farmer_id, ST_AsGeoJSON(geom) AS geometry,
                              area_ha, status, monitoring_state, flags,
                              created_at, updated_at
                    """,
                    (warning_flags, plot_id),
                ).fetchone()

            for planting in payload.plantings:
                conn.execute(
                    """
                    INSERT INTO plantings (id, plot_id, species_code, trees_planted, planted_on)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        uuid4(),
                        plot_id,
                        planting.species_code,
                        planting.trees_planted,
                        planting.planted_on,
                    ),
                )
            points = award_points(conn, user["id"], "plot_mapped", plot_id, 100)
            create_notification(
                conn,
                user["id"],
                "plot_mapped",
                plot_id,
                "Your plot has been mapped.",
                points=points,
            )
            plantings = conn.execute(
                """
                SELECT id, species_code, trees_planted, planted_on
                FROM plantings
                WHERE plot_id = %s
                ORDER BY planted_on, species_code
                """,
                (plot_id,),
            ).fetchall()
            response = _serialize_plot(plot, plantings, [])
    except RaiseException as exc:
        raise _map_geometry_error(exc)
    except DataException as exc:
        raise ApiError(422, "INVALID_GEOMETRY", "The plot outline is not a valid polygon.") from exc
    except UniqueViolation:
        raise ApiError(409, "PLANTING_ALREADY_EXISTS", "This planting is already recorded for the plot.")

    response["density_trees_per_ha"] = round(density, 2)
    response["points_awarded"] = points
    return response


@router.get("/plots")
def list_plots(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] not in {"farmer", "auditor", "admin"}:
        raise ApiError(403, "FORBIDDEN", "You do not have permission to view plots.")
    with connection() as conn:
        if user["role"] in {"auditor", "admin"}:
            rows = conn.execute(
                """
                SELECT p.id, p.farmer_id, ST_AsGeoJSON(p.geom) AS geometry,
                       p.area_ha, p.status, p.monitoring_state, p.flags,
                       p.created_at, p.updated_at, u.display_name AS farmer_display_name
                FROM plots p JOIN users u ON u.id = p.farmer_id
                ORDER BY p.created_at DESC
                LIMIT 500
                """
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT p.id, p.farmer_id, ST_AsGeoJSON(p.geom) AS geometry,
                       p.area_ha, p.status, p.monitoring_state, p.flags,
                       p.created_at, p.updated_at, NULL::text AS farmer_display_name
                FROM plots p
                WHERE p.farmer_id = %s
                ORDER BY p.created_at DESC
                LIMIT 500
                """,
                (user["id"],),
            ).fetchall()
        plot_ids = [row["id"] for row in rows]
        if not plot_ids:
            return {"items": []}
        plantings_by_plot: dict[UUID, list[dict]] = defaultdict(list)
        for planting in conn.execute(
            """
            SELECT plot_id, id, species_code, trees_planted, planted_on
            FROM plantings
            WHERE plot_id = ANY(%s)
            ORDER BY plot_id, planted_on, species_code
            """,
            (plot_ids,),
        ).fetchall():
            plantings_by_plot[planting["plot_id"]].append(planting)
        photos_by_plot: dict[UUID, list[dict]] = defaultdict(list)
        for photo in conn.execute(
            """
            SELECT plot_id, id, captured_at, accuracy_m, distance_m, gps_match, flags
            FROM plot_photos
            WHERE plot_id = ANY(%s)
            ORDER BY plot_id, created_at DESC
            """,
            (plot_ids,),
        ).fetchall():
            photos_by_plot[photo["plot_id"]].append(photo)
        return {
            "items": [
                _serialize_plot(
                    row,
                    plantings_by_plot[row["id"]],
                    photos_by_plot[row["id"]],
                )
                for row in rows
            ]
        }


@router.get("/plots/{plot_id}")
def get_plot(
    plot_id: UUID,
    user: dict = Depends(get_current_user),
) -> dict:
    row = _plot_access(plot_id, user)
    with connection() as conn:
        row["geometry"] = conn.execute(
            "SELECT ST_AsGeoJSON(geom) AS geometry FROM plots WHERE id = %s",
            (plot_id,),
        ).fetchone()["geometry"]
        plantings = conn.execute(
            """
            SELECT id, species_code, trees_planted, planted_on
            FROM plantings
            WHERE plot_id = %s
            ORDER BY planted_on, species_code
            """,
            (row["id"],),
        ).fetchall()
        photos = conn.execute(
            """
            SELECT id, captured_at, accuracy_m, distance_m, gps_match, flags
            FROM plot_photos
            WHERE plot_id = %s
            ORDER BY created_at DESC
            """,
            (row["id"],),
        ).fetchall()
        return _serialize_plot(row, plantings, photos)


def _image_type(content_type: str | None, content: bytes) -> str | None:
    detected: str | None = None
    if content.startswith(b"\xff\xd8\xff"):
        detected = "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = "image/png"
    elif len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        detected = "image/webp"
    if detected and content_type == detected:
        return detected
    return None


@router.post("/plots/{plot_id}/photos", status_code=201)
def upload_plot_photo(
    plot_id: UUID,
    file: UploadFile = File(...),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    accuracy_m: float = Form(..., ge=0, le=100_000),
    user: dict = Depends(require_roles("farmer")),
) -> dict:
    content = file.file.read(settings.max_photo_bytes + 1)
    file.file.close()
    if not content:
        raise ApiError(422, "EMPTY_PHOTO", "Choose a photo to upload.")
    if len(content) > settings.max_photo_bytes:
        raise ApiError(
            413,
            "PHOTO_TOO_LARGE",
            "The photo is larger than the upload limit.",
            {"max_bytes": settings.max_photo_bytes},
        )
    content_type = _image_type(file.content_type, content)
    if not content_type:
        raise ApiError(415, "UNSUPPORTED_PHOTO_TYPE", "Upload a valid JPEG, PNG, or WebP image.")

    photo_id = uuid4()
    sha256 = hashlib.sha256(content).hexdigest()
    flags: list[str] = []
    if accuracy_m > settings.photo_accuracy_limit_m:
        flags.append("PHOTO_ACCURACY_POOR")
    try:
        with connection() as conn, conn.transaction():
            plot = conn.execute(
                """
                SELECT id, farmer_id, status,
                       ST_Distance(
                           geom::geography,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                       ) AS distance_m
                FROM plots
                WHERE id = %s AND farmer_id = %s
                FOR UPDATE
                """,
                (longitude, latitude, plot_id, user["id"]),
            ).fetchone()
            if not plot:
                raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
            if plot["status"] in {"rejected", "frozen"}:
                raise ApiError(409, "PLOT_NOT_ACCEPTING_EVIDENCE", "This plot is not accepting new evidence.")
            distance_m = float(plot["distance_m"])
            gps_match = distance_m <= settings.photo_gps_tolerance_m
            if not gps_match:
                flags.append("NO_GPS_MATCHED_PHOTO")
            conn.execute(
                """
                INSERT INTO plot_photos
                    (id, plot_id, farmer_id, content_type, content, sha256, gps,
                     accuracy_m, distance_m, gps_match, flags)
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    %s, %s, %s, %s
                )
                """,
                (
                    photo_id,
                    plot_id,
                    user["id"],
                    content_type,
                    content,
                    sha256,
                    longitude,
                    latitude,
                    accuracy_m,
                    distance_m,
                    gps_match,
                    flags,
                ),
            )
            if flags:
                conn.execute(
                    """
                    UPDATE plots
                    SET flags = ARRAY(
                        SELECT DISTINCT unnest(flags || %s::text[])
                    ), updated_at = now()
                    WHERE id = %s
                    """,
                    (flags, plot_id),
                )
            points = award_points(conn, user["id"], "photo_uploaded", photo_id, 100)
            create_notification(
                conn,
                user["id"],
                "photo_uploaded",
                photo_id,
                "A photo has been added to your plot evidence.",
                points=points,
            )
    except UniqueViolation:
        raise ApiError(409, "PHOTO_REUSED", "This photo has already been submitted.")

    return {
        "id": str(photo_id),
        "plot_id": str(plot_id),
        "gps_match": gps_match,
        "distance_m": round(distance_m, 2),
        "accuracy_m": accuracy_m,
        "flags": flags,
        "points_awarded": points,
        "content_url": f"/api/plots/{plot_id}/photos/{photo_id}",
    }


@router.get("/plots/{plot_id}/photos/{photo_id}")
def get_plot_photo(
    plot_id: UUID,
    photo_id: UUID,
    user: dict = Depends(get_current_user),
) -> Response:
    _plot_access(plot_id, user)
    with connection() as conn:
        photo = conn.execute(
            """
            SELECT content, content_type
            FROM plot_photos
            WHERE id = %s AND plot_id = %s
            """,
            (photo_id, plot_id),
        ).fetchone()
    if not photo:
        raise ApiError(404, "PHOTO_NOT_FOUND", "Photo not found.")
    return Response(
        content=bytes(photo["content"]),
        media_type=photo["content_type"],
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/plots/{plot_id}/submit")
def submit_plot(
    plot_id: UUID,
    user: dict = Depends(require_roles("farmer")),
) -> dict:
    with connection() as conn, conn.transaction():
        plot = conn.execute(
            """
            SELECT id, status
            FROM plots
            WHERE id = %s AND farmer_id = %s
            FOR UPDATE
            """,
            (plot_id, user["id"]),
        ).fetchone()
        if not plot:
            raise ApiError(404, "PLOT_NOT_FOUND", "Plot not found.")
        if plot["status"] != "draft":
            raise ApiError(409, "PLOT_ALREADY_SUBMITTED", "Only a draft plot can be submitted.")
        planting_count = conn.execute(
            "SELECT count(*) AS total FROM plantings WHERE plot_id = %s",
            (plot_id,),
        ).fetchone()["total"]
        photo_count = conn.execute(
            "SELECT count(*) AS total FROM plot_photos WHERE plot_id = %s",
            (plot_id,),
        ).fetchone()["total"]
        if planting_count == 0:
            raise ApiError(422, "PLANTING_REQUIRED", "Add at least one planting before submitting.")
        if photo_count == 0:
            raise ApiError(422, "PHOTO_REQUIRED", "Add at least one photo before submitting.")
        submitted_at = conn.execute(
            """
            UPDATE plots
            SET status = 'submitted', updated_at = now()
            WHERE id = %s
            RETURNING updated_at
            """,
            (plot_id,),
        ).fetchone()["updated_at"]
    return {
        "plot_id": str(plot_id),
        "status": "submitted",
        "submitted_at": submitted_at.isoformat(),
    }


@router.get("/plots/{plot_id}/photos")
def list_plot_photos(
    plot_id: UUID,
    user: dict = Depends(get_current_user),
) -> dict:
    _plot_access(plot_id, user)
    with connection() as conn:
        photos = conn.execute(
            """
            SELECT id, captured_at, accuracy_m, distance_m, gps_match, flags
            FROM plot_photos WHERE plot_id = %s ORDER BY created_at DESC
            """,
            (plot_id,),
        ).fetchall()
    return {
        "items": [
            {
                "id": str(item["id"]),
                "captured_at": item["captured_at"],
                "accuracy_m": float(item["accuracy_m"]),
                "distance_m": float(item["distance_m"]),
                "gps_match": item["gps_match"],
                "flags": item["flags"],
                "content_url": f"/api/plots/{plot_id}/photos/{item['id']}",
            }
            for item in photos
        ]
    }
