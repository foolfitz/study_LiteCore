// SPEC-P-calc-copy 3.2: the ods-editor-v7 worker, as tools/derive_ms_formats_worker.py --profile calc-copy derives it
// (dist/profiles/ods-editor-v6/sdk-worker.js + tests/ods-v7-worker-delta.json), against the frozen v6 worker as the control.
// The harness is tests/ods-v6-worker.test.mjs's.
import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const here = new URL("..", import.meta.url).pathname;
const dir = mkdtempSync(join(tmpdir(), "ods-v7-worker-"));
execFileSync("python3", ["tools/derive_ms_formats_worker.py", "--profile", "calc-copy", "--out", join(dir, "w.js")], {cwd: here});
const v7 = readFileSync(join(dir, "w.js"), "utf8");
rmSync(dir, {recursive: true});
const v6 = readFileSync(new URL("../dist/profiles/ods-editor-v6/sdk-worker.js", import.meta.url), "utf8");
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

const V6 = ["cell-editing", "cell-range-formatting", "cell-range-styling", "cell-headers", "cell-structure"];
const ALL = [...V6, "cell-copy"];

test("cellCopy needs cell-copy and never touches WASM without it", () => {
  const w = worker(v7, V6);
  assert.equal(w.request("cellCopy", {column: 1, row: 0, endColumn: 2, endRow: 1}).error.code, "UNSUPPORTED_OPERATION");
  assert.deepEqual(w.cells(), []);
});

test("cellCopy is cell operation 15 with the endpoints as the bridge's JSON", () => {
  const w = worker(v7, ALL);
  assert.equal(w.request("cellCopy", {part: 2, column: 1, row: 0, endColumn: 2, endRow: 1, extra: 1}), undefined);
  const [call] = w.cells();
  assert.equal(call.args[6], 15);
  assert.deepEqual(call.args.slice(3, 6), [2, 1, 0]);
  assert.deepEqual(JSON.parse(call.text), {endColumn: 2, endRow: 1});
});

test("whole columns, rows and the sheet pass the cell limit; other large rectangles do not", () => {
  for (const range of [{column: 0, row: 0, endColumn: 0, endRow: ROWS - 1}, {column: 0, row: 4, endColumn: COLUMNS - 1, endRow: 9},
                       {column: 0, row: 0, endColumn: COLUMNS - 1, endRow: ROWS - 1}]) {
    const w = worker(v7, ALL);
    assert.equal(w.request("cellCopy", range), undefined, JSON.stringify(range));
    assert.equal(w.cells().length, 1);
  }
  for (const range of [{column: 0, row: 0, endColumn: 25, endRow: 2999}, {column: 3, row: 3, endColumn: 2, endRow: 3},
                       {column: 0, row: 0, endColumn: 1}, {column: 0, row: 0, endColumn: 0.5, endRow: 1}]) {
    const w = worker(v7, ALL);
    assert.equal(w.request("cellCopy", range).error.code, "INVALID_ARGUMENT", JSON.stringify(range));
    assert.deepEqual(w.cells(), []);
  }
});

test("control: the frozen v6 worker has no cellCopy", () => {
  const w = worker(v6, ALL);
  assert.equal(w.request("cellCopy", {column: 1, row: 0, endColumn: 2, endRow: 1}).error.code, "UNKNOWN_OPERATION");
  assert.deepEqual(w.cells(), []);
});
