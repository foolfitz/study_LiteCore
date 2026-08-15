# Prediction: the three checks that decide B' against A

**Written and committed before the probe exists and before any run.**

Required by `specs/SPEC-E2-B-paragraph-format-contract.md` section 9.7. In
English per `AGENTS.md`.

## What is being decided

SPEC E2-B 9.7 adopts **B'** for cross-paragraph ranges: dispatch the format
command, then verify by reading back the **surviving original selection** and
requiring its text to be byte-equal to the text captured before the dispatch;
if that cannot be done, return the "dispatched, could not verify" typed failure
that 2.3 and 3.5 already define.

That adoption is an **owned deviation** from the pre-registered disposition,
which was refusal only. 9.7 names three checks, any one of which sends the
decision back to **A** (refuse before dispatch). This file predicts all three
before running any of them.

**All three run with zero relinks.** They are native, on the same 26.8 source
tree the shipped engine is built from, so they answer "does the core do this",
not "does the wasm artifact do this".

## Why native and not the browser harness

B' reads the selection **after the uno command and before anything collapses
it**. The shipped engine's barrier collapses to its restore point and re-selects
with `.uno:SelectText`, so from JavaScript the surviving selection is not
observable on this build. Making it observable is an engine change — which is
the relink these checks exist to de-risk. Native LOK has the calls directly.

The cost is the standing one (`handoff` trap 3): this probe waits with fixed
sleeps, so **callback counts and timings are only citable within a run**, and
any arm that flips between rounds is not citable at all.

## Check 1 — substrate

**Question.** On an ordinary cross-paragraph selection, does
`getTextSelection("text/html")` return, and is the markup something the
readback parser can enumerate per block?

**Prediction: it returns, and the markup contains two block elements.**

*Basis.* The plain-text variant already works on exactly this selection: the
gate recorded `selectionBeforeDispatch.text = "E1-MULTI-START alpha\n第二段中文
beta"` in all six G3 runs. The HTML variant goes through the same
`pDoc->getSelection()` (`init.cxx`), and `multi-paragraph.odt` contains no
frame, no footnote and no image — none of the shapes findings 037/038 wedge on.

*Why the check exists anyway.* This call is in the family that findings 037 and
038 measured wedging. "This fixture has none of the wedging shapes" is a reason
to expect it to return, not a measurement that it does.

**If it wedges, or the markup cannot be enumerated per block → A.** B' would
have no verification substrate.

## Check 2 — survival

**Question.** After `.uno:DefaultBullet` is dispatched on a cross-paragraph
range, does the selection survive with **identical** text?

**Prediction: it survives, with identical text.** This is the least supported of
the three and I expect it least confidently.

*Basis.* `.uno:DefaultBullet` changes paragraph attributes; it is not a cursor
movement and not a text edit. Paragraph-level formatting does not change text
content, so if the selection survives at all, byte-equality should follow.

*What I do not have.* No prior measurement. Every gate arm reports
`collapsedAfterDispatch: true`, but that is the **barrier deliberately
collapsing**, not the command's own effect — it says nothing about what the
selection looked like in between. Recorded here so this is not later mistaken
for supporting evidence.

**If the selection does not survive in the common case → A.** B' would fall back
on every multi-paragraph press, so every correct outcome would be reported as
"may have changed, check and undo" — worse for a user than A's clean refusal.

## Check 3 — undo

**Question.** Is a cross-paragraph format dispatch a **single** undo step?

**Prediction: one `.uno:Undo` restores both paragraphs.**

*Basis.* Writer wraps a list toggle over a multi-paragraph selection in one undo
action. This is an expectation about Writer, not a measurement.

*Judged on the document, not on a return value* — the same rule the gate uses.
The probe saves the ODT three times (before dispatch, after dispatch, after one
undo) and a separate judge compares them. Pass requires **after-undo equals
before-dispatch** on the paragraph signature of all five paragraphs.

**If it takes more than one undo → A.** 2.3's fallback tells the host to prompt
the user to undo; if one undo leaves the document half-changed, that instruction
is dishonest for this class, and shipping a dishonest recovery message is worse
than refusing.

## Positive controls

Each check needs an arm that would come out differently if the probe were
measuring nothing:

- **Check 1** also reads the HTML of a **single-paragraph** selection. One block
  there and two in the cross-paragraph case is the discriminating pair; two in
  both would mean the count is not reading paragraphs.
- **Check 2** also runs the same dispatch on a **single-paragraph** range. If the
  selection does not survive there either, survival is not a cross-paragraph
  property and check 2's reading changes.
- **Check 3** also undoes a **single-paragraph** dispatch. If that needs two
  undos, the fixture or the dispatch is wrong, not Writer's undo grouping.

## Rounds

Three rounds of every arm. Any arm whose verdict is not identical in all three
is recorded as unstable and **may not be cited** — arms F, Y and Z of task #49
flipped exactly this way under the same fixed-sleep probe.

## What these checks do not decide

- They do not measure the WASM artifact.
- They do not establish that B' is implementable, only that its substrate exists.
- They do not touch section 5's protocol blockers, which are separate.
