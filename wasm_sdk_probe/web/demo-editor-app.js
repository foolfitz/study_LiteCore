// LiteCore Writer demo shell.
//
// This is a presentation front end for the frozen `e1-editor-v1` profile.  It
// adds no engine capability: every mutation goes through the same
// EditorSession / NarrowEditorClient contract that E1-B and E1-C validated, and
// the ODT is produced by the engine's own save path.
//
// Two deliberate design rules, both inherited from the findings:
//
//   * The toolbar never reads the engine's *precondition* format state.
//     Finding 021 showed that state is not refreshed by caret movement in this
//     build, and finding 022 showed that trusting it produces a silent no-op.
//     Product route C is "do not read the precondition": bold/italic dispatch
//     an explicit boolean, and the button only ever reflects what *we* last
//     asked for since the caret last moved.  After a caret move the intent is
//     unknown, and the button says so.
//
//   * Unsupported actions are refused visibly.  Line navigation (finding 018),
//     redo and structural editing are not in the contract; pressing those keys
//     tells the operator instead of silently doing nothing.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorSession } from "./editor-shell/editor-session.js";
import { recoveryNotice } from "./editor-shell/recovery-notice.js";

const $ = (selector) => document.querySelector(selector);
const el = {
  canvas: $("#canvas"),
  overlay: $("#overlay"),
  comments: $("#comments"),
  paper: $("#paper"),
  desk: $("#desk"),
  sink: $("#sink"),
  sinkMirror: $("#sink-mirror"),
  toolbar: $("#toolbar"),
  fixture: $("#fixture"),
  file: $("#file"),
  statePill: $("#state-pill"),
  engineProfile: $("#engine-profile"),
  zoomLabel: $("#zoom-label"),
  toast: $("#toast"),
  about: $("#about"),
  aboutFacts: $("#about-facts"),
  recovery: $("#recovery"),
  recoveryText: $("#recovery-text"),
  rescue: $("#rescue"),
  s: {
    state: $("#s-state"),
    revision: $("#s-revision"),
    dirty: $("#s-dirty"),
    pending: $("#s-pending"),
    generation: $("#s-generation"),
    latency: $("#s-latency"),
    caret: $("#s-caret"),
    doc: $("#s-doc"),
  },
};

const STATE_LABEL = {
  idle: "閒置",
  loading: "載入中",
  ready: "就緒",
  busy: "處理中",
  blocked: "已阻擋",
  "recoverable-error": "可回復錯誤",
  "restart-required": "需重新啟動",
  closed: "已關閉",
};

const ZOOM_STEPS = [0.6, 0.75, 0.9, 1, 1.15, 1.3, 1.6, 2];
const MAX_BACKING_WIDTH = 2400;

let session = null;
let ready = null;
let zoomIndex = 3;
let rendering = false;
let renderAgain = false;
let documentName = "—";

// What we last explicitly asked for since the caret last moved.  `null` means
// unknown, which is the honest answer after any caret movement.
const intent = { bold: null, italic: null, underline: null, strikethrough: null };

// Caret and selection geometry, in document twips, exactly as the engine last
// reported it.  `confirmed` is false when the engine's editor state did not
// advance for the operation we just ran -- see refreshGeometry().
const geometry = { caret: null, rectangles: [], sequence: -1, confirmed: false };

// Comments as the engine reports them.  LOK does not paint them into the tile;
// it hands them over as data and leaves the margin column empty, which is why
// documents with comments report a wider area than their page.  Drawing them is
// this shell's job.
let comments = [];

function toast(message, bad = false) {
  el.toast.textContent = message;
  el.toast.classList.toggle("bad", bad);
  el.toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.toast.classList.remove("show"), 2600);
}

function describeError(error) {
  const code = error?.code || error?.name || "ERROR";
  return `${code}：${error?.message || String(error)}`;
}

const FORMAT_LABELS = Object.freeze({
  bold: "粗體", italic: "斜體", underline: "底線", strikethrough: "刪除線",
});

function resetIntent() {
  for (const format of Object.keys(FORMAT_LABELS))
    intent[format] = null;
  refreshFormatButtons();
}

function refreshFormatButtons() {
  for (const [format, label] of Object.entries(FORMAT_LABELS)) {
    const button = el.toolbar.querySelector(`[data-action="${format}"]`);
    if (!button)
      continue;
    const value = intent[format];
    button.setAttribute("aria-pressed", value === true ? "true" : "false");
    button.title = value === null
      ? `${label}：目前狀態未知（游標剛移動過），按下會套用`
      : value ? `${label}：已套用，按下會取消` : `${label}：已取消，按下會套用`;
  }
}

