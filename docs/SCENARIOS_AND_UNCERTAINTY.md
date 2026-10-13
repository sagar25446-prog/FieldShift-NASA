# Scenario stress tests and uncertainty

## Purpose

FieldShift's scenarios are deterministic sensitivity tests. They help a farmer see which documented rules or component scores change if selected planning assumptions change. They are **not** weather forecasts, probabilities of crop success, crop-yield models, or calibrated soil models.

## Scenario definitions

| Scenario | Exact transformation | What it does not mean |
| --- | --- | --- |
| Historical baseline | Uses the retrieved historical NASA POWER daily context unchanged and the farmer-provided water budget unchanged. | A future weather forecast. |
| Dry stress test | Multiplies every available `PRECTOTCORR` daily value by `1 - dry reduction / 100`. Default reduction is 25%. Missing values remain missing. | A prediction that rainfall will decline by that amount. |
| Hotter-than-baseline stress test | Adds the selected Celsius increment to available `T2M`, `T2M_MIN`, and `T2M_MAX` daily values. Default increment is +2 °C. Missing values remain missing. | A climate projection or a crop heat-risk calculation. |
| Reduced water-budget stress test | Only when a user chooses a reduction: multiplies the **farmer-provided total crop-water budget** by `1 - reduction / 100`. | A conversion of NASA precipitation into available irrigation water. |

The first two perturbations transform only a displayed, labelled hypothetical climate frame. The current crop catalogue does not contain verified crop-specific thermal thresholds, so FieldShift deliberately does not turn those transforms into a climate-suitability score.

## Robustness method

For each baseline sequence, FieldShift re-runs the same deterministic rotation checks under every scenario. It retains a sequence in the report even when it becomes infeasible, so a known hard-constraint failure is visible rather than silently omitted.

- A water-budget scenario can change the documented water-feasibility check and water score.
- A dry or hot stress test may change calculated climate summaries, but it cannot change crop eligibility until a sourced crop rule applies to that metric.
- A composite score remains a weighted comparison only; it is never a probability.

## Uncertainty categories

FieldShift lists notes rather than an invented confidence percentage.

- **Data coverage uncertainty:** missing farmer/laboratory soil inputs, missing daily climate values, and NASA POWER's gridded spatial context.
- **Model uncertainty:** incomplete crop water/thermal parameters and the small source-linked rotation graph. The engine does not predict yield, profit, pests, nitrogen fixation, or soil-carbon change.
- **Scenario uncertainty:** every dry, hot, or water-reduction perturbation is a user-selected hypothetical stress test.

### How uncertainty is tracked

| Source of uncertainty | Category | How FieldShift handles it |
| --- | --- | --- |
| Missing soil measurements (pH, EC, organic carbon, waterlogging) | Data coverage | Listed as specific missing-input notes; affected feasibility checks return "unknown" not "fail" |
| Incomplete climate records (missing daily values in NASA POWER response) | Data coverage | Missing observation counts are reported; stress transforms preserve NaN; totals warn about excluded days |
| Coarse spatial resolution (NASA POWER gridded ~0.5° point query) | Data coverage | Spatial applicability note is preserved from POWER provenance; labelled "not a field measurement" |
| Uncertain crop parameters (no thermal thresholds, some crops lack water ranges) | Model uncertainty | Unavailable metrics shown as "N/A" with method explanation; effective weight becomes zero |
| Simplified agronomic assumptions (rule-based feasibility, no yield/pest model) | Model uncertainty | Each check names its rule and source; no prediction or probability is implied |

### What FieldShift does NOT do

- **No numerical confidence percentage** is reported. There is no validated probabilistic model.
- **No probability of crop success** is computed. Composite scores are preference-weighted comparisons only.
- **No machine learning** is used for appearance. All logic is deterministic and source-linked.

## Pareto comparison

A plan is labelled dominated only when another plan has scores for every objective known in either plan, is at least as high for all of them, and is strictly higher for at least one. If an objective is unknown for either plan, FieldShift does not infer that the unknown is zero or use it to claim dominance. Non-dominated alternatives remain visible so the farmer retains the final choice.

## Soil-state modelling (Feature E)

A simplified soil-state and nutrient-balance module is included as `soil_nutrient_model.py`. It uses:

- **FAO Fertilizer and Plant Nutrition Bulletin 16** for legume N-fixation credit ranges (20–40 kg N/ha).
- **Brady & Weil (2017)** for residue C:N ratios and dry-matter ranges.
- **Janssen (1984)** one-compartment first-order SOC decay model with IPCC-referenced decay constants.

### Calibration limitations

- The N-fixation credit is a rough FAO estimate, **not calibrated** to Punjab conditions.
- The SOC decay constant (k = 0.025 yr⁻¹ for subtropical semi-arid) is interpolated from temperate/tropical studies.
- Residue-return fractions assume a default 30%; actual farmer practice (burning, baling, incorporation) varies.
- No micronutrient, phosphorus, or potassium balance is estimated.
- All outputs are labelled "Simplified estimate — not calibrated to local conditions."

### Required inputs

1. Crop residue management practice (returned, burned, removed)
2. Initial soil organic carbon (%) from laboratory analysis
3. Soil bulk density (Mg/m³) from field measurement
4. Applied fertiliser rates (kg N/ha) per crop
5. Irrigation method and scheduling

If any of these are unavailable, the limitation is disclosed alongside the estimate.
