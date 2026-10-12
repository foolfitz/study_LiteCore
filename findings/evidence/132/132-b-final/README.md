# 132-B on the final page `abe93f45…` (the bytes that will be frozen) — step G0 of `handoff/tasks/TASK-2026-10-13-132-guard-chain.md`

SPEC-M3-held-key §5.2. The pre-final run on `abc3d97b…` is `../132-b/`; the final page differs from it by one moved doc comment (review 1 N10, comment only). This is the same probe, the same arms and the same judge, run again on the final bytes.

## Conditions

- Host `litecore` 0.2.15 (`appinfo/info.xml` changed, not committed; host commit `237f2cb`), engine package buildId `daf70d77b8facb4b`; served page `abe93f4575c7797d…` at the start (`static.servedPage`) and at the end (`staticAfter.servedPage`) of `report.json`, equal to `dist/e2-editor-app.js` (`static.distPage`).
- Probe `wasm_sdk_probe/tools/probe_hand_test_0212.py` (last commit touching it `bb9b8c9f`): `--browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3`, hold as in the baseline (GNOME `delay` 500 ms, `repeat-interval` 30 ms: 52 keydowns over 2 s, keyup at about 2015 ms). Chrome 151.0.7922.169 2026-10-12 17:41:31–17:58:16Z, Firefox 157.0.1 17:58:16–18:15:19Z. The owner's own Chrome (about 16 h old) and Firefox were open on the desk and were left alone; no other probe ran (`pgrep -af "probe_|check_m3|run_e2_c"` showed nothing before the start).
- Judge `../judge_132b.py` (`bb9b8c9f`), run with `--page abe93f4575c7797db97462f1f0e3a71cf5fc4063205cd6d5877093ca1c248fcf`: `judge-output.txt`, **exit 0**. Numbers: `read_hold-output.txt` (`../read_hold.py`, exit 0).
- Not checked / odd: `static.shellBundle` in `report.json` is `exit 1` ("manifest is out of date … changed=['web/e2-editor-app.js']", `e2/editor-shell-v2-bundle-v63.json`). The same line is in the pre-final report; the shell generation is not frozen for this page yet, so the line is expected and the probe did not stop on it.

## Result: 132-B PASS (12 of 12 holds, both wash-control positive controls)

The judge printed `132-B PASS`, every `chrome|firefox hold-high|hold-low round 0|1|2: PASS`, `chrome wash-control: selection fills [5]  PASS`, `firefox wash-control: selection fills [9]  PASS`.

| | Chrome high | Chrome low | Firefox high | Firefox low | baseline (`../baseline/`) |
|---|---|---|---|---|---|
| keydowns / flagged repeat | 52 / 51 ×3 | 52 / 51 ×3 | 52 / 51 ×3 | 52 / 51 ×3 | same |
| deletes sent = deleted | 26, 25, 25 | 25, 25, 26 | 26 ×3 | 26 ×3 | 52 |
| (a) deletes after release | 2, 1, 1 | 2, 2, 2 | 2, 1, 1 | 2, 2, 2 | 27–29 |
| last delete after release (ms) | 115.7, 64.0, 52.3 | 69.8, 63.1, 113.6 | 78.3, 60.7, 57.7 | 73.7, 75.7, 74.4 | 1788–1855 |
| (b) shown / done at release | 23/24, 22/24, 22/24 | 22/23, 22/23, 23/24 | 23/24, 23/25, 24/25 | 23/24 ×3 | low: 1 / 23–25 |
| caret band repainted before release | 25, 24, 24 | 24, 24, 25 | 25, 25, 26 | 25 ×3 | low: 1 |
| caret band fresh after release (ms) | 130.3, 82.5, 64.9 | 84.6, 78.5, 129.4 | 98.7, 81.0, 72.4 | 93.5, 92.8, 95.5 | 1806–1870 |
| (d) washes (hold; single presses) | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 52; 1 each |
| (e) `persistent.differing` | 0 ×3 | 0 ×3 | 0 ×3 | 0 ×3 | 0 |
| median gap between deletes in the hold (ms) | 65.6–66.1 | 65.8 ×3 | 66.5–66.6 | 66.9–67.1 | 65.6–66.6 |
| wash-control: range fills after a drag | 5 | | 9 | | — |

## Against §7's predictions (written before any implementation)

- Deleted per hold 23–27: **25 / 26**, hit. Deletes after release 1–2, last at 40–140 ms after release: **1–2, 52.3–115.7 ms**, hit. Screen 0–1 behind the engine at release: **1–2 behind** (done minus shown at release: 1 in 9 holds, 2 in 3 holds), missed by one in the same way as the pre-final run; (b)'s bound of 2 holds. Caret band fresh ≤ 160 ms after release: **64.9–130.3 ms**, hit (the two largest, Chrome 130.3 and 129.4, are higher than the pre-final run's maximum of 100.2; both are under the bound). Blue 0: hit.
- The engine's rate during the hold is unchanged (median gap 65.6–67.1 ms, as in the baseline 65.6–66.6): H2 removed the tail, not speed — as §3.2 said.
- Single presses (`read_hold-output.txt`, `single lag` / `fresh`): keydown → done 44.0–48.4 ms in Chrome and 45.6–50.8 ms in Firefox except one Firefox press at 59.5 ms; caret band fresh 55.6–78.5 ms after the keyup. Pre-final: 43.8–50.9 and 56–75; baseline 44.2–50.4 and 56–75. The one Firefox press at 59.5 / 78.5 ms (holdLow, round 1) is the largest single-press value in this run; the next largest is 50.8 ms (two presses), 0.4 ms above the baseline's maximum of 50.4.

## Limits of this reading

Unchanged from `../132-b/README.md` (review 1, `../review/review-1.md`): the `repeat` flags are set by the drivers (CDP `autoRepeat`, WebDriver), not by the owner's keyboard path (S3); (b) reads the band holding the caret's top row only (S2, registered L-132-other-bands); devicePixelRatio 1 only (N8).
