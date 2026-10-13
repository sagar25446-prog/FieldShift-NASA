"""MODIS MCD12Q2 observed-land-use adapter and its role in plan evaluation.

The fixture is the unmodified ORNL DAAC response for the demo farm pixel
(30.85 N, 75.70 E), saved 2026-10-13. No test calls the live service.
"""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from fieldshift.land_use_phenology import (
    BANDS,
    FILL_VALUE,
    PhenologyClient,
    PhenologyError,
    PhenologyNetworkError,
    PhenologyResponseError,
    VegetationCycle,
    build_band_url,
    load_demo_phenology,
    parse_phenology,
    season_of_cycle,
    season_use,
)
from fieldshift.nasa_power import load_offline_demo_snapshot
from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "modis_mcd12q2_demo_farm_2016_2025.json"
EPOCH = date(1970, 1, 1)


def days(d: date) -> int:
    return (d - EPOCH).days


def wrapper(years: list[int], num_cycles: dict[int, int], cycles: dict[tuple[int, int], dict]) -> dict:
    """Synthetic ORNL-shaped responses: cycles[(year, mode)] = {MidGreenup: date, ...}."""
    bands = {}
    for band in BANDS:
        subset = []
        for year in years:
            if band == "NumCycles":
                value = num_cycles.get(year, FILL_VALUE)
            else:
                name, mode = band.split(".Num_Modes_0")
                entry = cycles.get((year, int(mode)), {})
                raw = entry.get(name, FILL_VALUE)
                value = days(raw) if isinstance(raw, date) else raw
            subset.append({"calendar_date": f"{year}-01-01", "data": [value], "proc_date": "2022113103008"})
        bands[band] = {"source_url": f"https://example.test/{band}", "response": {"latitude": 30.0, "longitude": 75.0, "subset": subset}}
    return {"_fixture_metadata": {"latitude": 30.0, "longitude": 75.0, "retrieved_at_utc": "2026-10-13T00:00:00Z"}, "bands": bands}


def cycle(mid_up: date, mid_down: date, qa: int = 0) -> dict:
    return {"Greenup": mid_up, "MidGreenup": mid_up, "MidGreendown": mid_down, "Dormancy": mid_down, "EVI_Amplitude": 3000, "QA_Overall": qa}


@pytest.fixture(scope="module")
def record():
    return parse_phenology(json.loads(FIXTURE.read_text(encoding="utf-8")))


class TestParsing:
    def test_saved_fixture_metadata_units_and_quality(self, record) -> None:
        assert record.years == tuple(range(2016, 2026))
        assert all(record.num_cycles[y] == 2 for y in record.years)
        first = record.cycles[0]
        assert first.mid_greenup == date(2016, 1, 10)  # days since 1970-01-01 → date
        assert first.evi2_amplitude == pytest.approx(0.318)  # scale factor 0.0001
        assert first.quality == "best"
        assert record.retrieved_at_utc == "2026-10-13T12:48:18Z"
        assert "500 m" in record.resolution and "MCD12Q2" in record.product
        assert all("modis.ornl.gov/rst/api/v1/MCD12Q2/subset" in url for url in record.source_urls)
        assert record.processing_dates  # processing dates retained from the service

    def test_fill_values_become_missing(self) -> None:
        parsed = parse_phenology(wrapper([2020], {}, {}))
        assert parsed.num_cycles[2020] is None and parsed.cycles == ()

    def test_malformed_response_is_rejected(self) -> None:
        bad = wrapper([2020], {2020: 1}, {})
        del bad["bands"]["NumCycles"]
        with pytest.raises(PhenologyResponseError, match="missing"):
            parse_phenology(bad)
        two_pixels = wrapper([2020], {2020: 1}, {})
        two_pixels["bands"]["NumCycles"]["response"]["subset"][0]["data"] = [1, 2]
        with pytest.raises(PhenologyResponseError, match="exactly one pixel"):
            parse_phenology(two_pixels)

    def test_demo_loader_is_labelled_saved(self) -> None:
        assert load_demo_phenology().mode == "saved"


