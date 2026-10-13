# Challenge Requirements — Field Shift: Adapting Farms with NASA Data

**Challenge URL:** <https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/>  
**Categories:** Advanced, Intermediate  
**Skills:** Arts & Multimedia, Earth Science, Software  
**Last verified:** 2026-10-14  
**Project Repository:** <https://github.com/sagar25446-prog/FieldShift-NASA>  
**Live Application:** <https://fieldshift-nasa.streamlit.app>

---

## Official Challenge Description

> Farmers around the world navigate shifting temperatures, changing rainfall patterns, water shortages, extreme weather, and declining soil health. These pressures make it difficult to choose crop rotations that protect fields, conserve water, and support long‑term resilience. Your challenge is to create a decision‑support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions.

---

## How FieldShift Addresses Each Challenge Requirement

| Challenge Requirement | FieldShift Implementation & Solution | Scientific & Technological Provenance | Verification Status |
|---|---|---|---|
| **"Farmers around the world"** | **Global Multi-Region Architecture:** 4 diverse agricultural archetypes: Indo-Gangetic Plain (Punjab, India), US Corn Belt (Iowa, USA), Mediterranean Basin (Andalusia, Spain), and Semi-Arid Tropics (Deccan, India). Includes automatic coordinate-based agro-ecological zone detection for any location on Earth. | Modular regional crop catalogues (`data/regions/*_crops.json`) and transition rules (`data/regions/*_rules.json`) grounded in PAU, USDA-ARS, IFAPA, and ICRISAT. | ✅ Fully Operational |
| **"NASA Earth observations"** | **Fuses 6 NASA Earth Observation Missions:**<br>1. **NASA POWER:** 40+ years daily surface solar radiation, Tmax, Tmin, precip on global 0.5° grid.<br>2. **NASA NEX-GDDP-CMIP6:** Downscaled 0.25° climate projections (2041–2060, SSP2-4.5 & SSP5-8.5, 5 models).<br>3. **NASA SMAP:** 9 km root-zone (0–100 cm) and surface soil moisture anomalies.<br>4. **NASA MODIS MCD12Q2 & MOD13Q1:** 500 m phenology and 250 m NDVI seasonal greenness.<br>5. **NASA GRACE / GRACE-FO:** Gravimetric regional groundwater depletion rates.<br>6. **NASA FIRMS:** VIIRS/MODIS post-harvest thermal active fire detection. | NASA Langley ASDC, NASA Earthdata, ORNL DAAC, LP DAAC, and PO.DAAC public APIs. Full URL request provenance preserved. | ✅ Fully Operational |
| **"Local soil information"** | **Flexible Multi-Tiered Soil Profiling:**<br>• Farmer/lab-entered: texture, pH, EC, organic carbon %, total nitrogen, waterlogging, drainage.<br>• **Soil Health Card (SHC) Mode:** Quick entry matching Government of India Soil Health Cards.<br>• **ISRIC SoilGrids 2.0 (250m):** Global modelled soil estimates with 90% uncertainty quantiles as an optional fallback when field tests are unavailable (farmer tests strictly take precedence). | Strict source hierarchy: Field/Lab measurements > SoilGrids estimates. No synthetic soil chemistry fabricated. | ✅ Fully Operational |
| **"Crop characteristics"** | **Source-Linked Multi-Region Crop Catalogues:** Documented water requirements (GoI Annexure AS110, FAO-56), cardinal thermal envelopes (FAO EcoCrop), crop families, legume status, and university Packages of Practices. | Every crop parameter references public, verifiable institutional sources with direct HTTPS links. | ✅ Fully Operational |
| **"Farmer priorities"** | **Interactive Preference Optimization:** Adjustable weight sliders for water suitability, climate thermal suitability, soil-related potential, rotation diversity, and indicative economic potential. | Normalizes weights to sum to 1.0; evaluates rank stability under ±20% preference perturbations. | ✅ Fully Operational |
| **"Explore rotation strategies"** | **Deterministic Graph Traversal Engine:** Explores documented crop-to-crop compatibility graphs with hard constraints (e.g. waterlogging blocks wheat, pest history avoidance). Ranks non-dominated candidate sequences on a Pareto frontier. | Transparent graph DFS; high composite scores cannot override hard agronomic failures. | ✅ Fully Operational |
| **"Strengthen soil health"** | **Soil Organic Carbon & Nutrient Dynamics:**<br>• **Janssen (1984) SOC Model:** First-order decomposition kinetics ($k=0.025\text{ yr}^{-1}$, $h=0.18$) tracking humus formation over 3–5 year horizons.<br>• **Nitrogen Budgeting:** Legume biological atmospheric $N_2$ fixation credits (Moong, Chickpea, Alfalfa, Pigeonpea) offsetting synthetic fertilizer demand. | Published FAO and IPCC biophysical equations. Uncalibrated status and educational comparison boundaries disclosed. | ✅ Fully Operational |
| **"Adapt to changing conditions"** | **Scenario Stress-Testing & Climate Projections:**<br>• User-defined hypothetical stress tests: severe dry (−precip), extreme hot (+temp), and reduced pumping budget.<br>• Mid-century warming projections using NASA NEX-GDDP-CMIP6 downscaled models.<br>• Retrospective validation: Verified against March 2022 Northwest India terminal heatwave. | Clean boundary separation: historical observations, downscaled climate models, and hypothetical stress tests are never conflated. | ✅ Fully Operational |

---

## What FieldShift Does NOT Do (Strict Scientific Boundaries)

To preserve scientific rigor and avoid misleading vulnerable smallholders, FieldShift maintains strict boundaries:
- ❌ **No black-box ML predictions:** Uses deterministic, verifiable biophysical equations rather than opaque neural networks.
- ❌ **No fabricated yield or profit guarantees:** Economic figures represent indicative GoI MSP (2024–25) and PAU/USDA cost-of-cultivation benchmarks for comparison only.
- ❌ **No remote soil chemistry claims:** Does not claim to measure nitrogen, phosphorus, or pH from space; remote sensors cannot measure root-zone chemistry without ground truth.
- ❌ **No fake confidence percentages:** Missing data is explicitly displayed as `N/A`, avoiding spurious probabilistic precision.

---

## Verification & Automated Test Status

- **Automated Tests:** 266 total test cases across 26 test files.
- **Pass Rate:** 262 passed, 4 skipped (live-network integration tests).
- **Continuous Integration:** Automated GitHub Actions pipeline running on Python 3.11 and 3.12 (`.github/workflows/ci.yml`).
- **Codebase Integrity:** MIT License, clean architecture separating engine logic from Streamlit presentation.
