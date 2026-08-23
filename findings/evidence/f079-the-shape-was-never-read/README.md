# Finding 079 — the page's selection shape was not stale; it was never read

Measured 2026-08-23 with `wasm_sdk_probe/tools/probe_079_selection_shape.py`,
against the **shipped** `e2-editor-v7` page (no `--profile`).

Finding 079 was raised indirectly the day before: a mutation gated on
`lastSelectionShape !== "collapsed"` never fired on two runs. That is consistent
with a stale shape — and equally consistent with the mutation not being
installed, with the press taking another path, or with the drag never selecting
anything. The finding said so and named three candidate mechanisms, all of them
about a value arriving late or being reset.

**All three were wrong. There was no value.**

## The instrument

Two answers, recorded in the same arm, because this tree spent 2026-08-23
signing five conclusions with some other thing's measurement:

* **what the page believes** — from the toolbar. `updateGestureAffordance()`
  writes `manifest 沒有為「SHAPE」宣告這個動作` into the title of every button it
  disables, so a disabled caret-only button *names* the shape the page holds and
  an enabled one says the page holds `collapsed`.
* **what the engine believes** — through the product's own copy path, whose
  toast comes from `copySelection()`. A canvas has no DOM selection, so nothing
  else in the page could answer.

Sampling runs **inside** the page from the moment the pointer goes down, keeping
a row whenever the toolbar changes, so "arrived at 900 ms" is distinguishable
from "never arrived" without paying a CDP round trip per sample.

## Positive control first

`positive-control-instrument-can-show-a-range.json` — a mirror whose only
difference is that `lastSelectionShape` **starts** as `range-single`. All six
caret-only buttons are disabled and every title reads `range-single`.

⇒ The toolbar read can show a range. Everything below is about the page, not
about the instrument.

## Before the fix

`before-fix-three-arms.json`

| arm | engine | page | changed within 8 s? |
|---|---|---|---|
| click, no drag (control) | 0 chars | `collapsed` | no — **the two agree** |
| drag inside one line | **12 chars** | `collapsed` | **never** |
| drag across two lines | **34 chars** | `collapsed` | **never** |

The toolbar did not change once in an eight-second sampling window. Not late.
Never.

## Why never: the two fields are not on that object

`what-selectrange-resolves-to.json` — a mirror with **one added statement**
after the `await`, recording what `session.selectRange()` actually resolves to.

```
top-level keys: method, revision, completion,
                callbackSequenceBefore, callbackSequenceAfter, state
```

No `collapsed`, no `rectangles`. They are one level down:

```
state.selection = { observed: true, collapsed: false, start, end, rectangles: [...] }
```

`editor-shell/editor-client.js` (the **v1** path) assembles
`{collapsed, text, rectangles, caret, revision}`. The **v2** path assembles
nothing: `ParagraphEditorClient.selectRange` returns the worker's envelope
verbatim. The page was reading the v1 shape.

```js
(result?.rectangles?.length ?? 0) > 1        // undefined?.length ?? 0 → 0
  ? "range-cross"
  : (result?.collapsed === false             // undefined === false → false
     ? "range-single" : "collapsed");        // ⇒ always "collapsed"
```

No input can make that expression return anything else.

Both branches measured, not just the one a within-line drag reaches:

| drag | `state.selection.collapsed` | rectangles | correct shape | page computed |
|---|---|---|---|---|
| inside one line | `false` | 1 | `range-single` | `collapsed` |
| across two lines | `false` | 3 | `range-cross` | `collapsed` |

## After the fix

`after-fix-three-arms.json` — `pumpDrag` reads `result?.state?.selection`, and
an unreadable result keeps the previous value and raises
`#toolbar[data-selection-unreadable]` rather than manufacturing `collapsed`.

| arm | engine | page | page caught up at |
|---|---|---|---|
| click, no drag | 0 chars | `collapsed` | — |
| drag inside one line | 12 chars | **`range-single`** | **52 ms** |
| drag across two lines | 34 chars | **`range-cross`** | **55 ms** |

52–55 ms. It was never a latency problem.

## The predicted consequence was unreachable, and reading the page says so

079 predicted the cost would land on `delete-selection` — offered for ranges
only, so a stale `collapsed` would show it DISABLED when it is available.

It cannot. `lastSelectionShape` is read in exactly one place,
`updateGestureAffordance()`, which touches only `#toolbar button[data-action]`.
There is no `delete-selection` button, and its only dispatch site (the cut
handler) asks `session.offers("delete-selection")` — the manifest, not the
shape.

The cost lands on the other side of the same gate: six buttons are offered for
`collapsed` only (both character moves, both deletes, both breaks), so a shape
stuck at `collapsed` left all six **enabled** while a range was selected, where
the engine's mask refuses them.

