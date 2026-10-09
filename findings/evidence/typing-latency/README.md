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
