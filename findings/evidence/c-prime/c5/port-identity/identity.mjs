// SPEC-M3-production-ui §17.11: the ported constants against the old ones on one
// fake page, offline.  P page (no data-window): every output must be EQUAL.
// Windowed (C′ shape, a fake that answers only rows [top, top + W)): the
// readers must report, in document rows, what the old readers report on the
// whole canvas -- for rows inside the window.
import vm from "node:vm";
import fs from "node:fs";
const [oldFile, newFile] = process.argv.slice(2);
const OLD = JSON.parse(fs.readFileSync(oldFile, "utf8"));
const NEW = JSON.parse(fs.readFileSync(newFile, "utf8"));

const W = 725, DOC = 2024;                       // two pages' rows at 725 px
function docPixel(x, y) {                        // RGBA of document row y, column x
  if (x < 6 || x > W - 7) return [0, 0, 0, 0];   // transparent surround
  if (x === 14 || x === W - 15) return [20, 20, 20, 255];          // page border
  if (y % 1012 < 2) return [20, 20, 20, 255];                       // page rule
  const line = y % 40;
  if (line >= 12 && line < 27 && x > 60 && x < W - 60 && (x * 7 + y * 3) % 5 === 0)
    return [30, 30, 30, 255];                                       // glyph ink
  if (x === 301 && y >= 492 && y < 508) return [26, 26, 26, 255];   // a caret bar
  return [255, 255, 255, 255];
}
function makePage({ top = 0, rows = DOC, windowed = false, scale = 1 }) {
  const events = [];
  const canvasBox = { left: 100, top: 50 + top / scale, width: W / scale, height: rows / scale };
  canvasBox.right = canvasBox.left + canvasBox.width; canvasBox.bottom = canvasBox.top + canvasBox.height;
  const paperBox = { left: 100, top: 50, width: W / scale, height: DOC / scale };
  paperBox.right = paperBox.left + paperBox.width; paperBox.bottom = paperBox.top + paperBox.height;
  const canvas = {
    width: W, height: rows, style: { width: `${W / scale}px`, height: `${rows / scale}px` },
    dataset: windowed ? { window: `${DOC} ${top} ${rows}`, changes: "7",
      bands: [0, 1].map((i) => `${i}:${i * 1023}:${i ? DOC - 1023 : 1023}:7`).join(" ") } : {},
    getBoundingClientRect: () => ({ ...canvasBox }),
    dispatchEvent: (e) => { events.push([e.type, e.clientX, e.clientY]); return true; },
    getContext: () => ({ getImageData(x0, y0, w, h) {
      const data = new Uint8ClampedArray(w * h * 4);
      for (let y = 0; y < h; y += 1) for (let x = 0; x < w; x += 1) {
        const cy = y0 + y, cx = x0 + x;
        const px = (cy < 0 || cy >= rows || cx < 0 || cx >= W) ? [0, 0, 0, 0] : docPixel(cx, cy + top);
        data.set(px, (y * w + x) * 4);
      }
      return { data };
    } }),
  };
  const sink = { getBoundingClientRect: () => ({ left: 100 + 301 / scale, top: 50 + 492 / scale,
    right: 100 + 302 / scale, bottom: 50 + 508 / scale, width: 1 / scale, height: 16 / scale }) };
  const paper = { getBoundingClientRect: () => ({ ...paperBox }) };
  const desk = { scrollTop: 0, clientHeight: 600, getBoundingClientRect: () => ({ top: 40, height: 600 }) };
  const toolbar = { querySelector: () => ({ click: () => events.push(["click"]) }) };
  const map = { "#canvas": canvas, "#paper": paper, "#desk": desk, "#sink": sink, "#toolbar": toolbar };
  const document = { querySelector: (s) => map[s] ?? null };
  const window = { dispatchEvent: (e) => { events.push([e.type]); return true; } };
  class PointerEvent { constructor(type, init) { Object.assign(this, init, { type }); } }
  class Event { constructor(type) { this.type = type; } }
  return { context: vm.createContext({ document, window, globalThis: {}, PointerEvent, Event,
    performance: { now: () => Date.now() }, setTimeout, Promise, Math, Number, Array, Object,
    Uint8Array, Int32Array, Uint8ClampedArray, JSON }), events };
}
const ARGS = { ARG_X1: "0.2", ARG_X2: "0.45", ARG_Y1: "0.24", ARG_Y2: "0.24", ARG_X: "0.35",
  ARG_EXCLUDE_CARET: "true", ARG_KIND: "blur" };
