# Result — findings 064 and 065 are both retracted, and neither was a product or engine defect

Prediction: [`PREDICTION-render-between-format-and-typing.md`](PREDICTION-render-between-format-and-typing.md).
Probe: `wasm_sdk_probe/tools/probe_064_format_reaches_typing.py`.
Artifact `29ec627b`, shell v25. One file mirrored (the render hook),
`probe.wasm` byte-identical, `dist/` never written, every diagnostic report
stamped `evidenceClass: "diagnostic"`.

**This page was rewritten on 2026-08-22.** Its 2026-08-21 version reached the
right headline for the wrong reason and invented a second defect on the way.
Both versions are wrong about the mechanism; the section "What went wrong twice"
is the part worth keeping.

## The answer

**Inline formats work.** They reach the text you type, they survive a paragraph
break, and they are exported correctly. All four formats, both directions, on
both browsers, read from the saved ODT.

**Finding 064 and finding 065 were the same bug, and it was in the oracle.**
`inline_styles_of()` stopped at:

```python
# Found, and deliberately NOT inheriting the paragraph's style: this asks
# about INLINE formatting, and text that is not in a span has none of it.
```

That premise is false for ODF. When a paragraph is **uniformly** formatted,
LibreOffice writes the character properties onto the paragraph's own automatic
style and emits **no span at all**:

```xml
<style:style style:name="P3" style:family="paragraph" style:parent-style-name="Standard">
  <style:text-properties fo:font-weight="bold" .../></style:style>
<text:p text:style-name="P3">RETLADDERONE</text:p>
```

Every arm of these checks presses `insert-paragraph-break` and then types its
marker, so **every marker ends up alone in its paragraph** — which is exactly
the uniform case. Every one of them read as unformatted.

## Who caught it

**An operator, on 2026-08-22**, running
`handoff/RUNBOOK-operator-2026-08-21-finding-065.md`. They reported "A: it is
bold" from the canvas; the ODT they had just saved read `bold: false`.

Nothing automated in this tree could have caught this. Every check that could
have — `every-inline-format-reaches-the-document`,
`clear-format-removes-every-inline-format`,
`formatting-survives-the-next-paragraph-break`, and the diagnostic probe's whole
ladder — is downstream of the same function. **An oracle's error is invisible to
the checks that depend on it.**

## Before and after the fix, same arms, same artifact

`retention-ladder-adjacent` — one action at a time, saving after each:

| step | before the fix | after the fix |
|---|---|---|
| break + `set-bold` ON + type the marker | bold **true**, span T1 | bold true, span T1 |
| `move-character-left` | bold true | bold true |
| `move-character-right` | bold true | bold true |
| **`insert-paragraph-break`, alone** | **bold FALSE, 0 spans** | **bold TRUE, `carrier: paragraph`, `styleName: P3`, 0 spans** |

The span count still goes 1 → 0, and that is **correct export**: the paragraph
became uniformly bold, so the bold moved from a span onto the paragraph's style.
Nothing was lost. Finding 065's whole story — "the span leaves the text behind
and follows the caret" — was this, misread.

`runner-sequence-saved` — the runner's eight-arm inline block, and this is the
one that settles 064. Re-read with the fixed oracle, **the original reading
(one save at the end, eight verdicts) is correct on all four formats, both
directions**:

```
bold          on P3 true   / off P4 false   ok
italic        on P5 true   / off P6 false   ok
underline     on P7 true   / off P8 false   ok
strikethrough on P9 true   / off T1 false   ok
```

Each marker keeps its own format for the whole run, moving from `carrier: span`
to `carrier: paragraph` as the next arm's break makes its paragraph uniform. So
**064 was not a timing bug either.** The 2026-08-21 story — "each arm's opening
paragraph break destroys the previous arm's evidence" — is withdrawn. Nothing
destroyed anything.

## What the diagnostic ladder is still good for

The five reports in `product/` were produced with the broken oracle. Their
**mechanism readings are void**. What remains valid is the record of what each
arm *did* — which actions ran, in what order, what the revisions were, and the
raw ODF fragments, which can be re-read against the corrected rules. The raw
fragments are in fact what made the fix checkable.

One arm keeps its full value independently: the probe's **instrument control**
passed on every run (render on → canvas ink moves; suppressed → frozen;
released → moves again), so the render-suppression apparatus did work. The
named candidate — the repaint between the format press and the typing — is
genuinely dead, and it was dead before any of this: the very first `baseline`
arm put italic on the marker with the repaint running.

## What went wrong twice, and it is the same shape

**Both retractions came from asking the document a question it does not answer
that way, then reading a mechanism out of the answer.**

* Round 1 read "no span on seven of eight markers" and produced *the product
  path is broken* — a story with a named culprit, a matching D1 comparison, and
  a plausible physical mechanism.
* Round 2 read "1 span → 0 spans across one break" and produced *the span
  follows the caret* — again with a clean A/B, again with raw XML.

Both were internally consistent, both survived adversarial review of their
*reasoning*, and both were zero. The reviewer that killed them was a person
looking at a screen.

Specific lessons, in the order they cost something:

1. **A deliberate wrong decision is harder to find than a careless one.** The
   comment explaining why the paragraph style was skipped is what made it look
   already-considered. It had been considered — and it was wrong.
2. **An oracle cannot be validated by the checks that use it.** The unit tests
   (`tests/test_inline_styles_of.py`) covered nine cases and every one of them
   put the marker in a span, so the whole paragraph-carrier branch was
   untested. Four cases were added; three of them fail against the pre-fix
   function.
3. **`spans: 1 → 0` was treated as loss and it was re-expression.** A count is
   not a measurement of the thing you care about unless you have checked what
   else can move it.
4. **The negative-control discipline worked and was still not enough.** The
   probe refused to read its arms when the baseline came back green, which is
   what produced the (correct) headline that formats do reach typed text. It
   cannot catch an oracle that is wrong in the *same direction* for every arm.
5. **The human round was scheduled as a confirmation and functioned as a
   refutation.** It was nearly deprioritised as "nice to have".

## Consequences

* `inline_styles_of()` resolves the paragraph's style when there is no span, and
  reports `fromParagraphStyle` so a caller can still tell the two apart. A span
  still wins over its paragraph.
* `KNOWN_RED` is **empty** — third time in this file's life. Both entries came
  off through the mechanism that exists for it: a declared-red check that passes
  fails the round as a stale declaration, and the runner said so both times.
* `clear-format-removes-every-inline-format` passes, after days of
  `NOT_ESTABLISHED`. Part of that was a genuinely mistimed read (its precondition
  was taken from the *cleared* document); part was this.
* `formatting-survives-the-next-paragraph-break` stays as a **passing** check.
  The question it asks — press B, type, press Enter, is it still bold — had
  never been asked before this round, and it is worth keeping now that it is
  answerable.
* **Nothing here needs an engine change.** The link's payload is unaffected by
  any of it.