class TestSeasonAssignment:
    def test_cycles_land_in_expected_windows(self, record) -> None:
        rabi, kharif = record.cycles[0], record.cycles[1]
        assert season_of_cycle(rabi) == ("rabi", 2015)  # centre in Feb 2016 → rabi 2015–16
        assert season_of_cycle(kharif) == ("kharif", 2016)

    def test_overlap_goes_to_window_with_largest_overlap(self) -> None:
        # Centre in April (rabi and summer windows overlap). Most of the span is in March → rabi.
        early = VegetationCycle(2020, 1, None, date(2020, 2, 20), date(2020, 4, 20), None, 0.3, 0)
        assert season_of_cycle(early)[0] == "rabi"
        late = VegetationCycle(2020, 1, None, date(2020, 4, 10), date(2020, 6, 10), None, 0.3, 0)
        assert season_of_cycle(late)[0] == "summer"

    def test_demo_farm_season_use(self, record) -> None:
        use = season_use(record)
        assert (use["kharif"].summary, use["kharif"].with_cycle, use["kharif"].clear) == ("regularly_green", 10, 10)
        assert (use["rabi"].summary, use["rabi"].with_cycle, use["rabi"].clear) == ("regularly_green", 9, 9)
        assert (use["summer"].summary, use["summer"].with_cycle, use["summer"].clear) == ("not_green", 0, 10)
        assert "2016 to 2025" in use["summer"].sentence()

    def test_unclear_years_are_not_counted_as_fallow(self) -> None:
        years = [2019, 2020, 2021, 2022]
        data = wrapper(years, {2019: 1, 2020: 3, 2022: 1}, {
            (2019, 1): cycle(date(2019, 7, 20), date(2019, 10, 10)),
            (2022, 1): cycle(date(2022, 7, 20), date(2022, 10, 10), qa=3),
        })
        use = season_use(parse_phenology(data))["kharif"]
        statuses = {y.label: y.status for y in use.years}
        assert statuses == {"2019": "cycle", "2020": "unclear", "2021": "unclear", "2022": "unclear"}
        assert use.summary == "insufficient"

    def test_irregular_and_not_green_rules(self) -> None:
        years = [2019, 2020, 2021, 2022]
        data = wrapper(years, {y: 1 for y in years}, {(2019, 1): cycle(date(2019, 7, 20), date(2019, 10, 10))})
        use = season_use(parse_phenology(data))
        assert use["kharif"].summary == "irregular"  # 1 of 4
        assert use["summer"].summary == "not_green"


class TestClient:
    def _payload_for(self, band: str) -> bytes:
        saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
        return json.dumps(saved["bands"][band]["response"]).encode()

    def test_fetch_requests_every_band_reports_progress_and_caches(self) -> None:
        calls: list[str] = []
        progress: list[tuple[int, int]] = []

        def transport(url: str, _: float) -> bytes:
            calls.append(url)
            band = url.split("band=")[1].split("&")[0]
            return self._payload_for(band)

        client = PhenologyClient(transport=transport)
        live = client.fetch(30.85, 75.70, 2016, 2025, progress=lambda d, t: progress.append((d, t)))
        assert len(calls) == len(BANDS) and progress[-1] == (len(BANDS), len(BANDS))
        assert live.mode == "live" and season_use(live)["summer"].summary == "not_green"
        client.fetch(30.85, 75.70, 2016, 2025)
        assert len(calls) == len(BANDS)
        assert calls[0] == build_band_url(30.85, 75.70, "NumCycles", 2016, 2025)

    def test_server_errors_are_retried_then_reported(self) -> None:
        attempts = 0

        def flaky(url: str, _: float) -> bytes:
            nonlocal attempts
            attempts += 1
            raise HTTPError(url, 502, "Bad Gateway", None, None)  # type: ignore[arg-type]

        with pytest.raises(PhenologyNetworkError, match="502"):
            PhenologyClient(transport=flaky, retries=2).fetch(30.85, 75.70, 2016, 2025)
        assert attempts == 3

    def test_client_errors_and_offline(self) -> None:
        def not_found(url: str, _: float) -> bytes:
            raise HTTPError(url, 404, "Not found", None, None)  # type: ignore[arg-type]

        with pytest.raises(PhenologyNetworkError, match="404"):
            PhenologyClient(transport=not_found).fetch(30.85, 75.70, 2016, 2025)
        with pytest.raises(PhenologyNetworkError):
            PhenologyClient(transport=lambda *_: (_ for _ in ()).throw(URLError("offline")), retries=0).fetch(30.85, 75.70, 2016, 2025)
        with pytest.raises(PhenologyResponseError):
            PhenologyClient(transport=lambda *_: b"<html>", retries=0).fetch(30.85, 75.70, 2016, 2025)

    def test_targeted_query_limits(self) -> None:
        with pytest.raises(PhenologyError, match="10"):
            PhenologyClient(transport=lambda *_: b"{}").fetch(30.85, 75.70, 2010, 2025)
        assert "kmAboveBelow=0&kmLeftRight=0" in build_band_url(30.85, 75.70, "NumCycles", 2016, 2025)


