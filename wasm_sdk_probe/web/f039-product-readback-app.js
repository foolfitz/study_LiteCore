// P1 (task #47): does the shipped bounded-readback completion actually fire?
//
// The whole of option C rests on one claim: the mechanism finding 039 needs is
// already implemented and already shipped, and only the discovery entry point
// declines to arm it.  editor_api.cpp:123 passes boundedReadback=true;
// editor_discovery_api.cpp:58 omits it; probe_engine.hpp:69-72 says the
// omission is deliberate.  That is all source reading.  This page is the
// measurement, and it runs on the FROZEN e1-editor-v1 -- nothing is rebuilt.
//
// The load-bearing arm is `identical-range-twice`.  The second request asks for
// a range that is already selected, so core has nothing to broadcast: exactly
// finding 039's condition, on the product path.  If the deadline fires we
// should see `verified-selection-readback` at roughly 250 ms
// (EditorSelectReadbackDeadlineMs).  If it completes by callback instead, core
// re-broadcasts unchanged selections and finding 039's model is wrong.  If it
// times out, the shipped mechanism does not work and option C's premise fails.
//
// Judged from the reported selection, never from the fact that the call
// returned -- probe_engine.cpp:1556-1559 says so about this very completion.
//
// Fresh engine per arm: a wedged pending slot must not decide the next arm's
// answer (finding 038's lesson).

import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-v1";
const timeoutMs = Number.parseInt(params.get("timeoutMs") || "15000", 10);
const fixture = params.get("fixture") || "plain-grapheme.odt";
const anchorText = params.get("anchor") || "ASCII abc XYZ 0123456789";

// The deadline the engine arms for a product range select, in ms.  Kept here
// only to classify "about the deadline" in the readout; the completion NAME is
// what decides the outcome, never the timing.
const ARMED_DEADLINE_MS = 250;

const metrics = {
  schemaVersion: 1,
  release: "task-047-P1-product-readback",
  prediction: "findings/evidence/sdk-e2/discovery/039-combination/PREDICTION.md",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  profile,
  fixture,
  timeoutMs,
  arms: [],
  outcome: null,
  complete: false,
  error: null,
};
// Two names on purpose.  ChromeSession.navigate() waits for
// `globalThis.__probe_metrics` to exist before it considers the page loaded
// (tools/run_browser_probe.py:281), so a page that only publishes its own name
// never finishes navigating -- which is how the first run of this page failed.
globalThis.__probe_metrics = metrics;
globalThis.__f039_product = metrics;

