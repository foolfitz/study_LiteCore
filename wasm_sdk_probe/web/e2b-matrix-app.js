// SPEC E2-B section 7: the positive matrix, on the product artifact.
//
// This is the run the freeze rests on, so unlike the smoke and parity runs it
// judges DOCUMENTS.  The harness drives and saves; the verdict comes from
// analyze_e2b_matrix.py reading only what is saved here.
//
// Gesture classes are the engine's own routing boundary (SPEC E2-B 9.9), not a
// taxonomy invented for the harness: `collapsed` is a caret, `range-single` is
// a range whose pre-dispatch html holds one block, `range-cross` is one that
// holds more.  Each arm records the route the ENGINE reported, so an arm that
// intended one class and got another is visible rather than silently counted.
//
// Coordinates are never hardcoded.  A sweep finds each anchor by reading the
// selection back, so a layout change shows up as "anchor not found" instead of
// as a confident measurement of the wrong paragraph.

import { createDocumentEngine } from "./sdk/document-sdk.js";
import { ParagraphEditorClient } from "./editor-shell-v2/paragraph-editor-client.js";

const params = new URLSearchParams(location.search);
const profile = params.get("profile") || "e2-editor-v2";
const rounds = Number.parseInt(params.get("rounds") || "3", 10);
const stepTimeoutMs = Number.parseInt(params.get("stepTimeoutMs") || "30000", 10);

const metrics = {
  schemaVersion: 1,
  release: "spec-e2b-positive-matrix",
  prediction: "findings/evidence/sdk-e2/discovery/e2b-matrix/PREDICTION.md",
  profile,
  rounds,
  browser: navigator.userAgent,
  crossOriginIsolated: globalThis.crossOriginIsolated,
  arms: [],
  complete: false,
  error: null,
};
globalThis.__e2b_matrix = metrics;
globalThis.__probe_metrics = metrics;
const saves = [];
globalThis.__e2b_matrix_save_count = () => saves.length;
globalThis.__e2b_matrix_save = (index) => saves[index] || null;

const logNode = document.querySelector("#log");
const log = (value) => { logNode.textContent += `${JSON.stringify(value)}\n`; };
const publicError = (error) => ({
  code: error?.code || error?.name || "ERROR",
  message: error?.message || String(error),
  formatBarrier: error?.details?.formatBarrier ?? null,
});

async function toBase64(bytes) {
  let binary = "";
  const view = new Uint8Array(bytes);
  for (let i = 0; i < view.length; i += 0x8000)
    binary += String.fromCharCode(...view.subarray(i, i + 0x8000));
  return btoa(binary);
}

const LIST = "list-contexts.odt";
const MULTI = "multi-paragraph.odt";
const WRAP = "wrapped-paragraph.odt";
const SPLIT = "list-split.odt";
const MIXED = "mixed-state.odt";

// Which directory each fixture lives in.  The E1 corpus is frozen
// (mutationPolicy copy-only), so E2-B's own fixtures have their own home.
const FIXTURE_DIR = {
  [LIST]: "e1-fixtures", [MULTI]: "e1-fixtures",
  [WRAP]: "e2b-fixtures", [SPLIT]: "e2b-fixtures", [MIXED]: "e2b-fixtures",
};

async function openDocument(engine, fixture) {
  const bytes = await fetch(`./${FIXTURE_DIR[fixture]}/${fixture}`, { cache: "no-cache" })
    .then((response) => response.arrayBuffer());
  return engine.open(bytes.slice(0), { name: fixture, timeoutMs: 180000 });
}

/** Sweep for an anchor, reading the selection back at each step. */
async function findAnchor(handle, client, anchor) {
  const hits = [];
  for (let y = 1300; y <= 4400; y += 130) {
    try {
      await client.selectRange({ xTwips: 1450, yTwips: y },
                               { xTwips: 9000, yTwips: y },
                               { timeoutMs: stepTimeoutMs });
      const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
      if ((selection.text || "").includes(anchor))
        hits.push(y);
    } catch { /* a step that cannot select tells us nothing; keep sweeping */ }
  }
  return hits;
}

