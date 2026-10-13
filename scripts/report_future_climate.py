"""Print the future-climate worked example for the demo farm from the installed extract.

    python scripts/report_future_climate.py

Uses the same engine, demo farm profile and priority weights as the app's demo
(balanced profile, 800 mm water budget, 3 seasons from kharif).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fieldshift.future_climate import (  # noqa: E402
    INDICATOR_LABELS, REFERENCE_EXPERIMENT, SHORT_LABELS, climate_changes, compare_plan, ensemble_median, load_extract,
)
from fieldshift.rotation_engine import ClimateContext, FarmProfile, RotationEngine, SoilInformation, normalize_weights  # noqa: E402


def main() -> None:
    extract = load_extract()
    engine = RotationEngine(ROOT / "data" / "crops.json", ROOT / "data" / "rotation_rules.json")
    weights = normalize_weights(json.loads((ROOT / "data" / "priority_weights.json").read_text())["profiles"]["balanced"])
    profile = FarmProfile(
        30.85, 75.70,
        SoilInformation(texture="medium", ph=7.4, organic_carbon_percent=0.55, electrical_conductivity_ds_m=0.35,
                        waterlogged=False, highly_deteriorated_alkaline=False, well_drained=True),
        ClimateContext(), 800.0, None, priority_weights=weights, number_of_seasons=3, start_season="kharif",
    )
    print(f"Grid cell {extract.grid_cell}; models {', '.join(extract.models)}; retrieved {extract.retrieved_utc}\n")
    for season in ("kharif", "rabi", "summer"):
        print(f"## {season}")
        for scenario, values in climate_changes(extract, season).items():
            parts = [f"{k}: {v.median:+.2f} ({v.low:+.2f} to {v.high:+.2f}; {v.agreement})" for k, v in values.items()]
            print(f"  {SHORT_LABELS[scenario]}: " + " | ".join(parts))
    plans = [("maize", "wheat", "moong"), ("cotton", "wheat", "moong"), ("pearl_millet", "chickpea", "moong"), ("maize", "potato", "moong")]
    print()
    for crop_ids in plans:
        comparison = compare_plan(engine, crop_ids, profile, extract)
        print(f"## Plan {' → '.join(crop_ids)}")
        for key, label in INDICATOR_LABELS.items():
            base = ensemble_median(comparison, REFERENCE_EXPERIMENT, key)
            row = [f"{label}: hist median {base:.3f}" if base is not None else f"{label}: hist n/a"]
            for scenario, changes in comparison.changes.items():
                spread = changes.get(key)
                if spread:
                    row.append(f"{SHORT_LABELS[scenario]} {spread.median:+.3f} ({spread.low:+.3f} to {spread.high:+.3f})")
            print("  " + " | ".join(row))
        for experiment in extract.experiments:
            print(f"  composite median {SHORT_LABELS[experiment]}: {ensemble_median(comparison, experiment, 'composite'):.3f}")
        if comparison.hard_failures:
            print("  hard failures:", dict(comparison.hard_failures))


if __name__ == "__main__":
    main()
