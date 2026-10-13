// SPEC-M3-link-batch 4.3 / 10.8 (ruling 2 conditions 11 and 13; ruling 4
// condition 30): `handle.pageRectangles()`.
//
// Three claims, each with a red case:
//   * the engine's raw `getPartPageRectangles()` string ("x, y, w, h; ..." in
//     twips, the shape measured natively in
//     findings/evidence/link-batch/page-rectangles/) parses to
//     `[{x, y, width, height}]`, and ANY malformed string is a typed error --
//     never an empty list, which a page would read as "no pages";
//   * rectangles = parts, two core sources for the page count (S-10), so a
//     mismatch is an error and not a silently shorter list;
//   * the method is absent unless the manifest's contract declares
//     `pageRectangles: "document-sdk-page-rectangles"` -- the redo precedent:
//     `oxsdk_document_page_rectangles` is a COMPILED export, and on a profile
//     whose binary predates it the call would reach for a symbol that is not
//     there.  Absent means UNSUPPORTED_OPERATION before any request is issued.

import assert from "node:assert/strict";
import test from "node:test";

import { DocumentHandle, DocumentSdkError, PageRectanglesError,
         parsePageRectangles } from "../document-sdk.js";

const DECLARATION = "document-sdk-page-rectangles";
const GOOD = "284, 284, 11906, 16838; 284, 17406, 11906, 16838; 284, 34528, 11906, 16838";
const GOOD_PARSED = [
  { x: 284, y: 284, width: 11906, height: 16838 },
  { x: 284, y: 17406, width: 11906, height: 16838 },
  { x: 284, y: 34528, width: 11906, height: 16838 },
];
/** The 60-page fixture's shape: 60 A4 pages, 284 twips apart, no trailing separator. */
const NATIVE_60 = Array.from({ length: 60 }, (_, i) =>
  `284, ${284 + i * 17122}, 11906, 16838`).join("; ");

const typed = (error) => error instanceof PageRectanglesError
  && error instanceof DocumentSdkError
  && error.code === "PAGE_RECTANGLES_INVALID";

test("a good string parses to twips rectangles, in order", () => {
  assert.deepEqual(parsePageRectangles(GOOD, 3), GOOD_PARSED);
});

test("the 60-page native shape parses to 60 rectangles", () => {
  const rectangles = parsePageRectangles(NATIVE_60, 60);
  assert.equal(rectangles.length, 60);
  assert.deepEqual(rectangles[59], { x: 284, y: 284 + 59 * 17122, width: 11906, height: 16838 });
});

test("one page is one rectangle", () => {
  assert.deepEqual(parsePageRectangles("284, 284, 11906, 16838", 1),
                   [{ x: 284, y: 284, width: 11906, height: 16838 }]);
});

const MALFORMED = [
  ["empty", ""],
  ["blank", "   "],
  ["not a string: null", null],
  ["not a string: number", 42],
  ["not a string: undefined", undefined],
  ["words", "abc"],
  ["three fields", "1, 2, 3"],
  ["five fields", "1, 2, 3, 4, 5"],
  ["trailing separator", "1, 2, 3, 4;"],
  ["trailing separator and space", "1, 2, 3, 4; "],
  ["leading separator", "; 1, 2, 3, 4"],
  ["empty rectangle between two", "1, 2, 3, 4;; 1, 2, 3, 4"],
  ["a non-numeric field", "1, 2, x, 4"],
  ["a decimal field", "1.5, 2, 3, 4"],
  ["a negative x", "-1, 2, 3, 4"],
  ["a zero width", "1, 2, 0, 4"],
  ["a zero height", "1, 2, 3, 0"],
  ["a negative height", "1, 2, 3, -4"],
  ["trailing garbage on a field", "1, 2, 3, 4 extra"],
  ["a second rectangle that is garbage", "1, 2, 3, 4; x"],
  ["a hexadecimal field", "0x10, 2, 3, 4"],
  ["an exponent field", "1e3, 2, 3, 4"],
];

for (const [label, value] of MALFORMED) {
  test(`malformed (${label}) is a typed error, never an empty list`, () => {
    let result = "did not throw";
    try {
      result = parsePageRectangles(value, 1);
    } catch (error) {
      assert.ok(typed(error), `${label}: ${error?.name} ${error?.code} ${error?.message}`);
      return;
    }
    assert.fail(`${label}: parse returned ${JSON.stringify(result)} instead of throwing`);
  });
}

