import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorSession } from "./editor-shell/editor-session.js";

const $ = (selector) => document.querySelector(selector);
const params = new URLSearchParams(location.search);
const scenario = params.get("scenario") || "integration";
const fixtureId = params.get("fixture") || "plain-grapheme";
const repetition = Number(params.get("repetition") || 1);
const manualMode = params.get("manual") === "1";
// The product default lives in EditorSession (`options.maxWorkerGenerations ?? 3`).
// Overridable here ONLY so the limit can be measured on the shipped artifact:
// every E1-C case navigates once per generation, so no case has ever driven more
// than one generation into a single page -- the cap has never been exercised at
// any value, including its own.  Default unchanged, so all 48 frozen cases keep
// the exact behaviour they were validated with.
const generationLimit = Number(params.get("maxGenerations") || 3);
const generationCycles = Number(params.get("generations") || 0);

const FIXTURES = Object.freeze({
  "plain-grapheme": {
    path: "./e1-fixtures/plain-grapheme.odt",
    name: "plain-grapheme.odt",
    anchors: [
      "E1-PLAIN-START", "臺灣中文游標測試", "emoji 😀 grapheme",
      "combining é boundary", "E1-PLAIN-END",
    ],
    editAnchor: "E1-PLAIN-START",
  },
  "table-boundary": {
    path: "./e1-fixtures/table-boundary.odt",
    name: "table-boundary.odt",
    anchors: ["E1-TABLE-BEFORE", "E1-CELL-A1", "E1-CELL-B2", "E1-TABLE-AFTER"],
    editAnchor: "E1-CELL-A1",
  },
  "l0-t1": {
    path: "./r7-compat-fixtures/l0-t1-plain-zh.odt",
    name: "l0-t1-plain-zh.odt",
    anchors: ["Final line：ODT round-trip 完整性檢查。"],
    editAnchor: "Final line：ODT round-trip 完整性檢查。",
  },
  "l0-t2": {
    path: "./r7-compat-fixtures/l0-t2-styled.odt",
    name: "l0-t2-styled.odt",
    anchors: ["文件結尾：請確認表格、圖片、註解與標題樣式均保留。"],
    editAnchor: "文件結尾：請確認表格、圖片、註解與標題樣式均保留。",
  },
  "l0-t3": {
    path: "./r7-compat-fixtures/l0-t3-long.odt",
    name: "l0-t3-long.odt",
    anchors: [
      "第 1 頁：長文件記憶體與效能測試",
      "第 22 頁：長文件記憶體與效能測試",
    ],
    editAnchor: "第 1 頁：長文件記憶體與效能測試",
  },
  "l1-review-odt": {
    path: "./r7-compat-fixtures/l1-review.odt",
    name: "l1-review.odt",
    anchors: ["Lorem ipsum"],
    editAnchor: "Lorem ipsum",
  },
  "l4-stress-100": {
    path: "./r7-compat-fixtures/l4-stress-100.odt",
    name: "l4-stress-100.odt",
    anchors: [
      "R7 stress page 001 頁面錨點",
      "R7 stress page 050 頁面錨點",
      "R7 stress page 100 頁面錨點",
    ],
    editAnchor: "R7 stress page 001 頁面錨點",
  },
});

const MANUAL_TEXT = Object.freeze({
  caret: "E1C人工第一筆中文輸入",
  selection: "E1C人工選取替換",
  cancel: "E1C人工取消不得出現",
  nativeClipboard: "E1C人工原生貼上臺灣😀",
  clipboard: "E1C人工剪貼簿臺灣😀",
});

const elements = {
  canvas: $("#canvas"),
  input: $("#input"),
  inputFeedback: $("#input-feedback"),
  log: $("#log"),
  status: $("#status"),
  scenario: $("#scenario"),
  revision: $("#revision"),
  message: $("#message"),
  manualToolbar: $("#manual-toolbar"),
  manualInstructions: $("#manual-instructions"),
  manualStatus: $("#manual-status"),
  manualChewingConfirm: $("#manual-chewing-confirm"),
  manualClipboardSource: $("#manual-clipboard-source"),
};

const metrics = {
  schemaVersion: 1,
  release: "E1-C-editor-validation",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  scenario,
  fixture: fixtureId,
  repetition,
  manual: manualMode,
  artifact: null,
  operations: [],
  states: [],
  sdkEvents: [],
  inputTrace: [],
  clipboardTrace: [],
  workers: { created: 0, terminated: 0, intentionalCrashes: 0 },
  output: null,
  manualEvidence: manualMode ? {
    expected: MANUAL_TEXT,
    cancelProbe: null,
    nativeCopy: null,
    clipboardWrite: null,
    clipboardRead: null,
    searches: [],
  } : null,
  complete: false,
  pass: false,
  error: null,
};
globalThis.__e1_c = metrics;
globalThis.__probe_metrics = metrics;

let fixture = null;
let fixtureBytes = null;
let session = null;
let activeWorkerControl = null;
let latestOutput = null;
let fakeClipboardMode = "normal";
let fakeClipboardText = "";
let fakeClipboardWrites = [];
let manualPendingCommitText = "";
let manualRenderChain = Promise.resolve();

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  elements.log.textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  elements.log.scrollTop = elements.log.scrollHeight;
}

