// SPEC E2-C, phase D1: the integration sequence.
//
// One session, one document, both action families interleaved -- and every
// mutating cell gets its OWN anchor and its OWN save.  The review that reshaped
// this spec put it plainly: one save after a mixed sequence cannot attribute an
// outcome to a single action, and all four inline formats return the same
// completion, so a mapping error would report the action it was asked for while
// changing the wrong property.
//
// The page judges nothing.  It produces observations and saved documents;
// tools/analyze_e2_c_d1.py applies the criteria frozen in
// e2/validation-matrix-v1.json, without a browser.
//
// Two things it is careful about:
//
//   * anchors are LOCATED, never hardcoded.  A layout that moved shows up as
//     "anchor not found" instead of as an action dispatched at the wrong place.
//     The initial survey runs in a throwaway document; inside the measured
//     document each cell re-locates its own anchor with a short local sweep,
//     because breaks and inserts move everything below them.
//
//   * the inline formats are judged through a committed marker, not through the
//     document alone: the D1 pre-flight measured that a format at a collapsed
//     caret leaves <office:body> byte-identical and shows up only in what is
//     typed afterwards.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { NarrowEditorV2Client } from "./editor-shell-v2/narrow-editor-v2-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const fixture = params.get("fixture") || "d1-anchors.odt";
const rounds = Number(params.get("rounds") || 3);
const stepTimeoutMs = 30000;

const metrics = {
  schemaVersion: 1,
  release: "spec-e2c-d1",
  phase: "D1",
  profile,
  fixture,
  rounds,
  browser: navigator.userAgent,
  cells: {},
  anchors: {},
  rounds_: [],
  complete: false,
  error: null,
};
globalThis.__e2c_d1 = metrics;
globalThis.__probe_metrics = metrics;

const saves = [];
globalThis.__e2c_d1_save_count = () => saves.length;
globalThis.__e2c_d1_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: String(error?.message || error).slice(0, 300),
  formatBarrier: error?.details?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

async function snapshot(handle, label) {
  const bytes = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
  saves.push({ label, b64: await toBase64(bytes) });
  return bytes.byteLength;
}

async function openFixture(engine) {
  const bytes = await fetch(`./e2-fixtures/${fixture}`, { cache: "no-cache" })
    .then((response) => response.arrayBuffer());
  return engine.open(bytes.slice(0), { name: fixture, timeoutMs: 180000 });
}

async function sweep(handle, client, anchor, from, to, step) {
  const hits = [];
  for (let y = from; y <= to; y += step) {
    try {
      await client.selectRange({ xTwips: 1450, yTwips: y },
                               { xTwips: 9000, yTwips: y },
                               { timeoutMs: stepTimeoutMs });
      const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
      if ((selection.text || "").includes(anchor)) hits.push(y);
    } catch { /* a step that cannot select tells us nothing; keep sweeping */ }
  }
  return hits;
}

/** Where the anchors are in a pristine copy -- surveyed away from the measurement. */
async function survey(anchors) {
  const engine = await createDocumentEngine({
    workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
  });
  const handle = await openFixture(engine);
  const client = new NarrowEditorV2Client(handle);
  const found = {};
  for (const anchor of anchors) {
    const hits = await sweep(handle, client, anchor, 1300, 14000, 130);
    found[anchor] = { first: hits[0] ?? null, last: hits[hits.length - 1] ?? null,
                      steps: hits.length };
  }
  await handle.close({ timeoutMs: stepTimeoutMs }).catch(() => {});
  engine.dispose();
  return found;
}

/** Re-find an anchor near where the survey put it: breaks move everything below. */
async function locate(handle, client, anchor, hint) {
  if (hint == null) return null;
  for (const radius of [0, 195, 390, 780, 1560]) {
    const hits = await sweep(handle, client, anchor,
                             Math.max(600, hint - radius), hint + radius, 65);
    if (hits.length) return hits[0];
  }
  return null;
}

const FORMAT_ACTIONS = new Set(["set-bold", "set-italic", "set-underline",
  "set-strikethrough"]);

