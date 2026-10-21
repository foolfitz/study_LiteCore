// Phase E's harness page (specs/SPEC-M4-ods-in-nextcloud.md §4, E1-E6): every
// corpus entry the runner staged, opened through the viewer's own session and
// SDK -- the same OdsViewerSession and OdsViewerEngine the product page uses --
// with the handle intercepted so that E3's part text, E4a's two paints and
// E5's engine-side refusal can be asked of the engine directly.
//
// It is written only into a scratch mirror of dist/ (tools/run_ods_viewer_phase_e.py)
// and is in no product import graph.  It decides nothing: it records what the
// engine and the session said, and the runner's judges decide.  Large values
// (sheet text, tile pixels) are recorded as sha256 and size, so a report slice
// stays far below CDP's 1 MiB frame; the runner hashes the expected text the
// same way.
import { OdsViewerEngine } from "./viewer-shell/ods-document-sdk.js";
import { OdsViewerSession } from "./viewer-shell/ods-viewer-session.js";

const params = new URLSearchParams(location.search);
const OPEN_TIMEOUT_MS = Number.parseInt(params.get("openTimeoutMs") || "180000", 10);
// `?recordText=1` (diagnostic, after the first full run): keep a sheet's text itself, not only
// its sha, when it is small enough for a CDP slice, so a differing text can be read.
const RECORD_TEXT = params.get("recordText") === "1";
const RECORD_TEXT_MAX = 20000;
const TILE_PX = 1024;
const TWIPS_PER_PX = 15;
const NS = "__odsPhaseE";
const DISTINCT_MESSAGES_KEPT = 200;

// The page's one worker literal; the runner rewrites it in its mirror copy for another profile.
const WORKER_URL = "./profiles/ods-viewer-v1/sdk-worker.js";
const WORKER_ABSOLUTE = new URL(WORKER_URL, location.href);

const report = { schemaVersion: 1, release: "m4-ods-phase-e-harness", openTimeoutMs: OPEN_TIMEOUT_MS,
                 workerUrl: null, cases: [], done: false, fatal: null };
window[NS] = report;

function errorValue(error) {
  if (!error) return null;
  return { name: error.name || null, code: error.code || null,
           message: String(error.message || error).slice(0, 400) };
}

