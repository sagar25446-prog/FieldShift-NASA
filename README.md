# FieldShift

**Explore how climate and crop rotation choices relate to a farm.**

FieldShift is a NASA Space Apps Challenge 2026 prototype for *Field Shift: Adapting Farms with NASA Data*. It combines historical NASA POWER climate context, farmer-provided soil and water details, documented crop information, and farmer priorities to compare rotation options where reviewed regional rules are available.

> FieldShift is a decision-support prototype. It does not forecast farm weather, predict yield or profit, or guarantee soil improvement. NASA POWER is gridded climate data, not a field measurement. Review any plan with a qualified local agricultural adviser.

## What works today

- Explore arbitrary coordinates with an interactive globe and retrieve historical daily NASA POWER climate data.
- Inspect monthly rainfall and temperature summaries, coverage, provenance and downloadable daily CSV.
- Enter soil and water details, leaving unmeasured values unknown. Optional SoilGrids estimates are identified as modelled.
- Generate explainable rule-based crop-rotation alternatives for four configured pilot areas: Punjab, the US Corn Belt, Andalusia, and the semi-arid tropics of India.
- Compare farmer priorities, historical context and clearly labelled hypothetical stress tests.
- Outside pilot regions, inspect global climate data and, where available, historical crop-calendar timing. Calendar timing alone is not an agronomic rotation recommendation.

Optional MODIS, soil-grid and future-climate features depend on source access, geographic coverage and local files. They are not all inputs to every recommendation. See [data and methods](docs/DATA_SOURCES.md) and [known limitations](docs/KNOWN_LIMITATIONS.md).

## Run locally

Python 3.11 or 3.12 is recommended.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

If PowerShell blocks activation, run the environment interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

NASA POWER does not require an API key. Live retrieval requires internet access. Never put credentials in source control; local `.env` and Streamlit secrets are ignored by Git.

## Checks

```powershell
python -m pytest
```

Run optional network checks separately when access is available:

```powershell
$env:RUN_POWER_INTEGRATION = "1"
python -m pytest tests/test_nasa_power_integration.py -q
```

The interactive browser journey is opt-in and requires installed Playwright and Microsoft Edge:

```powershell
$env:FIELDSHIFT_BROWSER_TEST = "1"
$env:FIELDSHIFT_BROWSER_CHANNEL = "msedge"
python -m pytest tests/test_world_map_browser.py -q
```

## Project layout

- `src/fieldshift/nasa_power.py` — NASA POWER client, validation and provenance.
- `src/fieldshift/rotation_engine.py` and regional JSON files — explainable rules and crop catalogues.
- `src/fieldshift/ui.py` — Streamlit user interface.
- `data/crops.json` — sourced Punjab crop catalogue.
- `docs/` — data provenance, assumptions, architecture, challenge fit, testing and review materials.
- `tests/fixtures/` — saved responses for deterministic offline tests.

## Project status

The prototype addresses the core challenge workflow, but it has not been validated by qualified agronomists or representative farmers. Agronomic review, observed user testing, and a verified hosted deployment check remain open. Read the [project status report](docs/PROJECT_STATUS_REPORT.md) and [challenge requirements mapping](docs/CHALLENGE_REQUIREMENTS.md) before relying on or presenting the outputs.

## Links

- [NASA challenge statement](https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/)
- [FieldShift app](https://fieldshift-nasa.streamlit.app/)
- [FieldShift repository](https://github.com/sagar25446-prog/Nasa-Hacakathon)
- [Earth explorer design](docs/EARTH_EXPLORER.md)

FieldShift is an independent student prototype and is not endorsed by NASA.
