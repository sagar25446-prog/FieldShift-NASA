# Rule-based rotation engine

## Scope and supported evidence

The engine is deliberately a small deterministic graph search. It uses the Phase 2 crop catalogue and `data/rotation_rules.json`, whose crop-to-crop links are taken from PAU's documented Punjab examples. An absent relationship is **unsupported by this MVP**, not proof that farming it is impossible.

Hard failures are limited to: a catalogue season mismatch, a farmer-provided blocked crop/family (for example, a locally identified pest-history restriction), a documented water minimum exceeded by the user-entered **total crop-water budget**, a documented wheat soil exception, or an absent supported successor link. Missing evidence creates an `unknown` check and a `conditionally_feasible` plan, never an automatic rejection.

The total crop-water budget must be in mm per crop period and is only comparable to catalogue water ranges labelled as total crop water (irrigation plus effective rainfall) for the cited method. It is not silently derived from rainfall or an irrigation-system estimate.

## Metrics

All available numeric metrics are 0–1. The composite re-normalises only the weights of available metrics, and reports zero effective weight for unavailable metrics. It is a preference-weighted comparison, **not** a probability of success.

| Metric | Method | Availability |
| --- | --- | --- |
| Water suitability | Mean margin above documented crop/method minimums | Unavailable if budget or any selected crop water range is unknown |
| Climate suitability | No score | Unavailable until sourced crop-specific thresholds exist |
| Soil-related potential | Mean of documented favourable soil-context checks | Unavailable if relevant soil evidence is missing |
| Rotation diversity | Unique crop families / planned seasons | Always a composition indicator, never soil improvement |
| Economic potential | No score | Unavailable until credible local price/cost data is added |

`data/priority_weights.json` contains editable `balanced`, `water_conscious`, and `soil_focused` profiles. Values are validated as non-negative and normalised to sum to one. Economic weight is zero until economic evidence exists.

## Explainability

Each returned plan includes crops and seasons, pass/fail/unknown checks, source URLs, individual metric method/score/warning, effective weights, positive factors, trade-offs and uncertainty warnings. The engine is independent of Streamlit and is tested with the real catalogue/rules files.
