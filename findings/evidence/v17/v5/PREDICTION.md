# V5 on v17: the owner's document, before the run

Written 2026-10-07 after reading spec section 26.3 (V5) and before any v17 run of the merge runner. Nothing below moves the criterion; it fixes how the criterion is read per cell, because section 26.3 states it as a summary ("276/414 -> 348/521") and the 11 cells have four native heights, not two.

## The run

From `wasm_sdk_probe/`: `python3 tools/run_merge_wasm_shakedown.py --browser chrome --candidate-profile e2-editor-v17 --owner-document --out ../findings/evidence/v17/v5/shakedown-chrome-v5.json`. Runner sha256 `c3f723b3be6eb4bf…` (re-verified before writing this file). Diagnostic, uncounted, one round, Chrome. The tool-generated list plus the owner's document (no `--cases`), so the 28 synthetic cases run as well; they are not part of V5 and are listed, not judged. The owner's document's saves go to `wasm_sdk_probe/build/merge-wasm-private/shakedown-chrome-v5.docs/` (not the repository); the report carries hashes and paragraph indexes only.

Precondition (not V5, but a run that fails it is not evidence about v17): report `candidate.profile` = `e2-editor-v17`, `candidate.pageSha256` = `4c0088c7a518bc36b9cc999d2e67796d20a58525355b68ae67881228dc95b498` (the value `build_cutover_page.py --profile e2-editor-v17` printed for `f4bcda37`), `pinAfter` = `ad3f68bb85f94589`, `restOfShellEqualsSource` true, `boot` ready.

## Per-cell reading of V5

Height = the fourth element of the engine caret the runner recorded for the case (`place.engineCaret`, or `place.afterClick` when the click alone placed it). Native heights are R0c's (`nativeCaret`), the same values the v16 run 3 report carries.

| case | native height | v16 engine height (red case, `v16-shakedown/merge/shakedown-chrome-3.json`) | V5 expects on v17 |
|---|---|---|---|
| E01 | 348 | 276 | 348 |
| E02 | 521 | 414 | 521 |
| E05 | 521 | 276 | 521 |
| E10 | 348 | 230 | 348 |
| E12 | 348 | 276 | 348 |
| T01 | 463 | 277 | 463 |
| P27 | 348 | 276 | 348 |
| E13 | 348 | 276 | 348 |
| E15 | 348 | 276 | 348 |
| P62 | 348 | 276 | 348 |
| P63 | 348 | 276 | 348 |

Clause 1 (heights): every row's engine height equals its native height. Section 26.3 names 348/521; E10 (230 on v16), T01 (463 natively, 277 on v16) and E05 (a 521 line that v16 drew at 276) are read the same way, by equality with the native caret, because that is what "becomes native R0c's" means per cell. A row that differs is a miss on that row, reported by name.

Clause 2 (class): each of the 11 rows has an outcome other than `placement-mismatch`. A row still `placement-mismatch` with the right height (x or y off) is a miss on clause 2 for that row, not on clause 1.

Red case: v16 run 3 (the table above, 11 of 11 `placement-mismatch`). Not re-run.

## Observed, not judged by V5

- The document height the page reports (`place.size.h`): v16 257,114 twips. Expected on v17: more than 275,530 (T01's native caret y), because natively T01's line starts there. A smaller value with matching heights would mean the layout differs elsewhere (pagination, spacing), which is a finding.
- For rows that place: the merge outcome, the after-key and after-`Z` paragraph text against the native key arms. Expected `verified-key-undo` and equal text (R0c decided `merge` for all 11). Any other outcome is a finding about B on this document, not a V5 miss. Whether the owner's document returns to M2-1 is not decided here (section 26.3: a new appended spec section with reasons).
- If clause 1 holds, V4's 19-vs-20 (TW-SIYUAN, TW-KAI) stays a canvas-pixel reading question, not a fidelity gap (handoff 10-07d, "Open").
- The 28 synthetic cases and M2-0: listed. A synthetic case that does not pass as on v16 run 3 is a finding to look at before V6, not part of V5.

## If V5 misses

Report the missing rows by name with their heights and x/y. Do not move the criterion. Then: first read the fontconfig debug of the owner's document's font names on v17 (the probe saw only 113's fixture), before any other explanation.
