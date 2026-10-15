# Finding 145, N1: the merge runner on the fixed page, no host (2026-10-15)

**Setup.** Page `901dd6a6…` (`f7887ced`), `dist/` = `web/`, engine v20, runner `run_merge_wasm_shakedown.py` `365ceef6…` (unchanged, still bound to `ccb67a52…`, so every report says `"counted": false`). Both browsers. The local server is the runner's own (`127.0.0.1`); the host was not touched. The criteria were written in `../../../145-a-refusal-leaves-the-delete-accounting-stuck.md` (`a01ac622`) while N1 was running and before any of its output was read.

**Readings** (`judge-output.txt` is `judge_counted_m2.py --dir . --profile e2-editor-v20`, unchanged):

| criterion | chrome | firefox |
|---|---|---|
| M2-1 (60 records) | **PASS**, not passing: none | **PASS**, not passing: none |
| M2-2 (counted completions) | **PASS**: 60 of 60, runner median 122.8 ms | **PASS**: 60 of 60, runner median 126.9 ms |
| M2-3 (15 records) | **PASS** | **PASS** |
| barrier | **PASS** | **PASS** |
| red (v8: C01, C02, C03 placed, refused and reopened) | **PASS** | **PASS** |
| `../leak_model.py` (the 0.2.23 page's accounting) | 42 match, **36 mismatch** | 42 match, **36 mismatch** |
| `../leak_model_counter.py` (a refused delete settles) | **78 / 78** | **78 / 78** |

`identity`, `control`, `M2-1b`, `M2-4` and their `M2-0`/`M2-2` read NOT DONE: identity because `BINDING` still names `ccb67a52…`, the others because N1 did not run those modes. The criteria name neither.

Second sources:
- The v8 repoint the red reports served is `daa868d3…`, the value the product-path runner's `repointed_page()` gives on `901dd6a6…`; the same call on `ccb67a52…` gives 0.2.23's `49d1fd5f…`.
- The bound values differ from `BINDING` only in `pageSha256` and `pageSourceSha256`.

**A run I broke, kept** (`failed-on-my-edit/`). While N1 ran, the main session pointed `build_e2_c_shell_bundle.py`'s `MANIFEST` at the not-yet-written v73. The merge runner reads that manifest, so the next three runs (red-chrome, counted-firefox, red-firefox) died at start with `FileNotFoundError` (exit 1, 12:07:34–35Z). counted-chrome had computed its bound values before the edit and completed (exit 0).
- The edit was set aside (`git checkout`), the three runs were run again (`chain.txt`, `RERUN` line, 12:08–12:20Z), and the edit was re-applied only for the freeze.
- No report in this directory was written with the edit in place.
- Lesson: no file an instrument imports changes while it runs.
