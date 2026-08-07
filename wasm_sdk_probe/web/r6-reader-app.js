import { createDocumentEngine } from "./document-sdk.js";
import { ReaderSession } from "./reader-shell/reader-session.js";

const $ = (selector) => document.querySelector(selector);
const elements = {
  status: $("#status"),
  viewport: $("#viewport"),
  surface: $("#surface"),
  tiles: $("#tiles"),
  zoomValue: $("#zoom-value"),
  search: $("#search"),
  searchResult: $("#search-result"),
  message: $("#message"),
  log: $("#log"),
  metadata: {
    documentId: $("#document-id"),
    version: $("#version"),
    etag: $("#etag"),
    sdkRevision: $("#revision"),
    profile: $("#profile"),
    sdkVersion: $("#sdk-version"),
    providerContractVersion: $("#provider-version"),
    coreCommit: $("#core-commit"),
    nextAction: $("#next-action"),
  },
};

const metrics = {
  schemaVersion: 1,
  release: "R6-A",
  userAgent: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  events: [],
  states: [],
  workersCreated: 0,
  workersTerminated: 0,
  tileDraws: 0,
  lateTileDrawsAfterClose: 0,
  firstTileMs: null,
  scrollTileY: null,
  searchLatin: null,
  searchCjk: null,
  staleObserved: false,
  reloadedVersion: null,
  oldWorkerClosedOnReload: false,
  crashCode: null,
  recoveredWorkerGeneration: null,
  closeSucceeded: null,
  schedulerHistory: [],
  scheduler: null,
  complete: false,
  pass: false,
  error: null,
};
globalThis.__r6_reader_metrics = metrics;
globalThis.__probe_metrics = metrics;

let reader = null;
let currentSnapshot = null;
let remoteSnapshot = null;
let activeWorkerControl = null;
let currentGeneration = 0;
let currentScale = 1;
let openedAt = performance.now();
let closed = false;
let invalidationTimer = 0;

function appendLog(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  elements.log.textContent += `[${performance.now().toFixed(1)} ms] ${text}\n`;
  elements.log.scrollTop = elements.log.scrollHeight;
}

async function sha256(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)]
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
}

