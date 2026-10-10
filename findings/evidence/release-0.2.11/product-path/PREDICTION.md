# Product-path net for the 0.2.11 release (release P and finding 123) — predictions (written 2026-10-10, before the run)

Spec: `specs/SPEC-M3-production-ui.md` §16.2 P4 ("產品路徑網照 M2-5（新頁面，突變全紅之後才計數），不動任何判讀器") and R⁗, bindings §16.11; per-cell rule `SPEC-M3-paragraph-merge.md` §23 with §36.2's row 1′ for `recovery-returns-what-the-product-promised`. Same design as `../../release-0.2.10/product-path/PREDICTION.md`; the reader `judge.py` here is that release's reader with the two page constants re-bound (its docstring says so; `diff` is the docstring and those two lines).

Runner `tools/run_e2_c_product_path.py` `a6e31896…` — unchanged since 0.2.10. Its mutation anchors still apply once each to the new page (`tests/test_product_path_mutations.py` in `make test-e2-c-static`, exit 0 before and after the freeze); the two that anchor in code release P moved — `caret` and `caret-ignores-x`, now inside `overlayShapes()` — are run once each before any counted run (below), and each must turn its own check red.

Runs (after shell generation v60 is frozen and host 0.2.11 is pinned), interleaved, 3 rounds × Chrome/Firefox, one at a time, after the M3 counts in the same chain:
- **v19 arm, plain**: `--browser B --out e2-editor-v19-B-rN.json` — dist as served, page `36c2b18b…` (release P, 123), worker v19.
- **v8 arm, candidate**: `--browser B --candidate-profile e2-editor-v8 --out e2-editor-v8-B-rN.json` — the same page source repointed to v8 (`bd29ecca…`, computed with the runner's own `repointed_page()`, which gives 0.2.10's `d446cbfd…` from 0.2.10's page).

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v19 reports: entrypoint `36c2b18b…`, no candidate keys; v8 reports: source `web/e2-editor-app.js` before repointing `36c2b18b…`, rest of shell equals source, entrypoint = `bd29ecca…`, profile e2-editor-v8 |
| P3 | 0 red cells under §23 + row 1′. The row 1′ window counted now (git-tracked v8 records with `finding038Reproduced`): Chrome 0 NE in 24, Firefox 2 in 24 — Chrome's recovery cell keeps row 1, Firefox's takes row 1′ (the reader recounts at read time) |
| P4 | descriptive: the cells that differ between the arms are 0.2.10's (Firefox `clear-format-removes-every-inline-format`, NE-only) or none |

Why P3 should hold although `paint()` now restores only the overlay's rectangles: the checks that read caret or selection ink read the canvas after the page is quiet, and P's canvas then holds the bands under exactly the current overlay — the property `page-paint-overlay.test.mjs` checks pixel by pixel; spec §16.4 predicted 0 red cells for that reason.

Also descriptive, not judged: each v19 cell here against 0.2.10's v19 reports on the old page (`../../release-0.2.10/product-path/`) — the shell-regression question for this release. Predicted: no cell where the old page's v19 passed every round and the new page's v19 does not.

Before the verdict is read, the reader is made red once on scratch copies (as 0.2.10's was): a flipped v19 cell where v8 passes → P3 MISS; a wrong v19 entrypoint → P2 MISS.

## The two mutations whose anchors release P moved, run once each (Chrome; before any counted run)

`mutation-caret-chrome.json` (`--mutate caret`): required `the-caret-is-drawn-where-it-was-placed` red. `mutation-caret-ignores-x-chrome.json` (`--mutate caret-ignores-x`): required `the-caret-lands-where-the-click-was` red. Results appended below when the runs end.

**Results (2026-10-10 01:36–01:49 UTC, Chrome, both exit 0):**
- `caret`: `the-caret-is-drawn-where-it-was-placed` **FAIL** (strokes 0: no caret drawn) — **bites, as required.** Collateral: `the-vertical-arrows-move-the-caret` FAIL, `caret-follows-the-text-you-type` and `the-caret-lands-where-the-click-was` NE (no caret to follow), plus the two designed abstentions.
- `caret-ignores-x`: `the-caret-lands-where-the-click-was` **NOT_ESTABLISHED, not FAIL** — the requirement is **not met as written**; its declared also-red `the-caret-is-drawn-where-it-was-placed` FAIL. Reading the oracle (`caret_from_columns`, `tools/run_e2_c_product_path.py` ~:2947–3011): both clicks land the mutated caret at x = 0 on the same line, so the two reads differ by nothing, both strokes are 0, and since the 2026-08-21 tie-break fix a read that does not find the caret gives `None` → the position check abstains. Finding 060's run of this mutation (`../../060/anchored-oracle-mutation-caret-ignores-x.json`) reported FAIL with `caretAfterClickNearStart: 0`, i.e. before that fix. Hypothesis: the NE is the current oracle's on any page, not release P's.

**Attribution control (prediction written before the run):** the same mutation on the shipped v59 page (`18c8afbe…`), same runner, Chrome (`mutation-caret-ignores-x-v59-control.sh`: `dist/e2-editor-app.js` swapped for this run and restored, sha checked). Predicted: identical outcome — `the-caret-lands-where-the-click-was` NE with strokes 0, `the-caret-is-drawn-where-it-was-placed` FAIL. If v59 gives FAIL on the position check instead, P changed what this mutation does and the counted runs do not start until that is explained.

**Control result (2026-10-10 01:50–01:57 UTC, exit 0, dist restored to `36c2b18b…` and checked):** identical to the P page — `the-caret-lands-where-the-click-was` NE (strokes 0, both positions `None`), `the-caret-is-drawn-where-it-was-placed` FAIL, 38 PASS / 3 NE / 1 FAIL on both pages. **Prediction hit; the NE is the current oracle's, not release P's.** The counted runs may start. **Registered (not fixed, §34):** under the oracle as it has been since 2026-08-21, `caret-ignores-x` no longer turns its declared check (`mustGoRed: the-caret-lands-where-the-click-was`) FAIL, only NE plus its declared also-red; the mutation registry's claim for that check rests on the also-red. Witness: these two reports.
