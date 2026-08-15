// Every method a product page calls on its client must exist on that client.
//
// `node --check` parses the page and says nothing, because `client.foo()` is
// valid syntax whatever `client` turns out to be.  So a page can be migrated
// from one client to another, load cleanly, show its toolbar -- and throw
// TypeError the first time the user touches it.  That is not hypothetical:
// demo-structure-app.js was migrated to ParagraphEditorClient while still
// calling `client.placeCaretByClick(...)`, a method that only ever existed on
// the diagnostic client, so clicking the page to place the caret could not
// work.  The page had been checked for BOOT, and booting was the thing that had
// broken the time before.
//
// This is the cheap general form of that check: pull the method names out of
// the page source and ask the class whether it has them.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { ParagraphEditorClient } from "../paragraph-editor-client.js";
import { NarrowEditorV2Client } from "../narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const read = (relative) =>
  readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8");

/** Method names called on `receiver` in this source, in call position. */
function calledMethods(source, receiver) {
  const pattern = new RegExp(`\\b${receiver}\\s*\\.\\s*([A-Za-z_$][\\w$]*)\\s*\\(`, "g");
  return new Set([...source.matchAll(pattern)].map((match) => match[1]));
}

/** Does the class, or anything it inherits from, define this method? */
function has(Class, name) {
  for (let proto = Class.prototype; proto; proto = Object.getPrototypeOf(proto)) {
    if (Object.prototype.hasOwnProperty.call(proto, name)) return true;
  }
  return false;
}

const PAGES = [
  ["../../web/demo-structure-app.js", "client", ParagraphEditorClient],
  ["../../web/e2-editor-app.js", "session", NarrowEditorV2Session],
  ["../../web/e2-editor-app.js", "client", NarrowEditorV2Client],
];

for (const [page, receiver, Class] of PAGES) {
  test(`${page}: every ${receiver}.* call exists on ${Class.name}`, () => {
    let source;
    try {
      source = read(page);
    } catch (error) {
      if (error.code === "ENOENT") return;   // page not built yet
      throw error;
    }
    const missing = [...calledMethods(source, receiver)]
      .filter((name) => !name.startsWith("_") && !has(Class, name))
      .sort();
    assert.deepEqual(missing, [],
                     `called on ${receiver} but not defined by ${Class.name}`);
  });
}

test("the extractor finds calls and the membership test can say no", () => {
  // Both halves need a control.  A regex that matched nothing would make every
  // page above pass, and a membership test that always said yes would too.
  const source = "client.setList('none'); client.notAMethod(1); client.getState()";
  assert.deepEqual([...calledMethods(source, "client")].sort(),
                   ["getState", "notAMethod", "setList"]);
  assert.ok(has(ParagraphEditorClient, "setList"));
  assert.ok(!has(ParagraphEditorClient, "notAMethod"));
  // And inheritance must count: the v2 session gets placeCaret from the base.
  assert.ok(has(NarrowEditorV2Session, "placeCaret"));
  assert.ok(has(NarrowEditorV2Session, "setList"));
});
