# Rule-Based Rotation Engine & Biophysical Decision Architecture

## 1. Scope, Multi-Region Evidence & Crop Compatibility Graph

FieldShift's engine uses a deterministic graph search coupled with rigorous biophysical models (FAO-56, FAO EcoCrop, Janssen SOC) to evaluate sustainable crop rotations.

### 1.1 Complete Crop Reachability
- The default Punjab catalogue features **10 crops connected by 19 PAU-documented transition edges** (Package of Practices for Kharif & Rabi 2026).
- Every single crop—including Pearl Millet (*Bajra*) and Rapeseed/Mustard (*Raya*)—is reachable in documented, feasible rotations (e.g. `pearl_millet → wheat → moong`, `pearl_millet → rapeseed_mustard → moong`, `maize → rapeseed_mustard → moong`).
- An absent relationship represents an unsupported edge in regional university practice guides, not an agronomic impossibility.

### 1.2 Global Multi-Region Dispatch Engine
FieldShift includes native support for 4 major global agricultural systems:
1. **Indo-Gangetic Plain (Punjab, India):** Rice, Wheat, Maize, Moong, Cotton, Potato, Raya Mustard, Chickpea, Pearl Millet.
2. **US Corn Belt (Iowa, USA):** Field Corn, Soybean, Cereal Rye cover crop, Spring Oats, Perennial Alfalfa (USDA-ARS Marsden trials).
3. **Mediterranean Basin (Andalusia, Spain):** Durum Wheat, Sunflower, Chickpea, Winter Barley (IFAPA guidelines).
4. **Semi-Arid Tropics (Deccan / Maharashtra, India):** Sorghum (*Jowar*), Pigeonpea (*Tur*), Chickpea, Rainfed Soybean (ICRISAT guidelines).
- Global coordinate bounding and distance heuristics automatically detect the agro-ecological archetype for any point on Earth.

---

## 2. Decision Metrics & Scoring Logic

All numeric metrics are normalized to 0.0–1.0. When candidate metrics are evaluated, the composite score applies normalized farmer priority weights:

$$Composite = \sum_{i \in \text{Available}} w'_i \times \text{Score}_i, \quad w'_i = \frac{w_i}{\sum_{j \in \text{Available}} w_j}$$

| Metric | Primary Scientific Method | How NASA Data Drives Decision | Availability & Status |
|---|---|---|---|
| **Water Suitability** | **FAO-56 Penman–Monteith Reference $ET_0$ & Stage $K_c$:** Computes daily reference evapotranspiration from NASA POWER solar radiation, temperature, humidity, and wind speed. Integrates dynamic crop growth stages ($ET_c = K_c \times ET_0$) and USDA SCS effective rainfall ($P_{\text{eff}}$). Net irrigation deficit ($NIR = \max(0, \sum ET_c - P_{\text{eff}})$) is evaluated against available water capacity. | **Direct Driver:** Uses daily NASA POWER solar radiation, humidity, wind, and rainfall. A drier/wetter climate record directly shifts the deficit and inverts rotation water rankings. | ✅ Active & Primary |
| **Climate Suitability** | **FAO EcoCrop Thermal Boundaries & Extreme Heat Alerts:** Evaluates daily mean temperatures against cardinal limits ($T_{\min,\text{abs}}, T_{\min,\text{opt}}, T_{\max,\text{opt}}, T_{\max,\text{abs}}$) via piece-wise linear response. Penalizes extreme heat days during critical reproductive windows (e.g. $>32^\circ\text{C}$ terminal heat for wheat anthesis). | **Direct Driver:** Uses daily NASA POWER $T_{\max}$ and $T_{\min}$. An extreme heatwave in the historical climate series penalizes thermal suitability and triggers heat-stress alerts. | ✅ Active & Primary |
| **Soil-Related Potential** | **Empirical University Soil Constraints:** Evaluates documented soil constraints (drainage, alkalinity, waterlogging sensitivity). Optional ISRIC SoilGrids 250 m estimates provide baseline texture/pH where field data is absent. | **Guiding Constraint:** Farmer/laboratory measurements strictly override remote estimates. Hard constraints (waterlogging blocks wheat/bajra) trigger immediate plan disqualification. | ✅ Active |
| **Rotation Diversity** | **Ecological Functional Diversity:** Evaluates unique botanical crop families, root depth alternation, and presence of an atmospheric $N_2$-fixing legume per cycle. | **Composition Indicator:** Promotes pest/disease interruption and soil microbial diversification. | ✅ Active |
| **Economic Potential & Water Productivity** | **Official Government Minimum Support Prices (MSP 2024–25) & University Costs:** Indicative gross revenue, operating cultivation costs, gross margin (₹/ha or \$/ha), and water productivity ($₹/m^3$ of irrigation water). | **Economic Benchmarking:** Compares candidate rotations against the regional monoculture baseline (e.g. continuous flooded rice-wheat), highlighting water saved ($m^3/\text{ha}$) and margin differences. | ✅ Active (Indicative Benchmark) |

