// Task 2026-10-14h: finding 140's fix, second pass.
//
// The pre-v68 129-B witness (findings/evidence/link-batch/v68-witness/) found
// two defects in the first pass (6c761117), which made `placeCaret` ask the
// engine (`editorPlaceCaretV2`) for every click:
//
//   1. The page passes `caret.y + caret.height / 2`; with an odd caret height
//      (277 in 129-B's s3 shape) that y is a half-integer, the worker refuses
//      it (INVALID_ARGUMENT: "requires non-negative integer twips"), and the
//      first pass let the refusal reach the user as a toast with the range
//      left selected: 6 of 54 cells in both browsers.
//   2. A click that collapses a range at the caret's own point moves no caret,
//      so core emits no visible-cursor callback -- the only callback the
//      engine's place-caret completes on -- and the engine answers at its
//      250 ms readback deadline.  Every 129-B click went from 26-32 ms on v67
//      to 253-268 ms.  Measured on the red bytes with `completion` recorded
//      (findings/evidence/paste-latency/second-pass/): a moving click is
//      answered on the callback at 24 ms, the collapse click at 251 ms
//      (`verified-caret-readback`), the identical-point click at 251 ms + the
//      grace.
//
// The second pass: the engine path is kept for a click made with a COLLAPSED
// selection, and gets integer twips; a click made while a RANGE IS OPEN takes
// v67's polling path, because a plain click always collapses the range and
// that collapse is the click's own evidence (138's predicate) at the speed v67
// had -- and because the engine's place-caret, pending until its deadline,
// holds `gEditorPending` and would answer BUSY to the key queued behind the
// click.  The polling path gains one bounded exit: collapsed by the click,
// caret stayed off the clicked line, after the grace.
//
// Like place-caret-blank-page.test.mjs: the REAL `placeCaret` of the class
// under test against a scripted engine.  This engine refuses non-integer twips
// as the worker does, answers on the cursor callback only when the caret
// RECTANGLE changes (else at the readback deadline), and reports whether its
// place-caret is still pending at the moment the session returns.

import assert from "node:assert/strict";
import test from "node:test";

import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const LINE = { y: 2000, height: 300 };
const ODD = { y: 1418, height: 277 };              // 129-B's s3 shape: an odd caret height
const rect = (x, y = LINE.y, width = 0, height = LINE.height) => ({ x, y, width, height });
const COLLAPSED = Object.freeze({ observed: true, collapsed: true, start: null, end: null, rectangles: [] });
const range = (fromX, toX, line = LINE) => ({
  observed: true, collapsed: false,
  start: rect(fromX, line.y, 0, line.height), end: rect(toX, line.y, 0, line.height),
  rectangles: [{ x: fromX, y: line.y, width: toX - fromX, height: line.height }],
});
const GRACE_MS = 400;                              // the base's default caretAckGraceMs
const READBACK_MS = 250;                           // the engine's EditorPlaceCaretDeadlineMs
const SAME_LINE = [5000, 2150];
const BELOW = [5000, 8000];                        // far below LINE
const mid = (line) => line.y + line.height / 2;    // what the page sends (web/e2-editor-app.js:1821, :2787)