async function collapsedAt(client, y) {
  await client.selectRange({ xTwips: 2000, yTwips: y },
                           { xTwips: 2000, yTwips: y },
                           { timeoutMs: stepTimeoutMs });
}

async function rangeAt(client, y, endY = y) {
  await client.selectRange({ xTwips: 1450, yTwips: y },
                           { xTwips: 9000, yTwips: endY },
                           { timeoutMs: stepTimeoutMs });
}

// The cells.  `kind` says how the cell is driven; the ORACLE is not here -- it
// is in the frozen matrix, and keeping the two apart is what stops a harness
// from quietly deciding what counts as passing.
const CELLS = [
  { id: "d1-place-caret", kind: "caret", anchor: "E2-D1-MOVE" },
  { id: "d1-insert-text", kind: "insert", anchor: "E2-D1-INSERT",
    marker: "D1INSERT" },
  { id: "d1-move-character-left", kind: "action", anchor: "E2-D1-MOVE",
    action: "move-character-left" },
  { id: "d1-move-character-right", kind: "action", anchor: "E2-D1-MOVE",
    action: "move-character-right" },
  { id: "d1-set-bold-true", kind: "format", anchor: "E2-D1-BOLD-ON",
    action: "set-bold", enabled: true, marker: "D1BOLDON" },
  { id: "d1-set-bold-false", kind: "format", anchor: "E2-D1-BOLD-OFF",
    action: "set-bold", enabled: false, marker: "D1BOLDOFF" },
  { id: "d1-set-italic-true", kind: "format", anchor: "E2-D1-ITALIC-ON",
    action: "set-italic", enabled: true, marker: "D1ITALON" },
  { id: "d1-set-italic-false", kind: "format", anchor: "E2-D1-ITALIC-OFF",
    action: "set-italic", enabled: false, marker: "D1ITALOFF" },
  { id: "d1-set-underline-true", kind: "format", anchor: "E2-D1-UNDERLINE-ON",
    action: "set-underline", enabled: true, marker: "D1UNDRON" },
  { id: "d1-set-underline-false", kind: "format", anchor: "E2-D1-UNDERLINE-OFF",
    action: "set-underline", enabled: false, marker: "D1UNDROFF" },
  { id: "d1-set-strikethrough-true", kind: "format", anchor: "E2-D1-STRIKE-ON",
    action: "set-strikethrough", enabled: true, marker: "D1STRKON" },
  { id: "d1-set-strikethrough-false", kind: "format", anchor: "E2-D1-STRIKE-OFF",
    action: "set-strikethrough", enabled: false, marker: "D1STRKOFF" },
  { id: "d1-list-unordered-collapsed", kind: "action",
    anchor: "E2-D1-LIST-UNORDERED", action: "set-list-unordered" },
  { id: "d1-list-ordered-collapsed", kind: "action",
    anchor: "E2-D1-LIST-ORDERED", action: "set-list-ordered" },
  { id: "d1-list-none-collapsed", kind: "action", anchor: "E2-D1-LIST-NONE",
    action: "set-list-none" },
  { id: "d1-heading-collapsed", kind: "action", anchor: "E2-D1-HEAD-TARGET",
    action: "set-paragraph-heading" },
  { id: "d1-body-collapsed", kind: "action", anchor: "E2-D1-BODY-TARGET",
    action: "set-paragraph-body" },
  { id: "d1-heading-range-single", kind: "action", anchor: "E2-D1-RANGE-ONE",
    action: "set-paragraph-heading", gesture: "range-single" },
  { id: "d1-heading-range-cross", kind: "action", anchor: "E2-D1-RANGE-ONE",
    action: "set-paragraph-heading", gesture: "range-cross",
    crossAnchor: "E2-D1-RANGE-TWO" },
  { id: "d1-ordered-range-cross-both-already-numbered", kind: "action",
    anchor: "E2-D1-NUM-ONE", action: "set-list-ordered", gesture: "range-cross",
    crossAnchor: "E2-D1-NUM-TWO" },
  // Deletes and breaks come after the layout-sensitive work: they move every
  // line below them, and a cell that has to re-find its anchor three times is a
  // cell whose result is mostly about the sweep.
  { id: "d1-delete-backward", kind: "action", anchor: "E2-D1-DELBACK",
    action: "delete-backward" },
  { id: "d1-delete-forward", kind: "action", anchor: "E2-D1-DELFWD",
    action: "delete-forward" },
  { id: "d1-insert-paragraph-break", kind: "action", anchor: "E2-D1-BREAKPARA",
    action: "insert-paragraph-break" },
  { id: "d1-insert-line-break", kind: "action", anchor: "E2-D1-BREAKLINE",
    action: "insert-line-break" },
  { id: "d1-interleave-v1-after-v2", kind: "interleave",
    anchor: "E2-D1-INTERLEAVE" },
  { id: "d1-characterisation-range-inherited", kind: "characterise",
    anchor: "E2-D1-MOVE" },
  { id: "d1-undo", kind: "undo" },
  { id: "d1-save", kind: "save" },
];

