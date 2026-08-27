# The second inducer exists, and the recovery path is covered on both cores

`queue-recovery-inducer-depends-on-an-unfixed-defect`, 2026-08-28.

## What it is

An **uncaught error inside the document worker**. That is the failure class
`DocumentSdk._handleCrash` listens for (`worker.addEventListener("error", ...)`,
document-sdk.js:126-129). It depends on no upstream defect, needs no product
change and no test-only affordance: the trigger is synthetic, the failure and
everything after it are the product's own.

Only the killing step is new. The checkpoint is already written by the selection
gesture the arm performs -- measured on `e2-editor-v11`, `有（r2）`, even on the
core where finding 038 no longer wedges anything -- so the branch under test is
the same one the 038 route exercises on the shipped profile.

## Measured

| | `e2-editor-v8` (shipped) | `e2-editor-v11` (a11y) |
|---|---|---|
| `finding038Reproduced` | **true** | **false** |
| `fallbackInducer` | **never fires** | `fired: true` |
| state after it | — | `recoverable-error` |
| `declaredCheckpoint` | `有（r2）` | **`有（r2）`** |
| `branch` | `checkpoint` | **`checkpoint`** |
| `noticeWasOffered` / `Enabled` | true / true | **true / true** |
| saved / unsaved work back | true / true | **true / true** |
| `declarationHonoured` | true | **true** |
| the check | PASS | **PASS** |
| the run | 38 PASS / 2 NE | **38 PASS / 2 NE**, was 37 / 3 |

**The checkpoint survives the worker crash**, which was the open question that
could have gone the other way: had it not, this arm would have gone red and that
would have been a finding rather than a harness problem.

The shipped profile is the regression control and it is clean: 038 still
reproduces there, the fallback is never reached, and nothing about that path
changed.

## The NE delta is closed

An adjudication on the cutover asked which check makes v11's runs 37/3 against
v8's 38/2, and called it *a finding wearing an NE costume* -- the net counts
NOT_ESTABLISHED as neither, so a reader of `ok: true` could not see that the
product's safety net for unsaved work was covered by nothing on the profile a
cutover would ship. It was this check. It is now PASS on both.

## The acceptance condition changed, deliberately

NOT_ESTABLISHED here used to mean *finding 038 no longer reproduces* -- the loud
exit, and the right answer while there was only one way in. It now means what it
should always have meant: **no inducer could reach the state at all**. 038 not
reproducing is still recorded (`finding038Reproduced`), because that is a fact
about that core; it just no longer costs the coverage. The reason is written at
the branch in `run_e2_c_product_path.py`, not only here.

## How it was found, and the lesson that repeats

The worker cannot be reached the obvious way. `Target.getTargets` reports eight
`worker` targets with **empty urls** -- the verified loader builds the worker
from a blob and the wasm's pthreads each take a target -- and
`Target.attachToTarget` on any of them returns a real sessionId to which nothing
is ever answered, `Runtime.enable` included, from the page connection and from a
second connection to the browser endpoint.

`Target.setAutoAttach` works: it delivers exactly one session, for the page's own
dedicated worker, and the url is in the **event** even though `getTargets`
reports it empty. It reaches a worker that already exists, so this runs mid-arm
rather than before the page loads -- which is why it is a helper and not a change
to the session class every runner shares.

**Three times in one day, a thing that arrives as an EVENT was thrown away by a
reader written for request/response.**

1. The first auto-attach probe polled with `ChromeSession.call`, which discards
   every message whose id does not match. All eight attachments arrived inside
   that loop. It reported zero.
2. Wired into the runner, `induce_worker_failure` called `setAutoAttach` through
   the same helper -- and Chrome emits `Target.attachedToTarget` **before** it
   answers the command, so the events were discarded again. The report said
   "auto-attach delivered no session for a document worker" on a run where every
   attachment had happened. That file is kept:
   `v11-fallback-could-not-fire.json`.
3. Earlier the same day, finding 084's own instrument dropped `sid` from its
   record and left two write-ups reasoning about the wrong thing.

The fix is eight lines of reading the socket directly, and the reason is written
where the lines are.

**And one hypothesis was refuted by a control rather than by a fix.** The plan
had been to tell the document worker from the pthreads by responsiveness --
pthreads sit in `Atomics.wait` with their event loop stopped. `Runtime.enable`
is answered by the browser rather than by the target's JavaScript thread, and it
timed out too, so the silence was never about blocked threads. Without that
control the write-up would have said "the pthreads are blocked, so they cannot be
asked": plausible, tidy, and wrong.

## Files

* `probe_autoattach.py` -- the probe that found the route
* `v11-fallback-could-not-fire.json` -- the run where the events were discarded
* `v11-fallback-fired-and-the-arm-passed.json` -- the same arm, after
* `v8-control-fallback-never-fires.json` -- the shipped profile, untouched
