// SPEC-M3-link-batch, v20 part 1: what the worker built from this source adds
// over the v15 archive's worker (00882139...), each with its red case.
//
//   * `documentSizeChangedCount` (12.3) is NAMED in every editor-state
//     projection -- the v2 state reply, the announcement, and the product
//     projection -- because every one of them is an allowlist, and an engine
//     field nothing names here does not exist as far as the page is concerned
//     (the `itemCount` and `documentSizeChanged` precedents in the worker);
//   * `page-rectangles` (10.8) passes through as a document-level operation
//     gated on the contract's declaration, the redo precedent, so a profile
//     whose binary lacks the export never has the symbol reached for;
//   * C's completion (10.5) carries `boundaryNoop.waitedMs`, and every barrier
//     refusal carries `caretBefore` (10.6), named fields only, like keyUndo
//     and mergeKey (M1-4).
//
// Same harness as sdk-worker-merge-key.test.mjs: the real worker script in a
// vm context with a stub `self`.

import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(fileURLToPath(new URL("../sdk-worker.js", import.meta.url)), "utf8");
const DECLARATION = "document-sdk-page-rectangles";

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
  /** Initialise the worker as if init had run against `manifest`, with a stub module. */
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
  return { deliver, initialised, request, posted };
}

const STATE = {
  sourceSequence: 41, documentChangeSequence: 7, documentSizeChangedCount: 3,
  visible: true, caret: { x: 1, y: 2, width: 0, height: 10 },
  selection: { observed: true, collapsed: true, start: null, end: null, rectangles: [] },
  a11y: { observed: false }, format: { bold: false, italic: null },
};

test("12.3: the v2 state reply names documentSizeChangedCount", () => {
  const { deliver } = worker();
  const message = deliver(3, "editorGetStateV2", {
    type: "editor-state-result", requestId: 3, documentHandle: 1, revision: 2,
    selectionType: "none", selectionText: "", ...STATE });
  assert.equal(message.ok, true, JSON.stringify(message));
  assert.equal(message.result.documentSizeChangedCount, 3);
  assert.equal(message.result.sourceSequence, 41);
});

test("12.3: the editor-state announcement names documentSizeChangedCount", () => {
  const { deliver } = worker();
  const message = deliver(0, "none", {
    type: "editor-state", requestId: 0, documentHandle: 1, revision: 2,
    source: "document-size-changed", ...STATE });
  assert.equal(message.kind, "event");
  assert.equal(message.event, "editor-state");
  assert.equal(message.documentSizeChangedCount, 3);
  assert.equal(message.source, "document-size-changed");
});

test("12.3: the product projection names documentSizeChangedCount, null when absent", () => {
  const { deliver } = worker();
  const completion = (state) => deliver(7, "editorActionV2", {
    type: "editor-action-completed", requestId: 7, documentHandle: 1,
    beforeRevision: 3, revision: 3, action: "move-character-left", option: false,
    changed: false, completion: "documented-callback-visible-cursor", state });
  assert.equal(completion(STATE).result.state.documentSizeChangedCount, 3);
  const { documentSizeChangedCount, ...older } = STATE;
  assert.equal(completion(older).result.state.documentSizeChangedCount, null,
               "a v19 engine emits no counter; the projection must say null, not 0");
  assert.equal(completion({ ...STATE, documentSizeChangedCount: "3" })
                 .result.state.documentSizeChangedCount, null);
});

test("10.8: page-rectangles passes through with named fields only", () => {
  const { deliver } = worker();
  const message = deliver(11, "pageRectangles", {
    type: "page-rectangles", requestId: 11, documentHandle: 1, revision: 5,
    rectangles: "284, 284, 11906, 16838; 284, 17406, 11906, 16838", parts: 2,
    documentWidthTwips: 12474, documentHeightTwips: 34528, engineInternal: "no" });
  assert.equal(message.ok, true, JSON.stringify(message));
  assert.deepEqual(message.result, {
    rectangles: "284, 284, 11906, 16838; 284, 17406, 11906, 16838", parts: 2,
    documentWidthTwips: 12474, documentHeightTwips: 34528, revision: 5 });
});

test("10.8: a pageRectangles request is refused unless the contract declares it", () => {
  const w = worker();
  w.initialised({ profile: "e2-editor-v19", capabilities: ["open-odt", "narrow-editor-v2"],
                  editorContract: { version: 2, redo: "document-sdk-redo" } });
  const { response, calls } = w.request(5, "pageRectangles", { documentHandle: 1 });
  assert.equal(response?.ok, false, JSON.stringify(response));
  assert.equal(response.error.code, "UNSUPPORTED_OPERATION");
  assert.deepEqual(calls, [], "the compiled export must not be reached for");
});

