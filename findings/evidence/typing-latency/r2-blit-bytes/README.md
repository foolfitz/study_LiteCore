# R2 and R1: bytes blitted per key, and what the invalidations carry (diagnostic, 2026-10-10)

Registered by spec `SPEC-M3-production-ui.md` §15.8 under finding 122 (fixed): **R2** — `updateState()` → `paint()` re-blits the whole canvas on every state write, ≈ 6 per key on both pages; measure the bytes blitted per key, v58 against A+B, before any design. **R1** — A′ (skip an invalidation the running pass already covers) is admissible only if every invalidation after an insert carries the post-increment revision; record the `document-invalidated` revisions. The owner chose to measure R2 next (2026-10-10, after the hand test of 0.2.10 passed). Nothing here counts and no product byte changes.

Instrument: `blit_bytes_probe.py` (header says exactly what it patches, all in memory or in the served mirror; `dist/` untouched). It runs the 122 probe `dbad93c0…` with its dataset writes coalesced (rule pp), times and counts every native `putImageData` (bytes = width × height × 4; first blit of an image = fresh, later = stale re-blit), snapshots the counters at every keydown, and has the served worker copy add the LOK callback id and payload to each `document-invalidated`. `--page v58` serves the v58 page `537d62d7…` from the mirror.

## Smoke run (boundaries, Chrome, gap 600 × 4, page A+B; scratch, not kept)

Canvas 725 × 2,007 (two bands). Per key: **6.0 canvases re-blitted** (12 stale calls in three same-task groups of 3, 2 and 1 canvas, the first group 1 ms after the keydown, i.e. before the commit), 2.0 ms inside `putImageData`; fresh 1.0 canvas. Invalidations: **one per key, all LOK id 1 (`INVALIDATE_VISIBLE_CURSOR`), payload the cursor rectangle, all carrying the post-increment revision; no id 0 (`INVALIDATE_TILES`) at all**, including for the End key before typing.

## Predictions (written before the owner-document runs)

Owner document, gap 600 × 10 (idle floor) and gap 80 × 20, pages v58 and A+B, Chrome and Firefox (8 runs, sequential).

1. Stale re-blits per key at gap 600: **6 ± 1 canvases on both pages** (the number of state writes per key does not depend on the banding). Stale bytes per key differ by < 15 % between v58 and A+B in each browser.
2. Time inside `putImageData` for those re-blits per key, gap 600: Chrome 10–30 ms (the smoke run's 2.0 ms × the canvas ratio ≈ 9 ≈ 18 ms), Firefox 15–60 ms (no reference). Equal within ± 20 % between the two pages in each browser.
3. Fresh per key at gap 600: v58 1.0 canvas; A+B 1.0 canvas plus 1–2 bands (≤ 1.15 canvases).
4. Hence R2 does **not** explain the ≈ 8 ms rise of the A+B idle floor over v58 (the bytes and time are the same on both pages); it is a cost both pages pay, of the order of a commit's whole budget.
5. R1: every invalidation after a key carries the post-increment revision (pre = 0), and only LOK id 1 appears, in both browsers and on both pages.
6. Gap 80: per-key mean stale re-blits 4–7 canvases on both pages.

If prediction 5 holds, it also bears on registration C (forward the invalidated rectangle): the only rectangle there is to forward during typing is the cursor's.

## Results (2026-10-10 00:00 UTC; eight reports `r2-{v58,current}-{chrome,firefox}-owner-gap{600,80}.json`; log `run-2026-10-10.log`)

All eight exit 0, wrapper as committed in `179a9efc`. Canvas: Chrome 725 × 17,929 (52.0 MB), Firefox 900 × 22,257 (80.1 MB); A+B bands: 18 (Chrome), 22 (Firefox). Per key, medians (gap 80 rows of v58 are backlogged — the original finding 122 — and are listed for completeness only):

| Browser | Gap | Page | Stale re-blits (canvases) | Time in stale `putImageData` | Fresh (canvases) | Time in fresh `putImageData` | Key → committed (median / max) | Key → on screen (median / max) |
|---|---|---|---|---|---|---|---|---|
| Chrome | 600 | v58 | 6.0 | 20.8 ms | 1.0 | 3.3 ms | 35.8 / 40.6 | 147.2 / 163.9 |
| Chrome | 600 | A+B | 6.0 | 20.3 ms | 1.0 | 3.2 ms | 34.8 / 55.1 | 48.7 / 55.3 |
| Firefox | 600 | v58 | 6.0 | 32.1 ms | 1.0 | 5.0 ms | 44.7 / 52.6 | 200.7 / 261.3 |
| Firefox | 600 | A+B | 6.0 (mean 6.4) | **46.1 ms** | 1.0 | **101.0 ms** | 54.2 / 104.0 | 67.9 / 106.1 |
| Chrome | 80 | v58 | 6.0 | 21.0 ms | 1.0 | 3.3 ms | 509.7 / 957.5 | 612.9 / 1049.2 |
| Chrome | 80 | A+B | 6.0 | 20.1 ms | 0.51 | 1.6 ms | 43.0 / 52.0 | 35.3 / 58.7 |
| Firefox | 80 | v58 | 4.0 (mean 5.1) | 23.6 ms | 0.0 (mean 0.85) | 0.0 ms | 861.6 / 1508.1 | 996.4 / 1628.9 |
| Firefox | 80 | A+B | 6.0 | 42.5 ms | 0.23 | 26.9 ms | 72.2 / 81.0 | 51.0 / 71.9 |

Where the six re-blits sit (Chrome gap 600, both pages, read from `raw.r2.groups` against the keydown): a same-task group of **3 canvases ≈ 1 ms after the keydown (≈ 9.5 ms)**, a group of **2 at ≈ +26–31 ms (≈ 6.3 ms) that ends just before `#s-revision` shows the new revision**, and 1 after. Read against the source (`editor-shell/editor-session.js` `_enqueue`/`_drain`, :266, :285, :291, :307, :333): every `state.update`/`transition` calls the page's `onState` → `updateState()` → `paint()` synchronously; an insert from idle writes `pending` (enqueue), `busy` (drain start) and `pending` (dequeue) **before** `item.operation` posts the insert to the Worker, then `revision/editorState` and `ready` in the same continuation after the reply. So five of the six whole-canvas re-blits are on the commit path: three delay the dispatch itself, two delay the moment the revision is shown (the probe's observer fires after the synchronous `paint()`).

