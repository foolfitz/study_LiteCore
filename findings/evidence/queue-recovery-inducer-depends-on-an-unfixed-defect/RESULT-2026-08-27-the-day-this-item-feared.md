# The day this item feared has arrived, and the first remedy did not land

2026-08-27.

## The item's own prediction, now measured

This item was written because the only route into `recoverable-error` is finding
038 staying broken: "When 038 is fixed the inducer will vanish again --
silently, unless something is watching."

It has not been fixed. It has stopped reproducing on one core.

| profile | `recovery-returns-what-the-product-promised` |
|---|---|
| shipped `e2-editor-v8` | **PASS**, every run |
| a11y `e2-editor-v11` | **NOT_ESTABLISHED**, 5 runs of 5 |

The report says why in its own words: *"the inducer did not put the session into
a state where the product OFFERS its recovery button... this is the loud exit for
038 no longer reproducing, NOT a silent pass."*

**The watching worked.** The consequence stands anyway: on the profile a cutover
would ship, the recovery path -- the checkpoint and the "return to your
checkpoint" button, the product's safety net for a user's unsaved work -- is
covered by nothing at all. An adjudication on the cutover called this *a finding
wearing an NE costume*, because the net counts NOT_ESTABLISHED as neither PASS
nor FAIL, and a reader who looks at "37 PASS / 3 NE, ok: true" will not see it.

## The first candidate: a real worker failure, induced from outside

The item names two candidates. The first attempted was neither of them exactly:
provoke a **real uncaught error inside the document worker** over CDP. That is
the failure class `DocumentSdk._handleCrash` listens for (`worker.addEventListener
("error", ...)`, document-sdk.js:126-129), it depends on no upstream defect, and
it requires no product change -- the failure is induced from outside the product
entirely.

It did not land. Three things were established and one was not.

**1. The worker cannot be found by URL.** `Target.getTargets` reports eight
`worker` targets and every one has an EMPTY url -- the verified loader builds the
worker from a blob, and the wasm's pthreads each occupy a target of their own.

**2. Nothing addressed to an attached worker session is answered.** Not
`Runtime.evaluate`, and not `Runtime.enable`. On all eight targets. From the
page-scoped connection AND from a second connection opened to the browser
endpoint (`/json/version`'s `webSocketDebuggerUrl`).

**3. It is NOT that the worker threads are blocked** -- and that mattered,
because it was the hypothesis. The plan was to use responsiveness as the
discriminator: pthreads sit in `Atomics.wait` with their event loop stopped,
while the document worker is idle-but-responsive, so the one that answers is the
one to crash. **`Runtime.enable` is answered by the browser, not by the target's
JavaScript thread, and it times out too.** So the silence is not eight blocked
threads.

Without that discriminator the write-up would have read "the pthreads are
blocked, so they cannot be asked" -- plausible, tidy, and wrong. Every "X did not
happen" arm needs a positive control, and this is the third time this tree has
paid for learning it.

**What is not established: why the attached sessions are silent.** A symptom, not
a diagnosis. Saying more than that would be inventing the part that was not
measured.

## Where this stops, and why it stops here rather than continuing

The next step is a design choice rather than a detail, so it is not one to make
while nobody is looking:

* keep digging at CDP, now that "the threads are blocked" is ruled out;
* take the item's second candidate -- a deliberately short `timeoutMs`, `TIMEOUT`
  being in `RECOVERY_ERRORS` -- which needs a seam the product does not expose
  today, i.e. a change to the product for the benefit of a test;
* accept the gap and record it as a named limit of the accessibility lineage:
  *the recovery path is not exercised on this core, and no run on it may be read
  as evidence that a user's unsaved work is protected*.

The third is not the same as doing nothing, but it is the one that must be
decided out loud rather than arrived at by silence -- which is exactly the shape
this item was opened to prevent.

## Files

* `probe_worker_inducer.py` -- the probe, including the discriminator
* `attach-is-silent-from-both-connections.json` -- its output
