// SPEC-M3-production-ui §16.2, P-U: release P's `paint()` -- only the caret and
// the selection are brought up to date, by dirty-rectangle restores from the
// cached bands.  The page's own functions are taken from its source and run
// against a canvas that models its pixels: each pixel holds the band image it
// was last put from (or "clear"), how many selection washes and whether a caret
// were drawn over it since.  So besides the calls each case names, every case
// checks what is ON the canvas: in a painted band, the band's image under
// exactly the current overlay (each selection rectangle once -- the wash is a
// multiply -- and the caret); in a band not painted yet, nothing but marks of
// the current overlay.
//
// Release C′ (§17.2, §17.5): the canvas is a window onto the document, rows
// [winTop, winTop + canvas.height).  Every case runs twice: on a canvas that
// is the whole document (the P page's shape) and on a window that starts
// inside a band (`winTop` 1746 of a seven-band document), with every row and
// band of the case moved two bands down the document -- "P-U1-U5 hold at
// winTop != 0".

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
  slice(/^const NO_OVERLAY = .*;$/m, "NO_OVERLAY"),
  fn("renderBands"), fn("paint"), fn("overlayAreas"), fn("paintBand"), fn("overlayShapes"), fn("drawOverlay"),
  fn("layoutCanvas"), fn("windowRows"), fn("windowTopFor"), fn("placeCanvas"), fn("publishWindow"),
  fn("visibleDocRows"),
  // SPEC-M3-held-key §3.3 (H3): the state the overlay draws, and what it keeps.
  // Taken when the page has them, so that on a page without them U5 fails by
  // name rather than this whole file failing to load.
  SOURCE.match(/^let overlayState = .*;$/m)?.[0] ?? "",
  SOURCE.match(/^function overlayEditorState\([^)]*\) \{[\s\S]*?\n\}$/m)?.[0] ?? "",
].join("\n");

/** A canvas whose 2d context records its calls and models its pixels. */
function modelCanvas(initialWidth, initialHeight) {
  const ops = [];
  let width = 0, height = 0, base, sel, caret;
  const allocate = () => {
    base = new Int32Array(width * height).fill(-1);
    sel = new Uint8Array(width * height);
    caret = new Uint8Array(width * height);
  };
  let state = { clips: [], composite: "source-over", fill: "#000000" };
  const stack = [];
  let path = [];
  const inClip = (i, j) => state.clips.every((rects) =>
    rects.some(([x, y, w, h]) => i + 0.5 >= x && i + 0.5 < x + w && j + 0.5 >= y && j + 0.5 < y + h));
  const each = (x0, y0, x1, y1, f) => {
    for (let j = Math.max(0, y0); j < Math.min(height, y1); j += 1)
      for (let i = Math.max(0, x0); i < Math.min(width, x1); i += 1) f(j * width + i, i, j);
  };
  const context = {
    get globalCompositeOperation() { return state.composite; },
    set globalCompositeOperation(v) { state.composite = v; },
    get fillStyle() { return state.fill; },
    set fillStyle(v) { state.fill = v; },
    save() { stack.push(state); state = { ...state, clips: [...state.clips] }; },
    restore() { state = stack.pop(); },
    beginPath() { path = []; },
    rect(x, y, w, h) { path.push([x, y, w, h]); },
    clip() { state.clips.push(path); },
    putImageData(image, dx, dy, ...rest) {
      ops.push(["put", image.id, dy, rest.length ? [...rest] : null]);
      let [rx, ry, rw, rh] = rest.length ? rest : [0, 0, image.width, image.height];
      const x0 = Math.max(0, rx), y0 = Math.max(0, ry);
      const x1 = Math.min(image.width, rx + rw), y1 = Math.min(image.height, ry + rh);
      // putImageData ignores the clip and the composite mode.
      each(dx + x0, dy + y0, dx + x1, dy + y1, (k) => { base[k] = image.id; sel[k] = 0; caret[k] = 0; });
    },
    clearRect(x, y, w, h) {
      ops.push(["clear", x, y, w, h]);
      each(Math.floor(x), Math.floor(y), Math.ceil(x + w), Math.ceil(y + h), (k, i, j) => {
        if (inClip(i, j)) { base[k] = -1; sel[k] = 0; caret[k] = 0; }
      });
    },
    fillRect(x, y, w, h) {
      ops.push(["fill", state.fill, x, y, w, h]);
      // Every pixel the rectangle covers with positive area, inside the clip.
      each(Math.floor(x), Math.floor(y), Math.ceil(x + w), Math.ceil(y + h), (k, i, j) => {
        if (!inClip(i, j)) return;
        if (state.fill === "#b7d3f2") sel[k] += 1;
        else if (state.fill === "#1a1a1a") caret[k] = 1;
      });
    },
  };
  const canvas = {
    get width() { return width; }, set width(v) { width = v; allocate(); },
    get height() { return height; }, set height(v) { height = v; allocate(); },
    style: {}, dataset: {}, clientWidth: 0, clientHeight: 0,
    getContext: () => context,
  };
  canvas.width = initialWidth;
  canvas.height = initialHeight;
  return { canvas, ops, pixels: () => ({ width, height, base, sel, caret }) };
}

