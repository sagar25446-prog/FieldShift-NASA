# Agronomic assumptions and evidence boundaries

`data/crops.json` is a research catalogue for Ludhiana district, Punjab. It is not a prescription, universal crop calendar or recommendation engine.

1. A water range appears only where the cited Government of India source states that crop and method range. It is an approximate seasonal total crop-water requirement, not an irrigation schedule or farm demand.
2. No numeric temperature threshold is recorded. NASA POWER can provide climate context, but locally applicable stage-specific thermal thresholds need review before they become rules.
3. Family and legume status do not quantify nitrogen fixation, fertilizer reduction, residue effect or soil improvement.
4. A listed sequence only means PAU documented it. Feasibility still depends on field, cultivar, water, market, planting date and pest history.
5. Soil statements are directly summarized from PAU or labelled unknown. No district-average soil is assumed.
6. Pest/disease notes are not risk forecasts or pesticide advice.

## Inputs must remain distinct

| Category | Examples | Required label |
| --- | --- | --- |
| Measured soil data | Lab pH, EC, organic carbon, nutrients | Field/lab measurement with date, depth, method, unit |
| Farmer-provided | Boundary, history, irrigation, priorities | Farmer-provided |
| Remotely sensed | MODIS NDVI/EVI, GPM rainfall | Satellite indicator/estimate with product and scale |
| Modelled/assimilated | NASA–USDA soil moisture | Modelled-assimilated estimate |
| Gridded meteorological | NASA POWER | Gridded climate context |
| Assumption | Future default or mapping | Assumption with owner/review date |

## Must be verified by people before farmer-facing advice

- PAU/local extension review of crop list, crop windows, cultivar scope and rotation constraints.
- Agronomist approval of every temperature, water, nutrient, soil, pest and disease threshold.
- Lab-report suitability for any future soil rule.
- Local validation of NASA products and field-location matching.
- Current official price/cost sources if economics is ever added.
- Current Space Apps Challenge page and current PAU packages before public demo/submission.
