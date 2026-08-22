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

import { EditorStateMachine } from "../../editor-shell/state-machine.js";
import { ParagraphEditorClient } from "../paragraph-editor-client.js";
import { EDITOR_V2_ACTIONS, NarrowEditorV2Client } from "../narrow-editor-v2-client.js";
import { NarrowEditorV2Session } from "../narrow-editor-v2-session.js";

const read = (relative) =>
  readFileSync(fileURLToPath(new URL(relative, import.meta.url)), "utf8");

/** Method names called on `receiver` in this source, in call position. */
function calledMethods(source, receiver) {
  const pattern = new RegExp(`\\b${receiver}\\s*\\.\\s*([A-Za-z_$][\\w$]*)\\s*\\(`, "g");
  return new Set([...source.matchAll(pattern)].map((match) => match[1]));
}

/** Fields a page reads off a snapshot, ignoring line comments.
 *
 * The comments matter: this test's first version flagged `requiresPageReload`
 * in a comment that was explaining the very bug being fixed.
 */
function snapshotFields(source) {
  const withoutComments = source.replace(/^\s*\/\/.*$/gm, "");
  return new Set([...withoutComments.matchAll(
    /\bsnapshot\s*(?:\?\.|\.)\s*([A-Za-z_$][\w$]*)/g)].map((m) => m[1]));
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

// Finding 054.  `web/e2-editor-app.js` disabled its recovery button on
// `snapshot.requiresPageReload`, and no snapshot has ever had that field: the
// flag is written into the ERROR's details at the generation ceiling, which is
// where the v1 component reads it from.  So the comparison was always false,
// the button never disabled, and at the ceiling the page pointed the user at a
// control guaranteed to refuse them.
//
// Same cheap general form as the method check above: a field name in the source
// is not evidence that anything publishes it.
test("every snapshot field a page reads is a field the state machine has",
     () => {
       const published = new Set(
         Object.keys(new EditorStateMachine().snapshot));
       for (const page of ["../../web/e2-editor-app.js",
                           "../../web/e2-c-d2-app.js",
                           "../../web/e2-c-d5-app.js",
                           "../../web/demo-editor-app.js"]) {
         const unknown = [...snapshotFields(read(page))]
           .filter((field) => !published.has(field));
         assert.deepEqual(unknown, [],
                          `${page} reads snapshot fields nobody publishes: `
                          + `${unknown.join(", ")}`);
       }
     });

// FINDING 067: the Enter key, bound in the page's keydown handler.
//
// The binding lives in the page rather than at the input adapter's commit
// boundary because a <textarea> reports BOTH Enter and Shift+Enter as
// `insertLineBreak` (measured, findings/evidence/067/), so the two are
// indistinguishable there -- and the adapter is in E1-C's frozen bundle
// anyway.  These cases pin the three things that make the binding correct;
// each of them fails if the corresponding clause is deleted.
test("Enter is bound to the paragraph break and Shift+Enter to the line break",
  () => {
    const page = read("../../web/e2-editor-app.js");
    const start = page.indexOf('el.sink.addEventListener("keydown"');
    assert.ok(start > 0, "the page has a keydown handler on the sink");
    const handler = page.slice(start, page.indexOf("\n});", start));

    assert.match(handler, /event\.key === "Enter"/,
      "the handler branches on Enter");
    assert.match(handler, /event\.shiftKey \? "insert-line-break"/,
      "Shift+Enter asks for the LINE break");
    assert.match(handler, /"insert-paragraph-break"/,
      "a plain Enter asks for the PARAGRAPH break");

    // Not optional: Enter during an IME composition COMMITS the composition,
    // and preventing it there breaks Chinese input.  Finding 050's
    // neighbourhood, in a file that is frozen and cannot be repaired.
    assert.match(handler, /!event\.isComposing/,
      "the Enter branch is guarded on isComposing");

    // Both must be real contract actions, or `editorAction` cannot label them.
    for (const action of ["insert-paragraph-break", "insert-line-break"]) {
      assert.ok(EDITOR_V2_ACTIONS.includes(action),
        `${action} is one of the contract's actions`);
    }
  });
