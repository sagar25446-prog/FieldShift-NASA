# 🌾 FieldShift

**Plan resilient crop rotations with evidence and transparency.**

FieldShift is a farmer-friendly decision-support web application for the NASA Space Apps Challenge 2026 challenge **"Field Shift: Adapting Farms with NASA Data."**

It combines **farmer-provided information**, historical **NASA POWER climate context**, and a source-linked crop catalogue to compare documented multi-season crop rotations. It provides transparent, rule-based alternatives—not yield, profit, or soil-improvement predictions.

> ⚠️ **Important:** FieldShift is a decision-support prototype. It cannot guarantee crop yield, profitability, or soil improvement. Farmers should combine its outputs with local expertise and field knowledge.

## ✨ Features

- 🧑‍🌾 **Farm Profile** — Enter location, soil conditions, water budget, and rotation history
- 🌤️ **NASA POWER Climate Data** — Retrieve real historical daily climate data (no API key needed) with clear live/offline mode indicators
- 📦 **Live Judging Preset & Offline Snapshot** — Instant one-click judging demo with real, verified 2024 Ludhiana daily NASA POWER observations and network fallback
- 📈 **Historical Climate Trends** — Multi-decadal OLS trend regression, decadal change rates, statistical significance ($p$-values), baseline comparisons, and consecutive dry-spell runs across regional growing seasons
- ⚖️ **Farmer Priorities** — Set and adjust weights for water, climate, soil, diversity objectives
- 🔄 **Rotation Engine** — Source-linked, deterministic crop-rotation alternatives powered by FAO-56 and EcoCrop
- 🧪 **Hypothetical Stress Tests** — User-chosen what-if changes (drier, hotter, less irrigation water); not climate projections
- 📊 **Pareto Comparison** — Multi-objective comparison with trade-off transparency
- 🌍 **Future Climate (NASA NEX-GDDP-CMIP6)** — Compares the same rotation's water and climate suitability under each of 5 models' 2041–2060 SSP2-4.5 and SSP5-8.5 projections against the same model's 1995–2014 simulation, with the spread across models; kept separate from hypothetical stress tests ([method](docs/FUTURE_CLIMATE.md))
- 🛰️ **Observed Land Use (NASA MODIS MCD12Q2)** — Shows which seasons were actually green at the farm's 500 m pixel over the last 10 years and flags plans that add a cropping season, with that season's extra crop water demand ([method](docs/OBSERVED_LAND_USE.md))
- 🛰️ **Optional SoilGrids Soil Estimates** — One click retrieves ISRIC SoilGrids 250 m estimates (texture, organic carbon, pH, total N; quantiles and uncertainty), clearly labelled; farmer/laboratory values always override them ([details](docs/SOIL_DATA.md))
- 🌱 **Soil-State Estimates** — Simplified N-balance and SOC direction using FAO/IPCC equations
- 📖 **Full Transparency** — Every score, check, and uncertainty is explained with source links

## 🖥️ Live Demo & Judging Preset

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fieldshift-nasa.streamlit.app)

FieldShift features a **Live Judging Quick-Start** preset right on the home page:
- One click loads the Ludhiana demonstration farm and its verified 2024 NASA POWER daily observations.
- Generates 4 diverse, feasible crop rotations scored via FAO-56 and EcoCrop in < 1 second.
- Toggles between live NASA POWER API calls and a saved, unmodified 2024 POWER response for the demo farm.
- If live NASA POWER calls timeout or fail during judging, an automatic one-click fallback restores the offline snapshot without interruption.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    app.py (entry point)                      │
│                         ↓                                    │
│                  ui.py (9 pages)                             │
│          ↙        ↓         ↓        ↘                      │
│   nasa_power.py  rotation_engine.py  climate_trends.py       │
│        ↓              ↓                 ↓                    │
│   NASA POWER    crops.json +      soil_nutrient_model.py     │
│   Daily API     rotation_rules.json                          │
└─────────────────────────────────────────────────────────────┘
```

**Data flow:**
1. Farmer enters location, soil, water budget, priorities → `FarmProfile`
2. `nasa_power.py` retrieves historical climate from NASA POWER → `PowerDataset`
3. `rotation_engine.py` searches documented crop-to-crop graph → `RotationPlan[]`
4. `scenarios.py` transforms climate data and re-evaluates → robustness report
5. `ui.py` renders everything with Plotly charts and source links

## Technology Stack

| Library | Use | Licence |
|---|---|---|
| [Python 3.11+](https://python.org) | Runtime | PSF |
| [Streamlit](https://streamlit.io) | Web interface | Apache 2.0 |
| [pandas](https://pandas.pydata.org) | Data handling | BSD 3-Clause |
| [NumPy](https://numpy.org) | Numeric operations | BSD 3-Clause |
| [Plotly](https://plotly.com) | Interactive charts | MIT |
| [pytest](https://pytest.org) | Automated tests | MIT |

## Project Layout

```text
app.py                          Streamlit entry point
src/fieldshift/                 Application modules
  __init__.py                   Package version
  data_access.py                Data source contracts
  nasa_power.py                 NASA POWER client and provenance
  climate_features.py           Historical climate indicators
  rotation_engine.py            Deterministic crop-rotation search
  scenarios.py                  Scenario stress tests and robustness
  soil_data.py                  SoilGrids adapter and soil source precedence
  land_use_phenology.py         MODIS MCD12Q2 adapter and observed season use
  growing_season.py             Per-crop season windows shared by water and climate metrics
  future_climate.py             NEX-GDDP-CMIP6 scenario extract, model-paired changes, plan comparison
  soil_nutrient_model.py        Simplified N-balance and SOC model
  agronomy.py                   Agronomic rule contracts
  recommendations.py            Rotation comparison contracts
  ui.py                         Streamlit interface (all 9 pages)
