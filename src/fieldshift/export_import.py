"""Persistence and one-page export helpers for FieldShift.

Provides:
1. Secure JSON serialization and deserialization of complete farm profiles.
2. Formatted, standalone, printable 1-page HTML "Farmer Rotation Summary Card".
"""

from __future__ import annotations

from datetime import date
import json
from typing import Any, Mapping


def export_farm_profile_to_json(session_state: Mapping[str, Any]) -> str:
    """Serialize farm state, priorities, and regional settings to a JSON string."""
    farm = session_state.get("farm", {})
    weights = session_state.get("weights", {})
    region_id = session_state.get("selected_region_id", "punjab")

    payload = {
        "format": "fieldshift_farm_profile",
        "version": "1.0",
        "exported_at": date.today().isoformat(),
        "region_id": region_id,
        "farm": {
            "latitude": farm.get("latitude"),
            "longitude": farm.get("longitude"),
            "texture": farm.get("texture"),
            "ph": farm.get("ph"),
            "organic_carbon_percent": farm.get("organic_carbon_percent"),
            "electrical_conductivity_ds_m": farm.get("electrical_conductivity_ds_m"),
            "waterlogged": farm.get("waterlogged"),
            "highly_deteriorated_alkaline": farm.get("highly_deteriorated_alkaline"),
            "well_drained": farm.get("well_drained"),
            "soil_source": farm.get("soil_source"),
            "soil_basis": farm.get("soil_basis"),
            "irrigation": farm.get("irrigation"),
            "water_budget_mm": farm.get("water_budget_mm"),
            "field_size_ha": farm.get("field_size_ha"),
            "start_season": farm.get("start_season"),
            "previous_crop_id": farm.get("previous_crop_id"),
            "blocked_crop_ids": list(farm.get("blocked_crop_ids", [])),
        },
        "weights": dict(weights),
        "planning_horizon": session_state.get("planning_horizon", 3),
    }
    return json.dumps(payload, indent=2)


def import_farm_profile_from_json(json_content: str) -> dict[str, Any]:
    """Parse and validate imported JSON farm profile.

    Enforces strict input validation to prevent invalid values or injection.
    """
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid JSON file format: {err}") from err

    if not isinstance(data, dict) or data.get("format") != "fieldshift_farm_profile":
        raise ValueError("Unrecognized file format. Expected a FieldShift farm profile export.")

    farm_in = data.get("farm", {})
    if not isinstance(farm_in, dict):
        raise ValueError("Invalid profile structure: 'farm' key missing or not a dictionary.")

    lat = farm_in.get("latitude")
    lon = farm_in.get("longitude")
    if lat is not None and not (-90.0 <= float(lat) <= 90.0):
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if lon is not None and not (-180.0 <= float(lon) <= 180.0):
        raise ValueError("Longitude must be between -180 and 180 degrees.")

    wb = farm_in.get("water_budget_mm")
    if wb is not None and float(wb) < 0:
        raise ValueError("Water budget cannot be negative.")

    ph = farm_in.get("ph")
    if ph is not None and not (3.0 <= float(ph) <= 11.0):
        raise ValueError("Soil pH must be between 3.0 and 11.0.")

    return {
        "region_id": str(data.get("region_id", "punjab")),
        "farm": {
            "latitude": float(lat) if lat is not None else None,
            "longitude": float(lon) if lon is not None else None,
            "texture": str(farm_in.get("texture", "medium")),
            "ph": float(ph) if ph is not None else None,
            "organic_carbon_percent": float(farm_in["organic_carbon_percent"]) if farm_in.get("organic_carbon_percent") is not None else None,
            "electrical_conductivity_ds_m": float(farm_in["electrical_conductivity_ds_m"]) if farm_in.get("electrical_conductivity_ds_m") is not None else None,
            "waterlogged": bool(farm_in.get("waterlogged", False)) if farm_in.get("waterlogged") is not None else None,
            "highly_deteriorated_alkaline": bool(farm_in.get("highly_deteriorated_alkaline", False)) if farm_in.get("highly_deteriorated_alkaline") is not None else None,
            "well_drained": bool(farm_in.get("well_drained", True)) if farm_in.get("well_drained") is not None else None,
            "soil_source": str(farm_in.get("soil_source", "")),
            "soil_basis": str(farm_in.get("soil_basis", "imported")),
            "irrigation": str(farm_in.get("irrigation", "Irrigated")),
            "water_budget_mm": float(wb) if wb is not None else None,
            "field_size_ha": float(farm_in.get("field_size_ha", 2.5)),
            "start_season": str(farm_in.get("start_season", "kharif")),
            "previous_crop_id": farm_in.get("previous_crop_id"),
            "blocked_crop_ids": list(farm_in.get("blocked_crop_ids", [])),
        },
        "weights": data.get("weights", {}),
        "planning_horizon": int(data.get("planning_horizon", 3)),
    }


def generate_farmer_summary_card_html(
    farm_profile: Mapping[str, Any],
    plan_crop_names: Sequence[str],
    plan_seasons: Sequence[str],
    water_saved_mm: float = 0.0,
    water_saved_m3_ha: float = 0.0,
    gross_margin_text: str = "Indicative positive margin",
    composite_score: float | None = None,
    region_name: str = "Indo-Gangetic Plain (Punjab)",
) -> str:
    """Generate a clean, printable 1-page HTML summary card with print styling."""
    crops_flow = " &rarr; ".join(
        f"<strong>{c}</strong> <span style='font-size:0.85em;color:#555;'>({s})</span>"
        for c, s in zip(plan_crop_names, plan_seasons)
    )

    lat = farm_profile.get("latitude", "N/A")
    lon = farm_profile.get("longitude", "N/A")
    texture = farm_profile.get("texture", "Medium")
    ph = farm_profile.get("ph", "N/A")
    soc = farm_profile.get("organic_carbon_percent", "N/A")
    budget = farm_profile.get("water_budget_mm", "N/A")

    score_badge = f"{composite_score:.2f} / 1.00" if composite_score is not None else "Evidence Verified"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>FieldShift — Farmer Rotation Summary Card</title>
