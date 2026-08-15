# SPEC E2-B section 7: the positive matrix on the product artifact

**Date** 2026-08-15. Artifact `572035ac…`, profile `e2-editor-v2`, driven
through the **product** v2 client. Prediction:
[`PREDICTION.md`](PREDICTION.md), committed before the harness existed
(`3316c76`).

**132 runs** — 22 arms x 3 rounds x 2 browsers. Chrome and Firefox are
**cell-for-cell identical, all 66 cells**, and the route each arm took is
identical too.

## Verdict

| | |
|---|---|
| 21 arms | **pass 3/3, both browsers** |
| the self-red arm | **fails 3/3, both browsers — which is its pass** |
| arms not as required | **none** |

Routes: 6 cells `collapsed`, 8 `range-single`, 8 `range-cross`, and every arm
took the route it intended. An arm that had drifted into another class would be
visible rather than counted, because the record carries the route the **engine**
reported, not the one the harness asked for.

## Each run had to satisfy all six

The route matched; the action completed with `changed: null` and
`verified-format-readback`; `revision == before + 1`; the targeted paragraphs
reached the target state; **every other paragraph was byte-unchanged**; and for
the crossing route both `crossIdentityHeld` and `crossStateHeld` held.

Criterion five is the load-bearing one. All five actions are paragraph-level, so
without it a range that silently collapsed to a caret would satisfy every other
check — the hole SPEC 3.4 was written to close.

## The three predictions that had no basis, and what they did

`PREDICTION.md` marked three as unsupported. All three held, and the two list
ones matter because a **stop condition** depended on them.

**List transition (`ul → ol`)**: only `E1-LC-BULLET-ONE` changed; the other item
in the same list did not. No structural loss. Until this run **nothing in this
project had ever dispatched a list action onto an already-listed paragraph**, so
"list switching causes silent ODT structure loss" was a stop condition that
could not fire. It can now, and it did not.

**Mid-list departure**: items TWO and THREE left a five-item list; ONE, FOUR and
FIVE stayed. The list split rather than truncating.

**Mixed-state crossing**: only `E2B-MIXED-PLAIN` changed — the other paragraph
in the crossing range was already a list item, so applying the same action to it
was a no-op at the document level while the range still covered both.

## The no-op equation, measured for the first time

7.1 states it: every completed action advances the revision by one, **including
one that changes nothing**. No round in this project had ever dispatched the
same action twice on the same paragraph.

Measured: the repeat completed, `revision` went 1 → 2, and `<office:body>` was
**byte-identical** to the save taken between the two dispatches. Both browsers,
three rounds.

## The self-red arm

9.9 requires the judge to demonstrate it can report a state mismatch rather than
asserting it. The arm dispatches bullet while telling the judge to expect an
ordered list, so a correct judge **must** fail it. It fails 3/3 in both
browsers, and the summary reports `selfRedBehavedAsRequired: true` separately
from the ordinary pass counts so that its failure cannot be mistaken for a
defect or quietly counted as a pass.

## Two harness faults this run found before it bound anything

**The judge guessed at ODF.** The first version required `<text:h>` for a
heading and failed all three heading arms. The document showed the engine had
worked: `text:style-name` went `Standard` → `Heading_20_1`, with the element
left as `<text:p>`. **SPEC E2-A 10.2 had already measured and corrected exactly
this expectation** — "期望值錯，不是產品錯" — and this analyzer made the same
guess. Recorded consequence, since it is a real difference: a paragraph carrying
the heading style but exported as `<text:p>` has no `text:outline-level`, so it
does not join the document outline the way an authored `<text:h>` does. The
contract promises the heading **style** (narrowing 2, H1 only) and has never
promised outline participation.

**The harness swept inside each arm**, on the very document that arm then
measured — twenty `selectRange` calls before the one that mattered. The
section-3 gate had already learned not to do that, and the cost appeared at
once: the wrapped arm's span read back as its first visual line instead of the
whole run. The survey now runs once per fixture on a throwaway document.

A third fault is worth recording because of how it was handled: the first
binding run was launched before the harness reported `selfRed` and `repeat` to
the judge, so the self-red arm would have been counted as an ordinary pass.
Chrome had already finished when this was noticed. **That half was discarded and
both browsers re-run** — one evidence set containing two harness versions is
worse than half an hour of wall clock.

## What this does not cover

- **`set-list-ordered` was never dispatched onto a crossing range whose
  paragraphs are already numbered.** Mixed-state covers listed-plus-plain;
  numbered-plus-numbered is not here.
- H2–H6 remain out of scope (narrowing 2).
- Physical pointer drags are still not measured: ranges arrive as coordinates.