/**
 * The page around its real functions: a document of `width` x `doc` backing
 * pixels, 100 twips a pixel, and a canvas of `rows` rows over document rows
 * [top, top + rows).  `shift` / `bandShift` move a case's rows and bands down
 * the document, so one case reads the same in both shapes.
 */
const SHAPES = {
  whole: { doc: 3 * 1023, rows: 3 * 1023, top: 0, shift: 0, bandShift: 0 },
  window: { doc: 7 * 1023, rows: 4 * 1023, top: 2 * 1023 - 300, shift: 2 * 1023, bandShift: 2 },
};

function page({ width = 24, shape = SHAPES.whole } = {}) {
  const model = modelCanvas(width, shape.rows);
  const sunk = [];
  const session = {
    state: { snapshot: { editorState: null } },
    document: { widthTwips: width * 100, heightTwips: shape.doc * 100 },
  };
  // layoutCanvas: the desk is as wide as gives back this canvas width (cssWidth >= 320),
  // as tall as gives a four-band window, and shows document rows around the window's centre.
  const centre = shape.top + shape.rows / 2;
  const el = {
    canvas: model.canvas,
    desk: { clientWidth: width + 40, clientHeight: 200,
            getBoundingClientRect: () => ({ top: 0, bottom: 200 }) },
    paper: { style: {}, getBoundingClientRect: () => ({ top: -(centre - 100), bottom: shape.doc - (centre - 100), height: shape.doc }) },
  };
  class FakeImage { constructor(id, w, h) { this.id = id; this.width = w; this.height = h; } }
  let images = 0;
  // eslint-disable-next-line no-new-func
  const made = new Function("session", "el", "moveSinkToCaret",
    `const MAX_BACKING_WIDTH = 2400; let lastTiles = []; let lastProjectedParagraphs = null;
     let docRows = ${shape.doc}, winTop = ${shape.top}, changes = 0;
     let deletesInFlight = 0;
     function positionProjection() {}
     ${PARTS}
     return {
       paint, layoutCanvas, renderBands, overlayShapes, RENDER_BAND_HEIGHT,
       tiles: () => lastTiles, window: () => ({ docRows, winTop }),
       setDeletes(n) { deletesInFlight = n; },
       // What renderDocument does: a slot per band, then each band as its reply arrives.
       allocate() { lastTiles = new Array(renderBands(docRows).length).fill(null); },
       band(index, image) {
         const b = renderBands(docRows)[index];
         const strip = { image, y: b.top, label: changes };
         lastTiles[b.index] = strip;
         paintBand(strip);
       },
     };`)(session, el, (caret) => sunk.push(caret));
  const api = {
    ...made, ...model, session, el, sunk, shape,
    newImage(index) {
      const b = made.renderBands(made.window().docRows)[index];
      return new FakeImage((images += 1), el.canvas.width, b.rows);
    },
    /** Bands by the case's numbering: band i of the case is band i + bandShift of the document. */
    paintBands(...indexes) { for (const i of indexes) made.band(i + shape.bandShift, api.newImage(i + shape.bandShift)); },
    /** A state write, as updateState() makes one: a new editorState, then paint(). */
    state(editorState) { session.state.snapshot = { editorState }; made.paint(); },
    /** The case's row y as a canvas row. */
    row: (y) => y + shape.shift - made.window().winTop,
    caretAt: (yPx, xPx = 5) => caretAt(yPx + shape.shift, xPx),
    selectionOf: (...rects) => selectionOf(...rects.map(([x, y, w, h]) => [x, y + shape.shift, w, h])),
    clearOps() { model.ops.length = 0; },
    puts: () => model.ops.filter((op) => op[0] === "put"),
    clears: () => model.ops.filter((op) => op[0] === "clear"),
    fills: () => model.ops.filter((op) => op[0] === "fill"),
  };
  return api;
}

