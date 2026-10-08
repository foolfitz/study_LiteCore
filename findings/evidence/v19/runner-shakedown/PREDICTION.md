# Shakedown of the reviewed merge runner, on v18, before shell generation v56 (2026-10-08)

Uncounted. Committed before the run. What it is for: the review of 2026-10-08 (`../review/DISPOSITION.md`) changed what the runner records — `toastsAtEnd` after the last save, `reopenedDocument.sha`, three new bound values, `teardownError`, the pair's comparison and exit code — and all of it is unit-tested only. This round puts each new field through a real browser once, on v18 (which has no 117 fix), with the cutover page as it is in the tree (the 118 fix; `web/e2-editor-app.js`), so that the first browser run of these fields is not a counted one.

Runner: `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py` at the commit that adds this file. Chain `chain.sh` (detached; rc captured first; `ps` snapshots around each step). Per browser, Chrome then Firefox:

1. `--cases C01,C15,C29,Y01` (shakedown mode, 1 round): one plain merge, the `keyPosted:true` refusal, a `nothing-selected` refusal, one typed merge.
2. The same with `--control`; then `--pair` of the two.
3. `--mode m2-4`.

Reader `read.py`, written before the run: exit 0 every prediction HIT, 1 a MISS, 3 a report missing or unreadable.

| # | Prediction |
|---|---|
| R1 | In step 1, all four cases `pass: true`. C01 and Y01 `verified-key-undo`, with `toastsAtEnd` exactly two strings of the form `已存出 N KB`. C15 `refused` / `key-deadline` / `keyPosted:true`, and C29 `refused` / `nothing-selected` / `keyPosted:false`. For each refusal, the window's toasts are the ordered start/end pair with one lead, and `generation[1]` is `generation[0]` + 1. `reopenedDocument.sha` equals the content hash of the kept `*-reopened.odt`. |
| R2 | `--pair` exits 0: 4 pairs, `sameOrder: true`, `differ: []`. |
| R3 | M2-4: 105 presses, each `verified-key-undo`. `latency` is false, because v18 has no 117 fix (expected about 102 presses ≥ 1000 ms). `noToast`, `noToastThroughSave`, `finalBytes` and `finalText` are true, and `toastsAtEnd` is exactly one `已存出 N KB`. `pass` is false, on `latency` alone. |
| R4 | Every report (6): `bound` has exactly the nine `BOUND_KEYS`, each a 64-hex string. `counted` is false. No `teardownError`, and no `error` in `observerAtEnd`. Every stderr is empty, every step exits 0, and no test browser is left afterwards: after each step no process has `--remote-debugging-port=`, `geckodriver` or `-marionette` in its command line (`<step>.ps-after.txt.test-browsers` empty; the owner's own Chrome and Firefox have none of these). |

If a step dies with a traceback, its report is NOT MEASURED for the predictions it carries, and the test browser is looked for and killed by PID before the next run (rule y). The orphaned `serve.py` of `../../v18/diag-117/attempt1/` (PID 1849783, port 48085, alive 3 h 29 min) was killed by PID before this file was written.
