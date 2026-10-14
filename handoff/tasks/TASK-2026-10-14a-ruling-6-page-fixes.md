# Task 2026-10-14a: ruling 6's three page/shell fixes (conditions 45, 47, 48), before shell generation v67

**Ruling:** `findings/evidence/link-batch/review/ruling-6.md` §Q2, §Q3, §Q4 and conditions 45, 47, 48. Read those sections first. They are the spec for this task, and where this file and the ruling disagree, the ruling wins. Background: `findings/evidence/link-batch/v20-part2/README.md` §3 (the scheduler) and §4 (C on the page, with the `_enqueueOwned` sketch). Review 6 §4 and appendix A give the `placeCaret` counterexample and the harness (`findings/evidence/link-batch/review/review-6-artifacts/`).

All three fixes go in `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-session.js` plus tests in `wasm_sdk_probe/editor-shell-v2/tests/`.

## Hard limits

- **Do not modify anything under `wasm_sdk_probe/editor-shell/`.** It is E1-C-bound. Run `python3 tools/check_e1_c_bundle_intact.py` (from `wasm_sdk_probe/`) before you start and after your last commit. Both runs must print `"intact": true`.
- Do not touch:
  - `src/`, `sdk/`, `Makefile` or `dist/`;
  - `web/` (the page needs no change for any of the three; if you find it does, stop and report);
  - any profile, pin or binding;
  - any tool under `tools/`.
- No build, no link, no shell-generation freeze, no push.
- Another session is committing in this same tree (specs, findings, tools). Stage and commit **only your own paths**, using `git commit -- <paths>` or explicit `git add <path>`. Never `git add -A` or `git add .`.

## Work, in this order; each item red first

1. **Condition 48: the scheduler after a failed read.**
   - Add `this._issuedAt = null` in `PageRectanglesScheduler._settle`'s error branch.
   - Tests:
     - (a) a failed read followed by a state write with the same counter re-reads;
     - (b) control: a successful read followed by the same counter does not re-read;
     - (c) a failed read followed by no state write issues nothing.
   - (a) must fail before the change; show the failing output.
2. **Condition 47: a `verified-boundary-noop` delete is not a mutation.**
   - Implement README §4's `_enqueueOwned` (or an equivalent that lets the operation flip its own queue item's `mutation`). Route the subclass's own `_enqueue` and `_releaseHeld` through it.
   - In `action()`'s operation, call it only when `result?.completion === "verified-boundary-noop" && result?.changed === false`.
   - Pin test for the second private seam of the frozen base, in the shape of `narrow-editor-v2-session.test.mjs:211`. It covers two facts: `super._enqueue` pushes the item synchronously, and the drain reads `item.mutation` only after the operation returns.
   - Red-first test, which is the README §4 measurement itself: a clean document and one noop delete give `dirty` false, `_contentSequence` and `_currentContentStamp` unchanged, and `hasUnsavedEdits()` false; the following boundary move then banks no checkpoint.
   - Control: a verified (changing) delete still sets `dirty`.
   - Also check that the view-only gate still refuses deletes.
3. **Condition 45: the `placeCaret` acknowledgement.**
   - Add an own `placeCaret` on `NarrowEditorV2Session`, with the base's contract and return shape. The predicate is in ruling 6 §Q2: acknowledgement = `sourceSequence` advanced **and** (caret position differs, `caretDiffers` position-only as today, **or** the selection's `collapsed`/`rectangles` differ from the pre-click state).
   - Return on that evidence when on target, or on `onTarget` after `graceMs` (unchanged), or on evidence with the caret moved off the line (the 052 path). Never return on the sequence alone.
   - Keep `caretConfirmedBy` values and the `EDITOR_CARET_NOT_PLACED` error as the base has them.
   - Test file: the seven arms of ruling 6's §Q2 table, driven through the product's method against a scripted engine, as review 6's harness does. Three arms must be red on the base class: lone size bump, lone tile bump, and a bump where the click is never processed. Four must be equal: plain, identical point at about 400 ms, selection collapse, and off-line.
   - Show the base run (3 red) and the override run (all green).
   - `product-page-calls.test.mjs` must still pass.
   - Before writing the predicate, read which state fields the v2 client's `getState()` actually returns (selection shape), from source, not from memory. If the selection is not in the state reply, stop and report rather than inventing a field.

## Done means

- `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs` passes in full (baseline 386/386 at `f1f75e88`; report the new count).
- `node --check` passes on the changed file.
- The E1-C check is intact before and after.
- An append to `findings/evidence/link-batch/v20-part2/README.md`, in English and append-only: a new section "Ruling 6 fixes" with:
  - one subsection per condition, with file:line;
  - the red-first outputs, quoted short;
  - README §3's corrected cost sentence ("a read that always fails costs one read per state write while it fails");
  - your judgement calls.
- Commits with your own model's `Co-Authored-By` trailer; one commit per condition is fine.
- Report: a `## SUMMARY` of at most 30 lines, giving commits, test counts, the E1-C result, and anything you stopped on.
