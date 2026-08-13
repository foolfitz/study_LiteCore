// Task 035: what the SHIPPED EditorSession does when the finding 038 wedge fires.
//
// Everything measured for 038 so far drove `NarrowEditorClient` bolted straight
// onto a `DocumentHandle` (`e1-note-frame-select-app.js`).  That is the layer
// BELOW the product.  The demo editor and `e1-editor-app.js` both drive
// `EditorSession`, which has a queue, a state machine and a restart path that
// the 038 runs never touched -- so "the editor is unusable afterwards" is, at
// the product layer, still an untested inference.
//
// This decides how big option (d) is.  (d) is "generalise the bounded close
// recovery to any engine-thread timeout".  If the session already escalates and
// already recovers, (d) is typing an existing behaviour down and tightening a
// deadline.  If it hangs, or recovers into something broken, (d) is a build.
//
// PREDICTIONS, written before the run, from reading the source:
//
//   1. `selectRange` on the wedge rejects with code TIMEOUT at ~30000 ms, not
//      15000: `EditorSession.selectRange` forwards no options, so the request
//      falls back to `_defaultTimeoutMs` (document-sdk.js:88), which
//      `engineFactory` sets to 30000.
//   2. TIMEOUT is in RECOVERY_ERRORS (editor-session.js:15-22), so the drain's
//      catch calls `_blockQueue(error, "recoverable-error", …)` -- state
//      `recoverable-error`, NOT `restart-required`.  `restart-required` is
//      reserved for EDITOR_BOUNDARY_UNSUPPORTED.
//   3. Further operations are then refused immediately by `_enqueue`'s state
//      guard with EDITOR_NOT_READY -- no second 30 s freeze.
//   4. `restart()` succeeds, because `_disposeRuntime({closeDocument:false})`
//      skips the close that finding 012 makes slow and just terminates the
//      Worker, parked engine thread and all.
//   5. Everything typed since the last save is GONE after the restart:
//      `_openFresh` reopens `_authorityBytes`, which only `save()` updates.
//      SPEC-E1-C 9.1 already asserts this; here it gets measured.
//   6. The session survives exactly TWO wedges.  `_maxWorkerGenerations`
//      defaults to 3 and `_openFresh` refuses at `_generation >= max`:
//      open=1, restart=2, restart=3, and the third restart throws
//      WORKER_GENERATION_LIMIT with requiresPageReload.  For a demo that is
//      the number that matters -- three bad selections and only F5 helps.
//
// A prediction that survives is worth more than one invented afterwards, so
// each is scored against the run in `metrics.predictions`.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { EditorSession } from "./editor-shell/editor-session.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-v1";
const fixture = params.get("fixture") || "frame-contexts.odt";
// The generation-ceiling probe costs one extra wedge (~30 s) plus a restart.
// It is the only case that answers "how many times can a demo survive this",
// so it is on by default and switchable off rather than the other way round.
const exhaustGenerations = params.get("exhaust") !== "0";

const MARKER = "WEDGE-MARKER-035";

const status = document.querySelector("#status");
const logNode = document.querySelector("#log");

const metrics = {
  schemaVersion: 1,
  release: "e1-session-wedge-recovery",
  task: "035 -- does EditorSession escalate and recover from the 038 wedge",
  profile,
  fixture,
  userAgent: navigator.userAgent,
  manifest: null,
  states: [],
  engineEvents: [],
  steps: [],
  predictions: {},
  complete: false,
  error: null,
};
globalThis.__e1_session_wedge = metrics;
globalThis.__probe_metrics = metrics;

const started = performance.now();
const now = () => Math.round(performance.now() - started);

function log(value) {
  logNode.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
}

function errorValue(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
    details: error?.details ?? null,
  };
}

/** One timed step, recorded whether it resolves or throws. */
async function step(label, action) {
  const entry = { label, at: now(), status: "running" };
  metrics.steps.push(entry);
  status.textContent = label;
  const stepStarted = performance.now();
  try {
    entry.value = await action();
    entry.status = "resolved";
  } catch (error) {
    entry.error = errorValue(error);
    entry.status = "rejected";
  }
  entry.elapsedMs = Math.round(performance.now() - stepStarted);
  entry.stateAfter = session?.state?.snapshot?.state ?? null;
  entry.generationAfter = session?.state?.snapshot?.generation ?? null;
  log(entry);
  return entry;
}

let session = null;

function firstRectangle(search) {
  const raw = (search?.selections?.[0]?.rectangles || "").split(";")[0];
  const numbers = raw.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item)))
    throw new Error("search did not return a usable rectangle");
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

/** Locate an anchor and return the span to drag across it. */
async function spanFor(anchor, spanTwips = null) {
  const found = await session.document.search(anchor, { timeoutMs: 30000 });
  if (!found?.found)
    throw new Error(`anchor not found: ${anchor}`);
  const rectangle = firstRectangle(found);
  const midY = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  return {
    start: { xTwips: rectangle.x, yTwips: midY },
    end: { xTwips: rectangle.x + (spanTwips ?? 8000), yTwips: midY },
  };
}

/** Is the marker text still in the document the session is holding? */
async function markerPresent() {
  try {
    const found = await session.document.search(MARKER, { timeoutMs: 30000 });
    return found?.found === true;
  } catch (error) {
    return { searchFailed: errorValue(error) };
  }
}

