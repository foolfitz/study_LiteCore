// SPEC-P-calc-zoom 3.2: the SDK and session side of op 16.  The zoom reply is the native core's own
// (findings/evidence/calc-v8/n-zoom-01/report.json, the 75% level).
import assert from "node:assert/strict";
import test from "node:test";
const { CalcDocumentEngine, normalizeZoom, ZOOM_PERCENTS, ZOOM_TILE_TWIPS } =
  await import(process.env.CALC_DOCUMENT_MODULE || "../spreadsheet-shell/calc-document-sdk.js");
const { CalcEditorSession } = await import(process.env.CALC_SESSION_MODULE || "../spreadsheet-shell/calc-editor-session.js");
import { readFileSync } from "node:fs";

const NATIVE = {ok: "true", part: "0", tileTwips: "5120", percent: "75", widthTwips: "34280", heightTwips: "240220",
                changed: "false", mutationAttempted: "false"};

test("the levels are the bridge's closed list", () => {
  const bridge = readFileSync(new URL("../src/calc_cell_bridge.cpp", import.meta.url), "utf8");
  const list = bridge.match(/constexpr int kTileTwips\[\] = \{([0-9, ]+)\};/)[1].split(",").map(Number);
  assert.deepEqual([...ZOOM_TILE_TWIPS], list);
  assert.deepEqual([...ZOOM_PERCENTS], [50, 75, 100, 125, 150, 200]);
});

test("the engine's zoom reply normalises; anything off the levels or claiming a change is refused", () => {
  assert.deepEqual({...normalizeZoom(NATIVE)}, {part: 0, tileTwips: 5120, percent: 75, widthTwips: 34280, heightTwips: 240220});
  for (const raw of [{...NATIVE, changed: "true"}, {...NATIVE, tileTwips: "1234", percent: "311"}, {...NATIVE, percent: "76"},
                     {...NATIVE, widthTwips: "0"}, {...NATIVE, heightTwips: "-1"}, null])
    assert.throws(() => normalizeZoom(raw), {code: "CELL_RESULT_INVALID"}, JSON.stringify(raw));
});

class Worker {
  listeners = []; calls = []; capabilities = []; reply = NATIVE;
  addEventListener(type, fn) { if (type === "message") this.listeners.push(fn); }
  terminate() {}
  postMessage(message) {
    if (message.kind !== "request") return;
    this.calls.push(message);
    let result;
    switch (message.operation) {
      case "init": result = {profile: "ods-editor-v8", capabilities: ["open-ods", "part-switch", "cell-editing", "save-ods",
        ...this.capabilities]}; break;
      case "open": result = {documentHandle: 1, revision: 4, parts: 2, width: 5000, height: 5000, tileMode: 1,
        documentType: "spreadsheet", inputSuffix: ".ods"}; break;
      case "currentPart": result = {part: 0}; break;
      case "partName": result = {name: "Sheet1"}; break;
      case "cellZoom": result = {revision: 4, changed: false, cell: this.reply}; break;
      default: result = {revision: 4, changed: false, cell: {}};
    }
    queueMicrotask(() => this.listeners.forEach(fn => fn({data: {protocolVersion: 1, kind: "response", requestId: message.requestId,
                                                                  ok: true, result}})));
  }
}

async function opened(capabilities) {
  const worker = new Worker();
  worker.capabilities = capabilities;
  const engine = new CalcDocumentEngine({workerUrl: "https://test/sdk-worker.js", workerFactory: () => worker});
  await engine._initialize();
  return {worker, handle: await engine.open(new Uint8Array([1]).buffer, {fileName: "a.ods"})};
}

test("setZoom sends cellZoom with tileTwips on the current part; the revision does not move", async () => {
  const {worker, handle} = await opened(["cell-zoom"]);
  assert.equal(handle.zoomSupported, true);
  const {zoom} = await handle.setZoom(5120);
  const call = worker.calls.find(c => c.operation === "cellZoom");
  assert.deepEqual([call.payload.tileTwips, call.payload.part], [5120, 0]);
  assert.equal(zoom.percent, 75);
  assert.equal(handle.revision, 4);
});

test("a level outside the list, a reply for another level, or no capability: refused", async () => {
  const {worker, handle} = await opened(["cell-zoom"]);
  assert.throws(() => handle.setZoom(1234), {code: "INVALID_ARGUMENT"});
  assert.ok(!worker.calls.some(c => c.operation === "cellZoom"));
  await assert.rejects(handle.setZoom(3840), {code: "CELL_RESULT_INVALID"});  // the fake answers 5120
  const {worker: plain, handle: v7} = await opened([]);
  assert.equal(v7.zoomSupported, false);
  assert.throws(() => v7.setZoom(3840), {code: "UNSUPPORTED_OPERATION"});
  assert.ok(!plain.calls.some(c => c.operation === "cellZoom"));
});

