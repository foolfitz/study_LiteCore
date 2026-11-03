# ods-editor-v4 frozen, the Calc page switched to it

2026-11-03 ~18:15. After CU held on the development profile (`../cu/v4-dev-03`) and the Calc regressions (`../cu8-dev`, `../post-link-dev/cell-v4`):

- `build/ods/editor-v4/profile` copied to `dist/profiles/ods-editor-v4` and `build/archive/ods-editor-v4-9f37ed5a-worker-4a06fbe4` (with `ATTRIBUTION.md`); the three copies equal file for file and equal `../link/profile.sha256`. The v4 make rule now refuses to relink.
- `web/ods-editor-app.js` `ENGINE_OPTIONS.workerUrl` -> `./profiles/ods-editor-v4/sdk-worker.js`; `make ods-editor-assets` (copies only); `dist/` equals `web/` and `spreadsheet-shell/`.
- The mirror tools that alias the page's engine URL by name learned v4 (`run_calc_editor_browser.py`, `check_calc_style.py`, `check_calc_sheet_view.py`); without it they load nothing once the page names v4.

On the switched page with the frozen engine:

| Run | Result |
|---|---|
| `check_calc_sheet_view.py`, `calc-sheet-view-v4` (C) | Chrome and Firefox, editor 14/14, viewer 11/11 |
| `check_calc_undo_cu.py --engine dist/profiles/ods-editor-v4`, `cu` | `CU_HOLDS`, both browsers |
| `run_calc_editor_browser.py --profile dist/profiles/ods-editor-v4 --repeats 1`, `cell-v4-dist` | 31/31, both browsers |

Also after the switch: the three Calc mutation tools pass, Calc unit tests 67/67, the Writer generation 88 bundle check has no problems. The first C and cell attempts here died at once on a mirror-directory name collision with earlier runs (those tools key their mirror by the output folder's name and keep it); rerun under new names, the empty receipts removed.
