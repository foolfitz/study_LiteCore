// SPEC-M3-production-ui §15.2, 122-U: finding 122's banded repaint (fable's
// ruling B′).  The page's own functions are taken from its source and run
// against a recording canvas and a fake engine, so these test the page's code.
// §15.6 (fable's third ruling, A+B): B1 restated for bands of
// floor(32767/32) = 1023 rows, the other counts follow the page's constant,
// and B8 / B8-control test A (a key that will reach the engine ends a pass).
// Release C′ (§17.2, §17.9 (c)): a pass asks only for the bands that overlap
// the window and are stale.  The 122 cases run on a window that is the whole
// document, as on the P page, and a change is what a `document-invalidated`
// does on the real page -- the counter goes up AND a repaint is asked for --
// where a case used to model it by the repaint alone.  The C′ cases (C1-U,
// W-U) are at the end.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url)), "utf8");

function slice(pattern, what) {
  const match = SOURCE.match(pattern);
  assert.ok(match, `${what} not found in the page`);
  return match[0];
}

const fn = (name) => slice(new RegExp(`^(async )?function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"), `${name}()`);
// SPEC-M3-held-key §5.1: renderDocument asks where the caret is (H1).  Taken
// when the page has it, so that on a page without it U2 fails by name rather
// than this whole file failing to load.
const optional = (name) => SOURCE.match(new RegExp(`^function ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n\\}$`, "m"))?.[0] ?? "";
const PARTS = [
  slice(/^const MAX_TILE_HEIGHT = .*;$/m, "MAX_TILE_HEIGHT"),
  slice(/^const RENDER_BAND_HEIGHT = .*;$/m, "RENDER_BAND_HEIGHT"),
  fn("renderBands"), fn("bandOrder"), fn("visibleDocRows"), optional("caretDocRows"), fn("renderDocument"), fn("paint"), fn("overlayAreas"),
  fn("paintBand"), fn("bandInWindow"), fn("publishWindow"), fn("windowRows"), fn("windowTopFor"), fn("placeCanvas"),
  fn("moveWindow"), fn("onDeskScroll"),
  slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES"),
  slice(/^const ENGINE_INPUT_TYPES = new Set\(\[[\s\S]*?\n\]\);$/m, "ENGINE_INPUT_TYPES"),
  fn("endRenderPassOnInput"),
].join("\n");
// A's registration, taken from the page as it stands: if the page stops
// registering it, B8 sees the pass run on (a behaviour, not a missing string).
const LISTENER = SOURCE.match(/^el\.sink\.addEventListener\("beforeinput", endRenderPassOnInput\);$/m)?.[0] ?? "";

/**
 * A page around the real functions: canvas, desk, session and engine are
 * recordings.  The document is `height` rows; the canvas holds `rows` of them
 * from `top` (by default all of them, the P page's shape).  `view` is the
 * document rows the desk shows; `scrollTo(a, b)` moves it.
 */
function page({ height = 22256, width = 10, view = [9000, 11000], onRender = null, painted = () => true,
                rows = height, top = 0 } = {}) {
  const ops = [];
  const requests = [];
  const toasts = [];
  let layouts = 0;
  const context = {
    putImageData(image, x, y) { ops.push(["blit", y, image.height, image.band]); },
    save() { ops.push(["save"]); }, restore() { ops.push(["restore"]); }, beginPath() {},
    rect(x, y, w, h) { ops.push(["clipRect", y, h]); }, clip() {},
    clearRect(x, y, w, h) { ops.push(["clear", y, h]); }, fillRect() {},
  };
  const canvas = { width, height: rows, dataset: {}, style: {}, getContext: () => context };
  const listeners = [];
  const sink = { addEventListener(type, listener) { listeners.push([type, listener]); } };
  let shown = [...view];
  // CSS height equals device height in this fake, so rows = pixels.
  const el = {
    canvas, sink,
    paper: { style: { height: `${height}px` },
             getBoundingClientRect: () => ({ top: -shown[0], bottom: height - shown[0], height }) },
    desk: { getBoundingClientRect: () => ({ top: 0, bottom: shown[1] - shown[0] }) },
  };
  const session = {
    state: { snapshot: { state: "ready", editorState: null } },
    document: {
      widthTwips: 12474, heightTwips: 308480,
      async render(request) {
        requests.push(request);
        const reply = { pixels: new ArrayBuffer(4 * width * request.canvasHeightPx), width,
                        height: request.canvasHeightPx, documentSizeChanged: false };
        if (onRender) await onRender(request, reply, api);
        return reply;
      },
    },
  };
  class FakeImageData { constructor(data, w, h) { this.width = w; this.height = h; } }
  // eslint-disable-next-line no-new-func
  const made = new Function("session", "el", "tileWasPainted", "ImageData", "layoutCanvas", "toast", "describeError",
    `let rendering = false, renderAgain = false, lastTiles = []; let engineActionsOut = 0, busyLeftToAction = false; const RENDER_BUSY_RETRIES = 2;
     let docRows = ${height}, winTop = ${top}, changes = 0;
     const NO_OVERLAY = { key: "", selection: [], caret: null, caretTwips: null };
     let paintedOverlay = NO_OVERLAY;
     function overlayShapes() {}
     function moveSinkToCaret() {}
     function drawOverlay(c) { c.putOverlay && c.putOverlay(); }
     // SPEC-M3-link-batch §10.8 (task 2026-10-13l): the page number's recompute
     // on scroll and its re-read on a resized paint -- stubbed like the rest.
     function updatePageStatus() {}
     function showScrollBubble() {}   // SPEC-M3-scroll-page-bubble: onDeskScroll's second line; the bubble has its own tests
     const pageRectangles = { sizeChangeReported() {} };
     ${PARTS}
     ${LISTENER}
     return { renderDocument, renderBands, bandOrder, paint, RENDER_BAND_HEIGHT, windowRows, onDeskScroll,
              moveWindow,
              // What a document-invalidated does on the real page, less the repaint it asks for.
              change() { changes += 1; publishWindow(); },
              state: () => ({ rendering, renderAgain, lastTiles, changes, winTop, docRows }) };`)(
    session, el, (tile) => painted(tile), FakeImageData, () => { layouts += 1; },
    (message) => toasts.push(message), (error) => error?.code ?? String(error));
  const scrollTo = (a, b) => { shown = [a, b]; made.onDeskScroll(); };
/** A `beforeinput` on the sink, through whatever the page registered there. */
  const beforeinput = (inputType, isComposing = false) => {
    for (const [type, listener] of listeners) if (type === "beforeinput") listener({ inputType, isComposing });
  };
  const api = { ...made, ops, requests, toasts, layouts: () => layouts, session, el, beforeinput, scrollTo };
  return api;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
async function quiet(p) {
  for (let i = 0; i < 200 && p.state().rendering; i += 1) await settle();
}
const H = page().RENDER_BAND_HEIGHT;
/** How many bands a canvas of `rows` is cut into, at the page's band height. */
const bandsIn = (rows) => Math.ceil(rows / H);
const bandOf = (request, p) => Math.round(request.yTwips / p.session.document.heightTwips * p.state().docRows / H);
/** The bands overlapping the default view [9000, 11000), in document order. */
const VISIBLE = [...Array(bandsIn(22256)).keys()].filter((i) => i * H < 11000 && (i + 1) * H > 9000);

test("122 B1: the bands cover the canvas exactly, from pixel edges", () => {
  const p = page();
  const bands = p.renderBands(22256);
  assert.equal(bands.length, 22, "a 22,256-px canvas is 22 bands of 1023 (§15.6 B)");
  let top = 0;
  for (const band of bands) {
    assert.equal(band.top, top, "a gap or an overlap");
    top += band.rows;
  }
  assert.equal(top, 22256);
  assert.ok(bands.slice(0, -1).every((band) => band.rows === 1023), "a band other than the last is not 1023 rows");
  assert.equal(bands.at(-1).rows, 22256 - 21 * 1023);
});

// SPEC-M3-production-ui §16.2, 123-U: finding 123.  Every canvas height from
// one row to five bands, generated here: the bands tile the canvas, all but
// the last are a full band, and the last is never under half a band unless
// the whole canvas is.
test("123-U: no canvas height up to five bands is cut with a short last band", () => {
  const p = page();
  const half = Math.ceil(H / 2);
  for (let total = 1; total <= 5 * H; total += 1) {
    const bands = p.renderBands(total);
    let top = 0;
    for (const [i, band] of bands.entries()) {
      if (band.index !== i || band.top !== top)
        assert.fail(`height ${total}: band ${i} is index ${band.index} at ${band.top}, expected ${i} at ${top}`);
      top += band.rows;
    }
    if (top !== total) assert.fail(`height ${total}: the bands cover ${top} rows`);
    if (!bands.slice(0, -1).every((band) => band.rows === H))
      assert.fail(`height ${total}: a band other than the last is not ${H} rows`);
    const last = bands.at(-1).rows;
    if (last < Math.min(total, half) || last > H + H / 2)
      assert.fail(`height ${total}: the last band is ${last} rows, outside [${Math.min(total, half)}, ${H + H / 2}]`);
  }
  // §16.2's case and §16.8's (the 800-px window at ratio 2): 53 and 19 rows on the shipped page.
  assert.deepEqual([p.renderBands(35858).length, p.renderBands(35858).at(-1).rows], [35, 1076]);
  assert.deepEqual([p.renderBands(36847).length, p.renderBands(36847).at(-1).rows], [36, 1042]);
});

test("122 B2: the bands under the view first, then nearest first", () => {
  const p = page();
  const order = p.bandOrder(p.renderBands(22256), [9000, 11000]).map((b) => b.index);
  assert.ok(VISIBLE.length >= 2, "the view should span more than one band");
  assert.deepEqual(order.slice(0, VISIBLE.length), VISIBLE, "the visible bands first, in document order");
  const bands = p.renderBands(22256);
  const gap = (i) => { const b = bands[i]; const end = b.top + b.rows;
    return end > 9000 && b.top < 11000 ? 0 : b.top >= 11000 ? b.top - 11000 : 9000 - end; };
  const distances = order.map(gap);
  for (let i = 1; i < distances.length; i += 1)
    assert.ok(distances[i] >= distances[i - 1], `band ${order[i]} before a nearer one`);
  assert.equal(order.length, bandsIn(22256));
});

// SPEC-M3-held-key §5.1 U1 (H1, finding 132 / L-128-rapid): among the bands
// under the view, the one holding the caret is asked for first -- the first
// band of a pass is the only one a held key lets through.  Without a caret, or
// with it in the first band under the view or outside the view, B2's order.
test("132 U1: among the bands under the view, the caret's comes first; otherwise B2's order exactly", () => {
  const p = page();
  const bands = p.renderBands(22256);
  const view = [9000, 11000];
  const plain = p.bandOrder(bands, view).map((b) => b.index);
  const caretBand = VISIBLE[1];
  const order = p.bandOrder(bands, view, [caretBand * H + 70, caretBand * H + 200]).map((b) => b.index);
  assert.equal(order[0], caretBand, "the caret's band is not asked for first");
  assert.deepEqual(order.slice(1), plain.filter((i) => i !== caretBand), "the other bands moved");
  for (const other of [[VISIBLE[0] * H + 900, VISIBLE[0] * H + 1000], [500, 630], null])
    assert.deepEqual(p.bandOrder(bands, view, other).map((b) => b.index), plain, `caret rows ${JSON.stringify(other)}`);
});

// U2: and renderDocument passes the engine's caret.
test("132 U2: a pass starts with the band holding the engine's caret; with no caret, with the view's first band", async () => {
  const caretBand = VISIBLE[1];
  const p = page();
  const twipsPerRow = p.session.document.heightTwips / 22256;
  p.session.state.snapshot.editorState = {
    caret: { x: 0, y: Math.round((caretBand * H + 70) * twipsPerRow), width: 0, height: 1800 },
    selection: { collapsed: true, rectangles: [] },
  };
  await p.renderDocument();
  await quiet(p);
  assert.equal(bandOf(p.requests[0], p), caretBand, "the pass did not start with the caret's band");
  assert.deepEqual(new Set(p.requests.map((r) => bandOf(r, p))).size, bandsIn(22256), "a band was not asked for");
  const q = page();
  await q.renderDocument();
  await quiet(q);
  assert.equal(bandOf(q.requests[0], q), VISIBLE[0], "without a caret the pass did not start at the top of the view");
});

test("122 B3: a change between bands ends the pass, and the next pass starts with the view again", async () => {
  let interrupted = false;
  const p = page({
    onRender: async (request, reply, api) => {
      if (!interrupted) { interrupted = true; api.change(); void api.renderDocument(); }   // a document-invalidated arrives
    },
  });
  await p.renderDocument();
  await quiet(p);
  const order = p.requests.map((r) => r.yTwips);
  const first = order[0];
  // Pass 1 asked for the view's first band, then stopped; pass 2 asked for it again first.
  assert.equal(order[1], first, "the interrupted pass went on instead of restarting with the view");
  assert.equal(p.requests.length, 1 + bandsIn(22256), "pass 2 did not cover every band");
});

test("122 B4: each band is blitted when it arrives, before the next band is asked for", async () => {
  const p = page();
  const seen = [];
  const original = p.session.document.render.bind(p.session.document);
  p.session.document.render = async (request) => {
    seen.push(p.ops.filter((op) => op[0] === "blit").length);
    return original(request);
  };
  await p.renderDocument();
  await quiet(p);
  assert.deepEqual(seen, [...Array(bandsIn(22256)).keys()], "a band was held back until the end of the pass");
  const tiles = p.state().lastTiles;
  assert.equal(tiles.length, bandsIn(22256));
  assert.ok(tiles.every((t, i) => t && t.y === i * H), "lastTiles is not one band per slot in document order");
});

test("122 B5: a document whose size changed is laid out again and painted in full", async () => {
  let once = false;
  const p = page({ onRender: async (request, reply) => { if (!once) { once = true; reply.documentSizeChanged = true; } } });
  await p.renderDocument();
  await quiet(p);
  assert.equal(p.layouts(), 1);
  assert.equal(p.requests.length, 1 + bandsIn(22256), "the pass after the relayout did not cover every band");
});

test("122 B6: a band the engine did not paint still raises TILE_NOT_PAINTED", async () => {
  const p = page({ painted: () => false });
  await p.renderDocument();
  await quiet(p);
  assert.equal(p.toasts.length, 1);
  assert.match(p.toasts[0], /TILE_NOT_PAINTED/);
});

test("122 B7: nothing is cleared; a band keeps its old pixels until its new ones arrive", async () => {
  const p = page();
  await p.renderDocument();
  await quiet(p);
  p.change();
  await p.renderDocument();
  await quiet(p);
  assert.ok(!p.ops.some((op) => op[0] === "clear"), "the canvas was cleared");
  // The overlay redrawn with each band is clipped to that band's rows.
  const clips = p.ops.filter((op) => op[0] === "clipRect");
  const blits = p.ops.filter((op) => op[0] === "blit");
  assert.equal(blits.length, 2 * bandsIn(22256), "the pass after the change did not paint every band again");
  assert.equal(clips.length, blits.length);
  assert.ok(clips.every((c, i) => c[1] === blits[i][1] && c[2] === blits[i][2]));
});

test("122 B8: a key that will reach the engine, mid-pass, ends the pass after the band in flight; the next pass starts with the view", async () => {
  const n = bandsIn(22256);
  const ENDS_AT = VISIBLE.length + 2;   // an off-screen band, well inside the pass
  let blitsWhenAsked = [];
  const p = page({
    onRender: async (request, reply, api) => {
      blitsWhenAsked.push(api.ops.filter((op) => op[0] === "blit").length);
      // Typed while this band is in flight; the change is what its insert
      // will be once it reaches the engine (the counter, not the repaint).
      if (api.requests.length === ENDS_AT) { api.beforeinput("insertText"); api.change(); }
    },
  });
  await p.renderDocument();
  await quiet(p);
  const bands = p.requests.map((r) => bandOf(r, p));
  assert.equal(p.requests.length, ENDS_AT + n,
    `the pass did not end after the band in flight (asked ${p.requests.length}, expected ${ENDS_AT} + a full pass of ${n})`);
  assert.equal(blitsWhenAsked[ENDS_AT], ENDS_AT, "the band in flight was not blitted before the next pass");
  assert.deepEqual(bands.slice(ENDS_AT, ENDS_AT + VISIBLE.length), VISIBLE, "the next pass did not start with the view");
  assert.equal(new Set(bands.slice(ENDS_AT)).size, n, "the next pass did not cover every band");
  assert.equal(p.state().renderAgain, false);
});

test("122 B8-control: a beforeinput while idle sets nothing and starts no pass; a composition update mid-pass ends nothing", async () => {
  const idle = page();
  for (const type of ["insertText", "insertParagraph", "deleteContentBackward"]) idle.beforeinput(type);
  await settle();
  assert.equal(idle.state().renderAgain, false, "an idle beforeinput set renderAgain");
  assert.equal(idle.state().rendering, false);
  assert.equal(idle.requests.length, 0, "an idle beforeinput started a pass");

  const n = bandsIn(22256);
  const composing = page({
    onRender: async (request, reply, api) => {
      if (api.requests.length === 2) {
        api.beforeinput("insertCompositionText");
        api.beforeinput("insertText", true);
      }
    },
  });
  await composing.renderDocument();
  await quiet(composing);
  assert.equal(composing.requests.length, n, "a composition update ended the pass");
});

// ------------------------------------------------------------------ release C′
// SPEC-M3-production-ui §17.9 (a) C1′, (c) the change counter, (g) S1 / S2;
// §17.5 "unit" and the ruling's conditions 2 and 3 (the unit halves).

test("C1-U: the window is three views, never under four bands, never more than the document", () => {
  const p = page();
  const FOUR = 4 * H;
  // (desk height in CSS px, backing px per CSS px): Chrome's default 800 x 600
  // leaves a 139-px desk; 470 is the host page's desk in that window; 540 at
  // 1400 x 1000; 1364 / 1365 and 682 / 683 are where the 3x term starts to
  // decide; a 4K screen at 200 % is a 2,000-px desk at scale 2.
  const desks = [[139, 1], [139, 2], [470, 1], [540, 1], [540, 1.5], [540, 2], [960, 2],
                 [1364, 1], [1365, 1], [682, 2], [683, 2], [2000, 2], [2000, 1]];
  for (const [desk, scale] of desks) {
    for (const doc of [1012, 3298, FOUR, 22256, 98869]) {
      const w = p.windowRows(doc, desk, scale);
      const view = Math.floor(desk * scale);
      const where = `desk ${desk} x ${scale}, document ${doc} rows: window ${w}`;
      assert.ok(w <= doc, `${where} is taller than the document`);
      assert.ok(w >= Math.min(doc, FOUR), `${where} is under four bands`);
      assert.ok(w >= Math.min(doc, 3 * view), `${where} is under three views`);
      assert.ok(w <= Math.max(3 * view, FOUR), `${where} is more than both terms ask for`);
    }
  }
  // The two the ruling names (condition 2), and one whole A4 page at the width cap.
  assert.equal(p.windowRows(98869, 139, 1), FOUR, "Chrome's default desk: the floor decides");
  assert.equal(p.windowRows(98869, 2000, 2), 12000, "a 4K desk at 200 %: three views decide");
  assert.equal(p.windowRows(98869, 1365, 1), 4095);
  assert.equal(p.windowRows(98869, 683, 2), 4098);
  assert.ok(p.windowRows(98869, 139, 2) >= Math.ceil(2400 * 1.374), "one A4 page at the width cap does not fit");
});

/** Indices of the bands a run of requests asked for, in order. */
const asked = (p, from = 0) => p.requests.slice(from).map((r) => bandOf(r, p));
/** The bands overlapping document rows [top, top + rows), in document order. */
const overlapping = (top, rows) => [...Array(bandsIn(22256)).keys()].filter((i) => i * H < top + rows && (i + 1) * H > top);

test("W-U1: a pass asks only for the stale bands in the window; nothing changed, nothing asked", async () => {
  const p = page({ rows: 4 * H, top: 8000 });
  await p.renderDocument();
  await quiet(p);
  const window = overlapping(8000, 4 * H);
  assert.deepEqual([...asked(p)].sort((a, b) => a - b), window, "the first pass did not ask for exactly the window's bands");
  const first = p.requests.length;
  await p.renderDocument();
  await quiet(p);
  assert.equal(p.requests.length, first, "a pass with nothing changed asked the engine for pixels");
  p.change();
  await p.renderDocument();
  await quiet(p);
  assert.deepEqual([...asked(p, first)].sort((a, b) => a - b), window, "after a change the window's bands were not all asked for again");
});

test("W-U2: a band stamped when it is ASKED for -- one in flight across a change is asked for again", async () => {
  let n = 0;
  const p = page({
    rows: 4 * H, top: 8000,
    // A change while the second band of the pass is in flight, without a repaint.
    onRender: async (request, reply, api) => { n += 1; if (n === 2) api.change(); },
  });
  await p.renderDocument();
  await quiet(p);
  const pass = asked(p);
  assert.equal(pass.length, 5);
  const before = p.requests.length;
  await p.renderDocument();
  await quiet(p);
  assert.deepEqual(asked(p, before), pass.slice(0, 2),
    "the next pass did not ask again for exactly the band finished before the change and the one in flight across it");
});

test("W-U3: the window follows the scroll; the cache holds the window only", async () => {
  const p = page({ rows: 4 * H, top: 8000 });
  await p.renderDocument();
  await quiet(p);
  const first = p.requests.length;
  p.scrollTo(15000, 17000);                     // far below: the window moves
  await quiet(p);
  const { winTop } = p.state();
  assert.equal(winTop, 16000 - 2 * H, "the window was not centred on the view");
  const held = p.state().lastTiles.map((t, i) => (t ? i : null)).filter((i) => i !== null);
  assert.deepEqual(held, overlapping(winTop, 4 * H), "the cache holds bands outside the window");
  assert.deepEqual([...asked(p, first)].sort((a, b) => a - b), overlapping(winTop, 4 * H),
    "the move did not ask for the new window's bands, or asked for others");
  // Back where it was: those bands were dropped, so they are asked for again.
  const second = p.requests.length;
  p.scrollTo(9000, 11000);
  await quiet(p);
  assert.deepEqual([...asked(p, second)].sort((a, b) => a - b), overlapping(p.state().winTop, 4 * H));
});

test("W-U4: a move puts the cached bands back at their new rows and clears the rest; only the uncached are asked for", async () => {
  const p = page({ rows: 4 * H, top: 8000 });
  await p.renderDocument();
  await quiet(p);
  p.ops.length = 0;
  const first = p.requests.length;
  p.scrollTo(10600, 12600);   // the view's bottom is inside the last quarter: move
  const { winTop } = p.state();
  assert.equal(winTop, 11600 - 2 * H);
  const now = overlapping(winTop, 4 * H);
  const kept = now.filter((i) => overlapping(8000, 4 * H).includes(i));
  const blits = p.ops.filter((op) => op[0] === "blit").map((op) => op[1]);
  const clears = p.ops.filter((op) => op[0] === "clear").map((op) => op[1]);
  assert.deepEqual(blits, kept.map((i) => i * H - winTop), "a cached band was not put back at its row on the moved canvas");
  assert.deepEqual(clears, now.filter((i) => !kept.includes(i)).map((i) => i * H - winTop), "an uncached band's rows were not cleared");
  await quiet(p);
  assert.deepEqual([...asked(p, first)].sort((a, b) => a - b), now.filter((i) => !kept.includes(i)),
    "a band still current was asked for again, or an uncached one was not");
});

test("W-U5 (S1): no move when the whole document is on the canvas, or the window is against the document's end", async () => {
  const whole = page();
  await whole.renderDocument();
  await quiet(whole);
  const n = whole.requests.length;
  whole.scrollTo(20000, 22000);
  await quiet(whole);
  assert.equal(whole.state().winTop, 0);
  assert.equal(whole.requests.length, n, "a scroll over a whole-document canvas asked for pixels");
  const end = page({ rows: 4 * H, top: 22256 - 4 * H, view: [20000, 22000] });
  await end.renderDocument();
  await quiet(end);
  const m = end.requests.length;
  end.ops.length = 0;
  end.scrollTo(20200, 22200);   // into the last quarter, but the window cannot go lower
  await quiet(end);
  assert.equal(end.state().winTop, 22256 - 4 * H);
  assert.equal(end.ops.length, 0, "the window was redrawn without moving");
  assert.equal(end.requests.length, m);
});

test("W-U6 (S2): a band the window left while it was in flight is neither drawn nor kept", async () => {
  let n = 0;
  const p = page({
    rows: 4 * H, top: 8000,
    onRender: async (request, reply, api) => { n += 1; if (n === 1) api.scrollTo(15000, 17000); },
  });
  await p.renderDocument();
  await quiet(p);
  const firstBand = bandOf(p.requests[0], p);
  const { winTop } = p.state();
  assert.ok(!overlapping(winTop, 4 * H).includes(firstBand), "the case needs the first band outside the moved window");
  assert.equal(p.state().lastTiles[firstBand] ?? null, null, "a band outside the window was kept");
  const blitted = p.ops.filter((op) => op[0] === "blit").map((op) => op[1] + winTop);
  assert.ok(!blitted.includes(firstBand * H), "a band outside the window was drawn");
});

test("W-U7: the window, the counter and the cached bands are on #canvas", async () => {
  const p = page({ rows: 4 * H, top: 8000 });
  await p.renderDocument();
  await quiet(p);
  p.change();
  const data = p.el.canvas.dataset;
  assert.equal(data.window, `22256 8000 ${4 * H}`);
  assert.equal(data.changes, "1");
  assert.equal(data.bands, overlapping(8000, 4 * H).map((i) => `${i}:${i * H}:${H}:0`).join(" "));
});
