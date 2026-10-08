# Finding 117 diagnosis on v18 (no link): result

Predictions: `PREDICTION.md` (committed in `b1b67b9c`, before any run). Reader: `read_trace.py`, written before the run; its output is in `reader-output.txt`.

**VERDICT R0 HIT, D1 HIT, D2 MISS, D3 HIT, D4 HIT** (reader exit 1, because D2 missed).

## What ran

- **Chain:** `chain.sh`, launched detached at 2026-10-08 12:05:50 +0800, runner `0e00aa4cffa5e92a` at chain start and end.
- **Profile:** `e2-editor-v18-trace117`. `--check` passed before and after every run (`profile-check*.stdout.txt`). Worker `7a1c7ff7…`; wasm, loader and manifest are v18's.
- **Page:** the cutover source repointed at that profile, page sha256 `638dc618ab71b59b…`. It differs from v18's `cfc8ba1d…` only by the worker URL.
- **Neither run is counted** (`"counted": false`).
- **M2-4** (`m2-4-chrome.json`): 12:05:50-12:10:52, exit 0, empty stderr.
- **M2-1b, first attempt** (`attempt1/`): it lost its CDP connection at its 5th record (`ConnectionClosedError: no close frame received or sent`). The ps snapshot taken at its end shows `kscreenlocker_greet` started that same second (12:11:34). The first 4 records are `verified-key-undo`; records 5 to 20 are `runner-error`. The runner's `finally` then raised on its `observerAtEnd` read, before `session.close()`; the test Chrome was gone when checked. Kept as is and not read for D4.
- **M2-1b, rerun** (`chain-rerun.sh`, same runner, profile and command; `m2-1b-chrome.json`): 12:13:17-12:15:56, exit 0, empty stderr. All 20 records `verified-key-undo` and `pass: true`.

## R0: 117 reproduces on the trace profile (HIT)

- Fast presses are exactly 1, 3 and 55 (`keyToUndoMs` 37-38). The other 102 are 2000.
- Runner latency: median 2095.3 ms, max 2097.8 ms, against 2095.4 and 2098.1 in the shakedown's `m2-4-chrome.json`.
- One toast. `noToast` is the only false clause. The final document equals native press 105, both reduced bytes and text.
- The instrument did not change what it measures.

## D1: on a slow press nothing arrives after the key (HIT)

- **Slow presses.** On all 102 of them, no `lok` event lies between key + 5 ms and the completion. In that window the trace holds only the page's repaint requests answered `BUSY`: 1,734 `error` events, about one every 120 ms, which is the page's retry budget. No other engine event appears.
- **Positive control.** Every press carries exactly one traced `editor-action-completed`. On the three fast presses the trace does show post-key callbacks: about 36 ms after the key, 1 ms before the completion.
- **Read with the engine source.** `feedMergeAttribution` queues a step on any callback once `afterKey` is set. No callback came, so no step was queued, and only `handleMergeDeadline` read `.uno:Undo`, at 2000 ms.
- **No step was lost.** The ruling's "id 0 arrives and the press is still slow" did not happen. Writer emits nothing at all after deleting a blank paragraph among blank paragraphs: no tile invalidation (nothing visible changed), no cursor (it did not move), no state.
- **Consequence (ruling section 1):** polling the key stage alone is the fix, and no second engine fix rides v19.

## D2: why 1, 3 and 55 are fast (MISS on press 1's payload)

Callbacks after the key, with offsets from the key:

| Press | Events | Offset |
|---|---|---|
| 1 | STATE_CHANGED `.uno:ModifiedStatus=true` | +36.0 |
| 3 | INVALIDATE_TILES `0, 0, 12473, 51649, 0, 0`, then DOCUMENT_SIZE_CHANGED `12474, 34528` | +36.5, +36.6 |
| 55 | the same INVALIDATE_TILES, then DOCUMENT_SIZE_CHANGED `12474, 17406` | +35.7, +35.9 |

- The prediction said press 1 would show `.uno:Undo`. It shows the document becoming modified instead. **That is recorded as a miss.**
- The kind held: each fast press is one where something observable changed. For press 1 that was the modified flag; for presses 3 and 55, a page disappeared.
- The page arithmetic held as predicted: 51,650 → 34,528 at press 3, 34,528 → 17,406 at press 55.

