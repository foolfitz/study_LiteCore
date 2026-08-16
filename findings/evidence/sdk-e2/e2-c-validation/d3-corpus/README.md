# E2-C phase D3 — the corpus half, and which round is which

Predictions were registered in `PREDICTION.md` before the harness existed.
`tools/analyze_e2_c_d3_corpus.py` applies them offline; the page judges nothing.

| directory | what it is | usable as evidence for |
|---|---|---|
| `run-1/` | the first execution. Five cells dispatched; the three `l0-t3` cells refused with `CARET_NOT_AT_ANCHOR` | the harness's tolerance constant, see below |
| `run-2-line-box/` | the same eight cells with the caret rule fixed. All eight dispatched, both browsers | the first structural measurement, and the `l4-stress-100` frame loss |
| **`run-3-with-controls/`** | **the canonical round**: the eight cells plus one no-action control per fixture | **the six predictions** |

## What run-1 measured, and why it is kept

Three cells refused, both browsers, identically -- and that identity is what
made the cause attributable.  The anchors in `l0-t3` are headings with a
**520-twip line box**, the harness aimed at the middle of the line, and the
caret came back reporting the line's top: 260 twips away, refused by a tolerance
constant of 195.

195 is half the *list* corpus's line pitch.  The caret was on the right line the
whole time; the rule was calibrated on a different document.  The product itself
accepted the click -- it uses half the caret rectangle's own height, which is
260 here -- so this was the harness refusing what the product had correctly
done.

The fix is not a bigger constant.  `web/e2-c-caret.js` gained `caretOnLine`: the
anchor's measured rectangle travels with the click, and acceptance is "these two
line boxes overlap by more than half the caret's height".  No constant, and an
adjacent line -- which does not overlap at all -- can never satisfy it.  The
sweeping harness in the list half keeps the old rule, because it has no anchor
rectangle to compare against and its rounds are already recorded.

## What run-2 measured: `l4-stress-100` loses 100 images, and it is not ours

Both `l4` cells failed `structurePreserved`: 100 `<draw:frame>` and 100
`<draw:image>` in the fixture, **zero** in the save.  The ZIP agrees -- the
`Pictures/` entry is gone and the document shrank from 35,772 to 14,977 bytes.

That is the shape of D3's stop condition, so it got the control it deserved
before anything was concluded:

| control | frames after | images after |
|---|---|---|
| fixture on disk | 100 | 100 |
| system LibreOffice 26.8, `--convert-to odt`, **no editing** | **0** | **0** |
| `build-native-26-8` (the core commit the WASM profile is built from), same | **0** | **0** |

**Neither LibreOffice keeps them, with no editor involved at all.**  The markup
says why: every frame is `<draw:frame text:anchor-type="as-char">` sitting
directly under `<office:text>`, a sibling of `text:p` rather than inside one.
An as-char anchor with no character to anchor to is not something the import
filter keeps.

So this is a **corpus defect** -- `l4-stress-100.odt` claims 100 images it
cannot round-trip through any LibreOffice -- and not a product one.  E1-C
already recorded half of this on 2026-08-13 ("attribute 101, effective 1"); the
part that was missing is that the ineffective 100 do not survive a save.

The criterion changed accordingly, and this is a **correction, not a
relaxation**: structure is now compared against a **no-action control save of
the same document**, which is the only comparison that can tell a corpus defect
from a product defect.  The list half learned the same thing at a smaller size
in L6, and for the same reason.

## run-3, the canonical round

Eight cells plus five controls, Chrome and Firefox.

| | |
|---|---|
| cells dispatched | **8/8 in both browsers**, caret confirmed `engine-acknowledged` in 22–29 ms |
| required anchors | preserved at the same count in every cell, including every per-page anchor of the 22-page and 100-page corpora |
| structure vs the control | identical in every cell |
| forbidden content | none |
| desktop reopen + PDF | passed for every saved document |
| carried fixtures | `list-contexts` and `list-split` pass the same criteria on the documents the L round saved |

### The one prediction that failed

**P-C5** asked for byte-identical `<office:body>` between browsers.  It holds
for seven cells and **fails for `c-l1-review`**.

Measured, rather than waved at: the two bodies are the same length (37,479
bytes), carry identical visible text, and become byte-identical after
normalising auto-generated tracked-change ids (`ct311...` in one browser,
`ct2888...` in the other).  Nothing about the content differs.

It is recorded as a **failed prediction** anyway, because it was written as
byte-identity and that is how it is scored.  "We would have accepted this" is a
thing to decide before the round, not after -- the same rule L2 and L5 were
scored under in the list half.  The narrower criterion ("byte-identical after
normalising generated ids") belongs in the second round's matrix, registered
before it runs.

The analyzer reports `bodiesIdenticalAfterIdNormalisation` beside the strict
answer so the next round has the number without anyone re-deriving it.

## Reproducing

```
python3 tools/run_e2_c_d0.py --page e2-c-d3-corpus.html --namespace __e2c_d3c \
    --browser chrome --output <a NEW directory>
python3 tools/analyze_e2_c_d3_corpus.py <chrome dir> <firefox dir> \
    --carried ../d3-lists/run-4-fixed-shell --output summary.json
```

A round is a record: the runner refuses to write into a directory that already
holds one.
