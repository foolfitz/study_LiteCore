# Round 3 — the shipped gesture, and clicks below the text with a caret that starts elsewhere

Exit 0.  Preserved exactly as it ran.  This is the round the design rests on.

## Outcomes

| prediction | outcome | what carried it |
|---|---|---|
| P-BI-0 control | HELD | `content: "BI-ANCHOR-ONE"` |
| P-BI-2a | HELD | a repeated click below the text: identical payload |
| P-BI-2b | **FAILED** | an x 400 twips left, below the text, still reads offset 7 |
| P-BI-2c | **FAILED** | there is no "inside the line" below the line — the clamp ignores x entirely |
| P-BI-3 | HELD | one line, `position` 13 → 45 |
| P-BI-4 | HELD | identical payload, caret y 2585 → 2974 |
| P-BI-5 | HELD | from another paragraph, a click below the text reports `BI-LAST` |
| P-BI-6 | HELD | the same x reads **4** on the line and **7** below it |
| P-BI-7 | HELD | `.uno:SelectText` returned `'    • \nBI-AFTER-EMPTY'` |

P-BI-1 is NOT_ESTABLISHED here by design: this round does not repeat the retired
pair.  `.uno:SelectText` sets `m_bInSelect` and nothing on that path clears it
(finding 039), so anything posted after it would be measuring a shell already in
selection mode.

## The two results that decide the design

**Finding 046 is separable by the payload the engine already receives.**

| step | a11y payload | caret y |
|---|---|---|
| click on the empty paragraph | `content: ""`, `position: 0` | 1807 |
| `.uno:DefaultBullet` | `content: "• "`, `listPrefixLength: 2` | 1807 |
| `.uno:SelectText` | `content: "BI-AFTER-EMPTY"`, `position: 14` | 2196 |

The read covers the empty list item *and* the paragraph below it.  The dispatch
paragraph and the read differ in the payload, and the barrier makes no such
comparison today.  The engine parses this payload already and keeps only
`contentLength` — 2 against 14 would have separated even this weaker form.

**Finding 052's residual is not about a missing datum.**

| arm | x | offset |
|---|---|---|
| `on-line-inside-x` | 400 twips left of the line's end, **on the line** | **4** |
| `below-from-elsewhere` | the line's end x, below the text | 7 |
| `below-from-elsewhere-inside-x` | the same 400-twips-left x, below the text | 7 |

x is carried on the line and dropped below it.  Every click below the text lands
at the same offset, so two of them are byte-for-byte identical — and a real
block index would not help, because the caret genuinely is in the last block and
the click has no expected destination to be compared against.

## Not established by this round

* **Anything about the WASM artifact.**  This is native core 26.8.
* **Where inside core the clamp happens.**  Not asked, and not to be guessed
  from these payloads — findings 040 and 048 are the precedents.
* **Whether the escape direction depends on the gesture.**  Two gestures escaped
  in two directions on two fixtures; that is two data points, not a rule.
