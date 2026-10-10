# The harness port, before C5 (i) (SPEC-M3-production-ui §17.11)

The port changes three runners: `run_e2_c_page_smoke.py` (the shared `POINT_AT`, and `DOC_WINDOW_JS`, the
document-window conversion), `run_e2_c_product_path.py` (`GEOMETRY`, `TOP_INK`, `CARET_COLUMNS`, `LINE_INK`,
`INK_ROWS`, `POINT_AT`, `DRAG`, `ABORT_DRAG`, `INDUCE_047`, `INDUCE_EMPTY_PARAGRAPH`) and
`check_m3_page_honesty.py` (`DRAG`, `TEXT_LINES`). No judging logic and no threshold moved. On a page without
`data-window` (the P page) every conversion is the identity and the one real change is that pointing
multiplies `#paper`'s box instead of `#canvas`'s.

Two measurements before the long chain, neither counted:

| File | What | Result |
|---|---|---|
| `identity.mjs`, `identity-output.txt` | Offline, node `vm`, a fake page: every ported constant (`constants-after.json`) against its pre-port text (`constants-before.json`, from the parent commit) on the same pixels. P page: 5 heights × 2 scales. Windowed fakes (the C′ shape): the whole document in the window, and rows [1000, 2024) only. | **146 compared, 0 different.** The first run reported the ten `GEOMETRY` cells DIFF (the port adds `canvasHeight`); the comparison now drops that field after asserting it equals `height`. |
| `identity-red-output.txt` | Red case: `TOP_INK` reads one row low, `LINE_INK` forgets `winTop`. | 13 DIFF, exit 1. |
| `paper_vs_canvas.py`, `paper-vs-canvas.json` | The served P page (`dist/` = `36c2b18b…`), Chrome and Firefox in their default windows, after the open, after a second fixture, and in Chrome at devicePixelRatio 1.5 and 2: `#paper`'s and `#canvas`'s `getBoundingClientRect()`; each ported reader evaluated once. | **Equal in every read** (Chrome 725 × 929 CSS px, Firefox 900 × 1153); every reader returned a plain object with no `windowWait` (the synchronous path), `GEOMETRY.height` = the canvas height. |

`dump_constants.py TOOLS_DIR` writes the constants of the three runners found in `TOOLS_DIR` (loaded by file, so
an old copy imports its own old page smoke).

The importer list (`../importers.py`, `../importers-output.txt`): all eight counted runners of the 0.2.11 chain
reach a ported module, so C5 (i) is the whole chain.

§34.4: the port is 因執行而修 1 for each of the three runners (§17.3); the importers are 0 bytes and are in C5 (i).
