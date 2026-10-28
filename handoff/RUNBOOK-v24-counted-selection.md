# v24 counted selection and four-arm execution

Prepared 2026-10-28. Execution mode still awaits the owner. No DDEV or build is involved.
The frozen product-path Enter FAIL in Chrome is the declared I-enter-raw-substring instrument
limit; its separate replay is already PASS. Do not edit any of the 40 live-asserted paths.

## Selection cohort

Fresh declaration: `findings/evidence/link-batch-v24/counted-selection-01/cohort.json`.
Stage order: S5 (1,176 cells), R1 (144), S1-S4 (234), both browsers, 1,554 cells total.
The launcher verifies the frozen config, source archive, prerequisites and generated population;
runs V0'' before **each** stage; and stops on the first nonpass or input drift. Existing status
or output refuses a retry. Never remove status to resume a stopped cohort.

Historical time basis (estimates, not gates): v23 R1 5,708.5 s; selection 7,466.8 s;
stopped S5 7,567.4 s for 402 observations. Linear extrapolation of that partial S5 is about
6.15 hours for 1,176 cells. Reserve about **10-12 hours** for this selection cohort, including
overhead. This is not a fresh full-v24 runtime measurement.

For owner-run, from the SDK directory:

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
python3 -I tools/run_v24_counted_cohort.py --cohort ../findings/evidence/link-batch-v24/counted-selection-01/cohort.json
python3 -I tools/read_v24_counted_cohort.py --cohort ../findings/evidence/link-batch-v24/counted-selection-01/cohort.json --out ../findings/evidence/link-batch-v24/counted-selection-01/completion-read-01.json
```

For detached execution, the agent launches the same first command with a new process session,
stdin disconnected, and stdout/stderr bound to a new log. This requires the owner's execution-mode
choice first; the preparation turn does not launch it. The final raw-artifact reader runs after
the launcher exits, including after a nonzero exit.

Progress: read `counted-selection-01/status.json` and the current `s5.runner.txt`, `r1.runner.txt`
or `selection.runner.txt`. Do not start competing browser measurements or builds. A foreign-CPU
refusal retains its evidence; do not weaken its threshold or close the owner's browser.

Acceptance: `status.state == ALL_COHORTS_PASS` plus the raw-artifact reader's
`V24_SELECTION_COUNTS_HOLD`. A stopped or partial cohort does not satisfy an unobserved population.
Any red is diagnosed from its retained raw cell, not retried into the same directory.

## A4 after the selection count

The v24 wrapper rebinds the bound bundle module's default from 76 to 77 **before** importing the
unchanged runner. It records the override; the v24 reader requires profile/ABI/artifacts, frozen
generation 77 and the frozen product page. Identity-only preflights and the old-run reds are in
`findings/evidence/link-batch-v24/count-preparation/`.

The pre-run tool closure is recorded in that directory's `a4-instruments.sha256` (paths relative
to the SDK directory). Verify it before and after the fresh run. Each wrapper runs V0'' itself.
The ordinary product-path suite may return nonzero for declared/inherited non-A4 checks;
the wrapper records that exit separately and returns according to its four-arm reader.

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe
sha256sum --check ../findings/evidence/link-batch-v24/count-preparation/a4-instruments.sha256
python3 -I tools/run_v24_four_arms.py --browser chrome --out ../findings/evidence/link-batch-v24/four-arms-counted-01/chrome
python3 -I tools/run_v24_four_arms.py --browser firefox --out ../findings/evidence/link-batch-v24/four-arms-counted-01/firefox
sha256sum --check ../findings/evidence/link-batch-v24/count-preparation/a4-instruments.sha256
python3 -I tools/judge_v24_product_four_arms.py ../findings/evidence/link-batch-v24/four-arms-counted-01/chrome/report.v23-four-arms ../findings/evidence/link-batch-v24/four-arms-counted-01/firefox/report.v23-four-arms --out ../findings/evidence/link-batch-v24/four-arms-counted-01/aggregate-judge.json
```

Stop at the first wrapper/identity failure; the commands above are a sequence, not permission to
continue past a red. Aggregate acceptance: all four arms PASS, 24 distinct rows, both real browsers,
no population problems. Historical v23 full product-path runs took about 8.6 minutes per browser;
reserve roughly 20-30 minutes for A4, excluding diagnosis and machine contention.

## Afterwards

Host package, BINDING, K remain separate work. Ask for the shared DDEV slot and the named quiet
window before K. No build authority, slot or release promotion is implied by selection/A4 success.
The uncounted-change ledger is `research/2026-10-25-count-batching-and-next-work.md`.
