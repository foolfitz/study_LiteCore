// SPEC-M3-link-batch-v21, the worker's half of the v21 link (task 2026-10-16,
// part S step 1), each with the red case it was shown on:
//
//   * wire ids 22/23 (`move-document-start` / `move-document-end`) in a
//     successor table, and still gated by the manifest intersection: the real
//     v20 manifest does not list them, so v20 refuses them before any id
//     reaches the binary (11.1 D5's other layer);
//   * init FAILS when `oxsdk_editor_set_action_gestures` answers anything but
//     OK (9.7, 11.1 D12) -- it used to ignore the status, so an engine whose
//     `kMaxExternalAction` did not move would have refused 22/23 forever while
//     the manifest granted them;
//   * `pasteMarkdown` is a document-level export gated on the contract's
//     declaration like `pageRectangles` (4.2, 11.2 M8), with insertText's
//     shape, and its engine refusals' `dispatched: false` reaches the SDK error
//     (10.4).
//
// Same harness as sdk-worker-v20.test.mjs -- the real worker script in a vm
// context with a stub `self` -- with a stub module that can allocate, so a
// text payload can be put into "WASM".

import assert from "node:assert/strict";
import test from "node:test";
import vm from "node:vm";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const SOURCE = readFileSync(fileURLToPath(new URL("../sdk-worker.js", import.meta.url)), "utf8");
const V20 = JSON.parse(readFileSync(fileURLToPath(
  new URL("../../dist/profiles/e2-editor-v20/sdk-manifest.json", import.meta.url)), "utf8"));
const DECLARATION = "document-sdk-paste-markdown";

/** The v20 manifest plus ABI 5's two actions and (optionally) the paste: the v21 contract as the builder will write it. */
function v21Manifest({ paste = true, gestures = ["collapsed"] } = {}) {
  const manifest = structuredClone(V20);
  manifest.profile = "e2-editor-v21";
  manifest.editorContract.abiVersion = 5;
  manifest.editorContract.actions["move-document-start"] = { id: 22, gestures, limits: ["no-extend-selection"] };
  manifest.editorContract.actions["move-document-end"] = { id: 23, gestures, limits: ["no-extend-selection"] };
  if (paste) manifest.editorContract.pasteMarkdown = DECLARATION;
  return manifest;
}

/**
 * The worker, with a module whose ccall answers by name (`answers[name]`, a
 * number or a function of the args; 0 otherwise), and that can allocate.
 */
function worker(answers = {}) {
  const posted = [];
  const self = {
    location: { href: "https://example.test/sdk-worker.js" },
    addEventListener() {},
    postMessage(message) { posted.push(message); },
  };
  const context = vm.createContext({ self, console, URL, TextDecoder, TextEncoder,
                                     setTimeout, clearTimeout, queueMicrotask, Uint8Array });
  vm.runInContext(SOURCE, context, { filename: "sdk-worker.js" });
  context.__answers = answers;
  vm.runInContext(`moduleInstance = {
      calls: [], HEAPU8: new Uint8Array(1 << 20), next: 64,
      ccall(name, returnType, types, args) {
        if (name === "oxsdk_buffer_alloc") { const p = this.next; this.next += args[0] + 8; return p; }
        if (name === "oxsdk_buffer_free") return 0;
        this.calls.push({ name, args: [...args] });
        const answer = __answers[name];
        return typeof answer === "function" ? answer(args) : (answer ?? 0);
      } };`, context);
  const plain = (value) => JSON.parse(JSON.stringify(value ?? null));
  const calls = () => plain(vm.runInContext("moduleInstance.calls", context));
  const heap = (pointer, length) =>
    Buffer.from(vm.runInContext("moduleInstance.HEAPU8", context).slice(pointer, pointer + length)).toString("utf8");
  const setManifest = (manifest) =>
    vm.runInContext(`activeManifest = ${JSON.stringify(manifest)};`, context);
  /** Run init against `manifest` with the module above; resolves to the init response (or null).
   *  Without its resource packs: loading them is a fetch, and not the question here. */
  const init = async (manifest) => {
    manifest = { ...manifest, resourcePacks: [] };
    vm.runInContext(`manifestPromise = Promise.resolve(${JSON.stringify(manifest)});
                     modulePromise = Promise.resolve(moduleInstance);`, context);
    const before = posted.length;
    await vm.runInContext(`handleInit({ requestId: 1, operation: "init",
                                        payload: { requestedAbiVersion: 0x00010001 } })`, context);
    return posted.length > before ? plain(posted.at(-1)) : null;
  };
  const request = (requestId, operation, payload) => {
    const before = posted.length;
    vm.runInContext(`handleRequest(${JSON.stringify({ protocolVersion: 1, kind: "request",
                                                        requestId, operation, payload })})`, context);
    return posted.length > before ? plain(posted.at(-1)) : null;
  };
  const deliver = (requestId, operation, event) => {
    vm.runInContext(`pending.set(${requestId}, { operation: ${JSON.stringify(operation)} });`, context);
    vm.runInContext(`handleCEvent(${JSON.stringify(JSON.stringify(event))})`, context);
    return plain(posted.at(-1));
  };
  return { init, request, deliver, calls, heap, setManifest, posted };
}

