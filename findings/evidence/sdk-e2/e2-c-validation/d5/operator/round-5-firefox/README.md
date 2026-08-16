# D5, fifth operator round (Firefox, 2026-08-16) — the round that found finding 050

One cell only: `d5-ime-commit`, redone cleanly after round 4's bookkeeping
tangle.  The cell recorded properly this time — and the product failed.

## What the operator did, and what the document shows

Three real Fcitx5 Chewing commits, **all trusted**, in one cell:

| commit | `compositionend` | landed? |
|---|---|---|
| `你好` | `isTrusted: true` | **yes** |
| `取代` (over a drag selection) | `isTrusted: true` | **no** |
| `取代二` | `isTrusted: true` | **no** |

Revision `0 → 1`.  The captured document contains `E1-LC-BETWEEN你好` and
nothing else new.

The operator's report was "it still does not replace".  **Replacing is not
broken** — a commit over a selection does replace, measured separately.  What is
broken is the *second* commit, and the second commit happened to be the one over
a selection.

## The cause: [finding 050](../../../../../050-every-ime-commit-after-the-first-is-rejected-as-a-buffer-mismatch.md)

`HostInputAdapter.handleCompositionEnd()` compares `compositionend`'s data with
the host sink textarea to catch a desynchronised IME, and **nothing ever cleared
that sink**.  From the second commit on, the buffer always disagreed and the
commit was rejected as `INPUT_COMPOSITION_MISMATCH` — with no visible error,
because the product wires no `onInputTrace`.

Reproduced at unit level (`input/tests/input-adapter.test.mjs`), fixed the same
day, and the fix is mutation-verified: removing it turns the new test red.

## The analyzer says PASS, and the analyzer is wrong

`tools/analyze_e2_c_d5.py` marks this cell **PASS**: it has events, they are all
trusted, a composition is present, the revision advanced, a document was
captured.  Every check it makes is satisfied.

**The frozen oracle is not.**  `e2/validation-matrix-v1.json` says:

> a real Fcitx5 Chewing commit at a collapsed caret, **and one replacing a
> selection**, on the v2 artifact

Two commits.  The analyzer only asks whether the revision moved *at all*, and it
moved once — for the first commit.  The commit the oracle explicitly names is
the one the product dropped.

So this cell is **PASS by the analyzer and NOT established by the matrix**, and
the difference is recorded rather than resolved in the analyzer's favour:

- the cell is treated as **not established** for the phase;
- the analyzer is **not** retroactively strengthened — it judged round one and
  every round since under one rule, and changing it now would change readings
  already filed;
- matrix v2's cell carries the stronger criterion: **one revision advance per
  commit the oracle names**.

This is the second time in two rounds that the analyzer has been found weaker
than its own frozen oracle (round 4: it checks that a document was captured, not
what is in it).  Both are recorded; neither was quietly fixed.

## Why this round is the evidence

The product did not do what the cell asks.  The round is kept because it is the
measurement that found a blocking product defect, on the shipped artifact, with
a person at the keyboard — and because it shows a criterion that would have
reported success for a build that silently discards two thirds of a user's
typing.

**A rerun is needed after the fix**, judged against the stronger criterion.

## Addendum, 2026-08-16 — the strengthened criterion, applied to this round

`tools/analyze_e2_c_d5.py --criteria round-two` now requires one revision
advance per commit the oracle names.  Re-judged with it, **this round's IME cell
is `NOT_ESTABLISHED`** — where round one's judge reported `PASS`:

```
commitsObserved: 3      revisionAdvance: 1
bothCommitsAttempted: true      everyCommitLanded: FALSE
```

The round-one verdict in `verdict.json` is **left exactly as it was**.  It was
made honestly under the rule of the day, and rewriting it would hide the thing
worth keeping: a judge can be weaker than its own frozen oracle, and the way to
find out is to run the stronger rule against evidence you already have.

Round 6, judged by the same stronger rule, is still `PASS` — so the rule
discriminates rather than rejecting everything.
