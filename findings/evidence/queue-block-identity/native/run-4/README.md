# Round 4 — round 3's arms plus the witnesses an adversarial review said were missing

Exit 0.  Preserved exactly as it ran.  **This is the round the below-the-text
results rest on**; round 3 measured the same numbers but could not prove the two
premises its arms were named for.

## What changed from round 3

Two arms and two fields, all so the judge reads what the probe claims:

* `before-below-from-elsewhere` and `before-below-inside-x` — the caret's
  paragraph *immediately before* each below-the-text click.  Without them,
  "from a caret on another paragraph" was the arm's name rather than a reading,
  and a caret already on `BI-LAST` with a click that never arrived would have
  produced the same row.
* `clickX` / `clickY` on every arm — P-BI-6 asserts "the same x, on the line and
  below it" and previously compared only offsets.

## Outcomes

| prediction | outcome | what carried it |
|---|---|---|
| P-BI-0 control | HELD | `content: "BI-ANCHOR-ONE"` |
| P-BI-1 | NOT_ESTABLISHED | this round does not run the retired pair (see round 2) |
| P-BI-2a | HELD | a repeated click below the text: identical payload |
| P-BI-2b | **FAILED** | an x 400 twips left, below the text, still reads offset 7 |
| P-BI-2c | **FAILED** | the clamp ignores x entirely; there is no "inside" below the line |
| P-BI-3 | HELD | one paragraph, both rectangles valid, `position` 13 → 45 |
| P-BI-4 | HELD | identical payload, both rectangles valid, caret y 2585 → 2974 |
| P-BI-5 | HELD | the caret was on `BI-ANCHOR-ONE` before the click and on `BI-LAST` after it |
| P-BI-6 | HELD | the same x (1937) reads **4** on the line and **7** below it |
| P-BI-7 | HELD | `.uno:SelectText` returned `'    • \nBI-AFTER-EMPTY'` — the neighbour by name |

## Re-judge

```
python3 tools/analyze_queue_block_identity.py \
  findings/evidence/queue-block-identity/native/run-4
```

The judge's self-test is 27 checks; every clause of every predicate has a
mutation that moves the verdict on its own.

## Still not established

Unchanged from round 3, and worth repeating because this round is the one that
gets cited:

* **Nothing here describes the WASM artifact.**  Native core 26.8.
* **Where inside core the clamp happens** is not asked and must not be guessed.
* **The scope of "x is dropped below the text"** is this fixture's last
  paragraph at three x values.  Not measured: the left margin, other page
  regions, other document structures, right-to-left text, tables.
