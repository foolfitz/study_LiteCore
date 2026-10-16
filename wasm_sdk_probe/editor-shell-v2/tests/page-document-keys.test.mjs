// Finding 142 on the page (SPEC-M3-link-batch-v21 4.1, 9.8, 9.10; 11.1 D4, D5,
// D9): Ctrl/Cmd+Home and Ctrl/Cmd+End.
//
//   * D5 -- the binding table x (absent, both withheld, one withheld, declared)
//     with the REAL v20 manifest as "absent": the page takes the key (and
//     `preventDefault`s it) only for an action the profile offers, and never
//     with Shift, Alt or during an IME composition.  A key the page cannot
//     dispatch must not be taken: on v20 the key keeps today's behaviour;
//   * D9 -- a flagged repeat is dropped, and so is a press of the same key while
//     its move is unanswered, so a 1 s hold leaves at most one move behind;
//   * D4 -- on a range the profile does not offer the move for, the page goes
//     through finding 129's `moveFromPoint` (click at the point, then move);
//   * wiring -- the keydown handler takes the key BEFORE `if (accel) return;`,
//     and the session is built with the held deletes' `beforeEnqueue`.
//
// The functions are sliced from the page source and driven with fakes.

import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";
import { selectionShapeOf } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");
const V20 = JSON.parse(readFileSync(here("../../dist/profiles/e2-editor-v20/sdk-manifest.json"), "utf8"));

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);

/** v20's contract with the two moves as `state` says: absent, withheld ([]) or declared (collapsed). */
function manifest(start, end) {
  const m = structuredClone(V20);
  const set = (action, id, how) => {
    if (how === "absent") return;
    m.editorContract.actions[action] = { id, gestures: how === "withheld" ? [] : ["collapsed"],
                                         limits: ["no-extend-selection"] };
  };
  set("move-document-start", 22, start);
  set("move-document-end", 23, end);
  return m;
}

function clientFor(m) {
  return new NarrowEditorV2Client({ handle: 1, revision: 0, _assertUsable() {},
                                    _engine: { manifest: m, async _request() { return null; } } });
}

/** The page's key path, compiled: takeDocumentKey and what it calls. */
function keys({ m = manifest("declared", "declared"), editorState = { selection: { collapsed: true } },
                answer = () => 250, pointMovesInFlight = 0 } = {}) {
  const client = clientFor(m);
  const sent = [];
  const fromPoint = [];
  let busyUntil = null;
  const session = {
    offers: (action) => client.offers(action),
    gesturesFor: (action) => client.gesturesFor(action),
    state: { snapshot: { editorState } },
  };
  // One action at a time, as the session's queue answers them; `onResult` at the answer.
  const editorAction = (action, options = {}) => {
    sent.push({ action, t: Date.now() });
    return new Promise((resolve) => {
      const start = () => {
        const duration = answer(action, sent.length);
        busyUntil = Date.now() + duration;
        setTimeout(() => { busyUntil = null; options.onResult?.({ action }); resolve({ action }); }, duration);
      };
      if (busyUntil === null) start();
      else setTimeout(start, busyUntil - Date.now());
    });
  };
  const moveFromPoint = (action, options = {}) => {
    fromPoint.push(action);
    return editorAction(action, options);
  };
  // eslint-disable-next-line no-new-func
  const api = new Function("session", "editorAction", "moveFromPoint", "selectionShapeOf", "pointMovesInFlight", `
    let lastSelectionShape = "collapsed";
    ${slice(/^const DOCUMENT_KEY_ACTIONS = \{[^\n]*\};$/m, "DOCUMENT_KEY_ACTIONS")}
    ${slice(/^const documentMovesUnanswered = new Map\(\);$/m, "documentMovesUnanswered")}
    ${fn("documentKeyAction")}
    ${fn("dropsDocumentMove")}
    ${fn("sendDocumentMove")}
    ${fn("takeDocumentKey")}
    return { takeDocumentKey, unanswered: () => [...documentMovesUnanswered.values()].reduce((a, b) => a + b, 0) };
  `)(session, editorAction, moveFromPoint, selectionShapeOf, pointMovesInFlight);
  const press = (init) => {
    const event = { ctrlKey: false, metaKey: false, shiftKey: false, altKey: false, isComposing: false,
                    repeat: false, ...init, defaultPrevented: false,
                    preventDefault() { this.defaultPrevented = true; } };
    const taken = api.takeDocumentKey(event);
    return { taken, prevented: event.defaultPrevented };
  };
  return { press, sent, fromPoint, unanswered: api.unanswered };
}

