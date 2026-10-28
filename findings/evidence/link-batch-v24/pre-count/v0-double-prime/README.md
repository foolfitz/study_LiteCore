# V0″ (ruling 1 v24 pre-count §3.4)

Runner `wasm_sdk_probe/tools/run_v24_v0_double_prime.py` (new). Two departures from §3.4's letter, both forced by the reader's own code and written into the runner's docstring: step 1's live failure is `final shell source/dist differs` (v23's `identity()` raises inside `config()` before any later assertion, as V0′ recorded), and step 2 proves "only declared drift" with a census over the cohort's 30 instruments (path as payload) — a read with a moved closure tool cannot name the path, because v23's `config()` hashes its whole import closure into `configSha256`.

## run-01 (2026-10-28 15:02 +0800): V0PP_RED at step 1 — a third binding, E1 reverted

With E1 live (`run_e2_c_product_path.py` `59804737…`), step 1's read did not reach the shell: it stopped in `read_v23_native_s5_settled_reference.verify_bindings` with **`native reference input changed: wasm_sdk_probe/tools/run_e2_c_product_path.py`** (`run-01/step1-live.stderr.txt`). Step 2's census itself was as declared (1 of 30 differing: exactly `tools/run_e2_c_product_path.py`); the run stopped there.

What that is: the native settled-reference report `link-batch-v23/feature-protocol/s5-native/settled-reference-reader-05.json` carries `bindings` for **1,772 input files** (the settled reader's own Python closure via `python_sources()`, the native witness run's files, sources, libraries, headers) and `references()` re-verifies every one against the live tree. Both `run_e2_c_product_path.py` and `build_e2_c_shell_bundle.py` are among them. v23's S5 plan **and v24's** (`v24_feature_selection_cases.config()` → v23 `s5()` → `settled_references()`) go through it, so with E1 live **v24 could not build its own S5/R1 plan** (checked: `ValueError: native reference input changed: …run_e2_c_product_path.py`). Ruling 1 §3.1 named the two counted cohorts and run-03's identity; this third binding was not in the brief or the ruling.

Action (V0's default, "stop: a bound byte moved, find and restore it"): **E1 reverted** — `tools/run_e2_c_product_path.py` restored to its frozen bytes `7ba30235…` from `da556907^`; afterwards v24's `config()` builds again and the live v23 read fails only on the shell, as before E1. `bound-tool-edits.json` marks E1 `reverted` with this reason. E1's controls (`../t4/enter-oracle-witness/`) stay as a record of the oracle; they ran against the E1 bytes (`runnerSha256` in their `results.json`). E2 is in the same 1,772 and would break the plan the same way. Back to fable.

## run-02 (15:45): instrument bug, recorded

The runner passed a relative `--out` to readers that run with cwd at the repository root, so their `--output` files were never written (`FileNotFoundError`); steps 2–3 read as red for that reason only. Put-back was clean (`git status` empty). Fixed by resolving `--out` (commit after run-02); the backup copies were removed from the record.

## run-03 (15:47, after T4's verdict, E1 reverted, declared list closed): **V0PP_HOLDS**

With Addendum 1 the declared list is empty (E1 `reverted`, skipped). Live-asserted set printed: cohort 30, settled reader-05 under `wasm_sdk_probe/` 30, native run-03 identity 12, union **40** paths (`report.json` `liveAsserted.paths`).

1. live read: exit 1, `final shell source/dist differs: sdk/document-sdk.js` (the shell, as V0′ recorded);
2. census 0/30 drift; with only the shell restored (nothing else declared) the read exits **0**: `COMPLETE_R1_PASS` 144/144, `STOPPED_S5_INCOMPLETE` 402 observed (401 PASS + 1 FAIL);
3. the same with every declared file restored (= the shell): exit 0, stages equal to `completion-read-01.json`;
4. native run-03 re-read equals `reader-03.json`;
5. E1-C `intact: true`;
6. put back: shell at the cutover bytes, no problems, `git status` empty under `wasm_sdk_probe/`;
7. four-arm cohort drift: exactly the two pre-v24 moves (`judge_v23_feature_selection.py`, `v23_feature_selection_cases.py`).

Red cases (`reds/`, scratch inputs kept beside): **V-1** a scratch cohort whose frozen hash for `tools/run_e2_c_product_path.py` is wrong → `V0PP_RED` at step 2, `undeclared drift ['tools/run_e2_c_product_path.py']` (the path as payload). **V-3** a scratch list declaring `web/serve.py`, which has not moved → `V0PP_RED` at step 2, `declared but unmoved ['web/serve.py']`. **V-2** (a declared entry with a wrong `liveSha256`) needs a bound file that has actually moved; the closed list forbids moving one, so it is not constructed — its check (step 6) runs on every V0″ whenever a list entry exists.

## run-04 (after the generation-77 freeze, `be13e0b5`): **V0PP_HOLDS**

Same seven steps on the frozen tree: census 0/30 drift; shell-restored read exit 0 with the recorded stages; native run-03 re-read equal; E1-C intact; put back clean; four-arm cohort drift exactly the two pre-v24 moves. The freeze's three changes (`e2/editor-shell-v2-bundle-v77.json`, `Makefile`, `tools/v24_feature_selection_cases.py`) touch nothing v23 asserts.
