from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from psycopg import Connection
from psycopg.types.json import Jsonb

from app.core.config import settings
from app.core.errors import ApiError
from app.modules.carbon.engine import (
    CarbonParameters,
    EstimateInputs,
    SpeciesParameters,
    compute_estimate,
)
from app.modules.carbon.serialization import canonical_value, decimal_string


def load_active_parameters(conn: Connection) -> tuple[dict[str, Any], CarbonParameters, dict[str, SpeciesParameters]]:
    row = conn.execute(
        """
        SELECT id, version, is_placeholder, buffer_pct, satellite_multipliers,
               source_citation, notes
        FROM carbon_param_sets
        WHERE active
        """
    ).fetchone()
    if not row:
        raise ApiError(503, "CARBON_PARAMETERS_UNAVAILABLE", "No active carbon parameter set is configured.")
    species_rows = conn.execute(
        """
        SELECT species_code, growth_curve, root_shoot_ratio, carbon_fraction,
               target_density_per_ha, min_density_per_ha, max_density_per_ha,
               default_survival, source_citation, notes
        FROM species_params
        WHERE param_set_id = %s
        ORDER BY species_code
        """,
        (row["id"],),
    ).fetchall()
    species_params = {
        item["species_code"]: SpeciesParameters(
            species_code=item["species_code"],
            growth_curve=item["growth_curve"],
            root_shoot_ratio=item["root_shoot_ratio"],
            carbon_fraction=item["carbon_fraction"],
            target_density_per_ha=item["target_density_per_ha"],
            min_density_per_ha=item["min_density_per_ha"],
            max_density_per_ha=item["max_density_per_ha"],
            default_survival=item["default_survival"],
            source_citation=item["source_citation"],
            notes=item["notes"],
        )
        for item in species_rows
    }
    parameters = CarbonParameters(
        version=row["version"],
        is_placeholder=row["is_placeholder"],
        buffer_pct=row["buffer_pct"],
        satellite_multipliers=row["satellite_multipliers"],
        source_citation=row["source_citation"],
        notes=row["notes"],
    )
    public = {
        "id": str(row["id"]),
        "version": row["version"],
        "is_placeholder": row["is_placeholder"],
        "buffer_pct": row["buffer_pct"],
        "satellite_multipliers": row["satellite_multipliers"],
        "source_citation": row["source_citation"],
        "notes": row["notes"],
        "species": species_rows,
    }
    return public, parameters, species_params


