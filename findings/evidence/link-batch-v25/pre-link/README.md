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

## Build mechanics step

- Makefile v25 block (v24's verbatim plus `-DOXSDK_E2_V25_FORMAT_PROOF`, v24 archive as base,
  `sdk/v25-feature-worker.js`, guarded link), `tools/check_v25_feature_contract.py`,
  `tools/build_e2_v25_feature_profile.py`, `tools/link_v25_feature_owner.sh` (owner-run; agent only
  `bash -n`), `tests/test_v25_feature_profile.py` (6 tests: exact successor, every other change named,
  v24 export list, v24 worker refused, wrong identity refused, build log needs the v25 define).
- **M1-1**: without the v25 carrier, exit 1 naming exactly E2_V25's `sdk_api.o`, `probe_engine.o`,
  `editor_api.o` (`m1-1-red-without-v25-carrier.*`); with
  `--carrier E2_V25=probe_engine,sdk_api,editor_api`, exit 0, 38 rules / 147 objects, E2_V25's three
  guard variants refused (`m1-1-green-with-v25-carrier.*`). 57 s each, one core.
- `ships.*`: `what_the_link_ships.py --since 1f95a9fca --variant link-batch-v25 --shipped-profile
  dist/profiles/e2-editor-v24`: only `probe_engine` changes (the declared hunks), the other three units
  identical; worker diff against the shipped v24 worker recorded.
- `static-tests.txt`: `make test-v25-feature-static` exit 0.
- v24's E1 now reads the source v24 was linked from (spec v25 section 13 item 2):
  `v24-static-live-tree-red-by-construction.txt` (before), `v24-static-on-linked-source.txt` (exit 0).
- `v24-archive-sha256sums.txt`: the v24 archive verifies 5/5. No `build/e2/editor-v25`,
  `dist/profiles/e2-editor-v25` or `build/link-v25-feature-01.log` exists before the link.
- `frozen-set-before.sha256`: every regular file under `dist/profiles/` and `build/archive/`.
