# Review brief 6 — the §6 engine-code review before the v20 runbook (one round, fixed questions)

**Why this exists.** `specs/SPEC-M3-link-batch.md` §6: "the engine code must pass one adversarial review before
the runbook is written". The link is the owner's step and mints a new identity (`e2-editor-v20`) that verdicts
bind to; a defect found after the link costs a relink. Spec §12.7 fixed two questions for this review, both
about the `extendUnconfirmed` flag; ruling 4 withdrew the flag (§13.1), so both are moot. The four questions
below replace them. They were proposed in `handoff/HANDOFF-2026-10-13f-…-v20-part1.md` ("Part 1 result") and
adopted, with questions 1 and 4 sharpened, by the main session on 2026-10-13. **This is the only round.**

**Subject.** v20 part 1, engine and C export, all under the new define `OXSDK_E2_V20_LINK_BATCH`:
`git show 82af92ca` (`wasm_sdk_probe/src/probe_engine.cpp`, `.hpp`, `src/sdk_api.cpp`, `.h`). The worker
(`150c1770`), SDK (`1b8b7c34`) and client (`44eb15f2`) are context: read them only where a question needs to
know what reaches the page. The executor's own account is `findings/evidence/link-batch/v20-part1/README.md`
(§2.1 and §9 are its claims; treat them as claims to test, not facts). Scope in the spec: §13.3 (what v20
ships), §10.5 (C's window), §10.6 (`caretBefore`), §10.8 and §12.3 (page number, counter). The v20 build
defines what v19 defines (`OXSDK_EDITOR_DISCOVERY`, `OXSDK_FINDING_016_SELECTION_BARRIER`,
`OXSDK_E2_FORMAT_BARRIER`, `OXSDK_MERGE_KEY_UNDO`) plus `OXSDK_E2_V20_LINK_BATCH`; read the code under exactly
that set.

**Answer exactly these four questions.** Each answer either names a concrete counterexample (file:line, a
step-by-step sequence of LOK callbacks / engine steps / page requests, and what the page then sees) or says
NONE and lists what you checked.

1. **C's window.** Find a path on which the window completes `verified-boundary-noop` (`changed: false`)
   while either (a) a selection is left in the live session, or (b) the document did change, or (c) a delete
   the user asked for had something deletable and v19 would have answered a refusal that reopens — **other
   than L-C-late-K1** (K1 arriving after about 2,250 ms, spec §10.5, named and accepted). Named lead to test:
   README §2.1 claims the `textSafe && !geometrySafe` re-entry into `AwaitingUnitSelection`
   (`verifyAndDispatchSelectionBarrierDelete`) is "later, never different". At that re-entry a
   `TEXT_SELECTION` has already arrived; trace what `rejectSelectionBarrierAtDeadline`
   (`probe_engine.cpp:4005–4050`) does when its next read is `NONE` and the typed selection is collapsed,
   both when `boundaryNoopWindow` is still false and when it is already true. Also: anything that can move
   `boundaryDeadline` or `boundaryNoopWindow` between the first NONE and expiry; whether
   `gSelectionBarrier` reset by `finishSelectionBarrierBoundaryNoop` can leave the merge attribution or
   ticket in a state the next delete inherits.
2. **Locks.** The two new `gMergeMutex` scopes (`appendCaretBefore`, `finishSelectionBarrierBoundaryNoop`;
   README §7). A lock-order inversion with `gState.mutex`, a re-entrant acquisition (is either reachable
   from a frame that already holds `gMergeMutex`, e.g. from the LOK callback thread's tracker), or an
   `emitJson` reached under a lock. `tools/check_engine_lock_scopes.py` is the existing check; say whether
   it would have seen what you found.
3. **`page-rectangles` staleness.** A sequence in which the `page-rectangles` reply describes a layout the
   document no longer has (layout pending, idle formatting, a reply built between a change and its
   `DOCUMENT_SIZE_CHANGED`), **and** no later trigger the page re-reads on (the counter's push, or a paint
   reply's `documentSizeChanged`) arrives to correct it — so the page keeps a wrong M or wrong rectangles
   with no further input. A stale reply that is followed by a trigger is not a counterexample.
4. **The counter's `sourceSequence` bump.** `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED` now sets
   `editorStateChanged`, which increments `gEditorState.sourceSequence`, pushes editor-state, and calls
   `handleSelectionBarrierStateCallback`, `handleFormatBarrierStateCallback` and
   `completePendingEditorOperation` with the new type (`probe_engine.cpp:2663–2700`). Find a consumer that
   reads "`sourceSequence` advanced" (or `callbackSequenceAfter > callbackSequenceBefore`) as evidence that
   a caret, selection or tiles callback arrived, and which a size-change bump now satisfies falsely: the
   selection barrier (`dispatchSequence`, `preselectionSequence`, `collapseSequence`), the format barrier,
   the merge tracker, 096's `verified-move-readback`, the worker's projections, and the page's finding-084
   guard (`editor-shell-v2/narrow-editor-v2-session.js:285–311`, drops an announcement whose sequence does
   not advance). Also say whether the self-push can overwrite a newer page state with an older cache.

**Outside the four questions** report only a defect that changes document data or leaves a selection the
user cannot see, as BLOCKING; anything else at most five NOTE lines. Do not reopen rulings 2–5, the scope of
§13.3, or L-C-late-K1.

**Limits.** SPEC-M3-paragraph-merge §34: checks guard honest accidents only; propose no new machinery unless a
product defect needs it. You are READ-ONLY in the repository except for the one output file. You may copy
files to your scratchpad and compile or run them there (`g++ -std=c++17 -Isrc …` for the pure headers and model
tests; `node --test …` reads only). Do not run any browser, any `make` target other than `make -n`, any
`tools/run_*.py`, or anything that writes into `wasm_sdk_probe/dist/` or `wasm_sdk_probe/build/`. Do not commit.

**Output:** write `findings/evidence/link-batch/review/review-6-engine-code.md` (English).
- Begin with `## SUMMARY` (≤ 20 lines: one verdict line per question, then each BLOCKING item in one line).
- One section per question, verdict COUNTEREXAMPLE, SHOULD or NONE.
- BLOCKING = the link would ship an engine that changes document data wrongly, leaves a selection the page
  does not know about, reports `changed: false` for a change, or deadlocks. Cite lines.
- Edit nothing else.
