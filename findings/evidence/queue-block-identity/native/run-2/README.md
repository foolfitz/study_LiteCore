# Round 2 — clean run, and it measured the barrier this tree stopped shipping

Exit 0.  Preserved exactly as it ran.

## Outcomes

| prediction | outcome |
|---|---|
| P-BI-0 control | HELD |
| P-BI-1 | **FAILED** — see below |
| P-BI-2a | HELD, and weaker than it looks — see below |
| P-BI-2b / P-BI-2c | NOT_ESTABLISHED — no arm clicked at an x inside the line's text |
| P-BI-3 | HELD — `position` 13 → 45 across one line |
| P-BI-4 | HELD — identical payload, caret y 2585 → 2974 |

## P-BI-1 failed because the probe used the retired gesture

The arm posted `.uno:GoToStartOfPara` + `.uno:EndOfParaSel`.  That is the
**pre-034** pair; finding 034 replaced it, and the shipped engine posts
`.uno:SelectText` (`kFormatBarrierSelectCommand` in `src/probe_engine.cpp`).
So this round says nothing about the barrier the product runs.

What it does say is worth keeping.  On the bulleted empty paragraph the retired
pair escaped **upward**:

| step | a11y `content` | caret y |
|---|---|---|
| click on the empty paragraph | `""` | 1807 |
| `.uno:DefaultBullet` | `"• "` (`listPrefixLength: 2`) | 1807 |
| the retired pair | **`"BI-ANCHOR-ONE"`** | **1418** |

and the readback is `<p>BI-ANCHOR-ONE</p>` — the paragraph *before* the one the
action was dispatched on.  Finding 046's own evidence has the escape going
downward on a different fixture and a different gesture.  Round 3 posts the
shipped command and the escape goes downward there too.

P-BI-1 as registered names `BI-AFTER-EMPTY` in the read, so it is FAILED, and it
stays FAILED.  Its **substance** — that comparing the read against the caret
paragraph's payload separates the two — is supported here and confirmed by
P-BI-7 in round 3, but that is a post-hoc reading of this round, not a
prediction it carried.

## Why P-BI-2a's HELD is weaker than it looks

Every below-the-text arm in this round started with the caret *already* at the
end of `BI-LAST`, because the search that located the line put it there.  So
"the payload did not move" is equally consistent with "the click never
arrived".  Round 3's arms each start from another paragraph, and P-BI-5 shows
the click does arrive.
