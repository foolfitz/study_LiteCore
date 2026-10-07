# Product-path net on the candidate page `b003534c...`: `e2-editor-v16` against `e2-editor-v8`, same runner, interleaved

This is a shakedown. It is not counted and nothing is bound to it. The predictions this run was judged against are in `PREDICTION.md` in this
directory (committed at `8e43c087`, before the first run, not edited). Everything below is read from the 12 report files by `judge.py`;
`judge-output.txt` is its raw output. Re-run the judgement with one line:

```
python3 findings/evidence/v16-shakedown/product-path-b003534c/judge.py
```

(`judge.py --dir <other dir>` reads another directory; `judge-selftest.txt` is the reader run on a scratch copy of the previous directory's
reports with two cells edited to FAIL, to show it can go red: it printed 2 red cells and P3 MISS; with a 41-check report it stopped with exit status 4.)

## What was run

Chain driver `chain.sh` is `../product-path-web-page/chain.sh` with only the `DIR=` line changed (checked with `diff`). From `wasm_sdk_probe/`, one run at a time,
order Chrome v8 r1, v16 r1, v8 r2, v16 r2, v8 r3, v16 r3, then the same six on Firefox. v8 arm: no profile flag. v16 arm: `--candidate-profile e2-editor-v16`.
Default `--timeout`, no other flag, no `--write` anywhere, no `make`. `chain.log` has each START (with the exact command) and END (with exit code) line.

- Runner `wasm_sdk_probe/tools/run_e2_c_product_path.py`: sha256 `b52779e498ae33cffea5970ad9a6f8cdf49b03240ef1211905ebc68f975c940c` before (`runner-sha-before.txt`),
  and the same after (`runner-sha-after.txt`, last line of `chain.log`). It is the value PREDICTION.md names.
- Before starting: `ps -ef` saved (`ps-before.txt`); no `run_*`, `geckodriver` or `chromedriver` process was running. After: `ps-after.txt`; none left.
- Chain start 2026-10-07 19:46:00 +08:00, `CHAIN DONE` 21:02:53 +08:00. Exit codes: Chrome (6 runs) 0; Firefox (6 runs) 1 (the single FAIL cell
  `an-inline-format-reaches-a-selection`, on both profiles, makes `ok: false`). All 12 runs wrote a report; the missing-report ABORT never fired.
- `chain.log` has no WAIT line (nothing else was running when a run was about to start). The overlap sampler (any other `tools/run_*` process, every 10 s) never saw one:
  `overlap-sampler.log` does not exist.
- Chrome 151.0.7922.169, Firefox 157.0 (snap `firefox/8995`; same main process pid 777820 in `ps-before.txt` and `ps-after.txt`; Chrome main pid 1090372 likewise).
- `sha256sum` of `dist/e2-editor-app.js` = `e97d6e03...` and `web/e2-editor-app.js` = `a3fd9ac1...` both before the chain and after it (unchanged; the full values are in PREDICTION.md).
- Each `*.stdout.txt` equals its `*.json` (parsed and compared, 12 of 12). `chain.stdout.txt` / `chain.stderr.txt` (output of the `chain.sh` shell itself) are empty.
- During the chain the main session committed once (`58c512cf`, a probe pre-registration); that commit is outside this directory and did not change the runner, `dist/` or `web/`.
- `git status --short` outside this directory showed nothing at the end.

## Check count

All 12 reports carry exactly 42 checks (`report["checks"]`, each with `id` and `outcome` in `PASS` / `FAIL` / `NOT_ESTABLISHED`), the same ids in the same order. No other outcome value occurs.

## P1: complete / liveness.lastState / pageErrors

| report | started | completed | PASS | FAIL | NE | ok | complete | lastState | pageErrors | exit |
|---|---|---|---|---|---|---|---|---|---|---|
| `e2-editor-v8-chrome-r1.json` | 19:46:00 | 19:52:52 | 40 | 0 | 2 | True | True | ready | None | 0 |
| `e2-editor-v16-chrome-r1.json` | 19:52:52 | 19:59:17 | 40 | 0 | 2 | True | True | ready | None | 0 |
| `e2-editor-v8-chrome-r2.json` | 19:59:17 | 20:06:09 | 40 | 0 | 2 | True | True | ready | None | 0 |
| `e2-editor-v16-chrome-r2.json` | 20:06:09 | 20:12:33 | 40 | 0 | 2 | True | True | ready | None | 0 |
| `e2-editor-v8-chrome-r3.json` | 20:12:33 | 20:19:25 | 40 | 0 | 2 | True | True | ready | None | 0 |
| `e2-editor-v16-chrome-r3.json` | 20:19:26 | 20:25:49 | 40 | 0 | 2 | True | True | ready | None | 0 |
| `e2-editor-v8-firefox-r1.json` | 20:25:49 | 20:31:53 | 31 | 1 | 10 | False | True | ready | None | 1 |
| `e2-editor-v16-firefox-r1.json` | 20:32:03 | 20:38:01 | 31 | 1 | 10 | False | True | ready | None | 1 |
| `e2-editor-v8-firefox-r2.json` | 20:38:12 | 20:44:13 | 30 | 1 | 11 | False | True | ready | None | 1 |
| `e2-editor-v16-firefox-r2.json` | 20:44:23 | 20:50:21 | 30 | 1 | 11 | False | True | ready | None | 1 |
| `e2-editor-v8-firefox-r3.json` | 20:50:31 | 20:56:34 | 30 | 1 | 11 | False | True | ready | None | 1 |
| `e2-editor-v16-firefox-r3.json` | 20:56:44 | 21:02:43 | 31 | 1 | 10 | False | True | ready | None | 1 |

