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

## Result of the red run (appended; the prediction above is unchanged)

- **Run:** 2026-10-13 02:18–02:21Z. Probe exit 0, no fatal round.
- **Static:** before = after: host 0.2.17 (`f5b34f0`, info.xml uncommitted), buildId `e39447158dba7a3b`, served = dist = `aebef525…`.
- **Judge:** exit 1, `FAIL (16)` (`red-aebef525/judge-output.txt`).
  - 8 of the lines are the other four table arms × two browsers at `0 rounds < 1`. That is by construction, as predicted.

| round | refusals | gens | stage (toast) | `kjkjk` gone, doc original | `wvy` in | `afterAtStart` | judge |
|---|---|---|---|---|---|---|---|
| chrome r0 | 1 | 1→2 | **nothing-selected** | yes | [1] | false | FAIL ×2 |
| chrome r1 | 1 | 1→2 | **nothing-selected** | yes | [1] | false | FAIL ×2 |
| firefox r0 | 1 | 1→2 | **nothing-selected** | yes | [1] | false | FAIL ×2 |
| firefox r1 | 1 | 1→2 | **nothing-selected** | yes | [1] | false | FAIL ×2 |

**The positive control did not hold. This contradicts the prediction and addendum 4's assumption.**

- At the start of cell A1, the engine answers the held Backspace's refusal with `nothing-selected` (「這一下沒有取得可刪除的內容」), not `anchor-mismatch`. It does so on both browsers, every round.
- So, by the arm's own rule, `cell-start-hold` **measures the `nothing-selected` stage at a cell start, not D at `anchor-mismatch`**. Each round FAILs first on `refusal stage 'nothing-selected': measures that stage, not D`.

**The caret was in A1.** `wvy` landed in paragraph 1 on every round. Had the ArrowDown failed, `kjkjk` would have gone to the document start and the reopened caret into paragraph 0.

**What it did show, outside the arm's intended stage:**

- B holds: 1 refusal per round, `kjkjk` fully deleted, document otherwise original.
- D misplaces `wvy` on 4 of 4 rounds: `afterAtStart` false. That is stable, not "unstable".
- A post-hoc read of the server file still on the host after the last round (Firefox r1; its sha256 equals that round's recorded `server.sha256`) puts `wvy` at index 1 of paragraph 1, **one character into A1**. The other three rounds' offsets were not recorded: the reader keeps booleans only.
- This is the same shape as `start-hold`'s 4/4 FAIL on `aebef525` (also `nothing-selected`), i.e. addendum 4's B1 mechanism.

**For the ruling author (not acted on here):** as specified, the arm cannot serve as the `anchor-mismatch` red/green pair.

- An `anchor-mismatch` hold into a cell exists already: `cell-hold`, a Delete held at A1's end.
- What `cell-start-hold` adds is a `nothing-selected` refusal **inside a cell**, where D's click must land at A1's start rather than the document start.
- Whether to keep the arm with its positive control changed to `nothing-selected`, or to drop it, is a decision for the ruling. The judge rule was not changed.