// Wording only.  Whether to speak at all, and whether a rescue or a restart may
// be offered, is decided by recoveryNotice() so that it can be tested without a
// DOM -- the mistake to guard against here is telling a user work was preserved
// when it was not, and that is a decision, not a sentence.
function updateRecovery(snapshot) {
  const notice = recoveryNotice(snapshot);
  el.recovery.hidden = !notice.visible;
  if (!notice.visible)
    return;
  el.recovery.classList.toggle("saved", notice.hasCheckpoint);
  el.rescue.hidden = !notice.canRescue;
  const stopped = notice.restartPossible
    ? "引擎沒有回應"
    : "引擎沒有回應，而且重新啟動次數已用盡";
  if (!notice.hasCheckpoint) {
    // "There was nothing to protect" and "we tried and the save failed" both
    // land here, and only the second one is the user's own work going missing.
    // Saying the same sentence to both is how the person with something to
    // lose gets told nothing.
    const why = notice.checkpointFailed
      ? "<b>手勢前的存檔點沒有建立成功</b>——"
      : "<b>最後一次儲存之後的編輯沒有存檔點</b>——";
    el.recoveryText.innerHTML = `${stopped}。${why}`
      + (notice.restartPossible
        ? "重新啟動會回到最後一次儲存的內容。"
        : "請重新整理頁面，從最後一次存出的 ODT 繼續。");
    return;
  }
  const at = notice.checkpointRevision === null
    ? ""
    : `（存檔點在修訂 ${notice.checkpointRevision}）`;
  el.recoveryText.innerHTML = notice.restartPossible
    ? `${stopped}，但你最後那段編輯<b>已經保住了</b>${at}。`
      + "按「重新啟動引擎」會從那份繼續，也可以先下載搶救檔留一份在本機。"
    : `${stopped}。你最後那段編輯<b>還在</b>${at}，`
      + "<b>下載搶救檔是把它取出的唯一方法</b>；取出後請重新整理頁面。";
}

function updateState(snapshot) {
  const label = STATE_LABEL[snapshot.state] || snapshot.state;
  el.statePill.dataset.state = snapshot.state;
  el.statePill.textContent = snapshot.error
    ? `${label}｜${snapshot.error.code}`
    : label;
  el.s.state.textContent = label;
  el.s.revision.textContent = snapshot.revision ?? "—";
  el.s.dirty.textContent = snapshot.dirty ? "是" : "否";
  el.s.pending.textContent = snapshot.pending ?? 0;
  el.s.generation.textContent = snapshot.generation ?? "—";
  el.s.doc.textContent = documentName;

  const usable = ["ready", "busy"].includes(snapshot.state);
  for (const button of el.toolbar.querySelectorAll("button")) {
    const action = button.dataset.action;
    if (action === "restart")
      button.disabled = !["restart-required", "recoverable-error"].includes(snapshot.state);
    else if (action === "about")
      button.disabled = false;
    else if (action === "open")
      button.disabled = snapshot.state === "loading";
    else
      button.disabled = !usable;
  }
  el.fixture.disabled = snapshot.state === "loading";
  updateRecovery(snapshot);

  if (snapshot.error)
    toast(`${snapshot.error.code}：${snapshot.error.message}`, true);
}

function documentCssSize() {
  if (!session?.document)
    return { width: 720, height: 900 };
  const zoom = ZOOM_STEPS[zoomIndex];
  return {
    width: Math.round(session.document.widthTwips / 15 * zoom),
    height: Math.round(session.document.heightTwips / 15 * zoom),
  };
}

function layoutCanvas() {
  const css = documentCssSize();
  const ratio = Math.min(
    globalThis.devicePixelRatio || 1,
    MAX_BACKING_WIDTH / Math.max(css.width, 1),
  );
  el.canvas.style.width = `${css.width}px`;
  el.canvas.style.height = `${css.height}px`;
  el.paper.style.width = `${css.width}px`;
  el.paper.style.height = `${css.height}px`;
  el.canvas.width = Math.max(1, Math.round(css.width * ratio));
  el.canvas.height = Math.max(1, Math.round(css.height * ratio));
  el.zoomLabel.textContent = `${Math.round(ZOOM_STEPS[zoomIndex] * 100)}%`;
}

