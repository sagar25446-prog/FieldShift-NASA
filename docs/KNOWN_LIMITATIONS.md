# FieldShift — Known Limitations

> **This document honestly discloses the boundaries of FieldShift's capabilities.**  
> It is part of the project's commitment to transparency over false precision.

---

## Data Integrity Correction (2026-10-13)

During Task 7 the two NASA POWER files that earlier versions described as "verified" real observations were compared with live POWER responses and found to be **synthetic**:

- `data/demo_snapshot_ludhiana_2024.json` had a non-POWER header ("Verified Offline Demonstration Snapshot", API v2.0.0) and differed from live POWER at the same coordinates on 365–366 of 366 days (2024 rainfall 372 mm vs 764 mm live).
- `tests/fixtures/power_daily_ludhiana_historical_2000_2024.json` carried a genuine-looking POWER header but contained **exactly 372.2 mm of rainfall in every year** and a planted +0.30 °C/decade temperature trend. Its own tests described "injected" missing days and an "embedded trend".

Both files were replaced with **unmodified live POWER responses** retrieved 2026-10-13 for the demonstration farm (30.85 N, 75.70 E; identical to the former city-centre point because both lie in the same POWER grid cell). Consequences:

- Climate-trend results shown earlier (e.g. "+0.30" or "+0.42 °C/decade kharif warming") were artefacts of synthetic data. The genuine record shows kharif mean T2M **declining by about 0.78 °C/decade** (2000–2024, p ≈ 0.0025) at this grid cell. This is a description of a gridded reanalysis product, not proof of local cooling, and has not been checked against station data.
- All demo rankings and water/thermal indicators changed and are now computed from real data.
- The demonstration farm was moved from Ludhiana city centre (MODIS MCD12Q1: *Urban and Built-up*) to a MODIS-confirmed cropland pixel (MCD12Q1: *Croplands*, 2020–2024).

## Engine Correction: Season Windows (2026-10-13)

Before this date the FAO-56 water balance gave **every crop the whole year's ET0 and rainfall** (so annual rainfall was counted once per crop), and the EcoCrop thermal assessment split the record into chronological thirds (a "kharif" crop received January–April temperatures). Both now use each crop's own regional season window for its FAO-56 crop duration (`src/fieldshift/growing_season.py`). A cross-year rabi season that is not complete in the record is assembled as a labelled composite. Remaining limitation: the summer window (1 Apr–15 Jun) overlaps the kharif window (from 1 Jun), so a 75-day summer moong and the next kharif crop share up to 14 calendar days.

---

## Scope Limitations

1. **Regional focus:** Prototype supports Punjab, India crop rotations (Ludhiana demonstration region and broader Indo-Gangetic Plains agro-climatic zone).
2. **Crop catalogue size:** 10 crops in catalogue, with 19 PAU-documented crop-to-crop transitions covering all active crops.
3. **Season model:** Fixed regional cycle: kharif → rabi → summer (zaid).
4. **Planning horizon:** Maximum 3 seasons (configurable to 2).
5. **Graph coverage:** All 10 catalogue crops (`rice`, `maize`, `cotton`, `moong`, `soybean`, `pearl_millet`, `wheat`, `chickpea`, `rapeseed_mustard`, `potato`) are fully reachable and form documented, feasible rotation sequences.

---

## Data Limitations

