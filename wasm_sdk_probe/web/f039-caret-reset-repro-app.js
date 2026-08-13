// Finding 039 reproduction: a caret reset with nothing to clear never returns.
//
// `selection-reset-unstable` (LOK_SETTEXTSELECTION_RESET) is how the E2
// discovery ABI places a caret.  It completes on the first call after a
// document is opened and hangs on every later one, taking the handle with it:
// the request never resolves, `gEditorPending` stays set, and every subsequent
// editor operation is refused BUSY.
//
// Anything that leaves a non-empty selection first -- a search, a range
// selection -- makes the next reset complete again.  That is the tell: the
// reset waits for a selection-change callback, and when the selection is
// already empty core has nothing to broadcast.  It is the same shape as
// SPEC E2-A 2.7 (二) for format state ("no change, no STATE_CHANGED, nothing to
// wait for"), on the selection path instead.
//
// Why 400+ sweep runs never met it: every one of them places the caret with
// caretAtAnchor, which searches for the anchor text first, and a search leaves
// a selection for the reset to clear.
//
// Each arm gets its own engine.  A hung reset wedges the handle, so sharing one
// would let arm N-1's damage decide arm N's answer -- the mistake finding 038
// was written after.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { FormatDiscoveryClient } from "./e2/format-discovery-client.js";

const output = document.querySelector("#out");
const status = document.querySelector("#status");
const params = new URLSearchParams(globalThis.location.search);
const fixture = params.get("fixture") || "list-contexts.odt";
const stepTimeoutMs = Number(params.get("timeoutMs") || 8000);

function log(value) {
  output.textContent = JSON.stringify(value, null, 2);
}

async function withEngine(plan) {
  const engine = await createDocumentEngine({
    workerUrl: "./profiles/e2-format-discovery/sdk-worker.js",
    timeoutMs: stepTimeoutMs,
  });
  const bytes = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" })
    .then((response) => response.arrayBuffer());
  const handle = await engine.open(bytes, { name: fixture, transfer: true,
                                            timeoutMs: 180000 });
  try {
    return await plan(handle, new FormatDiscoveryClient(handle), engine);
  } finally {
    engine.dispose?.();
  }
}

function stepper(steps) {
  return async (name, operation) => {
    const started = performance.now();
    try {
      await operation();
      steps.push({ step: name, outcome: "ok",
                   ms: Math.round(performance.now() - started) });
    } catch (error) {
      steps.push({ step: name, outcome: error?.code || "ERROR",
                   ms: Math.round(performance.now() - started),
                   message: String(error?.message || error).slice(0, 160) });
    }
  };
}

const rangeSelect = (handle, x1, y1, x2, y2) =>
  handle._engine._request("editorDiscoverySelect", {
    documentHandle: handle.handle,
    method: "text-handles-unstable",
    startXTwips: x1, startYTwips: y1, endXTwips: x2, endYTwips: y2,
  }, { timeoutMs: stepTimeoutMs });

