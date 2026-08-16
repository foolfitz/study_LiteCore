# Round 1 — settled three predictions and exited 9 on the fourth

Preserved exactly as it ran.  `verdict.json` is the judge's output for these
captures under the criteria as they stand now; the paragraph below records the
one place where those criteria changed after this round and why.

## What it established

| prediction | outcome |
|---|---|
| P-BI-0 control | HELD — `content: "BI-ANCHOR-ONE"`, so accessibility was on |
| P-BI-2a | HELD — a repeated click below the text left the payload byte-for-byte identical |
| P-BI-3 | HELD — one line, two x, `position` 13 → 45 |
| P-BI-4 | HELD — two paragraphs with the same text, one identical payload, caret y 2585 → 2974 |

## Two arms that did not test what they were written to test

1. **The probe exited 9 before finding 046's cell.**  It navigated by searching
   for `BI-ANCHOR-ONE` a second time — and the caret was already there, so no
   `INVALIDATE_VISIBLE_CURSOR` arrived and `searchFor` read that as "not found".
   **A search that does not move the caret is indistinguishable from a search
   that found nothing**, which is finding 052's shape one level up.  Round 2
   navigates from a different paragraph.
2. **P-BI-2b's two x were both at or past the end of the last line.**  The
   fixture's last paragraph is `BI-LAST`, seven characters, and the search left
   the caret at offset 7; the arm clicked there and again 2400 twips to the
   right.  Both clamp to offset 7 by construction.

The judge originally reported P-BI-2b as FAILED for this round, on a bare
comparison of the two positions.  It now reports NOT_ESTABLISHED, because the
arm cannot bear on the claim: **this weakens the criterion, and it is a
statement about the probe rather than about core.**  The change is recorded in
the addendum to `../PREDICTION.md`, written before round 2 ran, and round 3 adds
the arm that does test it (P-BI-6, HELD).
