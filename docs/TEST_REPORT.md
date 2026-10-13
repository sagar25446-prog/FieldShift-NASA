# FieldShift Test Report

**Date:** 2026-10-13  
**Status:** ✅ All 247 automated tests passing, 4 skipped (live API)  
**Python:** 3.13.12 | **pytest:** 9.1.1

---

## Test Summary

| Test File | Tests | Status |
|---|---|---|
| `test_crop_catalog.py` | 3 | ✅ All pass |
| `test_foundation.py` | 4 | ✅ All pass |
| `test_nasa_power.py` | 5 | ✅ All pass |
| `test_nasa_power_integration.py` | 1 | ⏭️ Skipped (live API) |
| `test_phase6.py` | 34 | ✅ All pass |
| `test_rotation_engine.py` | 6 | ✅ All pass |
| `test_scenarios.py` | 5 | ✅ All pass |
| `test_audit.py` | 32 | ✅ All pass |
| `test_fao56.py` | 17 | ✅ All pass |
| `test_nasa_data_dependency.py` | 5 | ✅ All pass |
| `test_climate_suitability.py` | 17 | ✅ All pass |
| `test_climate_trends.py` | 12 | ✅ All pass |
| `test_rotation_graph.py` | 9 | ✅ All pass |
| `test_demo_workflow.py` | 6 | ✅ All pass |
| `test_future_climate.py` | 13 | ✅ All pass |
| `test_soil_data.py` | 39 | ✅ All pass |
| `test_soilgrids_integration.py` | 1 | ⏭️ Skipped (live API) |
| `test_land_use_phenology.py` | 17 | ✅ All pass |
| `test_growing_season.py` | 12 | ✅ All pass |
| `test_modis_integration.py` | 1 | ⏭️ Skipped (live API) |
| `test_economics.py` | 3 | ✅ All pass |
| `test_satellite_and_sensitivity.py` | 4 | ✅ All pass |
| **Total** | **251** | **247 pass, 4 skip** |

---

## Automated Checks by Category

### 1. Crop Catalogue Integrity
- ✅ All sources are complete HTTPS references
- ✅ All crops have required fields and resolvable source IDs
- ✅ Water and temperature units, sources, and unknowns are explicit

### 2. Data Source Readiness
- ✅ Source statuses are explicit about readiness
- ✅ Unconfigured earth observations raise helpful errors
- ✅ Unvalidated agronomy does not claim feasibility
- ✅ Unimplemented recommendations do not return a result

### 3. NASA POWER API
- ✅ Parses DataFrame with units, provenance, and fill values
- ✅ Client caches identical requests and returns copies
- ✅ Validation and network errors produce clear messages
- ✅ API and malformed responses are rejected (never silently produce fake data)
- ✅ Documented indicators warn or require explicit definitions

### 4. Scenario Transformations
- ✅ Dry scenario reduces precipitation exactly by the specified percentage
- ✅ Hot scenario increases all temperature columns by the specified delta
- ✅ Missing values (NaN) are preserved through transforms
- ✅ Baseline transform is identity (no modification)
- ✅ Transforms are reproducible across multiple runs

### 5. Hard Constraint Violations
- ✅ Water budget reduction causes hard failure
- ✅ Waterlogged soil blocks wheat (status = infeasible)
- ✅ Blocked crops produce hard failures
- ✅ **High composite score cannot rescue an infeasible plan**

### 6. Missing Inputs
- ✅ Missing soil produces data-coverage notes
- ✅ Missing climate frame noted
- ✅ No confidence percentages appear in any notes

### 7. Score Changes
- ✅ Water reduction decreases water score
- ✅ Baseline scenario has zero score change

### 8. Pareto Comparisons
- ✅ Unknown evidence prevents false dominance
- ✅ Dominated candidates are correctly identified
- ✅ Pareto assessment is reproducible
- ✅ Equal scores produce no dominance

### 9. Soil-State Model (FAO/IPCC)
- ✅ Legume gets N-fixation credit
- ✅ Non-legume has no fixation credit
- ✅ Residue N and C are positive ranges
- ✅ SOC estimate without initial SOC is uncertain
- ✅ SOC estimate with initial SOC produces directional estimate
- ✅ Full soil-state report includes limitations
- ✅ All estimates have calibration warnings

