# Judge red cases for ruling-3 conditions 3 and 4 (task 2026-10-13c)

Judge: `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py`, now tool-closed over both probes (`probe_held_into_refusal.py`, `probe_table_refusal.py`; picked by `report["probe"]`, arms read by `ast` from that probe's `ARMS`). All three reds were run with `--page 6470dec0…` (the page both old reports were taken on), before any baseline run. Each file ends with the judge's exit code.

| file | report | exit | what fails |
|---|---|---|---|
| `red-a-table-run-3.txt` | `134/table/run-3/report.json` | 1 | `cell-press-type` on contiguity, both browsers |
| `red-b-acceptance-0.2.16.txt` | `134/acceptance-0.2.16/report.json` | 1 | the `scrollTop` rule on `end-hold` ×2 and `end-press-type`, both browsers |
| `red-c-made-up-arm-table.txt` | run-3, scratch copy of the table probe with `"made-up-arm"` added to its `ARMS` dict | 1 | `made-up-arm: no rule for an arm the probe declares` |
| `red-c-made-up-arm-held.txt` | acceptance-0.2.16, scratch copy of the held probe with `"made-up-arm"` added to its `ARMS` tuple | 1 | the same line |

## (a) table run-3: contiguity red, and what the old report lacks

- **The red asked for:** `cell-press-type` FAILs `CONTROL then MARK not contiguous (controlThenMark False)` on Chrome and Firefox (`kj` in paragraph 1, `zqx` in 2). `before-table-press-type` reads `controlThenMark True` on both, so the contiguity rule separates the two shapes.
- `controlThenMark` is read from `run["control"]`, where run-3's reader (`control_read`) put it, with the same definition (`kj` + `zqx` in one paragraph). The judge reads it there only when the server read lacks it, and the printed line names the source. That is the only fallback in the judge.
- **Fails because the report predates the new fields or arms:**
  - `controls not recorded`, `afters not recorded`: all four press rounds.
  - `server differs after the reader stripped its marks`: all four press rounds. Run-3's reader stripped only `zqx`, so the `kj` it typed is still counted as a change (`charDelta 2`). The new reader strips all three marks.
  - `before-table-hold` and `cell-hold`: 0 rounds < 1 on both browsers. Run-3 ran the press arms only.
- Verdict FAIL (18).

## (b) acceptance-0.2.16: scrollTop red, and what the old report lacks

- **The red asked for:** every end round FAILs `scrollTop: 2 of 8 samples in the reopen window < 0.5 x 21477` (Chrome) or `x 21463` (Firefox), lowest 0. That is 6 rounds: `end-hold` r0 and r1 plus `end-press-type` r0, on each browser. The window runs from the first `restart-required` to the first toast containing 「已重新載入」, inclusive. The two low samples are the new generation's `ready` and the `busy` that follows it, both at 0.
- **Passes:** the start rounds' `scrollTop` (every sample 0), one reopen, document kept, `marks 1`, and `end-press-type`'s mark in the last paragraph.
- **Fails because the report predates the new fields:**
  - every round: `controls not recorded`, `afters not recorded`;
  - `start-press`, `start-hold`: `afterParagraphs`, `afterAtStart` not recorded (no `wvy` was typed);
  - `end-hold`: `afterParagraphs`, `afterAtEnd`, `markThenAfter` not recorded;
  - `end-press-type`: `controlThenMark` not recorded (no `kj` was typed).
- No other line fails. Verdict FAIL (56).

## (c) fictitious arm

Scratch copies under the session scratchpad mirror the relative layout (`ev/132/held-into-refusal/`, `ev/134/table/`). The judge copy is byte-identical to the committed one, and each probe copy differs only in its `ARMS` line. Both runs add exactly one failure to (a) and (b): `made-up-arm: no rule for an arm the probe declares` (FAIL 19 = 18 + 1; FAIL 57 = 56 + 1). Every other line is identical to (a) and (b), checked with `diff`.

## Rules beyond the task's literal text (named here so they are not mistaken for drift)

- **Mark counts include zero where a mark is not typed.** Start-hold's `kjkjk` contains `kj`, and the reader strips `kj`, so a residue of `kjkjk` would vanish from the "document kept" comparison. The count catches it: `kjkj`, `kjk` and `kj` leave `controls ≥ 1`, and `k` leaves a difference.
- **`markThenAfter`** is a reader boolean added for `end-hold`'s "`zqxwvy` closes the last paragraph": `wvy` in the last paragraph only, `afterAtEnd`, and `zqx` immediately before `wvy`.
- **`scrollTop` non-vacuity:** on the end arms the last sample before the refusal must be > 0, and the window must close at a 「已重新載入」 toast. With the view at 0 before the key, `≥ 0.5 × 0` would hold for any page.
- **Probe instrument:** `#desk` scroll events also trigger a sample, because a scroll is not a DOM mutation. The last sample before the key is recorded as `stateBeforeKey`. The old reports have neither, and their mutation-driven samples were enough to show the jump to 0.
