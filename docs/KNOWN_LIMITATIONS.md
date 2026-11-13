# FieldShift — known limitations and safe use

FieldShift is an explainable decision-support prototype. It supports exploration and discussion; it is not agricultural advice or a validated farm-management service.

## What the app does not claim

- It does not forecast weather or future yields.
- It does not measure soil pH, NPK, organic carbon, salinity, crop identity, groundwater level, or crop yield from NASA climate data.
- It does not guarantee water savings, profit, pest control, soil improvement, resilience, or successful establishment.
- A composite score is a preference-weighted comparison, not a probability of success.
- A legume in a sequence does not imply a fixed nitrogen contribution.

## Data boundaries

1. **NASA POWER.** The primary live integration is historical, gridded daily climate context. It is not a field weather station or a forecast. Missing observations are retained as missing and reported.
2. **Soil.** Farmer and laboratory values take precedence. SoilGrids is an optional modelled estimate, not a laboratory result. Unknown soil values remain unknown.
3. **Crop catalogues.** Rotation rules and seasons are limited to their configured regional catalogues and their cited sources. An undocumented edge means the prototype cannot support it; it does not prove the transition is impossible.
4. **Optional sources.** MODIS phenology, SoilGrids, and an optional local NEX-GDDP-CMIP6 extract have separate access and coverage requirements. SMAP, GPM, GRACE, ECOSTRESS, Landsat, SRTM, FIRMS, and GEDI are documented resources, not active location-specific plan inputs in this release.
5. **Economics.** Economic values are displayed only where the catalogue has identified benchmarks. They are not local prices, costs, or profit forecasts.

## Model boundaries

1. The rule engine is deterministic and small by design. It evaluates documented season, rotation, water, soil, and climate information; it does not simulate a complete farm system.
2. Hypothetical dry, hot, and irrigation-reduction scenarios are user-defined perturbations of historical context. They are stress tests, not climate forecasts or probability estimates.
3. Pareto comparisons only use metrics with available numeric values. Missing metrics are not treated as zero.
4. Any simplified soil-state or multi-year display is educational only and should not be used as a nutrient budget or soil-carbon prediction without local calibration and review.

## Required human verification before use in a field

- Crop calendar overlap, local variety, seed availability, equipment, irrigation delivery, drainage, and market access.
- Current laboratory soil results with sampling depth, date, method, and units.
- Local crop disease and pest history.
- Agronomist or extension-worker review of crop rules for the actual field and season.

## Product boundaries

- The app has no accounts and does not persist a farm profile after a session unless the user downloads it.
- Public services can be unavailable. The app reports live-request errors and does not substitute invented data.
- The team should re-run tests and the live workflow after each deployment. A successful code push alone does not prove the public application has rebuilt.
