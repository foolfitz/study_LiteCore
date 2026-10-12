# 132-B on the 134 page `6470dec0…` — step G0 of `handoff/tasks/TASK-2026-10-13-134-guard-chain.md`

SPEC-M3-held-key §14, ruling-1 condition 4. Finding 134 changed two things on top of the 132 final page `abe93f45…`: B (after a delete this page sent is refused, the rest of that Backspace/Delete hold is not sent) and D (after an automatic reopen the caret is put back). A mid-document hold has no refusal, so 132-B must read exactly as it did on `abe93f45…`; this run is the witness. Same probe, same arms, same judge as `../../../132/132-b-final/`, run on the new bytes. Nothing in the instruments or the judge was changed.

## Conditions

- Host `litecore` 0.2.16 (`appinfo/info.xml` changed, not committed; host commit `568608c`, `hostDirty: ["M appinfo/info.xml"]`), engine package buildId `9352fae3aea68b5e` (`engine/MANIFEST.json`, `source.page` = the page below, `source.profile` e2-editor-v19). `report.json` → `static` (at the start) and `staticAfter` (at the end) both read `servedPage` `6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b`, equal to `static.distPage` (= `dist/e2-editor-app.js` = `web/e2-editor-app.js`, `sha256sum` checked before the run).
- Probe `wasm_sdk_probe/tools/probe_hand_test_0212.py` (last commit touching it `bb9b8c9f`, the same as in `132-b-final`): `--browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (exit 0, `probe.out`), hold as in the baseline (GNOME `delay` 500 ms, `repeat-interval` 30 ms: 52 keydowns over 2 s). Chrome 151.0.7922.169 2026-10-12 23:00:13–23:17:33Z, Firefox 157.0.1 23:17:33–23:34:34Z (`report.json` `runs[].startedAt/completedAt`). At the start `pgrep -c chrome` = 1 (Codex desktop's `chrome_crashpad_handler`, not a browser), load 0.74 0.98 0.90 (`started-utc.txt`); the owner's own Firefox (pid 3932) was already open and was left alone; `pgrep -af "probe_|check_m3|run_e2_c"` showed nothing of ours before the start.
- Judge `../../../132/judge_132b.py` (`bb9b8c9f`), run with `--page 6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b`: `judge-output.txt`, **exit 0** (the last line of that file, `exit 0`, was appended by me from `$?` after the judge finished; it is not judge output). Numbers: `read_hold-output.txt` (`../../../132/read_hold.py`, exit 0).
- Not checked / odd: `static.shellBundle` in `report.json` is `exit 1` ("manifest is out of date … changed=['web/e2-editor-app.js']", manifest `e2/editor-shell-v2-bundle-v64.json`, which exists with a different digest than the tree now hashes). The shell generation is not frozen for this page; the probe records the line and does not stop on it. Not investigated further.

## Result: 132-B PASS (12 of 12 holds, both wash-control positive controls)

The judge printed `132-B PASS`, every `chrome|firefox hold-high|hold-low round 0|1|2: PASS`, `chrome wash-control: selection fills [5]  PASS`, `firefox wash-control: selection fills [9]  PASS`.

| | Chrome high | Chrome low | Firefox high | Firefox low | baseline (`../../../132/baseline/`) |
|---|---|---|---|---|---|
| keydowns / flagged repeat | 52 / 51 ×3 | 52 / 51 ×3 | 52 / 51 ×3 | 52 / 51 ×3 | same |
| deletes sent = deleted | 25 ×3 | 25 ×3 | 26 ×3 | 26 ×3 | 52 |
| (a) deletes after release | 2, 2, 2 | 2, 1, 2 | 2, 2, 2 | 2, 1, 2 | 27–29 |
| last delete after release (ms) | 63.4, 71.0, 61.7 | 72.6, 61.3, 79.0 | 92.4, 80.3, 66.6 | 78.2, 62.2, 79.8 | 1788–1855 |
| (b) shown / done at release | 22/23 ×3 | 22/23, 22/24, 22/23 | 23/24, 23/24, 23/25 | 23/24, 23/25, 23/24 | low: 1 / 23–25 |
| caret band repainted before release | 24 ×3 | 24 ×3 | 25 ×3 | 25 ×3 | low: 1 |
| caret band fresh after release (ms) | 76.7, 84.9, 73.9 | 89.2, 78.6, 94.5 | 104.0, 95.5, 80.4 | 97.5, 84.7, 100.8 | 1806–1870 |
| (d) washes (hold; single presses) | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 52; 1 each |
| (e) `persistent.differing` | 0 ×3 | 0 ×3 | 0 ×3 | 0 ×3 | 0 |
| median gap between deletes in the hold (ms) | 65.6–66.3 | 66.2–66.5 | 66.8–67.1 | 66.9–67.3 | 65.6–66.6 |
| wash-control: range fills after a drag | 5 | | 9 | | — |

For comparison, the run on the previous final page `abe93f45…` (`../../../132/132-b-final/README.md`): deleted per hold 25 / 26 (the same), deletes after release 1–2 (the same), last delete after release 52.3–115.7 ms (this run 61.3–92.4), caret band fresh 64.9–130.3 ms (this run 73.9–104.0), median gap 65.6–67.1 ms (this run 65.6–67.3). Not compared against any threshold other than the judge's.

## Against §7's predictions (written before any implementation of finding 132)

- Deleted per hold 23–27: **25 / 26**, hit. Deletes after release 1–2, last at 40–140 ms after release: **1–2, 61.3–92.4 ms**, hit. Screen 0–1 behind the engine at release: **1–2 behind** (done minus shown at release: 1 in 9 holds, 2 in 3 holds — Chrome low round 1, Firefox high round 2, Firefox low round 1), missed by one in the same way as the previous two runs; (b)'s bound of 2 holds. Caret band fresh ≤ 160 ms after release: **73.9–104.0 ms**, hit. Blue 0: hit.
- The engine's rate during the hold is unchanged (median gap 65.6–67.3 ms, as in the baseline 65.6–66.6; the Firefox maximum is 0.7 ms above the baseline's maximum): H2 removed the tail, not speed — as §3.2 said.
- Single presses (`read_hold-output.txt`, `single lag` / `fresh`): keydown → done 44.0–49.3 ms in Chrome and 46.5–51.9 ms in Firefox; caret band fresh 55.1–63.4 ms (Chrome) and 60.7–72.2 ms (Firefox) after the keyup. Previous final page: 44.0–48.4 and 45.6–50.8 except one at 59.5; baseline 44.2–50.4 and 56–75. The largest single-press value in this run is Firefox 51.9 ms (holdLow, round 2), 1.5 ms above the baseline's maximum of 50.4.

## Limits of this reading

Unchanged from `../../../132/132-b/README.md` (review 1, `../../../132/review/review-1.md`): the `repeat` flags are set by the drivers (CDP `autoRepeat`, WebDriver), not by the owner's keyboard path (S3); (b) reads the band holding the caret's top row only (S2, registered L-132-other-bands); devicePixelRatio 1 only (N8). This run holds in the middle of the document; it says nothing about holds that end in a refusal (that is finding 134's own acceptance, `../../acceptance-0.2.16/`).
