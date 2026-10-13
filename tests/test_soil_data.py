"""SoilGrids adapter, source precedence, units, depth handling and engine use.

Fixtures are unmodified SoilGrids v2.0 REST responses saved on 2026-10-13
(see each file's ``_fixture_metadata``); no test calls the live service.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation
from fieldshift.soil_data import (
    ESTIMATE_LABEL,
    SOILGRIDS_DEPTHS,
    SOILGRIDS_PROPERTIES,
    ManualSoilEntry,
    SoilGridsClient,
    SoilGridsEstimate,
    SoilGridsLayerValue,
    SoilGridsNetworkError,
    SoilGridsRateLimitError,
    SoilGridsResponseError,
    SoilGridsValidationError,
    aggregate_topsoil,
    assess_texture,
    fao_texture_group,
    parse_soilgrids_response,
    resolve_soil_values,
)
from fieldshift.soil_nutrient_model import build_soil_state_report, estimate_soc_change


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"
RURAL = FIXTURES / "soilgrids_rural_ludhiana_district.json"
CITY = FIXTURES / "soilgrids_ludhiana_city_centre.json"


def load(path: Path) -> SoilGridsEstimate:
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    meta = wrapper["_fixture_metadata"]
    return parse_soilgrids_response(wrapper["response"], meta["latitude"], meta["longitude"], meta["source_url"], meta["retrieved_at_utc"])


@pytest.fixture(scope="module")
def rural() -> SoilGridsEstimate:
    return load(RURAL)


@pytest.fixture(scope="module")
def city() -> SoilGridsEstimate:
    return load(CITY)


def synthetic(values: dict[str, list[tuple[float | None, float | None, float | None]]]) -> SoilGridsEstimate:
    """Build an estimate from (mean, q05, q95) per standard depth, in conventional units."""
    units = {"clay": "%", "sand": "%", "silt": "%", "soc": "g/kg", "phh2o": "-", "nitrogen": "g/kg"}
    ranges = {"0-5cm": (0, 5), "5-15cm": (5, 15), "15-30cm": (15, 30)}
    layers: dict[str, dict[str, SoilGridsLayerValue]] = {}
    for name, rows in values.items():
        for depth, (mean, q05, q95) in zip(SOILGRIDS_DEPTHS, rows):
            top, bottom = ranges[depth]
            layers.setdefault(name, {})[depth] = SoilGridsLayerValue(name, depth, top, bottom, units[name], "", 10.0, mean, q05, mean, q95, None)
    return SoilGridsEstimate(30.0, 75.0, 75.0, 30.0, "https://example.test/soilgrids", "2026-10-13T00:00:00Z", None, layers)


# ───────────────────────────── parsing and units ─────────────────────────────

class TestParsingUnitsAndProvenance:
    def test_units_are_converted_with_d_factor(self, rural: SoilGridsEstimate) -> None:
        clay = rural.value("clay", "0-5cm")
        assert clay.unit == "%" and clay.mapped_unit == "g/kg" and clay.d_factor == 10
        assert clay.mean == pytest.approx(22.8) and clay.q05 == pytest.approx(1.9) and clay.q95 == pytest.approx(77.0)
        assert rural.value("soc", "0-5cm").mean == pytest.approx(11.0)  # 110 dg/kg → 11.0 g/kg
        assert rural.value("soc", "0-5cm").unit == "g/kg"
        assert rural.value("nitrogen", "0-5cm").mean == pytest.approx(0.98)  # d_factor 100: cg/kg → g/kg
        assert rural.value("phh2o", "0-5cm").mean == pytest.approx(7.9)  # pH×10 → pH

    def test_uncertainty_ratio_matches_isric_definition(self, rural: SoilGridsEstimate) -> None:
        clay = rural.value("clay", "0-5cm")
        # ISRIC stores (Q0.95 − Q0.05)/Q0.50 ×10.
        assert clay.uncertainty_ratio == pytest.approx(4.8)
        assert clay.uncertainty_ratio == pytest.approx((clay.q95 - clay.q05) / clay.q50, abs=0.05)

    def test_every_requested_property_and_depth_is_retained(self, rural: SoilGridsEstimate) -> None:
        for name in SOILGRIDS_PROPERTIES:
            for depth in SOILGRIDS_DEPTHS:
                assert rural.value(name, depth) is not None
        assert [(rural.value("sand", d).top_cm, rural.value("sand", d).bottom_cm) for d in SOILGRIDS_DEPTHS] == [(0, 5), (5, 15), (15, 30)]
        assert rural.missing == ()

    def test_provenance_is_retained(self, rural: SoilGridsEstimate) -> None:
        assert rural.source_url.startswith("https://rest.isric.org/soilgrids/v2.0/properties/query?")
        assert rural.retrieved_at_utc == "2026-10-13T12:25:31Z"
        assert (rural.latitude, rural.longitude) == (30.85, 75.70)
        assert (rural.returned_latitude, rural.returned_longitude) == (30.85, 75.70)
        assert "250 m" in rural.resolution
        assert "CC BY 4.0" in rural.licence
        assert rural.label == ESTIMATE_LABEL == "Estimated from SoilGrids"

    def test_unexpected_unit_is_rejected_not_converted(self) -> None:
        wrapper = json.loads(RURAL.read_text(encoding="utf-8"))
        wrapper["response"]["properties"]["layers"][0]["unit_measure"]["target_units"] = "g/100g"
        with pytest.raises(SoilGridsResponseError, match="unexpected unit"):
            parse_soilgrids_response(wrapper["response"], 30.85, 75.70, "u", "t")

    def test_malformed_responses_are_rejected(self) -> None:
        with pytest.raises(SoilGridsResponseError):
            parse_soilgrids_response([], 0, 0, "u", "t")
        with pytest.raises(SoilGridsResponseError, match="layers"):
            parse_soilgrids_response({"type": "Feature"}, 0, 0, "u", "t")
        bad_value = {"properties": {"layers": [{"name": "clay", "unit_measure": {"d_factor": 10, "target_units": "%"}, "depths": [
            {"label": "0-5cm", "range": {"top_depth": 0, "bottom_depth": 5}, "values": {"mean": "high"}}]}]}}
        with pytest.raises(SoilGridsResponseError, match="non-numeric"):
            parse_soilgrids_response(bad_value, 0, 0, "u", "t")


# ───────────────────────────── missing values ─────────────────────────────

class TestMissingValues:
    def test_all_null_location_is_an_estimate_with_no_values(self, city: SoilGridsEstimate) -> None:
        assert city.has_any_value is False
        assert len(city.missing) == len(SOILGRIDS_PROPERTIES) * len(SOILGRIDS_DEPTHS)
        assert city.value("clay", "0-5cm").mean is None

    def test_null_location_leaves_soil_unknown(self, city: SoilGridsEstimate) -> None:
        resolved = resolve_soil_values(ManualSoilEntry(), city)
        assert resolved.estimate_available is False
        for key in ("texture", "organic_carbon", "ph", "total_nitrogen"):
            assert resolved[key].value is None and resolved[key].source_type == "unknown"
        assert any("no prediction" in note for note in resolved.notes)

    def test_partial_depth_is_never_presented_as_0_30_cm(self) -> None:
        estimate = synthetic({"soc": [(10.0, 5.0, 20.0), (9.0, 4.0, 18.0), (None, None, None)]})
        assert aggregate_topsoil(estimate, "soc") is None
        assert resolve_soil_values(ManualSoilEntry(), estimate)["organic_carbon"].value is None

    def test_missing_quantiles_keep_mean_but_drop_range(self) -> None:
        estimate = synthetic({"soc": [(10.0, None, 20.0), (9.0, 4.0, 18.0), (6.0, 3.0, 12.0)]})
        aggregate = aggregate_topsoil(estimate, "soc")
        assert aggregate is not None and aggregate.envelope_low is None and aggregate.envelope_high is None

    def test_missing_sand_or_clay_gives_unknown_texture(self) -> None:
        estimate = synthetic({"clay": [(20.0, 18.5, 22.0)] * 3})
        assessment = assess_texture(estimate)
        assert assessment.fieldshift_texture is None and "missing" in assessment.explanation


# ───────────────────────────── depth intervals ─────────────────────────────

class TestDepthIntervals:
    def test_thickness_weighted_0_30_cm_mean(self, rural: SoilGridsEstimate) -> None:
        clay = aggregate_topsoil(rural, "clay")
        assert clay.depth_label == "0-30cm"
        assert clay.mean == pytest.approx((22.8 * 5 + 24.3 * 10 + 28.5 * 15) / 30)
        assert clay.envelope_low == pytest.approx(1.8) and clay.envelope_high == pytest.approx(86.3)
        assert clay.component_depths == ("0-5cm", "5-15cm", "15-30cm")

    def test_estimate_used_by_model_carries_its_depth(self, rural: SoilGridsEstimate) -> None:
        soc = resolve_soil_values(ManualSoilEntry(), rural)["organic_carbon"]
        assert soc.depth == "0-30cm"
        report = estimate_soc_change(["rice", "wheat"], soc.value, soc_depth_m=0.30, soc_range_percent=(soc.low, soc.high))
        assert report.soc_depth_m == 0.30 and "30 cm depth" in report.method_description

    def test_manual_value_keeps_its_own_stated_depth(self, rural: SoilGridsEstimate) -> None:
        soc = resolve_soil_values(ManualSoilEntry(source_type="laboratory", organic_carbon_percent=0.45, sample_depth="0–15 cm"), rural)["organic_carbon"]
        assert soc.depth == "0–15 cm" and soc.source_type == "laboratory"


# ───────────────────────────── texture rule ─────────────────────────────

class TestTextureAppropriateness:
    @pytest.mark.parametrize("sand,clay,group", [(80, 10, "coarse"), (40, 25, "medium"), (70, 20, "medium"), (20, 45, "fine"), (66, 17.9, "coarse")])
    def test_fao_groups(self, sand: float, clay: float, group: str) -> None:
        assert fao_texture_group(sand, clay) == group

    def test_wide_uncertainty_blocks_texture_use(self, rural: SoilGridsEstimate) -> None:
        assessment = assess_texture(rural)
        assert assessment.group_at_mean == "medium"
        assert assessment.robust_group is None and assessment.fieldshift_texture is None
        resolved = resolve_soil_values(ManualSoilEntry(), rural)
        assert resolved["texture"].value is None
        assert "not used for crop soil checks" in resolved["texture"].note

    def test_narrow_uncertainty_allows_texture_estimate(self) -> None:
        estimate = synthetic({"sand": [(40.0, 35.0, 45.0)] * 3, "clay": [(25.0, 21.0, 29.0)] * 3})
        resolved = resolve_soil_values(ManualSoilEntry(), estimate)
        assert resolved["texture"].value == "medium" and resolved["texture"].source_type == "soilgrids_estimate"


# ───────────────────────────── precedence and overrides ─────────────────────────────

class TestSourcePrecedenceAndOverrides:
    def test_estimate_fills_only_empty_fields_and_is_labelled(self, rural: SoilGridsEstimate) -> None:
        soc = resolve_soil_values(ManualSoilEntry(), rural)["organic_carbon"]
        assert soc.source_type == "soilgrids_estimate" and soc.source_label == "Estimated from SoilGrids"
        assert soc.unit == "%" and soc.value == pytest.approx(7.6167 / 10, abs=1e-3)  # g/kg → %
        assert soc.low == pytest.approx(0.13) and soc.high == pytest.approx(2.90)

    def test_laboratory_value_overrides_estimate_and_stays_identifiable(self, rural: SoilGridsEstimate) -> None:
        entry = ManualSoilEntry(source_type="laboratory", organic_carbon_percent=0.45, ph=8.2, texture="light", reference="SHC report 2025")
        resolved = resolve_soil_values(entry, rural)
        assert resolved["organic_carbon"].value == 0.45
        assert resolved["organic_carbon"].source_label == "Laboratory soil test (farmer-entered)"
        assert "0.76%" in resolved["organic_carbon"].not_used_alternative
        assert resolved["organic_carbon"].low is None  # no estimate range mixed into a lab value
        assert resolved["ph"].value == 8.2 and resolved["ph"].source_type == "laboratory"
        assert resolved["texture"].value == "light" and resolved["texture"].source_type == "laboratory"

    def test_illustrative_and_observed_values_are_distinct_sources(self, rural: SoilGridsEstimate) -> None:
        illustrative = resolve_soil_values(ManualSoilEntry(source_type="illustrative", organic_carbon_percent=0.55), rural)["organic_carbon"]
        observed = resolve_soil_values(ManualSoilEntry(source_type="farmer_observation", texture="heavy"), rural)["texture"]
        assert "not measured" in illustrative.source_label
        assert observed.source_label == "Farmer observation"

    def test_ph_and_nitrogen_are_context_only(self, rural: SoilGridsEstimate) -> None:
        resolved = resolve_soil_values(ManualSoilEntry(), rural)
        assert resolved["ph"].value == pytest.approx((7.9 * 5 + 8.0 * 10 + 7.9 * 15) / 30)
        assert resolved["ph"].used_in_model is False and resolved["total_nitrogen"].used_in_model is False
        assert "available N" in resolved["total_nitrogen"].note

    def test_ec_is_never_estimated(self, rural: SoilGridsEstimate) -> None:
        assert resolve_soil_values(ManualSoilEntry(), rural)["electrical_conductivity"].value is None

    def test_invalid_manual_source_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            ManualSoilEntry(source_type="soilgrids_estimate")

    def test_ui_soil_information_keeps_sources(self, rural: SoilGridsEstimate) -> None:
        from fieldshift.ui import soil_information_from

        farm = {"ph": None, "electrical_conductivity_ds_m": None, "waterlogged": None, "highly_deteriorated_alkaline": None, "well_drained": True, "soil_source": ""}
        soil = soil_information_from(farm, resolve_soil_values(ManualSoilEntry(), rural))
        assert soil.organic_carbon_source == "soilgrids_estimate" and soil.organic_carbon_depth == "0-30cm"
        assert soil.organic_carbon_range_percent == (pytest.approx(0.13), pytest.approx(2.90))
        assert soil.texture is None and soil.texture_source is None
        # Hard-constraint inputs come only from the farmer.
        assert soil.waterlogged is None and soil.highly_deteriorated_alkaline is None


# ───────────────────────────── failed requests ─────────────────────────────

class TestFailedRequests:
    def test_network_failure(self) -> None:
        def offline(_: str, __: float) -> bytes:
            raise URLError("offline")

        with pytest.raises(SoilGridsNetworkError, match="paused or busy"):
            SoilGridsClient(transport=offline).fetch(30.85, 75.70)

    def test_timeout(self) -> None:
        def slow(_: str, __: float) -> bytes:
            raise TimeoutError()

        with pytest.raises(SoilGridsNetworkError):
            SoilGridsClient(transport=slow).fetch(30.85, 75.70)

    def test_http_errors(self) -> None:
        def make(code: int):
            def transport(url: str, __: float) -> bytes:
                raise HTTPError(url, code, "error", None, None)  # type: ignore[arg-type]
            return transport

        with pytest.raises(SoilGridsRateLimitError):
            SoilGridsClient(transport=make(429)).fetch(30.85, 75.70)
        with pytest.raises(SoilGridsNetworkError, match="HTTP 503"):
            SoilGridsClient(transport=make(503)).fetch(30.85, 75.70)

    def test_invalid_json_and_coordinates(self) -> None:
        with pytest.raises(SoilGridsResponseError, match="JSON"):
            SoilGridsClient(transport=lambda _u, _t: b"<html>maintenance</html>").fetch(30.85, 75.70)
        with pytest.raises(SoilGridsValidationError):
            SoilGridsClient(transport=lambda _u, _t: b"{}").fetch(95, 75)

    def test_fair_use_guard_and_cache(self) -> None:
        payload = json.dumps(json.loads(RURAL.read_text(encoding="utf-8"))["response"]).encode()
        calls: list[str] = []
        clock = iter([0.0, 1.0, 20.0]).__next__

        def transport(url: str, __: float) -> bytes:
            calls.append(url)
            return payload

        client = SoilGridsClient(transport=transport, clock=clock)
        first = client.fetch(30.85, 75.70)
        assert client.fetch(30.85, 75.70) is first  # cached: no clock tick, no call
        with pytest.raises(SoilGridsRateLimitError, match="5 requests per minute"):
            client.fetch(31.0, 75.0)  # 1 s after the previous live call
        client.fetch(31.0, 75.0)  # 20 s later
        assert len(calls) == 2
        assert "property=soc" in calls[0] and "depth=15-30cm" in calls[0] and "value=Q0.95" in calls[0]

    def test_failed_soil_retrieval_does_not_block_the_planner(self) -> None:
        engine = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")
        resolved = resolve_soil_values(ManualSoilEntry(), None)
        from fieldshift.ui import soil_information_from

        farm = {"ph": None, "electrical_conductivity_ds_m": None, "waterlogged": None, "highly_deteriorated_alkaline": None, "well_drained": None, "soil_source": ""}
        profile = FarmProfile(30.9, 75.86, soil_information_from(farm, resolved), ClimateContext(), 800.0, None, priority_weights={"water_suitability": 1.0})
        result = engine.generate(profile)
        assert result.plans, "Planner must still generate plans with unknown soil"


# ───────────────────────────── engine and soil model ─────────────────────────────

class TestEngineUse:
    def _profile(self, soil: SoilInformation) -> FarmProfile:
        return FarmProfile(30.9, 75.86, soil, ClimateContext(), 800.0, None, priority_weights={"soil_related_potential": 1.0}, start_season="rabi", number_of_seasons=1)

    def test_estimated_texture_is_disclosed_in_soft_checks_only(self) -> None:
        engine = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")
        soil = SoilInformation(well_drained=True, waterlogged=False, highly_deteriorated_alkaline=False, texture="medium", texture_source="soilgrids_estimate")
        plan = engine.assess_sequence(("rapeseed_mustard",), self._profile(soil))
        context = [c for c in plan.checks if c.rule == "documented_rapeseed_mustard_soil_context"][0]
        assert context.status == "pass" and "estimated from SoilGrids" in context.message
        assert "SoilGrids" in plan.metrics["soil_related_potential"].method
        wheat = engine.assess_sequence(("wheat",), self._profile(soil))
        hard = [c for c in wheat.checks if c.rule == "documented_wheat_soil_constraint"][0]
        assert "SoilGrids" not in hard.message

    def test_measured_texture_has_no_estimate_note(self) -> None:
        engine = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")
        soil = SoilInformation(well_drained=True, texture="medium", texture_source="laboratory")
        plan = engine.assess_sequence(("rapeseed_mustard",), self._profile(soil))
        assert all("SoilGrids" not in c.message for c in plan.checks)
        assert plan.metrics["soil_related_potential"].warning is None

    def test_soc_range_that_changes_direction_reports_uncertain(self) -> None:
        # Moong residue C input is 126–252 kg/ha/yr; at 0–30 cm the model's loss is
        # 105 × SOC% kg/ha/yr, so it reports increase below 1.2% and decrease above 2.4%.
        crops = ["moong"]
        low = estimate_soc_change(crops, 0.5, soc_depth_m=0.30)
        high = estimate_soc_change(crops, 3.0, soc_depth_m=0.30)
        assert (low.estimated_annual_change_direction, high.estimated_annual_change_direction) == ("likely_increase", "likely_decrease")
        ranged = estimate_soc_change(crops, 1.0, soc_depth_m=0.30, soc_range_percent=(0.5, 3.0))
        assert ranged.estimated_annual_change_direction == "uncertain"
        assert len(ranged.directions_across_range) == 3

    def test_soc_report_names_estimate_source(self) -> None:
        report = build_soil_state_report(["rice"], ["Rice"], ["kharif"], {"rice": False}, initial_soc_percent=0.76,
                                         soc_source_type="soilgrids_estimate", soc_source_label="Estimated from SoilGrids", soc_depth_m=0.30)
        assert any("SoilGrids 250 m estimate" in item for item in report.missing_inputs)
        assert "Estimated from SoilGrids" in report.soc_estimate.method_description

    def test_soc_model_is_reproducible_without_range(self) -> None:
        # Existing behaviour is unchanged when no range or depth is supplied.
        a = estimate_soc_change(["rice", "wheat"], 0.55)
        b = estimate_soc_change(["rice", "wheat"], 0.55, soc_depth_m=0.20)
        assert a.estimated_annual_change_direction == b.estimated_annual_change_direction
        assert a.soc_depth_m == 0.20