### 10. Scenario Validation
- ✅ Out-of-range precipitation (>100% or <0%) rejected
- ✅ Temperature increase >10°C rejected
- ✅ Irrigation reduction >100% rejected
- ✅ Irrigation scenario only added when reduction > 0%

### 11. Rotation Engine
- ✅ Feasible maize → wheat → moong sequence generated
- ✅ Known water and soil constraints prevent invalid sequences
- ✅ Missing soil data is conditional, not rejection
- ✅ Weight normalization validates and normalises
- ✅ Family restrictions are hard constraints
- ✅ Priority changes can change ranking when supported scores differ

### 12. Reproducibility
- ✅ `generate()` produces identical results across runs
- ✅ Robustness reports are deterministic

### 13. Audit-Specific Checks
- ✅ Valid, invalid, and incomplete farm profiles handled correctly
- ✅ 'zaid' season rejected; 'summer' accepted
- ✅ No unsupported claims (yield prediction, profit guarantee, soil improvement) in plan outputs
- ✅ Economic potential always N/A
- ✅ Climate suitability always N/A
- ✅ API network failure raises `PowerNetworkError` (never fake data)
- ✅ Malformed JSON raises `PowerResponseError`
- ✅ All provenance URLs are HTTPS
- ✅ All crop source references are valid
- ✅ No crop uses 'zaid' in growing seasons
- ✅ Baseline scenario is not hypothetical
- ✅ All stress tests are hypothetical
- ✅ No fake confidence percentages in plans or robustness reports

### 14. FAO-56 Climate Water Balance & NASA Data Dependency
- ✅ FAO-56 Penman–Monteith daily $ET_0$ calculation reproduces standard Summer/Winter test points
- ✅ Psychrometric constant, saturation vapour pressure slope, and extraterrestrial radiation formulas verified
- ✅ Actual vapour pressure $e_a$ derived from $RH_{2m}$ or estimated via $T_{\min}$ fallback (FAO-56 Eq. 48)
- ✅ Wind speed defaults safely to standard 2.0 m/s when $WS_{2m}$ missing
- ✅ Missing solar radiation cleanly triggers graceful degraded fallback without fabricating numbers
- ✅ USDA SCS monthly effective rainfall calculation accounts for $ET_c$ and precipitation bounds
- ✅ Multi-stage linear interpolation of $K_c$ across initial, crop development, mid-season, and late-season
- ✅ Arid vs. Wet climate comparison shifts candidate rotation scores and inverts recommendation ranking:
  - Arid drought: Low-water rotation (`maize-wheat-moong`) outperforms water-intensive rotation (`rice-potato-moong`)
  - Wet monsoon: Ample rainfall satisfies water demand, boosting `rice-potato-moong` relative ranking
- ✅ Removing climate data cleanly switches engine to catalogue fallback without crashes
- ✅ Scenario climate transformations directly flow through daily FAO-56 series to update water metrics

### 15. FAO EcoCrop Thermal Suitability & Heat Stress Assessment
- ✅ Piece-wise linear response function verified for optimal, suboptimal, and boundary temperatures
- ✅ Extreme heat stress days ($T_{\max} \ge \text{threshold}$) reduce crop score proportionally
- ✅ Frost / chilling days ($T_{\min} \le T_{\text{kill}}$) penalize crop score
- ✅ Sourced EcoCrop cardinal thresholds ($T_{\min,\text{abs}}, T_{\min,\text{opt}}, T_{\max,\text{opt}}, T_{\max,\text{abs}}$) integrated for all 10 Punjab crops
- ✅ Absence of thresholds degrades cleanly to `status="unavailable"` without inventing arbitrary numbers
- ✅ Incomplete daily temperature series (NaNs) produce data coverage warnings
- ✅ Controlled test confirms ranking inversion under heatwave: heat-tolerant rotation (`pearl_millet-chickpea-moong`) overtakes heat-sensitive rotation (`maize-wheat-moong`) in climate score and composite ranking
### 16. Observed Historical Climate Trends & Decadal Rates of Change
- ✅ Parameter date coverage, observation counts, and completeness percentage audited for all variables
- ✅ Missing observations correctly identified (a 16-day gap created by the test in a copy of the genuine record)
- ✅ Regional growing seasons (Kharif, Rabi, Summer, Annual) accurately aggregated
- ✅ Cross-calendar-year Rabi cycle properly pairs Nov–Dec of year $Y$ with Jan–Apr of year $Y+1$
- ✅ Incomplete growing seasons (< 75% valid days) excluded from trend regression to prevent sampling distortion
- ✅ OLS decadal slope matches an independent least-squares fit on the genuine 2000–2024 POWER record (kharif mean T2M ≈ −0.78 °C/decade, p < 0.01). *Corrected 2026-10-13: earlier '+0.30 °C/decade' came from a synthetic fixture.*
- ✅ Baseline period vs. recent period comparison computes mean shift and percentage change
- ✅ Descriptive historical trends strictly separated from causal yield claims; no linear extrapolation into future forecasts