const logElement = document.querySelector("#log");
const log = (value) => {
  logElement.textContent +=
    `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
};

function publicError(error) {
  return {
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: error?.message || String(error),
  };
}

function firstRectangle(search) {
  const numbers = (search.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item)))
    throw new Error("search did not return a usable rectangle");
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

// The PRODUCT entry point.  Not editorDiscoverySelect -- the whole point is
// which of the two arms the readback deadline, so calling the other one would
// measure the wrong thing.
async function selectRangeV1(handle, start, end) {
  const started = performance.now();
  try {
    const result = await handle._engine._request("editorSelectRangeV1", {
      documentHandle: handle.handle,
      startXTwips: start.x, startYTwips: start.y,
      endXTwips: end.x, endYTwips: end.y,
    }, { timeoutMs });
    return {
      status: "completed",
      completion: result.completion ?? null,
      elapsedMs: Math.round(performance.now() - started),
      revision: result.revision ?? null,
    };
  } catch (error) {
    return {
      status: error?.code === "TIMEOUT" ? "timeout"
        : error?.code === "BUSY" ? "busy" : "error",
      error: publicError(error),
      elapsedMs: Math.round(performance.now() - started),
    };
  }
}

async function readSelection(handle) {
  try {
    const selection = await handle.getSelection({ timeoutMs: 10000 });
    return {
      selectionType: selection.selectionType ?? null,
      text: selection.text ?? "",
      length: (selection.text || "").length,
    };
  } catch (error) {
    return { readFailed: publicError(error) };
  }
}

async function runArm(name, body) {
  const entry = { arm: name, steps: [] };
  let engine = null;
  let handle = null;
  const started = performance.now();
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    const bytes = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    handle = await engine.open(bytes.slice(0), {
      name: fixture, timeoutMs: 180000,
    });
    const anchor = await handle.search(anchorText, { timeoutMs: 30000 });
    if (!anchor.found)
      throw new Error(`anchor not found: ${anchorText}`);
    await body(handle, firstRectangle(anchor), entry);
  } catch (error) {
    entry.fatal = publicError(error);
  } finally {
    entry.elapsedMs = Math.round(performance.now() - started);
    try {
      if (handle) await handle.close({ timeoutMs: 15000 });
    } catch {
      entry.closeFailed = true;
    }
    engine?.dispose();
  }
  log(entry);
  metrics.arms.push(entry);
  return entry;
}

async function step(entry, name, run) {
  const outcome = await run();
  entry.steps.push({ step: name, ...outcome });
  return outcome;
}

function classify() {
  const twice = metrics.arms.find((arm) => arm.arm === "identical-range-twice");
  if (!twice || twice.fatal)
    return { code: "D", label: "nothing measured", detail: "arm did not run" };
  const first = twice.steps.find((s) => s.step === "select-R");
  const second = twice.steps.find((s) => s.step === "select-R-again");
  if (!first || first.status !== "completed")
    return { code: "D", label: "nothing measured",
      detail: "the first select did not complete, so the second says nothing" };
  if (!second)
    return { code: "D", label: "nothing measured", detail: "second select missing" };
  if (second.status === "timeout" || second.status === "busy")
    return { code: "C", label: "the shipped mechanism did not complete it",
      detail: `second select ${second.status}` };
  if (second.status !== "completed")
    return { code: "D", label: "nothing measured", detail: second.status };
  if (second.completion === "verified-selection-readback")
    return { code: "A", label: "readback deadline fired",
      detail: `${second.elapsedMs} ms (armed deadline ${ARMED_DEADLINE_MS} ms)` };
  if (String(second.completion || "").startsWith("documented-callback-"))
    return { code: "B", label: "core broadcast anyway",
      detail: `completion ${second.completion}` };
  return { code: "D", label: "nothing measured",
    detail: `unrecognised completion ${second.completion}` };
}

async function runAll() {
  if (metrics.complete)
    return metrics;
  try {
    log(`profile=${profile} fixture=${fixture} timeoutMs=${timeoutMs}`);

    // Arm 1 mirrors what finding 039's <影響> section claims but never landed:
    // five product range selects in a row.  Recording `completion` is the
    // whole point -- the original numbers do not have it.
    await runArm("five-selects", async (handle, line, entry) => {
      const y = line.y + Math.floor(line.height / 2);
      const spans = [0.25, 0.5, 0.75, 0.4, 0.9];
      for (let index = 0; index < spans.length; index += 1) {
        const width = Math.max(1, Math.floor(line.width * spans[index]));
        await step(entry, `select-${index + 1}`, () => selectRangeV1(handle,
          { x: line.x, y }, { x: line.x + width, y }));
      }
      entry.selectionAfter = await readSelection(handle);
    });

    // Arm 2 is the load-bearing one: ask for a range that is already selected.
    await runArm("identical-range-twice", async (handle, line, entry) => {
      const y = line.y + Math.floor(line.height / 2);
      const end = { x: line.x + Math.floor(line.width / 2), y };
      await step(entry, "select-R", () => selectRangeV1(handle, { x: line.x, y }, end));
      entry.selectionAfterFirst = await readSelection(handle);
      await step(entry, "select-R-again", () => selectRangeV1(handle, { x: line.x, y }, end));
      entry.selectionAfterSecond = await readSelection(handle);
      // Did the pending slot survive?  A wedge here would answer C even if the
      // call itself reported completion.
      entry.stillUsable = await readSelection(handle);
    });

    // Arm 3 is the contrast that makes arm 2 legible: a select that DOES change
    // the selection should complete by callback.  Without it, "readback fired"
    // could just mean "this build labels everything that way".
    await runArm("changing-range", async (handle, line, entry) => {
      const y = line.y + Math.floor(line.height / 2);
      await step(entry, "select-half", () => selectRangeV1(handle,
        { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y }));
      await step(entry, "select-full", () => selectRangeV1(handle,
        { x: line.x, y }, { x: line.x + line.width, y }));
      entry.selectionAfter = await readSelection(handle);
    });

    metrics.outcome = classify();
    log(`P1 outcome = ${metrics.outcome.code}: ${metrics.outcome.label} (${metrics.outcome.detail})`);
  } catch (error) {
    metrics.error = publicError(error);
    log(`fatal: ${metrics.error.message}`);
  } finally {
    metrics.complete = true;
  }
  return metrics;
}

globalThis.__f039_product_run = runAll;
if (params.get("autorun") === "1")
  runAll();