function scripted({ caret, selection = COLLAPSED, click = null, lonePushAt = null, readbackMs = READBACK_MS }) {
  const t0 = Date.now();
  let sequence = 10;
  let state = { caret, selection };
  let enginePending = false;
  const timers = [];
  const calls = { documentClick: 0, enginePlaceCaret: 0, documentClickArguments: [], engineArguments: [] };
  const postClick = () => {
    if (lonePushAt !== null) timers.push(setTimeout(() => { sequence += 1; }, lonePushAt));
    if (click !== null) {
      timers.push(setTimeout(() => {
        sequence += 1;
        state = { caret: click.caret ?? state.caret, selection: click.selection ?? state.selection };
      }, click.at));
    }
  };
  const document = {
    revision: 7,
    async click(x, y) {
      calls.documentClick += 1;
      calls.documentClickArguments.push([x, y]);
      postClick();
      return { revision: 7 };
    },
  };
  const editor = {
    async getState() {
      return { sourceSequence: sequence, caret: structuredClone(state.caret), selection: structuredClone(state.selection) };
    },
    async placeCaret(x, y) {
      calls.enginePlaceCaret += 1;
      calls.engineArguments.push([x, y]);
      // sdk/sdk-worker.js:1553-1559, verbatim in effect.
      if (!Number.isInteger(x) || x < 0 || !Number.isInteger(y) || y < 0) {
        const error = new Error("editorPlaceCaretV2 requires non-negative integer twips");
        error.code = "INVALID_ARGUMENT";
        throw error;
      }
      enginePending = true;
      const before = sequence;
      postClick();
      const rectChanges = click !== null && click.caret
        && (click.caret.x !== state.caret.x || click.caret.y !== state.caret.y);
      const answerAt = rectChanges && click.at < readbackMs ? click.at : readbackMs;
      await new Promise((resolve) => timers.push(setTimeout(resolve, answerAt)));
      enginePending = false;
      return {
        revision: 7,
        completion: rectChanges && click.at < readbackMs ? "documented-callback-visible-cursor" : "verified-caret-readback",
        callbackSequenceBefore: before, callbackSequenceAfter: sequence,
        state: { sourceSequence: sequence, caret: structuredClone(state.caret), selection: structuredClone(state.selection) },
      };
    },
  };
  return { document, editor, t0, timers, calls, enginePending: () => enginePending };
}

async function drive(script, [x, y], options = {}) {
  const engine = scripted(script);
  const session = Object.create(NarrowEditorV2Session.prototype);
  session._enqueue = (label, operation) => operation({ document: engine.document, editor: engine.editor });
  let result = null;
  let error = null;
  try {
    result = await session.placeCaret(x, y, options);
  } catch (thrown) {
    error = thrown;
  }
  const returnedAtMs = Date.now() - engine.t0;
  const enginePendingAtReturn = engine.enginePending();
  await new Promise((resolve) => setTimeout(resolve, 40));
  engine.timers.forEach(clearTimeout);
  return { result, error, returnedAtMs, enginePendingAtReturn, calls: engine.calls };
}

/* ------------------------------------------------------- defect 1: integer twips */

test("defect 1: the reopen path's half-integer y (odd caret height) reaches the engine as integers and is not refused", async () => {
  // web/e2-editor-app.js:1821 after a restart: placeCaret(caret.x, caret.y + caret.height / 2)
  // with a collapsed selection.  1418 + 277 / 2 = 1556.5.
  const caret = rect(1000, ODD.y, 0, ODD.height);
  const o = await drive({ caret, click: { at: 25, caret }, readbackMs: 30 }, [1000, mid(ODD)], { caretAckGraceMs: 60 });
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.calls.enginePlaceCaret, 1);
  const [x, y] = o.calls.engineArguments[0];
  assert.ok(Number.isInteger(x) && Number.isInteger(y), `the engine was asked with ${x}, ${y}`);
  assert.equal(y, 1557, "rounded to the nearest twip (Math.round), not truncated");
  assert.equal(o.result.caretConfirmedBy, "already-at-target");
});

test("defect 1, 129-B's s3 shape: a half-integer y while a range is open ends in neither INVALID_ARGUMENT nor a 30 s wait", async () => {
  // moveFromPoint (web/e2-editor-app.js:2787): the caret end of a range on a
  // 277-twip line, the click at its own point collapses the range.
  const caret = rect(5000, ODD.y, 0, ODD.height);
  const o = await drive({ caret, selection: range(1000, 5000, ODD), click: { at: 25, caret, selection: COLLAPSED } },
                        [5000, mid(ODD)]);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.caretOnClickedLine, true);
  assert.ok(o.returnedAtMs < 150, `returned at ${o.returnedAtMs} ms`);
  assert.equal(o.calls.enginePlaceCaret, 0, "a click on an open range takes the polling path");
  assert.deepEqual(o.calls.documentClickArguments, [[5000, 1556.5]],
                   "document.click receives what v67 sent (the bytes 129-B's reference rounds were made with)");
});

