// Finding 018 discriminating experiment.
//
// Question: is the nondeterministic completion of Home/End line navigation the
// same root cause as finding 021 -- an engine loop that never advances the VCL
// scheduler -- or something else?
//
// Both `e1-editor-discovery` (no live loop) and `e2-mainloop-attribution`
// (live loop via SAL_LOK_OPTIONS=unipoll + Application::Execute) declare
// `editor-discovery-closed-actions`, so the same closed line actions can be
// driven against both **with no rebuild**.  Control vs exposure differ in the
// loop and nothing else.
//
// The sequence is finding 018's own minimal repro: open multi-paragraph.odt,
// put the caret at the end of the "第二段中文 beta" rectangle, then alternate
// three rounds of Home/End waiting for the typed cursor callback.
//
// Each round uses a fresh engine: finding 018 records that one timeout leaves
// gEditorPending set, so every later action in that worker returns BUSY and
// would tell us nothing.

import { createDocumentEngine } from "./sdk/document-sdk.js";

// The two profiles carry different `diagnostic.scope` values, so neither the
// E1 nor the E2 typed client accepts both.  Rather than widen a validated
// client's gate for a diagnostic run, this harness issues the same closed
// requests directly -- the pattern FormatDiscoveryClient.nudgeCaret already
// uses.  The action list stays closed here: JS names an action, never a key
// code and never a UNO command.
const LINE_ACTIONS = Object.freeze([
  "move-line-up", "move-line-down", "move-line-home", "move-line-end",
]);

function lineAction(handle, action, options = {}, extendSelection = false) {
  if (!LINE_ACTIONS.includes(action))
    throw new Error(`not a closed line action: ${action}`);
  return handle._engine._request("editorDiscoveryAction", {
    documentHandle: handle.handle,
    expectedRevision: handle.revision,
    action,
    extendSelection,
    option: false,
  }, options);
}

function resetCaret(handle, x, y, options = {}) {
  return handle._engine._request("editorDiscoverySelect", {
    documentHandle: handle.handle,
    method: "selection-reset-unstable",
    startXTwips: x, startYTwips: y, endXTwips: x, endYTwips: y,
  }, options);
}

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-discovery";
const rounds = Number.parseInt(params.get("rounds") || "6", 10);
const actionTimeoutMs = Number.parseInt(params.get("timeoutMs") || "30000", 10);
// `extend=1` runs the same sequence with Shift held, which gives the move an
// observable postcondition (the selected text) instead of only a callback.
const extend = params.get("extend") === "1";

if (!/^[a-z0-9-]+$/.test(profile))
  throw new Error("invalid profile id");

const metrics = {
  schemaVersion: 1,
  release: "finding-018-line-nav-attribution",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  profile,
  rounds,
  actionTimeoutMs,
  extendSelection: extend,
  manifest: null,
  results: [],
  summary: null,
  complete: false,
  error: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__f018 = metrics;

const logElement = document.querySelector("#log");
function log(value) {
  logElement.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
  logElement.scrollTop = logElement.scrollHeight;
}

function publicError(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: error?.message || String(error),
  };
}

function firstRectangle(search) {
  const value = search.selections?.[0]?.rectangles || "";
  const numbers = value.split(";")[0].split(",")
    .map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item)))
    throw new Error("search did not return a usable rectangle");
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

