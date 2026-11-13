# FieldShift crop catalogue

`crops.json` is a manually curated research catalogue for Ludhiana, Punjab. It contains source-linked crop characteristics and **indicative economic benchmarks** for comparison only. It does not contain farm observations, yield projections, local market quotes, or guaranteed economic returns.

The top level has `catalog_metadata`, a reusable `sources` registry, and a `crops` array. Each crop records identity, family/legume status, season, intended role, temperature and water evidence, soil/nutrient/rotation/pest evidence, evidence quality and source IDs.

Unknowns are deliberate: they have `status: "unknown"`, null numeric values where relevant, and an `evidence_needed` message. Unknown does not mean zero, safe or unsuitable. Economic benchmark fields are not farm-specific costs, prices, or profit predictions; see `docs/DATA_SOURCES.md` and `docs/KNOWN_LIMITATIONS.md`.

`source_ids` refer to the exact URL and access date in the source registry. Numeric water ranges retain their source method/context and unit; they are not converted into an irrigation recommendation.

Run `python -m pytest` to validate required fields, source IDs/HTTPS URLs, required units, documented water values, and explicit missing evidence. That validation checks structure, not agricultural truth; human review is listed in `docs/AGRONOMIC_ASSUMPTIONS.md`.

## Global historical crop calendar lookup

`global_calendar.npz` is a compact, read-only point lookup extracted from the **unfilled 0.5°** Sacks et al. crop-calendar archive (25 crop calendars). The archive is from [UW SAGE's 0.5-degree dataset page](https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/netcdf-0-5-degree/); dataset methods are described by [UW SAGE](https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/). The upstream archive checksum is verified by `scripts/build_calendar_atlas.py` before extraction. Its source archive is deliberately not committed; it may be downloaded from the linked page if the bundled lookup must be rebuilt.

The lookup contains the crop names and half-day-of-year planting and harvest values on the original 0.5° latitude/longitude grid. Empty source cells stay empty: no spatial filling or extrapolation is performed. The app displays only records present in the cell covering the selected point. These are regional historical calendar observations, not current field measurements or validated agronomic recommendations. The planner checks only non-overlapping timing and repeats a 365-day calendar; local crop suitability, soil, water, pest constraints, and multiple-year variability remain outside this calendar-only comparison.
