// SPEC E2-C 2.4: the product page for the v2 contract.
//
// It exists because a client and a session are not a product.  Until this file,
// nothing a user could open drove NarrowEditorV2Client, and `demo-structure`
// offered five of the fifteen actions with no drag selection at all -- so D5's
// "select with a real pointer drag, then press a format button" had no product
// path to run on, and measuring it in a harness would have measured the
// harness.
//
// Three things this page is careful about, each of them a rule from evidence
// rather than a preference:
//
//   * Format buttons follow a SELECTION gesture.  SPEC E2-B 5.13 makes a failed
//     dispatch recoverable by rolling back to the checkpoint that
//     `_checkpointBeforeSelection` writes before a range selection.  Press a
//     format button with no gesture in front of it and the rollback reaches
//     further back than the one action.
//
//   * The toolbar never shows what the paragraph currently IS.  Route C does
//     not read the precondition (finding 022), so an "active" button would only
//     report what this page last asked for.  What the buttons DO reflect is the
//     manifest's gesture declaration for the current selection shape, which is
//     a statement about the contract rather than about the document.
//
//   * A dispatched failure is recovered by rolling back, not by undo: undo goes
//     through the queue that the failure has just blocked, so the user would
//     get EDITOR_NOT_READY.  The page offers the rollback explicitly.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { EDITOR_V2_ACTIONS } from "./editor-shell-v2/narrow-editor-v2-client.js";

// The artifact this page is for.  A page that runs on whatever build happens to
// be in dist/ is a page that can show behaviour no evidence covers.
const PINNED_WASM_SHA256 = "d538ce0b91478426";

const $ = (selector) => document.querySelector(selector);
const el = {
  canvas: $("#canvas"), paper: $("#paper"), desk: $("#desk"), sink: $("#sink"),
  toolbar: $("#toolbar"), fixture: $("#fixture"), text: $("#text"),
  statePill: $("#state-pill"), toast: $("#toast"), expired: $("#expired"),
  notice: $("#notice"), noticeText: $("#notice-text"),
  noticeAction: $("#notice-action"),
  pinnedHash: $("#pinned-hash"), expectedHash: $("#expected-hash"),
  actualHash: $("#actual-hash"),
  s: { state: $("#s-state"), revision: $("#s-revision"), pending: $("#s-pending"),
       generation: $("#s-generation"), checkpoint: $("#s-checkpoint"),
       latency: $("#s-latency"), doc: $("#s-doc") },
};

const MAX_BACKING_WIDTH = 2400;
const MOVE_ACTIONS = new Set(["move-character-left", "move-character-right"]);
const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

let session = null;
let documentName = "—";
let rendering = false;
let renderAgain = false;
let lastSelectionShape = "collapsed";

function toast(message, bad = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("bad", bad);
  el.toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.toast.classList.remove("show"), 4000);
}

function describeError(error) {
  const code = error?.code ? `${error.code}：` : "";
  return `${code}${error?.message || String(error)}`;
}

/* ------------------------------------------------------------------ state */

function updateState(snapshot) {
  el.statePill.dataset.state = snapshot.state;
  el.statePill.textContent = {
    idle: "未開啟", loading: "載入中", ready: "就緒", busy: "處理中",
    "recoverable-error": "需要回復", "restart-required": "需要重新開啟",
    stopped: "已停止",
  }[snapshot.state] ?? snapshot.state;
  el.s.state.textContent = snapshot.state;
  el.s.revision.textContent = snapshot.revision ?? "—";
  el.s.pending.textContent = snapshot.pending ?? "—";
  el.s.generation.textContent = snapshot.generation ?? "—";
  el.s.checkpoint.textContent = snapshot.hasCheckpoint
    ? `有（r${snapshot.checkpointRevision ?? "?"}）`
    : snapshot.checkpointError ? "寫入失敗" : "無";
  const recoverable = ["recoverable-error", "restart-required"]
    .includes(snapshot.state);
  el.notice.dataset.show = recoverable ? "1" : "0";
  if (recoverable) {
    el.noticeText.textContent = snapshot.hasCheckpoint
      ? "這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。"
      : "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。";
    el.noticeAction.textContent = snapshot.hasCheckpoint
      ? "回到檢查點" : "重新開啟";
    // Finding 054: this read `snapshot.requiresPageReload`, and nothing writes
    // that name at the top level of a snapshot -- the flag lives in the error's
    // details (`editor-session.js`, at the generation ceiling), which is where
    // the v1 component reads it from.  So the button never disabled, and at the
    // ceiling it pointed the user at a control guaranteed to refuse them.
    // Both conditions, like recovery-notice.js: the code alone is enough.
    el.noticeAction.disabled =
      snapshot.error?.code === "WORKER_GENERATION_LIMIT"
      || snapshot.error?.details?.requiresPageReload === true;
  }
  updateGestureAffordance();
}

