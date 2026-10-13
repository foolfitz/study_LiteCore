# 132-B on the 136 page `b24d754a…` — step G0 of `handoff/tasks/TASK-2026-10-13d-136-guard-chain.md`

SPEC-M3-held-key §16, ruling-3 conditions 5–6. Finding 136 changed two things on top of the 134 page `6470dec0…`: `updateState` notes the last caret the engine pushed with no range selected (the reopen puts the caret back there), and `updateState` does not follow the caret while the page reopens. Every state write now notes the caret, so 132-B is a witness that holds and presses read as before. Same probe, same arms, same judge as `../../134/guard/132-b/`. Nothing in the instruments or the judge was changed.

## Result: 132-B FAIL (judge exit 1) — the Chrome half did not run; the Firefox half is 6 of 6 holds PASS

The judge printed (`judge-output.txt`, the trailing `exit 1` line was appended by me from `$?`):

```
chrome: fatal in the run  FAIL
chrome hold-high: 0 holds < 3  FAIL
chrome hold-low: 0 holds < 3  FAIL
chrome wash-control: not run  NOT_ESTABLISHED
firefox wash-control: selection fills [10]  PASS
132-B FAIL
```

and `firefox hold-high|hold-low round 0|1|2: PASS` (6 lines).

### Chrome: fatal before any measurement (not a measured cell)

`report.json` → `runs[0]` (chrome, `Chrome/151.0.7922.169`, 2026-10-13T03:36:01Z–03:39:08Z): `fatal` is a traceback ending `TimeoutError: timed out in 180.0s`, raised in `login()` → `navigate(session, base + "/login", timeout=60)` → `session.call("Page.navigate", …)` → `websocket.recv(timeout=180)` (`probe_hand_test_0212.py` line 648, `check_m3_locks.py` line 308). That is: Chrome was launched, the CDP `Page.navigate` to the host's `/login` got no answer within 180 s. Upload (HTTP 204) and `clearedLocks` had succeeded before it. No Chrome hold, press or wash-control was run, so Chrome has no verdict on this page from this run — it is neither a PASS nor a measured FAIL. Cause not investigated (unverified). Context: this was the first Chrome launch after the owner's reboot (the earlier attempt in `../132-b-aborted-for-reboot/` was stopped before any browser step finished). The probe moved on to Firefox by itself (`probe.out`: `chrome fatal`, `firefox done`, `probe exit 0`).

Per the task ("if a cell is red, stop that step, record it, go on"; "do not rerun anything beyond what the task explicitly allows") I did not rerun the Chrome half. A Chrome-only rerun (`--browsers chrome`) would take about 17 minutes; the judge accepts several `report.json` arguments, but it flags `chrome: fatal in the run FAIL` for any report that carries that run record, so the first report would still print FAIL.

## Conditions

- Host `litecore` 0.2.18 (`appinfo/info.xml` changed, not committed; host commit `f5b34f0`, `hostDirty: ["M appinfo/info.xml"]`), engine package buildId `d6d04880f56e31da` (`engine/MANIFEST.json` read before the run: `source.page` = the page below, `source.profile` e2-editor-v19, `packagedAt` 2026-10-13T02:25:55+00:00). `report.json` → `static` (start) and `staticAfter` (end) both read `servedPage` `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`, equal to `static.distPage` (= `dist/e2-editor-app.js` = `web/e2-editor-app.js`, `sha256sum` of both checked before the run).
- Probe `wasm_sdk_probe/tools/probe_hand_test_0212.py`: `--browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (exit 0, `probe.out`), hold as in the baseline (GNOME `delay` 500 ms, `repeat-interval` 30 ms). Run started 2026-10-13T03:36:01Z, Chrome fatal at 03:39:08Z, Firefox 157.0.1 03:39:08–03:56:10Z. At the start `pgrep -c chrome` = 0, load 0.27 0.33 0.31 (`started-utc.txt`); no Firefox of the owner's was open; `pgrep -af "probe_|check_m3|run_e2_c"` showed nothing of ours.
- Judge `../../../132/judge_132b.py`, run with `--page b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`. Numbers: `read_hold-output.txt` (`../../../132/read_hold.py`, exit 0).
- Not checked / odd: `static.shellBundle` in `report.json` is `exit 1` ("manifest is out of date … changed=['web/e2-editor-app.js']", manifest `e2/editor-shell-v2-bundle-v65.json`): the shell generation is not frozen for this page; the probe records the line and does not stop on it. Not investigated further.

## Firefox numbers (read, for comparison with `../../134/guard/132-b/`)

| | Firefox high | Firefox low | 134 page, Firefox high / low |
|---|---|---|---|
| keydowns / flagged repeat | 52 / 51 ×3 | 52 / 51 ×3 | same |
| deletes sent = deleted | 26 ×3 | 26 ×3 | 26 ×3 / 26 ×3 |
| (a) deletes after release | 2, 2, 2 | 2, 1, 2 | 2, 2, 2 / 2, 1, 2 |
| last delete after release (ms) | 93.0, 87.6, 78.4 | 72.1, 70.6, 105.3 | 92.4, 80.3, 66.6 / 78.2, 62.2, 79.8 |
| (b) shown / done at release | 23/24 ×3 | 23/24, 23/25, 23/24 | 23/24, 23/24, 23/25 / 23/24, 23/25, 23/24 |
| caret band repainted before release | 25 ×3 | 25 ×3 | 25 ×3 |
| caret band fresh after release (ms) | 108.4, 103.1, 92.1 | 90.2, 89.6, 123.4 | 104.0, 95.5, 80.4 / 97.5, 84.7, 100.8 |
| (d) washes (hold; single presses) | 0; 0 | 0; 0 | 0; 0 |
| (e) `persistent.differing` | 0 ×3 | 0 ×3 | 0 ×3 |
| median gap between deletes in the hold (ms) | 67.5–67.7 | 67.6–68.2 | 66.8–67.1 / 66.9–67.3 |
| single presses: keydown → done (ms) | 46.7–52.1 | 46.0–51.4 | 46.5–51.9 |
| wash-control: range fills after a drag | 10 | | 9 |

The medians of the gap between deletes (high 67.5–67.7, low 67.6–68.2 ms) are 0.6 (high) and 0.9 (low) ms above the 134 page's Firefox maxima, and the largest caret-band-fresh figure (123.4 ms) is above the 134 page's 104.0; the judge's thresholds (§5.2: `deletesAfterRelease` ≤ 2, shown ≥ done − 2) hold in all six holds. Not compared against any threshold other than the judge's.

## Limits of this reading

Unchanged from `../../../132/132-b/README.md`: the `repeat` flags are set by the drivers (CDP `autoRepeat`, WebDriver), not by the owner's keyboard path; (b) reads the band holding the caret's top row only; devicePixelRatio 1 only. This run holds in the middle of the document; it says nothing about holds that end in a refusal. Chrome: nothing measured.
