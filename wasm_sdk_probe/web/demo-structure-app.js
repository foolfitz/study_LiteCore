// LiteCore structure demo -- the PRODUCT shell.
//
// Headings and lists on the product v2 artifact, through the product v2 client.
// It replaces the bench that shipped these actions on the diagnostic ABI; that
// bench is kept, unedited, as `demo-structure-discovery.html`, because it is
// part of E2-A's evidence and is pinned to the artifact that evidence was
// measured on.
//
// Derived from the bench rather than written afresh: the rendering, caret
// placement and serialisation were already product paths, and rewriting working
// code to make a new file look new is how demos acquire bugs the old one had
// already fixed.  What changed is the part that matters -- the client, the
// profile, and the pin.
//
// Two contract facts the page has to respect, both from SPEC E2-B:
//
//   * The format buttons follow a SELECTION gesture.  Section 5.13 makes a
//     failed dispatch recoverable by rolling back to the checkpoint that
//     `_checkpointBeforeSelection` writes before a range selection -- so the
//     checkpoint is only there if a selection preceded the press.  Pressing a
//     format button with no preceding gesture would roll back further than the
//     one action, and the demo must not model that.
//
//   * The toolbar does not show what the paragraph currently is.  Route C never
//     reads the precondition (finding 022), so a button that looked "active"
//     would be reporting only what this shell last did, which is worse than
//     showing nothing.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { ParagraphEditorClient } from "./editor-shell-v2/paragraph-editor-client.js";
import { recoveryFor } from "./editor-shell-v2/paragraph-editor-session.js";

// The artifact this demo is for.  A demo that silently runs on whatever build
// happens to be in dist/ is a demo that can show behaviour no evidence covers.
const PINNED_WASM_SHA256 =
  "572035accd0f2754";

const $ = (selector) => document.querySelector(selector);
const el = {
  canvas: $("#canvas"), paper: $("#paper"), caret: $("#caret"), desk: $("#desk"),
  toolbar: $("#toolbar"), fixture: $("#fixture"), text: $("#text"),
  statePill: $("#state-pill"), toast: $("#toast"), expired: $("#expired"),
  pinnedHash: $("#pinned-hash"), expectedHash: $("#expected-hash"),
  actualHash: $("#actual-hash"),
  s: { state: $("#s-state"), revision: $("#s-revision"), caret: $("#s-caret"),
       latency: $("#s-latency"), doc: $("#s-doc") },
};

const MAX_BACKING_WIDTH = 2400;
const SCALE = 15;   // twips per CSS pixel at 100%

let engine = null;
let document_ = null;
let client = null;
let documentName = "—";
let rendering = false;
let renderAgain = false;
// What we last asked for since the caret last moved.  Same rule as the product
// demo: finding 021 showed the engine's cached format state is not refreshed by
// caret movement, so the only honest source for a toggle is our own intent.

function toast(message, bad = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("bad", bad);
  el.toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.toast.classList.remove("show"), 3000);
}

function setState(state, label = state) {
  el.statePill.dataset.state = state;
  el.statePill.textContent = label;
  el.s.state.textContent = label;
  const usable = state === "ready";
  for (const button of el.toolbar.querySelectorAll("button"))
    button.disabled = !usable;
  el.fixture.disabled = !usable;
}

function describeError(error) {
  return `${error?.code || error?.name || "ERROR"}：${error?.message || String(error)}`;
}

function layoutCanvas() {
  const width = Math.round(document_.widthTwips / SCALE);
  const height = Math.round(document_.heightTwips / SCALE);
  const ratio = Math.min(globalThis.devicePixelRatio || 1,
                         MAX_BACKING_WIDTH / Math.max(width, 1));
  el.canvas.style.width = `${width}px`;
  el.canvas.style.height = `${height}px`;
  el.paper.style.width = `${width}px`;
  el.paper.style.height = `${height}px`;
  el.canvas.width = Math.max(1, Math.round(width * ratio));
  el.canvas.height = Math.max(1, Math.round(height * ratio));
}

async function renderDocument() {
  if (!document_)
    return;
  if (rendering) {
    renderAgain = true;
    return;
  }
  rendering = true;
  try {
    const tile = await document_.render({
      xTwips: 0, yTwips: 0,
      widthTwips: document_.widthTwips, heightTwips: document_.heightTwips,
      canvasWidthPx: el.canvas.width, canvasHeightPx: el.canvas.height,
    }, { timeoutMs: 60000 });
    el.canvas.getContext("2d").putImageData(
      new ImageData(new Uint8ClampedArray(tile.pixels), tile.width, tile.height), 0, 0);
  } finally {
    rendering = false;
    if (renderAgain) {
      renderAgain = false;
      void renderDocument();
    }
  }
}

