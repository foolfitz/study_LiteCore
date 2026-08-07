import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorDiscoveryClient } from "./e1/editor-discovery-client.js";

const canvas = document.querySelector("#canvas");
const context = canvas.getContext("2d");
const status = document.querySelector("#status");
const logNode = document.querySelector("#log");
const fixtureSelect = document.querySelector("#fixture");
const scenarioResult = document.querySelector("#scenario-result");
const controls = [...document.querySelectorAll("button, input, select")];
const freshPageControlIds = new Set([
  "reload",
  "scenario-delete",
  "scenario-backspace",
  "scenario-paragraph-start",
  "scenario-paragraph-end",
]);
const metrics = {
  schemaVersion: 1,
  release: "E1-Finding-016-manual-delete",
  phase: "starting",
  ready: false,
  busy: false,
  fixture: null,
  revision: 0,
  operations: [],
  lastError: null,
  recoveryRequired: false,
};
globalThis.__e1_manual_delete = metrics;
globalThis.__probe_metrics = metrics;

let corpus = null;
let engine = null;
let documentHandle = null;
let editor = null;
let renderRegion = null;

function log(message, detail = null) {
  const timestamp = new Date().toISOString().slice(11, 23);
  logNode.textContent += `[${timestamp}] ${message}${detail ? ` ${JSON.stringify(detail)}` : ""}\n`;
  logNode.scrollTop = logNode.scrollHeight;
}

function errorValue(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details || null,
  };
}

function setBusy(value, message = null) {
  metrics.busy = value;
  for (const control of controls) {
    control.disabled = value || (metrics.recoveryRequired
      && !freshPageControlIds.has(control.id));
  }
  status.textContent = message || (metrics.recoveryRequired
    ? "Worker 狀態失效；請重新載入"
    : (metrics.ready ? `就緒 · revision ${metrics.revision}` : "初始化中"));
}

async function renderDocument() {
  renderRegion = {
    xTwips: 0,
    yTwips: 0,
    widthTwips: Math.min(documentHandle.widthTwips, 12240),
    heightTwips: Math.min(documentHandle.heightTwips, 15840),
    canvasWidthPx: canvas.width,
    canvasHeightPx: canvas.height,
  };
  const tile = await documentHandle.render(renderRegion, { timeoutMs: 180000 });
  context.putImageData(
    new ImageData(new Uint8ClampedArray(tile.pixels), tile.width, tile.height),
    0,
    0,
  );
  metrics.revision = documentHandle.revision;
}

async function openFixture(fixtureId) {
  const fixture = corpus.fixtures.find((item) => item.id === fixtureId);
  if (!fixture)
    throw new Error(`unknown fixture: ${fixtureId}`);
  const response = await fetch(`./e1-fixtures/${fixture.path}`, { cache: "no-cache" });
  const input = await response.arrayBuffer();
  documentHandle = await engine.open(input, {
    name: fixture.path,
    transfer: true,
    timeoutMs: 180000,
  });
  editor = new EditorDiscoveryClient(documentHandle);
  await renderDocument();
  metrics.fixture = fixtureId;
  metrics.revision = documentHandle.revision;
  metrics.ready = true;
  metrics.phase = "ready";
  metrics.lastError = null;
  metrics.recoveryRequired = false;
  fixtureSelect.value = fixtureId;
  log("已載入原始 fixture", { fixture: fixtureId, revision: metrics.revision });
}

function navigateToFreshPage(fixtureId, scenario = null) {
  metrics.phase = "restarting";
  setBusy(true, "建立全新 Worker…");
  const url = new URL(location.href);
  url.search = "";
  url.searchParams.set("fixture", fixtureId);
  if (scenario)
    url.searchParams.set("scenario", scenario);
  url.searchParams.set("instance", String(Date.now()));
  location.assign(url.href);
}

async function runOperation(name, callback, { manual = false } = {}) {
  setBusy(true, `${name} 執行中`);
  const entry = { name, manual, startedAt: new Date().toISOString(), status: "running" };
  metrics.operations.push(entry);
  try {
    entry.result = await callback();
    entry.status = entry.result?.verification?.pass === false
      ? "verification-failed" : "completed";
    await renderDocument();
    entry.revision = documentHandle.revision;
    metrics.revision = documentHandle.revision;
    metrics.lastError = null;
    if (entry.result?.verification) {
      scenarioResult.className = `result ${entry.result.verification.pass ? "pass" : "fail"}`;
      scenarioResult.textContent = entry.result.verification.pass
        ? `${name}：字串檢查通過，請再看畫面確認。`
        : `${name}：字串檢查失敗，實際刪除與預期不符。`;
      log(`${name} 字串檢查${entry.result.verification.pass ? "通過" : "失敗"}`, entry.result);
    } else if (manual)
      log(`${name} 命令已回覆；請人工確認畫面`, entry.result);
    else
      log(`${name} 完成`, entry.result || { revision: entry.revision });
  } catch (error) {
    entry.status = "failed";
    entry.error = errorValue(error);
    metrics.lastError = entry.error;
    if (entry.error.code === "TIMEOUT" || entry.error.code === "BUSY") {
      metrics.recoveryRequired = true;
      metrics.phase = "recovery-required";
      metrics.ready = false;
      scenarioResult.className = "result fail";
      scenarioResult.textContent = `${name}：Worker 狀態已失效，請按重新載入或重新執行任一一鍵案例。`;
    }
    log(`${name} 失敗`, entry.error);
  } finally {
    entry.finishedAt = new Date().toISOString();
    setBusy(false, metrics.recoveryRequired
      ? "Worker 狀態失效；請重新載入"
      : null);
  }
}