def run_estimates(
    conn: Connection,
    *,
    actor_id: UUID,
    as_of: date,
    plot_ids: list[UUID] | None = None,
) -> list[dict[str, Any]]:
    if as_of > date.today():
        raise ApiError(422, "INVALID_AS_OF_DATE", "as_of cannot be a future date.")
    active_public, parameters, species_parameters = load_active_parameters(conn)
    if not species_parameters:
        raise ApiError(503, "CARBON_PARAMETERS_UNAVAILABLE", "The active parameter set has no species values.")

    plots = conn.execute(
        """
        SELECT p.id, p.farmer_id, p.area_ha, p.status, p.monitoring_state, p.flags
        FROM plots p
        WHERE (%s::uuid[] IS NULL OR p.id = ANY(%s::uuid[]))
        ORDER BY p.created_at, p.id
        """,
        (plot_ids, plot_ids),
    ).fetchall()
    estimates: list[dict[str, Any]] = []
    for plot in plots:
        planting_rows = conn.execute(
            """
            SELECT species_code, trees_planted, planted_on
            FROM plantings
            WHERE plot_id = %s AND planted_on <= %s
            ORDER BY planted_on, species_code
            """,
            (plot["id"], as_of),
        ).fetchall()
        if not planting_rows:
            continue
        missing_species = sorted(
            {item["species_code"] for item in planting_rows} - species_parameters.keys()
        )
        if missing_species:
            raise ApiError(
                422,
                "SPECIES_PARAMETERS_MISSING",
                "The active carbon parameter set does not include every planted species.",
                {"species_codes": missing_species},
            )
        photos = conn.execute(
            """
            SELECT gps_match, flags
            FROM plot_photos
            WHERE plot_id = %s
            ORDER BY created_at DESC
            """,
            (plot["id"],),
        ).fetchall()
        latest_observation = conn.execute(
            """
            SELECT observed_on, ndvi_plot, ndvi_control,
                   valid_px_plot, valid_px_control, source, scene_id
            FROM ndvi_observations
            WHERE plot_id = %s AND observed_on <= %s
            ORDER BY observed_on DESC, created_at DESC
            LIMIT 1
            """,
            (plot["id"], as_of),
        ).fetchone()
        prior_issued = conn.execute(
            """
            SELECT COALESCE(sum(be.tonnes_attributed), 0) AS total
            FROM batch_estimates be
            JOIN carbon_batches b ON b.id = be.batch_id
            WHERE be.plot_id = %s
              AND b.status IN ('approved', 'issued', 'listed', 'sold_out')
            """,
            (plot["id"],),
        ).fetchone()["total"]
        survival_override = conn.execute(
            """
            SELECT survival, note, auditor_id, created_at
            FROM plot_survival_overrides
            WHERE plot_id = %s
            """,
            (plot["id"],),
        ).fetchone()
        photo_flags = sorted({flag for item in photos for flag in item["flags"]})
        planting_snapshot = [
            {
                "species_code": item["species_code"],
                "trees_planted": item["trees_planted"],
                "planted_on": item["planted_on"],
            }
            for item in planting_rows
        ]
        latest_pixels = (
            (latest_observation["valid_px_plot"], latest_observation["valid_px_control"])
            if latest_observation
            else (None, None)
        )
        engine_inputs = EstimateInputs(
            plot_id=str(plot["id"]),
            area_ha=plot["area_ha"],
            plantings=planting_snapshot,
            monitoring_state=plot["monitoring_state"],
            as_of=as_of,
            already_issued_t=prior_issued,
            existing_flags=plot["flags"],
            has_gps_matched_photo=any(item["gps_match"] for item in photos),
            photo_flags=photo_flags,
            latest_valid_px_plot=latest_pixels[0],
            latest_valid_px_control=latest_pixels[1],
            min_valid_pixels=settings.carbon_min_valid_pixels,
            survival_override=survival_override["survival"] if survival_override else None,
            survival_override_note=survival_override["note"] if survival_override else None,
            plot_status=plot["status"],
        )
        try:
            result = compute_estimate(engine_inputs, parameters, species_parameters)
        except ValueError as exc:
            raise ApiError(
                422,
                "CARBON_ESTIMATE_INVALID",
                str(exc),
                {"plot_id": str(plot["id"])},
            ) from exc

        used_species = {
            code: {
                "growth_curve": species_parameters[code].growth_curve,
                "root_shoot_ratio": str(species_parameters[code].root_shoot_ratio),
                "carbon_fraction": str(species_parameters[code].carbon_fraction),
                "target_density_per_ha": str(species_parameters[code].target_density_per_ha),
                "min_density_per_ha": str(species_parameters[code].min_density_per_ha),
                "max_density_per_ha": str(species_parameters[code].max_density_per_ha),
                "default_survival": str(species_parameters[code].default_survival),
                "source_citation": species_parameters[code].source_citation,
                "notes": species_parameters[code].notes,
            }
            for code in sorted({item["species_code"] for item in planting_snapshot})
        }
        inputs_snapshot = canonical_value(
            {
                "plot": {
                    "id": plot["id"],
                    "area_ha": plot["area_ha"],
                    "status": plot["status"],
                    "monitoring_state": plot["monitoring_state"],
                    "flags": plot["flags"],
                },
                "plantings": planting_snapshot,
                "parameter_set": active_public,
                "species_parameters_used": used_species,
                "satellite": latest_observation,
                "photos": photos,
                "survival_override": survival_override,
                "already_issued_t": prior_issued,
                "as_of": as_of,
            }
        )
        estimate_id = uuid4()
        conn.execute(
            """
            INSERT INTO carbon_estimates
                (id, plot_id, param_set_id, as_of, inputs, area_ha,
                 co2e_gross_t, buffer_t, co2e_net_cum_t, already_issued_t,
                 issuable_t, flags, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                estimate_id,
                plot["id"],
                UUID(active_public["id"]),
                as_of,
                Jsonb(inputs_snapshot),
                plot["area_ha"],
                result.co2e_gross_t,
                result.buffer_t,
                result.co2e_net_cum_t,
                result.already_issued_t,
                result.issuable_t,
                list(result.flags),
                actor_id,
            ),
        )
        estimates.append(
            {
                "id": str(estimate_id),
                "plot_id": str(plot["id"]),
                "area_ha": decimal_string(plot["area_ha"]),
                "as_of": as_of.isoformat(),
                "co2e_gross_t": decimal_string(result.co2e_gross_t),
                "buffer_t": decimal_string(result.buffer_t),
                "co2e_net_cum_t": decimal_string(result.co2e_net_cum_t),
                "already_issued_t": decimal_string(result.already_issued_t),
                "issuable_t": decimal_string(result.issuable_t),
                "flags": list(result.flags),
                "parameter_version": parameters.version,
                "is_placeholder": parameters.is_placeholder,
            }
        )
    return estimates
