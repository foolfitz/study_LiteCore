// Finding 079: the shape of a selection, derived from the result that
// describes it -- and the reason this file exists at all.
//
// The product page used to derive the shape inline, from `result.collapsed` and
// `result.rectangles`. Those are the fields `editor-shell/editor-client.js`
// assembles on the V1 path. The v2 client returns the worker's envelope
// verbatim and the selection sits at `state.selection`, so both reads were
// `undefined` and the page computed "collapsed" for every drag ever made. No
// test could have failed, because there was nothing under test.
//
// THE FIXTURES ARE REAL. Both envelopes below are trimmed from what
// `session.selectRange()` actually resolved to on the shipped e2-editor-v7
// page on 2026-08-23, recorded by mirroring the page with one added statement
// (`tools/probe_079_selection_shape.py --capture-result`, kept at
// findings/evidence/f079-the-shape-was-never-read/what-selectrange-resolves-to.json).
// A fixture I invented would only prove this accessor correct on shapes I had
// already thought of -- which is exactly how a parser was wrong four times in
// one day here.

import { test } from "node:test";
import assert from "node:assert/strict";
import { selectionShapeOf, selectionShapeEvidence }
  from "../narrow-editor-v2-session.js";

// Recorded: a drag inside one line. 12 code points selected per the engine.
const WITHIN_ONE_LINE = {
  method: "text-handles-unstable",
  revision: 0,
  completion: "documented-callback-text-selection",
  callbackSequenceBefore: 9,
  callbackSequenceAfter: 10,
  state: {
    sourceSequence: 10,
    documentChangeSequence: 0,
    visible: true,
    caret: { x: 2861, y: 3184, width: 0, height: 348 },
    selection: {
      observed: true,
      collapsed: false,
      start: { x: 1995, y: 3184, width: 0, height: 347 },
      end: { x: 2861, y: 3184, width: 0, height: 347 },
      rectangles: [{ x: 1995, y: 3184, width: 1786, height: 347 }],
    },
  },
};

// Recorded: a drag across two lines. 34 code points, three rectangles.
const ACROSS_TWO_LINES = {
  method: "text-handles-unstable",
  revision: 0,
  completion: "documented-callback-text-selection",
  callbackSequenceBefore: 11,
  callbackSequenceAfter: 12,
  state: {
    selection: {
      observed: true,
      collapsed: false,
      rectangles: [{ x: 1, y: 1 }, { x: 2, y: 2 }, { x: 3, y: 3 }],
    },
  },
};

const COLLAPSED = {
  method: "text-handles-unstable",
  revision: 0,
  state: { selection: { observed: true, collapsed: true, rectangles: [] } },
};

test("a real within-line envelope is a range-single", () => {
  assert.equal(selectionShapeOf(WITHIN_ONE_LINE), "range-single");
});

test("a real cross-line envelope is a range-cross", () => {
  assert.equal(selectionShapeOf(ACROSS_TWO_LINES), "range-cross");
});

test("a collapsed selection is collapsed", () => {
  assert.equal(selectionShapeOf(COLLAPSED), "collapsed");
});

test("THE DEFECT: the v1 field names at the top level are NOT read as an answer", () => {
  // This is finding 079 written as a test. Before the fix the page read these
  // two names off the envelope, found nothing, and answered "collapsed".
  // Anything shaped like the v1 result must come back null -- unknown -- and
  // never as a shape, because a caller that gets "collapsed" here cannot tell
  // it from a genuinely empty selection.
  const v1Shaped = { collapsed: false, rectangles: [{ x: 1 }], text: "hello" };
  assert.equal(selectionShapeOf(v1Shaped), null);
});

test("an envelope with no selection at all is unknown, not collapsed", () => {
  assert.equal(selectionShapeOf({ method: "x", revision: 3, state: {} }), null);
  assert.equal(selectionShapeOf({ method: "x", revision: 3 }), null);
});

test("a non-boolean collapsed is unknown, not a shape", () => {
  // `collapsed: "false"` and `collapsed: 0` are the shapes a serialisation
  // change produces, and both are truthy/falsy in ways that would silently pick
  // a branch. The type test is what refuses them.
  for (const value of ["false", "true", 0, 1, null, undefined]) {
    assert.equal(
      selectionShapeOf({ state: { selection: { collapsed: value } } }), null,
      `collapsed: ${JSON.stringify(value)} must be unknown`);
  }
});

test("null, undefined and primitives are unknown rather than throwing", () => {
  for (const value of [null, undefined, 0, "", "collapsed", true]) {
    assert.equal(selectionShapeOf(value), null);
  }
});

test("a range with no rectangles array is range-single, not a crash", () => {
  assert.equal(
    selectionShapeOf({ state: { selection: { collapsed: false } } }),
    "range-single");
});

test("the evidence names the keys and carries no document text", () => {
  const evidence = selectionShapeEvidence(WITHIN_ONE_LINE);
  assert.match(evidence, /callbackSequenceAfter/);
  assert.match(evidence, /state:/);
  assert.match(evidence, /selection/);
  // The envelope's `state` can carry the focused paragraph's text on a profile
  // that projects it. A diagnostic attribute on a public DOM node is not a
  // place to put a user's paragraph.
  assert.ok(!evidence.includes("text-handles-unstable"),
            "values must not travel, only key names");
});

test("the evidence survives the shapes that produce it", () => {
  assert.equal(selectionShapeEvidence(null), "null");
  assert.equal(selectionShapeEvidence(undefined), "undefined");
  assert.equal(selectionShapeEvidence(42), "number");
  assert.equal(selectionShapeEvidence({ a: 1, b: 2 }), "a,b");
});
