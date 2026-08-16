// SPEC E2-C, phase D4: bounded lifecycle.
//
// Ten independent edit-save-reopen sessions, one page load, and the numbers the
// frozen matrix asks for: worker generations per session, residual workers and
// handles after close, and memory at two checkpoints per cycle.
//
// The page measures and publishes.  It does not judge, and it does not sample
// the process -- that is the runner's job, because a page cannot see its own
// browser's PSS.  The page's contract with the runner is `sampleState.token`:
// bump it, and the runner takes a process snapshot labelled with whatever the
// page put beside it.  That is R7-D's pattern, reused rather than reinvented.
//
// Criteria and predictions:
// findings/evidence/sdk-e2/e2-c-validation/d4/PREDICTION.md

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Session } from "./editor-shell-v2/narrow-editor-v2-session.js";
import { placeCaretVerified } from "./e2-c-caret.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const cycleCount = Number(params.get("cycles") || 10);
// The matrix says "at quiescence, and again three seconds later, smaller value
// used".  Both numbers are the runner's; the page only marks the moments.
const secondSampleDelayMs = Number(params.get("settleMs") || 3000);
const openTimeoutMs = Number(params.get("openTimeout") || 180000);

// Counted the way E1-C's lifecycle phase counts them: wrap the constructor, and
// wrap terminate() with it.  A count the product volunteers would be a count of
// what the product believes; this one is of what the browser was actually asked
// to make.
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

const handles = { opened: 0, closed: 0 };

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d4",
  phase: "D4",
  profile,
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated === true,
  cycles: [],
  workers,
  handles,
  memoryApi: null,
  sampleState: { token: 0 },
  complete: false,
  error: null,
};
globalThis.__e2c_d4 = metrics;
globalThis.__probe_metrics = metrics;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
});

/** The only browser-side route to a WASM heap figure that exists at all.
 *
 *  Recorded WHOLE -- the breakdown, its types, and whatever the browser refuses
 *  to say -- rather than reduced to a number here.  PREDICTION.md P-D4-4 says
 *  this will not yield a WASM-attributed figure in either browser; a summary
 *  written by the page would make that prediction unfalsifiable. */
async function measureMemory() {
  if (typeof performance.measureUserAgentSpecificMemory !== "function")
    return { available: false, why: "measureUserAgentSpecificMemory unavailable" };
  try {
    const value = await performance.measureUserAgentSpecificMemory();
    return {
      available: true,
      bytes: value.bytes ?? null,
      breakdown: (value.breakdown || []).map((entry) => ({
        bytes: entry.bytes, types: entry.types,
        attributionCount: (entry.attribution || []).length,
      })),
    };
  } catch (error) {
    return { available: false, why: String(error).slice(0, 200) };
  }
}

function publish(checkpoint, cycle, extra = {}) {
  metrics.sampleState = {
    token: metrics.sampleState.token + 1,
    checkpoint,
    cycle,
    activeWorkers: workers.created - workers.terminated,
    activeHandles: handles.opened - handles.closed,
    jsHeapBytes: globalThis.performance?.memory?.usedJSHeapSize ?? null,
    // Always null here, and deliberately visible: no product path reports it.
    // See PREDICTION.md.  Left in the shape R7-D's sampler already reads so the
    // absence is legible in the evidence rather than a missing key.
    wasmHeapBytes: null,
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

async function anchorRectangle(session, anchor) {
  const found = await session.document.search(anchor, { timeoutMs: 30000 });
  if (!found.found)
    throw Object.assign(new Error(`anchor not found: ${anchor}`),
                        { code: "ANCHOR_NOT_FOUND" });
  const values = (found.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((v) => Number.parseInt(v.trim(), 10));
  if (values.length !== 4 || values.some((v) => !Number.isFinite(v)))
    throw Object.assign(new Error("search returned no usable rectangle"),
                        { code: "ANCHOR_RECTANGLE_UNUSABLE" });
  return { x: values[0], y: values[1], width: values[2], height: values[3] };
}

async function runCycle(index) {
  const entry = { cycle: index, startedAtMs: Math.round(performance.now()) };
  const session = new NarrowEditorV2Session({
    engineFactory: () => createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    }),
    secureContext: globalThis.isSecureContext,
    clipboard: navigator.clipboard,
  });
  try {
    await session.open({ bytes: (await fixtureBytes()).slice(0),
                         name: FIXTURE.name, timeoutMs: openTimeoutMs });
    handles.opened += 1;
    session.attachInput(document.querySelector("#sink"));
    const rectangle = await anchorRectangle(session, ANCHOR);
    const x = rectangle.x + Math.max(1, Math.floor(rectangle.width / 2));
    const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    const { arrivedAfterMs } = await placeCaretVerified(
      session, x, y, { caretTimeoutMs: 30000, anchorRect: rectangle });
    entry.caretArrivedAfterMs = arrivedAfterMs ?? null;
    const result = await session.action("set-list-unordered");
    entry.completion = result.completion;
    entry.revision = result.revision;
    const { bytes } = await session.save({ timeoutMs: openTimeoutMs });
    entry.savedBytes = bytes.byteLength ?? bytes.length ?? null;
    // What the SESSION says about its own generations, which is the bound the
    // matrix names.  Read before close, because close is where it goes away.
    // The session's own typed state carries it (`state.snapshot.generation`,
    // set on every transition), so this is the product's number rather than a
    // count the harness kept beside it.
    entry.workerGenerations = session.state?.snapshot?.generation ?? null;
  } catch (error) {
    entry.error = publicError(error);
  } finally {
    await session.close().catch(() => {});
    handles.closed += 1;
    entry.endedAtMs = Math.round(performance.now());
  }
  return entry;
}

void (async () => {
  try {
    {
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const contract = engine.manifest?.editorContract || {};
      metrics.inventory = {
        profile: engine.manifest?.profile,
        abiVersion: contract.abiVersion,
        wasmSha256: contract.wasmSha256,
        loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
      handles.opened += 0;
    }
    metrics.memoryApi = await measureMemory();
    publish("baseline", 0, { memory: metrics.memoryApi });

    for (let index = 1; index <= cycleCount; index += 1) {
      const entry = await runCycle(index);
      // Quiescence first: close() has resolved, so there is nothing in flight.
      entry.memoryAtQuiescence = await measureMemory();
      publish("quiescent", index, { memory: entry.memoryAtQuiescence });
      await new Promise((resolve) => setTimeout(resolve, secondSampleDelayMs));
      entry.memoryAfterSettle = await measureMemory();
      publish("settled", index, { memory: entry.memoryAfterSettle });
      entry.activeWorkers = workers.created - workers.terminated;
      entry.activeHandles = handles.opened - handles.closed;
      metrics.cycles.push(entry);
      log(entry);
    }

    metrics.complete = true;
    log({ complete: true, cycles: metrics.cycles.length, workers, handles });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
