# W-3: the four inline-format checks, and which of them was actually uncovered

Work item W-3 of `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md`, done
2026-09-03. The item was written from a census taken 2026-08-28 which reported
**five** of the 40 product-path checks as carrying no mutation at all, four of
them in the inline-format family.

**The census was too strong, and the correction is the main result.** Asking a
different question — *has this check ever gone red, and under what?* — over all
160 reports carrying `release == "e2-c-product-path"`:

| check | PASS | FAIL, unmutated | FAIL, collateral of another mutation | NE |
|---|---|---|---|---|
| `every-inline-format-reaches-the-document` | 109 | **3** (2026-08-23) | 0 | 3 |
| `formatting-survives-the-next-paragraph-break` | 109 | **2** (2026-08-22) | 2 (`copy`, `ime`) | 2 |
| `a-format-that-worked-is-not-reported-as-failed` | 125 | **2** (2026-08-18) | 2 (`inline-format-rollback`, `caret-ignores-x`) | 0 |
| `clear-format-removes-every-inline-format` | 104 | **0** | 0 *(before today)* | 10 |

Three of the four have gone red **in the field, with no mutation applied** —
which this plan already treats as stronger evidence than a synthetic mutation,
in the sentence that excused `caret-follows-the-text-you-type` from the same
list. Two of them additionally go red as collateral of existing mutations, so
"has no mutation" was true only of *dedicated* ones.

**The hole was one check, not four**: `clear-format-removes-every-inline-format`
had 104 passes, 10 abstentions and had never once gone red.

**W-3 therefore produces no finding**, and the soak count is untouched. The
coupling written into W-3 fires when a mutation is unwriteable *because the
check cannot fail*; here the four can all fail, and three had already shown it.

The census script is banked beside this file and re-runnable. It now includes
today's own mutation run, which is why the last row reads `FAIL 1` in the JSON.

## The mutation that closes the one real hole

`clear-format-leaves-one-format-on` → `clear-format-removes-every-inline-format`.
The clear button clears three of four, **only when all four were on** — which is
the case a user presses it for. Measured:

```
verdict: the mutation was detected by the check that owns it
clear-format-removes-every-inline-format  FAIL
  everyFormatWasOn: true
  allOnWhenTyped:  {bold: true, italic: true, underline: true, strikethrough: true}
  cleared:         {bold: false, italic: false, underline: false, strikethrough: TRUE}
```

Blast radius, **measured**: nothing else moved. The only non-PASS cells are the
two standing NOT_ESTABLISHED ones. `alsoRed` and `alsoNotEstablished` are empty
because they were measured empty, not because nothing was written in them.

## Two attempts that did not fire, and the shape they share

Both are banked; a mutation that fails to fire is worth more in the record than
out of it, because it is the same shape twice.

**Attempt 1 — `format-success-reported-as-failure`.** A successful `set-bold`
that reports `LOK_COMMAND_FAILED` to the user: finding 059's exact shape. It was
written to fire **once**, deliberately, to keep the radius small. It fired in the
wrong place. `the-keyboard-reaches-the-document` presses **Ctrl+B** long before
the check under test, and the page routes the accelerator through the same
`editorAction` as the button — on purpose, with a comment saying so, *"so the
shortcut and the button cannot drift apart"*. The single shot was spent there.
The runner said so plainly: `THE MUTATION WAS NOT DETECTED`.

**Withdrawn rather than widened.** Making it fire on every bold press would
work and would invert all four bold arms; and the check it targets already has
two unmutated field FAILs and two collateral reds. Building a wide-radius
mutation to cover a check that has twice demonstrated it can fail is machinery
sustaining a claim that is no longer true (`AGENTS.md` §4).

**Attempt 2 — `clear-format-skips-strikethrough`.** Drop `set-strikethrough`
from `clearInlineFormatting`'s loop. It made the target **abstain**, not fail:

```
allOnWhenTyped: {bold: true, italic: true, underline: true, strikethrough: FALSE}
everyFormatWasOn: false  ->  NOT_ESTABLISHED
```

`#clear-format` is both the button under test **and** the normaliser
`format_arm` runs before each of its eight arms. A clear that leaves a format
on inverts that format's toggle polarity for the following arm (finding 077's
shape), so MKALLON never got all four and the precondition the check needs was
destroyed by the mutation meant to test it.

**The shape both share.** *A check whose precondition is established by the
mechanism under test cannot be reddened by breaking that mechanism — it
abstains.* Both attempts assumed a narrow radius from reading; both were wrong
in a direction reading does not reveal. The third version fixes it by
conditioning on **state** rather than on a count or a single shot: the skip
fires only when all four formats are already on, which is the state of the press
under test and never the state of a normalising press. Conditioning on a call
count would pass today and go silently inert the moment an arm is added — the
same defect one layer up.
