# Handoff — 2026-08-19: every row on the checklist is now driven by a check

> Entry point. Reading this page is enough to take over; you do not need the
> earlier handoffs.
> Previous: `HANDOFF-2026-08-18-predicate-and-disposition.md`.
> The plan this round executed: `PLAN-2026-08-18-usable-editor-autonomous.md`
> (T3b, T3c and T4; T1.3 is still held).
>
> **This file is in English by decision of 2026-08-19** (see `AGENTS.md`): the
> only reader of a handoff is the next agent, and nine tenths of what is in one
> — check names, file names, symbols, log fragments — is English already.
> `devlog/`, `research/` and `specs/` stay zh-TW.

## 0. Current bindings

| | |
|---|---|
| artifact | `d538ce0b91478426…` (**untouched**; no link this round) |
| shell | v17 `34289a7bd8ffc3df…` (unchanged) |
| matrix | `e2/validation-matrix-v2.json`, **D0 still not run** |
| checklist | **8 done / 6 partial / 0 unverified / 0 missing / 2 blocked** |
| queue | `P1 complete: **False**` — still blocked by the engine half of 059, and that is correct |

**Zero `unverified` and zero `missing` rows.** Every row now points at a check
that runs and can fail. Three rows moved this round, and two of them moved
because something was finally measured rather than because anything was fixed.

## 1. The one sentence that matters most

**A long document is drawn as a blank page, in silence.** Above a canvas height
of about 32,767 px the product paints nothing, reports `ready`, and says
nothing at all — and the *same* twenty-page document draws on a 1× display and
is blank on a 2×. Finding 062. The layer is deliberately **not** named, and
naming it is what decides whether the fix needs a link.

## 2. What was done

### T3b — `format-a-paragraph`: `unverified` → `partial`

Five actions, pressed on the product's own toolbar
(`format-a-paragraph-changes-that-paragraph`). Three disciplines, each of which
a simpler check would have got wrong:

* every arm aims at a paragraph in the **opposite** state, so an implementation
  that does nothing cannot pass;
* the verdict is anchored to the target paragraph's **exact text** — the fixture
  already contains a heading, a bullet list and a numbered list, so a
  document-wide test passes both when the wrong paragraph changed and when
  nothing did;
