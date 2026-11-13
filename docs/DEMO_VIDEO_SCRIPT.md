# FieldShift — demonstration scripts

Use only a current app run. Do not pre-record a fixed plan, water saving, profit, trend, or ranking and present it as a live result.

## Submission-format check

The official 2026 Project Submission Guide should determine the final video length, file host, language, and any slide rules. On 2026-11-13, the public guide URL could not be retrieved reliably, so this repository does **not** claim that a 30-second limit is confirmed. The 30-second cut below is ready if that is the published requirement; the 90-second version is for a local pitch, a fuller demonstration, or social media.

Before uploading, confirm the current guide and test the public video link in a private browser window.

## Official-submission cut — 30 seconds

| Time | Screen action | Narration |
|---|---|---|
| 0:00–0:05 | **Home / Overview**: title and globe | “Farmers face hard crop decisions as climate and water change. FieldShift helps them explore their next rotation.” |
| 0:05–0:10 | Select **Punjab**; show the **Location report** | “For a chosen location, we retrieve historical NASA POWER data with its dates, units, and source.” |
| 0:10–0:17 | **Farm Profile**, then **Rotation Recommendations** | “Farmers add soil and water details; unknown stays unknown.” |
| 0:17–0:23 | Expand **Your current rotation** and one alternative | “The app compares current and alternative rotations with documented checks, sources, and trade-offs.” |
| 0:23–0:27 | **Farmer Priorities**, then **Hypothetical stress tests** | “They set priorities and test dry or hot what-ifs—not forecasts.” |
| 0:27–0:30 | Return to the title or globe | “NASA data, local context, farmer decision.” |

## Local-pitch cut — 90 seconds

| Time | Screen action | Narration |
|---|---|---|
| 0:00–0:12 | **Home / Overview** | “Farmers must decide what to grow with uncertain water, changing temperatures, and incomplete soil information. FieldShift helps a farmer or extension worker compare crop-rotation options without hiding what is unknown.” |
| 0:12–0:25 | Globe → select **Punjab** → **Farm Profile** | “We start with a location and the information the farmer actually has: soil conditions, irrigation budget, previous crops, and priorities. A missing value remains unknown; it is never replaced with a favourable guess.” |
| 0:25–0:40 | **Climate Insights**: retrieve NASA POWER and open provenance | “For the selected location and dates, FieldShift retrieves historical NASA POWER climate context. The screen preserves the exact request, daily units, missing-data count, and source URL. This is gridded climate context, not a field weather station.” |
| 0:40–0:57 | **Rotation Recommendations**: open one plan | “The deterministic engine searches a small, source-linked crop graph. It shows the sequence, hard feasibility checks, separate water and climate methods, trade-offs, and the evidence behind each rule. The composite score is a preference-weighted comparison, never a success probability.” |
| 0:57–1:08 | **Comparison View**: current rotation and alternatives | “A farmer can compare their current rotation with distinct alternatives under the same inputs. A documented failure stays visible instead of being hidden by a high score.” |
| 1:08–1:20 | **Farmer Priorities** then **Hypothetical stress tests** | “When water conservation matters most, the farmer changes the priority weights. Then they can stress-test dry, hot, or reduced-irrigation assumptions. These are transparent what-if tests, not forecasts.” |
| 1:20–1:30 | **Data and Methods** | “FieldShift makes NASA data, local inputs, calculated indicators, and unknowns visible separately. It supports a conversation with local expertise; the farmer keeps the final decision.” |

## Recording safeguards

- Use the Punjab pilot in the primary recording; do not suggest that an arbitrary world coordinate receives a locally validated rotation plan.
- Trigger the NASA POWER request before recording. If the saved response is used, label it “Saved offline demonstration record,” not live data.
- Do not imply that an optional source changes the shown plan unless its provenance is visible in that session.
- Do not include NASA logos, a NASA endorsement claim, music, images, audio, or other third-party material unless the team has the rights to use it and cites it.
- If the final submission form requires an AI-use statement, use the factual draft in `docs/AI_USE_DISCLOSURE.md` and add any tools used by other team members.
