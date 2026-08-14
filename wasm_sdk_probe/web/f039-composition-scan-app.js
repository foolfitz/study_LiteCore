// Task #47, P2: does finding 039's arm 8 survive in the combination E2-B ships?
//
// Arm 8 is the cell the E2-B entry condition is actually about: after ONE
// format action, even a range selection times out, because the barrier's
// teardown restores the selection away and leaves nothing for core to
// broadcast.  Measured on the discovery engine, which by documented design
// does not arm the bounded readback (probe_engine.hpp:69-72).
//
// The combination artifact exports BOTH select paths, so this page runs arm 8
// twice on the same document, the same format action, the same coordinates,
// and differs in exactly one thing: which entry point issues the select.
//
//   arm8-discovery   editorDiscoverySelect   -> expected to STILL time out
//   arm8-product     editorSelectRangeV1     -> expected to complete correctly
//
// That makes the control intrinsic.  A pass on the product path only means
// something if the discovery path, on the same artifact and the same run, still
// fails -- otherwise "it passes now" could be anything about the new build.
// The cross-artifact control (this tool reproducing arm 8 on the archived
// c89f069e) is run separately, by pointing --profile at it.
//
// Coordinates are copied from f039-caret-reset-repro-app.js arm 8 verbatim
// (1500,2000->3000,2000 then 1500,2600->3000,2600) and there is deliberately NO
// search between the format action and the second select: a search leaves a
// selection to clear, which is the search-prime recipe that keeps the sweeps
// alive and would mask exactly what this measures.
//
// Judged by the reported selection, never by the fact that a call returned --
// probe_engine.cpp:1556-1559 says so about the bounded completion itself.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { FormatDiscoveryClient } from "./e2/format-discovery-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-combination";
const fixture = params.get("fixture") || "list-contexts.odt";
const stepTimeoutMs = Number.parseInt(params.get("stepTimeoutMs") || "10000", 10);
const rounds = Number.parseInt(params.get("rounds") || "3", 10);

const metrics = {
  schemaVersion: 1,
  release: "task-047-P2-composition-scan",
  prediction: "findings/evidence/sdk-e2/discovery/039-combination/PREDICTION.md",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  profile,
  fixture,
  stepTimeoutMs,
  rounds,
  productAbiAvailable: null,
  arms: [],
  judgement: null,
  complete: false,
  error: null,
};
globalThis.__probe_metrics = metrics;
globalThis.__f039_composition = metrics;

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

const discoveryRangeSelect = (handle, x1, y1, x2, y2) =>
  handle._engine._request("editorDiscoverySelect", {
    documentHandle: handle.handle,
    method: "text-handles-unstable",
    startXTwips: x1, startYTwips: y1, endXTwips: x2, endYTwips: y2,
  }, { timeoutMs: stepTimeoutMs });

const productRangeSelect = (handle, x1, y1, x2, y2) =>
  handle._engine._request("editorSelectRangeV1", {
    documentHandle: handle.handle,
    startXTwips: x1, startYTwips: y1, endXTwips: x2, endYTwips: y2,
  }, { timeoutMs: stepTimeoutMs });

async function readSelection(handle) {
  try {
    const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
    return {
      selectionType: selection.selectionType ?? null,
      text: selection.text ?? "",
      length: (selection.text || "").length,
    };
  } catch (error) {
    return { readFailed: publicError(error) };
  }
}

