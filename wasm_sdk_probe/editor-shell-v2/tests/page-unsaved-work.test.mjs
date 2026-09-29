// The product page's own "are there edits nobody saved?" (finding 107).
//
// SPEC-M3-page-honesty U3: the page's judgement reads the session's
// `hasUnsavedEdits()` (dirty or pending) and its own count of saves not yet
// settled -- never a revision, because revisions restart at zero with every
// Worker (the 099 class).  The session half has its unit test; this is the
// page half, which had none: a page that compared revisions would have kept
// every browser cell green, because no cell crosses a Worker restart
// (review 2026-09-29, implementation, BLOCKING 2).
//
// The function is taken from the page source and compiled with exactly two
// names in scope, `session` and `savesUnsettled`.  Reading anything else -- a
// saved-revision variable, a snapshot field through another name -- is a
// ReferenceError here, and the cases below tell the two sources apart where
// they disagree.

import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PAGE = fileURLToPath(new URL("../../web/e2-editor-app.js", import.meta.url));

function pagePredicate() {
  const source = readFileSync(PAGE, "utf8");
  const match = source.match(/^function hasUnsavedWork\(\) \{\n([\s\S]*?)\n\}$/m);
  assert.ok(match, "hasUnsavedWork() not found in the page");
  // eslint-disable-next-line no-new-func
  return new Function("session", "savesUnsettled", match[1]);
}

/** A session stub whose revision says the opposite of hasUnsavedEdits(). */
const session = (unsaved, revision) => ({
  hasUnsavedEdits: () => unsaved,
  revision,
  state: { snapshot: { revision, dirty: unsaved, pending: 0 } },
});

test("no document: nothing to lose, unless a save is still settling", () => {
  const unsaved = pagePredicate();
  assert.equal(unsaved(null, 0), false);
  assert.equal(unsaved(null, 1), true);
});

test("the session's answer decides, whatever the revision says", () => {
  const unsaved = pagePredicate();
  // A fresh Worker after a rollback: revision back at 0, content unsaved.
  assert.equal(unsaved(session(true, 0), 0), true, "revision 0, unsaved");
  // Edited and saved long ago: the revision moved, nothing unsaved.
  assert.equal(unsaved(session(false, 7), 0), false, "revision 7, saved");
  // Same revision number as some save, other content.
  assert.equal(unsaved(session(true, 3), 0), true, "revision 3, unsaved");
});

test("a save asked for and not yet settled counts, even when the session is clean", () => {
  const unsaved = pagePredicate();
  assert.equal(unsaved(session(false, 4), 1), true);
  assert.equal(unsaved(session(false, 4), 0), false);
});

test("fail closed: a session without hasUnsavedEdits throws (the host asks on a throw)", () => {
  const unsaved = pagePredicate();
  assert.throws(() => unsaved({ state: { snapshot: { dirty: false, pending: 0, revision: 0 } } }, 0));
});
