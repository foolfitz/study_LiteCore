// Finding 140 (ruling, 2026-10-14): a click below the first line of a blank
// document must not hold the queue for 30 s.
//
// The product's `placeCaret` now asks the ENGINE where the click put the caret
// (`editorPlaceCaretV2`, 052's prescription): the engine posts the mouse
// events itself and answers either on the cursor callback the click caused
// (`documented-callback-visible-cursor`) or, when the click changed nothing
// and no callback came, at its own 250 ms readback deadline
// (`verified-caret-readback`, probe_engine.cpp EditorPlaceCaretDeadlineMs).
// The session then judges that answer with finding 138's predicate -- caret
// or selection evidence, never the sequence alone -- and, for an answer
// without evidence, gives the core the same grace the identical-point click
// already gets (048's guard against a click the core has not processed yet)
// before accepting "the click was answered and the caret stayed".
//
// Like place-caret-acknowledgement.test.mjs: the REAL `placeCaret` of the
// class under test is driven against a scripted engine; only timing and what
// the click changes are scripted.  The scripted engine here carries
// `placeCaret` with the engine's two completions; the other file's engine does
// not, and so keeps exercising the polling path (an old client, or BUSY).

import assert from "node:assert/strict";
import test from "node:test";

import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const LINE = { y: 2000, height: 300 };            // the first (only) line of a blank page, twips
const rect = (x, y = LINE.y, width = 0, height = LINE.height) => ({ x, y, width, height });
const COLLAPSED = Object.freeze({ observed: true, collapsed: true, start: null, end: null, rectangles: [] });
const GRACE_MS = 400;                              // the base's default caretAckGraceMs
const READBACK_MS = 250;                           // the engine's EditorPlaceCaretDeadlineMs
const BELOW = [5000, 8000];                        // the middle of a blank A4 page, far below LINE
const SAME_LINE = [5000, 2150];

/**
 * A scripted engine with `editor.placeCaret`.  `click`: when the core
 * processes the click and what it changes (null: never).  The engine's answer
 * comes on the click's cursor callback when the click changes the caret
 * rectangle, else at the readback deadline with the state at that moment.
 * `lonePushAt`: an unrelated state-changing callback (138's shape); it bumps
 * the sequence and does NOT complete the engine's place-caret.
 * `refuse`: the engine's error code for placeCaret (BUSY: a barrier in flight).
 */
function scripted({ caret, selection = COLLAPSED, click = null, lonePushAt = null, refuse = null,
                    readbackMs = READBACK_MS, withPlaceCaret = true }) {
  const t0 = Date.now();
  let sequence = 10;
  let state = { caret, selection };
  let clickTookEffectAtMs = null;
  const timers = [];
  const calls = { documentClick: 0, enginePlaceCaret: 0, getState: 0 };
  const postClick = () => {
    if (lonePushAt !== null) timers.push(setTimeout(() => { sequence += 1; }, lonePushAt));
    if (click !== null) {
      timers.push(setTimeout(() => {
        sequence += 1;
        state = { caret: click.caret ?? state.caret, selection: click.selection ?? state.selection };
        clickTookEffectAtMs = Date.now() - t0;
      }, click.at));
    }
  };
  const document = {
    revision: 7,
    async click() { calls.documentClick += 1; postClick(); return { revision: 7 }; },
  };
  const editor = {
    async getState() {
      calls.getState += 1;
      return { sourceSequence: sequence, caret: structuredClone(state.caret), selection: structuredClone(state.selection) };
    },
  };
  if (withPlaceCaret) {
    editor.placeCaret = async () => {
      calls.enginePlaceCaret += 1;
      if (refuse) { const error = new Error(refuse); error.code = refuse; throw error; }
      const before = sequence;
      postClick();
      const caretRectChanges = click !== null && click.caret && (click.caret.x !== state.caret.x || click.caret.y !== state.caret.y);
      const answerAt = caretRectChanges && click.at < readbackMs ? click.at : readbackMs;
      await new Promise((resolve) => timers.push(setTimeout(resolve, answerAt)));
      return {
        revision: 7,
        completion: caretRectChanges && click.at < readbackMs ? "documented-callback-visible-cursor" : "verified-caret-readback",
        callbackSequenceBefore: before, callbackSequenceAfter: sequence,
        state: { sourceSequence: sequence, caret: structuredClone(state.caret), selection: structuredClone(state.selection) },
      };
    };
  }
  return { document, editor, t0, timers, calls, clickTookEffectAt: () => clickTookEffectAtMs, caretNow: () => structuredClone(state.caret) };
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
  const caretWhenNextCommandIsSent = engine.caretNow();
  await new Promise((resolve) => setTimeout(resolve, 40));
  engine.timers.forEach(clearTimeout);
  return { result, error, returnedAtMs, calls: engine.calls, clickTookEffectAtMs: engine.clickTookEffectAt(), caretWhenNextCommandIsSent };
}

