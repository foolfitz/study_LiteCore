# The accessibility tree's shape, measured 2026-08-23 — and it answers more than was asked

`research/DESIGN-2026-08-22-aria-projection.md` §9.2.2 said the reachability
measurement stopped at the **edit window's** accessible context, and that
getting from there to the **focused paragraph** was a different question with
no estimate attached. This is that question, measured.

Profile `a11y-tree` (diagnostic, wasm `06550b46…`), fixture `list-contexts.odt`,
three caret placements.

## What the tree looks like

```
emitted 10 nodes    maxDepth 1    focused 1    managesDescendants 1
roles: DOCUMENT_TEXT(85) x1,  HEADING(26) x1,  PARAGRAPH(41) x8
```

The fixture has **9 paragraphs**: one heading and eight others. The tree has
one root plus exactly those nine, **as direct children at depth 1**.

## The three things it settles

**1. Descent finds the focused paragraph, and it is the right one.**

| placement | engine's `paragraphText` | FOCUSED node | textLen |
|---|---|---|---|
| 0 | `E1-LC-HEADING` | **HEADING** | 13 |
| 1 | `E1-LC-ISOLATED 前後都不是清單的段落` | **PARAGRAPH** | 25 |
| 2 | `E1-LC-SPACER` | **PARAGRAPH** | 12 |

Exactly one node carries FOCUSED in each snapshot, and its text agrees with
what LOK independently reported through `getA11yFocusedParagraph()` — same
string, same length, three times. Two independent paths to the same answer.

**2. The role is there, and it is an ENUM.** `AccessibleRole::HEADING` (26)
versus `PARAGRAPH` (41). This is the locale-independent source that
`paragraphStyle` could never be: that field carries a **localised UI name**
(finding 031 — `標題 1` under zh-TW), so deriving a role from it passes in
en-US and fails silently in the target market. The tree does not have that
problem.

**3. `MANAGES_DESCENDANTS` does not block the descent — here.** It is set, and
only on the root `DOCUMENT_TEXT`; the nine children are enumerable anyway. The
worry that core's own listener descends by *listening* because the children are
not materialised turns out not to apply to this document. **"Here" is doing
work in that sentence — see the limits below.**

## What it gives beyond the question asked

The children of `DOCUMENT_TEXT` are the document's paragraphs **in order, with
roles**. That is the *document outline* — the second half of fable's
prescription — from the same walk, with no new engine field, no invented
ordinal, and **no fingerprint join at all**. The join is not merely unnecessary
(as the adjudication concluded); the problem it was solving does not arise,
because one tree carries both the structure and the focus.

## Limits, named now rather than discovered later

* ~~**This document fits on one screen.**~~ **MEASURED, and it holds.** A
  133-paragraph document (`l0-t3-long.odt`, opened through the page's own file
  input) exposes the **whole thing**: root `childCount: 133`, 133 nodes at
  depth 1, 134 emitted, roles `HEADING x22 + PARAGRAPH x111` — and exactly one
  FOCUSED. `MANAGES_DESCENDANTS` truncates nothing. **The tree is the outline,
  on a document that scrolls.** Record:
  `tree-shape-long-2026-08-23.json`.

  **The first attempt at this said the opposite, and the difference was mine.**
  At `kMaxChildrenPerNode = 64` the same document reported 65 nodes — 1 root
  plus the cap — which reads exactly like "MANAGES_DESCENDANTS materialises
  only part of the document". That would have been a conclusion about
  LibreOffice manufactured by a constant in the probe. Caps are now 4096 and,
  more importantly, **the payload carries them** (`maxNodes`,
  `maxChildrenPerNode`, `maxDepth`) so a reader can tell the document's edge
  from the instrument's without opening the source. The old payload reported
  `truncatedAt: 300` — the bound that was *not* binding — while staying silent
  about the one that was. **Reporting the wrong limit is worse than reporting
  none.**
* ~~**Outline LEVEL is not measured.**~~ **MEASURED, and it is exact.** Asked
  the way core asks it — `getCharacterAttributes(0, {NumberingLevel,
  Numbering})`, the same query `getListPrefixSize()` makes off the same object.
  On `paragraph-content.odt`, seven distinct heading levels **including a gap**:

  | ODT `outline-level` | 2 | 3 | 4 | 5 | 6 | 7 | 10 |
  |---|---|---|---|---|---|---|---|
  | tree `numberingLevel` | 1 | 2 | 3 | 4 | 5 | 6 | 9 |

  `numberingLevel = outline-level - 1`. ARIA's `aria-level` is 1-based, so
  `aria-level = numberingLevel + 1` returns the document's own number.
  Record: `heading-levels-2026-08-23.json`.

  **A weaker reading was available and would have been wrong**: on the
  133-paragraph document all 22 headings report level 0, which looks like
  "level is always 0". That document has one heading style. Reading it as a
  property of the tree rather than of the document is the same mistake the 64
  bound nearly produced, one measurement later.
