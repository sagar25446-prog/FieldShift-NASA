"""Live test: run only when RUN_MODIS_INTEGRATION=1 and network access is available.

The ORNL DAAC subset service sometimes returns HTTP 502; a failure here does not
affect the fixture-based tests in test_land_use_phenology.py.
"""

import os

import pytest

from fieldshift.land_use_phenology import PhenologyClient, season_use


pytestmark = pytest.mark.integration


@pytest.mark.skipif(os.getenv("RUN_MODIS_INTEGRATION") != "1", reason="Set RUN_MODIS_INTEGRATION=1 to call the live ORNL DAAC MODIS subset service.")
def test_live_mcd12q2_query_for_demo_farm() -> None:
    record = PhenologyClient().fetch(30.85, 75.70, 2021, 2023)
    assert record.years == (2021, 2022, 2023)
    use = season_use(record)
    assert use["kharif"].summary == "regularly_green"
