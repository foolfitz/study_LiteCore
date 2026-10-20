// SPEC-M4-ods-in-nextcloud 3.2: the worker half of the read-only spreadsheet
// viewer (W7, B1).  What the worker built from this source adds:
//
//   * four operations -- setPart, currentPart, partName (capability
//     `part-switch`) and partText (`part-text`) -- refused on a profile that
//     does not declare the capability, so an editor engine, which has no such
//     export, never has the symbol reached for;
//   * a part that is not an integer refused before the engine (ccall would
//     make it 0, the first sheet, silently);
//   * their replies, named fields only;
//   * the open reply's `documentType` and `inputSuffix`, present only when the
//     engine sent them, so an editor engine's reply keeps its exact shape.
//
// Same harness as sdk-worker-v20.test.mjs: the real worker script in a vm
// context with a stub `self`.  ODS_VIEWER_WORKER points it at another copy
// (tests/sdk_worker_ods_viewer_mutations.py uses that for the red cases).

import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(process.env.ODS_VIEWER_WORKER
  || fileURLToPath(new URL("../sdk-worker.js", import.meta.url)), "utf8");

function worker() {
  const posted = [];
  const self = {
    location: { href: "https://example.test/sdk-worker.js" },
    addEventListener() {},
    postMessage(message) { posted.push(message); },
  };
  const context = vm.createContext({ self, console, URL, TextDecoder, TextEncoder,
                                     setTimeout, clearTimeout, queueMicrotask });
  vm.runInContext(SOURCE, context, { filename: "sdk-worker.js" });
  const plain = (value) => JSON.parse(JSON.stringify(value));
  const deliver = (requestId, operation, event) => {
    vm.runInContext(`pending.set(${requestId}, { operation: ${JSON.stringify(operation)} });`,
                    context);
    vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify(event))})`, context);
    return plain(posted.at(-1));
  };
  const initialised = (manifest) => {
    vm.runInContext(
      `moduleInstance = { calls: [], ccall(name, returnType, types, args) {
         this.calls.push({ name, args }); return 0; } };
       activeManifest = ${JSON.stringify(manifest)};`, context);
  };
  const request = (requestId, operation, payload) => {
    const before = posted.length;
    vm.runInContext(`handleRequest(${JSON.stringify({ protocolVersion: 1, kind: "request",
                                                        requestId, operation, payload })})`,
                    context);
    return {
      response: posted.length > before ? plain(posted.at(-1)) : null,
      calls: plain(vm.runInContext("moduleInstance.calls", context)),
    };
  };
  // The open reply needs both halves: `opened` and the engine's view-ready.
  const open = (event) => {
    vm.runInContext(`pending.set(5, { operation: "open" }); openStates.set(5, {});`, context);
    vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify(event))})`, context);
    vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify(
      { type: "view-ready", requestId: 5, documentHandle: 1, revision: 0 }))})`, context);
    // The RAW message as well: a JSON round trip drops a key whose value is
    // undefined, and structured clone -- what postMessage does -- keeps it.
    const raw = posted.find((m) => m.kind === "response" && m.requestId === 5);
    return { ...plain(raw), rawResultKeys: raw ? Object.keys(raw.result) : null };
  };
  return { deliver, initialised, request, open };
}

const VIEWER = { profile: "ods-viewer-v1",
                 capabilities: ["open-odt", "rgba-tile", "cancel-queued", "search",
                                "open-ods", "part-switch", "part-text"] };
const EDITOR = { profile: "e2-editor-v22",
                 capabilities: ["open-odt", "rgba-tile", "insert-text", "save-odt"] };
const OPENED = { type: "opened", requestId: 5, documentHandle: 1, revision: 0, parts: 3,
                 width: 26593, height: 13005, tileMode: 1 };

test("the open reply carries documentType and inputSuffix when the engine sends them", () => {
  const message = worker().open({ ...OPENED, documentType: "spreadsheet", inputSuffix: ".ods" });
  assert.equal(message.ok, true, JSON.stringify(message));
  assert.equal(message.result.documentType, "spreadsheet");
  assert.equal(message.result.inputSuffix, ".ods");
  assert.equal(message.result.parts, 3);
});

test("an editor engine's open reply keeps exactly the keys it had", () => {
  const message = worker().open(OPENED);
  assert.equal(message.ok, true, JSON.stringify(message));
  assert.deepEqual(message.rawResultKeys.sort(),
                   ["documentHandle", "height", "parts", "revision", "tileMode", "viewReady", "width"]);
});

test("the four replies pass through with named fields only", () => {
  const w = worker();
  const extra = { engineInternal: "never forwarded", schemaVersion: 1, documentHandle: 1 };
  assert.deepEqual(w.deliver(11, "setPart", { type: "part-set", requestId: 11, revision: 0,
                                             part: 2, width: 9000, height: 4000, ...extra }).result,
                   { part: 2, width: 9000, height: 4000, revision: 0 });
  assert.deepEqual(w.deliver(12, "currentPart", { type: "current-part", requestId: 12, revision: 0,
                                                 part: 1, ...extra }).result,
                   { part: 1, revision: 0 });
  assert.deepEqual(w.deliver(13, "partName", { type: "part-name", requestId: 13, revision: 0,
                                              part: 0, name: "Alpha", ...extra }).result,
                   { part: 0, name: "Alpha", revision: 0 });
  assert.deepEqual(w.deliver(14, "partText", { type: "part-text", requestId: 14, revision: 0,
                                              part: 1, text: "Beta\n", partBefore: 0, partAfter: 0,
                                              ...extra }).result,
                   { part: 1, text: "Beta\n", partBefore: 0, partAfter: 0, revision: 0 });
});

test("on an editor profile every viewer operation is refused and no symbol is reached for", () => {
  const w = worker();
  w.initialised(EDITOR);
  for (const [id, operation] of [[21, "setPart"], [22, "currentPart"], [23, "partName"], [24, "partText"]]) {
    const { response, calls } = w.request(id, operation, { documentHandle: 1, part: 1 });
    assert.equal(response.ok, false, operation);
    assert.equal(response.error.code, "UNSUPPORTED_OPERATION", operation);
    assert.deepEqual(calls, [], `${operation} reached for ${JSON.stringify(calls)}`);
  }
});

test("part-switch does not open partText: each capability gates its own operations", () => {
  const w = worker();
  w.initialised({ ...VIEWER, capabilities: VIEWER.capabilities.filter((c) => c !== "part-text") });
  const { response, calls } = w.request(31, "partText", { documentHandle: 1, part: 0 });
  assert.equal(response.error.code, "UNSUPPORTED_OPERATION");
  assert.equal(response.error.requiredCapability, "part-text");
  assert.deepEqual(calls, []);
  const allowed = w.request(32, "setPart", { documentHandle: 1, part: 0 });
  assert.deepEqual(allowed.calls, [{ name: "oxsdk_document_set_part", args: [32, 1, 0] }]);
});

test("on the viewer profile each operation calls its own export with request, handle and part", () => {
  const w = worker();
  w.initialised(VIEWER);
  const expected = [
    [41, "setPart", { documentHandle: 7, part: 2 }, { name: "oxsdk_document_set_part", args: [41, 7, 2] }],
    [42, "partName", { documentHandle: 7, part: 1 }, { name: "oxsdk_document_part_name", args: [42, 7, 1] }],
    [43, "partText", { documentHandle: 7, part: 0 }, { name: "oxsdk_document_part_text", args: [43, 7, 0] }],
    [44, "currentPart", { documentHandle: 7 }, { name: "oxsdk_document_current_part", args: [44, 7] }],
  ];
  for (const [id, operation, payload, call] of expected) {
    const { response, calls } = w.request(id, operation, payload);
    assert.equal(response, null, `${operation} answered before the engine: ${JSON.stringify(response)}`);
    assert.deepEqual(calls.at(-1), call, operation);
  }
});

test("a part that is not an integer is refused before the engine", () => {
  const w = worker();
  w.initialised(VIEWER);
  for (const [id, part] of [[51, undefined], [52, "1"], [53, 1.5], [54, null]]) {
    const { response, calls } = w.request(id, "setPart", { documentHandle: 7, part });
    assert.equal(response.ok, false, `part ${JSON.stringify(part)}`);
    assert.equal(response.error.code, "INVALID_ARGUMENT", `part ${JSON.stringify(part)}`);
    assert.deepEqual(calls, [], `part ${JSON.stringify(part)} reached the engine`);
  }
});
