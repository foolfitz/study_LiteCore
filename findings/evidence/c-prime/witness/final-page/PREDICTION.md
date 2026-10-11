# The witness on the final page — prediction (written 2026-10-11, before any run on this page)

The owner's choice (2026-10-11, after the C′-only witness came back 0 red, `../README.md`): measure once more
on the final page — C′ + finding 124 + finding 125, `dist/e2-editor-app.js` sha256 `8909564eb2316afa…`
(main `0ad30e73`; the tree at `e1303987`) — because 124 scrolls `#desk` to follow the caret, which is where the
unported readers' assumption "the canvas's top is the document's top" (`winTop = 0`) is most likely to break.
The second half of the choice, production UI `Rdel` with the pre-port `run_e2_c_page_smoke.py` on the first
host build that carries the page (0.2.12), runs at the release step before the count and is predicted in
`../PREDICTION.md` (red in both browsers).

## What runs

Four product-path runs, v19 arm (dist as served, no `--candidate-profile`), one each:

| Run | Runners | Browser |
|---|---|---|
| unported | `08d73cff`'s `run_e2_c_page_smoke.py` `5f26e3bd1280b3a9`, `run_e2_c_product_path.py` `a6e318966d50cf14`, `check_m3_page_honesty.py` `505f4f3a91ab93e5`, restored temporarily | Chrome, Firefox |
| ported | HEAD's: `cc38ee97ca20611d`, `bd6fc0caf677ee9c` (the port plus re-anchors that only `--mutate` and the two diagnostics read), `17a38fe756fe3e0b` | Chrome, Firefox |

Reference: `../../../release-0.2.11/product-path/e2-editor-v19-{chrome,firefox}-r{1,2,3}.json`. Reader:
`../judge_witness.py` (unchanged), once per run.

## Why the ported run is in it (a confound, designed out)

On this page a red cell can have two causes: (i) an unported reader reading the window as if it were the
document — the port's §34.4 witness; (ii) 124 (or 125) changing what the product does, seen by ported and
unported runners alike — not about the port. Reading:

- **port-witness cell**: witness-red in the unported run AND not witness-red in the ported run, same browser;
- **page-effect cell**: witness-red in the ported run (whatever the unported run says) — a product-path red
  on the page about to ship, to be diagnosed before the release step (a finding or a check question), and
  not a port witness.

## Predicted

**Port-witness cells: 0 in both browsers.** From the code:

- `onDeskScroll` (`web/e2-editor-app.js` :1003–1013) moves the window only when the view leaves the window's
  middle half; from `winTop = 0` with `W = 4,092` that needs the view's bottom past document row 3,069, and
  `windowTopFor` then gives `winTop > 0` only for a view centred past row 2,046.
- Every fixture of four pages or fewer has `W = docRows` (`windowRows`, :917): the canvas is the whole
  document and no scroll can change what it holds. That includes "the document that grew" (2,007 → 3,002 rows),
  whose click on the LAST band now makes 124 scroll the desk to about row 1,900 — the canvas does not move.
- The long-document arms that click (`long_arm`, 1 / 5 / 20 pages, `edit=True`, 08d73cff :8700–8728) click
  `bands[0]`, the first line of text, about row 100. `followCaret` (:782–797) centres that caret in the 139-px
  desk at most (Chrome's default 800 × 600, per the `windowRows` comment): `scrollTop` about 30–60, view rows
  about [30, 200]. The keystroke that follows moves the caret one character. The window stays at 0, so the
  unported `TOP_INK` / `INK_ROWS` read document rows as they did on the C′-only page. The 35-page and 2×
  arms do not click.

**Page-effect cells: 0 in both browsers, and no other movements** — a weaker prediction: it is not derived
cell by cell. The basis: 124 scrolls only `#desk`; the harness dispatches on `#canvas` with coordinates taken
from a fresh `getBoundingClientRect()` at each call, and the page maps them through `#paper`'s box, so a
scroll between two calls cancels; the projection and `#sink` are placed in `#paper` coordinates. 125 delays
only the shown pill text (`#state-shown`); `#state-pill`'s `data-state`, which the product path reads, still
changes at once. Firefox's known red `an-inline-format-reaches-a-selection` stays FAIL (FAIL in all three
0.2.11 rounds, so not witness-red).

## What follows

- 0 port-witness cells (as predicted): the ports of `run_e2_c_product_path.py` and `check_m3_page_honesty.py`
  are registered as having no witness on either page (§34.4, the owner's fallback); the page-smoke port waits
  for the host-build `Rdel` run.
- Any port-witness cell: that report is the §34.4 witness for the port of the runner whose reader misread.
- Any page-effect cell: stop before the C′ measurements that depend on it, diagnose, and bring it to the
  owner; it is not resolved by changing a check without a witness.
