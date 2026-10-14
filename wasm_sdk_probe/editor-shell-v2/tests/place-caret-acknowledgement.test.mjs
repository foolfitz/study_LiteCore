// Ruling 6 Q2 (condition 45), finding 138: `placeCaret`'s acknowledgement.
//
// The base class (editor-shell/editor-session.js, E1-C-bound) returns a
// same-line click as placed when `sourceSequence` advanced and the caret is on
// the clicked line.  The sequence advances for callbacks that have nothing to
// do with the click -- INVALIDATE_TILES on v19 (F5), DOCUMENT_SIZE_CHANGED on
// v20 -- so a lone one inside the click's 22-28 ms window reports the click
// placed while the caret core still holds the OLD position, and the next
// synchronous paste or format lands there.
//
// The rule (ruling 6 §Q2): evidence = the sequence advanced AND a field the
// click can change differs from the pre-click state -- the caret position
// (`caretDiffers`, position only) or the selection (`collapsed` / `rectangles`).
// Return on evidence when on target, on `onTarget` after `graceMs` (unchanged),
// or on evidence with the caret moved off the line (052); never on the
// sequence alone.
//
// This is review 6's harness (review-6-artifacts/q4-placecaret.mjs) with the
// four arms ruling 6 added: the REAL `placeCaret` of the class under test is
// driven against a scripted engine in which only the TIMING of editor-state
// changes is scripted.  Seven arms, once per class.  On the subclass all seven
// must hold; on the frozen base three are false acknowledgements, kept here as
// controls -- they are what shows the lone bump really lands inside the window
// and that a predicate returning on the sequence alone would be caught.

import assert from "node:assert/strict";
import test from "node:test";

import { EditorSession } from "../../editor-shell/editor-session.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const LINE = { y: 2000, height: 300 };            // the caret's line, twips
const rect = (x, y = LINE.y, width = 0, height = LINE.height) => ({ x, y, width, height });
const COLLAPSED = Object.freeze({ observed: true, collapsed: true, start: null, end: null, rectangles: [] });
const GRACE_MS = 400;                              // the base's default caretAckGraceMs

/**
 * A scripted engine.  `lonePushAt`: a state-changing callback unrelated to the
 * click bumps `sourceSequence` (and, for the v20 shape, the size counter) at
 * that time.  `click`: when the click is processed and what it changes; null
 * means the engine never processes it.
 */
function scripted({ caret, selection = COLLAPSED, lonePushAt = null, lonePushBumpsSize = false, click = null }) {
  const t0 = Date.now();
  let sequence = 10;
  let sizeCount = 4;
  let state = { caret, selection };
  let clickTookEffectAtMs = null;
  const timers = [];
  const document = {
    revision: 7,
    async click() {
      if (lonePushAt !== null) {
        timers.push(setTimeout(() => { sequence += 1; if (lonePushBumpsSize) sizeCount += 1; }, lonePushAt));
      }
      if (click !== null) {
        timers.push(setTimeout(() => {
          sequence += 1;
          state = { caret: click.caret ?? state.caret, selection: click.selection ?? state.selection };
          clickTookEffectAtMs = Date.now() - t0;
        }, click.at));
      }
      return { revision: 7 };
    },
  };
  const editor = {
    async getState() {
      return { sourceSequence: sequence, documentSizeChangedCount: sizeCount,
               caret: structuredClone(state.caret), selection: structuredClone(state.selection) };
    },
  };
  return {
    document, editor, t0, timers,
    clickTookEffectAt: () => clickTookEffectAtMs,
    caretNow: () => structuredClone(state.caret),
  };
}

/** Drive `Class.prototype.placeCaret` -- the product's code -- against one script. */
async function drive(Class, script, [x, y], options = {}) {
  const engine = scripted(script);
  const session = Object.create(Class.prototype);
  session._enqueue = (label, operation) => operation({ document: engine.document, editor: engine.editor });
  let result = null;
  let error = null;
  try {
    result = await session.placeCaret(x, y, options);
  } catch (thrown) {
    error = thrown;
  }
  const returnedAtMs = Date.now() - engine.t0;
  // What a synchronous paste dispatched next would see: the caret the core holds NOW.
  const caretWhenNextCommandIsSent = engine.caretNow();
  await new Promise((resolve) => setTimeout(resolve, 40));
  engine.timers.forEach(clearTimeout);
  return { result, error, returnedAtMs, clickTookEffectAtMs: engine.clickTookEffectAt(), caretWhenNextCommandIsSent };
}

/* --------------------------------------------------------------- expectations */

/** Placed after the click took effect, caret at the clicked x, without waiting out the grace. */
const acknowledgedAt = (x) => (o) => {
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.caretOnClickedLine, true);
  assert.equal(o.result.state.caret.x, x, "the state returned carries the clicked point");
  assert.ok(o.clickTookEffectAtMs !== null && o.returnedAtMs >= o.clickTookEffectAtMs,
            `returned at ${o.returnedAtMs} ms, the click took effect at ${o.clickTookEffectAtMs} ms`);
  assert.equal(o.caretWhenNextCommandIsSent.x, x, "the next command lands at the clicked point");
  assert.ok(o.result.caretWaitedMs < GRACE_MS, `waited ${o.result.caretWaitedMs} ms: fell back to the grace`);
};

/** The 138 shape: placed BEFORE the click was processed, on the sequence alone. */
const falselyAcknowledged = (o) => {
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.state.caret.x, 1000, "the state returned still holds the OLD caret");
  assert.ok(o.clickTookEffectAtMs === null || o.returnedAtMs < o.clickTookEffectAtMs,
            `returned at ${o.returnedAtMs} ms, the click took effect at ${o.clickTookEffectAtMs} ms`);
  assert.equal(o.caretWhenNextCommandIsSent.x, 1000, "the next command lands at the old caret");
};

