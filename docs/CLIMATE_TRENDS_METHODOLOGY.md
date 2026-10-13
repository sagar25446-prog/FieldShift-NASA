# Historical Climate Trends Methodology

## 1. Overview and Purpose

FieldShift's Historical Climate Trends module analyzes empirical, multi-decadal meteorological data from the **NASA Prediction of Worldwide Energy Resources (POWER)** API (1981–present).

The purpose of this module is to provide farmers, agronomists, and judges with transparent, evidence-based context on how local growing-season climate conditions have evolved historically over the long term.

Rather than presenting uncalibrated black-box forecasts or arbitrary numbers, FieldShift calculates:
1. **Actual date coverage and completeness** for every meteorological parameter.
2. **Growing-season aggregations** based on verified regional crop calendars (Punjab Agricultural University).
3. **Ordinary Least Squares (OLS) linear regressions** with decadal rates of change and two-tailed Student's $t$-test $p$-values.
4. **Historical baseline vs. recent period comparative anomalies**.
5. **Strict scientific boundaries**, explicitly distinguishing descriptive historical observations from causal agronomic claims and preventing linear extrapolation into future forecasts.

---

## 2. Regional Growing Season Definitions

FieldShift defines regional growing seasons in accordance with the **Punjab Agricultural University (PAU) Package of Practices** and agro-ecological calendar:

| Season ID | Display Name | Calendar Window | Description & Key Crops | Cross-Year Cycle |
|---|---|---|---|---|
| `kharif` | Kharif (Monsoon Summer) | June 1 – October 31 | Summer monsoon season: Rice, Maize, Cotton, Moong | No |
| `rabi` | Rabi (Winter / Spring) | November 1 – April 30 (+1 yr) | Winter/spring season: Wheat, Chickpea, Mustard, Potato | **Yes** (Year $Y$ to $Y+1$) |
| `summer` | Summer (Zaid) | April 1 – June 15 | Short pre-monsoon summer window: Summer Moong | No |
| `annual` | Full Calendar Year | January 1 – December 31 | Complete annual cycle for general climatological trends | No |

### Cross-Calendar-Year Handling (Rabi)
Rabi crops in Punjab are sown in November/December of calendar year $Y$ and harvested in March/April of calendar year $Y+1$. 
- A single calendar year's data is agronomically meaningless for Rabi because it would split the winter growing season in half.
- FieldShift pairs November–December of year $Y$ with January–April of year $Y+1$ to form an intact growing season labeled `$Y–(Y+1)$`.
- If the dataset ends in December of year $Y$, the incomplete Rabi season (missing January–April) is flagged as `is_valid = False` (< 75% complete) and excluded from regression to prevent sampling distortion.

---

## 3. Data Completeness and Quality Auditing

Before calculating any historical trend, the module executes `audit_variable_coverage()`, checking every variable:

- **Temporal Coverage:** First observation date to last observation date.
- **Valid Observations:** Count of non-NaN, non-fill-value records.
- **Missing Observations:** Calendar days with missing or fill-value entries (`-999.0` converted to NaN by `PowerClient`).
- **Completeness Percentage:** $\frac{\text{Valid Days}}{\text{Total Calendar Days}} \times 100\%$.
- **Trend Suitability Rule:** A parameter is considered sufficient for linear trend estimation if and only if it has $\ge 80\%$ completeness over at least 5 years.

### Growing Season Completeness Threshold
For each annual season:
- $\text{Expected Days} = \text{Calendar days in season window}$.
- $\text{Completeness} = \frac{\text{Valid Days}}{\text{Expected Days}} \times 100\%$.
- If $\text{Completeness} < 75\%$, the season is marked `is_valid = False` with an explicit missing-data warning and is excluded from trend calculations.

---

## 4. Mathematical and Statistical Formulation

### Ordinary Least Squares (OLS) Linear Regression
For $n$ valid annual growing seasons with years $x_i$ and climate indicators $y_i$:

$$\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i, \quad \bar{y} = \frac{1}{n}\sum_{i=1}^{n} y_i$$

$$SS_{xx} = \sum_{i=1}^{n} (x_i - \bar{x})^2, \quad SS_{xy} = \sum_{i=1}^{n} (x_i - \bar{x})(y_i - \bar{y}), \quad SS_{yy} = \sum_{i=1}^{n} (y_i - \bar{y})^2$$

