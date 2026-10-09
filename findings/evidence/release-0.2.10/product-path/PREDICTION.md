# Product-path net for the 0.2.10 release (findings 122, 121, 120) — predictions (written 2026-10-10, before the run)

Spec: `specs/SPEC-M3-production-ui.md` §15.2 R‴ ("產品路徑網（M2-5，新頁面）"), bindings §15.11; per-cell rule `SPEC-M3-paragraph-merge.md` §23 with §36.2's row 1′ for `recovery-returns-what-the-product-promised`. Same design as `../../release-0.2.9/product-path/PREDICTION.md`; the reader `judge.py` here is that release's reader with the two page constants re-bound (its docstring says so).

Runs (after shell generation v59 is frozen and host 0.2.10 is pinned; `tools/run_e2_c_product_path.py` `a6e31896…`, i.e. 0.2.9's runner with only the `ignore-a-document-that-grew` anchor re-anchored), interleaved, 3 rounds × Chrome/Firefox, one at a time, after the M3 counts in the same chain:
- **v19 arm, plain**: `--browser B --out e2-editor-v19-B-rN.json` — dist as served, page `18c8afbe…` (122 A+B, 121, 120), worker v19.
- **v8 arm, candidate**: `--browser B --candidate-profile e2-editor-v8 --out e2-editor-v8-B-rN.json` — the same page source repointed to v8 (`d446cbfd…`, computed with the runner's own `repointed_page()`, which gives 0.2.9's `4d3f3bd6…` from 0.2.9's page).

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v19 reports: entrypoint `18c8afbe…`, no candidate keys; v8 reports: source `web/e2-editor-app.js` before repointing `18c8afbe…`, rest of shell equals source, entrypoint = `d446cbfd…`, profile e2-editor-v8 |
| P3 | 0 red cells under §23 + row 1′. The row 1′ window counted now: Chrome 0 NE in 21 v8 records, Firefox 2 in 21 — so Chrome's recovery cell keeps row 1, Firefox's takes row 1′ (the reader recounts at read time; the 0.2.10 v8 reports will be in the window only once committed) |
| P4 | descriptive: the cells that differ between the arms are the ones that differed in 0.2.9 (none) or X5 (Firefox `an-inline-format-reaches-a-selection`, the NE-only cells) |

Why P3 should hold although the page now repaints in bands (finding 122): every check that reads the canvas reads it after the page is quiet, and once quiet every band carries the last revision ((ii) of §15.6, measured in all six 122-B reports); spec §15.3 predicted 0 red cells for exactly this reason.

Also descriptive, not judged: each v19 cell here against 0.2.9's v19 reports on the old page (`../../release-0.2.9/product-path/`) — the shell regression question for this release. Predicted: no cell where the old page's v19 passed every round and the new page's v19 does not.

Before the verdict is read, the reader is made red once on scratch copies (as 0.2.9's was): a flipped v19 cell where v8 passes → P3 MISS; a wrong v19 entrypoint → P2 MISS.

## The re-anchored mutation, run once (fable's fourth ruling Part 2, condition 2; before any counted run)

`mutation-ignore-a-document-that-grew-chrome.json` (Chrome, `--mutate ignore-a-document-that-grew`): result appended below when the run ends; required: `the-canvas-follows-a-document-that-grew` red.

**Result (2026-10-10 02:17–02:23 +0800, before any counted run):** `the-canvas-follows-a-document-that-grew` **FAIL** — the edit reached the document (2 pages), the canvas kept the height it was opened with (2007 rows after the edit), and reopening the saved file gives the taller canvas, so the ground truth was established; exactly the defect the mutation reintroduces. The other 41 cells: 39 PASS and the two designed abstentions (`notice-action-recovers-the-session`, the recovery pairing's sentinel; `a-refused-action-is-reported-and-changes-nothing`, judgeable only in diagnostic runs). The re-anchor hit; the condition is met.
