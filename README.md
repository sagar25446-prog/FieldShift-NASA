# 🌾 FieldShift

**Plan resilient crop rotations with evidence, NASA Earth observations, and biophysical transparency.**

FieldShift is a global decision-support web application for the NASA Space Apps Challenge 2026 challenge **"Field Shift: Adapting Farms with NASA Data."**

It combines **farmer-provided field data**, 6 core **NASA Earth Observation satellite datasets**, and source-linked regional crop catalogues to help farmers transition away from water-depleting monocultures to resilient, diversified multi-season crop rotations. FieldShift provides deterministic, biophysically grounded alternatives—not black-box yield predictions or spurious profit guarantees.

> ⚠️ **Important:** FieldShift is a decision-support prototype. It cannot guarantee crop yield, profitability, or soil improvement. Farmers should combine its outputs with local expertise, certified soil testing, and local agricultural extension guidance.

---

## ✨ Key Features & Global Capabilities

- 🌍 **Global Multi-Region Architecture** — Designed for agricultural regions worldwide:
  - 🇮🇳 **Indo-Gangetic Plain (Punjab, India):** Monsoonal subtropical (Kharif–Rabi–Summer) diversification from continuous Rice–Wheat to Maize, Pulses, and Millets.
  - 🇺🇸 **US Corn Belt (Iowa, USA):** Humid continental (Spring–Summer–Fall) transitions from continuous Corn/Soybean to Oats, Alfalfa, and Cereal Rye cover crops based on USDA-ARS Marsden Farm research.
  - 🇪🇸 **Mediterranean Basin (Andalusia, Spain):** Winter-wet / summer-dry rainfed & deficit systems rotating Durum Wheat, Garbanzo Chickpeas, and Sunflowers based on IFAPA guidelines.
  - 🇮🇳 **Semi-Arid Tropics (Maharashtra / Deccan, India):** Rainfed Vertisol systems rotating drought-hardy Sorghum (Jowar), Pigeonpea (Tur), and Chickpea based on ICRISAT research.
  - 🌐 **Global Coordinate Archetype Detection:** Enter any latitude and longitude on Earth; FieldShift automatically detects the corresponding agro-ecological zone and retrieves NASA POWER daily climate.
- 🛰️ **Comprehensive NASA Earth Observation Suite (6 Missions):**
  1. **NASA POWER (Daily Surface Reanalysis):** 40+ years of daily historical solar radiation, Tmax, Tmin, and precipitation on a global 0.5° grid.
  2. **NASA NEX-GDDP-CMIP6 (Future Climate):** High-resolution downscaled climate projections (SSP2-4.5 & SSP5-8.5, 2041–2060, 5 models) stress-testing future thermal and heat wave limits.
  3. **NASA SMAP (Soil Moisture Active Passive):** 9 km radiometer surface (0–5 cm) and root-zone (0–100 cm) volumetric water content assessing seed germination security.
  4. **NASA MODIS (MCD12Q2 & MOD13Q1):** 250m satellite phenology and NDVI tracking historical double-cropping cycles and seasonal canopy vigor.
  5. **NASA GRACE / GRACE-FO:** Gravimetric satellite measurement revealing regional groundwater mass loss (-4.0 cm/yr in NW India; Ogallala and Mediterranean depletion).
  6. **NASA FIRMS:** VIIRS/MODIS thermal anomaly monitoring identifying post-harvest residue burning windows.
- 🔄 **Deterministic Rotation Engine** — Searches documented crop compatibility graphs with hard agronomic constraints; scores candidate rotations on water suitability, climate suitability, soil-related potential, and diversity.
- 📐 **Biophysical Rigor:**
  - **FAO-56 Penman–Monteith:** Dynamic stage-interpolated crop coefficients ($K_c$) and SCS effective precipitation for net irrigation deficits.
  - **FAO EcoCrop:** Cardinal temperature envelopes and extreme anthesis heat-stress threshold alerts.
  - **Janssen (1984) SOC Model:** First-order soil organic carbon decomposition ($k = 0.025 \text{ yr}^{-1}$) and crop residue humification tracking over 3–5 year horizons.
  - **Nitrogen Dynamics:** Legume biological atmospheric $N_2$ fixation credits (Moong, Chickpea, Pigeonpea, Alfalfa, Berseem) and crop removal balances.
- 🔄 **Multi-Year Rotational Trajectory Simulation (3–5 Years)** — Simulates cumulative multi-year water consumption, soil organic carbon trajectory curves, and soil nitrogen balances.
- 💰 **Indicative Economics & Water Savings** — Computes indicative gross margins and water productivity using Government of India Minimum Support Prices (MSP 2024-25), USDA-ARS benchmarks, and university cultivation costs. Highlights headline water savings in physical units (e.g. 1,000 mm / 10,000 m³/ha saved vs monoculture).
- 🧑‍🌾 **Farmer Tubewell & Canal Water Calculator** — Converts local pumping practices (motor HP, weekly hours, canal turns) into an equivalent seasonal crop-water budget in mm.
- 💾 **Farm Profile Persistence** — Export complete farm configurations to `.json` and restore state with secure, validated file upload.
- 📄 **1-Page Printable Farmer Rotation Card** — One-click export to a clean, formatted printable HTML/PDF summary card designed for field extension workers.
- ⚖️ **Weight Sensitivity & Rank Stability Analysis** — Evaluates whether the #1 recommended plan remains stable under ±20% preference weight perturbations.
- 🗣️ **Plain-Language Explainability & Bilingual Labels** — Farmer-focused "Why recommended" summaries and bilingual crop names (English, Punjabi ਪੰਜਾਬੀ, Hindi हिंदी).
- 🏆 **Built-In Pitch Deck & Video Storyboard** — Interactive 5-slide pitch deck, 75-second video recording script, and expert agronomic validation statements embedded directly in the app.

