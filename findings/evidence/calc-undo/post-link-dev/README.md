# Smoke runs on the development v4 profile (before any freeze)

Mirror of the `web/` Calc page with `build/ods/editor-v4/profile` mounted (both tools alias the page's worker URL), 2026-11-03 ~16:40.

| Run | Result |
|---|---|
| `run_calc_editor_browser.py --profile build/ods/editor-v4/profile --repeats 1 --out cell-v4` | `pass: true`, Chrome 31/31, Firefox 31/31: the existing cell operations hold on the new engine |
| `check_calc_undo.py` (the U-probe, unedited; imported with `ENGINE` set to the development profile), `u-probe-v4` | Both browsers: U1 the page offers 復原 and 重做; U2 Ctrl+Z after committing `UNDOME` in D9 sends `undo` and the saved file has D9 empty (v3, `run-calc-undo-03`: still `UNDOME`); U3 Ctrl+Z after Ctrl+B and the file's weight is gone (v3: still `bold`); U4 Ctrl+Z mid-entry in the formula bar is still the browser's text undo; U5 a raw `undo` with the probe's string request id now passes the worker and is refused by the engine's C entry (`INVALID_ARGUMENT`, a number is required), where v3's worker refused it as unsupported |

These are smoke runs, not the CU criteria (spec 4.5, 6), which want their own tool, red on v3 first.
