## SUMMARY

- Task 2026-10-13m: P1's mixed-page fixture (8 pages: A4 portrait, A4 landscape x2, A5 portrait, US Letter portrait, A4 portrait, A3 landscape, A4 portrait) measured on native LibreOffice 26.8 (`native-lok-26-8/build/instdir`, buildid `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`, `SAL_USE_VCLPLUGIN=svp`), 3 fresh processes, all exit 0. Round: `mixed-round-20261013T145218Z/`. No browser, no WASM, no product bytes.
- Fixture sha256 `e7f7611fd86e53243b7ab791283770a5612da236b19c41aab6064f0e8eb62b0a` (1841 bytes). The generator is deterministic (fixed zip timestamps): two runs 3 s apart gave the same sha256, while the earlier 60-page generator is not (its output hashed differently in two rounds, `README.md`). Nothing overflowed: native lays out exactly 8 pages, nothing was tuned, the fixture is the one first generated.
- Settled string, byte-identical in all 3 rounds (and across the 10 timed calls and the call after 2 s idle): `284, 284, 11906, 16838; 284, 17406, 16838, 11906; 284, 29596, 16838, 11906; 284, 41786, 8391, 11906; 284, 53976, 12240, 15840; 284, 70100, 11906, 16838; 284, 87222, 23811, 16838; 284, 104344, 11906, 16838`
- P-M1 HELD: 8 rectangles; `getParts()` = 8 right after the load and after settling; `.uno:StatePageNumber` = `Page 1 of 8`.
- P-M2 HELD: every w and h is within 0.005 % of its page style's size x 566.93 (US Letter is exactly 12240 x 15840); pages 2, 3, 7 are wider than tall (16838 x 11906, 16838 x 11906, 23811 x 16838) and no other page is.
- P-M3 HELD: y strictly increases in string order; the gap between consecutive pages is the single value 284 (`DOCUMENTBORDER`) for all 7 pairs, whatever the page heights (11906, 15840, 16838 mixed).
- P-M4 (open) answer: LEFT-ALIGNED. x = 284 on all 8 pages, so pages narrower than the widest are NOT centred; x + w/2 is not common (2x + w = 12474, 17406, 17406, 8959, 12808, 12474, 24379, 12474) and x + w is not common. `getDocumentSize()` = `[24379, 121466]` = widest page (23811) + 2 x 284 wide, last bottom (121182) + 284 high.
- For the v20 runner: the page of a document-space y is found from y alone and per-page heights; for x, a point right of a narrower page (x > 284 + w) lies inside NO rectangle, so "hit rectangle" and "nearest rectangle" differ there and the rule must say which it uses. Page rectangles of one document have different w and h, so an implementation that takes one h for all pages fails this fixture (the 60-page document could not catch that).
- Extras (not predicted): the probe's Edit A (page break at end) appends a 9th rectangle `284, 121466, 11906, 16838` (A4 portrait, because page 8's style follows itself; it does not test a mixed append), Edit B changes nothing; calls cost 0.009-0.013 ms first, <= 0.016 ms later.
- Red cases shown: generator `--self-test` 18/18 (eight mutations of its own output each turn `--verify` red; `--self-test --mutate drop-master-p3` exits 1), analyzer `--self-test` 6/6 (synthetic run green, five mutations red), and the same analyzer run on a real raw file with page 4's width edited to A4's reports P-M2 FAILED.
- Not covered: WASM (fonts and fallback may change line breaks, not page sizes, but nothing here says so); multi-column sections, headers/footers, a mixed append (Edit A on a document whose last page is not the one that follows itself).

## Predictions (verbatim from the brief; the same block is in `README.md`, "Mixed-page round", committed before the first run: commit `7cceb0ee`)

- P-M1: 8 rectangles; `getParts()` = 8.
- P-M2: each rectangle's width x height equals its page style's size in twips (1 cm = 566.93 twips) within 1 %; pages 2, 3, 7 are wider than tall.
- P-M3: rectangles' `y` strictly increase in string order, with a gap between consecutive pages.
- P-M4 (open, no expectation): how `x` relates across pages of different widths (left-aligned at one x, or centred on the widest page). Record what native does; the page-number rule intersects both axes, so either is fine, but the v20 runner must know which.

## The fixture and how to regenerate it

