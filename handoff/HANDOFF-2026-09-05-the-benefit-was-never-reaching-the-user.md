# Handoff: the benefit was in the tree and never reached the user

Written 2026-09-05, covering 09-03 through 09-05. Continues
[`HANDOFF-2026-09-03-the-day-was-a-gate-and-three-holes.md`](HANDOFF-2026-09-03-the-day-was-a-gate-and-three-holes.md).

**In one line.** The cutover gate's soak went from 8 of 12 to **0 of 12**,
deliberately: the human round found that a screen reader moving through the
document hears no structure at all — the thing the whole +24.5 MiB is being paid
for — and fixing it moved the page. Three findings (087, 088, 089), two
adjudications, and **the owner's ear caught something six machine checks had
called green**.

## State

`e2-editor-v8` still ships; `dist/e2-editor-app.js` is the baseline
`28e03e5bc9fcb8c4`. **77 commits unpushed**, tree clean.

| | |
|---|---|
| candidate page | **`20f09cc9…`** (was `3dfdcfef…` this morning; moved twice) |
| 4a | **8 terms, all green** on the current page |
| 4b mechanical half | **both requirements pass** — text, and the heading with its level |
| soak (condition 1) | **0 / 12** — every banked run was for the old page |
| gates | queue 64 items 0 drifted, E1-C intact |
| findings opened | **087**, **088**, **089** |

## 1. What the human round found, and why 4a could not

The manual round (condition 3) failed on its third cell — see finding **086**,
and note it is **not a regression**: the shipped profile fails the same action.

Then 4b, agent-driven under the owner's recorded consent, found the thing this
gate exists for. A caret moving through the document announced **bare text**.
`E1-LC-HEADING` spoken twice, both times with no role and no level, in a
15 MB log with no heading announcement anywhere.

