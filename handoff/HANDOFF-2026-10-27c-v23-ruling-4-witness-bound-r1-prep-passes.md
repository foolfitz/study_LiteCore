# Ruling 4 witness bound, R1 prep passes; two order-dependent cells block counted S5-02

This supersedes `HANDOFF-2026-10-27b-v23-s5-type-oracle-landed-s5-counted-running.md`. State: HEAD `b80e5c53`; tree clean except the unrelated untracked `codex-claude-code-delegation.md` (preserve it). Times +0800, 2026-10-27. Stopped at the owner's request ("這輪掃描結束就先交接，我們usage快燒完了"). Owner authorization for this session (not later ones; re-confirm): build/long runs handled by the session, hard calls to fable. Nothing is running: no browser, native run or build.

## 1. What happened since the 27b handoff

1. **s5-counted-01 stopped** (`feature-protocol/s5-counted-01/`, README): 106 Chrome cells, 105 PASS, then FAIL `shift-End@cell-end/backspace`: product and its settled arm saved `A1 cell tex`, run-01 native saved `A1 cell text`. Counts for nothing (fable ruling 4).
2. **Cause: Writer's empty mark.** A Shift key that does not move still sets a mark; `SwCursorShell::IsSelection()` counts `HasMark()` with mark == point (`sw/inc/crsrsh.hxx:951-955`), so the next `DelLeft`/`DelRight` deletes the empty range (`sw/source/uibase/wrtsh/delete.cxx:167-191`, `:308`). Not timing: `s5-native/diag-settled-01/` (every member settled) equals run-01 in 66/66. Product deletes one character (its caret delete builds its own selection, `src/probe_engine.cpp:6281`); `s5-prep-04/` 10/12 FAIL by exactly one character. Finding **167** opened.
3. **Fable ruling 4** (`s5-silent-shift-deletion-ruling/RULING.md`, verbatim): option B1. A deletion cell is `emptyMark` iff a bound native settled run of its own sequence shows, right after its Shift, selection type 0 with empty selection text; such cells compare with the fresh settled-WASM arm, are labelled, and the native branch refuses them. The coordinator's nine-arm sentence in the brief was wrong for five before-and-after cells (fable caught it). Conditions 1-4 in the ruling.
4. **Ruling 4 implementation** (`acdb444b`, `0dbd8bbb`): plan route `empty_mark_route()` in `v23_feature_selection_cases.py`; judge refuses native for emptyMark rows, reads `native save not order-independent` as NE, FAIL records carry `reference`/`singleLineWitness`/`emptyMark`/`differingParagraph`, aggregate `emptyMarkCells`/`emptyMarkRoutedCells` per browser (NE if a counted run routed none). Red cases (a)-(f) in `tests/test_v23_feature_selection.py::S5EmptyMarkControls` were shown red on the previous code. Addendum 1 item 2 (E3) landed in the same change.
5. **Witness run** (ruling 4 condition 1): `s5-native/empty-mark-witness-01/` (336 cells, 39 min, diag harness `v23_native_s5_settled.cpp`), read by `tools/read_v23_native_s5_empty_mark.py` into `s5-native/empty-mark-reader-01.json` `fc62e6ad…7974`, bound in the plan. Verdict READ: **49 emptyMark** (36 single/twice + 13 before-and-after, as the diag predicted), both consistency checks hold, **2 cells not order-independent** (section 2).
6. **R1 collector** built by an opus subagent in an isolated worktree while counted-01 held the main tree, merged as `2b561678` (`--population r1`; workorder `handoff/WORKORDER-2026-10-27-v23-r1-collector.md`; `feature-protocol/r1-source/README.md`). **R1 prep-01** (`r1-prep-01/`): 12 cells × Chrome and Firefox, **24/24 PASS**. Independent opus review (`r1-review-01/REVIEW.md`): no false-PASS path under the protocol's list except "late". **Fable R1 ruling 1** (`r1-review-01/RULING-1.md`, verbatim): adopt S2's stale comparison for both arms; keep the pre-red prerequisite; token-wrap default stays FAIL-with-note. The stale check and its four red cases (C1 a-d) are in `judge_v23_feature_selection.py` `r1_arm` and `tests/test_v23_feature_r1.py::test_stale_reply`, **not yet verified** (section 3).

