// SPEC E2-C, D4 follow-up: is the WASM heap really unreachable from the product?
//
// D4 registered "nothing in the product reports a WASM heap size" as a
// prediction and opened a relink queue item on the strength of it.  A relink
// mints a new identity and voids every verdict filed against the old one, so
// the premise is measured before it is paid for.
//
// THIS PAGE EDITS NOTHING.  The engine already prints
// `emscripten_get_heap_size()` at every stage (`probe_engine.cpp:1665`, no
// compile guard), the shipped worker already forwards stage events as
// `diagnostic` when `debug` is on, and `createDocumentEngine` already takes
// `debug`.  So the whole harness is: pass an option the SDK accepts, and
// subscribe to an event the SDK delivers.  No hash-bound file is touched.
//
// Two arms, because the first one cannot answer the leak question:
//   fresh   -- D4's own shape, a new session (hence a new Worker, hence a new
//              WASM instance) per cycle.  Shows whether the number arrives in
//              the shape D4 measures.
//   shared  -- one engine, every document through it.  DRIVEN AT THE SDK LEVEL
//              and declared as such: `EditorSession.close()` disposes its
//              engine by contract, so a shared engine cannot be the product
//              session.  This arm is not evidence about the product session.
//
// Criteria: findings/evidence/sdk-e2/e2-c-validation/d4/heap/PREDICTION.md

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { placeCaretVerified } from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const cycleCount = Number(params.get("cycles") || 8);
// `shared-nosearch` exists because the first `shared` rounds wedged: cycle 1
// worked, cycle 2's search never returned, and every later cycle came back BUSY
// -- in BOTH browsers.  Dropping the search is the controlled variable: if the
// same loop then completes eight cycles, the wedge belongs to search after a
// reopen and not to reopening itself.
const ARMS = ["fresh", "shared", "shared-nosearch"];
const arm = ARMS.includes(params.get("arm")) ? params.get("arm") : "fresh";
// The control arm for P-H5.  Default on, because the whole question is what
// debug makes visible; the runner drives a debug=0 round separately.
const debug = params.get("debug") !== "0";
const settleMs = Number(params.get("settleMs") || 1500);
const openTimeoutMs = Number(params.get("openTimeout") || 180000);

const workers = { created: 0, terminated: 0 };
const NativeWorker = globalThis.Worker;
globalThis.Worker = class extends NativeWorker {
  constructor(...args) {
    super(...args);
    workers.created += 1;
    const terminate = this.terminate.bind(this);
    this.terminate = () => { workers.terminated += 1; return terminate(); };
  }
};

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d4-heap",
  phase: "D4-followup",
  profile,
  arm,
  debug,
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated === true,
  cycles: [],
  // Every stage event that carried a heap figure, whole and in arrival order.
  // Not reduced to a per-cycle number here: a page that summarises decides, and
  // deciding is the analyzer's job.
  stages: [],
  workers,
  sampleState: { token: 0 },
  complete: false,
  error: null,
};
globalThis.__e2c_d4_heap = metrics;
globalThis.__probe_metrics = metrics;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
});

let currentCycle = 0;
let lastHeapBytes = null;
// The engine prints two numbers on the same stage line.  `heapBytes` is
// `emscripten_get_heap_size()`; every profile in this tree links with
// `-sTOTAL_MEMORY=1GB` and no ALLOW_MEMORY_GROWTH, so it is a constant by
// construction.  `sbrk` is the allocator's break -- the one that can move.
// Both are carried; neither is chosen here.
let lastSbrkBytes = null;

/** The one thing this page exists to try.
 *
 *  `event.event === "diagnostic"` with `level === "stage"` is what
 *  sdk-worker.js posts for an engine stage line; `detail.heapBytes` is what
 *  emitStage() puts in it.  Anything else is ignored rather than coerced --
 *  if the shape is not what the source says, the evidence should show an empty
 *  series, not a series of guesses. */
function attachHeapListener(engine, label) {
  return engine.onEvent((event) => {
    if (event?.event !== "diagnostic" || event.level !== "stage") return;
    const detail = event.detail || {};
    if (typeof detail.heapBytes !== "number") return;
    lastHeapBytes = detail.heapBytes;
    if (typeof detail.sbrk === "number") lastSbrkBytes = detail.sbrk;
    metrics.stages.push({
      engine: label,
      cycle: currentCycle,
      stage: detail.name ?? null,
      heapBytes: detail.heapBytes,
      sbrk: typeof detail.sbrk === "number" ? detail.sbrk : null,
      atMs: Math.round(performance.now()),
    });
  });
}

function publish(checkpoint, cycle, extra = {}) {
  metrics.sampleState = {
    token: metrics.sampleState.token + 1,
    checkpoint,
    cycle,
    activeWorkers: workers.created - workers.terminated,
    jsHeapBytes: globalThis.performance?.memory?.usedJSHeapSize ?? null,
    // The field R7-D's sampler has always read and always found null.  If the
    // reading behind this round is right, this is where it stops being null.
    wasmHeapBytes: lastHeapBytes,
    wasmSbrkBytes: lastSbrkBytes,
    atMs: Math.round(performance.now()),
    ...extra,
  };
}

const FIXTURE = { dir: "e2-fixtures", name: "d1-anchors.odt" };
const ANCHOR = "E2-D1-BODY-TARGET";

