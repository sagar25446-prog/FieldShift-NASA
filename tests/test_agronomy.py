"""Tests for agronomy calendar windows, pilot protocol, and historical hindcast."""

from __future__ import annotations

from fieldshift.agronomy import (
    CROP_CALENDARS,
    get_crop_calendar,
)
from fieldshift.export_import import generate_farmer_summary_card_html


def test_crop_calendars_exist_and_populated():
    assert len(CROP_CALENDARS) >= 10
    assert "wheat" in CROP_CALENDARS
    assert "rice" in CROP_CALENDARS
    assert "corn" in CROP_CALENDARS

    wheat_entry = get_crop_calendar("wheat")
    assert wheat_entry is not None
    assert "November" in wheat_entry.sowing_window
    assert "April" in wheat_entry.harvest_window
    assert wheat_entry.typical_duration_days > 100
    assert "PAU" in wheat_entry.source_reference


def test_crop_calendar_multiregion():
    corn = get_crop_calendar("corn")
    assert corn is not None
    assert corn.region_id == "us_corn_belt"

    durum = get_crop_calendar("durum_wheat")
    assert durum is not None
    assert durum.region_id == "mediterranean"

    sorghum = get_crop_calendar("sorghum")
    assert sorghum is not None
    assert sorghum.region_id == "semi_arid"


def test_summary_card_renders_calendar_and_disclosures():
    farm = {
        "latitude": 30.85,
        "longitude": 75.70,
        "texture": "Medium",
        "ph": 7.4,
        "organic_carbon_percent": 0.48,
        "water_budget_mm": 600.0,
    }
    html = generate_farmer_summary_card_html(
        farm_profile=farm,
        plan_crop_names=["Maize", "Wheat", "Moong"],
        plan_seasons=["kharif", "rabi", "summer"],
        water_saved_mm=985.0,
        water_saved_m3_ha=9850.0,
        composite_score=0.88,
    )
    assert "Local review required" in html
    assert "Catalogue sowing and harvest windows" in html
    assert "Wheat" in html
    assert "NASA GRACE" not in html