R1, read without time windows (backlog makes window attribution meaningless): after the first typed key, every revision base+1 … base+N is carried by **exactly one** `document-invalidated`, none carries the pre-insert revision, none is out of range, and every one is LOK id 1 — 140 keys over eight runs. The only gap: Firefox v58 gap 80 has no event for revisions 18–20 (17 of 20; backlog, coalesced), which is a missing event, not a pre-increment one. **No id 0 (`INVALIDATE_TILES`) arrived in any run.**

### Against the predictions

1. Six ± 1 canvases on both pages, bytes within 15 %: **hit** (6.0 everywhere at gap 600; identical bytes per page in each browser).
2. Chrome 10–30 ms, Firefox 15–60 ms: **hit** (20.3–20.8; 32.1, 46.1). Equal within ± 20 % between pages: Chrome **hit** (2 %), Firefox **miss** — the same bytes re-blitted as 22 band calls cost 46.1 ms against 32.1 as six whole-canvas calls (+44 %).
3. Fresh 1.0 / ≤ 1.15 canvases: **hit** (1.0 / 1.0). Not predicted: Firefox A+B spends **101 ms per key inside fresh `putImageData`** at gap 600 against 5.0 on v58 for the same bytes (22 calls ≈ 4.6 ms each against one call of 80 MB in 5 ms).
4. "R2 does not explain the A+B idle-floor rise": **miss in Firefox**. The bytes are equal but the banded re-blit costs ≈ 14 ms more per key, five-sixths of it on the commit path (≈ 12 ms); the floor here is v58 44.7 against A+B 54.2 (+9.5), the lazy-shim reading was +8. In Chrome there is neither a per-call penalty nor a floor rise (35.8 against 34.8).
5. R1 post-increment only, id 1 only: **hit** on both pages and both browsers (read as above).
6. Gap 80, four to seven canvases per key: **hit** (6.0, 6.0, 4.0 with mean 5.1 on the backlogged v58, 6.0).

### What this says (diagnostic reading; nothing here is a criterion)

