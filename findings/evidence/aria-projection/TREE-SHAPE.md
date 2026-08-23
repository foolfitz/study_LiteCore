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
* **Outline LEVEL is not measured.** Heading-versus-paragraph is; heading *1*
  versus heading *2* is not. `getListPrefixSize()` already queries
  `UNO_NAME_NUMBERING_LEVEL` off the same object, so the datum is probably
  there — *probably* is not measured.
* **Lists are the open gap, and it is now a measured one.** Across both
  documents every non-heading node reports `PARAGRAPH` — never `LIST_ITEM`,
  and no `LIST` container appears anywhere. `list-contexts.odt` contains
  bulleted and numbered lists; the tree does not say so. **1.3.1 wants lists to
  be lists, and this tree does not carry that.** Whether it is recoverable from
  `listPrefixLength` plus numbering level, or needs a different query, is not
  known.
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
