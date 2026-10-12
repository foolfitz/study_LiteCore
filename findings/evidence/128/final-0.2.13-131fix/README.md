# 128-B re-run on the 131-fixed page (SPEC-M3-autosave §9.12 step 6), 2026-10-12

Host 0.2.13 serving buildId `59e6a9fed026a0ad` (page `d761f1ce…`; `check-engine-decoded.txt` read just before). One run, `probe_hand_test_0212.py --arms high,low,selection,hostseg,hostseg-red --selection-keys Backspace,Delete` (tree `8fc9365c`), owner's document via Files, Chrome 151 then Firefox 157. The model is `../final-0.2.13/` (pre-fix page `c7f904fa…`). Numbers are `staleAfterCaretMs` (the caret moved → its band carries the change), read by `../../131/read_128b_cells.py` into `cells.txt`; `–` = the caret did not move inside that key's own 50 ms window.

| Cell | Clause | Chrome | Firefox | Pre-fix 0.2.13 (`../final-0.2.13/`) |
|---|---|---|---|---|
| single keys, high | ≤ 40 ms | 13.4 16.3 16.6 16.6 | 18.9 18.1 19.4 19.8 | 13.8–19.5 / 19.5–22.3 |
| single keys, low | ≤ 40 ms | 28.4 24.4 24.7 30.4 | 28.3 30.9 28.0 31.6 | 22.6–29.7 / 29.0–34 |
| rapid keys, high | max ≤ 60 ms | 15.3 – 80.3 23.8 | 77.3 – 76.2 85.1 | Chrome 17.2; Firefox 84.6 |
| rapid keys, low | max ≤ 60 ms | **167.1** – 100.5 25.2 | **220.5** 154.5 153.2 89.0 | Chrome 90.5; Firefox 96.4 |
| host segment | drawn before the PUT ends | PASS (23.6 ms; PUT answered 2.7 s later) | PASS (31.4 ms) | PASS / PASS |
| host segment, red control | must FAIL | FAIL (2780 ms, 1 held paint) | FAIL (2767 ms) | FAIL / FAIL |

- **Single keys: hold** (every one ≤ 40 ms). **Host segment: holds**, and its red control turns red in both browsers.
- **Rapid clause: not met.** And it is not the same number as before the fix: the low arm's worst rapid key is 167.1 (Chrome) / 220.5 (Firefox) ms against 90.5 / 96.4 pre-fix. The 131-B run of the same page, an hour earlier, read 213.9 / 223.8 (`../../131/131-B/ghost-arms.txt`): two samples agree. 0.2.12 read 125–283.
- `selection` arms (121's witness, first form): all four ran 「刪除選取 8–11 ms」 with no toast; the third clause as first read is withdrawn (spec §9.13) and judged by 121-B instead (`../../121/0.2.13-131fix-*`).

What this means for the ruling (`../ruling/fable-ruling.md` §2) is recorded in the spec, not here.
