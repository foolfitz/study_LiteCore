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
| artifact | **`29ec627bf8a5588b…` — relinked twice on 2026-08-19** (`d538ce0b…` → `296f3ea7…` → `29ec627b…`, both archived) |
| shell | **v25 `07143f961d82c4b3…`** (v17 → … → v25; one generation per shell change, as the tool insists) |
| matrix | `e2/validation-matrix-v2.json`, **D0 still not run** |
| checklist | **13 done / 1 partial / 0 unverified / 0 missing / 2 blocked** |
| queue | `P1 complete: **True**` — nothing blocking, and `KNOWN_RED` is **empty** for the first time |

**Zero `unverified` and zero `missing` rows.** Every row now points at a check
that runs and can fail. Three rows moved this round, and two of them moved
because something was finally measured rather than because anything was fixed.

## 0.5 The relink of 2026-08-19

The user asked for it after the evidence for both engine-side items was
complete. Two changes rode it, both guarded by `OXSDK_E2_FORMAT_BARRIER` so the
frozen `e1-editor` profiles keep the exact behaviour E1-C validated:

* **finding 059** — the engine stops gating the four inline formats on core's
  `success`, which was measured *anti-correlated* with the request being
  honoured, and calls `inlineFormatArgumentResolved()` instead: observed state
  against requested state, with `…Known` required so "I don't know" can never
  read as "yes". Underline and Strikeout gained the state cache they never had.
* **finding 062's second half** — `handlePaintTile` re-reads `getDocumentSize`
  and reports it on the reply, so a document that grew a page is no longer drawn
  at the size it had when it was opened.

**Both KNOWN_RED declarations went green on the first run after the link, and
the runner is what said so** — it reports a declared-red check that passes as a
STALE DECLARATION and fails the round. Neither could have quietly outlived its
defect.

One thing worth carrying: **the worker's reply is a whitelist**
(`sdk/sdk-worker.js`), so the engine change alone was invisible to every client.
An engine field that nobody forwards is an engine field that does not exist.

## 0.7 Closing the four `partial` rows

Three closed, one honestly characterised, and the fourth is the interesting one.

* **`recover-from-an-error` → done.** Finding 061 fixed: the page stops
  re-deriving the notice and takes `recoveryNotice()`'s decision, so a FAILED
  rescue has its own sentence. The same edit retired finding 054's cause — both
  defects came from one re-derivation. The oracle is now structural: the page
  stamps `#notice[data-rescue]` and the check requires the two surfaces (pill and
  notice) to AGREE, instead of comparing wording that would go green on a
  rephrase.
* **`keyboard-shortcuts` → done.** Ctrl+B/I/U wired now that 059 is fixed, going
  through the same `editorAction` the buttons call. Ctrl+A was **removed**:
  select-all is not one of the fifteen actions and the geometric substitute was
  measured selecting nothing. The row's sentence was changed rather than the
  check widened.
* **`format-a-paragraph` → done.** The note claiming the gesture mask blocked
  multi-paragraph conversion was **wrong** — that mask is on the four inline
  formats; all five paragraph actions declare all three gestures and the
  disposition is `verify-every-block`. Nothing was blocking it; nothing had
  driven it. A sixth arm drags across two paragraphs.
* **`cut` → still partial, and it turned up two things.** Granting the harness a
  clipboard (permission *and* focus emulation — `writeText` needs both) made the
  delete half run for the first time. It is refused every time:
  `delete-backward` is caret-only and a cut is always a range, so **cut is
  effectively copy**. And the refusal used to put the session into
  `recoverable-error` and tell the user their unsaved work was gone — for an
  action whose own error says "nothing was dispatched and the document is
  unchanged" — with no message at all, swallowed by a bare `.catch`. That is
  **finding 063**, now fixed.

**The lesson worth carrying**: that path was not measured wrong, it was
*unreachable* — the harness had no clipboard, so the delete never ran, and the
check looked green while only ever exercising one branch.

## 1. The one sentence that matters most

**A long document is drawn as a blank page, in silence.** Above a canvas height
of about 32,767 px the product paints nothing, reports `ready`, and says
nothing at all — and the *same* twenty-page document draws on a 1× display and
is blank on a 2×. Finding 062.

**The layer is established: the ENGINE side.** A *cold* render of a tile taller
than 32,767 px comes back correctly sized, entirely zero, and reported as a
success. Measured at two widths whose buffers differ twofold — 45 MB paints at
32,767 and 45 MB is blank at 32,768 — so it is the **height**, not the memory.
2^15 − 1.

