# Finding 059 — the replacement predicate, measured

Round `round-20260818T065756Z`, native core 26.8 (`build-native-26-8`,
`SAL_USE_VCLPLUGIN=svp`), fixture `test-docs/f059-predicate-paragraphs.odt`
(fourteen short unstyled paragraphs, one per arm). Predictions were committed
before the probe existed: [`PREDICTION.md`](PREDICTION.md).

Reproduce: `tools/run_f059_native_predicate.sh`.
Judge: `tools/analyze_f059_predicate.py ROUND_DIR` (self-test 9/9).

**Nothing here describes the WASM build.**

## What came back

Every arm placed its caret by keystroke (Ctrl+Home, Down × N, End) rather than
by clicking a guessed y, so each arm owns a paragraph and no arm's pending
attribute can reach another's marker. The document verdict is the style
**actually attached to that arm's marker run**, resolved through `content.xml`.

| arm | requested | core broadcast | document |
|---|---|---|---|
| control, no command | — | — | unstyled |
| `.uno:Bold` true | true | `.uno:Bold=true` | **bold** |
| `.uno:Bold` false | false | *(nothing)* | not bold |
| `.uno:Italic` true | true | `.uno:Italic=true` | **italic** |
| `.uno:Italic` false | false | *(nothing)* | not italic |
| `.uno:Underline` true | true | `.uno:Underline=true` | **underlined** |
| `.uno:Underline` false | false | *(nothing)* | not underlined |
| `.uno:Strikeout` true | true | `.uno:Strikeout=true` | **struck through** |
| `.uno:Strikeout` false | false | *(nothing)* | not struck through |
| `.uno:Bold` true, view read-only | true | `.uno:Bold=true` | **bold** |

Every scored arm's document outcome equals what was requested — nine of nine.
Every arm reported `success: false`, and `wasModified: true` throughout (the
document was already dirty, which is all that field ever meant).

## Scoring the predictions

| | | |
|---|---|---|
| **P1** Bold applies and broadcasts | **holds** | |
| **P2** `value:false` broadcasts `.uno:Bold=false` | **FAILS** | see below — this is the load-bearing result |
| **P3** Italic behaves as Bold | **holds** for the true arm, fails as P2 for the false arm |
| **P4** Underline broadcasts | **holds** | `.uno:Underline=true` arrives |
| **P5** Strikeout broadcasts | **holds** | `.uno:Strikeout=true` arrives |
| **P6** a refusal produces a result and no state change | **NOT ESTABLISHED** | the arm did not refuse; see below |
| **P7** no selection command is needed | **holds** | no `.uno:SelectText` was issued anywhere |

### P2 failed, and it changes the shape of the fix

Core broadcasts a state **change**, not a state. The caret was already not bold,
so `value:false` produced *no broadcast at all* — while doing exactly the right
thing to the document.

So **"did a broadcast arrive?" cannot be the predicate.** Absence is ambiguous
between *already in the requested state* (a success) and *nothing happened* (a
failure), and a predicate that required an arrival would report failure for four
of the nine arms above, every one of which was correct.

The predicate that survives is the one the format barrier already uses
(`formatBarrierPostconditionMet()`, `src/probe_engine.cpp:1189`): **compare the
observed state against the requested one** — a postcondition on the cached
state, not the arrival of a notification. On these arms that answers correctly
in all nine cases, including the four silent ones.

### P4 and P5 hold, and a comment in our engine is wrong

`src/probe_engine.cpp:4308-4310` states, as the reason underline and
strikethrough keep no format-state cache:

> Neither command appears in core's `GetKitUnoCommandList()`, so no format-state
> cache is kept for them

Both appear in that list (`sfx2/source/control/unoctitm.cxx:1165ff`), the list is
ungated, and both slots demonstrably broadcast here. The cache those two slots
lack is available to them; nothing in core prevents it.

### P6 is not established, and that is a gap not a pass

The intended refusal arm set the view read-only via `setViewReadOnly(doc, 0, true)`
and dispatched bold. **Core applied it anyway** — the broadcast arrived and the
marker came back bold. So the arm is not a refusal, and P6 was not tested.

What that leaves unmeasured: **whether the postcondition predicate can say NO.**
Every arm here is a command that took effect. A negative arm is owed — a caret in
a genuinely protected context, or the WASM build's own failure — before the
predicate is claimed to discriminate rather than merely to agree.

## Not established

* Anything about the WASM build.
* Why core reports `success: false` for commands it applied. Not measured, not
  named (040/048 precedent).
* **Whether the state cache is primed when the predicate needs it.** The
  postcondition reads a cache filled by broadcasts; a caret that has never
  produced one leaves the slot `…Known == false`. Finding 021 is about exactly
  that staleness. Not measured here.
