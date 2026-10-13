"""Tests for crop catalogue connectivity, rotation graph reachability, and calendar logic.

Verifies:
1. Every crop in data/crops.json is reachable in at least one valid multi-season rotation.
2. pearl_millet and rapeseed_mustard have active, source-backed graph connectivity.
3. Seasonal transitions strictly follow regional crop calendars (kharif -> rabi -> summer -> kharif).
4. Soil constraints and water requirements are properly evaluated for newly reachable crops.
5. Every relationship in data/rotation_rules.json has valid PAU provenance.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fieldshift.rotation_engine import (
    ClimateContext,
    FarmProfile,
    RotationEngine,
    SoilInformation,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CROPS_PATH = DATA_DIR / "crops.json"
RULES_PATH = DATA_DIR / "rotation_rules.json"


@pytest.fixture(scope="module")
def engine() -> RotationEngine:
    return RotationEngine(CROPS_PATH, RULES_PATH)


@pytest.fixture(scope="module")
def crops_catalog() -> list[dict]:
    data = json.loads(CROPS_PATH.read_text(encoding="utf-8"))
    return data["crops"]


@pytest.fixture(scope="module")
def rules_data() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _favourable_profile(
    start_season: str = "kharif",
    number_of_seasons: int = 3,
    water_budget: float = 800.0,
    **kwargs,
) -> FarmProfile:
    defaults = {
        "latitude": 30.9010,
        "longitude": 75.8573,
        "soil": SoilInformation(
            waterlogged=False,
            highly_deteriorated_alkaline=False,
            well_drained=True,
            texture="medium",
            source_description="Test field conditions",
        ),
        "climate": ClimateContext(
            source_url="https://power.example/request",
            date_range="2024-01-01 to 2024-12-31",
            available_parameters=("T2M", "PRECTOTCORR"),
        ),
        "total_crop_water_budget_mm": water_budget,
        "previous_crop_id": None,
        "blocked_crop_ids": frozenset(),
        "blocked_families": frozenset(),
        "priority_weights": {
            "water_suitability": 0.35,
            "climate_suitability": 0.20,
            "soil_related_potential": 0.25,
            "rotation_diversity": 0.20,
            "economic_potential": 0.0,
        },
        "number_of_seasons": number_of_seasons,
        "start_season": start_season,
    }
    defaults.update(kwargs)
    return FarmProfile(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Graph Reachability Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCropGraphReachability:
    """Verify that every crop in the catalogue can appear in feasible plans."""

    def test_every_crop_has_feasible_rotation_sequence(self, engine, crops_catalog) -> None:
        """Every crop in crops.json must form at least one feasible/conditionally feasible rotation."""
        for crop in crops_catalog:
            cid = crop["id"]
            # Find an incoming or outgoing relationship in rotation rules
            rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
            rel = next((r for r in rules["relationships"] if r["from"] == cid or r["to"] == cid), None)
            assert rel is not None, f"Crop {cid} has no graph relationships"

        # Verify specific key crops appear in generated plans under appropriate conditions:
        # 1. Bajra / pearl millet in standard kharif profile
        millet_res = engine.generate(_favourable_profile(start_season="kharif", number_of_seasons=3), max_plans=30)
        assert any("pearl_millet" in p.crop_ids for p in millet_res.plans)

        # 2. Rapeseed/mustard in standard kharif profile
        mustard_res = engine.generate(_favourable_profile(start_season="kharif", number_of_seasons=3), max_plans=30)
        assert any("rapeseed_mustard" in p.crop_ids for p in mustard_res.plans)

        # 3. Rice when water budget supports its documented requirement (>= 2500 mm)
        rice_res = engine.generate(_favourable_profile(start_season="kharif", number_of_seasons=3, water_budget=2600.0), max_plans=30)
        assert any("rice" in p.crop_ids and p.status != "infeasible" for p in rice_res.plans)

        # 4. Soybean when other kharif competitors are blocked
        soy_res = engine.generate(_favourable_profile(start_season="kharif", number_of_seasons=3, blocked_crop_ids=frozenset({"cotton", "maize", "pearl_millet"})), max_plans=30)
        assert any("soybean" in p.crop_ids and p.status != "infeasible" for p in soy_res.plans)

        # 5. Assess all 10 crops in valid 3-season sequences
        valid_triplets = [
            ("rice", "wheat", "moong"),
            ("maize", "wheat", "moong"),
            ("cotton", "wheat", "moong"),
            ("soybean", "wheat", "moong"),
            ("pearl_millet", "wheat", "moong"),
            ("rice", "chickpea", "moong"),
            ("rice", "potato", "moong"),
            ("maize", "rapeseed_mustard", "moong"),
        ]
        all_triplet_crops = {c for triplet in valid_triplets for c in triplet}
        assert all_triplet_crops == {c["id"] for c in crops_catalog}, "All 10 catalog crops must be represented across valid triplets"

        profile_high_water = _favourable_profile(water_budget=2600.0)
        for triplet in valid_triplets:
            plan = engine.assess_sequence(triplet, profile_high_water)
            assert plan.status in ("feasible_with_known_constraints", "conditionally_feasible"), \
                f"Sequence {triplet} failed: {[c.message for c in plan.checks if c.status == 'fail']}"

    def test_pearl_millet_is_reachable_and_feasible(self, engine) -> None:
        """Bajra (pearl millet) must appear in feasible 3-season rotations starting in Kharif."""
        res = engine.generate(_favourable_profile(start_season="kharif", number_of_seasons=3), max_plans=30)
        millet_plans = [p for p in res.plans if "pearl_millet" in p.crop_ids and p.status != "infeasible"]

        assert len(millet_plans) >= 1, "pearl_millet must appear in at least one feasible plan"

        # Check specific PAU-backed rotation paths
        millet_sequences = [p.crop_ids for p in millet_plans]
        assert any(seq == ("pearl_millet", "wheat", "moong") for seq in millet_sequences) or \
               any(seq == ("pearl_millet", "rapeseed_mustard", "moong") for seq in millet_sequences) or \
               any(seq == ("pearl_millet", "chickpea", "moong") for seq in millet_sequences)

    def test_rapeseed_mustard_is_reachable_and_feasible(self, engine) -> None:
        """Rapeseed/mustard must appear in feasible rotations starting in Kharif."""
        res = engine.generate(_favourable_profile(start_season="kharif", number_of_seasons=3), max_plans=30)
        mustard_plans = [p for p in res.plans if "rapeseed_mustard" in p.crop_ids and p.status != "infeasible"]

        assert len(mustard_plans) >= 1, "rapeseed_mustard must appear in at least one feasible plan"

        mustard_sequences = [p.crop_ids for p in mustard_plans]
        assert any("rapeseed_mustard" == seq[1] for seq in mustard_sequences), \
            f"Expected rapeseed_mustard at position 1 (Rabi), found: {mustard_sequences}"

    def test_no_isolated_crops_in_graph(self, crops_catalog, rules_data) -> None:
        """No crop should have 0 incoming and 0 outgoing edges."""
        relationships = rules_data["relationships"]
        from_nodes = {r["from"] for r in relationships}
        to_nodes = {r["to"] for r in relationships}

        for crop in crops_catalog:
            cid = crop["id"]
            has_edge = (cid in from_nodes) or (cid in to_nodes)
            assert has_edge, f"Crop '{cid}' is completely isolated in rotation_rules.json"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Season Alignment & Transition Validity
# ─────────────────────────────────────────────────────────────────────────────


class TestSeasonTransitions:
    """Verify that rotation relationships strictly follow crop calendar progression."""

    def test_transitions_respect_seasonal_progression(self, engine, rules_data) -> None:
        """Verify each relationship connects valid adjacent seasons in the cycle."""
        crops = engine.crops
        relationships = rules_data["relationships"]

        for rel in relationships:
            u, v = rel["from"], rel["to"]
            u_seasons = set(crops[u]["growing_seasons"])
            v_seasons = set(crops[v]["growing_seasons"])

            # Valid transitions: kharif -> rabi, rabi -> summer, summer -> kharif
            is_valid_transition = (
                ("kharif" in u_seasons and "rabi" in v_seasons) or
                ("rabi" in u_seasons and "summer" in v_seasons) or
                ("summer" in u_seasons and "kharif" in v_seasons)
            )
            assert is_valid_transition, f"Invalid transition: {u} ({u_seasons}) -> {v} ({v_seasons})"

    def test_summer_not_zaid_used_everywhere(self, rules_data, crops_catalog) -> None:
        """Ensure no 'zaid' remains in rule cycle or crop seasons."""
        assert "zaid" not in rules_data["season_cycle"]
        assert "summer" in rules_data["season_cycle"]

        for c in crops_catalog:
            for s in c["growing_seasons"]:
                assert s != "zaid", f"Crop {c['id']} uses 'zaid' instead of 'summer'"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Agronomic Constraints on Reached Crops
# ─────────────────────────────────────────────────────────────────────────────


class TestAgronomicConstraintsOnReachedCrops:
    """Verify hard constraints and soil checks on newly connected crops."""

    def test_pearl_millet_fails_on_waterlogged_soil(self, engine) -> None:
        """PAU cautions that bajra (pearl millet) is sensitive to waterlogging."""
        waterlogged_profile = _favourable_profile(
            start_season="kharif",
            number_of_seasons=3,
            soil=SoilInformation(waterlogged=True, highly_deteriorated_alkaline=False),
        )
        plan = engine.assess_sequence(("pearl_millet", "wheat", "moong"), waterlogged_profile)
        assert plan.status == "infeasible"
        assert any(c.status == "fail" and "waterlog" in c.message.lower() for c in plan.checks)

    def test_rapeseed_mustard_soil_score_boost_on_well_drained(self, engine) -> None:
        """Well-drained light/medium soil receives documented favourable soil credit."""
        profile = _favourable_profile(
            start_season="kharif",
            number_of_seasons=3,
            soil=SoilInformation(well_drained=True, texture="medium", waterlogged=False, highly_deteriorated_alkaline=False),
        )
        plan = engine.assess_sequence(("rice", "rapeseed_mustard", "moong"), profile)
        soil_metric = plan.metrics["soil_related_potential"]
        assert soil_metric.score is not None
        assert soil_metric.score == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Source Provenance Integrity
# ─────────────────────────────────────────────────────────────────────────────


class TestProvenanceIntegrity:
    """Verify all relationship source IDs resolve to valid HTTPS documentation."""

    def test_every_rule_has_resolvable_source_url(self, engine, rules_data) -> None:
        sources = engine.sources
        for rel in rules_data["relationships"]:
            source_ids = rel["source_ids"]
            assert source_ids, f"Relationship {rel['from']} -> {rel['to']} has no source_ids"
            for sid in source_ids:
                assert sid in sources, f"Source '{sid}' not found in catalog sources"
                url = sources[sid]["url"]
                assert url.startswith("https://"), f"Source '{sid}' URL must be HTTPS: {url}"
