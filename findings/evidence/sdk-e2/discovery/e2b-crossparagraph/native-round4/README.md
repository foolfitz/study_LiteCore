# The identity gate closes on html per-block text — ordered included

**Date** 2026-08-15. Native, five arms, three rounds. Prediction:
[`../PREDICTION.md`](../PREDICTION.md) round-4 addendum, committed before the
probe was amended (`e9b732d`).

Round 4 is round 3's arms re-run with one change: the probe now keeps the **full
html string** on both sides of the dispatch. The counts were never enough — the
adjudicated gate runs on text extracted *from* that markup, so the markup is the
evidence and a count of it is not.

## Predicted, and it holds: no marker digits in the html text

The crossing ordered readback:

```html
<ol><li><p style="…">E1-MULTI-START alpha</p></li>
<li><p style="…"><font face="DejaVu Sans"><span lang="zh-TW">第二段中文</span></font></p></li>
</ol>
```

**The number is in the `<ol>`. The text is the paragraph's own text.** The
incrementing `"    1. "` / `"    2. "` decoration round 3 found exists only in
the plain-text serialisation. So the decoration set never needed closing, the
pattern question never needed answering, and **`set-list-unordered` and
`set-list-ordered` verify identically** — the manifest pair stays a pair.

## The gate, run on the records

`tools/analyze_e2b_identity_gate.py`. Per-block text, before against after:

| arm | blocks | items after | per-block text identical |
|---|---|---|---|
| `cross-paragraph` | 2 | 2 | **3/3** |
| `cross-paragraph-partial-head` | 2 | 2 | **3/3** |
| `cross-paragraph-ordered-sample` | 2 | 2 | **3/3** |
| `single-paragraph-whole` | 1 | 1 | **3/3** |
| `single-paragraph-control` | 1 | 0 | **3/3** |

Fifteen for fifteen.

## A first attempt that had no discriminating power, recorded because it is the point

The first digit check searched the whole `<body>` after stripping tags and
reported digits in almost every arm. It was matching `#000080` in the body
element's own attributes — the extraction began *inside* the opening tag. It
"found" digits in the bullet arms too, which is what gave it away.

The one arm it reported clean was `cross-paragraph-partial-head`, and only
because its range starts mid-word so the text is `TART alpha` — the fixture's
own `1` in `E1-MULTI-START` was cut off. **Every digit the broken check found was
the fixture's anchor, not a list marker.**

`analyze_e2b_identity_gate.py` now runs four extractor controls before it will
report anything, and exits non-zero if any fails: two blocks extract as two, a
lost block is visible, inline markup is concatenated, a changed character is
visible.

## Why the gate is per block and not whole-body

Measured, not asserted — `--show-body` reports both:

| arm | per-block identical | whole-body identical |
|---|---|---|
| `single-paragraph-control` | true | true |
| every other arm | **true** | **false** |

`</li>\n<li>` leaves a tab between the paragraphs after the dispatch that was
not there before, and wrapping a single paragraph in `<ul><li>` does the same.
A whole-body comparison would report a difference that is pure serialisation —
it would fail on every successful list dispatch, which is exactly the failure
mode the plain-text gate had. **Per-block extraction has no such seam.**

## What is still open

- **wasm parity is a premise, not a result.** These are native records. The A2
  sample that started this is from the wasm artifact and agrees, but the crossing
  case has not been measured there.
- Byte-exact round-trip of *genuine* text through html extraction — entities,
  `&nbsp;`, unusual characters — is not established by this fixture. The
  misfire-direction control the adjudicator asked for (outline-shaped prose,
  dispatched with numbering, gate must **pass**) is not yet built.
