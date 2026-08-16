# 046 — what the barrier actually read, off the frozen engine

Criteria in `PREDICTION.md`, registered before the profile was built.  Judged by
`tools/analyze_f046_diagnostic.py`; self-test 9/9.

**Evidence class: diagnostic.**  This round did not pass the matrix entry
assertion and is not matrix evidence; the runner was given
`--diagnostic-round <reason>` and the reason is stamped into every
`result.json`.

## The engine is the shipping one

```
dist/profiles/e2-readback-diagnostic/probe.wasm  ==  dist/profiles/e2-editor-v2/probe.wasm
```

Byte-identical (`cmp`), loader identical, `572035ac…`.  The profile is a Python
repackage: `build_e2_discovery_profile.py` **copies** the wasm and patches only
the worker, with five declared edits.  The two that matter swap the named
projection for the raw event, so the page sees the record the engine already
writes.  `workerPatch.sourceSha256` records the frozen worker it was patched
from.

**P-046D-5, the method's own control, holds**: every arm reaches the same
outcome on both profiles, in both browsers.  Swapping the projection changed
what could be seen, not what happened.

## What the barrier read

| arm | parsed | blockCount | itemCount | bytes | containment | outcome |
|---|---|---|---|---|---|---|
| `A3-text-click` (control) | true | **1** | 1 | 520 | checked, **held** | **succeeds** |
| `A1-empty-click` | true | **2** | 1 | 576 | checked, **held** | `multi-block-readback` |
| `A2-empty-selectrange` | true | **2** | 1 | 576 | checked, **held** | `multi-block-readback` |
| `A4-last-empty-click` | **false** | 0 | 0 | 0 | **not checked** | `stage-deadline:awaiting-selection` |
| `A5-text-range` | true | 1 | 1 | 520 | checked, held | succeeds |

Identical in Chrome and Firefox.

### The markup, which is the whole answer

```html
A3 (a paragraph with text)
<ul><li><p>E1-EMPTY-BEFORE</p></li></ul>

A1 (the empty paragraph)
<ul><li><p></p></li></ul><p>E1-EMPTY-AFTER</p>
```

**The bullet applied.**  The empty paragraph is there as a list item with an
empty `<p>` in it.  And the read **also swallowed the paragraph below it** — so
the barrier saw two blocks and refused a mutation that had in fact succeeded.

## Both relink blockers are answered, and neither the way I expected

**3b (`empty-readback`) — withdrawn.**  P-046D-2 predicted `parsed:true,
blockCount:0, itemCount>=2`; the measurement is `parsed:true, blockCount:2,
itemCount:1`.  **No arm produced a parsed readback with zero blocks.**  The
shape 3b would name has nothing to name here, and the "zero blocks" that
motivated it was `postBlocks: 0` — the field that is never written on the
collapsed route (`findings/evidence/046/browser-vs-native/`).  `multiBlock` is
not a misreport: the read really did cover two paragraphs.

**The containment reorder — not in this link.**  P-046D-3 predicted `checked:
true, held: false`; the measurement is **`held: true`** (selection 1807–2471,
restore centre 1945 — inside it).  Reordering containment ahead of `multiBlock`
would change **no** disputed cell.  This retreat condition was named by the
adjudication before the data existed.

## The actual defect, now precise

**On an empty paragraph, `.uno:SelectText` selects past the paragraph and into
the next one.**  The action succeeds; the verification read covers one paragraph
too many; the barrier reports `MUTATION_OUTCOME_UNKNOWN`.

And containment cannot catch it, by construction: it asks *does the selection
cover the caret*, not *does it cover only the caret's paragraph*.  It is a
**one-sided check** — it catches a selection that missed, never one that
overshot.  The overshoot is caught incidentally by `multiBlock`, which is why
`multiBlock` fires first and why the reorder would not help.

## A correction to the native round

`findings/evidence/046/native/README.md` calls
`.uno:GoToStartOfPara` + `.uno:EndOfParaSel` "the barrier's own selection pair".
**It is not the engine's gesture.**  The barrier posts a single
`.uno:SelectText` (`probe_engine.cpp:804`, `postFormatBarrierParagraphSelection`),
and the comment above it records that the pair was replaced *because* it escaped
to a neighbouring paragraph whenever the caret sat at a paragraph edge
(finding 034).

So the native round re-measured a superseded gesture, and measured exactly the
defect that superseded it.  Its numbers are real; what they describe is the old
pair, not the shipped barrier.  A dated addendum has been added there.

## Reproducing

```
V2=dist/profiles/e2-editor-v2
python3 tools/build_e2_discovery_profile.py \
  --source-manifest $V2/sdk-manifest.json --loader $V2/probe.js \
  --wasm $V2/probe.wasm --worker $V2/sdk-worker.js \
  --output dist/profiles/e2-readback-diagnostic \
  --profile-name e2-readback-diagnostic --scope e2-paragraph-format-discovery

python3 tools/run_e2_c_d0.py --browser chrome --profile e2-readback-diagnostic \
  --page e2-c-046-empty.html --namespace __f046_browser \
  --diagnostic-round "<why>" --output <new dir>

python3 tools/analyze_f046_diagnostic.py --diagnostic <dirs> --product <dirs>
```
