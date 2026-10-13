import pytest

from fieldshift.agronomy import evaluate_rotation
from fieldshift.data_access import DataSourceNotConfiguredError, fetch_earth_observations, source_statuses
from fieldshift.recommendations import RecommendationNotReadyError, compare_rotations


def test_source_statuses_are_explicit_about_readiness() -> None:
    statuses = source_statuses()

    assert len(statuses) == 3
    assert all(status.message for status in statuses)
    assert statuses[0].available is True
    assert statuses[1].available is False
    assert statuses[2].available is True


def test_unconfigured_earth_observations_raise_a_helpful_error() -> None:
    with pytest.raises(DataSourceNotConfiguredError, match="not configured"):
        fetch_earth_observations()


def test_unvalidated_agronomy_does_not_claim_feasibility() -> None:
    result = evaluate_rotation()
    assert result.feasible is False
    assert "not been validated" in result.explanation


def test_unimplemented_recommendations_do_not_return_a_result() -> None:
    with pytest.raises(RecommendationNotReadyError, match="unavailable"):
        compare_rotations()
