# Finding 048, native arm — predictions registered before the probe was written

Written 2026-08-16, before `tools/f048_native_click_latency.cpp` existed.  The
judging is offline (`tools/analyze_f048_native.py`) so the run and the criteria
stay separable.

## The question

The product's click takes **22–28 ms (Chrome) / 23–33 ms (Firefox)** to take
effect, measured by polling at 5 ms in the browser.  `EditorSession.placeCaret`
now waits for the engine to acknowledge it, so the product is no longer harmed.
What is still unknown is **why 22–28 ms**, and that decides whether this is
upstream's problem or ours.

Finding 048 names two hypotheses and says not to write either one down before
it is measured:

| | hypothesis | the product remedy it implies |
|---|---|---|
| **A** | the mouse event sits in a queue and core processes it late | wait for the engine |
| **B** | core moves the caret promptly and `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` arrives late | wait for the callback |

Native separates them because nothing in a native run crosses a worker, a
`postMessage` boundary or a browser event loop.  **Nothing produced here
describes the WASM artifact**, and this file does not claim it does — the same
rule finding 016 and finding 045 ran under.

## What the probe does

One document (`test-docs/e1/list-contexts.odt`), one core install
(`build-native-26-8/instdir`), coordinates **measured rather than guessed**: a
phase-0 walk with cursor commands records the visible-cursor rectangle at each
paragraph, and every later arm reuses those measured positions.

Every callback is timestamped on arrival from one `steady_clock`, and the
timestamp of each `post*` call is recorded on the same clock.  The two derived
numbers per arm are:

- **`firstCallbackMs`** — post → the first callback of any type attributable to
  this arm.  This is "when did core start telling anyone anything".
- **`cursorRectMs`** — post → `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` carrying
  a rectangle on the requested line.  This is what `placeCaret` waits for.

Five arms, one variable each, five repetitions per arm:

| arm | what it is | what it controls for |
|---|---|---|
| `N1 click-cold` | first click after load and paint, at a different paragraph | the state the D3 harness was actually in |
| `N2 click-warm` | a later click at a different paragraph | whether the first one pays a one-off cost |
| `N3 click-same` | a click at the position the caret is already on | 048 says the engine says nothing here; the product's 400 ms quiet rule rests on it |
| `N4 uno-godown` | `.uno:GoDown`, a cursor command, not a mouse event | separates "queued work is slow" from "mouse events are slow" |
| `N5 set-text-selection` | `setTextSelection(RESET)` at the same coordinates | the gesture the harness used, which appeared to land synchronously |

## Predictions

Scored exactly as written.  "The behaviour is reasonable" is not a pass.

- **P-N1** — `N1.firstCallbackMs` median **< 5 ms**.  (I expect core to start
  reacting promptly and the 22–28 ms to belong to our side of the boundary.)
- **P-N2** — `|N1.cursorRectMs − N1.firstCallbackMs|` median **< 2 ms**, i.e.
  the cursor rectangle is not systematically later than the other signals the
  same click produces.  **If P-N2 holds, hypothesis B does not.**
- **P-N3** — `N3` produces **zero** callbacks within a 900 ms drain.
- **P-N4** — `N4.cursorRectMs` is within **2×** of `N2.cursorRectMs` in either
  direction, i.e. the latency is not specific to mouse events.
- **P-N5** — `N5.cursorRectMs` **≤** `N2.cursorRectMs`.

## Decision rule, registered in advance

Applied to the **median of `N2.cursorRectMs`** across three whole executions of
the probe:

| measured natively | conclusion | what happens next |
|---|---|---|
| **≥ 20 ms** | core's own latency: an upstream candidate | write the upstream section of finding 048 and build a reproduction package.  Do **not** submit — submissions are on hold |
| **≤ 2 ms** | our side (worker scheduling / transport), not core | record it in 048's mechanism section and close that checkbox.  No upstream report |
| **2–20 ms** | not separated | record "mechanism not separated" and name the next variable to control, rather than picking the nearer edge |

## Addenda, each with the moment it was made

Written down because "when did you know that" is the only thing that separates a
correction from a rationalisation.

### A1 — the walk needed a second measured path (before any arm data existed)

The first two attempts produced no arm data at all: `attempt-01` died in LO's
userinstall (a relative OUTPUT_DIR makes `file://../...`), and `attempt-02`
reached the walk and found that **`.uno:GoDown` on `list-contexts.odt` emits no
`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` at all** — 186 callbacks, 177 of them
`STATE_CHANGED`, exactly one cursor rectangle and that one from the load.  The
same walk on `styled-list.odt`, same install, same probe binary: 23 cursor
rectangles and a completed run.

`list-contexts.odt` is the document the 22–28 ms was measured on, so changing
the fixture would have added a second variable.  The probe gained a fallback
instead: search for the named anchors and take the rectangle core returns.
**The coordinates are still measured, not guessed** — which is the property
that mattered, not the command used to reach them.

This is an observation in its own right and it is kept: a document on which
cursor commands move the caret without announcing it is a document on which
anything waiting for that announcement waits forever.  `attempt-02` is retained
as its record.

### A2 — what a `OUR_SIDE` verdict is allowed to conclude (before any arm data existed)

External review (fable, same day, while both attempts had produced zero arm
measurements) pointed out that the `≤ 2 ms → our side` branch skips a third
suspect, and that this tree has the precedent: **finding 040 was clean natively,
broken on WASM, and still upstream** — an Emscripten-build-specific scheduler
integration.

The thresholds are unchanged.  What is narrowed is what the branch licenses:

> `OUR_SIDE` concludes **"the wait is not in core's click handling"**.  It does
> **not** identify where the wait is.  Separating our transport and worker
> scheduling from the Emscripten main-loop integration is a further measurement,
> and until it is made, neither may be named as the cause.

### A3 — two judge fixes made AFTER round one's data existed

Both are in `tools/analyze_f048_native.py`; neither touches the recorded
evidence, and **neither converts a FAILED prediction into a HELD one**.

1. **Mid-line comparison.**  The judge compared the callback rectangle's *top*
   against a target that is the *middle* of the line, which puts every correct
   landing exactly on the tolerance boundary; three of round one's five N2
   repetitions were scored as misses while the caret was on the right line.
   Now both sides are mid-line.  This changes how many repetitions contribute a
   sample; it does not change the latency of any of them.
2. **`NOT_MEASURED` is no longer folded into `FAILED`.**  `.uno:GoDown` emitted
   nothing on this fixture (A1), so P-N4 had no data — and a prediction with no
   data behind it is not a refuted prediction.  The self-test's P-N4 mutation
   was changed accordingly: it now *adds* a callback (NOT_MEASURED → scored),
   because delaying callbacks that do not exist could never move a verdict.

## What voids the round

- The three executions disagree by more than an order of magnitude on
  `N2.cursorRectMs` — then this is measuring the host, not the engine.
- Phase 0 fails to measure a rectangle for a paragraph: an arm aiming at a
  guessed coordinate measures nothing, and is recorded as skipped rather than
  as a result.
- The probe is run against an install whose core commit differs from the one
  the WASM profile was built from — the comparison then has two variables.  The
  commit is recorded in the output and checked by the analyzer.