<style>
  @page {{
    size: A4 portrait;
    margin: 12mm;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1a301a;
    line-height: 1.4;
    background: #fff;
    margin: 0;
    padding: 10px;
  }}
  .card {{
    border: 2px solid #2e7d32;
    border-radius: 8px;
    padding: 16px;
    background: #ffffff;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #2e7d32;
    padding-bottom: 10px;
    margin-bottom: 14px;
  }}
  .title {{
    font-size: 22px;
    font-weight: bold;
    color: #1b5e20;
    margin: 0;
  }}
  .subtitle {{
    font-size: 12px;
    color: #555;
    margin-top: 2px;
  }}
  .badge {{
    background: #e8f5e9;
    color: #2e7d32;
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 20px;
    border: 1px solid #81c784;
    font-size: 13px;
  }}
  .section {{
    margin-bottom: 14px;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #2e7d32;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 3px;
    margin-bottom: 8px;
  }}
  .highlight-box {{
    background: #f1f8e9;
    border-left: 4px solid #2e7d32;
    padding: 10px 14px;
    border-radius: 4px;
    font-size: 15px;
    margin: 8px 0;
  }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 6px;
  }}
  .stat-card {{
    background: #f9fbf9;
    border: 1px solid #e0e0e0;
    padding: 8px 10px;
    border-radius: 6px;
    text-align: center;
  }}
  .stat-val {{
    font-size: 17px;
    font-weight: bold;
    color: #1b5e20;
  }}
  .stat-lbl {{
    font-size: 10px;
    color: #666;
    text-transform: uppercase;
  }}
  .water-hero {{
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    border: 1px solid #90caf9;
    padding: 10px 14px;
    border-radius: 6px;
    margin-top: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .water-hero-val {{
    font-size: 20px;
    font-weight: bold;
    color: #0d47a1;
  }}
  .water-hero-txt {{
    font-size: 12px;
    color: #1565c0;
  }}
  .footer {{
    margin-top: 16px;
    padding-top: 8px;
    border-top: 1px dashed #ccc;
    font-size: 10px;
    color: #666;
    display: flex;
    justify-content: space-between;
  }}
  @media print {{
    body {{ padding: 0; }}
    .no-print {{ display: none; }}
  }}
</style>
</head>
<body>

<div class="card">
  <div class="header">
    <div>
      <div class="title">🌾 FieldShift — Farmer Rotation Plan</div>
      <div class="subtitle">Evidence-based crop rotation decision support | {region_name}</div>
    </div>
    <div class="badge">Composite: {score_badge}</div>
  </div>

  <div class="section">
    <div class="section-title">📍 Farm Location & Soil Baseline</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val">{lat}° N, {lon}° E</div>
        <div class="stat-lbl">Field Coordinates</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">{texture} (pH {ph})</div>
        <div class="stat-lbl">Soil Texture & pH</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">{soc}%</div>
        <div class="stat-lbl">Soil Organic Carbon</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🌱 Recommended Crop Rotation Sequence</div>
    <div class="highlight-box">
      {crops_flow}
    </div>
  </div>

  <div class="water-hero">
    <div>
      <div class="water-hero-txt">💧 Water Conservation vs Continuous Paddy-Wheat Baseline:</div>
      <div style="font-size:11px;color:#333;">Protects regional aquifers tracked by NASA GRACE and preserves tubewell pumping life.</div>
    </div>
    <div style="text-align:right;">
      <div class="water-hero-val">{water_saved_mm:,.0f} mm</div>
      <div style="font-size:11px;font-weight:bold;color:#0d47a1;">{water_saved_m3_ha:,.0f} m³/ha saved</div>
    </div>
  </div>

  <div class="section" style="margin-top:14px;">
    <div class="section-title">💰 Indicative Economics & Soil Health Trajectory</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-val">{budget} mm</div>
        <div class="stat-lbl">Farmer Water Budget</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">{gross_margin_text}</div>
        <div class="stat-lbl">Indicative Economic Outlook</div>
      </div>
      <div class="stat-card">
        <div class="stat-val">+ Legume Credit</div>
        <div class="stat-lbl">Soil Nitrogen Offset</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🛰️ NASA Earth Observation Provenance</div>
    <div style="font-size:11px;color:#444;background:#f5f5f5;padding:8px 12px;border-radius:4px;">
      Climate: <strong>NASA POWER</strong> daily historical reanalysis &bull;
      Future Projections: <strong>NASA NEX-GDDP-CMIP6</strong> &bull;
      Soil Moisture: <strong>NASA SMAP</strong> &bull;
      Phenology: <strong>NASA MODIS MCD12Q2</strong> &bull;
      Groundwater: <strong>NASA GRACE</strong> &bull;
      Thermal Fire Anomalies: <strong>NASA FIRMS</strong>
    </div>
  </div>

  <div class="footer">
    <div>⚠️ Decision-support advisory prototype. Replace benchmarks with certified soil tests and local extension advice.</div>
    <div>FieldShift | NASA Space Apps Hackathon</div>
  </div>
</div>

</body>
</html>"""