test("rectangles != parts is a typed error, in both directions", () => {
  for (const parts of [2, 4]) {
    assert.throws(() => parsePageRectangles(GOOD, parts),
                  (error) => typed(error)
                    && error.details.rectangles === 3 && error.details.parts === parts);
  }
});

test("parts that is not a positive integer is a typed error", () => {
  for (const parts of [0, -1, 1.5, "3", null, undefined, NaN]) {
    assert.throws(() => parsePageRectangles(GOOD, parts), typed, String(parts));
  }
});

// ------------------------------------------------------------- the handle

function handleWith(manifest, reply) {
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
    documentHandle: 1, revision: 3, parts: 3, width: 12474, height: 51650, tileMode: 0,
  });
  return { handle, issued };
}

const REPLY = { rectangles: GOOD, parts: 3, documentWidthTwips: 12474,
                documentHeightTwips: 51650, revision: 3 };

test("declared: the handle returns rectangles, parts, the size in twips and the revision", async () => {
  const { handle, issued } = handleWith({ editorContract: { pageRectangles: DECLARATION } }, REPLY);
  const result = await handle.pageRectangles();
  assert.deepEqual(result, { rectangles: GOOD_PARSED, parts: 3, widthTwips: 12474,
                             heightTwips: 51650, revision: 3 });
  assert.equal(issued.length, 1);
  assert.equal(issued[0].operation, "pageRectangles");
  assert.deepEqual(issued[0].payload, { documentHandle: 1 });
});

test("declared: the handle's size and revision follow the reply, as render() does", async () => {
  const { handle } = handleWith({ editorContract: { pageRectangles: DECLARATION } },
                                { ...REPLY, documentWidthTwips: 12475, documentHeightTwips: 68772,
                                  parts: 4, rectangles: `${GOOD}; 284, 51650, 11906, 16838`,
                                  revision: 5 });
  await handle.pageRectangles();
  assert.equal(handle.widthTwips, 12475);
  assert.equal(handle.heightTwips, 68772);
  assert.equal(handle.revision, 5);
});

for (const [label, manifest] of [
  ["no manifest", null],
  ["no contract", {}],
  ["a contract without the field", { editorContract: { version: 2, redo: "document-sdk-redo" } }],
  ["the field with another value", { editorContract: { pageRectangles: "page-rectangles" } }],
  ["the field as a boolean", { editorContract: { pageRectangles: true } }],
]) {
  test(`absent (${label}): UNSUPPORTED_OPERATION and no request is issued`, async () => {
    const { handle, issued } = handleWith(manifest, REPLY);
    await assert.rejects(() => handle.pageRectangles(),
                         (error) => error.code === "UNSUPPORTED_OPERATION");
    assert.deepEqual(issued, []);
  });
}

test("declared: a malformed engine string rejects with the typed error", async () => {
  const { handle } = handleWith({ editorContract: { pageRectangles: DECLARATION } },
                                { ...REPLY, rectangles: "" });
  await assert.rejects(() => handle.pageRectangles(), typed);
});

test("declared: an engine count that disagrees with its own string rejects", async () => {
  const { handle } = handleWith({ editorContract: { pageRectangles: DECLARATION } },
                                { ...REPLY, parts: 2 });
  await assert.rejects(() => handle.pageRectangles(),
                       (error) => typed(error) && error.details.parts === 2);
});

test("declared: an engine error passes through untouched", async () => {
  const failure = Object.assign(new Error("engine said no"), { code: "LOK_ERROR" });
  const { handle } = handleWith({ editorContract: { pageRectangles: DECLARATION } }, failure);
  await assert.rejects(() => handle.pageRectangles(), (error) => error === failure);
});

test("a closed handle refuses before the gate", async () => {
  const { handle, issued } = handleWith({ editorContract: { pageRectangles: DECLARATION } }, REPLY);
  handle._closed = true;
  await assert.rejects(() => handle.pageRectangles(), (error) => error.code === "DOCUMENT_CLOSED");
  assert.deepEqual(issued, []);
});
