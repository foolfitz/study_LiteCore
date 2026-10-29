# F1: finding 171/172 scenarios on v22, v24, v25, with the engine's own record (2026-10-29)

Spec `specs/SPEC-M3-link-batch-v25.md` 6.3 F1, and 13 item 4 (the JSON serialisation of `dispatched` and `witness` is first measured post-link). Local mirror, no DDEV. Chrome, fresh browser per scenario, 3 repetitions.

## Tools

- `diag_format_v25.py` (new): imports `../../host-0.2.39/k-nine-cells/diag-format/diag_format.py` by path and does **not** edit it (its run-01/02 stay as produced; the report records its sha256). Same scenarios, observer, page read and ODT reading. Closed list of differences, in the docstring: (1) products -- v22 the 0.2.27 package as before; **v24 from its own bytes** (page `b15a6d8e` from git `b241c83a4`, the v24 archive's profile, shell generation 77) because `dist/` serves v25 since the cutover and `diag_format.py`'s "v24 = dist/ as served" would now measure v25; v25 as `dist/` serves it; both identity-checked file by file by `wasm_sdk_probe/tools/v25_f_products.py`; (2) the engine's record: after `ready`, `Target.setAutoAttach` reaches the page's worker and wraps its `JSON.parse` (observer only; same value returned; no served byte changes) to keep, per engine `error` / `editor-action-completed` event, whether `formatBarrier.dispatched` and `witness` are present and their values, and `stage`; (3) traffic rows add the reply's `completion`, `changed`, `witness`.
- Why (2) is needed: the v25 worker projects `dispatched` from the engine's field when it is a boolean, else from `stage` -- and v25 also moves `stage`, so a page-level `dispatched: true` cannot tell the serialised field from the fallback. Measured: v22's engine never sends `dispatched` (`hasDispatched: false`, `stage: awaiting-restore`) and its page still shows `true`, by inference. So the page level alone would not have measured 13.4.
- `v25_f_products.py` identity checks, each red on its own case before use (scratch mirrors, 2026-10-29): the "v24 = dist/ as served" trap -> `shellEqualsGeneration`, `pageServed`, `pagePointsAtProfile` false; v25's mirror judged as v24 and vice versa -> the same three false; one byte appended to the served v24 worker -> only `profileEqualsArchive` false.
- `read_f1.py` (new): the verdict, from `report.json` only. Clauses per run: B-pill, B-page, B-raw (engine `dispatched` present and true, `stage` not idle), F-cleared (`MKAFTERCLEAR` not italic), F-again (`MKITALAGAIN` italic), F-no-fail, F-raw (every set-* engine completion carries a known `witness`). `F1_HOLDS` needs v25 all true every run; v24 B-pill, B-raw, F-cleared, F-again false every run (each clause seen red on real data); v22 B-pill, F-cleared, F-again true every run; identities ok; every planned run present, none fatal. `--self-test`: eight in-memory mutations of the real report must each turn it red.

A shakedown on a scratch dir preceded run-01 (one repetition, the same result shape); it is not evidence.

## run-01 (15:24:13-15:33:35 +0800): **F1_HOLDS** (`read-01.json`, exit 0)

| Clause | v22 | v24 | v25 |
| --- | --- | --- | --- |
| B-pill (`ready` after the bullet) | 3/3 | 0/3 (`recoverable-error`) | 3/3 |
| B-page (projection `dispatched: true`) | 3/3 | 0/3 | 3/3 |
| B-raw (engine `dispatched` present, true; stage not idle) | 0/3 (not sent; inferred) | 0/3 (absent; `stage: idle`) | 3/3 (`awaiting-result`) |
| F-cleared (`MKAFTERCLEAR` not italic) | 3/3 | 0/3 | 3/3 |
| F-again (`MKITALAGAIN` italic) | 3/3 | 0/3 | 3/3 |
| F-no-fail | 3/3 | 0/3 (`LOK_COMMAND_FAILED`) | 3/3 |
| F-raw (engine `witness` present, known) | 0/3 (not sent) | 0/3 | 3/3 |

v25's bullet still answers `MUTATION_OUTCOME_UNKNOWN` (multi-block readback), exactly as v22 does; with `dispatched: true` the page stays `ready` instead of demanding a rollback. In the format scenario v25's set-* witnesses are `state-noop` for the requests that ask for the state the text already has and `on-time-item` otherwise.

`read-01-self-test.json`: base `F1_HOLDS`; all eight mutations `F1_RED` (engine `dispatched` removed, one engine `witness` removed, `MKAFTERCLEAR` italic, bullet pill `recoverable-error`, v24's counterexample "fixed", v25 identity not ok, one run dropped, no runs).

Identity (report `products`): v24 and v25 `ok`, all four checks true; v22 page `3b96cb16`.
