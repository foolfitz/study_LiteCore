# Brief 4 for fable — after 0.2.10: R2 measured, and the whole-document canvas itself is now the question (2026-10-10)

Host 0.2.10 (shell v59, page `18c8afbe…`) shipped with findings 122/121/120 fixed under your four rulings; the owner hand-tested it in both browsers and replied "全部通過". Your fourth ruling registered R1 (A′, admissibility first), R2 (`updateState()`→`paint()` re-blits the whole canvas on every state write; measure bytes per key before any design) and C (Worker forwards the invalidated rectangle). The owner chose to measure R2; the measurements went further than R2 and the owner sent the result to you: **"發給fable裁決"**. Read-only. H# are my claims; check the ones your ruling rests on.

## The owner's words (verbatim, 2026-10-10)

- "我平常用1倍；不過無論如何，collabora的畫面我已經很習慣了"
- "立場說明：我可以承擔大改的成本，前提是要划算"
- Earlier, asking how Collabora handles canvases taller than 32,767 rows: "\"能否畫超過32,767列的畫布\" => collabora 怎麼做呢？"

Context you know: the product is a Nextcloud app sold to institutions (their machines, not the owner's); the owner uses Collabora daily.

## Sources

`findings/evidence/typing-latency/r2-blit-bytes/README.md` (every section has predictions written before its runs, then results and a line-by-line score; read it — the misses are listed); wrapper `blit_bytes_probe.py` (all patches in memory or in a served mirror, `dist/` untouched; options `--page v58`, `--skip-stale`, `--dpr`, `--window`); micro-bench `canvas-bench/`; spec `specs/SPEC-M3-production-ui.md` §15.13–15.15; page `wasm_sdk_probe/web/e2-editor-app.js`; session `wasm_sdk_probe/editor-shell/editor-session.js`; Collabora reference `cool-26-04/browser/src/` (read-only checkout).

## What was measured (owner document, real keys, A+B page unless said)

- **H1. R2 is six whole-canvas re-blits per key, five on the commit path.** Both pages, both browsers, gap 600 and 80: 6.0 canvases per key (Chrome 52 MB, Firefox 80 MB per canvas at ratio 1). Time inside `putImageData`: Chrome ≈ 20 ms; Firefox 32 (v58) / 42–46 ms (A+B). Read against the source (`editor-session.js` :266, :285, :291, :307, :333): every `state.update`/`transition` calls `onState` → `updateState()` → `paint()` synchronously; an insert from idle writes pending, busy, pending **before** `item.operation` posts it to the Worker, then revision/editorState and ready in one continuation after the reply. Chrome timeline: 3 canvases at keydown +1 ms (≈ 9.5 ms), 2 at +27–31 ending just before `#s-revision` shows, 1 after.
- **H2. Removing the re-blits (what-if: counted but not passed to the native call, paired with a same-session baseline)**: commit median Chrome −19 / −16 ms, Firefox −24 / −22 ms (gap 600 / 80); on screen −10 to −25 ms. Ratio 1, 900-px canvas.
- **H3. The A+B idle-floor rise in Firefox is R2 × band count** (same bytes as 22 calls cost ≈ 14 ms more per key than as one); my prediction said otherwise and missed. Chrome has neither.
- **H4. Higher pixel ratio multiplies it.** Backing width = `min(2400, cssWidth × devicePixelRatio)` with cssWidth ≤ 900 (`layoutCanvas`, :773). Ratio 2, narrow window (Chrome 1450 × 35,858; Firefox 1238 × 30,616): gap-80 commit median 106.7 / 105.6 ms, on screen 66.8 / 68.9; skip → 34.5 / 59.8. **Ratio 2, window wide enough for the 900-px cap (both 1800 × 44,514, 321 MB per canvas)**: Chrome gap-80 on screen **368.5 median, 595.8 max** (finding 122's symptom), skip → 47.0; Firefox gap-80 commit 208.1, on screen 90.5, and **with the re-blits skipped the commit is still 158.8**.
- **H5. What stays in Firefox without R2 is the whole-document repaint itself.** Wide skip run, one key: the insert's invalidation arrives +86 ms after the keydown (the Worker is rendering background bands when the insert arrives), the visible band is blitted at +110 with a 30 ms first blit; at gap 600 the pass after one key is 44 bands, each first blit ≈ 22 ms on the main thread.
- **H6. In Firefox the per-blit cost is the destination canvas's, by any method** (micro-bench, single blit per task, 12 calls): into 1800 × 44,514 — fresh `putImageData` 26 ms, same image again 24, `drawImage` of a new `ImageBitmap` 28, of the same one 24; into 1800 × 2000 — 2 / 1 / 5 / 1; into 900 × 22,257 — 6 / 0 / 7 / 0; into 900 × 1000 — 1 / 0 / 2 / 0. Chrome < 1 ms everywhere (medians). So a viewport-sized canvas removes it; Collabora's `ImageBitmap` route alone does not (my prediction said it would; missed).
- **H7. Firefox draws a 44,514-row canvas** (ink in three strips). I predicted blank and was wrong: no finding-062-class defect.
- **H8. R1 (A′) is admissible by your criterion**: 140 keys over eight runs, every revision carried by exactly one `document-invalidated`, none pre-increment.
- **H9. C's premise does not hold during typing**: no `INVALIDATE_TILES` (LOK id 0) arrived in any run; every invalidation was id 1 (cursor), payload the cursor rectangle. Whether this engine build never emits id 0 or only not while typing is not measured (discovery-era reports do show an `invalidate-tiles` editor-state source). Any design that re-renders "only what changed" cannot get that from the engine today; "re-render what is visible, mark the rest stale by revision" can.

## How Collabora does it (read in `cool-26-04/browser/src/`)

Canvas = the container's size × `devicePixelRatio` (`canvas/CanvasSectionContainer.ts:1518–1543`, `:685–691`); the document is 256 × 256 tiles (`js/global.js:297`) cached as `ImageBitmap` (`app/BitmapTileManager.ts:369–373`); scrolling moves the viewed rectangle (`app/ViewLayoutNewBase.ts:86–`, `canvas/sections/ScrollSection.ts:570`) and visible tiles are `drawImage`d at their offsets (`canvas/sections/TilesSection.ts:826–837`); the scrollbar is drawn by the page. Your second answer (fable-ruling.md, "Second answer") already borrowed its ordering and keep-the-old-picture rules into B′.

## What depends on "the canvas is the whole document" (grep census, approximate — I have not read every hit)

- Page (2,324 lines): `layoutCanvas` :773, `visibleCanvasRows` :844, `renderDocument` :855, `paint` :1025, `paintBand` :1039, `drawOverlay` :1050, `moveSinkToCaret` :1100, `pointToTwips` :1115, `positionProjection` :369 (finding 093's a11y nodes are placed in CSS px over the canvas), `endDrag` :1697, `endRenderPassOnInput` :1876.
- Harness: 35 files under `wasm_sdk_probe/tools/` read canvas geometry. The counted ones: `run_e2_c_product_path.py` 52 references — `POINT_AT` (:1099, 25 uses) clicks at a **fraction of the canvas's bounding box** with synthetic pointer events, off-screen coordinates included, and four `getImageData` ink reads at **document rows**; `check_m3_page_honesty.py` 6, `check_m3_production_ui.py` 3, locks / assets / host entry 2 each, versions and same-second 0. All of that addressing assumes canvas = document.

## Options as I see them (attack them, including my cost estimates)

- **A. R2 only** (page): `paint()` re-blits only the rectangles the overlay touched (old and new caret/selection), and state writes within one task coalesce to one paint. Fixes Chrome in every configuration (H2, H4 skip rows). Firefox at ratio 2 wide stays ≈ 159 commit / ≈ 80–120 on screen (H4, H5). Harness untouched. One page release.
- **B. A + lazy off-screen bands** (page): after an edit render only the visible bands; the rest are marked stale by revision and rendered when scrolled into view. Removes H5's Worker contention and most first blits; the visible band's first blit into a 321 MB canvas still costs ≈ 22–28 ms in Firefox (H6). Your §15.6 cell "(ii) all current after the last key" and the mutation `ignore-a-document-that-grew` / check `the-canvas-follows-a-document-that-grew` need restating or re-reading. One page release.
- **C. Collabora's shape**: viewport-sized canvas, tile/band cache, page-drawn scrolling. Removes R2, H5, H6, the canvas-height ceiling and the 2 × 321 MB of pixels (backing store + the JS copy in `lastTiles`). Rewrites the eleven page functions and the harness's addressing; the product-path net is the regression net we would be changing at the same time as the product.
- **C′. Viewport-sized canvas, native scrolling kept**: a full-height spacer element sized like the document scrolls as today; a viewport-sized canvas sits `position: sticky` inside it and draws the visible band images at the scroll offset. Everything positioned in document CSS px relative to the spacer (sink, a11y nodes, click mapping) keeps its coordinates; the harness change is the target of `POINT_AT` (the spacer instead of `#canvas`) and the four ink reads (scroll the rows into view, read the viewport). I think this gets H6 and H5 for most of C's cost — untested; element-height limits of browsers are in the tens of millions of px.
- **D. Register, do nothing now.** The owner is at ratio 1 and hand-tested 0.2.10 as passing.

My leaning: **C′ in one release**, because every option above A costs the same page-release cycle (shell generation, host version, R‴ chain ≈ 5 h of counted runs), the owner accepts a large change if it pays, and the configurations it fixes (ratio 2 with a wide window) are ordinary institutional laptops, not exotic ones. Against my leaning: it is the largest change, it moves the regression net together with the product, and at ratio 1 (the owner's) A alone already gets most of the user-visible gain (H2).

## What I need back

1. Which option (or another), judged against the owner's "划算" — say what it buys per configuration and what it costs, using the numbers above, and which of my H# you relied on.
2. If C or C′: what the harness change counts as under spec §34 (`SPEC-M3-paragraph-merge.md`): a new tool (one review before first counted use) or a check fix (needs a witness)? And how the product-path net stays trustworthy while it is ported (e.g. a run of the ported net on the **unchanged** v59 page that must reproduce 0.2.10's verdicts cell for cell before it judges the new page).
3. The acceptance criteria, in the forms of `CLAUDE.md`'s 驗收判準的形式 §1 (per-instance or tool-closed), each with "if never done": which configurations are criteria (ratio 1 at 900 px; ratio 2 at 1800 px?) and which are named limits; what replaces §15.6 (ii); R1 (A′) — in or out; whether H9 (no `INVALIDATE_TILES`) must be explained before or after.
4. Red cases for the new criteria, computed before running (standing rule (oo)).
5. Sequencing: one release, or A first then C/C′ as its own project.
