# v25 pre-link evidence (SPEC-M3-link-batch-v25 6.1), engine step

Engine edits (all under `OXSDK_E2_V25_FORMAT_PROOF`): `src/editor_api.h` guard,
`FormatStateBarrier.dispatchRecorded/dispatched`, `appendFormatBarrierDetails` emits `dispatched`,
`ordered_format.inc` sets `AwaitingResult` before the post and records `dispatched` in the reply,
`ordered_engine_reply.inc` `orderedInlineFormatWitness` + `witness` in the success reply.

- `native-tests.json` (`native_receipt.py`): `tests/test_ordered_format_v25.py`, original green and
  every mutation red with the expected FAIL lines -- 171: v24-behaviour (D1 dispatched, D1 stage,
  D2), stage-not-advanced (D1 stage), dispatched-always-true (D2), record-skipped (D1, D2, success);
  172: noop-ignores-cache (R2), noop-removed (R1, strikeout no-op), result-ignored (uno-success
  cases). R1 also asserts the shipped v23/v24 gate refuses the same no-op. Existing
  `tests/test_ordered_format.py` stays green. Not covered here: the JSON serialisation of
  `dispatched`/`witness` (lives in probe_engine.cpp; covered post-link by F1/F2).
- `v0-v25.json` (`v0_preprocess.py cd60b7d61`): **V0_V25_HOLDS**, eight v23/v24 objects preprocess
  identically to the pre-edit commit. `v0-v25-positive-control.json`: one injected shared token
  makes exactly the two probe_engine rows differ.
- `s-v25.json` (`s_syntax.py`): **S_V25_HOLDS**, four sources clean with the v25 define; a
  v25-only error is caught with the define and invisible without it; the v25 define without v24
  hits editor_api.h's #error. Run 01 (`s-v25-run01-wrong-control-tu.json`) aimed the last control at
  probe_engine.cpp, which does not include editor_api.h, so it stayed green: the control was wrong,
  not the guard (v24's guard has the same single include site). Fixed-by-execution: 1.

All runs pinned to one core (`taskset -c 0`), load 0.4-0.7, no make running.

## Worker step

`sdk/v25-feature-worker.js` = archived v24 worker (`41041fe7...`) + `tests/v25-worker-delta.json`
(items 1 dispatched from the engine, 2 witness set + forwarded, 3 profile term, 4 header).
- `w1-delta.txt`: **W1** byte-for-byte; a copy with one extra line outside the list fails (run by
  hand with `V25_W1_WORKER` pointing at the copy in the scratchpad).
- `w2-worker.txt`: **W2** in a vm sandbox: engine boolean wins over stage, stage fallback for
  engines without it, known witnesses forwarded, others null; three causal controls each turn it red.
