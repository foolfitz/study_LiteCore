# v16 shakedown: product-path net, `e2-editor-v16` against `e2-editor-v8`

This is a shakedown. It is not counted and nothing is bound to it.

Nothing in the tree was edited for this run. The only files created are in this directory
(6 reports, 6 `*.stdout.txt` [the runner prints the same JSON it writes with `--out`], 6 `*.stderr.txt`,
`chain.log`, this README). `git status --short` after the last run showed `?? findings/evidence/v16-shakedown/`
and one modified tracked file that is not part of this task (`wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`,
edited by the main session while the chain was running).

**The v8 baseline was NOT re-run for this README.** The three `v8 chrome` and three `v8 firefox` reports used
below are the six v8 reports of this morning's v15 shakedown:
`findings/evidence/v15-shakedown/product-path/e2-editor-v8-{chrome,firefox}-r{1,2,3}.json`
(run 10:42-11:23 +08:00 the same day; that README records the same runner sha256 prefix, the same Chrome and Firefox version numbers,
and a served shell with the same two differing paths; see it). The v16 reports here were taken 14:36-15:15 +08:00.

## Commands

From `wasm_sdk_probe/`, strictly sequential (one run at a time; the order was chrome r1, r2, r3, then firefox r1, r2, r3;
driven by a small shell loop that is not kept, which also waited for any `run_e2_c_product_path` / `run_merge` /
`geckodriver` / `chromedriver` process to be absent before each run; `chain.log` has each start and end line with the
exact command). `<N>` is 1, 2, 3.

```
python3 tools/run_e2_c_product_path.py --browser chrome  --candidate-profile e2-editor-v16 --out <DIR>/e2-editor-v16-chrome-r<N>.json  > <DIR>/e2-editor-v16-chrome-r<N>.stdout.txt  2> <DIR>/e2-editor-v16-chrome-r<N>.stderr.txt
python3 tools/run_e2_c_product_path.py --browser firefox --candidate-profile e2-editor-v16 --out <DIR>/e2-editor-v16-firefox-r<N>.json > <DIR>/e2-editor-v16-firefox-r<N>.stdout.txt 2> <DIR>/e2-editor-v16-firefox-r<N>.stderr.txt
```

`<DIR>` = `/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v16-shakedown/product-path`.
Default `--timeout`; no other flags. `build_cutover_page.py` was not called. No `make`. The profile
`wasm_sdk_probe/dist/profiles/e2-editor-v16/` was not rebuilt or touched (its `probe.wasm` sha256 starts `ad3f68bb85f94589`,
which equals `pinAfter` in every report). No other runner of mine ran. No run refused to start; every run wrote a report.

Start of chain 2026-10-07 14:36:08 +08:00, end 15:15:45 +08:00. Exit codes from `chain.log`: Chrome r1/r2/r3 = 0; Firefox
r1/r2/r3 = 1 (`ok: false`, as expected from the FAIL cell described below). Every run completed (`complete: true`,
`liveness.lastState: ready`, `pageErrors: null`, `knownRed: {}`, `staleKnownRedDeclarations: []`).

## Environment

- Google Chrome 151.0.7922.169; Firefox 157.0 (snap, firefox/8995); runner `tools/run_e2_c_product_path.py`
  sha256 `5900ce877146c7bc...` (same prefix before the first run and after the last).
- Served shell, all 6 v16 runs: bundle `e2/editor-shell-v2-bundle-v55.json`, `declaredSha256`
  `2470765ae19ced019b423b55e856ef8d60759ee878d56ff835e6e9387b62167c`, `servedSha256`
  `063dee943a662b7ca8686765436efc6a007d0b5f864455467e14199f7b163c5f`, `missing: []`,
  `differingPaths`: `editor-shell-v2/narrow-editor-v2-client.js`, `editor-shell-v2/narrow-editor-v2-session.js`,
  `web/e2-editor-app.js`; `differsOnlyInTheEntrypoint: false`. (The first two are the known "red by design" item of the
  runbook; the third is the repointed candidate entrypoint.) The runner did not refuse on this.
  The v8 reports were served bundle v55 with `servedSha256` `5bfc7642f5d1f8ecad23679f117115fa8b052604c7d0f9f82d1a709866ac657f`
  and `differingPaths` the first two only; entrypoint `web/e2-editor-app.js` sha256 `e97d6e035d8f84ef...` (shipped page).
