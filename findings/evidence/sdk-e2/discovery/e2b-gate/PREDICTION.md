# Prediction: the E2-B gate, dispatching a format action on a range selection

**Written and committed before the harness exists and before any run.**
Required by `specs/SPEC-E2-B-paragraph-format-contract.md` section 3.7.

In English per `AGENTS.md` (2026-08-15): everything newly written under
`findings/evidence/**` is English.

## What the gate is for

E2-A narrowing 7: every format dispatch E2-A measured started from a **collapsed
caret**. Dispatching while a **range** is selected has never entered the matrix.
That is the gesture a v2 user performs — drag across a paragraph, then press the
button — so it is a product gap, not an academic one.

Task #49 left 24 incidental records of exactly that (`dispatchSelectionCollapsed:
false`, all completed, `failureShape` empty, `dispatchSelectionRectangles` 1).
Incidental observations cannot retire a narrowing under this project's rules, but
they do supply a cost model, and they narrow what is actually dark: one action
(`.uno:DefaultBullet`) and one geometry (single rectangle, single paragraph,
forward).

## Artifact and entry point

Combination artifact `e2-combination` = `940b7723…`, through the **diagnostic**
client (`FormatDiscoveryClient`) — the same path #49's P1/P2 used. The gate
measures engine behaviour, not the product protocol; the product protocol
problems are spec section 5 and block freezing, not this gate.

Range selection is issued through the **product** entry point
(`editorSelectRangeV1`), because that is the call a v2 shell would make.

## Arms

Eight arms, each 1 fixture x 2 browsers x 3 runs = 48 runs. Fresh engine per arm.

### Action dimension — geometry fixed at single-paragraph, forward

Fixture `list-contexts.odt`.

| arm | action | uno command | why it is dark |
|---|---|---|---|
| **A1** `bullet-from-range` | `set-list-unordered` | `.uno:DefaultBullet` | bridge arm: promotes the 24 incidental records to pre-registered bindable evidence |
| **A2** `ordered-from-range` | `set-list-ordered` | `.uno:DefaultNumbering` | never dispatched from a range |
| **A3** `list-none-from-range` | `set-list-none` | `.uno:RemoveBullets` | never dispatched from a range, and semantically different: it leaves a list |
| **A4** `heading-from-range` | `set-paragraph-heading` | `.uno:StyleApply` | never dispatched from a range; different arguments and a different expected tag |
| **A5** `body-from-range` | `set-paragraph-body` | `.uno:StyleApply` | arguments and expected tag are the inverse of A4 |

### Geometry dimension — action fixed at `set-list-unordered`

| arm | geometry | fixture | why it is dark |
|---|---|---|---|
| **G1** `wrapped-line-range` | one paragraph, selection spanning more than one visual line (**> 1 rectangle**) | `list-contexts.odt` | all 24 records are single-rectangle |
| **G2** `reverse-range` | END left of START | `list-contexts.odt` | #49 measured reverse **selection**, never reverse **dispatch** |
| **G3** `cross-paragraph-range` | spanning two paragraphs | `multi-paragraph.odt` | all 24 records are single-paragraph. **Judged differently — see below** |

Anchors rather than coordinates are what the criteria are pinned to. Coordinates
come from a setup pass whose output is recorded next to the results; if the
selection does not read back as the expected anchor text, the run is **void**,
not failed.

## Pass criteria for A1-A5, G1, G2

Before the dispatch, all four must hold or the run is void:

1. the selection reads back as the expected anchor text;
2. `dispatchSelectionCollapsed == false`;
3. `dispatchSelectionRectangles` matches the arm (G1 requires **> 1**);
4. the endpoint direction matches the arm (G2 requires reverse).

After the dispatch, all three must hold to pass:

5. in the **saved ODT**, every paragraph the arm declares should change has
   reached the target state;
6. the adjacent unselected paragraphs are **byte-identical** to the fixture;
7. the final selection is collapsed (`restoreConfirmed`).

Criterion 6 is the one that makes this a real check. Without it, "this paragraph
became a heading" does not establish "only this paragraph became a heading" —
and every one of these actions is paragraph-level, so a range that silently
collapsed to a caret would still satisfy criteria 1 and 5.

## Predictions

| arm | prediction |
|---|---|
| A1 | **passes.** The 24 incidental records are exactly this case; the cost model says completed, callback, ~30 ms, selection collapsed afterwards |
| A2 | **passes.** `DefaultNumbering` is `DefaultBullet`'s sibling and takes the same `On` argument |
| A3 | **passes**, with lower confidence than A1/A2: `RemoveBullets` is dispatched bare and leaves a list rather than entering one |
| A4 | **passes.** `StyleApply` with the heading arguments |
| A5 | **passes.** Same path as A4, inverse arguments |
| G1 | **passes.** More rectangles is a rendering fact; nothing in the barrier reads the rectangle count for its verdict |
| G2 | **passes.** Reverse ranges produced identical text natively (#49 arms AJ/AK) |
| **G3** | **fails**, and this is the arm worth running — see below |

## G3 is judged differently, and it is predicted to fail

`multiBlock` is computed from the **barrier's own** postcondition selection
(`probe_engine.cpp:601`), and the barrier selects with `.uno:SelectText`
(`FN_SELECT_PARA`), which selects **exactly one paragraph**. The judgement also
happens **after** the dispatch (`:3320`), not before it. So a cross-paragraph
input cannot structurally reach that refusal.

Predicted sequence: the uno command applies to **both** paragraphs (that is what
Writer does with a multi-paragraph selection); the barrier then collapses to the
restore point, selects **one** paragraph, verifies that one, and reports success.

| reading | verdict |
|---|---|
| named failure, and the ODT shows **zero** mutation | pass — a pre-dispatch refusal, the cleanest outcome |
| named failure, and the ODT shows mutation | pass, but recorded: this is the "dispatched, cannot verify" class, host must prompt undo |
| **success reported, and the ODT shows both paragraphs changed** | **fail — silent under-verification. This is the predicted outcome.** |
| success reported, and the ODT shows one paragraph changed | fail: the command did not apply to the whole range, which contradicts what the user asked for |

## Dispositions, pre-registered

- **All eight pass** → range dispatch enters the ABI, and "selection collapses
  after dispatch" is promoted to a contract term (spec 3.8).
- **Only G3 fails** → range dispatch enters the ABI, but a cross-paragraph range
  must be refused **before dispatch** with zero mutation and its own shape name;
  that refusal needs its own round.
- **Any action arm fails** → that action does not accept range dispatch, the
  others may; expressed as a capability field, not UI text.
- **G1 or G2 fails** → range dispatch does not enter the ABI at all; v2 promises
  collapsed-caret dispatch only.
- **collapse-first is not available as a fallback here.** It changes the user's
  selection and the target of the action, so it requires its own prediction and
  its own round (spec 3.7).

## What this gate does not claim

- **It does not bind the product build.** It runs on the combination artifact.
  Spec 3.9 requires all eight arms to be re-run on the product profile after the
  relink, and A3/A4/A5 re-swept, before the ABI can be frozen.
- **It does not test the v2 protocol.** The worker's `endsWith("V1")` gate, the
  action map, and the product client's `changed === true` requirement are spec
  section 5 and are all still unresolved.
- **It does not measure the drag gesture.** The range arrives through
  `editorSelectRangeV1` with coordinates, not through real pointer events. What a
  physical drag does at the event layer is not covered.
