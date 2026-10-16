# D2's no-host smoke (Chrome, N=1): development runs, NOT evidence

`wasm_sdk_probe/tools/run_v21_d2.py --mode nohost --smoke` (ARMS-item1.md D2, ruling D-1 B: the no-host predictor before the freeze; the host run after the freeze is the criterion and is not run in phase B). The probe `probe_10_14n.py` is imported unchanged; the wrapper adds the save, the comparison with the opened document, and the positive control.

| file | page | outcome (smoke) |
|---|---|---|
| `d2-nohost-v21-chrome-20261017T023023.json` | v21 (`3d511216…`) | PASS in the wrapper's own verdict: Ctrl+Home's `move-document-start` answered `documented-callback-visible-cursor` [observed: `fullLog`], the Backspace `verified-boundary-noop` (`waitedMs` 2256), revision 0→0, the saved text equal to the opened document's, and the positive control's second save different |
| `d2-nohost-dist0224-chrome-20261017T022113.json` | 0.2.24 (dist/'s page, shell and v20 profile) | the red case is red as required: `verified-selection-delete`, revision 0→1, no move request |

The first v21 smoke was misjudged by the wrapper (it read the move from the probe's Backspace-only summary window); it is kept as a §34.4 witness in `../witness-item1/` with the fix's reason. The re-run above used the fixed wrapper (commit `29219561`).
