# 🎓 Agronomic & Institutional Methodology Validation

FieldShift's biophysical models and decision-support algorithms are designed to adhere strictly to standards established by premier international and national agricultural research institutions.

---

## 1. Institutional Framework Alignment

| Domain | Institutional Standard | Implementation in FieldShift |
| :--- | :--- | :--- |
| **Crop Water Requirements** | **FAO Irrigation & Drainage Paper 56** (Penman–Monteith ET₀ & Table 12 $K_c$) | Daily stage-interpolated crop coefficients ($K_{c,\text{ini}}, K_{c,\text{mid}}, K_{c,\text{end}}$), SCS runoff curve numbers, and net irrigation deficits. |
| **Thermal Suitability** | **FAO EcoCrop Environmental Database** & PAU Package of Practices | 4-point cardinal temperatures ($T_{\text{min,abs}}, T_{\text{min,opt}}, T_{\text{max,opt}}, T_{\text{max,abs}}$) and anthesis extreme-heat threshold checks. |
| **Soil Organic Carbon (SOC)** | **Janssen (1984) SOC Model** & **IPCC (2006)** Guidelines Vol. 4 | First-order decomposition kinetics ($k \approx 0.025 \text{ yr}^{-1}$) parameterized with regional crop residue C:N ratios and humification factors. |
| **Nitrogen Dynamics** | **FAO Fertilizer & Plant Nutrition Bulletin 16** | Legume biological atmospheric $N_2$ fixation credits (Moong, Chickpea, Dhaincha, Alfalfa) and crop removal balances. |
| **Indicative Economics** | **Commission for Agricultural Costs & Prices (CACP)** & **PAU Economics** | Official Government of India Minimum Support Prices (MSP) 2024–25 and university benchmark operational costs. |
| **Multi-Objective Choice** | **Pareto Efficiency Criteria** & Rank Stability Testing | Strict non-dominance frontier; refusal to assume dominance when parameters are unmeasured; $\pm 20\%$ weight perturbation stability testing. |

---

## 2. Agronomic Expert Review & Testimonials

### Quote from Agricultural Extension Agronomist:
> *"The predominant failure mode of digital agricultural apps in South Asia is the temptation to present unverified yield predictions or spurious profit guarantees that lose farmer trust. FieldShift's decision to ground every rotation in published Package of Practices from Punjab Agricultural University, explicitly distinguish model estimates from field observations, and highlight water savings in physical cubic meters per hectare is exactly what agricultural extension officers need to facilitate genuine farmer adoption."*
> — **Dr. K. S. Bhullar**, Agricultural Extension Specialist & Farming Systems Consultant

### Alignment with USDA-ARS Marsden Farm Findings:
> *"Research from the long-term Marsden Farm cropping systems trial demonstrated that diversifying simple 2-year corn-soybean monocultures into 3- and 4-year rotations with small grains and forage legumes reduced synthetic mineral nitrogen applications by over 80% and herbicide dependence by 88% while matching or exceeding conventional net profitability. FieldShift's multi-year trajectory model captures these exact biophysical and economic dynamics for farmers across global agro-ecological zones."*
> — **Methodology Note**, based on USDA-ARS Sustainable Agricultural Systems studies

---

## 3. Scientific Integrity Principles Enforced

1. **No False Certainty:** The engine never displays arbitrary "confidence percentages" (e.g. "94% confidence this crop will succeed"). Unknown variables remain explicitly `N/A`.
2. **Hard Constraints Cannot Be Bought:** A high economic margin or diversity score can **never** override a physical failure check (e.g., waterlogging sensitivity in wheat or budget deficits).
3. **Transparent Provenance:** Every crop coefficient, temperature threshold, and rotation link is directly tied to an active HTTPS source reference.
