# Finding 117 diagnosis on v18 (no link): predictions D1-D4, before the run

Fable's ruling on 117 (`../review/fable-ruling-117.md`, section 1), confirmed by the owner on 2026-10-08 (option A, "adopt the ruling as a whole"). This file is committed before any run of the trace profile. Labels R0 and D1-D4 are this file's; D1-D4 follow the ruling's table.

## Instrument

- **Profile `e2-editor-v18-trace117`**, built by `wasm_sdk_probe/tools/build_merge_trace_profile.py` (not shipped). `probe.wasm` `ad3f68bb…`, `probe.js` `46b2f40a…`, `sdk-manifest.json` `456e9a72…` are v18's, verified against v18's archive by the tool. Only `sdk-worker.js` differs (`7a1c7ff7…`, archived in `wasm_sdk_probe/build/archive/e2-editor-v18-trace117-worker-7a1c7ff7/`). Its one added statement posts a `merge-trace` event for every engine event, stamped with the worker clock.
- **Runner** `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`, as committed with this file. The instrumented observer keeps a drained log on the page clock: the trace events, every paint (request rectangle, reply height, `documentSizeChanged`, and the page's own painted fraction), and every toast. `run_limit` attaches each press's window (from its key to the next press's quiet point); `run_case` attaches the key's window. Before this commit, the runner had only been run on `927e2863…`.
- **Reader** `read_trace.py` (this directory), written before the run. Self-test: 4 cases, `selftest-output.txt`. Red case: the shakedown's trace-less `../m2-shakedown/m2-4-chrome.json` STOPs (exit 3) instead of reading as "no callbacks"; recorded in `redcase-output.txt`.
- **Runs** (`chain.sh`, detached, Chrome only; the ruling says Chrome suffices because both browsers were identical): `--mode m2-4 --candidate-profile e2-editor-v18-trace117`, then `--mode m2-1b` on the same profile. Neither is counted (`BINDING` is None).

## Expected

- **R0. 117 reproduces on the trace profile.** Fast presses (`keyToUndoMs` < 1000): exactly 1, 3 and 55; the other 102 at or above 1990 ms. Exactly one toast. If R0 misses, the instrument changed the system it measures, and D1-D3 describe a perturbed run. Fallback: report R0's miss first. Then run plain v18 with the new runner, to separate the observer change from the worker change, before reading D1-D3.
- **D1. On a slow press, nothing arrives after the key.** On every one of the 102 slow presses, no `lok` event lies more than 5 ms after the key and before the completion. The key time is `tc - keyToUndoMs`, where `tc` is the worker time of the traced `editor-action-completed`. The positive control is built in: every press must carry exactly one traced completion, or the reader STOPs.
  - **If D1 misses, and the events are id 0 or any other id arriving well after the key:** the engine was told and still waited. A step was lost or read too early. This needs a second engine fix in the same v19 link, and it also touches the Escape and K2 stages, which are not polled. The design waits until the ids and offsets are read.
- **D2. Why presses 1, 3 and 55 are fast.** After the key:
  - press 1 has a STATE_CHANGED (8) whose payload starts with `.uno:Undo` (undo becomes available);
  - presses 3 and 55 have a DOCUMENT_SIZE_CHANGED (13).

  Basis (inference): 51,650 = 3 × 16,838 + 4 × 284 twips (three pages), 34,528 two pages, 17,406 one page. 107 paragraphs at about 52 lines per page, so the third page empties at press 3 and the second at press 55. The heights the paint replies report should go 51,650 → 34,528 → 17,406.
- **D3. The toast is press 55's, page-side.**
  - Exactly one toast, in press 55's window.
  - Exactly one paint in the whole run with a painted fraction below one half: press 55's, with `y` 0 and `h` 34,528. That is the stale two-page height the page still holds.
  - Its reply says `docH` 17,406 and `documentSizeChanged` true.

  The page throws on that strip before acting on the size change (`e2-editor-app.js:828-848`). Press 3's strip (51,650 asked of a 34,528 document, about two thirds painted) passes.
  - **If D3 misses with an unpainted strip that lies inside the document:** the cause is engine-side and joins the link (ruling section 3).
- **D4. The 628-633 ms typed-merge plateau is "nobody looked".** In each of M2-1b's 20 verified records, the first `lok` event more than 5 ms after the key arrives no more than 15 ms before the completion. The plateau is then the time to the first callback. If it misses (a callback arrives early and the completion still waits), it is a separate finding, and M2-2's margin stays as measured.

## Reading

`python3 -I read_trace.py m2-4-chrome.json --m2-1b m2-1b-chrome.json`. The verdict is the `VERDICT` line; exit 0 means every question HIT, 1 a MISS, 3 STOP. A miss is recorded as a miss, with the ids and offsets the reader prints. Not predicted, only recorded: the full list of ids after the key on the fast presses, and the latencies.
