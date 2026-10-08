# Adversarial review before the v19 link (2026-10-08)

Repository: `/home/jiajun/LibreOffice/study_LiteCore` (git, HEAD `daa5de61`). Paths below are relative to it. You are READ-ONLY: do not edit, create, commit or delete anything inside the repository. You may copy files to a temporary directory OUTSIDE the repository and run them there (Python tests: `cd wasm_sdk_probe && python3 -m unittest tests.<name>`; they only read). Do not run any browser, `make` (except `make -n`), any `tools/run_*.py`, or anything that writes into `wasm_sdk_probe/dist/` or `wasm_sdk_probe/build/`.

## What you are reviewing and why

A WebAssembly build of LibreOffice is being turned into an editor. "Paragraph merge" (pressing Delete at a paragraph end) is done by sending Writer's own key and proving the result from the `.uno:Undo` payload. Finding 117: on a run of blank paragraphs, 102 of 105 Delete presses each waited the full 2000 ms step deadline because no LOK callback reached the engine after the key. The fix polls `.uno:Undo` every 15 ms while waiting for the key. Finding 118: a page bug repainting a shrunk document at its old height. A new profile identity, v19, is about to be linked by the owner (a link is expensive and mints an identity that verdicts bind to), and then a counted measurement round (X1-X7) will decide whether it ships.

Your job is to attack the CRITERIA and the CHECKS, not to confirm the conclusions. For every predicate below, try to construct a concrete scenario in which the thing it guards is broken but the check stays green (or a correct thing that the check would wrongly turn red). Prefer scenarios you can demonstrate (a copied file, a mutated JSON, a unit test run on a copy) over ones you only argue. When a section has no defect, say "no defect found" for it explicitly; do not pad.

## Scope (read these)

1. **Spec** `specs/SPEC-M3-paragraph-merge.md` sections 30, 31, 32 (the last three; zh-TW). Earlier sections only as needed (22.1 is the per-clause table for M2-1/M2-3; 24 the M2-0 reduction; 7 the binding).
2. **The counted-M2 reader** `wasm_sdk_probe/tools/judge_counted_m2.py` and its tests `wasm_sdk_probe/tests/test_judge_counted_m2.py` (green case is synthetic). Evidence `findings/evidence/v18/counted-m2-reader/README.md`. Question: can a set of reports that is NOT the counted M2 as the spec defines it, or in which some clause is broken, make it exit 0 with `VERDICT PASS`? Can a correct counted run make it fail?
3. **The runner** `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`: `--mode` (`mode_schedule`), `run_case`, `run_limit`, `limit_clauses` (now with `latency`), `bound_values` / `is_counted` (the red case on v8 now counts when the non-profile bound values equal the binding), `teardown`, `pair`, the observer's drained log (finding 117). Unit tests `wasm_sdk_probe/tests/test_merge_wasm_clauses.py`.
4. **The engine fix** commit `66e5c0af` (`git show 66e5c0af`; `wasm_sdk_probe/src/probe_engine.cpp`, `MergeKeyPollMs` near line 551, the wait in `engineLoop` from about line 6058, `syntheticSelectionDeadline` near 6134). Named concerns: (a) the completion may now be sent between the key's KEYINPUT and KEYUP (spec 31.5); (b) a poll wake reuses the deadline's synthetic-command path, which only skips the queue pop; (c) can a poll read `.uno:Undo` before Writer has finished the key and judge a half-done state as verified (or as a refusal), or race with a callback that arrives at the same time; (d) anything that changes the meaning of the 2000 ms deadline (`values[0] = 2`) or the other three stages. The pure judgement `judgeAfterKey` (`wasm_sdk_probe/src/merge_key_undo.hpp`) is unchanged and model-tested (`tests/merge_key_undo_model_test.cpp`); nothing tests the poll itself.
5. **The page fix** commit `840794af`, `wasm_sdk_probe/web/e2-editor-app.js` (`documentResized` around lines 822, 844, 853; `paint()` around 961; `layoutCanvas()`). Named concern: the fix's `break` leaves `strips` partly filled while the code after the loop still runs `lastTiles = strips; paint(); layoutCanvas()`. Its red-case runner `wasm_sdk_probe/tools/run_shrink_repaint.py`, evidence `findings/evidence/v18/finding-118/{PREDICTION.md,RESULT.md}`. The fix was written after the red cases P1/P2 had run.
6. **v19 plumbing**: the v19 block in `wasm_sdk_probe/Makefile` (search `E2_V19`), the extended M1-1 checker `wasm_sdk_probe/tools/check_merge_key_undo_scope.py`, the X1 checker `wasm_sdk_probe/tools/check_profile_identity.py` and `tests/test_profile_identity.py`, the runbook `handoff/RUNBOOK-relink-v19.md`, evidence `findings/evidence/v19/pre-link/`.

## Context you will want

- The diagnosis: `findings/evidence/v18/diag-117/RESULT.md` (and its appended corrections), `findings/evidence/v18/review/fable-ruling-117.md`. Prediction D2 missed (recorded). The instrument sat at the engine's callback hook, downstream of LOK's flush handler.
- Five v18 M2-4 reports are spec 31.2's red cases: `findings/evidence/v18/m2-shakedown/m2-4-{chrome,firefox}.json`, `findings/evidence/v18/diag-117/m2-4-chrome.json`, `findings/evidence/v18/finding-118/p4-m2-4-fixed-{chrome,firefox}.json`.
- No counted run exists; nothing is bound (`BINDING` is None); v19 does not exist yet.

## Output

Write your full report to the file named in your instructions (outside the repository). Structure:

```
## SUMMARY            (at most 30 lines: counts per severity, the BLOCKING items in one line each)
## BLOCKING           (must be dispositioned before the link; each: file:line, the predicate, the scenario, how you showed it, suggested remedy)
## SHOULD
## NOTE
## No defect found    (sections 1-6, which ones)
```

BLOCKING = a counted run could be declared PASS while something the spec guards is broken, or a correct v19 cannot pass, or the link/plumbing would mint the wrong identity. Be concrete; cite lines.
