// Finding 144 (task 2026-10-14q; the owner chose A).  Finding 141's hold kept
// `deletesInFlight` at one -- the second press of a held key is held, not
// sent -- so finding 132's depth cut (`dropsHeldRepeat`, keydown, depth 2)
// never fired: every flagged repeat was held, then released one per engine
// answer, and a 2 s hold inside text deleted 52 characters, 27–29 of them
// after the key came up (host 0.2.21, 132-B red,
// findings/evidence/host-0.2.21/k3/).  The cut now counts the sent deletes
// PLUS the held presses, and a held press is released by a direct call, not a
// synthetic `beforeinput` (132-B's instrument counted those).
//
// Driven the way a browser drives the page: a keydown goes to the sink's
// keydown listeners first and, unless one of them called preventDefault, the
// `beforeinput` follows.  The fake engine answers one action at a time on
// mocked time.  `PAGE_SOURCE=<path>` runs the same tests against another copy
// of the page: on 0.2.21's page (`2d6c4580…`) U1 is red -- about 28 deletes
// after release -- the witness kept in findings/evidence/host-0.2.22/.

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

const CARET = Object.freeze({ x: 3000, y: 1418, width: 0, height: 368 });
const WINDOW_MS = 2250;      // the engine's window at a C boundary (§10.5)
const DELETE_MS = 66;        // a verified delete inside text (finding 132's measurement)
const REPAINT_MS = 10;       // what run() awaits after the answer

/** A held key as the desk delivers it (132-B): the press, then a repeat every 30 ms from 500 ms to 2,000 ms, up at 2,015. */
const HOLD = { downs: [0, ...Array.from({ length: 51 }, (_, i) => 500 + 30 * i)], up: 2015 };

function page({ answer }) {
  const listeners = [];
  const sink = { addEventListener: (type, l) => listeners.push([type, l]) };
  const state = { caret: { ...CARET }, selection: { collapsed: true, rectangles: [] }, revision: 0 };
  const session = { document: { id: 1 }, offers: () => true, state: { snapshot: { editorState: state } } };
  const requests = [];
  const answers = [];
  const beforeinputs = [];
  const paints = [];
  let busyUntil = null;
  const now = () => Date.now();
  function editorAction(sent, options = {}) {
    requests.push({ sent, t: now() });
    return new Promise((resolve, reject) => {
      const start = () => {
        const reply = answer(sent, state, requests.length);
        const duration = reply.duration ?? WINDOW_MS;
        busyUntil = now() + duration;
        setTimeout(() => {
          busyUntil = null;
          if (reply.mutate) reply.mutate(state);
          answers.push({ sent, t: now(), reply, revision: state.revision });
          if (reply.reject) { reject(reply.reject); return; }
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
  const api = new Function("el", "session", "selectionShapeOf", "editorAction", "paint", `
    ${slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES")}
    let lastSelectionShape = "collapsed"; let deletesInFlight = 0; let deleteRefusedThisHold = false;
    ${optional(/^let deletesUnanswered = 0;$/m)}
    ${optional(/^const heldDeletes = \{[^\n]*\};$/m)}
    ${optional(/^const DELETE_INPUT_TYPE_OF = [\s\S]*?\]\)\);$/m)}
    ${slice(/^const HELD_DELETE_DEPTH = \d+;$/m, "HELD_DELETE_DEPTH")}
    ${slice(fn("deleteActionFor"), "deleteActionFor()")}
    ${["deleteStateOf", "boundaryNoopStands", "holdsDelete", "dropHeldDeletes", "releaseHeldDelete", "settleDelete", "dispatchDelete"]
      .map((name) => optional(fn(name))).join("\n")}
    ${slice(fn("dropsHeldRepeat"), "dropsHeldRepeat()")}
    ${slice(fn("skipHeldRepeat"), "skipHeldRepeat()")}
    ${slice(/^el\.sink\.addEventListener\("keydown", skipHeldRepeat\);$/m, "the keydown registration")}
    ${slice(/^el\.sink\.addEventListener\("beforeinput", \(event\) => \{[\s\S]*?\n\}\);$/m, "the beforeinput handler")}
    return { inFlight: () => deletesInFlight,
             held: () => (typeof heldDeletes === "object" ? heldDeletes.count : null) };
  `)({ sink }, session, selectionShapeOf, editorAction, () => paints.push(now()));
  // The 0.2.21 page released a held press with a synthetic event on the sink; give it one so the
  // old page runs here too (its re-dispatched events count as beforeinputs, as 132-B counted them).
  sink.dispatchEvent = (event) => {
    beforeinputs.push({ t: now(), synthetic: true });
    for (const [type, l] of listeners) if (type === event.type) l(event);
    return true;
  };
  globalThis.InputEvent ??= class { constructor(type, init = {}) { this.type = type; this.inputType = init.inputType; } preventDefault() {} };
  /** One keydown of the key, as a browser delivers it: keydown listeners, then beforeinput unless prevented. */
  const keydown = (repeat, key = "Backspace") => {
    let prevented = false;
    const event = { type: "keydown", key, repeat, isComposing: false, preventDefault() { prevented = true; } };
    for (const [type, l] of listeners) if (type === "keydown") l(event);
    if (prevented) return false;
    beforeinputs.push({ t: now(), synthetic: false });
    const input = { type: "beforeinput", inputType: key === "Backspace" ? "deleteContentBackward" : "deleteContentForward", preventDefault() {} };
    for (const [type, l] of listeners) if (type === "beforeinput") l(input);
    return true;
  };
  return { api, keydown, requests, answers, beforeinputs, paints, state };
}

const NOOP = () => ({
  duration: WINDOW_MS,
  result: (state) => ({ action: "delete-backward", beforeRevision: state.revision, revision: state.revision, changed: false,
                        completion: "verified-boundary-noop", boundaryNoop: { waitedMs: WINDOW_MS },
                        state: { caret: { ...state.caret }, selection: { ...state.selection } } }),
});
const REAL = () => ({
  duration: DELETE_MS,
  mutate: (state) => { state.caret = { ...state.caret, x: state.caret.x - 100 }; state.revision += 1; },
  result: (state) => ({ action: "delete-backward", beforeRevision: state.revision - 1, revision: state.revision, changed: true,
                        completion: "verified-selection-delete",
                        state: { caret: { ...state.caret }, selection: { ...state.selection } } }),
});

const flush = () => new Promise((resolve) => setImmediate(resolve));
async function advance(ms, step = 5) {
  for (let left = ms; left > 0; left -= step) {
    mock.timers.tick(Math.min(step, left));
    await flush();
  }
}
/** The hold: keydowns on their schedule (the first a press, the rest flagged repeats), then the keyup. */
async function hold(p, { repeatFlag = true, key = "Backspace" } = {}) {
  let at = 0;
  let taken = 0;
  for (const [i, t] of HOLD.downs.entries()) {
    await advance(t - at);
    at = t;
    if (p.keydown(i > 0 && repeatFlag, key)) taken += 1;
  }
  await advance(HOLD.up - at);
  return { taken, releaseAt: Date.now() };
}

test("144 U1: a held Backspace inside text (51 flagged repeats over 2 s) deletes at most 2 characters after the key comes up", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => REAL() });
    const { taken, releaseAt } = await hold(p);
    const beforeRelease = p.answers.filter((a) => a.t <= releaseAt).length;
    await advance(5000);
    const after = p.answers.filter((a) => a.t > releaseAt);
    assert.ok(after.length <= 2, `${after.length} deletes after release (0.2.21: 27–29); last at +${after.length ? after[after.length - 1].t - releaseAt : 0} ms`);
    assert.equal(p.api.held(), 0);
    assert.equal(p.api.inFlight(), 0);
    // Every press the keydown guard let through was deleted, and nothing else (132-B's clause (c)).
    assert.equal(p.beforeinputs.filter((b) => !b.synthetic).length, taken);
    assert.equal(p.beforeinputs.length, p.answers.length, "beforeinputs != deleted: a synthetic re-dispatch, or a press lost");
    assert.equal(p.state.revision, p.answers.length);
    // The engine was kept busy during the hold: about one delete per DELETE_MS, well above half the keydowns' worth.
    assert.ok(beforeRelease >= 20, `only ${beforeRelease} deletes during the 2 s hold`);
    assert.ok(p.answers.length < HOLD.downs.length, `every keydown was deleted (${p.answers.length}): the depth cut never fired`);
  } finally {
    mock.timers.reset();
  }
});

test("144 U1b (control): an UNFLAGGED burst inside text is still deleted press for press (finding 131)", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => REAL() });
    const { taken } = await hold(p, { repeatFlag: false });
    await advance(HOLD.downs.length * (DELETE_MS + REPAINT_MS) + 500);
    assert.equal(taken, HOLD.downs.length, "an unflagged press was dropped at the keydown");
    assert.equal(p.answers.length, HOLD.downs.length);
    assert.equal(p.state.revision, HOLD.downs.length);
  } finally {
    mock.timers.reset();
  }
});

