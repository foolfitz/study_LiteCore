import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorSession } from "./editor-shell/editor-session.js";

const $ = (selector) => document.querySelector(selector);
const elements = {
  canvas: $("#canvas"),
  input: $("#input"),
  toolbar: $("#toolbar"),
  status: $("#status"),
  revision: $("#revision"),
  message: $("#message"),
  log: $("#log"),
};

const metrics = {
  schemaVersion: 1,
  release: "E1-B-narrow-editor",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  profile: null,
  contract: null,
  operations: [],
  states: [],
  events: [],
  inputTrace: [],
  clipboardTrace: [],
  output: null,
  complete: false,
  pass: false,
  error: null,
};
globalThis.__e1_b = metrics;
globalThis.__probe_metrics = metrics;

let session = null;
let initializationPromise = null;
let latestOutput = null;
let rendering = false;
let renderAgain = false;

function log(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  elements.log.textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  elements.log.scrollTop = elements.log.scrollHeight;
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
    : snapshot.dirty ? "尚未儲存" : "已同步到最近一次authority bytes";
  elements.message.classList.toggle("error", Boolean(snapshot.error));
  const disabled = !["ready", "busy"].includes(snapshot.state);
  for (const button of elements.toolbar.querySelectorAll("button")) {
    if (button.dataset.action !== "restart")
      button.disabled = disabled;
  }
  elements.toolbar.querySelector('[data-action="restart"]').disabled =
    !["restart-required", "recoverable-error"].includes(snapshot.state);
}

function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/e1-editor-v1/sdk-worker.js",
    timeoutMs: 30000,
  });
}

