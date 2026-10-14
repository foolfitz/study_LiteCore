# v68 candidate witness (task 2026-10-14g): 129-B on both browsers is RED -- 6 of 54 cells differ in both browsers

Facts only. Anything not checked is marked "unverified". Times are UTC unless stated. Task: `handoff/tasks/TASK-2026-10-14g-pre-v68-witness.md` (repeats `handoff/tasks/TASK-2026-10-14c-pre-v67-witness.md`). Executor: Sonnet 5.5. No shell generation was frozen, no `--write` mode was run, nothing under `web/`, `editor-shell*/`, `sdk/`, `src/`, the `Makefile` or the host repo was edited or touched. No check, judge or instrument was changed. No pin was changed (the page is unchanged, `FINAL_PAGE_SHA256` already reads `7815e16c…`, last touched by `5f7f26fe`).

## Verdict per step

| Step | Verdict |
|---|---|
| W0 candidate bytes in `dist/`, five pairs equal, session `fc5ac883…`, bundle intact, profile `e2-editor-v19` | PASS |
| W1 129-B Chrome | FAIL: 48/54 cells as before; the 6 `s3` cells differ from all four reference rounds, each carries a toast, and the toolbar after the key is `range-cross`, not `collapsed` |
| W1 129-B Firefox | FAIL: the same 6 cells, the same toast, the same shape |
| W2 | not part of this task |

Red cells are recorded here, nothing was changed. The cause below is from reading the source and is not confirmed by a probe.

## W0 -- the candidate

`make -n e2-c-assets` (from `wasm_sdk_probe/`, 07:40Z) printed `make: Nothing to be done for 'e2-c-assets'.` -- no `cp` lines, nothing else. `make e2-c-assets` printed the same. The reason is that `dist/` was already up to date: `dist/editor-shell-v2/narrow-editor-v2-session.js` has mtime 2026-10-14 15:34:03 CST, the source 15:32:27 CST, i.e. an earlier session had already copied it. I did not run any other make target.

sha256 now, each source/dist pair compared in a script, all five EQUAL:

| File | sha256 (source = dist) | v67 witness's value |
|---|---|---|
| `e2-editor.html` | `b1185aaa4f77b892a82edb8d892aadff6f7f025369bb700f316b884661ad9512` | same |
| `e2-editor-app.js` | `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799` | same |
| `editor-shell-v2/narrow-editor-v2-client.js` | `aaceb5556b0e326c53b0f8294feb6c8a097d92f1a98f1ca364cf974ab4ff3d35` | `af4919b2…` (changed) |
| `editor-shell-v2/narrow-editor-v2-session.js` | `fc5ac8830385f0f3e529608d9daa0c489b5625ce51708f115fe9e5beef9fffab` | `77841656…` (changed; this is the expected `fc5ac883…`) |
| `sdk/document-sdk.js` | `6898b7958d8ef08571be4215eaaab4d8911cb90ce89a81a6e6c9fdce8c9a3347` | same |

The client file also differs from v67 (`aaceb555…` against `af4919b2…`). The task names it ("the client additions in `narrow-editor-v2-client.js` and `paragraph-editor-client.js`"); I did not diff it.

`python3 tools/check_e1_c_bundle_intact.py` exit 0: `"bundleSha256": "187706b2dcb07d2b"`, `"includedFiles": 5`, `"availableModules": 6`, `"intact": true`, `"divergedAsDeclared": []`, `"unbinds": null`, `"problems": []`.

Profile, read from `dist/e2-editor-app.js` line 3020: `workerUrl: "./profiles/e2-editor-v19/sdk-worker.js"`. `dist/e2-editor.html` names no profile; it loads `./e2-editor-app.js` as a module (line 346). So the page loads `e2-editor-v19`.

## W1 -- 129-B

Command, from `wasm_sdk_probe/` (run detached through a wrapper in the session scratchpad, not kept in the tree):

