# T4 reader red cases (ruling 1 §1.4), before run 02

`reader_red.py` copies run 01's `chrome/` (and `firefox/` for R-f) into a scratch directory, mutates the copy, runs the corrected `wasm_sdk_probe/tools/read_v24_t4.py` (Correction 1: rule 2a/2b, volatile list) on it and checks the declared outcome; run 01's committed files are only read. `results.json` has every case's exit, verdicts and red rows. 2026-10-28: **6/6 hold, `RED_CASES_HOLD`**.

| Case | Mutation (scratch copy) | Outcome |
|---|---|---|
| R-a | `ctrl-v-reaches-the-document` v24 PASS→FAIL | rule 2 FAIL, the one red row is that check under 2a |
| R-b | `clear-format-removes-every-inline-format` v24 NE→PASS | rule 2 FAIL under 2b (equality, not "at least as good") |
| R-c | `every-inline-format-reaches-the-document` `observed.arms[0].bold` flipped | rule 2 FAIL under 2b, payload `[0]/observed/arms[0]/bold \| True \| False` |
| R-d | the same member, only `formatPressWaitedMs` 402→999 | the member stays ok, rule 2 PASS (the exclusion applies, and only there) |
| R-e | `wire.json` without the 23 paste-route `insertText` requests (no `replaceSelection`/`pasteMarkdown` occurred) | T4 NE, not PASS |
| R-f | run 01 unmodified, both browsers | rule 2 PASS → `../read-01b.json` |

**`read-01b.json` is not T4's verdict**: the rule was corrected after run 01 (CLAUDE.md §9(1)); it is a dry re-read of real data. T4's verdict is run 02's.