async function fetchFixture() {
  const params = new URLSearchParams(location.search);
  const fixture = params.get("fixture") || "plain-grapheme";
  if (!/^[a-z0-9-]+$/.test(fixture))
    throw new Error("invalid fixture id");
  const response = await fetch(`./e1-fixtures/${fixture}.odt`, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed with HTTP ${response.status}`);
  return { bytes: await response.arrayBuffer(), name: `${fixture}.odt`, fixture };
}

async function renderDocument() {
  if (!session?.document || !["ready", "busy"].includes(session.state.snapshot.state))
    return;
  if (rendering) {
    renderAgain = true;
    return;
  }
  rendering = true;
  try {
    const tile = await session.document.render({
      xTwips: 0,
      yTwips: 0,
      widthTwips: session.document.widthTwips,
      heightTwips: session.document.heightTwips,
      canvasWidthPx: elements.canvas.width,
      canvasHeightPx: elements.canvas.height,
    }, { timeoutMs: 60000 });
    elements.canvas.getContext("2d").putImageData(new ImageData(
      new Uint8ClampedArray(tile.pixels), tile.width, tile.height,
    ), 0, 0);
  } finally {
    rendering = false;
    if (renderAgain) {
      renderAgain = false;
      void renderDocument();
    }
  }
}

async function initialize() {
  const fixture = await fetchFixture();
  session = new EditorSession({
    engineFactory,
    clipboard: navigator.clipboard,
    secureContext: globalThis.isSecureContext,
    onState: updateState,
    onEvent(event) {
      metrics.events.push(event);
      if (event.event === "document-invalidated")
        queueMicrotask(() => void renderDocument());
    },
    onInputTrace(event) {
      metrics.inputTrace.push(event);
      log({ input: event });
    },
    onClipboardTrace(event) {
      metrics.clipboardTrace.push(event);
      log({ clipboard: event });
    },
  });
  await session.open(fixture);
  session.attachInput(elements.input);
  metrics.fixture = fixture.fixture;
  metrics.profile = session.engine.manifest.profile;
  metrics.contract = session.engine.manifest.editorContract;
  await renderDocument();
  log({ type: "editor-ready", profile: metrics.profile, contract: metrics.contract });
}

async function record(name, operation) {
  const beforeRevision = session.document.revision;
  try {
    const result = await operation();
    const entry = { name, status: "passed", beforeRevision, revision: session.document.revision, result };
    metrics.operations.push(entry);
    log(entry);
    await renderDocument();
    return result;
  } catch (error) {
    const entry = { name, status: "failed", beforeRevision, error: publicError(error) };
    metrics.operations.push(entry);
    log(entry);
    throw error;
  }
}

async function searchExact(text) {
  const search = await session.document.search(text, { timeoutMs: 30000 });
  if (!search.found)
    return { found: false, text: "" };
  const selection = await session.document.getSelection({ timeoutMs: 30000 });
  return {
    found: selection.selectionType === "text" && selection.text === text,
    text: selection.text,
    selections: search.selections || [],
  };
}

function firstRectangle(search) {
  const value = search.selections?.[0]?.rectangles || "";
  const numbers = value.split(";")[0].split(",")
    .map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((value) => !Number.isFinite(value)))
    throw new Error("search did not return a usable document rectangle");
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

async function placeAtAnchorBoundary(text, boundary) {
  const found = await searchExact(text);
  if (!found.found)
    throw new Error(`test anchor not found: ${text}`);
  const rectangle = firstRectangle(found);
  const xTwips = boundary === "start"
    ? rectangle.x + 1
    : rectangle.x + Math.max(1, rectangle.width - 1);
  const yTwips = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  return session.placeCaret(xTwips, yTwips, { caretTimeoutMs: 30000 });
}

async function runAll() {
  await initializationPromise;
  if (metrics.complete)
    return metrics;
  try {
    const negative = await session.editor.action("redo").then(
      () => ({ pass: false, code: null }),
      (error) => ({ pass: error.code === "EDITOR_ACTION_UNSUPPORTED", code: error.code }),
    );
    metrics.operations.push({ name: "unsupported-redo", status: negative.pass ? "passed" : "failed", result: negative });

    await record("move-character-left", async () => {
      await placeAtAnchorBoundary("ASCII abc", "end");
      return session.moveCharacter("left");
    });
    await record("move-character-right", () => session.moveCharacter("right"));
    await record("extend-selection-left", () => session.moveCharacter("left", { extendSelection: true }));
    const selected = await session.editor.getState();
    metrics.operations.push({
      name: "typed-selection-state",
      status: selected.selectionType === "text" && selected.selection.collapsed === false ? "passed" : "failed",
      result: selected,
    });

    await placeAtAnchorBoundary("ASCII abc", "end");
    const backward = await record("delete-backward", () => session.delete("backward"));
    const backwardText = await searchExact("ASCII ab");
    metrics.operations.push({ name: "delete-backward-text", status: backwardText.found ? "passed" : "failed", result: backwardText });
    await record("undo-delete-backward", () => session.undo());

    await placeAtAnchorBoundary("0123456789", "start");
    const forward = await record("delete-forward", () => session.delete("forward"));
    const forwardText = await searchExact("123456789");
    metrics.operations.push({ name: "delete-forward-text", status: forwardText.found ? "passed" : "failed", result: forwardText });
    await record("undo-delete-forward", () => session.undo());

    await placeAtAnchorBoundary("E1-PLAIN-START", "end");
    await record("insert-text", () => session.commitText("E1B-文字😀"));
    const inserted = await searchExact("E1B-文字😀");
    metrics.operations.push({ name: "insert-text-search", status: inserted.found ? "passed" : "failed", result: inserted });
    await placeAtAnchorBoundary("E1B-文字😀", "end");
    await record("insert-paragraph-break", () => session.insertBreak("paragraph"));
    await record("paragraph-text", () => session.commitText("E1B-PARAGRAPH"));
    const paragraph = await searchExact("E1B-PARAGRAPH");
    metrics.operations.push({ name: "paragraph-search", status: paragraph.found ? "passed" : "failed", result: paragraph });
    await placeAtAnchorBoundary("E1B-PARAGRAPH", "end");
    await record("insert-line-break", () => session.insertBreak("line"));
    await record("line-text", () => session.commitText("E1B-LINE"));
    const line = await searchExact("E1B-LINE");
    metrics.operations.push({ name: "line-search", status: line.found ? "passed" : "failed", result: line });

    await searchExact("ASCII");
    await record("set-bold-on", () => session.setInlineFormat("bold", true));
    await record("set-italic-on", () => session.setInlineFormat("italic", true));
    await record("set-bold-off", () => session.setInlineFormat("bold", false));
    await record("set-italic-off", () => session.setInlineFormat("italic", false));

    await placeAtAnchorBoundary("E1B-LINE", "end");
    await record("insert-undo-marker", () => session.commitText("E1B-UNDO"));
    const beforeUndo = await searchExact("E1B-UNDO");
    await record("public-undo", () => session.undo());
    const afterUndo = await searchExact("E1B-UNDO");
    metrics.operations.push({
      name: "undo-text-postcondition",
      status: beforeUndo.found && !afterUndo.found ? "passed" : "failed",
      result: { beforeUndo, afterUndo },
    });

    let savedBytes = null;
    await record("save", async () => {
      const saved = await session.save();
      savedBytes = saved.bytes;
      return { revision: saved.revision, bytes: saved.bytes.byteLength };
    });
    latestOutput = savedBytes;
    const digest = await crypto.subtle.digest("SHA-256", latestOutput);
    metrics.output = {
      bytes: latestOutput.byteLength,
      sha256: [...new Uint8Array(digest)].map((value) => value.toString(16).padStart(2, "0")).join(""),
    };
    metrics.deleteResults = { backward, forward };
    metrics.pass = metrics.profile === "e1-editor-v1"
      && metrics.contract?.version === 1
      && metrics.operations.length >= 20
      && metrics.operations.every((entry) => entry.status === "passed")
      && metrics.states.every((state) => state.state !== "restart-required"
        && state.state !== "recoverable-error");
  } catch (error) {
    metrics.error = publicError(error);
    metrics.pass = false;
  } finally {
    metrics.complete = true;
    log({ type: "e1-b-complete", pass: metrics.pass, error: metrics.error });
  }
  return metrics;
}

async function toolbarAction(action) {
  await initializationPromise;
  const map = {
    left: () => session.moveCharacter("left"),
    right: () => session.moveCharacter("right"),
    "select-left": () => session.moveCharacter("left", { extendSelection: true }),
    "select-right": () => session.moveCharacter("right", { extendSelection: true }),
    backspace: () => session.delete("backward"),
    delete: () => session.delete("forward"),
    paragraph: () => session.insertBreak("paragraph"),
    line: () => session.insertBreak("line"),
    undo: () => session.undo(),
    bold: () => session.setInlineFormat("bold", session.state.snapshot.editorState?.format?.bold !== true),
    italic: () => session.setInlineFormat("italic", session.state.snapshot.editorState?.format?.italic !== true),
    copy: () => session.copySelection({ metadata: { source: "toolbar-user-gesture" } }),
    paste: () => session.pasteFromClipboard({
      userGesture: true,
      metadata: { source: "toolbar-user-gesture" },
    }),
    "cancel-composition": () => session.input.cancelComposition("explicit-user-cancel"),
    save: async () => { latestOutput = (await session.save()).bytes; },
    restart: () => session.restart(),
    run: () => runAll(),
  };
  if (!map[action])
    return;
  await record(`toolbar-${action}`, map[action]);
}

elements.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (action)
    void toolbarAction(action).catch((error) => log(publicError(error)));
});

elements.canvas.addEventListener("click", (event) => {
  if (!session?.document)
    return;
  const rectangle = elements.canvas.getBoundingClientRect();
  const xTwips = Math.round((event.clientX - rectangle.left) / rectangle.width
    * session.document.widthTwips);
  const yTwips = Math.round((event.clientY - rectangle.top) / rectangle.height
    * session.document.heightTwips);
  void record("canvas-click", () => session.placeCaret(xTwips, yTwips))
    .catch((error) => log(publicError(error)));
  elements.input.focus();
});

globalThis.__e1_b_run_all = runAll;
globalThis.__e1_b_get_output_base64 = () => {
  if (!latestOutput)
    return "";
  const bytes = new Uint8Array(latestOutput);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000)
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  return btoa(binary);
};

initializationPromise = initialize().catch((error) => {
  metrics.error = publicError(error);
  metrics.complete = true;
  metrics.pass = false;
  updateState({ state: "recoverable-error", revision: null, error: metrics.error });
  log(metrics.error);
});

if (new URLSearchParams(location.search).get("autorun") === "1")
  void initializationPromise.then(() => runAll());
