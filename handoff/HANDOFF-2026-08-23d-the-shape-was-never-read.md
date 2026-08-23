# Handoff: the selection shape was never read, and a gate had been red for nine commits

Written 2026-08-23, continuing `HANDOFF-2026-08-23c-selected-text-can-be-emboldened.md`.
That one's closing instruction was: run the verification section, then take
finding 079, measuring the `delete-selection` direction first because it was
derived rather than observed. Both were done. Both came back differently than
that document expected.

## Read this first: the verification section pointed at the wrong target

`HANDOFF-...-23c` §"Verify before trusting this document" says
`check_gesture_offers.py` is "now in `test-e2-b-static`". **It is in
`test-e2-c-static`.** So the recipe named two targets that were green
(`make test-e2-b-static`, `check_gesture_offers.py` standalone — both pass,
`e2-editor-v7: 21 actions, 0 problems`) and never named the one that was red.

`make test-e2-c-static` **fails on `test_the_real_manifest_matches_the_real_tree`,
and had been failing since commit `7fcb143`** — nine commits, spanning two
`出貨` commits. Three shell files had drifted from the frozen `v38` manifest and
no new generation was taken. Verified by hashing each file at every commit in
`19c7eee..HEAD`: clean at `19c7eee` and `6773d64`, drifted from `7fcb143`
onward.

So the shell that `e2-editor-v7` shipped on, that the operator's real-mouse pass
ran on, had **no manifest binding it at all**.

**Fixed**: `e2/editor-shell-v2-bundle-v39.json` is frozen, `v38` is in
`FROZEN_MANIFESTS`, `MANIFEST` is `v39`. The generation note says what it is and
what it is not: it records the shell at `be8291a`, and it *cannot* give the
rounds it swallowed (the v5 mint and revert, findings 075/076/077, 078/v7) the
generations they never got. `dist/` was already in sync, so nothing but the
freeze was owed.

**The lesson is not "run the gate".** It is that a round's verification recipe
was written from memory of which target held which check, and a wrong memory
produced a recipe that could only pass. If you write a "verify before trusting"
section, derive the target list from the Makefile rather than recalling it.

## The shipped page, before anything was changed

`python3 tools/run_e2_c_product_path.py --out …` with no `--profile`:
**33 PASS / 6 NOT_ESTABLISHED, `ok: true`**. No FAIL, so by `23c`'s own honest
criterion the cutover stands. `an-inline-format-reaches-a-selection` passed —
078's fix holds on the shipped page.

(Kept as
`findings/evidence/f079-the-shape-was-never-read/product-path-shipped-before-fix.json`.)

## Finding 079: not stale. Never read.

### The predicted direction does not exist, and the page says so without a browser

`23c` said to measure the `delete-selection` direction first. **That direction is
unreachable.** `lastSelectionShape` is read in exactly one place —
`updateGestureAffordance()` — which touches only `#toolbar button[data-action]`.
There is no `delete-selection` button, and its sole dispatch site (the cut
handler) asks `session.offers("delete-selection")`: the manifest, not the shape.

The cost lands on the other side of the same gate. Six buttons are offered for
`collapsed` only (both character moves, both deletes, both breaks), so a shape
stuck at `collapsed` left all six **enabled** while a range was selected, where
the engine's mask refuses them.

### What was measured

`tools/probe_079_selection_shape.py`, on the shipped page, both sides in one arm
— the page's belief from the toolbar's titles, the engine's from the product's
own copy path.

| arm | engine | page | changed in 8 s? |
|---|---|---|---|
| click, no drag (control) | 0 chars | `collapsed` | no — the two agree |
| drag inside one line | **12 chars** | `collapsed` | **never** |
| drag across two lines | **34 chars** | `collapsed` | **never** |

Positive control (`--positive-control`, a mirror where the variable *starts* as
`range-single`): all six caret-only buttons disabled, titles naming
`range-single`. So the instrument can show a range; `collapsed` is a statement
about the page.

### Why never

`--capture-result` mirrors the page with one added statement recording what
`session.selectRange()` resolves to. Top-level keys:
`method, revision, completion, callbackSequenceBefore, callbackSequenceAfter,
state`. **No `collapsed`, no `rectangles`** — they are at `state.selection`.

`editor-shell/editor-client.js` (v1) *assembles*
`{collapsed, text, rectangles, caret, revision}`. `ParagraphEditorClient`
(v2) assembles nothing and returns the envelope verbatim. The page read the v1
shape, got `undefined` twice, and `undefined === false` → false,
`undefined?.length ?? 0` → 0, so the expression returned `collapsed`
**unconditionally, for every drag ever made**. There was no value to go stale.

