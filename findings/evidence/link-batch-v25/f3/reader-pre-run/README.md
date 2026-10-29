# F3 reader before any F3 run (2026-10-29)

`wasm_sdk_probe/tools/read_v25_f3.py`, the reader of spec v25 section 16, exercised before F3 ran, on inputs that need no browser:

- `v24-as-v25.json`: the baseline (v24 T4 run-02) given as the v25 run. `F3_RED`, exactly the six P cells (Chrome 4, Firefox 2), each `v24 X -> v25 X`. Counts per browser: Chrome P 4, no-regression 34, same-or-pass 4, excluded 4; Firefox P 2, no-regression 29, same-or-pass 11, excluded 4 (46 each).
- `synthetic-fixed.json`: the baseline with only the six P cells set to PASS (scratch copy, not a measurement). `F3_HOLDS`, the six listed as `improved`.
- `synthetic-fixed-self-test.json`: on that synthetic input, base `F3_HOLDS` and all seven mutations `F3_RED` (a v24-PASS check FAIL, a P cell NE, a same-or-pass cell moved NE -> FAIL, one check missing, one extra, an empty report, DISPOSITIONS without product rows).

The self-test runs again on the real F3 report after the run.
