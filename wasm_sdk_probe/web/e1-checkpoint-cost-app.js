// Task 039: what does a checkpoint save cost on the documents the verdict
// rests on?
//
// The (c'') design in task 033 is "save before a selection-creating gesture,
// so the bytes exist before the trap can be armed".  It is only shippable if
// that save is cheap.  The one number we have is 141 ms, measured on
// frame-contexts.odt -- an 11 KB fixture with three paragraphs.  E1-C's C3
// corpus includes a 22-page document and a 100-page one carrying 100 as-char
// frames, and promising "we save before every drag" on the strength of the
// 11 KB number would be exactly the kind of extrapolation this project keeps
// having to retract.
//
// So: the five C3 documents plus frame-contexts as the reference, on the
// shipped artifact, measuring the save that (c'') would actually issue.
//
// Four saves per document, because they answer different questions:
//
//   clean          the cheapest case: nothing changed since open.  If a
//                  checkpoint fires on an unmodified document this is its cost.
//   dirty          after one edit.  This is the case that matters -- a
//                  checkpoint on a clean document has nothing to protect.
//   repeat         the same save again with no edit between.  Says whether
//                  anything is cached, which decides whether checkpointing
//                  every gesture costs full price every time.
//   loop x3        the real pattern: checkpoint, select, edit, checkpoint, ...
//                  Reported per iteration, because a cost that grows with the
//                  number of checkpoints would rule the design out even if the
//                  first one is cheap.
//
// PREDICTIONS, written before the run:
//
//   1. All six documents save in well under a second.  They are 11-45 KB;
//      "100 pages" is layout stress, not bytes.
//   2. l4-stress-100 is the slowest of the six -- 100 as-char frames to
//      serialise, and frames are the content this whole family of findings is
//      about.
//   3. The dirty save costs no more than roughly the clean one.  If it does,
//      the checkpoint has to be smarter than "save every time".
//   4. Nothing hangs.  Saving is on the surviving side of finding 038's
//      liveness ladder, and no selection here covers a footnote citation --
//      but l4-stress-100 has never been saved through this path before, and a
//      hang here would be a new finding rather than a measurement.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorClient } from "./editor-shell/editor-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e1-editor-v1";
const saveTimeoutMs = Number.parseInt(params.get("saveTimeoutMs") || "180000", 10);
const loopIterations = Number.parseInt(params.get("loops") || "3", 10);

const status = document.querySelector("#status");
const logNode = document.querySelector("#log");

// Anchor text is per document because the checkpoint has to be measured with a
// real selection in play, and each corpus document has its own anchors.  The
// anchors are ordinary body text: none of them is near a footnote citation, so
// none of these runs should trip finding 038.
const DOCUMENTS = [
  { id: "frame-contexts", dir: "e1-fixtures", file: "frame-contexts.odt",
    anchor: "FX-PLAIN", note: "reference: the 11 KB fixture 141 ms came from" },
  { id: "l0-t1-plain-zh", dir: "r7-compat-fixtures", file: "l0-t1-plain-zh.odt",
    anchor: null, note: "C3: plain text and CJK" },
  { id: "l0-t2-styled", dir: "r7-compat-fixtures", file: "l0-t2-styled.odt",
    anchor: null, note: "C3: styles, table, image, comment -- 1 as-char frame" },
  { id: "l0-t3-long", dir: "r7-compat-fixtures", file: "l0-t3-long.odt",
    anchor: null, note: "C3: 22 pages" },
  { id: "l1-review", dir: "r7-compat-fixtures", file: "l1-review.odt",
    anchor: null, note: "C3: comments and tracked changes" },
  { id: "l4-stress-100", dir: "r7-compat-fixtures", file: "l4-stress-100.odt",
    anchor: null, note: "C3: 100 pages, 100 as-char frames -- the worst case" },
];

const metrics = {
  schemaVersion: 1,
  release: "e1-checkpoint-cost",
  task: "039 -- is a checkpoint save cheap enough to issue before every selection",
  profile,
  saveTimeoutMs,
  loopIterations,
  userAgent: navigator.userAgent,
  manifest: null,
  documents: [],
  summary: null,
  complete: false,
  error: null,
};
globalThis.__e1_checkpoint_cost = metrics;
globalThis.__probe_metrics = metrics;

function log(value) {
  logNode.textContent += `${typeof value === "string" ? value : JSON.stringify(value)}\n`;
}

function errorValue(error) {
  return {
    name: error?.name || "Error",
    code: error?.code || "UNCLASSIFIED_ERROR",
    message: String(error?.message || error),
  };
}

/** Time one save and record its size; a save that returns no bytes is not a save. */
async function timedSave(handle, label, entry) {
  const started = performance.now();
  try {
    const result = await handle.save({ format: "odt" }, { timeoutMs: saveTimeoutMs });
    const bytes = result?.bytes?.byteLength ?? result?.byteLength ?? null;
    const record = { label, ms: Math.round(performance.now() - started), bytes };
    (entry.saves ||= []).push(record);
    return record;
  } catch (error) {
    const record = {
      label, ms: Math.round(performance.now() - started),
      error: errorValue(error),
    };
    (entry.saves ||= []).push(record);
    return record;
  }
}

