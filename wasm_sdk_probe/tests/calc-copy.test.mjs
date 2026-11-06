// SPEC-P-calc-copy 3.2: the SDK and session side of op 15, and SPEC-P-calc-sheets 2.1's protected flags.  The copy reply is
// the native core's own (findings/evidence/calc-copy/n-01/observations-n.jsonl, the B1:C2 line).
import assert from "node:assert/strict";
import test from "node:test";
const { CalcDocumentEngine, normalizeCopy, SHEET_ROWS } =
  await import(process.env.CALC_DOCUMENT_MODULE || "../spreadsheet-shell/calc-document-sdk.js");
const { CalcEditorSession } = await import(process.env.CALC_SESSION_MODULE || "../spreadsheet-shell/calc-editor-session.js");

const NATIVE = {ok: "true", part: "0", column: "1", row: "0", endColumn: "2", endRow: "1", markedColumn: "1", markedRow: "0",
                markedEndColumn: "2", markedEndRow: "1", plainText: "42\t84\n格式測試\t待清除\n", changed: "false",
                mutationAttempted: "false"};

test("the engine's copy reply normalises, the text kept as it came", () => {
  const c = normalizeCopy(NATIVE);
  assert.deepEqual([c.part, c.column, c.row, c.endColumn, c.endRow, c.plainText], [0, 1, 0, 2, 1, "42\t84\n格式測試\t待清除\n"]);
  for (const raw of [{...NATIVE, changed: "true"}, {...NATIVE, plainText: undefined}, {...NATIVE, endRow: "-1"}, null])
    assert.throws(() => normalizeCopy(raw), {code: "CELL_RESULT_INVALID"}, JSON.stringify(raw));
});

class Worker {
  listeners = []; calls = []; capabilities = []; reply = NATIVE; info = ['{"visible":1,"protected":0}', '{"visible":1,"protected":1}'];
  addEventListener(type, fn) { if (type === "message") this.listeners.push(fn); }
  terminate() {}
  postMessage(message) {
    if (message.kind !== "request") return;
    this.calls.push(message);
    let result;
    switch (message.operation) {
      case "init": result = {profile: "ods-editor-v7", capabilities: ["open-ods", "part-switch", "cell-editing", "save-ods",
        "cell-range-formatting", "cell-headers", ...this.capabilities]}; break;
      case "open": result = {documentHandle: 1, revision: 4, parts: 2, width: 5000, height: 5000, tileMode: 1,
        documentType: "spreadsheet", inputSuffix: ".ods"}; break;
      case "currentPart": result = {part: 0}; break;
      case "partName": result = {name: "Sheet1"}; break;
      case "partInfo": result = {info: this.info[message.payload.part]}; break;
      case "cellCopy": result = {revision: 4, changed: false, cell: this.reply}; break;
      default: result = {revision: 4, changed: false, cell: {}};
    }
    queueMicrotask(() => this.listeners.forEach(fn => fn({data: {protocolVersion: 1, kind: "response", requestId: message.requestId,
                                                                  ok: true, result}})));
  }
}

async function opened(capabilities, configure = () => {}) {
  const worker = new Worker();
  worker.capabilities = capabilities;
  configure(worker);
  const engine = new CalcDocumentEngine({workerUrl: "https://test/sdk-worker.js", workerFactory: () => worker});
  await engine._initialize();
  const handle = await engine.open(new Uint8Array([1]).buffer, {fileName: "a.ods"});
  return {worker, handle};
}

test("copyRange sends cellCopy with the endpoints and returns the core's text; the revision does not move", async () => {
  const {worker, handle} = await opened(["cell-copy"]);
  assert.equal(handle.copySupported, true);
  const {copy} = await handle.copyRange(1, 0, 2, 1);
  const call = worker.calls.find(c => c.operation === "cellCopy");
  assert.deepEqual([call.payload.column, call.payload.row, call.payload.endColumn, call.payload.endRow], [1, 0, 2, 1]);
  assert.equal(copy.plainText, NATIVE.plainText);
  assert.equal(handle.revision, 4);
  // A whole column passes the cell limit; a large partial rectangle is refused before anything is sent.
  worker.reply = {...NATIVE, column: "0", endColumn: "0", endRow: String(SHEET_ROWS - 1)};
  await handle.copyRange(0, 0, 0, SHEET_ROWS - 1);
  const sent = worker.calls.filter(c => c.operation === "cellCopy").length;
  assert.throws(() => handle.copyRange(0, 0, 25, 2999), {code: "RANGE_TOO_LARGE"});
  assert.equal(worker.calls.filter(c => c.operation === "cellCopy").length, sent);
});

test("a copy reply for another range is refused", async () => {
  const {worker, handle} = await opened(["cell-copy"]);
  worker.reply = {...NATIVE, endRow: "0"};
  await assert.rejects(handle.copyRange(1, 0, 2, 1), {code: "CELL_RESULT_INVALID"});
});

test("without cell-copy nothing is sent", async () => {
  const {worker, handle} = await opened([]);
  assert.equal(handle.copySupported, false);
  assert.throws(() => handle.copyRange(1, 0, 2, 1), {code: "UNSUPPORTED_OPERATION"});
  assert.ok(!worker.calls.some(c => c.operation === "cellCopy"));
});

