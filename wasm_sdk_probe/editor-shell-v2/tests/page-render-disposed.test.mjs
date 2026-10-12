// A repaint whose engine the page disposed itself is not a failed repaint.
//
// `restart()` (a boundary refusal's reopen, the recovery notice) and `close()`
// dispose the engine; the SDK then rejects every request still waiting for a
// reply with ENGINE_DISPOSED (sdk/document-sdk.js `dispose()`).  A repaint in
// flight at that moment used to toast 「重繪失敗：ENGINE_DISPOSED」 beside the
// reopen's own sentence -- seen on the merge shakedown 2026-10-07 (F01 run 2,
// C17 run 1) and counted by SPEC-M3-paragraph-merge M2-3 as a second toast.
//
// `renderDocument` is taken from the page source and run with stubs, so this
// tests the page's own code, not a copy of it.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PAGE = fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url));
const SOURCE = readFileSync(PAGE, "utf8");

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}

const RENDER_FN = slice(/^async function renderDocument\(retriesLeft = RENDER_BUSY_RETRIES\) \{[\s\S]*?\n\}$/m,
                        "renderDocument()");
const RETRIES_DECL = slice(/^const RENDER_BUSY_RETRIES = \d+;$/m, "RENDER_BUSY_RETRIES");
// Finding 122 (SPEC-M3-production-ui §15): renderDocument paints in bands, so
// its band helpers come with it.  The assertions below are unchanged.
// Release C′ (§17.2): and its window helpers; the canvas here is the whole
// ten-row document.
const BAND_PARTS = [
  slice(/^const RENDER_BAND_HEIGHT = .*;$/m, "RENDER_BAND_HEIGHT"),
  ...["renderBands", "bandOrder", "visibleDocRows", "bandInWindow", "publishWindow"].map((name) =>
    slice(new RegExp(`^function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`)),
  // SPEC-M3-held-key §3.1: renderDocument asks where the caret is; taken when the page has it.
  SOURCE.match(/^function caretDocRows\([^)]*\) \{[\s\S]*?\n\}$/m)?.[0] ?? "",
].join("\n");

/** The page's renderDocument over a render() stub, with its toasts. */
function renderer(render) {
  const toasts = [];
  const session = {
    state: { snapshot: { state: "ready" } },
    document: { heightTwips: 1000, widthTwips: 1000, render: async () => render() },
  };
  const el = { canvas: { width: 10, height: 10, dataset: {} },
              paper: { getBoundingClientRect: () => ({ top: 0, bottom: 10, height: 10 }) },
              desk: { getBoundingClientRect: () => ({ top: 0, bottom: 10 }) } };
  // eslint-disable-next-line no-new-func
  const renderDocument = new Function(
    "session", "el", "toast", "describeError", "tileWasPainted", "paint", "layoutCanvas",
    "setTimeout", "ImageData", "paintBand",
    `let rendering = false, renderAgain = false, lastTiles = []; let engineActionsOut = 0, busyLeftToAction = false;
     let docRows = 10, winTop = 0, changes = 0;
     const MAX_TILE_HEIGHT = 32767;
     ${RETRIES_DECL}
     ${BAND_PARTS}
     ${RENDER_FN}
     return { renderDocument, change() { changes += 1; } };`)(
    session, el, (message) => toasts.push(message),
    (error) => `${error.code}：${error.message}`, () => true, () => {}, () => {},
    (resolve) => resolve(), class { constructor(pixels, width, height) {
      Object.assign(this, { pixels, width, height }); } }, () => {});
  return { renderDocument: renderDocument.renderDocument, change: renderDocument.change, toasts };
}

/** Run renderDocument once; returns the toasts and how often render() was asked. */
async function repaint(render) {
  let calls = 0;
  const { renderDocument, toasts } = renderer(() => { calls += 1; return render(calls); });
  await renderDocument();
  return { toasts, calls };
}

const TILE = { width: 10, height: 10, pixels: new Uint8ClampedArray(400) };
const turn = () => new Promise((resolve) => setImmediate(resolve));

const failure = (code) => Object.assign(new Error(code.toLowerCase()), { code });

test("a repaint rejected because the page disposed its engine says nothing", async () => {
  const { toasts } = await repaint(() => { throw failure("ENGINE_DISPOSED"); });
  assert.deepEqual(toasts, []);
});

// The control: the silence above is about ENGINE_DISPOSED, not about every
// rejection.  Without it, a renderDocument that swallowed all errors would
// pass the test above.
test("any other failed repaint is still reported", async () => {
  for (const code of ["INTERNAL", "TILE_NOT_PAINTED", "WORKER_CRASHED", "WORKER_RESTARTED"]) {
    const { toasts } = await repaint(() => { throw failure(code); });
    assert.equal(toasts.length, 1, code);
    assert.match(toasts[0], /^重繪失敗：/, code);
  }
});

test("BUSY is still retried, and a later success says nothing", async () => {
  const { toasts, calls } = await repaint((n) => {
    if (n < 3) throw failure("BUSY");
    return TILE;
  });
  assert.deepEqual(toasts, []);
  assert.equal(calls, 3);
});

// Review N4 (2026-10-07): `return renderDocument(retriesLeft - 1)` inside the
// catch let the outer `finally` clear `rendering` while the retried request
// was still in flight, so a repaint asked for in that window started a SECOND
// loop.  With B a barrier keeps the engine BUSY for up to about 8 s (84
// retries), and two loops can both fail and both toast.
test("a BUSY retry keeps one repaint in flight", async () => {
  let calls = 0, inFlight = 0, most = 0, release;
  const held = new Promise((resolve) => { release = resolve; });
  const { renderDocument, change, toasts } = renderer(async () => {
    calls += 1;
    inFlight += 1; most = Math.max(most, inFlight);
    try {
      if (calls === 1) throw failure("BUSY");
      if (calls === 2) await held;          // the retried request, still in flight
      return TILE;
    } finally { inFlight -= 1; }
  });
  const first = renderDocument();
  for (let i = 0; i < 5; i += 1) await turn();
  // Asked for while the retry is in flight, by a change (release C′: a pass
  // asks only for stale bands, and on the page a repaint is asked for by a
  // document-invalidated, which is a change).
  change();
  const second = renderDocument();
  for (let i = 0; i < 5; i += 1) await turn();
  release();
  await first; await second;
  for (let i = 0; i < 10; i += 1) await turn();
  assert.equal(most, 1, `${most} repaints were in flight at once`);
  assert.equal(calls, 3, "the repaint asked for meanwhile still runs, after the retry");
  assert.deepEqual(toasts, []);
});
