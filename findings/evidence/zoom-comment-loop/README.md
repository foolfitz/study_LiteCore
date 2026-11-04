# Writer zoom on a document with a comment: the resize loop and its fix

The owner's hand test of host 0.2.56, item 1 (`../host-0.2.56/handtest-2026-11-04/README.md`); finding 185. Fix on the dev page
(`wasm_sdk_probe/web/e2-editor-app.js`, `laidOut` / `sizeReportMovesLayout`, `RESIZE_TOLERANCE_PX = 8`), not frozen, not released: it
waits for the owner's next hand-test slot (CLAUDE.md, the section on cadence).

Tool: `wasm_sdk_probe/tools/check_writer_zoom.py`, changed for this (sha and argv in each `report.json`):

- `--document`, default `t3-long.odt` as before.
- Z0, Z1, Z6: the paper (Z0: the document rows) is the level applied to *a width the page may be laid out for*: reported by the engine
  (every paint's `documentWidthTwips`, and the open's `width`) and within 1 percent of the last report (`laid_out_widths`), compared
  unrounded. One width for a document without comments, so as strict as before there; Writer reports a few for a document with a comment.
  The 1 percent keeps a page stuck at an old width, or one that missed a real change (a comment sidebar is about 27 percent), red.
- Z2: also requires no paint request during `QUIET` (1 s) after the level settled. The defect painted forever.

| Run | Page | Document | Result |
|---|---|---|---|
| `red-on-current-page` | HEAD's page (before the fix) | `r7-compat/l1-layout-table-image.odt` (one comment) | **`Z_RED`**. Chrome wide 31/37: Z2 red at 100, 125, 150 up and down (not covered, 31-57 paints in the quiet second). Chrome DPR 2 13/18: Z2 red at 125, 150, 200 (the backing width is capped at 2400, but each request's width follows the report, so the scale still moves). Firefox wide 30/37: Z2 the same six, 84-120 paints in the quiet second, and Z1 at up-150 read mid-loop. Narrow 6/6 on both; fit holds in the 1400 px window, as fable's model predicts |
| `green-on-fix-l1` | the fix | l1 | `Z_RED` from the reader, not the page: Z2 green in all 27 cells, **0 paints in every quiet second**. Red: Z0/fit (rows 2734 against 2736 from the last report), Z6 narrow (2266 against 2265), Z1 DPR 2 at 150 (paper 1699; Python's banker's `round(1698.5)` is 1698, the page's `Math.round` 1699). The reader compared with the *last* report; the fix keeps an earlier one inside its tolerance |
| `green-on-fix-t3` | the fix | `t3-long.odt` | **`Z_HOLDS`** 34/34, 6/6, 16/16, 34/34, 6/6: the tool's new Z1/Z2 do not turn the old document red |
| `green-on-fix-l1-r2` | the fix | l1 | Reader fixed (`laid_out_widths`: reported and within 1 percent of the last report; compared unrounded). Z6 and Z1 green; Z0/fit still red: rows 2734, candidates 2738.28 and 2736.02 |
| `green-on-fix-t3-r2` | the fix | t3 | **`Z_HOLDS`** with that reader |
| `green-on-fix-l1-r3` | the fix | l1 | Reader fixed again: the open's reply names the size as `width`/`height`, which the observer did not keep, and the page lays out for it first (about 17003; the paints at fit then report 16976 and 16990, inside the tolerance). With it Z0's candidates are 2733.77, 2738.28, 2736.02. **`Z_HOLDS`**: Chrome wide 37/37, narrow 6/6, DPR 2 18/18; Firefox wide 37/37, narrow 6/6; 0 paints in every quiet second |

The red run used the tool before the two reader fixes; its red cells are Z2 (covered and quiet), which those fixes do not touch. t3 was not
re-run after the second fix: it only adds the open's width to the candidates, and for t3 that is the one width there is (cadence rule 4).

Page sha256 prefixes: before the fix `08c474eaf969` (HEAD at the time), with the fix `0749bb918443`. Final tool `18049c3e031b`.

**One-off, not a gate** (`fit-narrow-on-fix/`): fable's probe `fit_narrow.py` (observer and state taken from the subagent's
`zoom_host2.py`, kept beside it) on a dist mirror carrying the fixed page, Chrome, l1 at the fit, no zoom press. Before the fix fable measured
780x600 blank (759 paints, 758 size changes, ink 0). With it: 780x600 2 paints, 1 size change, ink 82945 (`fit-780x600.png`, page and comment
sidebar painted); 784x600 2 paints, ink 84001; 770x600 2 paints, ink 79200.

Unit: `editor-shell-v2/tests/page-render-bands.test.mjs`, "0.2.56 hand test, item 1": red with the condition reverted to
`if (tile.documentSizeChanged)` (the page re-laid out on every report), green with the fix; the suite 586/586. Five page-test sandboxes take
the new helpers (`layoutTwips`, `sizeReportMovesLayout`).

Two mutation anchors in `tools/run_e2_c_product_path.py` moved with the lines they name (`ignore-a-document-that-grew`,
`caret-off-by-one-line`). Not this change's: four Writer mutations there (`paragraph-action-swallowed`, `paragraph-action-misrouted`,
`toolbar-drops-the-list-action`, `copy-lies`) already had no anchor on HEAD's page.

**Released (appended 2026-11-04 16:30):** frozen as shell generation 90 (`gen-90/`) and installed as host 0.2.57 (`../host-0.2.57/`), on the owner's word. On the host, the same l1 zoom is blank at 100-150 percent on 0.2.56 and painted at every step on 0.2.57, both browsers.