const caretAt = (yPx, xPx = 5) => ({
  caret: { x: xPx * 100, y: yPx * 100, width: 0, height: 1800 },
  selection: { collapsed: true, rectangles: [] },
});
const selectionOf = (...rects) => ({
  caret: { x: 300, y: rects[0][1] * 100, width: 0, height: 1800 },
  selection: { collapsed: false, rectangles: rects.map(([x, y, w, h]) => ({ x: x * 100, y: y * 100, width: w * 100, height: h * 100 })) },
});

/** In painted bands: the band's image under exactly the current overlay.  In unpainted ones: no stale mark. */
function assertCanvasCurrent(p, what) {
  const { width, height, base, sel, caret } = p.pixels();
  const shapes = p.overlayShapes() ?? { selection: [], caret: null };
  const touches = ([x, y, w, h], i, j) => x < i + 1 && x + w > i && y < j + 1 && y + h > j;
  const { docRows, winTop } = p.window();
  const bands = p.renderBands(docRows);
  const tiles = p.tiles();
  for (const band of bands) {
    const strip = tiles[band.index];
    const first = Math.max(0, band.top - winTop), last = Math.min(height, band.top + band.rows - winTop);
    for (let j = first; j < last; j += 1) {
      for (let i = 0; i < width; i += 1) {
        const k = j * width + i;
        const wantSel = shapes.selection.filter((r) => touches(r, i, j)).length;
        const wantCaret = shapes.caret && touches(shapes.caret, i, j) ? 1 : 0;
        const where = `${what}: pixel (${i}, ${j}) in band ${band.index}`;
        if (strip) {
          if (base[k] !== strip.image.id) assert.fail(`${where} shows image ${base[k]}, not the band's ${strip.image.id}`);
          if (sel[k] !== wantSel) assert.fail(`${where} has ${sel[k]} selection washes, the overlay has ${wantSel}`);
          if (caret[k] !== wantCaret) assert.fail(`${where} caret ${caret[k]}, the overlay ${wantCaret}`);
        } else {
          if (base[k] !== -1) assert.fail(`${where} (not painted) shows image ${base[k]}`);
          if (sel[k] > wantSel || caret[k] > wantCaret) assert.fail(`${where} (not painted) has a stale mark`);
        }
      }
    }
  }
}

const H = 1023;

