# Product-path net for the 0.2.9 release (findings 119 and 111) — predictions (written 2026-10-09, before the run)

Spec: `specs/SPEC-M3-production-ui.md` §14.2 R′ (the ruling's step 7: "product-path net per M2-5 on the new page"); per-cell rule `SPEC-M3-paragraph-merge.md` §23 with §36.2's row 1′ for `recovery-returns-what-the-product-promised`.

Runs (after shell generation v58 is frozen; `tools/run_e2_c_product_path.py` unchanged), interleaved, 3 rounds × Chrome/Firefox, one at a time:
- **v19 arm, plain**: `--browser B --out e2-editor-v19-B-rN.json` — dist as served, page `537d62d7…` (the 119 and 111 fixes), worker v19.
- **v8 arm, candidate**: `--browser B --candidate-profile e2-editor-v8 --out e2-editor-v8-B-rN.json` — the same page source repointed to v8 (`4d3f3bd6…`).
Roles are the reverse of X5's because dist now serves v19 (reader `judge.py`, this commit, docstring).

| | Prediction |
|---|---|
| P1 | all 12 reports complete, last state `ready`, no page errors; 42 checks each, same ids |
| P2 | v19 reports: entrypoint `537d62d7…`, no candidate keys; v8 reports: source `web/e2-editor-app.js` before repointing `537d62d7…`, rest of shell equals source, entrypoint = cutover page `4d3f3bd6…`, profile e2-editor-v8 |
| P3 | 0 red cells under §23 + row 1′. The row 1′ window today: Chrome 0 NE in 18 v8 records, Firefox 2 in 18 — so Chrome's recovery cell keeps row 1, Firefox's takes row 1′ |
| P4 | descriptive: the cells that differ between the arms are the ones that differed in X5 (Firefox `an-inline-format-reaches-a-selection` red in both arms, the NE-only cells) |

Also descriptive, not judged: each v19 cell here against X5's v19 reports on the old page (`../../v19/x5-product-path/`) — the shell regression question for this release. Predicted: no cell where the old page's v19 passed every round and the new page's v19 does not.

## Correction (2026-10-09, before any run): the runner is no longer "unchanged"

`tools/run_e2_c_product_path.py` changed after this file was written: its `rollback` mutation's find/replace strings were re-anchored to `    await session.rollback();` / `    await session.undo();` (same check `notice-action-recovers-the-session`, same meaning), because U6 of finding 119 moved the focus into `onNoticeAction`'s operation and the old anchor line no longer exists. Ruling: fable's second ruling, `../../fast-delete-recovery/ruling/fable-ruling.md` (option A). Witness: `test-e2-c-static-before-reanchor.txt` (the one failing static test after the v58 freeze). The runner's sha256 is now `7468abcdaa6a0c1c59a4096a01df25bd3af7768b7299336ba390cad80c26e1b9`. No product-path run preceded the change, so nothing is voided. `judge.py` pins no runner hash (it prints the chain log's tool line), so no pin moves. Before any counted run of this net, the `rollback` mutation is run once on one browser and must turn `notice-action-recovers-the-session` red (the ruling's condition 3).
