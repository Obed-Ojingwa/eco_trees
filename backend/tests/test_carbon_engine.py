from datetime import date
from decimal import Decimal

import pytest

from app.modules.carbon.batches import allocate_batch_units
from app.modules.carbon.engine import (
    CarbonParameters,
    EstimateInputs,
    SpeciesParameters,
    compute_estimate,
    interpolate_growth_curve,
)
from app.modules.carbon.serialization import canonical_json, decimal_string


PARAMETERS = CarbonParameters(
    version="illustrative-test",
    is_placeholder=True,
    buffer_pct=Decimal("0.20"),
    satellite_multipliers={"ok": Decimal("1"), "watch": Decimal("0.8"), "frozen": Decimal("0")},
)
SPECIES = {
    "GMELINA": SpeciesParameters(
        species_code="GMELINA",
        growth_curve=[[0, 0], [1, 10]],
        root_shoot_ratio=Decimal("0.25"),
        carbon_fraction=Decimal("0.47"),
        target_density_per_ha=Decimal("500"),
        min_density_per_ha=Decimal("50"),
        max_density_per_ha=Decimal("2500"),
        default_survival=Decimal("0.90"),
    )
}


def _inputs(**overrides) -> EstimateInputs:
    values = {
        "plot_id": "plot-1",
        "area_ha": Decimal("0.5"),
        "plantings": [
            {
                "species_code": "GMELINA",
                "trees_planted": 250,
                "planted_on": date(2023, 1, 1),
            }
        ],
        "monitoring_state": "ok",
        "as_of": date(2024, 1, 2),
        "has_gps_matched_photo": True,
        "latest_valid_px_plot": 10,
        "latest_valid_px_control": 10,
        "plot_status": "verified",
    }
    values.update(overrides)
    return EstimateInputs(**values)


def test_golden_carbon_estimate_is_7_7550() -> None:
    result = compute_estimate(_inputs(), PARAMETERS, SPECIES)

    assert result.co2e_net_cum_t == Decimal("7.7550")
    assert result.co2e_gross_t == Decimal("9.6937")
    assert "PLACEHOLDER_PARAMS" in result.flags


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (Decimal("-1"), Decimal("0")),
        (Decimal("0.5"), Decimal("5")),
        (Decimal("2"), Decimal("10")),
    ],
)
def test_growth_curve_interpolation_boundaries(age: Decimal, expected: Decimal) -> None:
    assert interpolate_growth_curve([[0, 0], [1, 10]], age) == expected


def test_frozen_monitoring_and_prior_issuance_reduce_incremental_tonnes() -> None:
    frozen = compute_estimate(
        _inputs(monitoring_state="frozen"),
        PARAMETERS,
        SPECIES,
    )
    incremental = compute_estimate(
        _inputs(already_issued_t=Decimal("2.5")),
        PARAMETERS,
        SPECIES,
    )

    assert frozen.co2e_net_cum_t == Decimal("0.0000")
    assert frozen.issuable_t == Decimal("0.0000")
    assert "SATELLITE_FROZEN" in frozen.flags
    assert incremental.issuable_t == Decimal("5.2550")


def test_blocking_evidence_flags_are_preserved_for_auditor_review() -> None:
    result = compute_estimate(
        _inputs(
            has_gps_matched_photo=False,
            latest_valid_px_plot=1,
            latest_valid_px_control=10,
        ),
        PARAMETERS,
        SPECIES,
    )

    assert "NO_GPS_MATCHED_PHOTO" in result.flags
    assert "FEW_VALID_PIXELS" in result.flags
    assert "PLACEHOLDER_PARAMS" in result.flags


def test_batch_allocation_sums_to_units_and_never_exceeds_claims() -> None:
    claims = [
        ("estimate-a", Decimal("1.6000")),
        ("estimate-b", Decimal("0.6000")),
    ]

    allocations = allocate_batch_units(claims, 2)

    assert sum(allocations.values()) == Decimal("2.0000")
    assert all(
        allocations[claim_id] <= claimed
        for claim_id, claimed in claims
    )


def test_canonical_json_is_stable_and_sensitive_to_value_changes() -> None:
    first = canonical_json({"b": Decimal("1.00"), "a": ["x", 2]})
    reordered = canonical_json({"a": ["x", 2], "b": Decimal("1.00")})
    changed = canonical_json({"a": ["x", 3], "b": Decimal("1.00")})

    assert first == reordered
    assert first != changed


def test_decimal_api_values_preserve_fixed_point_precision() -> None:
    assert decimal_string(Decimal("12345678901234.1234")) == "12345678901234.1234"
