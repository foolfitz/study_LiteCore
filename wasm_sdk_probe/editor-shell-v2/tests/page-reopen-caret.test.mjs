// Finding 136 and L-134-restore-flash (SPEC-M3-held-key §16; fable's ruling-3 for the owner, addendum 4).  The
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
const REOPEN = () => slice(/^async function reopenAfterBoundaryRefusal\(error\) \{[\s\S]*?\n\}$/m,
                           "reopenAfterBoundaryRefusal()");

const caret = (x, y) => ({ x, y, width: 0, height: 276 });
const collapsed = (c) => ({ caret: c, selection: { collapsed: true } });
const range = (c) => ({ caret: c, selection: { collapsed: false, rectangles: [{}] } });

// Ruling-3 addendum 4: the caret D puts back is the last one the engine pushed with no range selected.
test("136 U-136a: a range push is skipped; a collapsed or a selection-less push is noted", () => {
  // eslint-disable-next-line no-new-func
  const made = new Function(`
    ${slice(/^let lastCollapsedCaret = null;$/m, "the last collapsed caret")}
    ${slice(/^function noteCollapsedCaret\([^)]*\) \{[\s\S]*?\n\}$/m, "noteCollapsedCaret()")}
    return { noteCollapsedCaret, last: () => lastCollapsedCaret };`)();
  made.noteCollapsedCaret(collapsed(caret(100, 200)));
  made.noteCollapsedCaret(range(caret(5000, 9000)));            // K1's one unit, into the next cell
  assert.equal(made.last().x, 100, "a range push replaced the caret");
  made.noteCollapsedCaret({ caret: caret(300, 400) });          // nothing-selected: no range at all
  assert.equal(made.last().x, 300);
  made.noteCollapsedCaret(collapsed({ x: NaN, y: 1, height: 1 }));
  made.noteCollapsedCaret(null);
  assert.equal(made.last().x, 300, "a push without a finite caret replaced it");
  const update = slice(/^function updateState\([^)]*\) \{[\s\S]*?\n\}$/m, "updateState()");
  assert.match(update, /noteCollapsedCaret\(snapshot\.editorState\);/, "updateState does not note the caret");
});

/** The page's reopenAfterBoundaryRefusal with stubs; returns the click it made and the toasts. */
async function reopenWith({ last, snapshotCaret, restartThrows = false, placeThrows = false, follow = [] }) {
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
                          "boundaryKeyUncertain", "lastCollapsedCaret", "followCaret", `
    ${slice(/^let reopening = false;$/m, "the reopen flag")}
    ${REOPEN()}
    return { reopenAfterBoundaryRefusal, flag: () => reopening };`)(
    session, (m) => toasts.push(m), async (_label, operation) => operation(), async () => {},
    { sink: { focus() {} } }, () => "這裡目前還不能這樣刪除", () => false, last,
    () => follow.push("follow"));
  const running = fn.reopenAfterBoundaryRefusal({});
  flags.push(fn.flag());
  await running.catch(() => {});
  flags.push(fn.flag());
  return { clicks, toasts, flags };
}

test("136 U-136b: the reopen clicks at the last collapsed caret, not the barrier's pushed one", async () => {
  const { clicks } = await reopenWith({ last: caret(100, 200), snapshotCaret: caret(7000, 9000) });
  assert.deepEqual(clicks, [[100, 200 + 138]], "not the last collapsed caret");
});

test("136 U-136c: with none noted, the reopen reads today's snapshot caret", async () => {
  const { clicks } = await reopenWith({ last: null, snapshotCaret: caret(300, 400) });
  assert.deepEqual(clicks, [[300, 400 + 138]]);
});

test("flash U-flash-a: the flag is up during the reopen and down after; the explicit follow runs once", async () => {
  const follow = [];
  const { flags } = await reopenWith({ last: caret(1, 2), snapshotCaret: caret(1, 2), follow });
  assert.deepEqual(flags, [true, false]);
  assert.equal(follow.length, 1);
});

test("flash U-flash-b: a throwing restart() still lowers the flag and follows once", async () => {
  const follow = [];
  const { flags, clicks } = await reopenWith({ last: caret(1, 2), snapshotCaret: caret(1, 2), restartThrows: true, follow });
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
