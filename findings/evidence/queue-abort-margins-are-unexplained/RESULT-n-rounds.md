# Eight rounds green, three rounds red, and the wall-clock sleeps are gone

Measured 2026-08-26 on the shipped `e2-editor-v8`, chrome, one machine, one
sitting, nothing else running. This answers the two debts
`queue-abort-margins-are-unexplained` was left open for on 2026-08-23:

> "this is ONE run each way. An intermittent margin measured once gives a
> confident and wrong answer, and that is the whole history of this check. It
> wants N consecutive rounds before `the pointercancel and blur wiring is
> verified` is a sentence anyone may write. Also still unexamined: the reads are
> still synchronised on wall-clock sleeps."

## The rounds

| run | mutation | control | reference | abort arms | outcome |
|---|---|---|---|---|---|
| `shipped-v8-chrome` | — | `E1-LC-ISOLATED 前後都不是清單的` | `E1-LC-ISOLAT` | 12, 12 | PASS |
| `control-liveness` | — | same | same | 12, 12 | PASS |
| `control-liveness-2` | — | same | same | 12, 12 | PASS |
| `refusal-diagnostic` | — | same | same | 12, 12 | PASS |
| `refusal-diagnostic-mutated` | `cut-swallows-the-refusal` | same | same | 12, 12 | PASS |
| `abort-round-3` | — | same | same | 12, 12 | PASS |
| `abort-round-4` | — | same | same | 12, 12 | PASS |
| `abort-round-5` | — | same | same | 12, 12 | PASS |
| `abort-mutated-1` | `gesture-abort-not-wired` | same | same | **23**, 12 | **FAIL** |
| `abort-mutated-2` | `gesture-abort-not-wired` | same | same | **23**, 12 | **FAIL** |
| `abort-mutated-3` | `gesture-abort-not-wired` | same | same | **23**, 12 | **FAIL** |

**Eight consecutive PASS and three consecutive detections**, and every one of
the eleven aimed at the same line and selected the same strings — no drift in
the aim across an hour, which is what the shared-aim fix of 2026-08-23 was for.
The one mutated PASS row is a different mutation (it moves the cut path and
leaves this check alone), which is why it belongs in the PASS column.

The detections are the oracle's own reason, three times: the arm whose
`pointercancel` listener the mutation removed **followed the pointer to the
end** — 23 code points, byte-identical to the control — while the still-wired
`blur` arm stopped at the reference's 12. One listener gone and one intact,
differentiated inside a single run on a single line.

So the sentence is now available: **the pointercancel and blur wiring is
verified.** It rests on eleven rounds, not one.

## The wall-clock sleeps, and why the two fields the queue item named cannot serve

The item asked for reads synchronised on "the `revision` / `callbackSequence`
fields the selectRange envelope already carries". Measured: **neither can serve
this arm.**

* `revision` is the **document's**, and a selection is not an edit — it does not
  advance on a `selectRange` at all. Waiting for it to move would wait forever.
* `callbackSequenceBefore/After` never leave the page's own closure. `pumpDrag`
  reads the envelope and publishes only `#toolbar[data-selection-shape]`
  (`web/e2-editor-app.js:865`). Publishing them is a product change and a shell
  generation, for a field only a harness would read.

What the page *does* publish is the answer itself, so both sleeps were replaced
by polls on it: the caret settle waits for the shape to read "no range", and the
copy waits for the toast the copy path writes. Both are recorded per arm, so a
wait that starts taking seconds becomes a measurement instead of a silence:

| wait | was | measured, every round |
|---|---|---|
| caret settles before the drag | `sleep(0.8)` | **0–1 ms** |
| the copy path answers | `sleep(1.5)` | **201–203 ms** (200 ms poll granularity) |

Four arms per round, so roughly 8.4 s per run was spent sleeping through an
answer that had already arrived. The 202 ms is a bucket, not a latency — the
poll interval is 200 ms — and it is there to show movement, not to be a
benchmark.

## What is still not established

* Anything about Firefox. Every round here is Chrome.
* That the aim is stable across **documents**. All eleven rounds open the same
  fixture and land on the same line; what was shown is that the shared aim does
  not drift between arms or between runs, not that another document would
  resolve at all.
