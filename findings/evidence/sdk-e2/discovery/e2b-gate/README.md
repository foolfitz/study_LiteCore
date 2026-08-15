# SPEC E2-B section 3 gate: dispatching a format action on a range selection

**Date** 2026-08-15
**Artifact** `e2-combination` = `940b7723…` (combination build; never shipped)
**Entry point** range selection through the product `editorSelectRangeV1`;
format actions through the diagnostic `FormatDiscoveryClient`
**Prediction** [`PREDICTION.md`](PREDICTION.md), committed **before the harness
existed** (`fc38a50`)
**Runner** `tools/run_e2b_gate.py` (drives, does not judge)
**Judge** `tools/analyze_e2b_gate.py` (reads only the saved files, so the verdict
can be recomputed without a browser)

## Verdict: the "only G3 fails" disposition, with one cell still dark

Chrome and Firefox are **cell-for-cell identical**, three rounds each.

| arm | what it dispatches | Chrome | Firefox |
|---|---|---|---|
| **A1** `bullet-from-range` | `set-list-unordered` | **pass 3/3** | **pass 3/3** |
| **A2** `ordered-from-range` | `set-list-ordered` | **pass 3/3** | **pass 3/3** |
| **A3** `list-none-from-range` | `set-list-none` | **pass 3/3** | **pass 3/3** |
| **A4** `heading-from-range` | `set-paragraph-heading` | **pass 3/3** | **pass 3/3** |
| **A5** `body-from-range` | `set-paragraph-body` | **pass 3/3** | **pass 3/3** |
| **G2** `reverse-range` | END left of START | **pass 3/3** | **pass 3/3** |
| **G1** `wrapped-line-range` | — | **void 3/3** | **void 3/3** |
| **G3** `cross-paragraph-range` | spans two paragraphs | **fail 3/3** | **fail 3/3** |

A pass means all seven criteria held: the selection read back as the whole
target paragraph, `dispatchSelectionCollapsed` was `false`, the geometry matched,
the saved ODT shows the selected paragraph in the target state, **every other
paragraph unchanged**, and the selection collapsed afterwards.

## G3 failed as predicted, but not in the way the failure sounds

The prediction said: the command applies to both paragraphs, the barrier then
collapses to the restore point, selects **one** paragraph with `.uno:SelectText`
(`FN_SELECT_PARA` selects exactly one), verifies that one, and reports success.

That is what happened, and the document outcome is **correct**:

| paragraph | baseline | after |
|---|---|---|
| `E1-MULTI-START alpha` | `p`, `Standard`, not in a list | `p`, auto style, **bullet** |
| `第二段中文 beta` | `p`, `Standard`, not in a list | `p`, auto style, **bullet** |
| `第三段跨行 gamma` | unchanged | unchanged |
| `第四段落 delta` | unchanged | unchanged |
| `E1-MULTI-END omega` | unchanged | unchanged |

Both selected paragraphs changed, nothing else did. **A user would call that
right.** The failure is not the document; it is that the engine **reported
success for a mutation it can only have verified half of**. The verdict records
this explicitly as `documentOutcomeCorrect: true` next to the failure, because it
changes which fix is appropriate: refusing a correct operation has a real cost,
and "verify every affected paragraph" is the other option SPEC E2-B section 3.5
already names.

## G1 is void, not passed: the cell is still dark

`multi-paragraph.odt` carries a paragraph named `第三段跨行 gamma` — "跨行" means
"spans lines" — and the survey shows it occupying four sweep steps where its
neighbours occupy two. But a selection spanning its full vertical extent still
reports **one rectangle** and reads back the whole paragraph text: it is a **tall**
paragraph, not a **wrapped** one.

So the arm did not exercise the case, and it is recorded as **void** rather than
passed. **Same-paragraph multi-rectangle selection remains unmeasured.**
Closing it needs a fixture with a paragraph long enough to wrap at the page
width; none of the current e1 fixtures has one.

## Three comparison bugs, all mine, all caught by the data

None of these were caught by review. Each was caught because the numbers were
absurd, which is the argument for judging on documents rather than on whether a
call returned.

**One — the baseline was the authored fixture.** The engine's ODT export
normalises what the fixture leaves implicit: a paragraph with no
`text:style-name` comes back as `Standard`. Comparing a saved document against
the authored file reported **every** paragraph as changed, on every arm. The
baseline has to be a save through the same engine with no action, which is why
there are now `BASELINE-*` arms. This is the same class of error as task #50's
first comparison, in the opposite direction.

**Two — automatic style names were in the signature.** `P1`, `P2`, `L1` … are
generated per document and **renumber** when the document changes: adding one
list paragraph pushed every later automatic name along by one, so A1 reported
five changed paragraphs for a one-paragraph action. The analyzer's own docstring
warned about exactly this and the first version did it anyway. Automatic names
are now folded to `(auto)`, and bullet-versus-number is read from the list style
in `office:automatic-styles`, which is where that distinction actually lives.

**Three — the analyzer quietly replaced a pre-registered criterion.** The first
version gave G3 `allowed = 2` and called two changed paragraphs a pass. But
`PREDICTION.md`, committed before the harness existed, says success reported
alongside a two-paragraph mutation **is** the failure. **The checker written
after the prediction drifted from it, and the drift made the arm pass.** The
criterion has been restored to what was committed; the document outcome is
recorded separately rather than being allowed to override it.

## What this gate does not establish

- **It does not bind a product build.** It ran on the combination artifact
  through the diagnostic client. SPEC E2-B section 3.9 requires all arms re-run
  on the product profile after the relink, and A3/A4/A5 re-swept, before the ABI
  can be frozen — and section 5 item 5 notes the product worker does not forward
  `formatBarrier`, so judging G3 there needs that resolved first.
- **It does not test the v2 protocol.** Section 5 is untouched by this run.
- **It does not measure a physical drag.** The range arrives as coordinates
  through `editorSelectRangeV1`, not as pointer events.
- **It does not cover same-paragraph multi-rectangle selection** (G1, void).