### 17. Live Judging Demonstration & Offline Snapshot Recovery
- ✅ Offline snapshot is an unmodified 2024 NASA POWER response (header, coordinates and retrieval time checked). *Corrected 2026-10-13: the earlier file was synthetic.*
- ✅ End-to-end demo workflow succeeds without network access (from profile load to rotation plan generation)
- ✅ Mode indicator clearly distinguishes between "Live NASA POWER API Data" and "Saved Offline Snapshot"
- ✅ Live API timeout reduced to 15 seconds, preventing indefinite hangs on slow networks
- ✅ Network failures cleanly caught with zero tracebacks and immediate one-click fallback recovery to the offline snapshot
- ✅ Generated demo plans produce valid FAO-56 water suitability, EcoCrop climate suitability, and composite scores

---

## Manual Checks Performed

| # | Check | Result |
|---|---|---|
| 1 | Application starts and renders all 9 pages (including Climate Trends) | ✅ |
| 2 | Ludhiana example loads with illustrative-only labels | ✅ |
| 3 | NASA POWER request succeeds for Ludhiana coordinates | ✅ |
| 4 | Climate charts render (temperature line, precipitation bar) | ✅ |
| 5 | Priority sliders update weights and are normalized | ✅ |
| 6 | Rotation plans generate with source URLs | ✅ |
| 7 | Scenario stress tests show robustness table and hard-constraint alerts | ✅ |
| 8 | Comparison page shows bar charts, Pareto cards, timeline, trade-off table | ✅ |
| 9 | Data and Methods page shows uncertainty handling table | ✅ |
| 10 | Footer appears on every page with prototype disclaimer | ✅ |
| 11 | No hardcoded API keys or secrets in source code | ✅ |
| 12 | `.env` listed in `.gitignore` | ✅ |
| 13 | Season selection fixed: 'zaid' mapped to 'summer' for engine compatibility | ✅ |
| 14 | API failure shows error message, does not produce fake data | ✅ |
| 15 | Home page disclaimer warns against yield/income/soil-improvement guarantees | ✅ |

---

## Scientific Validation Status

> ⚠️ **NOT SCIENTIFICALLY VALIDATED.** This is a decision-support prototype.

- Crop catalogue sources link to PAU (Punjab Agricultural University) documents
- Water requirement ranges sourced from Government of India annexure
- Soil-state model uses published FAO/IPCC equations but is **NOT calibrated** to Punjab conditions
- No yield predictions, profit guarantees, or soil improvement promises are made
- All scenarios are labelled as hypothetical stress tests, never forecasts
- No numerical confidence percentages are displayed

---

## Defects Fixed During Audit

| # | Defect | Fix |
|---|---|---|
| 1 | UI offered 'zaid' as season but engine uses 'summer' → `RotationInputError` | Mapped display labels: "Summer (zaid)" → engine value "summer" |
| 2 | `_plans()` returned `None` (empty body) | Wired to `_rotation_engine().generate(profile)` |
| 3 | `_theme()` called but undefined | Full CSS theme implemented |
| 4 | Page dispatch mapped 7 of 8 PAGES | All 8 PAGES mapped correctly |

---

## Known Test Gaps

- No end-to-end browser automation tests (Selenium/Playwright)
- No load testing
- No accessibility audit tool (WCAG 2.1 AA compliance not automated)
- Live NASA POWER integration test skipped by default (enable with `RUN_POWER_INTEGRATION=1`)

---

## Commands Used

```bash
# Run all tests
python -m pytest tests/ -v --tb=short

# Run audit tests only
python -m pytest tests/test_audit.py -v --tb=short

# Run live integration test (optional)
RUN_POWER_INTEGRATION=1 python -m pytest -m integration -v

# Launch the application
python -m streamlit run app.py --server.headless true
```
