// Finding 136 and L-134-restore-flash (SPEC-M3-held-key §16; fable's ruling-3 for the owner).  The
// functions are taken from the page source and run here, so these test the page's own code.  Each
// test compiles inside itself: on a page without these, it fails by name instead of the whole file
// failing to load.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
const EDITOR_ACTION = () => slice(/^async function editorAction\(action\) \{[\s\S]*?\n\}$/m, "editorAction()");
const REOPEN = () => slice(/^async function reopenAfterBoundaryRefusal\(error\) \{[\s\S]*?\n\}$/m,
                           "reopenAfterBoundaryRefusal()");
const FOLLOW = () => slice(/^function followCaret\(\) \{[\s\S]*?\n\}$/m, "followCaret()");

/** The page's editorAction with stubs; `out` resolves or rejects each action by hand. */
function makeEditorAction(session) {
  const out = [];
  // eslint-disable-next-line no-new-func
  const made = new Function("session", "run", "el", "renderDocument", `
    const SESSION_ACCEPTS = new Set(["ready", "busy"]);
    const ACTION_LABELS = {}; const FORMAT_ACTIONS = new Set(); const formatStateFor = () => null;
    let engineActionsOut = 0; let busyLeftToAction = false;
    ${slice(/^const DELETE_ACTIONS = .*;$/m, "DELETE_ACTIONS")}
    ${slice(/^const pendingDeleteCarets = \[\];$/m, "the send-time caret FIFO")}
    ${EDITOR_ACTION()}
    return { editorAction, fifo: pendingDeleteCarets };`)(
    session,
    (_label, operation) => new Promise((resolve, reject) => out.push({ resolve, reject, operation })),
    { toolbar: { querySelector: () => null } }, async () => {});
  return { ...made, out };
}

const caret = (x, y) => ({ x, y, width: 0, height: 276 });

test("136 U-136a: a delete's caret is taken when it is sent, and released when it settles", async () => {
  const session = { state: { snapshot: { state: "ready", editorState: { caret: caret(100, 200) } } } };
  const { editorAction, fifo, out } = makeEditorAction(session);
  const first = editorAction("delete-forward").catch(() => {});
  session.state.snapshot.editorState = { caret: caret(5000, 9000) };   // the barrier moved it
  const second = editorAction("delete-forward").catch(() => {});
  assert.deepEqual(fifo.map((c) => c.x), [100, 5000], "not one entry per delete, in send order");
  void editorAction("set-bold");
  assert.equal(fifo.length, 2, "a non-delete action entered the FIFO");
  out[0].reject(new Error("refused"));
  await first;
  assert.deepEqual(fifo.map((c) => c.x), [5000], "the settled delete's caret was not released first");
  out[1].resolve();
  await second;
  assert.equal(fifo.length, 0);
});

/** The page's reopenAfterBoundaryRefusal with stubs; returns the click it made and the toasts. */
async function reopenWith({ fifo, snapshotCaret, restartThrows = false, placeThrows = false, follow = [] }) {
  const clicks = [];
  const toasts = [];
  const session = {
    state: { snapshot: { state: "restart-required", dirty: true, editorState: { caret: snapshotCaret } } },
    restartAvailable: () => true,
    restartKeepsContent: () => true,
    async restart() {
      if (restartThrows) throw new Error("no");
      session.state.snapshot = { state: "ready", editorState: { caret: caret(0, 0) } };
    },
    async placeCaret(x, y) { if (placeThrows) throw new Error("no"); clicks.push([x, y]); },
  };
  const flags = [];
  // eslint-disable-next-line no-new-func
  const fn = new Function("session", "toast", "run", "rescueAtGenerationLimit", "el", "boundaryText",
                          "boundaryKeyUncertain", "pendingDeleteCarets", "followCaret", `
    ${slice(/^let reopening = false;$/m, "the reopen flag")}
    ${REOPEN()}
    return { reopenAfterBoundaryRefusal, flag: () => reopening };`)(
    session, (m) => toasts.push(m), async (_label, operation) => operation(), async () => {},
    { sink: { focus() {} } }, () => "這裡目前還不能這樣刪除", () => false, fifo,
    () => follow.push("follow"));
  const running = fn.reopenAfterBoundaryRefusal({});
  flags.push(fn.flag());
  await running.catch(() => {});
  flags.push(fn.flag());
  return { clicks, toasts, flags };
}

test("136 U-136b: the reopen clicks at the refused delete's send-time caret, not the last pushed one", async () => {
  const { clicks } = await reopenWith({ fifo: [caret(100, 200), caret(5000, 9000)], snapshotCaret: caret(7000, 9000) });
  assert.deepEqual(clicks, [[100, 200 + 138]], "not the head of the FIFO");
});

test("136 U-136c: with no delete of the page's out, the reopen reads today's snapshot caret", async () => {
  const { clicks } = await reopenWith({ fifo: [], snapshotCaret: caret(300, 400) });
  assert.deepEqual(clicks, [[300, 400 + 138]]);
});

test("flash U-flash-a: the flag is up during the reopen and down after; the explicit follow runs once", async () => {
  const follow = [];
  const { flags } = await reopenWith({ fifo: [caret(1, 2)], snapshotCaret: caret(1, 2), follow });
  assert.deepEqual(flags, [true, false]);
  assert.equal(follow.length, 1);
});

test("flash U-flash-b: a throwing restart() still lowers the flag and follows once", async () => {
  const follow = [];
  const { flags, clicks } = await reopenWith({ fifo: [caret(1, 2)], snapshotCaret: caret(1, 2), restartThrows: true, follow });
  assert.deepEqual(flags, [true, false]);
  assert.equal(follow.length, 1);
  assert.equal(clicks.length, 0);
});

// U-flash-c: the state writes reach followCaret only when the page is not reopening; followCaret itself
// is unchanged (124-U1..U5 cover it), so a skipped write cannot count as followed.
test("flash U-flash-c: a state write during the page's reopen does not reach followCaret", () => {
  const update = slice(/^function updateState\([^)]*\) \{[\s\S]*?\n\}$/m, "updateState()");
  assert.match(update, /\n  if \(!reopening\) followCaret\(\);\n\}$/, "updateState follows unconditionally");
  assert.equal((update.match(/followCaret\(\)/g) || []).length, 1, "another unguarded follow in updateState");
  slice(/^let reopening = false;$/m, "the reopen flag");
});
