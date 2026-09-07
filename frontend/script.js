/* =========================================================================
   EXAMIX AI — frontend logic
   Flow: UPLOAD -> OCR -> CONCEPTS -> SELECT -> TYPE -> NUMBER -> GENERATE -> ANSWERS
   ========================================================================= */

const state = {
  file: null,
  allConcepts: [],
  detectedConcepts: [],
  selectedConcepts: new Set(),
  questionType: null,
  numQuestions: null,
  demoMode: false,
  questions: [],
  selfCheck: {}, // { [questionIndex]: true | false }
};

// ---- element refs ---------------------------------------------------------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const dropzoneFile = document.getElementById("dropzoneFile");
const analyzeBtn = document.getElementById("analyzeBtn");
const demoBtn = document.getElementById("demoBtn");
const uploadStatus = document.getElementById("uploadStatus");

const stepUpload = document.getElementById("step-upload");
const stepConcepts = document.getElementById("step-concepts");
const stepOptions = document.getElementById("step-options");
const stepPaper = document.getElementById("step-paper");
const allSteps = [stepUpload, stepConcepts, stepOptions, stepPaper];

const conceptGrid = document.getElementById("conceptGrid");
const toOptionsBtn = document.getElementById("toOptionsBtn");
const conceptStatus = document.getElementById("conceptStatus");

const typeGroup = document.getElementById("typeGroup");
const countGroup = document.getElementById("countGroup");
const generateBtn = document.getElementById("generateBtn");
const generateStatus = document.getElementById("generateStatus");

const paperContainer = document.getElementById("paperContainer");
const printRoot = document.getElementById("printRoot");

const themeToggle = document.getElementById("themeToggle");
const stepperItems = document.querySelectorAll(".stepper__item");
const stepperLines = document.querySelectorAll(".stepper__line");

// ---- theme toggle -----------------------------------------------------------
themeToggle.addEventListener("click", () => {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("examix-theme", "light");
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("examix-theme", "dark");
  }
});

// ---- helpers ---------------------------------------------------------------
function setStatus(el, message, kind) {
  el.textContent = message || "";
  el.className = "status" + (kind ? ` status--${kind}` : "");
}

function updateStepper(activeStepNum) {
  stepperItems.forEach((item) => {
    const n = parseInt(item.dataset.stepper, 10);
    item.classList.remove("is-active", "is-done");
    if (n === activeStepNum) item.classList.add("is-active");
    else if (n < activeStepNum) item.classList.add("is-done");
  });
  stepperLines.forEach((line, i) => {
    line.classList.toggle("is-done", i + 1 < activeStepNum);
  });
}

function showStep(step) {
  allSteps.forEach((s) => {
    if (s !== step) s.classList.add("step--hidden");
  });

  step.classList.remove("step--hidden");
  step.classList.add("step--entering");
  // Force layout so the browser registers the "entering" state before we
  // transition it away, giving a small fade+slide-in on every step change.
  void step.offsetWidth;
  requestAnimationFrame(() => step.classList.remove("step--entering"));

  updateStepper(parseInt(step.dataset.step, 10));
  step.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---- initial state ---------------------------------------------------------
updateStepper(1);
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") fileInput.click();
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dropzone--drag");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dropzone--drag");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelected(file);
});
fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) handleFileSelected(file);
});

function handleFileSelected(file) {
  const validExt = /\.(pdf|jpg|jpeg|png)$/i;
  if (!validExt.test(file.name)) {
    setStatus(uploadStatus, "Please choose a PDF, JPG, JPEG, or PNG file.", "error");
    return;
  }
  state.file = file;
  dropzoneFile.textContent = `Selected: ${file.name}`;
  analyzeBtn.disabled = false;
  setStatus(uploadStatus, "", null);
}

analyzeBtn.addEventListener("click", async () => {
  if (!state.file) return;
  analyzeBtn.disabled = true;
  setStatus(uploadStatus, "Reading your paper and identifying concepts…", "info");

  try {
    const formData = new FormData();
    formData.append("file", state.file);

    const res = await fetch("/api/upload-and-analyze", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || "Analysis failed.");

    state.allConcepts = data.all_concepts;
    state.detectedConcepts = data.detected_concepts;
    state.demoMode = false;
    setStatus(uploadStatus, "Paper analyzed successfully.", "ok");
    renderConcepts();
    showStep(stepConcepts);
  } catch (err) {
    setStatus(
      uploadStatus,
      `${err.message} You can still try "Use expo demo mode" below.`,
      "error"
    );
  } finally {
    analyzeBtn.disabled = false;
  }
});

