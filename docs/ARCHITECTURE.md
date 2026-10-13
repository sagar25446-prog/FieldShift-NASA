# FieldShift Architecture

## Module Diagram

```
                        ┌──────────────┐
                        │    app.py    │  Streamlit entry point
                        │ (page_config)│  sets layout, title, icon
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │    ui.py     │  8-page Streamlit interface
                        │  (1161 lines)│  sidebar, forms, charts
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
              │    │ + PAU   │  │(11 edges│   └────────────────┘
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
| `data_access.py` | Data source readiness contracts (NASA POWER, GPM, MODIS, soil-moisture) |
| `agronomy.py` | Agronomic rule contracts (not yet fully implemented) |
| `recommendations.py` | Rotation comparison contracts (not yet fully implemented) |

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
