# FAO EcoCrop Climate Suitability Methodology

## Overview

FieldShift evaluates growing-season thermal suitability using the **Food and Agriculture Organization (FAO) EcoCrop framework** combined with regional agronomic thermal stress thresholds from **Punjab Agricultural University (PAU)**.

Prior to this implementation, climate suitability was marked permanently `N/A` because crop-specific thermal thresholds were unverified. This implementation replaces the `N/A` placeholder with an **evidence-backed, traceable, piece-wise linear thermal suitability model** whenever daily NASA POWER observations and documented crop thresholds exist.

---

## 1. Mathematical Formulation

### 1.1 EcoCrop Cardinal Temperature Suitability ($S_{\text{temp}}$)

In the FAO EcoCrop crop ecological requirements framework (FAO 1998, 2000), each crop species is characterized by four cardinal temperatures for mean growing-season air temperature ($T_{\text{mean}}$):

- $T_{\min,\text{abs}}$: Absolute minimum temperature below which vegetative growth stalls or cold injury occurs.
- $T_{\min,\text{opt}}$: Lower boundary of the optimal thermal range for healthy vegetative and reproductive growth.
- $T_{\max,\text{opt}}$: Upper boundary of the optimal thermal range.
- $T_{\max,\text{abs}}$: Absolute maximum temperature above which physiological processes cease or heat injury occurs.

The standard FAO EcoCrop thermal suitability response $S_{\text{temp}}(T_{\text{mean}})$ is a piece-wise linear function bounded in $[0.0, 1.0]$:

$$
S_{\text{temp}}(T_{\text{mean}}) =
\begin{cases}
0.0 & \text{if } T_{\text{mean}} \le T_{\min,\text{abs}} \\
\frac{T_{\text{mean}} - T_{\min,\text{abs}}}{T_{\min,\text{opt}} - T_{\min,\text{abs}}} & \text{if } T_{\min,\text{abs}} < T_{\text{mean}} < T_{\min,\text{opt}} \\
1.0 & \text{if } T_{\min,\text{opt}} \le T_{\text{mean}} \le T_{\max,\text{opt}} \\
\frac{T_{\max,\text{abs}} - T_{\text{mean}}}{T_{\max,\text{abs}} - T_{\max,\text{opt}}} & \text{if } T_{\max,\text{opt}} < T_{\text{mean}} < T_{\max,\text{abs}} \\
0.0 & \text{if } T_{\text{mean}} \ge T_{\max,\text{abs}}
\end{cases}
$$

### 1.2 Extreme Temperature Stress Deduction ($P_{\text{stress}}$)

Mean temperature alone does not capture acute extreme temperature events (such as late-season heatwaves during wheat grain filling). FieldShift evaluates daily maximum temperatures ($T_{\max}$) against documented crop-specific extreme heat thresholds, and daily minimum temperatures ($T_{\min}$) against documented killing/frost temperatures:

$$f_{\text{heat}} = \frac{N_{\text{heat}}}{N_{\text{valid}}}, \quad N_{\text{heat}} = \sum_{d=1}^{N_{\text{valid}}} \mathbf{1}(T_{\max, d} \ge T_{\text{heat\_thresh}})$$

$$f_{\text{frost}} = \frac{N_{\text{frost}}}{N_{\text{valid}}}, \quad N_{\text{frost}} = \sum_{d=1}^{N_{\text{valid}}} \mathbf{1}(T_{\min, d} \le T_{\text{kill}})$$

The thermal stress penalty $P_{\text{stress}}$ proportionally reduces suitability based on the frequency of extreme events:

$$P_{\text{stress}} = \min\left(1.0, 0.5 \times f_{\text{heat}} + 0.5 \times f_{\text{frost}}\right)$$

### 1.3 Crop-Level Climate Score ($S_{\text{crop}}$)

$$S_{\text{crop}} = \max\left(0.0, \min\left(1.0, S_{\text{temp}} \times (1.0 - P_{\text{stress}})\right)\right)$$

