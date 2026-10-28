// SPEC-M3-link-batch-v24 6.1 T3 and U1: the SDK's typed-insert route.
//
//   * T3 (form two): every `source: "<literal>"` in input/*.js is a key of
//     INSERT_ROUTE_BY_SOURCE and every key is such a literal -- equality, so an
//     added commit source and a stale key are both red.  Non-vacuity: at least
//     two files and four literals, or red (a renamed directory must not read
//     as "nothing to route").  V24_T3_INPUT_DIR points the extraction at a
//     scratch copy for red case (iv).
//   * U1 (per row): on a declaring manifest every insert carries `route`, an
//     unknown source is refused before any request; on any other manifest the
//     request is byte-for-byte today's and nothing new is thrown (ruling 2,
//     follow-up A1).

import assert from "node:assert/strict";
import test from "node:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  DocumentHandle, INSERT_ROUTE_BY_SOURCE, TYPED_INSERT_DECLARATION,
} from "../sdk/document-sdk.js";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const INPUT_DIR = process.env.V24_T3_INPUT_DIR || join(ROOT, "input");
const SOURCE_LITERAL = /\bsource:\s*"([^"]*)"/g;

function adapterSources(directory) {
  const files = readdirSync(directory).filter((name) => name.endsWith(".js"));
  const literals = new Set();
  for (const name of files)
    for (const match of readFileSync(join(directory, name), "utf8").matchAll(SOURCE_LITERAL))
      literals.add(match[1]);
  return { files, literals };
}

test("T3: the adapters' source literals are exactly the routed sources", () => {
  const { files, literals } = adapterSources(INPUT_DIR);
  assert(files.length >= 2, `read ${files.length} adapter file(s) in ${INPUT_DIR}`);
  assert(literals.size >= 4, `found ${literals.size} source literal(s)`);
  assert.deepEqual([...literals].sort(), [...INSERT_ROUTE_BY_SOURCE.keys()].sort());
});

function documentOn(manifest) {
  const requests = [];
  const engine = {
    _generation: 1,
    manifest,
    async _request(operation, payload) {
      requests.push({ operation, payload });
      return { revision: requests.length, method: payload.route ?? "paste" };
    },
  };
  return { document: new DocumentHandle(engine, 1, { documentHandle: 7, revision: 0 }), requests };
}

const DECLARING = { editorContract: { abiVersion: 6, typedInsert: TYPED_INSERT_DECLARATION } };
const LEAFLESS = { editorContract: { abiVersion: 6 } };

const ROWS = [
  // [text, metadata, route on a declaring manifest]
  ["x", { source: "beforeinput", inputType: "insertText" }, "uno-insert-text"],
  ["中", { source: "composition", compositionId: 3 }, "uno-insert-text"],
  ["\u{1F600}", { source: "beforeinput", inputType: "insertText" }, "uno-insert-text"],
  ["x", { source: "clipboard-event", htmlPresent: false }, "paste"],
  ["x", { source: "clipboard-api" }, "paste"],
  ["x", undefined, "paste"],
  ["x", { requestNumber: 4 }, "paste"],
  ["x", { source: "" }, "paste"],
  ["x", { source: null }, "paste"],
  ["\n", { source: "beforeinput", inputType: "insertParagraph" }, "paste"],
  ["a\rb", { source: "beforeinput", inputType: "insertText" }, "paste"],
  ["a\u0000b", { source: "composition" }, "paste"],
  ["a\nb", { source: "composition" }, "paste"],
];

test("U1: a declaring manifest routes every row and names the route", async () => {
  for (const [text, metadata, route] of ROWS) {
    const { document, requests } = documentOn(DECLARING);
    await document.insertText(text, metadata === undefined ? {} : { metadata });
    assert.equal(requests.length, 1);
    assert.deepEqual(requests[0], { operation: "insertText", payload: { documentHandle: 7, text, route } },
      JSON.stringify([text, metadata]));
  }
});

test("U1: a declaring manifest refuses an unknown source before any request", async () => {
  for (const source of ["fake", "BEFOREINPUT", "toString", 1, true, {}]) {
    const { document, requests } = documentOn(DECLARING);
    await assert.rejects(document.insertText("x", { metadata: { source } }), (error) => {
      assert.equal(error.code, "INSERT_ORIGIN_UNKNOWN");
      assert.equal(error.details.dispatched, false);
      return true;
    }, String(source));
    assert.equal(requests.length, 0);
  }
});

test("U1: any other manifest sends today's request and throws nothing new", async () => {
  for (const manifest of [LEAFLESS, null, { editorContract: { typedInsert: "document-sdk-other" } }]) {
    for (const [text, metadata] of [...ROWS, ["x", { source: "fake" }]]) {
      const { document, requests } = documentOn(manifest);
      await document.insertText(text, metadata === undefined ? {} : { metadata });
      assert.deepEqual(requests, [{ operation: "insertText", payload: { documentHandle: 7, text } }]);
      assert.deepEqual(Object.keys(requests[0].payload), ["documentHandle", "text"]);
    }
  }
});
