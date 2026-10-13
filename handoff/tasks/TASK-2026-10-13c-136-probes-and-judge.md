# Task 2026-10-13c — ruling-3 conditions 3 and 4: probe arms, reader fields, judge rules, and the pre-fix baseline

Implement the browser-acceptance side of `findings/evidence/134/ruling/ruling-3.md` (read it in full, including addenda 1–3). The page fix is already committed (`b2b488c0`, page `aebef525…`) but **not packaged**: the ddev host still serves 0.2.16 = page `6470dec0…`. That is deliberate: the pre-fix baseline (step 4) runs on it.

## Files you change (and nothing else)

- `findings/evidence/132/held-into-refusal/probe_held_into_refusal.py`
- `findings/evidence/134/table/probe_table_refusal.py`
- `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py`

Do not touch `wasm_sdk_probe/web/`, `dist/`, the host repo, any other judge, and do not run `make`.

## What to build

1. **A second mark.**
   - `AFTER = "wvy"` is typed **after** the reopen in every arm that needs it (below). Before using it, check that the owner document and the table fixture contain no `wvy`.
   - `MARK` (`zqx`) keeps its current meanings.
   - `CONTROL = "kj"` is typed at the caret just before the key where condition 3 asks for it.
2. **Exception to condition 3's literal text — reason it in the probe docstring.** `start-press` is Backspace at the document start. Typing `kj` first would make that Backspace delete `j`, so the key would no longer be refused. So `start-press` gets **no control**. Instead it types `AFTER` after the reopen and is judged by the hold rule: `AFTER` at the start of paragraph 0.
   - `end-press-type`, `before-table-press-type` and `cell-press-type` get `CONTROL` before the key and `AFTER` (or the existing `zqx`) after the reopen. They are judged on contiguity (`CONTROL` immediately followed by the post-reopen mark).
3. **Hold arms type `AFTER` after release and settle.**
   - Arms: `start-hold`, `end-hold`, `before-table-hold`, `cell-hold`.
   - Judged: `start-hold` → `AFTER` at the start of paragraph 0. The others → `AFTER` at the end of its own paragraph: the last paragraph for `end-hold`; paragraph 0 for `before-table-hold` (end of `E1-TABLE-BEFORE`); paragraph 1 for `cell-hold` (end of `E1-CELL-A1`).
   - For `end-hold`, `zqx` was typed at the end before the hold, so `zqxwvy` must close the last paragraph.
4. **Reader booleans, no text in the report.**
   - `server_read` (both probes) strips `MARK`, `CONTROL` and `AFTER` before the original-sequence comparison.
   - It records, for each mark, the indexes of the paragraphs holding it.
   - It records `controlThenMark` (`CONTROL + <post-reopen mark>` contiguous anywhere).
   - It records `afterAtStart` (the paragraph holding `AFTER` starts with it) and `afterAtEnd` (that paragraph ends with it).
5. **Judge.**
   - **Tool-closed over both probes.** Pick the probe by `report["probe"]`, read that probe's `ARMS` by `ast` (the table probe's `ARMS` is a dict literal; its keys are the arms), and FAIL any arm with no rule. The non-vacuity rule stays: every required browser has at least the minimum rounds per arm.
   - **Placement rules** as above, plus the existing ones: one reopen, document kept (with the three marks stripped), each mark exactly once where it is typed.
   - **The `scrollTop` rule, condition 4.** It applies to the end arms of the held probe (`end-hold`, `end-press-type`). Every state sample from the first `restart-required` up to the first state entry whose toast contains 「已重新載入」 must be ≥ 0.5 × the last sample before that refusal. On `start-*` arms every sample stays 0. Table arms are exempt.
   - Exit 0 only if all pass. Print the raw inputs per round.
6. **Red cases first**, saved under `findings/evidence/136/judge/`:
   - (a) The judge on `findings/evidence/134/table/run-3/report.json` FAILs `cell-press-type` on contiguity. It will also fail what that old report lacks; print it and say so.
   - (b) The judge on `findings/evidence/134/acceptance-0.2.16/report.json` FAILs the `scrollTop` rule on the end arms. Record exactly what else fails because the report predates the new fields.
   - (c) A fictitious arm added to a probe's `ARMS` (scratch copy) → FAIL "no rule".

## The pre-fix baseline (browser; one job at a time; nothing else of ours running — check `pgrep -af "probe_|check_m3|ab_wrapper"`)

Run both probes with all their arms, both browsers, default rounds, on the host as it is (0.2.16, `6470dec0…`):

- held probe → `findings/evidence/136/baseline-0.2.16/held/`
- table probe → `findings/evidence/136/baseline-0.2.16/table/`

Then judge both with `--page 6470dec0…`.

**Expected on 6470dec0** (write this prediction into `findings/evidence/136/baseline-0.2.16/README.md` **before** running):

- `cell-press-type` FAILs contiguity.
- `cell-hold` FAILs `AFTER` at the end of paragraph 1 (D puts it in B1).
- `end-hold` and `end-press-type` FAIL the `scrollTop` rule (the view goes to 0).
- `start-press` and `start-hold` PASS the new hold rule — the caret really is at the start. That is the red/green pair ruling-3 condition 3 asks for.
- `end-press-type` PASSes contiguity and `before-table-*` PASS: D is exact where nothing was selected.

Any other outcome is reported as is; do not adjust the judge to fit.

## Output

- Commit in two steps:
  - the probes, the judge and the reds (a)–(c) first;
  - then the prediction README, the baseline runs and the judge outputs.
- Commit messages: zh-TW, ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, never a `Claude-Session:` line. Use `git commit -- <paths>` so that only your files go in.
- Final reply: `## SUMMARY` (≤30 lines): what changed, each red case's exit and failing lines, the baseline verdict per arm per browser against the prediction, and anything that did not match.