12 of 12 reports: `complete` True, `liveness.lastState` `ready`, `pageErrors` None (printed as `None` by Python; `null` in the JSON).

**P1: HIT.**

## P2: served page and candidate fields

| report | servedShell.entrypointSha256 | candidateSource.page | sha256BeforeRepoint | distPageWasTheSame | restOfShellEqualsSource | candidateCutover.pageSha256 | profile | pinBefore | pinAfter |
|---|---|---|---|---|---|---|---|---|---|
| `v8-chrome-r1` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` | (no key) | | | | (no key) | | | |
| `v16-chrome-r1` | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | `web/e2-editor-app.js` | `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc` | False | True | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | e2-editor-v16 | `4a2710bba1ef07d9` | `ad3f68bb85f94589` |
| `v8-chrome-r2` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` | (no key) | | | | (no key) | | | |
| `v16-chrome-r2` | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | `web/e2-editor-app.js` | `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc` | False | True | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | e2-editor-v16 | `4a2710bba1ef07d9` | `ad3f68bb85f94589` |
| `v8-chrome-r3` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` | (no key) | | | | (no key) | | | |
| `v16-chrome-r3` | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | `web/e2-editor-app.js` | `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc` | False | True | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | e2-editor-v16 | `4a2710bba1ef07d9` | `ad3f68bb85f94589` |
| `v8-firefox-r1` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` | (no key) | | | | (no key) | | | |
| `v16-firefox-r1` | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | `web/e2-editor-app.js` | `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc` | False | True | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | e2-editor-v16 | `4a2710bba1ef07d9` | `ad3f68bb85f94589` |
| `v8-firefox-r2` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` | (no key) | | | | (no key) | | | |
| `v16-firefox-r2` | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | `web/e2-editor-app.js` | `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc` | False | True | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | e2-editor-v16 | `4a2710bba1ef07d9` | `ad3f68bb85f94589` |
| `v8-firefox-r3` | `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f` | (no key) | | | | (no key) | | | |
| `v16-firefox-r3` | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | `web/e2-editor-app.js` | `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc` | False | True | `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` | e2-editor-v16 | `4a2710bba1ef07d9` | `ad3f68bb85f94589` |

Every v8 report:
`servedShell.entrypointSha256 == e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f`, and no `candidateSource` / `candidateCutover` key. Every v16 report:
`candidateSource.page == "web/e2-editor-app.js"`, `sha256BeforeRepoint == a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc`, `distPageWasTheSame == false`,
`restOfShellEqualsSource == true`, and `servedShell.entrypointSha256 == candidateCutover.pageSha256 == b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d`.
The served shell is the same single value inside each arm: bundle `e2/editor-shell-v2-bundle-v55.json`, `declaredSha256` `2470765ae19ced01...`, `missing: []`;
v8 `servedSha256` `5bfc7642f5d1f8ec...`, v16 `81f2a7805d140f0e...`; `differingPaths` for v8 are the client and session files, for v16 the same two plus `web/e2-editor-app.js`.

**P2: HIT.**

## P3: spec 23 verdict, every check x 2 browsers, 3 rounds per arm

Rule applied per (check, browser) cell (as written in the task and PREDICTION.md): v8 all PASS -> v16 must be all PASS; v8 has a FAIL -> v16 FAIL rounds <= v8 FAIL rounds;
v8 has NE and no FAIL -> v16 has no FAIL. `NE` = NOT_ESTABLISHED.

| check id | chrome v8 | chrome v16 | chrome | firefox v8 | firefox v16 | firefox |
|---|---|---|---|---|---|---|
| `product-save-button-writes-a-real-odt` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `every-ime-commit-reaches-the-document` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `ctrl-c-asks-the-engine` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `product-insert-button-inserts-what-the-field-holds` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `product-undo-button-reverses-the-last-edit` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `product-redo-button-restores-what-undo-removed` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `bulleting-a-blank-line-does-not-demand-a-rollback` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `notice-action-recovers-the-session` | 3 NE | 3 NE | ok | 3 NE | 3 NE | ok |
| `backspace-and-arrows-reach-the-document` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-keyboard-reaches-the-document` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `ctrl-v-reaches-the-document` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-caret-is-drawn-where-it-was-placed` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-caret-lands-where-the-click-was` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `bold-can-be-turned-off-again` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `a-format-that-worked-is-not-reported-as-failed` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `a-failed-format-does-not-block-the-session` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `format-a-paragraph-changes-that-paragraph` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `cut-removes-the-selected-text` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `a-refused-action-is-reported-and-changes-nothing` | 3 NE | 3 NE | ok | 3 NE | 3 NE | ok |
| `every-inline-format-reaches-the-document` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `clear-format-removes-every-inline-format` | 3 PASS | 3 PASS | ok | 1 PASS, 2 NE | 2 PASS, 1 NE | ok |
| `formatting-survives-the-next-paragraph-break` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-toolbar-gives-the-keyboard-back` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `the-edit-buttons-do-what-they-say` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-open-button-opens-the-file-chooser` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `an-aborted-gesture-stops-selecting` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `caret-follows-the-text-you-type` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-vertical-arrows-move-the-caret` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `the-composition-you-are-typing-is-visible` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `the-document-region-says-why-it-is-empty` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-projection-is-placed-where-the-document-is` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `an-inline-format-reaches-a-selection` | 3 PASS | 3 PASS | ok | 3 FAIL | 3 FAIL | ok |
| `the-page-agrees-with-the-engine-about-the-selection` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `the-canvas-follows-a-window-that-changed-size` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-sample-picker-opens-a-second-document` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `product-opens-a-document-the-user-chose` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-enter-key-reaches-the-document` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |
| `a-long-document-is-drawn-or-the-product-says-it-is-not` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `the-canvas-follows-a-document-that-grew` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `editing-a-long-document-stays-responsive` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `recovery-returns-what-the-product-promised` | 3 PASS | 3 PASS | ok | 3 PASS | 3 PASS | ok |
| `a-boundary-arrow-press-does-not-cost-the-work` | 3 PASS | 3 PASS | ok | 3 NE | 3 NE | ok |