async function renderDocument(retriesLeft = 6) {
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
      canvasWidthPx: el.canvas.width,
      canvasHeightPx: el.canvas.height,
    }, { timeoutMs: 60000 });
    el.canvas.getContext("2d").putImageData(new ImageData(
      new Uint8ClampedArray(tile.pixels), tile.width, tile.height,
    ), 0, 0);
  } catch (error) {
    // A repaint that lands while the verified-selection-delete transaction is
    // still settling comes back BUSY.  Nothing is wrong with the document -- the
    // canvas is simply a frame behind -- so retry rather than reporting a
    // failure the operator would reasonably read as "the delete was refused".
    if (error?.code === "BUSY" && retriesLeft > 0) {
      rendering = false;
      await new Promise((resolve) => setTimeout(resolve, 40));
      return renderDocument(retriesLeft - 1);
    }
    toast(`繪製失敗 ${describeError(error)}`, true);
  } finally {
    rendering = false;
    if (renderAgain) {
      renderAgain = false;
      void renderDocument();
    }
  }
}

/* --------------------------------------------------------------- comments */

/**
 * Where the page ends, measured from the canvas we are already showing.
 *
 * An earlier attempt asked the engine for a second, smaller render and scanned
 * that; it disagreed with a standalone probe on the same document, so it was
 * measuring something other than what the screen shows.  Reading back the
 * pixels we actually painted cannot drift from the display, needs no extra
 * render, and degrades to null when the answer is not clear-cut.
 */
function measurePageEdgePx() {
  const width = el.canvas.width;
  const height = el.canvas.height;
  if (!width || !height)
    return null;
  let context;
  try {
    context = el.canvas.getContext("2d", { willReadFrequently: true });
  } catch {
    return null;
  }
  let edge = 0;
  const rows = 24;
  for (let index = 1; index <= rows; index += 1) {
    const y = Math.min(height - 1, Math.floor(height * index / (rows + 1)));
    let data;
    try {
      data = context.getImageData(0, y, width, 1).data;
    } catch {
      return null;   // a tainted canvas is not something to work around
    }
    for (let x = width - 1; x > edge; x -= 1) {
      const at = x * 4;
      if (data[at] > 240 && data[at + 1] > 240 && data[at + 2] > 240) {
        edge = x;
        break;
      }
    }
  }
  if (edge <= 0 || edge >= width - 2)
    return null;   // no page edge distinguishable from the rest of the image
  return edge / width * Number.parseFloat(el.canvas.style.width || String(width));
}

/** `"x, y, width, height"` in twips, as LOK reports an anchor. */
function parseAnchor(value) {
  const parts = String(value || "").split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (parts.length < 4 || parts.some((item) => !Number.isFinite(item)))
    return null;
  return { x: parts[0], y: parts[1], width: parts[2], height: parts[3] };
}

/**
 * The engine hands comment bodies over as an HTML fragment.  It is document
 * content, so it is parsed and reduced to text rather than inserted as markup:
 * a comment must never be able to put nodes into this page.
 */
function commentText(html) {
  const parsed = new DOMParser().parseFromString(String(html || ""), "text/html");
  return (parsed.body.textContent || "").trim();
}

async function loadComments() {
  comments = [];
  if (!session?.document)
    return;
  try {
    const result = await session.document.listComments({ timeoutMs: 30000 });
    comments = (result.comments || []).map((entry) => ({
      id: entry.id,
      author: String(entry.author || "").trim(),
      text: commentText(entry.html),
      resolved: String(entry.resolved) === "true",
      anchor: parseAnchor(entry.anchorPos),
    })).filter((entry) => entry.anchor && entry.text);
  } catch {
    // Comments are presentation; failing to list them must not stop the open.
  }
  paintComments();
}