/* ------------------------------------- defect 2: the collapse click at v67's speed */

test("defect 2: a click that collapses a range (129-B's 48 cells) resolves on the selection evidence before the engine's deadline, with no engine place-caret left pending", async () => {
  const o = await drive({ caret: rect(5000), selection: range(1000, 5000),
                          click: { at: 25, caret: rect(5000), selection: COLLAPSED } }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.caretOnClickedLine, true);
  assert.ok(o.returnedAtMs >= 25 && o.returnedAtMs < 150, `returned at ${o.returnedAtMs} ms (v67: 26-32; the red candidate: 253-268)`);
  assert.equal(o.enginePendingAtReturn, false, "the key queued behind the click would meet the engine's BUSY");
  assert.equal(o.calls.enginePlaceCaret, 0);
  assert.equal(o.calls.documentClick, 1);
});

test("control: a moving click with a collapsed selection still asks the engine and is answered on the cursor callback", async () => {
  const o = await drive({ caret: rect(1000), click: { at: 25, caret: rect(5000) } }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.completion, "documented-callback-visible-cursor");
  assert.ok(o.returnedAtMs < 150, `returned at ${o.returnedAtMs} ms`);
  assert.equal(o.enginePendingAtReturn, false);
  assert.equal(o.calls.enginePlaceCaret, 1);
  assert.equal(o.calls.documentClick, 0, "the engine posts the click itself");
});

test("control: the blank-page click (collapsed selection, caret cannot move) is unchanged from the first pass", async () => {
  const o = await drive({ caret: rect(1000), click: { at: 25, caret: rect(1000) } }, BELOW, { caretTimeoutMs: 1500 });
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-answered-the-caret-stayed");
  assert.equal(o.result.completion, "verified-caret-readback");
  assert.ok(o.result.caretWaitedMs >= GRACE_MS - 20 && o.returnedAtMs < 1000, `waited ${o.result.caretWaitedMs}, returned at ${o.returnedAtMs}`);
  assert.equal(o.calls.documentClick, 0);
});

/* ------------------------------------ the polling path's bound, and its named limit */

test("a range open and a click in the margin at the caret end's own clamp point: collapsed by the click, caret stayed -- bounded at the grace, not the 30 s timeout", async () => {
  // The first pass bounded every no-move click through the engine's deadline;
  // routing open-range clicks to the polling path must not give this one back
  // its 30 s.  The selection collapsing is the click's own evidence; the caret
  // is where the engine left it, off the clicked line.
  const o = await drive({ caret: rect(5000), selection: range(1000, 5000),
                          click: { at: 25, caret: rect(5000), selection: COLLAPSED } }, BELOW, { caretTimeoutMs: 1500 });
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-answered-the-caret-stayed");
  assert.equal(o.result.caretOnClickedLine, false);
  assert.equal(o.result.state.caret.x, 5000);
  assert.equal(o.result.state.selection.collapsed, true);
  assert.ok(o.result.caretWaitedMs >= GRACE_MS - 20 && o.returnedAtMs < 1000, `waited ${o.result.caretWaitedMs}, returned at ${o.returnedAtMs}`);
  assert.equal(o.calls.enginePlaceCaret, 0);
  assert.equal("completion" in o.result, false, "no engine answer on the polling path");
});

test("named limit: a range open and a click the core never processes keeps v67's timeout contract (no second click is posted)", async () => {
  const o = await drive({ caret: rect(5000), selection: range(1000, 5000) }, BELOW,
                        { caretTimeoutMs: 60, caretAckGraceMs: 30 });
  assert.equal(o.result, null);
  assert.equal(o.error.code, "EDITOR_CARET_NOT_PLACED");
  assert.equal(o.calls.documentClick, 1);
  assert.equal(o.calls.enginePlaceCaret, 0);
});
