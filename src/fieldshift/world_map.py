"""Offline equirectangular farm picker. Natural Earth provides the land outlines."""

from functools import lru_cache
import json
from pathlib import Path

import streamlit as st

from .regions import REGIONS


@lru_cache(maxsize=1)
def _land_path() -> str:
    features = json.loads(
        (Path(__file__).resolve().parents[2] / "assets/world-land.geojson").read_text("utf-8")
    )["features"]
    rings = [ring for feature in features for ring in feature["geometry"]["coordinates"]]
    return "".join(
        "M" + "L".join(f"{(lon + 180) * 2:.2f},{(90 - lat) * 2:.2f}" for lon, lat in ring) + "Z"
        for ring in rings
    )


_appearance = dict(
    html="""
    <section>
      <nav aria-label="Map zoom"><button class="zoomIn" aria-label="Zoom in">+</button>
        <button class="zoomOut" aria-label="Zoom out">−</button></nav>
      <svg viewBox="0 0 720 360" role="group" aria-label="World location picker" tabindex="0"
           aria-description="Click to select a point, or move the cursor with the arrow keys.">
        <defs><pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
          <path d="M60 0H0V60" fill="none" stroke="#bad4cd" stroke-width="0.65"/>
        </pattern></defs>
        <rect width="720" height="360" fill="#e4f0ef"/>
        <path class="land" fill="#b0c9a8" stroke="#64866e" stroke-width=".55" fill-rule="evenodd"/>
        <rect width="720" height="360" fill="url(#grid)" pointer-events="none"/>
        <g class="pilots"></g><g class="lock" pointer-events="none" visibility="hidden">
          <g class="reticle"><path d="M-17 -8v-9h9M8 -17h9v9M17 8v9H8M-8 17h-9V8"
            fill="none" stroke="#733813" stroke-width="2.5"/></g>
          <circle r="3" fill="#f5c564" stroke="#58321d"/>
        </g>
      </svg>
      <footer><output aria-live="polite">Select a point on the map</output>
        <button type="button" disabled>Use this location</button></footer>
      <label class="pilot-list">Choose a pilot by name
        <select aria-label="Choose a pilot by name"></select>
      </label>
    </section>
    """,
    css="""
    section { position:relative; border:1px solid #b8cfc2; border-radius:18px; overflow:hidden; }
    nav { position:absolute; top:8px; right:8px; display:flex; gap:2px; }
    nav button { width:34px; height:34px; padding:0; background:#fff; color:#1c4538; font-size:1.3rem; }
    .name { font:600 10px system-ui,sans-serif; fill:#174a37; stroke:#edf6ec; stroke-width:3;
      paint-order:stroke; pointer-events:none; }
    svg:focus-visible { outline:3px solid #89510c; outline-offset:-3px; }
    .pilot-list { display:none; }
    @media (max-width:680px) {
      .pilot-list { display:grid; gap:.3rem; padding:.7rem 1rem; background:#f4f7ef;
        color:#234438; font-size:.85rem; }
      .pilot-list select { font:inherit; color:#173e31; background:#fff; padding:.55rem;
        border:1px solid #a3baab; border-radius:7px; }
    }
    svg { display:block; width:100%; cursor:crosshair; }
    [data-pilot] { cursor:pointer; outline:none; }
    [data-pilot]:focus-visible .dot { stroke:#ffbc40; stroke-width:4px; }
    footer { background:#153e34; color:white; padding:.75rem 1rem; display:flex;
      flex-wrap:wrap; gap:.7rem; align-items:center; justify-content:space-between; }
    output { font:500 .92rem var(--st-font, sans-serif); }
    button { background:#edf6c8; color:#183f30; font:inherit; border:0;
      border-radius:8px; padding:.6rem .9rem; cursor:pointer; }
    button:disabled { opacity:.6; cursor:default; }
    .scan { transform-box:fill-box; transform-origin:center;
      animation:acquire .65s cubic-bezier(.16,.8,.32,1) both; }
    @keyframes acquire { from { transform:rotate(-35deg) scale(2.1); opacity:.15; }
      to { transform:rotate(0) scale(1); opacity:1; } }
    @media(prefers-reduced-motion: reduce) { .scan { animation:none; } }
    """,
    js="""
    export default function({parentElement, data, setTriggerValue}) {
      const svg = parentElement.querySelector("svg");
      const pilots = svg.querySelector(".pilots");
      const lock = svg.querySelector(".lock");
      const output = parentElement.querySelector("output");
      const button = parentElement.querySelector("footer button");
      const list = parentElement.querySelector("select");
      list.replaceChildren(new Option("Select a regional planner", ""));
      for (const pilot of data.pilots) list.add(new Option(pilot.label, pilot.id));
      list.onchange = () => {
        const pilot = data.pilots.find(p => p.id === list.value);
        if (pilot) { select(pilot.lat, pilot.lon, pilot, true); changeZoom(1); }
      };
      let cursor = {lat:0, lon:0};
      let zoom = 720 / svg.viewBox.baseVal.width;
      function changeZoom(factor) {
        zoom = Math.max(1, Math.min(16, zoom * factor));
        const width = 720/zoom, height = 360/zoom;
        const left = Math.max(0, Math.min(720-width, (cursor.lon+180)*2-width/2));
        const top = Math.max(0, Math.min(360-height, (90-cursor.lat)*2-height/2));
        svg.setAttribute("viewBox", [left, top, width, height].join(" "));
      }
      parentElement.querySelector(".zoomIn").onclick = () => changeZoom(2);
      parentElement.querySelector(".zoomOut").onclick = () => changeZoom(.5);
      svg.querySelector(".land").setAttribute("d", data.land);
      const ns = "http://www.w3.org/2000/svg";
      function element(tag, attributes) {
        const node = document.createElementNS(ns, tag);
        for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
        return node;
      }
      function select(lat, lon, pilot, inspect=false) {
        const point = {lat, lon, pilot:pilot?.id ?? null};
        list.value = point.pilot ?? "";
        cursor = point;
        svg.fieldPoint = point;
        lock.setAttribute("transform", "translate(" + (lon+180)*2 + " " + (90-lat)*2 + ")");
        lock.setAttribute("visibility", "visible");
        const reticle = lock.querySelector(".reticle");
        reticle.classList.remove("scan");
        reticle.getBoundingClientRect();
        reticle.classList.add("scan");
        output.textContent = (pilot ? pilot.short + " pilot" : "Climate location") + " · " +
          Math.abs(lat).toFixed(4) + "°" + (lat < 0 ? "S" : "N") + "  " +
          Math.abs(lon).toFixed(4) + "°" + (lon < 0 ? "W" : "E");
        button.disabled = false;
        button.textContent = pilot ? "Open farm profile" : "Explore this location";
        button.onclick = () => setTriggerValue("chosen", point);
        if (inspect) setTriggerValue("inspected", point);
      }
      pilots.replaceChildren();
      for (const pilot of data.pilots) {
        const group = element("g", {"data-pilot":pilot.id, tabindex:0, role:"button",
          "aria-label":pilot.label, transform:"translate("+(pilot.lon+180)*2+" "+(90-pilot.lat)*2+")"});
        const title = element("title", {});
        title.textContent = pilot.label;
        group.append(title, element("circle", {r:10, fill:"transparent"}),
          element("circle", {class:"dot", r:5, fill:"#155f53", stroke:"#fff", "stroke-width":2}));
        const label = element("text", {class:"name", x:8, y:3});
        label.textContent = pilot.short;
        group.append(label);
        group.onclick = event => { event.stopPropagation(); select(pilot.lat, pilot.lon, pilot, true); };
        group.onkeydown = event => { if (event.key === "Enter" || event.key === " ") {
          event.preventDefault(); select(pilot.lat, pilot.lon, pilot, true);
        }};
        pilots.append(group);
      }
      svg.onkeydown = event => {
        if (event.target === svg && event.key === "Enter") {
          event.preventDefault(); select(cursor.lat, cursor.lon, null, true); return;
        }
        if (event.target !== svg || !["ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].includes(event.key)) return;
        event.preventDefault();
        const step = 1 / zoom;
        const north = event.key === "ArrowUp" ? step : event.key === "ArrowDown" ? -step : 0;
        const east = event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0;
        select(Math.max(-90, Math.min(90,cursor.lat+north)), Math.max(-180, Math.min(180,cursor.lon+east)), null);
        changeZoom(1);
      };
      svg.onclick = event => {
        const point = new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse());
        const lat = Math.max(-90, Math.min(90, 90-point.y/2));
        const lon = Math.max(-180, Math.min(180, point.x/2-180));
        select(+lat.toFixed(4), +lon.toFixed(4), null, true);
      };
      const saved = svg.fieldPoint ?? data.selected;
      if (saved) select(saved.lat, saved.lon, data.pilots.find(p => p.id === saved.pilot));
    }
    """,
)


def world_picker(selected=None):
    # Register in the active runtime, including fresh AppTest sessions.
    picker = st.components.v2.component("fieldshift_world_picker", **_appearance)
    names = {"punjab":"Punjab", "semi_arid_tropics":"Deccan", "us_corn_belt":"Iowa", "mediterranean":"Andalusia"}
    pilots = [
        {"id": r.id, "label": r.name, "short": names.get(r.id, r.country), "lat": r.latitude, "lon": r.longitude}
        for r in REGIONS.values()
    ]
    return picker(data={"land": _land_path(), "pilots": pilots, "selected": selected},
                  key="farm_atlas", on_chosen_change=lambda: None, on_inspected_change=lambda: None)
