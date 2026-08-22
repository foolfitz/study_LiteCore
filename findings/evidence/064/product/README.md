# Diagnostic reports, finding 064's mechanism round (2026-08-21)

All five are `evidenceClass: "diagnostic"`. They were produced by
`wasm_sdk_probe/tools/probe_064_format_reaches_typing.py` on artifact
`29ec627b`, shell v25, Chrome, from a symlink mirror of `dist/` in which exactly
one file differs from the shipped tree (`e2-editor-app.js`, a counter and an
early return at the top of `renderDocument()`, inert unless the probe installs
`globalThis.__f064`). `probe.wasm` is byte-identical to the shipped profile and
`dist/` was never written.

**None of these is a product measurement** and none may be read as one. The
reading is in [`../RESULT-render-between-format-and-typing.md`](../RESULT-render-between-format-and-typing.md).

> ## Produced with a broken oracle (flagged 2026-08-22)
>
> All five ran before `inline_styles_of()` was fixed. That function stopped at
> "the marker is not inside a `<text:span>`, therefore it carries no
> formatting", and ODF puts the character properties of a **uniformly
> formatted** paragraph onto the paragraph's own automatic style with no span at
> all — which is exactly what "the marker alone in its paragraph" produces.
>
> **Every `bold` / `italic` / `underline` / `strikethrough` reading in these
> files is a false negative wherever `carrier` is `"paragraph"`.** Findings 064
> and 065 were both built on those readings and both are retracted.
>
> What is still good here: the record of **what each arm did** — the actions, the
> order, the revisions, the instrument counters, and the raw ODF fragments.
> The fragments are what made the fix checkable. Re-read them against the
> corrected rules, not against the `bold:` fields.

| file | what it answers |
|---|---|
| `01-render-candidate-and-baseline.json` | the named candidate — the repaint between the format press and the typing. Control PASS, and the **baseline did not reproduce the defect**, which is why the verdict refused to read the other two arms |
| `02-runner-sequence-replay.json` | the product-path runner's inline block, verbatim, on one fresh page load. All eight arms fail, `set-bold` first among them, and seven of eight markers carry no `<text:span>` at all |
| `03-every-marker-at-every-save.json` | the same sequence with a save after every arm, reading **every** marker each time. Exactly one span exists at any moment and it is always the marker just typed |
| `04-raw-odf-per-save.json` | the `content.xml` itself: span counts, automatic text styles, and the paragraph fragment carrying each marker |
| `05-retention-ladder-ab.json` | the A/B, **as it read before the fix**: `insert-paragraph-break` alone appears to take the bold off (1 span → 0). It does not; the span count moved because the paragraph became uniform |
| `06-retention-ladder-with-the-oracle-fixed.json` | **the same arm, after the fix.** `bold: true`, `carrier: "paragraph"`, `styleName: "P3"`, `spans: 0`. Finding 065 dies here |
| `07-runner-sequence-with-the-oracle-fixed.json` | **the eight-arm block, after the fix.** The original one-save-at-the-end reading is correct on all four formats in both directions (`P3`…`P9`), and every marker keeps its format for the whole run. Finding 064 dies here, and so does the 2026-08-21 story about arms destroying each other |

In every report `control.outcome` must be `PASS` before anything else in it is
readable: it is the proof that the probe's suppression flag both stops a repaint
and releases it again. A run whose instrument was not shown to bite measures
nothing, and the arms are written to say so rather than to report a verdict.