const ENGINE_ABI = { oxsdk_abi_version: 0x00010001, oxsdk_editor_abi_version: 5 };

// ------------------------------------------------------------------ ids 22/23

const ACTION = (action) => ({ documentHandle: 1, expectedRevision: 4, action,
                              extendSelection: false, enabled: false });

for (const [action, id] of [["move-document-start", 22], ["move-document-end", 23]]) {
  test(`${action} goes out as wire id ${id} on a profile that offers it`, () => {
    const w = worker();
    w.setManifest(v21Manifest());
    assert.equal(w.request(9, "editorActionV2", ACTION(action)), null, "accepted: no response until the engine answers");
    assert.deepEqual(w.calls(), [{ name: "oxsdk_editor_action", args: [9, 1, 4, id, 0, 0] }]);
  });

  test(`${action} is refused on the real v20 manifest, before any id reaches the binary`, () => {
    const w = worker();
    w.setManifest(V20);
    const response = w.request(9, "editorActionV2", ACTION(action));
    assert.equal(response?.ok, false);
    assert.equal(response.error.code, "UNSUPPORTED_OPERATION");
    assert.deepEqual(w.calls(), []);
  });

  test(`${action} withheld (present, gestures []) is refused like an absent one`, () => {
    const w = worker();
    w.setManifest(v21Manifest({ gestures: [] }));
    assert.equal(w.request(9, "editorActionV2", ACTION(action))?.error?.code, "UNSUPPORTED_OPERATION");
    assert.deepEqual(w.calls(), []);
  });

  test(`${action} refuses extendSelection, as the line moves do`, () => {
    const w = worker();
    w.setManifest(v21Manifest());
    const response = w.request(9, "editorActionV2", { ...ACTION(action), extendSelection: true });
    assert.equal(response?.error?.code, "INVALID_ARGUMENT");
    assert.deepEqual(w.calls(), []);
  });
}

// ------------------------------------------------------- init: the mask status

test("init pushes every manifest action's mask and starts the engine when each answers OK (control)", async () => {
  const w = worker(ENGINE_ABI);
  const response = await w.init(v21Manifest());
  assert.equal(response, null, `init failed: ${JSON.stringify(response)}`);
  const masks = w.calls().filter((c) => c.name === "oxsdk_editor_set_action_gestures");
  assert.equal(masks.length, 23, "one mask per declared action, ids 1-23");
  assert.deepEqual(masks.find((c) => c.args[0] === 22).args, [22, 1]);
  assert.deepEqual(masks.find((c) => c.args[0] === 21).args, [21, 0], "select-all stays withheld (mask 0)");
  assert.ok(w.calls().some((c) => c.name === "oxsdk_engine_start"));
});

test("D12: init FAILS when the binary refuses a mask (an engine whose bound did not move), and never starts the engine", async () => {
  // The shape a v21 manifest meets on a binary with kMaxExternalAction still 21:
  // oxsdk_editor_set_action_gestures answers INVALID_ARGUMENT for id 22.
  const w = worker({ ...ENGINE_ABI,
                     oxsdk_editor_set_action_gestures: ([id]) => (id > 21 ? 1 : 0) });
  const response = await w.init(v21Manifest());
  assert.equal(response?.ok, false, "init succeeded over a refused mask");
  assert.equal(response.error.code, "INCOMPATIBLE_ABI");
  assert.equal(response.error.actionId, 22);
  assert.equal(response.error.status, 1);
  assert.match(response.error.message, /move-document-start/);
  assert.equal(w.calls().some((c) => c.name === "oxsdk_engine_start"), false,
               "the engine was started on a manifest the binary cannot narrow");
});

test("D12: any non-OK status fails init, not only INVALID_ARGUMENT", async () => {
  for (const status of [7, 3]) {
    const w = worker({ ...ENGINE_ABI, oxsdk_editor_set_action_gestures: ([id]) => (id === 5 ? status : 0) });
    const response = await w.init(v21Manifest());
    assert.equal(response?.ok, false, `status ${status}`);
    assert.equal(response.error.status, status);
  }
});