demoBtn.addEventListener("click", async () => {
  setStatus(uploadStatus, "Loading expo demo mode…", "info");
  try {
    const res = await fetch("/api/demo-sample");
    const data = await res.json();
    state.allConcepts = data.all_concepts;
    state.detectedConcepts = data.detected_concepts;
    state.demoMode = true;
    setStatus(uploadStatus, "", null);
    renderConcepts();
    showStep(stepConcepts);
  } catch (err) {
    setStatus(uploadStatus, "Could not load demo mode. Check the backend server.", "error");
  }
});

// ---- STEP 2: concepts ---------------------------------------------------------
function renderConcepts() {
  state.selectedConcepts.clear();
  conceptGrid.innerHTML = "";

  const detectedSet = new Set(state.detectedConcepts || []);

  state.allConcepts.forEach((concept) => {
    const isDetected = detectedSet.has(concept);
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "concept-chip";
    chip.innerHTML = `
      <span class="concept-chip__mark"></span>
      <span class="concept-chip__label">${escapeHtml(concept)}</span>
      ${isDetected ? '<span class="concept-chip__badge">Found in your paper</span>' : ""}
    `;
    chip.addEventListener("click", () => {
      if (state.selectedConcepts.has(concept)) {
        state.selectedConcepts.delete(concept);
        chip.classList.remove("is-selected");
      } else {
        state.selectedConcepts.add(concept);
        chip.classList.add("is-selected");
      }
      toOptionsBtn.disabled = state.selectedConcepts.size < 2;
      setStatus(
        conceptStatus,
        state.selectedConcepts.size < 2 ? "Select at least 2 concepts to continue." : "",
        state.selectedConcepts.size < 2 ? "info" : null
      );
    });

    if (isDetected) {
      state.selectedConcepts.add(concept);
      chip.classList.add("is-selected");
    }

    conceptGrid.appendChild(chip);
  });

  toOptionsBtn.disabled = state.selectedConcepts.size < 2;
  const baseMsg = state.demoMode ? "EXPO DEMO MODE — using the built-in sample paper. " : "";
  setStatus(
    conceptStatus,
    state.selectedConcepts.size < 2
      ? `${baseMsg}Select at least 2 concepts to continue.`
      : baseMsg,
    "info"
  );
}

toOptionsBtn.addEventListener("click", () => {
  showStep(stepOptions);
});

// ---- STEP 3: options ---------------------------------------------------------
function wirePillGroup(group, stateKey) {
  group.querySelectorAll(".pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      group.querySelectorAll(".pill").forEach((p) => p.classList.remove("is-selected"));
      pill.classList.add("is-selected");
      state[stateKey] = pill.dataset.value;
      generateBtn.disabled = !(state.questionType && state.numQuestions);
    });
  });
}
wirePillGroup(typeGroup, "questionType");
wirePillGroup(countGroup, "numQuestions");

generateBtn.addEventListener("click", async () => {
  generateBtn.disabled = true;
  setStatus(generateStatus, "Generating your mixed-concept practice paper…", "info");

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        concepts: Array.from(state.selectedConcepts),
        question_type: state.questionType,
        num_questions: parseInt(state.numQuestions, 10),
        demo_mode: state.demoMode,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Generation failed.");

    state.questions = data.questions;
    state.demoMode = data.demo_mode || state.demoMode;
    state.selfCheck = {};
    setStatus(generateStatus, data.notice || "", data.notice ? "info" : null);

    renderPaper();
    showStep(stepPaper);
  } catch (err) {
    setStatus(generateStatus, err.message, "error");
  } finally {
    generateBtn.disabled = false;
  }
});

// ---- STEP 4: generated paper ---------------------------------------------------
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function questionHtml(q, index, withSolution) {
  const letters = ["A", "B", "C", "D"];
  let optionsHtml = "";
  if (q.type === "mcq" && Array.isArray(q.options)) {
    optionsHtml = `<ul class="question__options">${q.options
      .map((opt, i) => `<li data-letter="${letters[i]}.">${escapeHtml(opt)}</li>`)
      .join("")}</ul>`;
  }

  let solutionHtml = "";
  if (withSolution) {
    const checked = state.selfCheck[index] ? "checked" : "";
    solutionHtml = `
      <div class="solution-block is-visible">
        <div class="solution-block__row"><span class="solution-block__label">Correct answer</span>${escapeHtml(q.answer)}</div>
        <div class="solution-block__row"><span class="solution-block__label">Step-by-step solution</span>${escapeHtml(q.solution)}</div>
        <div class="solution-block__row"><span class="solution-block__label">Concepts used</span>${escapeHtml((q.concepts_used || []).join(", "))}</div>
      </div>
      <div class="self-check">
        <label>
          <input type="checkbox" data-self-check-index="${index}" ${checked} />
          I got this one right
        </label>
      </div>`;
  }

  return `
    <div class="question">
      <div class="question__head">
        <span class="question__num">Q${index + 1}.</span>
        <span class="question__type-tag">${escapeHtml(q.type)}</span>
      </div>
      <p class="question__text">${escapeHtml(q.question)}</p>
      ${optionsHtml}
      ${solutionHtml}
    </div>`;
}

