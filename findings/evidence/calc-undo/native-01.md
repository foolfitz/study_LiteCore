# NU: how many engine undos each Calc page write takes (native)

Spec `specs/SPEC-P-calc-undo.md` section 2, criteria and predictions committed before the run (`683864f21`). Tool `wasm_sdk_probe/tools/probe_calc_undo_native.py`, on the existing native bridge `build/calc-style-native/calc-cell-native` (the Calc v3 bridge source on native core 26.8; nothing compiled). Run 2026-11-03 14:19, `python3 probe_calc_undo_native.py --out native-01` (without `-I`: the tool imports its neighbours; a first attempt with `-I` died on that import before creating anything, `native-01.stderr.txt` was overwritten by this run). Report `native-01/report.json`; every arm's requests, replies and the saved B, U0 to U5 are in `native-01/`.

Back = every cell of the first sheet equals the zero-write save B in content and resolved automatic style. Two observers: the saved file, and the bridge's op 0 read of the target cell.

| Arm | Writes | Undos to get back (file = read) |
|---|---|---|
| `zero` | none | 0 |
| `two-inputs` | op 1 F1, op 1 F2 | 2 |
| `input-text`, `-number`, `-formula`, `-overwrite`, `-clear` | op 1 | 1 each |
| `cell-bold`, `cell-italic` | op 2, op 3 on B2 | **3 each** |
| `cell-underline` | op 4 on B2 | 1 |
| `range-bold`, `-italic`, `-underline` | op 7, 8, 9 on A1:C2 | 1 each |
| `range-textColor`, `-backColor`, `-align` | op 10, 11, 12 on A1:C2 | 1 each |
| `draft-then-bold` | op 1 F1, op 2 F1 | **4** |

- NU-0 holds: `zero` 0, `two-inputs` 2. NU-1: the two observers agree on every arm. Every write replied `ok: true, changed: true`.
- Matches the prediction on every arm.
- `cell-bold` step by step (op 0 read of B2): after the write all three true; undo 1 clears `boldComplex`, undo 2 `boldAsian`, undo 3 `bold`. The bridge's op 2 and op 3 call `setPropertyValue` once per script (`src/calc_cell_bridge.cpp` 400-415), and each call is its own undo action. On a Chinese cell the first undo changes nothing visible and the second makes the Chinese text regular; the Latin script stays bold until the third.
- `range-bold` writes the same three properties in one `setPropertyValues` and takes one undo. So op 2 and op 3 written the same way would take one; this is inferred from the range arms (the same call), not measured on a single cell.
- `draft-then-bold` is the page's Ctrl+B with a draft pending (`CalcEditorSession.setFormat` commits first): 1 for the commit plus 3.

Each arm's LOK user profile (`native-01/profile-*`, about 570 KB each, caches only) was deleted after the run and is not in git.
