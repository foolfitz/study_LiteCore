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