async function fixtureBytes() {
  const response = await fetch(`./${FIXTURE.dir}/${FIXTURE.name}`,
                              { cache: "no-cache" });
  if (!response.ok)
    throw new Error(`fixture fetch failed: ${response.status}`);
  return response.arrayBuffer();
}

function firstRectangle(found) {
  const values = (found.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((v) => Number.parseInt(v.trim(), 10));
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v)))
    throw Object.assign(new Error("search returned no usable rectangle"),
                        { code: "ANCHOR_RECTANGLE_UNUSABLE" });
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

function engineOptions() {
  return {
    workerUrl: `./profiles/${profile}/sdk-worker.js`,
    timeoutMs: 60000,
    debug,
  };
}

// ---- arm: fresh -----------------------------------------------------------
// D4's cycle, one option added.  Deliberately the same shape, so a heap value
// here is a heap value in the round D4 actually judged.

async function freshCycle(index) {
  const entry = { cycle: index, arm: "fresh",
                  startedAtMs: Math.round(performance.now()) };
  const stagesBefore = metrics.stages.length;
  const session = new NarrowEditorV2Session({
    engineFactory: async () => {
      const engine = await createDocumentEngine(engineOptions());
      attachHeapListener(engine, `fresh-${index}`);
      return engine;
    },
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
  try {
    await session.open({ bytes: (await fixtureBytes()).slice(0),
                         name: FIXTURE.name, timeoutMs: openTimeoutMs });
    session.attachInput(document.querySelector("#sink"));
    const rectangle = firstRectangle(
      await session.document.search(ANCHOR, { timeoutMs: 30000 }));
    const x = rectangle.x + Math.max(1, Math.floor(rectangle.width / 2));
    const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    await placeCaretVerified(session, x, y,
                             { caretTimeoutMs: 30000, anchorRect: rectangle });
    const result = await session.action("set-list-unordered");
    entry.completion = result.completion;
    entry.revision = result.revision;
    const { bytes } = await session.save({ timeoutMs: openTimeoutMs });
    entry.savedBytes = bytes.byteLength ?? bytes.length ?? null;
  } catch (error) {
    entry.error = publicError(error);
  } finally {
    await session.close().catch(() => {});
    entry.endedAtMs = Math.round(performance.now());
    entry.stageEvents = metrics.stages.length - stagesBefore;
  }
  return entry;
}

// ---- arm: shared ----------------------------------------------------------
// One engine for the whole run.  SDK level, declared: the product session
// disposes its engine on close, so "one engine across cycles" is not something
// the product session can be asked to do.

async function sharedCycle(engine, index) {
  const entry = { cycle: index, arm,
                  startedAtMs: Math.round(performance.now()) };
  const stagesBefore = metrics.stages.length;
  let handle = null;
  try {
    handle = await engine.open(await fixtureBytes(),
                               { name: FIXTURE.name, timeoutMs: openTimeoutMs });
    if (arm !== "shared-nosearch") {
      const rectangle = firstRectangle(
        await handle.search(ANCHOR, { timeoutMs: 30000 }));
      await handle.click(
        rectangle.x + Math.max(1, Math.floor(rectangle.width / 2)),
        rectangle.y + Math.max(1, Math.floor(rectangle.height / 2)));
    }
    // An edit, so the arm exercises the same machinery the product's cycle
    // does.  insertText rather than a paragraph action: the editor actions are
    // the client's, and the client is not what this arm is driving.
    await handle.insertText("H");
    entry.revision = handle.revision ?? null;
    // The SDK's handle.save returns the buffer itself, not a {bytes} wrapper
    // like the session's does.
    const saved = await handle.save({ format: "odt" },
                                    { timeoutMs: openTimeoutMs });
    entry.savedBytes = saved?.byteLength ?? saved?.length ?? null;
  } catch (error) {
    entry.error = publicError(error);
  } finally {
    await handle?.close().catch(() => {});
    entry.endedAtMs = Math.round(performance.now());
    entry.stageEvents = metrics.stages.length - stagesBefore;
  }
  return entry;
}

void (async () => {
  try {
    {
      const engine = await createDocumentEngine(engineOptions());
      const contract = engine.manifest?.editorContract || {};
      metrics.inventory = {
        profile: engine.manifest?.profile,
        abiVersion: contract.abiVersion,
        wasmSha256: contract.wasmSha256,
        loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
    }
    publish("baseline", 0);

    let shared = null;
    if (arm.startsWith("shared")) {
      shared = await createDocumentEngine(engineOptions());
      attachHeapListener(shared, "shared");
      metrics.sharedEngineGeneration = shared._generation ?? null;
    }

    for (let index = 1; index <= cycleCount; index += 1) {
      currentCycle = index;
      const entry = shared
        ? await sharedCycle(shared, index) : await freshCycle(index);
      entry.heapAfterCycleBytes = lastHeapBytes;
      entry.sbrkAfterCycleBytes = lastSbrkBytes;
      entry.activeWorkers = workers.created - workers.terminated;
      publish("quiescent", index);
      await new Promise((resolve) => setTimeout(resolve, settleMs));
      publish("settled", index);
      metrics.cycles.push(entry);
      log(entry);
    }

    if (shared) {
      // Read before dispose: a generation bump here means the engine was
      // restarted mid-run, and the PREDICTION says such a run is not joined.
      metrics.sharedEngineGenerationAtEnd = shared._generation ?? null;
      shared.dispose();
    }
    metrics.complete = true;
    log({ complete: true, cycles: metrics.cycles.length,
          stages: metrics.stages.length, workers });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
