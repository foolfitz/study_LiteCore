# T4: worker JS heap during 60 s of typing (2026-11-01)

Spec section 6 T4, append 2 and append 3. `heap_during_typing.py`: the unchanged typing probe, Chrome, `boundaries`, gap 80, 700 keys, eleven samples of forced GC then `Runtime.getHeapUsage`, on every worker reached by recursive `Target.setAutoAttach`. Eight workers, all answered all eleven samples in every arm.

| run | subject (v29) max growth | red (v28 + stock immediate) max growth |
|---|---|---|
| 01 | 0.060 MiB | 21.9 MiB |
| 02 | 0.070 MiB | 23.0 MiB |
| 03 | 0.069 MiB | 23.8 MiB |

**The reading as first pinned was T4_RED in runs 01 and 02** (`reading-pinned-run-0N.json`), on `redGrows` only: `grows` asked for at least 8 of 10 intervals up, and the leak grows in steps because V8 doubles the array (red 01: 11.1, 15.3, 15.3, 19.1, 24.6, 24.6, 24.6, 33.0, 33.0, 33.0, 33.0 MiB; 6 of 10 up). The instrument saw the leak; the clause described a smooth line no such leak draws. Spec append 3 drops the clause. That can only make `subject` easier to turn red, and `subject` was 300 times under the remaining 1 MiB line in all three runs.

**As corrected: T4_HOLDS in all three runs** (`reading-run-0N.json`). `self-test-01.json`: ALL_RED, 4 mutations.

In these reports `onScreenMs` is large for early keys (median ~8 s). That is the probe's window, not the product: the page instrument keeps the last 600 fresh blits, so at 700 keys the first kept blit is long after the early keys; the last 60 keys read a median of 7.7 ms. T4 does not read it.
