# E2-C phase D4 — bounded lifecycle and regression

Predictions in `PREDICTION.md`, registered before the harness existed.
Thresholds come from `e2/validation-matrix-v1.json`, frozen 2026-08-15.
`tools/analyze_e2_c_d4.py` applies them offline; self-test 10/10.

**Verdict: `PARTIAL`**, and the reason is named rather than shrugged at: the
WASM heap half of `d4-memory` is `notValidated`, because no product path
reports a WASM heap size at all.

## What ran

Ten independent edit-save-reopen sessions per browser, one page load, each
cycle opening `test-docs/e2/d1-anchors.odt`, placing the caret with the
product's click at `E2-D1-BODY-TARGET`, dispatching `set-list-unordered`,
saving and closing.  The runner sampled the browser's whole process tree at two
checkpoints per cycle -- quiescence and three seconds later -- and the analyzer
takes the smaller of each pair, as the matrix requires.

| cell | Chrome | Firefox |
|---|---|---|
| `d4-sessions` | **pass** — 10/10, generation 1 each | **pass** — 10/10, generation 1 each |
| `d4-residuals` | **pass** — workers 0, handles 0 at every sample | **pass** — same |
| `d4-memory` | **PARTIAL** — PSS slope 0.45 MB/session (limit 8) | **PARTIAL** — PSS slope 7.52 MB/session (limit 8) |
| `d4-regression` | **pass** — 11 targets, artifacts unchanged | same run, shared |

## The WASM heap cannot be measured on this artifact

`PREDICTION.md`'s P-D4-4 said it would not be, and it was not:

- `sdk/sdk-worker.js` never reports a heap size, and adding one is an engine or
  worker change -- both bound hashes, both relink queue material.
- R7-D's longevity page has carried `wasmHeapBytes: null` unconditionally for as
  long as it has existed, while `r7_longevity_analysis.py` computes a series
  from it.  That field has been decorative the whole time.
- The one browser-side route, `performance.measureUserAgentSpecificMemory()`,
  is available in Chrome (this page is cross-origin isolated) and its breakdown
  carries **no WASM-attributed entry**: types `Shared`, `DOM`, `JavaScript`.
  Firefox does not implement it at all.

So the cell is `PARTIAL` with the WASM half `notValidated`.  **Not a pass** --
the matrix's `onUnavailable` is PARTIAL and that is what is recorded.  The fix
belongs in the relink queue: the engine can report its heap in typed state, and
D4 is the phase that found this out, which is what "D2–D5 are a
queue-completeness problem" meant.

## Firefox's PSS passes, and the margin is thin enough to say so

| | Chrome | Firefox |
|---|---|---|
| per-cycle PSS, MB | 419.9 → 425.0 | 661.5 → 696.6 |
| slope, MB/session | **0.45** | **7.52** (limit 8) |
| tenth minus first, MB | +5.1 | **+35.1** |

The cell passes as frozen: the matrix's PSS criterion is the slope, and 7.52 is
under 8.

**But `PREDICTION.md`'s P-D4-3 was written with two clauses** -- slope ≤ 8
*and* the tenth sample within +20 MB of the first -- and Firefox fails the
second at +35.1 MB.  So:

- the **cell** passes (the matrix is the authority for cells);
- the **prediction** is recorded as **failed for Firefox** (what was written is
  what gets scored, the same rule L2, L5 and P-C5 were scored under).

The curve is not a straight climb: 661, 639, 639, 645, 649, **706**, 717, 695,
692, 697 -- flat, one step at cycle 6, then flat again around the new level.
That shape is consistent with an allocator or GC step rather than a per-session
leak, but this round did not measure which, and it is not claimed.  A round that
wanted to answer it would run more cycles and watch whether the step repeats.

## Regression

`tools/run_e2_c_d4_regression.py`, eleven targets, all green, and **every
profile's `probe.wasm` hashed before and after: unchanged**.  The matrix
excludes `test-e1-c-static` by name and puts `check_e1_c_bundle_intact` and
`test-e1-c-frozen-guard` in its place; both ran and both passed.

(`test-e1-c-static` itself was red from 2026-08-16 morning until repaired the
same day -- it did not know about the declared shell divergence.  It is green
now, and it is still excluded here, because the matrix says so and a frozen
criterion is not edited to match new facts.)

## Reproducing

```
python3 tools/run_e2_c_d4.py --browser chrome --cycles 10
python3 tools/run_e2_c_d4.py --browser firefox --cycles 10
python3 tools/run_e2_c_d4_regression.py
python3 tools/analyze_e2_c_d4.py <chrome dir> <firefox dir> \
    --regression regression/summary.json --output summary.json
```