function paintCaret(caret) {
  // The discovery state reports the caret as bare geometry, with no
  // `available` flag -- that field belongs to the product state shape, and
  // checking for it here made the indicator read "-" on every gesture while
  // the caret was in fact moving.
  if (!caret || !Number.isFinite(caret.x)) {
    el.caret.style.display = "none";
    el.s.caret.textContent = "—";
    return;
  }
  el.caret.style.display = "block";
  el.caret.style.left = `${caret.x / SCALE}px`;
  el.caret.style.top = `${caret.y / SCALE}px`;
  el.caret.style.height = `${Math.max(caret.height, 120) / SCALE}px`;
  el.s.caret.textContent = `${caret.x}, ${caret.y} twips`;
}

async function refresh() {
  const state = await client.getState({ timeoutMs: 30000 });
  el.s.revision.textContent = state.revision ?? "—";
  paintCaret(state.caret);
  await renderDocument();
}

// One engine operation at a time.  The engine refuses a second
// callback-correlated operation with BUSY while one is in flight, and a person
// clicking two toolbar buttons in a second is not doing anything wrong -- the
// product shell absorbs exactly this with EditorSession's queue, and a demo
// without one turns ordinary use into an error message.  Found by driving this
// page from a script fast enough to overlap two caret placements.
let pending = Promise.resolve();

function serial(task) {
  // `task` runs whether or not the previous one failed; the chain itself is
  // kept unrejected so one failure cannot wedge every later gesture.
  const next = pending.then(task, task);
  pending = next.then(() => {}, () => {});
  return next;
}

async function run(label, operation) {
  const started = performance.now();
  setState("busy", "處理中");
  try {
    // The readback is inside the chain, not after it.  With it outside, the
    // next gesture could start while this one's getState was still in flight
    // and the engine answered BUSY -- which is what happened the first time,
    // and it was the *refresh* colliding, not two user gestures.
    const result = await serial(async () => {
      const value = await operation();
      await refresh();
      return value;
    });
    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    setState("ready", "就緒");
    return result;
  } catch (error) {
    el.s.latency.textContent = `${label} 失敗`;
    // MUTATION_OUTCOME_UNKNOWN is not "nothing happened": route C dispatches
    // unconditionally and only the check was skipped, so the message the engine
    // writes is addressed to the person looking at the document.  Passing it
    // through verbatim is the point -- summarising it would drop the part that
    // tells them to look and undo.
    // SPEC E2-B 5.13: what the host should DO is a field, not a guess from the
    // message.  "rollback" means reopen from the checkpoint -- not "press undo",
    // which cannot run while the queue is blocked by this same failure.
    const recovery = recoveryFor(error);
    toast(`${label}：${describeError(error)}` +
          (recovery === "rollback" ? "（這一步可能已經改到文件：請從上一個檢查點重開）"
           : recovery === "restart" ? "（需要重新開啟文件）" : ""), true);
    setState("ready", "就緒");
    throw error;
  }
}

async function applyStructure(action) {
  await run(el.toolbar.querySelector(`[data-action="${action}"]`).textContent,
            () => client.action(action));
}

// Bold and italic are v1 actions and are NOT on the v2 paragraph client.  The
// bench had them because it drove the diagnostic ABI, which carries both; this
// shell would have to instantiate the v1 client beside the v2 one to offer
// them, and a demo that quietly runs two contracts at once is a demo nobody can
// read a result off.  The buttons are gone from the toolbar rather than left
// present and dead.

// Undo goes through the Document SDK, not through client.action("undo").
//
// The diagnostic build exports an undo action of its own, and
// e2/demo-structure-client.js names it in FORBIDDEN rather than merely leaving
// it out: it is not the path E1 validated.  A button people press after every
// mistake is the last place to put an unmeasured path, so this calls the same
// document_.undo() that demo-editor's 復原 calls -- the one the shipped editor's
// evidence covers.
//
// (The intent ledger the bench kept for bold and italic is gone along with
// those buttons: there is no toggle on this shell to remember, and a ledger
// nothing reads would suggest one exists.  It was there because after an undo,
// what we last asked for is no longer what the paragraph is.)
async function undoLast() {
  await run("復原", () => document_.undo({ timeoutMs: 30000 }));
}

async function insertText() {
  const text = el.text.value;
  if (!text) {
    toast("先在欄位裡輸入要插入的文字", true);
    return;
  }
  await run("插入文字", () => document_.insertText(text, { timeoutMs: 30000 }));
}

async function saveDocument() {
  const bytes = await run("儲存", () => document_.save({ format: "odt" },
                                                       { timeoutMs: 180000 }));
  const url = URL.createObjectURL(
    new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = documentName.replace(/\.odt$/i, "") + "-structure.odt";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  toast(`已存出 ${(bytes.byteLength / 1024).toFixed(1)} KB，可用桌面版 LibreOffice 開啟`);
}

const ACTIONS = {
  undo: () => undoLast(),
  "set-paragraph-heading": () => applyStructure("set-paragraph-heading"),
  "set-paragraph-body": () => applyStructure("set-paragraph-body"),
  "set-list-unordered": () => applyStructure("set-list-unordered"),
  "set-list-ordered": () => applyStructure("set-list-ordered"),
  "set-list-none": () => applyStructure("set-list-none"),
  "insert-text": () => insertText(),
  save: () => saveDocument(),
};

el.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (ACTIONS[action])
    void Promise.resolve(ACTIONS[action]()).catch(() => {});
});

