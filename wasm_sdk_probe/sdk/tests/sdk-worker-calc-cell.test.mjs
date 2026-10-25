import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../sdk-worker.js", import.meta.url), "utf8");
function worker(capabilities = []) {
  const posted = [];
  const self = { location: { href: "https://test/sdk-worker.js" }, addEventListener() {},
    postMessage(message) { posted.push(JSON.parse(JSON.stringify(message))); } };
  const context = vm.createContext({ self, console, URL, TextDecoder, TextEncoder,
    setTimeout, clearTimeout, queueMicrotask, Uint8Array });
  vm.runInContext(source, context);
  vm.runInContext(`activeManifest = { profile: "test", capabilities: ${JSON.stringify(capabilities)} };
    moduleInstance = { calls: [], HEAPU8: new Uint8Array(200000),
      ccall(name, rt, types, args) { this.calls.push({name,args}); return name === "oxsdk_buffer_alloc" ? 32 : 0; } };`, context);
  return {
    request(operation, payload = {}) {
      vm.runInContext(`handleRequest(${JSON.stringify({ protocolVersion: 1, kind: "request", requestId: posted.length + 1,
        operation, payload: { documentHandle: 8, expectedRevision: 2, part: 0, column: 1, row: 3, ...payload } })})`, context);
      return posted.at(-1);
    },
    calls() { return JSON.parse(JSON.stringify(vm.runInContext("moduleInstance.calls", context))); },
    deliver(event) {
      vm.runInContext('pending.set(77, {operation:"cellRead"})', context);
      vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify({ requestId: 77, ...event }))})`, context);
      return posted.at(-1);
    },
  };
}

test("cell operations without the declaration never touch a WASM symbol", () => {
  const w = worker(["save-odt"]);
  for (const operation of ["cellRead", "cellHit", "cellInput", "cellFormat"])
    assert.equal(w.request(operation).error.code, "UNSUPPORTED_OPERATION");
  assert.deepEqual(w.calls(), []);
});

test("fractional, missing or negative cell indices refuse before ccall", () => {
  for (const payload of [{column:1.5}, {row:-1}, {part:"0"}, {column:null}, {expectedRevision:NaN}]) {
    const w = worker(["cell-editing"]);
    assert.equal(w.request("cellRead", payload).error.code, "INVALID_ARGUMENT");
    assert.deepEqual(w.calls(), []);
  }
});

test("empty input clears a cell without allocating an empty WASM buffer", () => {
  const w = worker(["cell-editing"]);
  assert.equal(w.request("cellInput", {text:""}), undefined);
  assert.deepEqual(w.calls(), [{name:"oxsdk_document_cell", args:[1,8,2,0,1,3,1,0,0,0]}]);
});

test("format action and enabled are validated before dispatch", () => {
  for (const payload of [{format:"font-family", enabled:true}, {format:"bold",enabled:1}]) {
    const w = worker(["cell-editing"]);
    assert.equal(w.request("cellFormat",payload).error.code,"INVALID_ARGUMENT");
    assert.deepEqual(w.calls(),[]);
  }
  const w = worker(["cell-editing"]);
  w.request("cellFormat",{format:"italic",enabled:true});
  assert.deepEqual(w.calls().at(-1),{name:"oxsdk_document_cell",args:[1,8,2,0,1,3,3,0,0,1]});
});

test("ODS save requires its own capability and preserves ODT save gating", () => {
  const old = worker(["save-odt"]);
  assert.equal(old.request("save",{format:"ods"}).error.code,"UNSUPPORTED_OPERATION");
  assert.deepEqual(old.calls(),[]);
  const current = worker(["save-ods"]);
  current.request("save",{format:"ods"});
  assert.equal(current.calls().some(c=>c.name==="oxsdk_document_save"),true);
  assert.equal(current.request("save",{format:"odt"}).error.code,"UNSUPPORTED_OPERATION");
});

test("cell result forwards named fields and the actual model payload", () => {
  const w = worker();
  const result = w.deliver({type:"cell-result",revision:4,changed:true,
    cellJson:JSON.stringify({input:"=B1*3",value:"63"}),internal:"do not forward"});
  assert.deepEqual(result.result,{revision:4,changed:true,cell:{input:"=B1*3",value:"63"}});
});