// The session: a fake document whose rectangles follow the zoom the way the core's do (not proportionally).
async function session({zoom = true} = {}) {
  const reads = [];
  const doc = {revision: 0, parts: 1, documentType: "spreadsheet", partNames: ["S"], partVisible: [true], currentPart: 0,
    widthTwips: 9000, heightTwips: 9000, headersSupported: true, rangeFormattingSupported: true, zoomSupported: zoom, tile: 3840,
    async setPart(part) { return {part, widthTwips: 9000, heightTwips: 9000}; }, async close() {}, async render() {},
    cell(c, r) {
      const px = 256 / this.tile, rowPx = Math.floor(17 * px * 0.98), columnPx = Math.floor(68 * px);  // floored per row
      return {part: 0, column: c, row: r, endColumn: c, endRow: r, input: "", formula: "", text: "", writable: true,
        bold: false, italic: false, underline: false, xTwips: Math.round(c * columnPx / px), yTwips: Math.round(r * rowPx / px),
        widthTwips: Math.round(columnPx / px), heightTwips: Math.round(rowPx / px)};
    },
    async readCell(c, r) { reads.push([this.tile, c, r]); return {cell: this.cell(c, r)}; },
    async readRange(c, r, ec, er) { return {range: {part: 0, column: c, row: r, endColumn: ec, endRow: er, bold: false,
      italic: false, underline: false, writable: true, refusalCode: ""}}; },
    async setZoom(tileTwips, options) {
      this.tile = tileTwips;
      return {zoom: {part: options.part, tileTwips, percent: 384000 / tileTwips, widthTwips: 8000, heightTwips: 7000}};
    },
  };
  const s = new CalcEditorSession({engineFactory: async () => ({manifest: {capabilities: ["open-ods"]}, open: async () => doc,
                                                                dispose() {}})});
  await s.open({bytes: new ArrayBuffer(8), name: "t.ods"});
  return {s, reads, doc};
}

test("setZoom: op 16, then the selection's ends read at the new zoom; tiles at the new scale and size; nothing dirty", async () => {
  const {s, reads, doc} = await session();
  await s.selectCell(1, 1);
  await s.selectCell(3, 40, {extend: true});
  reads.length = 0;
  const result = await s.setZoom(75, {centre: {column: 2, row: 20}});
  assert.deepEqual(reads, [[3840, 2, 20], [5120, 2, 20], [5120, 1, 1], [5120, 3, 40]]);
  assert.equal(s.state.zoom, 75);
  assert.equal(s.viewer.scale, 0.75);
  assert.deepEqual(s.scheduler.documentCssSize, {width: 8000 / 15 * 0.75, height: 7000 / 15 * 0.75});
  assert.deepEqual([s.state.selection.yTwips, s.state.selection.focus.yTwips], [doc.cell(1, 1).yTwips, doc.cell(3, 40).yTwips]);
  assert.deepEqual([result.centre.before.yTwips, result.centre.after.yTwips], [(await session()).doc.cell(2, 20).yTwips,
                                                                               doc.cell(2, 20).yTwips]);
  assert.equal(s.hasUnsavedEdits(), false);
  await s.close();
});

test("setZoom refuses a level off the list, an entry in progress, and an engine without zoom", async () => {
  const {s, reads} = await session();
  await assert.rejects(s.setZoom(80), {code: "INVALID_ARGUMENT"});
  s.beginEdit("formula");
  await assert.rejects(s.setZoom(150), {code: "EDIT_IN_PROGRESS"});
  s.cancelEdit();
  assert.equal(s.state.zoom, 100);
  assert.deepEqual(reads.filter(([tile]) => tile !== 3840), []);
  await s.close();
  const {s: v7} = await session({zoom: false});
  await assert.rejects(v7.setZoom(150), {code: "UNSUPPORTED_OPERATION"});
  assert.equal(v7.viewer.scale, 1);
  await v7.close();
});

test("a whole-column selection is redrawn over the document's extent at the new zoom", async () => {
  const {s} = await session();
  await s.selectWhole("columns", 2, 2);
  await s.setZoom(200);
  assert.equal(s.state.selection.whole, "columns");
  assert.equal(s.state.selection.heightTwips, 7000);
  await s.close();
});
