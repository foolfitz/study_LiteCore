# `queue-verify-caret-by-block-identity` — what the datum is, and what it settles

Three native rounds against LibreOffice core 26.8 (`build-native-26-8`), judged
against predictions registered before each round ran:
[`native/PREDICTION.md`](native/PREDICTION.md).

**Nothing here describes the WASM artifact.**  Native, for the reason finding
048's native arm was native: a payload observed only through our transport
cannot separate what core reports from what our worker forwards.

## The queue item said three ambiguities reduce to one missing datum.  Two do.

| ambiguity | settled by this datum? | measured |
|---|---|---|
| **finding 046** — the barrier verifies the wrong paragraph | **yes** | round 3, P-BI-7 |
| **same line, different x** — `caretIsOnLine` has no x | **yes**, but by the *offset*, not by block identity | round 2, P-BI-3 |
| **finding 052's residual** — a second click outside the text | **no**, and the reason is measured | round 3, P-BI-5/P-BI-6 |

## There is no block index, and the thing that exists is a fingerprint

Established by reading core, not by measurement: the focused-paragraph payload —
shared by `getA11yFocusedParagraph()` and `LOK_CALLBACK_A11Y_FOCUS_CHANGED` —
carries `content`, `position`, `start`, `end` and `listPrefixLength`
(`sfx2/source/view/viewsh.cxx`, `paragraphPropertiesToTree`) and **no paragraph
index**.  No `getCommandValues` command in Writer supplies one either.

Measured (round 2 and round 3, P-BI-4): the caret in each of two paragraphs
whose text is identical produces a payload that is **byte-for-byte the same**,
while the caret rectangle moves from y 2585 to y 2974.  So what is available is
a **fingerprint of the paragraph, not its identity**.

That distinction decides how far the datum can be pushed.  It is enough to
answer *"is this the paragraph I dispatched on?"* — which is finding 046's whole
question.  It is not enough to answer *"which paragraph is this?"*

## Finding 046, reproduced natively on the gesture the product actually uses

Round 3, on the empty paragraph, with the shipped
`kFormatBarrierSelectCommand`:

| step | a11y payload | caret y |
|---|---|---|
| click on the empty paragraph | `content: ""`, `position: 0` | 1807 |
| `.uno:DefaultBullet` | `content: "• "`, `listPrefixLength: 2` | 1807 |
| `.uno:SelectText` | **`content: "BI-AFTER-EMPTY"`, `position: 14`** | **2196** |

and the readback for that selection is `'    • \nBI-AFTER-EMPTY'` — the empty
list item **and the paragraph below it**, which is finding 046's shape
(`<ul><li><p></p></li></ul><p>E1-EMPTY-AFTER</p>`) on a second fixture.

**The dispatch paragraph and the read differ in the payload the engine already
receives.**  A comparison detects the overshoot; the barrier does not currently
make one.  Note that the engine keeps only `contentLength` from this payload and
discards `content` — and even the length alone (2 against 14) would have
separated this case.

Round 2 measured the **pre-034** pair (`.uno:GoToStartOfPara` +
`.uno:EndOfParaSel`) by mistake, and it escaped **upward**, to the paragraph
*before* the empty one.  Two gestures, two directions, same failure to stay in
the dispatch paragraph.

## Finding 052's residual is not a missing-datum problem

Round 3, each arm starting from a caret on a different paragraph so that a
delivered click is distinguishable from no click at all:

| arm | x | result |
|---|---|---|
| `below-from-elsewhere` | end-of-line x | `BI-LAST`, position **7** — the click arrives and clamps |
| `below-from-elsewhere-inside-x` | 400 twips left | `BI-LAST`, position **7** |
| `on-line-inside-x` | the same 400 twips left, but **on the line** | `BI-LAST`, position **4** |

So **x is carried on the line and dropped below it**: every click below the text
lands at the same offset, whatever its x.  Two such clicks are therefore
byte-for-byte identical in the payload (P-BI-2a), and a *real* block index would
not help either — the caret genuinely is in the last block, and the click has no
expected destination to compare it against.

This is the part of the queue item that does not survive: 052's residual needs a
decision about what success means for a click that lands outside the text, not a
better datum.

## What each round is

| | |
|---|---|
| [`native/run/`](native/run/) | round 1.  Exit 9: the probe searched for a paragraph the caret was already on, and a search that does not move the caret is indistinguishable from one that found nothing.  P-BI-2a/3/4 settled here |
| [`native/run-2/`](native/run-2/) | round 2, clean.  Measured the retired barrier pair; found the upward escape |
| [`native/run-3/`](native/run-3/) | round 3, clean.  The shipped `.uno:SelectText`, and the below-the-text arms with a caret that starts elsewhere |

Re-judge any of them:

```
python3 tools/analyze_queue_block_identity.py \
  findings/evidence/queue-block-identity/native/run-3
```

The judge carries a self-test (18 checks) in which every predicate is flipped
and must move the verdict.
