// SPEC-M3-paragraph-merge M1-4: the worker forwards the boundary completion's
// `keyUndo` and the refusal's `mergeKey` for PRODUCT operations, named fields
// only, and a refusal that does not clearly say "no key went out" reaches the
// page as keyPosted true.
//
// There was no harness for sdk-worker.js's engine-event handling: product
// operations had been getting only `formatBarrier`, and nothing would have
// noticed a second record not being forwarded.  This loads the real worker
// script into a vm context with a stub `self`, registers a pending request the
// way the request path does, and feeds handleCEvent the JSON the engine emits.

import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { DocumentSdkError } from "../document-sdk.js";

const SOURCE = readFileSync(fileURLToPath(new URL("../sdk-worker.js", import.meta.url)), "utf8");

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
  const deliver = (requestId, operation, event) => {
    vm.runInContext(`pending.set(${requestId}, { operation: ${JSON.stringify(operation)} });`,
                    context);
    context.self.__probe_on_event?.(JSON.stringify(event))
      ?? vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify(event))})`, context);
    // Objects made in the vm context have that realm's prototypes; compare
    // what crosses postMessage, which is plain data.
    return JSON.parse(JSON.stringify(posted.at(-1)));
  };
  return { deliver, posted };
}

const COMPLETION = {
  type: "editor-action-completed", requestId: 7, documentHandle: 1,
  beforeRevision: 3, revision: 4, action: "delete-forward", option: false,
  changed: true, completion: "verified-key-undo", state: {},
};
const KEY_UNDO = { comment: "Delete paragraph", actionsBefore: 2, actionsAfter: 3,
                   restorePresses: 2, keyToUndoMs: 41, codePoints: [10],
                   engineInternal: "must not cross" };

test("M1-4: a product completion carries keyUndo, named fields only", () => {
  const { deliver } = worker();
  const message = deliver(7, "editorActionV2", { ...COMPLETION, keyUndo: KEY_UNDO });
  assert.equal(message.ok, true, JSON.stringify(message));
  const keyUndo = message.result.keyUndo;
  assert.deepEqual(keyUndo, { comment: "Delete paragraph", actionsBefore: 2,
                              actionsAfter: 3, restorePresses: 2, keyToUndoMs: 41,
                              codePoints: [10] });
});

test("M1-4: malformed keyUndo fields are dropped to null, not passed through", () => {
  const { deliver } = worker();
  const message = deliver(7, "editorActionV2", {
    ...COMPLETION,
    keyUndo: { comment: 5, actionsAfter: "3", restorePresses: 1.5, codePoints: [10, "x"] },
  });
  assert.deepEqual(message.result.keyUndo, { comment: "", actionsBefore: null,
                                             actionsAfter: null, restorePresses: null,
                                             keyToUndoMs: null, codePoints: [10] });
});

const REFUSAL = {
  type: "error", requestId: 9, documentHandle: 1, operation: "editor-action",
  code: "EDITOR_BOUNDARY_UNSUPPORTED", message: "refused",
};

for (const [label, keyPosted, expected] of [
  ["true", true, true], ["false", false, false],
  ["missing", undefined, true], ["not a boolean", "no", true],
]) {
  test(`M1-4: a refusal's mergeKey.keyPosted ${label} reaches the SDK error as ${expected}`, () => {
    const { deliver } = worker();
    const mergeKey = { stage: "key-deadline", restorePresses: 1, internal: 1 };
    if (keyPosted !== undefined) mergeKey.keyPosted = keyPosted;
    const message = deliver(9, "editorActionV2", { ...REFUSAL, mergeKey });
    assert.equal(message.ok, false, JSON.stringify(message));
    assert.deepEqual(message.error.mergeKey,
                     { keyPosted: expected, stage: "key-deadline", restorePresses: 1 });
    // And through the SDK's own error constructor, which is where the page
    // reads it: the fields land in `details`, not on the error itself.
    const error = new DocumentSdkError(message.error.code, message.error.message,
                                       { operation: "editorActionV2", ...message.error });
    assert.equal(error.details.mergeKey.keyPosted, expected);
  });
}

test("M1-4: a refusal without mergeKey carries none (v8 and v14 engines)", () => {
  const { deliver } = worker();
  const message = deliver(9, "editorActionV2", REFUSAL);
  assert.equal(message.error.mergeKey, undefined);
});