| item | value |
|---|---|
| generator | `wasm_sdk_probe/tools/create_mixed_page_document.py` (commit `7f712905`; mode bit changed in `7cceb0ee`, content unchanged) |
| regenerate | `python3 wasm_sdk_probe/tools/create_mixed_page_document.py --out <scratch>/mixed8.odt` |
| fixture | 1841 bytes, sha256 `e7f7611fd86e53243b7ab791283770a5612da236b19c41aab6064f0e8eb62b0a` (`mixed-round-20261013T145218Z/inputs.sha256`) |
| deterministic? | yes. In the runner two generations 3 s apart were compared with `cmp` (`create-fixture-command.txt`: "second run byte-identical to the first: yes"), and a separate pair of runs 3 s apart before the round gave `e7f7611f...b0a` twice. Every zip member carries the fixed timestamp 1980-01-01 and fixed attributes, so no clock enters the bytes. (The earlier `tools/create_long_document.py` does not fix its timestamps; its 60-page output hashed differently in two rounds, see `README.md`.) |
| check | `python3 tools/create_mixed_page_document.py --verify <file>` reads any .odt back and checks 8 master pages, each page's size, orientation and 2 cm margins, 8 forcing paragraph styles, the headings `MP-PAGE-1..8` and the lines `MP-P{n}-L{1..9}` (9 per page so no marker is a prefix of another). It reports "is the fixture" for `mixed8.odt` |
| not committed | the .odt itself (built into the scratch directory, as for the 60-page document) |

Page styles as declared (twips are cm x 566.93): 1 `Standard` 21 x 29.7 portrait; 2 `MP2` 29.7 x 21 landscape; 3 `MP3` 29.7 x 21 landscape; 4 `MP4` 14.8 x 21 portrait; 5 `MP5` 21.59 x 27.94 portrait; 6 `MP6` 21 x 29.7 portrait; 7 `MP7` 42 x 29.7 landscape; 8 `MP8` 21 x 29.7 portrait. Page 1's master page is called `Standard` because LibreOffice insists on a page style of that name; the document therefore carries exactly the eight master pages and no unused ninth.

## The eight rectangles as measured

Raw settled string of each round (`mixed-r{1,2,3}.jsonl`, record `rects`, phase `timed`, index 0), verbatim:

```
r1: 284, 284, 11906, 16838; 284, 17406, 16838, 11906; 284, 29596, 16838, 11906; 284, 41786, 8391, 11906; 284, 53976, 12240, 15840; 284, 70100, 11906, 16838; 284, 87222, 23811, 16838; 284, 104344, 11906, 16838
r2: 284, 284, 11906, 16838; 284, 17406, 16838, 11906; 284, 29596, 16838, 11906; 284, 41786, 8391, 11906; 284, 53976, 12240, 15840; 284, 70100, 11906, 16838; 284, 87222, 23811, 16838; 284, 104344, 11906, 16838
r3: 284, 284, 11906, 16838; 284, 17406, 16838, 11906; 284, 29596, 16838, 11906; 284, 41786, 8391, 11906; 284, 53976, 12240, 15840; 284, 70100, 11906, 16838; 284, 87222, 23811, 16838; 284, 104344, 11906, 16838
```

The three are identical (`settled_strings_identical_across_runs: true` in `analysis.json`), and inside every run the ten timed calls and the call after 2 s idle returned the same string (`timed_all_identical`, `stability_after_2s_identical`). As a table (identical in all three rounds):

| page | style | x | y | w | h | expected w | expected h | w error | h error | wider than tall |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 1 | A4 portrait | 284 | 284 | 11906 | 16838 | 11905.5 | 16837.8 | 0.004 % | 0.001 % | no |
| 2 | A4 landscape | 284 | 17406 | 16838 | 11906 | 16837.8 | 11905.5 | 0.001 % | 0.004 % | yes |
| 3 | A4 landscape | 284 | 29596 | 16838 | 11906 | 16837.8 | 11905.5 | 0.001 % | 0.004 % | yes |
| 4 | A5 portrait | 284 | 41786 | 8391 | 11906 | 8390.6 | 11905.5 | 0.005 % | 0.004 % | no |
| 5 | US Letter portrait | 284 | 53976 | 12240 | 15840 | 12240.0 | 15840.0 | 0.000 % | 0.000 % | no |
| 6 | A4 portrait | 284 | 70100 | 11906 | 16838 | 11905.5 | 16837.8 | 0.004 % | 0.001 % | no |
| 7 | A3 landscape | 284 | 87222 | 23811 | 16838 | 23811.1 | 16837.8 | 0.000 % | 0.001 % | yes |
| 8 | A4 portrait | 284 | 104344 | 11906 | 16838 | 11905.5 | 16837.8 | 0.004 % | 0.001 % | no |

