# The double announcement is present on the profile a cutover would ship

Measured 2026-09-03 for `queue-list-prefix-read-twice`, characterised
2026-08-23 on the accessibility projection and never since checked against a
**candidate**. Verdict: **present, 4 of 4 list items, three runs agreeing.**

## Why this was answered without a new run

The question is *what does the AX tree on the candidate page contain*, and three
AX trees taken on that exact page (`pageSha256 3dfdcfef…`) were already banked
as gate condition 4a's evidence. Spending a run to re-ask a question the record
answers is how a record stops being used.

## What is there

Every list paragraph is projected as `role="listitem"` with `level: 1` — from
which a screen reader speaks the marker itself — **and** its own text begins
with that same marker:

| listitem | text an AT would read |
|---|---|
| `level: 1` | `• E1-LC-BULLET-ONE` |
| `level: 1` | `• E1-LC-BULLET-TWO 中文項目` |
| `level: 1` | `1. E1-LC-NUMBER-ONE` |
| `level: 1` | `2. E1-LC-NUMBER-TWO` |

So the marker is announced twice: once from the role, once from the text.

**The shipped control has neither**: `documentTextInTree: false`, zero
`listitem` nodes. v8 has no double announcement because it has no announcement.

## Two instrument errors caught here, both mine

**A prefix pattern cannot tell a document from a toolbar.** The first pass
counted **6** items carrying their own marker. Two of them were the toolbar's
own buttons, labelled `• 項目符號` and `1. 編號` (`role: button`, nodeIds 27 and
28). The count was corrected by resolving each `listitem` to its own descendant
text through `childIds` — structure, not a string that looks like a bullet.

**Comparing node ids reported a difference the product does not have.** The
first reproducibility check compared the whole record across the three runs,
`nodeId` included, and declared them in disagreement. AX node ids are
per-session. Compared on level, name, text and the flag, the three runs are
identical. An instrument that reports a difference the product does not have is
the same defect as one that hides a difference it does.

## What this means for the cutover

This is on the **benefit** side — the only side the gate has not measured — and
it is the kind of thing a screen reader user meets in the first ten seconds.
It is **not** a reason the candidate is worse than the incumbent: v8 announces
nothing at all, so v12 is still strictly more usable. It is a reason the human
round (condition 3 with 4b folded in) should expect to hear it rather than
discover it, and a reason the cutover record must name it.

**Not fixed here, and the queue item already says why**: the obvious remedy is
to strip `listPrefixLength` characters, and that field is exactly what finding
074 describes — it returns the end of the first attribute run, not the prefix
length, and it returned 13 for a heading whose true prefix is 0. Two samples
that happened to be right is not a licence to slice text on a field with a known
upstream defect. Any fix is also a shell change, which mints a generation and
restarts the soak, so it is post-cutover work either way.