$$\text{Slope } \beta_1 = \frac{SS_{xy}}{SS_{xx}}, \quad \text{Intercept } \beta_0 = \bar{y} - \beta_1 \bar{x}$$

$$\text{Fitted Value } \hat{y}_i = \beta_0 + \beta_1 x_i$$

$$\text{Residual Sum of Squares } SS_{\text{res}} = \sum_{i=1}^{n} (y_i - \hat{y}_i)^2$$

$$\text{Coefficient of Determination } R^2 = 1 - \frac{SS_{\text{res}}}{SS_{yy}}$$

### Decadal Rate of Change and Total Change
$$\text{Rate of Change per Decade} = \beta_1 \times 10$$
$$\text{Total Change over Observed Span} = \beta_1 \times (x_{\max} - x_{\min})$$

### Statistical Significance (Two-Tailed Student's $t$-Test)
Degrees of freedom $df = n - 2$. The standard error of the slope is:

$$SE(\beta_1) = \sqrt{\frac{SS_{\text{res}} / (n - 2)}{SS_{xx}}}$$

$$t = \frac{\beta_1}{SE(\beta_1)}$$

$$p\text{-value} = 2 \times \int_{|t|}^{\infty} f(t; df) \, dt$$

The trend is classified as statistically significant at the standard scientific threshold $\alpha = 0.05$ if $p < 0.05$.

---

## 5. Baseline Period vs. Recent Period Comparative Analysis

To provide historical context without arbitrary assumptions:
- The time series is split at the midpoint into a **Baseline Period** ($x_{\min}$ to $x_{\text{mid}}$) and a **Recent Period** ($x_{\text{mid}} + 1$ to $x_{\max}$).
- Mean indicators are computed for each partition:
  $$\bar{y}_{\text{baseline}} = \frac{1}{n_{\text{base}}} \sum_{i \in \text{base}} y_i, \quad \bar{y}_{\text{recent}} = \frac{1}{n_{\text{recent}}} \sum_{i \in \text{recent}} y_i$$
- Absolute anomaly: $\Delta = \bar{y}_{\text{recent}} - \bar{y}_{\text{baseline}}$.
- Percentage shift: $\Delta\% = \frac{\Delta}{|\bar{y}_{\text{baseline}}|} \times 100\%$.

---

## 6. Supported Growing-Season Indicators

1. **Mean 2 m Temperature (`T2M`, °C):** Mean daily air temperature over the growing season.
2. **Average Maximum Temperature (`T2M_MAX`, °C):** Average daytime maximum temperature.
3. **Average Minimum Temperature (`T2M_MIN`, °C):** Average nighttime minimum temperature.
4. **Seasonal Precipitation Total (`PRECTOTCORR`, mm):** Cumulative sum of daily precipitation.
5. **Longest Consecutive Dry Spell (days):** Maximum consecutive days where daily precipitation $\le 1.0\text{ mm/day}$ during the growing season.
6. **Extreme Heat Days (count):** Number of days where $T_{\max} \ge 35^\circ\text{C}$.
7. **Frost Days (count):** Number of days where $T_{\min} \le 2^\circ\text{C}$.

---

## 7. Strict Scientific and Agronomic Boundaries

FieldShift enforces strict scientific boundaries on historical climate trends:

1. **Descriptive, Not Causal:**
   - A historical temperature or precipitation trend describes gridded atmospheric data over time.
   - FieldShift never claims that an observed trend proves crop yields declined, farm incomes fell, or soil organic carbon changed. Agronomic yield is multifactorial (influenced by genetics, fertilizer, management, irrigation, and pest pressure).

2. **No Future Extrapolation:**
   - Historical OLS linear regression fits past observations.
   - It is strictly forbidden to extrapolate a historical slope (e.g. the −0.78 °C/decade kharif slope in the 2000–2024 demo record) as a forecast of future Punjab weather.

3. **Gridded Context vs. In Situ Measurements:**
   - NASA POWER daily values are derived from NASA GMAO MERRA-2 and GEOS atmospheric models at approximately $0.5^\circ \times 0.625^\circ$ resolution (~50 km grid).
   - They represent regional climatology, not microclimate conditions at an individual field or canopy level.