---

## 3. How NASA Earth Observations Decisively Drive Decisions

If NASA data is removed, FieldShift cannot function as intended:
1. **Evapotranspiration & Deficit:** Without NASA POWER radiation, humidity, and temperature, FAO-56 Penman-Monteith reference $ET_0$ and crop water deficits cannot be computed.
2. **Thermal Stress & Grain Sterility:** Without NASA POWER daily $T_{\max}$ and $T_{\min}$, FAO EcoCrop thermal suitability and extreme anthesis heat-stress days cannot be identified.
3. **Multi-Year Stress Robustness:** Without NASA historical daily records, rotation performance under dry years (e.g. 20th percentile precipitation) vs. wet monsoon seasons cannot be simulated.
4. **Historical Land Use Verification:** Without NASA MODIS MCD12Q2 500 m phenology, the tool cannot verify whether an added cropping season is consistent with recent 10-year vegetation cycles.
5. **Future Mid-Century Projections:** Without NASA NEX-GDDP-CMIP6 downscaled models, rotations cannot be stress-tested against 2041–2060 warming scenarios (SSP2-4.5 and SSP5-8.5).

---

## 4. Hard Constraints vs. Soft Preferences

FieldShift strictly enforces agronomic safety over statistical optimization:
- **Hard Constraints (Immediate Failure):**
  - Planned crop outside its catalogued growing season.
  - Crop blocked by farmer-entered pest/disease avoidance restriction.
  - Crop planted in waterlogged soil when documented as sensitive (e.g. Wheat, Pearl Millet).
  - Crop planted in highly deteriorated alkaline soil when contraindicated.
  - Candidate sequence not documented in regional university compatibility rules.
- **Safeguard:** A high composite score or strong water score **CANNOT bypass or rescue a hard constraint failure**. If any check fails, the plan status is strictly marked as `infeasible` and excluded from recommendations.

---

## 5. Multi-Year Rotational Trajectory Simulation (3–5 Years)

FieldShift extends beyond single-season planning to simulate 3-year and 5-year multi-year cumulative impacts:
1. **Cumulative Water Savings:** Calculates physical groundwater conserved ($m^3/\text{ha}$ and million litres/ha) vs. regional continuous monoculture baselines.
2. **Discrete Janssen (1984) SOC Model:** Tracks soil organic carbon formation and decomposition kinetics:
   $$k = 0.025 \text{ yr}^{-1}, \quad h = 0.18$$
   Simulates humus accumulation trajectories based on crop residue retention.
3. **Biological Nitrogen Dynamics:** Quantifies biological atmospheric $N_2$ fixation credits from grain and forage legumes (Summer Moong, Chickpea, Pigeonpea, Alfalfa) to offset synthetic fertilizer applications in subsequent cereal crops.
