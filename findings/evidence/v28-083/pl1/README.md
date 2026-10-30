# PL-1-v28 (SPEC-M3-v28-last-line-fallback 7.2)

**Tool.** `wasm_sdk_probe/tools/check_v28_pl1_last_line.py`. It runs S3's procedure (`check_v81_blank_line_bullet.py`, imported, not edited) with three changes:
- the click is below the text (0.80, 0.15 of `#paper`), which puts the caret at the end of the last paragraph;
- `selectionResultSeen` is added to the recorded barrier keys;
- the product identity is generation 81's frozen page instead of the tree's (the tree carries v28's shell now).

**Run** `run-01/` (`run-01.stderr.txt`, exit 0): **PL1_V28_HOLDS**, Chrome 3/3 and Firefox 3/3.
- Every bullet reply is the trigger: `failureShape select-text-returned-none`, `route collapsed`, `dispatched true`, `selectionResultSeen true`.
- The toast is 083's sentence.

**Self-test** (`run-01-self-test.json`): `ALL_AS_EXPECTED`, 6 cases:
- route range-single;
- 046's shape;
- the select result not seen;
- not dispatched;
- a verified reply;
- one run missing.

**Scope.** This pins only that the trigger fires on WASM. What v28's fallback then reads is measured after the link (S4).