- `candidateCutover` (identical in all 6 v16 reports): `profile: e2-editor-v16`,
  `pageSha256: cc523c9c48c25385e10af6ec72b6dd004dc1d83f926d6807541f99cd454551cc`, `pinBefore: 4a2710bba1ef07d9`,
  `pinAfter: ad3f68bb85f94589`. The report's own note: "This run measured the CANDIDATE page for a cutover to e2-editor-v16 --
  the page as it will ship, with its own pinned hash and its own worker URL, not a --profile override.
  `tools/build_cutover_page.py --profile e2-editor-v16` produces these exact bytes; the cutover is proven by that sha256
  matching. It is NOT a verdict on the profile the product ships pointing at today." In the v8 reports `candidateCutover` is `null`.
  `entrypointSha256` in `servedShell` equals `pageSha256` in all 6 v16 reports.

Desktop notes: processes that are not mine, present in `ps` before the first run (14:35:58) and again after the last run, with start times:
Firefox pid 777820 (and its `crashhelper` 778346), both up since Oct 6 20:57:20; Chrome pid 1090372 (no flags), up since Oct 7 12:00:19,
with the `extension-host` (pid 1090982) and `claude --chrome-native-host` (pid 1091012) helpers started 12:00:50. `ps` was not
sampled during the chain, so nothing is claimed about the interval. At 15:15:52, seven seconds after `CHAIN DONE`, a process
`python3 tools/run_merge_wasm_shakedown.py --browser chrome --candidate-profile e2-editor-v16 ...` (pid 1182213, with its own
headless Chrome 1182218) appeared; it started after my last run ended and did not overlap with any of the six.

## Runs

Times are the report's own `startedAt` / `completedAt` (+08:00, 2026-10-07); `chain.log` END lines are about 10 s later
because they include browser teardown.

| report | started | completed | PASS | FAIL | NE | ok | complete | last state | pageErrors |
|---|---|---|---|---|---|---|---|---|---|
| (v15-shakedown dir) `e2-editor-v8-chrome-r1.json` | 10:42:26 | 10:49:18 | 40 | 0 | 2 | True | True | ready | null |
| (v15-shakedown dir) `e2-editor-v8-chrome-r2.json` | 10:49:18 | 10:56:09 | 40 | 0 | 2 | True | True | ready | null |
| (v15-shakedown dir) `e2-editor-v8-chrome-r3.json` | 10:56:09 | 11:03:01 | 40 | 0 | 2 | True | True | ready | null |
| (v15-shakedown dir) `e2-editor-v8-firefox-r1.json` | 11:03:02 | 11:11:04 | 29 | 1 | 12 | False | True | ready | null |
| (v15-shakedown dir) `e2-editor-v8-firefox-r2.json` | 11:11:14 | 11:17:17 | 30 | 1 | 11 | False | True | ready | null |
| (v15-shakedown dir) `e2-editor-v8-firefox-r3.json` | 11:17:27 | 11:23:30 | 30 | 1 | 11 | False | True | ready | null |
| `e2-editor-v16-chrome-r1.json` | 14:36:08 | 14:42:30 | 40 | 0 | 2 | True | True | ready | null |
| `e2-editor-v16-chrome-r2.json` | 14:42:30 | 14:48:54 | 40 | 0 | 2 | True | True | ready | null |
| `e2-editor-v16-chrome-r3.json` | 14:48:54 | 14:55:18 | 40 | 0 | 2 | True | True | ready | null |
| `e2-editor-v16-firefox-r1.json` | 14:55:18 | 15:01:18 | 30 | 1 | 11 | False | True | ready | null |
| `e2-editor-v16-firefox-r2.json` | 15:01:28 | 15:09:25 | 29 | 1 | 12 | False | True | ready | null |
| `e2-editor-v16-firefox-r3.json` | 15:09:35 | 15:15:35 | 30 | 1 | 11 | False | True | ready | null |

`ok: false` on every Firefox run comes from the single FAIL cell `an-inline-format-reaches-a-selection`; Firefox here has no CDP, so
11-12 of the 42 checks abstain by design. This is the same FAIL cell, and the same 11/12 range, as in the v8 Firefox reports.
The Firefox NE count differs between rounds (v16: 11, 12, 11; v8: 12, 11, 11) only through
`recovery-returns-what-the-product-promised` (see the table note below); every other check has the same outcome in all
three rounds on both profiles.

## Every check, over 3 rounds each

