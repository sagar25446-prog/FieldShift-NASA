# Testing approach

## Automated checks in this release

**58 tests total (57 passed + 1 opt-in integration skip)**

### Foundation tests (`test_foundation.py`)
- Import and behaviour checks for data-access, agronomy, and recommendation contracts.

### Catalogue tests (`test_crop_catalog.py`)
- Source URL validity, required fields, water/temperature schema, and provenance.

### NASA POWER tests (`test_nasa_power.py`)
- Fixture-based response parsing, units, provenance, fill values, caching, validation, network errors, and climate feature summaries.

### NASA POWER integration test (`test_nasa_power_integration.py`)
- Live public API test; runs only when `RUN_POWER_INTEGRATION=1`.

### Rotation engine tests (`test_rotation_engine.py`)
- Documented feasible/infeasible sequences, hard water/soil failures, missing soil data, weight normalisation, deterministic repeatability, and priority-change ranking.

### Scenario tests (`test_scenarios.py`)
- Deterministic dry/hot transformations, irrigation-reduction hard failures, score changes, missing-input uncertainty, Pareto comparisons, validation, and repeatability.

### Phase 6 tests (`test_phase6.py`) — **34 new tests**

| Test class | Count | Coverage |
| --- | --- | --- |
| `TestScenarioTransformations` | 5 | Dry/hot/baseline transforms, missing-value preservation, reproducibility |
| `TestHardConstraintViolations` | 3 | Water budget failure, waterlogged soil blocks wheat, blocked crop is hard failure |
| `TestMissingInputs` | 3 | Missing soil → data coverage notes, missing climate frame, no confidence percentages |
| `TestScoreChanges` | 2 | Water reduction decreases score, baseline has zero change |
| `TestParetoComparisons` | 4 | Unknown prevents false dominance, dominated identified, reproducible, equal scores |
| `TestReproducibility` | 2 | Generate and robustness reports are deterministic |
| `TestScenarioValidation` | 5 | Boundary rejection for precipitation, temperature, irrigation; conditional scenario |
| `TestSoilStateModel` | 8 | Legume N-credit, non-legume, positive ranges, SOC uncertain/with data, limitations, calibration warnings |
| `TestScenarioProfile` | 2 | Water budget adjustment, None stays None |

## Running tests

```bash
# All offline tests
python -m pytest

# With verbose output
python -m pytest -v

# Phase 6 tests only
python -m pytest tests/test_phase6.py -v

# Live NASA POWER integration
RUN_POWER_INTEGRATION=1 python -m pytest -m integration
```

## Manual workflow checklist

Start the app and complete this full workflow:

1. **Home** → verify prototype warning, data readiness, Ludhiana example button
2. **Farm Profile** → enter or load Ludhiana example, save profile
3. **Climate Insights** → retrieve NASA POWER data, view charts and provenance
4. **Farmer Priorities** → adjust weights, verify normalization
5. **Rotation Recommendations** → generate alternatives, view feasibility checks and scores
6. **Scenario stress tests** → adjust dry/hot/water sliders, view robustness table, hard-constraint alerts, sensitivity summary, uncertainty categories
7. **Comparison View** → view score bar chart, Pareto status, planning timeline, trade-off summary
8. **Data and Methods** → verify information types, uncertainty explanation, provenance

Confirm: visible prototype warning, loading/error states, real NASA POWER provenance, source-linked checks, missing scores shown as "N/A" (not zero), no confidence percentages, soil-state estimates labelled as simplified.