- **R2 is the largest main-thread cost per key left on the shipped page**: 20 ms (Chrome) and 42–46 ms (Firefox) of `putImageData` per typed character, ≈ 5/6 of it before the commit is visible. In Firefox at gap 80 that is more than half of the 80 ms between keys.
- **In Firefox, most of A+B's floor rise is R2 multiplied by the band count**: the same bytes cost ≈ 0.35 ms × 22 calls per paint against one call; five of the six paints sit on the commit path. Separately, and not yet placed on or off the commit path, Firefox's first blit of each fresh band image costs ≈ 4.6 ms (101 ms per key at gap 600, mostly during the background pass).
- **R1 (A′) is admissible** by fable's criterion on this evidence.
- **Registration C's premise does not hold during typing**: the engine delivered no `INVALIDATE_TILES` at all; the only rectangle the Worker could forward is the cursor's. Whether id 0 is never emitted in this engine build or only not while typing is not measured here (discovery-era reports, e.g. `../../sdk-e2/discovery/wedge-split/`, do record `invalidate-tiles` as an editor-state source).

## What-if arm: the stale re-blits skipped (predictions written before the runs)

`--skip-stale` (wrapper change after the eight runs; the eight reports above carry the earlier wrapper hash): the shim still counts every stale re-blit but does not pass it to the native call, so the page pays nothing for `paint()`'s whole-canvas re-blit while everything else runs as shipped. The overlay draws over old pixels; only timing is read. It bounds from above what removing R2 could buy, since a real fix would still re-blit the overlay's old and new rectangles (small). Fresh blits are logged per call. Runs: A+B page, owner document, Chrome and Firefox, gap 600 × 10 and gap 80 × 20, each paired with a same-session baseline run (no skip) immediately before it; eight reports `whatif-{base,skip}-{browser}-owner-gap{gap}.json`.

Predictions:

