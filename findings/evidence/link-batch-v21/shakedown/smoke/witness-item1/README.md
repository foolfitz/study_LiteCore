# Item-1 runner witnesses (§34.4), development runs before the smoke

These are development runs of `wasm_sdk_probe/tools/run_v21_shakedown_item1.py` in Chrome, under the S-9 lock, before the smoke. They are kept because the runner lost honest arms in them; the fix came after this commit (§34.4: witness first).

| run | what was lost | cause | fix |
|---|---|---|---|
| `dev2-report-chrome-d2p-d11b-d11a-d12-d11c.json` | d11a, d12, d11c: `TimeoutError: timed out in 180.0s` in `Page.navigate` | d11b's dirty round left the page with unsaved work; the next navigation raised the page's own beforeunload prompt (finding 107's guard, `web/e2-editor-app.js:130-134`, `:149`) and headless Chrome waited on the dialog [inferred from the hang's place, `Page.navigate`, right after the only round that leaves the page dirty] | attempted in `dev3`: a capture listener calling `stopImmediatePropagation` before navigating |
| `dev3-report-chrome-d11b-d11a-d12-d11c.json` | the same three arms, the same timeout | the attempted fix did not stop the prompt [observed: the same hang at the same call]. `dev3-runner-as-run.py.txt` is the runner as it ran | the runner answers the dialog itself: Chrome `Page.navigate` is sent without waiting, `Page.javascriptDialogOpening` is answered with `Page.handleJavaScriptDialog {accept: true}`, and the report records `leaveDialogAccepted` |

What these runs did measure is not discarded: d2p and d11b completed in `dev2` (and d11b again in `dev3`); they are development data, not evidence.

## The D2 wrapper misjudged an honest run (smoke, 2026-10-17)

| run | what happened | cause | fix |
|---|---|---|---|
| `d2-nohost-v21-chrome-20261017T014754.json` (the D2 no-host predictor smoke on page v21) | verdict FAIL "no move-document-start request: the key did not reach the action", while the Backspace was a boundary no-op (`waitedMs` 2257, revision 0→0) and the saved text equalled the opened document's | the wrapper read the Ctrl+Home move from `probe_10_14n`'s `summary.editorResponses`, but the probe's `arm_backspace` summarises the instrument log only from the Backspace on (`start = LOG_LENGTH` is taken after `to_start`, `probe_10_14n.py:397`, `:400`), so the move is never in that window [source]. The run is honest; the wrapper's reading was wrong. `d2-wrapper-as-run.py.txt` is the wrapper as it ran | the wrapper keeps the probe's whole instrument log (`log_from(session, 0)`) and reads the move from it; the self-test gains the case "the move only before the Backspace window" |