function manualStatus(message) {
  if (elements.manualStatus)
    elements.manualStatus.textContent = message;
  log({ manualStatus: message });
}

function setInputFeedback(message, { error = false } = {}) {
  if (!elements.inputFeedback)
    return;
  elements.inputFeedback.textContent = message;
  elements.inputFeedback.classList.toggle("error", error);
}

function scheduleManualRender() {
  if (!manualMode)
    return;
  manualRenderChain = manualRenderChain
    .catch(() => {})
    .then(async () => {
      await renderFirstTile();
      log({ manualRender: "completed", revision: session?.document?.revision ?? null });
    })
    .catch((error) => {
      setInputFeedback(`文字已提交，但文件畫面重畫失敗：${error.message}`, { error: true });
      log({ manualRender: "failed", error: publicError(error) });
    });
}

function handleManualInputState(snapshot) {
  if (!manualMode)
    return;
  if (snapshot.blocked) {
    setInputFeedback(`輸入目前被封鎖：${snapshot.blockedReason || "unknown"}`, { error: true });
    return;
  }
  if (snapshot.composing)
    setInputFeedback(`組字中：${snapshot.compositionText || "…"}`);
}

function handleManualInputTrace(event) {
  if (!manualMode)
    return;
  if (event.type === "compositionupdate") {
    setInputFeedback(`組字中：${event.compositionText || event.data || "…"}`);
    return;
  }
  if (event.type === "commit-start") {
    manualPendingCommitText = event.text || "";
    setInputFeedback(`提交中：${manualPendingCommitText}`);
    return;
  }
  if (event.type === "commit-end") {
    const revision = event.result?.revision ?? session?.document?.revision ?? "—";
    setInputFeedback(`已提交到 ODT（revision ${revision}）：${manualPendingCommitText}`);
    elements.input.value = "";
    scheduleManualRender();
    return;
  }
  if (event.type === "commit-error") {
    setInputFeedback(`提交失敗：${event.error?.code || "ERROR"} ${event.error?.message || ""}`, {
      error: true,
    });
    return;
  }
  if (event.type === "compositionend" && event.wasComposing && event.commitText === "")
    setInputFeedback("組字已取消，沒有送出 SDK mutation");
}

function publicError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: error?.message || String(error),
    details: error?.details || null,
  };
}

function updateState(snapshot) {
  metrics.states.push({ atMs: performance.now(), ...snapshot });
  elements.status.value = snapshot.state;
  elements.status.textContent = snapshot.state;
  elements.revision.value = snapshot.revision ?? "—";
  elements.revision.textContent = snapshot.revision ?? "—";
  elements.message.textContent = snapshot.error
    ? `${snapshot.error.code}: ${snapshot.error.message}`
    : snapshot.dirty ? "尚未儲存" : "authority bytes已同步";
  elements.message.classList.toggle("error", Boolean(snapshot.error));
}

function workerFactory(url) {
  const worker = new Worker(url, { name: `e1-c-${scenario}-${metrics.workers.created + 1}` });
  metrics.workers.created += 1;
  let terminated = false;
  const control = {
    terminate() {
      if (terminated)
        return;
      terminated = true;
      metrics.workers.terminated += 1;
      worker.terminate();
    },
    crash(label) {
      metrics.workers.intentionalCrashes += 1;
      worker.dispatchEvent(new ErrorEvent("error", {
        message: `intentional E1-C ${label} Document Worker crash`,
      }));
      this.terminate();
    },
  };
  activeWorkerControl = control;
  return {
    addEventListener: (...args) => worker.addEventListener(...args),
    postMessage: (...args) => worker.postMessage(...args),
    terminate: () => control.terminate(),
  };
}

function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/e1-editor-v1/sdk-worker.js",
    timeoutMs: 30000,
    closeRecoveryTimeoutMs: 10000,
    workerFactory,
  });
}

const fakeClipboard = {
  async writeText(text) {
    if (fakeClipboardMode === "denied")
      throw Object.assign(new Error("denied"), { name: "NotAllowedError" });
    fakeClipboardWrites.push(text);
  },
  async readText() {
    if (fakeClipboardMode === "denied")
      throw Object.assign(new Error("denied"), { name: "NotAllowedError" });
    return fakeClipboardText;
  },
};

