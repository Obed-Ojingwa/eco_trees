from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Any, Mapping, Sequence


TONNE_QUANTUM = Decimal("0.0001")
ZERO = Decimal("0")
CO2_TO_CARBON = Decimal(44) / Decimal(12)


def decimal_value(value: Any, *, name: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be a decimal number.") from exc
    if not result.is_finite():
        raise ValueError(f"{name} must be finite.")
    return result


def round_tonnes(value: Decimal) -> Decimal:
    return value.quantize(TONNE_QUANTUM, rounding=ROUND_DOWN)


def interpolate_growth_curve(
    growth_curve: Sequence[Sequence[Any]],
    age_years: Decimal,
) -> Decimal:
    if not growth_curve:
        raise ValueError("growth_curve must contain at least one point.")
    points: list[tuple[Decimal, Decimal]] = []
    for index, point in enumerate(growth_curve):
        if len(point) != 2:
            raise ValueError("Each growth_curve point must contain age and biomass.")
        age = decimal_value(point[0], name=f"growth_curve[{index}].age")
        biomass = decimal_value(point[1], name=f"growth_curve[{index}].biomass")
        if age < ZERO or biomass < ZERO:
            raise ValueError("Growth curve age and biomass must be non-negative.")
        points.append((age, biomass))
    points.sort(key=lambda point: point[0])
    if len({age for age, _ in points}) != len(points):
        raise ValueError("growth_curve ages must be unique.")
    if age_years < points[0][0]:
        return ZERO
    if age_years >= points[-1][0]:
        return points[-1][1]
    for (left_age, left_value), (right_age, right_value) in zip(points, points[1:]):
        if left_age <= age_years <= right_age:
            fraction = (age_years - left_age) / (right_age - left_age)
            return left_value + fraction * (right_value - left_value)
    raise RuntimeError("Validated growth curve did not contain the requested age.")


@dataclass(frozen=True)
class SpeciesParameters:
    species_code: str
    growth_curve: Sequence[Sequence[Any]]
    root_shoot_ratio: Any
    carbon_fraction: Any
    target_density_per_ha: Any
    min_density_per_ha: Any
    max_density_per_ha: Any
    default_survival: Any
    source_citation: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class CarbonParameters:
    version: str
    is_placeholder: bool
    buffer_pct: Any
    satellite_multipliers: Mapping[str, Any]
    source_citation: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class EstimateInputs:
    plot_id: str
    area_ha: Any
    plantings: Sequence[Mapping[str, Any]]
    monitoring_state: str
    as_of: date
    already_issued_t: Any = ZERO
    existing_flags: Sequence[str] = ()
    has_gps_matched_photo: bool = False
    photo_flags: Sequence[str] = ()
    latest_valid_px_plot: int | None = None
    latest_valid_px_control: int | None = None
    min_valid_pixels: int = 5
    survival_override: Any | None = None
    survival_override_note: str | None = None
    plot_status: str = "verified"


@dataclass(frozen=True)
class Estimate:
    co2e_gross_t: Decimal
    buffer_t: Decimal
    co2e_net_cum_t: Decimal
    already_issued_t: Decimal
    issuable_t: Decimal
    flags: tuple[str, ...]


def compute_estimate(
    inputs: EstimateInputs,
    params: CarbonParameters,
    species_params: Mapping[str, SpeciesParameters],
) -> Estimate:
    area_ha = decimal_value(inputs.area_ha, name="area_ha")
    already_issued = decimal_value(inputs.already_issued_t, name="already_issued_t")
    buffer_pct = decimal_value(params.buffer_pct, name="buffer_pct")
    if area_ha <= ZERO:
        raise ValueError("area_ha must be greater than zero.")
    if already_issued < ZERO:
        raise ValueError("already_issued_t must be non-negative.")
    if not ZERO <= buffer_pct <= Decimal(1):
        raise ValueError("buffer_pct must be between zero and one.")
    if not inputs.plantings:
        raise ValueError("At least one planting is required.")
    if inputs.survival_override is not None and not inputs.survival_override_note:
        raise ValueError("A survival override requires an audit note.")

    flags = set(inputs.existing_flags)
    flags.update(inputs.photo_flags)
    if params.is_placeholder:
        flags.add("PLACEHOLDER_PARAMS")
    if not inputs.has_gps_matched_photo:
        flags.add("NO_GPS_MATCHED_PHOTO")
    if inputs.latest_valid_px_plot is None or inputs.latest_valid_px_control is None:
        flags.add("FEW_VALID_PIXELS")
    elif (
        inputs.latest_valid_px_plot < inputs.min_valid_pixels
        or inputs.latest_valid_px_control < inputs.min_valid_pixels
    ):
        flags.add("FEW_VALID_PIXELS")
    if inputs.monitoring_state == "pending":
        flags.add("SATELLITE_PENDING")
    elif inputs.monitoring_state == "frozen":
        flags.add("SATELLITE_FROZEN")
    if inputs.plot_status != "verified":
        flags.add("PLOT_NOT_VERIFIED")

    gross = ZERO
    for planting in inputs.plantings:
        species_code = str(planting["species_code"])
        species = species_params.get(species_code)
        if species is None:
            raise ValueError(f"No carbon parameters for species {species_code}.")
        trees = decimal_value(planting["trees_planted"], name="trees_planted")
        if trees <= ZERO:
            raise ValueError("trees_planted must be greater than zero.")
        planted_on = planting["planted_on"]
        if isinstance(planted_on, str):
            planted_on = date.fromisoformat(planted_on)
        if not isinstance(planted_on, date) or planted_on > inputs.as_of:
            raise ValueError("planted_on must be a date on or before as_of.")
        age_years = Decimal((inputs.as_of - planted_on).days) / Decimal("365.25")
        default_survival = decimal_value(
            species.default_survival,
            name=f"{species_code}.default_survival",
        )
        survival = (
            decimal_value(inputs.survival_override, name="survival_override")
            if inputs.survival_override is not None
            else default_survival
        )
        if not ZERO <= survival <= Decimal(1):
            raise ValueError("Survival must be between zero and one.")
        target_density = decimal_value(
            species.target_density_per_ha,
            name=f"{species_code}.target_density_per_ha",
        )
        if target_density <= ZERO:
            raise ValueError("target_density_per_ha must be greater than zero.")
        planted_density = trees / area_ha
        minimum_density = decimal_value(
            species.min_density_per_ha,
            name=f"{species_code}.min_density_per_ha",
        )
        maximum_density = decimal_value(
            species.max_density_per_ha,
            name=f"{species_code}.max_density_per_ha",
        )
        if planted_density < minimum_density:
            flags.add("DENSITY_BELOW_MIN")
        if planted_density > maximum_density:
            flags.add("DENSITY_ABOVE_MAX")

        live_density = trees * survival / area_ha
        stocking_factor = min(Decimal(1), live_density / target_density)
        agb_per_ha = interpolate_growth_curve(species.growth_curve, age_years)
        agb = agb_per_ha * area_ha * stocking_factor
        root_shoot_ratio = decimal_value(
            species.root_shoot_ratio,
            name=f"{species_code}.root_shoot_ratio",
        )
        carbon_fraction = decimal_value(
            species.carbon_fraction,
            name=f"{species_code}.carbon_fraction",
        )
        if root_shoot_ratio < ZERO or not ZERO <= carbon_fraction <= Decimal(1):
            raise ValueError(
                f"Carbon parameters for {species_code} are outside valid ranges."
            )
        bgb = agb * root_shoot_ratio
        gross += (agb + bgb) * carbon_fraction * CO2_TO_CARBON
    buffer = gross * buffer_pct
    multipliers = {
        state: decimal_value(value, name=f"satellite_multipliers.{state}")
        for state, value in params.satellite_multipliers.items()
    }
    if inputs.monitoring_state not in multipliers:
        raise ValueError(
            f"No satellite multiplier configured for {inputs.monitoring_state!r}."
        )
    satellite_multiplier = multipliers[inputs.monitoring_state]
    if not ZERO <= satellite_multiplier <= Decimal(1):
        raise ValueError("Satellite multipliers must be between zero and one.")
    net = (gross - buffer) * satellite_multiplier
    if inputs.plot_status != "verified":
        net = ZERO
    if net < already_issued:
        flags.add("REVERSAL_RISK")
    issuable = max(ZERO, net - already_issued)
    return Estimate(
        co2e_gross_t=round_tonnes(gross),
        buffer_t=round_tonnes(buffer),
        co2e_net_cum_t=round_tonnes(net),
        already_issued_t=round_tonnes(already_issued),
        issuable_t=round_tonnes(issuable),
        flags=tuple(sorted(flags)),
    )
