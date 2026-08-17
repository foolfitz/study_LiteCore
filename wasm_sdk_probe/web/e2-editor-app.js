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
  openFile: $("#open-file"), file: $("#file"),
  clearFormat: $("#clear-format"),
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
// The last tile the engine painted, kept so a caret move can be drawn without
// asking for pixels again (finding 058).  Cleared on resize, where the canvas
// changes size and the cached pixels stop describing it.
let lastTile = null;

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
  // Finding 058.  The caret arrives as a state update, not as a document
  // change, so redrawing only on render would leave it a gesture behind.
  paint();
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
  // Show the state for the two formats the engine can actually answer for, and
  // for no others.  `aria-pressed` is only set when the answer is known: a
  // button that renders a state it is guessing at is the trap the toggle bug
  // already was, one layer up.  Underline and strikethrough get no pressed
  // state because core keeps no cache for them.
  for (const action of ["set-bold", "set-italic"]) {
    const button = el.toolbar.querySelector(`[data-action="${action}"]`);
    if (!button) continue;
    const state = formatStateFor(action);
    if (state === null) button.removeAttribute("aria-pressed");
    else button.setAttribute("aria-pressed", state ? "true" : "false");
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
  // Setting width/height clears the canvas AND invalidates the cached tile,
  // which is sized in device pixels for the old dimensions.
  lastTile = null;
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
    lastTile = new ImageData(
      new Uint8ClampedArray(tile.pixels), tile.width, tile.height);
    paint();
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

/**
 * Finding 058: draw the caret and the selection.
 *
 * The engine has always sent both -- `caret` and `selection.rectangles` reach
 * the page in `editorState`, and the page used the rectangles only to COUNT
 * them for gesture shape.  Its one drawing call pasted the tile.  LOK does not
 * paint the text cursor or the selection into tiles; they arrive as callback
 * rectangles for the client to draw, and the client never did.  So a user
 * clicked and saw nothing move, dragged and saw nothing highlight.
 *
 * Nine product-path checks were green throughout, because every one of them
 * reads the DOM or the saved ODT -- and all of those pass on a page that draws
 * nothing at all.
 *
 * The tile is cached so the overlay can be repainted on a caret move without
 * asking the engine for pixels again: a caret arriving as a state update must
 * not cost a full document render.
 */
function paint() {
  if (!lastTile) return;
  const context = el.canvas.getContext("2d");
  context.putImageData(lastTile, 0, 0);
  const editorState = session?.state?.snapshot?.editorState;
  if (!editorState || !session?.document) return;

  // Rectangles are twips in document space; the canvas is the whole document.
  const scaleX = el.canvas.width / session.document.widthTwips;
  const scaleY = el.canvas.height / session.document.heightTwips;
  const box = (r) => [r.x * scaleX, r.y * scaleY,
                      Math.max(1, r.width * scaleX),
                      Math.max(1, r.height * scaleY)];

  const rectangles = editorState.selection?.rectangles;
  if (Array.isArray(rectangles) && rectangles.length) {
    context.save();
    // Multiply keeps the glyphs readable under the wash instead of covering
    // them, which a filled rectangle at any useful opacity would do.
    context.globalCompositeOperation = "multiply";
    context.fillStyle = "#b7d3f2";
    for (const rectangle of rectangles) context.fillRect(...box(rectangle));
    context.restore();
  }

  // The caret last, so it is never washed over by the selection it sits in.
  // Drawn only when the selection is collapsed: LOK keeps sending a cursor
  // rectangle during a range selection, and painting a caret in the middle of
  // a highlight says something about the document that is not true.
  const caret = editorState.caret;
  if (caret && editorState.selection?.collapsed !== false) {
    const [x, y, , height] = box(caret);
    context.save();
    context.fillStyle = "#1a1a1a";
    context.fillRect(x, y, Math.max(1, Math.round(scaleX * 15)), height);
    context.restore();
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
           : recovery === "restart" ? "（需要重新開啟文件）"
           // Finding 046's residual.  Says dispatched-and-unverified, and does
           // NOT say it worked -- the barrier did not verify it.  Undo is
           // named because "review" leaves the queue open, which is the only
           // reason that advice is honest.
           : recovery === "review"
             ? "（動作已送出，但這一格的檢查涵蓋了不只一個段落，無法單獨核對你的段落。"
               + "請看一下結果，不是你要的就按「復原」。這是檢查的極限，不是文件壞了）"
           : ""), true);
    throw error;
  }
}

