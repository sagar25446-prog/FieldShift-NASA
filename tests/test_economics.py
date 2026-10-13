"""Tests for indicative economics module."""

import json
from pathlib import Path
import pytest

from src.fieldshift.economics import (
    compute_crop_economics,
    compute_rotation_economics,
    compare_vs_rice_wheat_baseline,
    CropEconomics,
    RotationEconomics,
    WaterSavingsComparison,
)


CROPS_PATH = Path(__file__).resolve().parents[1] / "data" / "crops.json"


@pytest.fixture
def catalog():
    with open(CROPS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"]: c for c in data["crops"]}


def test_crop_economics_computation(catalog):
    rice = catalog["rice"]
    ce = compute_crop_economics(rice, "kharif")
    assert isinstance(ce, CropEconomics)
    assert ce.crop_id == "rice"
    assert ce.msp_inr_per_q == 2300.0
    assert ce.benchmark_yield_q_ha == 65.0
    assert ce.indicative_gross_revenue_inr_ha == 2300.0 * 65.0
    assert ce.benchmark_cost_inr_ha == 50000.0
    assert ce.indicative_gross_margin_inr_ha == (2300.0 * 65.0) - 50000.0
    assert ce.msp_procurement_assured is True


def test_rotation_economics_aggregation(catalog):
    crops = [catalog["maize"], catalog["wheat"], catalog["moong"]]
    seasons = ["kharif", "rabi", "summer"]
    econ = compute_rotation_economics(crops, seasons, net_irrigation_mm=750.0)

    assert isinstance(econ, RotationEconomics)
    assert len(econ.crop_economics) == 3
    assert econ.total_cost_inr_ha == 38000.0 + 40000.0 + 24000.0
    assert econ.total_revenue_inr_ha is not None
    assert econ.total_margin_inr_ha is not None
    assert econ.total_margin_inr_ha > 0
    # 750 mm on 1 ha = 7,500 m3
    assert econ.water_productivity_inr_per_m3 is not None
    assert econ.water_productivity_inr_per_m3 == pytest.approx(econ.total_margin_inr_ha / 7500.0, rel=1e-3)


def test_compare_vs_rice_wheat_baseline(catalog):
    crops = [catalog["maize"], catalog["wheat"], catalog["moong"]]
    seasons = ["kharif", "rabi", "summer"]
    comp = compare_vs_rice_wheat_baseline(crops, seasons, candidate_irrigation_mm=750.0)

    assert isinstance(comp, WaterSavingsComparison)
    assert comp.baseline_net_irrigation_mm == 1750.0
    assert comp.candidate_net_irrigation_mm == 750.0
    assert comp.water_saved_mm == 1000.0
    assert comp.water_saved_pct == pytest.approx((1000.0 / 1750.0) * 100.0, rel=1e-3)
    assert comp.water_saved_m3_per_ha == 10000.0
    assert "Conserves 1000 mm of net irrigation" in comp.headline_summary
    assert "litres" in comp.headline_summary
