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
- **The Firefox floor rise of A+B is R2 multiplied by the band count**, not the bands' rendering: per-call overhead on re-blits (≈ 0.35 ms × 22 per paint) and, separately, slow first blits of fresh band images (≈ 4.6 ms each).
- **R1 (A′) is admissible** by fable's criterion on this evidence.
- **Registration C's premise does not hold during typing**: the engine delivered no `INVALIDATE_TILES` at all; the only rectangle the Worker could forward is the cursor's. Whether id 0 is never emitted in this engine build or only not while typing is not measured here (discovery-era reports, e.g. `../../sdk-e2/discovery/wedge-split/`, do record `invalidate-tiles` as an editor-state source).
