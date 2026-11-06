// SPEC-P-calc-sheets 4.1: U-T1..U-T3, the pure functions behind the name box and pointed references.
import assert from "node:assert/strict";
import test from "node:test";
import { parseCellTarget, referenceSlot, sheetReference } from "../spreadsheet-shell/calc-editor-session.js";

// tools/create_calc_sheets_fixture.py's nine sheets.
const NAMES = ["編輯測試", "另一張表", "保護測試", "邊界測試", "陣列測試", "有 空白", "2026", "O'Neil", "Sheet_3"];
const at = (part, column, row, endColumn, endRow) => ({part, column, row, endColumn, endRow});

test("U-T1 sheetReference spells references the way the core does (E1)", () => {
  assert.equal(sheetReference(NAMES, 0, at(1, 0, 0)), "$另一張表.A1");
  assert.equal(sheetReference(NAMES, 0, at(5, 1, 0)), "$'有 空白'.B1");
  assert.equal(sheetReference(NAMES, 0, at(6, 1, 0)), "$'2026'.B1");
  assert.equal(sheetReference(NAMES, 0, at(7, 1, 0)), "$'O''Neil'.B1");
  assert.equal(sheetReference(NAMES, 0, at(8, 1, 0)), "$Sheet_3.B1");
  assert.equal(sheetReference(NAMES, 0, at(0, 1, 0)), "B1");
  assert.equal(sheetReference(NAMES, 5, at(5, 1, 0)), "B1");
  assert.equal(sheetReference(NAMES, 0, at(5, 1, 0, 2, 1)), "$'有 空白'.B1:C2");
  assert.equal(sheetReference(NAMES, 0, at(0, 26, 999, 26, 999)), "AA1000");
});

test("U-T2 referenceSlot: after an operator, an open bracket or a separator, and the previous point", () => {
  for (const text of ["=", "=SUM(", "=A1+", "=A1 + ", "=IF(A1;", "=A1:", "=-"])
    assert.deepEqual(referenceSlot(text, text.length), {start: text.length, end: text.length}, text);
  for (const text of ["=A1", "=5", "=SUM(A1)", "abc", "", "=A1%"])
    assert.equal(referenceSlot(text, text.length), null, text);
  assert.equal(referenceSlot("=A1+", 0), null);
  // In the middle: =SUM(|) takes a reference before the closing bracket.
  assert.deepEqual(referenceSlot("=SUM()", 5), {start: 5, end: 5});
  // A selection after an operator is replaced.
  assert.deepEqual(referenceSlot("=A1+B2", 4, 6), {start: 4, end: 6});
  // Right after the previous point: replace it, as desktop Calc does.
  const last = {start: 1, end: 3, text: "B1"};
  assert.deepEqual(referenceSlot("=B1", 3, 3, last), {start: 1, end: 3});
  // ... but not once the text there has changed.
  assert.equal(referenceSlot("=B2", 3, 3, last), null);
});

test("U-T3 parseCellTarget reads the name box", () => {
  assert.deepEqual(parseCellTarget("A1", NAMES), {column: 0, row: 0, part: null});
  assert.deepEqual(parseCellTarget(" $B$2 ", NAMES), {column: 1, row: 1, part: null});
  assert.deepEqual(parseCellTarget("另一張表.A1", NAMES), {column: 0, row: 0, part: 1});
  assert.deepEqual(parseCellTarget("$另一張表.A1", NAMES), {column: 0, row: 0, part: 1});
  assert.deepEqual(parseCellTarget("'有 空白'.B1", NAMES), {column: 1, row: 0, part: 5});
  assert.deepEqual(parseCellTarget("$'O''Neil'.c3", NAMES), {column: 2, row: 2, part: 7});
  assert.deepEqual(parseCellTarget("另一張表!A1", NAMES), {column: 0, row: 0, part: 1});
  assert.deepEqual(parseCellTarget("SHEET_3.B1", NAMES), {column: 1, row: 0, part: 8});
  assert.deepEqual(parseCellTarget("xfd1048576", NAMES), {column: 16383, row: 1048575, part: null});
  assert.deepEqual(parseCellTarget("不存在.A1", NAMES), {error: "UNKNOWN_SHEET", sheet: "不存在"});
  for (const text of ["A0", "XFE1", "A1048577", "A01", "1A", "", "A1:B2", "另一張表."])
    assert.deepEqual(parseCellTarget(text, NAMES), {error: "INVALID_ADDRESS"}, text);
});
