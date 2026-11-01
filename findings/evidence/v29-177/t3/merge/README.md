# T3: merge through the K wrapper on v29 (2026-11-01)

Spec section 6 T3, append 2. `tools/run_v83_merge.py` is a closed-list derivation of `run_k_0244_merge.py` (K's file not edited). `binding.json` is computed by `compute_binding.py`, the way the runner's `main()` does; against v28 only `wasmSha256`, `pageSha256` and `pageSourceSha256` moved (`compute_binding.stdout.txt`). Runner `aaee0cda` unchanged. Keying table `ordered-abi6`.

**MERGE_T3_HOLDS** (`read_merge.py` -> `reading-01.json`). Every case's `pass`, never `outcome`:

| report | cases | pass |
|---|---|---|
| full-chrome, shakedown | 26 | 26 |
| full-firefox, shakedown | 26 | 26 |
| instrumented, `--cases C01,C15,C29` | 3 | 3 |
| control, same cases, `--control` | 3 | 3 |
| m2-4, Chrome | 1 | 1 |
| m2-1b, Firefox | 20 | 20 |

`--pair instrumented control`: 3 pairs, same order, no difference (`pair.stdout.txt`). `self-test-01.json`: ALL_RED, 8 mutations. Every report stderr empty.

The five rows that were FAIL by the old table on v28 (C15, C16, C17, C29, C30) pass through the ordered table here, as they did in K's mirror proof.
