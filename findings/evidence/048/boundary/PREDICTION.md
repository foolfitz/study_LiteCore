# Finding 048 — which side of the worker boundary the 22 ms is on.  Registered before the harness existed.

Written 2026-08-16.  048's own open item names the next controlled variable:

> **the rest of it is where?** 0.6 ms natively against 22–28 ms in the browser,
> forty times, and that gap has not been separated into "our transport / worker
> scheduling" and "Emscripten main-loop integration".  040's precedent says the
> latter may still be upstream, so **neither may be written as a conclusion
> until it is measured.**
> Next controlled variable: timestamp the moment `postMouseEvent` goes out and
> the moment the worker sees the cursor callback, and see which side of the
> worker boundary the 22 ms falls on.

## What can be timestamped without touching anything

The shipped worker cannot be instrumented — it is one of the hashes the verdict
binds.  It does not need to be.  The click already produces **two** observable
moments in the page, not one:

| symbol | moment | what lies between it and the previous one |
|---|---|---|
| `t0` | the page calls `handle.click(x, y)` | — |
| `tResponse` | the click's promise resolves | postMessage out, worker dispatch, the synchronous call into wasm that posts the mouse event, the response postMessage back |
| `tInvalidated` | the page receives `document-invalidated` (LOK callback id 0/1, forwarded unconditionally by the shipped worker) | **core's own processing plus the Emscripten main loop**, then one worker→page hop |

And a calibration the same page can take: **`Δrt`**, the round trip of
`editorGetStateV2`, a request that crosses the same boundary in both directions
and asks the engine for a value it already holds.  That is the transport floor,
measured rather than assumed.

The split follows: `Δ1 = tResponse − t0` is transport plus the synchronous
post; `Δ2 = tInvalidated − tResponse` is everything on the engine's side of the
boundary.

**This is the SDK path, and that is declared**: the product's `placeCaret` sits
on top of `handle.click`, and 048's fix made it wait for the caret.  Waiting is
what this round is trying to take apart, so it drives the layer underneath it.

## Fixture and gesture

`e1-fixtures/list-contexts.odt` — the same document the 22–28 ms was measured
on, on purpose.  Ten clicks, alternating between two anchors located by the
product's own `search` so the caret really moves each time (a click on the line
the caret is already on may produce no cursor callback at all — measured in the
native round, where three arms produced zero callbacks).

## Predictions

- **P-048B-1** — `Δrt` (the getState round trip) has a **median ≤ 3 ms** in both
  browsers.  This is the transport floor; if it is not small, the whole split is
  uninteresting and the round says so.
- **P-048B-2** — `Δ1` is **within 2× of the `Δrt` median**.  Posting the mouse
  event is not where the wait is.
- **P-048B-3** — `Δ2` is **≥ 10 ms** and is **≥ 70 %** of `tInvalidated − t0`.
- **P-048B-4** — `tInvalidated − t0` lands in the band the D3 caret probe
  measured for the same gesture on the same document: **15–40 ms**.  If it does
  not, this round is measuring something else and the split does not transfer.
- **P-048B-5** — at least 8 of the 10 clicks produce a cursor invalidation.
  Recorded rather than assumed, because the native round measured a gesture that
  produced none.

## The decision rule, written before the data

- **P-048B-2 and P-048B-3 both hold** → the wait is on **the engine's side of
  the worker boundary**.  That excludes our transport and our worker scheduling,
  and it is as far as this round goes.
- **P-048B-2 fails** → the wait is (at least partly) in the transport, which is
  ours, and 048 gets a product-side item instead of an upstream question.
- **P-048B-3 fails** → the total is not dominated by either side and the round
  reports that the split does not exist at this granularity.

**What this round may NOT conclude, whatever the numbers**: that the remainder
is Emscripten's main-loop integration.  Native measured core's own click
handling at 0.6 ms, so subtracting gives a residue — but a residue is not an
attribution, and finding 040 is the precedent for exactly this mistake (a
condition an Emscripten build never sets, blamed on the wrong layer for weeks).
The next controlled variable after this one is an engine-side timestamp, and
that needs a diagnostic build.

## What voids the round

- Fewer than 8 of 10 clicks produce an invalidation: reported as measured, and
  the deltas are computed only over the clicks that did.
- The caret does not move to the clicked anchor: that click is recorded with its
  readback and excluded from the deltas, not retried.
- The artifact hashes do not match the frozen four.
