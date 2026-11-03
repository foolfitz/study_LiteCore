// SPEC-P-ms-formats 5.2, the Calc session's half: a spreadsheet is saved in the
// format the engine opened it as, and Save As is a copy that leaves the saved
// revision where it was.  The fixture is calc-editor-session.test.mjs's.
import assert from "node:assert/strict";
import test from "node:test";
const { CalcEditorSession, calcDocumentFormatOf, CALC_SAVE_FORMATS } =
  await import(process.env.CALC_SESSION_MODULE || "../spreadsheet-shell/calc-editor-session.js");

async function opened({ format, name = "test.ods", readOnly = false } = {}) {
  const calls = [];
  let formula = "原始內容";
  const doc = { revision: 0, parts: 1, documentType: "spreadsheet", partNames: ["Sheet1"], partVisible: [true],
    currentPart: 0, widthTwips: 9000, heightTwips: 9000, format,
    async setPart(part) { this.currentPart = part; return { part, widthTwips: 9000, heightTwips: 9000 }; },
    async close() {}, async render() {},
    cell(col = 0, row = 0) { return { part: this.currentPart, column: col, row, endColumn: col, endRow: row, input: formula,
      formula, text: formula, writable: true, bold: false, italic: false, underline: false,
      xTwips: col * 1000, yTwips: row * 300, widthTwips: 999, heightTwips: 299 }; },
    async readCell(col, row) { return { cell: this.cell(col, row) }; },
    async setCellInput(col, row, text) { calls.push(["input", text]); formula = text; this.revision++;
      return { cell: this.cell(col, row), changed: true }; },
    async save(options) { calls.push(["export", options.format]); return new TextEncoder().encode(options.format).buffer; },
  };
  const session = new CalcEditorSession({ engineFactory: async () => ({ manifest: { capabilities: ["open-ods"] },
    open: async () => doc, dispose() {} }) });
  await session.open({ bytes: new ArrayBuffer(8), name, readOnly });
  return { session, doc, calls };
}

test("the save format is the engine's, and only one the Calc engine can write", () => {
  assert.deepEqual(CALC_SAVE_FORMATS, ["ods", "xlsx"]);
  assert.equal(calcDocumentFormatOf({ format: "xlsx" }), "xlsx");
  assert.equal(calcDocumentFormatOf({ format: "ods" }), "ods");
  // v4's .odt path: opened under a text name, saved as ODS as it always was.
  assert.equal(calcDocumentFormatOf({ format: "odt" }), "ods");
  assert.equal(calcDocumentFormatOf({ format: null }), "ods");
  assert.equal(calcDocumentFormatOf({}), "ods");
  assert.equal(calcDocumentFormatOf(null), "ods");
});

test("an XLSX is saved as XLSX, and the host is told the format", async () => {
  const { session, calls } = await opened({ format: "xlsx", name: "book.xlsx" });
  assert.equal(session.documentFormat(), "xlsx");
  session.beginEdit("formula"); session.setDraft("新內容");
  let told;
  await session.save(async (bytes, meta) => { told = { ...meta, bytes: new TextDecoder().decode(bytes) }; return {}; });
  assert.deepEqual(told, { name: "book.xlsx", format: "xlsx", bytes: "xlsx" });
  assert.deepEqual(calls.filter((c) => c[0] === "export"), [["export", "xlsx"]]);
  assert.equal(session.hasUnsavedEdits(), false);
  await session.close();
});

test("an engine that does not say saves ODS, as v4 did", async () => {
  const { session, calls } = await opened({});
  await session.save(async () => ({}));
  assert.deepEqual(calls.filter((c) => c[0] === "export"), [["export", "ods"]]);
  await session.close();
});

test("Save As: the chosen format, the draft committed first, and the edits still unsaved", async () => {
  const { session, calls } = await opened({ format: "xlsx", name: "book.xlsx" });
  session.beginEdit("formula"); session.setDraft("草稿");
  const copy = await session.saveCopy("ods", async (bytes, meta) => ({ got: new TextDecoder().decode(bytes), meta }));
  assert.deepEqual(calls, [["input", "草稿"], ["export", "ods"]]);
  assert.deepEqual(copy.result, { got: "ods", meta: { format: "ods" } });
  assert.equal(copy.format, "ods");
  assert.equal(session.hasUnsavedEdits(), true, "a copy is not a save of this document");
  assert.equal(session.state.committedDirty, true);
  // The next save is still the document's own.
  await session.save(async () => ({}));
  assert.deepEqual(calls.at(-1), ["export", "xlsx"]);
  assert.equal(session.hasUnsavedEdits(), false);
  await session.close();
});

test("Save As refuses a read-only document and a format Calc does not write", async () => {
  const ro = await opened({ format: "xlsx", name: "book.xlsx", readOnly: true });
  await assert.rejects(ro.session.saveCopy("ods", async () => ({})), { code: "READ_ONLY" });
  assert.deepEqual(ro.calls, []);
  await ro.session.close();
  const { session, calls } = await opened({ format: "xlsx", name: "book.xlsx" });
  await assert.rejects(session.saveCopy("odt", async () => ({})), { code: "INVALID_ARGUMENT" });
  await assert.rejects(session.saveCopy("docx", async () => ({})), { code: "INVALID_ARGUMENT" });
  assert.deepEqual(calls, []);
  await session.close();
});

test("a failed copy changes nothing and the session keeps working", async () => {
  const { session, calls } = await opened({ format: "xlsx", name: "book.xlsx" });
  session.beginEdit("formula"); session.setDraft("x");
  await session.commit();
  const taken = Object.assign(new Error("taken"), { code: "NAME_TAKEN" });
  await assert.rejects(session.saveCopy("ods", async () => { throw taken; }), (e) => e === taken);
  assert.equal(session.state.saving, false);
  assert.equal(session.hasUnsavedEdits(), true);
  await session.save(async () => ({}));
  assert.deepEqual(calls.at(-1), ["export", "xlsx"]);
  await session.close();
});
