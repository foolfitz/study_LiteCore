# The barrier's selection overshoot — how far does it go?  Registered before the harness existed.

Written 2026-08-16, after `findings/evidence/046/diagnostic-readback/` measured
the defect on exactly **one** position of **one** fixture.

## What is known

On the empty paragraph of `empty-paragraph.odt`, the barrier's `.uno:SelectText`
selects past the paragraph and into the next one:

```html
<ul><li><p></p></li></ul><p>E1-EMPTY-AFTER</p>
```

The bullet applied; the read covered two paragraphs; the barrier reported
`MUTATION_OUTCOME_UNKNOWN` for a mutation that had succeeded.  Both browsers,
both gestures.

**One position of one fixture is not a characterisation.**  Nothing yet says
whether this is about empty paragraphs, or about carets at paragraph edges, or
about what follows the paragraph.

## Why the answer changes what it is worth

Finding 034 replaced the old two-command selection pair because it "escaped to a
neighbouring paragraph **whenever the caret already sat at a paragraph edge**".
An empty paragraph is one where the caret is at both edges at once.  So there
are two candidate scopes, and they are worth very different amounts:

| scope | who it hits |
|---|---|
| **empty paragraphs only** | someone bulleting a blank line |
| **any caret at a paragraph end** | someone who clicks at the end of a line and presses the bullet button -- an ordinary gesture |

The second would be a product defect of a different order, and would argue for
holding the v3 link open until it is fixed.

## Cells

All on the **frozen** engine, through the diagnostic profile
(`probe.wasm` byte-identical to `e2-editor-v2`), same page machinery as the
readback round, both browsers.

| id | fixture | where the caret goes |
|---|---|---|
| `text-mid` | `empty-paragraph.odt` | middle of `E1-EMPTY-BEFORE` — the control |
| `text-start` | `empty-paragraph.odt` | left edge of the same paragraph |
| `text-end` | `empty-paragraph.odt` | **past the last character** — the discriminator |
| `empty-mid` | `empty-paragraph.odt` | the empty paragraph — the reproduction |
| `isolated-mid` | `list-contexts.odt` | middle of `E1-LC-ISOLATED`, a plain paragraph with non-list neighbours |
| `isolated-end` | `list-contexts.odt` | past its last character |
| `between-mid` | `list-contexts.odt` | `E1-LC-BETWEEN`, a paragraph between two lists |
| `bullet-one-mid` | `list-contexts.odt` | inside an existing list item |

Each cell records the caret the product reports, the whole raw barrier record
(`readback.html`, counts, containment), and the saved document where the session
state allows it.

## Predictions

- **P-OV-1** — `text-mid` reads `blockCount: 1` and the action **succeeds**.
  The control reproduces what the readback round measured.
- **P-OV-2** — `empty-mid` reads `blockCount: 2` and fails `multi-block-readback`.
  The defect reproduces.
- **P-OV-3** — **the discriminator**: `text-end` reads `blockCount: 1`.
  Registered as the NARROW hypothesis — that the overshoot is about the
  paragraph being empty, not about the caret being at an edge.
- **P-OV-4** — `text-start` reads `blockCount: 1`.
- **P-OV-5** — `bullet-one-mid` reads `blockCount: 1`: being inside a list does
  not by itself cause the overshoot.
- **P-OV-6** — every cell that overshoots reports `containment.held: true`.
  The structural claim from the readback round — containment asks whether the
  selection covers the caret, never whether it covers **only** the caret's
  paragraph — tested on more than one cell.

## The decision rule, written before the data

- **P-OV-3 holds** → the defect is scoped to empty paragraphs.  It stays a
  non-blocking queue item, and the fix can be designed calmly.
- **P-OV-3 fails** (`text-end` also reads two blocks) → the defect is "a caret
  at a paragraph end", which is an ordinary gesture, and that **changes the
  link decision**: it argues for fixing it before the link rather than after.
  That conclusion goes to the user, not into the tree.
- **P-OV-6 fails** anywhere → containment does catch some overshoots, and the
  reorder question reopens with data instead of by argument.

## What voids a cell

- The caret does not land on the requested line: the cell is recorded with its
  readback and excluded from the conclusions, not retried.
- A cell fails for a reason unrelated to the barrier (anchor not found): void,
  not retried.
- The diagnostic profile's `probe.wasm` is not byte-identical to the frozen
  one: the whole round is void.
