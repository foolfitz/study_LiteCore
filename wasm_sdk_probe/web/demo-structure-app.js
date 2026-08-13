// LiteCore structure demo -- BLOCKED, see finding 039.
//
// Headings and lists, on the artifact whose evidence describes them.
//
// It does not work yet, and the reason is not in this file: on the discovery
// ABI there is no usable way to put the insertion point where the user
// clicked.  The reset method never returns from its second call and takes the
// handle with it; the SDK click reports success and moves nothing; a range
// selection starts timing out after the first format action.  The only path
// still standing is the sweep harness's (search for known text, then reset),
// which is not a gesture and dispatches from a selection state A3/A4/A5 never
// measured.  Everything else here -- the artifact pin, the narrowed surface,
// the serialised queue, the tests -- is finished and correct.
//
// Task #36 asked for these in the shipped editor.  That is E2-B by SPEC
// E2-000's own definition, and E2-000 section 5 fixes the order E2-A -> E2-B,
// forbids freezing a new ABI before E2-A is done, and does not pre-authorise
// the E2-B spec.  E2-A has no verdict yet.  So this shell shows the five
// paragraph actions where they *were* measured -- the isolated
// e2-format-discovery profile -- instead of promoting them into the product
// contract on evidence that does not cover a product build.
//
// Three things follow, and they are the whole design:
//
//   * It refuses to run on any other build (StructureDemoClient's pin), and
//     shows the hash it is pinned to.  Disposable by design.
//   * Its surface is narrower than the ABI underneath it.  The forbidden set
//     and the reasons live in e2/demo-structure-client.js.
//   * It never claims to be the product editor, in the page and in the code.
//
// Text insertion and save go through the Document SDK's own capabilities, not
// the diagnostic editor ABI: those are product paths R5/E1 validated, and
// using them here keeps the diagnostic surface to the five actions plus bold
// and italic.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { StructureDemoClient, PINNED_WASM_SHA256 }
  from "./e2/demo-structure-client.js";

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
const intent = { "set-bold": null, "set-italic": null };

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
    toast(`${label}：${describeError(error)}`, true);
    setState("ready", "就緒");
    throw error;
  }
}

async function applyStructure(action) {
  await run(el.toolbar.querySelector(`[data-action="${action}"]`).textContent,
            () => client.action(action));
  for (const key of Object.keys(intent))
    intent[key] = null;
}

async function applyInline(action) {
  const next = intent[action] !== true;
  await run(action === "set-bold" ? "粗體" : "斜體",
            () => client.action(action, { enabled: next }));
  intent[action] = next;
}

async function insertText() {
  const text = el.text.value;
  if (!text) {
    toast("先在欄位裡輸入要插入的文字", true);
    return;
  }
  await run("插入文字", () => document_.insertText(text, { timeoutMs: 30000 }));
  for (const key of Object.keys(intent))
    intent[key] = null;
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
  "set-paragraph-heading": () => applyStructure("set-paragraph-heading"),
  "set-paragraph-body": () => applyStructure("set-paragraph-body"),
  "set-list-unordered": () => applyStructure("set-list-unordered"),
  "set-list-ordered": () => applyStructure("set-list-ordered"),
  "set-list-none": () => applyStructure("set-list-none"),
  "set-bold": () => applyInline("set-bold"),
  "set-italic": () => applyInline("set-italic"),
  "insert-text": () => insertText(),
  save: () => saveDocument(),
};

el.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (ACTIONS[action])
    void Promise.resolve(ACTIONS[action]()).catch(() => {});
});

el.canvas.addEventListener("pointerdown", (event) => {
  if (!document_ || event.button !== 0)
    return;
  event.preventDefault();
  const rectangle = el.canvas.getBoundingClientRect();
  const xTwips = Math.max(0, Math.round(
    (event.clientX - rectangle.left) / rectangle.width * document_.widthTwips));
  const yTwips = Math.max(0, Math.round(
    (event.clientY - rectangle.top) / rectangle.height * document_.heightTwips));
  for (const key of Object.keys(intent))
    intent[key] = null;
  void run("選取這一行", () => client.selectLineAt(xTwips, yTwips, { timeoutMs: 30000 }))
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
  client = new StructureDemoClient(document_);
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
    workerUrl: "./profiles/e2-format-discovery/sdk-worker.js",
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
