# The arithmetic says it is a stale read, and the read is the harness's

Measured 2026-08-26 from data already collected — **nineteen runs, both cores,
no new browser started**. `caret-follows-the-text-you-type` reads `#sink`'s
`offsetLeft` before and after each of three commits.

## Every run, side by side

| runs | profile | outcome | sink `left` after each round | deltas |
|---|---|---|---|---|
| 11 | `e2-editor-v8` | PASS | 163, **278**, 393, 509 | 115, 115, 116 |
| 2 | `e2-editor-v10` | PASS | 163, **278**, 393, 509 | 115, 115, 116 |
| 2 | `e2-editor-v11` | PASS | 163, **278**, 393, 509 | 115, 115, 116 |
| **1** | `e2-editor-v10` | **FAIL** | 163, **163**, 393, 509 | **0, 230, 116** |
| **1** | `e2-editor-v11` | **FAIL** | 163, **163**, 393, 509 | **0, 230, 116** |

**Only the second reading differs, and the totals are identical.** Both paths
end at 509. The failing runs miss 278 and then move 230 — which is 115 + 115,
exactly two marks.

So the caret **did** move after the first commit. The reading taken after it was
one commit stale, and the next reading had caught up. A defect that leaves the
end state correct is not a caret that failed to follow; it is a read taken too
early.

## And the read was on a clock

```python
landed = wait_for(session, revision > floor, 25)
time.sleep(1.2)                      # <- here
after = evaluate(session, SINK_POSITION)
```

The check's own comment, written when the defect it covers was fixed, says what
that sleep is sitting on:

> "Before the fix this defect was intermittent at 2/7 — the page's snapshot was
> refreshed once per queued operation and the cursor callback landed one
> sequence later, so whether the caret was current depended on which side of
> that race the read fell."

A fixed sleep decides which side of that race the reading falls on. On a core
that walks its accessibility tree on every caret event, 1.2 s is a different bet
from the one it was on the product core — **0 failures in 11 runs there, 2 in 6
here**.

## What was changed

The sleep is now a poll on the check's **own predicate** — forward in reading
order — with an 8 s deadline, and the wait is recorded per round as
`settledAfterMs`.

**It cannot mask the defect it was written for**, which is the question to ask
of any sleep replaced by a poll: nothing is typed while it waits, so a caret
that only catches up when the *next* commit arrives runs the deadline out and
the check still fails. What the poll removes is the harness reading too early,
and only that.

Polled on the predicate rather than on "the value changed", so a caret that
moved backwards and stayed there still fails instead of being accepted as
movement.

The instrument control's second wait went the same way; the first keeps its
sleep because there is nothing yet to compare it against, and that is said in
the code rather than left to be noticed.

## And then the new instrument refuted the title of this file

The runs with the poll came back and **the check is still red** — with a number
on it:

```
v11 round 4   163->278 (1 ms)   278->393 (1 ms)   393->509 (1 ms)     PASS
v11 round 5   163->278 (1 ms)   278->278 (8013 ms)  278->509 (1 ms)   FAIL
v11 round 6   163->278 (1 ms)   278->393 (1 ms)   393->509 (1 ms)     PASS
v8  (poll)    163->278 (0 ms)   278->393 (0 ms)   393->509 (0 ms)     PASS
```

**8013 ms is the deadline.** The poll asked continuously for eight seconds and
the caret never moved; it caught up only when the *next* commit arrived. Nothing
was typed while it waited, which is why the poll could not mask it — the
property the change was designed around.

So "a stale read" was **wrong**, and this file's own title is left standing as
the record of it. The read was not early; the update was not there to be read.

The distribution says the rest: **0 or 1 ms when it works, 8013 when it does
not, and nothing in between.** That is not latency. It is a dropped update.

## Where it stands

| core | commits measured | dropped |
|---|---|---|
| product `e2-editor-v8` | **42** | **0** |
| a11y `e2-editor-v10` / `v11` | **27** | **3** |

Filed as **finding 084**. Still not established, and still not to be named: WHY
only on that core (two build differences, one measurement) and WHICH layer drops
it — the next question is whether the engine's cursor callback arrives and the
page ignores it, or never arrives, and that needs the engine's caret state
recorded beside `#sink` in the same round.

## What the instrument change was worth

Two things, and neither is "it went green":

* it turned an intermittent red with no number into a red with **8013 ms** in
  the record;
* it **eliminated the competing explanation** — the harness reading too early —
  which was my first reading of the arithmetic and which the measurement killed.
