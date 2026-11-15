"""Economics must remain unavailable without verified crop-level inputs."""

import json
from pathlib import Path

import pytest

from src.fieldshift.economics import (
    compare_vs_rice_wheat_baseline,
    compute_crop_economics,
    compute_rotation_economics,
)


CROPS_PATH = Path(__file__).resolve().parents[1] / "data" / "crops.json"


@pytest.fixture
def catalog():
    with CROPS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {crop["id"]: crop for crop in data["crops"]}


def test_unverified_catalogue_has_no_fabricated_returns(catalog):
    assert all("indicative_economics" not in crop for crop in catalog.values())
    result = compute_crop_economics(catalog["rice"], "kharif")
    assert result.benchmark_yield_q_ha is None
    assert result.benchmark_cost_inr_ha is None
    assert result.indicative_gross_margin_inr_ha is None


def test_missing_values_propagate_through_rotation(catalog):
    crops = [catalog[name] for name in ("maize", "wheat", "moong")]
    result = compute_rotation_economics(crops, ("kharif", "rabi", "summer"), 750.0)
    assert result.total_cost_inr_ha is None
    assert result.total_revenue_inr_ha is None
    assert result.total_margin_inr_ha is None
    assert result.water_productivity_inr_per_m3 is None


def test_comparison_requires_explicit_baseline_and_avoids_groundwater_claim(catalog):
    crops = [catalog["maize"], catalog["wheat"]]
    with pytest.raises(ValueError, match="documented baseline"):
        compare_vs_rice_wheat_baseline(crops, ("kharif", "rabi"), 750.0)
    # The following numbers are test inputs, not regional measurements.
    result = compare_vs_rice_wheat_baseline(
        crops, ("kharif", "rabi"), 750.0, baseline_irrigation_mm=1000.0
    )
    assert result.water_saved_mm == 250.0
    assert result.water_saved_m3_per_ha == 2500.0
    assert result.margin_diff_inr_ha is None
    assert "not observed groundwater saved" in result.headline_summary