- When temperatures remain entirely within the optimal range and zero stress days occur: $S_{\text{crop}} = 1.0$.
- When mean temperature is optimal but 20% of days suffer heatwaves: $P_{\text{stress}} = 0.10 \implies S_{\text{crop}} = 0.90$.
- When mean temperature is outside absolute tolerance: $S_{\text{temp}} = 0.0 \implies S_{\text{crop}} = 0.0$.

### 1.4 Rotation-Level Aggregation ($S_{\text{rotation}}$)

For a multi-season rotation sequence of crops $c_1, \dots, c_K$:

$$S_{\text{rotation}} = \frac{1}{K} \sum_{k=1}^K S_{\text{crop}, k}$$

---

## 2. Documented Crop Thermal Parameters

All 10 crops in the FieldShift catalogue have been sourced from the official **FAO EcoCrop database** and regional **Punjab Agricultural University (PAU)** packages of practices:

| Crop ID | Scientific Name | EcoCrop Code | $T_{\min,\text{abs}}$ (°C) | $T_{\min,\text{opt}}$ (°C) | $T_{\max,\text{opt}}$ (°C) | $T_{\max,\text{abs}}$ (°C) | $T_{\text{kill}}$ (°C) | Heat Threshold $T_{\text{heat}}$ (°C) & Agronomic Context | Sources |
|---|---|---|---|---|---|---|---|---|---|
| `wheat` | *Triticum aestivum* | 2114 | 5.0 | 15.0 | 23.0 | 27.0 | 0.0 | **32.0°C**: Terminal heat during March grain filling causes forced maturity and yield depression. | `fao_ecocrop`, `pau_rabi_2026` |
| `rice` | *Oryza sativa* | 1574 | 10.0 | 20.0 | 30.0 | 36.0 | — | **35.0°C**: High temperature during anthesis/flowering induces spikelet sterility. | `fao_ecocrop`, `pau_kharif_2026` |
| `maize` | *Zea mays* | 2175 | 10.0 | 18.0 | 33.0 | 47.0 | — | **38.0°C**: Extreme heat during pollination and silking impairs pollen viability. | `fao_ecocrop`, `pau_kharif_2026` |
| `cotton` | *Gossypium hirsutum* | 1160 | 15.0 | 22.0 | 36.0 | 42.0 | — | **42.0°C**: Extreme temperatures induce square and boll shedding. | `fao_ecocrop`, `pau_kharif_2026` |
| `moong` | *Vigna radiata* | 2150 | 8.0 | 21.0 | 36.0 | 40.0 | — | **40.0°C**: Prolonged heat accelerates flower drop and reduces pod setting. | `fao_ecocrop`, `pau_kharif_2026` |
| `soybean` | *Glycine max* | 1150 | 10.0 | 20.0 | 33.0 | 38.0 | — | **38.0°C**: Heat during reproductive stages impairs pod fill and nodulation. | `fao_ecocrop`, `pau_kharif_2026` |
| `pearl_millet` | *Pennisetum glaucum* | 8418 | 12.0 | 25.0 | 35.0 | 40.0 | 0.0 | **42.0°C**: Highly heat-resilient C4 cereal; extreme heat causes leaf scorch. | `fao_ecocrop`, `pau_kharif_2026` |
| `chickpea` | *Cicer arietinum* | 2479 | 7.0 | 15.0 | 29.0 | 35.0 | 0.0 | **32.0°C**: High temperature during flowering causes flower and pod abortion. | `fao_ecocrop`, `pau_rabi_2026` |
| `rapeseed_mustard` | *Brassica juncea* | 548 | 7.0 | 15.0 | 28.0 | 40.0 | 0.0 | **30.0°C**: High temperature during siliqua filling causes shriveled seed. | `fao_ecocrop`, `pau_rabi_2026` |
| `potato` | *Solanum tuberosum* | 1971 | 7.0 | 15.0 | 25.0 | 30.0 | -1.0 | **30.0°C**: Day temperature exceeding 30°C halts tuber initiation and bulking. | `fao_ecocrop`, `pau_rabi_2026` |

---

## 3. Evidence Sufficiency & Agronomic Boundary Conditions

