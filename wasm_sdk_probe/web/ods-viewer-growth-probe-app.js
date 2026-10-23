// finding 164's work item (SPEC-M4-viewer-v2 §11): growth WITHIN one open,
// measured by count.  Each run is a fresh OdsViewerEngine, one open, K
// operations, close, dispose; the runner compares document-destroy-enter's
// sbrk across K.  The link's boots are identical (B = 0, §8.5), so the K
// operations are the only difference between two runs of one arm.
//
//   paint   -- K 256x256 px tiles (the product's tileSizePx) at 15 twips/px
//              along a scroll path: four per row, row after row, wrapping to
//              the top past the document's height.
//   switch  -- K x (setPart(i mod parts), one 256 px tile at (0,0)).
//   control -- K x one 4096x4096 px tile at (0,0): the engine callocs 64 MiB
//              for it, so destroy-enter must show it (the positive control).
//
// SDK-level, like the E6 harness.  Written only into a scratch mirror
// (tools/probe_ods_viewer_intra_open_growth.py), in no product import graph.
// It records; it decides nothing.
import { OdsViewerEngine } from "./viewer-shell/ods-document-sdk.js";

const NS = "__odsGrowth";
const OPEN_TIMEOUT_MS = 180000;
const TWIPS_PER_PX = 15;
const TILE_PX = 256;
const CONTROL_PX = 4096;
const COLUMNS = 4;
const WORKER_URL = "./profiles/ods-viewer-v2/sdk-worker.js";
// The destroy stage lines arrive while the document is closed (the E6 harness waits the same).
const SETTLE_MS = 300;

const report = { schemaVersion: 1, release: "m4-ods-growth-probe", workerUrl: null, runs: [], done: false, fatal: null };
window[NS] = report;

function errorValue(error) {
  if (!error) return null;
  return { name: error.name || null, code: error.code || null,
           message: String(error.message || error).slice(0, 400) };
}

function settle() {
  return new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
}

function region(xTwips, yTwips, px) {
  return { xTwips, yTwips, widthTwips: px * TWIPS_PER_PX, heightTwips: px * TWIPS_PER_PX,
           canvasWidthPx: px, canvasHeightPx: px };
}

async function operate(arm, handle, k, run) {
  const step = TILE_PX * TWIPS_PER_PX;
  const rows = Math.max(1, Math.floor((handle.heightTwips || step) / step));
  for (let i = 0; i < k; i += 1) {
    if (arm === "paint") {
      const row = Math.floor(i / COLUMNS) % rows;
      await handle.render(region((i % COLUMNS) * step, row * step, TILE_PX), { timeoutMs: 60000 });
    } else if (arm === "switch") {
      await handle.setPart(i % handle.parts);
      await handle.render(region(0, 0, TILE_PX), { timeoutMs: 60000 });
    } else if (arm === "control") {
      await handle.render(region(0, 0, CONTROL_PX), { timeoutMs: 120000 });
    } else {
      throw new Error(`unknown arm ${arm}`);
    }
    run.operations = i + 1;
  }
  run.rows = rows;
}

async function runOne(spec, bytes) {
  const run = { ...spec, stages: [], opsStartStage: null, operations: 0, rows: null, parts: null,
                widthTwips: null, heightTwips: null, error: null, workerCrashed: false, elapsedMs: null };
  report.runs.push(run);
  const started = performance.now();
  let engine = null;
  let handle = null;
  try {
    engine = new OdsViewerEngine({ workerUrl: WORKER_URL, timeoutMs: 120000, debug: true });
    report.workerUrl = String(engine._workerUrl);
    engine.onEvent((event) => {
      if (event?.event === "worker-crashed") run.workerCrashed = true;
      if (event?.event !== "diagnostic" || event.level !== "stage" || !event.detail) return;
      run.stages.push({ name: event.detail.name, sbrk: event.detail.sbrk });
    });
    await engine._initialize();
    handle = await engine.open(bytes.slice(0), { name: spec.name, timeoutMs: OPEN_TIMEOUT_MS, transfer: true });
    run.parts = handle.parts;
    run.widthTwips = handle.widthTwips ?? null;
    run.heightTwips = handle.heightTwips ?? null;
    run.opsStartStage = run.stages.length;
    await operate(spec.arm, handle, spec.k, run);
    await handle.close({ timeoutMs: 30000 });
    await settle();
  } catch (error) {
    run.error = errorValue(error);
    try { await handle?.close({ timeoutMs: 30000 }); await settle(); } catch { /* recorded above */ }
  } finally {
    try { engine?.dispose(); } catch { /* nothing left */ }
    run.elapsedMs = Math.round(performance.now() - started);
  }
}

async function main() {
  try {
    const plan = await (await fetch("./ods-growth-plan.json")).json();
    report.planned = plan.length;
    const files = new Map();
    for (const spec of plan) {
      if (!files.has(spec.file)) {
        const response = await fetch(spec.file);
        if (!response.ok) throw new Error(`fetch ${spec.file}: ${response.status}`);
        files.set(spec.file, await response.arrayBuffer());
      }
      await runOne(spec, files.get(spec.file));
    }
  } catch (error) {
    report.fatal = errorValue(error);
  }
  report.done = true;
}
main();
