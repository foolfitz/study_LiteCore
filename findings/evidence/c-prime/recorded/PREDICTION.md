# C1's runtime read and §17.4's recorded items — predictions (2026-10-11, before any run)

Page `dist/e2-editor-app.js` = `8909564eb2316afa…`. Instruments: `wasm_sdk_probe/tools/probe_c_prime_recorded.py`
(new; C1, `lastTiles` bytes, fling, save) on the owner document at ratio 2 wide (`--dpr 2 --window 1400x1000`) and
ratio 1 at 800 × 600 (the 139-px desk); `findings/evidence/typing-latency/r2-blit-bytes/blit_bytes_probe.py`
(DIAGNOSTIC, unchanged; `--page current --dpr 2 --window 1400x1000`, owner, gap 80 × 20) for the H9 census.
Both browsers. Nothing here is a gate (§17.4: recorded).

| Item | Prediction | Basis |
|---|---|---|
| C1′ (`#canvas.height` = `min(docRows, max(3·floor(desk·scale), 4,092))`) | holds in all four runs. Ratio 2 wide: **Chrome 4,380**, Firefox 4,092. 800 × 600 ratio 1: 4,092 (the floor) in both | C6 / C2 already recorded 4,380 / 4,092 at ratio 2 wide; so **§17.9 N4's "W = 4,092 at 1400 × 1000 in both ratios" does not hold for Chrome** (its desk is about 730 CSS px, not 540) — a prediction miss recorded here, not a defect |
| `#paper` CSS height = document height | holds (within 1 px) in all four | `layoutCanvas` sets both from the same `cssHeight` |
| `lastTiles` bytes, top | Chrome 5 bands = 36.8 MB; Firefox 4 bands = 29.5 MB (ratio 2 wide, width 1,800) | window rows 4,380 / 4,092 from row 0 |
| `lastTiles` bytes, middle | Firefox 5 bands = 36.8 MB; Chrome 5 or 6 bands = 36.8 or 44.2 MB — **6 would exceed N4's "≤ 5 bands ≈ 37 MB"**; both under §17.4's ≤ 60 MB | a window not aligned to bands crosses one more band |
| fling, 20 frames × 500 CSS px | 15–20 of the 21 recorded frames have a band under the view that is not current; current again 100–400 ms after the last frame | the window (~2,050–2,190 CSS px) is left after 2–4 frames; C4 measured 62–151 ms for one move |
| H9 census | **no `INVALIDATE_TILES` (LOK id 0)** while typing; one id 1 (`INVALIDATE_VISIBLE_CURSOR`) per key | R2 on the P-family page (no id 0 in any run); C′ changes no engine byte |
| save, owner document (563 KB) | one `busy`, 300–1,500 ms; if ≥ 700 ms, 「處理中」 shown at 700–760 ms after its start; if < 700 ms, never shown | 125's 700 ms; save time not measured before on this document |