1. Baselines repeat the earlier A+B rows within run-to-run spread (commit median ± 6 ms).
2. Commit median, skip against its baseline: Chrome gap 600 drops by 12–20 ms (≈ 5/6 of 20.3), gap 80 by 10–20; Firefox gap 600 by 25–40 ms (≈ 5/6 of 46), gap 80 by 20–35.
3. On screen median drops in both browsers, by less than the commit (the visible band's render is a Worker round trip that the re-blits only delay when they overlap it): Chrome 5–20 ms, Firefox 10–35 ms.
4. Fresh blits are unchanged in count; in Firefox the per-call time of fresh blits stays ≈ 4–5 ms with or without the skip (i.e. it is not the stale re-blits' doing).

### What-if results (2026-10-10 00:03–00:06 UTC; `whatif-*.json`, log `whatif-2026-10-10.log`; all eight exit 0, page `18c8afbe…`)

| Browser | Gap | Arm | Stale time / key | Fresh time / key (per call, median) | Key → committed (median / max) | Key → on screen (median / max) | All current after last key |
|---|---|---|---|---|---|---|---|
| Chrome | 600 | baseline | 19.5 ms | 3.1 ms (0.18) | 35.7 / 48.7 | 48.3 / 52.7 | 205.6 |
| Chrome | 600 | skip | 0.0 | 3.2 ms (0.18) | **16.8** / 23.0 | **28.8** / 37.3 | 183.6 |
| Firefox | 600 | baseline | 42.6 ms | 85.8 ms (4.94) | 53.2 / 64.3 | 65.9 / 67.3 | 316.1 |
| Firefox | 600 | skip | 0.0 | 85.7 ms (4.96) | **29.4** / 42.7 | **40.6** / 43.4 | 297.2 |
| Chrome | 80 | baseline | 19.3 ms | 1.8 ms (0.18) | 41.9 / 51.6 | 34.1 / 50.0 | 199.3 |
| Chrome | 80 | skip | 0.0 | 1.8 ms (0.18) | **25.7** / 37.0 | **24.6** / 35.6 | 171.1 |
| Firefox | 80 | baseline | 35.2 ms | 24.6 ms (4.84) | 60.5 / 74.5 | 45.2 / 69.0 | 319.3 |
| Firefox | 80 | skip | 0.0 | 25.4 ms (5.10; one call 44.1) | **38.9** / 73.9 | **31.6** / 70.2 | 315.1 |

Removing the stale re-blits, against the paired baseline: commit median −18.9 / −16.2 ms (Chrome, gap 600 / 80), −23.8 / −21.6 ms (Firefox); on screen −19.5 / −9.5 (Chrome), −25.3 / −13.6 (Firefox). That is 37–48 % of the commit and 28–38 % of the on-screen time.

Against the what-if predictions:

1. Baselines within ± 6 ms of the earlier A+B rows: **3 of 4**. Firefox gap 80 came in at 60.5 against 72.2 (−11.7): run-to-run spread of the Firefox gap-80 commit median is wider than 6 ms (65.3, 71.1, 72.2, 60.5 over four sessions today).
2. Commit drops: Chrome 600 (12–20) **hit** 18.9; Chrome 80 (10–20) **hit** 16.2; Firefox 600 (25–40) **miss**, 23.8; Firefox 80 (20–35) **hit** 21.6.
3. On-screen drops in range: **4 of 4**. "By less than the commit": **hit** at gap 80, **miss** at gap 600 (the on-screen drop equals or slightly exceeds the commit drop, 19.5 vs 18.9 and 25.3 vs 23.8) — at idle the visible band's render waits behind the same re-blits.
4. Fresh blits unchanged in count and, in Firefox, ≈ 5 ms per call with or without the skip: **hit**. Firefox's first blit of a new `ImageData` costs ≈ 5 ms regardless of its size (one 80 MB canvas on v58: 5.0 ms; one 3.7 MB band: 4.9 ms); Chrome's is 0.18 ms. Most of it falls in the background pass (≈ 22 × 5 ms per pass), not on the commit path.

Scaling not measured here: the canvas backing width is `min(2400, cssWidth × devicePixelRatio)` (`web/e2-editor-app.js` `layoutCanvas`), and its height follows, so on a display with devicePixelRatio 2 each canvas — and every re-blit — carries four times these bytes. The headless runs above are at ratio 1.

## devicePixelRatio 2 (predictions written before the runs)

`--dpr 2` (wrapper change after the what-if runs): Chrome gets `Emulation.setDeviceMetricsOverride` (CSS viewport kept, ratio 2) before the first navigation; Firefox gets `layout.css.devPixelsPerPx = 2`, which halves the CSS viewport of the headless window, so the two browsers' canvases differ more than at ratio 1. READ now samples three 120-row strips (caret line, middle, end) for transparent pixels (never drawn) and opaque ink. The smoke runs (boundaries, scratch) caught the first version counting transparent black as ink — exactly the blank canvas it was meant to see — and it was fixed before any run below. Smoke at ratio 2, boundaries: Chrome canvas 1450 × 4014, Firefox 1238 × 3427, both drawn.

Runs (A+B page, owner document): ratio 2 × {gap 600, gap 80, gap 80 skip} × {Chrome, Firefox}, and a ratio-1 gap-600 control per browser for the new ink sampling — eight reports `dpr{1,2}-{base,skip}-{browser}-owner-gap{gap}.json`.

Predictions:

1. Chrome ratio 2: canvas 1450 × ≈ 35,860 (4.0 × the bytes, ≈ 208 MB); drawn (ink at the caret line; Chrome's canvas limit is 65,535 per finding 062). Firefox ratio 2: canvas ≈ 1238 × ≈ 30,600 (≈ 1.9 × the bytes, ≈ 152 MB), under 32,767, drawn. Whether a Firefox canvas taller than 32,767 draws at all is **not** reached by this configuration.
2. Stale re-blit time per key at gap 600: Chrome 60–100 ms, Firefox 65–110 ms. Six canvases per key as before.
3. Commit median at gap 600: Chrome 60–110 ms, Firefox 70–120 ms.
4. **Gap 80 backlogs again in both browsers on the shipped page**: commit median > 80 ms and the last-five median above the first-five.
5. Gap 80 with the re-blits skipped: no backlog; commit median < 50 ms in both.
6. Ratio-1 controls: canvases as in the eight earlier runs, ink > 0 in the caret-line strip, not all transparent.

### devicePixelRatio 2 results (2026-10-10 00:11–00:14 UTC; `dpr*.json`, log `dpr-2026-10-10.log`; all eight exit 0; wrapper `73396c96`)

| Browser | Ratio | Arm | Gap | Canvas | Stale time / key | Key → committed median (first five / last five) / max | On screen median / max | Caret-line strip: ink, transparent of pixels |
|---|---|---|---|---|---|---|---|---|
| Chrome | 1 | base | 600 | 725 × 17,929 (52 MB) | 19.3 ms | 35.0 (36.8 / 33.0) / 43.2 | 46.7 / 61.9 | 11,651; 2,880 of 87,000 |
| Chrome | 2 | base | 600 | 1450 × 35,858 (208 MB) | 73.5 ms | 104.5 (104.2 / 104.5) / 121.3 | 81.4 / 120.3 | 19,463; 6,840 of 174,000 |
| Chrome | 2 | base | 80 | same | 73.3 ms | **106.7** (116.0 / 104.6) / 124.9 | 66.8 / 119.6 | 19,075 |
| Chrome | 2 | skip | 80 | same | 0.0 | **34.5** (34.1 / 34.5) / 50.2 | 33.3 / 49.0 | 19,085 |
| Firefox | 1 | base | 600 | 900 × 22,257 (80 MB) | 43.3 ms | 52.2 (53.7 / 51.6) / 58.1 | 66.1 / 74.2 | 12,874; 3,720 of 108,000 |
| Firefox | 2 | base | 600 | 1238 × 30,616 (152 MB) | 83.5 ms | 118.2 (118.2 / 108.6) / 194.0 | 82.7 / 183.6 | 19,110; 5,640 of 148,560 |
| Firefox | 2 | base | 80 | same | 78.9 ms | **105.6** (101.8 / 105.6) / **171.2** | 68.9 / 115.9 | 18,810 |
| Firefox | 2 | skip | 80 | same | 0.0 | **59.8** (56.6 / 57.2) / 111.6 | 33.3 / 101.7 | 18,810 |

Against the predictions: 1 **hit** (canvases as computed, all drawn). 2 **hit** (73.5, 83.5). 3 **hit** (104.5, 118.2). 4 half: commit median > 80 in both (**hit**), growth (last five above first five) only in Firefox (101.8 → 105.6), **not** in Chrome (116.0 → 104.6) — at ratio 2 the shipped page runs saturated rather than diverging. 5 Chrome **hit** (34.5), Firefox **miss** (59.8 against < 50). 6 **hit** (ink in every strip; transparent pixels are the page margins).

Read against 122-B's restated commit cell (§15.8; not a criterion here, the window and ratio differ from the counted runs): at ratio 2 and gap 80 the shipped page would fail (b) "median < gap" in both browsers (106.7, 105.6) and (a) "every key < 160" in Firefox (171.2); with the re-blits skipped it would pass both in both. On-screen medians stay under 70 ms at gap 80 — the cost lands on the dispatch and the commit, then on everything queued behind them.

Not reached: a window wide enough for the page's 900-px cap. Then the backing width is 1800, this document's canvas 1800 × ≈ 44,500 (≈ 320 MB), and Firefox's canvas would be taller than 32,767, which has never been measured in Firefox (finding 062's sweep was Chrome, whose limit is 65,535).

## Ratio 2 in a window wide enough for the 900-px cap (predictions written before the runs)

`--window 1400x1000` (wrapper change after the ratio-2 runs): Chrome's Emulation call gets that CSS viewport; Firefox's headless screen is sized by `MOZ_HEADLESS_WIDTH/HEIGHT` = 2800 × 2000 device pixels. Smoke (boundaries, scratch): both canvases 1800 × 4982, drawn. Runs: owner document, ratio 2, window 1400 × 1000, {gap 600, gap 80, gap 80 skip} × {Chrome, Firefox} — `wide-{base,skip}-{browser}-owner-gap{gap}.json`.

Predictions:

1. Both canvases 1800 × ≈ 44,500 (≈ 320 MB per canvas).
2. Chrome draws it (its limit is 65,535). **Firefox: not known**; I lean (≈ 60 %) to the canvas not drawing at all — every strip transparent, no ink — because I believe Firefox's maximum canvas side is 32,767. If it draws, everything below is about cost; if it does not, that is a defect of finding 062's class on the shipped page (a long document blank on a ratio-2 display in Firefox) and is recorded as a finding candidate before anything else.
3. Chrome stale re-blit time per key 90–140 ms; commit median at gap 600 130–190 ms.
4. Chrome gap 80 diverges: commit median > 120 ms and last five above first five.
5. Chrome gap 80 with the re-blits skipped: commit median < 50, no growth.
6. If Firefox draws: stale 140–220 ms per key, gap 80 diverges, skip brings the commit median under 80.

### Wide-window results (2026-10-10 00:16–00:18 UTC; `wide-*.json`, log `wide-2026-10-10.log`; all six exit 0; wrapper `dc891cd0`)

Canvas 1800 × 44,514 (321 MB) in both browsers; ink in all three strips in every run (caret line 25,974, middle ≈ 17,800, end 12,647).

| Browser | Arm | Gap | Stale time / key | Key → committed median (first five / last five) / max | Key → on screen median / max | Fresh first blit, per call (median) |
|---|---|---|---|---|---|---|
| Chrome | base | 600 | 112.6 ms | 164.2 (168.1 / 159.2) / 171.8 | 125.6 / 178.4 | — |
| Chrome | base | 80 | 111.2 ms | **425.7** (465.2 / 408.0) / 516.9 | **368.5 / 595.8** | — |
| Chrome | skip | 80 | 0.0 | **46.8** (46.8 / 42.4) / 86.3 | **47.0** / 84.9 | 0.44 ms |
| Firefox | base | 600 | 155.1 ms | 215.2 (215.2 / 214.7) / 220.9 | 108.7 / 135.0 | 22.6 ms |
| Firefox | base | 80 | 146.4 ms | 208.1 (204.4 / 204.6) / 226.8 | 90.5 / 109.2 | 22.9 ms |
| Firefox | skip | 80 | 0.0 | **158.8** (158.8 / 142.8) / 214.5 | 81.6 / 122.5 | 24.3 ms |

Against the predictions: 1 **hit**. 2 Chrome **hit**; Firefox **miss** — it draws a 44,514-row canvas (the lean to "blank" was wrong; there is no finding-062-class defect here). 3 **hit** (112.6; 164.2). 4 median **hit** (425.7), growth **miss** (465.2 → 408.0: saturated with a large lag, not diverging within 20 keys) — on screen the characters arrive 368 ms late at the median and up to 596 ms, finding 122's symptom back on this configuration. 5 **hit** (46.8, no growth). 6 Firefox: stale 155 **hit**; growth **miss** (204.4 / 204.6); "skip brings the commit under 80" **miss** (158.8).

Why Firefox stays slow without the re-blits (key 3 of each run, read from `raw.r2`): in the skip arm at gap 80 the invalidation that marks the insert done arrives **86 ms** after the keydown and the visible band is blitted at +110 (a 30 ms first blit); at gap 600 the background pass after one key is 44 bands, each first blit ≈ 22 ms on the main thread (≈ 5 ms at ratio 1 and 900 px wide). So on this configuration two costs besides R2 dominate: the Worker is busy rendering background bands when the insert arrives, and Firefox's first blit of each new band image is slow at this width. Both come from repainting the whole document after every change; neither is touched by removing the re-blits. Chrome without the re-blits is fine (46.8 / 47.0).

## Canvas micro-bench (for brief 4; predictions written before the runs)

`canvas-bench/bench.html` + `run_bench.py`: no product code. A fresh canvas per configuration inside an 800-px scrolling div, at destination sizes 1800 × 44,514 (the wide ratio-2 whole document), 1800 × 2000 (a viewport-sized canvas at ratio 2), 900 × 22,257 (the ratio-1 whole document), 900 × 1000; bands of width × 1023; 12 repetitions each of: `putImageData` of a new `ImageData` (the page's fresh band), of the same one again (the page's re-blit), `createImageBitmap` (async) + `drawImage` of a new bitmap, and `drawImage` of the same bitmap again — each also with a 1-pixel `getImageData` after it ("+flush") to force deferred work. Times are main-thread time.

Predictions:

1. Firefox reproduces the product: fresh `putImageData` ≈ 15–30 ms into 1800 × 44,514 and ≈ 3–8 ms into 900 × 22,257.
2. **The cost is the destination's**: into the viewport-sized canvases (1800 × 2000, 900 × 1000) fresh `putImageData` is under a third of its whole-document value in Firefox. (If not, a viewport canvas alone does not remove it.)
3. `drawImage` of an `ImageBitmap` costs under 2 ms per call in both browsers and both destination sizes, without flush.
4. Chrome: every call under 2 ms.

### Micro-bench results (2026-10-10; `canvas-bench/bench-{chrome,firefox}.json`; Chrome 151, Firefox 157, ratio 1)

Medians / max in ms over 12 calls (Firefox's timer here is 1 ms — the page is not cross-origin isolated — so its values are whole milliseconds):

| Browser | Destination | fresh put | same put again | createImageBitmap (async) | drawImage new bitmap | drawImage same bitmap |
|---|---|---|---|---|---|---|
| Firefox | 1800 × 44,514 | **26** / 358 | **24** / 26 | 9 / 14 | **28** / 40 | **24** / 25 |
| Firefox | 1800 × 2000 | 2 / 12 | 1 / 3 | 9 / 10 | 5 / 6 | 1 / 2 |
| Firefox | 900 × 22,257 | 6 / 86 | 0 / 7 | 2 / 4 | 7 / 8 | 0 / 6 |
| Firefox | 900 × 1000 | 1 / 3 | 0 / 0 | 3 / 5 | 2 / 3 | 0 / 1 |
| Chrome | 1800 × 44,514 | 0.4 / 112 | 0.4 / 0.5 | 2.6 / 2.9 | 0.0 / 0.1 | 0.0 / 0.1 |
| Chrome | 1800 × 2000 | 0.4 / 5.3 | 0.4 / 0.5 | 2.6 / 3.8 | 0.0 / 0.1 | 0.0 / 0.1 |
| Chrome | 900 × 22,257 | 0.2 / 27.7 | 0.2 / 0.3 | 1.2 / 1.5 | 0.0 / 0.0 | 0.0 / 0.1 |
| Chrome | 900 × 1000 | 0.2 / 1.3 | 0.2 / 0.3 | 1.3 / 1.8 | 0.0 / 0.1 | 0.0 / 0.1 |

(The "+flush" columns are in the JSON; they change no conclusion: Chrome's `drawImage` defers ≈ 1.3–3 ms to the flush, Firefox's are the same with or without.)

Against the predictions: 1 **hit** (26; 6). 2 **hit, strongly** — in Firefox a blit costs what the destination costs: ≈ 24–28 ms per call into the 321 MB canvas by every method, 1–5 ms into a viewport-sized one. 3 **miss** for Firefox: `drawImage` of an `ImageBitmap` is no cheaper than `putImageData` into the big canvas (24–28) and not cheaper at viewport size either (5 vs 2 fresh). 4 **hit** by median (Chrome < 1 ms per call except the async `createImageBitmap`); two first-call outliers (112, 27.7 ms) look like the backing store's allocation.

Reading: in Firefox the per-blit cost is a property of the canvas size, so a viewport-sized canvas removes it whatever the draw method; Collabora's `ImageBitmap` route by itself does not. Single blits per task here; in the product the re-blits come 18–44 to a task and cost less per call (≈ 0.6 ms in the wide Firefox run), the fresh bands one per task (≈ 22 ms there) — the bench matches the latter.

## Before release A: fable's fifth ruling, Part 5 items 1 and 3 (predictions written before the runs)

**Item 1, small blits** (`canvas-bench/bench.html?small=1`, `run_bench.py --small`): a 64 × 64 `ImageData` into destinations 1800 × 44,514, 1350 × 33,400 (ratio 1.5 at the 900-px cap), 1238 × 30,616, 900 × 22,257, 1800 × 2000, 900 × 1000; per task the first blit and a second one, and separately a 64 × 64 `ImageBitmap` `drawImage` per task. Prediction (mine, against fable's two-way split): in Firefox the cost is **per task, not per call** — in the product the re-blits that come 18–44 to a task cost ≈ 0.6 ms each while a band alone in its task costs ≈ 22 ms — so the **first** small blit per task costs about what a band did (≈ 15–30 ms into the 321 MB canvas, ≈ 4–8 into the 80 MB one) and the **second** in the same task < 1 ms. If the first small blit is ≤ 1 ms instead, the cost is per byte and A reaches ratio-2-narrow Firefox (fable's first branch). Chrome < 1 ms everywhere.

**Item 3, ratio 1.5 wide, emulated** (`blit_bytes_probe.py --dpr 1.5 --window 1400x1000`, shipped page, owner document, gap 80 × 20, base and `--skip-stale`, both browsers — `dpr15-{base,skip}-{browser}-owner-gap80.json`). Fable's predictions on the shipped page: Chrome commit median 150–250 (fails §15.8 (b)), Firefox 120–160 (fails (b), (a) borderline). Mine: canvas 1350 × ≈ 33,400 in both; Chrome base 110–200, skip 30–45; Firefox base 100–160, skip 50–110; the finding-123 toast does not appear (remainder 33,400 mod 1023 ≈ 664 rows, far above twice the ≈ 26-row gap).

### Results of items 1 and 3 (2026-10-10 00:45–00:47 UTC; `canvas-bench/bench-small-*.json`, `dpr15-*.json`, log `pre-a-2026-10-10.log`; all exit 0)

Item 1, Firefox (whole ms; medians / max): first 64 × 64 `putImageData` in a task — **22** / 328 into 1800 × 44,514, **15** / 170 into 1350 × 33,400, 10 / 169 into 1238 × 30,616, 6 / 90 into 900 × 22,257, 0 / 12 and 0 / 3 into the viewport-sized ones; **the second in the same task 0 / 0 everywhere**; a 64 × 64 `ImageBitmap` `drawImage` per task **0** / 25, 0 / 16, 0 / 10, 0 / 0, 0 / 1, 0 / 0. Chrome: every cell 0 / ≤ 0.1. My prediction (per task, not per call; first ≈ a band's cost, second < 1 ms) **hit**; fable's branch is the second one (≈ 22 ms: Firefox HiDPI is C′'s). Not predicted: a small `drawImage` per task costs nothing at the median — the per-task surface cost belongs to `putImageData`, while a large `drawImage` (the first bench, a 1800 × 1023 bitmap) paid ≈ 24–28.

Item 3, ratio 1.5 wide (canvas 1350 × 33,385 in both), gap 80 × 20:

| Browser | Arm | Stale / key | Commit median (first five / last five) / max | On screen median / max | All current after last key |
|---|---|---|---|---|---|
| Chrome | base | 67.9 ms | 102.6 (100.3 / 109.0) / 133.3 | 77.3 / 121.5 | 732.6 |
| Chrome | skip | 0.0 | 35.5 (35.4 / 34.3) / 54.6 | 34.5 / 56.8 | 626.3 |
| Firefox | base | 104.7 ms | 151.6 (137.1 / 155.9) / 183.9 | 92.3 / 129.4 | 981.2 |
| Firefox | skip | 0.0 | 98.1 (94.9 / 98.3) / 206.9 | 63.2 / 161.1 | 1052.0 |

Against the predictions: fable's shipped-page Chrome 150–250 **miss** (102.6, low), Firefox 120–160 **hit** (151.6; max 183.9 fails (a) too). Mine: Chrome base 110–200 **miss** (low), skip 30–45 **hit**; Firefox base 100–160 **hit**, skip 50–110 **hit**; no finding-123 toast **hit**. So on the buyer's default 150 % laptop with a maximized browser the shipped page fails §15.8 (b) in both browsers; without the re-blits Chrome passes (35.5) and Firefox does not (98.1 > 80; the skip arm is an upper bound for A).

## Release A's restore method (prediction written before the run)

`bench.html?restore=1`: one 64 × 64 restore per task from a cached 1023-row band — `putImageData(band, 0, 0, dirtyX, dirtyY, 64, 64)` against `drawImage(bandBitmap, sx, sy, 64, 64, dx, dy, 64, 64)` — into the same six destinations. Prediction: in Firefox the dirty-rect `putImageData` pays the per-task surface cost of item 1 (≈ 22 / 15 / 10 / 6 ms into the four whole-document sizes), the sub-rectangle `drawImage` from a bitmap does not (median ≤ 1 ms). Chrome ≤ 0.1 both.

### Restore-method results (2026-10-10; `canvas-bench/bench-restore-{chrome,firefox}.json`)

Firefox, one 64 × 64 restore per task (medians / max, whole ms): dirty-rect `putImageData` from the cached band — **27** / 345, **16** / 161, 10 / 166, **6** / 84 into the four whole-document sizes, 0 / 12 and 0 / 3 into the viewport-sized ones; sub-rectangle `drawImage` from the band as an `ImageBitmap` — **23** / 31, **13** / 16, 8 / 10, **5** / 44, 0 / 11, 0 / 5. Chrome ≤ 0.1 for both everywhere.

Prediction **missed**: the sub-rectangle `drawImage` is not cheaper; both restores pay Firefox's per-task cost of the whole-document canvas. Only a draw whose **source** is small (item 1's 64 × 64 bitmap) escaped it. Consequence for release A as fable specified it (restore the old and new overlay rectangles from the band cache): in Firefox each paint task that changes the overlay costs ≈ 6 ms at ratio 1 (900-px canvas), ≈ 16 at ratio 1.5 wide, ≈ 25 at ratio 2 wide — one such task per typed key if only the caret's state write changes the overlay. A's Firefox ratio-1 predictions (fable: commit 36–45) should carry ≈ + 6 ms. A design that keeps the caret and selection off the document canvas altogether (DOM elements over `.paper`, positioned like `#sink`) would pay nothing per key in either browser, but moves the product-path's canvas-ink caret/selection checks into release A — a design question, not settled here.
