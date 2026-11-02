# Calc: each sheet keeps its view (SPEC-P-demo-batch-1 section 2)

Tool: `wasm_sdk_probe/tools/check_calc_sheet_view.py`. Mirror of the live sources, frozen profiles `ods-editor-v2` and `ods-viewer-v3`, real pointer, wheel and keys, one run per browser and page. Three sheets: 300, 200 and 8 rows; the short one exists to catch a restore that scrolls before the surface has grown back.

| Run | Sources | Result |
|---|---|---|
| `red-before` | the pages before the change | Red in the shape the owner reported: editor, sheet 2 first visit `scrollTop` 2500, equal to sheet 1. Viewer C2 red: a sheet seen before came back at 0. |
| `green-01` | after the change | Editor 14/14, viewer 11/11, Chrome 156 and Firefox 157. |

- `red-before` also carries two Firefox C3 reds with `ink: 0` on the editor. Those tiles were real and blank: the stale scroll position lay past the data of the shorter sheets. They vanish because the view does, not because of a separate fix.
- `showPart` read `readCell(0,0)` on every switch, so restoring the scroll alone left the view on row 171 with A1 active and the next arrow key jumped to the top. The session keeps each sheet's active cell (`tests/calc-editor-session.test.mjs`, red before the change: `[0,0,0]` against `[0,1,0]`).
- `green-01/chrome-editor-back-to-sheet1.png` read by eye: sheet 表一, P171 active, name box and formula bar agree, the grid is painted at row 148-193.
- Shell unit tests 97/97; `check_calc_format_entry_mutations.py` 15 of 15 and `check_calc_range_mutations.py` 6 of 6 still caught.