Vertical gaps between consecutive rectangles (`y(i+1) - (y(i) + h(i))`): 284 for all seven pairs, in every round. Per-run detail is in `analysis.txt` / `analysis.json` (arithmetic on the raw strings only).

## Verdicts

| prediction | verdict | what the raw output shows |
|---|---|---|
| P-M1 | **held** (3 of 3 rounds) | 8 rectangles; `getParts()` 8 right after the load and 8 after the settle wait; `.uno:StatePageNumber` `Page 1 of 8` |
| P-M2 | **held** (3 of 3) | largest size error 0.005 % (limit 1 %); wider-than-tall exactly for pages 2, 3, 7 |
| P-M3 | **held** (3 of 3) | y strictly increasing; every gap 284 |
| P-M4 | open question answered: **left-aligned** | x = 284 on every page; centred on a common axis: no; right-aligned: no |

### P-M4 in detail

`x` is `DOCUMENTBORDER` (284) for all eight pages, whatever the page width: the pages are laid out against the left edge, not centred on the widest page. The document is as wide as its widest page plus a border on each side (`getDocumentSize()` width 24379 = 23811 + 2 x 284), so the A5 page's rectangle ends at x = 284 + 8391 = 8675 while the document is 24379 wide: a point at x > 8675 inside that page's y range (y 41786 to 53692) is inside no rectangle. The sanity checks in the analyzer: `docW - widest page = 568` and `docH - last bottom = 284` in every round.

## Observed, not predicted

- `getDocumentSize()`: `[24379, 121466]` in every round.
- First `getPartPageRectangles()` call 0.0093 / 0.0125 / 0.0126 ms (rounds 1-3); the other nine at most 0.0050 / 0.0155 / 0.0128 ms. Native only; nothing about WASM.
- The probe's Edit A (`.uno:GoToEndOfDoc`, `.uno:InsertPagebreak`) gave 9 rectangles, `getParts()` 9, the first eight byte-identical, the ninth `284, 121466, 11906, 16838` (284 below page 8, A4 portrait: page 8's page style follows itself). It therefore says nothing about appending a page to a mixed document whose last page is not A4. Edit B (one typed `Q` at the start) left all nine unchanged.
- `*.stderr` (1096 bytes each) hold only the usual LibreOffice warnings (OpenCL driver check, "no explicit viewshell set", `SvxTabStopItem expected`, ...). `*.exit` are all `exit 0`.

## Red cases (the checks can fail)

- Generator: `python3 tools/create_mixed_page_document.py --self-test` prints 18/18 (the generator's output passes `--verify`; markers unique; builds byte-identical; fixed timestamps; each of eight mutations of its own output turns verification red). `--self-test --mutate drop-master-p3` verifies a mutated copy and exits 1 with "7 master pages, expected 8" and "page 3: master page 'MP3' missing".
- Analyzer: `python3 tools/analyze_native_mixed_page_rectangles.py --self-test` prints 6/6 (a synthetic probe output satisfying every prediction is judged green; `drop-last-rect`, `page4-is-a4`, `page2-portrait`, `page5-overlaps-page4`, `getParts-7` each turn the targeted verdict red). It was run before the first native run.
- On real data: a copy of `mixed-r1.jsonl` in the scratch directory with page 4's rectangle edited from `8391` to `11906` wide (replaced in all 15 `rects` records) gives `P-M2: FAILED` with P-M1 and P-M3 still `HELD`. The edited copy is not committed.

## Files

`mixed-round-20261013T145218Z/`: `mixed-r{1,2,3}.jsonl` (raw), `.stderr`, `.exit`; `analysis.json`, `analysis.txt`; `inputs.sha256` (probe `.cpp` sha256 `44bdd543...` is the same as in `round-20261012T030439Z/inputs.sha256`, so the probe is unchanged; runner, generator and analyzer hashes; the fixture); `create-fixture-command.txt`; `build-command.txt`; `environment.txt`; `ended-utc.txt` (2026-10-13T14:52:56Z). Tools: `wasm_sdk_probe/tools/{create_mixed_page_document.py,run_native_mixed_page_rectangles.sh,analyze_native_mixed_page_rectangles.py}`.