// Finding 045, the product half.  The ENGINE has taken an explicit boolean
// since the v3 link -- `inlineFormatArgument` builds
// {"Bold":{"type":"boolean","value":...}} from it -- and this line sent `true`
// unconditionally, so from a user's seat bold could be turned on and never off.
// The fix shipped in the artifact and the page never used it.
//
// Bold and italic are decided from state: the worker already projects
// `format: {bold, italic}` as a tri-state (null = the engine does not know).
// Underline and strikethrough have no state to read -- core keeps no cache for
// them (probe_engine.cpp says neither is in GetKitUnoCommandList) -- so they
// stay one-way here and get their off path from 清除格式 below, which claims
// nothing about the current state.
//
// Note what the 045 fix buys beyond correctness: an explicit set is ROBUST
// under a stale read.  Guess wrong and the user presses again and it is right,
// because the second dispatch names the value it wants.  A toggle would turn a
// stale read into a silent no-op.
function formatStateFor(action) {
  const format = session?.state?.snapshot?.editorState?.format;
  if (action === "set-bold") return format?.bold ?? null;
  if (action === "set-italic") return format?.italic ?? null;
  return null;
}

async function editorAction(action) {
  const label = el.toolbar.querySelector(`[data-action="${action}"]`).textContent.trim();
  const options = FORMAT_ACTIONS.has(action)
    // `=== true` and not truthiness: null means the engine has no answer, and
    // the honest response to that is to ask for ON, which is what the button
    // says it does.
    ? { enabled: formatStateFor(action) !== true }
    : {};
  await run(label, () => session.action(action, options));
}