// ------------------------------------------------------------------ D5

const STATES = [
  ["absent (the real v20 manifest)", "absent", "absent"],
  ["both withheld", "withheld", "withheld"],
  ["only start withheld", "withheld", "declared"],
  ["only end withheld", "declared", "withheld"],
  ["declared", "declared", "declared"],
];
const BINDINGS = [
  ["Ctrl+Home", { key: "Home", ctrlKey: true }, "move-document-start"],
  ["Ctrl+End", { key: "End", ctrlKey: true }, "move-document-end"],
  ["Cmd+Home", { key: "Home", metaKey: true }, "move-document-start"],
  ["Cmd+End", { key: "End", metaKey: true }, "move-document-end"],
];

test("D5: the absent state really is v20's manifest, with neither move in it", () => {
  assert.equal(Object.hasOwn(V20.editorContract.actions, "move-document-start"), false);
  assert.equal(Object.hasOwn(V20.editorContract.actions, "move-document-end"), false);
  assert.equal(V20.profile, "e2-editor-v20");
});

for (const [label, start, end] of STATES) {
  test(`D5 (${label}): only an offered move takes its key`, () => {
    const m = manifest(start, end);
    const offered = { "move-document-start": start === "declared", "move-document-end": end === "declared" };
    for (const [name, init, action] of BINDINGS) {
      const k = keys({ m });
      const { taken, prevented } = k.press(init);
      assert.equal(taken, offered[action], `${name}: taken`);
      assert.equal(prevented, offered[action], `${name}: preventDefault`);
      assert.deepEqual(k.sent.map((s) => s.action), offered[action] ? [action] : [], `${name}: sent`);
    }
  });
}

test("D5: Shift, Alt and an IME composition are never taken, even when the move is offered", () => {
  for (const [name, init] of BINDINGS) {
    for (const extra of [{ shiftKey: true }, { altKey: true }, { isComposing: true }]) {
      const k = keys();
      const { taken, prevented } = k.press({ ...init, ...extra });
      assert.equal(taken, false, `${name} ${JSON.stringify(extra)}`);
      assert.equal(prevented, false, `${name} ${JSON.stringify(extra)}`);
      assert.deepEqual(k.sent, []);
    }
  }
});

test("D5: plain Home/End and other Ctrl keys are not this binding's", () => {
  for (const init of [{ key: "Home" }, { key: "End" }, { key: "ArrowUp", ctrlKey: true },
                      { key: "PageDown", ctrlKey: true }, { key: "a", ctrlKey: true }]) {
    const k = keys();
    assert.equal(k.press(init).taken, false, JSON.stringify(init));
  }
});

// ------------------------------------------------------------------ D9

const flush = () => new Promise((resolve) => setImmediate(resolve));
async function advance(ms, step = 5) {
  for (let left = ms; left > 0; left -= step) {
    mock.timers.tick(Math.min(step, left));
    await flush();
  }
}

