# S5 type oracle landed; the first counted S5 run is running detached

This supersedes `HANDOFF-2026-10-27-v23-s1-s4-closed-s5-type-oracle-next.md` as the working checkpoint. State at writing: HEAD `1e63f8de` plus this file; the only unrelated untracked file is `codex-claude-code-delegation.md` (preserve it). Times are +0800, 2026-10-27. Artifact and shell identity unchanged (profile `e2-editor-v23`, ABI6, wasm `fe1f99cd…`, page `c25b11c4…`, shell generation 76).

Owner authorization for this session (not for later sessions; re-confirm): "如果需要編譯或長時程建置，一律替我處理" and "難以決定的地方就發給fable，我授權他替我裁決".

## 1. Done in this checkpoint (step 1 of the previous handoff, plus step 2's preparation)

- Fable ruling 3 implemented as new files, leaving run-01's bound sources untouched (`de68de56`, `77e4caad`, `13981a0d`): `wasm_sdk_probe/tools/v23_native_s5_type.cpp`, `build_v23_native_s5_type_owner.py`, `run_v23_native_s5_type.py`, `read_v23_native_s5_type.py`, `tests/test_v23_native_s5_type.py`. `read_v23_native_s5.py run-01` still reproduces `reader-01.json` byte for byte.
- Native type runs (`findings/evidence/link-batch-v23/feature-protocol/s5-native/`): run-02 (build `type-build-01`) is superseded: its six-digit timestamps could not witness order in any cell (fable Addendum 1). Run-03 (build `type-build-02`, `reader-03.json` `30530678…0706`) is the type oracle: 56/56 witnessed, 47 `selection-before-x`, 9 `settle-only`, 0 fallback; it is the last type run under ruling 3 (a run-04 needs a new ruling).
- Fable ruling 3 Addendum 1 (`s5-type-oracle-ruling/RULING.md`, verbatim) after the independent opus review (`implementation-review/REVIEW.md`: no path to a false PASS on the bound data). Review items B, C, D, E fixed (`1e63f8de`); item E3 is deferred (see section 4).
- S5 plan (`v23_feature_selection_cases.py` `s5()`): type cells bind run-03 by hash; no run-01 type save is bound anywhere; deletion families keep run-01 under ruling 2. Judge (`inspect_s5`): a native type reference needs `nativeOrderWitness`; a missing native save is NE unless it is a reasoned type fallback with its settled arm.
- `s5-prep-03` (`ef0e6792`): 11 cells in Chrome and Firefox, 22/22 PASS, the first Firefox S5 execution; `shift-Right@caret-mid/type` (prep-02's FAIL under the withdrawn oracle) passes against run-03. Re-judged with the final judge: still 22/22.
- Finding 166 opened (`findings/166-…md`, evidence `findings/evidence/166/`): native LOK, Shift+arrow and x posted back to back, Writer applies x first (run-01 52/52 derivable, 14/14 shapes key-invariant; settled: 7/52, 0/14). Layer not determined; source-reading hypothesis: asynchronous accelerator dispatch outside unipoll (`svtools/source/misc/acceleratorexecute.cxx:213-226`, tdf#130382 comment). Falsifiable next step recorded in the finding (a unipoll native run of one type cell).
- Selection tests 41/41; native tests pass; counted-05 still EXPECTED_RED.

## 2. Running now: the first counted S5 run

- Launched 07:31:09 detached (`setsid nohup bash findings/evidence/link-batch-v23/feature-protocol/s5-counted-01.launch.sh`) from HEAD `1e63f8de`. Runner: `python3 -I tools/run_v23_feature_selection.py --population s5 --pre-red-report ../findings/evidence/link-batch-v23/feature-pre-red/counted-05/report.json --output ../findings/evidence/link-batch-v23/feature-protocol/s5-counted-01` (cwd `wasm_sdk_probe/`). preRed EXPECTED_RED and foreignCpu ok at start.
- The launcher writes `s5-counted-01.runner-log.txt` beside the directory while running, then moves it to `s5-counted-01/runner.command-output.txt`, runs `judge_v23_feature_selection.py s5-counted-01/report.json` into `aggregate-judge.stdout.json`/`.stderr.txt`, and writes `commands.json`.
- Expected length: about 7.3 h (Chrome 14–19 s per cell, Firefox 22–30 s, from prep-03), so roughly 15:00.
- Counted runs stop at the first nonpassing cell (no `--keep-going`); a stop means diagnose, never resume into the same directory.
- **Do not edit any file in the selection instrument's import closure while it runs** (each cell re-checks `config()`; the judge needs `report.config == config()` afterwards): `tools/{v23_feature_selection_cases,run_v23_feature_selection,judge_v23_feature_selection,judge_v23_feature_pre_red,v23_feature_pre_red_cases,v23_feature_s_cases,run_browser_probe,run_e2_c_product_path,run_e2_c_page_smoke,run_merge_wasm_shakedown,odt_paragraphs,firefox_worker_error,build_e1_b_profile,build_e2_c_shell_bundle,create_long_document,e1_support,r7_support,v21_input,v21_shakedown_common,validate_e1_c}.py`, `web/serve.py`, `web/v23-feature-selection.js` and the frozen bundle files. No browser work, native run or build may overlap it.
- After it ends: closure needs every cell PASS, `populationComplete`, a nonempty overlap set; type cells are covered by run-03 (all native-capable type cells witnessed). Then gzip the cells (`gzip -9 -n -k`, as prep-02/03), write the README, commit.

## 3. Next, in order (after the counted S5 run)

1. Read and record the counted S5 result (above). If S5 PASSes, S5 closes for both browsers.
2. Land Addendum 1 item 2 (E3): type-reader cells that fail validity (missing save, before≠fixture, discovery cursor, rounds disagreeing) make the plan refuse; fallback A only for witness (i)/(ii)/(iii) reasons. Red cases first: a missing save and a wrong pre-key selection must each raise. §34: forced by review.
3. Four arms (previous handoff step 3): re-run `git apply --check` of `product-four-arms-source/integration-pending.patch`, apply, run the product runner unpatched and patched once per browser (42 checks must match), then the first four-arm execution per browser and `judge_v23_product_four_arms.py`. This patch edits `run_e2_c_product_path.py`, which is in the S5 closure: never while a counted selection run is going.
4. R1 (72 cells × 2 browsers), then the remaining named product inputs (previous handoff steps 4–5, unchanged).
5. Finding 166's unipoll arm when native runs are free.

## 4. Named deviations and tallies

- Fallback A is wider than ruling 3's trigger until step 3.2 lands (Addendum 1 item 2). Run-03 has 0 cells affected.
- §34 for this checkpoint: forced by execution 1 (native timestamp precision), forced by review 4 (B tests and a test-state leak, C judge witness check, D plan guard, E records/aggregate counts); E3 deferred.

## 5. Not claimed

No S5 verdict exists until `s5-counted-01` finishes and its aggregate judge reads it. Nothing here claims R1, the four arms, Firefox 096 B2/B4, the remaining named inputs, host/DDEV work or K acceptance. Finding 166's layer is undetermined.
