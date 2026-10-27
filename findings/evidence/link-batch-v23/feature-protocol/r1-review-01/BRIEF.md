# Adversarial review brief: the R1 collector before its first counted run

Read only. Do not edit any file except `REVIEW.md` in this directory; do not run browsers, native LibreOffice, compilers, `make` or any `run_*`/`diag_*` tool; no repository-wide `grep -r`/`find`. A native measurement is running on this machine; keep CPU light (unit tests are fine). Write in English; start `REVIEW.md` with `## SUMMARY` (at most 30 lines).

## What to review

Repository `/home/jiajun/LibreOffice/study_LiteCore`. Commit `2b561678` (`git show 2b561678`) adds `--population r1` to the public selection collector: `wasm_sdk_probe/tools/v23_feature_selection_cases.py` (`r1()` plan), `run_v23_feature_selection.py` (`run_r1`), `judge_v23_feature_selection.py` (`inspect_r1`, `judge(kind='r1')`), `web/v23-feature-selection.js` (page side), tests `wasm_sdk_probe/tests/test_v23_feature_r1.py`, and `findings/evidence/link-batch-v23/feature-protocol/r1-source/` (README with the executor's choices and open questions, mutation sweep 61/61). It was built to `handoff/WORKORDER-2026-10-27-v23-r1-collector.md` against `handoff/PROTOCOL-2026-10-26-v23-r1-inputs.md` (read the protocol first; it is the authority). The first browser preparation, `findings/evidence/link-batch-v23/feature-protocol/r1-prep-01/` (12 cells × Chrome and Firefox, 24/24 PASS, raw cells `*.json` with `report.json`), is real data you can read with the judge's `inspect`.

Later commits may touch the same files for S5 (fable ruling 4: an empty-mark route for some S5 deletion cells); those are not your subject.

## What to attack

1. Any path by which an R1 cell PASSes while the protocol says it must not: a setup that does not reproduce the recorded shape semantics, a control whose point came from the candidate, a nonpublic candidate request, an uncollapsed result, a changed revision, a missing marker/export, a late/error/recovery result, a literal Home/End row without its premise, a wrong oracle kind for a cell, the emuend rule applied to the wrong cells or not to the three.
2. The marker mapping (native `.uno:SelectAll` text to paragraph/offset; browser save with exactly one `#`): can two different landings map to the same logical position, or one landing to two? Read the tests that cover all 216 native observations.
3. The executor's open questions Q1-Q7 in `r1-source/README.md`: for each, is the current behaviour safe (no false PASS), and which ones need a ruling before counting? Q1 (token wrap exposure) in particular.
4. On the real prep-01 pages: does each PASS hold for the reasons the README claims? Spot-check at least one literal, one layout-relative, one emuend control and the s5 table-cell shape, in both browsers.
5. Whether selection (S1-S4) and S5 behaviour changed (the README claims preserved pages re-read identically).

For each issue: file and line, a concrete failure scenario, and whether it can give a false PASS, a false FAIL/NE, or only a wrong record. Say explicitly whether you found any path to a false PASS. Do not propose new mechanisms or criteria beyond the protocol; if a fix needs one, say so and stop.
