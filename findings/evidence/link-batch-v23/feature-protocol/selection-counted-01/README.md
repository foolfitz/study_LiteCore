# Public selection collector, counted run 01: S1, S2, S3 and S4 PASS

The first qualifying execution of the public ABI6 selection collector over its complete declared population: 108 S1/S2/S3 source cells plus the 9 S4 interactions, once each in Chrome and in Firefox (234 cells). The run was launched detached (`setsid nohup`) at 2026-10-27 02:19 (+0800) from git HEAD `9309cdbc`; every file in the instrument's recorded closure is committed at that HEAD. It took 124 minutes and exited 0. Receipts: `commands.json`, `runner.command-output.txt`.

Run prerequisites recorded in `report.json`:

- `preRed` is the sealed historical counted-05 cohort, re-judged EXPECTED_RED by `check_pre_red` (`42b6a97b`).
- `foreignCpu.ok` is true.
- `postConfig` equals `config`.
- `preparationOnly` is false.

Independent aggregate reader, run immediately after with the same tree: `judge_v23_feature_selection.py report.json`, exit 0 (`aggregate-judge.stdout.json`).

| Group | Required | Observed | Verdict |
| --- | ---: | ---: | --- |
| S1 | 168 | 168 | PASS |
| S2 | 216 | 216 | PASS |
| S3 | 20 | 20 | PASS |
| S4 | 18 | 18 | PASS |

Aggregate PASS; `populationComplete: true`; all 234 cells PASS.

- **Table-selection members.** Exactly the five members, each in both browsers, took the A′ branch (`s1-table-selection-ruling/RULING.md`): `shift-Up@cell-end`, `shift-Down@cell-end`, `shift-Right@cell-end`, `shift-Down@list-mid` and `shift-Up@doc-end`.
- **Native-text agreement**, recorded but never asserted (review 01 item 1): 0 disagreements. Every S1 candidate's selected text equals all three native rounds, including the Up/Down members whose predicate has no native comparison.

Per the protocol's closure rule ("the first complete declared clean population and its artifact reader closes that feature group"), this closes S1, S2, S3 and S4 for `e2-editor-v23` ABI6 on the actual product page (`c25b11c4…`, shell generation 76). It says nothing about S5, R1, the product arms, 096 or the other named product inputs.

Raw cells are stored as deterministic `.json.gz` (58 MB), each verified equal to its original before compression and after decompression; the uncompressed originals are ignored. The preparation history that shaped this instrument is in `selection-prep-01` … `selection-prep-07` and `selection-review-01`.