async function sha256Hex(bytes) {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// The normalisation E3 names: CRLF to LF, nothing else.
async function textDigest(text) {
  const normalised = String(text ?? "").replace(/\r\n/g, "\n");
  return { sha256: await sha256Hex(new TextEncoder().encode(normalised)), length: normalised.length };
}

async function tileRecord(result) {
  const view = new Uint8Array(result.pixels);
  let nonPaper = 0;
  for (let i = 0; i + 3 < view.length; i += 4)
    if (view[i] !== 255 || view[i + 1] !== 255 || view[i + 2] !== 255) nonPaper += 1;
  return {
    width: result.width, height: result.height, bytes: view.length, nonPaperPixels: nonPaper,
    sha256: await sha256Hex(view),
    widthTwipsType: typeof result.documentWidthTwips,
    heightTwipsType: typeof result.documentHeightTwips,
    sizeChangedType: typeof result.documentSizeChanged,
    documentWidthTwips: result.documentWidthTwips ?? null,
    documentHeightTwips: result.documentHeightTwips ?? null,
    documentSizeChanged: result.documentSizeChanged ?? null,
  };
}

// SPEC-M4-viewer-v2 3.4: what the product page does -- the manifest beside the
// worker, asked only for a file with form controls (the session decides when).
async function formControlsSupported() {
  const response = await fetch(new URL("./sdk-manifest.json", WORKER_ABSOLUTE), { cache: "no-cache" });
  if (!response.ok) return false;
  const manifest = await response.json();
  return Array.isArray(manifest?.capabilities) && manifest.capabilities.includes("form-controls");
}

const TILE_REGION = { xTwips: 0, yTwips: 0, widthTwips: TILE_PX * TWIPS_PER_PX,
                      heightTwips: TILE_PX * TWIPS_PER_PX, canvasWidthPx: TILE_PX, canvasHeightPx: TILE_PX };

function recordEvent(entry, started, event) {
  if (!event?.event) return;
  if (event.event === "view-ready" && entry.viewReadyAtMs === null)
    entry.viewReadyAtMs = Math.round(performance.now() - started);
  if (event.event === "worker-crashed") entry.workerCrashed = true;
  if (event.event !== "diagnostic") return;
  if (event.level === "stage" && event.detail) {
    entry.stages.push({ name: event.detail.name, sbrk: event.detail.sbrk });
    return;
  }
  const text = String(event.message ?? JSON.stringify(event.detail ?? "")).slice(0, 160);
  if (entry.messageIndex.has(text)) entry.messageIndex.get(text).count += 1;
  else if (entry.messages.length < DISTINCT_MESSAGES_KEPT) {
    const row = { message: text, count: 1 };
    entry.messageIndex.set(text, row);
    entry.messages.push(row);
  }
}

async function runCase(spec) {
  const entry = {
    name: spec.name, kind: spec.kind, file: spec.file, inputSha256: null, inputBytes: null,
    engineCreated: false, viewReadyAtMs: null, workerCrashed: false, opened: null,
    refused: null, error: null, state: null, handleFields: null,
    sheets: [], engineRefusal: null, sessionRefusal: null,
    stages: [], messages: [], messageIndex: new Map(), closed: false, elapsedMs: null,
  };
  report.cases.push(entry);
  const started = performance.now();
  let handle = null;
  // SPEC-M4-viewer-v2 4 (V2-157): how many switches reached the handle -- a hidden
  // sheet must be refused by the session with none.
  let setPartCalls = 0;
  const response = await fetch(spec.file);
  if (!response.ok) throw new Error(`fetch ${spec.file}: ${response.status}`);
  const bytes = await response.arrayBuffer();
  entry.inputBytes = bytes.byteLength;
  entry.inputSha256 = await sha256Hex(new Uint8Array(bytes));

  const session = new OdsViewerSession({
    openTimeoutMs: OPEN_TIMEOUT_MS,
    formControlsSupported,
    tileOptions: { tileSizePx: 256, prefetchTiles: 0, maxInFlight: 1 },
    onEvent: (event) => recordEvent(entry, started, event),
    engineFactory: async ({ onEvent }) => {
      entry.engineCreated = true;
      const engine = new OdsViewerEngine({ workerUrl: WORKER_URL, timeoutMs: 120000, debug: true });
      report.workerUrl = String(engine._workerUrl);
      engine.onEvent(onEvent);
      const open = engine.open.bind(engine);
      engine.open = async (...args) => {
        handle = await open(...args);
        if (typeof handle.setPart === "function") {
          const setPart = handle.setPart;
          handle.setPart = (...setArgs) => { setPartCalls += 1; return setPart(...setArgs); };
        }
        return handle;
      };
      return engine._initialize();
    },
  });
  try {
    await session.open({ bytes, name: spec.name });
    entry.opened = { atMs: Math.round(performance.now() - started) };
  } catch (error) {
    if (session.state.state === "refused") entry.refused = errorValue(error);
    else entry.error = errorValue(error);
  }
  entry.state = JSON.parse(JSON.stringify(session.state));
  if (handle) {
    entry.handleFields = { documentType: handle.documentType ?? null, inputSuffix: handle.inputSuffix ?? null,
                           parts: handle.parts, partNames: handle.partNames ?? null,
                           currentPartAtOpen: handle.currentPart ?? null };
  }
  if (entry.opened && handle) {
    const parts = handle.parts;
    for (let k = 0; k < parts; k += 1) {
      const sheet = { part: k, switch: null, readBack: null, text: null, tiles: [], error: null,
                      setPartCalls: null, readBackAfterError: null };
      entry.sheets.push(sheet);
      const callsBefore = setPartCalls;
      try {
        // E5 through the session (its read-back is the engine's), then E3 and E4a on the handle.
        const before = session.state.currentPart;
        try {
          await session.showPart(k);
        } finally {
          sheet.setPartCalls = setPartCalls - callsBefore;
        }
        sheet.switch = { before, after: session.state.currentPart, readBack: session.state.currentPartReadBack };
        sheet.readBack = await handle.readCurrentPart();
        const partBefore = handle.currentPart;
        const text = await handle.partText(k);
        sheet.text = { ...(await textDigest(text.text)), textNull: text.textNull,
                       selectAllConfirmed: text.selectAllConfirmed, partBefore: text.partBefore,
                       partAfter: text.partAfter, currentPartBefore: partBefore,
                       // SPEC-M4-viewer-v2 3.3: present only from v2's engine.
                       selectAllWaitMs: text.selectAllWaitMs ?? null,
                       selectAllDeadlineMs: text.selectAllDeadlineMs ?? null,
                       lateSelectAllResults: text.lateSelectAllResults ?? null };
        if (RECORD_TEXT && typeof text.text === "string" && text.text.length <= RECORD_TEXT_MAX)
          sheet.text.sample = text.text;
        for (let n = 0; n < 2; n += 1)
          sheet.tiles.push(await tileRecord(await handle.render(TILE_REGION, { timeoutMs: 60000 })));
      } catch (error) {
        sheet.error = errorValue(error);
        // Where the engine is after a refused or failed switch (V2-157: unchanged).
        try { sheet.readBackAfterError = await handle.readCurrentPart(); } catch { /* recorded as null */ }
      }
    }
    // E5: the current part again reads back unchanged; part `parts` is refused,
    // by the session before the engine and by the engine itself, and the
    // engine's part does not move.
    try {
      const current = await handle.readCurrentPart();
      await session.showPart(current);
      entry.reselect = { current, readBack: await handle.readCurrentPart() };
      try { await session.showPart(parts); } catch (error) { entry.sessionRefusal = errorValue(error); }
      try { await handle.setPart(parts); } catch (error) { entry.engineRefusal = errorValue(error); }
      entry.afterRefusals = await handle.readCurrentPart();
    } catch (error) {
      entry.e5Error = errorValue(error);
    }
  }
  try { await session.close(); entry.closed = true; } catch (error) { entry.closeError = errorValue(error); }
  // The destroy stage lines arrive while the document is closed; give the
  // last of them a moment to cross the worker boundary.
  await new Promise((resolve) => setTimeout(resolve, 300));
  entry.elapsedMs = Math.round(performance.now() - started);
  delete entry.messageIndex;
}

async function main() {
  try {
    const specs = await (await fetch("./ods-e-cases.json")).json();
    report.caseCount = specs.length;
    for (const spec of specs) {
      try { await runCase(spec); }
      catch (error) { report.cases.push({ name: spec.name, fatal: errorValue(error) }); }
    }
  } catch (error) {
    report.fatal = errorValue(error);
  }
  report.done = true;
}
main();
