# Unit-test red cases for the view-only gate and the unsaved predicate

Spec: `specs/SPEC-M3-page-honesty.md` §4 V3 and §7.3 U3/V3.  The handoff
`HANDOFF-2026-09-29f` said four mutations had each gone red during
implementation but wrote nothing down; this directory is those four,
**re-run** on 2026-09-29 (not copied from the session notes).

How: `unit_red_cases.py <scratch-dir>` copies `editor-shell-v2/`,
`editor-shell/`, `input/`, `reader-shell/` and `sdk/` into a scratch tree
(`dist/` symlinked, read-only use), applies one mutation to
`editor-shell-v2/narrow-editor-v2-session.js`, and runs
`node --test --test-reporter=tap editor-shell-v2/tests/narrow-editor-v2-session.test.mjs`
there.  The tree itself is never edited.  Each JSON holds the mutations
verbatim, the TAP summary, the failing test names, and the first lines of
each failing assertion.

Bound to: session file sha256 `747eea718c253ea01e00ec7477915c9a78c62148a6f167e6b42a677d2ff331f2`
(the one the dev instance serves); the test file's sha256 is in each JSON.

## A mutant nothing caught, and the test that now does

The first re-run added a fifth mutant nobody had tried: a revision
comparison written with `!==` instead of `>` ("unsaved unless the revision is
the one I saved at").  **It passed all 42 tests**
(`2026-09-29-unit-red-cases-before-strengthening.json`, test file
`6993bda09f19…`).  That is spec U3 not met: U3 says a mutation to a revision
comparison must go red, and this is one.  Its failure in the product: after a
rollback the fresh Worker restarts the revision at 0; edit until the number
equals the one the last save was taken at, and the page calls the document
saved and lets the user leave without asking -- the finding 099 class.

The finding-107 unit test now carries two more assertions: after the
rollback, `set-bold` until the revision is back at the saved number
("back at the saved revision's number"), then `hasUnsavedEdits()` must still
be true ("same revision number, other content").  After that change
(`2026-09-29-unit-red-cases-after-strengthening.json`, test file
`84f1c3428af1…`):

| Mutation | Tests | Red test(s) | The assertion that caught it |
|---|---|---|---|
| none (control) | 42/42 pass | — | — |
| gate removed (`if (false && this._viewOnly ...)`) | 40/42 | 38 "every mutating entry point is refused before it is queued"; 41 "view-only survives a fresh Worker" | `commitText` was called; "Missing expected rejection." |
| `actionMutates` defaults to false (known names true, unknown false) | 41/42 | 40 "actionMutates is fail-closed" | `no-such-control` |
| unsaved compares revisions with `>` | 41/42 | 42 "finding 107: unsaved edits follow dirty and pending, never the revision" | `rolled back to unsaved content` |
| unsaved compares revisions with `!==` | 41/42 | 42 (same test) | `same revision number, other content` (new) |
| unsaved ignores `pending` (`dirty` only) | 41/42 | 42 (same test) | `an edit still in the engine (pending)` |

Each mutation is caught by the assertion written for it, not by a crash:
the control run is green on the same scratch copy, and every red run names
a specific assertion message.
