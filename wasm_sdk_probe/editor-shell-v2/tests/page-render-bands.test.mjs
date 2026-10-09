// SPEC-M3-production-ui §15.2, 122-U: finding 122's banded repaint (fable's
// ruling B′).  The page's own functions are taken from its source and run
// against a recording canvas and a fake engine, so these test the page's code.

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
].join("\n");

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
  const el = { canvas, desk: { getBoundingClientRect: () => ({ top: 0, bottom: view[1] - view[0] }) } };
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
     return { renderDocument, renderBands, bandOrder, paint,
              state: () => ({ rendering, renderAgain, lastTiles }) };`)(
    session, el, (tile) => painted(tile), FakeImageData, () => { layouts += 1; },
    (message) => toasts.push(message), (error) => error?.code ?? String(error));
  const api = { ...made, ops, requests, toasts, layouts: () => layouts, session, el };
  return api;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));
async function quiet(p) {
  for (let i = 0; i < 200 && p.state().rendering; i += 1) await settle();
}
const bandOf = (request, p) => Math.round(request.yTwips / p.session.document.heightTwips * p.el.canvas.height / 2047);

test("122 B1: the bands cover the canvas exactly, from pixel edges", () => {
  const p = page();
  const bands = p.renderBands(22256);
  assert.equal(bands.length, 11, "a 22,256-px canvas is 11 bands of 2047");
  let top = 0;
  for (const band of bands) {
    assert.equal(band.top, top, "a gap or an overlap");
    top += band.rows;
  }
  assert.equal(top, 22256);
  assert.equal(bands.at(-1).rows, 22256 - 10 * 2047);
});

test("122 B2: the bands under the view first, then nearest first", () => {
  const p = page();
  const order = p.bandOrder(p.renderBands(22256), [9000, 11000]).map((b) => b.index);
  assert.deepEqual(order.slice(0, 2), [4, 5], "the visible bands (8188-10235, 10235-12282) first");
  const bands = p.renderBands(22256);
  const gap = (i) => { const b = bands[i]; const end = b.top + b.rows;
    return end > 9000 && b.top < 11000 ? 0 : b.top >= 11000 ? b.top - 11000 : 9000 - end; };
  const distances = order.map(gap);
  for (let i = 1; i < distances.length; i += 1)
    assert.ok(distances[i] >= distances[i - 1], `band ${order[i]} before a nearer one`);
  assert.equal(order.length, 11);
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
  assert.equal(p.requests.length, 1 + 11, "pass 2 did not cover every band");
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
  assert.deepEqual(seen, [...Array(11).keys()], "a band was held back until the end of the pass");
  const tiles = p.state().lastTiles;
  assert.equal(tiles.length, 11);
  assert.ok(tiles.every((t, i) => t && t.y === i * 2047), "lastTiles is not one band per slot in document order");
});

test("122 B5: a document whose size changed is laid out again and painted in full", async () => {
  let once = false;
  const p = page({ onRender: async (request, reply) => { if (!once) { once = true; reply.documentSizeChanged = true; } } });
  await p.renderDocument();
  await quiet(p);
  assert.equal(p.layouts(), 1);
  assert.equal(p.requests.length, 1 + 11, "the pass after the relayout did not cover every band");
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