1. **Climate data:** NASA POWER is gridded (~0.5° resolution), not field-level measurement. It is historical context, not a local forecast.
2. **Soil data:** Farmer/lab values are primary. An optional ISRIC SoilGrids 2.0 estimate (250 m modelled grid, not a field measurement) can fill empty fields where appropriate. Its 90% prediction ranges are documented at Punjab test points. Unknown values remain unknown. See `docs/SOIL_DATA.md`.
3. **Temperature thresholds:** Sourced from [FAO EcoCrop Database](https://ecocrop.apps.fao.org/) cardinal temperature limits ($T_{\min,\text{abs}}$, $T_{\min,\text{opt}}$, $T_{\max,\text{opt}}$, $T_{\max,\text{abs}}$) and PAU heat-stress thresholds (e.g. 32°C terminal heat for wheat).
4. **Economic benchmarks:** Indicative gross revenues and margins are calculated using Government of India Minimum Support Prices (MSP 2024-25) and Punjab Agricultural University (PAU) benchmark operational costs. They represent policy benchmarks and indicative comparisons, not farm-specific profit guarantees.
5. **Water requirements:** Sourced from Government of India Annexure AS110 and PAU Packages of Practices. In addition, real-time climate-derived crop water requirements (ETc) and net irrigation deficits are calculated via FAO-56 Penman–Monteith daily ET₀ and crop development stage coefficients (Kc).
6. **Missing observations:** NASA POWER fill values (-999.0) are converted to NaN and counted. They are never silently replaced with interpolated values.

---

## Model Limitations

1. **Composite score:** A preference-weighted comparison, not a probability of success. It cannot be interpreted as yield prediction.
2. **Pareto analysis:** Only compares on available numeric scores. Missing scores are preserved as N/A, not treated as zero. This prevents false dominance claims.
3. **Soil-state model:** Simplified FAO/IPCC N-balance and Janssen (1984) SOC model. **NOT calibrated to Punjab conditions.** Uses assumed defaults for residue parameters. Labelled as "educational comparison only" in the UI.
4. **Rotation graph:** Deterministic graph traversal over 19 documented relationships. Absence of a relationship means "unsupported by this prototype," not "agronomically impossible."
5. **No machine learning:** No black-box ML models are used. This is intentional — the goal is decision transparency, scientific explainability, and traceability over complexity.
6. **No pest/disease modelling:** Pest and disease cycles are not dynamically simulated. Farmers can provide avoidance restrictions (e.g. pest history) but the system does not predict pest pressure.

---

## UI/UX & Regional Usability

1. **Bilingual labels:** Regional crop names in Punjabi (ਪੰਜਾਬੀ) and Hindi (हिंदी) are displayed alongside English names for accessible communication.
2. **Water Budget Estimator:** Farmers can input tubewell motor horsepower, operating hours/week, and canal water turns (warrabandi) to automatically calculate equivalent seasonal water budgets in mm.
3. **Offline Mode Scope:** Includes a saved, unmodified 2024 NASA POWER response for the demonstration farm (`data/demo_snapshot_ludhiana_2024.json`, 30.85 N 75.70 E) for walkthroughs and automatic network fallback. Other coordinates use live NASA POWER API.
4. **No multi-user accounts:** Session-based prototype; no persistent database or user logins.
5. **Charts require JavaScript:** Interactive Plotly charts require JavaScript in the browser.

---

## Security Considerations

1. **No authentication system:** This is a client-side decision-support prototype. No user login or access control.
2. **No persistent user data:** All data is session-only and discarded on refresh/close.
3. **NASA POWER API:** Public endpoint, no API key required, no credentials stored.
4. **Input validation:** Server-side validation exists for coordinates (-90 to 90, -180 to 180), dates, priority weights, and numeric ranges. No SQL or command injection risk (no database, no shell commands).
5. **CORS:** Not applicable — single-page Streamlit application.
6. **License:** Open-source under the MIT License.

---

## Items Requiring Expert Review

1. **District-level crop water requirement calibration:** While FAO-56 Penman–Monteith ETc and GoI approximations are implemented, district-level microclimates benefit from local agronomist review.
2. **Soil constraint rules:** Sourced from PAU recommendations; can be extended for micro-level alkaline/saline pockets.
3. **Soil-state model equations:** Published FAO/IPCC equations can be calibrated with local long-term Punjab field trial datasets (e.g., PAU Ludhiana rotation trials).
4. **Rotation compatibility graph:** Can be expanded beyond the current 19 edges as additional multi-crop transitions receive documented agronomic trials.

---

## Future Roadmap (Next Phases)

| Priority | Feature | Notes | Status in Prototype |
|---|---|---|---|
| Implemented | Temperature suitability thresholds | FAO EcoCrop cardinal temperatures & PAU heat thresholds | ✅ Active |
| Implemented | Extended rotation graph | 19 edges; all 10 crops reachable and feasible | ✅ Active |
| Implemented | Indicative economics & MSP benchmarks | GoI MSP 2024-25 & PAU costs; baseline water savings | ✅ Active |
| Implemented | Future climate projections | NASA NEX-GDDP-CMIP6 (5 models, SSP2-4.5 & SSP5-8.5) | ✅ Active |
| Implemented | Observed land use dynamics | NASA MODIS MCD12Q2 phenology & greenup seasons | ✅ Active |
| Implemented | Regional Earth observation context | NASA GRACE groundwater depletion & NASA FIRMS fires | ✅ Active |
| Implemented | Weight sensitivity & rank stability | ±20% priority perturbations tested | ✅ Active |
| Medium | GPM IMERG precipitation integration | Sub-daily / high-resolution precipitation data | Future Phase |
| Medium | SMAP / NASA-USDA root-zone soil moisture | Real-time satellite root zone moisture | Future Phase |
| Medium | Multi-year planning horizon | Multi-year cumulative soil organic carbon dynamics | Future Phase |

---

## Disclaimer

FieldShift is an **explainable decision-support prototype**. It does not:
- Measure soil chemistry from space
- Forecast weather
- Predict crop yield or profit
- Guarantee soil improvement
- Replace local agronomic advice

All outputs should be confirmed with qualified agricultural advisors and local evidence before making farming decisions.
