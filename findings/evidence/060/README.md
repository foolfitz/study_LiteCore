# Finding 060 — the caret check's verdict depends on the browser window size

Measured 2026-08-18 on the shipped v3 artifact (`d538ce0b…`) and shell v16
(`e48685976e8626c5…`, served digest verified equal to the declared bundle), Chrome,
`dist/` unmodified.

## What happened

A clean product-path round reported `the-caret-is-drawn-where-it-was-placed` as
**FAIL**, with `darkWithCaret == darkAfterItMovedAway == 2051`. The same check
was green on 2026-08-17 with 2763 → 2739 (finding 058). Nothing in `dist/` or
`web/` changed in between.

`product-path-chrome-fail.json` holds that check, with the served-shell identity
that proves it ran against the declared generation.

## The caret IS drawn — this is not a regression of 058's fix

`row_profile_probe.py` profiles every canvas row's dark-pixel count instead of
one 46-row band, and runs against two roots: `dist/` and the `caret` mutation
mirror (which disables the caret draw and is the control 058 already used).

Diffing the two at the same gesture isolates the caret:

| | rows differing (clean vs no-caret) |
|---|---|
| after click A (`y = 0.28`) | none inside the text area |
| after click B (`y = 0.42`) | **rows 276–283, +1 dark pixel each** |

Eight rows, one pixel wide, present only when the caret draw is enabled. That is
the caret stroke. Raw profiles: `row-profile-clean.json`,
`row-profile-caret-mutation.json`.

## Why the check nevertheless goes red

Canvas geometry in this run was 725 × 929 at `devicePixelRatio` 1 — `layoutCanvas`
sizes the canvas from `el.desk.clientWidth`, so **the canvas is a function of the
browser window**, and 058's recorded numbers (2763 baseline) came from a larger
one.

At this geometry the check's two fixed click fractions do not produce the state
its oracle assumes. The band it samples is rows 242–287; the caret stroke lands
at rows 276–283 — **inside that band after the second click**, which is the read
the oracle expects the caret to have left. The comparison inverts, and where the
document is short enough that both fractions resolve to the same line it flattens
to equality instead.

`single_click_timing_probe.py` rules out the obvious alternative: after one
click, re-sampling at 1 s, 3 s, 6 s and 12 s never produces the stroke, so this
is not the check waiting too little.

## Not established

* **Where the caret is after the first click.** No countable ink appears, which
  is consistent with the stroke landing on pixels that are already dark, but that
  is inference, not measurement.
* **Whether Firefox behaves the same way.** Only Chrome was run.
* **Any mechanism for the first-click/second-click asymmetry.** Not measured, not
  named.

## What this costs

`see-where-the-caret-is` is `done` in the acceptance checklist on the strength of
this check. The check can still fail — the mutation control proves that — but its
green depends on the window the harness happened to open. A geometry-anchored
oracle is owed; it is the same work the plan already schedules for
`put-the-caret-where-i-clicked`.
