# FAO-56 Reference Evapotranspiration & Crop Water Balance Methodology

FieldShift implements the FAO-56 Penman–Monteith framework to calculate crop water requirements from NASA POWER daily weather observations, allowing historical and hypothetical climate data to directly determine water suitability scores and rotation rankings.

---

## 1. Reference Evapotranspiration ($ET_0$)

### 1.1 Penman–Monteith Equation (FAO-56 Eq. 6)

The standard FAO-56 Penman–Monteith equation calculates reference evapotranspiration ($ET_0$, $\text{mm}\cdot\text{day}^{-1}$) for a hypothetical grass reference surface:

$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T_{\text{mean}} + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$

Where:
- $R_n$: Net radiation at the crop surface ($\text{MJ}\cdot\text{m}^{-2}\cdot\text{day}^{-1}$)
- $G$: Soil heat flux density ($\text{MJ}\cdot\text{m}^{-2}\cdot\text{day}^{-1}$); taken as $G \approx 0$ for daily timesteps (FAO-56 §4.1)
- $T_{\text{mean}}$: Mean daily air temperature at 2 m height ($^\circ\text{C}$), computed as $\frac{T_{\max} + T_{\min}}{2}$
- $u_2$: Wind speed at 2 m height ($\text{m}\cdot\text{s}^{-1}$)
- $e_s$: Saturation vapour pressure ($\text{kPa}$)
- $e_a$: Actual vapour pressure ($\text{kPa}$)
- $\Delta$: Slope of the saturation vapour pressure curve ($\text{kPa}\cdot^\circ\text{C}^{-1}$)
- $\gamma$: Psychrometric constant ($\text{kPa}\cdot^\circ\text{C}^{-1}$)

### 1.2 Auxiliary Thermodynamic Relationships

1. **Saturation Vapour Pressure ($e_s$, FAO-56 Eq. 11 & 12):**
   $$e^\circ(T) = 0.6108 \exp\left(\frac{17.27 T}{T + 237.3}\right)$$
   $$e_s = \frac{e^\circ(T_{\max}) + e^\circ(T_{\min})}{2}$$

2. **Slope of Vapour Pressure Curve ($\Delta$, FAO-56 Eq. 13):**
   $$\Delta = \frac{4098 \left[0.6108 \exp\left(\frac{17.27 T_{\text{mean}}}{T_{\text{mean}} + 237.3}\right)\right]}{(T_{\text{mean}} + 237.3)^2}$$

3. **Psychrometric Constant ($\gamma$, FAO-56 Eq. 7 & 8):**
   $$P = 101.3 \left(\frac{293 - 0.0065 z}{293}\right)^{5.26}$$
   $$\gamma = 0.000665 P$$
   Where $z$ is elevation above sea level ($\text{m}$).

4. **Actual Vapour Pressure ($e_a$):**
   - When Relative Humidity ($RH_{2\text{M}}$, $\%$) is available:
     $$e_a = \frac{RH_{\text{mean}}}{100} \frac{e^\circ(T_{\max}) + e^\circ(T_{\min})}{2}$$
   - When Relative Humidity is unavailable (FAO-56 Eq. 48):
     $$e_a \approx e^\circ(T_{\min})$$
     *(Assuming $T_{\min} \approx T_{\text{dew}}$ in sub-humid/irrigated agricultural regions)*

5. **Net Radiation ($R_n$, FAO-56 Eq. 37–40):**
   - Net shortwave: $R_{ns} = (1 - \alpha) R_s$, with albedo $\alpha = 0.23$ for grass.
   - Solar radiation $R_s$ is taken directly from NASA POWER `ALLSKY_SFC_SW_DWN` ($\text{MJ}\cdot\text{m}^{-2}\cdot\text{day}^{-1}$).
   - Extraterrestrial radiation $R_a$ computed from latitude and day of year ($DOY$).
   - Clear-sky radiation: $R_{so} = (0.75 + 2 \times 10^{-5} z) R_a$.
   - Net longwave radiation ($R_{nl}$, FAO-56 Eq. 39):
     $$R_{nl} = \sigma \left[\frac{(T_{\max}+273.16)^4 + (T_{\min}+273.16)^4}{2}\right] (0.34 - 0.14\sqrt{e_a}) \left(1.35 \frac{R_s}{R_{so}} - 0.35\right)$$
   - Total net radiation: $R_n = R_{ns} - R_{nl}$.

---

## 2. Crop Evapotranspiration ($ET_c$)

Crop water requirement is estimated using the single crop coefficient method:

$$ET_c = K_c \times ET_0$$

### 2.1 Crop Coefficients ($K_c$) and Growth Stages (FAO-56 Table 12 & Table 11)

