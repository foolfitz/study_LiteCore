# T5: table2 with real keys — typed `x` and Ctrl+V `x`, 3/3 per browser

Spec `specs/SPEC-M3-link-batch-v24.md` §6.3 T5 (ruling 1 T5); default if not done or NE: no counted S5. Runner `wasm_sdk_probe/tools/run_v24_t5.py` (new). Written and committed before the first run.

Both arms use the v24 harness page and plan, the readiness check, a fresh document and the Table 1 shape of `shift-Right@cell-end` (caret at A1's text end, a real Shift+Right selecting A1's tail and B1), then differ only in how `x` arrives. Each repetition is a fresh browser; nothing is retried.

| Arm | How `x` arrives | Expected save (A1 / B1, paragraphs 8 / 9) | Expected wire |
|---|---|---|---|
| typed | a real `x` key: CDP `Input.dispatchKeyEvent` (Chrome) / WebDriver key actions (Firefox), via v23's unchanged `run_s5` — not `commitText` | `""` / `"x"` (native keyboard, run-03) | one `insertText`, `route: "uno-insert-text"`; reply `method: "uno-insert-text"`, `completion: "uno-command-result"` |
| paste | `x` written to the clipboard before the document opens (`tools/v21_clipboard.py`: Chrome `Browser.grantPermissions`, Firefox pref `dom.events.testing.asyncClipboard`), read back equal; then a real Ctrl+V after the Shift+Right answered | `"A1 cell textx"` / `"B1 cell textx#"` (finding 169 on the unchanged paste route) | one `insertText`, `route: "paste"`; reply `method: "paste"`, no `completion` |

A repetition PASSes only if: the original save equals the fixture; every paragraph other than A1/B1 is unchanged; the sequence window's non-modifier keydowns are exactly `ArrowRight`+Shift then `x` (typed) or `v`+Ctrl (paste), all trusted; exactly one `insertText` with text `x` and the row's wire above; and A1/B1 as above. T5 holds if all 12 repetitions PASS and the plan did not drift. The typed arm is also read by the v24 S5 reader (`s5Inspection`), as a cross-check, not as T5's rule.

The paste arm is the control of the fix's scope: it shows the paste route is still Writer's paste (append, plus 169), i.e. v24 changed typing, not pasting (ruling 1: the fix is not option B).
