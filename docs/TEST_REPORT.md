# FieldShift Test Report

**Date:** 2026-10-13  
**Status:** ✅ All 89 automated tests passing, 1 skipped (live API)  
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
| **Total** | **90** | **89 pass, 1 skip** |

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

---

## Manual Checks Performed

| # | Check | Result |
|---|---|---|
| 1 | Application starts and renders all 8 pages | ✅ |
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
