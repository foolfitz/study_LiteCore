# Product-path net for the 0.2.13 release (autosave, findings 127–131) — predictions (written 2026-10-12, before the run; page constants re-bound to `d761f1ce…` the same day, still before any run, SPEC-M3-autosave §9.19)

Spec: `specs/SPEC-M3-autosave.md` §9.4 「計數」 (the product-path net passes on 0.2.13 as on 0.2.12); per-cell rule `SPEC-M3-paragraph-merge.md` §23 with §36.2's row 1′ for `recovery-returns-what-the-product-promised`. Same design as `../../release-0.2.12/product-path/PREDICTION.md`; the reader `judge.py` here is that release's reader with the two page constants re-bound (its docstring says so; `diff` is the docstring and those lines).

Runner `tools/run_e2_c_product_path.py` — unchanged since 0.2.12's count (`bd6fc0caf677ee9c`); the chain records its sha256 in `chain.log`. Its 41 page-mutation anchors and 2 diagnostic anchors each match exactly once in the new page (checked when 128 took remedy B, spec §9.10).

Runs (after shell generation v62 is frozen and host 0.2.13 is pinned), interleaved, 3 rounds × Chrome/Firefox, one at a time, after the M3 counts in the same chain:
- **v19 arm, plain**: `--browser B --out e2-editor-v19-B-rN.json` — dist as served, page `d761f1ce…` (0.2.13: autosave, 128 remedy B, 129 click-then-move, 130 toast predicate, 131 rule A), worker v19.
- **v8 arm, candidate**: `--browser B --candidate-profile e2-editor-v8 --out e2-editor-v8-B-rN.json` — the same page source repointed to v8 (`fac708d0…`, computed with the runner's own `repointed_page()`; the same call on 0.2.12's page `8909564e…` gives 0.2.12's `0660beaf…`, and on the pre-fix page `c7f904fa…` it gives `2609266a…`).

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v19 reports: entrypoint `d761f1ce…`, no candidate keys; v8 reports: source before repointing `d761f1ce…`, rest of shell equals source, entrypoint `fac708d0…`, profile e2-editor-v8 |
| P3 | 0 red cells under §23 + row 1′ (the reader recounts row 1′'s window at read time) |
| P4 | descriptive: the cells that differ between the arms are 0.2.12's kind (Firefox `clear-format-removes-every-inline-format`, NE-only) or none |

**Why the page's new behaviour should not reach this net**: the runner serves `dist/` from a local server with no host, and autosave runs only with a host (§9.2 first bullet), so no autosave fires here. What does reach it: 128's remedy B (a BUSY repaint is given up while an `editorAction` is out and the action's end repaints), 129's click-then-move on a range (taken only when an unshifted arrow, Home or End is pressed on a range; whether any of the net's checks does that was NOT checked — if one does, the page now moves the caret where 0.2.12 refused, and such a cell would differ from 0.2.12 in both arms alike), and 130's toast predicate (fires only on a rejected commit or a full queue; predicted 0 in these runs).

**Rule A (finding 131, spec §9.12, added 2026-10-12 before the first run)**: rule A acts only while the page's own delete is still unsettled (`deletesInFlight > 0`). The net sends exactly one Backspace through the page's delete listener (`backspace-and-arrows-reach-the-document`; the dispatch is `run_e2_c_product_path.py:5826`, `bs = evaluate(session, DELETE_KEY…)`, the `check(` call at 5836), after waiting for the caret placement to settle (「定位游標」) with no other delete out, so the count is 0 and the key goes out by finding 121's rule. No other check dispatches a delete `beforeinput` or a Backspace/Delete key (grep of the runner: `DELETE_KEY` is used once). Predicted: no cell changes because of rule A.

**Watch item (as 0.2.12)**: Chrome `clear-format-removes-every-inline-format` NE (finding 077's toggle). If it is NE in ≥ 2 of the 6 Chrome runs (either arm), the product-path verdict is not read until that is diagnosed; the M3 counts are read on their own.

Also descriptive, not judged: each v19 cell here against 0.2.12's v19 reports (`../../release-0.2.12/product-path/`) — the page-regression question for this release. Predicted: no cell where 0.2.12's v19 passed every round and this page's v19 does not.

Before the verdict is read, the reader is made red once on scratch copies (as 0.2.12's was): a flipped v19 cell where v8 passes → P3 MISS; a wrong v19 entrypoint → P2 MISS.
