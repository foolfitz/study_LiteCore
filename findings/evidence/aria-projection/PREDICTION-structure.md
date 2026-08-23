# Prediction for §3.4's structure increment — written 2026-08-23, before the projection exists

Nothing here was chosen after seeing a structured projection run. The
before-picture is the increment already shipped: the **focused paragraph only**,
in a region with no role, which `TREE-SHAPE.md` and the standard together show
is **below the Level A floor** (WCAG 2.1 1.3.1 — information and relationships
must be programmatically determinable).

Instrument, unchanged from the two measurements before it:
`tools/probe_aria_projection.py`, reading `Accessibility.getFullAXTree`. One
ruler across all three readings.

## What is being built

The whole document projected into an off-screen DOM: one node per paragraph,
in document order, carrying **role** (`heading` with `aria-level`, or
`listitem` inside a `list`, or a plain paragraph), the paragraph's **text**, and
**focus** following the caret.

The data is measured and available from one walk (`TREE-SHAPE.md` §"What the
projection can therefore be built on"). The tree tracks edits live
(`UNDER-EDIT.md`), so the projection walks on demand rather than rebuilding
from events.

## What this increment is NOT

**Not the product contract.** It is driven by `a11y.tree`, which exists only on
the diagnostic `a11y-tree` profile, behind `OXSDK_A11Y_TREE_PROBE`. The shipped
profile has no such field and must keep behaving exactly as it does today.
Turning this into a product field is a one-shot operation on the next link, and
that is deliberately out of scope here: **build it, measure it, then design the
contract from something that has been measured** rather than the other way
round.

## G3.4-3 — the gate

**PASS requires all five**, in one run on the diagnostic profile:

1. **Every paragraph is in the tree.** The accessibility tree contains one
   node per document paragraph — 9 for `list-contexts.odt`, and the count
   matches the document, not a cap.
2. **Headings are headings, with their level.** The heading appears with AX
   role `heading` and `level` equal to its ODT outline level (measured
   correspondence: `numberingLevel + 1`).
3. **Lists are lists.** The four list paragraphs in `list-contexts.odt` appear
   as list items inside a list container; the five non-list paragraphs do not.
4. **The text is there and it is right** — each projected node's text matches
   the paragraph it stands for, compared against the fixture's own XML in code,
   not by eye. This is the term that a page doing nothing cannot satisfy, and
   it is the same term that carried G3.4-1.
5. **Focus follows the caret**: across three placements, the node the AX tree
   reports as focused is the paragraph the caret is in.

**FAIL** = any of the five.

## G3.4-4 — the shipped profile must not change

On `e2-editor-v4` the region must still report `reason: profile` and the honest
sentence, and `run_e2_c_product_path.py` must stay green including
`the-document-region-says-why-it-is-empty`.

A projection that improves the diagnostic profile by breaking the product is a
regression, not a trade-off. **Measured on both profiles, one instrument.**

## What must go red

A mutation that unwires the structure walk must take G3.4-3 from PASS to FAIL
**with the focused-paragraph projection still working** — otherwise the
mutation only proves the old check can fail, which is already known.

## Traps this run must avoid, each earned today

* **A cap is not an answer.** The tree probe's own 64-child bound produced
  "MANAGES_DESCENDANTS truncates the document" out of nothing. Any bound in the
  projection travels in the record beside the count it bounds.
* **A transient is not an emptiness.** Two readings today came back with no
  tree at all, immediately after a keystroke. The projection **must keep its
  last announcement** rather than blank the region; blanking mid-typing
  announces "document, blank".
* **One document is not the property of a tree.** All 22 headings in the long
  document report level 0 — because it has one heading style. Level variation
  must be shown on a document that has several (`paragraph-content.odt` has
  seven).
* **Check the instrument before believing its silence.** Four false negatives
  today came from an unset define, a skipped patch, `strings` on a wasm, and a
  cap. Each looked like a verdict.