let solutionsVisible = false;

function renderPaper() {
  solutionsVisible = false;
  paperContainer.innerHTML = `
    ${state.demoMode ? '<div class="demo-flag">EXPO DEMO MODE</div>' : ""}
    <div class="paper-head">
      <p class="paper-head__brand">EXAMIX AI</p>
      <p class="paper-head__subtitle">Mixed Concept Practice Paper — CBSE Class 9</p>
      <p class="paper-head__credit">Developed by Krishiv Patel</p>
    </div>
    <div class="paper-toolbar">
      <button class="btn btn--outline btn--small" id="printBtn">Print paper</button>
      <button class="btn btn--outline btn--small" id="downloadBtn">Download PDF</button>
      <button class="btn btn--primary btn--small" id="answersBtn">Answers &amp; solutions</button>
    </div>
    <p class="self-check-tally" id="selfCheckTally"></p>
    <div id="questionsList">
      ${state.questions.map((q, i) => questionHtml(q, i, false)).join("")}
    </div>
  `;

  document.getElementById("printBtn").addEventListener("click", printPaper);
  document.getElementById("downloadBtn").addEventListener("click", downloadPdf);
  document.getElementById("answersBtn").addEventListener("click", toggleAnswers);
}

function wireSelfCheckBoxes() {
  document.querySelectorAll("[data-self-check-index]").forEach((box) => {
    box.addEventListener("change", () => {
      const idx = parseInt(box.dataset.selfCheckIndex, 10);
      state.selfCheck[idx] = box.checked;
      updateSelfCheckTally();
    });
  });
}

function updateSelfCheckTally() {
  const tallyEl = document.getElementById("selfCheckTally");
  if (!tallyEl) return;
  const marked = Object.values(state.selfCheck).filter(Boolean).length;
  const total = Object.keys(state.selfCheck).length;
  if (total === 0) {
    tallyEl.classList.remove("is-visible");
    return;
  }
  tallyEl.textContent = `You've marked ${marked} of ${total} as correct so far`;
  tallyEl.classList.add("is-visible");
}

function toggleAnswers() {
  solutionsVisible = !solutionsVisible;
  document.getElementById("questionsList").innerHTML = state.questions
    .map((q, i) => questionHtml(q, i, solutionsVisible))
    .join("");
  document.getElementById("answersBtn").textContent = solutionsVisible
    ? "Hide answers & solutions"
    : "Answers & solutions";

  if (solutionsVisible) {
    wireSelfCheckBoxes();
    updateSelfCheckTally();
  } else {
    document.getElementById("selfCheckTally").classList.remove("is-visible");
  }
}

function printPaper() {
  printRoot.innerHTML = `
    <div class="paper-head">
      <p class="paper-head__brand">EXAMIX AI</p>
      <p class="paper-head__subtitle">Mixed Concept Practice Paper — CBSE Class 9</p>
      <p class="paper-head__credit">Developed by Krishiv Patel</p>
    </div>
    <div>${state.questions.map((q, i) => questionHtml(q, i, false)).join("")}</div>
  `;
  window.print();
}

function downloadPdf() {
  if (typeof html2pdf === "undefined") {
    // CDN library hasn't loaded (e.g. no internet at the moment) - fall
    // back to the browser print dialog, which can still "Save as PDF".
    printPaper();
    return;
  }

  const wrapper = document.createElement("div");
  wrapper.style.padding = "24px";
  wrapper.style.fontFamily = "Georgia, serif";
  wrapper.innerHTML = `
    <div style="text-align:center;border-bottom:2px solid #1F2A44;padding-bottom:16px;margin-bottom:20px;">
      <h1 style="margin:0 0 4px;">EXAMIX AI</h1>
      <p style="margin:0;color:#5B6478;">Mixed Concept Practice Paper — CBSE Class 9</p>
      <p style="margin:8px 0 0;font-size:11px;color:#94998F;">Developed by Krishiv Patel</p>
    </div>
    <div>${state.questions.map((q, i) => questionHtml(q, i, solutionsVisible)).join("")}</div>
  `;

  html2pdf()
    .set({
      margin: 10,
      filename: "examix-ai-practice-paper.pdf",
      html2canvas: { scale: 2 },
      jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
    })
    .from(wrapper)
    .save();
}
