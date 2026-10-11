# Product-path net for the 0.2.12 release (C′ with findings 124 and 125) — predictions (written 2026-10-11, before the run)

Spec: `specs/SPEC-M3-production-ui.md` §17.7 step 5, bindings §17.22; per-cell rule `SPEC-M3-paragraph-merge.md` §23
with §36.2's row 1′ for `recovery-returns-what-the-product-promised`. Same design as
`../../release-0.2.11/product-path/PREDICTION.md`; the reader `judge.py` here is that release's reader with the two
page constants re-bound (its docstring says so; `diff` is the docstring and those lines).

Runner `tools/run_e2_c_product_path.py` `bd6fc0caf677ee9c` — the runner C5 (ii) ran (changed since 0.2.11 by the
§17.3 port `a0925990` and the re-anchor `e1303987`; unchanged since). Its mutations on this page: C5 (ii)′ holds
(§17.21).

Runs (after shell generation v61 is frozen and host 0.2.12 is pinned), interleaved, 3 rounds × Chrome/Firefox, one at
a time, after the M3 counts in the same chain:
- **v19 arm, plain**: `--browser B --out e2-editor-v19-B-rN.json` — dist as served, page `8909564e…` (C′, 124, 125),
  worker v19.
- **v8 arm, candidate**: `--browser B --candidate-profile e2-editor-v8 --out e2-editor-v8-B-rN.json` — the same page
  source repointed to v8 (`0660beaf…`, computed with the runner's own `repointed_page()`, which gives 0.2.11's
  `bd29ecca…` from 0.2.11's page `36c2b18b…`).

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v19 reports: entrypoint `8909564e…`, no candidate keys; v8 reports: source before repointing `8909564e…`, rest of shell equals source, entrypoint `0660beaf…`, profile e2-editor-v8 |
| P3 | 0 red cells under §23 + row 1′. Row 1′ window counted now (git-tracked v8 records with `finding038Reproduced`): Chrome 0 NE in 30, Firefox 2 in 30 — Chrome's recovery cell keeps row 1, Firefox's takes row 1′ (the reader recounts at read time) |
| P4 | descriptive: the cells that differ between the arms are 0.2.11's kind (Firefox `clear-format-removes-every-inline-format`, NE-only) or none |

**The v8 arm has never run on the C′ page** (the witness and C5 (ii) ran the v19 arm only). Why P3 should still hold:
the product-path fixtures are one-page documents that sit inside C′'s window, where the window canvas is the whole
document (§17.3), and the ported locating and ink reads are identities there (C5 (i) on the P page; witness on this
page, both v19).

**Watch item (§17.15)**: Chrome `clear-format-removes-every-inline-format` NE (finding 077's toggle). If it is NE in
≥ 2 of the 6 Chrome runs (either arm), the product-path verdict is not read until that is diagnosed; the M3 counts are
read on their own. Note that under §23 a v19-only NE where v8 passed all three rounds is already a red cell, so this
is also the most likely way P3 misses.

Also descriptive, not judged: each v19 cell here against 0.2.11's v19 reports on the P page
(`../../release-0.2.11/product-path/`) — the page-regression question for this release. Predicted: no cell where the
P page's v19 passed every round and this page's v19 does not.

Before the verdict is read, the reader is made red once on scratch copies (as 0.2.11's was): a flipped v19 cell where
v8 passes → P3 MISS; a wrong v19 entrypoint → P2 MISS.