Cells judged: 84. **Section-23 red cells: 0.**

**P3: HIT.**

## P4: count equality (descriptive, not judged)

- Cells with equal v8/v16 counts: **83 of 84**. The one cell that differs is Firefox `clear-format-removes-every-inline-format`: v8 = 1 PASS + 2 NE, v16 = 2 PASS + 1 NE
  (PASS/NE only; no FAIL on either side). This is the cell PREDICTION.md named.
- Firefox `an-inline-format-reaches-a-selection`: 3 FAIL on v8 and 3 FAIL on v16 (Chrome: 3 PASS on both).
- Firefox NE totals by round (from the runs table): v8 10, 11, 11; v16 10, 11, 10.

Firefox `clear-format-removes-every-inline-format`, `observed.allOnWhenTyped` per round (bold / italic / underline / strikethrough) and `observed.everyFormatWasOn`:

| arm | round | outcome | allOnWhenTyped | everyFormatWasOn |
|---|---|---|---|---|
| v8 | r1 | PASS | True / True / True / True | True |
| v8 | r2 | NOT_ESTABLISHED | False / True / True / True | False |
| v8 | r3 | NOT_ESTABLISHED | True / True / False / True | False |
| v16 | r1 | PASS | True / True / True / True | True |
| v16 | r2 | NOT_ESTABLISHED | True / False / False / False | False |
| v16 | r3 | PASS | True / True / True / True | True |

`allOnWhenTyped` was not all-true in 2 of 3 rounds on v8 and in 1 of 3 rounds on v16; in the 3 PASS rounds all four were true. Chrome: 3 PASS on both profiles.
This README does not say why.

**P4: HIT** (as worded: at least 83 of 84 equal, the differing cell is that Firefox cell, and the Firefox selection cell FAILs on both profiles).

## Predictions

| prediction | result |
|---|---|
| P1: all 12 reports `complete: true`, `liveness.lastState: ready`, `pageErrors: null` | HIT |
| P2: v16 candidate fields and `b003534c...` on all 6 v16 reports; `e97d6e03...` on all 6 v8 reports | HIT |
| P3: spec 23 verdict holds in every cell | HIT (0 red of 84) |
| P4: at least 83 of 84 counts equal; a differing cell is Firefox `clear-format...`; Firefox `an-inline-format...` FAILs on both | HIT (83 of 84; the one is that cell) |

Not measured here: anything about `observed` fields beyond the ones listed above (the earlier README's "equal counts, different observed" comparison was not repeated), mutation runs,
`--refusal-diagnostic` runs, the WASM shakedown, the CJK tile comparison, the freeze, or noise beyond 3 rounds per arm.

## Files

12 reports `e2-editor-{v8,v16}-{chrome,firefox}-r{1,2,3}.json` with matching `.stdout.txt` and `.stderr.txt` (step lines), `chain.sh`, `chain.log`, `chain.stdout.txt`, `chain.stderr.txt`,
`ps-before.txt`, `ps-after.txt`, `runner-sha-before.txt`, `runner-sha-after.txt`, `judge.py`, `judge-output.txt`, `judge-selftest.txt`, `PREDICTION.md`, this README.