function firstRectangle(search) {
  const raw = (search?.selections?.[0]?.rectangles || "").split(";")[0];
  const numbers = raw.split(",").map((item) => Number.parseInt(item.trim(), 10));
  if (numbers.length !== 4 || numbers.some((item) => !Number.isFinite(item)))
    return null;
  return { x: numbers[0], y: numbers[1], width: numbers[2], height: numbers[3] };
}

/** A selection somewhere in the body, without needing a per-document anchor. */
async function selectSomething(handle, client, spec, entry) {
  // With an anchor, search for it.  Without one, the first line of the page is
  // as good a target as any: what is being measured is the save, not the
  // selection, and the selection only has to be real.
  let rectangle = null;
  if (spec.anchor) {
    const found = await handle.search(spec.anchor, { timeoutMs: 30000 });
    if (found?.found)
      rectangle = firstRectangle(found);
  }
  if (!rectangle)
    rectangle = { x: 1418, y: 1418, width: 1000, height: 275 };
  const midY = rectangle.y + Math.max(1, Math.floor(rectangle.height / 2));
  try {
    await client.selectRange(
      { xTwips: rectangle.x, yTwips: midY },
      { xTwips: rectangle.x + 2000, yTwips: midY },
      { timeoutMs: 30000 });
    entry.selectionOk = true;
  } catch (error) {
    // A failed selection is worth knowing about but does not invalidate the
    // save timings, which are what this run is for.
    entry.selectionOk = false;
    entry.selectionError = errorValue(error);
  }
}

async function runDocument(spec) {
  const entry = { ...spec, status: "running" };
  metrics.documents.push(entry);
  status.textContent = spec.id;
  let engine = null;
  let handle = null;
  try {
    const response = await fetch(`./${spec.dir}/${spec.file}`, { cache: "no-cache" });
    if (!response.ok)
      throw new Error(`fixture fetch failed: ${response.status}`);
    const bytes = await response.arrayBuffer();
    entry.sourceBytes = bytes.byteLength;

    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`,
      timeoutMs: 30000,
      closeRecoveryTimeoutMs: 10000,
    });
    metrics.manifest = engine.manifest;
    const openStarted = performance.now();
    handle = await engine.open(bytes.slice(0), {
      name: spec.file, transfer: true, timeoutMs: 180000,
    });
    entry.openMs = Math.round(performance.now() - openStarted);
    const client = new NarrowEditorClient(handle);

    await timedSave(handle, "clean", entry);

    await selectSomething(handle, client, spec, entry);
    try {
      await handle.insertText("X", { timeoutMs: 30000 });
      entry.edited = true;
    } catch (error) {
      entry.edited = false;
      entry.editError = errorValue(error);
    }

    await timedSave(handle, "dirty", entry);
    await timedSave(handle, "repeat", entry);

    // The pattern (c'') would actually run.
    for (let iteration = 1; iteration <= loopIterations; ++iteration) {
      await timedSave(handle, `loop-${iteration}`, entry);
      await selectSomething(handle, client, spec, entry);
      try {
        await handle.insertText("Y", { timeoutMs: 30000 });
      } catch (error) {
        (entry.loopEditErrors ||= []).push(errorValue(error));
      }
    }

    entry.status = "measured";
  } catch (error) {
    entry.error = errorValue(error);
    entry.status = "failed";
  } finally {
    if (handle) {
      const closeStarted = performance.now();
      try {
        await handle.close({ timeoutMs: 30000 });
        entry.close = "completed";
      } catch (error) {
        entry.close = "failed";
        entry.closeError = errorValue(error);
      }
      entry.closeMs = Math.round(performance.now() - closeStarted);
    }
    try {
      engine?.dispose();
    } catch (error) {
      entry.disposeError = errorValue(error);
    }
  }
  log(entry);
  return entry;
}

function summarise() {
  const rows = metrics.documents.map((entry) => {
    const saves = entry.saves || [];
    const value = (label) => saves.find((item) => item.label === label);
    const loops = saves.filter((item) => item.label.startsWith("loop-"));
    return {
      id: entry.id,
      sourceBytes: entry.sourceBytes ?? null,
      openMs: entry.openMs ?? null,
      cleanMs: value("clean")?.ms ?? null,
      dirtyMs: value("dirty")?.ms ?? null,
      repeatMs: value("repeat")?.ms ?? null,
      loopMs: loops.map((item) => item.ms),
      anySaveFailed: saves.some((item) => item.error),
      status: entry.status,
    };
  });
  const timings = rows.flatMap((row) => [row.cleanMs, row.dirtyMs, row.repeatMs,
    ...row.loopMs]).filter((value) => Number.isFinite(value));
  metrics.summary = {
    rows,
    worstSaveMs: timings.length ? Math.max(...timings) : null,
    // The number the design turns on.  Anything a user would notice as a pause
    // before their drag responds makes "checkpoint every gesture" the wrong
    // shape, however cheap it looks on an 11 KB file.
    allUnder500ms: timings.every((value) => value < 500),
    allSavesReturned: rows.every((row) => !row.anySaveFailed),
  };
  log({ summary: metrics.summary });
}

async function main() {
  try {
    for (const spec of DOCUMENTS)
      await runDocument(spec);
    summarise();
    status.textContent = "complete";
  } catch (error) {
    metrics.error = errorValue(error);
    status.textContent = "failed";
    log({ fatal: metrics.error });
  } finally {
    metrics.complete = true;
  }
}

main();
