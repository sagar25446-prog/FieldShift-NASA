# FieldShift judge questions: evidence-based answers

These answers describe the current repository. They are not claims of NASA endorsement or external scientific validation.

### What problem are you addressing?

Farmers face changing climate, water availability and soil constraints when choosing crops. The NASA challenge asks for a decision-support tool combining NASA Earth observations, local soil information, crop characteristics and farmer priorities to explore rotations. FieldShift provides that workflow for four configured pilot regions.

### What NASA data does the app actually use?

NASA POWER Daily is the primary on-demand global climate source. The app records request dates, coordinates, parameter units, retrieval time and missing observations. Its temperature and precipitation values are gridded climate estimates, not measurements from a farm weather station. Other modules cover selected optional datasets, but they are not all retrieved or fused into every plan. See `docs/DATA_SOURCES.md` for current availability.

### What happens outside the pilot regions?

Users can explore coordinates and NASA POWER climate context anywhere in the supported coordinate range. Some grid cells have historical planting and harvest timing from the Sacks atlas; some have no record. Calendar timing does not check crop suitability or pest, soil and water constraints. The rule-based agronomic rotation planner is limited to the four pilot catalogues.

### How does the recommendation engine work?

For a supported pilot region, it evaluates source-linked crop and rotation rules, available farmer inputs and climate features, then presents component metrics and explanations. Missing values are not treated as zero. A score is a preference-weighted comparison, not a probability, yield prediction, or guarantee.

### What can it tell you about soil improvement or nitrogen?

It cannot establish that a rotation will improve a particular field's soil. Optional simplified soil-state calculations are educational comparisons with calibration limitations. Legume status does not imply a fixed nitrogen credit in all conditions. Soil chemistry should come from a current laboratory test or other field evidence.

### Have farmers or agronomists validated it?

No external agronomist review, representative farmer usability study, or field-trial calibration is recorded. `docs/EXPERT_VALIDATION.md` contains the review worksheet and open status. We will not present an unverified person or testimonial as endorsing the project.

### What checks have you run?

The current dated test result is in `docs/TEST_REPORT.md`. Software tests do not prove scientific accuracy or farmer benefit. Live data checks depend on internet and source availability; Streamlit deployment must be verified separately from a Git push.

### Why use rules instead of machine learning?

The initial goal is to show which inputs and documented rules influence a comparison. A black-box model would need suitable local training data and validation that this project does not have.

### What is the most important next step?

Have a qualified regional agronomist review the crop calendars, hard constraints and assumptions, then observe farmers and extension advisers using the app with a demo profile. Record findings and revise before presenting outputs as locally suitable advice.
