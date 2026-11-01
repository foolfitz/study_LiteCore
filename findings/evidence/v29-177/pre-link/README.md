# v29 pre-link evidence (spec section 5)

- U: `pacing-mutations.txt`, four mutations of `main_loop_pacing.hpp`, each red; the unmutated test is green (`make test-v29-tick-pacing-static`).
- S: `syntax-v29.*` exit 0. Controls: `syntax-control-no-v28-define.*` fires the `#error`; `syntax-control-call.*` and `syntax-control-switch.*` break the hook in a temporary copy and fail at those lines. Under `taskset -c 0`, about 1.3 s each; `syntax-desk.txt` is the load before the first run.
- A control that proved nothing, kept out: `-DEM_TIMING_SETIMMEDIATE=...` exited 0, the header's own define overrides the command line. A green there could not tell "compiled" from "not reached", so it was replaced by the two above.
- M: `static-reds-after-v29.txt` equals `findings/evidence/k-0.2.44/p6-named-reds.txt`; M1-1 green with `--carrier E2_V29`.
- D: `make-n-owner-line.txt`: four compile lines, all under `build/e2/editor-v29`, each with `OXSDK_E2_V29_TICK_PACING`, one guarded link. It also caught the batch rename that had mangled `-DOXSDK_E2_V28_LAST_BLOCK`.
- Source delta since v28's link (`7a04885ec`): `src/probe_engine.cpp`, 54 lines, all under the new define, plus the new `src/main_loop_pacing.hpp`.
