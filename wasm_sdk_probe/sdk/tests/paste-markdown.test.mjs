// SPEC-M3-link-batch-v21 4.2 / 9.2 / 11.2 M3, M8: `handle.pasteMarkdown(text)`.
//
// Three claims, each with its red case:
//   * the method is absent unless the manifest's contract declares
//     `pasteMarkdown: "document-sdk-paste-markdown"` -- the pageRectangles
//     precedent: the export is COMPILED, so on v20 (the real manifest) the call
//     must be UNSUPPORTED_OPERATION with no request issued (M8's SDK layer);
//   * the OPERATIVE size limit lives here (9.2): exactly 65,536 UTF-8 bytes
//     goes out, 65,537 is INVALID_ARGUMENT with no request, and the error says
//     which layer refused (`details.limitBytes`, M3 "assert which layer");
//   * empty text is refused here (the worker cannot put zero bytes into WASM);
//     everything else about the content is the engine's to judge.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { DocumentHandle, MARKDOWN_PASTE_LIMIT_BYTES } from "../document-sdk.js";

const DECLARATION = "document-sdk-paste-markdown";
const V20 = JSON.parse(readFileSync(fileURLToPath(
  new URL("../../dist/profiles/e2-editor-v20/sdk-manifest.json", import.meta.url)), "utf8"));
const DECLARED = { editorContract: { ...V20.editorContract, pasteMarkdown: DECLARATION } };

function handleWith(manifest, reply = { revision: 4 }) {
  const issued = [];
  const engine = {
    _generation: 1,
    manifest,
    async _request(operation, payload, options) {
      issued.push({ operation, payload: { ...payload }, options });
      if (reply instanceof Error) throw reply;
      return typeof reply === "function" ? reply(payload) : reply;
    },
  };
  const handle = new DocumentHandle(engine, 1, {
    documentHandle: 1, revision: 3, parts: 1, width: 12240, height: 15840, tileMode: 0,
  });
  return { handle, issued };
}

/** `bytes` UTF-8 bytes: three-byte CJK characters and a stated ASCII tail (11.2 M3's corpus shape). */
function corpus(bytes) {
  const cjk = Math.floor(bytes / 3);
  const text = "中".repeat(cjk) + "a".repeat(bytes - 3 * cjk);
  assert.equal(Buffer.byteLength(text, "utf8"), bytes);
  return text;
}

test("the operative limit is 65,536 UTF-8 bytes", () => {
  assert.equal(MARKDOWN_PASTE_LIMIT_BYTES, 65536);
});

test("declared: the text goes out as `pasteMarkdown`, and the revision follows the reply", async () => {
  const { handle, issued } = handleWith(DECLARED, { revision: 4 });
  const result = await handle.pasteMarkdown("# 標題\n\n**粗體中文**");
  assert.deepEqual(result, { revision: 4 });
  assert.equal(handle.revision, 4);
  assert.equal(issued.length, 1);
  assert.equal(issued[0].operation, "pasteMarkdown");
  assert.deepEqual(issued[0].payload, { documentHandle: 1, text: "# 標題\n\n**粗體中文**" });
});

for (const [label, manifest] of [
  ["no manifest", null],
  ["no contract", {}],
  ["the real v20 manifest", V20],
  ["the field with another value", { editorContract: { ...V20.editorContract, pasteMarkdown: "paste-markdown" } }],
  ["the field as a boolean", { editorContract: { ...V20.editorContract, pasteMarkdown: true } }],
  ["the page-rectangles declaration in its place",
   { editorContract: { ...V20.editorContract, pasteMarkdown: "document-sdk-page-rectangles" } }],
]) {
  test(`M8 (SDK) absent (${label}): UNSUPPORTED_OPERATION and no request is issued`, async () => {
    const { handle, issued } = handleWith(manifest);
    await assert.rejects(() => handle.pasteMarkdown("# a"),
                         (error) => error.code === "UNSUPPORTED_OPERATION");
    assert.deepEqual(issued, []);
  });
}

test("M3 (SDK): exactly the limit goes out; one byte over is INVALID_ARGUMENT, nothing sent, the layer named", async () => {
  const at = corpus(MARKDOWN_PASTE_LIMIT_BYTES);
  const over = corpus(MARKDOWN_PASTE_LIMIT_BYTES + 1);
  {
    const { handle, issued } = handleWith(DECLARED);
    await handle.pasteMarkdown(at);
    assert.equal(issued.length, 1, "a text of exactly the limit was refused");
  }
  {
    const { handle, issued } = handleWith(DECLARED);
    await assert.rejects(() => handle.pasteMarkdown(over), (error) => {
      assert.equal(error.code, "INVALID_ARGUMENT");
      assert.equal(error.details.dispatched, false);
      assert.equal(error.details.limitBytes, MARKDOWN_PASTE_LIMIT_BYTES);
      assert.equal(error.details.utf8Bytes, MARKDOWN_PASTE_LIMIT_BYTES + 1);
      return true;
    });
    assert.deepEqual(issued, [], "an over-limit paste reached the worker");
    assert.equal(handle.revision, 3);
  }
});

test("M3 (SDK): the limit counts UTF-8 bytes, not UTF-16 units -- 21,846 CJK characters are over it", async () => {
  // 21,846 characters is far under 65,536 code units and 65,538 UTF-8 bytes.
  const { handle, issued } = handleWith(DECLARED);
  await assert.rejects(() => handle.pasteMarkdown("中".repeat(21846)),
                       (error) => error.code === "INVALID_ARGUMENT" && error.details.utf8Bytes === 65538);
  assert.deepEqual(issued, []);
});

test("empty or non-string text is INVALID_ARGUMENT before any request", async () => {
  for (const text of ["", undefined, null, 7, ["# a"]]) {
    const { handle, issued } = handleWith(DECLARED);
    await assert.rejects(() => handle.pasteMarkdown(text),
                         (error) => error.code === "INVALID_ARGUMENT" && error.details.dispatched === false,
                         String(text));
    assert.deepEqual(issued, []);
  }
});

test("whitespace-only text is the ENGINE's to judge (no block other than the document), so it is sent", async () => {
  const { handle, issued } = handleWith(DECLARED);
  await handle.pasteMarkdown("   \n\t ");
  assert.equal(issued.length, 1);
});

test("an engine refusal passes through untouched, and the revision does not move", async () => {
  const failure = Object.assign(new Error("remote image"),
                                { code: "MARKDOWN_REMOTE_IMAGE", details: { dispatched: false } });
  const { handle } = handleWith(DECLARED, failure);
  await assert.rejects(() => handle.pasteMarkdown("![a](https://example.test/a.png)"),
                       (error) => error === failure);
  assert.equal(handle.revision, 3);
});

test("a closed handle refuses before the gate", async () => {
  const { handle, issued } = handleWith(DECLARED);
  handle._closed = true;
  await assert.rejects(() => handle.pasteMarkdown("# a"), (error) => error.code === "DOCUMENT_CLOSED");
  assert.deepEqual(issued, []);
});
