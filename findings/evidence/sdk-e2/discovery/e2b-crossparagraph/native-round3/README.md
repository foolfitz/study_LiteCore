# The last dark cell closes, and the decoration set turns out not to be a set of strings

**Date** 2026-08-15. Native, five arms, three rounds, **fifteen records,
identical within every arm**. Prediction:
[`../PREDICTION.md`](../PREDICTION.md) round-3 addendum, committed before this
ran (`0b04ef2`).

## `cross-paragraph-partial-head`: predicted, and it holds

The range starts **two thirds into paragraph 1** — mid-word — and ends inside
paragraph 2. Both edges partial, one boundary crossed.

| | before | after `.uno:DefaultBullet` |
|---|---|---|
| text | `"TART alpha\n第二段中文"` | `"    • TART alpha\n    • 第二段中文"` |
| blocks | 2 | 2 |
| items | — | 2 |

**Full block structure at a partial leading edge**, three rounds out of three,
document-confirmed (both paragraphs changed, one undo restores).

So the discriminator is confirmed on **both** edges: what decides whether the
readback carries block structure is **whether the selection crosses a paragraph
boundary**, not how much of any paragraph it covers. The repaired B'
construction has **no structural hole at ordinary drags**, and the flip
condition that would have sent the decision back to A does not fire.

## The ordered-list sample: the prefix is not a constant

Recorded, not judged — no prediction was committed for its value.

`.uno:DefaultNumbering` on the same crossing selection reads back as:

```
    1. E1-MULTI-START alpha
    2. 第二段中文
```

**The decoration is `"    1. "` then `"    2. "` — it increments per line.** The
adjudicated normalisation rule asks for "a closed, sampled set of **exact byte
strings** measured on this build per action". For bullets that is satisfiable:
`"    • "` is one string, stable across nine records. For numbering it is not —
the set of exact strings is unbounded in the list length.

This does not break the construction, but it changes what condition 1 has to
say: numbering needs a **bounded pattern** (four spaces, digits, a period, a
space) rather than a literal, and a pattern can mask text that genuinely starts
that way in a manner a literal cannot. That is a weakening of an adjudicated
condition, so it goes back to the adjudicator rather than being adopted here.

## Every arm, this round

| arm | blocks before | items after | text equal |
|---|---|---|---|
| `cross-paragraph` | 2 | 2 | false |
| `cross-paragraph-partial-head` | 2 | 2 | false |
| `cross-paragraph-ordered-sample` | 2 | 2 | false |
| `single-paragraph-whole` | 1 | 1 | **true** |
| `single-paragraph-control` (partial, inside ¶1) | 1 | **0** | **true** |

All fifteen: dispatch applied, one `.uno:Undo` restored every paragraph
signature.

The last row is break two at its corrected scope — and it is the row the
repaired construction routes **away** from the surviving-selection read, because
`blocks == 1` goes to the existing `.uno:SelectText` barrier, which handles one
paragraph honestly.
