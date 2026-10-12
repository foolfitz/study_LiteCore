# 132-B on page `abc3d97b…` (H1–H3 as committed in `69c05657`) — a pre-final run

SPEC-M3-held-key §5.2. **Pre-final**: the page that will be frozen differs from `abc3d97b…` by one moved doc comment (review 1 N10, comment only); 132-B is run again on the final bytes before the freeze. This run is kept as the first reading of H1–H3 in a browser.

## Conditions

- Host `litecore` 0.2.15 (`appinfo/info.xml` changed, not committed; host commit `237f2cb`), engine package buildId `d16755622286e9af` (differs from 0.2.14's `eb3f9408…` only in `e2-editor-app.js`, `check_engine_decoded.py` passed), served page `abc3d97b6fcc6c9f…` at the start (`static`) and at the end (`staticAfter`).
- Probe `wasm_sdk_probe/tools/probe_hand_test_0212.py` at `bb9b8c9f`: `--arms hold-high,hold-low,wash-control --hold-rounds 3`, hold as in the baseline (GNOME delay 500 ms, repeat-interval 30 ms: 52 keydowns over 2 s, keyup at 2015 ms). Chrome 151.0.7922.169, Firefox 157.0.1, 2026-10-12 17:02–17:35 UTC.
- Judge `../judge_132b.py` (`bb9b8c9f`; self-test OK, the baseline judged red as §6 says): `judge-output.txt`, exit 0. Numbers: `read_hold-output.txt` (`../read_hold.py`).

## Result: 132-B PASS (12 of 12 holds, both positive controls)

| | Chrome high | Chrome low | Firefox high | Firefox low | baseline (`../baseline/`) |
|---|---|---|---|---|---|
| keydowns / flagged repeat | 52 / 51 ×3 | 52 / 51 ×3 | 52 / 51 ×3 | 52 / 51 ×3 | same |
| deletes sent = deleted | 25 ×3 | 25 ×3 | 26 ×3 | 26 ×3 | 52 |
| (a) deletes after release | 2, 2, 1 | 2, 2, 2 | 1, 2, 1 | 2, 1, 2 | 27–29 |
| last delete after release (ms) | 84.9, 66.3, 63.1 | 78.3, 72.2, 67.7 | 64.6, 69.1, 54.5 | 70.1, 52.1, 70.2 | 1788–1855 |
| (b) shown / done at release | 22/23, 22/23, 22/24 | 22/23 ×3 | 23/25, 23/24, 24/25 | 23/24, 24/25, 23/24 | low: 1 / 23–25 |
| caret band repainted before release | 24 ×3 | 24 ×3 | 25, 25, 26 | 25, 26, 25 | low: 1 |
| caret band fresh after release (ms) | 100.2, 84.5, 75.9 | 96.1, 90.6, 85.9 | 80.1, 85.1, 71.4 | 96.6, 72.4, 91.9 | 1806–1870 |
| (d) washes (hold; single presses) | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 52; 1 each |
| (e) `persistent.differing` | 0 ×3 | 0 ×3 | 0 ×3 | 0 ×3 | 0 |
| median gap between deletes in the hold (ms) | 65.5–66.0 | 65.8–66.0 | 66.3–66.8 | 66.7–66.9 | 65.6–66.6 |
| wash-control: range fills after a drag | 5 | | 9 | | — |

## Against §7's predictions (written before any implementation)

- Deleted per hold 23–27: **25 / 26**, hit. Deletes after release 1–2, last at 40–140 ms after release: **1–2, 52–85 ms**, hit. Screen 0–1 behind the engine at release: **1–2 behind**, missed by one (the delete that completed just before the keyup has its band in flight; (b)'s bound of 2 holds). Caret band fresh ≤ 160 ms after release: **71–100 ms**, hit. Blue 0: hit.
- The engine's rate during the hold is unchanged (median gap 66 ms, as in the baseline): H2 removed the tail, not speed — as §3.2 said.
- Single presses: keydown → done 43.8–50.9 ms, caret band fresh 56–75 ms after the keyup, as in the baseline (44.2–50.4, 56–75).

## Limits of this reading (review 1, `../review/review-1.md`)

- The `repeat` flags are set by the drivers (CDP `autoRepeat`, WebDriver), not by the owner's keyboard path (S3): this shows H2 works when the flag arrives; the owner's hand test is the witness for the platform half.
- (b) reads the band holding the caret's top row only; under a hold only that band is repainted, so text in other bands (a caret line straddling a band edge, lines reflowing across an edge below) stays as it was until release (S2, registered L-132-other-bands).
- devicePixelRatio 1 only (N8).
