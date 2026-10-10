# The witness: the unported net on the C′-only page — prediction (written 2026-10-11, before any witness run)

Ruling condition 5 (`../ruling/fable-ruling-1.md`), spec §17.9 (b), (f), §17.11 (last paragraph): the report
names the C′-only page commit and the pre-port runner commit, and its predicted red set is committed before it
runs. This file is that prediction. Nothing below has been measured; the C′ page has not been opened in a browser.

## What runs

| Item | Value |
|---|---|
| Page | the C′-only commit `57d21411` on branch `c-prime-page` (page `f5121fd4…`; no 124, no 125), brought into the main tree and built into `dist/` by `make e2-c-assets` after C5 (i)'s chain has finished |
| Runners | the pre-port commit `08d73cff` (the port is `a0925990`): `run_e2_c_page_smoke.py`, `run_e2_c_product_path.py`, `check_m3_page_honesty.py` as they were, every other file as in the tree |
| Product path | the v19 arm (dist as served), Chrome and Firefox, one run each |
| Reference | the 0.2.11 count's v19 reports, `../../release-0.2.11/product-path/e2-editor-v19-{chrome,firefox}-r{1,2,3}.json` |
| A witness-red cell | FAIL in the witness and PASS in all three 0.2.11 rounds of the same browser. NE-only movements are listed apart and are not witness-red. |

## Predicted red set: the product path — **0 cells**

§17.3 and §17.9 (b) predicted the two long-document cells and the "document that grew" cell. Re-derived under
C1′ (`W = min(docRows, max(3·floor(desk·scale), 4 bands))`, 4 bands = 4,092 rows), from the code:

- **Every fixture of four pages or fewer is wholly on the canvas** (`W = docRows`, `winTop = 0`), so `#canvas`
  has the P page's box, height and pixels: every unported reader reads what it read on the P page. That covers
  every cell but the long-document arms; the "document that grew" arm is 2 pages at dpr 1 (about 1,990 rows,
  about 2,985 after the edit), so it is one of them — **not red** (§17.3's reason, the canvas height taken as
  the document's, needs `W < docRows`).
- **The long-document arms** (`long_arm`, `run_e2_c_product_path.py` :8743–8784 at `08d73cff`: 1, 5, 20, 35
  pages at dpr 1; 20 pages at dpr 2) are windowed from 5 pages up, but every read they make is of the canvas's
  own frame at `winTop = 0`: `TOP_INK` reads canvas rows 0–400; `stable_bands` → `INK_ROWS` scans the canvas and
  the click (`POINT_AT`) is a fraction of the same canvas box, so the band it aims at is the band it read;
  `keystroke_to_ink` reads `TOP_INK`. `winTop` stays 0 because the desk is not scrolled past about 1,900 CSS
  px by anything before them (the keyboard helpers' `sink.focus()` brings a one-page fixture's caret into a
  139-px desk, `scrollTop` about 140; `windowTopFor` then gives 0). `GEOMETRY.height` reports `W` instead of
  the document's rows, but `long_arm` only records it. — **not red**.
- Everything that reads `#a11y-doc`, `#sink` or the projection reads `#paper`-relative offsets, unchanged by C′.

## Not observable on the product path: the host-served runners

`check_m3_production_ui.py` and the six M3 runners drive the page the HOST serves (bound by `servedPage`), so
they meet the C′-only page only on a host build that carries it. Predicted there, from the code at `08d73cff`:

- **production UI `Rdel`, both browsers, every round — red.** It clicks `LAST_LINE` (y 0.990622,
  `check_m3_production_ui.py:98`, :445) with `POINT_AT`'s fraction of the CANVAS box; on the owner document
  (22 pages, windowed in the host's desk) that box is the window at the top, so the click lands near document
  row 0.99 × 4,092 ≈ 4,050, about page 4, not the last line; End, the marker and Delete then act mid-document,
  and the refusal the arm expects at the document's end does not come.
- Every other production-UI position (`IN_TEXT`, `HEADING_END`, `PARA_START`, `FIRST_LINE`: y ≤ 0.010373) lies
  in the first band — not red. Page honesty, locks, versions, assets, host entry, same second click at
  (0.35, 0.28) on one-page host fixtures — not red.

## What follows from the prediction (not a decision)

If the product path's witness is 0 red as predicted, the ports of `run_e2_c_product_path.py` and
`check_m3_page_honesty.py` (§17.3 counted 因執行而修 1 each) have no witness on the C′-only page, and the port
of `run_e2_c_page_smoke.py` has its witness only on a host build. §34.4 says a check changes on a witness or is
only registered; what to do then is the owner's (or fable's) call, asked after the measurement, with these
options written down then.
