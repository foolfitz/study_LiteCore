# `cell-start-hold`: a held Backspace into the start of a table cell (ruling-3 addendum 4)

**Prediction written and committed before any run.**

## The arm (`findings/evidence/134/table/probe_table_refusal.py`)

Fixture `e1-fixtures/table-boundary.odt`. Paragraph 0 is `E1-TABLE-BEFORE`, and paragraphs 1–4 are cells A1, B1, A2, B2.

The probe focuses the sink at the document start, then:

1. ArrowDown, then Home: the caret is at the start of A1.
2. Types `kjkjk`.
3. Holds Backspace for 8 s (delay 500 ms, interval 30 ms), releases, and waits for the page to settle.
4. Types `wvy` and saves.

The read-back has no text, only these fields:

- `refusalStage`: the stage named by the page's reopen toast. 「這裡目前還不能這樣刪除」 is labelled `anchor-mismatch`.
  - Named limit: the page shows the same sentence for the other keyPosted:false "unchanged" stages (`restore`, `return-mismatch`, `unit-late`, `undo-read`), and it exposes no stage, so the probe cannot tell them apart.
- `cellStart.paragraph1StartsWithAfter` and `cellStart.paragraph1IsAfterThenOriginal` (A1 is exactly `wvy` followed by the original A1).
- The held probe's reader: counts, paragraph indexes, `afterAtStart`.

## The judge rule (`judge_held_into_refusal.py`, `cell-start-hold`)

- One reopen: 1 refusal, generations 1→2, no limit notice.
- **Positive control:** `refusalStage.stage == "anchor-mismatch"`. Any other stage FAILs as "measures that stage, not D".
- Document kept once the three marks are stripped.
- Counts `zqx` 0, `kj` 0, `wvy` 1. `kjkjk` must be fully gone: a residue leaves `kj` ≥ 1, or, for a lone `k`, a difference.
- `afterParagraphs == [1]` and `afterAtStart`.
- 2 rounds per browser.

## Red run: host as it is now, 0.2.17, page `aebef525…` (send-time FIFO, addendum 4's refused rule)

**Run:** only this arm, Chrome and Firefox, 2 rounds each, into `red-aebef525/`. Judged with `--page aebef52560bce2a3572c4e0f85197366ef544809331ae8b7dd2be55faaa4d2b8`.

**Expected:**

- **Positive control holds:** 1 refusal per round, stage `anchor-mismatch`, generations 1→2.
  - If the stage is anything else, the arm measures that stage, not D. That is reported as such, not as D's red.
- **B holds:** `kjkjk` fully gone, document otherwise original, `wvy` counted once.
- **D's red:** in at least one round per browser, `wvy` lands one character into A1, not at its start: `afterParagraphs [1]`, `afterAtStart` false, `paragraph1StartsWithAfter` false.
  - The cause: the refused Backspace is sent while the previous delete is unprocessed, so its send-time caret is one character right of the caret at refusal (addendum 4, review 1 B1).
  - "Unstable" also counts as the predicted red: some rounds at the start, some one character in.
  - All four rounds at A1's start would contradict the prediction.
- **Judge exit 1.**
  - It also FAILs the four other table arms on both browsers as `0 rounds < 1`, because only this arm runs. That failure is by construction, not a finding.
