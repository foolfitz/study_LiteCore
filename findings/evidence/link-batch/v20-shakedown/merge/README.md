# v20 merge shakedown on WASM (task 2026-10-14e, Part B)

The existing merge runner `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py` (sha256 `73b2e9ff4b1e6fbe…`, the same bytes as v19's count; not edited) run with `--candidate-profile e2-editor-v20`, Chrome then Firefox, one runner at a time. **A shakedown, not a count:** `BINDING` in the runner still holds v19's values, so every report says `"counted": false` (seven of the nine bound values differ from it: wasm, worker, session, shell, html, page, page source). Nothing under `tools/`, `web/`, `dist/`, `editor-shell*/`, `sdk/`, `src/`, the `Makefile` or the host was touched. The prediction was committed first (`PREDICTION.md`, commit `83ea8eb8`).

## Result in four lines

1. **Everything behaves as on v19 and v18 except C29 and C30, which now complete `verified-boundary-noop`** instead of `refused` / `nothing-selected` (C, spec §10.5). Both browsers, both rounds: 4 records per browser. The runner records `pass: false` for exactly those 4 records, because its `expectation()` still maps R0c's `nothing-selected` to a refusal. It is the expected effect of C, reported verbatim below. Not a product red; the runner was not edited (§34).
2. Every other record passes: Chrome 52/56 and Firefox 52/56 in the shakedown, the same 52/56 in the control; M2-1b 20/20; M2-4 105/105 `verified-key-undo`, 0 slow presses. No `runner-error`, no `重繪失敗` toast, no `teardownError`, every stderr empty, no test browser alive after any step.
3. `--pair`: 56 pairs, `sameOrder: true`, exit 1 in both browsers, because **one pair each differs in `toastsAtEnd` only** (Chrome C10 r2, Firefox C03 r2): `已存出 14.2 KB` against `已存出 14.3 KB`. That is v19's known cause (fable ruling §35, `findings/evidence/v19/x7-counted-m2/fable-ruling-control.md`: `dc:date` / `Rsid` change a byte or two per save, and the 14.25 KB rounding edge). The reader that tolerates it (`judge_counted_m2.py`) is bound to v19 and was not used. All other fields of those two pairs are equal.
4. Latency is where v19's was: M2-4 engine `keyToUndoMs` [min, median, max] = [30, 32, 33] ms (Chrome) and [30, 32, 33] ms (Firefox); v19 [30, 32, 36] and [30, 32, 33].

## Commands (as run, from `wasm_sdk_probe/`)

Per browser `B` in `chrome`, `firefox` (`chain.sh B`, detached; the log is `chain.log`). Precedents: `findings/evidence/v18/chain.sh` (shakedown, control and pair; the last shakedown-mode full-list run in the tree) and `findings/evidence/v19/chain.sh` (`m2-1b` and `m2-4`).

```
python3 tools/run_merge_wasm_shakedown.py --browser B --candidate-profile e2-editor-v20 --frame-cell --rounds 2 --out merge/shakedown-B.json
python3 tools/run_merge_wasm_shakedown.py --browser B --candidate-profile e2-editor-v20 --frame-cell --rounds 2 --control --out merge/control-B.json
python3 tools/run_merge_wasm_shakedown.py --pair merge/shakedown-B.json merge/control-B.json
python3 tools/run_merge_wasm_shakedown.py --browser B --mode m2-1b --candidate-profile e2-editor-v20 --out merge/m2-1b-B.json
python3 tools/run_merge_wasm_shakedown.py --browser B --mode m2-4  --candidate-profile e2-editor-v20 --out merge/m2-4-B.json
```

Not run: `--mode counted` (the same list as the shakedown at 3 rounds, without the frame cell), `--mode m2-1-red` (the v8 red case of a bound candidate), `--owner-document`. Steps 4 and 5 are modes of the same runner, taken from v19's X7 step list; they are uncounted here only because BINDING is v19's.

Pre-run records (`prechecks.txt`, written before each of the 8 steps): KWallet `Locked` was `b false` every time; `pgrep -c chrome` was 2 every time, and both are crashpad handlers of other desktop apps (`/opt/marktext/chrome_crashpad_handler`, `/opt/codex-desktop/chrome_crashpad_handler`), not test browsers; the listing of `probe_|check_m3|run_e2_c|run_merge|run_v20` was empty every time (no wait was needed, `chain.log` has 0 `WAIT` lines). `*.ps-before/after.txt.test-browsers` hold the by-command-line listing of CDP/geckodriver/marionette processes: empty after every step. `identity-at-start-B.txt` and `identity-at-end-B.txt` hold the same sha256 lines and the same HEAD (`83ea8eb8`) at start and end of each browser's chain: profile `313b08d5…` / `e6b8c74a…` / `478d0da1…` / `50aade86…`, page source `7815e16c…`, runner `73b2e9ff…`.

## Identity every report carries

| field | value (all 8 reports, both browsers) |
|---|---|
| `candidate.profile` | `e2-editor-v20` (`pinBefore` `1aafd4f9da42fd83`, `pinAfter` `313b08d5cb085897`) |
| `candidate.pageSha256` | `53019168651b6b4686f1baaba9aa75e0b566d02a3e2cc8a8e8ed4339f360bfd7` = what `tools/build_cutover_page.py --profile e2-editor-v20` prints (no `--write`) |
| `candidate.workerSha256` | `478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099` (the shipped worker; no instrumented worker here) |
| `restOfShellEqualsSource` | true |
| `runner` | `73b2e9ff4b1e6fbe` |
| `counted` | false |

## What each step printed

| step | Chrome 151 | Firefox 157 |
|---|---|---|
| shakedown (`--frame-cell --rounds 2`) | 56 records, `exit 0`, 12:53:38-13:07:50; 52 pass, 4 not pass (C29 and C30, two rounds each) | 56 records, `exit 0`, 13:26:34-13:41:26; same 52 / 4 |
| control | 56 records, `exit 0`, 13:07:51-13:21:41; 52 pass, the same 4 not pass. The control's `outcome` is `control` for every case (its observer keeps only caret and size); C29/C30 fail on the clauses the control still keeps: `generation`, `toastWindowClosed`, `onlyTheReopenToasts` (C29 also `checkpointRevision`) | 13:41:37-13:56:07; same 52 / 4 and same clauses |
| `--pair` | 56 pairs, `sameOrder` true, differ: C10 r2 (`toastsAtEnd` only); exit **1** | 56 pairs, `sameOrder` true, differ: C03 r2 (`toastsAtEnd` only); exit **1** |
| `m2-1b` | 20/20 `verified-key-undo`; engine `keyToUndoMs` min 30, median 30, max 31; runner 129.3 / 132.0 / 154.7 ms | 20/20; engine 30 / 30 / 30; runner 129.4 / 131.6 / 150.5 ms |
| `m2-4` | 105/105 `verified-key-undo`, comment `Delete paragraph`, 0 slow, all 11 clauses true, engine 30 / 32 / 33 ms, `toastsAtEnd` = `已存出 8.3 KB` | same; engine 30 / 32 / 33 ms |

(`compare-output.txt` is the full read, from `compare.py`, a descriptive script written for this directory; it decides nothing and its exit code carries no verdict. `compare-selfred-output.txt` is its own red case: fed v19's report in place of v20's it prints `RED profile / pageSha256 / workerSha256`.)

### The case table, against v19's counted run and v18's shakedown

Per case, the set of `(outcome, stage, keyPosted)` and of `pass` values, both browsers identical:

- 24 of 28 cases are the same as v19's counted run (the other four are C29 and C30, below, and F01 and F02, which v19's counted mode did not run: it takes no `--frame-cell`; they `refused` / `anchor-mismatch` / `keyPosted: false`, `pass: true`, as in v18's shakedown).
- 26 of 28 are the same as v18's shakedown (same list, same flags, same rounds). The two that differ are C29 and C30.
- M2-1 cases (20 `verified-key-undo` cases), C15 and C16 (`refused` / `key-deadline` / `keyPosted: true`), C17 (`refused` / `anchor-mismatch` / `false`), G01 (`verified-selection-delete`), Y01 and Y02: all as before.
- Kept documents: all 101 paragraph-text lists of the shakedown and all 101 of the control are identical to v18's, file for file, in both browsers (`kept documents` lines of `compare-output.txt`). That includes the documents saved after C29 and C30: with the marker typed elsewhere they read as the original plus the marker, the same text a v19 refusal-and-reopen produced.

## The arms that expected a `nothing-selected` refusal, verbatim

C29 (Backspace at the document start, `M01 plain alpha`) and C30 (Delete at the document end, `M29 last`), 2 rounds, both browsers. `spec["expected"]` is still `("refused", "nothing-selected", False)`. What the runner recorded:

- `outcome`: `verified-boundary-noop` (was `refused`); the response is `{"ok": true, "completion": "verified-boundary-noop", "code": null, "keyUndo": null, "mergeKey": null}`; `generation` `['1', '1']` (a refusal gives `['1', '2']`); `keyToResponseMs` Chrome 2255.2-2256.4, Firefox 2256.5-2258.2 ms (the 250 ms deadline plus the 2,000 ms window, as ARMS.md C1 predicted).
- `pass`: **false**. Clauses that are false: `outcome`, `stage`, `keyPosted`, `generation`, `toastWindowClosed`, `onlyTheReopenToasts` (C29 also `checkpointRevision`, both browsers, both rounds; C30 not). Not established: `noUnchanged`. Every one is a clause that presupposes a refusal and its reopen; none reports a changed or damaged document: the saved document equals original plus marker (`reopenedDocument` 27 paragraphs, sha `0b2940828b2e3c3b…` in all four records of each browser).
- The merge runner does not record `boundaryNoop.waitedMs` or the engine's selection after the completion; that is Part A's C1 arm. `toastWindow` is `{closed: false, generation: '1', toasts: []}`: no toast appeared, as C predicts.
- The control side is the same four records (its observer keeps only the caret and the size).

**Why the two steps took about 14 minutes instead of v18's 7:** the runner's refusal branch (`refusal = spec["expected"][0] == "refused"`) still calls `toast_window(..., limit=90)`, which waits for a reopen toast that a no-op never shows. Four records times 90 s is the extra six minutes in each of the shakedown and control steps. A consequence of the unedited expectation, not of the product (wall times from `chain.log`: Chrome 14m13s / 13m50s, Firefox 15m03s / 14m40s).

## Predictions (PREDICTION.md) against the outcome

| | outcome |
|---|---|
| P-a every case except C29/C30 as on v19 and v18 | HIT, both browsers |
| P-b C29/C30 `verified-boundary-noop`, `generation` `[1, 1]`, runner `pass: false`, 4 records per report | HIT |
| P-c pair 0 differ, exit 0 | **MISS** on the raw pair: 1 pair per browser differs in the KB figure of `toastsAtEnd` (v19's §35 cause; PREDICTION named it as the one acceptable reason) |
| P-d M2-4 105/105, engine near [30, 32, 36] / [30, 32, 33]; M2-1b 30-42 ms band | HIT: [30, 32, 33] both; M2-1b 30-31 and 30 |
| P-e no `重繪失敗`, no `runner-error`, no leftover browser | HIT |

## Deviations and things to know

- **`chain.sh` logged the wrong exit for Chrome's `--pair`.** In the first version of the script `$(ts)` came before `$?` in the `echo`, so `chain.log` says `END pair-chrome exit=0` while the command exited 1. Noticed after Chrome's chain, fixed (the code is captured first, and written to `pair-B.exit`) before Firefox started. Chrome's exit was re-derived by running `--pair` again, offline (`pair-chrome.rerun.stdout.txt`, byte-identical to `pair-chrome.stdout.txt`, exit 1 in `pair-chrome.exit`). The file `chain.sh` here is the fixed one; the committed prediction commit holds the first version.
- Nothing else in the run deviated; no step crashed, no report is missing, no mode was stopped.
- Not looked at: the trace windows (`keyTrace`, `presses[n].trace`) beyond their presence; Firefox's `ps-after` listings beyond being empty; the engine-side selection after a no-op (Part A's C1 arm measures that).
- This directory has no judge. Whether v20 may be bound and counted is the main session's, with the binding and the count chain (RUNBOOK-relink-v20 §4.2, §4.3). The runner's `expectation()` will have to be revisited by whoever binds v20: a counted run reads C29/C30 as M2-3 refusals and would fail on them. That is a spec/runner decision (§34), recorded here and not made.

## Files

`PREDICTION.md`, `chain.sh`, `chain.log`, `prechecks.txt`, `identity-at-{start,end}-{chrome,firefox}.txt`; per step `*.json` (report), `*.docs/` (kept documents), `*.stdout.txt`, `*.stderr.txt` (all empty), `*.ps-{before,after}.txt` and `.test-browsers`; `pair-{chrome,firefox}.{stdout.txt,exit}`, `pair-chrome.rerun.*`; `compare.py`, `compare-output.txt`, `compare-selfred-output.txt`.
