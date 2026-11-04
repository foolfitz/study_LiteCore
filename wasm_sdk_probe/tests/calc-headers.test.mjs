// SPEC-P-calc-headers 3.1-3.3: the SDK side of op 13 and whole ranges.  The replies are the native core's own
// (tests/calc-headers-replies.json, copied from findings/evidence/calc-headers/n-01).
import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
const { CalcDocumentEngine, normalizeHeaders, normalizeRange, isWholeRange, SHEET_ROWS, SHEET_COLUMNS } =
  await import(process.env.CALC_DOCUMENT_MODULE || "../spreadsheet-shell/calc-document-sdk.js");
const replies = JSON.parse(readFileSync(new URL("./calc-headers-replies.json", import.meta.url)));

test("the engine's header reply normalises to one closed run per axis", () => {
  const h = normalizeHeaders(replies.topLeft);
  assert.equal(h.maxColumns, SHEET_COLUMNS); assert.equal(h.maxRows, SHEET_ROWS);
  assert.deepEqual(h.columns.slice(0, 5).map(e => [e.label, e.startPx, e.endPx, e.hidden]),
    [["A", 0, 113, false], ["B", 113, 181, false], ["C", 181, 294, false], ["D", 294, 294, true], ["E", 294, 407, false]]);
  assert.deepEqual(h.rows.slice(0, 5).map(e => [e.label, e.index, e.endPx, e.hidden]),
    [["1", 0, 18, false], ["2", 1, 55, false], ["3", 2, 73, false], ["4", 3, 73, true], ["5", 4, 90, false]]);
});

test("an empty axis arrives as the JSON writer's empty string", () => {
  const h = normalizeHeaders(replies.columnsOnly);
  assert.equal(h.rows.length, 0); assert.ok(h.columns.length > 0);
});

test("a reply that is not one closed run is refused", () => {
  const cols = replies.topLeft.columns;
  const broken = [
    {...replies.topLeft, columns: [cols[0], cols[2]]},                                   // a gap in the indices
    {...replies.topLeft, columns: [cols[0], {...cols[1], startPx: "112"}]},              // does not start where A ended
    {...replies.topLeft, columns: [{...cols[3], hidden: "false"}]},                       // hidden D claimed visible
    {...replies.topLeft, columns: [{...cols[0], label: "a"}]},                             // not a column name
    {...replies.topLeft, maxRows: "16777216"},                                            // a jumbo sheet
    {...replies.topLeft, rows: "nope"},
  ];
  for (const raw of broken) assert.throws(() => normalizeHeaders(raw), /CELL_RESULT_INVALID|entries|jumbo|list/);
});

test("whole column, whole row and whole sheet are the only ranges past the cell limit", () => {
  assert.equal(isWholeRange(2, 0, 2, SHEET_ROWS - 1), true);
  assert.equal(isWholeRange(0, 5, SHEET_COLUMNS - 1, 9), true);
  assert.equal(isWholeRange(0, 0, SHEET_COLUMNS - 1, SHEET_ROWS - 1), true);
  assert.equal(isWholeRange(2, 0, 2, SHEET_ROWS - 2), false);
  assert.equal(isWholeRange(1, 0, SHEET_COLUMNS - 1, 0), false);
  const reply = {part: "0", column: "2", row: "0", endColumn: "2", endRow: String(SHEET_ROWS - 1), bold: "on", italic: "off",
    underline: "off", writable: "true", refusalCode: ""};
  assert.equal(normalizeRange(reply).endRow, SHEET_ROWS - 1);
  assert.throws(() => normalizeRange({...reply, endRow: String(SHEET_ROWS - 2)}), /RANGE_TOO_LARGE|65536/);
});

class Worker {
  listeners = []; calls = []; capabilities = [];
  addEventListener(type, fn) { if (type === "message") this.listeners.push(fn); }
  terminate() {}
  postMessage(message) {
    if (message.kind !== "request") return;
    this.calls.push(message);
    let result;
    switch (message.operation) {
      case "init": result = {profile: "ods-editor-v6", capabilities: ["open-ods", "part-switch", "cell-editing", "save-ods",
        "cell-range-formatting", ...this.capabilities]}; break;
      case "open": result = {documentHandle: 1, revision: 4, parts: 3, width: 5000, height: 5000, tileMode: 1, documentType: "spreadsheet", inputSuffix: ".ods"}; break;
      case "currentPart": result = {part: 0}; break;
      case "partName": result = {name: "Sheet1"}; break;
      case "cellHeaders": result = {revision: 4, changed: false, cell: replies.topLeft}; break;
      default: result = {revision: 5, changed: true, cell: {part: "0", column: "2", row: "0", endColumn: "2", endRow: String(SHEET_ROWS - 1),
        bold: "on", italic: "off", underline: "off", writable: "true", refusalCode: ""}};
    }
    queueMicrotask(() => this.listeners.forEach(fn => fn({data: {protocolVersion: 1, kind: "response", requestId: message.requestId, ok: true, result}})));
  }
}

async function opened(capabilities) {
  const worker = new Worker();
  worker.capabilities = capabilities;
  const engine = new CalcDocumentEngine({workerUrl: "https://test/sdk-worker.js", workerFactory: () => worker});
  await engine._initialize();
  const handle = await engine.open(new Uint8Array([1]).buffer, {fileName: "a.ods"});
  return {worker, handle};
}