// Written so the arms disagree with each other.  If every arm timed out the
// result would say "this engine cannot place a caret"; if none did it would say
// nothing at all.  The claim is that the difference tracks whether a selection
// existed to be cleared, so the arms differ in exactly that.
const ARMS = [
  {
    name: "two resets, different points",
    expects: "the second times out",
    async plan(handle, client, step) {
      await step("reset-A", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
      await step("reset-B", () => client.placeCaret(2000, 2600, { timeoutMs: stepTimeoutMs }));
    },
  },
  {
    name: "two resets, the same point",
    expects: "the second times out; the point is not what matters",
    async plan(handle, client, step) {
      await step("reset-A", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
      await step("reset-A-again", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
    },
  },
  {
    name: "a state read between the resets",
    expects: "the second still times out; reading changes nothing",
    async plan(handle, client, step) {
      await step("reset-A", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
      await step("getState", () => client.getState({ timeoutMs: stepTimeoutMs }));
      await step("reset-B", () => client.placeCaret(2000, 2600, { timeoutMs: stepTimeoutMs }));
    },
  },
  {
    name: "a search between the resets",
    expects: "the second completes: a search leaves a selection to clear",
    async plan(handle, client, step) {
      await step("reset-A", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
      await step("search", () => handle.search("E1-LC-END", { timeoutMs: stepTimeoutMs }));
      await step("reset-B", () => client.placeCaret(2000, 2600, { timeoutMs: stepTimeoutMs }));
    },
  },
  {
    name: "a range selection between the resets",
    expects: "the second completes, with no search involved",
    async plan(handle, client, step) {
      await step("reset-A", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
      await step("range", () => rangeSelect(handle, 1500, 2600, 3000, 2600));
      await step("reset-B", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
    },
  },
  {
    name: "range selections only, never a reset",
    expects: "all three complete: the range path does not have this problem",
    async plan(handle, client, step) {
      await step("range-1", () => rangeSelect(handle, 1500, 2000, 3000, 2000));
      await step("range-2", () => rangeSelect(handle, 1500, 2600, 3000, 2600));
      await step("range-3", () => rangeSelect(handle, 1500, 3200, 3000, 3200));
    },
  },
  {
    name: "a format action between the resets",
    expects: "the second still times out; a mutation is not a selection",
    async plan(handle, client, step) {
      await step("reset-A", () => client.placeCaret(2000, 2000, { timeoutMs: stepTimeoutMs }));
      await step("set-list-unordered",
                 () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
      await step("reset-B", () => client.placeCaret(2000, 2600, { timeoutMs: stepTimeoutMs }));
    },
  },
  {
    // The range path is not immune after all -- it only looked immune while no
    // format action had run.  This is the arm that decides whether "use ranges
    // instead" is a fix or a coincidence.
    name: "a range selection after a format action",
    expects: "it times out too: the barrier, not the method, is what blocks it",
    async plan(handle, client, step) {
      await step("range-1", () => rangeSelect(handle, 1500, 2000, 3000, 2000));
      await step("set-list-unordered",
                 () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
      await step("range-2", () => rangeSelect(handle, 1500, 2600, 3000, 2600));
    },
  },
  {
    // What the sweeps do, 375 times, without ever meeting any of the above.
    name: "search then reset, three rounds with an action each",
    expects: "every step completes: a search always leaves a selection to clear",
    async plan(handle, client, step) {
      for (const round of [1, 2, 3]) {
        await step(`search-${round}`,
                   () => handle.search("E1-LC-END", { timeoutMs: stepTimeoutMs }));
        await step(`reset-${round}`,
                   () => client.placeCaret(2000, 1600 + round * 600,
                                           { timeoutMs: stepTimeoutMs }));
        await step(`action-${round}`,
                   () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
      }
    },
  },
  {
    // The Document SDK click is how the product shell places its caret, and it
    // WORKS -- but only if you wait for it.  The first version of this arm read
    // the state once, immediately, saw the caret unmoved five times running and
    // recorded "reports success and does nothing".  That was the probe, not the
    // engine: the click is fire-and-forget and the caret arrives by callback a
    // few hundred milliseconds later.  EditorSession.placeCaret has always
    // polled for exactly this reason.
    //
    // Kept as an arm because the withdrawn claim is worth being unable to make
    // again: this one records both the immediate read and the settled one.
    name: "the SDK click, read immediately and then polled",
    expects: "the immediate read is stale; the polled caret tracks the click",
    async plan(handle, client, step, steps) {
      for (const [index, y] of [1600, 2800, 3600].entries()) {
        await step(`click-${index}`, () => handle.click(1800, y, { timeoutMs: stepTimeoutMs }));
        const immediate = await client.getState({ timeoutMs: stepTimeoutMs });
        const started = performance.now();
        let settled = null, previous = null, stable = 0;
        while (performance.now() - started < 3000) {
          const state = await client.getState({ timeoutMs: stepTimeoutMs });
          const here = `${state?.caret?.x},${state?.caret?.y}`;
          stable = here === previous ? stable + 1 : 0;
          previous = here;
          if (stable >= 3) { settled = here; break; }
          await new Promise((resolve) => setTimeout(resolve, 60));
        }
        steps.push({ step: `caret-after-click-${index}`, outcome: "read",
                     clickedY: y,
                     immediate: `${immediate?.caret?.x},${immediate?.caret?.y}`,
                     settled: settled ?? previous,
                     settledAfterMs: Math.round(performance.now() - started) });
      }
    },
  },
  {
    // What the demo actually needs, and what the withdrawn arm 10 wrongly ruled
    // out: place the caret by clicking, then dispatch.  Four paragraphs, four
    // actions, no reset and no search anywhere.
    name: "click-place then dispatch, four times",
    expects: "every step completes; this is a usable gesture after all",
    async plan(handle, client, step) {
      for (const [index, y] of [1600, 2400, 3000, 3600].entries()) {
        await step(`click-place-${index}`, async () => {
          await handle.click(1800, y, { timeoutMs: stepTimeoutMs });
          const started = performance.now();
          let previous = null, stable = 0;
          while (performance.now() - started < 3000) {
            const state = await client.getState({ timeoutMs: stepTimeoutMs });
            const here = `${state?.caret?.x},${state?.caret?.y}`;
            stable = here === previous ? stable + 1 : 0;
            previous = here;
            if (stable >= 3) return;
            await new Promise((resolve) => setTimeout(resolve, 60));
          }
        });
        await step(`action-${index}`, () => client.action(
          index % 2 ? "set-paragraph-heading" : "set-list-unordered",
          { timeoutMs: stepTimeoutMs }));
      }
    },
  },
];

void (async () => {
  const report = {
    schemaVersion: 1,
    finding: "039-caret-reset-with-nothing-to-clear-never-returns",
    fixture,
    stepTimeoutMs,
    userAgent: navigator.userAgent,
    crossOriginIsolated: globalThis.crossOriginIsolated,
    arms: [],
  };
  for (const arm of ARMS) {
    status.textContent = `running: ${arm.name}`;
    const steps = [];
    try {
      await withEngine((handle, client) => {
        if (report.artifact === undefined) {
          report.artifact = handle._engine.manifest?.diagnostic?.wasmSha256 ?? null;
          report.profile = handle._engine.manifest?.profile ?? null;
        }
        return arm.plan(handle, client, stepper(steps), steps);
      });
    } catch (error) {
      steps.push({ step: "arm", outcome: "SETUP_FAILED",
                   message: String(error?.message || error) });
    }
    report.arms.push({ name: arm.name, expects: arm.expects, steps });
    log(report);
  }
  const timedOut = (name) => report.arms.find((arm) => arm.name === name)
    ?.steps.some((step) => step.outcome === "TIMEOUT");
  // The reproduction judges itself, so a run that quietly stopped reproducing
  // says so instead of leaving a reader to compare seven arms by eye.
  const clicks = report.arms
    .find((arm) => arm.name === "the SDK click, read immediately and then polled")
    ?.steps.filter((step) => step.outcome === "read") ?? [];
  report.clickMovedTheCaret = new Set(clicks.map((step) => step.settled)).size > 1;
  // The withdrawn claim, restated as the thing that must stay false: reading
  // once, immediately, is not a measurement of where the caret went.
  report.immediateReadIsStale = clicks.some((step) => step.immediate !== step.settled);
  report.reproduced = timedOut("two resets, different points")
    && timedOut("two resets, the same point")
    && timedOut("a state read between the resets")
    && timedOut("a format action between the resets")
    && timedOut("a range selection after a format action")
    && !timedOut("a search between the resets")
    && !timedOut("a range selection between the resets")
    && !timedOut("range selections only, never a reset")
    && !timedOut("search then reset, three rounds with an action each")
    && !timedOut("click-place then dispatch, four times")
    && report.clickMovedTheCaret === true
    && report.immediateReadIsStale === true;
  report.complete = true;
  status.textContent = report.reproduced
    ? "reproduced" : "NOT reproduced — read the arms";
  log(report);
  globalThis.__f039 = report;
})().catch((error) => {
  status.textContent = `failed: ${error?.message || error}`;
});
