# Item-2 runner witnesses (§34.4), development runs before the smoke

These are two development runs of `wasm_sdk_probe/tools/run_v21_shakedown_item2.py` in Chrome, under the S-9 lock (`lockTakenAt` in each report), N=1, with `--limit 2` and `--only` (so the judge refuses them as development reports). They were started by the first item-2 agent, which ran out of context; its successor commits them here **before** fixing the runner (§34.4: witness first). Neither is evidence, and neither was judged.

| file | runner as it ran | note |
|---|---|---|
| `dev-r1-report-chrome.json` | `runnerSha256` `46fa600b…`; that text is not recoverable [observed: no copy exists] | started 00:24, never completed (`completedAt` null) [observed] |
| `dev-r2-report-chrome.json` | `runnerSha256` `68e7d197…`; not recoverable either. `runner-629fd436-after-dev-r2-start.py.txt` is the runner file as it stood 13 s after dev-r2 started (mtime 00:59:49 against `startedAt` 00:59:36), the closest text that exists [observed `stat`] | completed 01:23 [observed] |

## What the runner lost (runner faults, each counted once in the tally)

| # | run | lost | cause | fix |
|---|---|---|---|---|
| 1 | dev-r1 | M4 `M4-P6-M1`, `M4-T1-P10-M1`, `M4-T1-P8-M5`: `StopIteration` | a runner bug in the M4 arm as it ran [observed: the exception]; the exact line is not recoverable (runner text lost) | fixed by the first agent before dev-r2 [observed: the same ids run in dev-r2 without it]; no witness was committed then, so it is committed now, late |
| 2 | dev-r1 | M9 ran on the wrong fixture | `fixture_odt` matched by suffix, and `header-protected-section.fodt` also ends in `protected-section.fodt` [source: the docstring of `fixture_odt` in the runner file kept here] | fixed by the first agent before dev-r2 (exact name match) |
| 3 | dev-r1, dev-r2 | dev-r1: M10b, M10c, M10d (`TimeoutError` 180 s); dev-r2: M9 clean and dirty, M10b and M10c, M11 cancel, the record arm, the trace arm's M10 preconditions, M8-v20 (`TimeoutError` 180 s, then "a JavaScript dialog was open when the next instance began", type `beforeunload`) | leaving a page with unsaved work raises the page's own beforeunload prompt (finding 107's guard), and headless Chrome waits on it; item 1 met the same (`../witness-item1/`). dev-r2 carried the first agent's attempted fix, a capture listener calling `stopImmediatePropagation` before navigating (`DISARM_LEAVE_GUARD`); it did not stop the prompt [observed: 4 `beforeunload` dialogs recorded in dev-r2's `javascriptDialogs`] | the runner answers the prompt itself during navigation, as item 1's runner does: Chrome `Page.navigate` sent without waiting, `Page.javascriptDialogOpening` answered with `Page.handleJavaScriptDialog {accept: true}`, and every load records `leaveDialogAccepted` |
| 4 | dev-r2 | M4 `M4-T1-P11-M1`: the drag selected `' text'` instead of the native `'A1 text\tB1 text\n'` (judged NOT_ESTABLISHED by the M4 rule); M10d the same | the drag ended at the end caret's x **minus** 1 px; when the end caret is at the start of cell B1 that point lies left of B1's text, inside A1, so the selection never crossed the cell [inferred from the drag's points in the report: from x 366.0 to x 576.5 at the same y, and the readback] | the drag ends 1 px right of the end caret, inside B1's text, as ARMS-item2 M10d says ("from inside A1's text to inside B1's text") |
| 5 | dev-r2 | M5: every item (`StopIteration`) | with `--limit`, the M5 items were looked up in the shortened M3 list [observed traceback]; a development-mode fault only | the M3 entry is looked up in the full population |

## What these runs did show (development data, not evidence)

- M1 (5 items), M3 (2 items per route and both positive controls), M6, M7a, M7b, M4 `M4-P4-M2` and `M4-T2-sec-M2` completed in dev-r1 as the arms predict [observed].
- **SDK-L** (65,536 bytes of one CJK paragraph through the page's `DocumentHandle`) answered `WORKER_CRASHED` ("Uncaught [object ErrorEvent]"), and **ENG-65536** (the same bytes posted to the worker) got no answer within 60 s, in dev-r1 [observed]. M6's 65,536-byte corpus of round-1 sections completed in the same run (busy to ready 628 ms) [observed]. Whether this is the product is for the smoke to show; it is not a runner fault.
- The trace pass saw LOK ids 0, 1, 8, 13, 14, 35, 48, 73 during the 64 KiB paste and **no id 70 (`CORE_LOG`)** in dev-r2 [observed `lokIds`]; the instrument sees other ids, so the zero is not an instrument that saw nothing [inferred].
- M5's positive control crossed the proxy: the worker's `probe.wasm` GET to the mirror port, and the observer's `/m5-control` request appeared both in the proxy's log and at the 18765 listener [observed dev-r2].
