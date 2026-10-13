# B + D at a table (handoff 10-13b Open 4: table refusals unmeasured in a browser)

Measurement only, not an acceptance arm. No product byte is touched. Host 0.2.16 (`f5b34f0`), page `6470dec0…`.

**Document:** `wasm_sdk_probe/dist/e1-fixtures/table-boundary.odt`, uploaded under the probe's usual name. Its paragraphs, as `paragraph_texts_from_xml` reads them:

| index | paragraph |
|---|---|
| 0 | `E1-TABLE-BEFORE` |
| 1–4 | the 2×2 table's cells: `E1-CELL-A1`, `-B1`, `-A2`, `-B2` |
| 5 | `E1-TABLE-AFTER` |

## Arms (`probe_table_refusal.py`)

The page opens with the caret at the document start.

| arm | keys | then | answer |
|---|---|---|---|
| `before-table-press-type` | End (end of paragraph 0, just before the table), one Delete | wait for the new generation and settle, type `zqx`, save | which paragraph holds the mark |
| `before-table-hold` | End | hold Delete 8 s | is the document unchanged |
| `cell-press-type` | ArrowDown, End (end of cell A1), one Delete | as `before-table-press-type` | as above |
| `cell-hold` | ArrowDown, End | hold Delete 8 s | as above |

Both browsers, 1 round per arm.

## Prediction (written before any run)

- **Positive control first.** Each arm's Delete is refused (`refusals ≥ 1`) — production-ui §13.1 *infers* that a paragraph end before a table and a cell end are refusal shapes on v19.
  - If an arm sees **no** refusal, that arm measures nothing about B + D. The finding is then about the inference ("not a refusal shape on v19"), not about the fix.
- **With B + D** (where refused):
  - `refusals == 1`, generations `['1','2']`.
  - Hold arms: document unchanged and `marks == 0`; the probe types no mark in hold arms.
  - Press-type arms: the mark in the paragraph the caret was in — 0 for `before-table`, 1 for `cell`. The rest of the document is unchanged.
- **Would contradict it:**
  - the mark in another paragraph — D did not land the caret where it was;
  - more than one refusal in a hold — B did not stop the hold;
  - any other change to the document.

  Any of these is a defect, registered as a finding. The page is not changed while the owner is away; a fork goes to fable (owner's authorisation, 2026-10-13).

## run-1: the positive control failed — nothing was measured

All eight arms read 0 refusals and an unchanged document. Even the press-type arms ended with `marks == 0`. The log shows why: every key, the Delete and `zqx`, landed on `body-user`, not the sink. Nothing had focused the sink: the owner-document probes click into the text first, and this probe did not. So run-1 says nothing about B + D or about whether these places are refusal shapes. It is kept as the failed control.

Probe fix (an instrument fix caused by a run, not a check): after opening, `#sink` is focused with the caret where the page opened it (the document start), recorded as `focused`. Then the moves follow. Same predictions; run-2 follows.