const ANCHORS = [...new Set(CELLS.flatMap(
  (cell) => [cell.anchor, cell.crossAnchor].filter(Boolean)))];

async function runCell(context, cell, round) {
  const { handle, client, hints } = context;
  const entry = { cell: cell.id, round, action: cell.action ?? null,
                  gesture: cell.gesture ?? "collapsed", anchor: cell.anchor ?? null,
                  locatedY: null, result: null, error: null, steps: [] };
  const label = `${cell.id}-round${round}`;
  try {
    let y = null;
    if (cell.anchor) {
      y = await locate(handle, client, cell.anchor, hints[cell.anchor]?.first);
      entry.locatedY = y;
      if (y == null) throw Object.assign(new Error(`anchor ${cell.anchor} not found`),
                                         { code: "ANCHOR_NOT_FOUND" });
      hints[cell.anchor] = { first: y };
    }

    if (cell.kind === "caret") {
      await collapsedAt(client, y);
      const state = await client.getState({ timeoutMs: stepTimeoutMs });
      entry.result = { selectionType: state.selectionType,
                       collapsed: state.selection?.collapsed ?? null,
                       observed: state.selection?.observed ?? null,
                       revision: state.revision };
      return entry;
    }

    if (cell.kind === "insert") {
      await collapsedAt(client, y);
      const before = handle.revision;
      const inserted = await handle.insertText(cell.marker,
                                               { timeoutMs: stepTimeoutMs });
      entry.result = { marker: cell.marker, beforeRevision: before,
                       revision: inserted?.revision ?? handle.revision };
      await snapshot(handle, label);
      return entry;
    }

    if (cell.kind === "undo") {
      const before = handle.revision;
      await handle.undo({ timeoutMs: stepTimeoutMs });
      entry.result = { beforeRevision: before, revision: handle.revision };
      await snapshot(handle, label);
      return entry;
    }

    if (cell.kind === "save") {
      entry.result = { bytes: await snapshot(handle, label) };
      return entry;
    }

    if (cell.kind === "characterise") {
      // Recorded, never judged (SPEC E2-C 2.5): the manifest declares
      // `collapsed` for the ten and this round does not change that.
      for (const action of ["set-bold", "delete-backward"]) {
        try {
          await rangeAt(client, y);
          const result = await client.action(
            action, action === "set-bold" ? { enabled: true } : {});
          entry.steps.push({ action, ok: true, revision: result.revision,
                             changed: result.changed,
                             completion: result.completion });
        } catch (error) {
          entry.steps.push({ action, ok: false, error: publicError(error) });
        }
      }
      await snapshot(handle, label);
      return entry;
    }

    if (cell.kind === "interleave") {
      await collapsedAt(client, y);
      const paragraph = await client.action("set-paragraph-heading");
      entry.steps.push({ action: "set-paragraph-heading",
                         changed: paragraph.changed,
                         completion: paragraph.completion,
                         revision: paragraph.revision });
      await collapsedAt(client, y);
      const inline = await client.action("set-bold", { enabled: true });
      entry.steps.push({ action: "set-bold", changed: inline.changed,
                         completion: inline.completion,
                         revision: inline.revision });
      await collapsedAt(client, y);
      const removed = await client.action("delete-backward");
      entry.steps.push({ action: "delete-backward", changed: removed.changed,
                         completion: removed.completion,
                         revision: removed.revision });
      await snapshot(handle, label);
      return entry;
    }

    // kind === "action" or "format"
    //
    // The before-picture is taken BEFORE the gesture, not after it.  Taken
    // after, the save itself disturbed the selection and the next dispatch
    // landed on a different state: delete-backward came back
    // EDITOR_BOUNDARY_UNSUPPORTED in a run where the identical sequence without
    // the extra save had worked.  A setup step that changes the state being
    // measured is the oldest mistake in this tree.
    await snapshot(handle, `${label}-before-action`);
    if (cell.gesture === "range-cross") {
      const endY = await locate(handle, client, cell.crossAnchor,
                                hints[cell.crossAnchor]?.first);
      entry.crossY = endY;
      if (endY == null)
        throw Object.assign(new Error(`anchor ${cell.crossAnchor} not found`),
                            { code: "ANCHOR_NOT_FOUND" });
      hints[cell.crossAnchor] = { first: endY };
      await rangeAt(client, y, endY);
    } else if (cell.gesture === "range-single") {
      await rangeAt(client, y);
    } else {
      await collapsedAt(client, y);
    }

    const before = handle.revision;
    const options = cell.kind === "format" ? { enabled: cell.enabled } : {};
    const result = await client.action(cell.action, options);
    entry.result = {
      action: result.action, beforeRevision: result.beforeRevision,
      revision: result.revision, changed: result.changed ?? null,
      completion: result.completion,
      formatBarrier: result.formatBarrier ?? null,
      handleRevisionBefore: before,
    };

    if (cell.kind === "format") {
      // The pre-flight showed the document does not move at a collapsed caret:
      // the format lands on what is typed next.  Saving BEFORE the marker as
      // well, so the analyzer can check both halves of that.
      await snapshot(handle, `${label}-after-action`);
      await handle.insertText(cell.marker, { timeoutMs: stepTimeoutMs });
      entry.result.marker = cell.marker;
    }
    await snapshot(handle, label);
    return entry;
  } catch (error) {
    entry.error = publicError(error);
    try { await snapshot(handle, `${label}-failed`); } catch { /* down */ }
    return entry;
  }
}