@pytest.fixture(scope="module")
def engine() -> RotationEngine:
    return RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")


class TestRecommendationRole:
    def _profile(self, use, seasons: int = 3) -> FarmProfile:
        return FarmProfile(
            30.85, 75.70,
            SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False, well_drained=True, texture="medium"),
            ClimateContext(), 800.0, None,
            priority_weights={"water_suitability": 0.35, "climate_suitability": 0.2, "soil_related_potential": 0.25, "rotation_diversity": 0.2},
            number_of_seasons=seasons, climate_data=load_offline_demo_snapshot().data, observed_season_use=use,
        )

    def test_added_summer_season_is_flagged_with_its_water_demand(self, engine, record) -> None:
        plan = engine.assess_sequence(("maize", "wheat", "moong"), self._profile(season_use(record)))
        moong_check = [c for c in plan.checks if c.rule == "observed_seasonal_land_use"][-1]
        assert moong_check.status == "unknown" and "adds a cropping season" in moong_check.message
        comparison = plan.land_use_comparison
        assert comparison.added_seasons == ("summer",) and comparison.added_crops == ("moong",)
        assert comparison.added_crop_water_demand_mm == pytest.approx(plan.water_balance.crop_results[2].etc_total_mm)
        assert any("extra crop water demand" in t for t in plan.tradeoffs)
        assert plan.status == "conditionally_feasible"

    def test_continued_seasons_pass_and_never_fail(self, engine, record) -> None:
        plan = engine.assess_sequence(("maize", "wheat"), self._profile(season_use(record), seasons=2))
        checks = [c for c in plan.checks if c.rule == "observed_seasonal_land_use"]
        assert [c.status for c in checks] == ["pass", "pass"]
        assert plan.land_use_comparison.added_seasons == () and plan.land_use_comparison.added_crop_water_demand_mm == 0.0
        assert all(c.status != "fail" for c in checks)

    def test_scores_are_not_double_counted(self, engine, record) -> None:
        with_modis = engine.assess_sequence(("maize", "wheat", "moong"), self._profile(season_use(record)))
        without = engine.assess_sequence(("maize", "wheat", "moong"), self._profile(None))
        assert with_modis.composite_score == without.composite_score
        assert {k: v.score for k, v in with_modis.metrics.items()} == {k: v.score for k, v in without.metrics.items()}
        assert without.land_use_comparison is None
        assert not any(c.rule == "observed_seasonal_land_use" for c in without.checks)


def test_demo_workflow_loads_phenology_for_the_demo_farm() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    next(b for b in at.button if "Load demo & view plans" in b.label).click()
    at.run()
    assert not at.exception
    assert at.session_state["phenology_record"] is not None
    text = " ".join(e.value for e in at.markdown) + " ".join(e.value for e in at.warning)
    assert "This plan adds a cropping season" in text
