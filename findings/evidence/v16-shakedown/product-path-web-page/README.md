# v16 on the page the cutover ships: product-path net, `e2-editor-v16` against `e2-editor-v8`, same runner, interleaved

This is a shakedown. It is not counted and nothing is bound to it. The predictions this run was made against are in
`PREDICTION.md` in this directory (written before the first run, not edited).

No tracked file was edited. The only files created are in this directory: 12 reports (`*.json`), 12 `*.stdout.txt` (the runner prints
the same JSON it writes with `--out`; checked equal for all 12), 12 `*.stderr.txt` (step lines only), `chain.log`, `chain.sh` (the loop
that drove the chain, copied here), `ps-before.txt` / `ps-after.txt`, `runner-sha-before.txt` / `runner-sha-after.txt`, this README.
`git status --short` after the last run showed this directory and one untracked file that is not part of this task
(`wasm_sdk_probe/editor-shell-v2/tests/page-render-disposed.test.mjs`, created by the main session while the chain was running).

**Both arms were run in this chain.** Unlike the earlier v16 shakedown (`../product-path/README.md`), which compared v16 against v8 reports
taken the same morning with runner `5900ce87...`, the v8 reports here were taken with the same runner file as the v16 reports, interleaved
with them (order: v8 r1, v16 r1, v8 r2, v16 r2, v8 r3, v16 r3 on Chrome, then the same six on Firefox).

## Commands

From `wasm_sdk_probe/`, strictly sequential. `<B>` is `chrome` or `firefox`, `<N>` is 1, 2, 3. The loop waited for any process matching
`run_e2_c_product_path|run_merge|geckodriver|chromedriver` to be absent before each run; `chain.log` has each start and end line with
the exact command and exit code.

```
python3 tools/run_e2_c_product_path.py --browser <B> --out <DIR>/e2-editor-v8-<B>-r<N>.json > <DIR>/e2-editor-v8-<B>-r<N>.stdout.txt 2> <DIR>/e2-editor-v8-<B>-r<N>.stderr.txt
python3 tools/run_e2_c_product_path.py --browser <B> --candidate-profile e2-editor-v16 --out <DIR>/e2-editor-v16-<B>-r<N>.json > <DIR>/e2-editor-v16-<B>-r<N>.stdout.txt 2> <DIR>/e2-editor-v16-<B>-r<N>.stderr.txt
```

`<DIR>` = `/home/jiajun/LibreOffice/study_LiteCore/findings/evidence/v16-shakedown/product-path-web-page`. Default `--timeout`; no other flags.
`build_cutover_page.py` was run once WITHOUT `--write` (`--profile e2-editor-v16`) to print the sha for P2; it wrote nothing. No `make`. Nothing under
`wasm_sdk_probe/dist/` or `wasm_sdk_probe/web/` was written. The profile `dist/profiles/e2-editor-v16/probe.wasm` sha256 starts `ad3f68bb85f94589`,
which equals `pinAfter` in every v16 report. No run refused to start; every run wrote a report. A background sampler (every 10 s, `pgrep -af 'tools/run_'`
excluding the product-path runner) never saw another `tools/run_*` process during the chain (it would have created `overlap-sampler.log`; that file does not exist).

Chain start 2026-10-07 16:40:23 +08:00, end 17:57:26 +08:00 (`chain.log`). Exit codes: Chrome (all 6 runs) = 0; Firefox (all 6 runs) = 1
(`ok: false`, because of the single FAIL cell `an-inline-format-reaches-a-selection`, present on both profiles). Every run: `complete: true`,
`liveness.lastState: ready`, `pageErrors: null`, `knownRed: {}`, `staleKnownRedDeclarations: []`.

## Environment

- Google Chrome 151.0.7922.169; Firefox 157.0 (snap, `firefox/8995`; `ps` before and after shows the same snap revision). Versions from
  `google-chrome --version` / `firefox --version` before the first run.