## 2. Blocker for counted S5-02: two order-dependent native cells (needs fable)

`shift-Home@heading-mid/backspace-twice` and `shift-Home@list-mid/backspace-twice`: Shift+Home selects to the paragraph start, Backspace deletes the selection, and the second Backspace lands at the start of a heading/list paragraph. Back-to-back (run-01) and settled (witness) saves differ: for heading-mid, back-to-back merges the heading into the previous paragraph (12 paragraphs), settled does not (13; Writer's first Backspace at a numbered/outline start removes the level); list-mid has equal paragraph text but different `reduce_content`. Both are `native-if-single-line` Home cells; under ruling 4 they read NE when the browser's single-line witness holds, so a counted run would stop there. Ruling 4 expected 0 such cells; per its own words a different number is a measurement to stop at. Ask fable: which oracle (settled native save from the witness run, which is the human-pace Writer result; settled-WASM; or NE stands). Measure the product on these two cells first (a 2-cell × 2-browser S5 prep, about 3 min) so the brief carries numbers.

## 3. Open test failures (expectation updates, not behaviour)

- `tests/test_v23_feature_r1.py`: 22 failures, all in the preserved-page re-read test: stored S5 inspections now differ only by the new record-only keys `emptyMark`, `emptyMarkWitness` (and R1 `staleFields`). Update the comparison to ignore those keys or compare verdict/reason/reference; then confirm `test_stale_reply` passes and the other R1 tests stay green.
- `tests/test_v23_feature_selection.py::S5TypeOracleControls::test_live_plan_binds_type_cells_to_run03_or_the_settled_fallback`: TypeError: its final loop assumes every native-policy deletion row has a native save; emptyMark rows now have `native: None`. Skip rows with `emptyMark` there.
- R1 ruling 1 C2-C3 then: re-run `r1-source/reader-mutation-sweep.py` (must list the new stale check, ALL_KILLED; regenerate its output) and re-read the 24 prep-01 pages (24 PASS, records identical apart from empty `staleFields`).

## 4. Next, in order

1. Fix section 3's tests; run all suites (selection, R1, native S5 type/boundary).
2. Section 2: product prep on the two cells, brief, fable ruling, implement, red cases.
3. S5 prep-05 under the final plan and the R1-merged page JS (S5 has not run in a browser since the R1 merge): a few emptyMark cells (e.g. `shift-End@cell-end/backspace`, `shift-Right@doc-end/backspace`), non-emptyMark before-and-after (`shift-End@empty-para/delete-before-and-after`), a type cell, a settled cell; both browsers.
4. Four arms (27b handoff step 3): `git apply --check` passed at 09:10 today; product runner unpatched and patched once per browser (`python3 -I tools/run_e2_c_product_path.py --browser chrome|firefox --out …`, from `wasm_sdk_probe/`), then `judge_v23_product_four_arms.py`. The patch edits `run_e2_c_product_path.py`, which is in the selection closure: never during a counted selection/S5/R1 run.
5. Counted R1 (72 × 2, about 1.7 h at prep-01's 15-73 s/cell; `--population r1 --pre-red-report ../findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json`), and counted S5-02 (about 7.3 h; use `findings/evidence/link-batch-v23/feature-protocol/s5-counted-01.launch.sh` as the template with a new output name). Detached with `setsid nohup`; no closure edits while either runs.
6. Finding 166's unipoll arm and finding 167's desktop-Writer check when convenient.

## 5. Records and tallies

- Fable rulings this session: ruling 3 Addendum 1 (run-03 is the type oracle), ruling 4 (empty mark), R1 ruling 1. Opus reviews: ruling 3 implementation, R1 collector.
- §34 for 27b→27c: forced by execution 3 (empty-mark route; FAIL record payload; order-independence NE), forced by review 2 (R1 stale check; ruling 3 review items already counted in 27b).
- Named limitation (ruling 4): S5 does not guard the delete unit after a no-op extension; the ordered-delete gates are where that mutation would be red; not yet confirmed which existing check, register it under §3 if none.

## 6. Not claimed

No S5 or R1 verdict exists (no complete counted population). Four arms, Firefox 096 B2/B4, remaining named inputs, host/DDEV and K are untouched. Findings 166 and 167 are native-LOK measurements with source readings; neither layer/desktop question is settled.