After the fix: `range-single` (12 chars) and `range-cross` (34 chars), the page
catching up **52–55 ms** after pointerdown. It was never a latency problem.

### What the fix is

The derivation moved OUT of the page into `selectionShapeOf()` in
`editor-shell-v2/narrow-editor-v2-session.js`, exported and unit-tested, with
`selectionShapeEvidence()` beside it. `editor-shell-v2/tests/selection-shape.test.mjs`
has 10 cases whose **fixtures are the recorded envelopes**, and one case IS this
finding: a v1-shaped object must come back `null`, never `collapsed`.

It returns `null` rather than `collapsed` when it cannot tell — those are
different claims and conflating them is the whole finding. The page, on `null`,
keeps the previous shape and raises `data-selection-unreadable` plus
`data-selection-evidence` (key names only; `state` can carry the user's
paragraph). **Stated degenerate case**: if the *first* result is unreadable the
kept value is the initial `collapsed`, so the policy degrades into the option it
rejects — which is why the regression check reads the *flag*, not the shape.

`updateGestureAffordance()` now also writes `#toolbar[data-selection-shape]`, so
the page's belief is legible without inferring it from which buttons went grey.

### The net

* `the-page-agrees-with-the-engine-about-the-selection` — engine's code points
  vs the page's own dataset, after a real drag.
* mutation `selection-shape-from-the-wrong-place` — restores the defect in its
  **silent** form (`result?.collapsed !== false` as a boolean, so the unreadable
  flag does *not* fire and the page says `collapsed` confidently). Measured
  detected: engine 3 code points, page `collapsed`, `unreadable: false`, FAIL.
* mutation `selection-shape-unreadable` — makes the accessor always answer
  `null`, so the unreadable branch fires. Without it, "the flag never lit" and
  "the flag is not wired" look identical and both are green.

## Finding 080: a check blamed the harness for the defect it was checking

`an-aborted-gesture-stops-selecting` asked "are the four format buttons
disabled?" and meant "is a range selected?". That was false on every run ever,
for two stacked reasons: **079** (the shape was always `collapsed`), and then
**`e2-editor-v7`** offering those buttons for ranges as well. It reported
NOT_ESTABLISHED permanently while its recorded declaration blamed the harness —
"the check's positive control cannot start an extending drag through this
harness". **That is false**, and the same day's measurement disproves it: 12 and
34 code points through the same `DRAG`. The declaration's *last* sentence named
the right fix and was ignored because it sat behind a sentence that assigned
blame elsewhere.

Re-aimed at `#toolbar[data-selection-shape]`, which does not turn on what the
manifest offers, so the next widening cannot disarm it the same way.
`format_buttons_disabled()` → `a_range_is_selected()`, and the report keys with
it: a name should say what it measures.

A sweep of every `button.disabled` read in the runner found only one other that
enters a verdict — 078's `buttonAfterDrag` precondition guard, now vacuous on v7
(all three gestures offered) but incapable of false green. Recorded in the
finding.

## The abort check went red three times, for three different reasons

Re-aiming `an-aborted-gesture-stops-selecting` took it red on its first
meaningful run, and each red was worth more than the one before.

**Red #1 — its own predicate.** Control true, and both abort arms true.
`ABORT_DRAG` moves once *before* it aborts, so a range up to that midpoint is
correct on every arm; "a range exists" is true whether the wiring works or not.
Replaced by extent: each abort arm's text must be a strict prefix of the
control's. That passed (control 11 code points, arms 10 and 10) and detected the
`gesture-abort-not-wired` mutation, so `expectedToBeDetected` went to `True`.

**Then an external adjudication refused the green**, on two grounds: the strict
prefix was the *weakest* predicate derivable, and I had adopted it after seeing
red while a stronger one would have stayed red — the definition of fitting; and
I had not explained the number that mattered most, that the control's own reach
moved **11 → 6** between two runs of the same gesture.

**Red #2 — the arms were reading different lines.** Margins of *minus four*. The
control had selected `1-LC-H` from band `[83,182]`; both abort arms had selected
`E1-LC-ISOL`. Different strings entirely. Each arm called `stable_bands` for
itself and took the first band wider than 40 px, and that scan is intermittent on
this core (finding 075). **That one cause explains every unexplained number this
check ever produced — including that the run where it PASSED passed by luck.**
Visible only because the selected *text* was in the record beside the count.

