# E2-C phase D1 — the integration sequence

**Artifact**: `e2-editor-v2`, wasm `572035ac…`, shell bundle `b01d77da…`.
**Criteria**: `e2/validation-matrix-v1.json`, frozen before D0 (the eight inline-format
cells were amended before D1 ran, on the strength of the D1 pre-flight; each amended
cell says so in an `amended` field).
**Date**: 2026-08-15. **Browsers**: Chrome and Firefox, three rounds each.

## Result

**23 of 28 cells pass 3/3 in both browsers. Five fail — systematically, in every
round, in both browsers, with identical values. The comparison projection is
identical across the two browsers for all 81 entries, failures included.**

That last sentence is the useful one: these are not flakes. Two independent
browsers produced the same answer three times each.

| failing cell | rounds passed | cause |
|---|---|---|
| `d1-set-bold-false` | 0/3 both | **[finding 045](../../../../045-inline-format-actions-discard-the-enabled-flag-and-toggle.md)** |
| `d1-set-italic-false` | 0/3 both | finding 045 |
| `d1-set-underline-false` | 0/3 both | finding 045 |
| `d1-set-strikethrough-false` | 0/3 both | finding 045 |
| `d1-body-collapsed` | 0/3 both | **open — see below** |

### The four `-false` cells: finding 045

`enabled: false` does not turn a format off. The engine stores the flag in a
variable it only reports back and dispatches `.uno:Bold` **bare**, and core's slot
is declared `Toggle = TRUE`. Requested off, delivered on. Full mechanism, source
lines and a fresh-document reproduction: finding 045.

Per the matrix's decision table this is `STOP` (a manifest-declared action fails),
and both ways of resolving it — send the parameter, or declare the narrowing in the
manifest — need a relink, which SPEC E2-C section 3 forbids. **That decision is
outside E2-C.**

The criteria were **not** relaxed to make these green. They ask for exactly what the
contract promises.

### `d1-body-collapsed`: open

`set-paragraph-body` at a collapsed caret on `E2-D1-BODY-TARGET` (a heading) is
refused **before dispatch**, all six runs:

```json
{"failureShape": "routing-selection-not-readable", "dispatched": false,
 "route": "collapsed", "preBlocks": 0, "postBlocks": 0}
```

The refusal is the finding-037 type guard in `routeFormatBarrier()`: the routing read
found a selection whose type is not `LOK_SELTYPE_TEXT`. Two things are worth saying
precisely rather than loosely:

* **Zero mutation.** `dispatched: false` means nothing was sent; this is the clean
  refusal shape, not an unknown outcome.
* **`route: "collapsed"` in that payload is a default, not an observation.** The
  shape is only ever set in the branch where the selection rectangles are NOT empty,
  and that branch returns before assigning the route. So the field says what the
  struct was initialised to. It should not be read as "the engine classified this as
  collapsed".

What is not yet known: why this anchor and not the five other collapsed cells that
pass. The next probe is a narrow one — place the caret at this anchor, read the
selection type directly, and compare with an anchor whose cell passes.

## What passed

Everything else, 3/3 in both browsers, including:

* all four inline formats in the `-true` direction, each judged at **its own anchor**
  through **its own marker**, so a mapping error could not hide behind a shared
  completion;
* both deletes (paragraph exactly one character shorter, and the result is the
  original minus one character), both breaks (paragraph break: block count +1 with
  the document text conserved; line break: `<text:line-break/>` present, block count
  unchanged);
* the three list actions and `set-paragraph-heading` at a collapsed caret, plus
  heading on a `range-single` and on a `range-cross` (both paragraphs verified);
* **`set-list-ordered` on a cross-paragraph range where both paragraphs were already
  numbered** — the first of the four cells E2-B 9.11 named as uncovered;
* the interleave cell: a delete and a bold dispatched **after** a paragraph action
  still satisfy v1's own postconditions, so route C's relaxation has not leaked.

## The analyzer says no when it should — including on red evidence

`python3 tools/analyze_e2_c_d1.py --self-test <evidence>` applies nine mutations and
requires each to **change the verdict**, rather than requiring each to make it fail.
The first version required the base evidence to pass, which would have made the
self-test unusable exactly here: a self-test that only works on green evidence stops
working when the evidence is red, which is when the analyzer's judgement matters
most. 9/9 change the verdict.

## Files

```
<profile>-<hash>/<browser>/result.json    per-round, per-cell observations and the anchor survey
<profile>-<hash>/<browser>/page.log       the page's own log
<profile>-<hash>/<browser>/saved/*.odt    174 saves: a before-picture and an after-picture per cell, per round
```

Every dispatching cell saves on **both** sides, and the before-picture is taken
**before the gesture is established**. Both of those are corrections made during the
smoke rounds: judging a cell against the document as it was *opened* charges it with
twenty other cells' edits, and taking the before-picture *after* the gesture let the
save disturb the selection — a delete came back `EDITOR_BOUNDARY_UNSUPPORTED` in a
run where the same sequence without that save had worked.
