// Finding 141 (task 2026-10-14o; the owner chose A).  At a C boundary every
// Backspace/Delete press used to queue one 2.26 s `verified-boundary-noop`, so
// a held key whose repeats arrive unflagged, or a user pressing again, sat the
// editor in 「處理中」 for N × 2.26 s (measured 18 presses → 40.6 s,
// findings/evidence/host-0.2.20-hand-test/).  The page now HOLDS a same-key
// press while its delete is unanswered, drops the held presses when the engine
// answers a standing boundary no-op, and delivers them again (through the same
// listener) otherwise -- finding 131's press-for-press rule for real deletes.
//
// The listener and its helpers are taken from the page source and driven here
// against a fake engine that answers one action at a time, as the session's
// queue does, on mocked time.  `PAGE_SOURCE=<path>` runs the same tests against
// another copy of the page: on the page before this change (`53019168…`) T1 is
// red -- 18 requests, ready after 40.5 s -- which is the witness kept in
// findings/evidence/host-0.2.21/.

import assert from "node:assert/strict";
import { mock, test } from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { selectionShapeOf } from "../narrow-editor-v2-session.js";

const here = (relative) => fileURLToPath(new URL(relative, import.meta.url));
const SOURCE = readFileSync(process.env.PAGE_SOURCE || here("../../web/e2-editor-app.js"), "utf8");

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}
const optional = (pattern) => (SOURCE.match(pattern) || [""])[0];
const fn = (name) => new RegExp(`^function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m");

const CARET = Object.freeze({ x: 1418, y: 1418, width: 0, height: 368 });
const WINDOW_MS = 2250;      // the engine's 250 + 2,000 ms window at a C boundary (§10.5)
const DELETE_MS = 66;        // a verified delete inside text (finding 132's measurement)
const REPAINT_MS = 10;       // what run() awaits after the answer before the listener's promise settles

/** One keydown schedule of a held key: the press, then a repeat every 30 ms from 500 ms on, for 1 s. */
const HELD_KEY_MS = [0, ...Array.from({ length: 17 }, (_, i) => 500 + 30 * i)];

class InputEvent {
  constructor(type, init = {}) { this.type = type; this.inputType = init.inputType; this.defaultPrevented = false; }
  preventDefault() { this.defaultPrevented = true; }
}

/** The page's listener compiled with a fake session whose engine answers serially on mocked time. */
function page({ answer }) {
  const listeners = [];
  const sink = {
    addEventListener: (type, l) => listeners.push([type, l]),
    dispatchEvent(event) { for (const [type, l] of listeners) if (type === event.type) l(event); return !event.defaultPrevented; },
  };
  const state = { caret: { ...CARET }, selection: { collapsed: true, rectangles: [] }, revision: 0 };
  const session = { document: { id: 1 }, offers: () => true, state: { snapshot: { editorState: state } } };
  const requests = [];
  const answers = [];
  const paints = [];
  let busyUntil = null;      // the fake queue: one action at a time
  const now = () => Date.now();
  function editorAction(sent, options = {}) {
    const request = { sent, t: now() };
    requests.push(request);
    return new Promise((resolve, reject) => {
      const start = () => {
        const reply = answer(sent, state, requests.length);
        const duration = reply.duration ?? WINDOW_MS;
        busyUntil = now() + duration;
        setTimeout(() => {
          busyUntil = null;
          answers.push({ sent, t: now(), reply });
          if (reply.reject) { reject(reply.reject); return; }
          if (reply.mutate) reply.mutate(state);
          const result = reply.result(state);
          if (options.onResult) options.onResult(result);
          setTimeout(() => resolve(result), REPAINT_MS);
        }, duration);
      };
      if (busyUntil === null) start();
      else setTimeout(start, busyUntil - now());
    });
  }
  // eslint-disable-next-line no-new-func
  const api = new Function("el", "session", "selectionShapeOf", "editorAction", "paint", "InputEvent", `
    ${slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES")}
    let lastSelectionShape = "collapsed"; let deletesInFlight = 0; let deleteRefusedThisHold = false;
    ${optional(/^let deletesUnanswered = 0;$/m)}
    ${optional(/^const heldDeletes = \{[^\n]*\};$/m)}
    ${optional(/^const DELETE_INPUT_TYPE_OF = [\s\S]*?\]\)\);$/m)}
    ${slice(fn("deleteActionFor"), "deleteActionFor()")}
    ${["deleteStateOf", "boundaryNoopStands", "holdsDelete", "dropHeldDeletes", "releaseHeldDelete", "settleDelete"]
      .map((name) => optional(fn(name))).join("\n")}
    ${slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler")}
    return { inFlight: () => deletesInFlight,
             held: () => (typeof heldDeletes === "object" ? heldDeletes.count : null),
             refused: () => deleteRefusedThisHold };
  `)({ sink }, session, selectionShapeOf, editorAction, () => paints.push(now()), InputEvent);
  const press = (inputType = "deleteContentBackward") => sink.dispatchEvent(new InputEvent("beforeinput", { inputType }));
  return { api, press, requests, answers, paints, state, session };
}

/** A boundary no-op: nothing changed, the state as it was. */
const NOOP = () => ({
  duration: WINDOW_MS,
  result: (state) => ({ action: "delete-backward", beforeRevision: state.revision, revision: state.revision, changed: false,
                        completion: "verified-boundary-noop", boundaryNoop: { waitedMs: WINDOW_MS },
                        state: { caret: { ...state.caret }, selection: { ...state.selection } } }),
});
/** A real delete inside text: one character gone, the caret one step left, the revision up. */
const REAL = () => ({
  duration: DELETE_MS,
  mutate: (state) => { state.caret = { ...state.caret, x: state.caret.x - 100 }; state.revision += 1; },
  result: (state) => ({ action: "delete-backward", beforeRevision: state.revision - 1, revision: state.revision, changed: true,
                        completion: "verified-selection-delete",
                        state: { caret: { ...state.caret }, selection: { ...state.selection } } }),
});

const flush = () => new Promise((resolve) => setImmediate(resolve));
async function advance(ms, step = 10) {
  for (let left = ms; left > 0; left -= step) {
    mock.timers.tick(Math.min(step, left));
    await flush();
  }
}
async function pressAt(p, schedule, inputType) {
  let at = 0;
  for (const t of schedule) {
    await advance(t - at);
    at = t;
    p.press(inputType);
  }
}

test("141 T1: a held key at a C boundary -- 18 unflagged presses in one second -- is ONE engine request, ready within 2.5 s", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => NOOP() });
    const t0 = Date.now();
    await pressAt(p, HELD_KEY_MS);
    assert.equal(p.requests.length, 1, "more than one delete went out for presses the first one answers");
    await advance(2500 - (Date.now() - t0));
    assert.equal(p.requests.length, 1);
    assert.equal(p.api.inFlight(), 0, "not ready 2.5 s after the first press");
    assert.equal(p.api.held(), 0, "presses still held after the no-op");
    assert.equal(p.paints.length, 1, "the overlay was not repainted once after the no-op");
    await advance(45000);
    assert.equal(p.requests.length, 1, "a held press went out later");
    assert.equal(p.answers[0].reply.duration, WINDOW_MS);
  } finally {
    mock.timers.reset();
  }
});

test("141 T2 (control, finding 131): the same 18 presses inside text are 18 deletes, press for press, each out at the previous answer", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => REAL() });
    await pressAt(p, HELD_KEY_MS);
    await advance(18 * (DELETE_MS + REPAINT_MS) + 500);
    assert.equal(p.requests.length, 18, "a press that could change the document was not sent");
    assert.equal(p.state.revision, 18);
    assert.equal(p.api.inFlight(), 0);
    assert.equal(p.api.held(), 0);
    // Throughput: a press that was held goes out AT the previous answer, before its repaint (132's depth);
    // a press that found nothing unanswered went out as it was pressed.
    let held = 0;
    for (let k = 1; k < 18; k++) {
      if (p.requests[k].t === HELD_KEY_MS[k]) continue;
      held += 1;
      assert.equal(p.requests[k].t, p.answers[k - 1].t, `press ${k + 1} waited for the repaint of press ${k}`);
    }
    assert.ok(held >= 10, `only ${held} of the 17 repeats were held behind an unanswered delete`);
  } finally {
    mock.timers.reset();
  }
});

test("141 T3a (control): once the caret has moved, the next press at the old boundary is sent", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => NOOP() });
    await pressAt(p, [0, 100, 200]);
    await advance(2500);
    assert.equal(p.requests.length, 1);
    // The user clicked elsewhere: the engine pushed a new caret.
    p.state.caret = { ...p.state.caret, y: p.state.caret.y + 5000 };
    p.press();
    await advance(2500);
    assert.equal(p.requests.length, 2, "a press after the caret moved was not sent");
  } finally {
    mock.timers.reset();
  }
});

test("141 T3b (control): a no-op whose returned state differs from the sent state releases the held presses", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => ({
      ...NOOP(),
      // the reply's caret is not where the delete was sent from (a K1 that moved it)
      result: (state) => ({ ...NOOP().result(state), state: { caret: { ...state.caret, x: state.caret.x + 10 }, selection: { collapsed: true } } }),
    }) });
    await pressAt(p, [0, 100, 200]);
    await advance(3 * (WINDOW_MS + REPAINT_MS) + 500);
    assert.equal(p.requests.length, 3, "held presses were dropped on an answer whose state had moved");
  } finally {
    mock.timers.reset();
  }
});

test("141 T3c (control): a no-op reply without a readable state releases the held presses (fail closed towards 131)", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => ({ ...NOOP(), result: (state) => ({ ...NOOP().result(state), state: {} }) }) });
    await pressAt(p, [0, 100, 200]);
    await advance(3 * (WINDOW_MS + REPAINT_MS) + 500);
    assert.equal(p.requests.length, 3);
  } finally {
    mock.timers.reset();
  }
});

test("141 T3d: a refused delete drops the held presses and marks the hold refused (134 B)", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const refusal = Object.assign(new Error("refused"), { code: "EDITOR_BOUNDARY_UNSUPPORTED" });
    const p = page({ answer: () => ({ duration: 250, reject: refusal, result: () => null }) });
    await pressAt(p, [0, 100, 200]);
    await advance(1000);
    assert.equal(p.requests.length, 1);
    assert.equal(p.api.held(), 0);
    assert.equal(p.api.refused(), true);
    assert.equal(p.api.inFlight(), 0);
  } finally {
    mock.timers.reset();
  }
});

test("141 T3e: a Delete press while a Backspace is unanswered is not held (another key)", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => NOOP() });
    p.press("deleteContentBackward");
    await advance(100);
    p.press("deleteContentForward");
    await advance(100);
    assert.equal(p.requests.length, 2);
    assert.deepEqual(p.requests.map((r) => r.sent), ["delete-backward", "delete-forward"]);
  } finally {
    mock.timers.reset();
  }
});

test("141 T4: flagged repeats still obey H2 at the keydown -- dropped at depth 2, taken at depth 1", () => {
  const listeners = [];
  // eslint-disable-next-line no-new-func
  const made = new Function("el", `let deletesInFlight = 0;
     ${slice(/^const HELD_DELETE_DEPTH = \d+;$/m, "HELD_DELETE_DEPTH")}
     ${slice(fn("dropsHeldRepeat"), "dropsHeldRepeat()")}
     ${slice(fn("skipHeldRepeat"), "skipHeldRepeat()")}
     ${slice(/^el\.sink\.addEventListener\("keydown", skipHeldRepeat\);$/m, "the keydown registration")}
     return { set(n) { deletesInFlight = n; } };`)({ sink: { addEventListener: (type, l) => listeners.push([type, l]) } });
  const keydown = (repeat) => {
    let prevented = false;
    for (const [type, l] of listeners) if (type === "keydown") l({ key: "Backspace", repeat, isComposing: false, preventDefault() { prevented = true; } });
    return prevented;
  };
  made.set(2);
  assert.equal(keydown(true), true, "a flagged repeat at depth 2 was taken");
  assert.equal(keydown(false), false, "a press at depth 2 was dropped at the keydown");
  made.set(1);
  assert.equal(keydown(true), false, "a flagged repeat at depth 1 was dropped at the keydown");
});
