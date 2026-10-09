# Typing latency on the shipped page (2026-10-09; finding 122)

The owner, hand-testing host 0.2.9: "打字到文字出現在段落中，有點慢". Probe `wasm_sdk_probe/tools/probe_typing_latency.py` (shipped standalone page from `dist/`, page `537d62d7…`; the served HTML gets a pre-module script that timestamps every `putImageData`; real keys; per character: keydown → the page's revision showing it committed, and → the first blit after that). Measured before any prediction was written — an exploratory measurement, not a judged one. The first version matched revisions wrongly (the page rewrites `#s-revision` on every state update, so the first write after a key was a repeat); fixed to wait for `start + i + 1` before any of the reports below.

| Report | Browser | Document | Gap | Key → committed (median, max) | Key → on screen (median, max) |
|---|---|---|---|---|---|
| `chrome-boundaries-gap200.json` | Chrome 151 | boundaries (27 short paragraphs) | 200 ms, 6 chars | 6.3, 17.1 ms | 9.1, 22.9 ms |
| `chrome-owner-gap200.json` | Chrome 151 | the owner's 563 KB document | 200 ms, 10 chars | 35.4, 37.4 ms | 39.4, 41.3 ms |
| `firefox-owner-gap200.json` | Firefox 157 | the owner's document | 200 ms, 10 chars | 44.9, 48.5 ms | 45.7, 49.3 ms |
| `chrome-owner-gap80.json` | Chrome 151 | the owner's document | 80 ms, 20 chars | 348.5, 774.9 ms | 348.7, **862.4** ms |

At 80 ms between keys the lag GROWS: character i commits about 120 ms after character i−1 (revisions 1 → 2 → 3 … at 38, 202, 333, 455, 577 … ms), so every key adds ~40 ms of backlog — 20 characters end ~0.8 s behind. At 200 ms between keys there is no backlog.

Why, read from the source: `renderDocument` (`web/e2-editor-app.js` ~:803) re-renders the WHOLE canvas, which is the whole document (the owner's ~22 pages), strip by strip through the document Worker, after every change (`document-invalidated` → `renderDocument`). The next character's insert waits in the same Worker behind that repaint. The Worker's `document-invalidated` event carries only the handle and revision (`sdk/sdk-worker.js` ~:1111), not the invalidated rectangle LOK reported, so the page cannot repaint only what changed.

## Correction (2026-10-10, fable's fact check, verified by the main session; replaces the "on screen" column above)

The "key → on screen" column does NOT measure the character appearing. The probe took the first `putImageData` after `#s-revision` changed; `updateState` writes that element and immediately calls `paint()`, which re-blits the CACHED tiles (the old picture) plus the caret (`web/e2-editor-app.js` :613, :665, :960–963). Paint − revision is 3.8–4.1 ms on every Chrome row at gap 200, 0.7–0.9 ms on Firefox, 0.1–4.2 ms on rows 0–18 at gap 80. The column is renamed **"next overlay blit (stale tiles)"**. The only direct observation of new text on screen is row 19 of `chrome-owner-gap80.json`: 87.5 ms after its revision. So on the owner's document a character appears roughly **revision + 85–90 ms ≈ 120–135 ms after its key in Chrome at ordinary speed** (unmeasured as such; an estimate from that one row) — every keystroke is slow, not only bursts. The "key → committed" column and the backlog at gap 80 stand. Acceptance must use the fixed instrument (`ruling/fable-ruling.md`, CONDITIONS).

## The fixed instrument on the current page (2026-10-10; the ruling's red case for the instrument)

`probe_typing_latency.py` (sha256 `40e119324bb35770…`) now counts "on screen" only when a FRESH image (a new `ImageData`, i.e. a new render) is blitted over the caret line and its paint reply carried that character's revision or a later one; the old metric is kept as `overlayBlitMs` for comparison. On the current page (`537d62d7…`, shell v58), the owner's document:

| Report | Browser, gap | Key → committed (median, max) | Key → **on screen** (median, min, max) | old metric (overlay blit, median) |
|---|---|---|---|---|
| `v58-chrome-owner-gap200-fixed-instrument.json` | Chrome, 200 ms × 10 | 34.9, 45.4 ms | **145.7**, 131.5, 210.3 ms | 38.8 ms |
| `v58-firefox-owner-gap200-fixed-instrument.json` | Firefox, 200 ms × 10 | 43.0, 50.5 ms | **187.3**, 174.2, 215.9 ms | 43.6 ms |
| `v58-chrome-owner-gap80-fixed-instrument.json` | Chrome, 80 ms × 20 | 508.2, 814.6 ms | **611.0**, 177.4, 903.9 ms | 461.7 ms |

The ruling predicted the fixed instrument would read about revision + 80–100 ms at gap 200; it reads revision + ≈ 111 ms (Chrome) and ≈ 144 ms (Firefox) — a little above, and nowhere near the 4 ms of the stale blit, so it tells a new render from a re-blit. These three reports are today's baseline and the acceptance criteria's red case (targets: median < 70 / < 90 ms, max < 150 ms).

## Acceptance on the candidate dist/ (2026-10-10; spec §15.2 122-B; page `b10f6017…`, B′ banded repaint)

Probe `probe_typing_latency.py` sha256 `dbad93c0dcf27fbf…` (adds `allCurrentAfterLastKeyMs`: after the last key, the first time every canvas row has been covered by fresh images whose paint reply carries the last character's revision or later). Six reports `v59-candidate-*.json`; numbers below are each report's `summary` block.

| Report | Key → committed (median, max) | Key → on screen (median, max) | Whole canvas current after last key | §15.2 |
|---|---|---|---|---|
| chrome owner gap 80 × 20 | 50.0, 63.9 ms | 62.3, 89.2 ms | 187.9 ms | all met |
| chrome owner gap 200 × 10 | 32.6, 48.4 ms | 50.9, 61.1 ms | 158.8 ms | all met |
| chrome boundaries gap 200 × 10 | **6.3**, 17.7 ms | 16.4, 22.9 ms | 18 ms | met |
| firefox owner gap 80 × 20 | 72.6, **93.4** ms | 79.8, 101.1 ms | **267.5** ms | commit max ≥ 80, canvas > 200 |
| firefox owner gap 200 × 10 | 91.1, 131.8 ms | **99.8**, 147.6 ms | **280.0** ms | on-screen median ≥ 90, canvas > 200 |
| firefox boundaries gap 200 × 10 | **8.1**, 11.5 ms | 17.9, 26.4 ms | 20.9 ms | met |

No backlog in either browser at gap 80 (the per-key commit delay does not grow over the 20 characters). Chrome meets every 122-B cell; **Firefox misses three**: gap-80 commit max 93.4 ms (< 80), gap-200 on-screen median 99.8 ms (< 90), whole canvas current 267.5 / 280.0 ms (≤ 200). Against the baseline (`v58-*-fixed-instrument.json`) Chrome's on-screen median went 145.7 → 50.9 ms (gap 200) and 611.0 → 62.3 ms (gap 80); Firefox's 187.3 → 99.8 ms (gap 200).

Why Firefox misses, read from the fresh-blit timeline (`raw.blits`: time, band top, rows, revision of the paint reply): the Firefox canvas is 22,257 rows (11 bands; Chrome's window gives 17,929, 9 bands), fresh band blits arrive every ≈ 18–20 ms, so a full pass takes ≈ 250 ms and a key at gap 200 usually lands inside one. Then, per key: (1) the insert waits behind the band already in flight (≈ 20 ms); (2) the page, not yet told about the change, posts the NEXT band of the old pass in its distance order — that band is rendered after the insert (its reply already carries the new revision) but it is not the visible band, ≈ 30 ms wasted; (3) only after `document-invalidated` reaches the page does the new pass start with the visible band. Example, firefox gap 200, key at 8225.7 ms: band 16376 blitted at +22.5 (old revision), band 18423 at +61.0 (new revision, off-screen), page revision shown at +78.9, band 0 (the caret's) at +87.4. The gap-80 run has the same shape (key 8631.2: +22.5 old, +54.4 new off-screen band, +83.6 visible band). Chrome at gap 200 finishes a pass before the next key, so neither (1) nor (2) happens. This reading is mine and not instrumented on the Worker side.

## Second acceptance, A+B (2026-10-10; spec §15.6; page `18c8afbe…`, commit `4353dcee`)

Same probe (`dbad93c0dcf27fbf…`), unchanged; six reports `v59-candidate2-*.json`, run sequentially with no other headless browser (the owner's interactive Firefox, started 10-06, was open). The window was not equalised (browser launch lives in shared modules, not one line in the probe); the canvas height is listed beside every number and the canvas width is unrecorded.

| Report | Key → committed (median, max) | Key → on screen (median, max) | (ii) all current after last key | canvas rows |
|---|---|---|---|---|
| chrome owner gap 80 × 20 | 45.2, 54.8 ms | 36.7, 59.2 ms | 216.1 ms | 17,929 |
| chrome owner gap 200 × 10 | 38.0, 48.4 ms | 46.0, 53.2 ms | 177.7 ms | 17,929 |
| chrome boundaries gap 200 × 10 | **6.2**, 10.8 ms | 13.7, 16.6 ms | 19.2 ms | 2,007 |
| firefox owner gap 80 × 20 | 65.3, **82.6** ms | 49.2, 72.3 ms | 359.8 ms | 22,257 |
| firefox owner gap 200 × 10 | 68.2, 87.1 ms | **51.1**, 72.9 ms | 336.0 ms | 22,257 |
| firefox boundaries gap 200 × 10 | **8.3**, 9.7 ms | 15.5, 16.8 ms | 23.6 ms | 2,491 |

Against §15.6: Chrome meets every cell. Firefox meets every cell but one: **gap-80 commit max 82.6 ms (criterion < 80)**; one key of 20 is ≥ 80 (the next highest 75.1, 73.1). No growth in either browser at gap 80 (commit-to-commit intervals track key-to-key intervals; Firefox first-five median 65.3, last-five 65.2). Firefox on screen: gap-80 median 49.2 / max 72.3, gap-200 median 51.1 / max 72.9 (criteria < 90, < 150). (ii) holds in all six (not `None`).

Predictions (§15.6), line by line: Firefox commit max 65–78 → **82.6, missed** (high). Firefox on-screen median 55–68 → 49.2 and 51.1, **missed** (low). Chrome commit max 45–55 → 54.8 and 48.4, met. Chrome on-screen median 45–55 → 36.7 **missed** (low), 46.0 met. Full pass Firefox 230–300 → 359.8 and 336.0, **missed** (high). Chrome 160–230 → 216.1 and 177.7, met.

The ruling's stop rule applies (Firefox commit max ≥ 80 with no growth): v59 is not frozen and the cell is not restated here.

### The insert-alone floor, measured on the candidate (the stop rule's request)

Gap 600 ms × 10 keys, owner document, Firefox — longer than a full pass (≈ 330 ms), so no pass is in flight when a key lands. The v58 page (`537d62d7…`, bytes from `05f46923^`) and the B′ page (`b10f6017…`, from `6993186c`) were run as same-session controls by copying their bytes into `dist/e2-editor-app.js` for the run only (restored to `18c8afbe…` after; checked).

| Report | Page | Key → committed (median, max) | Key → on screen (median, max) |
|---|---|---|---|
| `control-v58page-firefox-owner-gap600-floor.json` | v58 `537d62d7` | **42.7**, 59.7 ms | 182.4, 247.6 ms |
| `control-bprime-b10f6017-firefox-owner-gap600-floor.json` | B′ `b10f6017` | **54.1**, 57.5 ms | 74.8, 78.5 ms |
| `v59-candidate2-firefox-owner-gap600-floor.json` | A+B `18c8afbe` | **57.6**, 74.4 ms | 69.6, 75.0 ms |
| `v59-candidate2-chrome-owner-gap600-floor.json` | A+B, Chrome | 35.9, 41.4 ms | 49.0, 54.7 ms |

So the 43 ms "insert alone" of brief 2 (F3) and the third ruling is the v58 page's floor, and it reproduces in this session (42.7). On the banded pages the idle floor is higher: ≈ 54 (B′) and ≈ 58 ms (A+B) median in Firefox, with nothing in flight.

### How much of that is the instrument (diagnostic, not 122-B)

The probe's paint shim writes `root.dataset.paints = JSON.stringify(<400 entries>)` on every stale `putImageData` and `root.dataset.blits = JSON.stringify(<600 entries>)` on every fresh one. The page re-blits its cached bands on every state update, so that cost scales with the band count — one call per re-blit on v58, 22 on A+B (bursts of 44–65 calls, two or three `paint()`s, spanning 11–16 ms). `diagnostic-shim-overhead/lazy_shim_probe.py` runs the same probe with those two writes coalesced into one per task (patched in memory; the committed probe is untouched; each report's `runner` says so):

| Report | Page | Key → committed (median, max) |
|---|---|---|
| `lazy-v58page-firefox-owner-gap600.json` | v58 | 44.7, 50.9 ms |
| `lazy-candidate2-firefox-owner-gap600.json` | A+B | 52.7, 65.9 ms |
| `lazy-candidate2-firefox-owner-gap80.json` | A+B | 71.1, **84.9** ms (3 of 20 keys ≥ 80) |

The instrument accounts for ≈ 5 ms of the A+B idle floor and nothing measurable on v58; the remaining ≈ 8 ms of floor rise is the page's, cause not located (per `paint()` the re-blit cost looks similar — v58's single whole-canvas calls start ≈ 5 ms apart, A+B's 22 calls take ≈ 5 ms — but on A+B the first re-blit burst after a key starts ≈ 5 ms later). Removing the overhead does not bring the gap-80 commit max under 80. Run-to-run spread at gap 80 is several ms (Firefox commit max 82.6 vs 84.9; median 65.3 vs 71.1).

### Per-key timeline under typing (Firefox, gap 80; `raw.blits` and `raw.revs`)

Key 8 (`i`, at 8670.8 ms): +20.0 state write (old revision 8) and the band in flight (top 3069, revision 8) blitted — A ended the old pass there; +51.5 band 0 blitted carrying the **new** revision 9 (the character is on screen); +75.1 the revision counter shows 9, and 0.5 ms later band 0 is blitted **again**, revision 9. Keys 9 and 10 have the same shape (+59.6 / +82.6 and +48.4 / +73.1). So per key the visible band is rendered twice: once by the pass A restarted (already after the insert) and once more because `document-invalidated` arrived while that band was in flight and ended that pass too. Brief 2 named this cost under option A. The committed time this probe reports is the moment `#s-revision` changes, and on A+B it changes just before the second band-0 blit, ≈ 23–25 ms after the character is already on screen. This is a reading of page-side timestamps; the Worker's queue order is not instrumented.
