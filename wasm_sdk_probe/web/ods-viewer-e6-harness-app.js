// Phase E's E6 harness (specs/SPEC-M4-ods-in-nextcloud.md §4 E6, addendum 6):
// the viewer link's own boot noise (B, A6.1) and the reopen series (A6.2), on
// the entries the runner staged.
//
// Two arms, both SDK-LEVEL and declared as such -- the product session
// disposes its engine on close (OdsViewerSession._release), so the product
// path cannot open twice on one engine; e2-c-d4-heap's shared arm carries the
// same declaration:
//   boots  -- N new OdsViewerEngine, the same bytes each time: open, close,
//             dispose.  The open.begin differences between them are the link's
//             own noise; B is their largest.
//   reopen -- ONE OdsViewerEngine: N x (open, one 1024x1024 tile per part,
//             close).  open.begin[n+1] - open.begin[n] is what a close did not
//             give back.  The SDK's open has no `open.close-previous` (engine
//             source, `!command.sdk` only), so every reopen is preceded by a
//             close, and the destroy stage lines are inside every cycle.
//
// Written only into a scratch mirror (tools/run_ods_viewer_e6_leak.py), in no
// product import graph.  It decides nothing: the runner's judges do.
import { OdsViewerEngine } from "./viewer-shell/ods-document-sdk.js";

const params = new URLSearchParams(location.search);
const NS = "__odsE6";
const CYCLES = Number.parseInt(params.get("cycles") || "5", 10);
const OPEN_TIMEOUT_MS = Number.parseInt(params.get("openTimeoutMs") || "180000", 10);
const TILE_PX = 1024;
const TWIPS_PER_PX = 15;
const TILE_REGION = { xTwips: 0, yTwips: 0, widthTwips: TILE_PX * TWIPS_PER_PX,
                      heightTwips: TILE_PX * TWIPS_PER_PX, canvasWidthPx: TILE_PX, canvasHeightPx: TILE_PX };
const WORKER_URL = "./profiles/ods-viewer-v1/sdk-worker.js";
// The destroy stage lines arrive while the document is closed; give the last
// of them a moment to cross the worker boundary (the Phase E harness waits the same).
const SETTLE_MS = 300;

const report = { schemaVersion: 1, release: "m4-ods-e6-harness", cycles: CYCLES, workerUrl: null,
                 entries: [], done: false, fatal: null };
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

function settle() {
  return new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
}

// One engine whose stage lines go to whichever cycle record is current.
function makeEngine(sink) {
  const engine = new OdsViewerEngine({ workerUrl: WORKER_URL, timeoutMs: 120000, debug: true });
  report.workerUrl = String(engine._workerUrl);
  engine.onEvent((event) => {
    if (event?.event === "worker-crashed") sink.current && (sink.current.workerCrashed = true);
    if (event?.event !== "diagnostic" || event.level !== "stage" || !event.detail) return;
    if (sink.current) sink.current.stages.push({ name: event.detail.name, sbrk: event.detail.sbrk });
  });
  return engine._initialize();
}

function newCycle(index) {
  return { cycle: index, startedAtMs: Math.round(performance.now()), stages: [], openBegin: null,
           destroyEnterSeen: false, parts: null, tiles: [], error: null, workerCrashed: false, elapsedMs: null };
}

function finishCycle(cycle) {
  cycle.openBegin = cycle.stages.find((s) => s.name === "open.begin")?.sbrk ?? null;
  cycle.destroyEnterSeen = cycle.stages.some((s) => s.name === "document-destroy-enter");
  cycle.peakSbrk = Math.max(-1, ...cycle.stages.filter((s) => Number.isInteger(s.sbrk)).map((s) => s.sbrk));
  if (cycle.peakSbrk < 0) cycle.peakSbrk = null;
  cycle.elapsedMs = Math.round(performance.now() - cycle.startedAtMs);
}

async function bootsArm(spec, bytes) {
  const arm = { arm: "boots", level: "sdk", cycles: [] };
  for (let n = 1; n <= CYCLES; n += 1) {
    const sink = { current: newCycle(n) };
    const cycle = sink.current;
    arm.cycles.push(cycle);
    let engine = null;
    let handle = null;
    try {
      engine = await makeEngine(sink);
      handle = await engine.open(bytes.slice(0), { name: spec.name, timeoutMs: OPEN_TIMEOUT_MS, transfer: true });
      cycle.parts = handle.parts;
      await handle.close({ timeoutMs: 30000 });
      await settle();
    } catch (error) {
      cycle.error = errorValue(error);
    } finally {
      try { engine?.dispose(); } catch { /* nothing left */ }
      finishCycle(cycle);
      sink.current = null;
    }
  }
  return arm;
}

async function reopenArm(spec, bytes) {
  const arm = { arm: "reopen", level: "sdk", cycles: [], engineError: null };
  const sink = { current: null };
  let engine = null;
  try {
    engine = await makeEngine(sink);
  } catch (error) {
    arm.engineError = errorValue(error);
    return arm;
  }
  for (let n = 1; n <= CYCLES; n += 1) {
    const cycle = newCycle(n);
    sink.current = cycle;
    arm.cycles.push(cycle);
    let handle = null;
    try {
      handle = await engine.open(bytes.slice(0), { name: spec.name, timeoutMs: OPEN_TIMEOUT_MS, transfer: true });
      cycle.parts = handle.parts;
      for (let k = 0; k < handle.parts; k += 1) {
        if (typeof handle.setPart === "function") await handle.setPart(k);
        const result = await handle.render(TILE_REGION, { timeoutMs: 60000 });
        cycle.tiles.push({ part: k, sha256: await sha256Hex(new Uint8Array(result.pixels)) });
      }
      await handle.close({ timeoutMs: 30000 });
      await settle();
    } catch (error) {
      cycle.error = errorValue(error);
      try { await handle?.close({ timeoutMs: 30000 }); } catch { /* recorded above */ }
    } finally {
      finishCycle(cycle);
      sink.current = null;
    }
  }
  try { engine.dispose(); } catch { /* nothing left */ }
  return arm;
}

async function runEntry(spec) {
  const entry = { name: spec.name, path: spec.path, file: spec.file, inputSha256: null, inputBytes: null,
                  boots: null, reopen: null, fatal: null };
  report.entries.push(entry);
  try {
    const response = await fetch(spec.file);
    if (!response.ok) throw new Error(`fetch ${spec.file}: ${response.status}`);
    const bytes = await response.arrayBuffer();
    entry.inputBytes = bytes.byteLength;
    entry.inputSha256 = await sha256Hex(new Uint8Array(bytes));
    entry.boots = await bootsArm(spec, bytes);
    entry.reopen = await reopenArm(spec, bytes);
  } catch (error) {
    entry.fatal = errorValue(error);
  }
}

async function main() {
  try {
    const specs = await (await fetch("./ods-e6-cases.json")).json();
    report.caseCount = specs.length;
    for (const spec of specs) await runEntry(spec);
  } catch (error) {
    report.fatal = errorValue(error);
  }
  report.done = true;
}
main();
