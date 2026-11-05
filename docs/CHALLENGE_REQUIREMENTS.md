# Challenge Requirements — Field Shift: Adapting Farms with NASA Data

**Challenge URL:** <https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/>  
**Categories:** Advanced, Intermediate  
**Skills:** Arts & Multimedia, Earth Science, Software  
**Last reviewed:** 2026-11-05
**Project Repository:** <https://github.com/sagar25446-prog/FieldShift-NASA>  
**Live Application:** <https://fieldshift-nasa.streamlit.app>

---

## Official Challenge Description

> Farmers around the world navigate shifting temperatures, changing rainfall patterns, water shortages, extreme weather, and declining soil health. These pressures make it difficult to choose crop rotations that protect fields, conserve water, and support long‑term resilience. Your challenge is to create a decision‑support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions.

---

## How FieldShift Addresses Each Challenge Requirement

| Challenge Requirement | FieldShift Implementation & Solution | Scientific & Technological Provenance | Verification Status |
|---|---|---|---|
| **Farmers around the world** | Globe supports arbitrary coordinate exploration. A separate deterministic rotation engine uses four pilot regional catalogues. | Coordinates outside supported pilot areas can see climate context and possibly historical timing only. | **Partial:** global selection works; agronomic rotation coverage is regional. |
| **NASA Earth observations** | NASA POWER daily climate is the primary dependable, on-demand integration. Other data modules are optional, require their own coverage/access, and are not all fused into each plan. | Request provenance and units are retained for NASA POWER; each optional dataset has a separate method. | **Partial:** do not interpret the app as a six-mission fused service. |
| **Local soil information** | Users can enter farmer/lab information; optional ISRIC SoilGrids estimates can be requested. | Modelled soil-grid values remain estimates and do not replace a field test. | **Available with limits:** local laboratory confirmation is required. |
| **Crop characteristics** | Regional crop catalogues and rotation rules inform the pilot planners; a global historical calendar atlas can provide dates where populated. | Calendar dates indicate historical regional timing, not field suitability. | **Regional:** source and agronomic review is still needed. |
| **Farmer priorities** | Editable priorities and normalized weights affect engine rankings when comparable plan metrics are available. | Deterministic weights and score explanations are shown in the planner. | **Implemented for pilot catalogues.** |
| **Explore rotation strategies** | The rule-based engine generates multiple alternatives for supported pilot regions; the global calendar tool compares non-overlapping dates only. | Global timing results are explicitly not agronomic feasibility recommendations. | **Regional engine; global timing-only exploration.** |
| **Strengthen soil health / conserve water** | Separate water and soil-related metrics, stress tests and educational soil-state methods are available in supported workflows. | These are model comparisons, not measured future improvements or guaranteed savings. Calibration and field validation are outstanding. | **Exploratory; expert review required.** |
| **Adapt to changing conditions** | Hypothetical dry/hot/water scenarios and an optional future-climate module are available. | Scenarios and climate projections are not local forecasts. | **Available with coverage and interpretation limits.** |

For the full gap analysis and work remaining, see [Project status report](PROJECT_STATUS_REPORT.md).

---

## What FieldShift Does NOT Do (Strict Scientific Boundaries)

To preserve scientific rigor and avoid misleading vulnerable smallholders, FieldShift maintains strict boundaries:
- ❌ **No black-box ML predictions:** Uses deterministic, verifiable biophysical equations rather than opaque neural networks.
- ❌ **No fabricated yield or profit guarantees:** Economic figures represent indicative GoI MSP (2024–25) and PAU/USDA cost-of-cultivation benchmarks for comparison only.
- ❌ **No remote soil chemistry claims:** Does not claim to measure nitrogen, phosphorus, or pH from space; remote sensors cannot measure root-zone chemistry without ground truth.
- ❌ **No fake confidence percentages:** Missing data is explicitly displayed as `N/A`, avoiding spurious probabilistic precision.

---

## Verification & Automated Test Status

- **Automated Tests:** 266 total test cases across 26 test files.
- **Pass Rate:** 262 passed, 4 skipped (live-network integration tests).
- **Continuous Integration:** Automated GitHub Actions pipeline running on Python 3.11 and 3.12 (`.github/workflows/ci.yml`).
- **Codebase Integrity:** MIT License, clean architecture separating engine logic from Streamlit presentation.