- Runner `wasm_sdk_probe/tools/run_e2_c_product_path.py`, sha256 `e31901440c75dc0ccf17b94ae97c92e21461e881e86378c5a5fde89d80079ebd`
  **before the first run** and `e31901440c75dc0ccf17b94ae97c92e21461e881e86378c5a5fde89d80079ebd` **after the last run** (unchanged; prefix `e31901440c75dc0c`
  as expected for commit `3ab4f04a`; `runner-sha-before.txt`, `runner-sha-after.txt`, and the first and last lines of `chain.log`).
- Served shell, all 12 reports: bundle `e2/editor-shell-v2-bundle-v55.json`, `declaredSha256`
  `2470765ae19ced019b423b55e856ef8d60759ee878d56ff835e6e9387b62167c`, `missing: []`, `differsOnlyInTheEntrypoint: false`.
  - v8 reports (6): `servedSha256` `5bfc7642f5d1f8ec...` (same in all 6), `differingPaths`: `editor-shell-v2/narrow-editor-v2-client.js`,
    `editor-shell-v2/narrow-editor-v2-session.js`; `entrypoint` `web/e2-editor-app.js` with `entrypointSha256`
    `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` (equals `sha256sum wasm_sdk_probe/dist/e2-editor-app.js` now). The reports have no
    `candidateSource` and no `candidateCutover` key at all. The stderr line says `STARTED page=shipped`.
  - v16 reports (6): `servedSha256` `c34f85d5d9141493...` (same in all 6), `differingPaths`: the same two plus `web/e2-editor-app.js`;
    `entrypointSha256` `3cf0133033e449ebd553c0ee64e7cbe2ef411e33c6013a4964c2b6123cf11b8f`. The stderr line says `STARTED page=candidate:e2-editor-v16`.
  - `differingPaths` is "red by design" for the first two entries (known item of the runbook); the third is the repointed candidate entrypoint.
    The runner did not refuse on it.
- `candidateSource` (identical in all 6 v16 reports): `page: "web/e2-editor-app.js"`,
  `sha256BeforeRepoint: 7834e5c2481e97d3223fff32019568dc70fa82f28477b489da2718b683132167` (equals `sha256sum wasm_sdk_probe/web/e2-editor-app.js` now),
  `distPageWasTheSame: false`, `restOfShellEqualsSource: true`.
- `candidateCutover` (identical in all 6 v16 reports): `profile: e2-editor-v16`,
  `pageSha256: 3cf0133033e449ebd553c0ee64e7cbe2ef411e33c6013a4964c2b6123cf11b8f`, `pinBefore: 4a2710bba1ef07d9`, `pinAfter: ad3f68bb85f94589`.
  `python3 tools/build_cutover_page.py --profile e2-editor-v16` (no `--write`), run before the chain, printed
  `pageSha256 3cf0133033e449ebd553c0ee64e7cbe2ef411e33c6013a4964c2b6123cf11b8f`, `pin 4a2710bba1ef07d9 -> ad3f68bb85f94589`, `unchanged False`, `written no`.

Desktop notes: processes that are not mine, in `ps` before the first run (16:40:01) and again after the last (17:57:45): Firefox pid 777820 and its
`crashhelper` 778346 (both up since Oct 6 20:57:20), Chrome pid 1090372 (no flags, up since Oct 7 12:00:19) with `extension-host` 1090982 and
`claude --chrome-native-host` 1091012 (both 12:00:50). Those main processes are the same pids in both listings. Their child processes changed in between
(one Firefox content process gone, one added; Chrome renderer process 1216928 gone, four new renderers started 17:56:50-17:56:52; a `claude` native-binary process, pid 1220909, started 16:40:36 under the VS Code extension); I did not touch any of them and `ps` was
not sampled during the chain, so nothing is claimed about the interval. After the last run no `chromedriver`, `geckodriver`, `run_e2*` or `--headless` process was left (`ps-after.txt`).

## Runs

Times are the report's own `startedAt` / `completedAt` (+08:00, 2026-10-07); `chain.log` END lines are about 10 s later because they include browser teardown.
`exit` is the process exit code from `chain.log`.

