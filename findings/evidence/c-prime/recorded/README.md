# C1's runtime read and §17.4's recorded items on the final C′ page (2026-10-11)

Page `8909564eb2316afa…`. Predictions: `PREDICTION.md` (first part committed in `a3379456` before the first chain;
addendum committed in `56e012a6` before the second). Chains: `chain-recorded.sh` → `chain.txt` (03:47–03:49Z, probe
`05a24e26ae4999fd`; reports `recorded-*`, `h9-*`), `chain-recorded-2.sh` → `chain-2.txt` (03:51–03:53Z, probe
`f7e97486aa39ad06`; reports `recorded2-*`). Nothing here is a gate (§17.4: recorded).

## C1 (C1′, §17.9 (a)) — holds in all eight runs

| Browser, configuration | desk `clientHeight` | canvas rows | C1′ expected | `#paper` = document height |
|---|---|---|---|---|
| Chrome, ratio 2, 1400 × 1000 | 730 | **4,380** | 4,380 (the 3× term) | yes |
| Chrome, ratio 1, 800 × 600 | 251 | 4,092 | 4,092 (the 4-band floor) | yes |
| Firefox, ratio 2, 1400 × 1000 | 645 | 4,092 | 4,092 (floor: 3 × 1,290 = 3,870) | yes |
| Firefox, ratio 1, 800 × 600 | 175 | 4,092 | 4,092 (floor) | yes |

Both halves of the formula decide somewhere, so the read discriminates: Chrome ratio 2 matches only with the 3×
term (without it, 4,092 ≠ 4,380), the others only with the floor. **§17.9 N4's "W = 4,092 at 1400 × 1000 in both
ratios" does not hold for Chrome** (its desk is 730 CSS px); predicted correctly in `PREDICTION.md`, from the C6 /
C2 reports. The desk at 800 × 600 is 251 / 175 px here, not the 139 px the `windowRows` comment cites (that figure
is Chrome's default window, not an emulated 800 × 600 viewport).

## `lastTiles` bytes

Ratio 2, width 1,800: top Chrome 36.8 MB (5 bands), Firefox 29.5 MB (4 bands); after a scroll to the middle both
36.8 MB (5 bands) — as predicted; Chrome did not cross into a sixth band (the predicted risk to N4's ≤ 37 MB). Ratio
1 (width 745 / 748): 12.2–15.3 MB. All under §17.4's ≤ 60 MB.

## Fling (named limit), 20 frames × 500 CSS px from the top

| | frames with a band under the view not current | current after the last frame (second chain) |
|---|---|---|
| Chrome ratio 2 | 17 / 21 | 18.1 ms |
| Chrome ratio 1 | 10 / 21 | 19.3 ms |
| Firefox ratio 2 | 18 / 21 | 61.6 ms |
| Firefox ratio 1 | 11 / 21 | 16.0 ms |

Frames not current as predicted at ratio 2 (15–20); **current-again times miss the prediction (100–400 ms) on the
fast side**. "Current" here is the page's own `data-bands` label against `data-changes`, not the C3 / C4 probe's
second observer. **The first chain's 1,680–1,691 ms were the instrument's floor** (it slept 2.0 s before polling;
the fling takes about 0.33 s) and are not a measurement; fixed before the second chain, kept in `chain.txt`.

## H9 census (`h9-*`, R2's DIAGNOSTIC probe, unchanged, ratio 2, owner, gap 80 × 20)

Chrome and Firefox: 24 `document-invalidated` events each, **every one LOK id 1** (`INVALIDATE_VISIBLE_CURSOR`), **no
id 0** (`INVALIDATE_TILES`) — as predicted, as on the P-family page; C′ changes no engine byte.

## Save, and 125's browser positive control

Owner document (563 KB), eight saves: 517.3–723.5 ms. One save reached 700 ms — **Chrome, ratio 1 (second chain):
`busy` 723.5 ms, 「處理中」 shown at 699.9 ms after the `busy` write** (the observer stamps the write slightly after
the page starts its 700 ms timer); every save under 700 ms showed nothing, as specified. The 80-page document saved
in 231–319 ms, faster than the owner document — **the prediction (≥ 700 ms) was wrong**: save time here follows the
document's content (the owner document has images), not its page count. **Firefox's positive control was not
exercised**: no Firefox save reached 700 ms (608.6, 649.7, 662.4, 633.2 ms; 80 pages 311.3, 318.6). Registered;
125-U (fake clock, red cases) covers the 700 ms show, and Chrome's run shows it in a browser.
