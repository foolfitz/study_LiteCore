# Paragraph merge, native round R0b — the anchor rectangle against the placed caret (written 2026-10-06, before R0b ran)

R0b measures the premise of the fence adopted in `specs/SPEC-M3-paragraph-merge.md` §13.1: with nothing queued, the anchor-side rectangle Writer sends in the one-unit selection's own flush (`TEXT_SELECTION_START` for Shift+Right, `TEXT_SELECTION_END` for Shift+Left) equals, on (x, y, height), the caret the engine last received before that selection (P). §13.1 says: all equal → implement the rule as written; any difference → the design returns to the spec before any engine code.

## Instruments

- Probe `tools/merge_native_boundaries.cpp` as of `dcbed256`: the select and b arms clear the stored `TEXT_SELECTION_START` / `_END` right before the Shift press and record what the unit's flush sent (`unit.selectionStart`, `unit.selectionEnd`). Nothing else changed; R0's arms, placement and restore are the same.
- Reader `tools/check_merge_anchor_rect.py`: for every select and b arm whose unit holds 10, 13, U+2028 or U+2029, compares the anchor-side rectangle with the origin caret (`placed.cursor`, or `typedAt.cursor` for a pretyped case) on x, y and height; exit 1 unless all agree. **Changed in this commit (before any run):** it also reports, without touching the exit status, the candidate mapping registered below (`mapping`, `mappingHolds` / `mappingFails`, `MAPPING-FAILS` lines).
- Reader red cases, run on synthetic rounds in scratch (shapes, expected → got): strict agree → exit 0; height one less → strict differ, mapping holds; taller line with the caret lower and shorter, bottoms equal → strict differ (y, height), mapping holds; x one off → mapping fails; anchor on another line → mapping fails; backward arm whose `selectionEnd` matches and `selectionStart` is garbage → mapping holds (reads End); backward arm whose `selectionStart` matches and `selectionEnd` is garbage → mapping fails (does not read Start); anchor missing → `absent`, exit 1; no separator unit → "no arm ... compared", exit 1. 9/9. On R0's committed evidence (no new fields) → exit 1, "no selectionStart field".

## Inputs and runs

Same inputs as R0 (`PREDICTION-R0.md`, Inputs); one round each, `MERGE_RESTORE_PRESSES=2`, no follow text. From `wasm_sdk_probe/`, one at a time:

1. `MERGE_RESTORE_PRESSES=2 tools/run_merge_native.sh ../findings/evidence/merge-native/r0b 1 test-docs/merge/odt/boundaries.odt test-docs/merge/r0-boundaries.cases.tsv 1`
2. the same with `test-docs/merge/odt/boundaries-indent.odt` and `test-docs/merge/r0-indent.cases.tsv`
3. the same with the owner's document (`build/scratch-m3-production-ui/`) and `test-docs/merge/r0-pmpc.cases.tsv`, output under `build/merge-native-pmpc/r0b` (only `arms.jsonl` and summaries are copied into `r0b/`)

Then `tools/check_merge_anchor_rect.py --json ../findings/evidence/merge-native/r0b/anchor-rect.json <the three round dirs>`.

## Predictions, from source

How the two payloads are made (26.8 tree):