function paintComments() {
  if (!session?.document || !comments.length) {
    el.comments.replaceChildren();
    return;
  }
  const zoom = ZOOM_STEPS[zoomIndex];
  const documentPx = session.document.widthTwips / 15 * zoom;
  const cardWidth = Math.min(260, Math.max(140, documentPx * 0.22));
  const nodes = [];
  let coverFrom = Infinity;
  for (const entry of [...comments].sort((a, b) => a.anchor.y - b.anchor.y)) {
    const anchorX = twipsToPx(entry.anchor.x);
    const anchorY = twipsToPx(entry.anchor.y);
    const left = Math.max(anchorX + 24, documentPx - cardWidth - 12);

    const card = document.createElement("div");
    card.className = entry.resolved ? "comment resolved" : "comment";
    card.style.left = `${left}px`;
    card.style.width = `${cardWidth}px`;
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = entry.resolved ? `${entry.author}（已解決）` : entry.author;
    card.append(who, document.createTextNode(entry.text));

    const pin = document.createElement("div");
    pin.className = "pin";
    pin.style.left = `${anchorX}px`;
    pin.style.top = `${anchorY}px`;

    const tie = document.createElement("div");
    tie.className = "tie";
    tie.style.left = `${anchorX}px`;
    tie.style.top = `${anchorY}px`;
    tie.style.width = `${Math.max(0, left - anchorX)}px`;

    nodes.push(pin, tie, card);
    card.dataset.anchorTop = String(anchorY);
    coverFrom = Math.min(coverFrom, left);
  }
  if (Number.isFinite(coverFrom)) {
    // Prefer the measured page edge so the engine's own comment box is covered
    // whole; fall back to just behind our card when the edge is unclear.
    const pageEdge = measurePageEdgePx();
    const left = pageEdge === null ? coverFrom - 14 : Math.min(coverFrom - 14, pageEdge + 1);
    const cover = document.createElement("div");
    cover.className = "margin-cover";
    cover.style.left = `${Math.max(0, left)}px`;
    cover.style.right = "0";
    nodes.unshift(cover);
  }
  el.comments.replaceChildren(...nodes);
  // Stack cards that would overlap: position after layout, when heights exist.
  let floor = -Infinity;
  for (const card of el.comments.querySelectorAll(".comment")) {
    const wanted = Number(card.dataset.anchorTop);
    const top = Math.max(wanted, floor);
    card.style.top = `${top}px`;
    floor = top + card.getBoundingClientRect().height + 8;
  }
}

/* ------------------------------------------------- caret and selection */

function twipsToPx(value) {
  return value / 15 * ZOOM_STEPS[zoomIndex];
}

function paintOverlay() {
  if (!geometry.caret) {
    el.overlay.replaceChildren();
    el.s.caret.textContent = "—";
    return;
  }
  const nodes = geometry.rectangles.map((rectangle) => {
    const node = document.createElement("div");
    node.className = "sel";
    node.style.left = `${twipsToPx(rectangle.x)}px`;
    node.style.top = `${twipsToPx(rectangle.y)}px`;
    node.style.width = `${Math.max(1, twipsToPx(rectangle.width))}px`;
    node.style.height = `${Math.max(1, twipsToPx(rectangle.height))}px`;
    return node;
  });
  const caret = document.createElement("div");
  caret.className = geometry.confirmed ? "caret" : "caret unconfirmed";
  caret.style.left = `${twipsToPx(geometry.caret.x)}px`;
  caret.style.top = `${twipsToPx(geometry.caret.y)}px`;
  caret.style.height = `${Math.max(2, twipsToPx(geometry.caret.height))}px`;
  nodes.push(caret);
  el.overlay.replaceChildren(...nodes);

  const selected = geometry.rectangles.length;
  el.s.caret.textContent = geometry.confirmed
    ? (selected ? `選取 ${selected} 段` : `${geometry.caret.x}, ${geometry.caret.y} twips`)
    : "位置未確認";
}

/**
 * Read caret/selection geometry back from the engine.
 *
 * The engine's editor state carries a monotonic `sourceSequence`, so we can
 * wait for an *observable* advance rather than sleeping and hoping.  Most
 * operations have already refreshed it by the time they resolve; text commits
 * are the exception -- their caret callback lands a few tens of milliseconds
 * later (finding 021's lag, in its mildest form).  If the sequence never
 * advances within the bound we keep the previous geometry and mark it
 * unconfirmed, which the overlay draws as a hollow caret.  We never move the
 * caret to a place the engine has not told us about.
 *
 * `downgrade` is the right to mark the geometry unconfirmed.  Only the call
 * that follows a real operation holds it: the debounced catch-up below runs
 * after operations that already refreshed successfully, and letting it demand
 * a *second* advance would flag good geometry as stale.
 */
