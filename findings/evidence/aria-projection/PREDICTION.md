# Prediction for §3.4's first increment — written 2026-08-23, before the projection exists

Nothing here was chosen after seeing a projection run. The baseline it will be
compared against is [`BASELINE.md`](BASELINE.md): **171 accessibility-tree
nodes, zero carrying a character of the document**, measured on the core that
*does* provide accessibility, so it is the best case and not a handicapped one.

The instrument is the same in both directions —
`tools/probe_aria_projection.py`, reading `Accessibility.getFullAXTree`. A
before and an after on one instrument; not two impressions.

## What this increment is, and what it deliberately is not

**Is**: the focused paragraph, projected into the accessibility tree, so a
screen reader announces where the caret is and what that paragraph says.

**Is not**: a browsable document. Browse mode needs every paragraph, and the
engine hands over exactly one — the focused one. Building a whole-document
shadow is roadmap §3.4's route A and it was not the route chosen. Naming this
now so that "the screen reader cannot navigate the document" is read later as a
**known scope boundary** rather than as a defect discovered in testing.

## G3.4-1 — the gate

**PASS requires all four**, measured in one run:

1. **The tree carries the text.** At least one non-ignored AX node's `name` or
   `value` contains the focused paragraph's text.
2. **It changes with the caret.** Across three caret placements on three
   different paragraphs, **≥ 2 distinct readings**.
3. **Each reading matches the paragraph actually targeted** — compared against
   the fixture's own XML, not against what the page thinks. This is the term
   that does the work: three different strings would also be produced by a
   counter, and G0-2 is the precedent for requiring the match rather than the
   difference.
4. **The document region is reachable and labelled**: the text sits inside a
   node with an accessible name, not loose in the page.

**FAIL** = no node carries the text, or one reading for all three placements, or
a reading that does not match its paragraph.

## G3.4-2 — the honesty term, and it is not optional

On a profile whose contract does **not** declare `caretParagraphText` — the
shipped `e2-editor-v4` — the projection must **say so** in the tree, not render
an empty document region.

An empty region reads to a screen reader as *"document, blank"*, which is a
confident wrong answer about the user's file. This is the same rule the engine
already obeys one layer down: `unavailable: "core-built-without-accessibility"`
rather than `enabled: true`.

**Measured by running the probe against `e2-editor-v4` as well.** Two profiles,
one instrument, opposite expected readings — the control arm, written in
before the first run rather than added when someone asks for it.

## What must go red

A mutation that unwires the projection must take G3.4-1 from PASS to FAIL with
nothing else moving. Written before the projection so it cannot be shaped to
whatever the code happens to look like afterwards.

**And the trap to avoid, named in advance**: a mutation that empties the region
would ALSO be caught by term 1, so term 1 alone cannot distinguish "the
projection was removed" from "the projection ran and found nothing". That is
the `downAndUpAreInverses` shape from 2026-08-22 — a predicate a page doing
nothing satisfies. Term 3 is what carries the conjunction here, because a
*matching* reading cannot be produced by a page that did nothing.

## Traps this run must avoid

* **`display:none` and `visibility:hidden` remove a node from the tree.** A
  projection hidden that way measures as absent and would read as a failure of
  the projection rather than of its CSS. Use the clip pattern.
* **A live region announces changes; it does not make text readable.** Both
  properties are wanted and they are different. Term 1 asks whether the text is
  IN the tree; that is the readable half and it does not depend on
  `aria-live` working.
* **Do not measure the page's own DOM and call it the tree.** The AX tree is
  what the browser derived, and the two differ — that is the entire reason
  this instrument was chosen over `document.querySelector`. Same error as
  reading a page snapshot and calling it the engine's state (068, third
  attempt).
* **The product must still work.** The visual editor is the product; a
  projection that breaks the canvas, the toolbar or the caret is not a
  trade-off, it is a regression. `run_e2_c_product_path.py` must stay green.

## Not a threshold, recorded anyway

Node count before and after. §3.4's value is not "more nodes" and no threshold
is set on it — but the number is recorded so a later round starts from a
measurement instead of a memory, exactly as G0-5 did for size.