/**
 * Grey a button out when the manifest does not offer that action for the shape
 * of selection currently in front of it.
 *
 * SPEC E2-C 2.5: the declaration for the ten inherited actions is `collapsed`
 * only, and the engine does not enforce it -- the mask is read on the paragraph
 * route alone.  The honest place to surface a narrowing nothing enforces is the
 * button, not a failure after the fact.
 */
function updateGestureAffordance() {
  if (!session?.editor) return;
  for (const button of el.toolbar.querySelectorAll("button[data-action]")) {
    const action = button.dataset.action;
    if (!EDITOR_V2_ACTIONS.includes(action)) continue;
    const gestures = session.gesturesFor(action);
    const offered = !Array.isArray(gestures) || gestures.includes(lastSelectionShape);
    button.disabled = !offered;
    button.title = offered ? "" :
      `manifest 沒有為「${lastSelectionShape}」宣告這個動作`;
  }
}

/* ----------------------------------------------------------------- canvas */

function layoutCanvas() {
  if (!session?.document) return;
  const available = Math.max(320, el.desk.clientWidth - 40);
  const cssWidth = Math.min(available, 900);
  const ratio = session.document.heightTwips / session.document.widthTwips;
  const backingWidth = Math.min(MAX_BACKING_WIDTH,
                                Math.round(cssWidth * (globalThis.devicePixelRatio || 1)));
  el.canvas.width = backingWidth;
  el.canvas.height = Math.round(backingWidth * ratio);
  el.canvas.style.width = `${cssWidth}px`;
  el.canvas.style.height = `${Math.round(cssWidth * ratio)}px`;
}

async function renderDocument(retriesLeft = 6) {
  if (!session?.document
      || !["ready", "busy"].includes(session.state.snapshot.state))
    return;
  if (rendering) { renderAgain = true; return; }
  rendering = true;
  try {
    const tile = await session.document.render({
      xTwips: 0, yTwips: 0,
      widthTwips: session.document.widthTwips,
      heightTwips: session.document.heightTwips,
      canvasWidthPx: el.canvas.width,
      canvasHeightPx: el.canvas.height,
    }, { timeoutMs: 60000 });
    el.canvas.getContext("2d").putImageData(new ImageData(
      new Uint8ClampedArray(tile.pixels), tile.width, tile.height), 0, 0);
  } catch (error) {
    // A repaint that lands while a barrier is still settling comes back BUSY.
    // The canvas is a frame behind; the document is fine.
    if (error?.code === "BUSY" && retriesLeft > 0) {
      await new Promise((resolve) => setTimeout(resolve, 120));
      rendering = false;
      return renderDocument(retriesLeft - 1);
    }
    toast(`重繪失敗：${describeError(error)}`, true);
  } finally {
    rendering = false;
    if (renderAgain) { renderAgain = false; void renderDocument(); }
  }
}

function pointToTwips(event) {
  const rectangle = el.canvas.getBoundingClientRect();
  return {
    xTwips: Math.max(0, Math.round(
      (event.clientX - rectangle.left) / rectangle.width
      * session.document.widthTwips)),
    yTwips: Math.max(0, Math.round(
      (event.clientY - rectangle.top) / rectangle.height
      * session.document.heightTwips)),
  };
}

/* ---------------------------------------------------------------- actions */

async function run(label, operation) {
  const started = performance.now();
  try {
    const result = await operation();
    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    await renderDocument();
    return result;
  } catch (error) {
    el.s.latency.textContent = `${label} 失敗`;
    // The disposition is a field, not a guess from the message (E2-B 5.13).
    const recovery = error?.recovery;
    toast(`${label}：${describeError(error)}` +
          (recovery === "rollback" ? "（可能已經改到文件：請回到檢查點）"
           : recovery === "restart" ? "（需要重新開啟文件）" : ""), true);
    throw error;
  }
}

