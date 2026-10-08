# The counted-M2 reader and its red cases (2026-10-08, before any counted run)

Handoff `HANDOFF-2026-10-08d-…` Next 1 and Next 2. Spec `SPEC-M3-paragraph-merge.md` §30.2, §31.2, §31.4 X7.

## What was added

| File | What |
|---|---|
| `wasm_sdk_probe/tools/judge_counted_m2.py` | The reader. One directory, per browser: M2-0, M2-1, M2-1b, M2-2, M2-3, the G01 barrier, M2-4 with §31.2, the M2-1 red case, the paired control. Exit 0 pass, 1 a FAIL, 3 nothing failed and something NOT DONE, 4 a full pass under `--uncounted` (never a counted verdict). Last line `VERDICT …`. Its docstring lists what it trusts and the decisions below. |
| `wasm_sdk_probe/tests/test_judge_counted_m2.py` | 32 tests: one green case (synthetic, see below) and its red cases, plus the five real §31.2 red reports. |
| `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py` | (a) `teardown()`: the browser is closed even when the last observer read fails (handoff Next 2; the orphaned Chrome of `diag-117/attempt1/`). (b) `limit_clauses` gains `latency` (§31.2), so the runner's M2-4 `pass` is no longer true on a report the criterion calls red. (c) `bound_values` gains `pageSourceSha256`, and `is_counted` lets the red case on v8 count when everything but the profile's own values (wasm, worker, repointed page) equals the binding; before, the red report compared v8's wasm with the binding and could never say `counted: true`. |
| `wasm_sdk_probe/tests/test_merge_wasm_clauses.py` | +10 tests: `latency` (at the bound, a missing number, the five v18 reports), `is_counted`, `teardown`. The teardown test was made red first: with the old order (read, then close) restored in place it ERRORs; restored, OK. |

## Decisions written down (in the reader's docstring as well)

- **The runner's M2-4 `pass` gets the §31.2 clause.** Rule x of the 10-08d handoff: a `pass: true` that the criterion calls red invites misreading. The reader does not read `pass` or `clauses` either way.
- **The reader recomputes every clause** from recorded fields and **every document comparison from the kept documents** against the native references. A kept document whose content hash or text verdict disagrees with what the report recorded is NOT DONE for that record.
- **The population is the reader's own:** `eshape.json` read directly, the two synthetic fixtures of §25, the decision → expectation table of §17/§22.1, the counts 20 / 5 / 1. The runner's `tool_cases` gives only the order (the red case's "first three") and must name the same cases.
- **M2-1 red:** "(109's refusal + reopen)" in §30.2 is taken as the clause: each case placed, refused, generation + 1. A case never placed is not a red.
- **The M2-4 control is not read:** §30.2 pairs a control with the counted run only.
- **A FAIL outranks NOT DONE in the exit code** (1 over 3): the verdict is not pass either way and the miss is the information. The VERDICT line names both.
- **Expected file names** the counted chain must write, per browser B: `counted-B.json`, `counted-control-B.json`, `m2-1b-B.json`, `m2-4-B.json`, `red-B.json`, each with its `.docs/`.

## The green case is synthetic

No counted report exists and no M2-4 report is green under §31.2. The test builds one in a temporary directory from real v18 reports, none edited in place: the tool-list shakedown (`../merge/shakedown-B.json`, `control-B.json`) with F01/F02 and the text-frame M2-0 dropped and round 1 copied as round 3; `../m2-shakedown/m2-1b-B.json` and `red-B.json`; and `../finding-118/p4-m2-4-fixed-B.json` **with every press's two latencies replaced by 40 / 140.5 ms**. Identity fields are normalised on every copy.

## Results (`selftest-output.txt`, `dry-run-v18-m2-shakedown.txt`)

- `python3 -m unittest -v tests.test_judge_counted_m2 tests.test_merge_wasm_clauses`: 70 tests, OK.
- The five §31.2 red reports (`../m2-shakedown/m2-4-{chrome,firefox}.json`, `../diag-117/m2-4-chrome.json`, `../finding-118/p4-m2-4-fixed-{chrome,firefox}.json`), each put into the green directory: exit 1, `VERDICT FAIL: ['<browser> M2-4']`, `'slow': 102`, `latency` not true. That includes the two reports whose runner `pass` was true.
- Dry run on the real `../m2-shakedown/` directory (`--uncounted`, profile v18): M2-1b, M2-2 (M2-1b's 40), the red case and M2-0 PASS; M2-4 FAIL on both browsers on `latency` and `noToast`; the counted run and its control NOT DONE (they do not exist). Exit 1.
- Two mistakes in my first test expectations, both fixed in the test and not in the reader: editing the instrumented side's document or toasts also turns the paired control red (that is what the pair compares); and C01's and C02's documents are the same text (Delete at the end of a paragraph, Backspace at the start of the next), so the control red case now copies C08's.

## Not done here

- No review yet (handoff Next 4). No counted run, no binding. The reader has not met a real counted report; its first one will be the counted chain after v56 and the v19 link.
- The runner change has not been run in a browser (the `teardown` path and the new `bound` key are unit-tested only).
