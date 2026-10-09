// SPEC-M3-production-ui §15.2: findings 121 (a delete on a selection) and 120
// (the input sink after a stopped session).  The functions are taken from the
// page source and run here, so these test the page's own code.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { selectionShapeOf } from "../narrow-editor-v2-session.js";

const SOURCE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}

// eslint-disable-next-line no-new-func
const deleteActionFor = new Function(
  `${slice(/^function deleteActionFor\([^)]*\) \{[\s\S]*?\n\}$/m, "deleteActionFor()")}\nreturn deleteActionFor;`)();

test("finding 121: a range goes out as delete-selection when the profile offers it", () => {
  for (const action of ["delete-backward", "delete-forward"]) {
    assert.equal(deleteActionFor(action, "range-single", true), "delete-selection", action);
    assert.equal(deleteActionFor(action, "range-cross", true), "delete-selection", action);
  }
});

test("finding 121: a caret, an unknown shape, or no offer keeps today's action", () => {
  for (const action of ["delete-backward", "delete-forward"]) {
    assert.equal(deleteActionFor(action, "collapsed", true), action);
    assert.equal(deleteActionFor(action, null, true), action);
    assert.equal(deleteActionFor(action, "range-single", false), action);
  }
});

test("finding 121: the handler asks the engine's current selection, the page's belief only as fallback", () => {
  const handler = slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler");
  assert.match(handler, /selectionShapeOf\(\{ state: session\.state\.snapshot\.editorState \}\) \?\? lastSelectionShape/);
  assert.match(handler, /deleteActionFor\(action, shape,/);
  // The accessor the handler relies on reads the snapshot's shape as the page holds it.
  assert.equal(selectionShapeOf({ state: { selection: { collapsed: true } } }), "collapsed");
  assert.equal(selectionShapeOf({ state: { selection: { collapsed: false, rectangles: [{}] } } }), "range-single");
  assert.equal(selectionShapeOf({ state: undefined }), null);
});
