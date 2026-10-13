# FieldShift crop catalogue

`crops.json` is a manually curated Phase 2 research catalogue for Ludhiana, Punjab. It contains no observations, recommendations, yield projections, costs, prices or economic returns.

The top level has `catalog_metadata`, a reusable `sources` registry, and a `crops` array. Each crop records identity, family/legume status, season, intended role, temperature and water evidence, soil/nutrient/rotation/pest evidence, evidence quality and source IDs.

Unknowns are deliberate: they have `status: "unknown"`, null numeric values where relevant, and an `evidence_needed` message. Unknown does not mean zero, safe or unsuitable.

`source_ids` refer to the exact URL and access date in the source registry. Numeric water ranges retain their source method/context and unit; they are not converted into an irrigation recommendation.

Run `python -m pytest` to validate required fields, source IDs/HTTPS URLs, required units, documented water values, and explicit missing evidence. That validation checks structure, not agricultural truth; human review is listed in `docs/AGRONOMIC_ASSUMPTIONS.md`.