Counts are over the 3 rounds. `NE` = NOT_ESTABLISHED (not a pass). The `v8` columns are the six morning v8 reports
(baseline not re-run, see top). The last column says `DIFF (<browser>)` for every row where the v16 count differs from the v8
count in that browser, and `same` otherwise. A differing v16 cell would be shown in bold.

| check id | v8 chrome | v8 firefox | v16 chrome | v16 firefox | v16 vs v8 |
|---|---|---|---|---|---|
| `product-save-button-writes-a-real-odt` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `every-ime-commit-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `ctrl-c-asks-the-engine` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `product-insert-button-inserts-what-the-field-holds` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `product-undo-button-reverses-the-last-edit` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `product-redo-button-restores-what-undo-removed` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `bulleting-a-blank-line-does-not-demand-a-rollback` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `notice-action-recovers-the-session` | 3 NE | 3 NE | 3 NE | 3 NE | same |
| `backspace-and-arrows-reach-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-keyboard-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `ctrl-v-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-caret-is-drawn-where-it-was-placed` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-caret-lands-where-the-click-was` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `bold-can-be-turned-off-again` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `a-format-that-worked-is-not-reported-as-failed` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `a-failed-format-does-not-block-the-session` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `format-a-paragraph-changes-that-paragraph` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `cut-removes-the-selected-text` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `a-refused-action-is-reported-and-changes-nothing` | 3 NE | 3 NE | 3 NE | 3 NE | same |
| `every-inline-format-reaches-the-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `clear-format-removes-every-inline-format` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `formatting-survives-the-next-paragraph-break` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-toolbar-gives-the-keyboard-back` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `the-edit-buttons-do-what-they-say` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-open-button-opens-the-file-chooser` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `an-aborted-gesture-stops-selecting` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `caret-follows-the-text-you-type` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-vertical-arrows-move-the-caret` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `the-composition-you-are-typing-is-visible` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `the-document-region-says-why-it-is-empty` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-projection-is-placed-where-the-document-is` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `an-inline-format-reaches-a-selection` | 3 PASS | 3 FAIL | 3 PASS | 3 FAIL | same |
| `the-page-agrees-with-the-engine-about-the-selection` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `the-canvas-follows-a-window-that-changed-size` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-sample-picker-opens-a-second-document` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `product-opens-a-document-the-user-chose` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-enter-key-reaches-the-document` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |
| `a-long-document-is-drawn-or-the-product-says-it-is-not` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `the-canvas-follows-a-document-that-grew` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `editing-a-long-document-stays-responsive` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `recovery-returns-what-the-product-promised` | 3 PASS | 2 PASS, 1 NE | 3 PASS | 2 PASS, 1 NE | same |
| `a-boundary-arrow-press-does-not-cost-the-work` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |


Rows flagged `DIFF`: **none**. For each of the 42 checks, the v16 count in Chrome equals the v8 count in Chrome, and the v16
count in Firefox equals the v8 count in Firefox. (The check list is the same 42 ids in the same order in all 12 reports.)

## Where v16 differs from v8 by count

No row. There is therefore no failure or NE text to quote for a difference.

## Cells that carry text, listed for completeness (equal counts)

These are not differences; they are the non-PASS cells, so their own text is on record next to the table.

- Firefox, both profiles, 3 of 3 rounds: `an-inline-format-reaches-a-selection` FAIL. `observed` is the same in v8 and v16 on the
  fields compared: `selectedText: ""`, `wasBoldBefore: false`; `bandsAvailable` 21/20/20 (v8) and 20/21/20 (v16).
- Firefox, `recovery-returns-what-the-product-promised`: v8 round 1 NE, rounds 2 and 3 PASS; v16 round 2 NE, rounds 1 and 3 PASS.
  The NE round has `finding038Reproduced: false`, `stateAfterDrag: "busy"`, `stateAfterNextOperation: "ready"`, and
  `fallbackInducer: {name: INDUCE_WORKER_FAILURE, fired: false, why: "no CDP; a worker cannot be reached over WebDriver"}` (the same text on
  both profiles). The report's own `why` for the v16 round-2 NE:
  > NEITHER inducer put the session into a state where the product offers its recovery button, which since 2026-08-27 is the only thing this outcome means. The first is finding 038 -- a drag covering the endnote reference mark of a paragraph whose note body holds an as-char frame -- and `finding038Reproduced` records whether it still wedges this core, because that is a fact about the core and not a reason to lose the coverage. The second is an uncaught error inside the document worker, which depends on no defect at all; `fallbackInducer.why` says why it could not fire. Both silent means the recovery path could not be reached, which is a stronger statement than it used to be
