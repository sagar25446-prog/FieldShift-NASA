# FieldShift — test report

## Latest verification

**Date:** 2026-11-13

**Environment:** Python 3.13.12, pytest 9.1.1

**Result:** `269 passed, 5 skipped in 18.60s`

Command:

```powershell
python -m pytest -q --tb=short
```

The five skipped tests are opt-in checks that need external data access or a local browser. A skip is not a pass.

## Additional live data check

**Date:** 2026-11-13

**Result:** `1 passed in 2.79s`

```powershell
$env:RUN_POWER_INTEGRATION = "1"
python -m pytest tests/test_nasa_power_integration.py -q --tb=short
```

This called the public NASA POWER daily endpoint for the Ludhiana demonstration coordinates and verified returned rows, units, and time standard. It does not validate crop outcomes.

## What the automated suite covers

- Crop-catalogue structure, required fields, source URLs, units, and explicitly unknown values.
- NASA POWER request validation, response parsing, missing-value handling, provenance, caching, and clear error cases.
- Climate features and FAO-56 calculations using saved fixtures.
- Documented rotation constraints, infeasible sequences, missing soil inputs, deterministic repeatability, and priority-weight normalization.
- Hypothetical scenario transforms, robust plan reassessment, hard-constraint preservation, and Pareto handling of unavailable metrics.
- Soil-data parsing and labelled modelled estimates.
- Export/import safety and the printable summary-card disclosures.
- UI-facing explanation helpers, strategy comparison, global-calendar workspace logic, and source-status messaging.

## Browser check

The opt-in browser test is available at `tests/test_world_map_browser.py`. It exercises the globe, location selection, farm form, rotation workflow, and mobile layout when an installed Chromium browser is available.

```powershell
$env:FIELDSHIFT_BROWSER_TEST = "1"
$env:FIELDSHIFT_BROWSER_CHANNEL = "msedge"
python -m pytest tests/test_world_map_browser.py -q
```

Run it after each visual or interaction change. A separate public-site check is still required after the hosting platform rebuilds.

## Scientific boundary

Software tests show that the code behaves as specified. They do **not** establish agronomic accuracy, farmer usability, crop yield, profit, soil improvement, or external NASA endorsement. Those require qualified review and real-world evidence.
