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

## After the link (2026-11-05)

| Folder | What | Result |
|---|---|---|
| `link/` | `make ods-editor-v6-dev`, agent-run on the owner's word ("需要連結還是編譯的話都請你幫我跑") after `uptime` / `pgrep -a make` | exit 0, 2 min 31 s; wasm `47e3792c`, worker `cbf3c1ef`, capability bits 24 and 25; archived `build/archive/ods-editor-v6-dev-47e3792c` (the headers-only link stays archived as `-bd85b751`) |
| `p-02/` | `tools/check_calc_structure.py --engine build/ods/editor-v6/profile` (spec 4.2), mirror of the live page sources -- **the binding run** | **`P_HOLDS`**: Chrome 18/18, Firefox 18/18 |
| `p-01/` | the same on the session before spec append 3 (with the withdrawn hidden-endpoint fallback, which never ran) | `P_HOLDS`, 18/18 both; superseded by `p-02` |
| `p-red-*/` | the spec's three page red cases, Chrome (run with `p-01`'s sources) | each **`MUTATION_RED`** in its named criterion |
| `p-s8-headers/` | P-S8: `tools/check_calc_headers.py` on the relinked profile | **`P_HOLDS`**: Chrome 145/145, Firefox 121/121 |

`p-02` in numbers: P-S1 right click on row header 3 lists the three row items with focus on the first; above inserts at row 3 (A3 empty, A4 the old A3), row 3 stays selected, row labels contiguous, toast; undo back. P-S2 column C's menu, right of C: D1 empty, F1 the old E1, C1 still 84, column C stays selected (append 1); undo back. P-S3 rows 2-3 (click, shift-click), delete: A3 is the old A5 and the hidden old row 4 is row 2 (no label "2"); 2:3 stays selected; undo back. P-S4 right click on B2 lists all six; left of B: B2 empty, C2 the old B2; undo back. P-S5 whole column C + Ctrl+minus deletes C; whole row 2 + Ctrl+plus inserts above; on a cell selection both keys change nothing and say why. P-S6 whole column selected: the cell menu's row items disabled with a reason; the protected sheet: all six disabled with a reason, choosing one changes nothing; the core's refusal on 邊界測試 (text in row 1048576): the reason in the toast, A1 and the revision unchanged, the same session, not uncertain. P-S7 Shift+F10 opens the menu on the first item, ArrowDown moves, Escape closes and the focus is back in `#cell-editor`.

Reds: `above-index-plus-1` red at P-S1 (and P-S4, P-S5, which insert before too); `count-one` red at P-S3 (and P-S6: a count of 1 no longer spans every row of a whole column); `no-reason-title` red at P-S6 only.

Spec append 3: a hidden row or column is readable through op 0 (A4: `heightTwips` 14; D1: `widthTwips` 14, measured on the native harness), so the hidden-endpoint fallback of append 2 was withdrawn before `p-02`.