async function fetchSnapshot(version, fixture) {
  const response = await fetch(`./r6-fixtures/${fixture}`, { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${response.status}`);
  const bytes = await response.arrayBuffer();
  const hash = await sha256(bytes);
  return {
    documentId: "r6-reader-fixture",
    version,
    etag: `\"sha256-${hash}\"`,
    name: fixture,
    bytes,
  };
}

function engineFactory() {
  return createDocumentEngine({
    workerUrl: "./profiles/writer-review-r6/sdk-worker.js",
    timeoutMs: 30000,
    workerFactory(url) {
      const worker = new Worker(url, { name: `r6-reader-worker-${metrics.workersCreated + 1}` });
      metrics.workersCreated += 1;
      let terminated = false;
      const control = {
        worker,
        terminate() {
          if (terminated)
            return;
          terminated = true;
          metrics.workersTerminated += 1;
          worker.terminate();
        },
        crash() {
          worker.dispatchEvent(new ErrorEvent("error", {
            message: "intentional R6-A document worker crash",
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
    },
  });
}

function updateState(snapshot) {
  metrics.states.push({ atMs: performance.now(), ...snapshot });
  elements.status.textContent = snapshot.state;
  elements.status.dataset.state = snapshot.state;
  for (const [key, element] of Object.entries(elements.metadata))
    element.textContent = snapshot[key] ?? "—";
  elements.message.textContent = snapshot.error
    ? `${snapshot.error.code}: ${snapshot.error.message}`
    : `狀態 ${snapshot.state}；下一動作 ${snapshot.nextAction}`;
  elements.message.classList.toggle("error", Boolean(snapshot.error));
}

function drawTile(entry) {
  if (closed) {
    metrics.lateTileDrawsAfterClose += 1;
    return;
  }
  if (entry.generation !== currentGeneration)
    return;
  if (metrics.firstTileMs === null)
    metrics.firstTileMs = performance.now() - openedAt;
  metrics.tileDraws += 1;
  metrics.scrollTileY = Math.max(metrics.scrollTileY ?? 0, entry.yPx);
  let canvas = elements.tiles.querySelector(`[data-key="${CSS.escape(entry.key)}"]`);
  if (!canvas) {
    canvas = document.createElement("canvas");
    canvas.className = "document-tile";
    canvas.dataset.key = entry.key;
    elements.tiles.append(canvas);
  }
  canvas.width = entry.tile.width;
  canvas.height = entry.tile.height;
  canvas.style.left = `${entry.xPx}px`;
  canvas.style.top = `${entry.yPx}px`;
  canvas.style.width = `${entry.cssWidth}px`;
  canvas.style.height = `${entry.cssHeight}px`;
  canvas.getContext("2d").putImageData(new ImageData(
    new Uint8ClampedArray(entry.tile.pixels), entry.tile.width, entry.tile.height,
  ), 0, 0);
}

function updateSurface() {
  const size = reader.scheduler.documentCssSize;
  elements.surface.style.width = `${Math.ceil(size.width)}px`;
  elements.surface.style.height = `${Math.ceil(size.height)}px`;
  elements.zoomValue.value = `${Math.round(currentScale * 100)}%`;
}

function scheduleViewport() {
  if (!reader?.scheduler)
    return 0;
  elements.tiles.replaceChildren();
  currentGeneration = reader.scheduleViewport({
    scrollLeft: elements.viewport.scrollLeft,
    scrollTop: elements.viewport.scrollTop,
    width: elements.viewport.clientWidth,
    height: elements.viewport.clientHeight,
  });
  return currentGeneration;
}

async function setScale(scale) {
  currentScale = scale;
  reader.setScale(scale);
  updateSurface();
  scheduleViewport();
  await reader.scheduler.drain();
}

async function waitForNewTile(drawsBefore, timeoutMs = 30000) {
  const deadline = performance.now() + timeoutMs;
  while (metrics.tileDraws <= drawsBefore) {
    if (performance.now() >= deadline)
      throw new Error(`no new tile completed within ${timeoutMs} ms`);
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
}

async function renderStableViewport() {
  const drawsBefore = metrics.tileDraws;
  scheduleViewport();
  await reader.scheduler.drain();
  // Writer emits a semantic invalidation shortly after open. Give the public
  // event handler time to invalidate and reschedule, then require a tile from
  // the resulting stable generation.
  await new Promise((resolve) => setTimeout(resolve, 50));
  const stableDrawsBefore = metrics.tileDraws;
  scheduleViewport();
  await reader.scheduler.drain();
  await waitForNewTile(Math.max(drawsBefore, stableDrawsBefore));
}

function recordScheduler(phase) {
  const snapshot = { phase, ...reader.scheduler.metrics };
  metrics.schedulerHistory.push(snapshot);
  return snapshot;
}

async function fitWidth() {
  const unscaledWidth = reader.document.widthTwips / 15;
  await setScale(Math.max(0.25, (elements.viewport.clientWidth - 36) / unscaledWidth));
}

async function searchNext(query = elements.search.value) {
  const result = await reader.search(query);
  elements.searchResult.textContent = result.found
    ? `命中；selection text：${result.selectionText}`
    : "未命中";
  return result;
}

async function reload(snapshot = remoteSnapshot || currentSnapshot) {
  const before = metrics.workersTerminated;
  recordScheduler(`before-reload-${reader.state.snapshot.version}`);
  await reader.reload(snapshot, { downloadedLocalBytes: true });
  currentSnapshot = snapshot;
  currentScale = 1;
  updateSurface();
  await renderStableViewport();
  metrics.oldWorkerClosedOnReload = metrics.workersTerminated > before;
  metrics.reloadedVersion = reader.state.snapshot.version;
}

async function initialize() {
  currentSnapshot = await fetchSnapshot("v1", "t1-plain-zh.odt");
  remoteSnapshot = await fetchSnapshot("v2", "t3-long.odt");
  reader = new ReaderSession({
    engineFactory,
    onState: updateState,
    onTile: drawTile,
    onEvent: (event) => {
      metrics.events.push(event);
      appendLog(event);
      if (event.event === "document-invalidated") {
        clearTimeout(invalidationTimer);
        invalidationTimer = setTimeout(() => {
          if (reader?.scheduler
              && ["ready", "stale", "saving"].includes(reader.state.snapshot.state)) {
            scheduleViewport();
          }
        }, 20);
      }
    },
    tileOptions: {
      tileSizePx: 256,
      prefetchTiles: 1,
      maxInFlight: 2,
      maxCacheBytes: 32 * 1024 * 1024,
    },
  });
  openedAt = performance.now();
  await reader.open(currentSnapshot);
  updateSurface();
  await renderStableViewport();
  appendLog({ type: "reader-ready", state: reader.state.snapshot });
}

async function runAll() {
  await initializationPromise;
  const initialWorkerGeneration = reader.workerGeneration;
  elements.viewport.scrollTop = Math.min(
    700,
    Math.max(0, reader.scheduler.documentCssSize.height - elements.viewport.clientHeight),
  );
  scheduleViewport();
  await reader.scheduler.drain();

  const zoomInPromise = setScale(1.5);
  const zoomGeneration = currentGeneration;
  const zoomBackPromise = setScale(1);
  await Promise.all([zoomInPromise, zoomBackPromise]);
  const latestGeneration = currentGeneration;

  metrics.searchLatin = await searchNext("LibreOfficeKit");
  metrics.searchCjk = await searchNext("臺灣軟體工程");

  reader.markStale({
    documentId: currentSnapshot.documentId,
    previousVersion: currentSnapshot.version,
    version: remoteSnapshot.version,
    eventSequence: 1,
  });
  metrics.staleObserved = reader.state.snapshot.state === "stale";
  await reload(remoteSnapshot);

  recordScheduler("v2-before-crash");
  activeWorkerControl.crash();
  await new Promise((resolve) => setTimeout(resolve, 20));
  metrics.crashCode = reader.state.snapshot.error?.code;
  await reader.reload(currentSnapshot, { discardLocalBytes: true });
  updateSurface();
  await renderStableViewport();
  metrics.recoveredWorkerGeneration = reader.workerGeneration;
  metrics.scheduler = recordScheduler("v2-recovered");

  await reader.close();
  closed = true;
  metrics.closeSucceeded = reader.state.snapshot.closeSucceeded === true;
  const drawsAtClose = metrics.tileDraws;
  await new Promise((resolve) => setTimeout(resolve, 100));
  metrics.pass = metrics.crossOriginIsolated
    && metrics.firstTileMs !== null
    && metrics.scrollTileY > 0
    && zoomGeneration < latestGeneration
    && metrics.searchLatin.found
    && metrics.searchLatin.selectionText === "LibreOfficeKit"
    && metrics.searchCjk.found
    && metrics.searchCjk.selectionText === "臺灣軟體工程"
    && metrics.staleObserved
    && metrics.reloadedVersion === "v2"
    && metrics.oldWorkerClosedOnReload
    && metrics.crashCode === "WORKER_CRASHED"
    && metrics.recoveredWorkerGeneration > initialWorkerGeneration
    && metrics.closeSucceeded
    && metrics.tileDraws === drawsAtClose
    && metrics.lateTileDrawsAfterClose === 0
    && metrics.scheduler.completed > 0
    && metrics.schedulerHistory.every((item) => item.maxObservedInFlight <= 2)
    && metrics.schedulerHistory.some((item) => item.cancelled > 0
      || item.staleCompletions > 0);
  metrics.complete = true;
  elements.message.textContent = metrics.pass ? "R6-A 自動流程通過" : "R6-A invariant 失敗";
  appendLog({ type: "r6-a-result", pass: metrics.pass, metrics });
  if (!metrics.pass)
    throw new Error("R6-A browser invariants failed");
  return metrics;
}

function guard(action) {
  return async () => {
    try {
      await action();
    } catch (error) {
      metrics.error = { code: error.code || "UNEXPECTED", message: String(error.stack || error) };
      metrics.complete = true;
      elements.message.textContent = `${metrics.error.code}: ${metrics.error.message}`;
      elements.message.classList.add("error");
      appendLog(metrics.error);
    }
  };
}

let scrollTimer = 0;
elements.viewport.addEventListener("scroll", () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(scheduleViewport, 30);
});
$("#fit-width").addEventListener("click", guard(fitWidth));
$("#zoom-100").addEventListener("click", guard(() => setScale(1)));
$("#zoom-150").addEventListener("click", guard(() => setScale(1.5)));
$("#search-next").addEventListener("click", guard(() => searchNext()));
$("#remote-update").addEventListener("click", () => reader.markStale({
  documentId: currentSnapshot.documentId,
  previousVersion: currentSnapshot.version,
  version: remoteSnapshot.version,
  eventSequence: 1,
}));
$("#reload").addEventListener("click", guard(() => reload()));
$("#worker-crash").addEventListener("click", () => activeWorkerControl.crash());
$("#recover").addEventListener("click", guard(() =>
  reader.reload(currentSnapshot, { discardLocalBytes: true })));
$("#close").addEventListener("click", guard(async () => {
  await reader.close();
  closed = true;
}));
$("#download").addEventListener("click", () => {
  const bytes = reader.localBytes || currentSnapshot?.bytes;
  if (!bytes)
    return;
  const url = URL.createObjectURL(new Blob([bytes], {
    type: "application/vnd.oasis.opendocument.text",
  }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${currentSnapshot.documentId}-${reader.state.snapshot.version}.odt`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
});
$("#run-all").addEventListener("click", guard(runAll));

globalThis.__r6_reader = { runAll, searchNext, setScale, reload };
const initializationPromise = initialize().catch((error) => {
  metrics.error = { code: error.code || "INIT_FAILED", message: String(error.stack || error) };
  metrics.complete = true;
  appendLog(metrics.error);
  throw error;
});