// ------------------------------------------------------------- pasteMarkdown

const PASTE = (text) => ({ documentHandle: 1, text });

test("M8 (worker): pasteMarkdown is refused unless the contract declares it -- the real v20 manifest, and wrong spellings", () => {
  for (const manifest of [V20, v21Manifest({ paste: false }),
                          { ...v21Manifest(), editorContract: { ...v21Manifest().editorContract, pasteMarkdown: true } },
                          { ...v21Manifest(), editorContract: { ...v21Manifest().editorContract,
                                                                  pasteMarkdown: "paste-markdown" } }]) {
    const w = worker();
    w.setManifest(manifest);
    const response = w.request(5, "pasteMarkdown", PASTE("# a"));
    assert.equal(response?.ok, false, JSON.stringify(manifest.editorContract.pasteMarkdown));
    assert.equal(response.error.code, "UNSUPPORTED_OPERATION");
    assert.deepEqual(w.calls(), [], "the compiled export must not be reached for");
  }
});

test("M8 (worker): a declared pasteMarkdown reaches oxsdk_document_paste_markdown with the UTF-8 bytes", () => {
  const w = worker();
  w.setManifest(v21Manifest());
  const text = "# 標題\n\n**粗體中文**";
  assert.equal(w.request(5, "pasteMarkdown", PASTE(text)), null, "accepted: no response until the engine answers");
  const [call] = w.calls();
  assert.equal(call.name, "oxsdk_document_paste_markdown");
  const [requestId, handle, pointer, length] = call.args;
  assert.deepEqual([requestId, handle], [5, 1]);
  assert.equal(length, Buffer.byteLength(text, "utf8"), "the length is UTF-8 bytes, not UTF-16 units");
  assert.equal(w.heap(pointer, length), text);
});

test("an empty or non-string text is INVALID_ARGUMENT before the export (zero bytes cannot be allocated)", () => {
  for (const text of ["", undefined, 42]) {
    const w = worker();
    w.setManifest(v21Manifest());
    const response = w.request(5, "pasteMarkdown", PASTE(text));
    assert.equal(response?.error?.code, "INVALID_ARGUMENT", String(text));
    assert.equal(response.error.dispatched, false);
    assert.deepEqual(w.calls(), []);
  }
});

test("the worker has no size limit of its own: 65,537 bytes reach the engine, whose hard limit judges (11.2 M3)", () => {
  const w = worker();
  w.setManifest(v21Manifest());
  const text = "中".repeat(21845) + "ab";   // 65,535 + 2 = 65,537 UTF-8 bytes
  assert.equal(Buffer.byteLength(text, "utf8"), 65537);
  assert.equal(w.request(5, "pasteMarkdown", PASTE(text)), null);
  assert.equal(w.calls()[0].args[3], 65537);
});

test("markdown-pasted completes with the new revision, named fields only", () => {
  const w = worker();
  const message = w.deliver(5, "pasteMarkdown", {
    type: "markdown-pasted", requestId: 5, documentHandle: 1, revision: 8,
    engineInternal: "must not cross", undoPayload: "{...}" });
  assert.equal(message.ok, true, JSON.stringify(message));
  assert.deepEqual(message.result, { revision: 8 });
});

test("10.4: an engine refusal's dispatched:false reaches the SDK error; absent stays absent; non-boolean is dropped", () => {
  const w = worker();
  const refusal = { type: "error", requestId: 5, documentHandle: 1, operation: "paste-markdown",
                    code: "MARKDOWN_REMOTE_IMAGE", message: "remote image" };
  const refused = w.deliver(5, "pasteMarkdown", { ...refusal, dispatched: false });
  assert.equal(refused.ok, false);
  assert.equal(refused.error.code, "MARKDOWN_REMOTE_IMAGE");
  assert.equal(refused.error.dispatched, false);
  assert.equal(refused.error.operation, "paste-markdown");
  const after = w.deliver(5, "pasteMarkdown", { ...refusal, code: "MUTATION_OUTCOME_UNKNOWN", dispatched: true });
  assert.equal(after.error.dispatched, true);
  assert.equal(w.deliver(5, "pasteMarkdown", refusal).error.dispatched, undefined,
               "an engine that does not say has not said");
  assert.equal(w.deliver(5, "pasteMarkdown", { ...refusal, dispatched: "false" }).error.dispatched, undefined);
});
