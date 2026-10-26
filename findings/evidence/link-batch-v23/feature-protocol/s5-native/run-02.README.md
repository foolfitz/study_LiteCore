# Native S5 type references, run 02 (superseded by run 03)

Executed 2026-10-27 06:49:47–06:56:40 (+0800), 6 min 53 s, runner exit 0, under fable ruling 3 (`../s5-type-oracle-ruling/RULING.md`) and the owner's in-session authorization to build and run long jobs. Harness build `type-build-01/` (binary `d0408e88…858b`, harness source `1ca67ef3…`), built in-session at 06:49 after `uptime` (load 0.45) and `pgrep -a make` (none). No browser measurement overlapped it. Command: `handoff/RUNBOOK-2026-10-26-v23-native-s5.md`, appended section, with `--out …/run-02`.

The 56 native-capable type cells ran once each. Per cell: fresh document, run-01's setup, Shift INPUT/UP, settle (800 ms quiet / 8000 ms cap), selection read, x INPUT/UP, settle, after-save.

## Why it is not the oracle

The reader (`read_v23_native_s5_type.py`) reported `NATIVE_S5_TYPE_SAVES_READ` with 0 run-level problems, but only 10 cells witnessed (4 `selection-before-x`, 6 `settle-only`). The other 46 read NE with one reason each: `between-read does not complete before the x post`. The harness printed doubles with the default six significant digits, so past 1000 ms the between-read end and the x post rounded to the same 0.01 ms (for example `shift-End@caret-mid/type`: 1141.75 and 1141.75). The reader's strict comparison was right to refuse equal values. The reading is preserved as `reader-02.precision-defect.json` (it was written as `reader-02.json` and renamed before any consumer bound it). The selection texts matched all three native rounds in all 56 cells; no other check failed.

Correction: `std::cout.precision(15)` in the harness (commit after `de68de56`), build `type-build-02/`, fresh run `run-03/`. Because the harness source changed, the current reader refuses to re-read run-02 (`changed bound input`); its sources are preserved in `type-build-01/source/` and at `de68de56`.

## What run 02 still shows

The saves are valid measurements of the settled sequence. `census_f166_native_type_order.py run-02` (finding 166): of the 52 cells whose offsets derive from setup names, 7 have the after-text "x typed over the pre-Shift shape", exactly the silent members whose Shift step moves nothing; no shape gives one after-text across its four Shift keys (run-01: 52/52 and 14/14). Settling the Shift step therefore restores Shift-then-x.

## Appended 2026-10-27: correction and status (fable ruling 3, Addendum 1)

The "past 1000 ms" account above is wrong as a description of which cells failed. Six significant digits give 1 µs resolution below 1000 ms and 10 µs above, and the true between-read-to-x gap is 0.26–0.74 µs (run 03), so the timestamp clause could not measure order in any cell: 4 of the 46 NE cells lie below 1000 ms, and 2 of the 10 "witnessed" cells lie above. The 10 `NATIVE_SAVE_AVAILABLE` cells in `reader-02.precision-defect.json` are rounding accidents, not witnesses. Status: superseded; instrument-NE 56/56 for the timestamp clause; bound nowhere. Run 02 vs run 03: before, after and between texts identical in 56/56.