| Crop ID | Name | Season | $K_{c,\text{ini}}$ | $K_{c,\text{mid}}$ | $K_{c,\text{end}}$ | $L_{\text{ini}}$ (d) | $L_{\text{dev}}$ (d) | $L_{\text{mid}}$ (d) | $L_{\text{late}}$ (d) | Total Days | FAO-56 Reference |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `rice` | Rice | Kharif | 1.05 | 1.20 | 0.90 | 30 | 30 | 60 | 30 | 150 | Table 12 (flooded rice) |
| `maize` | Maize | Kharif | 0.30 | 1.20 | 0.35 | 20 | 35 | 40 | 30 | 125 | Table 12 (grain maize) |
| `cotton` | Cotton | Kharif | 0.35 | 1.15 | 0.50 | 30 | 50 | 55 | 45 | 180 | Table 12 (cotton) |
| `moong` | Summer Moong | Summer / Kharif | 0.40 | 1.05 | 0.35 | 15 | 25 | 25 | 10 | 75 | Table 12 (beans, green/dry) |
| `soybean` | Soybean | Kharif | 0.40 | 1.15 | 0.50 | 20 | 30 | 60 | 25 | 135 | Table 12 (soybean) |
| `pearl_millet` | Pearl Millet | Kharif | 0.30 | 1.00 | 0.30 | 15 | 25 | 40 | 25 | 105 | Table 12 (millet) |
| `wheat` | Wheat | Rabi | 0.30 | 1.15 | 0.25 | 20 | 30 | 60 | 40 | 150 | Table 12 (winter wheat) |
| `chickpea` | Chickpea (Gram) | Rabi | 0.40 | 1.00 | 0.35 | 20 | 30 | 40 | 20 | 110 | Table 12 (pulses/legumes) |
| `rapeseed_mustard` | Rapeseed / Mustard | Rabi | 0.35 | 1.15 | 0.35 | 20 | 30 | 35 | 25 | 110 | Table 12 (rapeseed/canola) |
| `potato` | Potato | Rabi | 0.50 | 1.15 | 0.75 | 25 | 30 | 30 | 30 | 115 | Table 12 (potato) |

Daily $K_c$ is linearly interpolated across the development stage ($L_{\text{dev}}$) and late-season stage ($L_{\text{late}}$) as prescribed in FAO-56 Chapter 6.

---

## 3. Effective Rainfall ($P_{\text{eff}}$)

To account for precipitation that is actually available to the crop root zone (excluding high-intensity runoff and deep percolation), monthly effective rainfall is computed using the **USDA Soil Conservation Service (SCS)** formula (FAO Irrigation and Drainage Paper 25):

$$P_{\text{eff, monthly}} = \begin{cases} 
P_{\text{month}} \times \frac{125 - 0.2 \times P_{\text{month}}}{125} & \text{if } P_{\text{month}} \le 250\text{ mm} \\
125 + 0.1 \times P_{\text{month}} & \text{if } P_{\text{month}} > 250\text{ mm}
\end{cases}$$

Seasonal effective rainfall $P_{\text{eff}}$ is the sum of monthly effective precipitation values over the crop period.

---

## 4. Seasonal Net Irrigation Requirement ($NIR$) and Water Score

### 4.1 Net Irrigation Requirement

$$NIR = \max\left(0, \sum ET_c - P_{\text{eff}}\right)$$

### 4.2 Climate-Derived Water Suitability Score

The water suitability score ($S_{\text{water}} \in [0, 1]$) expresses how adequately available water (rainfall and optional farmer irrigation budget) covers the crop demand:

1. **Rainfall coverage ratio:**
   $$C_{\text{rain}} = \min\left(1.0, \frac{P_{\text{eff}}}{\sum ET_c}\right)$$

2. **With Farmer Irrigation Budget ($W_{\text{budget}}$):**
   - If $NIR \le 0$: $S_{\text{water}} = 1.0$ (no irrigation needed).
   - If $W_{\text{budget}} \ge NIR$: $S_{\text{water}} = 1.0$ (budget fully satisfies irrigation deficit).
   - If $W_{\text{budget}} < NIR$:
     $$S_{\text{water}} = C_{\text{rain}} + (1.0 - C_{\text{rain}}) \times \frac{W_{\text{budget}}}{NIR}$$

3. **Without Farmer Irrigation Budget ($W_{\text{budget}} = \text{None}$):**
   $$S_{\text{water}} = C_{\text{rain}}$$
   *(Reflects purely rainfed suitability for the climate context)*

---

## 5. Disclosures & Scientific Limitations

1. **No Root-Zone Storage Measurement:** Neither $ET_0$ nor $NIR$ measures actual water currently stored in a specific farm's root zone. They represent atmospheric water demand and surface water balances.
2. **Omitted Hydrological Fluxes:** Capillary rise from shallow water tables, surface runoff partitioning, deep drainage below the root zone, and irrigation application efficiencies (canal/tubewell delivery losses) are omitted in this simplified balance.
3. **No Field Yield Prediction:** Water deficit scores compare rotation demand against supply; they do not predict crop yield or economic loss.
4. **Data Coverage Fallback:** If NASA POWER solar radiation or temperature data are missing, the engine explicitly falls back to catalogue water-budget range approximations, recording the degraded state.

---

## Growing-season windows (corrected 2026-10-13)

Each crop is evaluated only on the days of its own growing period: the regional season window (kharif from 1 Jun, rabi from 1 Nov, summer from 1 Apr; `climate_trends.REGIONAL_SEASONS`) for the crop's FAO-56 duration (sum of the Table 11/12 stage lengths), truncated at the window end with a warning. Shared implementation: `src/fieldshift/growing_season.py`.

- A record with several complete seasons gives one result per season, and the results are averaged. Heat and frost day counts are reported per season.
- A cross-year rabi season that is not complete in the record (e.g. a single calendar year) is assembled from the same month-days of the available record and labelled **"Composite"** in the UI and plan method text.
- Before this correction, the water balance gave every crop the whole year's ET0 and rainfall (annual rainfall counted once per crop), and the thermal assessment split the record into chronological thirds. Results produced before 2026-10-13 should not be compared with current results.
- Known overlap: the summer window (to 15 Jun) and kharif window (from 1 Jun) share 15 days, so a 75-day summer moong and the following kharif crop can overlap by up to 14 days.