async function refreshGeometry(previousSequence,
  { expectAdvance = true, downgrade = true } = {}) {
  if (!session?.editor || !["ready", "busy"].includes(session.state.snapshot.state))
    return;
  const deadline = performance.now() + 400;
  for (;;) {
    let state;
    try {
      state = await session.editor.getState({ timeoutMs: 30000 });
    } catch {
      return;   // a readback failure must never break the operation itself
    }
    const advanced = state.sourceSequence > previousSequence;
    if (advanced || !expectAdvance || performance.now() >= deadline) {
      if (advanced || geometry.sequence < 0) {
        geometry.caret = state.caret ?? null;
        geometry.rectangles = state.selection?.collapsed === false
          ? (state.selection?.rectangles || []) : [];
        geometry.sequence = state.sourceSequence;
      }
      if (advanced)
        geometry.confirmed = true;
      else if (downgrade)
        geometry.confirmed = false;
      paintOverlay();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
}

// Typing does not go through run(): the input adapter calls
// EditorSession.commitText directly, so the only hook is the invalidation the
// mutation raises.  Debounced so a fast typist does not queue one readback per
// keystroke.
let geometryTimer = null;
function scheduleGeometryRefresh() {
  clearTimeout(geometryTimer);
  geometryTimer = setTimeout(() => {
    void refreshGeometry(geometry.sequence, { downgrade: false });
  }, 30);
}

/** Run one editor operation, time it, refresh the canvas, then the overlay. */
async function run(label, operation, { movesCaret = false } = {}) {
  await ready;
  const started = performance.now();
  const beforeSequence = geometry.sequence;
  try {
    const result = await operation();
    el.s.latency.textContent = `${label} ${Math.round(performance.now() - started)} ms`;
    if (movesCaret)
      resetIntent();
    await renderDocument();
    await refreshGeometry(beforeSequence);
    return result;
  } catch (error) {
    el.s.latency.textContent = `${label} 失敗`;
    toast(`${label}：${describeError(error)}`, true);
    throw error;
  }
}

function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/e1-editor-v1/sdk-worker.js",
    timeoutMs: 30000,
  });
}

async function openBytes(bytes, name) {
  if (session) {
    try {
      await session.close();
    } catch {
      // A dead session must not block opening the next document.
    }
    session = null;
  }
  documentName = name;
  updateState({ state: "loading", revision: null, pending: 0 });
  session = new EditorSession({
    engineFactory,
    clipboard: navigator.clipboard,
    secureContext: globalThis.isSecureContext,
    onState: updateState,
    onEvent(event) {
      if (event.event === "document-invalidated") {
        queueMicrotask(() => void renderDocument());
        scheduleGeometryRefresh();
      }
    },
  });
  await session.open({ bytes, name });
  session.attachInput(el.sink);
  resetIntent();
  geometry.caret = null;
  geometry.rectangles = [];
  geometry.sequence = -1;
  geometry.confirmed = false;
  paintOverlay();
  const manifest = session.engine.manifest;
  el.engineProfile.textContent =
    `${manifest.profile} · contract v${manifest.editorContract?.version}`;
  fillAboutFacts(manifest);
  layoutCanvas();
  await renderDocument();
  await loadComments();
  await refreshGeometry(-1, { expectAdvance: false, downgrade: false });
}

async function openFixture(id) {
  const response = await fetch(`./e1-fixtures/${id}.odt`, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`範例文件載入失敗：HTTP ${response.status}`);
  await openBytes(await response.arrayBuffer(), `${id}.odt`);
}

function fillAboutFacts(manifest) {
  const contract = manifest.editorContract || {};
  const facts = [
    ["Profile", manifest.profile],
    ["契約版本", `v${contract.version}`],
    ["能力", (manifest.capabilities || []).join("、")],
    ["動作", (contract.actions || []).join("、")],
    ["WASM SHA-256", contract.wasmSha256 || "—"],
    ["cross-origin isolated", String(globalThis.crossOriginIsolated)],
  ];
  el.aboutFacts.replaceChildren(...facts.flatMap(([term, value]) => {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value ?? "—";
    return [dt, dd];
  }));
}

/* ---------------------------------------------------------------- actions */

function applyFormat(format) {
  const next = intent[format] !== true;
  const label = FORMAT_LABELS[format] || format;
  return run(next ? `套用${label}` : `取消${label}`,
  async () => {
    const result = await session.setInlineFormat(format, next);
    intent[format] = next;
    refreshFormatButtons();
    return result;
  });
}

function downloadOdt(bytes, suffix) {
  const blob = new Blob([bytes], {
    type: "application/vnd.oasis.opendocument.text",
  });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = documentName.replace(/\.odt$/i, "") + suffix;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  return (bytes.byteLength / 1024).toFixed(1);
}

async function saveDocument() {
  const saved = await run("儲存", () => session.save());
  toast(`已存出 ${downloadOdt(saved.bytes, "-edited.odt")} KB，可用桌面版 LibreOffice 開啟`);
}

// Deliberately not routed through run(): the session is in an error state by
// definition here, and checkpointBytes() is a plain accessor over bytes the
// session already holds -- it touches neither the engine nor the queue, which
// is exactly why it still works when nothing else does.
function rescueCheckpoint() {
  const bytes = session?.checkpointBytes();
  if (!bytes) {
    toast("沒有可搶救的存檔點", true);
    return;
  }
  toast(`已存出搶救檔 ${downloadOdt(bytes, "-rescued.odt")} KB，可用桌面版 LibreOffice 開啟`);
}