| report | started | completed | PASS | FAIL | NE | ok | complete | last state | pageErrors | exit |
|---|---|---|---|---|---|---|---|---|---|---|
| `e2-editor-v8-chrome-r1.json` | 16:40:24 | 16:47:15 | 40 | 0 | 2 | true | True | ready | null | 0 |
| `e2-editor-v16-chrome-r1.json` | 16:47:15 | 16:53:40 | 40 | 0 | 2 | true | True | ready | null | 0 |
| `e2-editor-v8-chrome-r2.json` | 16:53:40 | 17:00:32 | 40 | 0 | 2 | true | True | ready | null | 0 |
| `e2-editor-v16-chrome-r2.json` | 17:00:32 | 17:06:56 | 40 | 0 | 2 | true | True | ready | null | 0 |
| `e2-editor-v8-chrome-r3.json` | 17:06:57 | 17:13:48 | 40 | 0 | 2 | true | True | ready | null | 0 |
| `e2-editor-v16-chrome-r3.json` | 17:13:48 | 17:20:14 | 40 | 0 | 2 | true | True | ready | null | 0 |
| `e2-editor-v8-firefox-r1.json` | 17:20:14 | 17:26:18 | 31 | 1 | 10 | false | true | ready | null | 1 |
| `e2-editor-v16-firefox-r1.json` | 17:26:28 | 17:32:29 | 30 | 1 | 11 | false | true | ready | null | 1 |
| `e2-editor-v8-firefox-r2.json` | 17:32:40 | 17:38:42 | 30 | 1 | 11 | false | true | ready | null | 1 |
| `e2-editor-v16-firefox-r2.json` | 17:38:52 | 17:44:53 | 30 | 1 | 11 | false | true | ready | null | 1 |
| `e2-editor-v8-firefox-r3.json` | 17:45:03 | 17:51:05 | 30 | 1 | 11 | false | true | ready | null | 1 |
| `e2-editor-v16-firefox-r3.json` | 17:51:16 | 17:57:16 | 30 | 1 | 11 | false | true | ready | null | 1 |

`ok: false` on every Firefox run comes from the single FAIL cell `an-inline-format-reaches-a-selection`. Firefox here has no CDP, so 10-11 of the 42 checks
abstain (NOT_ESTABLISHED). The Firefox NE count by round is v8: 10, 11, 11; v16: 11, 11, 11. The one cell that moves it is
`clear-format-removes-every-inline-format` (see the next section).

## Every check, over 3 rounds each

Counts are over the 3 rounds of that arm. `NE` = NOT_ESTABLISHED (not a pass). The last column says `DIFF (<browser>)` for every row where the v16 count differs
from the v8 count in that browser, and `same` otherwise. The check list is the same 42 ids in the same order in all 12 reports.

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
| `clear-format-removes-every-inline-format` | 3 PASS | 1 PASS, 2 NE | 3 PASS | 3 NE | **DIFF (firefox)** |
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
| `recovery-returns-what-the-product-promised` | 3 PASS | 3 PASS | 3 PASS | 3 PASS | same |
| `a-boundary-arrow-press-does-not-cost-the-work` | 3 PASS | 3 NE | 3 PASS | 3 NE | same |

Rows flagged `DIFF`: **1** (`clear-format-removes-every-inline-format`, Firefox). Chrome: 42 of 42 checks have equal counts. Firefox: 41 of 42 checks have equal counts.

## The differing row, quoted from the reports

`clear-format-removes-every-inline-format`, Firefox only.

| arm | round | outcome | `observed.allOnWhenTyped` (bold / italic / underline / strikethrough) | `observed.everyFormatWasOn` |
|---|---|---|---|---|
| v8 | r1 | PASS | true / true / true / true | true |
| v8 | r2 | NOT_ESTABLISHED | false / false / false / false | false |
| v8 | r3 | NOT_ESTABLISHED | true / false / true / true | false |
| v16 | r1 | NOT_ESTABLISHED | true / true / true / false | false |
| v16 | r2 | NOT_ESTABLISHED | true / false / true / false | false |
| v16 | r3 | NOT_ESTABLISHED | true / false / true / false | false |