async function editorAction(action) {
  const label = el.toolbar.querySelector(`[data-action="${action}"]`).textContent.trim();
  const options = FORMAT_ACTIONS.has(action) ? { enabled: true } : {};
  await run(label, () => session.action(action, options));
}

async function insertText() {
  const text = el.text.value;
  if (!text) { toast("先在欄位裡輸入要插入的文字", true); return; }
  await run("插入文字", () => session.commitText(text));
}

async function saveDocument() {
  // `EditorSession.save()` resolves to {bytes, revision, contentStamp}, not to
  // the bytes.  Taking the whole result made `new Blob([result])` stringify it,
  // so every save from this button wrote 15 bytes of "[object Object]" and the
  // toast below reported NaN KB -- finding 049, found by an operator pressing
  // the button, because every harness in this tree calls session.save() itself
  // and destructures.
  const { bytes } = await run("儲存", () => session.save());
  const url = URL.createObjectURL(
    new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = documentName.replace(/\.odt$/i, "") + "-v2.odt";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  toast(`已存出 ${(bytes.byteLength / 1024).toFixed(1)} KB`);
}

el.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (!action || !session) return;
  const handler =
    action === "undo" ? () => run("復原", () => session.undo())
    : action === "insert-text" ? () => insertText()
    : action === "save" ? () => saveDocument()
    : EDITOR_V2_ACTIONS.includes(action) ? () => editorAction(action)
    : null;
  if (handler) void Promise.resolve(handler()).catch(() => {});
});

el.noticeAction.addEventListener("click", () => {
  void run("回到檢查點", () => session.rollback())
    .then(() => renderDocument())
    .catch(() => {});
});

/* ------------------------------------------------------------------- drag */

// A real pointer drag through this page's own handler.  Coordinates, not
// synthesised mouse events: SPEC E1-D 2.1 measured the synthesised path
// reporting a selection it had not made.
const drag = { active: false, start: null, latest: null, inFlight: false,
  pointerId: null };

async function pumpDrag() {
  if (drag.inFlight || !drag.latest || !session?.editor) return;
  const end = drag.latest;
  drag.latest = null;
  drag.inFlight = true;
  try {
    const result = await session.selectRange(drag.start, end);
    // What the engine read back, not what we asked for.
    lastSelectionShape = (result?.rectangles?.length ?? 0) > 1
      ? "range-cross" : (result?.collapsed === false ? "range-single" : "collapsed");
    updateGestureAffordance();
  } catch {
    // A refused range must not abort the gesture.
  } finally {
    drag.inFlight = false;
    if (drag.latest) void pumpDrag();
  }
}

function endDrag(event) {
  if (!drag.active) return;
  drag.active = false;
  if (drag.pointerId !== null) {
    try { el.canvas.releasePointerCapture(drag.pointerId); } catch { /* gone */ }
    drag.pointerId = null;
  }
  if (!session?.document || !event) return;
  const end = pointToTwips(event);
  if (end.xTwips === drag.start.xTwips && end.yTwips === drag.start.yTwips)
    return;   // a click is a zero-length drag; leave the caret where it landed
  drag.latest = end;
  void pumpDrag();
}

el.canvas.addEventListener("pointerdown", (event) => {
  if (!session?.document || event.button !== 0) return;
  event.preventDefault();
  const point = pointToTwips(event);
  el.sink.focus({ preventScroll: true });
  drag.active = true;
  drag.start = point;
  drag.latest = null;
  drag.pointerId = event.pointerId;
  try { el.canvas.setPointerCapture(event.pointerId); }
  catch { drag.pointerId = null; }
  lastSelectionShape = "collapsed";
  void run("定位游標", () => session.placeCaret(point.xTwips, point.yTwips))
    .then(() => updateGestureAffordance())
    .catch(() => {});
});

// Ctrl+C.  The document is a canvas, so the browser's default copy has no DOM
// selection to take and puts nothing on the clipboard -- which is why four
// operator rounds of the D5 clipboard cell pasted either nothing or whatever
// had been copied from some other application earlier.  The shell has always
// had `copySelection()`, which asks the ENGINE for the selected text; nothing
// called it.
el.sink.addEventListener("copy", (event) => {
  if (!session?.document) return;
  event.preventDefault();
  void run("複製", () => session.copySelection())
    .then((result) => toast(`已複製 ${result?.codePoints ?? "?"} 字`))
    .catch(() => {});
});

