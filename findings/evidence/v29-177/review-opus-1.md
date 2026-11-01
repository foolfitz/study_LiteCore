# v29 tick pacing: adversarial review, one round (opus, read-only, 2026-11-01)

Verdict as delivered: the pacing rule and the hook are sound; do not link yet, one runtime defect needed a code change. Nothing was run in a browser. The main session checked item 1 against `probe.js` and measured the fix.

| # | Sev | Item | Disposition |
|---|---|---|---|
| 1 | HIGH | Stock mode 2 in a pthread: `Module["setImmediates"]` has no consumer, an unbounded leak; every tick hops through `sdk-worker`, so two threads spin and ticks stall during synchronous `sdk-worker` JS | **Adopted.** Confirmed in `probe.js`. `MessageChannel` pre-installed as `MainLoop.setImmediate`. Mirror, three repetitions: Chrome 8.4/10.1/8.4 ms, Firefox 9.7/9.5/9.3 ms, against stock 9.9/10.9/9.8 and 9.2/9.4/9.3 |
| 2 | HIGH | T1 is already red on Firefox: 10.1 > 10; the finding's "thresholds all pass" is false for that cell | **Adopted.** Finding corrected. Spec: the gate is not moved on v29; whether it is re-set for the ordered engine is decided before the next K spec. The link is not blocked: the fix is needed either way |
| 3 | MEDIUM | T3's "S1-S4 reread" has no referent; all v23-v28 evidence was taken at 85 ms, so timer-class callbacks may now fall after the reply | **Adopted.** T3 names live arms, and gaps 290/310 ms straddling the grace |
| 4 | MEDIUM | T2 has no red case, an ambiguous formula, measures only after load on the mirror; a timer with no input keeps immediate past the grace on a long document | **Adopted.** One formula over the process tree, four situations, red case; limit L-v29-idle-chain-outlives-the-grace |
| 5 | LOW | The desk cannot see contention on a 2-core client | **Named**, L-v29-small-client-contention, not a criterion |

Premises that held: the poll is reached on idle ticks and this is the ordered engine's path; `emscripten_set_main_loop_timing` runs in the engine worker's realm and neither transition double-schedules; no starvation, commands arrive through a shared deque under `gState.mutex`; the poll does not block; a long command stamps `lastWorkMs` after it returns; `processed` is a real 0/1. Page and worker JS and core beyond `svpinst` were not audited for cadence dependence.

Found by the main session after the review: `EM_ASM` bodies can have `=>` and `===` split by the preprocessor (`probe_engine.cpp:1334`), so the channel code uses plain functions. The `-E` expansion is intact and the body parses as JS.

A Makefile derivation bug was caught by `make -n` before any of this: the batch rename turned `-DOXSDK_E2_V28_LAST_BLOCK` into `V29_LAST_BLOCK`, and the new define was missing.
