# Long-hold ghost, A/B over three pages (2026-10-12)

Same instrument, same host, same session file, same day: `probe_hand_test_0212.py --arms high,low --ghost-rapid-keys 20` (tree `4797df0d`; script `../ghost-20-ab.sh`): type 24 letters, 4 single Backspaces, then 20 Backspaces 50 ms apart. `high` = the caret in the first band under the view; `low` = the caret in the second band with the first also in view. The engine package was swapped per page (`log.txt`) and the fixed one restored afterwards (`check-engine-decoded-after.txt`, exit 0). Read by `../read_ghost_long.py` (`read.txt` in each directory; the fixed page's run is `../ghost-20/`).

| Page (served) | low: band under the caret first repainted, ms after key 1 (Chrome / Firefox) | low: first deleted character drawn after the caret moved | high: worst key | `persistent.differing` (characters left behind), high/low × Chrome/Firefox |
|---|---|---|---|---|
| 0.2.12 `8909564e…` | 1049.6 / 1160.5 | 1005.7 / 1114.8 ms | 562.9 / 465.2 ms | 21778 / 13843 / 22753 / 13843 |
| 0.2.13 pre-fix `c7f904fa…` | 1072.7 / 1234.1 | 1030.0 / 1188.0 ms | 138.6 / 77.8 ms | 20606 / 47938 / 23122 / 13748 |
| 0.2.13 fixed `d761f1ce…` | 1319.1 / 1341.9 | 1274.1 / 1296.2 ms | 281.0 / 286.3 ms | 0 / 0 / 0 / 0 |

Reading:
- With the caret below the first band, the band under it is not repainted at all while a 1 s burst lasts, on **all three pages**: every key's band turns fresh at the same instant, about 0.0–0.3 s after the last key. This is older than rule A (0.2.12 has it) — the band order H2 of `../../128/README.md`, which the 4-key arms could not separate. Rule A makes it about 20 % longer (every key now executes; before, refused keys did no work).
- On the two pages without rule A, a 20-key burst leaves characters in the document (131 at scale). On the fixed page, none.
- The 4-key rapid clause of 128-B (low arm 167–224 ms on the fixed page against 90–96 pre-fix) is the short end of the same thing: in a 4-key burst a refusal happened to open a gap for a repaint.