/* --------------------------------------------------------- the 140 shape */

test("140: a click below the only line of a blank page returns promptly with the engine's caret", async () => {
  // The core processes the click at 25 ms and moves nothing (the caret is
  // already where every click on a blank page clamps to).  Today: 30 s, then
  // EDITOR_CARET_NOT_PLACED.  The 1,500 ms cap is the test's, so that the
  // red case fails in 1.5 s instead of 30.
  const o = await drive({ caret: rect(1000), click: { at: 25, caret: rect(1000) } }, BELOW, { caretTimeoutMs: 1500 });
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-answered-the-caret-stayed");
  assert.equal(o.result.caretOnClickedLine, false);
  assert.equal(o.result.state.caret.x, 1000, "the engine's caret is returned");
  assert.equal(o.result.completion, "verified-caret-readback");
  assert.ok(o.returnedAtMs < 1000, `returned at ${o.returnedAtMs} ms`);
  assert.ok(o.result.caretWaitedMs >= GRACE_MS - 20, `waited ${o.result.caretWaitedMs} ms: 048's grace was not given`);
  assert.equal(o.calls.enginePlaceCaret, 1);
  assert.equal(o.calls.documentClick, 0, "the engine posts the click itself; the session must not post a second one");
});

test("140: the same with the engine saying nothing at all (no callback, no sequence change)", async () => {
  const o = await drive({ caret: rect(1000) }, BELOW, { caretTimeoutMs: 1500 });
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-answered-the-caret-stayed");
  assert.ok(o.returnedAtMs < 1000, `returned at ${o.returnedAtMs} ms`);
});

/* ------------------------------------------- 048 / 138 / 052 on the engine path */

test("048 guard: a readback answer that precedes a late click is not accepted -- the moved caret is returned", async () => {
  // The core is stalled: the engine's readback (250 ms) answers with the OLD
  // caret, the click lands at 300 ms (inside the grace) on another line.
  const o = await drive({ caret: rect(1000), click: { at: 300, caret: rect(0, 5000) } }, [2000, 6000]);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-moved-the-caret-off-the-clicked-line");
  assert.equal(o.result.state.caret.y, 5000, "the state returned carries the caret the click produced");
  assert.equal(o.caretWhenNextCommandIsSent.y, 5000, "the next command lands where the click put the caret");
  assert.ok(o.clickTookEffectAtMs !== null && o.returnedAtMs >= o.clickTookEffectAtMs);
});

test("named limit: a click the core processes only after the grace is accepted as 'stayed' with the old caret (the identical-point bound)", async () => {
  const o = await drive({ caret: rect(1000), click: { at: 700, caret: rect(0, 5000) } }, [2000, 6000]);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-answered-the-caret-stayed");
  assert.ok(o.returnedAtMs < 700, `returned at ${o.returnedAtMs} ms`);
  assert.equal(o.result.state.caret.x, 1000);
});

test("138: a lone unrelated callback inside the window does not end the wait; the click's own evidence does", async () => {
  const o = await drive({ caret: rect(1000), lonePushAt: 3, click: { at: 25, caret: rect(5000) } }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.caretOnClickedLine, true);
  assert.equal(o.result.state.caret.x, 5000);
  assert.equal(o.caretWhenNextCommandIsSent.x, 5000);
  assert.ok(o.result.caretWaitedMs < GRACE_MS);
});

