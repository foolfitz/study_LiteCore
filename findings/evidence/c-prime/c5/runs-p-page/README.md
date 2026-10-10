# C5 (i): the ported harness on the P page — result (chain 2026-10-10 17:08–21:57 UTC)

Chain `chain-c5i.sh` (commit `d402d6df`), progress `chain.txt`, host 0.2.11 `6b53c2e`, `dist/` = `web/` = the P page
`36c2b18b…`, ported runners (page smoke `cc38ee97`, product path `aa9a2280`, page honesty `17a38fe7`). Six
shakedowns clean, then production UI's three counted-shape reports, the six M3 runners counted-shape (moved
into `m3/`), the product path's twelve runs (`product-path/`). Read with `../compare.py`
(`compare-output.txt`, the full command is in it as run by the main session):

| Set | Result |
|---|---|
| Product path, 168 cells (42 checks × 2 browsers × 2 arms), forward §23 + row 1′ and reverse | **0 differences** |
| production UI KR x3, ctl/S/P, B3x x2 | **0 differences** |
| host entry | **0 differences** (`HOST_ENTRY LANDS`) |
| page honesty, locks, versions, assets, same second | **every cell's counts equal to 0.2.11's; the VERDICT line differs** (`NOT YET`, `LOCKS DO NOT LAND`, `VERSIONS NOT CORRECT`, `ASSETS NOT DELIVERED`, `SAME-SECOND SAVES NOT KEPT`) |

**SUMMARY differences 5 — STOP (spec §17.4 C5 (i) wants 0; the handoff says any difference stops the release).**

All five verdict differences have one cause, read from each report: `problems: ['make test-e2-c-static exit 2']`
(page honesty: `static.testStatic` 2, which its scorer makes `NOT YET`). A counted M3 run gates its verdict on
the static suite. Re-run by the main session after the chain (`static-failure-excerpt.txt`): `Ran 108 tests,
FAILED (failures=18)`, all in `wasm_sdk_probe/tests/test_ink_rows_caret.py`, which runs the ACTUAL `INK_ROWS`
string from `run_e2_c_product_path.py` under node against a synthetic canvas with no `dataset`; the ported
`INK_ROWS` reads `canvas.dataset.window` (`DOC_WINDOW_JS`, `run_e2_c_page_smoke.py`) and throws
`TypeError: Cannot read properties of undefined (reading 'window')`. The port broke an existing unit test of the
reader it ported; the port's offline identity proof (`../port-identity/`) used a fake canvas WITH `dataset`, and
`make test-e2-c-static` was not run before the chain. In a browser `dataset` always exists, which is why every
cell agrees.

What to do is the owner's decision (asked 2026-10-11, options in the main session's reply); nothing was fixed
or re-run after the chain.
