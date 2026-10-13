import json
from datetime import date
from pathlib import Path
from urllib.error import URLError

import pandas as pd
import pytest

from fieldshift.climate_features import consecutive_dry_periods, historical_anomaly, seasonal_precipitation_total, temperature_summary
from fieldshift.nasa_power import PowerAPIError, PowerClient, PowerNetworkError, PowerRequest, PowerResponseError, PowerValidationError, parse_power_daily_response


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "power_daily_ludhiana_2024-01-01_2024-01-03.json"


def request() -> PowerRequest:
    return PowerRequest(30.9009, 75.8573, date(2024, 1, 1), date(2024, 1, 3))


def fixture_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def test_parses_dataframe_units_provenance_and_fill_values() -> None:
    dataset = parse_power_daily_response(fixture_payload(), request(), "https://example.test/power")
    assert list(dataset.data.columns) == ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN"]
    assert len(dataset.data) == 3
    assert pd.isna(dataset.data.loc[pd.Timestamp("2024-01-02"), "PRECTOTCORR"])
    assert dataset.provenance.parameter_metadata["PRECTOTCORR"].unit == "mm/day"
    assert dataset.provenance.parameter_metadata["ALLSKY_SFC_SW_DWN"].unit == "MJ/m^2/day"
    assert dataset.provenance.missing_observation_counts["PRECTOTCORR"] == 1
    assert dataset.provenance.latitude_returned == 30.901


def test_client_caches_identical_requests_and_returns_a_copy() -> None:
    calls = 0

    def transport(_: str, __: float) -> bytes:
        nonlocal calls
        calls += 1
        return FIXTURE_PATH.read_bytes()

    client = PowerClient(transport=transport)
    first = client.fetch_daily(request())
    first.data.loc[pd.Timestamp("2024-01-01"), "T2M"] = 999
    second = client.fetch_daily(request())
    assert calls == 1
    assert second.data.loc[pd.Timestamp("2024-01-01"), "T2M"] == 10.82


def test_validation_and_network_errors_are_clear() -> None:
    with pytest.raises(PowerValidationError, match="Latitude"):
        PowerRequest(91, 75, date(2024, 1, 1), date(2024, 1, 2))

    def broken_transport(_: str, __: float) -> bytes:
        raise URLError("offline")

    with pytest.raises(PowerNetworkError, match="Could not reach"):
        PowerClient(transport=broken_transport).fetch_daily(request())


def test_api_and_malformed_responses_are_rejected() -> None:
    with pytest.raises(PowerAPIError, match="rejected"):
        parse_power_daily_response({"errors": ["bad coordinate"]}, request(), "https://example.test/power")
    with pytest.raises(PowerResponseError, match="missing"):
        parse_power_daily_response({"messages": []}, request(), "https://example.test/power")


def test_documented_indicators_warn_or_require_explicit_definitions() -> None:
    dataset = parse_power_daily_response(fixture_payload(), request(), "https://example.test/power")
    precipitation = seasonal_precipitation_total(dataset.data)
    assert precipitation.value == 2.5
    assert precipitation.warning == "1 day(s) are missing and excluded from this total."
    summary = temperature_summary(dataset.data)
    assert round(summary.loc[pd.Timestamp("2024-01-01"), "T2M"], 2) == 10.78
    dry_runs = consecutive_dry_periods(dataset.data, dry_day_max_mm=0.0)
    assert dry_runs.to_dict("records") == [{"start_date": pd.Timestamp("2024-01-01"), "end_date": pd.Timestamp("2024-01-01"), "days": 1, "dry_day_max_mm": 0.0}]
    anomaly = historical_anomaly(precipitation, pd.Series([1.0, 2.0, 3.0]), "2021-2023 selected ranges")
    assert anomaly.value == 0.5
    assert "2021-2023" in anomaly.definition
