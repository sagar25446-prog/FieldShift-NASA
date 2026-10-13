# 🌾 FieldShift

**Plan resilient crop rotations with evidence and transparency.**

FieldShift is a farmer-friendly decision-support web application for the NASA Space Apps Challenge 2026 challenge **"Field Shift: Adapting Farms with NASA Data."**

It combines **farmer-provided information**, historical **NASA POWER climate context**, and a source-linked crop catalogue to compare documented multi-season crop rotations. It provides transparent, rule-based alternatives—not yield, profit, or soil-improvement predictions.

> ⚠️ **Important:** FieldShift is a decision-support prototype. It cannot guarantee crop yield, profitability, or soil improvement. Farmers should combine its outputs with local expertise and field knowledge.

## ✨ Features

- 🧑‍🌾 **Farm Profile** — Enter location, soil conditions, water budget, and rotation history
- 🌤️ **NASA POWER Climate Data** — Retrieve real historical daily climate data (no API key needed)
- ⚖️ **Farmer Priorities** — Set and adjust weights for water, soil, diversity objectives
- 🔄 **Rotation Engine** — Source-linked, deterministic crop-rotation alternatives
- 🧪 **Scenario Stress Tests** — Compare rotations under dry, hot, and reduced-water scenarios
- 📊 **Pareto Comparison** — Multi-objective comparison with trade-off transparency
- 🌱 **Soil-State Estimates** — Simplified N-balance and SOC direction using FAO/IPCC equations
- 📖 **Full Transparency** — Every score, check, and uncertainty is explained with source links

## 🖥️ Live Demo

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fieldshift-nasa.streamlit.app)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    app.py (entry point)                      │
│                         ↓                                    │
│                  ui.py (8 pages)                             │
│          ↙        ↓         ↓        ↘                      │
│   nasa_power.py  rotation_engine.py  scenarios.py            │
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
  soil_nutrient_model.py        Simplified N-balance and SOC model
  agronomy.py                   Agronomic rule contracts
  recommendations.py            Rotation comparison contracts
  ui.py                         Streamlit interface (all 8 pages)
data/                           Crop, rotation-rule and priority-weight config
  crops.json                    Source-linked Punjab crop catalogue (10 crops)
  rotation_rules.json           PAU-documented crop-to-crop relationships (11)
  priority_weights.json         Editable farmer priority profiles
docs/                           Sources, assumptions, architecture, testing
tests/                          90 automated checks (89 pass, 1 live API skip)
  test_audit.py                 Comprehensive audit tests (32)
  test_phase6.py                Scenarios, constraints, Pareto, soil-state (34)
  test_rotation_engine.py       Engine rules and determinism (6)
  test_scenarios.py             Scenario transforms and robustness (5)
  test_nasa_power.py            POWER parsing and error handling (5)
  test_crop_catalog.py          Catalogue schema validation (3)
  test_foundation.py            Foundation contracts (4)
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
