# The extra START is a measured no-op for ordinary range selections

Written in English per `AGENTS.md` (2026-08-15): everything newly written under
`findings/evidence/**` is English. The neighbouring files in this tree predate
that rule and were left as they are by the user's ruling.

## The question

Task #49 changed the engine's range selection from `RESET` + `END` to
`RESET` + `START` + `END`. Four native rounds showed the three-call form selects
the same characters as the two-call form when the shell state is clean (arms
AG/AH/AI, and AJ/AK for a range running right to left). That is a native result.

The engine comment claims the extra call is free. This checks that claim on the
artifact, not only natively.

## The measurement

The composition scan carries an arm named `select-y2600-without-format`: the
same range selection at the same coordinates, with **no format action before
it**. It exists as the attribution control for the defect, but it doubles as a
before/after control for the fix, because it exercises the ordinary path.

Comparing that arm across the two artifacts -- `ba1a5dd5` (two calls) and
`940b7723` (three calls) -- on the same fixture and the same coordinates:

| artifact | browser | elapsed | collapsed | rectangles | start.x | end.x | completion |
|---|---|---|---|---|---|---|---|
| `ba1a5dd5` | Chrome | 20 ms | false | 1 | 1524 | 2924 | `documented-callback-text-selection` |
| `ba1a5dd5` | Firefox | 20 ms | false | 1 | 1524 | 2924 | `documented-callback-text-selection` |
| **`940b7723`** | Chrome | **20 ms** | **false** | **1** | **1524** | **2924** | **`documented-callback-text-selection`** |
| **`940b7723`** | Firefox | **20 ms** | **false** | **1** | **1524** | **2924** | **`documented-callback-text-selection`** |

Identical in every column, in both browsers.

## What this does and does not say

It says the third call does not change the outcome of an ordinary range
selection on the artifact: same geometry, same completion route, same latency to
the millisecond.

It does not say the endpoints are correct in general. The endpoint semantics
were measured natively with three distinct coordinates, and with the range
running right to left; this arm uses one coordinate pair and only shows that
the two artifacts agree on it. The native arms are what carry the endpoint
claim.

It also does not rule out a cost that this arm cannot see. The measurement is a
single selection per browser, so a latency difference smaller than the timer
resolution, or one that only appears under load, would not show up here.

## Where the numbers come from

`fixed-940b7723/e2-combination/{chrome,firefox}/result.json`, arm
`select-y2600-without-format`, compared against the same arm in
`../../039-combination/p2-composition-scan-ba1a5dd5/e2-combination/{chrome,firefox}/result.json`.
Both artifacts are archived under `wasm_sdk_probe/build/archive/`.
