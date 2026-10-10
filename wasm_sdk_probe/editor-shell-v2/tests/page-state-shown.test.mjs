// SPEC-M3-production-ui §17.4 125-U as amended by §17.9 (d): finding 125, the
// owner's A.  The page's own `installStateShown` and `showState` are taken
// from its source and run on a fake clock against a fake `#state-pill`, so
// this tests the page's code.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");
const PART = SOURCE.match(/^const BUSY_SHOWN_AFTER_MS = [\s\S]*?\nfunction showState\([^)]*\) \{[\s\S]*?\n\}$/m)?.[0];

function element(tag) {
  const classes = new Set();
  const node = {
    tag, id: "", dataset: {}, children: [], _text: "",
    get className() { return [...classes].join(" "); },
    set className(v) { classes.clear(); for (const c of String(v).split(/\s+/).filter(Boolean)) classes.add(c); },
    classList: { remove: (c) => classes.delete(c), contains: (c) => classes.has(c) },
    get textContent() { return node.children.length ? node.children.map((c) => c.textContent).join("") : node._text; },
    set textContent(v) { node.children = []; node._text = String(v); },
    replaceChildren(...kids) { node.children = kids; node._text = ""; },
  };
  return node;
}

/** The page's pill on a clock that moves only when told to. */
function page() {
  assert.ok(PART, "the 125 code (BUSY_SHOWN_AFTER_MS .. showState) not found in the page");
  let now = 0, next = 1;
  const timers = new Map();
  const clock = {
    setTimeout: (f, ms) => { const id = next++; timers.set(id, [now + ms, f]); return id; },
    clearTimeout: (id) => { timers.delete(id); },
    advance(ms) {
      const until = now + ms;
      for (;;) {
        const due = [...timers.entries()].filter(([, [at]]) => at <= until).sort((a, b) => a[1][0] - b[1][0])[0];
        if (!due) break;
        timers.delete(due[0]);
        now = due[1][0];
        due[1][1]();
      }
      now = until;
    },
  };
  const pill = element("span");
  pill.id = "state-pill";
  pill.className = "pill";
  pill.dataset.state = "loading";
  pill.textContent = "啟動中";
  const el = { statePill: pill };
  const document = { createElement: element };
  // eslint-disable-next-line no-new-func
  const made = new Function("el", "document", "setTimeout", "clearTimeout",
    `${PART}\nreturn { showState, stateShown };`)(el, document, clock.setTimeout, clock.clearTimeout);
  const shownLog = [];
  const write = (state, label) => {
    made.showState(state, label);
    shownLog.push(made.stateShown.textContent);
  };
  return { ...made, pill, clock, write, shownLog, shown: () => made.stateShown };
}

test("125-U1: busy for 699 ms and then not -- the shown pill never says 處理中", () => {
  const p = page();
  p.write("ready", "就緒");
  p.write("busy", "處理中");
  p.clock.advance(699);
  assert.equal(p.shown().textContent, "就緒", "the shown pill changed before 700 ms of busy");
  p.write("ready", "就緒");
  p.clock.advance(5000);
  assert.ok(!p.shownLog.includes("處理中") && p.shown().textContent === "就緒", "處理中 was shown");
});

test("125-U2: busy that lasts shows 處理中 at exactly 700 ms", () => {
  const p = page();
  p.write("ready", "就緒");
  p.write("busy", "處理中");
  p.write("busy", "處理中");          // more busy writes do not restart the wait
  p.clock.advance(699);
  assert.equal(p.shown().textContent, "就緒");
  p.clock.advance(1);
  assert.equal(p.shown().textContent, "處理中");
  assert.equal(p.shown().dataset.state, "busy");
});

test("125-U3: leaving busy shows the new state at once; every other state at once", () => {
  const p = page();
  p.write("busy", "處理中");
  p.clock.advance(800);
  assert.equal(p.shown().textContent, "處理中");
  p.write("recoverable-error", "需要回復");
  assert.equal(p.shown().textContent, "需要回復");
  assert.equal(p.shown().dataset.state, "recoverable-error");
  for (const [state, label] of [["ready", "就緒"], ["restart-required", "需要重新開啟"], ["expired", "已過期"], ["stopped", "錯誤"]]) {
    p.write(state, label);
    assert.equal(p.shown().textContent, label);
  }
});

test("125-U4: #state-pill's data-state and data-label are written at once, every write", () => {
  const p = page();
  for (const [state, label] of [["ready", "就緒"], ["busy", "處理中"], ["ready", "就緒"], ["busy", "處理中"]]) {
    p.write(state, label);
    assert.equal(p.pill.dataset.state, state, "the machine-read state lagged");
    assert.equal(p.pill.dataset.label, label);
  }
});

test("125-U5: never blank, and a direct write (已過期, 錯誤) cancels the wait", () => {
  const p = page();
  assert.equal(p.shown().textContent, "啟動中", "the shown pill did not start with the page's own word");
  p.write("busy", "處理中");
  assert.equal(p.shown().textContent, "啟動中", "blank or changed during the wait");
  p.write("expired", "已過期");
  p.clock.advance(5000);
  assert.equal(p.shown().textContent, "已過期", "a pending 處理中 overwrote 已過期");
});

test("125-U6: the class pill is on the child, not on #state-pill; the child is #state-pill's only content", () => {
  const p = page();
  assert.equal(p.pill.classList.contains("pill"), false, "#state-pill kept class pill");
  assert.equal(p.shown().className, "pill");
  assert.equal(p.shown().id, "state-shown");
  assert.deepEqual(p.pill.children, [p.shown()]);
});