for (const [name, shape] of Object.entries(SHAPES)) {

test(`P-U1 (${name}): an overlay equal to the one on the canvas costs no putImageData and no clearRect`, () => {
  const p = page({ shape });
  p.allocate();
  p.paintBands(0, 1, 2);
  p.state(p.caretAt(1500));
  p.clearOps();
  // The writes typing makes around a key that do not move the caret: pending, busy, pending, ready.
  for (let i = 0; i < 4; i += 1) p.state(p.caretAt(1500));
  assert.equal(p.puts().length, 0, `${p.puts().length} putImageData on an unchanged overlay`);
  assert.equal(p.clears().length, 0, `${p.clears().length} clearRect on an unchanged overlay`);
  assert.equal(p.fills().length, 0, "the overlay was drawn again");
  assert.equal(p.sunk.length > 0, true, "the sink stopped following the caret");
  assertCanvasCurrent(p, "after four unchanged writes");
});

test(`P-U2 (${name}): a caret that moves is restored from the bands under its old and new rectangles only`, () => {
  const p = page({ shape });
  p.allocate();
  p.paintBands(0, 1, 2);
  p.state(p.caretAt(400));
  p.clearOps();
  p.state(p.caretAt(1500));   // band 0 -> band 1
  const puts = p.puts();
  assert.ok(puts.length > 0 && puts.every((op) => op[3] !== null), "a whole band was put back");
  const covered = (row) => puts.some(([, , dy, [, ry, , rh]]) => dy + ry <= row && row < dy + ry + rh);
  for (const row of [399, 400, 417, 418, 1499, 1500, 1517, 1518])
    assert.ok(covered(p.row(row)), `row ${row} (old or new caret, widened by one) was not restored`);
  const rows = puts.reduce((n, [, , , [, , , rh]]) => n + rh, 0);
  assert.ok(rows <= 2 * (18 + 3), `${rows} rows restored for two carets 18 rows tall`);
  assert.equal(p.clears().length, 0);
  assert.ok(p.fills().some((op) => op[1] === "#1a1a1a"), "the caret was not drawn");
  assertCanvasCurrent(p, "after the caret moved");

  // And over a sequence: carets and selections, bands replaced in between, the
  // canvas always the bands under exactly the current overlay.
  let seed = 7;
  const random = (n) => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed % n; };
  for (let step = 0; step < 60; step += 1) {
    if (random(4) === 0) p.paintBands(random(3));
    const y = random(3 * H - 30);
    p.state(random(3) === 0
      ? p.selectionOf([random(10), y, 5 + random(10), 18], [0, y + 18, 3 + random(20), 18])
      : p.caretAt(y, random(20)));
    assertCanvasCurrent(p, `step ${step}`);
  }
});

test(`P-U3 (${name}): a selection that changes is restored under every old and every new rectangle, washed once`, () => {
  const p = page({ shape });
  p.allocate();
  p.paintBands(0, 1, 2);
  p.state(p.selectionOf([2, 1000, 20, 18], [0, 1018, 12, 18]));   // across the band edge at 1023
  assertCanvasCurrent(p, "the first selection");
  p.clearOps();
  p.state(p.selectionOf([4, 1018, 18, 18], [0, 1036, 15, 18], [0, 1054, 6, 18]));
  const puts = p.puts();
  assert.ok(puts.every((op) => op[3] !== null), "a whole band was put back");
  for (const row of [999, 1000, 1035, 1036, 1053, 1054, 1071, 1072])
    assert.ok(puts.some(([, , dy, [, ry, , rh]]) => dy + ry <= p.row(row) && p.row(row) < dy + ry + rh), `row ${row} was not restored`);
  // The wash overlaps itself where two rectangles overlap -- as a full draw does -- and nowhere else twice.
  assertCanvasCurrent(p, "the second selection");
  assert.ok(!p.fills().some((op) => op[1] === "#1a1a1a"), "a caret drawn inside a range selection");
  p.state(p.caretAt(1040, 6));   // collapsed again: every wash gone
  assertCanvasCurrent(p, "back to a caret");
});

