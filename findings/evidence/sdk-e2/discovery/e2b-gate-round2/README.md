# SPEC E2-B section 3 gate, round 2: closing G1

**Date** 2026-08-15
**Artifact** `e2-combination` = `940b7723…` — **the same artifact round 1 used**,
so the two runs compose
**Prediction** [`../e2b-gate/PREDICTION-G1-rerun.md`](../e2b-gate/PREDICTION-G1-rerun.md),
committed before any run of the new fixture (`1b41131`)
**Round 1** [`../e2b-gate/`](../e2b-gate/README.md) — unchanged, still the record
of that run

## Why there is a round 2

Round 1 recorded arm **G1** (`wrapped-line-range`) **void**. It aimed at
`第三段跨行 gamma` in `multi-paragraph.odt`, and that paragraph is **tall, not
wrapped**: a selection across its full vertical extent reported one rectangle.
Same-paragraph multi-rectangle selection was therefore still unmeasured, and
SPEC E2-B 9.5 said so in as many words.

No fixture in the E1 corpus has a paragraph long enough to wrap, and that corpus
is frozen (`dist/e1-fixtures/manifest.json`: `frozenDate 2026-08-04`,
`mutationPolicy copy-only`). So this round adds
`dist/e2b-fixtures/wrapped-paragraph.odt` — its own directory, its own manifest,
the E1 corpus untouched.

## Verdict: G1 passes, everything else reproduces

Chrome and Firefox are **cell-for-cell identical**, three rounds each — and
identical to each other round by round, not merely in totals.

| arm | Chrome | Firefox | vs round 1 |
|---|---|---|---|
| **A1** `bullet-from-range` | pass 3/3 | pass 3/3 | same |
| **A2** `ordered-from-range` | pass 3/3 | pass 3/3 | same |
| **A3** `list-none-from-range` | pass 3/3 | pass 3/3 | same |
| **A4** `heading-from-range` | pass 3/3 | pass 3/3 | same |
| **A5** `body-from-range` | pass 3/3 | pass 3/3 | same |
| **G2** `reverse-range` | pass 3/3 | pass 3/3 | same |
| **G3** `cross-paragraph-range` | fail 3/3 | fail 3/3 | same, as predicted both times |
| **G1** `wrapped-line-range` | **pass 3/3** | **pass 3/3** | **was void 3/3** |
| **G1c** `single-line-control` | **pass 3/3** | **pass 3/3** | new |

**The dark cell is closed.** A format action dispatched on a range that spans
several visual lines inside one paragraph behaves exactly like the
single-rectangle case: the command applies to that paragraph, the barrier reads
it back, the engine reports success, every other paragraph is untouched, and the
selection collapses afterwards.

## What G1 actually measured

Identical in all six runs (2 browsers x 3 rounds):

- **3 rectangles**, tiling contiguously: `y=1807 h=275`, `y=2083 h=1931`,
  `y=4015 h=275` — first visual line, the full-width middle block, last partial
  line. `1807+275 = 2082`, `2083+1931 = 4014`, and the last ends at `4290`.
- selection text **584 characters** of the paragraph's 1319, all of it `G1WRAP-…`
  tokens, so it is unambiguously inside one paragraph
- `collapsedBeforeDispatch: false`, `collapsedAfterDispatch: true`
- `completion: verified-format-readback`, `changed: null`, `revision: 1`
- saved ODT: paragraph 2 in a bullet list, paragraphs 1, 3 and 4 unchanged

The control, in the same document and the same runs: **1 rectangle**,
`y=1418 h=275`, 25 characters, and the same completion and collapse.

## The prediction was right on the criterion and wrong on the number

`PREDICTION-G1-rerun.md` predicted "greater than one" rectangle and guessed
**8–20**, reasoning from 1319 characters at the default page width. The answer
is **3**, because LOK does not emit one rectangle per visual line: it merges the
full-width middle lines into a single tall rectangle. The guess was wrong; the
criterion it was attached to (`> 1`) was right, and was the only thing the
verdict depended on. Recorded here rather than quietly dropped.

## The fixture was validated separately from the measurement

Whether that paragraph wraps **at this build's page width** is a property of the
fixture, and finding out costs a span select — which is also the first half of
arm G1. If the gate had answered it, one run would have both tuned the fixture
and produced the verdict.

So `tools/run_e2b_gate.py --geometry-only` selects the spans, records the
rectangles, and dispatches nothing and saves nothing. Its output is in
[`../e2b-gate-round2-geometry/`](../e2b-gate-round2-geometry/). It reported 3
and 1 rectangles, matching what the verdict run later saw — which is a
consistency check, not the verdict.

## The check can fail, and round 1 is the proof

The rectangle criterion is not decorative: **round 1 is the negative control.**
Its `verdict.json` still reads, for all three rounds,
`"only 1 rectangle: the fixture did not provide a wrapped line, so this case was
not exercised"`. The same analyzer, the same criterion, a fixture that does not
wrap, and the arm does not go green.

## One analyzer bug found and fixed: it could no longer reproduce round 1

Re-aiming G1 meant changing the analyzer's anchor table. Keyed by arm name
alone, the new table would have judged round 1's evidence differently —
still void, but for the wrong reason, and with `G1c` counted as a missing arm.
**A judge that silently stops reproducing its own earlier verdict is the same
failure as round 1's third comparator bug**, in which the analyzer replaced a
pre-registered criterion and the replacement made an arm pass.

The table is now keyed by `(arm, fixture)`, and both fixtures are listed. Round
1's `verdict.json` was re-derived with the new analyzer and is **byte-identical**
to the file committed on 2026-08-15, in both browsers.

## Residual: a partial wrapped range, not a whole-paragraph wrapped range

The G1 range covers 584 of the paragraph's 1319 characters. Both endpoints are
**inside** the paragraph, because the survey sweep stops at `y=4400` and the
paragraph continues past it.

So what is now measured is: **a multi-rectangle range inside one paragraph**.
What is still not measured is a range covering an **entire** wrapped paragraph,
end to end. The A-arms cover whole-paragraph ranges and G1 covers
multi-rectangle ranges; **their conjunction is not covered**. That is a much
smaller cell than the one round 1 left, and naming it is cheaper than implying
it is closed.

## What this round does not establish

Unchanged from round 1:

- **It does not bind a product build.** SPEC E2-B 3.9 requires every arm re-run
  on the product profile. That is now known to be more than a relink: the
  product objects are not compiled with `-DOXSDK_E2_FORMAT_BARRIER`
  (`Makefile:538` versus `Makefile:610`), so route C is **not in the product
  build at all**.
- **It does not test the v2 protocol** (spec section 5).
- **It does not measure a physical drag.** The range arrives as coordinates
  through `editorSelectRangeV1`, not as pointer events.
- **It does not resolve G3.** Cross-paragraph still fails 3/3 in both browsers,
  with the document outcome still correct, exactly as in round 1.