test("138: a lone bump and a click the core never processes (image-click shape) is already-at-target after the grace, never acknowledged", async () => {
  const o = await drive({ caret: rect(1000), lonePushAt: 3 }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "already-at-target");
  assert.ok(o.result.caretWaitedMs >= GRACE_MS - 20, `waited ${o.result.caretWaitedMs} ms`);
});

test("052: the engine moved the caret to another line -- answered on the cursor callback, no grace paid", async () => {
  const o = await drive({ caret: rect(1000), click: { at: 25, caret: rect(0, 5000) } }, [2000, 6000]);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-moved-the-caret-off-the-clicked-line");
  assert.equal(o.result.completion, "documented-callback-visible-cursor");
  assert.ok(o.result.caretWaitedMs < GRACE_MS);
  assert.equal(o.calls.documentClick, 0);
});

test("a click that collapses a selection at its caret end is acknowledged by the selection evidence", async () => {
  const o = await drive({ caret: rect(5000),
                          selection: { observed: true, collapsed: false, start: rect(1000), end: rect(5000),
                                       rectangles: [{ x: 1000, y: LINE.y, width: 4000, height: LINE.height }] },
                          click: { at: 25, caret: rect(5000), selection: COLLAPSED } }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.caretOnClickedLine, true);
});

/* ----------------------------------------------------- falling back to polling */

test("BUSY from the engine's place-caret falls back to the polling path (document.click + getState)", async () => {
  const o = await drive({ caret: rect(1000), click: { at: 25, caret: rect(5000) }, refuse: "BUSY" }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.result.state.caret.x, 5000);
  assert.equal(o.calls.enginePlaceCaret, 1);
  assert.equal(o.calls.documentClick, 1, "the polling path posts the click once");
});

test("an engine without the entry point (UNSUPPORTED_OPERATION) falls back to polling and keeps the timeout contract", async () => {
  const o = await drive({ caret: rect(1000, 8000), refuse: "UNSUPPORTED_OPERATION" }, SAME_LINE,
                        { caretTimeoutMs: 60, caretAckGraceMs: 30 });
  assert.equal(o.result, null);
  assert.equal(o.error.code, "EDITOR_CARET_NOT_PLACED");
  assert.equal(o.calls.documentClick, 1);
});

test("any other engine error is the caller's (not swallowed into polling)", async () => {
  const o = await drive({ caret: rect(1000), refuse: "ENGINE_DISPOSED" }, SAME_LINE);
  assert.equal(o.result, null);
  assert.equal(o.error.code, "ENGINE_DISPOSED");
  assert.equal(o.calls.documentClick, 0);
});

test("a client without placeCaret (an old client) takes the polling path unchanged", async () => {
  const o = await drive({ caret: rect(1000), click: { at: 25, caret: rect(5000) }, withPlaceCaret: false }, SAME_LINE);
  assert.equal(o.error, null, o.error?.message);
  assert.equal(o.result.caretConfirmedBy, "engine-acknowledged");
  assert.equal(o.calls.documentClick, 1);
});

test("contract: the engine path yields the base's three values plus the one 140 adds, and nothing else", async () => {
  const seen = new Set();
  for (const [script, at] of [
    [{ caret: rect(1000), click: { at: 25, caret: rect(5000) } }, SAME_LINE],
    [{ caret: rect(1000) }, [1000, 2150]],
    [{ caret: rect(1000), click: { at: 25, caret: rect(0, 5000) } }, [2000, 6000]],
    [{ caret: rect(1000), click: { at: 25, caret: rect(1000) } }, BELOW],
  ]) {
    seen.add((await drive(script, at, { caretAckGraceMs: 60 })).result.caretConfirmedBy);
  }
  assert.deepEqual([...seen].sort(), ["already-at-target", "engine-acknowledged", "engine-answered-the-caret-stayed",
                                      "engine-moved-the-caret-off-the-clicked-line"]);
});