/** Put the engine into the gesture class this arm intends. */
async function establishGesture(handle, client, spec, anchorY, lastY) {
  switch (spec.gesture) {
    case "collapsed":
      // Same point twice: a range of zero width is a caret.
      await client.selectRange({ xTwips: 1500, yTwips: anchorY },
                               { xTwips: 1500, yTwips: anchorY },
                               { timeoutMs: stepTimeoutMs });
      return true;
    case "range-single":
      await client.selectRange({ xTwips: 1450, yTwips: anchorY },
                               { xTwips: 9000, yTwips: anchorY },
                               { timeoutMs: stepTimeoutMs });
      return true;
    case "range-single-reverse":
      // END left of START.  #49 measured reverse SELECTION; reverse DISPATCH
      // is what SPEC 3.9 requires re-run here and what the three gesture
      // classes on their own would drop.
      await client.selectRange({ xTwips: 9000, yTwips: anchorY },
                               { xTwips: 1450, yTwips: anchorY },
                               { timeoutMs: stepTimeoutMs });
      return true;
    case "range-single-wrapped":
      // One paragraph, several visual lines: the same route as range-single,
      // reached through a different geometry (SPEC 7.1 records it as a fixture
      // variant, not a fourth class -- its preBlocks is still 1).
      await client.selectRange({ xTwips: 1450, yTwips: anchorY },
                               { xTwips: 9000, yTwips: lastY },
                               { timeoutMs: stepTimeoutMs });
      return true;
    case "range-cross":
      await client.selectRange({ xTwips: 1450, yTwips: anchorY },
                               { xTwips: 9000, yTwips: anchorY + (spec.crossOffset ?? 390) },
                               { timeoutMs: stepTimeoutMs });
      return true;
    default:
      return false;
  }
}

// Anchor coordinates, surveyed ONCE per fixture on a throwaway document.
//
// The first version of this harness swept inside each arm, on the very document
// the arm then measured -- twenty selectRange calls before the one that
// mattered.  The gate had already learned not to do that ("the search itself
// selects, and a selection made by the setup is exactly the shell state this is
// trying to measure"), and the cost showed up immediately: the wrapped arm's
// span read back as its first visual line instead of the whole run.
const anchorCache = new Map();

async function surveyFixture(fixture, anchor) {
  const key = `${fixture}::${anchor}`;
  if (anchorCache.has(key))
    return anchorCache.get(key);
  let engine = null;
  let handle = null;
  let hits = [];
  try {
    engine = await createDocumentEngine({
      workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
    });
    handle = await openDocument(engine, fixture);
    hits = await findAnchor(handle, new ParagraphEditorClient(handle), anchor);
  } catch (error) {
    hits = [];
  } finally {
    await handle?.close({ timeoutMs: 15000 }).catch(() => {});
    engine?.dispose();
  }
  const span = { first: hits[0] ?? null, last: hits[hits.length - 1] ?? null,
                 steps: hits.length };
  anchorCache.set(key, span);
  metrics.anchors = metrics.anchors || {};
  metrics.anchors[key] = span;
  return span;
}

async function runArm(spec) {
  const entry = { arm: spec.name, gesture: spec.gesture, action: spec.action,
                  fixture: spec.fixture, anchor: spec.anchor,
                  expects: spec.expects, rounds: [] };
  for (let round = 1; round <= rounds; round++) {
    // A fresh engine per round, not merely per arm: finding 038's rule is that
    // a wedged pending slot must not be allowed to decide the next answer, and
    // a round is the unit that gets cited.
    let engine = null;
    let handle = null;
    const record = { round };
    try {
      engine = await createDocumentEngine({
        workerUrl: `./profiles/${profile}/sdk-worker.js`, timeoutMs: 60000,
      });
      handle = await openDocument(engine, spec.fixture);
      const client = new ParagraphEditorClient(handle);

      // The comparison baseline is a save through THIS engine with no action.
      // Never the authored fixture: the export normalises what the fixture
      // leaves implicit, and comparing against the authored file reports every
      // paragraph as changed (the e2b-gate lesson, learned the hard way).
      const before = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
      saves.push({ arm: spec.name, round, phase: "before",
                   fixture: spec.fixture, b64: await toBase64(before) });

      const span = await surveyFixture(spec.fixture, spec.anchor);
      if (span.first === null) {
        record.void = `anchor not found: ${spec.anchor}`;
        entry.rounds.push(record);
        continue;
      }
      record.anchorY = span.first;
      record.anchorSteps = span.steps;
      await establishGesture(handle, client, spec, span.first, span.last);

      const selection = await handle.getSelection({ timeoutMs: stepTimeoutMs });
      record.selectionBeforeDispatch = {
        text: (selection.text || "").slice(0, 120),
        length: (selection.text || "").length,
      };

      try {
        record.result = await client.action(spec.action, { timeoutMs: stepTimeoutMs });
        record.actionStatus = "completed";
        record.route = record.result.formatBarrier?.route ?? null;
        record.preBlocks = record.result.formatBarrier?.preBlocks ?? null;
        record.crossIdentityHeld = record.result.formatBarrier?.crossIdentityHeld ?? null;
        record.crossStateHeld = record.result.formatBarrier?.crossStateHeld ?? null;
        record.revision = record.result.revision;
        record.changed = record.result.changed;
        record.completion = record.result.completion;
      } catch (error) {
        record.actionStatus = "failed";
        record.actionError = publicError(error);
        record.route = error?.details?.formatBarrier?.route ?? null;
      }

      // The no-op arm dispatches the SAME action a second time and saves in
      // between, because the revision equation is about what a repeat does and
      // no round in this project had ever repeated one.
      if (spec.repeat) {
        const middle = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
        saves.push({ arm: spec.name, round, phase: "middle",
                     fixture: spec.fixture, b64: await toBase64(middle) });
        try {
          record.repeatResult = await client.action(spec.action,
                                                    { timeoutMs: stepTimeoutMs });
          record.repeatStatus = "completed";
          record.repeatRevision = record.repeatResult.revision;
        } catch (error) {
          record.repeatStatus = "failed";
          record.repeatError = publicError(error);
        }
      }

      const after = await handle.save({ format: "odt" }, { timeoutMs: 180000 });
      saves.push({ arm: spec.name, round, phase: "after",
                   fixture: spec.fixture, b64: await toBase64(after) });
    } catch (error) {
      record.fatal = publicError(error);
    } finally {
      await handle?.close({ timeoutMs: 15000 }).catch(() => {});
      engine?.dispose();
    }
    entry.rounds.push(record);
  }
  log({ arm: entry.arm, rounds: entry.rounds.length,
        routes: entry.rounds.map((r) => r.route ?? r.void ?? "?") });
  metrics.arms.push(entry);
}

