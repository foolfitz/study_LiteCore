# Prediction: closing G1, the one dark cell the first gate run left

**Written and committed before any run of the new fixture.** This is the second
prediction under `specs/SPEC-E2-B-paragraph-format-contract.md` section 3; the
first is [`PREDICTION.md`](PREDICTION.md) and everything it says still stands.

One difference from the first prediction, stated rather than glossed: that one
was committed **before the harness existed**. This one was written **after** the
fixture and the harness change, and before **any** run of either. So it is not
protected against "the harness shape suggested the prediction"; it is protected
against the thing that actually goes wrong here, which is a prediction fitted to
a number already seen. No run of the new fixture had happened when this was
committed.

In English per `AGENTS.md` (2026-08-15).

## Why there is a second prediction

The 2026-08-15 gate run recorded arm **G1** (`wrapped-line-range`) as **void**,
not passed. It aimed at `第三段跨行 gamma` in `multi-paragraph.odt`, and that
paragraph turned out to be **tall, not wrapped**: a selection across its full
vertical extent reported one rectangle and read back the whole paragraph text.
The arm therefore did not exercise the case it exists for. Same-paragraph
multi-rectangle selection is still unmeasured, and until it is, "range dispatch
is characterised" is not a sentence this project may write.

No fixture in the E1 corpus has a paragraph long enough to wrap at the page
width, and that corpus is frozen (`dist/e1-fixtures/manifest.json`:
`frozenDate 2026-08-04`, `mutationPolicy copy-only`). So the fixture is new and
lives in its own directory.

## The fixture

`dist/e2b-fixtures/wrapped-paragraph.odt`, from
`wasm_sdk_probe/tools/create_e2b_fixtures.py`, four paragraphs:

1. `E2B-WRAP-HEAD single line`
2. 120 tokens `G1WRAP-001 … G1WRAP-120`, 1319 characters — cannot fit on one
   line at any plausible font metric
3. `E2B-WRAP-TAIL single line`
4. `E2B-WRAP-LAST single line`

The wrapped paragraph is a repeated token rather than prose for a mechanical
reason: the gate's survey selects a horizontal band at one `y` and reads the
text back, so it recognises a paragraph on a given visual line only if the
anchor is **on that line**. `G1WRAP` is on every line; prose would put the
anchor on the first line only and `findSpan` would find nothing to span.

## Fixture validation is separated from measurement

Whether that paragraph actually wraps **at this build's page width** is a
property of the fixture, and finding out costs a span select — which is also
the first half of arm G1. If the gate answered it, the same run would both tune
the fixture and produce the verdict.

So there is a `?geometryOnly=1` mode: it selects the two spans, records the
rectangles, and **dispatches nothing and saves nothing**. Its output is a
fixture property. If it shows one rectangle, the fixture is wrong and gets
rebuilt; that is fixture construction and it is disclosed as such. The verdict
run happens afterwards and is judged on its own records.

## The control, and what it is for

Arm **G1c** (`single-line-control`) is new: the same span mechanism, the same
document, the same action, aimed at `E2B-WRAP-HEAD` — a paragraph that does
**not** wrap.

The reading this guards against is "this build reports more than one rectangle
for everything", under which G1's count would say nothing at all. If G1c reports
anything other than exactly one rectangle, **G1 is uninterpretable** and is
recorded void regardless of what else it did.

The control does **not** establish that the rectangle count tracks visual lines.
That claim is supported separately, by recording the rectangle geometry itself
(`rectangleGeometryBeforeDispatch`): stacked boxes at distinct `y`, all within
one paragraph's vertical extent, with the selection text reading back as the
whole paragraph.

## Predictions

**Both of these are falsifiable by the run, and I expect the first.**

**P1 — G1 passes, and behaves exactly like the single-rectangle case.** The
range covers one paragraph across several visual lines. `.uno:DefaultBullet`
applies to that paragraph, the barrier's `.uno:SelectText` reads back that same
paragraph, and the engine reports success. The saved ODT shows paragraph 2 in a
bullet list and paragraphs 1, 3, 4 unchanged. Selection collapses afterwards.
Rectangle count before dispatch is **greater than one**; expected 8–20 given
1319 characters at the default page width, but the criterion is only `> 1`.

*Basis*: the mechanism that broke G3 is paragraph **count**, not rectangle
count. `FN_SELECT_PARA` selects one paragraph, and here the mutation is one
paragraph, so the barrier verifies all of what changed. Nothing in
`probe_engine.cpp`'s containment check is per-rectangle: it is vertical
containment of the restore point (`:3126`), and a wrapped selection contains it.

**P2 — G1c passes with exactly one rectangle.**

*Basis*: it is geometrically the same as A1, which passed 3/3 in both browsers.

### What would falsify P1, and what each failure would mean

| reading | means |
|---|---|
| G1 reports **1** rectangle | the fixture still does not wrap — **void**, rebuild the fixture, do not read anything else from the arm |
| G1c reports **more than 1** | the rectangle count is not reading visual lines — **G1 void too** |
| G1 changes **more than one** paragraph | a multi-line range reaches beyond its paragraph; this would be a **new** defect, not G3's |
| G1 selection does not collapse afterwards | section 3.8's collapse semantics cannot be promised for wrapped ranges |
| G1 reports a typed failure with zero mutation | range dispatch is refused for wrapped ranges; under section 3.7 that is **"G1 fails" → range dispatch does not enter the ABI at all** |

That last row is the one with teeth: by the decision rule already committed in
section 3.7, a G1 failure is not a narrowing, it removes range dispatch from v2
entirely. Writing that down before the run is the point.

## Scope

Two browsers, three rounds, on `e2-combination` = `940b7723…` — the same
artifact the first run used, so the two runs compose. The other arms re-run
unchanged; their results are expected to reproduce and any that do not is
itself a finding.

This does **not** bind a product build (section 3.9), does not test the v2
protocol (section 5), and does not measure a physical drag.