In all six rounds, the other `observed` fields are equal: `buttonFound: true`, `toast: "已清除粗體、斜體、底線、刪除線"`, `allOn: {found: true, bold: false, italic: false,
underline: false, strikethrough: false}` and `cleared: {found: true, carrier: "span", bold: false, italic: false, underline: false, strikethrough: false}`.

The NE text, identical in all five NE reports (`notEstablished`):

> the four formats were not all ON before the clear, so what the button did cannot be read: a clear that removes nothing and a clear that never ran look identical from here. The precondition is read from MKALLON's OWN save rather than from the cleared document, because asking a cleared document whether every format WAS on asks it about a moment it no longer records -- which is why this looked unbuildable under finding 064, now retracted

The `oracle` text (identical in all six): "all four inline formats are turned ON and a marker committed under them, the product's own #clear-format button is clicked, and a second marker is committed after it. The first marker must carry all four in the saved ODT and the second must carry none -- clearing an already-clear document is a no-op that a broken button would pass".

For reference only (a different runner file, `5900ce87...`, and the page in `dist/`; not re-run here): `../product-path/README.md` (v8 reports from the v15 shakedown of 2026-10-07, v16 reports of the same day) recorded this cell as 3 NE on Firefox for v8 and 3 NE on Firefox for v16.
This README does not diagnose the difference.

## Cells that carry text, listed for completeness (equal counts)

- Firefox, both profiles, 3 of 3 rounds: `an-inline-format-reaches-a-selection` FAIL. `observed.selectedText: ""` and `wasBoldBefore: false` in all six reports;
  `bandsAvailable` 20, 21, 20 (v8) and 20, 20, 20 (v16). `observed.drag` (v16 r1) `{x1: 0.12883, x2: 0.18567, y: 0.38942}`, `buttonAfterDrag: {disabled: false, title: ""}`, `toast: ""`.
- Chrome, both profiles, 3 of 3 rounds: `notice-action-recovers-the-session` NE and `a-refused-action-is-reported-and-changes-nothing` NE (their `why` texts are in the reports and are not repeated here).
- Firefox, both profiles, 3 of 3 rounds NE: `a-boundary-arrow-press-does-not-cost-the-work`, `a-refused-action-is-reported-and-changes-nothing`, `an-aborted-gesture-stops-selecting`,
  `cut-removes-the-selected-text`, `notice-action-recovers-the-session`, `the-composition-you-are-typing-is-visible`, `the-enter-key-reaches-the-document`,
  `the-page-agrees-with-the-engine-about-the-selection`, `the-toolbar-gives-the-keyboard-back`, `the-vertical-arrows-move-the-caret` (10 cells), plus `clear-format-removes-every-inline-format` in the rounds listed above.
  The boundary cell's `why` on Firefox (v16 r1): "no CDP (so a real arrow key cannot be delivered), or this profile does not offer `move-line-up`. On a profile without it the page leaves the key to the browser and there is no gesture to protect".
- `recovery-returns-what-the-product-promised` is 3 PASS on both profiles in both browsers in this chain: `finding038Reproduced: true` and `stateAfterDrag: "busy"` in all 12 reports, and no `fallbackInducer` key in any of them. (The earlier v16 README recorded one NE round per profile in Firefox for this cell; none occurred here.)

## Equal counts, different `observed` (found by comparing the reports, not diagnosed)

Method: for every check and every browser, every flattened scalar field of `observed` that has one single value across the three v8 rounds and one single value across
the three v16 rounds, and the two values differ. Rows where the count differs (the DIFF row above) are not covered by this method because their `observed` fields vary within an arm. Result:

- Both browsers, `the-vertical-arrows-move-the-caret` (`offered.profile`), `an-inline-format-reaches-a-selection` (`profile`), and on both browsers
  `a-boundary-arrow-press-does-not-cost-the-work` (`offered.profile`): the profile name string (`e2-editor-v8` vs `e2-editor-v16`). Nothing else.