test(`P-U4 (${name}): after layoutCanvas the first paint() restores nothing of the overlay drawn before it`, () => {
  const p = page({ width: 400, shape });
  p.layoutCanvas();
  assert.deepEqual(p.window(), { docRows: shape.doc, winTop: shape.top }, "layoutCanvas placed the window elsewhere");
  p.allocate();
  p.paintBands(0, 1, 2);
  p.state(p.caretAt(400));
  // A resize to the same size: the canvas is cleared, the bands are asked for
  // again, and a state write lands before the first of them.
  p.layoutCanvas();
  p.allocate();
  p.clearOps();
  p.state(p.caretAt(1500));
  const areas = p.clears();
  assert.ok(areas.length > 0, "the new caret's area was not cleared before drawing it");
  assert.ok(areas.every(([, , y]) => y >= p.row(1400)), `a rectangle of the overlay from before the layout was restored: ${JSON.stringify(areas)}`);
  assert.equal(p.puts().length, 0, "restored from a band that no longer exists");
  // The overlay drawn before the layout, again: the cleared canvas does not carry it, so it is drawn.
  p.clearOps();
  p.state(p.caretAt(400));
  p.layoutCanvas();
  p.allocate();
  p.state(p.caretAt(400));
  assert.ok(p.fills().some((op) => op[1] === "#1a1a1a"), "an overlay equal to the one before the layout was not drawn");
  p.paintBands(0, 1, 2);
  assertCanvasCurrent(p, "after the bands came back");
});

test(`P-U5 (${name}): a restore over a band not painted yet is a clearRect`, () => {
  const p = page({ shape });
  p.allocate();
  p.paintBands(0, 2);           // band 1 (rows 1023-2045) not painted yet
  p.state(p.caretAt(1200));
  p.clearOps();
  p.state(p.caretAt(1600));       // inside band 1 both times
  assert.equal(p.puts().length, 0, "put from a band that has no image");
  assert.ok(p.clears().length >= 2, "the old and new rectangles were not cleared");
  assertCanvasCurrent(p, "inside the unpainted band");
  p.clearOps();
  p.state(p.caretAt(300));        // band 1 -> band 0
  assert.equal(p.clears().length, 1, "the old rectangle in band 1");
  assert.equal(p.puts().length, 1, "the new rectangle in band 0");
  assertCanvasCurrent(p, "back in band 0");
  p.paintBands(1);
  assertCanvasCurrent(p, "band 1 arrived");
});


// SPEC-M3-held-key §5.1 U5 (H3): the blue flash of finding 132 / §9.18 item 2.
// While a delete the page sent is out, a range in the engine's state is the
// barrier's one-character selection: the overlay stays the one drawn before it
// (not the engine's caret of that moment).  With no delete out, the same kind
// of range is the user's and is drawn as always, without a caret.
test(`132 U5 (${name}): while a delete is out the engine's range is not drawn; with none out it is`, () => {
  const p = page({ shape });
  p.allocate();
  p.paintBands(0, 1, 2);
  p.state(p.caretAt(1500, 8));
  const before = p.overlayShapes();
  assert.ok(before?.caret, "the caret was not drawn");
  p.clearOps();
  p.setDeletes(1);
  p.state(p.selectionOf([7, 1500, 1, 18]));
  assert.equal(p.fills().length, 0, "something was drawn for the barrier's range");
  assert.equal(p.overlayShapes().key, before.key, "the overlay left the caret drawn before the delete");
  assertCanvasCurrent(p, "a range while a delete is out");
  p.state(p.caretAt(1500, 7));
  assert.ok(p.fills().some((op) => op[1] === "#1a1a1a"), "the caret the delete returned was not drawn");
  assert.ok(!p.fills().some((op) => op[1] === "#b7d3f2"), "a wash was drawn while the delete was out");
  p.setDeletes(0);
  p.clearOps();
  p.state(p.selectionOf([4, 1500, 6, 18]));
  assert.ok(p.fills().some((op) => op[1] === "#b7d3f2"), "the user's own range was not drawn");
  assert.equal(p.overlayShapes().caret, null, "a caret drawn inside the user's range");
  assertCanvasCurrent(p, "the user's range");
});

}
