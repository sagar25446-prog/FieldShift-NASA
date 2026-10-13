"""Tests for global multi-region framework."""

import json
from pathlib import Path
import pytest

from src.fieldshift.regions import (
    REGIONS,
    detect_region_from_coordinates,
    get_region,
    list_regions,
)
from src.fieldshift.rotation_engine import (
    FarmProfile,
    RotationEngine,
    SoilInformation,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def test_list_and_get_regions():
    regions = list_regions()
    assert len(regions) >= 4
    ids = {r.id for r in regions}
    assert {"punjab", "us_corn_belt", "mediterranean", "semi_arid_tropics"} <= ids

    reg = get_region("us_corn_belt")
    assert reg.name == "US Corn Belt (Iowa & Upper Midwest, USA)"
    assert reg.currency_symbol == "$"

    fallback = get_region("unknown_region")
    assert fallback.id == "punjab"


def test_detect_region_from_coordinates():
    # Iowa coordinates
    iowa_reg = detect_region_from_coordinates(42.0, -93.5)
    assert iowa_reg.id == "us_corn_belt"

    # Spain coordinates
    spain_reg = detect_region_from_coordinates(37.4, -6.0)
    assert spain_reg.id == "mediterranean"

    # Punjab coordinates
    punjab_reg = detect_region_from_coordinates(30.9, 75.8)
    assert punjab_reg.id == "punjab"

    # Maharashtra coordinates
    mh_reg = detect_region_from_coordinates(19.1, 74.7)
    assert mh_reg.id == "semi_arid_tropics"


def test_us_corn_belt_engine_generates_valid_plans():
    reg = get_region("us_corn_belt")
    catalog_path = DATA_DIR / reg.catalog_filename
    rules_path = DATA_DIR / reg.rules_filename
    assert catalog_path.exists()
    assert rules_path.exists()

    engine = RotationEngine(catalog_path, rules_path)
    profile = FarmProfile(
        latitude=reg.latitude,
        longitude=reg.longitude,
        soil=SoilInformation(texture="medium", waterlogged=False, well_drained=True),
        climate=None,
        total_crop_water_budget_mm=700.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 1.0, "rotation_diversity": 1.0},
        number_of_seasons=3,
        start_season="spring",
    )
    res = engine.generate(profile)
    assert res.plans, "US Corn Belt must generate feasible rotation plans"
    first = res.plans[0]
    assert first.crop_ids
    assert first.status in ("feasible_with_known_constraints", "conditionally_feasible")


def test_mediterranean_engine_generates_valid_plans():
    reg = get_region("mediterranean")
    catalog_path = DATA_DIR / reg.catalog_filename
    rules_path = DATA_DIR / reg.rules_filename

    engine = RotationEngine(catalog_path, rules_path)
    profile = FarmProfile(
        latitude=reg.latitude,
        longitude=reg.longitude,
        soil=SoilInformation(texture="medium", waterlogged=False, well_drained=True),
        climate=None,
        total_crop_water_budget_mm=500.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 1.0, "rotation_diversity": 1.0},
        number_of_seasons=2,
        start_season="autumn_winter",
    )
    res = engine.generate(profile)
    assert res.plans, "Mediterranean must generate feasible rotation plans"


def test_semi_arid_engine_generates_valid_plans():
    reg = get_region("semi_arid_tropics")
    catalog_path = DATA_DIR / reg.catalog_filename
    rules_path = DATA_DIR / reg.rules_filename

    engine = RotationEngine(catalog_path, rules_path)
    profile = FarmProfile(
        latitude=reg.latitude,
        longitude=reg.longitude,
        soil=SoilInformation(texture="fine", waterlogged=False, well_drained=False),
        climate=None,
        total_crop_water_budget_mm=600.0,
        previous_crop_id=None,
        priority_weights={"water_suitability": 1.0, "rotation_diversity": 1.0},
        number_of_seasons=2,
        start_season="kharif",
    )
    res = engine.generate(profile)
    assert res.plans, "Semi-Arid Tropics must generate feasible rotation plans"
