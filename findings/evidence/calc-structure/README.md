# Calc insert/delete rows and columns (SPEC-P-calc-structure)

| Folder | What | Result |
|---|---|---|
| `native-build-01/` | `tools/build_calc_undo_native.py --variant structure=...,-DOXSDK_ODS_HEADERS,-DOXSDK_ODS_STRUCTURE --variant headers=...` from the bridge source to be linked (receipt with argv, sources, outputs) | built, about 5.5 s per variant |
| `n-01/` | `tools/check_calc_structure_native.py` (spec 4.1) on `structure`, control `headers` | **`N_HOLDS`** |

`n-01` in numbers (one fresh harness session and fixture per cell; reads are op 0 and op 13; the undo count is the length of
`getCommandValues(".uno:Undo")`): **N-S1** two rows inserted at index 1: A2/A3 empty, A4 the old A2, the merge moved to A5:B5, row 6
hidden, A1002 the old A1000, C1 still `=B1*2`; one undo action; one Undo back to the fixture. **N-S2** one column at index 1: C1 42,
D1 `=C1*2` = 84, column E hidden, AB1 the old AA1, and the merge A3:B3 grown to A3:C3 (the core re-merges across the insertion);
one undo action; one Undo back, merge A3:B3 again. **N-S3** row index 1 deleted: A2 is the merge, A999 the old A1000; Undo back.
**N-S4** column B deleted: the old C1 reads `=#REF!1*2`; Undo back to `=B1*2` = 84. **N-S5** protected sheet `READ_ONLY`; text in
A1048576 / XFD1 refuses both inserts with `STRUCTURE_REFUSED`; an insert that splits the array `{=E2:F3*2}` at B2:C3 refuses the
same way; count 0, index past the end and axis `x` are `INVALID_ARGUMENT`; every refusal `mutationAttempted: false`, the undo count
unchanged and the reads unchanged. **N-S6** (registered): 2-9 ms per change.

Red cases, each red in its own cell: (a) N-S1's judge on an insert at index 2 (its `after` red, the change applied); (b) N-S3 without
the Undo (its `undoneToOriginal` red). Control (`headers`, no `OXSDK_ODS_STRUCTURE`): op 14 `INVALID_ARGUMENT`, A2 unchanged.

The harness user profiles (`session-*/profile/`) were deleted after the run; the fixture and stderr of each session are kept.
