# S5 preparation 04 (uncounted): silent-Shift deletion cells

Chrome then Firefox, six cells each, runner exit 0 (`--keep-going`), 2026-10-27 08:44–08:50 (+0800); output in `runner.command-output.txt`. Raw cells are `.json.gz` (`gzip -9 -n`). Run after `../s5-counted-01/` stopped, to measure what the product does where Writer's first deletion after a no-movement Shift removes nothing.

| Cell | Chrome | Firefox | Candidate removed | Native removed |
| --- | --- | --- | --- | --- |
| shift-End@cell-end/backspace | FAIL (native) | FAIL (native) | 1 | 0 |
| shift-Right@doc-end/backspace | FAIL (native) | FAIL (native) | 1 | 0 |
| shift-Left@range-one/backspace | FAIL (native) | FAIL (native) | 1 | 0 |
| shift-Home@empty-para/delete | PASS (settled-WASM; no single-line witness) | PASS (same) | 1 | 0 |
| shift-End@doc-end/backspace-twice | FAIL (native) | FAIL (native) | 2 | 1 |
| shift-Left@doc-start/delete | FAIL (native) | FAIL (native) | 1 | 0 |

Every FAIL is the same difference: the product deletes one character more than Writer. Where a settled-WASM arm ran, it equals the candidate. Decision requested in `../s5-silent-shift-deletion-ruling/BRIEF.md`.