const ACTIONS = {
  bold: () => applyFormat("bold"),
  italic: () => applyFormat("italic"),
  underline: () => applyFormat("underline"),
  strikethrough: () => applyFormat("strikethrough"),
  undo: () => run("復原", () => session.undo(), { movesCaret: true }),
  save: () => saveDocument(),
  open: () => el.file.click(),
  restart: () => run("重新啟動引擎", () => session.restart(), { movesCaret: true }),
  about: () => el.about.showModal(),
  "zoom-in": () => changeZoom(1),
  "zoom-out": () => changeZoom(-1),
};

async function changeZoom(delta) {
  const next = Math.min(ZOOM_STEPS.length - 1, Math.max(0, zoomIndex + delta));
  if (next === zoomIndex)
    return;
  zoomIndex = next;
  layoutCanvas();
  paintOverlay();
  paintComments();
  await renderDocument();
}

// The banner lives outside #toolbar on purpose: updateState() disables every
// button in there whenever the session is not usable, and this is the one
// control that has to work precisely then.
el.rescue.addEventListener("click", () => rescueCheckpoint());

el.toolbar.addEventListener("click", (event) => {
  const action = event.target.closest("button")?.dataset.action;
  if (ACTIONS[action])
    void Promise.resolve(ACTIONS[action]()).catch(() => {});
});

el.about.addEventListener("click", (event) => {
  if (event.target.hasAttribute("data-close"))
    el.about.close();
});

el.fixture.addEventListener("change", () => {
  void openFixture(el.fixture.value).catch((error) => toast(describeError(error), true));
});

el.file.addEventListener("change", async () => {
  const file = el.file.files?.[0];
  el.file.value = "";
  if (!file)
    return;
  try {
    await openBytes(await file.arrayBuffer(), file.name);
    toast(`已開啟 ${file.name}`);
  } catch (error) {
    toast(describeError(error), true);
  }
});

/* ------------------------------------------------------------ caret input */

function moveSink(clientX, clientY) {
  const rectangle = el.paper.getBoundingClientRect();
  el.sink.style.left = `${clientX - rectangle.left}px`;
  el.sink.style.top = `${clientY - rectangle.top}px`;
}

/**
 * Put the composition box where the engine says the caret is, rather than where
 * the pointer last went down.  Those agree right after a click but drift apart
 * once the caret has moved by keyboard, and a composition started without a
 * recent click would otherwise appear wherever the sink was last left.
 */
function moveSinkToCaret() {
  if (!geometry.caret)
    return;
  el.sink.style.left = `${twipsToPx(geometry.caret.x)}px`;
  el.sink.style.top = `${twipsToPx(geometry.caret.y)}px`;
}

/**
 * Grow the box with the preedit instead of clipping it.
 *
 * The text has to come from the composition event: a browser does not
 * necessarily mirror the preedit into `textarea.value` while composition is
 * running, so measuring `.value` saw an empty string, the box shrank to its
 * minimum and `overflow: hidden` cut the bopomofo down to its first symbol --
 * typing ㄏㄠˇ showed only ㄏ.
 */
function sizeSink(text) {
  if (!el.sink.classList.contains("composing"))
    return;
  const content = typeof text === "string" && text.length ? text : el.sink.value;
  const style = getComputedStyle(el.sink);
  el.sinkMirror.style.font = style.font;
  el.sinkMirror.textContent = content || " ";
  const width = Math.ceil(el.sinkMirror.getBoundingClientRect().width) + 4;
  el.sink.style.width = `${width}px`;
  el.sink.style.height = "auto";
  el.sink.style.height = `${el.sink.scrollHeight}px`;
}

function pointToTwips(event) {
  const rectangle = el.canvas.getBoundingClientRect();
  return {
    xTwips: Math.max(0, Math.round((event.clientX - rectangle.left) / rectangle.width
      * session.document.widthTwips)),
    yTwips: Math.max(0, Math.round((event.clientY - rectangle.top) / rectangle.height
      * session.document.heightTwips)),
  };
}

// Drag selection (SPEC E1-D).  The gesture lives here, in JS: the browser knows
// where the pointer went, so the engine is asked for a range between two known
// points rather than being fed synthesised mouse events.  The gate found that
// the synthesised-event path reports a selection it did not make.
const drag = { active: false, start: null, latest: null, inFlight: false,
  pointerId: null };

