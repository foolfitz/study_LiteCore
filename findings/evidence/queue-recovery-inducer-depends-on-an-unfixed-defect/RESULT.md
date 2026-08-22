# Result (2026-08-21) — no defect-independent inducer found; three candidates eliminated

`queue-recovery-inducer-depends-on-an-unfixed-defect`. The obligation the queue
item states was honoured first: **show a candidate LANDS in `recoverable-error`
rather than being refused by name**, before anything is wired into the
regression net. Nothing was wired. Probe:
`tools/probe_second_recovery_inducer.py`, stamped `evidenceClass: "diagnostic"`.

## Why this stopped being hypothetical

The debt was written as "when 038 is fixed the inducer will vanish". **On Firefox
it already has.** Measured 2026-08-21: `recovery-returns-what-the-product-promised`
reports `NOT_ESTABLISHED` there because 038's recipe does not reproduce. So the
recovery coverage is already gone on one of the two supported browsers.

## Candidate 1 — `selectRange` with a short `timeoutMs`. NOT REACHABLE.

`TIMEOUT` is in `RECOVERY_ERRORS` (`editor-shell/editor-session.js:15-22`), so
the error class is right. The route is not: the product constructs its session
**without** `selectionTimeoutMs` (`web/e2-editor-app.js:762`), so it defaults to
5000 (`editor-session.js:84`) and nothing outside the page can change it.

Reaching it would mean putting test-only configuration into the product. Rejected
on that basis, not on the error class.

## Candidate 2 — terminating the worker. NOT PUBLIC API, AND WRONG SHAPE.

`_worker.terminate()` is private and reached only inside `restart()` /
`dispose()` (`sdk/document-sdk.js:333`). It is also not a selection gesture, so
it could not satisfy the **capability clause** on
`recovery-returns-what-the-product-promised` (fable's 2026-08-18 adjudication,
`run_e2_c_product_path.py:3316`): when the inducer is a selection gesture on a
dirty document, the declaration may not be 無.

The queue item calls both candidates "reachable through public API". **For this
one that is wrong**, and the item is corrected.

## Candidate 3 — a selection that genuinely takes too long. DID NOT REACH.

A whole-canvas drag in a long, dirty document. No product change, an ordinary
thing for a user to do, and it IS a selection gesture on a dirty document.

| pages | state after | reported latency | checkpoint |
|---|---|---|---|
| 40 | `ready` | `定位游標 160 ms` | 有（r1） |
| 200 | `ready` | `定位游標 401 ms` | 有（r1） |

`recoverable-error` was not reached, and the notice was never offered
(`shown: false`, `rescue: "none"`) on either arm.

### What this arm does NOT establish, and the limitation is the point

**It does not establish that a range was selected at all.**

* The reported latency is `定位游標` — **placeCaret's**, not the selection
  readback's. The pre-gesture checkpoint fired (`有（r1）`), which shows the shell
  treated it as a selection gesture, but that is the shell's bookkeeping, not the
  engine's answer.
* So "the selection did not time out" is **not supported**. What is supported is
  the narrower "the session did not enter `recoverable-error`".

This is the **third** check today that needed a positive control and did not have
one — after the caret oracle's tie-break and the aborted-gesture check, whose
`gesture-abort-not-wired` mutation stayed green because the drag had never
started. Two data points from an arm that cannot show its own precondition are
two data points about nothing in particular.

**Do not escalate the page count further until the probe can show a range was
selected.** Increasing a parameter until something breaks, on an arm that cannot
prove it is exercising the mechanism, is how a number gets attached to a
measurement that never happened.

## Where this leaves the item

**Open, and narrowed.** The remedy is now one of:

1. make the product's selection timeout configurable — which puts test-only
   configuration in the product, and should be argued rather than assumed;
2. find a route this round did not think of; or
3. accept that recovery coverage depends on an upstream defect, and say so where
   the checklist can see it.

The check already reports `NOT_ESTABLISHED` and names 038 rather than passing
quietly, so the loud exit is intact and nothing regressed. What is not true is
the queue item's claim that two candidates are "both reachable through public
API".

## Next step, before any retry

Give the probe a **positive control**: show that the drag produces a range —
through something that reads the engine's answer rather than the shell's
bookkeeping, e.g. the copy path's `codePoints`, which the product-path runner
already uses. Without it, every arm here is unfalsifiable in the same way.
