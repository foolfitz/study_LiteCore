// SPEC-P-calc-headers 3.3: the ods-editor-v6 worker, as tools/derive_ms_formats_worker.py --profile calc-headers derives it
// (dist/profiles/ods-editor-v5/sdk-worker.js + tests/ods-v6-worker-delta.json), against the frozen v5 worker as the control.
// The harness is sdk/tests/sdk-worker-calc-cell.test.mjs's.
import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const here = new URL("..", import.meta.url).pathname;
const dir = mkdtempSync(join(tmpdir(), "ods-v6-worker-"));
execFileSync("python3", ["tools/derive_ms_formats_worker.py", "--profile", "calc-headers", "--out", join(dir, "w.js")], {cwd: here});
const v6 = readFileSync(join(dir, "w.js"), "utf8");
rmSync(dir, {recursive: true});
const v5 = readFileSync(new URL("../dist/profiles/ods-editor-v5/sdk-worker.js", import.meta.url), "utf8");
const ROWS = 1048576, COLUMNS = 16384;

function worker(source, capabilities) {
  const posted = [];
  const self = { location: { href: "https://test/sdk-worker.js" }, addEventListener() {},
    postMessage(message) { posted.push(JSON.parse(JSON.stringify(message))); } };
  const context = vm.createContext({ self, console, URL, TextDecoder, TextEncoder, setTimeout, clearTimeout, queueMicrotask, Uint8Array });
  vm.runInContext(source, context);
  vm.runInContext(`activeManifest = { profile: "test", capabilities: ${JSON.stringify(capabilities)} };
    moduleInstance = { calls: [], HEAPU8: new Uint8Array(200000),
      ccall(name, rt, types, args) { this.calls.push({name, args, text: name === "oxsdk_document_cell" && args[8] > 0
        ? new TextDecoder().decode(this.HEAPU8.subarray(args[7], args[7] + args[8])) : null});
        return name === "oxsdk_buffer_alloc" ? 32 : 0; } };`, context);
  return {
    request(operation, payload = {}) {
      vm.runInContext(`handleRequest(${JSON.stringify({ protocolVersion: 1, kind: "request", requestId: posted.length + 1,
        operation, payload: { documentHandle: 8, expectedRevision: 2, part: 0, column: 0, row: 0, ...payload } })})`, context);
      return posted.at(-1);
    },
    cells() { return JSON.parse(JSON.stringify(vm.runInContext("moduleInstance.calls", context))).filter(c => c.name === "oxsdk_document_cell"); },
  };
}

const ALL = ["cell-editing", "cell-range-formatting", "cell-range-styling", "cell-headers"];

test("cellHeaders needs cell-headers and never touches WASM without it", () => {
  const w = worker(v6, ["cell-editing", "cell-range-formatting"]);
  assert.equal(w.request("cellHeaders", {rectangle: {x: 0, y: 0, width: 10, height: 10}}).error.code, "UNSUPPORTED_OPERATION");
  assert.deepEqual(w.cells(), []);
});

test("cellHeaders is cell operation 13 with the rectangle as the bridge's JSON", () => {
  const w = worker(v6, ALL);
  assert.equal(w.request("cellHeaders", {rectangle: {x: 4410, y: 1095, width: 9000, height: 0}}), undefined);
  const [call] = w.cells();
  assert.equal(call.args[6], 13);
  assert.deepEqual(JSON.parse(call.text), {x: 4410, y: 1095, width: 9000, height: 0});
});

test("a rectangle the bridge would refuse is refused before ccall", () => {
  for (const rectangle of [undefined, {x: 0, y: 0, width: 0, height: 0}, {x: -1, y: 0, width: 5, height: 5},
                           {x: 0, y: 0, width: 245761, height: 5}, {x: 0.5, y: 0, width: 5, height: 5}, {x: 0, y: 0, width: 5}]) {
    const w = worker(v6, ALL);
    assert.equal(w.request("cellHeaders", {rectangle}).error.code, "INVALID_ARGUMENT", JSON.stringify(rectangle));
    assert.deepEqual(w.cells(), []);
  }
});

