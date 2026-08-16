# Finding 046, native arm — the readback describes the paragraph ABOVE

Produced 2026-08-16 by `tools/run_f046_native.sh` against
`build-native-26-8/instdir`, core commit `671c848b…` — the commit the
`e2-editor-v2` WASM profile is built from.  Predictions in `PREDICTION.md`,
registered before the probe was written.

Classification is done by **the engine's own parser**:
`tools/test_format_readback_parser.py` slices the scanner out of
`probe_engine.cpp`, compiles it, and runs it over the captured markup.  No
Python restatement of the rules is involved.

**Nothing here describes the WASM artifact.**

## What was asked

046's remedy (relink queue item 3b) needs a criterion, and the 2026-08-15
correction says why it could not be written: the same empty paragraph produces
`postcondition-not-met` after one gesture and `multi-block-readback` after
another, both with `postBlocks: 0`, and the difference turns on `itemCount`,
which the shipped product does not project.

## What came back

`test-docs/e1/empty-paragraph.odt`: `E1-EMPTY-BEFORE`, empty, `E1-EMPTY-AFTER`,
empty.

| arm | caret y | selection type | readback |
|---|---|---|---|
| `click-text-pair` (control) | 1418 | 1 (text) | `E1-EMPTY-BEFORE`, 495 bytes |
| `click-empty-bare` | **1807** (the empty line) | 0 (none) | **empty string** |
| `click-empty-pair` | **1418** | 1 | **`E1-EMPTY-BEFORE`**, 495 bytes |
| `select-empty-bare` | **1807** | 0 | **empty string** |
| `select-empty-pair` | **1418** | 1 | **`E1-EMPTY-BEFORE`**, 495 bytes |
| `after-bullet-bare` | 1807 | 0 | empty string |
| `after-bullet-pair` | **1418** | 1 | **`E1-EMPTY-BEFORE`**, 495 bytes |
| `last-empty-bare` | 2585 (the last, empty) | 0 | empty string |
| `last-empty-pair` | **2196** | 1 | **`E1-EMPTY-AFTER`**, 494 bytes |

**On an empty paragraph, the barrier's own selection pair —
`.uno:GoToStartOfPara` then `.uno:EndOfParaSel` — moves the caret UP and selects
the paragraph above.**  Measured at two different positions (mid-document
1807 → 1418, last paragraph 2585 → 2196), before and after the action.

### The action did reach the document

Saved after the run: the empty paragraph really did become a list item.

```xml
<text:p text:style-name="Standard">E1-EMPTY-BEFORE</text:p>
<text:list text:style-name="L1"><text:list-item>
  <text:p text:style-name="P1"/>
</text:list-item></text:list>
<text:p text:style-name="Standard">E1-EMPTY-AFTER</text:p>
```

So this is not "the bullet did nothing".  **The action worked and the check
looked somewhere else.**

## What the engine's parser makes of it

Run over the captures, and over hand-built markup for the shapes 046 inferred:

| markup | parsed | blockCount | itemCount | multiBlock |
|---|---|---|---|---|
| the pair readbacks above | 1 | **1** | 0 | 0 |
| empty string / whitespace / `<html><body></body></html>` | **0** | 0 | 0 | 0 |
| `<ul><li></li></ul>` | 1 | **0** | 1 | 0 |
| `<ul><li></li><li></li></ul>` | 1 | **0** | 2 | **1** |

Two things settled:

1. **An empty readback is `parsed = false`**, not `parsed && blockCount == 0`.
   Any criterion written as "parsed with zero blocks" would miss it.
2. **`blockCount == 0` with `itemCount ≥ 1` is real in the parser** — and with
   two items it is `multiBlock` with no block in it, which is exactly the
   combination 046 inferred from the shipped product's contradictory message
   ("covered more than one paragraph" beside a paragraph count of 0).

## Predictions, scored as written

| | | |
|---|---|---|
| P-046-1 | an arm produces `parsed=true, blockCount=0` | **FAILED** — every pair readback has blockCount 1; the bare ones are `parsed=false` |
| P-046-2 | the control produces `blockCount >= 1` | **HELD** |
| P-046-3 | the two gestures differ | **FAILED** — natively they are identical, in caret position, selection type and markup |
| P-046-4 | an arm shows `itemCount > blockCount` | **NOT OBSERVED** from core; the shape exists in the parser but this round did not make core emit it |

## What this does to relink queue item 3b

`PREDICTION.md` registered three outcomes in advance.  The third one applies —
`blockCount == 0` never occurred natively — and it says the browser evidence
then needs re-explaining, **which is itself a finding**.

So 3b is **not withdrawn and not written**: it is blocked on a question that is
now sharper than the one it was blocked on before.

- **Before**: "is zero blocks nothing-read or only-list-items?"  Unanswerable on
  the shipped product because `itemCount` is not projected.
- **Now**: core's readback for an empty paragraph is **the paragraph above,
  with one block in it**.  The shipped build reports **zero** blocks for the
  same gesture on an empty paragraph.  Those disagree, and until that is
  explained, a shape named `empty-readback` would be named after a symptom
  whose mechanism is unknown.

And a second thing is now on the table, larger than 046's classification bug:
**the barrier verifies a paragraph the action did not touch.**  On an empty
paragraph the selection pair walks up one paragraph, so the postcondition
compares the wrong text — the same family as finding 048, where the product
confirmed a click that had not landed.  046's own remedy (rename the outcome)
does not touch that.

## Addendum (2026-08-16, later the same day): the gesture measured here is NOT the barrier's

This round dispatches `.uno:GoToStartOfPara` then `.uno:EndOfParaSel`
(`tools/f046_native_empty_readback.cpp:126-127`) and calls that "the barrier's
own selection pair".  **The shipped barrier does not use it.**  It posts a
single `.uno:SelectText` (`src/probe_engine.cpp:804`, dispatched by
`postFormatBarrierParagraphSelection()`), and the comment directly above that
function records why: the pair reordered its own effects (finding 033) and
**escaped to a neighbouring paragraph whenever the caret already sat at a
paragraph edge** (finding 034).

So this round re-measured the superseded gesture -- and re-measured exactly the
defect that superseded it.  **The numbers here are real; what they describe is
the old pair, not the shipped barrier.**

Measured the same day off the frozen engine, with the barrier's actual gesture
(`findings/evidence/046/diagnostic-readback/`): on the same empty paragraph the
readback is `parsed:true, blockCount:2` -- the bullet applies and the selection
swallows the paragraph BELOW, not the one above.  Containment holds there, so
the "verifies a paragraph the action did not touch" conclusion below does not
carry over to the shipped barrier either.

**What survives from this round**: the parser facts (an empty read is
`parsed=false`; `blockCount 0` with `itemCount >= 2` is representable), the
saved document proving the action applies, and the discipline of classifying
with the engine's own scanner.

## Reproducing

```
tools/run_f046_native.sh <a NEW directory>
python3 tools/test_format_readback_parser.py --captures <that dir>/captures.jsonl
```

Three rounds are kept: `run/` (the first, arms 1–2), `run-2-after-action/` (adds
the dispatch), `run-3-last-and-save/` (adds the last paragraph and the save that
proves the action applied).  A round is a record; the runner refuses to write
into a directory that already holds one.
