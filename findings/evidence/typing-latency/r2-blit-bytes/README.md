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
