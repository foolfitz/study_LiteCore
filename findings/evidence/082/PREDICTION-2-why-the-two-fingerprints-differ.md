# Prediction 2, written before reading the paragraph trace

Written 2026-08-26, after
[`PREDICTION-which-paragraph-was-read.md`](PREDICTION-which-paragraph-was-read.md)
**was refuted**, and while the run carrying the trace was still going.

## What the first widened run settled

`--barrier-details-diagnostic` now also widens the worker's
`productFormatBarrier` allowlist, so the engine's whole barrier object reaches
the report. On the failing `內文` arm:

```json
{ "stage": "awaiting-restore", "command": ".uno:StyleApply",
  "expectedStyles": ["Body Text"],
  "resultSuccess": true, "resultModified": true,
  "readback": { "parsed": true, "blockCount": 1, "blockTag": "p",
                "html": "… <p>E1-LC-HEADING</p> …" },
  "containment": { "checked": true, "held": true,
                   "selectionTop": 1418, "selectionBottom": 1693,
                   "restoreCentre": 1625 } }
```

**The prediction was wrong and the correction is the finding.** The readback
did NOT describe a different paragraph: `readback.html` is the paragraph the
action was dispatched on, `E1-LC-HEADING`, and it is a `<p>` — the style change
**took effect**. The engine's own result callback agrees (`resultSuccess`,
`resultModified`). The restore landed inside the selection it produced
(1625 ∈ [1418, 1693]), and the band is 275 twips — a body line, not a heading's.

So the mutation was correct, the barrier's own read was of the correct
paragraph, and **the identity gate refused it anyway**. Its disposition is
"roll back to your checkpoint", and on this profile there is no checkpoint.

The gate compares two `a11yContentHash` values. `readback.html` comes from
`getTextSelection`. **Those are two different questions** — one asks what the
barrier selected, the other what the accessibility layer says the caret is in —
and nothing in the barrier ties them together. That is the gap this run is for.

## The prediction

The trace records `editorState.caretParagraph` on every state transition:
`fingerprint`, `text`, `length`, `offset`, `listPrefixLength`, `fresh`.

**(a) The likely one — the slice, not the content.** `text` is IDENTICAL at the
two moments (`E1-LC-HEADING` both times) and `fingerprint` differs, because
`listPrefixLength` differs. The fingerprint is FNV-1a over
`content[listPrefixLength:]`, and finding 074 already recorded that **LOK
reports the first attribute run as the list prefix** — a heading and a body
paragraph do not split into the same runs, so the same text is sliced at two
different places and hashed to two different numbers.

If that is what the trace shows, the defect is: *the fingerprint is not an
identity for the paragraph, it is an identity for the paragraph's first
attribute run*, and any action that changes character formatting at the start of
a paragraph will fire this gate.

**(b) The other one.** `text` DIFFERS between the two moments — the
accessibility focus was on another paragraph while the barrier's selection was
on the right one. Then the gate is comparing a quantity that does not track its
own read, and the remedy is a different one.

**(c) `fresh: false` at one of the two moments**, which would mean the gate
compared a fingerprint the engine had already declared not current. The gate
requires `refreshCaretParagraph()` to return true at both ends, so this should
be impossible; recording it here because "should be impossible" is how the last
two of these went.

## What is being predicted, in one line

**(a)**: same `text`, different `listPrefixLength`, different `fingerprint`.
