# 🌾 FieldShift

**Plan resilient crop rotations with evidence, NASA Earth observations, and biophysical transparency.**

FieldShift is a global decision-support web application built for the NASA Space Apps Challenge 2026 challenge **"Field Shift: Adapting Farms with NASA Data."**

It combines **farmer-provided field data**, **6 core NASA Earth Observation satellite datasets**, and source-linked regional crop catalogues to help farmers transition away from water-depleting monocultures to resilient, diversified multi-season crop rotations. FieldShift provides deterministic, biophysically grounded alternatives—not black-box yield predictions or spurious profit guarantees.

> ⚠️ **Important:** FieldShift is an explainable decision-support prototype. It cannot guarantee crop yield, profitability, or soil improvement. Farmers should combine its outputs with local expertise, certified soil testing, and local agricultural extension guidance (e.g. Krishi Vigyan Kendras / university farm advisors).

---

## 🖥️ Live Application & Judging Quick-Start

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fieldshift-nasa.streamlit.app)

**Live Demo URL:** [https://fieldshift-nasa.streamlit.app](https://fieldshift-nasa.streamlit.app)  
*(Note: If the application has been idle on Streamlit Community Cloud, please click **"Yes, get this app back up!"** — it will wake within 15–30 seconds).*

### 🌟 30-Second Demonstration Workflow for Judges:
1. **Open the Live App:** Load [fieldshift-nasa.streamlit.app](https://fieldshift-nasa.streamlit.app).
2. **One-Click Demo Farm:** Click **"🌟 Load complete demo farm & cached climate data"** on the home page.
3. **Explore Multi-Region Switching:** Use the sidebar dropdown to switch between **Punjab (India)**, **US Corn Belt (Iowa)**, **Mediterranean (Spain)**, and **Semi-Arid Tropics (Deccan)**.
4. **View Recommendations:** Navigate to **"Rotation Recommendations"** to see Pareto-optimal multi-season alternatives, physical water savings vs. continuous rice-wheat (1,000+ mm saved), FAO-56 net irrigation deficits, and 3–5 year multi-year trajectory graphs.
5. **Print Farmer Summary Card:** Expand **"Export 1-Page Printable Farmer Summary Card"** to see the clean, high-contrast, print-optimized summary ready for field distribution.

---

## 🛰️ NASA Earth Observation Data Lineage & Decision Impact Table

FieldShift does not use satellite data as decorative background graphics. Every NASA dataset feeds directly into an agronomic check, dynamic biophysical equation, or risk envelope:

| NASA Dataset / Mission | Variables Used | Spatial & Temporal Resolution | Exactly How It Drives FieldShift's Decision & Ranking |
|---|---|---|---|
| **NASA POWER** (Surface Meteorology) | `T2M`, `T2M_MAX`, `T2M_MIN`, `PRECTOTCORR`, `ALLSKY_SFC_SW_DWN`, `RH2M`, `WS2M` | 0.5° global grid; Daily (1981–present) | Directly drives **FAO-56 Penman-Monteith daily reference evapotranspiration ($ET_0$)**, stage crop coefficients ($K_c$), effective rainfall deficit, and **FAO EcoCrop thermal suitability scoring**. |
| **NASA NEX-GDDP-CMIP6** (Downscaled Projections) | Daily `tasmax`, `tasmin`, `pr` across 5 downscaled GCMs | 0.25° downscaled grid; 2041–2060 (SSP2-4.5 & SSP5-8.5) | Stresstests rotations under mid-century warming; computes thermal threshold exceedances, heat wave risks, and multi-model agreement. |
| **NASA SMAP** (L4 Soil Moisture) | Root-zone (0–100 cm) & surface (0–5 cm) volumetric moisture | 9 km grid; 3-hour / daily | Establishes root-zone moisture anomalies during planting windows; alerts farmers to germination moisture deficits for rainfed crops. |
| **NASA MODIS MCD12Q2** (Land Phenology) | Mid-Greenup, Mid-Greendown, EVI2 cycle count & QA | 500 m pixel; Annual (2016–2025) | Verifies historical multi-season vegetation cycles; transparently warns if a candidate plan adds a cropping season not seen in recent years. |
| **NASA MODIS MOD13Q1** (Vegetation Index) | 16-day Composite 250m NDVI | 250 m pixel; 16-day (2000–present) | Evaluates historical seasonal canopy vigor and provides independent phenological greenness verification. |
| **NASA GRACE / GRACE-FO** (Terrestrial Water Storage) | Gravimetric Mascon Water Storage Anomalies | ~300 km footprint; Monthly | Quantifies regional groundwater mass depletion (-4.0 cm/yr in NW India; Ogallala and Mediterranean overdraft); grounds water conservation impact metrics. |
| **NASA FIRMS** (Active Fire) | VIIRS (375m) & MODIS (1km) Thermal Anomalies | 375 m / 1 km; Near-Real-Time | Maps post-monsoon crop residue burning hotspots; informs residue retention and Happy Seeder soil organic carbon credits. |

---

## 🧑‍🌾 Farmer Persona & End-to-End User Journey

### Persona: Sardar Gurpreet Singh (Ludhiana District, Punjab)
* **Profile:** 52 years old, manages a 6-acre family farm in central Punjab.
* **The Dilemma:** Has grown continuous flooded paddy (Kharif) → wheat (Rabi) for 25 years. His submersible tubewell pump is now at 160 feet (falling 2–3 feet every year), and electricity cuts threaten his crop during peak summer. He wants to diversify into maize, moong, or mustard, but fears yield collapse, pest carryover, or running out of water.
* **How FieldShift Empowers Gurpreet:**
  1. **Enters Real Field Reality:** Uses the **Tubewell Water Helper** to enter his 10 HP motor and 25 hours/week pumping allowance $\rightarrow$ FieldShift computes his exact seasonal water capacity in mm.
  2. **Enters Soil Health Card:** Enters his Government of India Soil Health Card (pH 7.4, EC 0.35, OC 0.48%) $\rightarrow$ FieldShift sets soil context constraints.
  3. **Discovers Feasible Alternatives:** FieldShift searches PAU-documented transition graphs and presents **Maize → Wheat → Summer Moong** and **Cotton → Wheat**.
  4. **Sees Transparent Trade-Offs:** The tool shows that Maize-Wheat-Moong saves **985 mm (9.8 million litres) of water per hectare** vs. paddy-wheat, preserves comparable gross margins under MSP, and adds a biological legume nitrogen credit for the subsequent wheat crop.
  5. **Prints 1-Page Summary Card:** Gurpreet downloads a clean, printable 1-page summary card with verified sowing/harvest calendar windows to review with his local Krishi Vigyan Kendra (KVK) extension officer.
  6. **Adopts "Pilot-First":** Following FieldShift's pilot protocol, Gurpreet tests the maize-wheat-moong rotation on 1 acre (16% of his holding) in Year 1 before scaling.

---

## 🔍 Retrospective Validation: March 2022 Terminal Heatwave Hindcast

To verify scientific validity against real agricultural outcomes, FieldShift was backtested against the **March 2022 Northwest India Terminal Heatwave**:
* **The Historic Anomaly:** March 2022 was the hottest March in 122 years across northwestern India. Daily maximum temperatures reached 38°–40°C during wheat anthesis and grain-filling (dough stage), shrivelling grains and causing a 10%–15% statewide yield loss.
* **FieldShift's Blind Hindcast:** When fed genuine NASA POWER daily observations from March 2022 for the Ludhiana grid cell (30.85°N, 75.70°E), FieldShift's FAO EcoCrop thermal module identified **9 days exceeding the critical 32°C grain-filling heat threshold** and **3 days exceeding the 35°C extreme heat threshold**.
* **Outcome:** FieldShift triggered a **"Terminal Heat Risk"** tradeoff warning and penalized the late-sown wheat score. In contrast, short-duration summer pulses (moong) and diversified rotations had clear avoidance windows, proving that FieldShift's thermal models accurately detect real-world climatic risks.

---

## 🌍 Global Multi-Region Architecture ("Farmers Around the World")

FieldShift is not restricted to one geography. It implements a modular **Global Agro-Ecological Archetype System**:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Global Multi-Region Dispatch Engine                  │
├─────────────────────┬────────────────────┬─────────────────────────────┤
│ Region              │ Climate Archetype  │ Documented Cropping System  │
├─────────────────────┼────────────────────┼─────────────────────────────┤
│ 🇮🇳 Punjab, India   │ Subtropical Summer │ Rice, Wheat, Maize, Moong,  │
│    (Indo-Gangetic)  │ Monsoon (Cwa/BSh)  │ Cotton, Potato, Raya Mustard│
│ 🇺🇸 US Corn Belt     │ Humid Continental  │ Corn, Soybean, Cereal Rye,  │
│    (Iowa, USA)      │ (Dfa)              │ Oats, Perennial Alfalfa     │
│ 🇪🇸 Mediterranean    │ Mediterranean      │ Durum Wheat, Sunflower,     │
│    (Andalusia)      │ Summer-Dry (Csa)   │ Garbanzo Chickpea, Barley   │
│ 🇮🇳 Semi-Arid Tropics│ Tropical Dry       │ Sorghum (Jowar), Pigeonpea, │
│    (Deccan/Maha)    │ Vertisol (BSh)     │ Chickpea, Rainfed Soybean   │
└─────────────────────┴────────────────────┴─────────────────────────────┘
```
* **Automatic Coordinate Matching:** Enter coordinates anywhere on Earth; FieldShift calculates geographic bounds and distance heuristics to match the nearest agro-ecological archetype while querying NASA POWER on the exact field coordinates.

---

## 📱 User Interface Walkthrough & Features

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           FieldShift Architecture                       │
├─────────────────────────────────────────────────────────────────────────┤
│  [Sidebar]                 [Main Workspace (11 Interactive Pages)]     │
│  • Region Selector (4)     1. Home / Overview & NASA EO Suite Inspector │
│  • Language (EN / ਪੰਜਾਬੀ / हिंदी) 2. Farm Profile (Tubewell & SHC Helpers) │
│  • Page Navigation (11)    3. Climate Insights (Live NASA POWER ET₀)    │
│  • Provenance Status       4. Climate Trends (25-Year OLS & P-Values)   │
│  • Reset / Clear           5. Farmer Priorities (Interactive Sliders)   │
│                            6. Rotation Recommendations (Pareto Top Plan)│
│                            7. Hypothetical Stress Tests (Dry / Hot)     │
│                            8. Future Climate (NASA NEX-GDDP-CMIP6)      │
│                            9. Comparison View & Weight Sensitivity (±20%)│
│                            10. Data and Methods & 2022 Heatwave Hindcast│
│                            11. Pitch Deck, Demo Video Script & Validation│
└─────────────────────────────────────────────────────────────────────────┘
```

* 🌐 **Multilingual Interface:** English, Punjabi (ਪੰਜਾਬੀ), and Hindi (हिंदी) support for regional crop nomenclature and advisories.
* 📜 **Soil Health Card (SHC) Mode:** Direct entry of government laboratory card values (pH, EC, Organic Carbon %).
* 🗓️ **Sowing & Harvesting Calendars:** University-verified calendar windows for every crop in candidate rotations.
* 🌱 **Pilot-First Protocol Banner:** Built-in guidance advising 10%–20% acreage trials before full field conversion.
* 💾 **Persistence (JSON Export & Import):** Save and restore complete farm profiles locally with strict schema validation.
* 📄 **1-Page Printable Summary Card:** Formatted HTML/PDF export for agricultural extension workers.
* 📱 **Mobile Responsive CSS:** Media queries tailored for high-contrast viewing on mobile devices in the field.

---

## 🏛️ Agricultural Extension & KVK Deployment Pathway

FieldShift is engineered for real-world institutional adoption:
1. **Primary Delivery Channel:** Delivered through **Krishi Vigyan Kendras (KVKs)**, agricultural university extension scientists (PAU, ICAR), and **Farmer Producer Organizations (FPOs)** rather than requiring isolated smartphone usage.
2. **Offline-Capable Field Tool:** Includes bundled verified NASA POWER snapshots (`data/demo_snapshot_ludhiana_2024.json`) to operate seamlessly during rural connectivity dropouts.
3. **Physical Handouts:** Extension officers generate and print the 1-Page Summary Card during village training camps (*kisan melas*).

---

## 🧪 Automated Testing & Continuous Integration

FieldShift is backed by **261 automated tests** verifying every biophysical equation, API contract, graph transition, and edge case:

```text
======================= 257 passed, 4 skipped in 20.76s =======================
```
* **Test Suites (25 files):** Covering FAO-56 Penman-Monteith, EcoCrop thermal limits, multi-year SOC kinetics, NASA POWER API parsers, SoilGrids, MODIS phenology, and JSON persistence.
* **GitHub Actions CI:** Automated continuous integration runs on every commit and PR across Python 3.11 and 3.12 (`.github/workflows/ci.yml`).
* **Zero Fabricated Data:** Unknowns remain explicit `N/A`, and no unsupported yield or profit predictions are made.

```bash
# Run the test suite
python -m pytest
```

---

## 📦 Installation & Local Development

```bash
# 1. Clone the repository
git clone https://github.com/sagar25446-prog/FieldShift-NASA.git
cd FieldShift-NASA

# 2. Install dependencies (pinned versions)
pip install -r requirements.txt

# 3. Launch the Streamlit application
streamlit run app.py
```

---

## ⚖️ Ethics, Governance & AI Tool Disclosure

* **NASA Space Apps Challenge Rules Compliance:** Developed openly and transparently for the 2026 Space Apps Challenge.
* **AI Tool Disclosure:** AI coding assistants (Google Antigravity / Gemini) were utilized for code implementation, test generation, and documentation drafting under human architectural oversight and agronomic verification.
* **Ethics & Bias Safeguards:**
  - *No Algorithmic Black Box:* Uses auditable deterministic graph search and published biophysical equations (FAO-56, EcoCrop, Janssen SOC).
  - *Smallholder Equity:* Does not penalize smallholder farmers who lack precision soil sensors; provides graceful fallback to regional university practice packages.
  - *No Commercial Vendor Bias:* Independent of seed or chemical corporate sponsorship; all inputs link to public university guidelines.

---

## 📄 Documentation Directory

- [Judge Defense Q&A Dossier (10 Judge Questions)](docs/JUDGE_QA.md)
- [Rotation Engine & Decision Architecture](docs/ROTATION_ENGINE.md)
- [Challenge Requirements Point-by-Point](docs/CHALLENGE_REQUIREMENTS.md)
- [5-Slide Pitch Deck](docs/PITCH_DECK.md)
- [75-Second Demo Video Script](docs/DEMO_VIDEO_SCRIPT.md)
- [Agronomic & Institutional Methodology Validation](docs/EXPERT_VALIDATION.md)
- [Test Report & Automated Audit (266 Tests)](docs/TEST_REPORT.md)
- [Known Limitations & Disclosures](docs/KNOWN_LIMITATIONS.md)
- [Submission Checklist](docs/SUBMISSION_CHECKLIST.md)
- [NASA POWER Data Guide](docs/NASA_POWER_DATA.md)
- [Climate Trends Methodology](docs/CLIMATE_TRENDS_METHODOLOGY.md)
- [Future Climate Projections](docs/FUTURE_CLIMATE.md)
- [Observed Land Use & Phenology](docs/OBSERVED_LAND_USE.md)

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
