// The v2 declaration and the v2 runtime must agree about which actions exist.
//
// The v1 pair drifted for two shipped artifacts -- editor-client.js grew
// underline and strikethrough, editor-client.d.ts did not, and nothing
// compared them.  This is the same guard for v2, added at the same time as the
// declaration rather than after the drift.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { EDITOR_V2_PARAGRAPH_ACTIONS } from "../paragraph-editor-client.js";

const declaration = readFileSync(
  fileURLToPath(new URL("../paragraph-editor-client.d.ts", import.meta.url)),
  "utf8");

function unionMembers(source, typeName) {
  const start = source.indexOf(`export type ${typeName} =`);
  assert.notEqual(start, -1, `${typeName} is not declared`);
  const end = source.indexOf(";", start);
  return source.slice(start, end).match(/"([^"]+)"/g)?.map((s) => s.slice(1, -1)) ?? [];
}

test("EditorV2ParagraphAction declares exactly the runtime's actions", () => {
  assert.deepEqual(
    unionMembers(declaration, "EditorV2ParagraphAction").slice().sort(),
    EDITOR_V2_PARAGRAPH_ACTIONS.slice().sort());
});

test("the gesture union matches the engine's routing classes", () => {
  // Not a free-form list: these are the three routes probe_engine.cpp decides
  // between, so a fourth here would be a type promising a route that does not
  // exist.
  assert.deepEqual(unionMembers(declaration, "EditorV2Gesture").slice().sort(),
                   ["collapsed", "range-cross", "range-single"]);
});

test("the declared completion is route C's, not v1's", () => {
  assert.ok(declaration.includes('"verified-format-readback"'));
  assert.ok(!declaration.includes('"uno-command-result"'));
});
