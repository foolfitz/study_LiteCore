# Release P: P1 and 123-B evidence (spec SPEC-M3-production-ui §16)

Reader: `../judge_p.py` (sha256 recorded with each reading). Instrument: `../r2-blit-bytes/blit_bytes_probe.py` (sha256 prefix `3dad37cbb03a769c`, over probe `dbad93c0dcf27fbf`). Report names: `PREFIX-BROWSER-SLOT.json`, slot `p1` (ratio 1, owner, gap 600 × 10) or `123b` (`--dpr 2 --window 800x1000`, owner, gap 600 × 3).

## Red cases on the shipped page (spec §16.3; predictions written before the runs)

`dist/e2-editor-app.js` = `18c8afbe…` (shipped, host 0.2.10). Prefix `shipped`. Script `red-shipped.sh`, log `red-shipped-2026-10-10.log`.

Predictions:

- **P1, both browsers: FAIL.** Every key re-blits ≈ 6.0 whole canvases (600 %, some keys 7 or 10 as in `r2-current-*`); canvas Chrome 725 × 17,929, Firefox 900 × 22,257. Dirty-rect calls 0 (the shipped page has no 7-argument call).
- **123-B, Chrome: FAIL** on all three cells: canvas 1450 × 35,858 (an 800-px CSS window gives the same 725-px canvas as Chrome's 800 × 600 default), at least one `TILE_NOT_PAINTED` toast, `allCurrentAfterLastKeyMs` `None`, lowest band ever blitted new at y 34,782 (the 53-row band at 35,805 never).
- **123-B, Firefox: probably does NOT reproduce.** Derived, not measured: Firefox's ratio-2 default run (`dpr2-base-firefox-*`) had canvas 1238 = 619 CSS px, i.e. desk = CSS window − 24 if headless Firefox defaults to 1366 device px; at an 800-px CSS window that gives a 1472-px canvas, 36,402 rows (± 1), last band ≈ 597 rows — not short, so no toast, `allCurrent` a number, 123-B PASS on the shipped page (a red case that is not red). If so, §16.3's own instruction applies: record it, choose a Firefox window whose canvas is 1450 px wide (CSS window = 725 + 40 + Firefox's measured offset), re-specify in the spec before any implementation, and re-run Firefox's 123-B red case.

### Results (2026-10-10 01:10–01:12 UTC; `shipped-*.json`, log `red-shipped-2026-10-10.log`; all four wrapper runs exit 0)

| Slot | Chrome | Firefox |
| --- | --- | --- |
| P1 (ratio 1) | canvas 725 × 17,929; **every key 6.0 canvases (600 %)**, 108 re-blits, 0 dirty-rect, 0 `clearRect` → **FAIL** | canvas 900 × 22,257; key 0 11.0 canvases, keys 1–9 6.0 (600 %), 0 dirty-rect, 0 `clearRect` → **FAIL** |
| 123-B (`--window 800x1000`) | canvas **1490 × 36,847** (not the predicted 1450 × 35,858: the 1450 came from Chrome's 800 × 600 *default* window, whose desk is narrower); last band **19 rows** at y 36,828, entirely inside the gap below the last page; toasts `重繪失敗：TILE_NOT_PAINTED…` at 6,276.4 and 8,988.9 ms; `allCurrent` `None`; lowest band ever blitted new y 35,805 → **FAIL** on all three cells | canvas **1496 × 36,996**; last band **168 rows**, blitted 1,237.3 ms after the last key; no `TILE_NOT_PAINTED` toast; `allCurrent` 1,237.3 → **PASS — the red case is not red** |

Against the predictions: P1 both FAIL (hit). Chrome 123-B FAIL (hit), canvas size missed. Firefox did not reproduce (hit), the predicted canvas width 1472 missed (1496: Firefox's desk is the CSS window − 12, Chrome's − 15, both measured here).

**Re-specified before any implementation (spec §16.8):** Firefox's 123-B window is **797x1000**, which by the measured offsets gives Firefox the same 745-CSS-px, 1490 × 36,847 canvas as Chrome at 800x1000. Chrome's stays 800x1000. `judge_p.py` binds the window per browser. The 800-px Firefox report is kept as `shipped-firefox-123b-window800.json` (the reader now refuses it: wrong window).

### Firefox 123-B at 797x1000 (prediction written before the run)

Canvas 1490 × 36,847, last band 19 rows at y 36,828; at least one `TILE_NOT_PAINTED` toast, `allCurrent` `None`, the last band never blitted → FAIL on all three cells. Script `red-shipped-ff797.sh`, log `red-shipped-ff797-2026-10-10.log`.

Result (2026-10-10 01:13 UTC; `shipped-firefox-123b.json`, exit 0): canvas **1490 × 36,847** (hit), toasts `重繪失敗：TILE_NOT_PAINTED…` at 7,756.2 and 10,261.9 ms, `allCurrent` `None`, lowest band ever blitted new y 35,805 → **FAIL on all three cells (hit)**. `judge_p.py --page 18c8afbe… --prefix shipped` over the four shipped reports: 8 cells FAIL, exit 1 (`judge-shipped.txt`; the reading before the re-run, with the 800-px Firefox report, is `judge-shipped-before-ff797.txt`).

## judge_p.py's own red cases (spec §16.3, last point)

`../judge_p_red_cases.py` → `../judge-p-red-cases.txt`. No report passes before P exists, so the base is the four shipped reports repaired in a temp directory into a pass (P1: every key 400 bytes; 123-B: TILE_NOT_PAINTED toasts removed, `allCurrent` 700, one blit of the merged 1,042-row last band appended). Every case came out as designed: base PASS (0); K1 one key at 3 % → only that P1 cell (1); K2 one TILE_NOT_PAINTED toast → only that 123-B cell (1); K3 wrapper hash swapped → REFUSED (2); K4 no toast recorded → only the toast cell (1); K5 `allCurrent` None → only that cell (1); K6 last-band blit removed → only that cell (1); K7 one key's snapshot missing → only the typed cell (1); the real shipped reports → 8 cells FAIL (1).

## Unit red cases (123-U, P-U; `unit_red_cases.py` → `unit-red-cases.txt`)

Each mutation applied alone to `web/e2-editor-app.js`, the two test files run, the page restored (sha256 checked). Spec §16.2's red cases: **R-123** (no merge) → only 123-U red; **R-P1** (paint() back to whole-band blits) → P-U1 red (and U2–U5, which also assert on calls); **R-P2** (old rectangles not restored) → P-U2, U3, U5 red; **R-P4** (no reset in `layoutCanvas`) → only P-U4 red. Baseline 15/15.

One extra mutation, not a §16.2 red case: **R-Px** (paint() draws the overlay without the clip) stays **green**. It is an equivalent mutation, not a blind spot: every rectangle `paint()` draws is one of the new overlay's, and each of those was restored (widened) just before, so the clip never cuts anything; it is kept as §16.1 writes it, as a guard. The pixel model in `page-paint-overlay.test.mjs` would see a wash landing on an unrestored pixel (P-U3 counts washes per pixel).
