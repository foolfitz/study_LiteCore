# v68 second-pass candidate witness (task 2026-10-14k): 129-B is GREEN in both browsers, and the added latency clause (W2) passes

Facts only. Anything not checked is marked "unverified". Times are UTC unless stated. Task: `handoff/tasks/TASK-2026-10-14k-pre-v68-witness-second-pass.md` (repeats `handoff/tasks/TASK-2026-10-14g-pre-v68-witness.md`; criterion C2 of `handoff/tasks/TASK-2026-10-14h-finding-140-second-pass.md`). Executor: Sonnet 5.5. No shell generation was frozen, no `--write` mode was run, no `make` other than `e2-c-assets` was run, nothing under `web/`, `editor-shell*/`, `sdk/`, `src/`, the `Makefile` or the host repo was edited or touched, and no check, judge, instrument or pin was changed. The round directory and the two scripts below are new files; nothing existing was edited.

## Verdict per step

| Step | Verdict |
|---|---|
| W0 candidate bytes in `dist/`, five pairs equal, session `f47c80ec…`, bundle intact, profile `e2-editor-v19` | PASS |
| W1 129-B Chrome | PASS: 54/54 cells, 0 differ from each of the four reference rounds, 0 toasts, all 54 toolbars `collapsed`, red control red |
| W1 129-B Firefox | PASS: the same |
| W2 `定位游標` latency (added clause) | PASS: Chrome 54 records, 25.9--41.6 ms, median 27.5; Firefox 54 records, 27.8--34.6 ms, median 29.1 |

No red cell. The round directory is `findings/evidence/129/final/round-20261014T085633Z/`.

## W0 -- the candidate

`make -n e2-c-assets` (from `wasm_sdk_probe/`, 08:56:19Z) printed `make: Nothing to be done for 'e2-c-assets'.` -- no `cp` lines and nothing else. `make e2-c-assets` printed the same. The reason is that `dist/` was already current: `dist/editor-shell-v2/narrow-editor-v2-session.js` has mtime 2026-10-14 16:45:27 CST, the source 16:43:49 CST (an earlier session had copied it). I ran no other make target.

sha256, each source/dist pair compared in a script, all five EQUAL:

| File | sha256 (source = dist) | note |
|---|---|---|
| `e2-editor.html` | `b1185aaa4f77b892a82edb8d892aadff6f7f025369bb700f316b884661ad9512` | as in the v67 and first-pass v68 witnesses |
| `e2-editor-app.js` | `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799` | as before, so `FINAL_PAGE_SHA256` needs no re-pin |
| `editor-shell-v2/narrow-editor-v2-client.js` | `aaceb5556b0e326c53b0f8294feb6c8a097d92f1a98f1ca364cf974ab4ff3d35` | as in the first-pass v68 witness |
| `editor-shell-v2/narrow-editor-v2-session.js` | `f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9` | the expected `f47c80ec…` (first pass was `fc5ac883…`) |
| `sdk/document-sdk.js` | `6898b7958d8ef08571be4215eaaab4d8911cb90ce89a81a6e6c9fdce8c9a3347` | as before |

`python3 tools/check_e1_c_bundle_intact.py` exit 0: `"bundleSha256": "187706b2dcb07d2b"`, `"includedFiles": 5`, `"availableModules": 6`, `"intact": true`, `"divergedAsDeclared": []`, `"unbinds": null`, `"problems": []`.

Profile, read from `dist/e2-editor-app.js` line 3020: `workerUrl: "./profiles/e2-editor-v19/sdk-worker.js"`. `dist/e2-editor.html` names no profile (no `profiles/` string in it). So the page loads `e2-editor-v19`.

After the run `dist/e2-editor-app.js` still hashed `7815e16c…`, the session `f47c80ec…`, the client `aaceb555…`.

## W1 -- 129-B

Command, from `wasm_sdk_probe/` (run detached through a wrapper in the session scratchpad, not kept in the tree):

```
tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1
```

Driver exit 0, round directory `findings/evidence/129/final/round-20261014T085633Z/`. Chrome 08:56:33--09:09:25Z (Chrome/151.0.7922.169), Firefox 09:09:25--09:23:39Z (157.0.1), driver ended 09:23:39Z. Neither `report-chrome.json` nor `report-firefox.json` has a `fatal` field. `inputs.sha256` lists the probe's as-run copy `ab773929…`, `run_probe_129_final.sh` `83c48ec7…` and the page `7815e16c…`, the same lines as the first-pass v68 round (diffed with the round directory name and the `docs/` lines masked: no difference).

`preflight.final`, both browsers: `pageUnderTestSha256` `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799`, `pageUnderTestIsFinal: true`; `redControlSha256` `8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401`, `redControlIs0212: true`; `patchedServedSha256` `05fd8b0adc3af8a4e30a1a5162152c33f04965b9e936018fbb9dccb2c2a7d1bb`. Identical to the v67 and first-pass v68 rounds.