**4a was green throughout, and it was not wrong.** The tree really does carry
the heading at `level: 1`. 4a term 3 reads `#a11y-structure`; term 4 reads
`#a11y-para`; **no term asserted that the node changed by caret movement carries
a role**. The page had two projections and the announced one carried text only.
That is a coverage gap, not a disagreement — and it is exactly the split
(engine → page → tree, versus tree → one AT's speech) that A-1 created 4a and 4b
to keep apart. **The first time the split paid.**

The 2026-09-04 adjudication ruled the failure **blocking**, and — more usefully —
converted the block into a machine check: **4a gained term 8**, so unblocking
depends on a checker rather than on one Orca session.

## 2. The obvious fix does not work, and it was measured before it was trusted

The adjudication named both candidate mechanisms **unmeasured** and said to
measure before trusting either. Measured with Orca on a standalone probe page
(`findings/evidence/087/RESULT-mechanisms.md`):

| mechanism | Orca announced |
|---|---|
| `role="heading" aria-level="1"` on the live region | **text only, no role** |
| `role="listitem"` on the live region | **text only, no role** |
| `aria-activedescendant` → a roled node | **`heading 1`**, and **`List with 2 items`** |

**Putting the role on the live region is the one-attribute fix anyone would
reach for, and it does nothing.** The adjudication was right that the
`paragraph` role sitting there proved nothing by its silence — a *different*
role is equally unspoken.

**The control arm caught two void runs before either mechanism could be
believed.** Runs 1 and 2 announced nothing at all, including the control that
must speak: `sink.focus()` focuses an element without making the window active,
and `Page.bringToFront` does not raise a window on Wayland, so Orca's
`present-from-inactive-tab = False` discarded everything. Without the control,
"neither mechanism works" would have been the recorded conclusion — the opposite
of the answer.

## 3. 087, fixed, with the red case exhibited first — and it was the defect

`projectStructure()` now gives each node an id and points `#sink` at the focused
one through `aria-owns` + `aria-activedescendant`.

Term 8 was added to `check_4a.py` **before** the fix and run on the unfixed page:
term 8 red, the other seven green. **The red case was not constructed** — it was
finding 087 itself, the focused node being `textbox 輸入` with no
`aria-activedescendant` at all.

Confirmed by ear afterwards: `heading 1`, `heading 2`, `List with 2 items`, on an
arrow-key walk — the form the ruling requires, having said plainly that the
clicked walk cannot discharge 4b because *a screen-reader user cannot click ink
they cannot see*.

**One instrument limit nearly became a false conclusion.** Term 8 first read
`Accessibility.getFullAXTree`, which **omits both `focused` and
`activedescendant`**, so the working mechanism read as broken and was one step
from an adjudication request claiming the criterion was unsatisfiable.
`getPartialAXTree` carries both. **The criterion was measurable all along; the
call was wrong.**

## 4. 088: the fix made an old waste audible, and the owner heard it

With the AT's attention finally routed into the structure subtree, the owner
said: 「清單部份好像有重複的地方？它是念 living list 嗎？」 — `leaving list`.

Counted: each paragraph spoken **2–6 times**, `leaving list` **9**,
`List with 2 items` **10** for a document with two lists.

`projectStructure()` rebuilt the whole subtree on **every snapshot**, so the
containers and the pointed-at node were new DOM nodes each time. **The live
region had carried a guard against exactly this since it was written** — same
file, same reasoning, and the structure half never got it.

Guarded on a content signature (**the focus flag deliberately excluded**: it
changes on every caret move, which is precisely when the rebuild must not
happen; including it would leave a guard that looks present and never fires).
Measured after: `List with 2 items` **10 → 2**, which is the number of lists in
the document. That answered a question this tree had explicitly marked
unmeasured — the repetition was the rebuild, not Orca's own behaviour at list
boundaries.

**Not declared fixed.** Most paragraphs are still announced twice.

## 5. The residue's cause, from data already banked — and a revert

Read out of the existing walk record without a new run: of nine caret moves,
**eight changed both `aria-activedescendant` and the live region**. The ninth was
the second heading, where only the pointer changed — and it was announced
**exactly once**. Two channels, two announcements; one channel, one. Nine points,
no exception.

Silencing the live region when the structure covers the paragraph **turned
terms 4 and 8 red** — `distinct: 1`, all three placements reading
`E1-LC-HEADING`, while the pointer moved correctly through `a11y-node-0/1/2` in
the same records. **The product was right and the probe could not see it**:
`axReading` is `carried[0]`, the first AX node carrying the fixture marker, which
equals the focused paragraph *only because the live region carries its text*.

**Reverted rather than fixing the probe.** Changing an instrument so a failing
criterion passes is what the rules forbid the drafting party from doing alone,
and I was the author of the fix, the taker of the measurement and the drafter of
the criterion at once. Sent for adjudication; the page is back at `20f09cc9…`
with 4a green on eight terms.

**Recorded as its own problem**: term 4 says "three distinct readings, each
matching the paragraph targeted" and actually measures "the first node carrying
fixture text". A correct product that moved the text to another channel reddens
it. The next person to attempt this residue will hit the same red and think their
fix broke something.

## 6. ODS: the milestone's two risks are retired, and one file is not

The decisive measurement passed — the a11y+calc core opens and renders a
spreadsheet, `parts == 3` on the three-sheet fixture, `view-ready` on all,
tiles drawn, a truncated file refused with a typed error and the worker alive.
The memory question the plan called the real risk came back at **23.6 MiB at the
owner's class maximum against 596 MiB of headroom**.

The 306-file sweep: **303 open, 4 do not**. Three are password-protected and the
native oracle refuses them too. The fourth, `tdf149752.ods`, is
finding **089**: 13 KB, two sheets, **269 ms natively and a 180-second timeout on
the candidate**, reproduced 2 of 2 with the ODT control opening normally in the
same run. Its one distinguishing feature is `number-rows-repeated="1048550"` —
2²⁰ minus 26, the ODF way of saying "the rest of the sheet". **That is a
hypothesis and it is labelled one**; the one-variable test (cap the repeat
counts, change nothing else) was running when this was written.

**Also measured and registered**: a Calc view in this build logs `no
accessibility broadcaster?` — the projection that justifies this core **does not
extend to spreadsheets**. Not a reason to stop reading ODS; a reason that
milestone may never be described as accessible spreadsheet reading.

## 7. What today cost, and what it is worth

The page moved twice. **Every identity-bound artefact for `3dfdcfef…` is void**:
8 clean soak runs, the 3 diagnostics, the revert rehearsal including step 3, the
ODT round-trip, and 4a's seven-term discharge. `check_soak_bank.py` says
`cleanRuns: 0`, which is the criterion working.

**No soak run has been banked on the new page, deliberately.** If the pending
adjudication makes the residue fix viable, the page moves a third time and
anything banked now is void. That caution is itself in the adjudication ticket,
with the question of whether it is caution or stalling.

## What is left, in order

1. **The pending adjudication** on the term-4 coupling — it gates whether the
   page is stable enough to bank against.
2. **089's one-variable test** and its result, either way.
3. **12 clean runs on the settled page**, ≥3 UTC days with ≥2 each. The UTC day
   rolls at 08:00 CST.
4. **3 diagnostic runs**, the revert rehearsal with step 3, the ODT round-trip —
   all re-earned on the new sha.
5. **4b's mechanical half discharged** on the settled page: arrow keys, window
   focus held, 9 of 9.
6. **The owner's confirmation** against +24.5 MiB, with R5's wording — which now
   must say that `documentOutline` reaches the tree and, before 087, did not
   reach the caret path.
7. **086** is unfixed and ships today on v8.
8. **77 commits unpushed.** Pushing is the user's step.

## The thing worth carrying forward

Six machine checks were green while a screen reader user got nothing. The gate's
own design is what caught it — but only because 4b was written to measure a
different link from 4a, and only because a human listened. **Every instrument
here reports on the link it was pointed at, and the gap between two links is
invisible to both.**
