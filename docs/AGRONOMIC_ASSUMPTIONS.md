# Agronomic Assumptions and Evidence Boundaries

`data/crops.json` is an evidence-linked research catalogue for Ludhiana district, Punjab, India. It is not an automated prescriptive recipe, universal crop calendar, or unconditional recommendation engine.

---

## 1. Crop Catalogue Connectivity & Reachability

FieldShift supports 10 regional crops across three seasonal windows (`kharif`, `rabi`, `summer`). All 10 crops have source-backed connectivity in the rotation graph (`data/rotation_rules.json`):

| Crop ID | Name | Botanical Family | Season(s) | Role & PAU Context | Reachability & Graph Edges |
|---|---|---|---|---|---|
| `rice` | Rice | Poaceae | Kharif | Baseline kharif cereal (2300–2600 mm water requirement) | Connected to `wheat`, `chickpea`, `potato`, `rapeseed_mustard`. Infeasible when water budget < 2300 mm. |
| `maize` | Maize | Poaceae | Kharif | Lower-water cereal alternative to rice (550–600 mm) | Connected to `wheat`, `potato`, `rapeseed_mustard`. |
| `cotton` | Cotton | Malvaceae | Kharif | Non-cereal commercial kharif crop in south-west Punjab | Connected to `wheat` (late sowing after cotton picking). |
| `soybean` | Soybean | Fabaceae | Kharif | Kharif oilseed legume | Connected to `wheat`. Shares Fabaceae family with summer moong (diversity 0.67 vs 1.0 for tri-family rotations). |
| `pearl_millet` | Bajra (pearl millet) | Poaceae | Kharif | Heat- and drought-hardy C4 cereal/fodder (250–350 mm) | Connected to `wheat`, `rapeseed_mustard`, and `chickpea`. Sensitive to waterlogging. |
| `wheat` | Wheat | Poaceae | Rabi | Primary rabi cereal staple (350–400 mm) | Successor to all kharif crops; connects to summer `moong`. Infeasible on waterlogged or highly alkaline soils. |
| `chickpea` | Gram (chickpea) | Fabaceae | Rabi | Low-water rabi pulse | Successor to `rice` and `pearl_millet`; connects to summer `moong`. |
| `rapeseed_mustard` | Rapeseed and mustard | Brassicaceae | Rabi | Major rabi oilseed group (Gobhi Sarson, Toria, Raya) (175–225 mm) | Successor to `rice`, `maize`, and `pearl_millet`; connects to summer `moong`. Best on well-drained soils. |
| `potato` | Potato | Solanaceae | Rabi | High-value, short-duration rabi tuber (300–320 mm) | Successor to `rice` and `maize`; connects to summer `moong`. |
| `moong` | Summer Moong | Fabaceae | Summer | Short-duration pre-monsoon catch crop (230–280 mm) | Successor to all 4 rabi crops; connects to kharif `rice`, `maize`, and `pearl_millet`. Fixes atmospheric N. |

---

## 2. Water Requirements & Dynamic Crop Water Balance

1. **Documented Approximation Ranges:** Sourced from Government of India Parliament Question Annexure AS110. They represent seasonal total crop water requirements (irrigation plus effective rainfall) under surface/flood irrigation.
2. **Dynamic FAO-56 Penman–Monteith Balance:** When daily NASA POWER observations are loaded, FieldShift evaluates real atmospheric evaporative demand ($ET_0$), applies stage-interpolated crop coefficients ($K_c$), calculates USDA SCS effective rainfall ($P_{\text{eff}}$), and derives the net irrigation deficit ($NIR = \max(0, \sum ET_c - P_{\text{eff}})$).
3. **Hard Constraint Enforcement:** If a farmer specifies a total crop water budget, any candidate crop whose documented minimum water requirement exceeds that budget fails feasibility. High composite scores can never bypass this constraint.

---

## 3. Thermal Suitability & Heat Stress Boundaries

1. **FAO EcoCrop Integration:** Sourced cardinal temperatures ($T_{\min,\text{abs}}, T_{\min,\text{opt}}, T_{\max,\text{opt}}, T_{\max,\text{abs}}$) define piecewise-linear thermal suitability (0.0 to 1.0) against growing-season mean temperature.
2. **Extreme Heat Stress:** Crops have documented thermal thresholds (e.g. 32°C for wheat anthesis, 35°C for rice flowering, 30°C for mustard siliqua development, 42°C for pearl millet). Days exceeding these thresholds penalize the crop score.
3. **Absence of Data:** If a crop lacks documented cardinal limits or extreme heat thresholds, its climate suitability score is explicitly marked `status="unavailable"` (N/A). No arbitrary numbers are fabricated.

---

## 4. Soil Context & Hard Constraints

1. **Wheat Constraint:** PAU documents that waterlogged and highly deteriorated alkaline soils cause complete wheat failure. When `waterlogged=True` or `highly_deteriorated_alkaline=True`, wheat is marked `status="fail"` (infeasible).
2. **Pearl Millet Constraint:** PAU cautions that bajra is sensitive to waterlogging. When `waterlogged=True`, pearl millet fails.
3. **Rapeseed/Mustard Context:** PAU states rapeseed/mustard performs best on well-drained, light-to-medium textured soils. Matching conditions earn documented favourable soil credit.
4. **Conditional Status:** When soil parameters are unknown (None), crops are marked `conditionally_feasible`, warning the user that field evidence is required.

---

## 5. Season Naming & Calendar Progression

1. **Engine Standard:** The engine internal cycle is strictly `["kharif", "rabi", "summer"]`.
2. **No 'zaid' in Engine:** To avoid naming collisions and validation errors, `"summer"` is used universally. The UI translates farmer-friendly labels ("Summer (zaid)") to `"summer"`.
3. **Seasonal Transitions:** Every graph edge connects adjacent seasons in the cycle:
   - Kharif (June–October) $\to$ Rabi (November–April)
   - Rabi (November–April) $\to$ Summer (April–June)
   - Summer (April–June) $\to$ Kharif (June–October)

---

## 6. Scientific and Disciplinary Boundaries

FieldShift enforces clear disciplinary boundaries:
- **No Yield Predictions:** FieldShift never outputs expected quintals per hectare.
- **No Profit Guarantees:** Economic potential is permanently N/A until verified local mandi prices and cost-of-cultivation budgets are configured.
- **No Soil-Improvement Promises:** Nitrogen credits and soil organic carbon trajectories are illustrative educational models based on FAO/IPCC equations, clearly disclosed as uncalibrated to Punjab conditions.
- **Hypothetical Scenarios:** Stress tests (+2°C heat, -25% rain) are hypothetical sensitivity analyses, never predictive weather forecasts.