for (const [name, init] of [["Ctrl+Home", { key: "Home", ctrlKey: true }], ["Ctrl+End", { key: "End", ctrlKey: true }]]) {
  test(`D9 (${name}): held 1 s with flagged repeats -- one move, ready within 500 ms of release`, async () => {
    mock.timers.enable({ apis: ["setTimeout", "Date"] });
    try {
      const k = keys();   // every move is a boundary readback: 250 ms
      const schedule = [0, ...Array.from({ length: 17 }, (_, i) => 500 + 30 * i)];
      let at = 0;
      let dropped = 0;
      for (const [i, t] of schedule.entries()) {
        await advance(t - at);
        at = t;
        const { taken, prevented } = k.press({ ...init, repeat: i > 0 });
        assert.equal(taken, true);
        assert.equal(prevented, true, "a dropped repeat must still be kept from the input sink");
        if (i > 0) dropped += 1;
      }
      assert.equal(k.sent.length, 1, `${k.sent.length} moves for one held key`);
      await advance(1000 - at + 500);
      assert.equal(k.unanswered(), 0, "not ready 500 ms after the key came up");
      assert.equal(dropped, 17);
    } finally {
      mock.timers.reset();
    }
  });

  test(`D9 (${name}): unflagged presses every 30 ms for 1 s -- a move only when the last one is answered, ready within 500 ms`, async () => {
    mock.timers.enable({ apis: ["setTimeout", "Date"] });
    try {
      const k = keys();
      const schedule = Array.from({ length: 34 }, (_, i) => 30 * i);   // 0 .. 990 ms
      let at = 0;
      for (const t of schedule) {
        await advance(t - at);
        at = t;
        k.press(init);
      }
      // One out at a time: a press while the move is unanswered is dropped.
      for (let i = 1; i < k.sent.length; i += 1)
        assert.ok(k.sent[i].t - k.sent[i - 1].t >= 250, "a second move went out while one was unanswered");
      assert.ok(k.sent.length <= 5, `${k.sent.length} moves queued by one held key`);
      await advance(500);
      assert.equal(k.unanswered(), 0, "not ready 500 ms after the last press");
    } finally {
      mock.timers.reset();
    }
  });
}

test("D9: the two keys do not drop each other -- Ctrl+End while Ctrl+Home is unanswered goes out", () => {
  const k = keys();
  k.press({ key: "Home", ctrlKey: true });
  k.press({ key: "End", ctrlKey: true });
  assert.deepEqual(k.sent.map((s) => s.action), ["move-document-start", "move-document-end"]);
});

// ------------------------------------------------------------------ D4

test("D4: on a range the move goes through moveFromPoint (click at the point, then move)", () => {
  for (const rectangles of [[{}], [{}, {}]]) {
    const k = keys({ editorState: { selection: { collapsed: false, rectangles } } });
    k.press({ key: "End", ctrlKey: true });
    assert.deepEqual(k.fromPoint, ["move-document-end"], `${rectangles.length} rectangle(s)`);
  }
});

test("D4: on a caret, or while a point move is already queued, the move goes straight out", () => {
  const caret = keys();
  caret.press({ key: "Home", ctrlKey: true });
  assert.deepEqual(caret.fromPoint, []);
  assert.deepEqual(caret.sent.map((s) => s.action), ["move-document-start"]);
  const queued = keys({ editorState: { selection: { collapsed: false, rectangles: [{}] } }, pointMovesInFlight: 1 });
  queued.press({ key: "Home", ctrlKey: true });
  assert.deepEqual(queued.fromPoint, []);
});

// ------------------------------------------------------------------ wiring

test("wiring: the keydown handler takes the document keys BEFORE `if (accel) return;`", () => {
  const handler = slice(/^el\.sink\.addEventListener\("keydown", \(event\) => \{[\s\S]*?\n\}\);$/m, "the keydown handler");
  const take = handler.indexOf("if (takeDocumentKey(event)) return;");
  const bail = handler.indexOf("if (accel) return;");
  assert.ok(take > 0, "the keydown handler does not call takeDocumentKey");
  assert.ok(bail > take, "takeDocumentKey runs after the accel bail-out, so it never sees Ctrl+Home");
});

test("wiring: both moves have a label (editorAction names a failure by it)", () => {
  const labels = slice(/^const ACTION_LABELS = \{[\s\S]*?\n\};$/m, "ACTION_LABELS");
  assert.match(labels, /"move-document-start": "移到文件開頭"/);
  assert.match(labels, /"move-document-end": "移到文件結尾"/);
});

test("wiring: the page builds its session with the held deletes' beforeEnqueue (§10.3 rule 4)", () => {
  const construction = slice(/session = new NarrowEditorV2Session\(\{[\s\S]*?\n {2}\}\);/, "the session construction");
  assert.match(construction, /\n\s+beforeEnqueue: releaseHeldDeletesBeforeEnqueue,\n/);
});