function bind(id, handler) {
  document.querySelector(id).addEventListener("click", handler);
}

async function selectRequired(query) {
  const result = await documentHandle.search(query);
  if (!result.found)
    throw new Error(`找不到測試 anchor：${query}`);
  return result;
}

function firstSearchRectangle(searchResult) {
  const value = searchResult?.selections?.[0]?.rectangles || "";
  const first = value.split(";")[0];
  const values = first.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (values.length !== 4 || values.some((value) => !Number.isFinite(value))) {
    const error = new Error("搜尋結果沒有可用的定位矩形");
    error.name = "CaretPlacementError";
    error.code = "CARET_RECTANGLE_UNAVAILABLE";
    error.details = { rectangles: value };
    throw error;
  }
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

async function placeCaretAtSearchBoundary(searchResult, boundary) {
  const rectangle = firstSearchRectangle(searchResult);
  const xTwips = boundary === "start"
    ? rectangle.x
    : rectangle.x + Math.max(1, rectangle.width);
  const yTwips = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  const reset = await editor.select("selection-reset-unstable", {
    startXTwips: xTwips,
    startYTwips: yTwips,
    endXTwips: xTwips,
    endYTwips: yTwips,
  });
  const selection = await documentHandle.getSelection();
  const state = await editor.getState();
  // Finding 017: two independent paths must agree before any mutation.
  //
  // The transferable path cannot tell a genuinely empty selection from one
  // whose plain-text flavor is missing -- core folds both into "none" -- and
  // a "complex" selection also reports empty text, so testing text === "" is
  // not enough. The callback path is only meaningful once a
  // LOK_CALLBACK_TEXT_SELECTION has actually arrived, hence `observed`.
  const selectionEmpty = selection.selectionType === "none";
  const stateObserved = state.selection?.observed === true;
  const stateCollapsed = state.selection?.collapsed === true;
  if (!selectionEmpty || !stateObserved || !stateCollapsed) {
    const error = new Error("游標定位後仍有文字被選取；已在刪除前停止");
    error.name = "CaretPlacementError";
    error.code = "CARET_NOT_COLLAPSED";
    error.details = {
      boundary,
      method: "selection-reset-unstable",
      rectangle,
      xTwips,
      yTwips,
      selectionType: selection.selectionType,
      selectionText: selection.text,
      stateObserved,
      stateCollapsed,
      state,
    };
    throw error;
  }
  return {
    boundary,
    method: "selection-reset-unstable",
    reset,
    rectangle,
    xTwips,
    yTwips,
    selectionType: selection.selectionType,
    selectionText: selection.text,
    stateObserved,
    stateCollapsed,
    state,
  };
}

async function runCharacterDeleteScenario({ name, action, boundary, expected }) {
  return runOperation(name, async () => {
    const original = "0123456789";
    const search = await selectRequired(original);
    const placement = await placeCaretAtSearchBoundary(search, boundary);
    const deletion = await editor.action(action, { manualObservation: true });
    // Finding 016 gate. The action returns on the UNO command result, so its
    // own state snapshot only shows callbacks that had already arrived. Read
    // the state again afterwards to tell "no callback ever arrives" apart from
    // "a callback arrives after we stopped looking". Purely observational --
    // no retry, no mutation, and the verdict below is unchanged by it.
    const afterDeletion = await editor.getState();
    const expectedSearch = await documentHandle.search(expected);
    const originalSearch = await documentHandle.search(original);
    return {
      anchor: original,
      placement,
      deletion,
      afterDeletion,
      expected,
      verification: {
        expectedFound: expectedSearch.found,
        originalStillFound: originalSearch.found,
        pass: expectedSearch.found && !originalSearch.found,
      },
    };
  }, { manual: true });
}

async function runParagraphBoundaryScenario({ name, anchor, boundary, action, expectation }) {
  return runOperation(name, async () => {
    const search = await selectRequired(anchor);
    const placement = await placeCaretAtSearchBoundary(search, boundary);
    const deletion = await editor.action(action, { manualObservation: true });
    return { anchor, placement, deletion, expectation };
  }, { manual: true });
}

const scenarioRunners = {
  delete: () => runCharacterDeleteScenario({
    name: "一鍵 Delete",
    action: "delete-forward",
    boundary: "start",
    expected: "123456789",
  }),
  backspace: () => runCharacterDeleteScenario({
    name: "一鍵 Backspace",
    action: "delete-backward",
    boundary: "end",
    expected: "012345678",
  }),
  "paragraph-start": () => runParagraphBoundaryScenario({
    name: "段首 Backspace",
    anchor: "ASCII abc XYZ 0123456789",
    boundary: "start",
    action: "delete-backward",
    expectation: "第二段應與 E1-PLAIN-START 所在段落合併",
  }),
  "paragraph-end": () => runParagraphBoundaryScenario({
    name: "段尾 Delete",
    anchor: "combining é boundary",
    boundary: "end",
    action: "delete-forward",
    expectation: "本段應與 E1-PLAIN-END 所在段落合併",
  }),
};

bind("#scenario-delete", () => navigateToFreshPage("plain-grapheme", "delete"));
bind("#scenario-backspace", () => navigateToFreshPage("plain-grapheme", "backspace"));
bind("#scenario-paragraph-start", () => navigateToFreshPage("plain-grapheme", "paragraph-start"));
bind("#scenario-paragraph-end", () => navigateToFreshPage("plain-grapheme", "paragraph-end"));

bind("#reload", () => navigateToFreshPage(fixtureSelect.value));
bind("#search", () => runOperation("選取文字", async () => {
  const query = document.querySelector("#search-text").value;
  if (!query)
    throw new Error("請輸入要尋找的文字");
  const result = await documentHandle.search(query);
  if (!result.found)
    throw new Error(`找不到文字：${query}`);
  return result;
}));
bind("#collapse-left", () => runOperation("游標到選取開頭", () =>
  editor.action("move-character-left")));
bind("#collapse-right", () => runOperation("游標到選取結尾", () =>
  editor.action("move-character-right")));
bind("#delete-backward", () => runOperation("Backspace", () =>
  editor.action("delete-backward", { manualObservation: true }), { manual: true }));
bind("#delete-forward", () => runOperation("Delete", () =>
  editor.action("delete-forward", { manualObservation: true }), { manual: true }));
bind("#insert", () => runOperation("插入文字", () => {
  const text = document.querySelector("#insert-text").value;
  if (!text)
    throw new Error("請輸入文字");
  return documentHandle.insertText(text);
}));
bind("#paragraph-break", () => runOperation("段落換行", () =>
  editor.action("insert-paragraph-break")));
bind("#line-break", () => runOperation("行內換行", () =>
  editor.action("insert-line-break")));
bind("#save", () => runOperation("儲存 ODT", async () => {
  const buffer = await documentHandle.save({ format: "odt" }, { timeoutMs: 180000 });
  const url = URL.createObjectURL(new Blob([buffer], { type: "application/vnd.oasis.opendocument.text" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `e1-manual-${metrics.fixture}-r${documentHandle.revision}.odt`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return { bytes: buffer.byteLength, revision: documentHandle.revision };
}));

canvas.addEventListener("click", (event) => runOperation("點擊放置游標", async () => {
  const bounds = canvas.getBoundingClientRect();
  const xPx = (event.clientX - bounds.left) * canvas.width / bounds.width;
  const yPx = (event.clientY - bounds.top) * canvas.height / bounds.height;
  const xTwips = Math.max(0, Math.floor(renderRegion.xTwips
    + xPx / canvas.width * renderRegion.widthTwips));
  const yTwips = Math.max(0, Math.floor(renderRegion.yTwips
    + yPx / canvas.height * renderRegion.heightTwips));
  await documentHandle.click(xTwips, yTwips);
  return { xTwips, yTwips, revision: documentHandle.revision };
}));

async function initialize() {
  try {
    setBusy(true);
    const params = new URLSearchParams(location.search);
    const requestedScenario = params.get("scenario");
    corpus = await (await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })).json();
    for (const fixture of corpus.fixtures) {
      const option = document.createElement("option");
      option.value = fixture.id;
      option.textContent = fixture.id;
      fixtureSelect.append(option);
    }
    fixtureSelect.value = params.get("fixture") || "plain-grapheme";
    engine = await createDocumentEngine({
      workerUrl: "./profiles/e1-editor-discovery/sdk-worker.js",
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    await openFixture(fixtureSelect.value);
    setBusy(false);
    if (requestedScenario) {
      const runner = scenarioRunners[requestedScenario];
      if (!runner)
        throw new Error(`unknown scenario: ${requestedScenario}`);
      const cleanUrl = new URL(location.href);
      cleanUrl.searchParams.delete("scenario");
      cleanUrl.searchParams.delete("instance");
      history.replaceState(null, "", cleanUrl.href);
      scenarioResult.textContent = `正在執行 ${requestedScenario}…`;
      await runner();
    }
  } catch (error) {
    metrics.lastError = errorValue(error);
    metrics.phase = "failed";
    metrics.ready = false;
    log("初始化失敗", metrics.lastError);
    status.textContent = "初始化失敗";
  }
}

window.addEventListener("beforeunload", () => engine?.dispose());
initialize();