test("144 U1c (control, finding 141): a flagged hold at a C boundary is still one engine request per window, nothing deleted", async () => {
  mock.timers.enable({ apis: ["setTimeout", "Date"] });
  try {
    const p = page({ answer: () => NOOP() });
    await hold(p);
    await advance(2 * WINDOW_MS + 500);
    assert.equal(p.requests.length, 1, "a 2 s hold at the boundary made more than one request");
    assert.equal(p.state.revision, 0);
    assert.equal(p.api.held(), 0);
  } finally {
    mock.timers.reset();
  }
});

test("144 U1d: the keydown guard counts a held press -- a flagged repeat is dropped with one delete out and one press held", () => {
  const listeners = [];
  // eslint-disable-next-line no-new-func
  const made = new Function("el", `let deletesInFlight = 0;
     ${slice(/^const heldDeletes = \{[^\n]*\};$/m, "heldDeletes")}
     ${slice(/^const HELD_DELETE_DEPTH = \d+;$/m, "HELD_DELETE_DEPTH")}
     ${slice(fn("dropsHeldRepeat"), "dropsHeldRepeat()")}
     ${slice(fn("skipHeldRepeat"), "skipHeldRepeat()")}
     ${slice(/^el\.sink\.addEventListener\("keydown", skipHeldRepeat\);$/m, "the keydown registration")}
     return { set(sent, held) { deletesInFlight = sent; heldDeletes.count = held; } };`)({ sink: { addEventListener: (type, l) => listeners.push([type, l]) } });
  const repeat = () => {
    let prevented = false;
    for (const [type, l] of listeners) if (type === "keydown") l({ key: "Backspace", repeat: true, isComposing: false, preventDefault() { prevented = true; } });
    return prevented;
  };
  made.set(1, 1);
  assert.equal(repeat(), true, "one out and one held: the repeat was taken");
  made.set(1, 0);
  assert.equal(repeat(), false, "one out and none held: the repeat was dropped");
  made.set(0, 2);
  assert.equal(repeat(), true);
  made.set(2, 0);
  assert.equal(repeat(), true);
});
