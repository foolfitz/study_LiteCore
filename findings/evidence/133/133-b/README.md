# 133-B on host 0.2.14 — HOLDS (12 runs, guard burned once)

Instrument: `wasm_sdk_probe/tools/probe_k8_frozen_recovery.py --repeats 6 --out-dir ../findings/evidence/133/133-b` (twice), host 0.2.14 `237f2cb`, buildId `eb3f94084995d3f0`, page `d761f1ce…`, SDK `e4c3fe92…`, Chrome 151. Reader: `../judge_133b.py` (written and made red before any run, `../judge_133b-red-case.txt`, `../judge_133b-cases.txt`).

- Series 1 (`probe-2026-10-12T133826+0000.json`): 6/6 pass (a)–(c), 0 guard burns → reader EXTEND (`judge-series-1.txt`). Checked that this is not a silent logpoint: every run's overdue-timer batch woke after the save reply (+379…+896 ms vs +270…+309 ms), so no deadline fired while the save was pending.
- Series 2 (`probe-2026-10-12T141424+0000.json`): 6/6 pass, run 3 burned the guard.
- Both series: **HOLDS — runs 12, failing 0, guard burns 1** (`judge-series-1-and-2.txt`).

The burned run (series 2, run 3), ms after thaw: `+240 autosaveNow idle` (the overdue batch wakes) → `+242 rearm save 18, 150625 ms late` (pre-fix this was `fail save TIMEOUT` → `recoverable-error`) → `+285 respIn/resp save 18 ok` → `+292 busy→ready` → auto save 204, manual save 204, server bytes = the manual save's.

Per run (timer batch = first `autosaveNow idle` after thaw; reply = first `respIn` after thaw):

| series/run | freezeAt | thawAt | timer batch wake (ms after thaw) | save reply (ms after thaw) | rearm (late ms) | end | auto attempts | manual | lock lostBy |
|---|---|---|---|---|---|---|---|---|---|
| 1/1 | 3736 | 334079 | 673 | 309 | – | ready | [[412, 204]] | 204 | save |
| 1/2 | 3728 | 334121 | 845 | 278 | – | ready | [[412, 204]] | 204 | save |
| 1/3 | 3864 | 334229 | 896 | 283 | – | ready | [[412, 204]] | 204 | save |
| 1/4 | 3437 | 333770 | 457 | 270 | – | ready | [[412, 204]] | 204 | refresh |
| 1/5 | 3399 | 333750 | 379 | 286 | – | ready | [[412, 204]] | 204 | save |
| 1/6 | 3739 | 334106 | 824 | 297 | – | ready | [[412, 204]] | 204 | save |
| 2/1 | 3763 | 334133 | 881 | 290 | – | ready | [[412, 204]] | 204 | save |
| 2/2 | 3704 | 334076 | 886 | 326 | – | ready | [[412, 204]] | 204 | save |
| 2/3 | 3429 | 333815 | 240 | 285 | 150625 | ready | [[204]] | 204 | refresh |
| 2/4 | 3696 | 334063 | 909 | 298 | – | ready | [[412, 204]] | 204 | save |
| 2/5 | 3702 | 334081 | 923 | 290 | – | ready | [[412, 204]] | 204 | save |
| 2/6 | 3768 | 334166 | 790 | 290 | – | ready | [[412, 204]] | 204 | save |

Predictions (spec §9.20, written before the run) against measured:

| Prediction | Measured |
|---|---|
| guard burns 2–5 of 6 | **missed low**: 0/6 then 1/6 (1/12). With the pre-fix probe (timer first 2/3) the timer won 3 of 15 races |
| each burn exactly 1 `rearm`, reply within 400 ms of thaw | holds (1 rearm, reply +285 ms) |
| auto save 412 (token) → 204 (no token), `lock.lostBy == "save"` | 10/12; in 2/12 the lock refresh at thaw found the loss first (`lostBy refresh`; in the burned run the auto save was a single 204) |
| manual 204 | 12/12 |
| the chain's K8 1/1 | not run: the count chain is deferred (spec §9.21) |

Probe output: `probe-run-1.out` ends in a traceback from the probe's last line (`relative_to` on a relative `--out-dir`; the report was already written); fixed in `0ff98687`, `probe-run-2.out` exits 0.