data/                           Crop, rotation-rule and priority-weight config
  crops.json                    Source-linked Punjab crop catalogue (10 crops)
  rotation_rules.json           PAU-documented crop-to-crop relationships (19)
  demo_snapshot_ludhiana_2024.json Unmodified NASA POWER daily response for the demo farm, 2024 (366 days; saved 2026-10-13)
  priority_weights.json         Editable farmer priority profiles
docs/                           Sources, assumptions, architecture, testing
tests/                          227 automated checks (224 pass offline; 3 live-API tests skipped unless enabled)
  test_audit.py                 Comprehensive audit tests (32)
  test_climate_suitability.py   FAO EcoCrop thermal suitability & heat stress (17)
  test_climate_trends.py        Historical climate trends and OLS regression (12)
  test_crop_catalog.py          Catalogue schema validation (3)
  test_demo_workflow.py         Live judging preset and offline recovery (6)
  test_fao56.py                 FAO-56 Penman-Monteith daily ET0, Kc, rain (17)
  test_foundation.py            Foundation contracts (4)
  test_nasa_data_dependency.py  Climate ranking inversion regression tests (5)
  test_nasa_power.py            POWER parsing and error handling (5)
  test_phase6.py                Scenarios, constraints, Pareto, soil-state (34)
  test_rotation_engine.py       Engine rules and determinism (6)
  test_rotation_graph.py        Rotation reachability & constraint tests (9)
  test_soil_data.py             SoilGrids parsing, units, depths, precedence, failures (39)
  test_soilgrids_integration.py Live SoilGrids query (skipped unless RUN_SOILGRIDS_INTEGRATION=1)
  test_land_use_phenology.py    MODIS phenology parsing, season use, plan role (17)
  test_growing_season.py        Per-crop season windows regression tests (12)
  test_modis_integration.py     Live MODIS query (skipped unless RUN_MODIS_INTEGRATION=1)
  test_scenarios.py             Scenario transforms and robustness (5)
```

## Run Locally

### Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

### With virtual environment

```bash
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints (usually `http://localhost:8501`).

## Run Tests

```bash
# All tests
python -m pytest

# Verbose with short tracebacks
python -m pytest -v --tb=short

# Optional live NASA POWER integration test
RUN_POWER_INTEGRATION=1 python -m pytest -m integration
```

## How Uncertainty Is Handled

FieldShift distinguishes three categories of uncertainty:

| Category | Examples | How it is disclosed |
|---|---|---|
| **Data coverage** | Missing soil measurements, incomplete climate records, coarse spatial resolution | Listed as specific missing-input notes; missing values are never filled |
| **Model uncertainty** | Simplified agronomic rules, absent crop thermal thresholds | Each score method is documented; unavailable metrics show "N/A" |
| **Scenario uncertainty** | User-defined stress tests are hypothetical, not forecasts | Every stress test is labelled "Hypothetical stress test" |

**No numerical confidence percentage** is reported. There is no validated probabilistic model.

## Documentation

- [`docs/CHALLENGE_REQUIREMENTS.md`](docs/CHALLENGE_REQUIREMENTS.md) — Official challenge text and FieldShift's response
- [`docs/WATER_BALANCE_METHODOLOGY.md`](docs/WATER_BALANCE_METHODOLOGY.md) — FAO-56 Penman–Monteith ET0, Kc stages, USDA SCS effective rainfall
- [`docs/CLIMATE_SUITABILITY_METHODOLOGY.md`](docs/CLIMATE_SUITABILITY_METHODOLOGY.md) — FAO EcoCrop cardinal thermal limits, heat stress criteria, and response functions
- [`docs/CLIMATE_TRENDS_METHODOLOGY.md`](docs/CLIMATE_TRENDS_METHODOLOGY.md) — Multi-decadal OLS trend regression, PAU seasonal calendars, and dry spells
- [`docs/NASA_POWER_DATA.md`](docs/NASA_POWER_DATA.md) — API parameters, units, resolution
- [`docs/ROTATION_ENGINE.md`](docs/ROTATION_ENGINE.md) — Rule checks, scoring, safeguards
- [`docs/SCENARIOS_AND_UNCERTAINTY.md`](docs/SCENARIOS_AND_UNCERTAINTY.md) — Scenario definitions, uncertainty categories
- [`docs/AGRONOMIC_ASSUMPTIONS.md`](docs/AGRONOMIC_ASSUMPTIONS.md) — Catalogue evidence and review items
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) — Source policy and provenance
- [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) — Honest disclosure of all limitations
- [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) — Automated and manual test results
- [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) — Deployment and submission guide
- [`data/README.md`](data/README.md) — Crop-record schema and provenance

## License

This project was built for the NASA Space Apps Challenge 2026.
