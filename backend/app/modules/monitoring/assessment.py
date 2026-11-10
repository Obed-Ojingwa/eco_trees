from dataclasses import dataclass
from datetime import date, timedelta
import math
from statistics import fmean
from typing import Iterable


@dataclass(frozen=True)
class Observation:
    observed_on: date
    ndvi_plot: float
    ndvi_control: float
    valid_px_plot: int
    valid_px_control: int
    source: str = "sentinel-2"

    @property
    def delta(self) -> float:
        return self.ndvi_plot - self.ndvi_control


@dataclass(frozen=True)
class AssessmentParameters:
    min_observations: int = 4
    rolling_n: int = 3
    reference_window_days: int = 365
    watch_drop: float = 0.15
    freeze_drop: float = 0.30
    freeze_consecutive: int = 2
    recover_consecutive: int = 3
    min_valid_pixels: int = 1


@dataclass(frozen=True)
class Assessment:
    state: str
    reason: str
    reference_delta: float | None
    latest_delta: float | None
    drop: float | None
    observation_count: int


def assess_monitoring(
    observations: Iterable[Observation],
    parameters: AssessmentParameters = AssessmentParameters(),
) -> Assessment:
    if parameters.rolling_n < 1:
        raise ValueError("rolling_n must be at least one.")
    if parameters.freeze_consecutive < 1 or parameters.recover_consecutive < 1:
        raise ValueError("Consecutive-observation thresholds must be at least one.")
    if parameters.freeze_drop < parameters.watch_drop:
        raise ValueError("freeze_drop must be greater than or equal to watch_drop.")

    valid = sorted(
        (
            item
            for item in observations
            if item.valid_px_plot >= parameters.min_valid_pixels
            and item.valid_px_control >= parameters.min_valid_pixels
        ),
        key=lambda item: (item.observed_on, item.source),
    )
    if len(valid) < parameters.min_observations:
        return Assessment(
            state="pending",
            reason=(
                f"Satellite check is pending: {len(valid)} valid observations "
                f"of {parameters.min_observations} required."
            ),
            reference_delta=None,
            latest_delta=None,
            drop=None,
            observation_count=len(valid),
        )

    deltas = [item.delta for item in valid]
    comparable: list[tuple[float, float, float]] = []
    for window_end in range(parameters.rolling_n - 1, len(valid)):
        window_start = window_end - parameters.rolling_n + 1
        start_date = valid[window_start].observed_on
        reference_cutoff = start_date - timedelta(days=parameters.reference_window_days)
        reference = [
            deltas[index]
            for index in range(window_start)
            if reference_cutoff <= valid[index].observed_on < start_date
        ]
        if not reference:
            continue
        reference_delta = fmean(reference)
        latest_delta = fmean(deltas[window_start : window_end + 1])
        drop = reference_delta - latest_delta
        if math.isclose(drop, 0.0, abs_tol=1e-12):
            drop = 0.0
        comparable.append((reference_delta, latest_delta, drop))

    if not comparable:
        return Assessment(
            state="pending",
            reason="Satellite check is pending: more reference observations are needed.",
            reference_delta=None,
            latest_delta=None,
            drop=None,
            observation_count=len(valid),
        )

    state = "pending"
    freeze_streak = 0
    recovery_streak = 0
    for _, _, drop in comparable:
        if state == "pending":
            state = "watch" if drop >= parameters.watch_drop else "ok"
            freeze_streak = 1 if drop >= parameters.freeze_drop else 0
            if freeze_streak >= parameters.freeze_consecutive:
                state = "frozen"
            continue

        if state == "frozen":
            if drop < parameters.watch_drop:
                recovery_streak += 1
                if recovery_streak >= parameters.recover_consecutive:
                    state = "ok"
                    freeze_streak = 0
                    recovery_streak = 0
            else:
                recovery_streak = 0
            continue

        recovery_streak = 0
        if drop >= parameters.freeze_drop:
            freeze_streak += 1
            state = "watch"
            if freeze_streak >= parameters.freeze_consecutive:
                state = "frozen"
        else:
            freeze_streak = 0
            state = "watch" if drop >= parameters.watch_drop else "ok"

    reference_delta, latest_delta, drop = comparable[-1]
    if state == "frozen":
        reason = (
            f"Plot greenness fell by {drop:.3f} relative to the control area. "
            "The plot is frozen for review."
        )
    elif state == "watch":
        reason = (
            f"Plot greenness is down by {drop:.3f} relative to the control area. "
            "Take a fresh photo and keep monitoring."
        )
    else:
        reason = (
            f"Plot greenness is stable relative to the control area "
            f"(change {drop:.3f})."
        )
    return Assessment(
        state=state,
        reason=reason,
        reference_delta=reference_delta,
        latest_delta=latest_delta,
        drop=drop,
        observation_count=len(valid),
    )