// Every inline format turned off in one press.  This is the off path for
// underline and strikethrough, which have no readable state, and it is honest
// precisely because it asserts nothing about what was on: it asks for off.
async function clearInlineFormatting() {
  for (const action of ["set-bold", "set-italic", "set-underline",
                        "set-strikethrough"]) {
    await run("清除格式", () => session.action(action, { enabled: false }));
  }
  toast("已清除粗體、斜體、底線、刪除線");
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

// NO paste listener here, deliberately, and it is not an oversight.
//
// Ctrl+V looks like the copy defect above -- `session.pasteEvent()` exists and
// nothing calls it -- and on 2026-08-17 a handler was written on exactly that
// reasoning.  The mutation round measured it: the marker landed in the saved
// document TWICE (markOccurrences 2, revision +2).  Paste already arrives, as
// `beforeinput` with inputType insertFromPaste, which the input adapter
// attached to this sink already commits.  Adding a page-level handler makes a
// second commit of the same text.
//
// The two cases are not the same shape after all: the canvas has no DOM
// selection for the browser to copy FROM, so copy needed the engine asked; the
// sink is a real editable target, so paste arrives on its own.  `pasteEvent()`
// is for hosts without an input sink.  `ctrl-v-reaches-the-document` in the
// product-path runner now requires EXACTLY ONE occurrence, so re-adding a
// handler here goes red rather than looking like success.

// Backspace and Delete.  NOT a keyboard shortcut -- this is the primary way
// anybody corrects a typo, and until now the product had none: the input
// adapter drops `deleteContentBackward`/`deleteContentForward` into
// `ignored-input-type` (input-adapter.js) and does not preventDefault, so the
// keys did nothing and the user had to reach for the toolbar's ⌫ button.
//
// Handled HERE and not in the adapter, deliberately: the adapter's job is to
// commit text, and deleting is an editor action with its own contracted wire
// id. Checked before writing, after the paste episode: the adapter really does
// leave these alone, so this is not a second handler for the same event.
const DELETE_INPUT_TYPES = {
  deleteContentBackward: "delete-backward",
  deleteContentForward: "delete-forward",
};

el.sink.addEventListener("beforeinput", (event) => {
  const action = DELETE_INPUT_TYPES[event.inputType];
  if (!action || !session?.document) return;
  event.preventDefault();
  void editorAction(action).catch(() => {});
});

// Arrow keys produce no `beforeinput` at all, so they need keydown. Only the
// two the contract carries: line up/down and Home/End are implemented in the
// engine but have no product wire id (see the relink queue), and offering a key
// that cannot dispatch would be worse than offering nothing.
const KEY_ACTIONS = {
  ArrowLeft: "move-character-left",
  ArrowRight: "move-character-right",
};

el.sink.addEventListener("keydown", (event) => {
  if (!session?.document) return;
  const accel = event.ctrlKey || event.metaKey;
  if (accel && event.key.toLowerCase() === "z" && !event.shiftKey) {
    // Ctrl+Z, and it earns its place: finding 046's review disposition tells
    // the user to press 復原, and until now the only way to do that was to find
    // the button.
    event.preventDefault();
    void run("復原", () => session.undo()).catch(() => {});
    return;
  }
  if (accel && event.key.toLowerCase() === "s") {
    // Without preventDefault this opens the BROWSER's save dialog, which saves
    // the page rather than the document -- an answer to the user's request that
    // is worse than no answer.
    event.preventDefault();
    void saveDocument().catch(() => {});
    return;
  }
  if (accel) return;
  const action = KEY_ACTIONS[event.key];
  if (!action) return;
  event.preventDefault();
  void editorAction(action).catch(() => {});
});

// Cut = copy, then delete what was copied.  Two dispatches rather than one
// because the contract has no cut action; the ORDER matters, since a failed
// copy must not still remove the text.
el.sink.addEventListener("cut", (event) => {
  if (!session?.document) return;
  event.preventDefault();
  void run("剪下", () => session.copySelection())
    .then((result) => session.action("delete-backward", {})
      .then(() => toast(`已剪下 ${result?.codePoints ?? "?"} 字`)))
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
  // The hidden input is unreachable once its button is disabled, but a control
  // that is only unreachable by layout is not disabled -- say it outright.
  el.file.disabled = true;
}

// The bytes are the only thing that ever differed between a bundled sample and
// a document the user chose: both end at the same `session.open({bytes, name})`.
// Splitting the fetch off is the whole of "open a real file" -- there is no
// engine side to it, which is why it does not need a link.
async function openDocument(bytes, name) {
  if (session) {
    try { await session.close(); } catch { /* a dead session must not block */ }
    session = null;
  }
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

async function openFixture(id) {
  const name = `${id}.odt`;
  const response = await fetch(`./e1-fixtures/${name}`, { cache: "no-cache" });
  if (!response.ok) throw new Error(`fixture fetch failed: ${response.status}`);
  await openDocument(await response.arrayBuffer(), name);
}

el.fixture.addEventListener("change", () => {
  void openFixture(el.fixture.value)
    .catch((error) => toast(describeError(error), true));
});

el.openFile.addEventListener("click", () => el.file.click());

el.clearFormat.addEventListener("click", () => {
  if (!session?.document) return;
  void clearInlineFormatting().catch(() => {});
});

el.file.addEventListener("change", () => {
  const file = el.file.files?.[0];
  // Clearing the input is what lets the same file be re-opened; without it a
  // second pick of the same path fires no change event at all.
  el.file.value = "";
  if (!file) return;
  // The fixture select must stop naming a document that is no longer open --
  // a control that reports the wrong document is the shape of finding 054.
  el.fixture.value = "";
  void file.arrayBuffer()
    .then((bytes) => openDocument(bytes, file.name))
    .then(() => toast(`已開啟 ${file.name}`))
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
