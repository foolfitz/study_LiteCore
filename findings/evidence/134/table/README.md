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

## run-2 (focus fixed; probe exit 0; static before = after: host 0.2.16, served page `6470dec0…`)

The positive control passed in every arm: both places are refused on v19, and both browsers read the same.

| arm | refusal (toast) | generations | result |
|---|---|---|---|
| before-table-press-type | key posted, not verified (「這一下刪除送出了，但沒能確認它做了什麼」) | 1→2 | mark in paragraph **0**, the rest unchanged |
| before-table-hold | same | 1→2 | **1 refusal**, document unchanged |
| cell-press-type | `anchor-mismatch` (「這裡目前還不能這樣刪除」) | 1→2 | mark in paragraph **2** (cell **B1**), the rest unchanged |
| cell-hold | same | 1→2 | **1 refusal**, document unchanged |

- **B holds at both table shapes.** One refusal per hold; nothing deleted.
- **D reported success in all four press-type rounds.** No toast said 「游標現在在文件開頭」.
- **Against the prediction:** the cell arm's mark landed in cell **B1** (2), not A1 (1). The before-table arm cannot tell success from failure: the end of paragraph 0 and the document start are the same paragraph.

Two readings of the cell result:

- **(a) Navigation.** ArrowDown + End had already put the caret in B1, and D was right.
- **(b) D defect.** The refused Delete's barrier moved the engine's caret into B1 before the refusal, so the "last caret the engine reported" that D reads is not the user's caret.

## run-3: control mark (prediction written before the run)

Press-type arms only, both browsers, `--control kj`. `kj` is typed at the caret just before the Delete. The read-back records three things, all without text: which paragraph holds `kj`, which holds `zqx`, and whether `kjzqx` occurs contiguously.

- **If (a):** `kj` and `zqx` in the same paragraph, contiguous `kjzqx`, in both arms. D put the caret exactly where it was.
- **If (b):** in the cell arm, `kj` in paragraph 1 (A1) and `zqx` in 2 (B1). D restores to the barrier's caret. That is a defect of D, registered as a finding. The page is not changed while the owner is away; it goes to fable.
- **Before-table arm:**
  - `kj` and `zqx` contiguous in paragraph 0 means D restored to the paragraph end.
  - `zqx` at the document start (not contiguous) would mean D's click landed at the start.

`sameAsOriginal` is false by construction in run-3, because `kj` stays in the document.

## run-3 result (control `kj`; probe exit 0; host 0.2.16, page `6470dec0…`)

| arm | browser | refusals | `kj` in | `zqx` in | `kjzqx` contiguous |
|---|---|---|---|---|---|
| before-table-press-type | chrome | 1 | 0 | 0 | **yes** |
| before-table-press-type | firefox | 1 | 0 | 0 | **yes** |
| cell-press-type | chrome | 1 | **1 (A1)** | **2 (B1)** | no |
| cell-press-type | firefox | 1 | **1 (A1)** | **2 (B1)** | no |

- **Paragraph end before the table** (refusal shape: key posted, not verified): D put the caret back exactly where it was.
- **Cell end** (refusal shape: `anchor-mismatch`): reading **(b)** holds. The user's caret was at the end of A1, and D put it in **B1**. Text typed after the reopen lands in the next cell. D reported success, so the toast said nothing about it.

Why, by code (unmeasured inside the engine): `startMergeKeyUndo` (`wasm_sdk_probe/src/probe_engine.cpp:3600-3612`) fails the fence and calls `finishMergeKeyError("anchor-mismatch")` **while K1's one-unit selection is still active**. That selection extends from A1's end into B1. No `.uno:Escape` restores it first. So the last editor state the engine pushed has its caret in B1. D reads exactly that (`session.state.snapshot.editorState.caret` before `restart()`; ruling-1 condition 2 named "the engine's last pushed state"). At the document ends (`nothing-selected`) nothing was selected, so the two coincide; that is why the acceptance run could not see this.

Registered as **finding 136**. It is not a regression against 0.2.15, which put the caret at the document start. It is the place where D's claim ("the caret goes back where it was") fails.
