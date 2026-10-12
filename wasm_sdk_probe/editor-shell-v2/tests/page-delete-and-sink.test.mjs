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
// eslint-disable-next-line no-new-func
const syncSinkToInput = new Function(
  `${slice(/^function syncSinkToInput\([^)]*\) \{[\s\S]*?\n\}$/m, "syncSinkToInput()")}\nreturn syncSinkToInput;`)();

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

// SPEC-M3-autosave §9.12, rule A.  While a delete this page sent has not
// settled, the engine's range is the barrier's one-character selection, not the
// user's: the key keeps its own collapsed form.
test("finding 131: while a delete this page sent is unsettled, the key keeps its collapsed form", () => {
  for (const action of ["delete-backward", "delete-forward"]) {
    assert.equal(deleteActionFor(action, "range-single", true, 1), action, action);
    assert.equal(deleteActionFor(action, "range-cross", true, 3), action, action);
    // None out: finding 121's rule stands.
    assert.equal(deleteActionFor(action, "range-single", true, 0), "delete-selection", action);
  }
});

test("finding 131: the handler passes its own unsettled deletes, counted before the call and released in finally", () => {
  const handler = slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler");
  assert.match(handler, /deleteActionFor\(action, shape,\s+session\.offers\?\.\("delete-selection"\) === true, deletesInFlight\)/);
  assert.match(handler, /deletesInFlight \+= 1;\n\s+void editorAction\(/);
  assert.match(handler, /\.finally\(\(\) => \{ deletesInFlight -= 1; \}\)/);
  // Its own counter, not every action out: a real range + Ctrl+B + Backspace is still delete-selection.
  assert.doesNotMatch(handler, /engineActionsOut/);
  assert.match(SOURCE, /^let deletesInFlight = 0;$/m);
});

test("finding 120: the sink follows the new adapter's blocked state", () => {
  const sink = { disabled: true };
  syncSinkToInput(sink, { state: { blocked: false } });
  assert.equal(sink.disabled, false, "a sink a stopped session left disabled stays disabled");
  syncSinkToInput(sink, { state: { blocked: true } });
  assert.equal(sink.disabled, true);
});

test("finding 120: openDocument syncs the sink right after attaching it", () => {
  assert.match(SOURCE, /session\.attachInput\(el\.sink\);\n\s+syncSinkToInput\(el\.sink, session\.input\);/);
});

// SPEC-M3-held-key §5.1 (finding 132).  Compiled inside each test: on a page
// without these, the test fails by name instead of the whole file failing to load.
const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
const heldRepeatSource = () => [
  slice(/^const HELD_DELETE_DEPTH = .*;$/m, "HELD_DELETE_DEPTH"),
  slice(/^function dropsHeldRepeat\([^)]*\) \{[\s\S]*?\n\}$/m, "dropsHeldRepeat()"),
].join("\n");

// U3 (H2): a held key does not outrun the engine.
test("132 U3: a repeat is dropped only while two deletes are out; a press, a composition, another key never", () => {
  // eslint-disable-next-line no-new-func
  const dropsHeldRepeat = new Function(`${heldRepeatSource()}\nreturn dropsHeldRepeat;`)();
  const key = (name, repeat, isComposing = false) => ({ key: name, repeat, isComposing });
  for (const name of ["Backspace", "Delete"]) {
    for (const depth of [0, 1, 2, 3, 10]) {
      assert.equal(dropsHeldRepeat(key(name, false), depth), false, `a press of ${name} at depth ${depth}`);
      assert.equal(dropsHeldRepeat(key(name, true, true), depth), false, `a composing ${name} at depth ${depth}`);
    }
    assert.equal(dropsHeldRepeat(key(name, true), 0), false, `${name} repeat at depth 0`);
    assert.equal(dropsHeldRepeat(key(name, true), 1), false, `${name} repeat at depth 1`);
    assert.equal(dropsHeldRepeat(key(name, true), 2), true, `${name} repeat at depth 2`);
    assert.equal(dropsHeldRepeat(key(name, true), 5), true, `${name} repeat at depth 5`);
  }
  for (const other of ["ArrowLeft", "a", "Enter"])
    assert.equal(dropsHeldRepeat(key(other, true), 5), false, other);
});

// U4 (H2): what the page registers on the sink does that, at its own count.
test("132 U4: the sink's keydown listener prevents exactly the repeats U3 drops, at the page's own count", () => {
  const listeners = [];
  // eslint-disable-next-line no-new-func
  const made = new Function("el", `let deletesInFlight = 0;
     ${heldRepeatSource()}
     ${slice(/^function skipHeldRepeat\([^)]*\) \{[\s\S]*?\n\}$/m, "skipHeldRepeat()")}
     ${slice(/^el\.sink\.addEventListener\("keydown", skipHeldRepeat\);$/m, "the keydown registration")}
     return { set(n) { deletesInFlight = n; } };`)({ sink: { addEventListener: (type, l) => listeners.push([type, l]) } });
  const key = (repeat, name = "Backspace") => {
    let prevented = false;
    for (const [type, listener] of listeners)
      if (type === "keydown") listener({ key: name, repeat, isComposing: false, preventDefault() { prevented = true; } });
    return prevented;
  };
  made.set(2);
  assert.equal(key(true), true, "a repeat at depth 2 went out");
  assert.equal(key(false), false, "a press at depth 2 was taken");
  assert.equal(key(true, "ArrowLeft"), false, "another key was taken");
  made.set(1);
  assert.equal(key(true), false, "a repeat at depth 1 was taken");
});

// U6 (H3): a range that arrives while a delete is out is drawn once the page's
// deletes have all settled -- the listener repaints the overlay then.
test("132 U6: the delete listener repaints the overlay once its deletes have all settled, not before", async () => {
  const listeners = [];
  const paints = [];
  const pending = [];
  const session = { document: {}, offers: () => true,
                    state: { snapshot: { editorState: { selection: { collapsed: true } } } } };
  // eslint-disable-next-line no-new-func
  const made = new Function("el", "session", "selectionShapeOf", "editorAction", "paint",
    `${slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES")}
     let lastSelectionShape = "collapsed"; let deletesInFlight = 0;
     ${slice(/^function deleteActionFor\([^)]*\) \{[\s\S]*?\n\}$/m, "deleteActionFor()")}
     ${slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler")}
     return { count: () => deletesInFlight };`)(
    { sink: { addEventListener: (type, l) => listeners.push([type, l]) } }, session, selectionShapeOf,
    () => new Promise((resolve) => pending.push(resolve)), () => paints.push(1));
  const input = () => {
    for (const [type, listener] of listeners)
      if (type === "beforeinput") listener({ inputType: "deleteContentBackward", preventDefault() {} });
  };
  input();
  input();
  assert.equal(made.count(), 2);
  pending[0]();
  await settle();
  assert.equal(made.count(), 1);
  assert.equal(paints.length, 0, "repainted while a delete was still out");
  pending[1]();
  await settle();
  assert.equal(made.count(), 0);
  assert.equal(paints.length, 1, "not repainted once every delete had settled");
});
