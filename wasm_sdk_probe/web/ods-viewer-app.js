// The read-only spreadsheet viewer page (DRAFT, plan W9 / gate G9).
//
// A file input, a tab strip (one element per part, text = the part's name), a
// scrolling viewport painted from a TileScheduler, and a status line that says
// what the page knows and what it is only assuming.  Everything that depends on
// W7 (the engine's document type, part switch, part names, ods open) lives in
// `viewer-shell/w7-adapter.js`; this page only renders what the session reports.
//
// Import layout is the DIST layout (`./sdk/...`, `./viewer-shell/...`), like
// every page in this directory; the page is not staged to dist/ by this draft.
// It is NOT in the product page's import graph, and the product page does not
// reach it.
import { DocumentEngine } from "./sdk/document-sdk.js";
import { OdsViewerSession } from "./viewer-shell/ods-viewer-session.js";

const params = new URLSearchParams(location.search);
const requestedProfile = params.get("profile") || "e2-editor-v14";
// The profile becomes a path segment; refuse anything that is not a plain name.
const profile = /^[A-Za-z0-9._-]+$/.test(requestedProfile) ? requestedProfile : "e2-editor-v14";
const OPEN_TIMEOUT_MS = Number.parseInt(params.get("openTimeoutMs") || "180000", 10);

const $ = (selector) => document.querySelector(selector);
const el = {
  file: $("#file-input"),
  close: $("#close-button"),
  banner: $("#diagnostic-banner"),
  tabs: $("#tab-strip"),
  viewport: $("#viewport"),
  surface: $("#surface"),
  tiles: $("#tiles"),
  message: $("#message"),
};

const FALLBACK_TEXT = {
  "name-spoofed":
    "檔名是以 .odt 交給引擎的（finding 013 的繞法）；這次開檔只算診斷，不是產品證據。",
  "document-type-unknown":
    "引擎不回報文件型別（W7 之前），無法確認這真的是試算表。",
  "part-names-synthesised":
    "工作表名稱是檢視頁自己編的（工作表 1…N），不是引擎的。",
  "part-switch-unavailable":
    "引擎沒有分頁切換；只有開檔時的那一頁看得到，其餘分頁停用。",
  "part-readback-unavailable":
    "引擎不回報目前是哪一頁；「目前分頁」只是假設，沒有被讀回確認。",
};

// What a test (or a person with devtools) can read without scraping pixels.
const record = {
  schemaVersion: 1,
  release: "m4-ods-viewer-draft",
  profile,
  openTimeoutMs: OPEN_TIMEOUT_MS,
  runs: [],
  current: null,
  session: null,
  state: null,
  tileDraws: 0,
};
window.__odsViewer = record;

function errorValue(error) {
  if (!error) return null;
  return {
    name: error.name || null,
    code: error.code || null,
    message: String(error.message || error),
    details: error.details || null,
  };
}

