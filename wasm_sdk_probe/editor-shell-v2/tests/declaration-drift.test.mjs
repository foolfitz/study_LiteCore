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
import { EDITOR_V2_ACTIONS, EDITOR_V2_INHERITED_ACTIONS,
         EDITOR_V3_ACTIONS, EDITOR_V3_APPENDED_ACTIONS,
         EDITOR_V4_ACTIONS, EDITOR_V4_APPENDED_ACTIONS }
  from "../narrow-editor-v2-client.js";

const declaration = readFileSync(
  fileURLToPath(new URL("../paragraph-editor-client.d.ts", import.meta.url)),
  "utf8");

const productDeclaration = readFileSync(
  fileURLToPath(new URL("../narrow-editor-v2-client.d.ts", import.meta.url)),
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

test("EditorV2InheritedAction declares exactly the runtime's ten", () => {
  assert.deepEqual(
    unionMembers(productDeclaration, "EditorV2InheritedAction").slice().sort(),
    EDITOR_V2_INHERITED_ACTIONS.slice().sort());
});

test("EditorV2Action is the union of the two lists, and it is fifteen", () => {
  // Declared as a union of two named types rather than fifteen literals, so
  // this checks the composition rather than re-listing them: the failure being
  // guarded against is one list growing without the other.
  const composed = productDeclaration.slice(
    productDeclaration.indexOf("export type EditorV2Action ="));
  assert.match(composed.slice(0, composed.indexOf(";")),
               /EditorV2InheritedAction\s*\|\s*EditorV2ParagraphAction/);
  assert.equal(EDITOR_V2_ACTIONS.length, 15);
  assert.deepEqual(EDITOR_V2_ACTIONS.slice().sort(),
                   [...EDITOR_V2_INHERITED_ACTIONS,
                    ...EDITOR_V2_PARAGRAPH_ACTIONS].sort());
});

test("the inherited result keeps a boolean `changed`", () => {
  // The one thing that must NOT be copied from the paragraph declaration.  If
  // this ever reads `changed: null`, delete has been given route C's shape and
  // finding 022's silent no-op has a way back in.
  const start = productDeclaration.indexOf("interface EditorV2InheritedResult");
  const body = productDeclaration.slice(start,
                                        productDeclaration.indexOf("}", start));
  assert.match(body, /changed:\s*boolean/);
  assert.doesNotMatch(body, /changed:\s*null/);
});

test("the declared completion is route C's, not v1's", () => {
  assert.ok(declaration.includes('"verified-format-readback"'));
  assert.ok(!declaration.includes('"uno-command-result"'));
});

// ---- ABI 4's append -------------------------------------------------------
//
// The same guard as above, extended the same day the list was, rather than
// after the drift.  The v2 tests below did NOT catch v3 arriving unguarded --
// they compare the v2 lists, and a new list is simply outside them -- which is
// the one thing a drift test cannot do for you.

test("EditorV3AppendedAction declares exactly the runtime's five", () => {
  assert.deepEqual(unionMembers(productDeclaration, "EditorV3AppendedAction")
                     .slice().sort(),
                   EDITOR_V3_APPENDED_ACTIONS.slice().sort());
});

test("EditorV3Action is v2's fifteen plus the append, and it is twenty", () => {
  assert.equal(EDITOR_V3_ACTIONS.length, 20);
  assert.deepEqual(EDITOR_V3_ACTIONS.slice(0, EDITOR_V2_ACTIONS.length),
                   EDITOR_V2_ACTIONS.slice(),
                   "the fifteen inherited actions must come through in order");
});

// ---- ABI 5's append (SPEC-M3-link-batch-v21 4.1) --------------------------
//
// Extended the day the list was, as the ABI 4 block above was.

test("EditorV4AppendedAction declares exactly the runtime's two", () => {
  assert.deepEqual(unionMembers(productDeclaration, "EditorV4AppendedAction")
                     .slice().sort(),
                   EDITOR_V4_APPENDED_ACTIONS.slice().sort());
  assert.deepEqual(EDITOR_V4_APPENDED_ACTIONS.slice().sort(),
                   ["move-document-end", "move-document-start"]);
});

test("EditorV4Action is v3's twenty plus the append, and it is twenty-two", () => {
  const composed = productDeclaration.slice(
    productDeclaration.indexOf("export type EditorV4Action ="));
  assert.match(composed.slice(0, composed.indexOf(";")),
               /EditorV3Action\s*\|\s*EditorV4AppendedAction/);
  assert.equal(EDITOR_V4_ACTIONS.length, 22);
  assert.deepEqual(EDITOR_V4_ACTIONS.slice(0, EDITOR_V3_ACTIONS.length),
                   EDITOR_V3_ACTIONS.slice(),
                   "the twenty inherited actions must come through in order");
});

test("the client pair declares the closed postcondition classes and the paste offer", () => {
  assert.deepEqual(unionMembers(productDeclaration, "EditorPostconditionClass").slice().sort(),
                   ["delete", "move", "mutation", "paragraph"]);
  assert.match(productDeclaration, /export function postconditionClassOf\(/);
  assert.match(productDeclaration, /offersPasteMarkdown\(\): boolean;/);
});

// SPEC-M3-select-all-v26 4.3.  Until v26 this test said "the withheld action is
// named nowhere in the client pair": the v4 contract shipped id 21 with no
// gestures, and a client naming it would have offered a control that could not
// work.  e2-editor-v26 GRANTS it on a measurement, so the rule becomes: named
// exactly once, as a grant -- EDITOR_SELECT_ALL_ACTIONS and its declared type --
// and still in neither ABI's append list, which keep meaning what each ABI
// appended.  Offering stays the manifest's (`offers`, offers.test.mjs).
test("the granted select-all is named only as the grant, and in no ABI append list", async () => {
  const name = ["select", "all"].join("-");
  const client = await import("../narrow-editor-v2-client.js");
  assert.deepEqual(client.EDITOR_SELECT_ALL_ACTIONS, [name]);
  assert.deepEqual(client.EDITOR_ACCEPTED_ACTIONS, [...EDITOR_V4_ACTIONS, name]);
  assert.equal(EDITOR_V3_ACTIONS.includes(name), false);
  assert.equal(EDITOR_V4_ACTIONS.includes(name), false);
  assert.deepEqual(unionMembers(productDeclaration, "EditorSelectAllAction"), [name]);
  assert.match(productDeclaration, /export type EditorAcceptedAction = EditorV4Action \| EditorSelectAllAction;/);
  assert.match(productDeclaration, /export const EDITOR_SELECT_ALL_ACTIONS: readonly EditorSelectAllAction\[\];/);
  assert.match(productDeclaration, /export const EDITOR_ACCEPTED_ACTIONS: readonly EditorAcceptedAction\[\];/);
});

test("the worker's wire ids are the header's, and the header pins them", () => {
  // THE SEAM NOTHING CHECKED.  editor_abi_header_test.cpp pins the C side and
  // the tests above pin the JS side to its own .d.ts, but no test compared the
  // two -- so the numbers a client puts on the wire were pinned to nothing.
  // A renumbering in either file alone is silent and total: the action still
  // dispatches, it just is not the one that was asked for.
  const worker = readFileSync(
    fileURLToPath(new URL("../../sdk/sdk-worker.js", import.meta.url)), "utf8");
  const header = readFileSync(
    fileURLToPath(new URL("../../src/editor_api.h", import.meta.url)), "utf8");

  const headerIds = new Map();
  for (const [, name, id] of header.matchAll(
         /OXSDK_EDITOR_V\d_([A-Z0-9_]+)\s*=\s*(\d+)/g))
    headerIds.set(name.toLowerCase().replaceAll("_", "-"), Number(id));
  // Twenty-three since ABI 5 (SPEC-M3-link-batch-v21 4.1): the header's
  // ABI-5 enum carries 22 and 23 under OXSDK_E2_V21_LINK_BATCH.
  assert.equal(headerIds.size, 23, "expected twenty-three pinned header ids");

  // Scoped to the PRODUCT tables, and the scoping is the point rather than
  // tidiness.  The same file also holds EDITOR_DISCOVERY_ACTION_IDS, which
  // carries the ENGINE'S INTERNAL numbering: delete-backward is 7 there and 3
  // here, move-line-up is 3 there and 16 here.  The two schemes disagree by
  // design -- editor_api.cpp's internalAction() is the only thing that converts
  // between them -- so a test that read both would either fail forever or, if
  // someone "fixed" the discovery map to agree, pass while the conversion table
  // it was supposed to protect had been flattened away.
  const productStart = worker.indexOf("const EDITOR_V1_ACTION_IDS");
  const productEnd = worker.indexOf("const EDITOR_DISCOVERY_ACTION_IDS");
  assert.ok(productStart !== -1 && productEnd > productStart,
            "the product id tables are not where this test expects them");
  const productTables = worker.slice(productStart, productEnd);

  const workerIds = new Map();
  for (const [, name, id] of productTables.matchAll(/"([a-z-]+)":\s*(\d+),/g))
    if (headerIds.has(name)) workerIds.set(name, Number(id));
  // TWENTY-ONE in the worker against TWENTY in the client, and the difference
  // is exactly one action -- the withheld one.  The worker has to know its id
  // or the manifest could not push a zero mask for it, and pushing that mask is
  // the only thing that withholds it: the engine initialises every entry to
  // all-permitted, so an id the worker does not know is an action shipped wide
  // open.  The client, in turn, must NOT name it.  Neither number is the other
  // one's mistake.
  assert.equal(workerIds.size, 23,
               "the worker must carry every wire id, withheld ones included");
  assert.equal(EDITOR_V4_ACTIONS.length, workerIds.size - 1,
               "the client offers every action but the withheld one");

  for (const [name, id] of workerIds)
    assert.equal(id, headerIds.get(name),
                 `${name} is ${id} in the worker and ${headerIds.get(name)} `
                 + `in editor_api.h`);
  // Every action the client can name must be one the worker has an id for.
  for (const action of EDITOR_V4_ACTIONS)
    assert.equal(workerIds.has(action), true,
                 `${action} is offered by the client with no wire id`);
});

// ---- the SDK's own declaration (SPEC-M3-link-batch-v21 4.2) ----------------
//
// The handle grew `pasteMarkdown` and the module an operative limit; the same
// guard as above, for the SDK pair: every public method the runtime classes
// carry is declared, and the limit the declaration names is the runtime's.

test("document-sdk.d.ts declares every public method of DocumentHandle and DocumentEngine", async () => {
  const sdk = await import("../../sdk/document-sdk.js");
  const sdkDeclaration = readFileSync(
    fileURLToPath(new URL("../../sdk/document-sdk.d.ts", import.meta.url)), "utf8");
  for (const Class of [sdk.DocumentHandle, sdk.DocumentEngine]) {
    const start = sdkDeclaration.indexOf(`export class ${Class.name} {`);
    assert.notEqual(start, -1, `${Class.name} is not declared`);
    const body = sdkDeclaration.slice(start, sdkDeclaration.indexOf("\n}", start));
    const methods = Object.getOwnPropertyNames(Class.prototype)
      .filter((name) => name !== "constructor" && !name.startsWith("_"));
    assert.ok(methods.length >= 4, `${Class.name}: the census is empty`);
    for (const name of methods)
      assert.match(body, new RegExp(`\\n\\s+${name}\\(`), `${Class.name}.${name} is not declared`);
  }
});

test("document-sdk.d.ts names the runtime's Markdown limit and the paste's signature", async () => {
  const { MARKDOWN_PASTE_LIMIT_BYTES } = await import("../../sdk/document-sdk.js");
  const sdkDeclaration = readFileSync(
    fileURLToPath(new URL("../../sdk/document-sdk.d.ts", import.meta.url)), "utf8");
  const declared = sdkDeclaration.match(/export const MARKDOWN_PASTE_LIMIT_BYTES: (\d+);/);
  assert.ok(declared, "MARKDOWN_PASTE_LIMIT_BYTES is not declared");
  assert.equal(Number(declared[1]), MARKDOWN_PASTE_LIMIT_BYTES);
  assert.match(sdkDeclaration,
               /pasteMarkdown\(text: string, options\?: AbortableOptions\): Promise<MarkdownPasteResult>;/);
});