```
tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1
```

Driver exit 0, round directory `findings/evidence/129/final/round-20261014T074321Z/` (the driver names it). Chrome 07:43:21--07:56:44Z (Chrome/151.0.7922.169), Firefox 07:56:44--08:11:45Z (157.0.1), driver ended 08:11:55Z. Neither `report-chrome.json` nor `report-firefox.json` has a `fatal` field. The probe itself is the v67 witness's: as-run copy `ab773929…`, `run_probe_129_final.sh` `83c48ec7…`, same as the v67 round's `inputs.sha256`.

`preflight.final`, both browsers: `pageUnderTestSha256` `7815e16c2cdfdebe90fbe8bf91d07a8315654bf76cf603fe8392acebb5be0799`, `pageUnderTestIsFinal: true`; `redControlSha256` `8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401`, `redControlIs0212: true`; `patchedServedSha256` `05fd8b0adc3af8a4e30a1a5162152c33f04965b9e936018fbb9dccb2c2a7d1bb`. Identical to the v67 round.

Analysis: `python3 ../../../../wasm_sdk_probe/tools/analyze_129_m4.py round-20261014T074321Z <reference>` from `findings/evidence/129/final/`, four invocations, all exit 0: against `round-20261014T022210Z` (the v67 witness, `analysis-vs-022210Z-stdout.txt`), `round-20261012T235136Z` (`analysis-vs-235136Z-stdout.txt`), `round-20261013T063013Z` (`analysis-vs-063013Z-stdout.txt`) and, last, `round-20261012T092119Z` (the precedent's reference; `analysis-stdout.txt`, `analysis.json`, `summary.md`). The 092119Z and 022210Z comparisons are the ones the task names; 235136Z and 063013Z are extra.

### Clauses (the v67 witness's table, same instrument)

| Clause | Chrome | Firefox | Verdict |
|---|---|---|---|
| 54/54 cells, 0 differ from the reference rounds and from `round-20261014T022210Z` | 54 compared, **6 differ** against each of the four rounds, `wrapOffsetsSame: True` | same 6 | FAIL |
| 42 brief cells land where native `ref` lands | analyzer bottom line `briefExactRef 22/30`, `briefByRuleRef 24/30` (v67 round: 28/30 exact, 30/30 by rule); old 12 = native exact 12/12; drag cells as before (`dragDownFollowsRef: ["s1d","m1d"]`) | same | FAIL (the 6 `s3` cells) |
| toolbar shape after the key is `collapsed` | 48 of 54 `collapsed`, 6 `range-cross` (`m4-s3-Left/Right/Up/Down/Home/End`) | same | FAIL |
| 0 toasts | 6 arms with a toast (the same 6 `s3` arms); pill `stopped` in none | same | FAIL |
| key -> move done < 400 ms (analyzer limit 200 ms for keys that move the caret) | moving keys 297.8--312.6 ms (43 of them, all over 200); the 5 non-moving keys 509.3--510.9 ms | moving 299.7--310.2; non-moving 512.2--515.4 | FAIL (v67 round: moving 81.4--91.4, non-moving 283.2--289.7) |
| Shift+arrow does not move, no toast | `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret`/`sameSelection` true | same | PASS |
| red control refuses | 3 of 3 `red-*` arms `refused: true`, toast `EDITOR_FORMAT_GESTURE_UNSUPPORTED` | 3 of 3 | red, as required |
| Chrome vs Firefox landing index | equal in 54/54 cells, `differ: []` | | PASS (they are red the same way) |
| L-129 `reach-*` cells (recorded, not judged) | caret and selection values as in the v67 round (e.g. `reach-s1d-0` caret `[10961, 1418]`, the other seven `[1418, 1694]`) | same | recorded |

### The differing cells, verbatim

Cross-check lines the analyzer printed, for each of the four reference rounds (this one is against `round-20261014T022210Z`; the others differ only in the round name):

```
## cross-check: chrome this round against round-20261014T022210Z: {'compared': 54, 'differ': ['s3/Left', 's3/Right', 's3/Up', 's3/Down', 's3/Home', 's3/End'], 'wrapOffsetsSame': True}
## cross-check: firefox this round against round-20261014T022210Z: {'compared': 54, 'differ': ['s3/Left', 's3/Right', 's3/Up', 's3/Down', 's3/Home', 's3/End'], 'wrapOffsetsSame': True}
```

Landing table rows (flat index; identical in Chrome and Firefox):

```
| s3 | Left  | 532 | 541 | 541 | False | False | False / False |
| s3 | Right | 532 | 543 | 543 | False | False | False / False |
| s3 | Up    | 532 | 507 | 507 | False | False | False / False |
| s3 | Down  | 532 | 543 | 543 | False | False | False / False |
| s3 | Home  | 532 | 542 | 542 | False | False | False / False |
| s3 | End   | 532 | 542 | 542 | False | False | False / False |
```

(columns: shape, key, WASM, native ref, native emu, = ref, = emu, by rule ref / emu.) In the v67 round the same six cells landed on 541, 543, 507, 543, 542, 542 -- the native `ref` values, e.g. `m4-s3-Left` hash `flatIndex 541`, `m4-s3-Up` `flatIndex 507`. Now every `s3` key leaves the caret at 532 (`excerpt "ore the empty <#>|S3 text after"`, paragraph 2 offset 25), the range selection is still there after the key (`afterKey.selection.collapsed: false`, same rectangles as before the key), and `timing.latencyRecords` holds one record, `[3.7, "定位游標 失敗"]` (Chrome `m4-s3-Left`), no key record (`moveDoneMs: null`).

The toast, verbatim (same text in all 6 arms of both browsers, e.g. Chrome `m4-s3-Left` at `346710.6`):

```
定位游標：INVALID_ARGUMENT：editorPlaceCaretV2 requires non-negative integer twips
```

All other 48 cells per browser (every shape except `s3`) are equal to the reference rounds, including the cells that are not exact against native `ref` in every round (`s1/Down`, `s1/End`, `s1d/Down`, `s1d/End`, the `m1d` rows).

### The click now takes about 254 ms in every other cell

Not a clause of the task, but it moved: in the 48 cells per browser whose click succeeded, the page's `定位游標` record is 253.4--268.3 ms (Chrome, median 253.8) and 253.9--258.8 ms (Firefox, median 254.9); in the v67 round it was 26.1--31.7 ms (Chrome, median 27.95) and 27.8--32.0 ms (Firefox, median 29.15). The key's own record is unchanged: `m4-s1-Left` Chrome `◀ 40 ms` now, `◀ 48 ms` in the v67 round. `clickDoneToMoveDone` is 44--46 ms (Chrome) and 45--51 ms (Firefox) now, 52--57 / 53--63 before. So `keyToMoveDone` rose by about the click's added 225--230 ms, and it is that, not the key, that crosses the 200 ms and 400 ms limits in the table. The 5 per browser non-moving keys (`s1/Home`, `s2/End`, `s5/Home`, `s1d/Home`, `m1d/Home`) wait for the same click and then show the same ~256 ms click-to-move gap (`clickDoneToMoveDone` 255.6--259.5) as the 7 non-moving keys of the v67 round (255.4--258.7); they are 5 and not 7 because the other two non-moving keys of the v67 round are `s3-Home` and `s3-End` (checked in the v67 round's `arms-*.jsonl`), which now have no key record. What the ~256 ms gap is, I did not look into.