**It did not need a link, and it is now FIXED** (shell v19). `renderDocument()`
issues one request per strip, none taller than 32,767, composed at their own y.
A document short enough to fit takes exactly one strip covering the whole
canvas, so nothing changes for the common case. Measured: 35 pages at 1x and the
same 20-page document at 2x both draw, and there is no seam — bands at 32,300 /
32,600 / 32,900 and at the bottom are all opaque and all carry ink.

The page also **refuses a tile the engine did not paint** (`TILE_NOT_PAINTED`),
by sampling alpha: an unpainted buffer is zero including alpha, a genuinely
blank page is opaque white. With the strips removed by mutation the product now
*says* `重繪失敗：TILE_NOT_PAINTED` instead of showing a silent blank page.

**The other half is not fixable from the page.** An edit that makes the document
taller leaves the canvas at its old size, at any length — and nothing tells the
page: `getDocumentSize` is called exactly once, at open
(`probe_engine.cpp:2520`), and none of the SDK's operations re-reads it. That
half is engine-side, needs a link, and now blocks it
(`queue-canvas-does-not-follow-a-document-that-grew`).

**This corrects a conclusion committed earlier the same day.** The first answer
was "page side", and it was wrong for a reason worth keeping: every probe run
swept an *ascending ladder* of heights inside one engine session, so the first
render was always below the limit and painted, and the later over-limit arms
came back carrying content — which exonerated the engine. One render per page
load, which is what the product actually does, returns an unpainted buffer every
time. **A probe that sweeps a parameter inside one session carries state between
its arms, and ascending order is exactly what hides a cold-start limit.**

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

### T1.3's measurement half — the predicate can say no, and the cache is primed

Native round, nine arms, zero disagreements
(`findings/evidence/059/native/negative-arm/`, analyzer self-test 10/10).
Nothing was rebuilt: the probe compiles against the LOK headers and loads the
existing native install.

**Two genuine negatives**, and the predicate said not-met on exactly those: a
wrong argument TYPE (`{"Bold":{"type":"string",...}}`) leaves the text normal
with no broadcast, and a paragraph inside a `text:protected` section refuses the
dispatch and does not even take the typing. Four refusals were tried rather than
one, because 037's lesson is that a guard may decline for another reason or not
at all — and `setViewReadOnly`, asked again, **still does not refuse**.

**The cache is primed at document LOAD**, for all four slots including underline
and strikeout — which contradicts `probe_engine.cpp:4308` a second way, by
measurement this time. But the priming comes from the load broadcast, **not from
caret movement**: moving between two paragraphs that already share a state
broadcasts nothing.

**And one that sharpens why the current gate is wrong rather than weak**:
`success: true` appeared on exactly the two arms where core **ignored the
argument and toggled**, and `success: false` on every arm where core honoured
the parameterised form. The field `commandResultSucceeded()` gates on is
**anti-correlated** with the caller's request being honoured.

**Why the engine change was not written**: this finding exists *because* 045's
fix shipped with native evidence, a static check, a queue item and a link — and
nobody ever pressed the button. Writing a second engine fix that cannot be
exercised until the next link repeats that shape. The design and both hazards
are recorded in the queue item instead.

### fable adjudicated finding 061, and overturned part of it

Verdict: **061 stands** — the shell's own spec revision (SPEC-E1-C §4.1 v8)
says the `checkpointError` field exists precisely so the two cases are not
conflated, and the product re-derives a two-way branch that conflates them
anyway. But one plank was wrong and is now removed: **the notice is not false**.
In that state `hasCheckpoint` really is false and the bytes really are the same
as the nothing-to-rescue case. It is *literally true and causally misleading* —
"the notice lies" loses the argument to the first hostile reader.

It also found **three holes in my check**, one of them self-disarming:

1. comparing against a hard-coded copy of the no-checkpoint sentence meant a
   rewording would make the check **silently pass**, defect intact;
2. requiring only "different from (b)" would pass the strictly worse regression
   of printing the *has-checkpoint* sentence, claiming a rescue that does not
   exist;
3. the branch never required the unsaved work to be gone.

All three fixed: both sentences are now read out of the **served source**, so a
rewording moves the reference instead of disarming the check, and an unreadable
reference reports NOT_ESTABLISHED rather than passing.

## 3. Not done

| | why it is still open |
|---|---|
| **T1.3 — the engine-side fix for 059** | **The two owed measurements are done** (see §2.4); the change itself was deliberately not written. Gated only on the link now, which is the user's decision. The full design and two measured hazards are in `queue-inline-format-argument-is-rejected-by-core`. |
| **Finding 062's second half** | The blank page is **fixed** (shell v19, strips, no link). What is left is the canvas not following a document that grew, and the page *cannot* fix it: `getDocumentSize` is called once, at open, and no SDK operation re-reads it. Engine-side, `blocksRelink: true` — see `queue-canvas-does-not-follow-a-document-that-grew`. |
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
