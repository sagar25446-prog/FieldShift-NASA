"""Live test: run only when RUN_SOILGRIDS_INTEGRATION=1 and network access is available.

ISRIC describes the SoilGrids REST API as a beta service that may be paused,
so a failure here says nothing about FieldShift's offline behaviour, which is
covered by fixture-based tests in test_soil_data.py.
"""

import os

import pytest

from fieldshift.soil_data import SoilGridsClient


pytestmark = pytest.mark.integration


@pytest.mark.skipif(os.getenv("RUN_SOILGRIDS_INTEGRATION") != "1", reason="Set RUN_SOILGRIDS_INTEGRATION=1 to call the live ISRIC SoilGrids REST API.")
def test_live_point_query_returns_units_depths_and_uncertainty() -> None:
    estimate = SoilGridsClient().fetch(30.85, 75.70, force_refresh=True)
    assert estimate.has_any_value
    clay = estimate.value("clay", "0-5cm")
    assert clay is not None and clay.unit == "%" and (clay.top_cm, clay.bottom_cm) == (0, 5)
    assert clay.q05 is not None and clay.q95 is not None and clay.uncertainty_ratio is not None