## Probable cause (read from the source, not measured; unverified by a probe)

1. The 6 failing cells are exactly the cells whose caret height is odd. `beforeKey.caret.height` in `arms-*.jsonl` is 277 for every `s3` arm and 276 for every arm of the other eight shapes (checked for both browsers). The page's arrow-key path `moveFromPoint` (`web/e2-editor-app.js` line 2787) calls `session.placeCaret(caret.x, caret.y + caret.height / 2)`; with height 277 that y is a half-integer (for the `far` caret, 3626 + 138.5). The worker's `editorPlaceCaretV2` (`sdk/sdk-worker.js` lines 1552--1559) answers `INVALID_ARGUMENT`, `"editorPlaceCaretV2 requires non-negative integer twips"`, to a non-integer; the new `placeCaret` in `editor-shell-v2/narrow-editor-v2-session.js` falls back to v67's polling loop only for `PLACE_CARET_FALLBACK_CODES` (its comment names BUSY and no such entry point), so this error is rethrown and the page toasts it with the `定位游標` prefix. The pointer-down path rounds (`pointToTwips`, line 1686, `Math.round`) and does not hit this; the reopen path (line 1821) uses the same `caret.y + caret.height / 2` form as `moveFromPoint`. Whether the v67 `document.click` path accepted a non-integer or rounded it, I did not read.
2. The roughly 254 ms click matches the new code's own comment: when the click changes nothing and no cursor callback comes, the engine answers "at its own 250 ms readback deadline (`EditorPlaceCaretDeadlineMs`)". In these arms `moveFromPoint` clicks at the caret's current position to collapse the range, so the caret does not move. That the engine's deadline is what the 254 ms measures, and that no cursor callback arrives in these arms, is inferred, not observed (`completion` is not in the arms' records).

