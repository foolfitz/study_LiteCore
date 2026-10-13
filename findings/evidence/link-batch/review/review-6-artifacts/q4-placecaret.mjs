// Q4 harness (review 6): drives the REAL EditorSession.prototype.placeCaret
// (editor-shell/editor-session.js, the base class NarrowEditorV2Session does
// not override) against a scripted engine.  Only the timing of editor-state
// changes is scripted; the decision code is the product's.
//
// Script (twips): caret at x=1000 on the line y=2000..2300.  The user clicks
// the SAME line at x=5000.  The click's caret callback lands at t=25 ms (the
// measured 22-28 ms, finding 048).  Arm "v20" adds one lone
// DOCUMENT_SIZE_CHANGED at t=3 ms, which on v20 bumps sourceSequence
// (probe_engine.cpp:2663-2679) and changes nothing else; on v19 the same
// callback does not reach the switch's editorStateChanged.
const repo = process.argv[2];
const { EditorSession } = await import(`${repo}/wasm_sdk_probe/editor-shell/editor-session.js`);

async function arm(name, lonePush) {
  const t0 = Date.now();
  const caretOld = { x: 1000, y: 2000, width: 0, height: 300 };
  const caretNew = { x: 5000, y: 2000, width: 0, height: 300 };
  let seq = 10;
  let caret = caretOld;
  let clickRunAt = null;
  const timers = [];
  const document = {
    revision: 7,
    async click() {
      if (lonePush) timers.push(setTimeout(() => { seq += 1; }, 3));
      timers.push(setTimeout(() => { seq += 1; caret = caretNew; clickRunAt = Date.now() - t0; }, 25));
      return { revision: 7 };
    },
  };
  const editor = {
    async getState() { return { sourceSequence: seq, caret: { ...caret } }; },
  };
  const session = Object.create(EditorSession.prototype);
  session._enqueue = (label, op) => op({ document, editor });
  const result = await session.placeCaret(5000, 2150);
  const returnedAt = Date.now() - t0;
  // What a synchronous paste dispatched next would see: the caret core has NOW.
  const caretAtNextCommand = { ...caret };
  await new Promise((r) => setTimeout(r, 40));
  timers.forEach(clearTimeout);
  console.log(JSON.stringify({
    arm: name,
    returnedAtMs: returnedAt,
    clickTookEffectAtMs: clickRunAt,
    caretConfirmedBy: result.caretConfirmedBy,
    caretInResult: result.state.caret.x,
    caretWhenNextCommandIsSent: caretAtNextCommand.x,
    nextCommandLandsAtClickedPoint: caretAtNextCommand.x === 5000,
  }));
}

await arm("v19 (no size bump)", false);
await arm("v20 (lone DOCUMENT_SIZE_CHANGED bump at 3 ms)", true);