- **Caret (P).** `SwCursorShell::UpdateCursor` computes `m_aCharRect` with `SwTextFrame::GetCharRect(..., &aTmpState)`, `m_bRealHeight = true` (`crsrsh.cxx:2376–2392`). With no mark the cursor height is the real height (`crsrsh.cxx:2402–2403`): `m_aRealHeight = (line ascent − portion ascent, min(portion height, line height))` (`itrcrsr.cxx:1330–1339`). `SwVisibleCursor::SetPos` puts the rectangle at the char rect's position, moved down by the first value, with the second as its height, width 0 (`viscrs.cxx:144–217`). The payload is built as `tools::Rectangle(x, y, x + w, y + h)` and printed with `getOpenWidth/Height` (`viscrs.cxx:286–289`, `gen.cxx:171–180`): **`x, y + offset, 0, h_caret`**.
- **Anchor.** `SwSelPaintRects::getLOKPayload` → `FillStartEnd` → `lcl_getLayoutRect` → `GetCharRect` with no move state (`viscrs.cxx:408–425`, `:533–566`): the char rect is `(1, line height)` at the line top (`itrcrsr.cxx:618–623`). The payload is `SwRect::SVRect().toString()`, and `SVRect` takes one off each dimension (`swrect.hxx:193–198`): **`x, line top, 0, line height − 1`**.
- x is computed by the same function at the same position on both sides; the move state's flags change height and y, not x. The one flag that changes x, `m_pSpecialPos` (caret in front of a numbering label, `crsrsh.cxx:2383–2388`), is not expected after the probe's `GoTo…` placement. Leading zero-length portions (the numbering label) are skipped on both sides (`itrcrsr.cxx:664`).
- `TEXT_SELECTION_START` / `_END` are not in the flush handler's last-state dedup list (`init.cxx:1592–1606`; only queue duplicates within one flush are dropped, `:1884–1922`), so a unit with area always sends them. The anchor rect has width 1 and a line height, so `HasArea` holds.

Corroboration (not a measurement of the anchor): R0's selection highlight rectangles show, on every line R0 placed a caret, the line height against the caret height. In `boundaries.odt` and `boundaries-indent.odt` every highlight piece on the caret's line has the caret's y and height − 1. In the owner's document so do eight cases, but on P27, P62 and P63 the highlight starts 52 twips above the caret and is 400 high where the caret is 348 (the line holds a taller portion than the caret's).

| What | Prediction |
|---|---|
| Rows compared | 68: boundaries 38 (C01 C02 C03 C08 C09 C15 C16 C17 C27 I02 C10 C11 C12 C13 I03 I01 C14 Y01 Y02, select and b), indent 8 (D01 D04 D08 D12), owner's 22 (E01 E02 E05 E10 E12 T01 P27 E13 E15 P62 P63) |
| `absent` | 0 |
| x | equal on all 68 |
| height | **differs on all 68**: anchor = caret − 1 on 62; on P27, P62, P63 (6 rows) anchor 399, caret 348 |
| y | equal on 62; **differs on the 6 rows** of P27, P62, P63: anchor = caret − 52 |
| Anchor width | 0 everywhere (not compared) |
| Reader | exit 1; `{"agree": 0, "differ": 68, "absent": 0, "xDiffers": 0, "yDiffers": 6, "heightDiffers": 68}` |
| Candidate mapping (registered now, adopted only by a spec append after the run) | holds on 68/68: equal x, and anchor y ≤ caret y and caret y + caret height ≤ anchor y + anchor height + 1 (on P27/P62/P63 the bottoms coincide: 348 + 52 = 399 + 1) |

## What would change the decision

- **As predicted:** §13.1's rule cannot be built as written — it would refuse every merge. The spec gets an append before any engine code, citing this round: the fence compares x exactly and requires the caret's vertical span inside the anchor's line rectangle (the mapping above). The append must also say what the relaxed vertical test gives up: two different model positions with the same x on the same line (a zero-width portion between them) pass the fence. That is registered, not fixed.
- **x differs anywhere:** the fence cannot rest on x; the design goes back to §13.1 with that row (for example a caret in front of a label), and no mapping is adopted from this round.
- **Mapping fails on a row where x agrees:** the vertical relation is not "caret inside the line"; the row is read before anything is proposed.
- **`absent` on any row:** the unit's flush can omit the anchor with nothing queued; the fence would refuse there. Read the case before anything else.
- **All 68 agree strictly:** this prediction's reading of `SVRect` / `getLOKPayload` is wrong somewhere; §13.1 is implemented as written, and the reading error is written up before relying on any other source reading in this file.

What R0b does not measure: the other half of the fence (a stale P is caught). It only shows, with nothing queued and the probe's `GoTo…`/arrow placement, whether the fence would refuse a correct merge. Placement by click (the product's path) is not covered here; M2 on WASM is where that runs.
