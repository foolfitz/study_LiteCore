// SPEC-M3-production-ui §15.2, 122-U: finding 122's banded repaint (fable's
// ruling B′).  The page's own functions are taken from its source and run
// against a recording canvas and a fake engine, so these test the page's code.
// §15.6 (fable's third ruling, A+B): B1 restated for bands of
// floor(32767/32) = 1023 rows, the other counts follow the page's constant,
// and B8 / B8-control test A (a key that will reach the engine ends a pass).

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
const PARTS = [
  slice(/^const MAX_TILE_HEIGHT = .*;$/m, "MAX_TILE_HEIGHT"),
  slice(/^const RENDER_BAND_HEIGHT = .*;$/m, "RENDER_BAND_HEIGHT"),
  fn("renderBands"), fn("bandOrder"), fn("visibleCanvasRows"), fn("renderDocument"), fn("paint"), fn("paintBand"),
  slice(/^const DELETE_INPUT_TYPES = \{[\s\S]*?\n\};$/m, "DELETE_INPUT_TYPES"),
  slice(/^const ENGINE_INPUT_TYPES = new Set\(\[[\s\S]*?\n\]\);$/m, "ENGINE_INPUT_TYPES"),
  fn("endRenderPassOnInput"),
].join("\n");
// A's registration, taken from the page as it stands: if the page stops
// registering it, B8 sees the pass run on (a behaviour, not a missing string).
const LISTENER = SOURCE.match(/^el\.sink\.addEventListener\("beforeinput", endRenderPassOnInput\);$/m)?.[0] ?? "";

/** A page around the real functions: canvas, desk, session and engine are recordings. */
function page({ height = 22256, width = 10, view = [9000, 11000], onRender = null, painted = () => true } = {}) {
  const ops = [];
  const requests = [];
  const toasts = [];
  let layouts = 0;
  const context = {
    putImageData(image, x, y) { ops.push(["blit", y, image.height]); },
    save() { ops.push(["save"]); }, restore() { ops.push(["restore"]); }, beginPath() {},
    rect(x, y, w, h) { ops.push(["clipRect", y, h]); }, clip() {},
    clearRect() { ops.push(["clear"]); }, fillRect() {},
  };
  const canvas = {
    width, height,
    getContext: () => context,
    // CSS height equals device height in this fake, so rows = pixels.
    getBoundingClientRect: () => ({ top: -view[0], bottom: height - view[0], height }),
  };
  const listeners = [];
  const sink = { addEventListener(type, listener) { listeners.push([type, listener]); } };
  const el = { canvas, sink, desk: { getBoundingClientRect: () => ({ top: 0, bottom: view[1] - view[0] }) } };
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
    `let rendering = false, renderAgain = false, lastTiles = []; const RENDER_BUSY_RETRIES = 2;
     function drawOverlay(c) { c.putOverlay && c.putOverlay(); }
     ${PARTS}
     ${LISTENER}
     return { renderDocument, renderBands, bandOrder, paint, RENDER_BAND_HEIGHT,
              state: () => ({ rendering, renderAgain, lastTiles }) };`)(
    session, el, (tile) => painted(tile), FakeImageData, () => { layouts += 1; },
    (message) => toasts.push(message), (error) => error?.code ?? String(error));
  /** A `beforeinput` on the sink, through whatever the page registered there. */
  const beforeinput = (inputType, isComposing = false) => {
    for (const [type, listener] of listeners) if (type === "beforeinput") listener({ inputType, isComposing });
  };
  const api = { ...made, ops, requests, toasts, layouts: () => layouts, session, el, beforeinput };
  return api;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
async function quiet(p) {
  for (let i = 0; i < 200 && p.state().rendering; i += 1) await settle();
}
const H = page().RENDER_BAND_HEIGHT;
/** How many bands a canvas of `rows` is cut into, at the page's band height. */
const bandsIn = (rows) => Math.ceil(rows / H);
const bandOf = (request, p) => Math.round(request.yTwips / p.session.document.heightTwips * p.el.canvas.height / H);
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

test("122 B3: a change between bands ends the pass, and the next pass starts with the view again", async () => {
  let interrupted = false;
  const p = page({
    onRender: async (request, reply, api) => {
      if (!interrupted) { interrupted = true; void api.renderDocument(); }   // a document-invalidated arrives
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
  await p.renderDocument();
  await quiet(p);
  assert.ok(!p.ops.some((op) => op[0] === "clear"), "the canvas was cleared");
  // The overlay redrawn with each band is clipped to that band's rows.
  const clips = p.ops.filter((op) => op[0] === "clipRect");
  const blits = p.ops.filter((op) => op[0] === "blit");
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
      if (api.requests.length === ENDS_AT) api.beforeinput("insertText");   // typed while this band is in flight
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