/** Fresh engine per arm: a wedged pending slot must not decide the next arm. */
async function runArm(name, expects, body) {
  const entry = { arm: name, expects, steps: [] };
  let engine = null;
  let handle = null;
  const started = performance.now();
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    metrics.productAbiAvailable =
      Boolean(engine.manifest?.capabilities?.includes("narrow-editor-v1"));
    const bytes = await fetch(`./e1-fixtures/${fixture}`, { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    handle = await engine.open(bytes.slice(0), {
      name: fixture, timeoutMs: 180000,
    });
    const client = new FormatDiscoveryClient(handle);
    const step = async (label, run) => {
      const at = performance.now();
      const record = { step: label };
      try {
        record.value = await run();
        record.status = "completed";
        record.completion = record.value?.completion ?? null;
      } catch (error) {
        const failure = publicError(error);
        record.status = failure.code === "TIMEOUT" ? "timeout"
          : failure.code === "BUSY" ? "busy"
          : failure.code === "UNSUPPORTED_OPERATION"
            || failure.code === "EDITOR_ACTION_UNSUPPORTED" ? "unsupported"
          : "error";
        record.error = failure;
      }
      record.elapsedMs = Math.round(performance.now() - at);
      entry.steps.push(record);
      return record;
    };
    await body(handle, client, step, entry);
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

function status(entry, label) {
  return entry.steps.find((s) => s.step === label)?.status ?? null;
}

async function runAll() {
  if (metrics.complete)
    return metrics;
  try {
    log(`profile=${profile} fixture=${fixture} stepTimeoutMs=${stepTimeoutMs}`);

    // 1. Arm 8 through the DISCOVERY entry point.  On c89f069e this is the
    //    control that must fail; on the combination it must ALSO still fail,
    //    because the ruling keeps that path unbuffered on purpose.
    await runArm("arm8-discovery",
      "range-2 times out: the discovery select is unbuffered by design",
      async (handle, client, step) => {
        await step("range-1", () => discoveryRangeSelect(handle, 1500, 2000, 3000, 2000));
        await step("set-list-unordered",
          () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
        await step("range-2", () => discoveryRangeSelect(handle, 1500, 2600, 3000, 2600));
      });

    // 2. The same thing through the PRODUCT entry point.
    await runArm("arm8-product",
      "range-2 completes and the reported selection is not empty",
      async (handle, client, step, entry) => {
        if (!metrics.productAbiAvailable) {
          entry.skipped = "narrow-editor-v1 is not exported by this profile";
          return;
        }
        await step("range-1", () => productRangeSelect(handle, 1500, 2000, 3000, 2000));
        entry.selectionAfterRange1 = await readSelection(handle);
        await step("set-list-unordered",
          () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
        await step("range-2", () => productRangeSelect(handle, 1500, 2600, 3000, 2600));
        entry.selectionAfterRange2 = await readSelection(handle);
      });

    // 2b. The control arm 2 needs and did not have.  "range-2 selected nothing"
    //     only implicates the format action if the SAME select at the SAME
    //     coordinates selects something when no format action precedes it.
    //     Without this, an empty line at y=2600 would produce an identical
    //     reading and I would have blamed the barrier for the fixture.
    await runArm("select-y2600-without-format",
      "the same select, no format action first: does it select anything at all?",
      async (handle, client, step, entry) => {
        if (!metrics.productAbiAvailable) {
          entry.skipped = "narrow-editor-v1 is not exported by this profile";
          return;
        }
        await step("range-2-only", () => productRangeSelect(handle, 1500, 2600, 3000, 2600));
        entry.selectionAfter = await readSelection(handle);
      });

    // 3. Repeated composition, and a trivial op after each round to prove the
    //    pending slot actually cleared rather than merely not being asked.
    await runArm("repeat-composition",
      `${rounds} rounds of format -> select, each followed by a state read`,
      async (handle, client, step, entry) => {
        if (!metrics.productAbiAvailable) {
          entry.skipped = "narrow-editor-v1 is not exported by this profile";
          return;
        }
        for (let round = 1; round <= rounds; round += 1) {
          const y = 2000 + round * 200;
          await step(`action-${round}`,
            () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
          await step(`select-${round}`,
            () => productRangeSelect(handle, 1500, y, 3000, y));
          await step(`state-${round}`,
            () => client.getState({ timeoutMs: stepTimeoutMs }));
        }
      });

    // 4. The v2 primary gesture, which has never been measured with the barrier
    //    compiled in: place by click + poll, then dispatch.
    await runArm("click-gesture",
      `${rounds} rounds of format -> click+poll -> format`,
      async (handle, client, step, entry) => {
        for (let round = 1; round <= rounds; round += 1) {
          const y = 2000 + round * 200;
          await step(`action-a-${round}`,
            () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
          await step(`click-${round}`, async () => {
            await handle.click(1500, y, { timeoutMs: stepTimeoutMs });
            // click is fire-and-forget: the caret arrives by callback a few
            // hundred ms later.  Reading immediately is the mistake finding 039
            // arm 10 was retracted for, so poll.
            const deadline = performance.now() + 3000;
            let state = null;
            while (performance.now() < deadline) {
              state = await client.getState({ timeoutMs: stepTimeoutMs });
              if (state?.caret?.available)
                break;
              await new Promise((resolve) => setTimeout(resolve, 50));
            }
            return state;
          });
          await step(`action-b-${round}`,
            () => client.action("set-list-unordered", { timeoutMs: stepTimeoutMs }));
        }
      });

    // 5. The discriminator made observable: an engineered no-change select must
    //    take the readback path, a changing one must take the callback path.
    await runArm("label-partition",
      "no-change select completes by readback, changing select by callback",
      async (handle, client, step, entry) => {
        if (!metrics.productAbiAvailable) {
          entry.skipped = "narrow-editor-v1 is not exported by this profile";
          return;
        }
        await step("changing", () => productRangeSelect(handle, 1500, 2000, 3000, 2000));
        await step("same-again", () => productRangeSelect(handle, 1500, 2000, 3000, 2000));
        entry.selectionAfter = await readSelection(handle);
      });

    const discoveryArm = metrics.arms.find((a) => a.arm === "arm8-discovery");
    const productArm = metrics.arms.find((a) => a.arm === "arm8-product");
    const repeatArm = metrics.arms.find((a) => a.arm === "repeat-composition");
    const clickArm = metrics.arms.find((a) => a.arm === "click-gesture");
    const labelArm = metrics.arms.find((a) => a.arm === "label-partition");

    const controlArm = metrics.arms.find((a) => a.arm === "select-y2600-without-format");
    const productSelection = productArm?.selectionAfterRange2 || {};
    const controlSelection = controlArm?.selectionAfter || {};
    metrics.judgement = {
      // The control: arm 8 must still reproduce through the unbuffered path.
      arm8ReproducesOnDiscoveryPath: status(discoveryArm, "range-2") === "timeout",
      arm8ProductCompletes: status(productArm, "range-2") === "completed",
      // Not "it returned": what did it say was selected?
      arm8ProductSelectionNonEmpty: (productSelection.length || 0) > 0,
      arm8ProductSelectionType: productSelection.selectionType ?? null,
      // Without this, "selected nothing" cannot be attributed to the format
      // action at all.
      sameSelectWithoutFormatSelectsText: (controlSelection.length || 0) > 0,
      sameSelectWithoutFormatText: controlSelection.text ?? null,
      repeatAllCompleted: Boolean(repeatArm && !repeatArm.skipped
        && repeatArm.steps.length > 0
        && repeatArm.steps.every((s) => s.status === "completed")),
      clickAllCompleted: Boolean(clickArm && clickArm.steps.length > 0
        && clickArm.steps.every((s) => s.status === "completed")),
      labelPartition: {
        changing: labelArm?.steps.find((s) => s.step === "changing")?.completion ?? null,
        sameAgain: labelArm?.steps.find((s) => s.step === "same-again")?.completion ?? null,
      },
      harnessTimeoutsOutsideControl: metrics.arms
        .filter((a) => a.arm !== "arm8-discovery")
        .flatMap((a) => a.steps)
        .filter((s) => s.status === "timeout").length,
    };
    log(metrics.judgement);
  } catch (error) {
    metrics.error = publicError(error);
    log(`fatal: ${metrics.error.message}`);
  } finally {
    metrics.complete = true;
  }
  return metrics;
}

globalThis.__f039_composition_run = runAll;
if (params.get("autorun") === "1")
  runAll();