test("10.8: a declared pageRectangles request reaches oxsdk_document_page_rectangles", () => {
  const w = worker();
  w.initialised({ profile: "e2-editor-v20", capabilities: ["open-odt", "narrow-editor-v2"],
                  editorContract: { version: 2, redo: "document-sdk-redo",
                                    pageRectangles: DECLARATION } });
  const { response, calls } = w.request(5, "pageRectangles", { documentHandle: 1 });
  assert.equal(response, null, "accepted: no response until the engine answers");
  assert.deepEqual(calls, [{ name: "oxsdk_document_page_rectangles", args: [5, 1] }]);
});

test("10.8: the declaration must be the exact string", () => {
  const w = worker();
  w.initialised({ profile: "x", capabilities: ["open-odt"],
                  editorContract: { version: 2, pageRectangles: true } });
  const { response, calls } = w.request(5, "pageRectangles", { documentHandle: 1 });
  assert.equal(response?.error?.code, "UNSUPPORTED_OPERATION");
  assert.deepEqual(calls, []);
});

test("10.5: a product completion carries boundaryNoop.waitedMs, named field only", () => {
  const { deliver } = worker();
  const message = deliver(7, "editorActionV2", {
    type: "editor-action-completed", requestId: 7, documentHandle: 1,
    beforeRevision: 3, revision: 3, action: "delete-backward", option: false,
    changed: false, completion: "verified-boundary-noop", state: STATE,
    boundaryNoop: { waitedMs: 2251, engineInternal: "must not cross" } });
  assert.equal(message.ok, true, JSON.stringify(message));
  assert.deepEqual(message.result.boundaryNoop, { waitedMs: 2251 });
  assert.equal(message.result.changed, false);
  assert.equal(message.result.completion, "verified-boundary-noop");
});

test("10.5: a malformed waitedMs is null, and a completion without the record carries none", () => {
  const { deliver } = worker();
  const base = { type: "editor-action-completed", requestId: 7, documentHandle: 1,
                 beforeRevision: 3, revision: 3, action: "delete-backward", option: false,
                 changed: false, completion: "verified-boundary-noop", state: STATE };
  assert.deepEqual(deliver(7, "editorActionV2", { ...base, boundaryNoop: { waitedMs: "2251" } })
                     .result.boundaryNoop, { waitedMs: null });
  assert.equal(deliver(7, "editorActionV2", base).result.boundaryNoop, undefined);
});

const REFUSAL = {
  type: "error", requestId: 9, documentHandle: 1, operation: "editor-action",
  code: "EDITOR_BOUNDARY_UNSUPPORTED", message: "refused",
  mergeKey: { keyPosted: false, stage: "anchor-mismatch", restorePresses: 0 },
};

test("10.6: a refusal's caretBefore reaches the SDK error, named fields only", () => {
  const { deliver } = worker();
  const message = deliver(9, "editorActionV2", { ...REFUSAL, caretBefore: {
    rect: { x: 1134, y: 2268, width: 0, height: 283, extra: 1 }, sourceSequence: 40,
    source: "attribution-P", engineInternal: "no" } });
  assert.equal(message.ok, false);
  assert.deepEqual(message.error.caretBefore, {
    rect: { x: 1134, y: 2268, width: 0, height: 283 }, sourceSequence: 40,
    source: "attribution-P" });
  // mergeKey still rides beside it (M1-4).
  assert.deepEqual(message.error.mergeKey, { keyPosted: false, stage: "anchor-mismatch",
                                             restorePresses: 0 });
});

test("10.6: a null rect stays null, an unknown source is reported as such, and absence is absence", () => {
  const { deliver } = worker();
  const nullRect = deliver(9, "editorActionV2", { ...REFUSAL, caretBefore: {
    rect: null, sourceSequence: 40, source: "cache" } });
  assert.deepEqual(nullRect.error.caretBefore, { rect: null, sourceSequence: 40, source: "cache" });
  const odd = deliver(9, "editorActionV2", { ...REFUSAL, caretBefore: {
    rect: { x: "1", y: 2, width: 3, height: 4 }, sourceSequence: 1.5, source: 7 } });
  assert.deepEqual(odd.error.caretBefore, { rect: null, sourceSequence: null, source: "" });
  assert.equal(deliver(9, "editorActionV2", REFUSAL).error.caretBefore, undefined,
               "a v19 engine sends no caretBefore; the error must carry none");
});
