# E2-C phase D4 — registered before the harness existed

Written 2026-08-16.  Bounded lifecycle and regression, the fourth of the six D
phases.  Thresholds are **not** invented here: `e2/validation-matrix-v1.json`
froze them on 2026-08-15, and they are numbers rather than "no continuous
growth" precisely because an adversarial review pointed out that one GC dip can
make a leaking curve look flat.

| cell | oracle, as frozen |
|---|---|
| `d4-sessions` | ten independent edit-save-reopen sessions per browser complete, each with at most three worker generations |
| `d4-residuals` | workers and handles are zero after dispose, at every sample including the tenth |
| `d4-memory` | WASM heap slope ≤ 2 MB/session and absolute growth ≤ 20 MB; browser PSS slope ≤ 8 MB/session; samples taken at quiescence and again three seconds later, smaller value used.  `onUnavailable: PARTIAL` |
| `d4-regression` | R6 release, R7-B/C/D, R8-D, E1-A, E1-B, E2-A and E2-B static targets pass; workspace preflight before and after passes; `test-e1-c-static` is NOT run and `check_e1_c_bundle_intact` plus `test-e1-c-frozen-guard` are run instead |

## How each number is obtained

**One cycle** = a fresh `NarrowEditorV2Session`, open the fixture, place the
caret with the product's click (proved to have landed, finding 048's path),
dispatch one paragraph action, save, close.  Ten of them, one page load, so the
"at most three worker generations" bound is measured per session rather than
per page — the semantics SPEC E1-C v7 corrected.

**Workers and handles** are counted by the page: the `Worker` constructor is
wrapped, and `terminate()` with it, exactly as E1-C's lifecycle phase does.
"Active" is created minus terminated, sampled after `close()` has resolved.

**PSS/RSS** is sampled by the RUNNER over the browser's whole process tree.
The page publishes a `sampleState` token at each checkpoint and the runner
snapshots whenever the token changes — the pattern R7-D established.  Each cycle
publishes two checkpoints: one at quiescence, one three seconds later.  The
analyzer takes the **smaller** of the pair, as the matrix requires.

## The WASM heap: registered expectation is that it CANNOT be measured

Checked before writing the harness: **nothing in the product reports a WASM heap
size.**  `sdk/sdk-worker.js` never sends one, and R7-D's page — the only other
place in this tree that wanted the number — sets `wasmHeapBytes: null`
unconditionally while `r7_longevity_analysis.py` computes a series from it.  So
that field has been decorative for as long as it has existed.

The harness therefore tries the only browser-side route that exists,
`performance.measureUserAgentSpecificMemory()` (needs cross-origin isolation,
which these pages have), and **records its whole breakdown** rather than a
number somebody chose.

- **P-D4-4 predicts it will not yield a WASM-attributed figure in either
  browser**, and that `d4-memory` will therefore be **PARTIAL** with the WASM
  half `notValidated`.
- If that prediction holds, the fix is an engine-side field in the typed state,
  which is a **relink queue item** — discovered by writing D4, which is exactly
  what the adversarial review meant by "D2–D5 are a queue-completeness problem,
  not a scheduling detail".
- **`notValidated` is not a pass.**  The matrix's `onUnavailable` is PARTIAL,
  and PARTIAL is what gets recorded.

## Predictions

- **P-D4-1** — ten cycles complete in both browsers, each reporting at most
  three worker generations.
- **P-D4-2** — active workers and active handles read **0** at every
  post-close sample, including the tenth.
- **P-D4-3** — browser PSS slope over the ten cycles is **≤ 8 MB/session**, and
  the tenth cycle's sample is within **+20 MB** of the first.
- **P-D4-4** — no WASM heap figure is obtainable in either browser (see above).
- **P-D4-5** — every regression target in the frozen list passes, and the
  workspace preflight passes before and after.  Measured already on 2026-08-16
  for the static half: ten of eleven green, `test-e1-c-static` excluded by the
  matrix and since repaired; this prediction is that the same holds when run
  around the lifecycle round rather than on its own.

## What voids the round

- A cycle fails for a reason unrelated to lifecycle (fixture fetch, anchor not
  found): recorded, not retried, and the round reports fewer than ten cycles
  rather than pretending ten.
- The runner's process tree loses the browser (crash): the samples after that
  point describe a different process and are dropped, not interpolated.
- PSS is unavailable in a browser: `notValidated` for that browser's memory
  half, PARTIAL, never a pass by absence.