Analysis: `python3 ../../../../wasm_sdk_probe/tools/analyze_129_m4.py round-20261014T085633Z <reference>` from `findings/evidence/129/final/`, four invocations, all exit 0, in this order: `round-20261014T022210Z` (the v67 witness; `analysis-vs-022210Z-stdout.txt`), `round-20261012T235136Z` (`analysis-vs-235136Z-stdout.txt`), `round-20261013T063013Z` (`analysis-vs-063013Z-stdout.txt`) and last `round-20261012T092119Z` (`analysis-stdout.txt`, `analysis.json`, `summary.md`).

Cross-check lines the analyzer printed (the first two lines per reference; verbatim, one example, the other three differ only in the round name):

```
## cross-check: chrome vs firefox landing index equal in 54/54 cells; differ: []
## cross-check: chrome this round against round-20261014T022210Z: {'compared': 54, 'differ': [], 'wrapOffsetsSame': True}
## cross-check: firefox this round against round-20261014T022210Z: {'compared': 54, 'differ': [], 'wrapOffsetsSame': True}
```

All four references print `'compared': 54, 'differ': [], 'wrapOffsetsSame': True` for both browsers (grep of the four stdout files).

Comparing this round's `analysis-stdout.txt` with the v67 round's (`round-20261014T022210Z/analysis-stdout.txt`) by `diff`: the only differing lines are the run header (times, load, memory), the timing lines (split, move-done, click-done, and the list of the seven non-moving keys) and the swap line; the landing tables, the bottom line (`briefExactRef 28/30`, `briefByRuleRef 30/30`, `briefNotExact ["s1/Down", "s1/End"]`, `dragDownFollowsRef ["s1d","m1d"]`), the Shift arms, the red control and the reach cells are identical.

### Clauses (10-14g's table, plus the latency row)

| Clause | Chrome | Firefox | Verdict |
|---|---|---|---|
| 54/54 cells, 0 differ from `round-20261012T092119Z`, `round-20261012T235136Z`, `round-20261013T063013Z`, `round-20261014T022210Z` | 54 compared, `differ: []` against each of the four, `wrapOffsetsSame: True` | same | PASS |
| 42 brief cells land where native `ref` lands | analyzer `briefExactRef 28/30`, `briefByRuleRef 30/30`; old 12 = native exact 12/12; `dragDownFollowsRef: ["s1d","m1d"]` | same | PASS (equal to the v67 round) |
| every toolbar after the key `collapsed` | 54 of 54 `collapsed` (`clause_counts.py`) | 54 of 54 | PASS |
| 0 toasts | 0 arms with a toast, 0 with a pp toast; pill `stopped` in none | same | PASS |
| key -> move done < 200 ms for keys that move the caret, < 400 ms for those that do not | moving keys 47: 81.1--91.5 ms; non-moving 7: 281.8--297.3 ms | moving 47: 83.9--95.8; non-moving 7: 285.2--288.5 | PASS (v67 round: Chrome 81.4--84.8 / 283.2--284.9, Firefox 83.9--91.4 / 284.3--289.7) |
| Shift+arrow does not move, no toast | `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret`/`sameSelection` true | same | PASS |
| red control refuses | 3 of 3 `red-*` arms `refused: true`, toast `EDITOR_FORMAT_GESTURE_UNSUPPORTED` | 3 of 3 | red, as required |
| Chrome vs Firefox landing index | equal in 54/54 cells, `differ: []` | | PASS |
| L-129 `reach-*` cells (recorded, not judged) | `reach-s1d-0` caret `[10961, 1418]`, the other seven `[1418, 1694]` | same | recorded; equal to the v67 round (identical lines in the diff above) |
| **added (W2): every `定位游標` record of a succeeded click < 100 ms, median <= 40 ms** | 54 of 54 succeeded, 25.9--41.6 ms, median 27.5 | 54 of 54 succeeded, 27.8--34.6 ms, median 29.1 | PASS |

