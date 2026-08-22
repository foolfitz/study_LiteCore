// `offers()` is "shipped dark" as the UI can see it.
//
// The v4 contract carries actions the engine implements and the manifest
// withholds, and withholding is spelled `gestures: []` -- PRESENT with an empty
// list, because the engine initialises every gesture entry to all-permitted and
// an omitted action would ship wide open. A client that read presence alone
// would draw a control for something the engine refuses every time.
//
// `gesturesFor()` cannot answer this question and these tests pin why: it
// returns null for a v1-shaped manifest AND for an action the profile does not
// carry, and those two must not be treated alike in either direction.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";

const clientWith = (actions) => new NarrowEditorV2Client({
  _assertUsable() {},
  _engine: { manifest: actions === undefined ? {}
                        : { editorContract: { actions } } },
});

test("an action with gestures is offered", () => {
  const client = clientWith({ "move-line-up": { id: 16, gestures: ["collapsed"] } });
  assert.equal(client.offers("move-line-up"), true);
});

test("an action PRESENT with an empty gesture list is NOT offered", () => {
  // This is the whole ship-dark mechanism seen from the UI. Getting it wrong
  // in this direction draws a control the engine refuses on every press.
  const client = clientWith({ "some-dark-action": { id: 21, gestures: [] } });
  assert.equal(client.offers("some-dark-action"), false);
});

test("an action the profile does not carry is NOT offered", () => {
  // A v3 profile asked about a v4 action. Before the ABI 4 link this is the
  // live case for ArrowUp on the product page.
  const client = clientWith({ "move-character-left": { id: 1, gestures: ["collapsed"] } });
  assert.equal(client.offers("move-line-up"), false);
});

test("gesturesFor CANNOT distinguish those two, which is why offers exists", () => {
  const dark = clientWith({ "a": { id: 1, gestures: [] } });
  const absent = clientWith({ "b": { id: 1, gestures: ["collapsed"] } });
  // Empty list and absent action: gesturesFor gives [] and null, and a caller
  // doing `(gesturesFor(x) || []).length > 0` collapses them -- which is fine
  // here but not for the v1 case below, where the same expression says
  // "withheld" for a profile that offers everything.
  assert.deepEqual(dark.gesturesFor("a"), []);
  assert.equal(absent.gesturesFor("a"), null);
});

test("a v1-shaped manifest carries a name list and offers what it lists", () => {
  const client = clientWith(["move-character-left", "delete-backward"]);
  assert.equal(client.offers("move-character-left"), true);
  assert.equal(client.offers("move-line-up"), false);
  // And gesturesFor answers null for BOTH -- the ambiguity offers() removes.
  assert.equal(client.gesturesFor("move-character-left"), null);
  assert.equal(client.gesturesFor("move-line-up"), null);
});

test("no contract at all offers everything", () => {
  // A profile with no editorContract withholds nothing; refusing here would
  // disable every control on such a profile.
  const client = clientWith(undefined);
  assert.equal(client.offers("move-character-left"), true);
});

test("offersRedo reads the contract, not the action map", () => {
  // redo has no wire id and no gesture; asking the action map about it would
  // answer "absent" on every profile including the ones that carry it.
  const v4 = clientWith({});
  v4.document._engine.manifest.editorContract.redo = "document-sdk-redo";
  assert.equal(v4.offersRedo(), true);
  assert.equal(v4.offers("redo"), false);

  const v3 = clientWith({ "move-character-left": { id: 1, gestures: ["collapsed"] } });
  assert.equal(v3.offersRedo(), false);
});

test("a profile with no contract at all does not claim redo", () => {
  // `offers()` answers true here -- nothing is withheld -- but redo is a
  // COMPILED EXPORT, so absence of a declaration must not be read as consent.
  const client = clientWith(undefined);
  assert.equal(client.offers("move-character-left"), true);
  assert.equal(client.offersRedo(), false);
});

test("the product page gates redo and cut on the profile too", () => {
  const source = readFileSync(
    new URL("../../web/e2-editor-app.js", import.meta.url), "utf8");
  // The button is hidden, not disabled: a disabled control promises a later
  // moment that never arrives on a profile without redo.
  assert.match(source, /button\.hidden = !session\?\.offersRedo\?\.\(\)/);
  assert.match(source, /if \(!session\.offersRedo\?\.\(\)\) return;/);
  // Cut prefers delete-selection and falls back to today's behaviour.
  assert.match(source, /session\.offers\("delete-selection"\)/);
});

test("the product page gates its arrow keys on offers, not gesturesFor", () => {
  // The binding and the gate are in one file and could drift apart silently:
  // listing a key without gating it is exactly the "looks like it worked"
  // failure this project unbound Ctrl+A to avoid.
  const page = new URL("../../web/e2-editor-app.js", import.meta.url);
  const source = readFileSync(page, "utf8");
  assert.match(source, /ArrowUp: "move-line-up"/);
  assert.match(source, /!session\.offers\(action\)/);
});
