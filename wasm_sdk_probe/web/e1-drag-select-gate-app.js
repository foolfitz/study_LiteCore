// First gate for adding range selection to the narrow editor contract.
//
// The engine already implements a `mouse-drag` selection method, but it is
// reachable only through `editorDiscoverySelect`, which is gated on
// `editor-discovery-closed-actions`.  Promoting it into `narrow-editor-v1`
// costs a rebuild of the frozen artifact plus a contract change, so this runs
// first, on the **already built** discovery profile, and answers the question
// that decides whether that cost is worth paying:
//
//   Does mouse-drag selection produce a correct, verifiable selection -- and
//   what does it do when the drag cannot select anything?
//
// The second half matters more than the first.  `handleEditorSelect` waits for
// LOK_CALLBACK_TEXT_SELECTION; findings 018 and 022 both turned on the same
// hazard -- an operation that legitimately has nothing to do emits no callback,
// so "nothing to select" is indistinguishable from "not finished yet" and
// leaves gEditorPending stuck, after which every later editor operation in that
// worker returns BUSY.  A contract that can wedge the editor when the user
// drags in the margin is not shippable, however well the happy path works.
//
// Postconditions are read back from the engine's selection, never inferred from
// the fact that the request resolved.

import { createDocumentEngine } from "./sdk/document-sdk.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-discovery";
const timeoutMs = Number.parseInt(params.get("timeoutMs") || "15000", 10);
// `only=handles-first` runs just the first-call repetition: that is the exact
// position where mouse-drag failed, and a single success there is not enough
// evidence to spend a rebuild on.
const only = params.get("only") || "";
const handleReps = Number.parseInt(params.get("handleReps") || "2", 10);

// Names only.  The worker owns the name-to-id mapping
// (`EDITOR_DISCOVERY_SELECTION_IDS`); duplicating the numbers here is exactly
// how a guessed constant disguises its own error as an engine bug.
const SELECT_METHODS = Object.freeze([
  "mouse-drag", "text-handles-unstable", "selection-reset-unstable",
]);

const metrics = {
  schemaVersion: 1,
  release: "e1-drag-select-gate",
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  profile,
  timeoutMs,
  cases: [],
  verdict: null,
  complete: false,
  error: null,
};
globalThis.__probe_metrics = metrics;