/** One round: fresh engine, caret at the anchor, then Home/End x3 alternating. */
async function runRound(index) {
  const round = { round: index, actions: [], engineError: null };
  let engine = null;
  let handle = null;
  const started = performance.now();
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      timeoutMs: 60000,
    });
    if (!metrics.manifest) {
      metrics.manifest = {
        profile: engine.manifest.profile,
        capabilities: engine.manifest.capabilities,
      };
    }
    const bytes = await fetch("./e1-fixtures/multi-paragraph.odt", { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    handle = await engine.open(bytes.slice(0), {
      name: "multi-paragraph.odt", timeoutMs: 180000,
    });
    const search = await handle.search("第二段中文 beta", { timeoutMs: 30000 });
    if (!search.found)
      throw new Error("anchor 第二段中文 beta not found");
    const rectangle = firstRectangle(search);
    const x = rectangle.x + Math.max(1, rectangle.width - 1);
    const y = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
    await resetCaret(handle, x, y, { timeoutMs: 30000 });

    // Finding 018's alternation: Home, End, Home, End, Home, End.
    const sequence = ["move-line-home", "move-line-end",
      "move-line-home", "move-line-end",
      "move-line-home", "move-line-end"];
    for (let step = 0; step < sequence.length; step += 1) {
      const name = sequence[step];
      const at = performance.now();
      const entry = { step: step + 1, action: name };
      try {
        const result = await lineAction(
          handle, name, { timeoutMs: actionTimeoutMs }, extend,
        );
        entry.status = "completed";
        entry.completion = result.completion ?? null;
        entry.changed = result.changed ?? null;
        if (extend) {
          // Postcondition, not the callback under test: if the caret really
          // travelled, a shift-Home from the anchor end selects that line's
          // text and a shift-End collapses it again.  A completion credited to
          // an unrelated callback would leave the selection unchanged.
          const selection = await handle.getSelection({ timeoutMs: 30000 });
          entry.selectionType = selection.selectionType ?? null;
          entry.selectedLength = (selection.text || "").length;
        }
      } catch (error) {
        entry.status = error?.code === "TIMEOUT" ? "timeout"
          : error?.code === "BUSY" ? "busy" : "error";
        entry.error = publicError(error);
      }
      entry.elapsedMs = Math.round(performance.now() - at);
      round.actions.push(entry);
      log(`  round ${index} step ${entry.step} ${name} -> ${entry.status} (${entry.elapsedMs} ms)`);
      // Once the pending slot is stuck every later action is BUSY; the round is
      // already conclusive, so stop instead of burning the remaining timeouts.
      if (entry.status !== "completed" && entry.status !== "busy")
        break;
    }
  } catch (error) {
    round.engineError = publicError(error);
    log(`  round ${index} engine error: ${round.engineError.message}`);
  } finally {
    round.elapsedMs = Math.round(performance.now() - started);
    try {
      if (handle) await handle.close({ timeoutMs: 30000 });
    } catch {
      // Bounded teardown: a stuck worker must not mask the round's result.
    }
    engine?.dispose();
  }
  return round;
}

async function runAll() {
  if (metrics.complete)
    return metrics;
  try {
    log(`profile=${profile} rounds=${rounds} timeoutMs=${actionTimeoutMs}`);
    for (let index = 1; index <= rounds; index += 1)
      metrics.results.push(await runRound(index));

    const actions = metrics.results.flatMap((round) => round.actions);
    const count = (status) => actions.filter((entry) => entry.status === status).length;
    metrics.summary = {
      rounds: metrics.results.length,
      roundsFullyCompleted: metrics.results.filter((round) =>
        round.actions.length === 6
        && round.actions.every((entry) => entry.status === "completed")).length,
      actions: actions.length,
      completed: count("completed"),
      timeout: count("timeout"),
      busy: count("busy"),
      error: count("error"),
      engineErrors: metrics.results.filter((round) => round.engineError).length,
      medianCompletedMs: (() => {
        const values = actions.filter((entry) => entry.status === "completed")
          .map((entry) => entry.elapsedMs).sort((a, b) => a - b);
        return values.length ? values[Math.floor(values.length / 2)] : null;
      })(),
    };
    log(JSON.stringify(metrics.summary));
  } catch (error) {
    metrics.error = publicError(error);
  } finally {
    metrics.complete = true;
  }
  return metrics;
}

globalThis.__f018_run = runAll;
if (params.get("autorun") === "1")
  void runAll();