const ACTIONS = ["set-list-none", "set-list-unordered", "set-list-ordered",
                 "set-paragraph-heading", "set-paragraph-body"];

// 5 actions x 3 gesture classes.  `set-list-none` aims at a paragraph that IS
// a list so that it has something to leave; `set-paragraph-body` aims at the
// heading for the same reason.  Aiming every action at the same paragraph would
// make two of them no-ops and the matrix would be quietly measuring less than
// it claims.
const ANCHOR_FOR = {
  "set-list-none": "E1-LC-BULLET-ONE",
  "set-list-unordered": "E1-LC-ISOLATED",
  "set-list-ordered": "E1-LC-ISOLATED",
  "set-paragraph-heading": "E1-LC-ISOLATED",
  "set-paragraph-body": "E1-LC-HEADING",
};

const ARMS = [];
for (const action of ACTIONS) {
  for (const gesture of ["collapsed", "range-single"]) {
    ARMS.push({
      name: `${action}--${gesture}`, action, gesture, fixture: LIST,
      anchor: ANCHOR_FOR[action],
      expects: "the targeted paragraph reaches the target state, nothing else moves",
    });
  }
  // The crossing class needs two adjacent paragraphs in a known state, which
  // list-contexts does not offer for every action; multi-paragraph does.
  ARMS.push({
    name: `${action}--range-cross`, action, gesture: "range-cross",
    fixture: MULTI, anchor: "E1-MULTI-START",
    expects: "both covered paragraphs reach the target state, the other three do not",
  });
}

// SPEC E2-B 7.1's six added cells, plus 9.9's self-red arm.
ARMS.push(
  { name: "reverse-range", action: "set-list-unordered",
    gesture: "range-single-reverse", fixture: LIST, anchor: "E1-LC-ISOLATED",
    expects: "SPEC 3.9 requires all eight gate arms re-run; reverse maps to no gesture class" },
  { name: "wrapped-line-range", action: "set-list-unordered",
    gesture: "range-single-wrapped", fixture: WRAP, anchor: "G1WRAP",
    expects: "one paragraph across several visual lines; still preBlocks 1" },
  { name: "list-transition-ul-to-ol", action: "set-list-ordered",
    gesture: "range-single", fixture: LIST, anchor: "E1-LC-BULLET-ONE",
    expects: "an already-bulleted paragraph becomes numbered without structural loss" },
  { name: "mid-list-departure", action: "set-list-none", gesture: "range-cross",
    fixture: SPLIT, anchor: "E2B-SPLIT-TWO", crossOffset: 390,
    expects: "items 2-3 leave a five-item list, splitting it; nothing else moves" },
  { name: "mixed-state-crossing", action: "set-list-unordered",
    gesture: "range-cross", fixture: MIXED, anchor: "E2B-MIXED-LISTED",
    expects: "one listed and one plain paragraph in a single crossing range" },
  { name: "no-op-repeat", action: "set-list-unordered", gesture: "collapsed",
    fixture: LIST, anchor: "E1-LC-ISOLATED", repeat: true,
    expects: "the repeat still advances the revision and leaves the body identical" },
  { name: "self-red-expect-ol-dispatch-bullet", action: "set-list-unordered",
    gesture: "range-cross", fixture: MULTI, anchor: "E1-MULTI-START",
    selfRed: "ol",
    expects: "the judge is told to expect an ordered list; it must report FAILURE" },
);

void (async () => {
  try {
    metrics.armCount = ARMS.length;
    for (const spec of ARMS)
      await runArm(spec);
  } catch (error) {
    metrics.error = publicError(error);
    log({ fatal: metrics.error });
  } finally {
    metrics.complete = true;
    log({ complete: true, arms: metrics.arms.length, saves: saves.length });
  }
})();
