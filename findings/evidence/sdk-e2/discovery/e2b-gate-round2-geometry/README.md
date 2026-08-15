# Fixture validation, not measurement

`tools/run_e2b_gate.py --geometry-only` on `e2-combination` = `940b7723…`,
Chrome, 2026-08-15.

This run answers one question: **does `wrapped-paragraph.odt` actually wrap at
this build's page width?** That is a property of the fixture. Establishing it
costs a span select, which is also the first half of arm G1 — so if the gate
answered it, the same run would both tune the fixture and produce the verdict.

The mode therefore selects the two spans, records the rectangles, and
**dispatches nothing and saves nothing**. There is no verdict here and no
`saved/` directory.

## Result

| probe | anchor | rectangles | geometry |
|---|---|---|---|
| wrapped | `G1WRAP` | **3** | `y=1807 h=275`, `y=2083 h=1931`, `y=4015 h=275` |
| control | `E2B-WRAP-HEAD` | **1** | `y=1418 h=275` |

The three tile contiguously from 1807 to 4290: first visual line, the merged
full-width middle block, last partial line. The fixture wraps.

The verdict run is [`../e2b-gate-round2/`](../e2b-gate-round2/README.md) and is
judged on its own records; that these two agree is a consistency check, not the
verdict.