Both points are about the two files this task is testing; I changed neither and ran nothing to test the reading.

## Desk and anything odd

- `make` was a no-op (above); dist was already the candidate.
- Before launching (07:43Z): the KWallet `Locked` property printed `b false`; `pgrep -af "probe_129|check_m3|run_e2_c|run_probe"` showed nothing of ours; `pgrep -c chrome` was 32 and `pgrep -c firefox` 1. Those are the owner's browsers (a desktop Chrome with a normal profile, parent PID 3036's session, running about 85 minutes, 29 processes at my first look and 32 at launch; a snap Firefox 157; and a Zen browser). The v67 round saw 1 chrome process. I left them alone; whether the owner's open windows affect the 129-B numbers here is unverified. The wallet was checked again between the two halves (07:56Z): `b false`; and after the run: `b false`.
- Load average: 1.3--1.6 for the whole 3 minutes I waited before launch (the v67 round started at 0.34); `machine-at-start.txt` 07:43:21Z load 1.53 1.44 1.30, MemAvailable 15.1 GB, SwapFree 64.8 GB; `machine-at-end.txt` 08:11:55Z load 1.06 1.37 1.70. The consumers I saw were a ddev php/drush cron (php-fpm workers and `drush.php cron`, 12--17 % each) and a short `php8.4` spike; none is ours. The machine has 12 cores. The analyzer shows swap activity in 13 Chrome arms and 17 Firefox arms (`pswpinMax` 356 and 119); the v67 round had none. Whether this load or swap contributed to anything in the table is unverified; it cannot explain the six `s3` cells, which fail in 6 of 6 in both browsers within 3.7 ms of the key, with a code-level error text.
- The driver exits 0 whatever the halves do; the verdict above is from the reports' `fatal` fields (absent) and the analyzer.
- After the run `dist/e2-editor-app.js` still hashed `7815e16c…` and `dist/…/narrow-editor-v2-session.js` `fc5ac883…`.
- Not run: any other `make` target, `package_m3_engine.py`, `ddev`, anything under `~/Projects/Nextcloud_Apps`, any `--write` mode, `git push`, the restore-window probe.
- Unverified: whether the `s3` fixture's odd caret height (277) is special to this document or an ordinary property of lines with a taller font/object; the document is `arrow-selection-shapes.odt`/`arrow-selection.odt` family (which of the three holds `s3` was not checked).
