"""Tests for profile persistence export/import and summary card generation."""

import json
import pytest

from src.fieldshift.export_import import (
    export_farm_profile_to_json,
    generate_farmer_summary_card_html,
    import_farm_profile_from_json,
)


def test_export_and_import_cycle():
    state = {
        "selected_region_id": "punjab",
        "farm": {
            "latitude": 30.9010,
            "longitude": 75.8573,
            "texture": "medium",
            "ph": 7.4,
            "organic_carbon_percent": 0.55,
            "electrical_conductivity_ds_m": 0.35,
            "waterlogged": False,
            "highly_deteriorated_alkaline": False,
            "well_drained": True,
            "soil_source": "Test Lab",
            "soil_basis": "laboratory",
            "irrigation": "Irrigated",
            "water_budget_mm": 800.0,
            "field_size_ha": 2.5,
            "start_season": "kharif",
            "previous_crop_id": None,
            "blocked_crop_ids": ["cotton"],
        },
        "weights": {"water_suitability": 0.4, "rotation_diversity": 0.6},
        "planning_horizon": 3,
    }

    json_str = export_farm_profile_to_json(state)
    assert "fieldshift_farm_profile" in json_str

    imported = import_farm_profile_from_json(json_str)
    assert imported["region_id"] == "punjab"
    assert imported["farm"]["latitude"] == pytest.approx(30.9010)
    assert imported["farm"]["water_budget_mm"] == pytest.approx(800.0)
    assert imported["farm"]["blocked_crop_ids"] == ["cotton"]
    assert imported["weights"]["water_suitability"] == 0.4


def test_import_validation_rejects_malformed_input():
    # Invalid JSON
    with pytest.raises(ValueError, match="Invalid JSON"):
        import_farm_profile_from_json("not valid json")

    # Wrong format header
    with pytest.raises(ValueError, match="Unrecognized file format"):
        import_farm_profile_from_json(json.dumps({"format": "other"}))

    # Invalid latitude
    bad_lat = {
        "format": "fieldshift_farm_profile",
        "farm": {"latitude": 120.0, "longitude": 75.0},
    }
    with pytest.raises(ValueError, match="Latitude must be between"):
        import_farm_profile_from_json(json.dumps(bad_lat))

    # Negative water budget
    bad_budget = {
        "format": "fieldshift_farm_profile",
        "farm": {"water_budget_mm": -50.0},
    }
    with pytest.raises(ValueError, match="Water budget cannot be negative"):
        import_farm_profile_from_json(json.dumps(bad_budget))


def test_generate_farmer_summary_card_html():
    html = generate_farmer_summary_card_html(
        farm_profile={"latitude": 30.9, "longitude": 75.8, "texture": "medium", "ph": 7.4, "organic_carbon_percent": 0.55, "water_budget_mm": 800.0},
        plan_crop_names=["Maize", "Wheat", "Summer Moong"],
        plan_seasons=["kharif", "rabi", "summer"],
        water_saved_mm=1000.0,
        water_saved_m3_ha=10000.0,
        gross_margin_text="₹1,24,000 / ha",
        composite_score=0.84,
        region_name="Punjab, India",
    )
    assert "<!DOCTYPE html>" in html
    assert "FieldShift" in html
    assert "Maize" in html
    assert "Wheat" in html
    assert "1,000 mm" in html
    assert "10,000 m³/ha" in html
    assert "NASA POWER" in html