## D3: the toast is press 55's, page-side (HIT)

- **The toast.** Exactly one toast, in press 55's window. Exactly one paint in the run has a painted fraction below one half, and it is press 55's: `y` 0, `h` 34,528 (the stale two-page height), `rows` 2,007, reply `docH` 17,406, `documentSizeChanged` true, painted 0.47.
- **Not predicted, measured.** After that toast the canvas is never re-laid out:
  - canvas rows by document height: 3,002 at three pages, 2,007 at two pages;
  - all 100 later paints (presses 56-105) ask for 17,406 twips into the same 2,007 rows;
  - a one-page canvas would be about 1,012 rows (2,007 × 17,406 / 34,528).

  The throw comes before the page reads `documentSizeChanged` (`e2-editor-app.js:839` against `:849`), so the size change is lost with the strip. **Inference, not looked at on screen:** the page then shows a one-page document drawn about twice as tall as it is. The same order is in the shipped page (`dist/e2-editor-app.js:824` against `:834`).

## D4: the typed-merge plateau is "nobody looked" (HIT)

- **Engine latency:** `keyToUndoMs` 627-629 in all 20 records. Runner latency 728.0-761.2 ms.
- **The first callback.** In every record the first `lok` event after the key comes 626.5-628.5 ms after it, and the completion follows within 1 ms. In all 20 records the post-key sequence is the same two events, `.uno:DocumentRepair=true` then `.uno:Undo=enabled`. Before them, the window holds only BUSY repaint replies.
- **What emits them at about 628 ms is not looked at** (ruling: do not guess). What matters here: the record was there earlier and nobody read it.
- **v19 prediction:** with polling, Y01 and Y02 drop near the untyped 28-49 ms range.

## What this decides (ruling section 1, table)

- **v19 change set:** the key-stage poll only, plus the v19 Makefile rule and M1-1 plumbing. D1 found no lost step.
- **The toast and the stale canvas:** a page fix, own finding (118), verified on v18 before v56. The same code ships on v8.
- **D2's miss** changes nothing downstream. The ruling only used D2 to confirm "state changes are what wake the engine", and they are.

## Correction, 2026-10-08: "exit 0" above is not a recorded exit code

`chain.sh` and `chain-rerun.sh` log `exit=$?` after a `$(ts)` substitution, so their `exit=0` lines always say 0 (see `../m2-shakedown/RESULT.md`, correction of the same date). Proof that they mean nothing: `attempt1/`'s M2-1b ended in a traceback, and its line still says `exit=0`. For M2-4 and the M2-1b rerun, what is recorded is an empty stderr and a report with `completedAt`. The reader's exit code (1) was taken directly by `read_trace.py ...; echo exit=${PIPESTATUS[0]}`, with no substitution in front, so it stands (`reader-output.txt`).

## Correction, 2026-10-08 (found by the handoff draft's re-reading): two sentences above say more than was measured

1. **"Writer emits nothing at all after deleting a blank paragraph"** (D1 section) is stronger than the instrument. The trace profile reports what reaches the engine's `onLokCallback`, which is downstream of LOK's own `CallbackFlushHandler`. Measured: **no callback reached the engine** after the key on the 102 slow presses. Whether Writer emitted nothing or the flush handler removed what it emitted is **not separated** by this instrument. The fix (polling the key stage) does not depend on which; the de-duplication hypothesis of the 10c handoff was neither confirmed nor refuted.
2. **"the test Chrome was gone when checked"** (What ran, M2-1b first attempt) is wrong. The check looked at the first lines of a `grep chrome`, which listed the owner's own Chrome. The test Chrome (headless, PID 1849812, `--remote-debugging-port=39999`, started 12:10:53) stayed alive: it is in `attempt1/m2-1b-chrome.ps-after.txt` and in the rerun's `m2-1b-chrome.ps-before.txt` and `ps-after.txt`. It was found at about 12:21 and killed by PID by the main session (session record, not in git; `ps -p 1849812` afterwards printed nothing). The rerun therefore ran with an idle orphan alive; no effect on the rerun was looked for. Cause: the runner's `finally` reads `observerAtEnd` before `session.close()`, and that read raised when CDP was gone.
