// SPEC-P-calc-zoom 3.2: the ods-editor-v8 worker, as tools/derive_ms_formats_worker.py --profile calc-html-zoom derives it
// (dist/profiles/ods-editor-v7/sdk-worker.js + tests/ods-v8-worker-delta.json), against the frozen v7 worker as the control.
// The harness is tests/ods-v7-worker.test.mjs's.
import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const here = new URL("..", import.meta.url).pathname;
const dir = mkdtempSync(join(tmpdir(), "ods-v8-worker-"));
execFileSync("python3", ["tools/derive_ms_formats_worker.py", "--profile", "calc-html-zoom", "--out", join(dir, "w.js")], {cwd: here});
const v8 = readFileSync(join(dir, "w.js"), "utf8");
rmSync(dir, {recursive: true});
const v7 = readFileSync(new URL("../dist/profiles/ods-editor-v7/sdk-worker.js", import.meta.url), "utf8");
const bridge = readFileSync(new URL("../src/calc_cell_bridge.cpp", import.meta.url), "utf8");
const LEVELS = bridge.match(/constexpr int kTileTwips\[\] = \{([0-9, ]+)\};/)[1].split(",").map(Number);

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

const V7 = ["cell-editing", "cell-range-formatting", "cell-range-styling", "cell-headers", "cell-structure", "cell-copy"];
const ALL = [...V7, "cell-copy-html", "cell-zoom"];

test("the worker's closed list is the bridge's", () => {
  assert.deepEqual(LEVELS, [7680, 5120, 3840, 3072, 2560, 1920]);
  assert.ok(v8.includes(`![${LEVELS.join(", ")}].includes(payload.tileTwips)`));
});

test("cellZoom needs cell-zoom and never touches WASM without it", () => {
  const w = worker(v8, V7);
  assert.equal(w.request("cellZoom", {tileTwips: 3840}).error.code, "UNSUPPORTED_OPERATION");
  assert.deepEqual(w.cells(), []);
});

test("cellZoom is cell operation 16 with {tileTwips} as the bridge's JSON, for every level", () => {
  for (const tileTwips of LEVELS) {
    const w = worker(v8, ALL);
    assert.equal(w.request("cellZoom", {part: 1, tileTwips, extra: 1}), undefined);
    const [call] = w.cells();
    assert.equal(call.args[6], 16);
    assert.deepEqual(call.args.slice(3, 6), [1, 0, 0]);
    assert.deepEqual(JSON.parse(call.text), {tileTwips});
  }
});

test("a tileTwips outside the list is refused before WASM", () => {
  for (const tileTwips of [1234, 0, -3840, 3840.5, "3840", undefined, null]) {
    const w = worker(v8, ALL);
    assert.equal(w.request("cellZoom", {tileTwips}).error.code, "INVALID_ARGUMENT", String(tileTwips));
    assert.deepEqual(w.cells(), []);
  }
});

test("cellCopy is unchanged: op 15 with the endpoints", () => {
  const w = worker(v8, ALL);
  assert.equal(w.request("cellCopy", {column: 1, row: 0, endColumn: 2, endRow: 1}), undefined);
  const [call] = w.cells();
  assert.equal(call.args[6], 15);
  assert.deepEqual(JSON.parse(call.text), {endColumn: 2, endRow: 1});
});

test("control: the frozen v7 worker has no cellZoom", () => {
  const w = worker(v7, ALL);
  assert.equal(w.request("cellZoom", {tileTwips: 3840}).error.code, "UNKNOWN_OPERATION");
  assert.deepEqual(w.cells(), []);
});
