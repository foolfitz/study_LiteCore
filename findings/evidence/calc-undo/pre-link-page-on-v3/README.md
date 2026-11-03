# The new Calc page on the frozen v3 engine, before the link

The page carries the undo buttons and keys (commit `bacfd8c84`), shown only when the manifest has `undo`. On `ods-editor-v3` they stay hidden and Ctrl+Z / Ctrl+Y are not taken, so the page must behave as before. Mirror runs from `web/`, 2026-11-03 ~15:25:

| Run | Result |
|---|---|
| `check_calc_sheet_view.py --out calc-sheet-view` (C) | Chrome and Firefox, editor 14/14, viewer 11/11 |
| `run_calc_editor_browser.py --profile dist/profiles/ods-editor-v3 --repeats 1 --out cell` | `pass: true`, Chrome 31/31, Firefox 31/31 |
