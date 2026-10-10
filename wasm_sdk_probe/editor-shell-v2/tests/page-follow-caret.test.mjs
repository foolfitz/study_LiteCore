// SPEC-M3-production-ui §17.4 124-U as amended by §17.9 (e): finding 124, the
// view follows the caret.  The page's own `followCaret` is taken from its
// source and run against a desk that scrolls a paper of known size, so this
// tests the page's code.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");
const FOLLOW = SOURCE.match(/^let followedCaret = null;\n\nfunction followCaret\(\) \{[\s\S]*?\n\}$/m)?.[0];

/**
 * A desk 500 px tall over a paper 20,000 px tall (padding 20), 10 twips a CSS
 * pixel.  `caret(yPx)` is a state write whose caret is at that paper pixel.
 */
function page() {
  assert.ok(FOLLOW, "followCaret() not found in the page");
  const desk = {
    scrollTop: 0, clientHeight: 500, scrollHeight: 20040,
    getBoundingClientRect: () => ({ top: 0, bottom: 500, height: 500 }),
  };
  const writes = [];
  const scrolled = new Proxy(desk, {
    set(target, key, value) { if (key === "scrollTop") writes.push(value); target[key] = value; return true; },
  });
  const el = {
    desk: scrolled,
    paper: { getBoundingClientRect: () => ({ top: 20 - desk.scrollTop, height: 20000 }) },
  };
  const session = { document: { heightTwips: 200000 }, state: { snapshot: { editorState: null } } };
  const drag = { active: false };
  // eslint-disable-next-line no-new-func
  const followCaret = new Function("session", "el", "drag", `${FOLLOW}\nreturn followCaret;`)(session, el, drag);
  return {
    desk, drag, writes,
    caret(yPx, heightPx = 18) {
      session.state.snapshot = { editorState: { caret: { x: 500, y: yPx * 10, width: 0, height: heightPx * 10 } } };
      followCaret();
    },
    /** Where the caret's middle is in the desk's view, in px from its top. */
    middle: (yPx, heightPx = 18) => 20 + yPx + heightPx / 2 - desk.scrollTop,
  };
}

test("124-U1: a caret that changed and is out of view is scrolled to the middle, once", () => {
  const p = page();
  p.caret(100);
  assert.equal(p.writes.length, 0, "a caret in view scrolled the desk");
  p.caret(900);                        // below the 500-px view
  assert.equal(p.writes.length, 1, "not exactly one scroll");
  assert.ok(Math.abs(p.middle(900) - 250) <= 1, `the caret is at ${p.middle(900)} px, not the middle (250)`);
});

test("124-U2: a caret that changed but is wholly in view does not scroll", () => {
  const p = page();
  p.caret(100);
  p.caret(300);
  p.caret(440);                        // bottom 20 + 440 + 18 = 478 <= 500
  assert.equal(p.writes.length, 0);
});

test("124-U3: an unchanged caret never scrolls -- a user who wheeled away is not pulled back", () => {
  const p = page();
  p.caret(900);
  assert.equal(p.writes.length, 1);
  p.desk.scrollTop = 5000;             // the wheel
  for (let i = 0; i < 4; i += 1) p.caret(900);   // pending, busy, pending, ready: the same caret
  assert.equal(p.writes.length, 1, "a state write with the same caret scrolled the desk back");
  assert.equal(p.desk.scrollTop, 5000);
  p.caret(918);                        // the caret moves: followed again
  assert.equal(p.writes.length, 2);
});

test("124-U4: the scroll is clamped to the desk's range", () => {
  const p = page();
  p.caret(19990, 18);                  // the paper's last line
  assert.equal(p.desk.scrollTop, 20040 - 500, "not clamped at the bottom");
  p.caret(2, 18);                      // the first line, now above the view
  assert.equal(p.desk.scrollTop, 0, "not clamped at the top");
});

test("124-U5 (§17.9 (e)): not while a pointer drag selects; the first caret after it is followed", () => {
  const p = page();
  p.caret(100);
  p.drag.active = true;
  p.caret(700);                        // the drag's selection end, out of view
  p.caret(800);
  assert.equal(p.writes.length, 0, "a drag scrolled the desk");
  p.drag.active = false;
  p.caret(800);                        // the drag's last caret, after the drag: changed since the last followed
  assert.equal(p.writes.length, 1, "the caret after the drag was not followed");
});
