# E1: `.uno:ViewRowColumnHeaders` on the native 26.8 core (no build)

Experiment E1 of `research/RESEARCH-2026-11-04-calc-row-column-headers.md` section 7.2. Tool `run_e1.py` (here); harness
`wasm_sdk_probe/build/calc-range-native/calc-cell-native` as built on 2026-10-25 (bridge object sha in `run-01/receipt.json`; the bridge
source has changed since, op 0 and the harness's `command-values` action have not); fixture `cell-editing.ods` from
`tools/create_calc_edit_fixture.py`, a fresh copy. One request at a time, timed.

| Question | `run-01/` |
|---|---|
| Shape under the bridge's client zoom (op 0 sets it) | Per-entry, cumulative px, first entry `{"text": <number>, "size": <start px>}`. A ends at 113 px, B 181, C 294, **D 294 (hidden)**, E 407; rows 1 18, 2 55, 3 73, **4 73 (hidden)**, 5 90. Without the zoom (the 2026-10-25 geometry discovery) A was 110 |
| Header px x 15 against the cursor's twips | A1 cursor width 1694 = 113 x 15 - 1; E1 `xTwips` 4410 = 294 x 15; A5 `yTwips` 1095 = 73 x 15; **A1000 `yTwips` 254820 = 16988 x 15, and row 999 ends at 16988** -- no drift to row 1000 |
| Does reading headers move the cursor | No: `.uno:CellCursor` is `0, 0, 1694, 269` before and after four header reads (full, columns only, empty, near row 1000) |
| One axis, empty rectangle | `height=0`: `rows: []`, columns as full. `width=0&height=0`: `{"rows": [], "columns": []}` -- both keys present (the research expected nothing written; corrected) |
| Enlargement | A 1000 x 400 px request returns columns to N (1172 px) and rows to 26; near row 1000 the first entry is `{"text": 993, ...}` |
| Cost | 0.1-0.5 ms per header read (native); the first command after load 2.1 s (warm-up) |

Not measured here: the WASM engine (its device DPI; P-H1 on the page measures it), LOK callbacks (the harness registers none).
