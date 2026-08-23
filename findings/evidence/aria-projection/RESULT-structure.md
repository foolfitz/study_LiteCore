# §3.4 structure increment — measured 2026-08-23: **G3.4-3 and G3.4-4 both PASS**

Criteria fixed in [`PREDICTION-structure.md`](PREDICTION-structure.md), written
before the projection existed. Same instrument as the two readings before it —
`tools/probe_aria_projection.py` reading `Accessibility.getFullAXTree`.

## The three readings on one ruler

```
171 nodes /  0 carrying document text     baseline, before any projection
175 nodes /  the focused paragraph        the first increment
205 nodes /  9 of 9 paragraphs, with roles   this one
```

## G3.4-3, term by term

| term | result |
|---|---|
| 1. every paragraph in the tree | **9 of 9** — 1 heading, 4 list items, 4 plain, plus the live region |
| 2. headings carry their level | `E1-LC-HEADING` → AX **`level: 1`**, matching the fixture's ODT `outline-level` |
| 3. lists are lists | **2 `list` containers, 4 `listitem`** — two because the fixture's bullet and numbered lists are separated by a plain paragraph, and the projection closes the container when one appears |
| 4. the text is there and right | all nine compared **in code** against the fixture's `content.xml`, not by eye |
| 5. focus follows the caret | three placements, **3 distinct readings**, each the paragraph targeted |

## G3.4-4 — the shipped profile

```
e2-editor-v4   175 nodes   structure roles: none   documentTextInTree: false
               region: reason "profile", the honest sentence
product path   38 checks, 35 PASS, ok: true   (identical to before this work)
```

`the-document-region-says-why-it-is-empty` still PASSES. 175 is the number from
*before* the structure increment: **unchanged to the node.**

That last part took a fix. Without it the shipped tree went 175 → **176** — one
empty, unroled container. Inert, and still a change to what a screen reader is
handed on a profile this increment is not supposed to touch. `aria-hidden`
removes it. **The difference between "the shipped page is unchanged" being true
and being nearly true.**

`aria-hidden` rather than `hidden` or `display:none`, deliberately: the
container has to come **back** when a profile carries the data, and the clip
pattern above it exists precisely because the display properties remove nodes
from the tree in ways that are easy to get wrong. One mechanism for invisible,
another for absent.

## What this increment is not

**Not the product contract.** It is driven by `a11y.tree`, which exists only
behind `OXSDK_A11Y_TREE_PROBE` on the diagnostic profile. The shipped page takes
the early return. Turning it into a contract is a one-shot operation on the next
link — designed from a measurement rather than ahead of one.

## Named gaps, not fixed here

* **List items carry their own prefix in the text** (`• E1-LC-BULLET-ONE`,
  `1. E1-LC-NUMBER-ONE`). With `role="listitem"` an AT announces the bullet
  itself, so it is read twice.

  The obvious fix is to strip `listPrefixLength` characters — and it is
  **deliberately not done**, because that field is what finding 074 is about.
  Measured today: it is correct for list items (2 and 3) and returns the whole
  paragraph for a heading whose true prefix is 0. Stripping on a field with a
  known upstream defect, on the strength of two samples that happened to be
  right, is building on the thing the finding warns about. Recorded as
  `queue-list-prefix-read-twice`.
* **`textHead` is capped at 4096 characters**, and the cap travels in the
  payload beside the untruncated `textLength`. A paragraph longer than that
  projects clipped.
* **A real screen reader has not read this.** The tree is what every AT
  consumes and it is now correct; how one particular AT *announces* it —
  order, verbosity, browse mode — remains the narrow human question named in
  `BASELINE.md`.

Shell generation **v38**, `5deba8e53ad9fd13`, frozen after these runs.
