# Control run 1 contradicted the prediction, and the reason is the fix

Run 2026-08-26, `--liveness-control`, chrome, shipped `e2-editor-v8`.
Prediction: [`PREDICTION-liveness-control.md`](PREDICTION-liveness-control.md).

## What was predicted and what happened

| predicted | measured |
|---|---|
| the run STOPS, `sessionDied` present, `ok: false` | **it did not stop**: 38 PASS / 2 NOT_ESTABLISHED, `ok: true`, `sessionDied: null` |
| it stops at `recovery-returns-what-the-product-promised` | that check PASSED, at 370 s, as on any other run |
| `neverReached` nearly empty | there is no `neverReached`: nothing was skipped |
| the run WITHOUT the flag is unchanged | **confirmed** — 37 PASS / 3 NE, `ok: true`, `liveness.probes: 39` |

## Why the control could not fire

The guard probes **after a recorded check**.  Both arms that induce the dead
state RECOVER BEFORE THEY RECORD THEIRS:

    drag across the endnote reference mark   ->  engine wedges
    one more operation                       ->  recoverable-error
    read the notice, press it, wait for ready
    save, compare, and only THEN  check(...)

So at every check boundary in the run the session is alive, and a control built
on the boundaries alone passes whether the guard works or not.  `probes: 42`
says the guard RAN forty-two times and was satisfied each time — which is the
one thing this run does establish, and it is not the thing the control was for.

This is the same shape the tree already had written down: *every "X did not
happen" arm needs a positive control, or "nothing happened" and "the mechanism
never ran" are the same green.*  Here the positive control itself needed one.

## What was changed because of it

`Liveness.under_control()` — a probe that is a **no-op** without
`--liveness-control` — now sits inside each inducing arm at the point the arm
has just wedged the engine and has not yet pressed the notice.  That is the one
moment in the run where the state is known in advance, and it is a REAL dead
session: the product's own buttons put it there, the real guard reads the real
page.  Only the moment is chosen.

Both directions are held by `tests/test_session_liveness.py`: a `under_control`
that probes unconditionally fails one test (it would stop every ordinary run at
the endnote inducer) and one that never probes fails another.

## The number that came free

Two fixed sleeps in `an-aborted-gesture-stops-selecting` were replaced by polls
on the product's own answer in the same session (see
`queue-abort-margins-are-unexplained`).  What they had been covering:

| wait | was | measured |
|---|---|---|
| caret settles before the drag | `sleep(0.8)` | **1 ms** |
| the copy path answers | `sleep(1.5)` | **202 ms** (200 ms poll granularity) |

Four arms per run, so about 8.4 s of the run was sleeping through an answer that
had already arrived — and, which matters more, a slow answer used to be
invisible where it is now in the record.
