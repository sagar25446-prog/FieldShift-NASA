import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = process.cwd();
const skillDir =
  "C:\\Users\\Sagar Jain\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1112.11217\\skills\\presentations";
const runtimePython =
  "C:\\Program Files\\WindowsApps\\OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt\\dependencies\\python\\python.exe";
const buildDir = path.join(workspaceDir, ".submission-build");
const finalPptx = path.join(
  workspaceDir,
  "submission",
  "FieldShift_Project_Demo_Deck.pptx",
);

const c = {
  ink: "#082B27",
  deep: "#052235",
  cream: "#F7F5ED",
  moss: "#DDE9DA",
  sage: "#9AB8A8",
  lime: "#D9EF79",
  sun: "#F2BE45",
  blue: "#78B8D4",
  muted: "#557069",
  white: "#FFFFFF",
};

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function imageBlob(relativePath) {
  const bytes = await fs.readFile(path.join(workspaceDir, relativePath));
  return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
}

function addText(slide, text, left, top, width, height, {
  size = 22,
  color = c.ink,
  bold = false,
  italic = false,
  align = "left",
  font = "Arial",
} = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left, top, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    fontFamily: font,
    fontSize: size,
    color,
    bold,
    italic,
    align,
    verticalAlignment: "middle",
  };
  return shape;
}

function addPageMark(slide, page, tone = c.muted) {
  addText(slide, `FIELD SHIFT  /  ${String(page).padStart(2, "0")}`, 72, 674, 250, 20, {
    size: 10,
    color: tone,
    bold: true,
  });
}

async function addImage(slide, relativePath, position, alt) {
  slide.images.add({
    blob: await imageBlob(relativePath),
    contentType: "image/png",
    alt,
    fit: "cover",
    position,
    geometry: "rect",
  });
}

function note(slide, sourceText) {
  slide.speakerNotes.text = sourceText;
}

