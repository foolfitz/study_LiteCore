# The accessibility tree while the document is edited — measured 2026-08-23

`TREE-SHAPE.md` ended with one unmeasured thing: every snapshot there was taken
**at rest**. This is the same tree during editing, and it decides the
projection's shape — walk on demand, or rebuild from events.

Tool: `tools/probe_a11y_tree_edits.py`, profile `a11y-tree`, fixture
`list-contexts.odt` (9 paragraphs). Record:
`tree-under-edit-2026-08-23.json`.

## It tracks. All of it, immediately.

| step | depth-1 | headings | paragraphs | numbered | focused |
|---|---:|---:|---:|---:|---|
| at rest | 9 | 1 | 8 | 5 | HEADING `E1-LC-HEADING` |
| caret placed | 9 | 1 | 8 | 5 | PARAGRAPH `E1-LC-SPACER` |
| **typed `ZZ`** | 9 | 1 | 8 | 5 | PARAGRAPH **`E1-LZZC-SPACER`** |
| **paragraph break** | **10** | 1 | **9** | 5 | PARAGRAPH `C-SPACER` |
| **set-list-unordered** | 10 | 1 | 9 | **6** | PARAGRAPH **`• C-SPACER`** |

Text edits, structure changes and style changes all appear in the next
reading, and the FOCUSED node follows the caret through every one.

⇒ **On-demand walking is viable.** The projection does not need to reconstruct
the document from an event stream; it can ask.

The first two rows after the caret placement are the **controls**: they are
changes this harness dispatched. If the tree had not moved there, nothing else
in this file could be read.

## The pre-registered falsification: one case confirmed, one not reached

The prediction (fable, `DESIGN §8.6`, written before this tool existed) was
that **3/3** of these change structure with no structure action from us.

**Follow-on style — CONFIRMED, and it is the sharp one.** With the caret at the
end of the **heading**, we dispatched `insert-paragraph-break`:

```
depth-1  10 -> 11      paragraphs  9 -> 10      headings  1 -> 1
new focused node: PARAGRAPH, empty
```

We asked for a *break*. Core decided the new paragraph's **role** — Writer's
follow-on style, so the heading did not beget a heading. A shell keeping its
own shadow would have had to encode Writer's style-succession rules to predict
that. **"The shell knows because it dispatched the action" is false for the
part that matters: the split is known, the structure is not.**

**Autocorrect (`- ` at the start of a paragraph) — DID NOT FIRE, and that is
not the result it looks like.** Typed at offset 0, `- E1-LC-ISOLATED…`, then a
word and a space to reach a word boundary: `isNumbered` stayed false and the
numbered count stayed 6.

This is evidence about **our insert path**, not about a person typing. The
harness dispatches `beforeinput`/`insertText`, which reaches core through the
SDK's text-commit path; Writer's autocorrect hangs off the edit engine's
**keyboard** input. So the honest statement is: *the product's own programmatic
insert does not trigger autocorrect*. Whether a real keystroke does is
**unmeasured** — `caret-after-real-typing` exists in the product path for
exactly this reason (CDP key-by-key), and pointing it at this question is the
next step if anyone needs the answer.

**Undo/redo across a split — not attempted.** Named rather than quietly
dropped.

The first run of the autocorrect arm was worse than inconclusive: the caret sat
where the click landed, so `- ` went into the **middle** of the line
(`E- 1-LC-ISOLATED…`) and the arm would have read as "autocorrect does not
happen" — a conclusion about LibreOffice produced by where a click landed.
Pressing Home first is now in the tool, with that reason attached.

## One limit found by accident, and it matters for the projection

Two snapshots came back with **no tree at all** (`before-autocorrect`,
`caret-at-end-of-heading`), and both were taken **immediately after a
`TYPE_KEY` press** (Home, End). Both recovered by the following step.

So the reading is not always available the instant after a keystroke. For a
projection that walks on demand this is a **liveness** question, not a
correctness one — but it means the projection must treat "no tree right now" as
a normal transient and keep its previous announcement, **not** blank the region.
Blanking on a transient would announce "document, blank" mid-typing, which is
the exact failure `the-document-region-says-why-it-is-empty` exists to prevent.

Cause not investigated. Two candidates, neither measured: the state read raced
the key handling, or the accessible is genuinely absent while the edit engine
holds it.
