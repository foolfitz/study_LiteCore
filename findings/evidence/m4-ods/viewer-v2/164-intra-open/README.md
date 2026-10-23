# finding 164's work item: growth within one open, ods-viewer-v2 `aa576ce7` (2026-10-23 14:25-14:28 CST)

SPEC-M4-viewer-v2 §11 (design and readings pinned in `48bf08d0` before any code or run). Probe: `tools/probe_ods_viewer_intra_open_growth.py` + `web/ods-viewer-growth-probe{.html,-app.js}`, mirror only, record-only; reader selftest 8/8 before the first run. Each run is a fresh engine, one open, K operations, close, dispose; `G(K)` = `sbrk` at `document-destroy-enter` minus the same at K = 0.

| report | what |
| --- | --- |
| `report-2026-10-23T062535Z.json` (`run-1.txt`, 42 s) | first run, 2 repeats; no record of what the operations produced |
| `report-2026-10-23T062735Z.json` (`run-2.txt`) | same plan, 2 repeats, with every 100th operation sampled (`2910e135`: run 1's 3,200 paints cost about 1 s, so "flat" had to be shown to come from operations that painted) |

## Did the operations happen? (run 2's samples)

- `paint` (numeric-100k.ods, 256 px tiles down a scroll path, rows 0..799 of 6,640): every sampled tile non-blank and all distinct (33/33 at K = 3,200); median 0.8-1.5 ms per tile, the first one 13-25 ms.
- `switch` (three-sheets-distinct.ods): every sampled `setPart` read back the part asked for (11/11 at K = 960); exactly three distinct tiles, one per sheet.
- `control`: the 4096x4096 tile (67,108,864 B) took 151-163 ms and is non-blank.

## The numbers (G in bytes; four repeats = run 1 r1, r2, run 2 r1, r2)

| arm | K | G |
| --- | ---: | --- |
| control | 1 | 68,788,224 x4 |
| paint | 200 | 0 x4 |
| paint | 800 | 0 x4 |
| paint | 3,200 | 3,268,608 · 2,220,032 · 2,220,032 · 3,399,680 |
| switch | 60 | 655,360 · 655,360 · 667,648 · 671,744 |
| switch | 240 | 819,200 · 905,216 · 839,680 · 901,120 |
| switch | 960 | 2,609,152 · 2,572,288 · 2,457,600 · 2,514,944 |

`destroyEnter` at K = 0: 261,304,320 (paint file) and 241,872,896 (switch file), identical in all four. The highest `sbrk` seen anywhere: 310,661,120 (the control), 264,704,000 outside it -- against E6's kill line 939,524,096.

## Reading (§11.3, as pinned)

- The positive control holds in all four (>= 67,108,864): `document-destroy-enter` does show an allocation made during the open.
- Not deterministic past K = 0: the same K gives different G between repeats (paint at 3,200; switch at 60 in run 2, 240, 960). Boots are identical; the operations are not, at the allocator. The readings use the larger value.
- **paint: flat.** G(3,200) - G(800) <= 4 MiB in every repeat.
- **switch: flat.** G(960) - G(240) <= 4 MiB in every repeat.
- What "flat" means here: in one open, 3,200 tile paints and 960 sheet switches raise the high-water mark by at most 3.4 MB and 2.6 MB. A retained growth smaller than about 4 MiB / ΔK per operation -- 1.7 KB per paint, 5.8 KB per switch -- plus whatever the allocator's slack absorbs is below this probe.

## Registered, not read

The switch arm rises with K in every repeat (0.66 → 0.82-0.91 → 2.46-2.61 MB), about 2.2-2.5 KB per switch between K = 240 and 960 -- inside the band §11.3 says this probe cannot resolve, so it is neither a leak nor its absence. If it were all retained and stayed linear, the kill line would be about 310,000 switches away (paint at its 800 → 3,200 rate: about 476,000 tiles) [extrapolation]. Telling retained bytes from allocator drift needs a live-byte count (`mallinfo().uordblks`), which finding 164 already puts with the next link.
