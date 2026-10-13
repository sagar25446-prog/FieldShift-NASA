"""Future-climate module: scenario metadata, temporal alignment, units, missing
variables and reproducible calculations.

Most tests build a small synthetic extract in a temporary folder so the expected
changes are known exactly (e.g. future = historical + 2 K). A final group runs
on the installed NEX-GDDP-CMIP6 extract for the demo farm when it is present.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from fieldshift.future_climate import (
    DEMO_EXTRACT_DIR,
    EXPECTED_UNITS,
    REFERENCE_EXPERIMENT,
    ProjectionDataError,
    Spread,
    climate_changes,
    compare_plan,
    convert_units,
    ensemble_median,
    load_extract,
)
from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation

ROOT = Path(__file__).resolve().parents[1]
UNITS = dict(EXPECTED_UNITS)


def _raw(years: tuple[int, int], warming_k: float = 0.0, rain_factor: float = 1.0, seed: int = 0) -> pd.DataFrame:
    """Deterministic, seasonal synthetic daily record in NEX source units."""
    dates = pd.date_range(f"{years[0]}-01-01", f"{years[1]}-12-31", freq="D")
    doy = dates.dayofyear.to_numpy()
    seasonal = 10.0 * np.sin(2 * np.pi * (doy - 100) / 365.0)
    tas = 297.0 + seasonal + warming_k + 0.1 * seed  # deterministic: no year-dependent noise
    monsoon = (doy > 180) & (doy < 270)
    return pd.DataFrame({
        "tasmax": tas + 6.0, "tasmin": tas - 6.0,
        "pr": np.where(monsoon, 6.0, 0.5) / 86400.0 * rain_factor,
    }, index=pd.Index(dates, name="date"))


def make_extract(folder: Path, models=("M1", "M2", "M3"), hist=(1995, 1998), future=(2041, 2044), warming=(1.0, 2.0, 3.0), drop=None, units=None, cell=None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    meta = {
        "requested_latitude": 30.85, "requested_longitude": 75.70,
        "experiments": {"historical": list(hist), "ssp245": list(future), "ssp585": list(future)},
        "citation": "test", "documentation": "https://example.test", "technical_note": "https://example.test/note",
        "retrieval_finished_utc": "2026-10-13T00:00:00Z", "models": {},
    }
    for index, model in enumerate(models):
        model_meta = {"licence": "CC-BY 4.0", "calendar": "proleptic_gregorian", "experiments": {}}
        for experiment, years in meta["experiments"].items():
            k = 0.0 if experiment == "historical" else warming[index] * (1.0 if experiment == "ssp245" else 1.5)
            raw = _raw(tuple(years), warming_k=k, rain_factor=1.1 if experiment != "historical" else 1.0, seed=index)
            if drop and (model, experiment) == drop[0]:
                raw = raw.drop(columns=[drop[1]])
            with gzip.open(folder / f"{model}_{experiment}_{years[0]}-{years[1]}.csv.gz", "wt", encoding="utf-8", newline="") as handle:
                raw.to_csv(handle)
            model_meta["experiments"][experiment] = {
                "variant": "r1i1p1f1", "years": list(years), "dataset_version": "2.0",
                "units": units or UNITS, "grid_cell_centre": list(cell or (30.875, 75.625)),
            }
        meta["models"][model] = model_meta
    (folder / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    return folder


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory) -> Path:
    return make_extract(tmp_path_factory.mktemp("extract"))


# ───────────────────────────── units ─────────────────────────────

class TestUnits:
    def test_conversions(self) -> None:
        raw = pd.DataFrame({"tasmax": [310.15], "tasmin": [290.15], "pr": [1 / 86400]})
        frame = convert_units(raw, UNITS)
        assert frame["T2M_MAX"].iloc[0] == pytest.approx(37.0) and frame["T2M_MIN"].iloc[0] == pytest.approx(17.0)
        assert frame["T2M"].iloc[0] == pytest.approx(27.0)  # (Tmax + Tmin) / 2
        assert frame["PRECTOTCORR"].iloc[0] == pytest.approx(1.0)  # kg m-2 s-1 → mm/day
        assert "ALLSKY_SFC_SW_DWN" not in frame  # radiation is estimated by FAO-56 Eq. 50, not invented here

    def test_inconsistent_temperatures_are_rejected(self) -> None:
        with pytest.raises(ProjectionDataError, match="below minimum"):
            convert_units(pd.DataFrame({"tasmax": [280.0], "tasmin": [290.0], "pr": [0.0]}), UNITS)

    def test_unexpected_unit_is_refused(self) -> None:
        raw = pd.DataFrame({k: [1.0] for k in UNITS})
        with pytest.raises(ProjectionDataError, match="refusing"):
            convert_units(raw, {**UNITS, "pr": "mm/day"})

    def test_missing_variable_is_refused(self) -> None:
        raw = pd.DataFrame({k: [1.0] for k in UNITS if k != "tasmin"})
        with pytest.raises(ProjectionDataError, match="tasmin"):
            convert_units(raw, UNITS)


# ───────────────────────────── metadata and alignment ─────────────────────────────

class TestMetadataAndAlignment:
    def test_loads_scenarios_models_and_provenance(self, synthetic: Path) -> None:
        extract = load_extract(synthetic)
        assert extract.models == ("M1", "M2", "M3")
        assert dict(extract.experiments) == {"historical": (1995, 1998), "ssp245": (2041, 2044), "ssp585": (2041, 2044)}
        record = extract.records[("M1", "ssp585")]
        assert record.licence == "CC-BY 4.0" and record.variant == "r1i1p1f1" and record.dataset_version == "2.0"
        assert extract.grid_cell == (30.875, 75.625)
        assert extract.covers(30.85, 75.70) and not extract.covers(31.2, 75.70)

    def test_declared_and_actual_periods_must_agree(self, tmp_path: Path) -> None:
        folder = make_extract(tmp_path / "x")
        meta = json.loads((folder / "metadata.json").read_text())
        meta["models"]["M2"]["experiments"]["ssp245"]["years"] = [2041, 2045]
        (folder / "metadata.json").write_text(json.dumps(meta))
        with pytest.raises(ProjectionDataError, match="covers"):
            load_extract(folder)

    def test_future_scenarios_must_share_one_period(self, tmp_path: Path) -> None:
        folder = make_extract(tmp_path / "x")
        meta = json.loads((folder / "metadata.json").read_text())
        meta["experiments"]["ssp585"] = [2081, 2084]
        (folder / "metadata.json").write_text(json.dumps(meta))
        with pytest.raises(ProjectionDataError, match="same period"):
            load_extract(folder)

    def test_data_span_must_match_declared_years(self, tmp_path: Path) -> None:
        folder = make_extract(tmp_path / "x")
        path = folder / "M1_ssp245_2041-2044.csv.gz"
        frame = pd.read_csv(path, parse_dates=["date"], index_col="date")
        frame.loc[:"2043-12-31"].to_csv(path)
        with pytest.raises(ProjectionDataError, match="span"):
            load_extract(folder)

    def test_records_from_different_grid_cells_are_rejected(self, tmp_path: Path) -> None:
        folder = make_extract(tmp_path / "x")
        meta = json.loads((folder / "metadata.json").read_text())
        meta["models"]["M3"]["experiments"]["ssp585"]["grid_cell_centre"] = [31.125, 75.625]
        (folder / "metadata.json").write_text(json.dumps(meta))
        with pytest.raises(ProjectionDataError, match="grid cells"):
            load_extract(folder)

    def test_missing_variable_in_one_file_is_rejected(self, tmp_path: Path) -> None:
        folder = make_extract(tmp_path / "x", drop=(("M2", "ssp585"), "pr"))
        with pytest.raises(ProjectionDataError, match="pr"):
            load_extract(folder)

    def test_missing_extract_and_missing_reference(self, tmp_path: Path) -> None:
        with pytest.raises(ProjectionDataError, match="No projection extract"):
            load_extract(tmp_path / "nothing")
        folder = make_extract(tmp_path / "x")
        meta = json.loads((folder / "metadata.json").read_text())
        del meta["experiments"]["historical"]
        (folder / "metadata.json").write_text(json.dumps(meta))
        with pytest.raises(ProjectionDataError, match="historical"):
            load_extract(folder)


# ───────────────────────────── calculations ─────────────────────────────

class TestReproducibleCalculations:
    def test_known_warming_is_recovered_per_model(self, synthetic: Path) -> None:
        changes = climate_changes(load_extract(synthetic), "kharif")
        t245 = changes["ssp245"]["mean_temperature_c"]
        assert t245.per_model == pytest.approx({"M1": 1.0, "M2": 2.0, "M3": 3.0}, abs=1e-9)
        assert (t245.median, t245.low, t245.high) == pytest.approx((2.0, 1.0, 3.0), abs=1e-6)
        assert changes["ssp585"]["mean_temperature_c"].median == pytest.approx(3.0, abs=1e-6)
        assert changes["ssp245"]["precipitation_pct"].median == pytest.approx(10.0, abs=1e-6)
        assert "all 3 models show an increase" == t245.agreement

    def test_spread_agreement_wording(self) -> None:
        assert Spread.of({"a": 1.0, "b": -1.0, "c": 2.0}).agreement.startswith("models disagree")

    def test_plan_comparison_is_deterministic_and_aligned(self, synthetic: Path) -> None:
        extract = load_extract(synthetic)
        engine = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")
        profile = FarmProfile(30.85, 75.70, SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False), ClimateContext(), 800.0, None,
                              priority_weights={"water_suitability": 0.5, "climate_suitability": 0.5})
        first = compare_plan(engine, ("maize", "wheat", "moong"), profile, extract)
        second = compare_plan(engine, ("maize", "wheat", "moong"), profile, extract)
        assert first.absolute == second.absolute
        # Each change is the same model's future minus its own historical value.
        etc = first.changes["ssp585"]["total_etc_mm"]
        for model in extract.models:
            expected = first.absolute["ssp585"][model]["total_etc_mm"] - first.absolute[REFERENCE_EXPERIMENT][model]["total_etc_mm"]
            assert etc.per_model[model] == pytest.approx(expected)
        assert etc.median > 0  # warmer climate → higher crop water demand
        assert ensemble_median(first, "historical", "water_suitability") is not None
        assert profile.climate_data is None  # the farmer's profile is not modified


# ───────────────────────────── installed extract ─────────────────────────────

installed = pytest.mark.skipif(not (DEMO_EXTRACT_DIR / "metadata.json").exists(), reason="NEX-GDDP-CMIP6 demo extract not installed")


@installed
def test_installed_extract_is_complete_and_consistent() -> None:
    extract = load_extract()
    assert len(extract.models) == 5
    assert dict(extract.experiments) == {"historical": (1995, 2014), "ssp245": (2041, 2060), "ssp585": (2041, 2060)}
    assert extract.covers(30.85, 75.70)
    for record in extract.records.values():
        assert record.licence == "CC-BY 4.0"
        assert record.frame[["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"]].notna().all().all()
        expected_days = 365 * 20 if record.calendar == "365_day" else (pd.Timestamp(f"{record.years[1]}-12-31") - pd.Timestamp(f"{record.years[0]}-01-01")).days + 1
        assert len(record.frame) == expected_days


def test_radiation_estimate_only_when_the_column_is_absent() -> None:
    from fieldshift.fao56 import compute_et0_series

    dates = pd.date_range("2050-06-01", periods=10, freq="D")
    temps = pd.DataFrame({"T2M_MAX": 40.0, "T2M_MIN": 28.0, "T2M": 34.0, "PRECTOTCORR": 0.0}, index=dates)
    estimated = compute_et0_series(temps, 30.85)
    assert estimated.valid_days == 10 and estimated.total_et0_mm > 0
    assert any("Eq. 50" in w for w in estimated.warnings)
    gaps = temps.assign(ALLSKY_SFC_SW_DWN=float("nan"))  # a POWER-style record with missing radiation
    assert compute_et0_series(gaps, 30.85).valid_days == 0  # gaps are not filled


def test_future_climate_page_renders_and_stays_separate_from_stress_tests(tmp_path: Path, monkeypatch) -> None:
    from streamlit.testing.v1 import AppTest

    import fieldshift.future_climate as fc

    monkeypatch.setattr(fc, "DEMO_EXTRACT_DIR", make_extract(tmp_path / "ui"))
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    next(b for b in at.button if "Load demo & view plans" in b.label).click()
    at.run()
    at.session_state["page"] = "Future climate (NASA CMIP6)"
    at.run()
    assert not at.exception
    text = " ".join(e.value for e in (*at.markdown, *at.warning, *at.info))
    assert "not weather forecasts" in text and "Hypothetical stress tests" in text
    assert at.dataframe, "climate-change and plan tables are shown"
    at.session_state["page"] = "Hypothetical stress tests"
    at.run()
    assert not at.exception
    assert any("not NASA climate projections" in i.value for i in at.info)
