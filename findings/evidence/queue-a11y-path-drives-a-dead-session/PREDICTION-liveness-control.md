# Prediction, written before the control run

Written 2026-08-26, before `--liveness-control` was run for the first time.
It is here so the run can contradict it.

## What the guard is

`queue-a11y-path-drives-a-dead-session`.  After every recorded check the runner
reads the page's state once.  If it is `recoverable-error` or
`restart-required`, the run stops, names the check after which it noticed, lists
the checks it never reached, and reports `ok: false`.

Two arms drive that state ON PURPOSE and then press the product's recovery
notice, so they hold the guard off for as long as they are inside themselves --
and are read once more on the way out, so an arm that fails to recover stops the
run naming itself rather than the innocent check that follows it.

## Why a control is owed

The guard is written against finding 081, which was measured on the
accessibility profile.  It does not reproduce on the shipped one.  So on every
run this tree normally takes, a guard that had been deleted and a guard that
works produce the same green report -- which is the shape this tree keeps
paying for.

`--liveness-control` stops the two inducing arms holding the guard off.  The
dead session it then meets is REAL: produced by the product's own buttons, read
the same way, on the same page.  Nothing is simulated.

## The prediction

1. The run STOPS.  `sessionDied` is present, `ok` is false, and the verdict says
   the session was dead rather than that a product path is broken.
2. It stops in one of the two inducing arms.  On the shipped profile finding
   047's recipe does NOT block the queue -- `notice-action-recovers-the-session`
   has reported NOT_ESTABLISHED for that reason since 2026-08-17 -- so the
   expected stop is the SECOND inducer, finding 038's endnote drag, and the
   `noticedAfter` should be `recovery-returns-what-the-product-promised`.
3. `sessionDied.pending` is `0`, `checkpoint` is not `無`, and the state is
   `recoverable-error`.  (`pending: 0` is the field that separates finding 081
   from a hang.  The checkpoint differs from 081's because THIS inducer takes
   one before it wedges, which is the whole subject of that arm.)
4. `neverReached` is EMPTY or nearly so, because 038's arm is the last check in
   the run.  That is the honest limit of this control: it shows the guard fires
   on a real dead session, and it does NOT show it saving twenty to fifty
   minutes.  Only an accessibility run can show that, and only if that run dies.
5. The run WITHOUT the flag, taken first, is unchanged: no `sessionDied`,
   `liveness.probes` roughly one per check plus two region exits, and the same
   verdict the shipped profile has been giving.

If instead the run stops at `bulleting-a-blank-line-does-not-demand-a-rollback`,
then finding 047's recipe has started blocking the queue again on the shipped
profile, which is `queue-047-may-have-closed-under-048` answering itself, and
the control has found something the net was not looking for.
