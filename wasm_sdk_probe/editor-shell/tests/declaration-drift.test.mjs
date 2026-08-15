// The TypeScript declaration and the runtime must agree about which actions
// exist.
//
// They did not.  E1-C shipped `set-underline` and `set-strikethrough` into the
// v1 contract and rebound the verdict; `editor-client.js` grew both, and
// `editor-client.d.ts` did not.  A TypeScript consumer calling a shipped,
// verified action got a type error, and nothing in the suite noticed -- there
// was no test that could notice, because nothing read the declaration.
//
// This reads it.  The parsing is deliberately crude: a declaration file is not
// a module you can import at runtime, and the alternative -- adding a
// TypeScript compiler to a project that has none -- costs more than the drift
// it would catch.  What matters is that the check FAILS when the two disagree,
// which is verified by mutation: remove an action from either side and this
// goes red.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { EDITOR_V1_ACTIONS } from "../editor-client.js";

const declaration = readFileSync(
  fileURLToPath(new URL("../editor-client.d.ts", import.meta.url)), "utf8");

/** The string-literal members of a `export type Name = | "a" | "b";` union. */
function unionMembers(source, typeName) {
  const start = source.indexOf(`export type ${typeName} =`);
  assert.notEqual(start, -1, `${typeName} is not declared`);
  const end = source.indexOf(";", start);
  assert.notEqual(end, -1, `${typeName} has no terminator`);
  return source.slice(start, end).match(/"([^"]+)"/g)?.map((s) => s.slice(1, -1)) ?? [];
}

/** The string-literal union of one parameter of one method signature. */
function parameterUnion(source, method, parameter) {
  const line = source.split("\n").find((row) => row.includes(`${method}(`));
  assert.ok(line, `${method} is not declared`);
  const match = line.match(new RegExp(`${parameter}:\\s*([^,)]+)`));
  assert.ok(match, `${method} has no ${parameter} parameter`);
  return match[1].match(/"([^"]+)"/g)?.map((s) => s.slice(1, -1)) ?? [];
}

test("EditorV1Action declares exactly the actions the runtime exports", () => {
  assert.deepEqual(
    unionMembers(declaration, "EditorV1Action").slice().sort(),
    EDITOR_V1_ACTIONS.slice().sort(),
  );
});

test("setInlineFormat declares exactly the formats the runtime accepts", () => {
  // The runtime derives its own set from EDITOR_V1_ACTIONS by prefix, so this
  // stays correct if a sixth inline format is ever added.
  const runtimeFormats = EDITOR_V1_ACTIONS
    .filter((action) => action.startsWith("set-"))
    .map((action) => action.slice("set-".length))
    .sort();
  assert.deepEqual(
    parameterUnion(declaration, "setInlineFormat", "format").slice().sort(),
    runtimeFormats,
  );
});
