from datetime import date, timedelta

from app.modules.monitoring.assessment import (
    AssessmentParameters,
    Observation,
    assess_monitoring,
)


def _series(deltas: list[float], *, start: date = date(2025, 1, 1)) -> list[Observation]:
    return [
        Observation(
            observed_on=start + timedelta(days=index * 30),
            ndvi_plot=0.5 + delta,
            ndvi_control=0.5,
            valid_px_plot=20,
            valid_px_control=30,
        )
        for index, delta in enumerate(deltas)
    ]


def test_common_seasonal_change_is_removed_by_control_ring() -> None:
    observations = [
        Observation(
            observed_on=date(2025, month, 1),
            ndvi_plot=plot,
            ndvi_control=control,
            valid_px_plot=15,
            valid_px_control=25,
        )
        for month, plot, control in (
            (1, 0.72, 0.52),
            (2, 0.62, 0.42),
            (3, 0.52, 0.32),
            (4, 0.62, 0.42),
        )
    ]

    assessment = assess_monitoring(observations)

    assert assessment.state == "ok"
    assert assessment.drop == 0


def test_sustained_plot_only_decline_freezes_after_two_observations() -> None:
    assessment = assess_monitoring(
        _series([0.3, 0.3, 0.3, -0.1, -0.1, -0.1]),
        AssessmentParameters(
            min_observations=4,
            rolling_n=2,
            freeze_consecutive=2,
        ),
    )

    assert assessment.state == "frozen"
    assert assessment.drop is not None and assessment.drop >= 0.30
    assert "frozen" in assessment.reason


def test_insufficient_observations_stay_pending() -> None:
    assessment = assess_monitoring(_series([0.2, 0.2, 0.2]))

    assert assessment.state == "pending"
    assert assessment.observation_count == 3