test("readHeaders sends the rectangle as cellHeaders and returns the closed reply", async () => {
  const {worker, handle} = await opened(["cell-headers"]);
  assert.equal(handle.headersSupported, true);
  const {headers} = await handle.readHeaders({x: 0, y: 0, width: 15000, height: 6000});
  const call = worker.calls.find(c => c.operation === "cellHeaders");
  assert.deepEqual(call.payload.rectangle, {x: 0, y: 0, width: 15000, height: 6000});
  assert.equal(call.payload.column, 0); assert.equal(call.payload.row, 0);
  assert.equal(headers.columns[0].label, "A");
  for (const bad of [{x: 0, y: 0, width: 0, height: 0}, {x: -1, y: 0, width: 10, height: 10}, {x: 0, y: 0, width: 245761, height: 1}])
    assert.throws(() => handle.readHeaders(bad), /INVALID_ARGUMENT|header rectangle|non-negative/);
});

test("without the capability: no header reads and no whole ranges", async () => {
  const {handle} = await opened([]);
  assert.equal(handle.headersSupported, false);
  assert.throws(() => handle.readHeaders({x: 0, y: 0, width: 10, height: 10}), /UNSUPPORTED_OPERATION|header contract/);
  assert.throws(() => handle.setRangeFormat(2, 0, 2, SHEET_ROWS - 1, "bold", true), /RANGE_TOO_LARGE|65536/);
});

test("with it, a whole column goes to the worker", async () => {
  const {worker, handle} = await opened(["cell-headers"]);
  const {range} = await handle.setRangeFormat(2, 0, 2, SHEET_ROWS - 1, "bold", true);
  assert.equal(range.endRow, SHEET_ROWS - 1); assert.equal(range.bold, true);
  assert.ok(worker.calls.some(c => c.operation === "rangeFormat" && c.payload.endRow === SHEET_ROWS - 1));
});

// The session: whole selections by index, kept whole through a format's endpoint refresh; refused without the contract.
const { CalcEditorSession } = await import(process.env.CALC_SESSION_MODULE || "../spreadsheet-shell/calc-editor-session.js");
async function session(headers = true) {
  const calls = [];
  const doc = {revision: 0, parts: 1, documentType: "spreadsheet", partNames: ["S"], partVisible: [true], currentPart: 0,
    widthTwips: 9000, heightTwips: 9000, headersSupported: headers, rangeFormattingSupported: true,
    async setPart(part) { return {part, widthTwips: 9000, heightTwips: 9000}; }, async close() {}, async render() {},
    cell(c, r) { return {part: 0, column: c, row: r, endColumn: c, endRow: r, input: "", formula: "", text: "", writable: true,
      bold: false, italic: false, underline: false, xTwips: c * 1000, yTwips: r * 300, widthTwips: 999, heightTwips: 299}; },
    async readCell(c, r) { calls.push(["read", c, r]); return {cell: this.cell(c, r)}; },
    async readRange(c, r, ec, er) { calls.push(["readRange", c, r, ec, er]);
      return {range: {part: 0, column: c, row: r, endColumn: ec, endRow: er, bold: false, italic: false, underline: false, writable: true, refusalCode: ""}}; },
    async setRangeFormat(c, r, ec, er, format, enabled) { calls.push(["format", c, r, ec, er, format, enabled]); this.revision++;
      return {range: {part: 0, column: c, row: r, endColumn: ec, endRow: er, bold: enabled, italic: false, underline: false, writable: true, refusalCode: ""}}; },
  };
  const s = new CalcEditorSession({engineFactory: async () => ({manifest: {capabilities: ["open-ods"]}, open: async () => doc, dispose() {}})});
  await s.open({bytes: new ArrayBuffer(8), name: "t.ods"});
  return {s, calls};
}

test("a whole column is the indices asked for, anchored in row 1, never read at the sheet's end", async () => {
  const {s, calls} = await session();
  await s.selectWhole("columns", 4, 2);
  const range = s.state.selection;
  assert.deepEqual([range.whole, range.column, range.row, range.endColumn, range.endRow], ["columns", 2, 0, 4, SHEET_ROWS - 1]);
  assert.deepEqual([s.state.cell.column, s.state.cell.row], [4, 0]);
  assert.ok(!calls.some(c => c[0] === "read" && c[2] > 0), "no cell below row 1 was read");
  assert.deepEqual(calls.at(-1), ["readRange", 2, 0, 4, SHEET_ROWS - 1]);
  await s.selectWhole("rows", 9, 9);
  assert.deepEqual([s.state.selection.column, s.state.selection.endColumn, s.state.selection.row, s.state.selection.endRow],
    [0, SHEET_COLUMNS - 1, 9, 9]);
  await s.selectWhole("sheet", 7, 7);
  assert.deepEqual([s.state.selection.whole, s.state.selection.endColumn, s.state.selection.endRow, s.state.cell.column],
    ["sheet", SHEET_COLUMNS - 1, SHEET_ROWS - 1, 0]);
  await s.close();
});

test("a format on a whole column writes the whole column and the selection stays whole", async () => {
  const {s, calls} = await session();
  await s.selectWhole("columns", 2, 2);
  await s.setFormat("bold", true);
  assert.ok(calls.some(c => c[0] === "format" && c[1] === 2 && c[3] === 2 && c[4] === SHEET_ROWS - 1));
  assert.equal(s.state.selection.whole, "columns");
  assert.equal(s.state.selection.endRow, SHEET_ROWS - 1);
  assert.equal(s.state.rangeFormat.bold, true);
  await s.close();
});

test("without the header contract a whole selection is refused", async () => {
  const {s} = await session(false);
  await assert.rejects(s.selectWhole("columns", 1, 1), /UNSUPPORTED_OPERATION|header contract/);
  await assert.rejects(s.selectWhole("diagonal", 1, 1), /INVALID_ARGUMENT|columns, rows or the sheet/);
  await s.close();
});