**Red #3 — the aim could not resolve.** With the aim derived once and shared, the
comparison became valid and the weak predicate lost its excuse, so a fourth
**reference** arm now makes the same moves and stops where the others abort: the
expected answer is *driven*, not predicted from pixels (the text is
proportionally spaced, so a pixel-to-character model would have been the weakest
link). First run of that: control `E1`, two characters; reference, at half of
that, nothing. Honest NOT_ESTABLISHED. The aim now spans 90% of the **widest**
band rather than half of the first band over 40 px.

**Measured after all three**, on the shipped page:

| arm | selected |
|---|---|
| control (no abort) | `E1-LC-ISOLATED 前後都不是清單的` |
| reference (stops at the abort point) | `E1-LC-ISOLAT` |
| pointercancel | `E1-LC-ISOLAT` |
| blur | `E1-LC-ISOLAT` |

Byte-exact agreement with the driven reference, on a 14-vs-9 margin. **38 PASS /
2 NOT_ESTABLISHED, `ok: true`.**

**And the mutation is now detected for the oracle's own reason**, which it was
not before — previously it went red on an empty-string guard, a different
property. Under `gesture-abort-not-wired`:

| arm | selected |
|---|---|
| control | `E1-LC-ISOLATED 前後都不是清單的` |
| reference | `E1-LC-ISOLAT` |
| **pointercancel, UNWIRED** | **`E1-LC-ISOLATED 前後都不是清單的`** — followed the pointer to the end |
| blur, still wired | `E1-LC-ISOLAT` — stopped where it was told |

One listener gone and one intact, separated inside a single run on a single
line. `listener:pointercancel#canvas` and `listener:blur#global` moved from
`uncovered` to `driven` in `e2/product-path-coverage.json`, with the old
reason **retracted in the entry** rather than edited away.

**What is still owed, and why `queue-abort-margins-are-unexplained` stays open:
this is one run each way.** An intermittent margin measured once gives a confident and
wrong answer, and that is precisely this check's history. It wants N consecutive
rounds before anyone writes "the pointercancel and blur wiring is verified". The
reads are also still synchronised on wall-clock sleeps rather than on the
`revision` / `callbackSequence` fields the envelope already carries.

The check's PASS record carries `establishes` / `doesNotEstablish`, and
`doesNotEstablish` names that queue id — which the queue item pins with a
`contains` check, along with the shared aim and the reference arm, so none of the
three can be quietly undone.

## State

| finding | what | state |
|---|---|---|
| 076 | `malloc`'d tile buffer paints uninitialised heap | **still waiting on a relink** |
| 078 | selected text could not be emboldened | closed, shipped as v7 |
| **079** | **the shape was computed from fields that are not there** | **fixed, measured before and after, in the net** |
| **080** | **the abort check blamed the harness** | **re-aimed; its margins are an open queue item** |
| — | the format barrier's `stage-deadline` on the a11y core | untouched this session |

Shell generations: `v39` = what `e2-editor-v7` shipped on; `v40` = this
session's page (the 079 fix, the accessor, the two datasets). No relink: every
change is shell-side, the artifact did not move, and the pin did not move.

## Open work, in the order I would take it

1. **`queue-abort-margins-are-unexplained`** — start with revision-based
   synchronisation, because it is the cheapest change that could settle all
   three numbers at once, and because every other margin question is downstream
   of the control being repeatable.
2. **Finding 076's relink** — `calloc` is in the source and nothing ships it.
3. The two standing NOT_ESTABLISHED on the product path
   (`notice-action-recovers-the-session`,
   `a-refused-action-is-reported-and-changes-nothing`) both come from finding
   047's recipe no longer blocking the queue. They are preconditions, not
   failures, but they have been abstaining a while and 080 is what a
   long-abstaining check turns out to be.
4. The a11y projection's own gaps, from `DESIGN-2026-08-22-aria-projection.md`
   §7.4.

## Two things a new session should not re-derive

* **The v2 client does not assemble a selection result.** It returns the
  worker's envelope; the selection is at `state.selection`. `selectionShapeOf`
  is the one place that knows this, and it has tests with the real fixtures.
* **A mutation that does nothing is a finding, not a mutation to replace.**
  Finding 079 exists only because the inert one was investigated. It named the
  wrong mechanism, but it named a real defect — and the direction it predicted
  turned out to be unreachable, which reading one function would have shown.
