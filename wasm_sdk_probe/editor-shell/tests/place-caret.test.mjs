// Finding 048: placeCaret used to confirm a click with a predicate that was
// already true before the click, so it returned before the engine had processed
// anything and the next action landed on the previous caret's paragraph.
//
// These tests are written so that the OLD implementation fails them.  The one
// that matters is "a click the engine never processes must not report success":
// under the old predicate -- selectionType none, observed, collapsed -- that
// case returned immediately, and it is exactly the case that produced eight
// mis-anchored cells in E2-C D3.

import assert from "node:assert/strict";
import test from "node:test";

import { EditorSession, caretIsOnLine } from "../editor-session.js";

/**
 * A session whose engine reports whatever caret and sequence the test says.
 *
 * `onClick` is called with a `step` object the test mutates to make the engine
 * respond -- move the caret, advance the sequence, or do neither.
 */
function fixture({ caret = { x: 100, y: 1418, width: 0, height: 300 },
                   sourceSequence = 7, onClick = () => {} } = {}) {
  const engineState = { caret, sourceSequence };
  const reads = [];
  const document = {
    handle: 1,
    revision: 0,
    widthTwips: 12240,
    heightTwips: 15840,
    _assertUsable() {},
    async render() { return { pixels: new ArrayBuffer(4), revision: 0 }; },
    async click(xTwips, yTwips) {
      onClick(engineState, { xTwips, yTwips });
    },
    async close() {},
  };
  const engine = {
    manifest: { profile: "test", capabilities: ["narrow-editor-v1"],
                editorContract: { version: 1 } },
    onEvent() { return () => {}; },
    async open() { return document; },
    async _request(operation) {
      if (operation !== "editorGetStateV1")
        throw new Error(`unexpected ${operation}`);
      reads.push(engineState.sourceSequence);
      return {
        documentHandle: 1,
        revision: 0,
        sourceSequence: engineState.sourceSequence,
        documentChangeSequence: 0,
        visible: true,
        caret: engineState.caret,
        selection: { observed: true, collapsed: true, start: null, end: null,
                     rectangles: [] },
        selectionType: "none",
        selectionText: "",
        format: { bold: false, italic: false },
      };
    },
    dispose() {},
  };
  document._engine = engine;
  const session = new EditorSession({
    engineFactory: async () => engine,
    secureContext: true,
    clipboard: { async writeText() {}, async readText() { return ""; } },
  });
  return { session, engineState, reads,
           open: () => session.open({ bytes: new ArrayBuffer(8), name: "t.odt" }) };
}

test("a click the engine acknowledges resolves once the caret is on the line",
     async () => {
       const value = fixture({
         onClick(state, { yTwips }) {
           state.caret = { x: 100, y: yTwips + 40, width: 0, height: 300 };
           state.sourceSequence += 1;
         },
       });
       await value.open();
       const result = await value.session.placeCaret(2000, 3640);
       assert.equal(result.caretConfirmedBy, "engine-acknowledged");
       assert.equal(result.state.caret.y, 3680);
     });

test("a click the engine never processes is a failure, not a success",
     async () => {
       // THE REGRESSION.  The engine says nothing and the caret stays where it
       // was; the old predicate returned here because a collapsed observed
       // caret existed, and the caller went on to dispatch at the wrong
       // paragraph.
       const value = fixture({ onClick() { /* the click is swallowed */ } });
       await value.open();
       await assert.rejects(
         () => value.session.placeCaret(2000, 3640,
                                        { caretTimeoutMs: 120, caretAckGraceMs: 40 }),
         (error) => {
           assert.equal(error.code, "EDITOR_CARET_NOT_PLACED");
           assert.equal(error.details.caret.y, 1418);
           assert.equal(error.details.sequenceAdvanced, false);
           return true;
         });
     });

test("a caret that arrives late is waited for, not missed", async () => {
  let reads = 0;
  const value = fixture({
    onClick(state, { yTwips }) {
      // Arrives on the fourth read, the way a 22-28 ms engine does against a
      // 5 ms poll.
      const target = { x: 100, y: yTwips + 40, width: 0, height: 300 };
      const tick = setInterval(() => {
        if (++reads >= 3) {
          clearInterval(tick);
          state.caret = target;
          state.sourceSequence += 1;
        }
      }, 5);
    },
  });
  await value.open();
  const result = await value.session.placeCaret(2000, 3640, { caretTimeoutMs: 2000 });
  assert.equal(result.state.caret.y, 3680);
  assert.equal(result.caretConfirmedBy, "engine-acknowledged");
});

test("clicking the point the caret already occupies resolves without an "
     + "acknowledgement", async () => {
       // Measured on the shipped engine: an identical-point click emits no
       // callback at all, because nothing changed.  The caret is already where
       // the caller asked, so this must resolve -- after the grace period, and
       // saying which signal it used.
       const value = fixture({
         caret: { x: 100, y: 3680, width: 0, height: 300 },
         onClick() { /* nothing changes, so the engine says nothing */ },
       });
       await value.open();
       const result = await value.session.placeCaret(
         2000, 3640, { caretTimeoutMs: 2000, caretAckGraceMs: 30 });
       assert.equal(result.caretConfirmedBy, "already-at-target");
       assert.ok(result.caretWaitedMs >= 30);
     });

test("an acknowledgement that is not about the caret does not end the wait",
     async () => {
       // A tile invalidation advances sourceSequence too.  Returning on the
       // bare advance would hand back the stale caret -- the same bug wearing a
       // different hat.
       const value = fixture({
         onClick(state) { state.sourceSequence += 1; },   // caret unmoved
       });
       await value.open();
       await assert.rejects(
         () => value.session.placeCaret(2000, 3640,
                                        { caretTimeoutMs: 120, caretAckGraceMs: 40 }),
         (error) => {
           assert.equal(error.code, "EDITOR_CARET_NOT_PLACED");
           assert.equal(error.details.sequenceAdvanced, true);
           return true;
         });
     });

test("caretIsOnLine scales with the caret, not with a corpus", () => {
  // The measured landings: the caret's top sits up to 119 twips from the click
  // in rectangles 276-414 twips tall.
  assert.ok(caretIsOnLine({ y: 3238, height: 348 }, 3120));
  assert.ok(caretIsOnLine({ y: 2795, height: 276 }, 2730));
  assert.ok(caretIsOnLine({ y: 1999, height: 348 }, 1950));
  // One line away in that corpus is 390 twips, and must be rejected in every
  // rectangle size it appears with.
  assert.ok(!caretIsOnLine({ y: 1418, height: 414 }, 1950));
  assert.ok(!caretIsOnLine({ y: 3238, height: 348 }, 3628));
  // Self-scaling: the same relative offset passes in a document whose lines are
  // twice as tall and fails in one whose lines are half as tall.
  assert.ok(caretIsOnLine({ y: 1000, height: 600 }, 1250));
  assert.ok(!caretIsOnLine({ y: 1000, height: 150 }, 1250));
  // No caret, no confirmation.
  assert.ok(!caretIsOnLine(null, 1250));
  assert.ok(!caretIsOnLine({ y: 1000 }, 1000));
});