* ~~**Lists are the open gap**~~ **— RECOVERABLE, measured.** The tree carries
  no `LIST_ITEM` role and no `LIST` container, which is true and was the wrong
  thing to look at. List membership is in the same two properties as the level:

  ```
  HEADING    lvl 0  numbered=True   runEnd 13  len 13  'E1-LC-HEADING'
  PARAGRAPH  lvl-1  numbered=False  runEnd 15  len 25  'E1-LC-ISOLATED …'
  PARAGRAPH  lvl 0  numbered=True   runEnd  2  len 18  '• E1-LC-BULLET-ONE'
  PARAGRAPH  lvl 0  numbered=True   runEnd  3  len 19  '1. E1-LC-NUMBER-ONE'
  PARAGRAPH  lvl-1  numbered=False  runEnd  9  len  9  'E1-LC-END'
  ```

  `isNumbered` marks exactly the four list paragraphs in `list-contexts.odt`
  and nothing else; non-list paragraphs report `-1 / False`. Read `role` first
  (HEADING vs PARAGRAPH), then `isNumbered` for list membership, then
  `numberingLevel` for nesting — because a **heading also reports
  `numbered=True`**, outline numbering being numbering. Record:
  `levels-and-lists-2026-08-23.json`.
* **Live update is not measured.** Every snapshot here was taken at rest. What
  the tree does *during* an edit — and whether it is safe to walk then — is
  unknown.
* **The walk is bounded** at depth 6, 64 children per node, 300 nodes total.
  Nothing here came close, so the bounds are untested as well.

## The probe, and why it is quarantined

`src/a11y_tree_probe.cpp` is the only translation unit compiled with
`-std=c++20 -DLIBO_INTERNAL_ONLY`, with its own Makefile rule; everything else
remains a LOK client seeing core through the public headers. Verified both
directions: the shipped v4 recipe contains `LIBO_INTERNAL_ONLY` zero times, the
variant once. It is a **bridge** — the destination is upstream adding role and
level to LOK's five-field payload, at which point the file is deleted.

## Three instrument failures on the way here, all the same shape

Recorded because each produced a **false negative that looked like a verdict**:

1. `EXTRA_DEFINES` was missing `-DOXSDK_A11Y_TREE_PROBE`, so the engine's call
   site was compiled out. The object linked; nothing called it. Symptom: the
   field is absent — **indistinguishable from "the engine cannot reach the
   tree"**. Compounded by `make` not tracking command-line flag changes, so the
   objects were not even rebuilt until deleted by hand.
2. `cd wasm_sdk_probe && python3 …` — the `cd` failed (already in that
   directory) and `&&` silently skipped the entire patch. Three `ok` lines
   printed by a *different* command in the same block were read as
   confirmation.
3. `strings` on the wasm reported the probe's markers absent — and also
   reported `core-built-without-accessibility` absent, a string whose runtime
   behaviour had already been **measured**. The instrument cannot see these
   strings at all; the negative was worthless.

Each time the honest-looking conclusion was "this route does not work". The
rule that saved it each time was the same: **check the instrument against
something known-present before believing its silence.**

## Finding 074, now confirmed from our side rather than by reading core

The same run measures `attrRunEnd` — the value
`getListPrefixSize()` returns as the list prefix length — beside the text it is
supposed to describe:

| paragraph | text | length | `attrRunEnd` | true prefix |
|---|---|---:|---:|---:|
| `• E1-LC-BULLET-ONE` | bullet | 18 | **2** | 2 (`"• "`) ✓ |
| `1. E1-LC-NUMBER-ONE` | numbered | 19 | **3** | 3 (`"1. "`) ✓ |
| `E1-LC-HEADING` | heading | 13 | **13** | **0** ✗ |

The mechanism is visible in one table. For bullets and numbers the prefix has
different character formatting, so it is its own attribute run and `SegmentEnd`
*coincides* with the prefix length. The heading's text contains **no numbering
label at all** — so the true prefix is 0 — but it carries outline numbering, so
`bIsCounted` is true, the guard passes, and the attribute run covers the whole
paragraph.

That is stronger than finding 074 was able to state from source alone: not
merely "the whole paragraph is claimed as prefix", but **13 returned where the
correct answer is 0, on a paragraph with no prefix in it**.

Note also `E1-LC-ISOLATED …`: `attrRunEnd` 15 on a 25-character paragraph — an
attribute-run boundary mid-text, nothing to do with numbering. It is harmless
only because `isNumbered` is false there and the guard returns 0 first. The
guard is what saves the ordinary case; the heading is where it stops saving it.

## What the projection can therefore be built on

Everything 1.3.1 asks for, measured and available from one walk:

| what | where |
|---|---|
| heading vs paragraph | `AccessibleRole` — an **enum**, not a localised name |
| heading level | `numberingLevel + 1` |
| list membership | `isNumbered` (after `role == PARAGRAPH`) |
| list nesting | `numberingLevel` |
| reading order | child index at depth 1 |
| which paragraph has the caret | the single `FOCUSED` node |
| the text | `XAccessibleText`, and LOK's `paragraphText` agrees with it |

**Still unmeasured**: what the tree does *during* an edit, and whether walking
it then is safe. Every snapshot here was taken at rest.