The landing tables, in the 10-14g layout, are in `round-20261014T085633Z/summary.md` and the stdout files. The six `s3` rows that were red on the first-pass candidate now read WASM 541, 543, 507, 543, 542, 542 (Left, Right, Up, Down, Home, End), equal to native `ref`, in both browsers (not re-listed cell by cell here: the analyzer's `differ: []` against four rounds is the statement).

## W2 -- the `定位游標` latency records

Script: `findings/evidence/link-batch/v68-witness-2/extract_click_latency.py ROUND_DIR [REFERENCE ...]`, run from `findings/evidence/129/final/`; output kept in `w2-click-latency-stdout.txt` (this round judged, the v67 round and the first-pass v68 round printed as references). It reads `timing.latencyRecords` of every arm in `arms-{chrome,firefox}.jsonl`; a record is `[ms from keydown to the record, page latency text]`. A record whose text matches `定位游標 <n> ms` is a succeeded click; `定位游標 失敗` is a failed click and is counted apart. The measured value is the first element (one decimal). That is the quantity the task's reference numbers come from: the script reproduces them exactly on the v67 round (Chrome 26.1--31.7, median 27.95; Firefox 27.8--32.0, median 29.15) and on the first-pass v68 round (253.4--268.3; Chrome median 253.8, Firefox 253.9--258.8 median 254.9). The page text's own integer `<n>` is printed beside it as a cross-check.

| Round | Browser | Succeeded / failed | min (ms) | max (ms) | median (ms) | page text min--max, median |
|---|---|---|---|---|---|---|
| this round | Chrome | 54 / 0 | 25.9 | 41.6 | 27.5 | 26--42, 27.0 |
| this round | Firefox | 54 / 0 | 27.8 | 34.6 | 29.1 | 28--34, 29.0 |
| v67 round (reference) | Chrome | 54 / 0 | 26.1 | 31.7 | 27.95 | 26--32, 28.0 |
| v67 round (reference) | Firefox | 54 / 0 | 27.8 | 32.0 | 29.15 | 28--32, 29.0 |
| first-pass v68 round (red reference) | Chrome | 48 / 6 | 253.4 | 268.3 | 253.8 | 253--268, 254.0 |
| first-pass v68 round (red reference) | Firefox | 48 / 6 | 253.9 | 258.8 | 254.9 | 254--259, 255.0 |

All 108 records of this round are `m4` arms (54 per browser, one click each); no record of another kind. The three slowest in Chrome: `m4-s2-End` 41.6, `m4-m1d-Up` 39.8, `m4-s5-Up` 29.8 ms; in Firefox: `m4-s4-Left` 34.6, `m4-s4-Home` 33.5, `m4-p2-backward-Left` 33.4 ms. The two Chrome records above 36 ms had `pswpin` 6 and 9 pages in their arms (`swapDuringArm`); whether the swap reads caused them is unverified. The clause asks for < 100 ms each and a median <= 40 ms: the largest record is 41.6 ms and both medians are below 30 ms.

Red case for the script: run with the first-pass v68 round as the judged round it prints `FAIL` and exits 1 (all-under-100 False, median-under-40 False), and it also exits 1 when it finds no records (tested on an empty `arms-*.jsonl` pair; my first draft crashed there with a `KeyError` instead of printing FAIL, which I fixed before the commit; the output of the real runs did not change); run on this round and then on the v67 round as the judged round it prints PASS. A second, read-only script `clause_counts.py` (output `clause-counts-stdout.txt`) prints the toolbar-shape, toast and key-to-move counts above for any round; on the first-pass v68 round it reproduces the numbers `v68-witness/README.md` reports (48 `collapsed` and 6 `range-cross`; moving keys 297.8--312.6 ms, 43 of them; non-moving 509.3--510.9 ms, 5 of them), which is its red case.

## Desk and anything odd

- `make` was a no-op (above); `dist/` was already the candidate.
- Before launching (08:56Z): KWallet `Locked` (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`) printed `b false`; `pgrep -af "probe_|check_m3|run_e2_c|run_probe|run_v20|python3 tools"` showed nothing of ours; `pgrep -c chrome` was 34 at 08:56:15 and 32 at 08:56:29, `pgrep -c firefox` 1. Those are the owner's desktop browsers (I did not inspect them again this time; the first-pass witness described a desktop Chrome with a normal profile, a snap Firefox 157 and a Zen browser). The v67 round saw 1 chrome process. I left them alone. Whether the owner's open windows affect any number here is unverified.
- Between the two halves (09:09:26Z): `Locked` `b false`, `pgrep -c chrome` 34, `pgrep -c firefox` 2 (our Firefox probe starting); after the run (about 09:24Z): `b false`, chrome 32, firefox 1.
- Machine: `machine-at-start.txt` 08:56:33Z load 0.45 0.77 1.02, MemAvailable 17.6 GB, SwapFree 63.4 GB; `machine-at-end.txt` 09:23:39Z load 1.64 1.54 1.39, MemAvailable 17.7 GB, SwapFree 62.9 GB (`free -m` afterwards: swap used 4,074 of 65,535 MB). Per-arm swap activity (`swapDuringArm` nonzero): 41 of the 54 `m4` arms in each browser (the analyzer's `armsWithNoSwapActivity: 13`); the v67 round had none. Chrome `pswpinMax` 719, `pswpoutMax` 13,293; Firefox 1,875 and 19,400. The first-pass witness README says swap activity "in 13 Chrome arms and 17 Firefox arms" for its round; a recount of that round's `arms-*.jsonl` gives 41 Chrome and 37 Firefox `m4` arms with swap activity, i.e. 13 and 17 are the analyzer's `armsWithNoSwapActivity` (54 minus 41 and minus 37), so that sentence in the first-pass README read the field the wrong way round. Nothing was edited there. Whether swap or load contributed to anything in this round's table is unverified; no clause is red.
- The driver exits 0 whatever the halves do; the verdict above is from the reports' `fatal` fields (absent) and the analyzer.
- Not run: any other `make` target, `package_m3_engine.py`, `ddev`, anything under `~/Projects/Nextcloud_Apps`, any `--write` mode, `git push`, the restore-window probe (not part of this task).
- Not done and not asked: freezing v68, re-pinning anything, reading `narrow-editor-v2-session.js`'s code (the bytes under test are known by hash only).
