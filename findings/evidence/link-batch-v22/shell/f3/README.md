# F3: finding 152's typing cells on the v22 page (SPEC-M3-link-batch-v22 §11.3), 2026-10-19 11:57–12:13

Tool: `wasm_sdk_probe/tools/diag_v21_dirty_move.py`, no `--fix`: the page's own fix 3, from the tree. Every report's page check:
- served `3b96cb16…`, `matches` and `identityOk` true;
- profile `e2-editor-v22`, wasm `f7a40bcc…`;
- HTML source `b9c2b975…`: the tree HTML with finding 154's rule.

Chrome 151, Firefox 157, headless. The commands are in `*.cmd`.

**F3: PASS.** All eight cells are 3/3: V5@0 ms, V5@300 ms, V11c and V11d, in both browsers. Every round:
- `outcome: done`;
- `insertTextAfterZ: true`, i.e. the typed Z produced a `beforeinput` `insertText`;
- the saved document holds Z, then Y and X: `ZYXAlpha first paragraph`, or `Bravo ZYX paragraph` for V11d, whose caret is in P2.

The reading is in `f3-reading.txt` (`python3 -I`). V5@0 ms is the cell fix 3 had never been measured on; it is 3/3 in both browsers.

## Three runs, and why each cell comes from where it does

Each cell is read from the report in which its variant ran its own procedure. No cell was re-run because of a product result. The two re-runs were forced by two faults in the tool addition that F3 itself required, which was to let V11c/V11d run in Firefox. Ruling 5 item 10 asked for a witness run, and these two faults are what that witness run found.

| run | reports | what it measured |
|---|---|---|
| 1 (11:57–12:04) | `run1/` | V5 correctly. **V11c/V11d went to `round_move`** (the v1–v4 dirty-move path: Z, Ctrl+End, Q), because the variant dispatch read `CHROME_ONLY` and the binding had just taken v11c/v11d out of it. Their summaries have no `insertTextAfterZ` |
| 2 (12:05–12:10) | Chrome `report-chrome-20261019T120543.json`; Firefox `run2-firefox-v11d-no-clipboard-prefs/` | After the dispatch fix (`V11_ROUNDS`). Chrome V11c/V11d correct. Firefox V11c correct (it does not paste). **Firefox V11d: `step-error` 3/3, "input-mismatch: the textarea holds {utf8: 0}"**: the tool gave Firefox its clipboard prefs only when `v5` was among the variants |
| 3 (12:11–12:13) | `report-firefox-20261019T121100.json` | Firefox V11d after the prefs fix: correct |

§34.4: **repaired because of execution +2**. Each repair has its witness committed here: the run-1 reports, and the run-2 Firefox report. The fault was in the main session's own addition to the tool, and the first execution caught it.
