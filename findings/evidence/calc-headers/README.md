# Calc row/column headers (SPEC-P-calc-headers)

| Folder | What | Result |
|---|---|---|
| `e1/` | `.uno:ViewRowColumnHeaders` on the native core through the 2026-10-25 harness, no build | shape, units and side effects pinned (its README) |
| `native-build-01/` | `tools/build_calc_undo_native.py --variant headers=...,-DOXSDK_ODS_HEADERS --variant v5=...` from the bridge source to be linked (receipt with argv, sources, outputs) | built, 11 s |
| `n-01/` | `tools/check_calc_headers_native.py` (spec 4.1) on `headers`, control `v5` | **`N_HOLDS`** |

`n-01` in numbers: fixture read back as built (AA1, A1000, E1, A5); **N-H1** six rectangles, 185 header cells each checked against op 0's cursor (start x 15 and size x 15 - 1), hidden D and row 4 where expected, labels to AF from the engine, the cursor unchanged across every op 13 (0.1-0.8 ms); **N-H2** whole columns A-F and AA, rows 1, 3 (merged) and 1000, and the sheet: bold at (c,0), (c,999), (c,1048575) or the row/sheet equivalents, all off after one `.uno:Undo`; **N-H3** protected sheet `READ_ONLY`, A1:B40000 `RANGE_TOO_LARGE`, A3:A3 `RANGE_MERGE_BOUNDARY`, whole column A applies and A3 reads bold. **N-H4** (registered): whole-column bold 0.3-6.9 ms, whole sheet 0.5 ms -- far under the spec's 2 s, so the corner keeps formatting (decision 4).

Red cases, each red in its own cell: (a) op 0 in place of op 13 moves the cursor; (b) endRow = maxRows - 2 is not a whole column: `RANGE_TOO_LARGE`; (c) the pre-zoom core reply (A = 110 px) misaligns from column A on (want 1649 twips, cursor 1694). Control (`v5`, no define): op 13 `INVALID_ARGUMENT`, whole column `RANGE_TOO_LARGE`.
