# Adversarial review brief: implementation of fable ruling 3 (S5 type oracle)

You are reviewing, not building. Read only; do not edit any file outside this directory, do not run browsers, native LibreOffice, compilers or any `run_*` tool, and do not run repository-wide searches (`grep -r` over the whole tree, `find /`). A browser preparation may be running on this machine; keep CPU use small. Write your result to `REVIEW.md` in this directory, starting with `## SUMMARY` (at most 30 lines).

## What was decided (do not re-litigate)

`../RULING.md` is fable ruling 3, verbatim in its quote block. Native run-01's 56 type saves measured x-then-Shift and are not oracles. The replacement: a type-only native run with Shift INPUT/UP, the existing settle, a selection read, then x; a per-cell order witness; NE without witness; fallback A (settled-WASM) for such cells; silent members get `orderWitness: settle-only`.

## What was built (review these)

Repository root `/home/jiajun/LibreOffice/study_LiteCore`; paths relative to it.

- `wasm_sdk_probe/tools/v23_native_s5_type.cpp` (harness), `build_v23_native_s5_type_owner.py`, `run_v23_native_s5_type.py`, `read_v23_native_s5_type.py` (reader with `order_witness`), tests `wasm_sdk_probe/tests/test_v23_native_s5_type.py`.
- `wasm_sdk_probe/tools/v23_feature_selection_cases.py` function `s5()` (plan binding: type cells to run-03 saves with witness, or `native: None` + `nativeFallback` + `settledReference: true`; deletion families still run-01).
- `wasm_sdk_probe/tools/judge_v23_feature_selection.py` function `inspect_s5()` (native used only when the plan row carries a save; a missing save is NE unless it is a reasoned type fallback).
- New tests in `wasm_sdk_probe/tests/test_v23_feature_selection.py` class `S5TypeOracleControls`.
- Evidence: `findings/evidence/link-batch-v23/feature-protocol/s5-native/run-02/`, `run-02.README.md` (first run; 46 cells unwitnessable because timestamps printed at six significant digits), `run-03/` and `reader-03.json` (the bound run), `type-build-01/`, `type-build-02/`.
- Prior state for comparison: `git show de68de56^` and earlier; run-01's sources are untouched by design.

## What to attack

1. Is there any path by which a counted S5 type cell PASSes against a reference that is not a witnessed Shift-then-x native save or a fresh settled-WASM arm? Consider plan construction, the judge's `native` predicate, Home/End `native-if-single-line`, and stale or mis-bound files.
2. Does `order_witness` actually establish the ruling's clauses (i)-(iii)? In particular: can a cell read `selection-before-x` when Writer had not finished the Shift step before x was posted? Is the strict timestamp comparison meaningful given both timestamps come from the same thread's sequential code? Is the `settle-only` branch (collapsed, caret equals the three rounds' after-caret, rounds' before-caret equals this run's before-caret) a faithful reading of "settled, collapsed, caret at the moving point", or does it over- or under-claim?
3. The ruling's three red cases: are they implemented as written (swap timestamps; between text replaced by post-x selection; a run-01 record), and do they fail for the stated reason rather than an incidental one?
4. Anything in `run-03/native.jsonl` or `reader-03.json` that the reader accepted and should not have (read a sample of cells, including at least one silent member and one Home/End cell).
5. Whether the change silently altered anything for the deletion families or for S1-S4.

For each issue give: the file and line, a concrete failure scenario (inputs and the wrong outcome), and whether it can produce a false PASS, a false FAIL/NE, or only a wrong record. Say explicitly if you find no path to a false PASS. Do not propose new mechanisms beyond the ruling; if a fix needs one, say so and stop.