/**
 * Click, then wait for the engine to confirm a collapsed caret.
 *
 * This used to call `client.placeCaretByClick`, which exists on the DIAGNOSTIC
 * client (`e2/demo-structure-client.js`) and not on the product one -- so from
 * the migration to v2 until 2026-08-15 every click on this page threw
 * TypeError.  The page had been checked for boot, and booting was what had
 * broken the time before.
 *
 * The poll is not optional: `click` is fire-and-forget, and reading the state
 * the instant it returns gives the PREVIOUS caret.  Doing exactly that is how
 * the bench first concluded, wrongly, that clicking did nothing.  The
 * postcondition here is the product one -- the same shape
 * `EditorSession.placeCaret` waits for -- rather than the bench's "three
 * identical reads", because a confirmed collapsed caret is a statement about
 * the engine and a settled coordinate is a statement about the polling.
 */
async function placeCaret(xTwips, yTwips, options = {}) {
  await document_.click(xTwips, yTwips, options);
  const deadline = Date.now() + (options.caretTimeoutMs ?? 30000);
  let state = null;
  do {
    state = await client.getState(options);
    if (state.selectionType === "none" && state.selection?.observed === true
        && state.selection?.collapsed === true)
      return state;
    await new Promise((resolve) => setTimeout(resolve, 10));
  } while (Date.now() < deadline);
  throw Object.assign(
    new Error("click did not produce a callback-confirmed collapsed caret"),
    { code: "EDITOR_STATE_UNAVAILABLE", details: { xTwips, yTwips, state } });
}

el.canvas.addEventListener("pointerdown", (event) => {
  if (!document_ || event.button !== 0)
    return;
  event.preventDefault();
  const rectangle = el.canvas.getBoundingClientRect();
  const xTwips = Math.max(0, Math.round(
    (event.clientX - rectangle.left) / rectangle.width * document_.widthTwips));
  const yTwips = Math.max(0, Math.round(
    (event.clientY - rectangle.top) / rectangle.height * document_.heightTwips));
  void run("定位游標", () => placeCaret(xTwips, yTwips, { timeoutMs: 30000 }))
    .catch(() => {});
});

el.fixture.addEventListener("change", () => {
  void openFixture(el.fixture.value).catch((error) => toast(describeError(error), true));
});

function showExpired(error) {
  el.expired.style.display = "block";
  el.paper.style.display = "none";
  el.expectedHash.textContent = error?.details?.expected ?? PINNED_WASM_SHA256;
  el.actualHash.textContent = error?.details?.actual ?? "（manifest 沒有提供）";
  setState("expired", "已過期");
  for (const button of el.toolbar.querySelectorAll("button"))
    button.disabled = true;
  el.fixture.disabled = true;
}

async function openFixture(id) {
  setState("busy", "載入中");
  if (document_) {
    await document_.close({ timeoutMs: 30000 }).catch(() => {});
    document_ = null;
    client = null;
  }
  const name = `${id}.odt`;
  const response = await fetch(`./e1-fixtures/${name}`, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${response.status}`);
  const bytes = await response.arrayBuffer();
  document_ = await engine.open(bytes, { name, transfer: true, timeoutMs: 180000 });
  client = new ParagraphEditorClient(document_);
  // The pin, checked here rather than trusted: the profile records the hash of
  // the artifact it was built from, and this demo only claims to describe one.
  const actual = engine.manifest?.editorContract?.wasmSha256 ?? "";
  if (!actual.startsWith(PINNED_WASM_SHA256))
    throw Object.assign(new Error("this build is not the one this demo describes"),
                        { code: "DEMO_BUILD_MISMATCH",
                          details: { expected: PINNED_WASM_SHA256,
                                     actual: actual.slice(0, 16) } });
  documentName = name;
  el.s.doc.textContent = name;
  layoutCanvas();
  await refresh();
  setState("ready", "就緒");
}

void (async () => {
  el.pinnedHash.textContent = PINNED_WASM_SHA256;
  if (!globalThis.crossOriginIsolated)
    toast("此頁需要 cross-origin isolation：請以 web/serve.py 提供", true);
  engine = await createDocumentEngine({
    workerUrl: "./profiles/e2-editor-v2/sdk-worker.js",
    timeoutMs: 30000,
  });
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
  toast("點一下段落放游標，再按「標題」或「項目符號」");
})().catch((error) => {
  if (error?.code === "DEMO_ARTIFACT_EXPIRED") {
    showExpired(error);
    return;
  }
  setState("error", "錯誤");
  toast(describeError(error), true);
});