---

## 🖥️ Live Application & Judging Quick-Start

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fieldshift-nasa.streamlit.app)

FieldShift features a **Live Judging Quick-Start** preset right on the home page:
- One click loads the Ludhiana demonstration farm and verified 2024 NASA POWER daily observations.
- Generates diverse, feasible crop rotations scored via FAO-56 and EcoCrop in < 1 second.
- Toggles between live NASA POWER API calls and a saved, unmodified 2024 POWER snapshot with automatic failure recovery.
- Instant region switching between Punjab, US Corn Belt, Mediterranean Basin, and Semi-Arid Tropics.

---

## 🏗️ Technical Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                          app.py (Streamlit entry)                       │
│                                ↓                                        │
│                         ui.py (11 pages)                                │
│       ↙          ↓            ↓             ↓              ↘            │
│  nasa_power.py  regions.py   multi_year_   climate_trends.py economics.py│
│       ↓          ↓            simulation.py        ↓              ↓     │
│  NASA POWER   4 Regional     Janssen (1984)      OLS Trends    GoI MSP /│
│  Daily API    Catalogs       SOC Kinetics       & P-Values    CACP/USDA │
└─────────────────────────────────────────────────────────────────────────┘
```

**Core Modules:**
- `src/fieldshift/regions.py` — Global multi-region registry and coordinate-based zone matcher.
- `src/fieldshift/multi_year_simulation.py` — 3- to 5-year rotational trajectory simulator for water, carbon, and nitrogen.
- `src/fieldshift/export_import.py` — Secure profile serialization and printable 1-page summary card generator.
- `src/fieldshift/satellite_context.py` — NASA GRACE, FIRMS, SMAP, GPM, and MODIS NDVI context layers and tubewell water calculator.
- `src/fieldshift/sensitivity.py` — Preference weight perturbation analysis and plain-language summary generator.
- `src/fieldshift/rotation_engine.py` — Graph search with hard agronomic constraints and Pareto multi-objective ranking.
- `src/fieldshift/fao56.py` — Penman–Monteith reference ET₀ and stage-interpolated crop coefficients ($K_c$).
- `src/fieldshift/climate_suitability.py` — FAO EcoCrop cardinal temperatures and extreme heat threshold analysis.
- `src/fieldshift/future_climate.py` — NASA NEX-GDDP-CMIP6 downscaled climate projections (SSP2-4.5 & SSP5-8.5).
- `src/fieldshift/climate_trends.py` — Multi-decadal OLS trend regression and dry-spell analysis on historical observations.
- `src/fieldshift/soil_nutrient_model.py` — Simplified FAO/IPCC nutrient and carbon balance.
- `src/fieldshift/soil_data.py` — ISRIC SoilGrids 250m REST API integration with uncertainty quantiles.
- `src/fieldshift/land_use_phenology.py` — NASA MODIS MCD12Q2 land-cover phenology dynamics.
- `src/fieldshift/ui.py` — Complete 11-page responsive Streamlit user interface with mobile CSS optimization.

---

## 🧪 Testing & Continuous Integration

FieldShift is backed by **261 automated tests** verifying every biophysical equation, API contract, graph transition, and edge case:

- **257 Passed**, 4 Skipped (optional live-network integration tests).
- Automated GitHub Actions CI workflow running on all commits and PRs (`.github/workflows/ci.yml`).
- Zero fabricated data, no yield predictions, and strict uncertainty disclosures.

```bash
# Run the test suite
python -m pytest
```

---

## 📦 Installation & Local Development

```bash
# Clone the repository
git clone https://github.com/sagar25446-prog/FieldShift-NASA.git
cd FieldShift-NASA

# Install dependencies
pip install -r requirements.txt

# Launch the Streamlit application
streamlit run app.py
```

---

## 📄 Documentation Directory

- [5-Slide Pitch Deck](docs/PITCH_DECK.md)
- [75-Second Demo Video Script](docs/DEMO_VIDEO_SCRIPT.md)
- [Agronomic & Institutional Methodology Validation](docs/EXPERT_VALIDATION.md)
- [Test Report & Automated Audit](docs/TEST_REPORT.md)
- [Known Limitations & Disclosures](docs/KNOWN_LIMITATIONS.md)
- [Submission Checklist](docs/SUBMISSION_CHECKLIST.md)
- [NASA POWER Data Guide](docs/NASA_POWER_DATA.md)
- [Climate Trends Methodology](docs/CLIMATE_TRENDS_METHODOLOGY.md)
- [Future Climate Projections](docs/FUTURE_CLIMATE.md)
- [Observed Land Use & Phenology](docs/OBSERVED_LAND_USE.md)

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
