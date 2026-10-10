# Finding 123 evidence — a short last band is judged "not painted" (2026-10-10)

Found while explaining why three Chrome ratio-2 reports in `../typing-latency/r2-blit-bytes/` (`dpr2-{base,skip}-chrome-owner-gap*.json`) carry `allCurrentAfterLastKeyMs: None` — fable's fifth ruling ("Wrong or missing", item 1) asked for it before ratio 2 could become a criterion. Shipped page `18c8afbe…` (host 0.2.10, shell v59); diagnostic wrapper `blit_bytes_probe.py` (not counted).

## Observed

- **The last band is never blitted.** Chrome, ratio 2, CSS window as headless default: canvas 1450 × 35,858. `renderBands` cuts it into 35 bands of 1023 rows and a last band of **53 rows** at y = 35,805. In all three reports no fresh or stale blit ever has y = 35,805 (blits at y ≥ 33,000: only 33,759 and 34,782, height 1023); coverage after the last key reaches 35,805, so the probe's "all current" never completes and prints `None`. Every other ratio-2 and wide report's last band is 525–949 rows and is blitted.
- **The page says so, to the user.** `chrome-dpr2-owner-toasts.json` (same configuration, 3 keys at gap 600, wrapper `26b95978…` with a toast recorder): toasts `已開啟 doc.odt` at 4,581.7 ms, then **`重繪失敗：TILE_NOT_PAINTED：引擎回了一張沒有畫進去的圖` at 6,190.6 ms (after the open's render pass) and again at 8,933.6 ms (after typing)**.
- **Why: the bottom rows of the canvas are transparent.** `chrome-dpr1-owner-bottom-rows.json` (ratio 1, 725 × 17,929, wrapper `2bf79999…`, `raw.ink.bottomOpaqueRows` = opaque fraction of each of the last 120 rows): rows are 0.96 opaque down to the last page's edge, then **14 rows of 0.00** (one 0.96 row inside them — the page's bottom border). The gap below the last page is fixed in twips, so its rows scale with the canvas width: ≈ 28 at 1450 px. A 53-row last band is then ≈ 25 × 0.96 / 53 ≈ 45 % opaque.
- **The test it fails.** `tileWasPainted` (`web/e2-editor-app.js` :1011–1023) samples alpha and requires at least half the samples opaque. Finding 062's unpainted buffer is all zeros; a band that is mostly the transparent gap below the last page fails the same test. `renderDocument` then throws `TILE_NOT_PAINTED` (:919–923), the catch toasts it (:983), and the pass ends.

## Derived (not measured)

- It hits when the canvas height's remainder modulo 1023 is below about twice the gap: ≈ 2 × 14 × (canvas width / 725) rows. At ratio 1 and the 900-px cap that is ≈ 35 of every 1023 possible heights (≈ 3.4 % of document-length × window-width combinations); at 1800 px, ≈ 70 (≈ 7 %). A remainder no taller than the gap itself fails any pixel-only test, including "any opaque sample".
- `bandOrder` puts visible bands first and keeps document order among them, so with the end of the document in view (typing at the end) the second-to-last band renders and the last one throws at once: the toast comes after every pass and the bands outside the view are not refreshed in that pass.
- v58 rendered the canvas as one tile up to 32,767 rows (062's split above that), so its last tile was short only on canvases above 32,767 rows with a small remainder; the 1023-row bands of A+B (v59) made the short last band common.