test("SPEC-P-calc-sheets 2.1: part-info's protected flag per sheet; an unreadable one leaves null", async () => {
  const {handle} = await opened(["part-info"]);
  assert.deepEqual(handle.partProtected, [false, true]);
  const {handle: odd} = await opened(["part-info"], worker => { worker.info = ['{"visible":1}', '{"visible":1}']; });
  assert.equal(odd.partProtected, null);
  assert.match(odd.partProtectedProblem, /PART_INFO_UNPARSEABLE/);
  const {handle: none} = await opened([]);
  assert.equal(none.partProtected, null);
});

// The session: the range is the selection's; a copy is a read.
async function session({copy = true} = {}) {
  const calls = [];
  const doc = {revision: 0, parts: 1, documentType: "spreadsheet", partNames: ["S"], partVisible: [true], currentPart: 0,
    widthTwips: 9000, heightTwips: 9000, headersSupported: true, rangeFormattingSupported: true, copySupported: copy,
    async setPart(part) { return {part, widthTwips: 9000, heightTwips: 9000}; }, async close() {}, async render() {},
    cell(c, r) { return {part: 0, column: c, row: r, endColumn: c, endRow: r, input: "", formula: "", text: "", writable: true,
      bold: false, italic: false, underline: false, xTwips: c * 1000, yTwips: r * 300, widthTwips: 999, heightTwips: 299}; },
    async readCell(c, r) { return {cell: this.cell(c, r)}; },
    async readRange(c, r, ec, er) { return {range: {part: 0, column: c, row: r, endColumn: ec, endRow: er, bold: false,
      italic: false, underline: false, writable: true, refusalCode: ""}}; },
    copyRange(c, r, ec, er, options) {
      if (!this.copySupported) throw Object.assign(new Error("no copy contract"), {code: "UNSUPPORTED_OPERATION"});
      calls.push([c, r, ec, er, options.part]);
      return Promise.resolve({copy: {part: 0, column: c, row: r, endColumn: ec, endRow: er, plainText: `${c},${r}:${ec},${er}`}});
    },
  };
  const s = new CalcEditorSession({engineFactory: async () => ({manifest: {capabilities: ["open-ods"]}, open: async () => doc,
                                                                dispose() {}})});
  await s.open({bytes: new ArrayBuffer(8), name: "t.ods"});
  return {s, calls, doc};
}

test("copySelection copies the selection: a single cell, a rectangle, a whole column; nothing becomes dirty", async () => {
  const {s, calls} = await session();
  assert.equal((await s.copySelection()).plainText, "0,0:0,0");
  await s.selectCell(1, 1);
  await s.selectCell(2, 4, {extend: true});
  const {plainText, range} = await s.copySelection();
  assert.deepEqual([plainText, range.column, range.endRow], ["1,1:2,4", 1, 4]);
  await s.selectWhole("columns", 2, 2);
  await s.copySelection();
  assert.deepEqual(calls.at(-1), [2, 0, 2, SHEET_ROWS - 1, 0]);
  assert.equal(s.hasUnsavedEdits(), false);
  await s.close();
});

test("copySelection without the capability is refused", async () => {
  const {s, calls} = await session({copy: false});
  await assert.rejects(s.copySelection(), {code: "UNSUPPORTED_OPERATION"});
  assert.deepEqual(calls, []);
  await s.close();
});

// SPEC-P-calc-copy 9.1.3: the core's text/html rides in the same reply (findings/evidence/calc-v8/n-copy-01, B1:C2's reply,
// shortened); absent on a v7 engine.
const HTML = '<!DOCTYPE html>\n<html><body><table cellspacing="0" border="0"><tr><td>42</td><td>84</td></tr></table></body></html>\n';

test("htmlText is kept as it came when the engine sends it, and must be text", () => {
  assert.equal(normalizeCopy({...NATIVE, htmlText: HTML}).htmlText, HTML);
  assert.equal("htmlText" in normalizeCopy(NATIVE), false);
  for (const htmlText of [null, 42, {}])
    assert.throws(() => normalizeCopy({...NATIVE, htmlText}), {code: "CELL_RESULT_INVALID"}, String(htmlText));
});

test("copySelection hands the page htmlText, or null from an engine without it", async () => {
  const {s, doc} = await session();
  assert.equal((await s.copySelection()).htmlText, null);
  const copyRange = doc.copyRange.bind(doc);
  doc.copyRange = (...args) => copyRange(...args).then(({copy}) => ({copy: {...copy, htmlText: HTML}}));
  assert.equal((await s.copySelection()).htmlText, HTML);
  await s.close();
});

test("copyHtmlSupported needs cell-copy-html on top of cell-copy", async () => {
  assert.equal((await opened(["cell-copy", "cell-copy-html"])).handle.copyHtmlSupported, true);
  assert.equal((await opened(["cell-copy"])).handle.copyHtmlSupported, false);
  assert.equal((await opened(["cell-copy-html"])).handle.copyHtmlSupported, false);
});
