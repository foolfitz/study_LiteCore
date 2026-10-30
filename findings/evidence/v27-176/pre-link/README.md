# v27 pre-link evidence (SPEC-M3-v27-finding-176 7.2), engine step

Engine edits, all under `OXSDK_E2_V27_FIRST_BLOCK` (spec 4.1 item 6's closed list):
- `src/editor_api.h`: the `#error` guard (v27 requires v25; the TU carrying it is `editor_api.cpp`);
- `src/probe_engine.cpp`: `FormatStateBarrier` undo fields; `appendFormatBarrierDetails` writes `undo` inside `formatBarrier`;
- `src/ordered_format.inc`:
  - the undo read before the post;
  - no restore before the select on the collapsed route;
  - the `multiBlock` refusal only off the collapsed route;
  - the undo read after the final restore.
- Every v27 block keeps v25's text verbatim under `#else`: `strip_v27(edited inc) == HEAD's inc`, byte for byte (checked when the tests ran).

## E1 / E2

- `e1-red-before-inc-edit.txt`: `tests/test_ordered_format_v27.py --witness`, run after the struct/serializer/guard edit and before the inc edit. Exit 1. (a), (b), (d) and every (f) clause FAIL; the guards that pass today, (c), pre-dispatch refusal and single-block, pass.
- `e1-e3-native-tests.txt`, after the inc edit:
  - `tests/test_ordered_format_v27.py` OK: the original is green; v25-behaviour (v27 blocks stripped, compiled WITH the v27 define) and three mutations (`collapsed-check-all-routes`, `g-on-range-single`, `undo-record-skipped`) are each red with FAIL lines.

## E3

The three inc-text tests that are in no Makefile target, run one by one (`PYTHONPATH=tests`): `test_ordered_format.py`, `test_ordered_format_scope.py` and `test_ordered_format_v25.py`, all OK.

The scope checker counts braces textually. A first form of the `multiBlock` edit split one `if (...) {` across `#ifdef`/`#else` and made it "unbalanced". It was rewritten so that each branch is a whole `if` block. That is fixed-by-execution 1.

Positive control for the scope rule, run when the tests ran: an undo read inserted into the reply is flagged.

## E4 (fable ruling 3 Q6.2)

`tests/test_format_readback_v27.py` (`e4-unittest.txt`: OK).

**How it runs.**
- It cuts the production `parseFormatReadback`, its three helpers and `formatBarrierReadbackSatisfied` out of `src/probe_engine.cpp`, and compiles them natively.
- It feeds them 18 rows' recorded `format.html`:
  - the F rows a1, a2, n2, n3 and r1-r6 (r2 has no readback);
  - their G twins, g-a1..g-n3 and g-r3..g-r5;
  - a6g and b1g.

**Ground truth.**
- Each row's predicate is judged against the saved document's dispatch paragraph (`read_cells.saved_target`).
- `e4-parser-on-recorded-markup.json` lists every row. All 18 agree, including the two shams that must be "not satisfied" (n2 and g-n2: the first tag is `p`, so `listTag` is "").
- Hand pins: n2, r6 (two items in one list), r5 (`h1`), and a1 (one block).

**Red cases.** One flipped expectation and one wrong pin are each reported.