el.canvas.addEventListener("pointermove", (event) => {
  if (!drag.active || !session?.document) return;
  if ((event.buttons & 1) === 0) { endDrag(event); return; }
  drag.latest = pointToTwips(event);
  void pumpDrag();
});

el.canvas.addEventListener("pointerup", endDrag);
el.canvas.addEventListener("pointercancel", () => endDrag(null));
globalThis.addEventListener("blur", () => endDrag(null));
globalThis.addEventListener("resize", () => {
  layoutCanvas();
  void renderDocument();
});

/* ------------------------------------------------------------------- boot */

// SPEC E2-C section 11: round two's product is the v3 artifact.
//
// Hard-coded, not a query parameter.  A product page that takes its engine from
// the URL is a page whose evidence does not say which engine it measured, and
// round one bound four hashes precisely because that had been left implicit.
// The harness pages (`e2-c-d*-app.js`) do take `?profile=`; they are harnesses.
function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/e2-editor-v3/sdk-worker.js",
    timeoutMs: 30000,
  });
}

function showExpired(details) {
  el.expired.style.display = "block";
  el.paper.style.display = "none";
  el.expectedHash.textContent = details?.expected ?? PINNED_WASM_SHA256;
  el.actualHash.textContent = details?.actual ?? "（manifest 沒有提供）";
  el.statePill.dataset.state = "expired";
  el.statePill.textContent = "已過期";
  for (const button of el.toolbar.querySelectorAll("button"))
    button.disabled = true;
  el.fixture.disabled = true;
}

async function openFixture(id) {
  if (session) {
    try { await session.close(); } catch { /* a dead session must not block */ }
    session = null;
  }
  const name = `${id}.odt`;
  const response = await fetch(`./e1-fixtures/${name}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  const bytes = await response.arrayBuffer();
  session = new NarrowEditorV2Session({
    engineFactory,
    clipboard: navigator.clipboard,
    secureContext: globalThis.isSecureContext,
    onState: updateState,
    onEvent(event) {
      if (event.event === "document-invalidated")
        queueMicrotask(() => void renderDocument());
    },
    // Finding 050 was invisible for as long as it existed because these two
    // callbacks were never wired: the input adapter rejected every commit after
    // the first, said so in its trace, and the trace went nowhere.  A rejection
    // the user cannot see is a rejection nobody reports.
    //
    // Only failures surface -- a toast per keystroke would be its own defect.
    onInputTrace(entry) {
      if (entry?.action === "composition-rejected" || entry?.status === "failed")
        toast(`輸入未送出：${entry.reason || entry.code || entry.action}`, true);
    },
    onClipboardTrace(entry) {
      if (entry?.status === "failed" || entry?.status === "rejected")
        toast(`剪貼簿未完成：${entry.code || entry.status}`, true);
    },
  });
  await session.open({ bytes, name });
  session.attachInput(el.sink);
  const actual = session.engine.manifest?.editorContract?.wasmSha256 ?? "";
  if (!actual.startsWith(PINNED_WASM_SHA256)) {
    showExpired({ expected: PINNED_WASM_SHA256, actual: actual.slice(0, 16) });
    throw Object.assign(new Error("this build is not the one this page describes"),
                        { code: "PAGE_BUILD_MISMATCH" });
  }
  documentName = name;
  el.s.doc.textContent = name;
  layoutCanvas();
  await renderDocument();
  updateGestureAffordance();
}

el.fixture.addEventListener("change", () => {
  void openFixture(el.fixture.value)
    .catch((error) => toast(describeError(error), true));
});

void (async () => {
  el.pinnedHash.textContent = PINNED_WASM_SHA256;
  if (!globalThis.crossOriginIsolated)
    toast("此頁需要 cross-origin isolation：請以 web/serve.py 提供", true);
  const manifest = await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })
    .then((value) => value.json());
  el.fixture.replaceChildren(...manifest.fixtures.map((fixture) => {
    const option = document.createElement("option");
    option.value = fixture.id;
    option.textContent = fixture.id;
    return option;
  }));
  el.fixture.value = "list-contexts";
  await openFixture(el.fixture.value);
  toast("點一下放游標，或拖曳選一段，再按動作");
})().catch((error) => {
  if (error?.code === "PAGE_BUILD_MISMATCH") return;
  el.statePill.dataset.state = "stopped";
  el.statePill.textContent = "錯誤";
  toast(describeError(error), true);
});