void (async () => {
  try {
    {
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const contract = engine.manifest?.editorContract || {};
      metrics.cells["d0-inventory"] = {
        profile: engine.manifest?.profile,
        wasmSha256: contract.wasmSha256,
        loaderSha256: contract.loaderSha256,
        workerSha256: contract.workerSha256,
      };
      engine.dispose();
    }

    metrics.anchors = await survey(ANCHORS);
    log({ step: "survey", anchors: metrics.anchors });
    const notFound = Object.entries(metrics.anchors)
      .filter(([, span]) => span.first == null).map(([name]) => name);
    if (notFound.length)
      throw Object.assign(new Error(`anchors not found: ${notFound}`),
                          { code: "ANCHOR_NOT_FOUND" });

    for (let round = 1; round <= rounds; round += 1) {
      // A fresh engine and a fresh document per round.  Rounds must be
      // independent: three rounds that inherited each other's mutations would
      // be one long round reported as three.
      const engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      const handle = await openFixture(engine);
      const client = new NarrowEditorV2Client(handle);
      const hints = JSON.parse(JSON.stringify(metrics.anchors));
      const context = { handle, client, hints };
      const results = [];
      await snapshot(handle, `round${round}-opened`);
      for (const cell of CELLS) {
        const entry = await runCell(context, cell, round);
        results.push(entry);
        log(entry);
      }
      metrics.rounds_.push({ round, cells: results });
      await handle.close({ timeoutMs: stepTimeoutMs }).catch(() => {});
      engine.dispose();
    }

    metrics.complete = true;
    log({ complete: true, rounds: metrics.rounds_.length, saves: saves.length });
  } catch (error) {
    metrics.error = publicError(error);
    metrics.complete = true;
    log({ complete: true, fatal: metrics.error });
  }
})();
