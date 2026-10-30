// SPEC-M3-v28-last-line-fallback 4.3 items 1-2 (U-v28, client half).
//
// v28's engine reports `fallback-readback-refused` when the one-position-back fallback read something it cannot
// judge (a table before the last line, an unexpected block count).  The action was dispatched and the queue is
// open, so the disposition is review; a shape the client does not know falls to dispatched-rollback, which is
// finding 173's regression on a new name.

import assert from "node:assert/strict";
import test from "node:test";

// A namespace import on purpose: before the change the module has no such export, and the test must then fail
// at its first assertion (the witness), not at link time.
import * as client from "../paragraph-editor-client.js";

const barrier = { dispatched: true, route: "collapsed", failureShape: "fallback-readback-refused",
                  selectionResultSeen: true };
const disposition = (over) => client.formatFailureDisposition({
  code: "MUTATION_OUTCOME_UNKNOWN", details: { formatBarrier: { ...barrier, ...over } } });

test("a fallback readback the engine refused is reviewed, not rolled back", () => {
  assert.equal(disposition({}), "dispatched-unverified");
});

test("narrow: the new branch needs dispatched, collapsed and the select's own result", () => {
  assert.equal(disposition({ dispatched: false }), "refused-no-mutation");
  assert.equal(disposition({ route: "range-single" }), "dispatched-rollback");
  assert.equal(disposition({ selectionResultSeen: false }), "dispatched-rollback");
  assert.equal(disposition({ failureShape: "selection-not-restored" }), "dispatched-rollback");
});

test("the 083 names keep their disposition, and their list is unchanged", () => {
  assert.equal(disposition({ failureShape: "select-text-returned-none" }), "dispatched-unverified");
  assert.deepEqual([...client.EMPTY_SELECTION_SHAPES].sort(),
                   ["select-text-returned-none", "stage-deadline:awaiting-selection"]);
});

test("one exported list, exactly one name", () => {
  assert.deepEqual(client.FALLBACK_REFUSED_SHAPES, ["fallback-readback-refused"]);
  assert.ok(Object.isFrozen(client.FALLBACK_REFUSED_SHAPES));
});