async function fetchFixture() {
  fixture = FIXTURES[fixtureId];
  if (!fixture)
    throw new Error(`unknown E1-C fixture: ${fixtureId}`);
  const response = await fetch(fixture.path, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed with HTTP ${response.status}: ${fixture.path}`);
  fixtureBytes = await response.arrayBuffer();
}

async function createSession() {
  const value = new EditorSession({
    engineFactory,
    maxWorkerGenerations: generationLimit,
    clipboard: manualMode ? navigator.clipboard : fakeClipboard,
    secureContext: manualMode ? globalThis.isSecureContext : true,
    onState: updateState,
    onInputState: handleManualInputState,
    onEvent(event) {
      metrics.sdkEvents.push(event);
    },
    onInputTrace(event) {
      metrics.inputTrace.push(event);
      log({ input: event });
      handleManualInputTrace(event);
    },
    onClipboardTrace(event) {
      metrics.clipboardTrace.push(event);
      log({ clipboard: event });
    },
  });
  await value.open({ bytes: fixtureBytes.slice(0), name: fixture.name });
  value.attachInput(elements.input);
  metrics.artifact = {
    profile: value.engine.manifest.profile,
    sdkVersion: value.engine.manifest.sdkVersion,
    coreCommit: value.engine.manifest.coreCommit,
    loader: value.engine.manifest.artifactFiles?.["probe.js"],
    wasm: value.engine.manifest.artifactFiles?.["probe.wasm"],
    editorContract: value.engine.manifest.editorContract,
  };
  return value;
}

async function renderFirstTile() {
  if (!session?.document)
    return;
  const widthTwips = Math.min(session.document.widthTwips, 12000);
  const heightTwips = Math.min(session.document.heightTwips, 15000);
  const tile = await session.document.render({
    xTwips: 0,
    yTwips: 0,
    widthTwips,
    heightTwips,
    canvasWidthPx: elements.canvas.width,
    canvasHeightPx: elements.canvas.height,
  }, { timeoutMs: 180000 });
  elements.canvas.getContext("2d").putImageData(new ImageData(
    new Uint8ClampedArray(tile.pixels), tile.width, tile.height,
  ), 0, 0);
}

async function record(name, operation) {
  const beforeRevision = session?.document?.revision ?? null;
  try {
    const result = await operation();
    const entry = {
      name,
      status: "passed",
      beforeRevision,
      revision: session?.document?.revision ?? null,
      result,
    };
    metrics.operations.push(entry);
    log(entry);
    return result;
  } catch (error) {
    const entry = { name, status: "failed", beforeRevision, error: publicError(error) };
    metrics.operations.push(entry);
    log(entry);
    throw error;
  }
}

async function expectedFailure(name, operation, code) {
  const beforeRevision = session.document.revision;
  try {
    await operation();
    const entry = {
      name, status: "failed", beforeRevision, revision: session.document.revision,
      error: { code: "UNEXPECTED_SUCCESS", message: `expected ${code}` },
    };
    metrics.operations.push(entry);
    log(entry);
    return entry;
  } catch (error) {
    const passed = error?.code === code && session.document.revision === beforeRevision;
    const entry = {
      name,
      status: passed ? "passed" : "failed",
      beforeRevision,
      revision: session.document.revision,
      expectedCode: code,
      error: publicError(error),
    };
    metrics.operations.push(entry);
    log(entry);
    return entry;
  }
}

async function searchText(text) {
  const result = await session.document.search(text, { timeoutMs: 30000 });
  if (!result.found)
    return { found: false, text: "", selections: [] };
  const selection = await session.document.getSelection({ timeoutMs: 30000 });
  return {
    found: selection.selectionType === "text" && selection.text === text,
    text: selection.text,
    selections: result.selections || [],
  };
}

function firstRectangle(search) {
  const raw = search.selections?.[0]?.rectangles || "";
  const values = raw.split(";")[0].split(",").map((value) => Number.parseInt(value.trim(), 10));
  if (values.length !== 4 || values.some((value) => !Number.isFinite(value)))
    throw new Error("search did not return a usable document rectangle");
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

async function placeAtBoundary(text, boundary) {
  const found = await searchText(text);
  if (!found.found)
    throw new Error(`anchor not found: ${text}`);
  const rectangle = firstRectangle(found);
  const xTwips = boundary === "start"
    ? rectangle.x + 1
    : rectangle.x + Math.max(1, rectangle.width - 1);
  const yTwips = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  return session.placeCaret(xTwips, yTwips, { caretTimeoutMs: 30000 });
}

function syntheticEvent(properties = {}) {
  return {
    isTrusted: false,
    cancelable: true,
    defaultPrevented: false,
    preventDefault() { this.defaultPrevented = true; },
    ...properties,
  };
}

async function syntheticComposition(text, { duplicateBeforeInput = false } = {}) {
  elements.input.value = text;
  session.input.handleCompositionStart(syntheticEvent({ data: "" }));
  session.input.handleCompositionUpdate(syntheticEvent({ data: text }));
  const completion = session.input.handleCompositionEnd(syntheticEvent({ data: text }));
  const duplicate = duplicateBeforeInput
    ? session.input.handleBeforeInput(syntheticEvent({
      inputType: "insertText",
      data: text,
    }))
    : Promise.resolve({ committed: false, reason: "not-requested" });
  const [result, duplicateResult] = await Promise.all([completion, duplicate]);
  elements.input.value = "";
  return { result, duplicateResult };
}

async function saveOutput() {
  const saved = await session.save({ timeoutMs: 180000 });
  latestOutput = saved.bytes;
  const digest = await crypto.subtle.digest("SHA-256", latestOutput);
  metrics.output = {
    bytes: latestOutput.byteLength,
    sha256: [...new Uint8Array(digest)]
      .map((value) => value.toString(16).padStart(2, "0")).join(""),
  };
  return metrics.output;
}

async function runIntegration() {
  await placeAtBoundary("ASCII abc", "end");
  const firstBefore = session.document.revision;
  const first = await record("composition-exactly-once", () => syntheticComposition(
    "E1C-COMMIT-臺灣😀", { duplicateBeforeInput: true },
  ));
  if (session.document.revision !== firstBefore + 1
      || first.duplicateResult.committed !== false)
    throw new Error("composition did not commit exactly once");
  const firstSearch = await searchText("E1C-COMMIT-臺灣😀");
  metrics.operations.push({
    name: "composition-anchor",
    status: firstSearch.found ? "passed" : "failed",
    result: firstSearch,
  });

  await placeAtBoundary("E1-PLAIN-END", "end");
  await record("move-before-composition", () => session.moveCharacter("left"));
  await record("composition-after-navigation", () => syntheticComposition("E1C-AFTER-MOVE"));

  await placeAtBoundary("臺灣中文游標測試", "end");
  await record("select-character-for-replacement", () => session.moveCharacter(
    "left", { extendSelection: true },
  ));
  const selected = await session.editor.getState({ timeoutMs: 30000 });
  metrics.operations.push({
    name: "selection-before-composition",
    status: selected.selectionType === "text"
      && selected.selection?.collapsed === false
      && selected.selectionText === "試" ? "passed" : "failed",
    result: selected,
  });
  const replaceBefore = session.document.revision;
  await record("composition-replaces-selection", () => syntheticComposition("E1C-REPLACE"));
  const replacement = await searchText("臺灣中文游標測E1C-REPLACE");
  metrics.operations.push({
    name: "selection-replacement-postcondition",
    status: replacement.found && session.document.revision === replaceBefore + 1
      ? "passed" : "failed",
    result: replacement,
  });

  await placeAtBoundary("emoji 😀 grapheme", "end");
  await record("move-before-cancel", () => session.moveCharacter("left"));
  const cancelBefore = session.document.revision;
  elements.input.value = "";
  session.input.handleCompositionStart(syntheticEvent({ data: "" }));
  session.input.handleCompositionUpdate(syntheticEvent({ data: "E1C-CANCEL" }));
  const cancelled = await session.input.handleCompositionEnd(syntheticEvent({ data: "" }));
  const cancelledSearch = await searchText("E1C-CANCEL");
  metrics.operations.push({
    name: "composition-cancel-zero-mutation",
    status: cancelled.committed === false
      && session.document.revision === cancelBefore
      && !cancelledSearch.found ? "passed" : "failed",
    result: { cancelled, cancelledSearch, cancelBefore, revision: session.document.revision },
  });

  await placeAtBoundary("0123456789", "end");
  await record("select-character-for-paste", () => session.moveCharacter(
    "left", { extendSelection: true },
  ));
  const pasteBefore = session.document.revision;
  await record("html-plus-plain-paste", () => session.pasteEvent({
    isTrusted: false,
    preventDefault() {},
    clipboardData: {
      types: ["text/html", "text/plain"],
      getData(type) {
        return type === "text/plain" ? "E1C-PASTE-臺灣😀" : "<b>forbidden</b>";
      },
    },
  }, { synthetic: true }));
  const pasted = await searchText("012345678E1C-PASTE-臺灣😀");
  metrics.operations.push({
    name: "plain-paste-selection-postcondition",
    status: pasted.found && session.document.revision === pasteBefore + 1
      ? "passed" : "failed",
    result: pasted,
  });

  await searchText("ASCII");
  const copyBefore = session.document.revision;
  await record("copy-public-selection", () => session.copySelection({
    metadata: { synthetic: true },
  }));
  metrics.operations.push({
    name: "copy-zero-mutation",
    status: fakeClipboardWrites.at(-1) === "ASCII"
      && session.document.revision === copyBefore ? "passed" : "failed",
    result: { fakeClipboardWrites, copyBefore, revision: session.document.revision },
  });

  fakeClipboardMode = "denied";
  await expectedFailure(
    "clipboard-denied-zero-mutation",
    () => session.pasteFromClipboard({ userGesture: true }),
    "CLIPBOARD_DENIED",
  );
  fakeClipboardMode = "normal";
  const emptyBefore = session.document.revision;
  fakeClipboardText = "";
  const empty = await session.pasteFromClipboard({ userGesture: true });
  metrics.operations.push({
    name: "clipboard-empty-zero-mutation",
    status: empty.committed === false && session.document.revision === emptyBefore
      ? "passed" : "failed",
    result: empty,
  });
  const oversizedBefore = session.document.revision;
  fakeClipboardText = "大".repeat(6000);
  await expectedFailure(
    "clipboard-oversized-zero-mutation",
    () => session.pasteFromClipboard({ userGesture: true }),
    "INPUT_TOO_LARGE",
  );
  if (session.document.revision !== oversizedBefore)
    throw new Error("oversized clipboard changed the document revision");

  await placeAtBoundary("E1C-PASTE-臺灣😀", "end");
  await record("delete-backward", () => session.delete("backward"));
  await record("undo-delete", () => session.undo());

  await placeAtBoundary("E1-PLAIN-START", "end");
  await record("insert-paragraph-break", () => session.insertBreak("paragraph"));
  await record("paragraph-marker", () => session.commitText("E1C-PARAGRAPH"));
  await record("insert-line-break", () => session.insertBreak("line"));
  await record("line-marker", () => session.commitText("E1C-LINE"));

  await searchText("ASCII");
  await record("set-bold-on", () => session.setInlineFormat("bold", true));
  await record("set-italic-on", () => session.setInlineFormat("italic", true));
  await record("set-bold-off", () => session.setInlineFormat("bold", false));
  await record("set-italic-off", () => session.setInlineFormat("italic", false));

  await placeAtBoundary("E1C-LINE", "end");
  await record("insert-undo-marker", () => session.commitText("E1C-UNDO"));
  const undoBefore = await searchText("E1C-UNDO");
  await record("public-undo", () => session.undo());
  const undoAfter = await searchText("E1C-UNDO");
  metrics.operations.push({
    name: "undo-postcondition",
    status: undoBefore.found && !undoAfter.found ? "passed" : "failed",
    result: { undoBefore, undoAfter },
  });
  await record("save", saveOutput);
}

async function runBoundary() {
  const definition = scenario === "boundary-table"
    ? { anchor: "E1-CELL-A1", boundary: "start", direction: "backward" }
    : { anchor: "E1-PLAIN-START", boundary: "start", direction: "backward" };
  await placeAtBoundary(definition.anchor, definition.boundary);
  const beforeRevision = session.document.revision;
  const oldDocument = session.document;
  const deletion = session.delete(definition.direction).then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", error: publicError(error) }),
  );
  const queued = session.commitText("E1C-BOUNDARY-QUEUED-MUST-NOT-REPLAY").then(
    () => ({ status: "unexpected-success" }),
    (error) => ({ status: "rejected", error: publicError(error) }),
  );
  const [deleteResult, queuedResult] = await Promise.all([deletion, queued]);
  const blockedState = session.state.snapshot;
  metrics.operations.push({
    name: "boundary-rejection-and-queue-block",
    status: deleteResult.error?.code === "EDITOR_BOUNDARY_UNSUPPORTED"
      && queuedResult.status === "rejected"
      && blockedState.state === "restart-required"
      && session.document.revision === beforeRevision ? "passed" : "failed",
    result: { deleteResult, queuedResult, blockedState, beforeRevision },
  });
  await record("fresh-worker-restart", () => session.restart());
  let staleCode = null;
  try {
    await oldDocument.search(definition.anchor, { timeoutMs: 5000 });
  } catch (error) {
    staleCode = error.code;
  }
  const anchor = await searchText(definition.anchor);
  const forbidden = await searchText("E1C-BOUNDARY-QUEUED-MUST-NOT-REPLAY");
  metrics.operations.push({
    name: "boundary-fresh-worker-no-replay",
    status: staleCode === "STALE_DOCUMENT" && anchor.found && !forbidden.found
      ? "passed" : "failed",
    result: { staleCode, anchor, forbidden, generation: session.state.snapshot.generation },
  });
  await record("save", saveOutput);
}

async function waitForState(expected, timeoutMs = 5000) {
  const deadline = performance.now() + timeoutMs;
  while (performance.now() < deadline) {
    if (session.state.snapshot.state === expected)
      return session.state.snapshot;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error(`editor did not enter ${expected}`);
}

async function runCrash() {
  const marker = `E1C-${scenario.toUpperCase()}-MUST-${scenario === "crash-saved" ? "SURVIVE" : "NOT-REPLAY"}`;
  const oldDocument = session.document;
  let pending = [];
  if (scenario === "crash-preedit") {
    elements.input.value = marker;
    session.input.handleCompositionStart(syntheticEvent({ data: "" }));
    session.input.handleCompositionUpdate(syntheticEvent({ data: marker }));
  } else if (scenario === "crash-queued") {
    pending = [
      session.commitText(`${marker}-FIRST`).catch((error) => publicError(error)),
      session.commitText(`${marker}-QUEUED`).catch((error) => publicError(error)),
    ];
  } else {
    await placeAtBoundary(fixture.editAnchor, "end");
    await record("pre-crash-commit", () => session.commitText(marker));
    if (scenario === "crash-saved")
      await record("pre-crash-save", saveOutput);
  }
  activeWorkerControl.crash(scenario);
  await waitForState("recoverable-error");
  const recoveryState = session.state.snapshot;
  if (pending.length)
    await Promise.all(pending);
  await record("crash-restart", () => session.restart());
  let staleCode = null;
  try {
    await oldDocument.search(fixture.editAnchor, { timeoutMs: 5000 });
  } catch (error) {
    staleCode = error.code;
  }
  const markerSearch = await searchText(marker);
  const firstSearch = scenario === "crash-queued"
    ? await searchText(`${marker}-FIRST`) : { found: false };
  const queuedSearch = scenario === "crash-queued"
    ? await searchText(`${marker}-QUEUED`) : { found: false };
  const expectedMarker = scenario === "crash-saved";
  metrics.operations.push({
    name: "crash-recovery-authority-and-no-replay",
    status: recoveryState.state === "recoverable-error"
      && staleCode === "STALE_DOCUMENT"
      && markerSearch.found === expectedMarker
      && !firstSearch.found
      && !queuedSearch.found
      && session.state.snapshot.generation === 2 ? "passed" : "failed",
    result: {
      recoveryState,
      staleCode,
      markerSearch,
      firstSearch,
      queuedSearch,
      generation: session.state.snapshot.generation,
    },
  });
  await record("post-recovery-save", saveOutput);
}

async function runCorpus() {
  const marker = `E1C-${fixtureId}-臺灣😀`;
  await placeAtBoundary(fixture.editAnchor, "end");
  await record("corpus-insert", () => session.commitText(marker));
  const inserted = await searchText(marker);
  metrics.operations.push({
    name: "corpus-insert-postcondition",
    status: inserted.found ? "passed" : "failed",
    result: inserted,
  });
  await placeAtBoundary(marker, "end");
  await record("corpus-delete", () => session.delete("backward"));
  await record("corpus-undo-delete", () => session.undo());
  await searchText(marker);
  await record("corpus-bold", () => session.setInlineFormat("bold", true));
  await record("corpus-italic", () => session.setInlineFormat("italic", true));
  const preserved = [];
  for (const anchor of fixture.anchors)
    preserved.push({ anchor, ...(await searchText(anchor)) });
  metrics.operations.push({
    name: "corpus-original-anchors",
    status: preserved.every((entry) => entry.found) ? "passed" : "failed",
    result: preserved,
  });
  await record("save", saveOutput);
}

async function runLifecycle() {
  const marker = `E1C-LIFECYCLE-${repetition.toString().padStart(2, "0")}`;
  await placeAtBoundary(fixture.editAnchor, "end");
  await record("lifecycle-insert", () => session.commitText(marker));
  await record("lifecycle-save", saveOutput);
  const beforeClose = {
    generation: session.state.snapshot.generation,
    workers: { ...metrics.workers },
  };
  await session.close();
  metrics.operations.push({
    name: "lifecycle-close",
    status: session.state.snapshot.state === "closed" ? "passed" : "failed",
    result: { beforeClose, workers: metrics.workers },
  });
}

// N engine generations inside ONE page on the shipped artifact, plus proof the
// limit still fails closed at N.  This is the evidence the spec's per-page cap
// never had: E1-C drives one generation per navigation, and R7's 50-generation
// runs used the writer-review probe, not e1-editor-v1.
async function runGenerations() {
  // A generation is NOT one opened document.  close() ends the session, and a
  // new document means a new EditorSession whose counter starts at zero.  The
  // only way _generation advances is restart() after a crash or a boundary --
  // so this cap governs "how many times may ONE session recover before the page
  // must be reloaded", and driving it means crashing the worker on purpose.
  const generations = [];
  for (let index = 2; index <= generationCycles; index += 1) {
    await placeAtBoundary(fixture.editAnchor, "end");
    await record(`gen-${index}-precrash-commit`,
      () => session.commitText(`E1C-GEN-${index.toString().padStart(2, "0")}`));
    await record(`gen-${index}-precrash-save`, saveOutput);
    activeWorkerControl.crash(`generations-${index}`);
    await waitForState("recoverable-error", 30000);
    const started = performance.now();
    await record(`gen-${index}-restart`, () => session.restart());
    generations.push({
      generation: session.state.snapshot.generation,
      restartMs: performance.now() - started,
      workers: { ...metrics.workers },
    });
    metrics.operations.push({
      name: `gen-${index}-observed`,
      status: session.state.snapshot.generation === index ? "passed" : "failed",
      result: { expected: index, observed: session.state.snapshot.generation },
    });
  }
  // Raising the number is only defensible if the limit is still a limit: the
  // (N+1)-th recovery must still be refused with the typed, reload-directing
  // error, or this change removes the backstop instead of moving it.
  activeWorkerControl.crash("generations-overrun");
  await waitForState("recoverable-error", 30000);
  let overrun = null;
  try {
    await session.restart();
    overrun = { code: "UNEXPECTED_SUCCESS", requiresPageReload: null };
  } catch (error) {
    overrun = {
      code: error?.code ?? null,
      requiresPageReload: error?.details?.requiresPageReload ?? null,
      maximumWorkerGenerations: error?.details?.maximumWorkerGenerations ?? null,
    };
  }
  metrics.operations.push({
    name: "generation-limit-still-fails-closed",
    status: overrun.code === "WORKER_GENERATION_LIMIT"
      && overrun.requiresPageReload === true ? "passed" : "failed",
    result: overrun,
  });
  metrics.generationLimitProbe = {
    configured: generationLimit,
    requested: generationCycles,
    reached: session.state.snapshot.generation,
    generations,
    overrun,
    workers: { ...metrics.workers },
  };
}

async function runAutomatic() {
  if (scenario === "generations")
    await runGenerations();
  else if (scenario === "integration")
    await runIntegration();
  else if (scenario.startsWith("boundary-"))
    await runBoundary();
  else if (scenario.startsWith("crash-"))
    await runCrash();
  else if (scenario === "corpus")
    await runCorpus();
  else if (scenario === "lifecycle")
    await runLifecycle();
  else
    throw new Error(`unsupported E1-C scenario: ${scenario}`);
  metrics.pass = metrics.crossOriginIsolated
    && metrics.artifact?.profile === "e1-editor-v1"
    && metrics.artifact?.editorContract?.version === 1
    && metrics.operations.length > 0
    && metrics.operations.every((entry) => entry.status === "passed")
    // Compare against the CONFIGURED limit, not a repeated literal: a gate that
    // restates the constant it is guarding drifts from it silently.  Default is
    // still 3, so every frozen case is unaffected.
    && metrics.workers.created <= generationLimit;
}

async function prepareManualCaret() {
  await placeAtBoundary("E1-PLAIN-START", "end");
  elements.input.focus();
  manualStatus(`請用Chewing輸入：${MANUAL_TEXT.caret}`);
}

async function prepareManualSelection() {
  await placeAtBoundary("臺灣中文游標測試", "end");
  await session.moveCharacter("left", { extendSelection: true });
  elements.input.focus();
  manualStatus(`請用Chewing取代選取字元：${MANUAL_TEXT.selection}`);
}

function startManualCancelProbe() {
  metrics.manualEvidence.cancelProbe = {
    requestBaseline: session.input.state.requestCount,
    revisionBaseline: session.document.revision,
    traceStart: metrics.inputTrace.length,
    pass: false,
  };
  elements.input.focus();
  manualStatus("請開始一段Chewing preedit，不選字直接按Escape；再按4驗證取消");
}

async function checkManualCancelProbe() {
  const probe = metrics.manualEvidence.cancelProbe;
  if (!probe)
    throw new Error("尚未記錄取消前狀態");
  const trace = metrics.inputTrace.slice(probe.traceStart);
  const forbidden = await searchText(MANUAL_TEXT.cancel);
  probe.requestDelta = session.input.state.requestCount - probe.requestBaseline;
  probe.revisionDelta = session.document.revision - probe.revisionBaseline;
  probe.trustedPreedit = trace.some((entry) =>
    entry.type === "compositionupdate" && entry.isTrusted === true);
  probe.emptyEnd = trace.some((entry) =>
    entry.type === "compositionend" && entry.commitText === "");
  probe.forbiddenFound = forbidden.found;
  probe.pass = probe.requestDelta === 0 && probe.revisionDelta === 0
    && probe.trustedPreedit && probe.emptyEnd && !probe.forbiddenFound;
  manualStatus(probe.pass
    ? "取消通過：零SDK mutation"
    : "取消未通過；本次結果會保留，請勿反覆嘗試掩蓋");
  log({ manualCancelProbe: probe });
}

function prepareNativeClipboard() {
  elements.manualClipboardSource.focus();
  elements.manualClipboardSource.select();
  manualStatus("fixture已全選：請按Ctrl+C，再點input sink按Ctrl+V");
}

async function manualClipboardWrite() {
  try {
    await navigator.clipboard.writeText(MANUAL_TEXT.clipboard);
    metrics.manualEvidence.clipboardWrite = { status: "passed" };
    manualStatus("Clipboard API固定字串已寫入；請按6b讀入");
  } catch (error) {
    metrics.manualEvidence.clipboardWrite = { status: "failed", error: publicError(error) };
    manualStatus(`Clipboard API寫入失敗：${error.name}`);
  }
}

async function manualClipboardRead() {
  const beforeRevision = session.document.revision;
  try {
    const result = await session.pasteFromClipboard({ userGesture: true });
    const found = await searchText(MANUAL_TEXT.clipboard);
    metrics.manualEvidence.clipboardRead = {
      status: "passed",
      revisionDelta: session.document.revision - beforeRevision,
      found: found.found,
      result,
    };
    manualStatus(found.found ? "Clipboard API讀入通過" : "Clipboard API文字未在ODT找到");
  } catch (error) {
    metrics.manualEvidence.clipboardRead = {
      status: "failed",
      revisionDelta: session.document.revision - beforeRevision,
      error: publicError(error),
    };
    manualStatus(`Clipboard API讀入失敗：${error.name}`);
  }
}

async function finishManual() {
  const searches = [];
  for (const text of [
    MANUAL_TEXT.caret, MANUAL_TEXT.selection,
    MANUAL_TEXT.nativeClipboard, MANUAL_TEXT.clipboard,
  ])
    searches.push({ text, ...(await searchText(text)) });
  const cancelled = await searchText(MANUAL_TEXT.cancel);
  searches.push({ text: MANUAL_TEXT.cancel, expectedAbsent: true, ...cancelled });
  metrics.manualEvidence.searches = searches;
  const trustedComposition = metrics.inputTrace.some((entry) =>
    entry.type === "compositionstart" && entry.isTrusted === true)
    && metrics.inputTrace.some((entry) =>
      entry.type === "compositionupdate" && entry.isTrusted === true);
  const trustedPaste = metrics.inputTrace.some((entry) =>
    entry.type === "paste" && entry.isTrusted === true);
  await saveOutput();
  metrics.manualEvidence.operatorInputMethod = elements.manualChewingConfirm.checked
    ? "Fcitx5 Chewing (operator-confirmed)" : null;
  metrics.manualEvidence.trustedComposition = trustedComposition;
  metrics.manualEvidence.trustedPaste = trustedPaste;
  metrics.manualEvidence.verifiedAt = new Date().toISOString();
  metrics.pass = elements.manualChewingConfirm.checked
    && trustedComposition
    && trustedPaste
    && metrics.manualEvidence.nativeCopy?.isTrusted === true
    && metrics.manualEvidence.clipboardWrite?.status === "passed"
    && metrics.manualEvidence.clipboardRead?.status === "passed"
    && metrics.manualEvidence.clipboardRead?.found === true
    && metrics.manualEvidence.cancelProbe?.pass === true
    && searches.filter((entry) => !entry.expectedAbsent).every((entry) => entry.found)
    && cancelled.found === false;
  metrics.complete = true;
  const browserId = navigator.userAgent.includes("Firefox") ? "firefox" : "chrome";
  try {
    const response = await fetch(`/e1-c-manual-submit?browser=${browserId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...metrics, outputBase64: globalThis.__e1_c_get_output_base64() }),
    });
    const submission = await response.json();
    if (!response.ok)
      throw new Error(submission.error || `HTTP ${response.status}`);
    metrics.manualEvidence.submission = submission;
    manualStatus(submission.pass
      ? `${browserId} manual pass，evidence已自動寫入`
      : `${browserId} manual failed，失敗evidence已自動保留`);
  } catch (error) {
    metrics.manualEvidence.submission = { status: "failed", error: publicError(error) };
    manualStatus(`驗收已完成但自動送出失敗：${error.message}`);
  }
  log({ manualComplete: true, pass: metrics.pass, manualEvidence: metrics.manualEvidence });
}

