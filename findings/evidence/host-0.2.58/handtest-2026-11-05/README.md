# Owner's hand test of host 0.2.58 (2026-11-05)

Script: `HANDTEST-2026-11-05-host-0.2.58.md` (repo root, 10 items), on `https://litecore.localhost:18443` with 0.2.58 installed
(host `0bf488a`, engine `9e9310e3`). Fixtures were put by the session into admin's `手測-0.2.58/` over WebDAV:

| Name | Source | For |
|---|---|---|
| `1-calc.ods` | `wasm_sdk_probe/tools/create_calc_structure_fixture.py` output (`calc-structure.ods`: 編輯測試, 另一張表, 保護測試, 邊界測試, 陣列測試) | 1-8 |
| `2-writer.odt` | `wasm_sdk_probe/test-docs/t1-plain-zh.odt` | 9-10 |

Result, in the owner's words: "手測全部通過" -- all 10 items pass (Calc headers, whole column/row/sheet selection, insert/delete
rows and columns with undo, refusals; Writer key bursts). The owner did not report per-item notes or the browsers used.

The owner's candidates for later Calc work, stated with the result (not started, not specified further):

1. Ctrl+C copies cells, whole columns and whole rows.
2. Ctrl+click adds cells to the selection (multi-range selection; a named limit of SPEC-P-calc-structure).
3. Naming (renaming) sheets.
4. Seeing a sheet's identity, and referencing data from another sheet.

The folder `手測-0.2.58/` is still on admin; deleting it is the owner's call.
