# FieldShift pitch outline

## 1. The challenge

Farmers weigh climate, water, soil and crop choices when planning what to grow next. The NASA Space Apps challenge asks teams to build decision support that brings those kinds of information together to explore crop rotations.

## 2. What we built

FieldShift is a Streamlit prototype. A user selects a location, reviews historical NASA POWER climate context, enters known soil and water details, chooses priorities and compares rule-based rotation plans in four pilot regions.

## 3. What the user can see

Each plan shows its crop sequence, available component scores, rule checks, trade-offs and missing inputs. A score is a comparison aid; it is not a probability of success, yield forecast, or promise of soil improvement.

## 4. How we use NASA data

NASA POWER daily temperature and precipitation are retrieved for the selected coordinate and date range. The app preserves units, dates, request URL and missing-data coverage. The data is gridded climate context, not a farm station measurement. Separate optional modules are described in the data-source documentation; they are not all inputs to each plan.

## 5. What remains

Crop calendars and rotation rules need review by qualified regional agronomists. Farmer and extension-adviser usability sessions, field calibration, and deployment verification are outstanding. Outside pilot areas, the app can provide climate context and sometimes historical crop timing, not a locally reviewed crop recommendation.

## Demo flow

1. Open Home and point out the prototype disclaimer and globe.
2. Choose the Punjab pilot and load the illustrative demo profile.
3. Review NASA POWER provenance and note the gridded-data limitation.
4. Compare two actual engine-generated plans and their checks and trade-offs.
5. Change one farmer priority and show the weights used by the planner.
6. Open Data and Methods and explain the unknown values and pending expert review.

Label demo inputs as illustrative. Use only the output shown in the current app session; do not promise particular rankings, savings or gains in advance.