## Finding 080 rides along, and the product-path runs are why

`product-path-shipped-before-fix.json` — the shipped page before any of this:
33 PASS / 6 NOT_ESTABLISHED, `ok: true`. Among the abstentions is
`an-aborted-gesture-stops-selecting`, which had been abstaining since
2026-08-21 while declaring the harness at fault. It asked "are the four format
buttons disabled?" and meant "is a range selected?" — a proxy poisoned by this
very defect, and then broken a second time by `e2-editor-v7` offering those
buttons for ranges. See finding 080.

`product-path-abort-check-red-on-its-own-predicate.json` — **kept because it is
wrong**. After re-aiming that check at `#toolbar[data-selection-shape]` it went
RED for the first time ever: control `true`, and both abort arms `true`.

That red is the **predicate**, not the product. `ABORT_DRAG` moves once *before*
it aborts, so a selection from the start to that midpoint is correct on every
arm — the abort is meant to stop the *next* move, not undo the last one. "A
range exists" is therefore true whether the wiring works or not, which is
exactly the pair the check exists to separate.

## The mutations that hold the new check

`mutation-silent-wrong-place-detected.json` — `selection-shape-from-the-wrong-place`
restores the defect in its **silent** form: engine 3 code points, page
`collapsed`, `unreadable: false`. FAIL. "The mutation was detected by the check
that owns it."

`mutation-unreadable-flag-detected.json` — `selection-shape-unreadable` makes the
accessor always answer `null`: engine 5 code points, page `collapsed`,
**`unreadable: true`**. FAIL. This is the arm that proves the unreadable branch
is wired, and it shows the degenerate case in the open — the shape stays
`collapsed`, which is why the check reads the flag rather than the shape.

## And then the abort check found an instrument defect, which is the point

`abort-check-arms-read-different-lines.json` — the run after all of the above.
The abort check FAILED with margins of **minus four**:

| arm | selected |
|---|---|
| control | `1-LC-H`, band `[83,182]` |
| pointercancel | `E1-LC-ISOL` |
| blur | `E1-LC-ISOL` |

**Different strings. Different lines.** Each arm called `stable_bands` for
itself and took the first band wider than 40 px, and that scan is intermittent
on this core (finding 075: 10 bands at rest for 9 lines in one round of five).
The arms were never comparable.

That single cause explains every unexplained number this check produced — the
control's reach moving 11 → 6 between runs, the one-character margin where the
coordinates predict five, the mutated arm reporting zero — **and it means the
run where the check PASSED passed by luck.** An external adjudication had said
to explain the control's instability before trusting any margin, and this is
what was behind it.

Fixed by deriving the aim ONCE and sharing it across all arms. With the
comparison valid, the weak strict-prefix predicate had no excuse left and was
replaced by the strong one: a fourth **reference** arm makes the same moves and
stops where the others abort, so the expected answer is *driven* rather than
predicted from pixels — which matters, because the text is proportionally
spaced and a pixel-to-character model would have been the weakest link.

The failing versions are kept here. A newly-armed check's first red is a
measurement; this one was red three times, for three different reasons, and only
the third was about the product's own instrument.

## The abort check, finally coherent

`abort-check-final-pass.json` — the shipped page, one aim shared by four arms,
the aim spanning 90% of the widest band, and the expected answer driven by a
reference arm rather than predicted from pixels:

| arm | selected |
|---|---|
| control (no abort) | `E1-LC-ISOLATED 前後都不是清單的` |
| reference (stops at the abort point) | `E1-LC-ISOLAT` |
| pointercancel | `E1-LC-ISOLAT` |
| blur | `E1-LC-ISOLAT` |

Byte-exact agreement with the reference on a 14-vs-9 margin. **38 PASS / 2
NOT_ESTABLISHED, `ok: true`.**

`abort-check-final-mutation-detected.json` — `gesture-abort-not-wired`, and this
time the red is the oracle's own sentence rather than an empty-string guard:

| arm | selected |
|---|---|
| control | `E1-LC-ISOLATED 前後都不是清單的` |
| reference | `E1-LC-ISOLAT` |
| **pointercancel, UNWIRED** | **`E1-LC-ISOLATED 前後都不是清單的`** — followed the pointer to the end |
| blur, still wired | `E1-LC-ISOLAT` — stopped where it was told |

One listener gone and one intact, separated inside a single run on a single
line.

**Still owed**: one run each way. This check has produced three confident wrong
answers on single runs already, so `queue-abort-margins-are-unexplained` stays
open until N consecutive rounds agree — and the check's own PASS record says so
in `doesNotEstablish`.

