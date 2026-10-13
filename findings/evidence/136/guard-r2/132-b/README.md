# 132-B on the 136 page `b24d754a…`, run 2 — step G0 of `handoff/tasks/TASK-2026-10-13e-136-guard-chain-r2.md`

Run 2 of `handoff/tasks/TASK-2026-10-13d-136-guard-chain.md` G0 (run 1: `../../guard/132-b/`, Chrome not measured because of the locked KWallet). SPEC-M3-held-key §16, ruling-3 conditions 5–6. Same probe, same arms, same judge as run 1 and as `../../../134/guard/132-b/`. Nothing in the instruments or the judge was changed.

## Result: 132-B PASS (judge exit 0) — 12 of 12 holds PASS, both wash controls PASS, both browsers measured

`judge-output.txt` (the first line is the `$ …` command line and the trailing `exit 0` line was appended by me from `$?`; the judge's own last line is `132-B PASS`):

```
chrome hold-high round 0|1|2: PASS      chrome hold-low round 0|1|2: PASS
firefox hold-high round 0|1|2: PASS     firefox hold-low round 0|1|2: PASS
chrome wash-control: selection fills [5]  PASS
firefox wash-control: selection fills [9]  PASS
132-B PASS
```

## Conditions

- Host `litecore` 0.2.18 (`appinfo/info.xml` changed, uncommitted; host commit `f5b34f0`), engine package buildId `d6d04880f56e31da`. `report.json` → `static` (start) and `staticAfter` (end) both read `servedPage` `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`, equal to `static.distPage`; `hostVersion` `0.2.18`. `static.shellBundle` is the same "not frozen for this page" record as in run 1 (the probe records it and does not stop on it; not investigated).
- Probe `wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/136/guard-r2/132-b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (exit 0, `probe.out` ends `probe exit 0`). Chrome/151.0.7922.169 2026-10-13T05:38:49–05:56:10Z, Firefox 157.0.1 05:56:10–06:13:11Z. Desk at the start (`started-utc.txt`): `pgrep -c chrome` 1 (MarkText's `chrome_crashpad_handler`, not a browser), Chrome browsers 0, `pgrep -c firefox` 1 (the owner's own Firefox, left alone), load 0.64 0.71 0.60.
- Wallet and Chrome health check immediately before: `../health-checks.txt` (`[before-G0]`, 05:38:47Z: `Locked` = `b false`, default-flag `--dump-dom` rc 0, `Nextcloud` ×328).
- Judge `findings/evidence/132/judge_132b.py --page b24d754a…` (exit 0); numbers: `read_hold-output.txt` (`findings/evidence/132/read_hold.py`, exit 0).

## Numbers (read; for comparison with run 1's Firefox half and with `../../../134/guard/132-b/`)

| | Chrome high | Chrome low | Firefox high | Firefox low | run 1 Firefox high / low |
|---|---|---|---|---|---|
| deletes sent = deleted | 25 ×3 | 25 ×3 | 26 ×3 | 26 ×3 | 26 ×3 / 26 ×3 |
| (a) deletes after release | 2, 2, 2 | 1, 2, 2 | 2, 1, 2 | 2, 2, 2 | 2, 2, 2 / 2, 1, 2 |
| last delete after release (ms) | 115.8, 76.0, 83.1 | 58.4, 74.8, 75.8 | 76.5, 60.9, 101.3 | 85.3, 92.3, 83.2 | 93.0, 87.6, 78.4 / 72.1, 70.6, 105.3 |
| (b) shown / done at release | 22/23 ×3 | 22/24, 22/23, 22/23 | 23/24, 23/25, 23/24 | 23/24 ×3 | 23/24 ×3 / 23/24, 23/25, 23/24 |
| caret band fresh after release (ms) | 130.4, 90.4, 95.4 | 73.0, 90.5, 92.7 | 93.4, 76.7, 116.4 | 105.1, 110.1, 101.9 | 108.4, 103.1, 92.1 / 90.2, 89.6, 123.4 |
| (d) washes (hold; single presses) | 0; 0 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| (e) `persistent.differing` | 0 ×3 | 0 ×3 | 0 ×3 | 0 ×3 | 0 ×3 |
| median gap between deletes (ms) | 66.7, 67.1, 66.7 | 66.7, 67.0, 66.9 | 67.2, 67.3, 67.9 | 67.2, 67.6, 67.8 | 67.5–67.7 / 67.6–68.2 |
| single presses: keydown → done (ms) | 44.2–48.4 | 44.3–49.2 | 45.6–50.8 | 46.7–49.6 | 46.7–52.1 / 46.0–51.4 |
| wash-control: range fills after a drag | 5 | | 9 | | 10 |

Chrome's own earlier record on the 134 page (`../../../134/guard/132-b/`: deleted per hold 25, last delete after release 61.3–92.4 ms, band fresh 73.9–104.0 ms) is the same shape; one Chrome value is above that page's range (high hold round 0: last delete 115.8 ms against 92.4, band fresh 130.4 ms against 104.0); the other eleven holds are not above it. The judge's thresholds (§5.2: `deletesAfterRelease` ≤ 2, shown ≥ done − 2, no wash, no ghost) hold in all twelve holds; I compared against no threshold other than the judge's.

## Limits of this reading

Unchanged from `../../../132/132-b/README.md`: the `repeat` flags are set by the drivers (CDP `autoRepeat`, WebDriver), not by the owner's keyboard path; (b) reads the band holding the caret's top row only; devicePixelRatio 1 only. This run holds in the middle of the document; it says nothing about holds that end in a refusal.