test("whole column, whole row and the sheet pass the cell limit; nothing else does", () => {
  const passes = [{column: 2, endColumn: 2, row: 0, endRow: ROWS - 1}, {column: 0, endColumn: COLUMNS - 1, row: 5, endRow: 5},
                  {column: 0, endColumn: COLUMNS - 1, row: 0, endRow: ROWS - 1}];
  const refused = [{column: 2, endColumn: 2, row: 0, endRow: ROWS - 2}, {column: 1, endColumn: COLUMNS - 1, row: 0, endRow: 4},
                   {column: 0, endColumn: 1, row: 0, endRow: 39999}];
  for (const range of passes) {
    const w = worker(v6, ALL);
    assert.equal(w.request("rangeFormat", {...range, format: "bold", enabled: true}), undefined, JSON.stringify(range));
    assert.equal(w.cells()[0].args[6], 7);
  }
  for (const range of refused) {
    const w = worker(v6, ALL);
    assert.equal(w.request("rangeFormat", {...range, format: "bold", enabled: true}).error.code, "INVALID_ARGUMENT", JSON.stringify(range));
    assert.deepEqual(w.cells(), []);
  }
});

test("control: the frozen v5 worker has neither", () => {
  const w = worker(v5, ALL);
  assert.equal(w.request("cellHeaders", {rectangle: {x: 0, y: 0, width: 10, height: 10}}).error.code, "UNKNOWN_OPERATION");
  assert.equal(w.request("rangeFormat", {column: 2, endColumn: 2, row: 0, endRow: ROWS - 1, format: "bold", enabled: true}).error.code,
               "INVALID_ARGUMENT");
  assert.deepEqual(w.cells(), []);
});

// SPEC-P-calc-structure 3.2: cellStructure, cell operation 14, on the same unreleased v6 worker.
const STRUCTURE = [...ALL, "cell-structure"];

test("cellStructure needs cell-structure and never touches WASM without it", () => {
  const w = worker(v6, ALL);
  assert.equal(w.request("cellStructure", {change: {axis: "rows", action: "insert", index: 1, count: 2}}).error.code,
               "UNSUPPORTED_OPERATION");
  assert.deepEqual(w.cells(), []);
});

test("cellStructure is cell operation 14 with the change as the bridge's JSON", () => {
  const w = worker(v6, STRUCTURE);
  assert.equal(w.request("cellStructure", {change: {axis: "columns", action: "delete", index: 3, count: 2, extra: 1}}), undefined);
  const [call] = w.cells();
  assert.equal(call.args[6], 14);
  assert.deepEqual(JSON.parse(call.text), {axis: "columns", action: "delete", index: 3, count: 2});
});

test("a change the bridge would refuse is refused before ccall", () => {
  for (const change of [undefined, {axis: "x", action: "insert", index: 0, count: 1}, {axis: "rows", action: "move", index: 0, count: 1},
                        {axis: "rows", action: "insert", index: 0, count: 0}, {axis: "rows", action: "insert", index: -1, count: 1},
                        {axis: "rows", action: "insert", index: ROWS - 1, count: 2}, {axis: "columns", action: "delete", index: COLUMNS, count: 1},
                        {axis: "rows", action: "insert", index: 0.5, count: 1}]) {
    const w = worker(v6, STRUCTURE);
    assert.equal(w.request("cellStructure", {change}).error.code, "INVALID_ARGUMENT", JSON.stringify(change));
    assert.deepEqual(w.cells(), []);
  }
});

test("control: the frozen v5 worker has no cellStructure", () => {
  const w = worker(v5, STRUCTURE);
  assert.equal(w.request("cellStructure", {change: {axis: "rows", action: "insert", index: 1, count: 1}}).error.code,
               "UNKNOWN_OPERATION");
  assert.deepEqual(w.cells(), []);
});
