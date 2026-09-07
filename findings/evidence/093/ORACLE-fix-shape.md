# Finding 093, phase 3 — the oracle a fix has to satisfy, registered before any number exists

Written 2026-09-08 by agent, **before any measurement in this phase was taken**
and before the probe that takes them was written. Nothing below may be moved
afterwards; a correction goes in a later section that names what it replaces
(AGENTS.md §10).

## Why this document exists rather than a scroll-fraction threshold

Phase 2 measured the scroll **fraction** — the share of `.desk`'s scrollable
room consumed by bringing the region into view — and measured the positive
control (`#a11y-doc { top: 0; left: 0 }`) collapsing it from 0.9759 to
**0.0000**.

**0.0000 is a perfect score for a page that shows paragraph 1 while the screen
reader is reading paragraph 8.** The fraction says how far the desk travelled,
not whether the reader can see what is being read. It was the right instrument
for phase 2's question ("is this node at the bottom of the paper, on both
profiles") and it is the wrong instrument for phase 3's ("does this candidate
fix work"). Ranking candidate shapes by the fraction would rank S1 first
because S1 pins the viewport to the top of the paper and never moves it.

So phase 3 registers the claim itself and measures that, per AGENTS.md §7.

## The claim

> When the screen reader is reading paragraph N, paragraph N is visible in the
> viewport.

## O-FIX — the machine form of that claim

### Terms

- **Anchor rect of paragraph N.** The caret rectangle the engine reports when
  the caret sits inside paragraph N, in CSS pixels relative to `.paper`, read
  as `#sink.offsetTop` and `#sink.offsetHeight`. These are the values
  `moveSinkToCaret()` writes from `editorState.caret`
  (`web/e2-editor-app.js:722-735`) — **the page's own existing computation,
  read as a DOM observable, not a new geometry invented for this run.** The
  anchor rect is one text line high: it is the line the caret is on, which is
  the line a reader arriving at paragraph N is reading.

- **Visible band.** `[0, desk.clientHeight]` in `.desk` viewport coordinates.

- **Paragraph N's band, in viewport coordinates.**
  `top = (paper.getBoundingClientRect().top - desk.getBoundingClientRect().top)
         + anchorTop(N)`, `bottom = top + anchorHeight(N)`.

- **Overlap.** `max(0, min(bottom, clientHeight) - max(top, 0))`.

### The predicate

**O-FIX holds for paragraph N iff `overlap >= 0.5 * anchorHeight(N)`.**

### The tolerance, and why this one

Registered before the numbers so it cannot be fitted to them:

- **Full containment is too strict.** A paragraph can be taller than the
  viewport, and a reader who has just arrived at it is on its first line.
- **A bare intersection is too lax.** One pixel of a text line at the very edge
  of the viewport satisfies "intersects" and does not satisfy "you can see what
  is being read". This is finding 069's lesson in a new place: its first
  criterion was a pixel count, and pixels could not separate "scrolled to the
  caret" from "scrolled past it".
- **Half of one line height** is the smallest threshold a line merely touching
  the viewport edge cannot reach.

### How the reader's arrival is driven

A screen reader landing its browse cursor on the projected node for paragraph N
is modelled as `node.scrollIntoView({ block: "nearest" })` — the same model
phase 2 used, for the reason recorded there (`nearest` is what a browser does
when it brings a focused or AT-targeted element into view; the aggressive
default would measure the instrument's choice).

The walk is **sequential and ascending**, the desk starting at `scrollTop = 0`
and **not reset between paragraphs**: a reader reads through a document, it
does not teleport back to the top before each paragraph. The starting position
is stated because it is a choice, not a fact.

### The limitation this run does NOT remove

**This probe does not run a screen reader.** The link from "Orca moves its
browse cursor onto the projected node" to "the browser scrolls that node into
view" is finding 069's precedent and the owner's two walks of 2026-09-08. It
was not measured in phase 2 and it is not measured here. Every result below is
conditional on that link, and the condition is repeated with the results rather
than left in this section.

## Which paragraphs

The first, a middle, and the last paragraph the caret walk can reach, named by
their index in `documentOutline.paragraphs`. Fixture `a11y-audible` — the one
the owner's walk used, named in the Orca log at 00:10:43.828.

**A shape passes only if O-FIX holds for every measured paragraph.** A shape
that holds for some and not others is reported per paragraph and is not rounded
to a verdict.

## The shapes, registered with their arms

- **S0 — the unfixed page.** The control.
- **S1 — `.a11y-only { top: 0; left: 0 }`.** Phase 2's positive control,
  promoted to a candidate. Fraction already measured as 0.0000.
- **S2 — `#a11y-doc` rides the caret**, reusing `moveSinkToCaret()`'s
  computation rather than inventing a second one. **Two arms, both registered
  now, and S2's verdict must carry both:**
  - **S2-focus** — the caret is in paragraph N when node N is browsed. This is
    the arrow-key flow: the page's own `keydown` handler on `#sink` moves the
    engine caret (`web/e2-editor-app.js:1183-1192,1287`), the engine's outline
    moves `focused`, and the page moves `aria-activedescendant`.
  - **S2-browse** — the caret stays in paragraph 0 while node N is browsed.
    This is a screen reader's browse cursor moving **without** moving the
    caret, which is what browse mode and structural navigation do.
  A shape that passes S2-focus and fails S2-browse has **not** passed.
- **S3 — each projected node positioned at its own paragraph.** Registered as
  **conditional**: it exists only if per-paragraph geometry is obtainable. The
  feasibility answer is a first-class result of this phase, with `file:line`
  citations, and if the answer is no then S3 as specified does not exist and
  the report says so rather than substituting something near it.
  - If a *derived* variant is measurable instead, it is reported as **S3′**,
    under its own name, with its own costs — not as S3.

## Pre-registered stopping conditions

- **The control must fail.** S0 must FAIL O-FIX for at least the first
  paragraph, **on both profiles**. **If S0 passes O-FIX everywhere, the oracle
  is wrong**: the run stops and reports that, and does not proceed to rank
  shapes. This is written here so that outcome cannot be reinterpreted later as
  "the page is fine".
- **An unestablished anchor is not a pass.** If the caret walk cannot establish
  an anchor rect for a target paragraph — finding 084's dropped commit, or an
  arrow key the profile does not offer — that paragraph is reported
  `NOT_ESTABLISHED` and is **not** dropped from the shape's verdict.
- **Nothing is landed.** Every shape is applied to a scratch mirror of `dist/`
  built with `build_mirror`. `web/`, `dist/` and every identity-bound path are
  left alone. `e2-editor.html` is hashed by nothing (finding 094), which is the
  reason for this rule and not a licence to relax it.

## What this phase does not decide

The choice of shape. The menu and its numbers go to the gate owner; ranking
with reasons is allowed, choosing is not (AGENTS.md §8, and the same rule that
put D-c in the owner's hands).
