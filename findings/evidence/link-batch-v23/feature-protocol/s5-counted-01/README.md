# S5 counted run 01: stopped at its first nonpassing cell

Launched 2026-10-27 07:31:09 (+0800) detached from HEAD `1e63f8de` by `../s5-counted-01.launch.sh` (receipt `commands.json`, runner output `runner.command-output.txt`). preRed EXPECTED_RED (counted-05), foreignCpu ok. It stopped at 08:05:24 (2054.5 s) after 106 Chrome cells, as a counted run must at its first nonpassing observation; no Firefox cell ran. Runner exit 1. The aggregate judge refuses the report (`aggregate-judge.stderr.txt`: no `postConfig`), as for any stopped run.

- 105 PASS: 98 against settled-WASM, 7 against native (one of them a type cell with `selection-before-x`).
- 1 FAIL: `shift-End@cell-end/backspace`, `sequence result differs from its reference`. Candidate and its settled-WASM arm saved `A1 cell tex`; the native reference (run-01, ruling 2) saved `A1 cell text`.

The FAIL is Writer's empty-mark behaviour (the first Backspace/Delete after a Shift that moves nothing deletes nothing), measured independent of timing by `../s5-native/diag-settled-01/` and reproduced in the product by `../s5-prep-04/`. Its classification is the subject of `../s5-silent-shift-deletion-ruling/`. Raw cells are `.json.gz` (`gzip -9 -n`); nothing here can be resumed.