/** Drive the 038 trigger through the product queue. */
async function wedge(label) {
  const span = await spanFor("FX-NOTE");
  return step(label, () => session.selectRange(span.start, span.end));
}

async function main() {
  let bytes = null;
  try {
    status.textContent = "loading fixture";
    const response = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" });
    if (!response.ok)
      throw new Error(`fixture fetch failed: ${response.status}`);
    bytes = await response.arrayBuffer();

    session = new EditorSession({
      engineFactory: () => createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`,
        timeoutMs: 30000,
      }),
      onState(snapshot) {
        metrics.states.push({
          at: now(),
          state: snapshot.state,
          generation: snapshot.generation ?? null,
          revision: snapshot.revision ?? null,
          dirty: snapshot.dirty ?? null,
          pending: snapshot.pending ?? null,
          error: snapshot.error ?? null,
        });
      },
      onEvent(event) {
        metrics.engineEvents.push({ at: now(), event: event.event });
      },
    });

    await step("open", async () => {
      const snapshot = await session.open({ bytes: bytes.slice(0), name: fixture });
      metrics.manifest = session.engine.manifest;
      return { state: snapshot.state, generation: snapshot.generation };
    });

    // Control.  Same gesture, same document, a paragraph with no frame: if this
    // one wedged too, the wedge would not be about the note at all.
    const plain = await spanFor("FX-PLAIN");
    await step("control-select-plain", () => session.selectRange(plain.start, plain.end));

    // Make the session dirty and diverged from the authority bytes, so
    // "what does a restart cost the user" is answerable rather than assumed.
    // Committing over the selection avoids depending on placeCaret, which has
    // its own open finding (021) and is not what this run is measuring.
    await step("commit-marker", () => session.commitText(MARKER));
    await step("marker-before-wedge", () => markerPresent());

    // The trigger.
    await wedge("wedge-1-select-note");

    // Prediction 3: once blocked, the next operation is refused at once.
    await step("operation-while-blocked", () => session.selectRange(plain.start, plain.end));

    await step("restart-1", async () => {
      const snapshot = await session.restart();
      return { state: snapshot.state, generation: snapshot.generation };
    });
    await step("marker-after-restart", () => markerPresent());

    // Prediction: a restarted session is a working session.
    await step("post-restart-select", async () => {
      const span = await spanFor("FX-PLAIN");
      return session.selectRange(span.start, span.end);
    });
    await step("post-restart-commit", () => session.commitText("AFTER-RESTART"));

    if (exhaustGenerations) {
      await wedge("wedge-2-select-note");
      await step("restart-2", async () => {
        const snapshot = await session.restart();
        return { state: snapshot.state, generation: snapshot.generation };
      });
      await wedge("wedge-3-select-note");
      // Prediction 6: this is the one that fails, and it fails for a reason
      // that has nothing to do with 038 -- the generation ceiling.
      await step("restart-3", async () => {
        const snapshot = await session.restart();
        return { state: snapshot.state, generation: snapshot.generation };
      });
    }

    status.textContent = "complete";
  } catch (error) {
    metrics.error = errorValue(error);
    status.textContent = "failed";
    log({ fatal: metrics.error });
  } finally {
    scorePredictions();
    try {
      await session?.close();
    } catch (error) {
      metrics.closeError = errorValue(error);
    }
    metrics.complete = true;
  }
}

/** Score each written-down prediction against what the run actually recorded. */
function scorePredictions() {
  const byLabel = (label) => metrics.steps.find((item) => item.label === label);
  const record = (key, predicted, observed) => {
    metrics.predictions[key] = {
      predicted,
      observed,
      held: JSON.stringify(predicted) === JSON.stringify(observed),
    };
  };

  const wedge1 = byLabel("wedge-1-select-note");
  record("1-wedge-rejects-timeout-near-30s", { code: "TIMEOUT", deadlineMs: 30000 }, {
    code: wedge1?.error?.code ?? null,
    deadlineMs: wedge1?.elapsedMs == null ? null
      : Math.round(wedge1.elapsedMs / 1000) * 1000,
  });
  record("2-state-is-recoverable-error", "recoverable-error", wedge1?.stateAfter ?? null);
  record("3-next-operation-refused-fast",
    { code: "EDITOR_NOT_READY", fast: true },
    {
      code: byLabel("operation-while-blocked")?.error?.code ?? null,
      fast: (byLabel("operation-while-blocked")?.elapsedMs ?? Infinity) < 1000,
    });
  record("4-restart-succeeds", { status: "resolved", state: "ready" }, {
    status: byLabel("restart-1")?.status ?? null,
    state: byLabel("restart-1")?.value?.state ?? null,
  });
  record("5-unsaved-work-lost",
    { beforeWedge: true, afterRestart: false },
    {
      beforeWedge: byLabel("marker-before-wedge")?.value ?? null,
      afterRestart: byLabel("marker-after-restart")?.value ?? null,
    });
  if (exhaustGenerations) {
    record("6-third-restart-hits-generation-limit",
      { status: "rejected", code: "WORKER_GENERATION_LIMIT" },
      {
        status: byLabel("restart-3")?.status ?? null,
        code: byLabel("restart-3")?.error?.code ?? null,
      });
  }
  log({ predictions: metrics.predictions });
}

main();
