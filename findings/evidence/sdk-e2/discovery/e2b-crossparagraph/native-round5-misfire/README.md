# The misfire control: the gate passes on text built to trip it

**Date** 2026-08-15. Native, `outline-prose.odt`, three rounds. Prediction:
[`../PREDICTION.md`](../PREDICTION.md) round-5 addendum, committed before the
fixture existed (`40f1c3e`).

This closes the adjudicator's last flip condition. A gate that only ever fires
red is as useless as one that only ever fires green; rounds 1–4 showed the gate
can distinguish, this shows it does not misfire.

## The fixture

`dist/e2b-fixtures/outline-prose.odt`, built to trip a naive implementation:

| ¶ | text |
|---|---|
| 1 | `E2B-OUT-HEAD marker` |
| 2 | four `text:s` spaces, then `OUT2 1. this line already looks numbered` |
| 3 | `Ampersand & less-than < quote " and 12. mid-line` |
| 4 | `E2B-OUT-TAIL marker` |

Paragraphs 2 and 3 are the crossing range, and `.uno:DefaultNumbering` is
dispatched on them — so the serialiser's own numbering coexists with text that
already looks numbered.

## Result: identical, 3/3, every crossing arm

```
['OUT2 1. this line already looks numbered',
 'Ampersand &amp; less-than &lt; quote &quot; and 12. mid-line']
```

before and after, in all three rounds, for the bullet arm, the partial-head arm
and the ordered arm alike, with `items: 2` after each dispatch.

Two things this shows that the earlier rounds could not:

- **A genuine `1. ` inside the selection survives.** Under a gate that stripped
  decoration it would have been eaten; the html gate strips nothing.
- **Escaping is stable across the dispatch.** `&`, `<` and `"` read back as
  `&amp;`, `&lt;`, `&quot;` on **both** sides. Stability is what the gate needs;
  it does not need the escaping to be inverted.

## The first build of this fixture did not exercise its own case

The anchor was `looks numbered`, which sits **after** the `1. `. Since the range
begins at the anchor's rectangle, the decoration-looking run was outside the
selection, and the extracted text was just `'looks numbered'` — the fixture's
whole point, absent.

It still reported identical 3/3, so **nothing in the output would have revealed
it**. Caught by reading the extracted text rather than the verdict. The anchor
moved to `OUT2`, at the head of that run, and the fixture was rebuilt;
`wrapped-paragraph.odt` was verified byte-identical after regeneration so the
round-2 gate evidence stays bound.

This is the same class of mistake as G1's first fixture: an arm that runs, and
passes, without exercising the thing it exists for.

## What remains open

**wasm parity.** Every record here is native. The A2 sample that started this
line of enquiry is from the wasm artifact and agrees, but the crossing case has
not been measured there, and the adjudicator's third flip condition stands until
it is.