// One request at a time, always for the newest point.  Without the coalescing a
// fast drag would queue a request per mousemove and the selection would keep
// redrawing positions the pointer had already left.
async function pumpDrag() {
  if (drag.inFlight || !drag.latest || !session?.editor)
    return;
  const end = drag.latest;
  drag.latest = null;
  drag.inFlight = true;
  try {
    await run("拖曳選取", () => session.selectRange(drag.start, end));
  } catch {
    // A refused range must not abort the gesture; the next move can still work.
  } finally {
    drag.inFlight = false;
    if (drag.latest)
      void pumpDrag();
  }
}

function endDrag(event) {
  if (!drag.active)
    return;
  drag.active = false;
  if (drag.pointerId !== null) {
    try {
      el.canvas.releasePointerCapture(drag.pointerId);
    } catch {
      // Capture may already be gone; releasing twice must not break the gesture.
    }
    drag.pointerId = null;
  }
  if (!session?.document || !event)
    return;
  const end = pointToTwips(event);
  // A click is a drag of zero length; leave the caret the mousedown placed
  // rather than asking for a range that selects nothing.
  if (end.xTwips === drag.start.xTwips && end.yTwips === drag.start.yTwips)
    return;
  drag.latest = end;
  void pumpDrag();
}

// Pointer events, not mouse events, and with capture: a drag released outside
// the window never delivers mouseup to the page.  Without capture the gesture
// stayed "active" forever, every later pointer move over the canvas queued
// another range request, and the editor looked dead to the keyboard.
el.canvas.addEventListener("pointerdown", (event) => {
  if (!session?.document || event.button !== 0)
    return;
  // Without this the browser's own focus handling runs after ours and parks
  // focus on <body>, because a canvas is not focusable.  The IME sink then
  // never sees a keystroke and the editor looks dead to the keyboard -- which
  // dispatching synthetic input events at the sink directly cannot reveal,
  // since that path skips focus entirely.
  event.preventDefault();
  const point = pointToTwips(event);
  moveSink(event.clientX, event.clientY);
  el.sink.focus({ preventScroll: true });
  drag.active = true;
  drag.start = point;
  drag.latest = null;
  drag.pointerId = event.pointerId;
  try {
    el.canvas.setPointerCapture(event.pointerId);
  } catch {
    drag.pointerId = null;   // capture is an optimisation, not a requirement
  }
  void run("定位游標", () => session.placeCaret(point.xTwips, point.yTwips),
    { movesCaret: true }).catch(() => {});
});

el.canvas.addEventListener("pointermove", (event) => {
  if (!drag.active || !session?.document)
    return;
  // Belt and braces: if the button came up somewhere we never heard about,
  // finish the gesture instead of dragging on forever.
  if ((event.buttons & 1) === 0) {
    endDrag(event);
    return;
  }
  drag.latest = pointToTwips(event);
  void pumpDrag();
});

el.canvas.addEventListener("pointerup", endDrag);
el.canvas.addEventListener("pointercancel", () => endDrag(null));
globalThis.addEventListener("blur", () => endDrag(null));

const UNSUPPORTED_KEYS = {
  ArrowUp: "本版不支援上下行移動（行導覽尚未進入契約）",
  ArrowDown: "本版不支援上下行移動（行導覽尚未進入契約）",
  Home: "本版不支援 Home／End 行首行尾",
  End: "本版不支援 Home／End 行首行尾",
  PageUp: "本版不支援翻頁移動",
  PageDown: "本版不支援翻頁移動",
};