function prepare(src, y) {
  let s = src;
  for (const k of Object.keys(ARGS).sort((a, b) => b.length - a.length)) s = s.split(k).join(ARGS[k]);
  return s.split("ARG_Y").join(String(y));
}
async function run(src, y, page) {
  const p = makePage(page);
  const value = await vm.runInContext(prepare(src, y), p.context);
  return JSON.stringify({ value, events: p.events });
}
let failures = 0, compared = 0;
const say = (ok, what) => { compared += 1; if (!ok) failures += 1; console.log(`${ok ? "SAME" : "DIFF"} ${what}`); };
for (const name of Object.keys(OLD)) for (const y of [0.05, 0.24, 0.28, 0.5, 0.97]) for (const scale of [1, 2]) {
  const a = await run(OLD[name], y, { scale });
  let b = await run(NEW[name], y, { scale });
  if (name === "pp.GEOMETRY") {
    // The one field the port adds: the canvas's own height, equal to `height`
    // on the P page.  The first run of this test compared it too and reported
    // these ten cells DIFF -- kept as the record that the test can say DIFF.
    const parsed = JSON.parse(b);
    const extra = parsed.value.canvasHeight === parsed.value.height;
    delete parsed.value.canvasHeight;
    b = extra ? JSON.stringify(parsed) : `canvasHeight differs from height: ${b}`;
  }
  say(a === b, `P-page ${name} y=${y} scale=${scale}`);
}
// Windowed, the whole document in the window (C′ on a short document): the
// readers' output equals the P page's but for the added `window` field.
for (const name of ["pp.TOP_INK", "pp.CARET_COLUMNS", "pp.LINE_INK", "pp.INK_ROWS", "ph.TEXT_LINES"]) for (const y of [0.24, 0.5]) {
  const a = JSON.parse(await run(OLD[name], y, {})), b = JSON.parse(await run(NEW[name], y, { windowed: true }));
  delete b.value.window;
  say(JSON.stringify(a) === JSON.stringify(b), `windowed-whole ${name} y=${y}`);
}
// Windowed, rows [1000, 2024) only: rows inside the window read as the whole
// canvas reads them, in document rows.
{
  const old = JSON.parse(await run(OLD["pp.INK_ROWS"], 0, {})).value;
  const neu = JSON.parse(await run(NEW["pp.INK_ROWS"], 0, { windowed: true, top: 1000, rows: 1024 })).value;
  const inside = (arr) => arr.slice(1000);
  say(neu.height === DOC && neu.counts.length === DOC, "windowed-part INK_ROWS reports the document's rows");
  say(JSON.stringify(inside(neu.counts)) === JSON.stringify(inside(old.counts)), "windowed-part INK_ROWS counts inside the window");
  say(neu.counts.slice(0, 1000).every((n) => n === 0), "windowed-part INK_ROWS no ink outside the window");
  for (const name of ["pp.LINE_INK", "pp.CARET_COLUMNS"]) {
    const y = 0.75;
    const a = JSON.parse(await run(OLD[name], y, {})).value;
    const b = JSON.parse(await run(NEW[name], y, { windowed: true, top: 1000, rows: 1024 })).value;
    say(JSON.stringify(a) === JSON.stringify(b), `windowed-part ${name} y=${y} (inside the window)`);
  }
  const lines = JSON.parse(await run(OLD["ph.TEXT_LINES"], 0, {})).value;
  const part = JSON.parse(await run(NEW["ph.TEXT_LINES"], 0, { windowed: true, top: 1000, rows: 1024 })).value;
  const later = lines.bands.filter((b) => b.a >= 1000 && b.b < 2024);
  say(JSON.stringify(part.bands.filter((b) => b.a > 1000)) === JSON.stringify(later.filter((b) => b.a > 1000)),
      "windowed-part TEXT_LINES bands inside the window, in document rows and fractions");
}
console.log(`SUMMARY compared ${compared}, different ${failures}`);
process.exit(failures ? 1 : 0);