/** The identical-point answer: the grace waited out, the caret where it was. */
const alreadyAtTarget = (o) => {
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "already-at-target");
  assert.equal(o.result.caretOnClickedLine, true);
  assert.equal(o.result.state.caret.x, 1000);
  assert.ok(o.result.caretWaitedMs >= GRACE_MS, `waited ${o.result.caretWaitedMs} ms, less than the grace`);
};

/** 052: the engine moved the caret to a line that is not the clicked one. */
const movedOffTheLine = (o) => {
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-moved-the-caret-off-the-clicked-line");
  assert.equal(o.result.caretOnClickedLine, false);
  assert.equal(o.result.state.caret.y, 5000);
  assert.ok(o.result.caretWaitedMs < GRACE_MS);
};

/* ------------------------------------------------------- the seven arms (§Q2) */

const SAME_LINE = [5000, 2150];
const PROCESSED = { at: 25, caret: rect(5000) };   // the measured 22-28 ms (finding 048)

const ARMS = [
  { name: "same-line click, no unrelated callback (v19)",
    script: { caret: rect(1000), click: PROCESSED }, at: SAME_LINE,
    candidate: acknowledgedAt(5000), base: acknowledgedAt(5000) },
  { name: "same-line click, lone DOCUMENT_SIZE_CHANGED at 3 ms (v20)",
    script: { caret: rect(1000), lonePushAt: 3, lonePushBumpsSize: true, click: PROCESSED }, at: SAME_LINE,
    candidate: acknowledgedAt(5000), base: falselyAcknowledged },
  { name: "same-line click, lone INVALIDATE_TILES at 3 ms (F5, v19)",
    script: { caret: rect(1000), lonePushAt: 3, click: PROCESSED }, at: SAME_LINE,
    candidate: acknowledgedAt(5000), base: falselyAcknowledged },
  { name: "identical-point click, engine says nothing",
    script: { caret: rect(1000) }, at: [1000, 2150],
    candidate: alreadyAtTarget, base: alreadyAtTarget },
  { name: "click collapses a selection at its caret end, caret rect unchanged",
    script: { caret: rect(5000),
              selection: { observed: true, collapsed: false, start: rect(1000), end: rect(5000),
                           rectangles: [{ x: 1000, y: LINE.y, width: 4000, height: LINE.height }] },
              click: { at: 25, caret: rect(5000), selection: COLLAPSED } },
    at: SAME_LINE,
    candidate: acknowledgedAt(5000), base: acknowledgedAt(5000) },
  { name: "click lands on another line (052 shape)",
    script: { caret: rect(1000), click: { at: 25, caret: rect(0, 5000) } }, at: [2000, 6000],
    candidate: movedOffTheLine, base: movedOffTheLine },
  { name: "lone size bump, the click is never processed (image-click shape)",
    script: { caret: rect(1000), lonePushAt: 3, lonePushBumpsSize: true }, at: SAME_LINE,
    candidate: alreadyAtTarget, base: falselyAcknowledged },
];

for (const arm of ARMS) {
  test(`override: ${arm.name}`, async () => {
    arm.candidate(await drive(NarrowEditorV2Session, arm.script, arm.at));
  });
}

// The frozen base, as a control: three false acknowledgements (ruling 6 §Q2's
// table, "today" column).  If these ever pass as placed-after-the-click, the
// lone bump is not landing inside the window and the seven arms above prove
// nothing.
for (const arm of ARMS) {
  test(`control, frozen base (E1-C-bound): ${arm.name}`, async () => {
    arm.base(await drive(EditorSession, arm.script, arm.at));
  });
}

test("the override is the subclass's own, and the base is untouched", () => {
  assert.ok(Object.prototype.hasOwnProperty.call(NarrowEditorV2Session.prototype, "placeCaret"),
            "placeCaret must be an own override on NarrowEditorV2Session");
  assert.notEqual(NarrowEditorV2Session.prototype.placeCaret, EditorSession.prototype.placeCaret);
});

test("contract: the timeout error keeps the base's code and details shape", async () => {
  // A click the engine never processes, with the caret on ANOTHER line: no
  // evidence, never on target, so both time out.
  const script = { caret: rect(1000, 8000) };
  const options = { caretTimeoutMs: 60, caretAckGraceMs: 30 };
  const base = await drive(EditorSession, script, SAME_LINE, options);
  const override = await drive(NarrowEditorV2Session, script, SAME_LINE, options);
  for (const o of [base, override]) {
    assert.equal(o.result, null);
    assert.equal(o.error.code, "EDITOR_CARET_NOT_PLACED");
  }
  assert.deepEqual(Object.keys(override.error.details).sort(), Object.keys(base.error.details).sort());
  assert.deepEqual(override.error.details, base.error.details);
  assert.equal(override.error.message, base.error.message);
});

test("contract: the three caretConfirmedBy values are the base's three", async () => {
  const seen = new Set();
  for (const [script, at] of [
    [{ caret: rect(1000), click: PROCESSED }, SAME_LINE],
    [{ caret: rect(1000) }, [1000, 2150]],
    [{ caret: rect(1000), click: { at: 25, caret: rect(0, 5000) } }, [2000, 6000]],
  ]) {
    seen.add((await drive(NarrowEditorV2Session, script, at, { caretAckGraceMs: 60 })).result.caretConfirmedBy);
  }
  assert.deepEqual([...seen].sort(), ["already-at-target", "engine-acknowledged",
                                      "engine-moved-the-caret-off-the-clicked-line"]);
});
