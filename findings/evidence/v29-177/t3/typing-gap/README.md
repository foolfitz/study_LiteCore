# T3: typing either side of the 300 ms grace (2026-11-01)

Spec `specs/SPEC-M3-v29-tick-pacing.md` section 6 T3, append 2. `gap_order.py` runs the unchanged `probe_typing_latency.py` with a save added in process. Mirror of `dist/`, generation 83, no ddev.

**GAP_ORDER_HOLDS, 24/24** (`reading-01.json`): gap 290 and 310 x Chrome, Firefox x `boundaries`, `owner` x 3 runs, 20 keys each. Every key committed, and the save holds `a...t` once, contiguous, in order. `self-test-01.json`: ALL_RED, 6 mutations.

Commit medians, ms, three runs each. The ~4 ms step on `boundaries` from 290 to 310 is L-v29-first-key-wakes-on-a-tick, as the spec expects:

| browser | document | gap 290 | gap 310 |
|---|---|---|---|
| Chrome | boundaries | 8.9, 8.2, 8.9 | 12.2, 13.0, 12.6 |
| Chrome | owner | 13.3, 14, 12.9 | 12.8, 13.2, 13.0 |
| Firefox | boundaries | 9.4, 9.6, 9.9 | 11.6, 10.9, 10.3 |
| Firefox | owner | 13.6, 14.4, 13.4 | 14.1, 13.6, 14 |

Not a timing measurement: the desk was not clean and the run overlapped nothing heavier than the session, but these numbers are not T1.
