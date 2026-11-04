// SPEC-P-calc-structure 3.2: the SDK and session side of op 14.  The reply is the native core's own
// (findings/evidence/calc-structure/n-01/observations-N-S1.jsonl, the op 14 line).
import assert from "node:assert/strict";
import test from "node:test";
const { CalcDocumentEngine, normalizeStructure, SHEET_ROWS, SHEET_COLUMNS } =
  await import(process.env.CALC_DOCUMENT_MODULE || "../spreadsheet-shell/calc-document-sdk.js");
const { CalcEditorSession } = await import(process.env.CALC_SESSION_MODULE || "../spreadsheet-shell/calc-editor-session.js");

const NATIVE = {ok: "true", part: "0", axis: "rows", action: "insert", index: "1", count: "2", maxColumns: "16384",
                maxRows: "1048576", changed: "true", mutationAttempted: "false"};

test("the engine's structure reply normalises to the change that happened", () => {
  const s = normalizeStructure(NATIVE);
  assert.deepEqual([s.part, s.axis, s.action, s.index, s.count, s.changed], [0, "rows", "insert", 1, 2, true]);
});

test("a reply that is not a closed change is refused", () => {
  for (const raw of [{...NATIVE, axis: "x"}, {...NATIVE, action: "move"}, {...NATIVE, count: "0"}, {...NATIVE, changed: "false"},
                     {...NATIVE, maxRows: "16777216"}, {...NATIVE, index: "-1"}, null])
    assert.throws(() => normalizeStructure(raw), /CELL_RESULT_INVALID|structure|jumbo|integer/, JSON.stringify(raw));
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
      case "init": result = {profile: "ods-editor-v6", capabilities: ["open-ods", "part-switch", "cell-editing", "save-ods",
        "cell-range-formatting", "cell-headers", ...this.capabilities]}; break;
      case "open": result = {documentHandle: 1, revision: 4, parts: 3, width: 5000, height: 5000, tileMode: 1,
        documentType: "spreadsheet", inputSuffix: ".ods"}; break;
      case "currentPart": result = {part: 0}; break;
      case "partName": result = {name: "Sheet1"}; break;
      case "cellStructure": result = {revision: 5, changed: true, cell: this.reply}; break;
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
  const handle = await engine.open(new Uint8Array([1]).buffer, {fileName: "a.ods"});
  return {worker, handle};
}

test("changeStructure sends the change as cellStructure and returns the closed reply", async () => {
  const {worker, handle} = await opened(["cell-structure"]);
  assert.equal(handle.structureSupported, true);
  const {structure, revision} = await handle.changeStructure({axis: "rows", action: "insert", index: 1, count: 2});
  const call = worker.calls.find(c => c.operation === "cellStructure");
  assert.deepEqual(call.payload.change, {axis: "rows", action: "insert", index: 1, count: 2});
  assert.equal(call.payload.expectedRevision, 4);
  assert.deepEqual([structure.index, structure.count, revision, handle.revision], [1, 2, 5, 5]);
  for (const bad of [{axis: "x", action: "insert", index: 0, count: 1}, {axis: "rows", action: "insert", index: 0, count: 0},
                     {axis: "rows", action: "delete", index: SHEET_ROWS - 1, count: 2},
                     {axis: "columns", action: "insert", index: SHEET_COLUMNS, count: 1}])
    assert.throws(() => handle.changeStructure(bad), /INVALID_ARGUMENT|structure change|non-negative/, JSON.stringify(bad));
});

test("a reply for another change than the one sent is an unknown outcome, not a success", async () => {
  const {worker, handle} = await opened(["cell-structure"]);
  worker.reply = {...NATIVE, index: "2"};
  await assert.rejects(handle.changeStructure({axis: "rows", action: "insert", index: 1, count: 2}), {code: "MUTATION_OUTCOME_UNKNOWN"});
  worker.reply = {...NATIVE, changed: "nope"};
  await assert.rejects(handle.changeStructure({axis: "rows", action: "insert", index: 1, count: 2}), {code: "MUTATION_OUTCOME_UNKNOWN"});
});

test("without the capability nothing is sent", async () => {
  const {worker, handle} = await opened([]);
  assert.equal(handle.structureSupported, false);
  assert.throws(() => handle.changeStructure({axis: "rows", action: "insert", index: 1, count: 1}),
                /UNSUPPORTED_OPERATION|structure contract/);
  assert.ok(!worker.calls.some(c => c.operation === "cellStructure"));
});

// The session: index and count from the selection, the same indices selected afterwards, refusals before anything is sent.
async function session({structure = true, readOnly = false} = {}) {
  const calls = [];
  const doc = {revision: 0, parts: 1, documentType: "spreadsheet", partNames: ["S"], partVisible: [true], currentPart: 0,
    widthTwips: 9000, heightTwips: 9000, headersSupported: true, rangeFormattingSupported: true, structureSupported: structure,
    async setPart(part) { return {part, widthTwips: 9000, heightTwips: 9000}; }, async close() {}, async render() {},
    cell(c, r) { return {part: 0, column: c, row: r, endColumn: c, endRow: r, input: `${c},${r}@${this.revision}`, formula: "",
      text: "", writable: true, bold: false, italic: false, underline: false, xTwips: c * 1000, yTwips: r * 300,
      widthTwips: 999, heightTwips: 299}; },
    async readCell(c, r) { calls.push(["read", c, r]); return {cell: this.cell(c, r)}; },
    async readRange(c, r, ec, er) { return {range: {part: 0, column: c, row: r, endColumn: ec, endRow: er, bold: false,
      italic: false, underline: false, writable: true, refusalCode: ""}}; },
    async changeStructure(change, options) { calls.push(["structure", change, options.expectedRevision]); this.revision++;
      return {structure: {...change, part: 0, changed: true}, revision: this.revision}; },
  };
  const s = new CalcEditorSession({engineFactory: async () => ({manifest: {capabilities: ["open-ods"]}, open: async () => doc,
                                                                dispose() {}})});
  await s.open({bytes: new ArrayBuffer(8), name: "t.ods", readOnly});
  return {s, calls, doc};
}

test("rows 3-4 selected: above inserts 2 at index 2, below at index 4, delete removes 2 at index 2", async () => {
  const {s, calls} = await session();
  await s.selectWhole("rows", 2, 3);
  assert.deepEqual(s.structurePlan("rows", "insert", "before"), {axis: "rows", action: "insert", where: "before", index: 2, count: 2, part: 0});
  assert.equal(s.structurePlan("rows", "insert", "after").index, 4);
  assert.deepEqual([s.structurePlan("rows", "delete").index, s.structurePlan("rows", "delete").count], [2, 2]);
  // A whole-row selection spans every column: the column items are not available.
  assert.equal(s.structurePlan("columns", "insert").refused, "WHOLE_AXIS");
  await s.changeStructure("rows", "insert", "before");
  assert.deepEqual(calls.find(c => c[0] === "structure").slice(1, 2), [{axis: "rows", action: "insert", index: 2, count: 2}]);
  const sel = s.state.selection;
  assert.deepEqual([sel.whole, sel.row, sel.endRow], ["rows", 2, 3], "the same indices stay selected");
  assert.equal(s.state.cell.input, "0,2@1", "the anchor was read again after the change");
  await s.close();
});

test("a cell range B2:C5 gives columns B..C and rows 2..5; a whole column refuses the row items", async () => {
  const {s} = await session();
  await s.selectCell(1, 1);
  await s.selectCell(2, 4, {extend: true});
  assert.deepEqual([s.structurePlan("columns", "insert", "after").index, s.structurePlan("columns", "insert").count], [3, 2]);
  assert.deepEqual([s.structurePlan("rows", "delete").index, s.structurePlan("rows", "delete").count], [1, 4]);
  await s.selectWhole("columns", 2, 2);
  assert.equal(s.structurePlan("rows", "insert").refused, "WHOLE_AXIS");
  assert.equal(s.structurePlan("columns", "delete").count, 1);
  await s.close();
});

test("refused before anything is sent: no capability, read-only", async () => {
  for (const options of [{structure: false}, {readOnly: true}]) {
    const {s, calls} = await session(options);
    assert.ok(s.structurePlan("rows", "insert").refused, JSON.stringify(options));
    await assert.rejects(s.changeStructure("rows", "insert"),
                         (error) => ["UNSUPPORTED_OPERATION", "READ_ONLY"].includes(error.code));
    assert.ok(!calls.some(c => c[0] === "structure"));
    await s.close();
  }
});
