# Brief 2 for fable: C5 (i) stopped on the static suite — A, B or C? (2026-10-11)

The owner, 2026-10-11: 「做法發給fable裁決，我授權他待我決定」 — fable decides on the owner's behalf.

## Facts (each checkable; paths relative to /home/jiajun/LibreOffice/study_LiteCore)

- **F-a** C5 (i) (spec `specs/SPEC-M3-production-ui.md` §17.4 C5, §17.11) ran the 0.2.11 count's chain with the PORTED harness on the P page (`findings/evidence/c-prime/c5/runs-p-page/`, `chain.txt`, `README.md`, `compare-output.txt`; commit `87d57ff6`). Read with `findings/evidence/c-prime/c5/compare.py`: product path 168 cells 0 differences; production UI's three reports 0; host entry 0; page honesty, locks, versions, assets, same second: every cell's pass/run counts equal to 0.2.11's, the VERDICT line differs. `SUMMARY differences 5`. The handoff's rule: any difference = stop and hand back.
- **F-b** All five verdict differences have one cause, in each report's `score.problems` (page honesty: `static.testStatic` 2 → `NOT YET`, `check_m3_page_honesty.py:1030`): `make test-e2-c-static exit 2`. A counted M3 run gates its verdict on the static suite; shakedown runs do not (all six shakedowns were clean).
- **F-c** The static failure, re-run after the chain (`runs-p-page/static-failure-excerpt.txt`): 108 tests, 18 failures, all in `wasm_sdk_probe/tests/test_ink_rows_caret.py`. That test runs the actual `INK_ROWS` string from `run_e2_c_product_path.py` under node against a synthetic canvas that has no `dataset`. The port (`a0925990`) prefixed every ink reader with `DOC_WINDOW_JS` (`wasm_sdk_probe/tools/run_e2_c_page_smoke.py`), whose `__docWindow()` reads `c.dataset.window` → `TypeError: Cannot read properties of undefined (reading 'window')`. A browser canvas always has `dataset` (an HTMLElement property), which is why every measured cell agrees.
- **F-d** The port's offline identity proof (`findings/evidence/c-prime/c5/port-identity/identity.mjs`) used a fake canvas WITH `dataset`; `make test-e2-c-static` was not run before the chain. The main session's miss.
- **F-e** §34 (`specs/SPEC-M3-paragraph-merge.md` §34.1–34.4): checks guard honest-run accidents only; a check changes only on a witness (an honest run misjudged); every handoff reports 因執行而修 / 因審核而修. This stretch so far: 因執行而修 3 (the port, one per ported runner), 因審核而修 5 (the six new tools' one review; budget spent). `test_ink_rows_caret.py` is not one of the six reviewed tools.
- **F-f** Re-running only the five M3 runners counted-shape takes about 2 h (page honesty 60 min, locks 46, versions 4, assets 4, same second 11; from `chain.txt`). The whole chain took 4 h 49 min.
- **F-g** Nothing has been fixed or re-run since the chain. The C′ page, 124 and 125 wait on branch `c-prime-page` (worktree `../study_LiteCore-cprime`) for C5 (i) to be accepted (`handoff/HANDOFF-2026-10-11b-c5i-chain-running-c-prime-written-in-worktree.md`, Next and Addendum).

## Options

- **A** Make `DOC_WINDOW_JS` tolerate a canvas without `dataset` (e.g. `(c.dataset && c.dataset.window) || ''`), a runner change. Then `make test-e2-c-static`, re-run the five M3 runners counted-shape, re-compare. The product path's and page honesty's effective reader text then differs from what the chain ran; the claim that the change is inert in a browser is argued (F-c), not measured, unless the product path is re-run too (another ~80 min for twelve runs, or the whole chain).
- **B** Give the test's synthetic canvas a `dataset` (`{}`), modelling what every browser canvas has — a check change whose witness is this chain's static failure (§34.4 因執行而修 +1). Every runner stays byte-identical to what the chain measured, so the product path, production UI and host entry results stand as measured. Then `make test-e2-c-static` (expect exit 0), re-run the five M3 runners counted-shape (~2 h, detached), re-compare (expect 0).
- **C** Accept C5 (i) on the cell counts with the five verdicts explained by F-b/F-c alone; no re-run. Cheapest; the zero then rests on the main session's reading, which CLAUDE.md §8 says a termination claim must not.

The main session's leaning: **B** — it keeps the measured bytes, the edit models the browser rather than bending the code to the fake, and its cost is the two hours of the five runners that must re-run under A as well. Against B: it edits a test to fit the change rather than the change to fit the test; a reader that crashes when `dataset` is absent is a latent defect in any non-browser host of that string.

## Questions

Q1. A, B or C (or another), and why.
Q2. Whatever is chosen: must the product path or production UI be re-run, or do their measured results stand?
Q3. The §34.4 entry for the fix (which count, which witness).

Please answer in this shape: RULING (one line), WHY for the owner (zh-TW, ≤ 5 short lines, plain language), CONDITIONS (numbered, checkable), then anything you checked in the source.