- Chrome, `a-boundary-arrow-press-does-not-cost-the-work` (3 PASS on both profiles). 23 fields (including the profile name above), all identical across the three rounds within each profile:

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

  On both profiles `verdict` is `{ok: true, B1: true, B2: true, B3: true, B4: true}` and `workCameBack: true` in all three rounds. This is the same set of differing fields that
  `../product-path/README.md` recorded for the same cell against the page in `dist/`; it is not new here.
- Chrome, `every-inline-format-reaches-the-document`: `arms[7].formatPressWaitedMs` is 403 in all three v8 rounds and 402 in all three v16 rounds (a timing field).
- Firefox, `a-long-document-is-drawn-or-the-product-says-it-is-not` (`arms[5].scanSettledAfterTries`) and `the-canvas-follows-a-document-that-grew` (`scanSettledAfterTries`):
  3 in all three v8 rounds, 2 in all three v16 rounds.
- `the-caret-is-drawn-where-it-was-placed` and `the-caret-lands-where-the-click-was`: `inkLeft`, `inkRight`, `inkSpan`, `caretAfterClickNearStart`, `caretAfterClickPastEnd`,
  `strokeGained`, `strokeLost`, `fractionNearStart` are equal between v8 and v16 in each browser, in all three rounds (Chrome: `inkSpan 423`, `caretAfterClickNearStart 132`,
  `strokeGained 19`, `strokeLost 14`; Firefox: `inkSpan 526`, `caretAfterClickNearStart 164`, `strokeGained 24`, `strokeLost 19`).

## Predictions

Judged by the wording in `PREDICTION.md`.

- **P1: HIT.** "All 12 reports `complete: true`, `liveness.lastState: ready`, `pageErrors: null`." 12 of 12 reports have `complete: true`, `liveness.lastState: "ready"`, `pageErrors: null`
  (Runs table: every row `true` / `ready` / `null`).
- **P2: HIT.** "Every v16 report has `candidateSource.page == "web/e2-editor-app.js"`, `candidateSource.distPageWasTheSame == false`, and `candidateCutover.pageSha256 ==
  3cf0133033e449ebd553c0ee64e7cbe2ef411e33c6013a4964c2b6123cf11b8f`, which is what `tools/build_cutover_page.py --profile e2-editor-v16` prints at `3ab4f04a`; `servedShell.entrypointSha256` equals it."
  6 of 6 v16 reports: `candidateSource.page` is `web/e2-editor-app.js`, `distPageWasTheSame` is `false`, `candidateCutover.pageSha256` is the full string
  `3cf0133033e449ebd553c0ee64e7cbe2ef411e33c6013a4964c2b6123cf11b8f`, `servedShell.entrypointSha256` is the same string, and `build_cutover_page.py --profile e2-editor-v16` printed the same `pageSha256`.
  The runner sha was `e31901440c75dc0c...` before and after. (The old runner's `cc523c9c...` appears in none of the 12 reports.)
- **P3: MISS.** "For each of the 42 checks, per browser, the v16 outcome counts equal the v8 outcome counts." Chrome: 42 of 42 equal. Firefox: 41 of 42 equal; the one that is not is
  `clear-format-removes-every-inline-format`, v8 = 1 PASS + 2 NE, v16 = 3 NE (see "The differing row"). 83 of 84 (check x browser) cells equal, 1 differs.
  PREDICTION.md says what a P3 miss means (a cell differs; not by itself a defect; to be diagnosed before shell generation v56 is frozen). This README does not diagnose it.

## Not measured here

- Why the Firefox `clear-format-removes-every-inline-format` cell differs, and whether it would differ with more rounds (3 rounds per arm; the precondition in that cell
  is a function of what the page and the browser did while typing, and the reports record only the four booleans above). No diagnostic run, mutation run or `--refusal-diagnostic` run was made.
- Whether any difference above matters. The arms for paragraph merge, refusal wording and the longer BUSY budget: PREDICTION.md says it has not read every arm;
  this README does not say whether any of the 42 checks reaches those paths.
- The WASM shakedown, the CJK tile comparison and the freeze. Baseline noise beyond 3 rounds of each profile.
- Firefox is not a clean baseline on this machine (the FAIL cell above is on both profiles).
