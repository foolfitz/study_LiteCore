# v18: shakedown of the new merge-runner modes (spec §30.2), before the run

Uncounted. `BINDING` is None (spec §7 / §30.1: bound only after shell generation v56 is frozen), so every report says `"counted": false` whatever its mode. Its purpose: show that M2-1b, M2-4 and the M2-1 red case run end to end, and give the adversarial review real reports to read, before the cutover chain. Nothing here satisfies a criterion.

Runner `tools/run_merge_wasm_shakedown.py` at `e62ddec4` (sha256 prefix `927e2863091c3208`; recorded again at chain start and end). Page: the cutover source repointed by the runner (v18: `cfc8ba1d…`; v8: whatever `repointed_page` gives for `e2-editor-v8`, recorded). Labels S1-S5 are this file's.

## Order (`chain.sh`, one tool at a time; Chrome, then Firefox)

Per browser: `--mode m2-1-red --candidate-profile e2-editor-v8`; `--mode m2-1b --candidate-profile e2-editor-v18`; `--mode m2-4 --candidate-profile e2-editor-v18`; the same with `--control`; `--pair` of the two M2-4 reports.

## Expected

- **S1 (M2-1 red case, v8).** Boot `ready`. The schedule is C01, C02, C03, one round each. None of them is `verified-key-undo`: each is `refused` (v8's worker has no B; finding 109's refusal and reopen), generation +1, and every case has `pass: false` (its expectation is `verified-key-undo`). If v8's page does not boot or a case is `placement-mismatch`, the red case did not run, which is a miss, not a red.
- **S2 (M2-1b, v18).** The schedule is Y01, Y02 alternating, 10 rounds: 20 records per browser. Every one is `verified-key-undo`, `restorePresses` 0, generation unchanged, no toast, after-key and follow paragraph text equal to native, `pass: true`. Latency, from the uncounted runs on v16-v18 (where typed-merge was the slowest M2-1 case at 729-760 ms):
  - runner-measured 700-800 ms;
  - engine `keyToUndoMs` 600-660 ms.
  - Expected refusals and reopens: 0 of 20. A refusal here would be §13.3's "LOK busy -> refusal + reopen", which M2-1b exists to measure; it would be recorded as found, not explained away.
- **S3 (M2-4, v18, instrumented).**
  - M2-0 on `undo-limit-105.odt`: reduced `content.xml` equal to native `original.odt`. This is my expectation: synthetic fixture, standard fonts; not measured before.
  - Placement at (1791, 1418, 0, 276) succeeds.
  - All 105 presses are `verified-key-undo`, comment `Delete paragraph`, `restorePresses` 0.
  - `actionsAfter` = n for n <= 100, then 100: WASM's undo limit is the same default 100 as native (`Common.xcs`, read for native; inference for WASM).
  - Generation unchanged, no toast.
  - The final document's reduced `content.xml` and paragraph text equal native press 105 (2 paragraphs).
  - Runner latency per press under 300 ms. The run takes 1.5-3 minutes: 0.5 s of quiet before each press.
- **S4 (M2-4 control).** The same final document, generation unchanged, no toast. The instrument-only clauses are NE. `--pair`: 1 pair, 0 differ, with 1 after-key document compared on each side.
- **S5.** No `runner-error`; every stderr is empty; Chrome and Firefox alike.

## Reading

By hand from the reports, with numbers. A reader for the counted M2-0 to M2-4 is written after the review, before the counted runs, and is not this file's. A miss is recorded as a miss. Before any fix, look at what the engine and the page did (a refusal's `code` and `mergeKey`, the presses around a stop).
