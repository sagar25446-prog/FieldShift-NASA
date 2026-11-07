# FieldShift Architecture

## Module Diagram

```
                        ┌──────────────┐
                        │    app.py    │  Streamlit entry point
                        │ (page_config)│  sets layout, title, icon
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │    ui.py     │  11-page Streamlit interface
                        │  (2854 lines)│  sidebar, forms, charts
                        └──┬──┬──┬──┬──┘
                           │  │  │  │
              ┌────────────┘  │  │  └────────────────┐
              │               │  │                    │
     ┌────────▼────────┐  ┌──▼──▼──────┐  ┌──────────▼──────────┐
     │  nasa_power.py  │  │rotation_   │  │    scenarios.py     │
     │ (NASA POWER API)│  │engine.py   │  │ (stress tests,      │
     │  fetch, cache,  │  │(DFS search,│  │  robustness, Pareto)│
     │  provenance     │  │ scoring)   │  │                     │
     └────────┬────────┘  └──┬──┬──────┘  └──────────┬──────────┘
              │              │  │                     │
              │         ┌────┘  └────┐        ┌───────▼────────┐
              │         │            │        │ soil_nutrient_ │
              │    ┌────▼────┐  ┌────▼────┐   │  model.py      │
              │    │crops.   │  │rotation_│   │ (FAO/IPCC,     │
              │    │json     │  │rules.   │   │  N-balance,    │
              │    │(10 crops│  │json     │   │  SOC direction)│
              │    │ + PAU   │  │(19 edges│   └────────────────┘
              │    │ sources)│  │+ season │
              │    └─────────┘  │ cycle)  │
              │                 └─────────┘
     ┌────────▼────────┐
     │  NASA POWER     │
     │  Daily API      │
     │  (HTTPS, no key)│
     └─────────────────┘
```

## Supporting Modules

| Module | Purpose |
|---|---|
| `climate_features.py` | Extract precipitation totals and temperature summaries from retrieved data |
| `climate_suitability.py` | FAO EcoCrop thermal suitability assessment |
| `climate_trends.py` | Multi-decadal OLS trend analysis from NASA POWER |
| `data_access.py` | Data source readiness contracts |
| `economics.py` | Indicative gross-margin economics (GoI MSP, PAU costs) |
| `export_import.py` | JSON farm profile serialization and printable HTML summary cards |
| `fao56.py` | Full FAO-56 Penman-Monteith ET₀/ETc water balance |
| `future_climate.py` | NASA NEX-GDDP-CMIP6 climate projection integration |
| `global_calendar.py` | Global crop calendar atlas (Sacks et al. 2010) |
| `growing_season.py` | Season date windowing and crop duration calculation |
| `land_use_phenology.py` | MODIS MCD12Q2 phenology client and season-use classification |
| `multi_year_simulation.py` | 3–5 year rotation trajectory simulation (SOC, N-balance) |
| `satellite_context.py` | GRACE, FIRMS, SMAP, GPM, MODIS reference context |
| `sensitivity.py` | Weight perturbation analysis and plain-language explanations |
| `soil_nutrient_model.py` | Simplified FAO/IPCC Tier 1 N-balance and SOC model |
| `soil_data.py` | ISRIC SoilGrids integration with uncertainty envelopes |
| `world_map.py` | D3.js interactive globe/map selector component |
| `calendar_workspace.py` | Custom calendar editing for non-pilot locations |
| `regions.py` | Multi-region framework (Punjab, US Corn Belt, Mediterranean, Semi-Arid) |
| `agronomy.py` | Verified crop calendars, pilot recommendations, heatwave hindcast |
| `recommendations.py` | Rotation comparison guard (logic lives in rotation_engine.py) |

## Data Flow

```
Farmer inputs          NASA POWER API          Crop catalogue
  (form)                 (HTTPS)               (crops.json)
    │                      │                       │
    ▼                      ▼                       ▼
┌─────────┐         ┌───────────┐          ┌────────────┐
│FarmPro- │         │PowerData- │          │Rotation-   │
│file     │         │set        │          │Engine      │
│(location│         │(DataFrame │          │(graph DFS, │
│ soil,   │◄────────│ + prove-  │          │ scoring,   │
│ water,  │         │ nance)    │          │ feasibility│
│ weights)│         └───────────┘          │ checks)    │
└────┬────┘                                └─────┬──────┘
     │                                           │
     ▼                                           ▼
┌─────────────────┐                    ┌──────────────────┐
│ Scenario engine │                    │ RotationPlan[]   │
│ (transform      │◄───────────────────│ (crop_ids,       │
│  climate data,  │                    │  metrics, checks,│
│  re-evaluate    │                    │  source URLs)    │
│  under stress)  │                    └──────────────────┘
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│ Robustness report│
│ + Pareto assess  │
│ + Uncertainty    │
│   notes          │
└──────────────────┘
```

## Key Design Decisions

1. **No ML** — With 10 crops and 11 edges, a transparent DFS is more appropriate than a model that hides its reasoning.
2. **Hard constraints first** — Feasibility checks run before scoring. A high composite score cannot override a hard constraint.
3. **Missing ≠ zero** — Unknown values stay unknown. Unavailable metrics show N/A, not 0.
4. **Source-linked** — Every crop, relationship, and rule links to a PAU or GoI source URL.
5. **Engine is Streamlit-independent** — `rotation_engine.py`, `scenarios.py`, `nasa_power.py` can be tested without Streamlit.