* the **neighbours** must survive (finding 046's shape).

Aiming uses the product's own route — a click on the canvas — and the page's own
pixels: rows carrying ink are grouped into bands and matched one-to-one against
the lines of the document the product just saved. Mismatch ⇒ `NOT_ESTABLISHED`,
never a guess.

**A measured correction**: the product's heading action writes
`<text:p text:style-name="Heading_20_1">`, not `<text:h>`. The first oracle
keyed on the element name and reported a *working* action as a no-op.

**A named limit, and it is the opposite of what I predicted**: displacing every
click down by a whole line leaves **both caret checks green**. Their oracle is
horizontal, so the caret row covers *which column*, and *which line* is covered
only by this row's neighbour clause.

### T3c — `recover-from-an-error`: `unverified` → `partial`

The inducer is back (`INDUCE_FOOTNOTE_APPARATUS`, finding 038) and the queue
item's expectation was flipped to `present` deliberately.

The oracle is fable's three-branch adjudication of 2026-08-18: the product
declares where its recovery button will go **before** it is pressed
(`#s-checkpoint` reads 有（rN）/ 寫入失敗 / 無), and pressing it must deliver
exactly that. Plus a **capability clause**: this inducer *is* a selection
gesture on a dirty document, so the declaration may not be 無.

That clause is not redundant, and this round proved it rather than arguing it:
under the `checkpoint-before-selection-noop` mutation `declarationHonoured` is
still `true` — the product declares 無, delivers 無, and is internally
consistent while silently dropping everything typed since the last save. Only
the capability clause turns that red.

**An inducer correction that cost a round**: the drag **alone wedges nothing**.
Finding 038's own 2026-08-13 correction says the selection returns and the
engine is still alive — what kills it is the first *read* of that selection —
and `_drain` short-circuits its `getState` whenever the operation's result
already carries `state`. Measured: 77 seconds of health after the drag, then a
single click → `busy` → `recoverable-error` about 30 s later. **A one-step
recipe reports "038 no longer reproduces". A wrong aim reads exactly like a
fixed defect.**

Measured outcome: branch 有（r2）, and both the saved and the unsaved marker
came back.

### T4 — the long-document wall: `missing` → `partial`

Prediction committed first (`7b4a38c`), with no corpus, probe or check in the
tree. Then: a page-exact corpus generator, a canvas-limit probe run in both
browsers, and two checks.

* **Usability is green.** Keystroke to visible ink: 60 ms at one page, 62 ms at
  five, 127 ms at twenty — about 3.6 ms per page. The pre-registered 1,000 ms
  threshold is never approached below the wall. The threshold can bite: under
  `slow-repaint` it measures 1.85 s and goes red.
* **Honesty is red, and KNOWN_RED against finding 062.** See §1.
* **A third thing, with no length threshold at all**: an edit that makes the
  document taller leaves the canvas at its old size, and says nothing. A
  two-page document opens at canvas height 2007, an insert of 3,336 characters
  leaves it at 2007, and saving those bytes and re-opening them gives 3002 —
  exactly what a genuine three-page document reports.

**Three guesses in the old queue note were wrong**, and the corrections matter
more than the confirmation:

| the note said | measured |
|---|---|
| browsers cap canvas dimensions near 32,767 | **65,535** in both browsers (Chrome 65,234 at 2400 wide) — so the product's wall is a 16-bit limit *inside the render path* |
| A4 breaks "around a dozen pages" | 33 pages at dpr 1, 17 at dpr 2 — and the dpr factor is the part that matters |
| per-edit repaint cost grows with length | essentially flat (60 → 127 ms from 1 to 20 pages) |

## 3. Not done

| | why it is still open |
|---|---|
| **T1.3 — the engine-side fix for 059** | The predicate was decided on 2026-08-18 but a genuine NEGATIVE arm is still owed: the predicate was shown to agree, never to disagree. Plus state-cache priming (finding 021's shape). Needs a link, and the link is held. |
| **Finding 062's layer** | The experiment is written down in `queue-long-document-renders-blank-in-silence`: call `document.render()` through the shell at `canvasHeightPx` 32,590 and 32,889 and compare the returned width/height and pixel byte length. This decides engine-side vs page-side, i.e. whether the fix needs a link. |
| **A defect-independent second inducer** | `queue-recovery-inducer-depends-on-an-unfixed-defect`. Recovery coverage is currently tied to finding 038 staying broken. |
| **D0** | Still not run. Once it is, moving the shell means changing the matrix. |

## 4. Two lessons this round, both expensive

**A watched string must not appear in the text that explains it.** The queue
sentinel for finding 062 was tried three ways. Naming a file the experiment
would create drifted immediately — the checker fails closed on a file it cannot
read, which is the checker working. Naming a Chinese phrase drifted because the
finding's own instruction *spelled that phrase*. The token now lives in the
queue's `checkNote` and the finding points at it without quoting it.

**A mutation is worth writing even when it is expected to be boring.** Three of
this round's five real discoveries came out of mutations rather than out of
checks:

* `checkpoint-write-fails` was meant only to show that the third branch was
  reachable. It is — and the product is wrong on it (finding 061).
* `slow-repaint` was meant to show the latency threshold could bite. It did not,
  twice, and both failures were defects in **my own check**: `drawn` was a
  snapshot rather than a waited-for condition, and a moving caret (about 60 dark
  pixels) could satisfy "the keystroke became visible ink".
* `caret-off-by-one-line` was declared with the two caret checks as collateral.
  They stayed green, which is how the named limit in §2 was found.

## 5. Do not repeat

* **Do not say finding 059 is fixed.** The disposition is; the engine half is
  not, and pressing B still shows a message saying it failed.
* **Do not name finding 062's layer without the experiment.** Findings 040 and
  048 are the precedent, and this one decides a link.
* **Do not treat `ready` as "the document is on screen".** It is a statement
  about the session; the tile arrives afterwards. This cost a round in T3c (the
  page was still showing the *previous* document when the marker was typed) and
  again in T4.
* **Do not aim a check with a hard-coded index next to a derived one.** The
  recovery inducer kept a literal `1` beside a derived line index and dragged
  across the endnote's body instead of the reference mark.
* **Do not measure a page count on a corpus that does not declare its page
  geometry.** Without a page-layout the build lays out a sheet with an aspect
  ratio of 2.52 and a "page" holds about 83 lines, so an edit adding 3,336
  characters added no page at all. The growth arm's ground-truth clause caught
  it and reported `groundTruthEstablished: false` rather than passing.
