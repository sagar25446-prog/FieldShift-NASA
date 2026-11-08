"""Tests for satellite context, water calculator, and rank stability."""

import pytest

from src.fieldshift.satellite_context import (
    calculate_water_budget_from_farm_inputs,
    GRACE_PUNJAB_CONTEXT,
    FIRMS_PUNJAB_CONTEXT,
    SMAP_PUNJAB_CONTEXT,
    GPM_GLOBAL_CONTEXT,
    MODIS_NDVI_CONTEXT,
    WaterBudgetCalculation,
)
from src.fieldshift.sensitivity import (
    evaluate_rank_stability,
    generate_plain_language_explanation,
    RankStabilityReport,
)
from pathlib import Path
from src.fieldshift.rotation_engine import RotationEngine, FarmProfile, SoilInformation

ROOT = Path(__file__).resolve().parents[1]
ENGINE = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")


def test_water_budget_calculator():
    # 7.5 HP motor, 6 hours per irrigation, 5 irrigations on 2.5 acres
    calc = calculate_water_budget_from_farm_inputs(
        tubewell_hours_per_irrigation=6.0,
        tubewell_irrigations_count=5,
        tubewell_motor_hp=7.5,
        canal_hours_per_week=2.0,
        canal_weeks_per_season=10,
        farm_area_acres=2.5,
    )
    assert isinstance(calc, WaterBudgetCalculation)
    assert calc.tubewell_hours == 30.0
    assert calc.tubewell_water_mm > 0
    assert calc.canal_water_mm > 0
    assert calc.total_water_budget_mm == calc.tubewell_water_mm + calc.canal_water_mm
    assert "Calculated from 7.5 HP pump" in calc.formula_explanation


def test_satellite_contexts():
    assert GRACE_PUNJAB_CONTEXT.rate_of_depletion_cm_per_year == -4.0
    assert "NASA GRACE" in GRACE_PUNJAB_CONTEXT.satellite_mission
    assert "Over-exploited" in GRACE_PUNJAB_CONTEXT.key_finding

    assert "MODIS" in FIRMS_PUNJAB_CONTEXT.sensor
    assert "Happy Seeder" in FIRMS_PUNJAB_CONTEXT.crop_residue_solution

    # SMAP
    assert "SMAP" in SMAP_PUNJAB_CONTEXT.satellite_mission
    assert SMAP_PUNJAB_CONTEXT.surface_moisture_m3_m3 > 0.0
    assert SMAP_PUNJAB_CONTEXT.rootzone_moisture_m3_m3 > 0.0

    # GPM
    assert "GPM" in GPM_GLOBAL_CONTEXT.satellite_constellation
    assert GPM_GLOBAL_CONTEXT.spatial_resolution_deg == 0.1

    # MODIS NDVI
    assert "MOD13Q1" in MODIS_NDVI_CONTEXT.sensor
    assert MODIS_NDVI_CONTEXT.peak_ndvi_rabi > MODIS_NDVI_CONTEXT.bare_soil_ndvi



def test_rank_stability_analysis():
    engine = ENGINE
    profile = FarmProfile(
        latitude=30.9010,
        longitude=75.8573,
        soil=SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False),
        climate=None,
        total_crop_water_budget_mm=600.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 0.4, "rotation_diversity": 0.6},
        start_season="kharif",
        number_of_seasons=3,
    )
    res = engine.generate(profile)
    assert len(res.plans) > 0

    weights = {"water_suitability": 0.4, "rotation_diversity": 0.6}
    report = evaluate_rank_stability(res.plans, weights, delta_fraction=0.20)
    assert isinstance(report, RankStabilityReport)
    assert 0.0 <= report.stability_percentage <= 100.0
    assert report.total_perturbations_tested > 0
    assert report.baseline_top_plan == res.plans[0].crop_names


def test_plain_language_explanation():
    engine = ENGINE
    profile = FarmProfile(
        latitude=30.9010,
        longitude=75.8573,
        soil=SoilInformation(waterlogged=False, highly_deteriorated_alkaline=False),
        climate=None,
        total_crop_water_budget_mm=600.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 0.5, "rotation_diversity": 0.5},
        start_season="kharif",
        number_of_seasons=3,
    )
    res = engine.generate(profile)
    top_plan = res.plans[0]
    explanation = generate_plain_language_explanation(top_plan)
    assert isinstance(explanation, str)
    assert "**Why recommended:**" in explanation



def test_nasa_earth_observation_suite_and_harmonization():
    from src.fieldshift.satellite_context import (
        ECOSTRESS_PUNJAB_CONTEXT,
        SRTM_PUNJAB_CONTEXT,
        LANDSAT_FIELD_CONTEXT,
        GEDI_BIOMASS_CONTEXT,
        DATA_HARMONIZATION_GRID,
    )
    # ECOSTRESS
    assert "ECOSTRESS" in ECOSTRESS_PUNJAB_CONTEXT.sensor
    assert ECOSTRESS_PUNJAB_CONTEXT.spatial_resolution_m == 70
    assert ECOSTRESS_PUNJAB_CONTEXT.evaporative_stress_index > 0.0

    # SRTM
    assert "SRTM" in SRTM_PUNJAB_CONTEXT.dataset
    assert SRTM_PUNJAB_CONTEXT.spatial_resolution_m == 30
    assert SRTM_PUNJAB_CONTEXT.slope_percent > 0.0

    # Landsat
    assert "Landsat" in LANDSAT_FIELD_CONTEXT.sensor
    assert LANDSAT_FIELD_CONTEXT.spatial_resolution_m == 30
    assert LANDSAT_FIELD_CONTEXT.bare_soil_index_summer > 0.0

    # GEDI
    assert "GEDI" in GEDI_BIOMASS_CONTEXT.sensor
    assert GEDI_BIOMASS_CONTEXT.aboveground_biomass_density_mg_ha > 0.0

    # Data Harmonization Grid
    assert len(DATA_HARMONIZATION_GRID) == 10
    datasets = [entry.dataset_name for entry in DATA_HARMONIZATION_GRID]
    assert "NASA POWER Daily" in datasets
    assert "NASA ECOSTRESS" in datasets
    assert "NASA SMAP L3/L4" in datasets
    assert "NASA GPM IMERG V07" in datasets
    assert "NASA/USGS Landsat 8/9" in datasets
    assert "NASA SRTM DEM" in datasets
    assert "NASA GRACE / GRACE-FO" in datasets


def test_strategy_comparison_5_point_narratives():
    from src.fieldshift.strategy_comparison import compare_existing_rotation
    engine = ENGINE
    profile = FarmProfile(
        latitude=30.85,
        longitude=75.70,
        soil=SoilInformation(),
        climate=None,
        total_crop_water_budget_mm=600.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 0.5, "rotation_diversity": 0.5},
    )
    alternatives = engine.generate(profile).plans
    strategies = compare_existing_rotation(engine, profile, ("rice", "wheat", "moong"), alternatives)
    assert len(strategies) >= 3
    for s in strategies:
        assert s.why_suggested != ""
        assert len(s.evidence_support) >= 3
        assert len(s.benefits_offered) >= 2
        assert len(s.information_gaps) >= 2
        assert len(s.risks_and_expert_review) >= 2
        assert s.bare_field_analysis != ""
        assert s.vulnerability_analysis != ""
        assert s.pest_break_analysis != ""
