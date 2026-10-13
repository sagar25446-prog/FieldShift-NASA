"""Live test: run only when RUN_POWER_INTEGRATION=1 and network access is available."""

from datetime import date
import os

import pytest

from fieldshift.nasa_power import PowerClient, PowerRequest


pytestmark = pytest.mark.integration


@pytest.mark.skipif(os.getenv("RUN_POWER_INTEGRATION") != "1", reason="Set RUN_POWER_INTEGRATION=1 to call the live public NASA POWER API.")
def test_live_daily_point_request_returns_metadata_and_rows() -> None:
    request = PowerRequest(30.9009, 75.8573, date(2024, 1, 1), date(2024, 1, 3))
    dataset = PowerClient().fetch_daily(request, force_refresh=True)
    assert len(dataset.data) == 3
    assert dataset.provenance.parameter_metadata["T2M"].unit == "C"
    assert dataset.provenance.time_standard == "UTC"
