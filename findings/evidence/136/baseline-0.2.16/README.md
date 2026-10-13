# Pre-fix baseline of the ruling-3 acceptance on host 0.2.16 (task 2026-10-13c)

**Prediction written and committed before any run.**

## What runs

- **Host:** as it is: 0.2.16 (`f5b34f0`), engine buildId `9352fae3aea68b5e`, served page = dist page = `6470dec0…`. Checked just before writing this.
  - The fix (`b2b488c0`, page `aebef525…`) is in `web/` only and is not packaged. The shell-bundle check therefore reports `web/e2-editor-app.js` changed against v65. That is expected, and the judge does not read it.
- **Probes:** the probes and judge as committed in `53f7aff5`, all arms, default rounds, both browsers (Chrome, then Firefox), one job at a time, nothing else of ours running.
  - `held/`: `probe_held_into_refusal.py`, owner's document. Rounds: start-press 1, start-hold 2, end-hold 2, end-press-type 1.
  - `table/`: `probe_table_refusal.py`, `e1-fixtures/table-boundary.odt`. 1 round per arm.
- **Judge:** `judge_held_into_refusal.py <report> --page 6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b`, output kept as `judge-output.txt` in each directory.

## Prediction (from the task, verbatim in substance)

- `cell-press-type` FAILs contiguity: `kj` in A1 (paragraph 1), `zqx` in B1 (paragraph 2). This is finding 136 as run-3 measured it.
- `cell-hold` FAILs "`wvy` at the end of paragraph 1": D puts it in B1, so `afterParagraphs` is `[2]`. Where inside B1 it lands is not predicted.
- `end-hold` and `end-press-type` FAIL the `scrollTop` rule: the view goes to 0 inside the reopen window (L-134-restore-flash).
- `start-press` and `start-hold` PASS the new hold rule (`wvy` at the start of paragraph 0). On this page the caret really is at the start, because D restores the snapshot caret and nothing was selected. Together with a later run on the fixed page, this is the red/green pair ruling-3 condition 3 asks for.
- `end-press-type` PASSes contiguity (`kjzqx`), and `before-table-press-type` and `before-table-hold` PASS: D is exact where nothing was selected.

## Implied by the above, stated now so it is not read after the fact

- **Every other rule passes on every arm:**
  - one reopen (1 refusal, generations 1→2, no limit notice);
  - document kept once the three marks are stripped;
  - mark counts as typed, 0 where not typed;
  - `end-press-type`'s `zqx` in the last paragraph;
  - `end-hold`'s `wvy` alone in the last paragraph, at its end, right after `zqx`;
  - `scrollTop` 0 throughout on the start arms.
- **So each FAILing arm FAILs on exactly one rule, on both browsers:**

  | arm | verdict | the one failing rule |
  |---|---|---|
  | `start-press` | PASS | |
  | `start-hold` | PASS | |
  | `end-hold` | FAIL | `scrollTop` |
  | `end-press-type` | FAIL | `scrollTop` |
  | `before-table-press-type` | PASS | |
  | `before-table-hold` | PASS | |
  | `cell-press-type` | FAIL | contiguity |
  | `cell-hold` | FAIL | `wvy` placement |

- **Both judges exit 1.**

Any other outcome is reported as it is. The judge is not adjusted to fit.

## Result (appended after the runs; the prediction above is unchanged)

- **Runs:** held 2026-10-13 01:38–01:48Z, table 01:48–01:53Z. Probe exit 0 both. No round fatal.
- **Static:** before = after in both reports: host 0.2.16 `f5b34f0`, buildId `9352fae3aea68b5e`, served = dist = `6470dec0…`. `marksInOriginal` all 0.
- **Judge:** both exit 1, `FAIL (6)` each (`held/judge-output.txt`, `table/judge-output.txt`).

| arm | Chrome | Firefox | predicted | failing rule (raw input) |
|---|---|---|---|---|
| start-press | PASS | PASS | PASS | `wvy` in [0], `afterAtStart` true, scroll [0] |
| start-hold ×2 | PASS, PASS | PASS, PASS | PASS | same, every round |
| end-hold ×2 | FAIL, FAIL | FAIL, FAIL | FAIL `scrollTop` | `scrollTop` only. Window [pre, pre, **0, 0**, pre, pre, pre, pre], pre 21477 (Chrome) / 21463 (Firefox). Placement holds: `wvy` in [210], `afterAtEnd`, `markThenAfter` |
| end-press-type | FAIL | FAIL | FAIL `scrollTop` | `scrollTop` only, the same window. `controlThenMark` true, `zqx` in [210] |
| before-table-press-type | PASS | PASS | PASS | `kj` and `zqx` in [0], `controlThenMark` true |
| before-table-hold | PASS | PASS | PASS | `wvy` in [0], `afterAtEnd` true |
| cell-press-type | FAIL | FAIL | FAIL contiguity | contiguity only: `kj` in [1], `zqx` in [2], `controlThenMark` false |
| cell-hold | FAIL | FAIL | FAIL `wvy` placement | placement only: `wvy` in [2], printed as two lines (`AFTER in paragraphs [2], expected [1]`; `afterAtEnd` false) |

- **Every outcome matches the prediction:** each arm, each browser, and each failing arm fails on exactly its one predicted rule. Every other rule passes on every round: one reopen, document kept with the marks stripped, and mark counts.
- **Observed, not predicted:** in `cell-hold`, `wvy` lands at the **start** of B1 (`afterAtStart` true) on both browsers. That is consistent with D clicking at the end of K1's one-unit selection, which is B1's start.
- **`stateBeforeKey`:** recorded on every round (scroll 0 on the start and table arms; 21477 / 21463 on the end arms). In every end round the log also had its own sample before the refusal, so the window's `pre` comes from the log.
- **Not judged, unchanged from `134/acceptance-0.2.16`:** on the hold arms, part of the held key's repeats land on `body-user` while the sink is disabled during the reopen. Chrome sends 218 of 255 to the sink, Firefox 192–193 of 255.
