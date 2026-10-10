# Release P: P1 and 123-B evidence (spec SPEC-M3-production-ui §16)

Reader: `../judge_p.py` (sha256 recorded with each reading). Instrument: `../r2-blit-bytes/blit_bytes_probe.py` (sha256 prefix `3dad37cbb03a769c`, over probe `dbad93c0dcf27fbf`). Report names: `PREFIX-BROWSER-SLOT.json`, slot `p1` (ratio 1, owner, gap 600 × 10) or `123b` (`--dpr 2 --window 800x1000`, owner, gap 600 × 3).

## Red cases on the shipped page (spec §16.3; predictions written before the runs)

`dist/e2-editor-app.js` = `18c8afbe…` (shipped, host 0.2.10). Prefix `shipped`. Script `red-shipped.sh`, log `red-shipped-2026-10-10.log`.

Predictions:

- **P1, both browsers: FAIL.** Every key re-blits ≈ 6.0 whole canvases (600 %, some keys 7 or 10 as in `r2-current-*`); canvas Chrome 725 × 17,929, Firefox 900 × 22,257. Dirty-rect calls 0 (the shipped page has no 7-argument call).
- **123-B, Chrome: FAIL** on all three cells: canvas 1450 × 35,858 (an 800-px CSS window gives the same 725-px canvas as Chrome's 800 × 600 default), at least one `TILE_NOT_PAINTED` toast, `allCurrentAfterLastKeyMs` `None`, lowest band ever blitted new at y 34,782 (the 53-row band at 35,805 never).
- **123-B, Firefox: probably does NOT reproduce.** Derived, not measured: Firefox's ratio-2 default run (`dpr2-base-firefox-*`) had canvas 1238 = 619 CSS px, i.e. desk = CSS window − 24 if headless Firefox defaults to 1366 device px; at an 800-px CSS window that gives a 1472-px canvas, 36,402 rows (± 1), last band ≈ 597 rows — not short, so no toast, `allCurrent` a number, 123-B PASS on the shipped page (a red case that is not red). If so, §16.3's own instruction applies: record it, choose a Firefox window whose canvas is 1450 px wide (CSS window = 725 + 40 + Firefox's measured offset), re-specify in the spec before any implementation, and re-run Firefox's 123-B red case.