async function main() {
  await fs.mkdir(buildDir, { recursive: true });
  await fs.mkdir(path.dirname(finalPptx), { recursive: true });

  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });

  // 1. Title
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.ink;
    addText(slide, "NASA SPACE APPS CHALLENGE 2026", 74, 72, 470, 28, {
      size: 13,
      color: c.lime,
      bold: true,
    });
    addText(slide, "FieldShift", 72, 173, 850, 96, {
      size: 72,
      color: c.cream,
      bold: true,
    });
    addText(
      slide,
      "An explainable crop-rotation decision-support prototype",
      77,
      290,
      650,
      56,
      { size: 28, color: c.sage },
    );
    addText(
      slide,
      "Field Shift: Adapting Farms with NASA Data",
      77,
      385,
      650,
      34,
      { size: 20, color: c.cream },
    );
    addText(
      slide,
      "Team roster: add the official team name and all registered members before publishing",
      77,
      596,
      860,
      32,
      { size: 14, color: c.sage, italic: true },
    );
    addPageMark(slide, 1, c.sage);
    note(
      slide,
      "Sources: NASA Space Apps 2026 challenge statement; project title and scope: docs/PROJECT_SUBMISSION_CONTENT.md. Before publishing, replace the roster note with the official team name and all registered member names.",
    );
  }

  // 2. Challenge
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.cream;
    addText(slide, "The farming decision", 72, 66, 520, 56, {
      size: 42,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "A crop rotation depends on climate history, available water, soil conditions, and what was grown before.",
      76,
      160,
      450,
      138,
      { size: 27, color: c.ink },
    );
    addText(
      slide,
      "Farmers need a way to examine those factors together without hiding missing information behind one opaque recommendation.",
      76,
      340,
      430,
      140,
      { size: 20, color: c.muted },
    );
    await addImage(
      slide,
      "outputs/atlas-desktop.png",
      { left: 585, top: 88, width: 617, height: 510 },
      "FieldShift Atlas showing a world map and selectable pilot regions",
    );
    addText(slide, "A location starts the conversation", 587, 618, 530, 28, {
      size: 15,
      color: c.muted,
      italic: true,
    });
    addPageMark(slide, 2);
    note(
      slide,
      "Sources: Field Shift challenge statement. Screenshot: FieldShift live application, captured by the team. The screenshot shows the Atlas entry point; only supported pilot catalogues offer documented regional rotation rules.",
    );
  }

  // 3. Farmer inputs
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.moss;
    addText(slide, "Farm context stays with the farmer", 72, 64, 630, 56, {
      size: 41,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "The workflow begins with a location, soil and irrigation information, previous crops, and the farmer’s priorities.",
      76,
      158,
      550,
      92,
      { size: 24, color: c.ink },
    );
    addText(
      slide,
      "If a soil value is unavailable, FieldShift keeps it visible as unknown. The tool explains how that missing information limits the comparison.",
      76,
      290,
      550,
      114,
      { size: 20, color: c.muted },
    );
    addText(
      slide,
      "The farmer chooses the final plan with local advice.",
      76,
      505,
      540,
      54,
      { size: 25, color: c.ink, bold: true },
    );
    await addImage(
      slide,
      "outputs/live-deployment-status.png",
      { left: 688, top: 105, width: 518, height: 510 },
      "FieldShift Atlas interface with a selected world location",
    );
    addPageMark(slide, 3);
    note(
      slide,
      "Sources: FieldShift Farm Profile design and docs/ROTATION_ENGINE.md. Screenshot: FieldShift live application, captured by the team. Illustrative values in the product are not farmer measurements.",
    );
  }

  // 4. NASA data
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.deep;
    addText(slide, "NASA climate context", 72, 64, 600, 58, {
      size: 42,
      color: c.cream,
      bold: true,
    });
    addText(
      slide,
      "NASA POWER Daily API provides historical climate context for the selected point and date range.",
      76,
      163,
      910,
      54,
      { size: 25, color: c.sage },
    );
    addText(slide, "Temperature", 76, 298, 260, 38, {
      size: 27,
      color: c.lime,
      bold: true,
    });
    addText(slide, "Precipitation", 390, 298, 260, 38, {
      size: 27,
      color: c.lime,
      bold: true,
    });
    addText(slide, "Solar radiation", 704, 298, 300, 38, {
      size: 27,
      color: c.lime,
      bold: true,
    });
    addText(slide, "Humidity and wind", 76, 354, 310, 38, {
      size: 27,
      color: c.lime,
      bold: true,
    });
    addText(
      slide,
      "The app preserves the date range, units, exact request URL, retrieval time, and missing-observation information.",
      76,
      456,
      860,
      56,
      { size: 22, color: c.cream },
    );
    addText(
      slide,
      "Gridded historical climate context does not replace a field sensor, soil test, or forecast.",
      76,
      546,
      920,
      42,
      { size: 20, color: c.blue, italic: true },
    );
    addPageMark(slide, 4, c.sage);
    note(
      slide,
      "Primary source: NASA POWER Daily API documentation, https://power.larc.nasa.gov/docs/services/api/temporal/daily/. Data provenance and parameter documentation: docs/NASA_POWER_DATA.md and docs/DATA_SOURCES.md.",
    );
  }

  // 5. Rules and comparison
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.cream;
    addText(slide, "Explainable rotation comparison", 72, 65, 720, 56, {
      size: 41,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "A deterministic engine searches a source-linked crop catalogue. It excludes sequences that break known hard rotation rules.",
      76,
      160,
      460,
      112,
      { size: 22, color: c.ink },
    );
    addText(
      slide,
      "Every candidate keeps its feasibility checks, water and climate context, soil-related potential, diversity, trade-offs, and unknowns visible.",
      76,
      322,
      460,
      122,
      { size: 20, color: c.muted },
    );
    addText(
      slide,
      "A combined score reflects editable priorities. It does not predict success.",
      76,
      523,
      440,
      54,
      { size: 19, color: c.ink, bold: true },
    );
    await addImage(
      slide,
      "outputs/live-comparison.png",
      { left: 590, top: 112, width: 615, height: 467 },
      "FieldShift comparison screen showing the current rotation fields",
    );
    addPageMark(slide, 5);
    note(
      slide,
      "Sources: FieldShift rotation engine, docs/ROTATION_ENGINE.md; crop catalogue sources, data/crops.json and docs/AGRONOMIC_ASSUMPTIONS.md. Screenshot: FieldShift live application, captured by the team.",
    );
  }

  // 6. Uncertainty
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.moss;
    addText(slide, "Stress tests and uncertainty", 72, 64, 680, 58, {
      size: 42,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "Dry, hot, and reduced-irrigation views change the historical inputs in a visible way.",
      76,
      158,
      840,
      50,
      { size: 25, color: c.ink },
    );
    addText(
      slide,
      "They are hypothetical stress tests. They do not forecast a coming season.",
      76,
      220,
      730,
      46,
      { size: 21, color: c.muted, italic: true },
    );
    addText(slide, "Data coverage", 77, 347, 280, 38, {
      size: 27,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "Missing soil measurements and incomplete climate records",
      77,
      395,
      290,
      78,
      { size: 18, color: c.muted },
    );
    addText(slide, "Model limits", 458, 347, 280, 38, {
      size: 27,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "Coarse spatial resolution and simplified agronomic rules",
      458,
      395,
      290,
      78,
      { size: 18, color: c.muted },
    );
    addText(slide, "Scenario limits", 840, 347, 290, 38, {
      size: 27,
      color: c.ink,
      bold: true,
    });
    addText(
      slide,
      "The result changes when the assumed stress changes",
      840,
      395,
      285,
      78,
      { size: 18, color: c.muted },
    );
    addText(
      slide,
      "The uncertainty is part of the decision, not an afterthought.",
      76,
      550,
      850,
      46,
      { size: 24, color: c.ink, bold: true },
    );
    addPageMark(slide, 6);
    note(
      slide,
      "Sources: docs/SCENARIOS_AND_UNCERTAINTY.md and docs/KNOWN_LIMITATIONS.md. Scenario transforms are hypothetical and are not climate forecasts.",
    );
  }

  // 7. Impact and close
  {
    const slide = presentation.slides.add();
    slide.background.fill = c.ink;
    addText(slide, "FieldShift", 72, 70, 520, 68, {
      size: 52,
      color: c.cream,
      bold: true,
    });
    addText(
      slide,
      "A farmer can explore realistic rotation questions with climate context, evidence, and uncertainty in view.",
      77,
      191,
      850,
      104,
      { size: 31, color: c.sage },
    );
    addText(
      slide,
      "FieldShift supports the conversation. The farmer makes the final choice with local expertise.",
      77,
      352,
      810,
      64,
      { size: 22, color: c.cream },
    );
    addText(slide, "Live project", 77, 500, 240, 30, {
      size: 15,
      color: c.lime,
      bold: true,
    });
    addText(slide, "fieldshift-nasa.streamlit.app", 77, 538, 620, 42, {
      size: 27,
      color: c.cream,
      bold: true,
    });
    addText(
      slide,
      "Data and methods: github.com/sagar25446-prog/Nasa-Hacakathon",
      77,
      596,
      900,
      26,
      { size: 14, color: c.sage },
    );
    addPageMark(slide, 7, c.sage);
    note(
      slide,
      "Sources: live project https://fieldshift-nasa.streamlit.app/; source and complete references https://github.com/sagar25446-prog/Nasa-Hacakathon. FieldShift is a decision-support prototype and does not provide farm-specific guarantees.",
    );
  }

  for (const [index, slide] of presentation.slides.items.entries()) {
    await writeBlob(
      path.join(buildDir, `slide-${String(index + 1).padStart(2, "0")}.png`),
      await presentation.export({ slide, format: "png", scale: 1 }),
    );
  }

  const { finalizePresentation } = await import(
    pathToFileURL(
      path.join(skillDir, "container_tools", "artifact_tool_utils.mjs"),
    ).href,
  );
  const candidatePath = path.join(buildDir, "candidate.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  await finalizePresentation({
    explicitTotalSlideCount: 7,
    requiredNativeTableOwnerSlides: [],
    workspaceDir,
    candidatePath,
    finalPath: finalPptx,
    pythonExecutable: runtimePython,
    integrityValidatorPath: path.join(
      skillDir,
      "container_tools",
      "inspect_presentation_package_integrity.py",
    ),
    layoutValidatorPath: path.join(
      skillDir,
      "container_tools",
      "inspect_presentation_layout_geometry.py",
    ),
    layoutArgs: [
      "--expected-slide-size-emu",
      "12192000,6858000",
      "--validate-bullet-geometry",
      "--validate-heading-fit",
    ],
    fontPolicy: { basis: "design", families: ["Arial"] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(buildDir, "FieldShift_Project_Demo_Deck.validation.json"),
  });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