const logElement = document.querySelector("#log");
const log = (value) => {
  logElement.textContent +=
    `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
};

function publicError(error) {
  return { code: error?.code || "UNCLASSIFIED_ERROR", message: error?.message || String(error) };
}

function selectRange(handle, method, start, end, options = {}) {
  if (!SELECT_METHODS.includes(method))
    throw new Error(`unsupported closed selection method: ${method}`);
  return handle._engine._request("editorDiscoverySelect", {
    documentHandle: handle.handle,
    method,
    startXTwips: start.x, startYTwips: start.y,
    endXTwips: end.x, endYTwips: end.y,
  }, options);
}

function firstRectangle(search) {
  const numbers = (search.selections?.[0]?.rectangles || "")
    .split(";")[0].split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item)))
    throw new Error("search did not return a usable rectangle");
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

/** Fresh engine per case: a stuck pending slot must not leak into the next one. */
async function runCase(name, body) {
  const entry = { case: name };
  let engine = null;
  let handle = null;
  const started = performance.now();
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    const bytes = await fetch("./e1-fixtures/plain-grapheme.odt", { cache: "no-cache" })
      .then((response) => response.arrayBuffer());
    handle = await engine.open(bytes.slice(0), {
      name: "plain-grapheme.odt", timeoutMs: 180000,
    });
    const anchor = await handle.search("ASCII abc XYZ 0123456789", { timeoutMs: 30000 });
    if (!anchor.found)
      throw new Error("anchor line not found");
    Object.assign(entry, await body(handle, firstRectangle(anchor)));
  } catch (error) {
    entry.fatal = publicError(error);
  } finally {
    entry.elapsedMs = Math.round(performance.now() - started);
    try {
      if (handle) await handle.close({ timeoutMs: 15000 });
    } catch {
      // A wedged worker is itself a result; teardown failure must not hide it.
      entry.closeFailed = true;
    }
    engine?.dispose();
  }
  log(entry);
  metrics.cases.push(entry);
  return entry;
}

/** Does a later editor operation still work, or did the pending slot wedge? */
async function probeStillUsable(handle) {
  try {
    const state = await handle._engine._request("editorDiscoveryGetState",
      { documentHandle: handle.handle }, { timeoutMs: 10000 });
    const selection = await handle.getSelection({ timeoutMs: 10000 });
    return { usable: true, selectionType: selection.selectionType,
      selectionText: selection.text ?? "", sequence: state.sourceSequence };
  } catch (error) {
    return { usable: false, error: publicError(error) };
  }
}

async function attempt(handle, method, start, end) {
  try {
    const result = await selectRange(handle, method, start, end, { timeoutMs });
    return { status: "completed", completion: result.completion ?? null };
  } catch (error) {
    return {
      status: error?.code === "TIMEOUT" ? "timeout" : error?.code === "BUSY" ? "busy" : "error",
      error: publicError(error),
    };
  }
}

async function runAll() {
  if (metrics.complete)
    return metrics;
  try {
    log(`profile=${profile} timeoutMs=${timeoutMs} only=${only || "all"}`);

    // `only=contract-shape` closes the three SPEC E1-D section 5 gaps that
    // change how the contract must be written: does a range cross lines, does a
    // selection survive into the mutations that consume it, and is the result
    // judged from the saved file rather than from the call that made it.
    if (only === "contract-shape") {
      await runCase("range-across-lines", async (handle) => {
        const first = await handle.search("E1-PLAIN-START", { timeoutMs: 30000 });
        const third = await handle.search("臺灣中文游標測試", { timeoutMs: 30000 });
        if (!first.found || !third.found)
          throw new Error("cross-line anchors not found");
        const a = firstRectangle(first);
        const b = firstRectangle(third);
        const outcome = await attempt(handle, "text-handles-unstable",
          { x: a.x, y: a.y + Math.floor(a.height / 2) },
          { x: b.x + b.width, y: b.y + Math.floor(b.height / 2) });
        const selection = await handle.getSelection({ timeoutMs: 10000 });
        return { outcome, type: selection.selectionType,
          text: selection.text ?? "", length: (selection.text || "").length };
      });

      await runCase("range-then-delete", async (handle, line) => {
        const y = line.y + Math.floor(line.height / 2);
        const outcome = await attempt(handle, "text-handles-unstable",
          { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
        const before = await handle.getSelection({ timeoutMs: 10000 });
        const beforeRevision = handle.revision;
        let deleteOutcome;
        try {
          const result = await handle._engine._request("editorDiscoveryAction", {
            documentHandle: handle.handle, expectedRevision: handle.revision,
            action: "delete-backward", extendSelection: false, option: false,
          }, { timeoutMs });
          deleteOutcome = { status: "completed", completion: result.completion ?? null,
            revision: result.revision };
        } catch (error) {
          deleteOutcome = { status: "failed", error: publicError(error) };
        }
        const stillThere = before.text
          ? await handle.search(before.text, { timeoutMs: 30000 })
          : { found: null };
        return { outcome, selectedText: before.text ?? "", beforeRevision,
          deleteOutcome, selectedTextStillFound: stillThere.found };
      });

      await runCase("range-then-bold-saved", async (handle, line) => {
        const y = line.y + Math.floor(line.height / 2);
        const outcome = await attempt(handle, "text-handles-unstable",
          { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
        const selection = await handle.getSelection({ timeoutMs: 10000 });
        let boldOutcome;
        try {
          const result = await handle._engine._request("editorDiscoveryAction", {
            documentHandle: handle.handle, expectedRevision: handle.revision,
            action: "set-bold", extendSelection: false, option: true,
          }, { timeoutMs });
          boldOutcome = { status: "completed", completion: result.completion ?? null };
        } catch (error) {
          boldOutcome = { status: "failed", error: publicError(error) };
        }
        const bytes = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
        const view = new Uint8Array(bytes);
        let binary = "";
        for (let offset = 0; offset < view.length; offset += 0x8000)
          binary += String.fromCharCode(...view.subarray(offset, offset + 0x8000));
        return { outcome, selectedText: selection.text ?? "", boldOutcome,
          savedBase64: btoa(binary), savedBytes: view.length };
      });

      // The delete barrier refuses a range (it needs a collapsed caret it can
      // build its own verified one-character selection from).  Replacement is
      // the other way a selection is consumed, it is already a shipped
      // capability, and E1-C's manual round covers it -- so whether it accepts
      // a range decides how much of an editor the promotion actually buys.
      await runCase("range-then-replace-saved", async (handle, line) => {
        const y = line.y + Math.floor(line.height / 2);
        const outcome = await attempt(handle, "text-handles-unstable",
          { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
        const selection = await handle.getSelection({ timeoutMs: 10000 });
        let replaced;
        try {
          const result = await handle.replaceSelection("E1D-REPLACED",
            { timeoutMs: 60000 });
          replaced = { status: "completed", revision: result.revision };
        } catch (error) {
          replaced = { status: "failed", error: publicError(error) };
        }
        const found = await handle.search("E1D-REPLACED", { timeoutMs: 30000 });
        const bytes = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
        const view = new Uint8Array(bytes);
        let binary = "";
        for (let offset = 0; offset < view.length; offset += 0x8000)
          binary += String.fromCharCode(...view.subarray(offset, offset + 0x8000));
        return { outcome, selectedText: selection.text ?? "", replaced,
          replacementFound: found.found, savedBase64: btoa(binary) };
      });

      metrics.verdict = Object.fromEntries(metrics.cases.map((item) =>
        [item.case, item.fatal ? { fatal: item.fatal }
          : { ...item, savedBase64: undefined }]));
      log("contract-shape complete");
      metrics.complete = true;
      return metrics;
    }

    if (only === "handles-first") {
      for (let repetition = 1; repetition <= handleReps; repetition += 1) {
        await runCase(`handles-first-${repetition}`, async (handle, line) => {
          const y = line.y + Math.floor(line.height / 2);
          const outcome = await attempt(handle, "text-handles-unstable",
            { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
          const selection = await handle.getSelection({ timeoutMs: 10000 });
          return { outcome, firstReadType: selection.selectionType,
            firstReadText: selection.text ?? "" };
        });
      }
      const runs = metrics.cases.filter((item) => item.case.startsWith("handles-first"));
      metrics.verdict = {
        attempted: runs.length,
        harnessFatals: runs.filter((item) => item.fatal).length,
        firstReadCorrect: runs.filter((item) => item.firstReadType === "text"
          && (item.firstReadText || "").length > 0).length,
        texts: runs.map((item) => item.firstReadText ?? null),
      };
      log(metrics.verdict);
      metrics.complete = true;
      return metrics;
    }

    // 1. The happy path: drag across the middle of a text line.
    await runCase("drag-across-text", async (handle, line) => {
      const y = line.y + Math.floor(line.height / 2);
      const outcome = await attempt(handle,
        "mouse-drag", { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
      return { outcome, after: await probeStillUsable(handle) };
    });

    // 2. Repeat it three times in one worker: does the pending slot clear?
    await runCase("drag-repeated", async (handle, line) => {
      const y = line.y + Math.floor(line.height / 2);
      const outcomes = [];
      for (let index = 1; index <= 3; index += 1) {
        outcomes.push(await attempt(handle, "mouse-drag",
          { x: line.x, y }, { x: line.x + 200 * index, y }));
      }
      return { outcomes, after: await probeStillUsable(handle) };
    });

    // 3. Degenerate drag: start equals end.  Selects nothing by construction.
    await runCase("drag-zero-length", async (handle, line) => {
      const point = { x: line.x + 100, y: line.y + Math.floor(line.height / 2) };
      const outcome = await attempt(handle, "mouse-drag", point, point);
      return { outcome, after: await probeStillUsable(handle) };
    });

    // 4. Drag in empty space well below the last paragraph.
    await runCase("drag-empty-area", async (handle, line) => {
      const y = line.y + 6000;
      const outcome = await attempt(handle,
        "mouse-drag", { x: line.x, y }, { x: line.x + 1500, y });
      return { outcome, after: await probeStillUsable(handle) };
    });

    // 5. Can the editor recover after a wedging drag, in the same worker?
    await runCase("drag-after-degenerate", async (handle, line) => {
      const y = line.y + Math.floor(line.height / 2);
      const point = { x: line.x + 100, y };
      const first = await attempt(handle, "mouse-drag", point, point);
      const second = await attempt(handle, "mouse-drag",
        { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
      return { first, second, after: await probeStillUsable(handle) };
    });

    // 6. The one that decides the fix.  Cases 1-5 showed the request resolves
    //    on a TEXT_SELECTION callback that carries the *cleared* selection the
    //    mouse-down produced, with the real selection arriving afterwards.  If
    //    that lag is short and bounded, a verified-selection postcondition --
    //    poll the readback until it is non-empty, the shape finding 016 used
    //    for delete -- makes the operation safe to promote.  If the selection
    //    never materialises, promotion is off.
    await runCase("drag-then-poll", async (handle, line) => {
      const y = line.y + Math.floor(line.height / 2);
      const outcome = await attempt(handle,
        "mouse-drag", { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
      const polls = [];
      const started = performance.now();
      for (let index = 0; index < 40; index += 1) {
        const selection = await handle.getSelection({ timeoutMs: 10000 });
        polls.push({
          atMs: Math.round(performance.now() - started),
          type: selection.selectionType,
          text: selection.text ?? "",
        });
        if (selection.selectionType === "text" && (selection.text || "").length)
          break;
        await new Promise((resolve) => setTimeout(resolve, 25));
      }
      return { outcome, polls, settledAtMs: polls.at(-1)?.atMs ?? null,
        settledText: polls.at(-1)?.text ?? "" };
    });

    // 7. The other implementation of the same idea.  `text-handles-unstable`
    //    reaches the same selection through setTextSelection(RESET) +
    //    setTextSelection(END) instead of three synthesised mouse events.  If
    //    the API path produces a verifiable selection where the mouse path does
    //    not, promotion is still on -- with that method, not mouse-drag.
    //    (The name carries "unstable" from E1-A; this is the experiment that
    //    says whether that label still applies.)
    for (const repetition of [1, 2]) {
      await runCase(`handles-then-poll-${repetition}`, async (handle, line) => {
        const y = line.y + Math.floor(line.height / 2);
        const outcome = await attempt(handle, "text-handles-unstable",
          { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
        const polls = [];
        const started = performance.now();
        for (let index = 0; index < 40; index += 1) {
          const selection = await handle.getSelection({ timeoutMs: 10000 });
          polls.push({
            atMs: Math.round(performance.now() - started),
            type: selection.selectionType, text: selection.text ?? "",
          });
          if (selection.selectionType === "text" && (selection.text || "").length)
            break;
          await new Promise((resolve) => setTimeout(resolve, 25));
        }
        return { outcome, settledAtMs: polls.at(-1)?.atMs ?? null,
          settledText: polls.at(-1)?.text ?? "", samples: polls.length };
      });
    }

    // 8. The safety half, now aimed at the method that actually works.  A
    //    contract that wedges the editor when the user clicks in the margin is
    //    not shippable however good the happy path is, so these must either
    //    complete or fail in a way that leaves the worker usable.
    await runCase("handles-zero-length", async (handle, line) => {
      const point = { x: line.x + 100, y: line.y + Math.floor(line.height / 2) };
      const outcome = await attempt(handle, "text-handles-unstable", point, point);
      return { outcome, after: await probeStillUsable(handle) };
    });

    await runCase("handles-empty-area", async (handle, line) => {
      const y = line.y + 6000;
      const outcome = await attempt(handle, "text-handles-unstable",
        { x: line.x, y }, { x: line.x + 1500, y });
      return { outcome, after: await probeStillUsable(handle) };
    });

    // 9. Does a wedging range leave the next, valid range still workable?
    await runCase("handles-recover-after-empty", async (handle, line) => {
      const y = line.y + Math.floor(line.height / 2);
      const first = await attempt(handle, "text-handles-unstable",
        { x: line.x, y: line.y + 6000 }, { x: line.x + 1500, y: line.y + 6000 });
      const second = await attempt(handle, "text-handles-unstable",
        { x: line.x, y }, { x: line.x + Math.floor(line.width / 2), y });
      return { first, second, after: await probeStillUsable(handle) };
    });

    // 10. Repeatability with distinct ranges, each judged by its own readback.
    await runCase("handles-distinct-ranges", async (handle, line) => {
      const y = line.y + Math.floor(line.height / 2);
      const steps = [];
      for (const span of [200, 400, 600, 800]) {
        const outcome = await attempt(handle, "text-handles-unstable",
          { x: line.x, y }, { x: line.x + span, y });
        const selection = await handle.getSelection({ timeoutMs: 10000 });
        steps.push({ span, status: outcome.status,
          type: selection.selectionType, text: selection.text ?? "" });
      }
      return { steps, after: await probeStillUsable(handle) };
    });

    const byName = Object.fromEntries(metrics.cases.map((item) => [item.case, item]));
    const happy = byName["drag-across-text"];
    const repeated = byName["drag-repeated"];
    metrics.verdict = {
      happyPathCompletes: happy?.outcome?.status === "completed",
      happyPathSelectedText: happy?.after?.selectionText || "",
      happyPathSelectionType: happy?.after?.selectionType || null,
      repeatsAllComplete: (repeated?.outcomes || []).every((item) => item.status === "completed"),
      zeroLengthStatus: byName["drag-zero-length"]?.outcome?.status || null,
      zeroLengthLeavesUsable: byName["drag-zero-length"]?.after?.usable ?? null,
      emptyAreaStatus: byName["drag-empty-area"]?.outcome?.status || null,
      emptyAreaLeavesUsable: byName["drag-empty-area"]?.after?.usable ?? null,
      recoversAfterDegenerate: byName["drag-after-degenerate"]?.second?.status || null,
      pollSettledAtMs: byName["drag-then-poll"]?.settledAtMs ?? null,
      pollSettledText: byName["drag-then-poll"]?.settledText ?? "",
      pollFirstSample: byName["drag-then-poll"]?.polls?.[0] ?? null,
      handlesFirstText: byName["handles-then-poll-1"]?.settledText ?? "",
      handlesFirstAtMs: byName["handles-then-poll-1"]?.settledAtMs ?? null,
      handlesSecondText: byName["handles-then-poll-2"]?.settledText ?? "",
      handlesSecondAtMs: byName["handles-then-poll-2"]?.settledAtMs ?? null,
      handlesZeroLength: byName["handles-zero-length"]?.outcome?.status ?? null,
      handlesZeroLeavesUsable: byName["handles-zero-length"]?.after?.usable ?? null,
      handlesEmptyArea: byName["handles-empty-area"]?.outcome?.status ?? null,
      handlesEmptyLeavesUsable: byName["handles-empty-area"]?.after?.usable ?? null,
      handlesRecoverSecond: byName["handles-recover-after-empty"]?.second?.status ?? null,
      handlesRecoverText: byName["handles-recover-after-empty"]?.after?.selectionText ?? "",
      handlesDistinctRanges: byName["handles-distinct-ranges"]?.steps ?? null,
    };
    log(metrics.verdict);
  } catch (error) {
    metrics.error = publicError(error);
  } finally {
    metrics.complete = true;
  }
  return metrics;
}

globalThis.__drag_gate_run = runAll;
if (params.get("autorun") === "1")
  void runAll();
