# Result: the caret is delivered and then overwritten by a stale read

Finding **084**, 2026-08-27. The prediction written before these runs
(`PREDICTION-2026-08-27-which-layer-drops-it.md`) held, including the mechanism
and the signature it named. Method:
`METHOD-2026-08-27-three-layer-caret.md`.

## The answer

**The engine is not the problem, and neither is the page's ability to draw.**
The engine emits the new caret. The page receives it and applies it. Then the
drain's own state read -- answered *before* that announcement and applied
*after* it -- puts the old caret back, and nothing asks again until the next
commit.

`editorState` on the page has **two writers and only one guard**:

| writer | where | guard |
|---|---|---|
| the engine's `editor-state` announcement | `editor-shell-v2/narrow-editor-v2-session.js:171-173` | **yes** -- refuses to write unless `sourceSequence` advances |
| the drain's own `editor.getState()` | `editor-shell/editor-session.js:301-311` | **none** -- writes whatever its read returned |

The announcement's guard was added by finding 068 and its comment says exactly
why: "a slow event could land after a fresher read and move the caret
backwards". The symmetric case -- a slow READ landing after a fresher event --
was not guarded, and that is this defect.

## The trace, one dropped commit (`stalled-run1`, CARETFOLLOW10)

```
believed  seq=294  caret=3458,4904  rev=128  ready
believed  seq=294  caret=3458,4904  rev=128  busy
believed  seq=294  caret=3458,4904  rev=128  busy
believed  seq=295  caret=3458,4904  rev=128  busy
believed  seq=296  caret=5618,4904  rev=128  busy    <- the caret ARRIVES
believed  seq=294  caret=3458,4904  rev=129  busy    <- the drain writes it BACK
believed  seq=294  caret=3458,4904  rev=129  ready

applied   3458,4904   (x4)
applied   5618,4904          <- the sink WAS moved to the new caret
applied   3458,4904   (x3)   <- and then moved back

engine, asked 53 ms into the stall: caret 5618,4904 at sourceSequence 296,
  against the page believing 3458,4904 at sourceSequence 294
sink: 196,278 -> 196,278, settled after 8039 ms (the deadline), engineProbes 1
```

Read from `product-path-v11-stalled-run1.json`, check
`caret-follows-the-text-you-type`, round `CARETFOLLOW10`.

`sourceSequence` going **backwards** is the signature, and the revision going
*forwards* in the same row is what identifies the writer: only the drain writes
`revision` and `editorState` together.

## The numbers

| series | engine probe | commits | dropped | `sourceSequence` reverted | engine ahead of the page |
|---|---|---|---|---|---|
| A | `every-round` | 24 | **0** | 0 | 0 |
| B | `stalled` | 48 | **10 (21%)** | **10 of 10** | **10 of 10** |

Per run under `stalled`: 4, 2, 1, 3 of 12. `settledAfterMs` for every dropped
round is 8023-8053 -- the 8 s deadline -- and for every passing round 0 or 1.
Still bimodal, still not latency.

**One probe was enough, every time.** In all ten dropped rounds the FIRST engine
probe -- taken 52-54 ms after the sink was seen not to have moved -- already
held the new caret. `engineProbes: 1` in all ten.

Instrument controls held in all four runs: `engineProbeTracked: true` (the
control pair before any typing read 1644,4352 then 2871,4352) and
`sinkTracksTheCaret: true`.

## The confound this measurement created, and what settles it

Series A is not a null result about the product. It is a result about the
instrument: **the first version of the probe suppressed the defect it was built
to measure.** `engineBefore` was a real `editor-get-state` issued immediately
before every commit, and with it in place 24 of 24 commits followed the caret;
with the identical configuration and no probe on a passing commit, 10 of 48
dropped. Fisher exact on 0/24 against 10/48 is p = 0.012.

That is why `--caret-engine-probe stalled` is the default now: a commit the sink
followed sends the engine nothing, so the rate a run reports is the product's.

The 2026-08-26 figure of 3 in 27 is a third configuration -- three commits per
run, no probe of any kind -- and it does not contradict either of these. What
the table above compares is two runs of the SAME configuration, twelve commits
each, differing only in whether the engine was asked before every commit.

**And the layer conclusion does not rest on the probe at all.** The decisive
record is `caretBelieved`, which is a log of what the PAGE was handed -- no
engine command involved. It shows the announcement arriving with the new caret
and then being overwritten. The engine probe agrees with it and cannot, on its
own, rule out having flushed a waiting callback; the belief log can, because the
announcement it records was unprompted.

## The shipped profile, same instrument: 24 of 24 followed the caret

And the reason is visible in the same column. **The shipped core advances
`sourceSequence` by ONE per commit; the accessibility core advances it by TWO.**

Shipped (`v8-run1`, CARETFOLLOW5, passing):

```
seq=226 caret=3111,4695 rev=123 ready
seq=226 caret=3111,4695 rev=123 busy
seq=226 caret=3111,4695 rev=123 busy
seq=226 caret=3111,4695 rev=124 busy    <- the drain's write (revision advances,
seq=226 caret=3111,4695 rev=124 ready       sourceSequence does not)
seq=227 caret=5151,4695 rev=124 ready   <- the caret arrives AFTER it
```

Accessibility (`stalled-run1`, CARETFOLLOW5, passing):

```
seq=282 caret=11032,4352 rev=123 ready
seq=282 caret=11032,4352 rev=123 busy
seq=282 caret=11032,4352 rev=123 busy
seq=284 caret=3111,4628  rev=124 busy   <- the drain's write, already at 284
seq=284 caret=3111,4628  rev=124 ready
seq=285 caret=3111,4628  rev=124 ready
seq=286 caret=5151,4628  rev=124 ready  <- the caret arrives
```

On the shipped core the announcement carrying the caret is the LAST thing that
happens in a commit -- after the drain has written -- so there is nothing left to
overwrite it. On the accessibility core each commit produces an extra
state-changing callback, and the drain's write lands in the middle of the
sequence instead of before it. Whether it lands before or after the
caret-bearing announcement is what separates a passing round from a dropped one,
and on this lineage it is a coin toss that comes up wrong about one time in five.

| profile | commits | dropped | `sourceSequence` per commit |
|---|---|---|---|
| shipped `e2-editor-v8` | 24 | **0** | **+1** |
| a11y `e2-editor-v11` | 48 | **10** | **+2** |

## What this does NOT establish

**Not that the defect is in the accessibility core.** The two writers and the
missing guard are in JavaScript that BOTH profiles run. What differs is the
number of announcements a commit produces, and therefore how often the drain's
read is stale by the time it writes. **"Not seen on the shipped profile in 66
commits" is a rate, not immunity** -- the code carrying the defect ships today,
and an ordering that holds for one core's callback schedule is not a guarantee.

**Not why the accessibility core emits two.** That is a build difference and one
measurement -- findings 040 and 048 are the record of what naming a layer from
one of those costs.

**Not the fix.** The natural home for a guard is `EditorSession._drain()`, and
that file is bound to E1-C's verdict (`check_e1_c_bundle_intact.py`, shell
bundle `187706b2…`) -- the same wall finding 068 hit, which is why 068's remedy
lives in a subclass override. Whether the same trick reaches this write is a
design question, not a measurement, and it is not answered here.
