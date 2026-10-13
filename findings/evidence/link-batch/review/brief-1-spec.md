# Review brief 1 — SPEC-M3-link-batch (draft + §9), before any engine code

**Subject:** `specs/SPEC-M3-link-batch.md` at commit `b5f2e812` (zh-TW). Its sources: `handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md`, `specs/SPEC-M3-held-key.md` §14 and §17, `findings/evidence/link-batch/extend-signatures/README.md` (native measurement, commit `81eaf66d`), `findings/evidence/link-batch/page-rectangles/README.md`.

**Your role:** adversarial reviewer. The author is the main session. Refute it where you can. Do not share its premises: check each claim against the source tree (`wasm_sdk_probe/src/probe_engine.cpp`, `src/editor_api.cpp`, `src/editor_api.h`, `editor-shell-v2/narrow-editor-v2-client.js`, `web/e2-editor-app.js`, `sdk/`, `libreoffice-26-8/`, `cool-26-04/`) before you accept or reject it.

**Limits (spec SPEC-M3-paragraph-merge §34, the owner's rule):** checks only guard against honest accidents, not against forged or hand-edited reports. Do not propose new checking machinery unless a criterion as written would let a broken PRODUCT pass during an honest run. Aim at the product design and at the criteria, not at tooling style.

## Questions

1. **The coupling claim (§3, §4.1–4.2).** The gesture gate is per action and ignores `extend`, so granting the six moves range gestures also lets plain moves from a range reach Writer. Is that true in the source? What else reads the moves' `gestures` or `limits` (page toolbar affordance, `session.offers`, the client, the format barrier's "unclassified range must satisfy both range bits" rule, other profiles' manifests or tests that pin v19's contract)? What breaks or changes meaning when the moves gain `range-single` and `range-cross`?
2. **§9's completion rule.** It completes an extend, and any move that starts on a range, on `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`. That rests on native evidence (the cursor callback is always last, and there is exactly one per cell). Find a path where this gives a wrong or stale completion on WASM:
   - a cursor callback still queued from an earlier operation;
   - "starts on a range" judged from a stale `selectionRectangles`;
   - a key that moves the cursor but emits no selection callback;
   - the a11y callback;
   - the 250 ms readback racing a late cursor callback;
   - interaction with the selection barrier or the format barrier being active;
   - anything else you find.

   Is the "S2 goes red on v19 first, 18 cells" prediction derivable from the source as the spec claims? Is the cell list right?
3. **Criteria S1–S4, R1, P1–P3, C1, E1–E3, K.**
   - For each, can an honest run pass while the product is broken for a user? Name the scenario.
   - Is each criterion form 1 or form 2 (`AGENTS.md` §1)?
   - Does each have a default conclusion?
   - Is S2's "engine readback 500 ms later" actually implementable with what the engine exposes today, or does it need a new engine operation the spec does not list?
4. **C (§4.4).** It says: complete `nothing-selected` with `keyPosted === false` as a successful no-op, but first read the selection back, and if a late Shift selected something, "collapse it back to the pre-barrier caret". Is that implementable without a new risk (how, exactly, in LOK)? Is the 250 ms window plus a readback enough to tell "nothing to delete" from "the Shift has not run yet"? Is there a safer rule?
5. **E1/E2 (§4.5).**
   - Is the stage table (`src/merge_key_undo.hpp` `kStages`) the full set of refusal exits, or are there refusals that do not go through `finishMergeKeyError` (for example `finishSelectionBarrierError`)? If there are, E1's enumeration is a hand-made list, not a tool-closed one.
   - Is `caretBefore` well defined at the moment each refusal is raised?
6. **Page number (§4.3 as corrected).**
   - Check the reading of Writer 26.8 (`sw/source/uibase/uiview/view2.cxx` FN_STAT_PAGE, `sw/source/core/view/viewsh.cxx` `GetFirstLastVisPageNumbers`) and of Collabora (`Control.StatusBar.js`, `Parts.js`).
   - Is the client-side rule equivalent apart from the two named limits?
   - Edge cases: zoom, the C′ windowed canvas (a canvas about three viewports tall with native scroll), pages wider than the view, a document that shrinks by a page (`documentSizeChanged` is on the paint reply only, after the page has painted), and the first paint after open.
7. **Scope and identity.**
   - Does ABI 4 → 5 break anything that checks ABI compatibility (the SDK's major/minor rule, the e1 profiles, frozen tests that pin the ABI header)?
   - Is anything the owner asked for missing from the scope (handoff 10-13d addendum 2)?
   - Is anything in scope that should not ride this link (one variable per link)?

## Output

Write `findings/evidence/link-batch/review/review-1-spec.md` (English). Each item:
- **BLOCKING / SHOULD / NOTE**;
- the claim it attacks, with the spec section;
- the evidence (`file:line`, quoted briefly);
- a concrete failure scenario;
- a suggested remedy, as narrow as possible.

Start with `## SUMMARY` (≤ 30 lines) and counts per class. Do not edit the spec or any other file. Commit only your review file (`git add … && git commit -m "…" -- <path>`; retry if `.git/index.lock` exists), English message ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, no `Claude-Session:` line.