async function manualAction(action) {
  if (action === "caret")
    return prepareManualCaret();
  if (action === "selection")
    return prepareManualSelection();
  if (action === "cancel-start")
    return startManualCancelProbe();
  if (action === "cancel-check")
    return checkManualCancelProbe();
  if (action === "native-prepare")
    return prepareNativeClipboard();
  if (action === "clipboard-write")
    return manualClipboardWrite();
  if (action === "clipboard-read")
    return manualClipboardRead();
  if (action === "finish")
    return finishManual();
  throw new Error(`unknown manual action: ${action}`);
}

elements.manualToolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.manual;
  if (action)
    void manualAction(action).catch((error) => {
      manualStatus(`步驟失敗：${error.code || error.name || "Error"} ${error.message}`);
      log(publicError(error));
    });
});

elements.input.addEventListener("focus", () => {
  if (manualMode && !session?.input?.state?.blocked)
    setInputFeedback("輸入區已聚焦；可直接用鍵盤或 Chewing 輸入");
});

elements.manualClipboardSource.addEventListener("copy", (event) => {
  if (!manualMode)
    return;
  metrics.manualEvidence.nativeCopy = {
    text: elements.manualClipboardSource.value,
    isTrusted: event.isTrusted === true,
    pass: event.isTrusted === true
      && elements.manualClipboardSource.value === MANUAL_TEXT.nativeClipboard,
  };
  manualStatus(metrics.manualEvidence.nativeCopy.pass
    ? "已收到trusted Ctrl+C；請點input sink按Ctrl+V"
    : "Ctrl+C事件不是trusted；請保留本次結果");
});

globalThis.__e1_c_get_output_base64 = () => {
  if (!latestOutput)
    return "";
  const bytes = new Uint8Array(latestOutput);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};
globalThis.__e1_c_manual_action = manualAction;

async function initialize() {
  elements.scenario.value = scenario;
  elements.scenario.textContent = scenario;
  await fetchFixture();
  session = await createSession();
  await renderFirstTile();
  if (manualMode) {
    elements.manualToolbar.hidden = false;
    elements.manualInstructions.hidden = false;
    elements.manualClipboardSource.hidden = false;
    elements.input.disabled = false;
    elements.input.readOnly = false;
    setInputFeedback("先按步驟 1；輸入完成後會顯示已提交文字與 revision");
    log({ manualReady: true, expected: MANUAL_TEXT });
    return;
  }
  try {
    await runAutomatic();
  } catch (error) {
    metrics.error = publicError(error);
    metrics.pass = false;
  } finally {
    if (session?.state.snapshot.state !== "closed")
      await session?.close();
    metrics.complete = true;
    log({ complete: true, pass: metrics.pass, error: metrics.error });
  }
}

initialize().catch((error) => {
  metrics.error = publicError(error);
  metrics.pass = false;
  metrics.complete = true;
  log(metrics.error);
});
