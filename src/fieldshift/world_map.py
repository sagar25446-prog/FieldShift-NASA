"""Offline globe and flat-map selector with bundled D3 geographic projections."""
from functools import lru_cache
import json
from pathlib import Path

import streamlit as st

from .regions import REGIONS

ASSETS = Path(__file__).resolve().parents[2] / "assets"


@lru_cache(maxsize=1)
def _appearance():
    # UMD libraries share a private export object; nothing is fetched by the browser.
    vendor = "const d3 = (() => { const exports = {}; const module = {exports}; const require = () => exports;\n"
    for name in ("d3-array", "d3-geo"):
        vendor += (ASSETS / "vendor" / f"{name}.min.js").read_text("utf-8") + "\n"
    vendor += "return exports; })();\n"
    return {
        "html": (ASSETS / "earth-explorer.html").read_text("utf-8"),
        "css": (ASSETS / "earth-explorer.css").read_text("utf-8"),
        "js": vendor + (ASSETS / "earth-explorer.js").read_text("utf-8"),
    }


@lru_cache(maxsize=1)
def _land():
    return json.loads((ASSETS / "world-land.geojson").read_text("utf-8"))


def world_picker(selected=None):
    picker = st.components.v2.component("fieldshift_world_picker", **_appearance())
    names = {"punjab": "Punjab", "semi_arid_tropics": "Deccan", "us_corn_belt": "Iowa", "mediterranean": "Andalusia"}
    pilots = [{"id": r.id, "label": r.name, "short": names.get(r.id, r.country),
               "lat": r.latitude, "lon": r.longitude} for r in REGIONS.values()]
    return picker(data={"land": _land(), "pilots": pilots, "selected": selected},
                  key="farm_atlas", on_chosen_change=lambda: None, on_inspected_change=lambda: None)