el.sink.addEventListener("keydown", (event) => {
  if (!session || !["ready", "busy"].includes(session.state.snapshot.state))
    return;
  // While an IME composition is running the keys belong to the IME, not to us.
  // Backspace in particular is how a Chewing user erases a bopomofo symbol
  // mid-composition; intercepting it fed a document delete *and* swallowed the
  // key, leaving the composition desynchronised so no further Chinese could be
  // entered.  keyCode 229 covers browsers that do not set isComposing.
  if (event.isComposing || event.keyCode === 229)
    return;
  const control = event.ctrlKey || event.metaKey;

  if (control && event.key.toLowerCase() === "b") {
    event.preventDefault();
    void ACTIONS.bold().catch(() => {});
    return;
  }
  if (control && event.key.toLowerCase() === "i") {
    event.preventDefault();
    void ACTIONS.italic().catch(() => {});
    return;
  }
  if (control && event.key.toLowerCase() === "u") {
    event.preventDefault();
    void ACTIONS.underline().catch(() => {});
    return;
  }
  if (control && event.key.toLowerCase() === "z") {
    event.preventDefault();
    if (event.shiftKey) {
      toast("本版不支援重做（Redo）");
      return;
    }
    void ACTIONS.undo().catch(() => {});
    return;
  }
  if (control && event.key.toLowerCase() === "y") {
    event.preventDefault();
    toast("本版不支援重做（Redo）");
    return;
  }
  if (control && event.key.toLowerCase() === "s") {
    event.preventDefault();
    void saveDocument().catch(() => {});
    return;
  }
  if (control && event.key.toLowerCase() === "c") {
    event.preventDefault();
    void run("複製", () => session.copySelection({
      metadata: { source: "keyboard-user-gesture" },
    })).catch(() => {});
    return;
  }
  if (control && event.key.toLowerCase() === "v") {
    // Let the native paste event reach the sink; the clipboard adapter
    // consumes it.  Intercepting here would strip the user gesture.
    return;
  }
  if (control)
    return;

  if (UNSUPPORTED_KEYS[event.key]) {
    event.preventDefault();
    toast(UNSUPPORTED_KEYS[event.key]);
    return;
  }

  switch (event.key) {
    case "ArrowLeft":
      event.preventDefault();
      void run("游標左移", () => session.moveCharacter("left", {
        extendSelection: event.shiftKey,
      }), { movesCaret: true }).catch(() => {});
      break;
    case "ArrowRight":
      event.preventDefault();
      void run("游標右移", () => session.moveCharacter("right", {
        extendSelection: event.shiftKey,
      }), { movesCaret: true }).catch(() => {});
      break;
    case "Backspace":
    case "Delete":
      event.preventDefault();
      void run(event.key === "Backspace" ? "向左刪除" : "向右刪除",
        () => session.delete(event.key === "Backspace" ? "backward" : "forward"),
        { movesCaret: true }).catch((error) => {
        if (error?.code === "EDITOR_STATE_UNAVAILABLE") {
          toast("本版不支援刪除整段選取；請先點一下取消選取，或直接打字取代");
        }
      });
      break;
    case "Enter":
      event.preventDefault();
      void run(event.shiftKey ? "軟換行" : "段落換行",
        () => session.insertBreak(event.shiftKey ? "line" : "paragraph"),
        { movesCaret: true }).catch(() => {});
      break;
    default:
      break;
  }
});

// The input adapter reads the sink's value at compositionend as a fail-closed
// guard: anything left over from an earlier commit makes it reject the new one
// with "compositionend data and host input buffer disagree".  Clearing is the
// host's job -- the adapter deliberately never touches the element -- and these
// listeners run after the adapter's, so it has already read what it needed.
el.sink.addEventListener("compositionstart", () => {
  el.sink.classList.add("composing");
  moveSinkToCaret();
  sizeSink();
});

el.sink.addEventListener("compositionupdate", (event) => sizeSink(event.data));

el.sink.addEventListener("compositionend", () => {
  el.sink.classList.remove("composing");
  el.sink.style.width = "";
  el.sink.style.height = "";
  queueMicrotask(() => { el.sink.value = ""; });
});

el.sink.addEventListener("input", () => {
  // Some IMEs mutate the element without a compositionupdate of their own.
  if (el.sink.classList.contains("composing"))
    sizeSink();
  else
    queueMicrotask(() => { el.sink.value = ""; });
});

el.sink.addEventListener("paste", (event) => {
  if (!session)
    return;
  void session.pasteEvent(event, { source: "native-paste" })
    .then(() => renderDocument())
    .catch((error) => toast(describeError(error), true));
});

globalThis.addEventListener("resize", () => {
  layoutCanvas();
  paintOverlay();
  paintComments();
  void renderDocument();
});

/* ------------------------------------------------------------------ start */

function fillFixtureList(manifest) {
  el.fixture.replaceChildren(...manifest.fixtures.map((fixture) => {
    const option = document.createElement("option");
    option.value = fixture.id;
    option.textContent = fixture.id;
    return option;
  }));
  el.fixture.value = "plain-grapheme";
}

ready = (async () => {
  if (!globalThis.crossOriginIsolated) {
    toast("此頁需要 cross-origin isolation：請以 web/serve.py 提供，並從 127.0.0.1 開啟", true);
  }
  const manifest = await fetch("./e1-fixtures/manifest.json", { cache: "no-cache" })
    .then((response) => response.json());
  fillFixtureList(manifest);
  await openFixture(el.fixture.value);
  toast("點一下文件放游標，就可以直接打字");
})().catch((error) => {
  updateState({ state: "recoverable-error", revision: null, error: {
    code: error?.code || "STARTUP_FAILED",
    message: error?.message || String(error),
  } });
});
