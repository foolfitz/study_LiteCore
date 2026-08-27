# Result: the extra announcement is the accessibility one, and it carries a stale caret

Finding **084**, follow-up measurement, 2026-08-27. Asked for by an
adjudication the same day: *characterize the extra callback; confirm it is
deterministically one extra, not sometimes two; and identify which callback it
is.*

## What was measured

`--caret-source-diagnostic` was widened to record **every** `editor-state`
announcement from the page's own `onEvent`, before any layer narrows it. That is
the only place `source` survives: the session's adoption copies twelve fields
and `source` is not one of them, which is why "which callback is the extra one"
could not be answered from the page's state log alone.

## The answer

| | announcements per commit | sources |
|---|---|---|
| shipped `e2-editor-v8` | **1**, on 12 of 12 commits | `visible-cursor` |
| a11y `e2-editor-v11` | **2**, on 24 of 24 commits | `a11y-paragraph-changed`, then `visible-cursor` |

**Deterministically one extra.** Never three, never one, in 24 consecutive
commits across two runs.

One commit verbatim, accessibility core:

```
seq=275  source='a11y-paragraph-changed'  rev=119  caret=2871,4352   <- the OLD caret
seq=276  source='visible-cursor'          rev=119  caret=4911,4352   <- the new one
```

and the shipped core, same commit index:

```
seq=222  source='visible-cursor'          rev=119  caret=4911,4419
```

**The extra announcement carries a caret of its own, and it is the stale one** --
the caret as it was before the commit, because the accessibility paragraph
callback fires before the cursor has moved. That is the second writer finding
084 needed and the reason the window exists at all: between two announcements
that both claim to describe the caret, the drain's read can be answered against
either.

## It is the accessibility callback, and that is read rather than inferred

`src/probe_engine.cpp:2433` -- `case LOK_CALLBACK_A11Y_FOCUS_CHANGED:` sets
`editorSource = "a11y-paragraph-changed"`. The name in the report is the
engine's own dispatch label, not a correlation between two build differences.

This matters because the adjudication warned specifically against attributing
the doubling to "a11y": the core changed **two** variables at once (writer+calc
*and* accessibility). That warning is satisfied here without being ignored --
the extra announcement is the accessibility focus callback by construction, and
the calc half of the build difference has nothing to do with it. What remains
un-measured is anything about *calc*, and nothing here claims otherwise.

## The guard, re-measured at the pre-fix sample size

The pre-fix rate was 10 dropped of 48 commits. Post-fix:

| profile | runs | commits | dropped | stale writes refused |
|---|---|---|---|---|
| a11y `e2-editor-v11` | 5 | **60** | **0** | **28** |
| shipped `e2-editor-v8` | 2 | 24 | 0 | **0** |

Sixty is more than the forty-eight it is being compared against, so the
comparison is not resting on a smaller post-fix sample. **The race is still
being lost -- twenty-eight times -- and was caught every time.**

Zero on the shipped profile, which is what one announcement per commit predicts:
with only `visible-cursor`, the caret-bearing announcement is the last event of
the commit and there is nothing left to overwrite it.

## And the guard is proven order-independent, not merely currently winning

The unit tests no longer assert only that the measured interleaving is refused.
They assert the invariant: **after any interleaving, the snapshot holds the
highest `sourceSequence` written and the caret that came with it** -- driven over
all 24 permutations of four arrivals, plus duplicates in every position, plus a
hostile stream in which the sequence is never allowed to decrease.

One of them reproduces the shape measured above -- two announcements per commit,
the caret on the second, the drain's read applied between them -- in all three
orders. That test was written from a hypothesis about what the a11y core does;
this measurement is what turned it into a description.

Mutations, each caught by exactly the test that should catch it: the guard
removed (6 red), installed but never stripping (2 red), the comparison inverted
to `>` (7 red), widened to `<=` (2 red).
