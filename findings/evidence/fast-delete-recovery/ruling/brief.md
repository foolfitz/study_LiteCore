# Brief for fable — findings 119 and 111: what to fix, where, how to verify (2026-10-09)

You are ruling ON THE OWNER'S BEHALF (the owner is asleep and authorised fable to decide for this round). Repository: /home/jiajun/LibreOffice/study_LiteCore (paths below relative to it; product code under wasm_sdk_probe/). Read whatever you need; do not edit or run anything that changes files. Every claim below marked F# is mine and may be wrong — check the ones your ruling rests on.

## Where things stand

- The product (page `e00ab76a…`, engine v19, shell generation v57, host `litecore` 0.2.8) was just re-counted end to end (R, `findings/evidence/m3-production-ui/RESULT-0.2.8.md`). Any change to a shell file means: a new shell generation (v58), a new host release (0.2.9, new engine package buildId), re-pinning and re-counting the seven M3 runners (about 3.5 h unattended), and a product-path net run. That cost is paid once per release, not per fix.
- `CLAUDE.md` (the repo rules) and spec §34 (`specs/SPEC-M3-paragraph-merge.md`: checks guard only honest accidents, no new review machinery) apply.

## Finding 119 (new; `findings/119-*.md`, evidence `findings/evidence/fast-delete-recovery/`)

Measured: on the owner's 563 KB document, typing X, Y and Backspace within ~1 ms, the delete sometimes fails with `EDITOR_STATE_UNAVAILABLE: selection text became visible without its required typed callback; no mutation was dispatched; start a fresh Worker`. 1 in 41 attempts in one long-lived page (`chrome-same-page-1.json` attempt 41), once at the 61st document in another page (`../111/browser/owner-chrome.json` round 6), 0 in 60 attempts with a fresh page each (`chrome.json`). After it: `recoverable-error`, checkpoint 「無」, save button disabled (no bytes), notice offers only 「重新開啟」 which reopens the last saved bytes — X is gone (data loss, measured). After that reopen, typing `Q` without a click did not reach the document. A second same-page run (`chrome-same-page-2.json`) is running now to see 2 more occurrences.

- F1. The message comes from the selection barrier's negative-deadline path, `src/probe_engine.cpp` ~:3870-3893 (`finishSelectionBarrierError`, ~:3324, appends "no mutation was dispatched; start a fresh Worker" when `viewRecoveryRequired`).
- F2. The engine emits `EDITOR_STATE_UNAVAILABLE` at four places: three in the selection barrier (~:3496 cannot schedule verification, ~:3888 the negative deadline, ~:4009 the precondition before the barrier starts) and one in the format barrier (~:4419, `failFormatBarrier`, which carries barrier details). In the selection barrier the delete is posted only after verification, so at the three selection-barrier sites the delete has not been dispatched. On v19 (`OXSDK_MERGE_KEY_UNDO`) the merge path's errors are `EDITOR_BOUNDARY_UNSUPPORTED` with `mergeKey`, not this code.
- F3. The shell maps it to rollback: `recoveryFor` (`editor-shell-v2/paragraph-editor-session.js` ~:44) → `formatFailureDisposition` (`editor-shell-v2/paragraph-editor-client.js` ~:234) has no barrier detail → default → "rollback"; `_blockQueueIfDispatched` (`editor-shell-v2/narrow-editor-v2-session.js` ~:716) blocks the queue in `recoverable-error`. 109's fix (checkpoint at the refusal, auto-reopen, zero loss; `SPEC-M3-production-ui.md` §3.1, §9) keys only on `EDITOR_BOUNDARY_UNSUPPORTED` (`narrow-editor-v2-session.js` ~:509-511; the page's `reopenAfterBoundaryRefusal`, `web/e2-editor-app.js` `run()` ~:1240).
- F4. `editor-shell/editor-session.js` and `input/input-adapter.js` are in E1-C's bundle (`e1/editor-shell-bundle-v2.json`) and cannot change; `narrow-editor-v2-session.js`, `paragraph-editor-*.js` and `web/e2-editor-app.js` can.
- F5 (inference, not measured): the callback is late because the engine is still applying the paste of the last typed character (the session's insert resolves when the paste is posted, comment at `narrow-editor-v2-session.js` ~:254); a large document and a long-lived page make that slower.

Options as I see them (attack them):
- **A (narrow, shell only).** For a delete action (`delete-backward`/`delete-forward`), treat `EDITOR_STATE_UNAVAILABLE` as 109's case: checkpoint at the refusal (the document is unchanged by the key, F2), block as `restart-required`, and let the page auto-reopen with the checkpoint (zero loss), with honest wording. Plus give focus back after the notice's reopen (the `Q` that did not land).
- **B (broad, shell only).** Whenever the session is about to enter `recoverable-error` with no checkpoint and the engine still answers, save a checkpoint first. Covers unknown future codes too, but saves states that may include one unverified mutation, and costs up to the 5 s selection timeout on a wedged engine.
- **C (engine, needs a relink).** Remove the cause: start the barrier only after the last paste has been applied, or re-arm the deadline when a typed callback is merely late. Root cause, but an engine change, a relink by the owner, and every engine re-validation.
- **D.** A now, C registered as the root-cause item.
My leaning: D (A now; C registered). Not B: it is new machinery for failures nobody has seen.

## Finding 111 (`findings/111-*.md`, evidence `findings/evidence/111/`)

Measured in browsers (real keys): a key pressed while typed characters are still in the input adapter is dispatched before them. Small fixture: only at real keydown gaps of 1–6 ms (Chrome Backspace 5/10, Enter 2/10; Firefox 9/10, 10/10); 0/10 at ≥ 13 ms. Owner's document: Firefox 10/10 also at ≈ 14 ms, 0/10 at ≥ 24 ms; Chrome 1/5 at 14 ms. Effect: the wrong character deleted, Enter splitting before the last letter. Not data loss.

A prototype fix exists (`findings/evidence/111/prototype/`, ~25 lines in the v2 session subclass, reads two private fields of the frozen adapter): hold any non-text operation behind the typed characters the adapter has not handed over yet; 5 new unit tests pass, 3 of them fail on the current session; the 155 existing v2 tests pass with it.

- F6. 111's fix does not remove 119 (the delete still follows the last paste immediately).

Options: ship the prototype (with its tests and a browser re-run of `tools/probe_111_overtake.py` expecting 0 overtaken) in the same release as 119's fix; or register 111 as a named limit (near-simultaneous keys) and leave it.
My leaning: ship it with 119's fix — same file, one release, one recount.

## What I need back

```
RULING:      for 119 (A/B/C/D or other), for 111 (ship/register), and whether together
WHY (for the owner, 台灣正體中文白話, ≤ 12 lines)
FACT CHECK:  which of F1–F6 you checked, and any that are wrong
CONDITIONS:  criteria to write before any run (unit and browser), what counts as verified for a defect seen 1 in ~40, and the release steps; plus anything I must not do
```