async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// The listener goes on BEFORE initialisation (commit 88472109): the engine's
// preRun diagnostics are emitted during `init`, and `createDocumentEngine`
// resolves only after it.  `_initialize` is what `createDocumentEngine` calls;
// splitting it is the only way to put the listener first.
async function engineFactory({ onEvent }) {
  const engine = new DocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`,
    timeoutMs: 60000,
  });
  engine.onEvent(onEvent);
  return engine._initialize();
}

function setField(name, value) {
  const node = document.querySelector(`[data-field="${name}"]`);
  if (node) node.textContent = value;
}

function renderBanner(state) {
  el.banner.replaceChildren();
  if (!state.adapterFallbacks.length) {
    el.banner.hidden = true;
    return;
  }
  el.banner.hidden = false;
  const head = document.createElement("strong");
  head.textContent = "診斷：以下幾處是檢視頁在 W7 缺席時自己代答的";
  const list = document.createElement("ul");
  for (const fallback of state.adapterFallbacks) {
    const item = document.createElement("li");
    item.dataset.fallback = fallback;
    item.textContent = FALLBACK_TEXT[fallback] || fallback;
    list.append(item);
  }
  el.banner.append(head, list);
}

function renderTabs(state) {
  el.tabs.replaceChildren();
  for (const tab of state.tabs) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ods-tab";
    button.setAttribute("role", "tab");
    button.dataset.part = String(tab.index);
    button.textContent = tab.label;
    button.setAttribute("aria-selected", tab.current ? "true" : "false");
    if (!tab.enabled) {
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      button.title = tab.disabledReason || "";
      button.dataset.disabledReason = tab.disabledReason || "";
    }
    button.addEventListener("click", () => switchPart(tab.index));
    el.tabs.append(button);
  }
}

function render(state) {
  record.state = state;
  setField("state", state.state);
  setField("documentType", state.documentType ?? "—");
  setField("parts", state.parts ? String(state.parts) : "—");
  setField("currentPart", state.currentPart === null ? "—" : String(state.currentPart + 1));
  setField("currentPartReadBack",
    state.currentPartReadBack === null ? "未提供" : String(state.currentPartReadBack + 1));
  setField("nameSpoofed", state.nameSpoofed ? "是（偽裝）" : "否");
  setField("evidenceClass", state.evidenceClass);
  renderBanner(state);
  renderTabs(state);
  if (state.error) {
    el.message.textContent = `${state.error.code}: ${state.error.message}`;
    el.message.classList.add("error");
  } else if (state.lastRefusal) {
    el.message.textContent = `已拒絕（${state.lastRefusal.code}）：${state.lastRefusal.message}`;
    el.message.classList.add("error");
  } else {
    el.message.textContent = "";
    el.message.classList.remove("error");
  }
}

function fitSurface(session) {
  const size = session.scheduler.documentCssSize;
  el.surface.style.width = `${Math.ceil(size.width)}px`;
  el.surface.style.height = `${Math.ceil(size.height)}px`;
}

function drawTile(entry) {
  const run = record.current;
  record.tileDraws += 1;
  if (run) run.tileDraws += 1;
  let canvas = el.tiles.querySelector(`[data-key="${CSS.escape(entry.key)}"]`);
  if (!canvas) {
    canvas = document.createElement("canvas");
    canvas.dataset.key = entry.key;
    el.tiles.append(canvas);
  }
  canvas.width = entry.tile.width;
  canvas.height = entry.tile.height;
  canvas.style.left = `${entry.xPx}px`;
  canvas.style.top = `${entry.yPx}px`;
  canvas.style.width = `${entry.cssWidth}px`;
  canvas.style.height = `${entry.cssHeight}px`;
  canvas.getContext("2d").putImageData(new ImageData(
    new Uint8ClampedArray(entry.tile.pixels), entry.tile.width, entry.tile.height), 0, 0);
  if (run && entry.xPx === 0 && entry.yPx === 0 && !run.firstTilePromise) {
    // Hash and paper count, BOTH: a hash cannot tell two blank tiles from two
    // identical drawn ones, and a count cannot tell two drawings apart.
    const view = new Uint8Array(entry.tile.pixels);
    let nonPaperPixels = 0;
    for (let i = 0; i + 3 < view.length; i += 4) {
      if (view[i] !== 255 || view[i + 1] !== 255 || view[i + 2] !== 255) nonPaperPixels += 1;
    }
    const part = record.state?.currentPart ?? null;
    run.firstTilePromise = sha256Hex(view).then((sha256) => {
      run.firstTile = {
        part, width: entry.tile.width, height: entry.tile.height, bytes: view.length,
        nonPaperPixels, sha256, key: entry.key,
        documentWidthTwips: entry.tile.documentWidthTwips ?? null,
        documentHeightTwips: entry.tile.documentHeightTwips ?? null,
        documentSizeChanged: entry.tile.documentSizeChanged ?? null,
      };
    });
  }
}

function scheduleViewport() {
  const session = record.session;
  if (!session || session.state.state !== "ready") return null;
  return session.scheduleViewport({
    scrollLeft: el.viewport.scrollLeft,
    scrollTop: el.viewport.scrollTop,
    width: el.viewport.clientWidth,
    height: el.viewport.clientHeight,
  });
}

// One door for the tab buttons and for anything that wants to try the same path.
// Resolves with what happened instead of throwing, so a caller can report a
// typed refusal.
async function switchPart(k) {
  const session = record.session;
  if (!session) return { ok: false, error: { code: "NO_SESSION" } };
  const before = { tileDraws: record.tileDraws, part: session.state.currentPart };
  let outcome = { ok: true, error: null };
  try {
    await session.showPart(k);
  } catch (error) {
    outcome = { ok: false, error: errorValue(error) };
  }
  // Repaint only if the session's part actually changed: a refusal leaves the
  // screen exactly as it was.
  if (session.state.state === "ready" && session.state.currentPart !== before.part) {
    el.tiles.replaceChildren();
    fitSurface(session);
    el.viewport.scrollTop = 0;
    el.viewport.scrollLeft = 0;
    scheduleViewport();
    await session.drain();
  }
  outcome.tilesDrawnBefore = before.tileDraws;
  outcome.tilesDrawnAfter = record.tileDraws;
  outcome.part = session.state.currentPart;
  return outcome;
}
record.switchPart = switchPart;

async function closeCurrent() {
  const session = record.session;
  record.session = null;
  el.tiles.replaceChildren();
  if (session) {
    try { await session.close(); } catch { /* the worker is disposed either way */ }
  }
}

async function openFile(file) {
  await closeCurrent();
  const run = {
    file: file.name, startedAtMs: Math.round(performance.now()),
    settled: false, opened: null, refused: null, error: null, tileDraws: 0,
    engineEvents: [], firstTile: null, firstTilePromise: null,
  };
  record.runs.push(run);
  record.current = run;
  const bytes = await file.arrayBuffer();
  run.inputBytes = bytes.byteLength;
  // BEFORE open: `open` transfers the buffer, which detaches it.
  run.inputSha256 = await sha256Hex(new Uint8Array(bytes.slice(0)));
  // Another file was chosen while this one was being read: that one owns the
  // page now, and this run must not build a session behind its back.
  if (record.current !== run) {
    run.error = { code: "SUPERSEDED", message: "another file was chosen first" };
    run.settled = true;
    return;
  }
  const session = new OdsViewerSession({
    engineFactory,
    openTimeoutMs: OPEN_TIMEOUT_MS,
    tileOptions: { tileSizePx: 256, prefetchTiles: 1, maxInFlight: 2 },
    onState: render,
    onTile: drawTile,
    onEvent: (event) => {
      if (event?.event && event.event !== "diagnostic") run.engineEvents.push(event.event);
    },
  });
  record.session = session;
  try {
    const state = await session.open({ bytes, name: file.name });
    run.opened = {
      atMs: Math.round(performance.now() - run.startedAtMs),
      parts: state.parts, documentType: state.documentType,
      widthTwips: state.widthTwips, heightTwips: state.heightTwips,
    };
    fitSurface(session);
    scheduleViewport();
    await session.drain();
    if (run.firstTilePromise) await run.firstTilePromise;
  } catch (error) {
    if (session.state.state === "refused") run.refused = errorValue(error);
    else run.error = errorValue(error);
  }
  // The state as the page ended up showing it, copied so a later run cannot
  // rewrite what this one reported.
  run.finalState = JSON.parse(JSON.stringify(session.state));
  run.settled = true;
}

el.file.addEventListener("change", () => {
  const file = el.file.files?.[0];
  if (file) openFile(file).catch((error) => {
    const run = record.current;
    if (run) { run.error = errorValue(error); run.settled = true; }
  });
});
el.close.addEventListener("click", () => { closeCurrent(); });
el.viewport.addEventListener("scroll", () => {
  clearTimeout(record.scrollTimer);
  record.scrollTimer = setTimeout(scheduleViewport, 30);
});
// Best effort: leaving the page should not leave an engine worker behind
// (finding 024 is about exactly that on Firefox).
window.addEventListener("pagehide", () => { closeCurrent(); });