- Chrome, both profiles, 3 of 3 rounds: `notice-action-recovers-the-session` NE and `a-refused-action-is-reported-and-changes-nothing` NE
  (the same two ids as in the v8 reports; their `why` / `notEstablished` texts are in the reports and are not repeated here).
- Firefox NE set, both profiles: the 11 cells listed as `3 NE` in the table above, plus `recovery-returns-what-the-product-promised` in one round.

## Equal counts, different `observed` (found by comparing the reports, not diagnosed)

Method: for every check and every browser, every flattened scalar field of `observed` that has one single value across the three
v8 rounds and one single value across the three v16 rounds, and the two values differ. Result:

- Both browsers, `the-vertical-arrows-move-the-caret` (`offered.profile`), `an-inline-format-reaches-a-selection` (`profile`) and, on Firefox,
  `a-boundary-arrow-press-does-not-cost-the-work` (`offered.profile`): the profile name string (`e2-editor-v8` vs `e2-editor-v16`). Nothing else.
- Chrome, `a-boundary-arrow-press-does-not-cost-the-work` (3 PASS on both profiles). 23 fields, all identical across the three rounds within each profile:

  | `observed` field | v8 chrome (3/3) | v16 chrome (3/3) |
  |---|---|---|
  | `theEngineAnsweredThePress` | `false` | `true` |
  | `stateAfterPress` | `"recoverable-error"` | `"ready"` |
  | `verdict.clausesExercised` | `["B1","B3","B4"]` | `["B1","B3","B2","B4"]` |
  | `verdict.b4Inducer` | `"boundary-press"` | `"worker-failure"` |
  | `fallbackInducer` | absent | `{name: INDUCE_WORKER_FAILURE, fired: true, dependsOnADefect: false, workerUrl: ["e2-editor-v16","sdk-worker.js"]}` |
  | `stateAfterFallback` | absent | `"recoverable-error"` |
  | `declaredCheckpointAfterFallback` | absent | `"有（r1）"` |
  | `checkpointOnOfferIsThisGestures` | absent | `true` |
  | `notice.*` (`shown`, `label`, `rescue`, `text`, `disabled`) | `true`, `"回到檢查點"`, `"checkpoint"`, `"這一步可能已經改到文件，而且無法驗證。回到選取手勢前的檢查點。"`, `false` | absent (the same five values appear under `noticeAfterFallback.*` on v16) |

  On both profiles `verdict` is `{ok: true, B1: true, B2: true, B3: true, B4: true}` and `workCameBack: true`.
  (The v15 shakedown reported this cell as 3 FAIL on v15 Chrome with `B4: null`; that is a different profile and is not compared here.)
- Chrome and Firefox, `recovery-returns-what-the-product-promised`: no field with a stable, differing value.
  On Chrome `finding038Reproduced: true` in 3/3 rounds on both v8 and v16, and the `observed` object has no `fallbackInducer` key in any of the six.
  `inducer.drag` on Firefox (the NE round): `[0.10667, 0.74, 0.06168]` (v16 round 2).
- `the-caret-is-drawn-where-it-was-placed` and `the-caret-lands-where-the-click-was`: all of `inkLeft`, `inkRight`, `inkSpan`,
  `caretAfterClickNearStart`, `caretAfterClickPastEnd`, `strokeGained`, `strokeLost`, `fractionNearStart` are equal between v8 and v16 in each
  browser, in all three rounds (Chrome: `inkSpan 423`, `caretAfterClickNearStart 132`, `strokeGained 19`, `strokeLost 14`;
  Firefox: `inkSpan 526`, `caretAfterClickNearStart 164`, `strokeGained 24`, `strokeLost 19`).
- The only other `observed` fields that moved between rounds within a profile were timings (`seconds`) and `savedBytes`
  (`12896`/`12898` on v8, `12898`/`12899` on v16, in the boundary check).

## Not measured here

- Whether any difference above matters, and why the Chrome boundary cell takes the `worker-failure` branch on v16: this README does not diagnose.
  No diagnostic run, mutation run or `--refusal-diagnostic` run was made.
- The WASM shakedown, the CJK tile comparison and the freeze. Baseline noise beyond the 3 rounds of each profile.
- Firefox is not a clean baseline on this machine (the FAIL cell above is on both profiles); a comparison here is v16 Firefox against this
  morning's v8 Firefox, not against a known-good Firefox run.
