# FieldShift — ready-to-paste project submission content

Use the official 2026 form labels and character limits when they become visible. The copy below is intentionally specific to the working prototype and does not claim field validation or NASA endorsement.

## Project title

FieldShift

## One-line summary

FieldShift helps farmers and extension workers compare source-linked crop rotations using historical NASA climate context, known local inputs, and their own priorities.

## Short description

FieldShift is an explainable crop-rotation exploration tool. A user selects a farm location, retrieves historical NASA POWER climate context, enters what they know about soil and water, and sets priorities such as water conservation or crop diversity. The app compares a current rotation with multiple documented alternatives, showing hard checks, data sources, trade-offs, and unknowns. It supports better local conversations; it does not forecast yields, profits, or soil improvement.

## Full project description

Choosing a crop rotation is difficult when farmers must balance seasonal water availability, heat, soil constraints, past crops, and market uncertainty. A simple score without evidence can hide the most important part of the decision: what the tool does not know.

FieldShift turns that uncertainty into a visible part of the workflow. A farmer or extension worker selects a location and retrieves historical daily NASA POWER climate context. The app retains the exact request URL, date range, parameters, units, retrieval time, and missing-data information. The user then enters known soil and irrigation information, previous crops, restrictions, and their priorities. Unknown values remain unknown rather than being silently replaced.

For supported pilot regions, a deterministic engine searches a documented crop-relationship graph and compares multiple multi-season rotations. Each result separates water suitability, historical climate suitability, soil-related potential, diversity, and available indicative economics. It displays feasibility checks, source links, benefits, trade-offs, and warnings. A farmer can also compare a current rotation with alternatives using the same inputs and weights.

FieldShift includes dry, hot, and reduced-irrigation stress tests to explore how assumptions change a plan. These are clearly labelled hypothetical stress tests, not climate forecasts. Optional modules handle MODIS phenology context, SoilGrids estimates, and a limited future-climate demonstration extract with their own provenance and limits.

FieldShift is a decision-support prototype, not agricultural advice. It does not measure soil chemistry from space, forecast weather, predict crop yield or profit, or guarantee soil improvement. The final decision remains with the farmer and local agricultural expertise.

## NASA data and resources used

- **NASA POWER Daily API (primary live data path):** historical daily temperature, precipitation, solar radiation, humidity, and wind for a selected coordinate.
- **MODIS MCD12Q2 Collection 6.1 (optional):** historical seasonal-greenness context; it does not identify crops or yield.
- **NASA NEX-GDDP-CMIP6 (optional demonstration extract):** future climate-projection comparison, explicitly not a weather forecast.

See `docs/SUBMISSION_REFERENCES.md` for direct source links, additional agronomic sources, and a clear statement of which resources are not active integrations.

## Demonstration and project links

- Live application: https://fieldshift-nasa.streamlit.app/
- Source code: https://github.com/sagar25446-prog/Nasa-Hacakathon
- Challenge: https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/

## What is next

The next responsible step is regional agronomist review followed by observed farmer and extension-worker usability sessions. FieldShift keeps these validation needs visible instead of presenting the prototype as a completed farming advisory service.