### 3.1 Why Flowering-Stage Heat Thresholds Are Not Universally Assumed
EcoCrop provides general whole-cycle thermal ranges ($T_{\min}, T_{\text{opt}}, T_{\max}$). It does **not** provide calendar-dated phenological stage models. In FieldShift:
- We do **not** claim a calendar-dated "flowering-stage heat stress" count unless both the localized flowering date and cultivar stage threshold are explicitly supported by PAU.
- Instead, extreme heat events are transparently labelled as **"Days exceeding documented crop heat threshold ($T_{\max} \ge X^\circ\text{C}$)"**.

### 3.2 Distinguishing Unavailable Evidence from Poor Suitability
If a crop has `temperature_suitability.status == "unknown"` or if daily NASA POWER observations are absent:
- The system **never fabricates arbitrary temperatures or scores**.
- The crop status is marked as `status: "unavailable"`.
- If some crops in a rotation have thresholds while others do not, the rotation status is marked `status: "partial"`, reporting the score over available evidence with an explicit warning listing the unevidenced crops.
- If all crops lack thresholds or climate data is omitted, `climate_suitability.score` remains `None` (effective weight re-normalized to zero).

---

## 4. Strict Separation from Water Suitability

To avoid counting meteorological factors twice without scientific justification:

| Dimension | Water Suitability Metric (FAO-56) | Climate Suitability Metric (FAO EcoCrop) |
|---|---|---|
| **Governing Framework** | FAO-56 Penman–Monteith & USDA SCS | FAO EcoCrop & PAU Thermal Thresholds |
| **Meteorological Inputs** | Solar radiation ($R_s$), precipitation ($P$), humidity ($RH$), wind ($u_2$), $T_{\max}$, $T_{\min}$ | Daily mean temperature ($T_{\text{mean}}$), daily maximum ($T_{\max}$), daily minimum ($T_{\min}$) |
| **Crop Parameters** | Stage-interpolated crop coefficients ($K_c$) | Cardinal temperatures ($T_{\min,\text{abs}}, T_{\min,\text{opt}}, T_{\max,\text{opt}}, T_{\max,\text{abs}}$), heat threshold ($T_{\text{heat}}$) |
| **Evaluated Phenomena** | Atmospheric evaporative demand ($ET_0$), crop transpiration demand ($ET_c$), effective rainfall ($P_{\text{eff}}$), irrigation deficit ($NIR$) | Biological thermal adaptation, chilling stress, terminal heat stress, frost injury |
| **Precipitation Counted?** | **Yes** (determines effective supply) | **No** (omitted to prevent double-counting) |

---

## 5. Scientific Limitations & Disclosures

1. **Gridded Spatial Resolution:** NASA POWER observations have a native resolution of $\sim 0.5^\circ \times 0.5^\circ$. They reflect regional meteorological assimilation, not farm-specific canopy microclimates or topography.
2. **Physiological Adaptation Index:** The EcoCrop suitability index is an ecological comparative indicator. It does **not** simulate biophysical carbon assimilation or yield (such as DSSAT or APSIM).
3. **Cultivar Variations:** Individual cultivars (e.g. short-duration vs long-duration wheat) vary in heat tolerance. FieldShift reflects species-level guidelines from PAU and FAO.

---

## Growing-season windows (corrected 2026-10-13)

Each crop is evaluated only on the days of its own growing period: the regional season window (kharif from 1 Jun, rabi from 1 Nov, summer from 1 Apr; `climate_trends.REGIONAL_SEASONS`) for the crop's FAO-56 duration (sum of the Table 11/12 stage lengths), truncated at the window end with a warning. Shared implementation: `src/fieldshift/growing_season.py`.

- A record with several complete seasons gives one result per season, and the results are averaged. Heat and frost day counts are reported per season.
- A cross-year rabi season that is not complete in the record (e.g. a single calendar year) is assembled from the same month-days of the available record and labelled **"Composite"** in the UI and plan method text.
- Before this correction, the water balance gave every crop the whole year's ET0 and rainfall (annual rainfall counted once per crop), and the thermal assessment split the record into chronological thirds. Results produced before 2026-10-13 should not be compared with current results.
- Known overlap: the summer window (to 15 Jun) and kharif window (from 1 Jun) share 15 days, so a 75-day summer moong and the following kharif crop can overlap by up to 14 days.
