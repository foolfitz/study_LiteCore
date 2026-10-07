# Prediction, before the run: the product-path net on the current candidate page `b003534c…`

Written 2026-10-07, before any run in this directory. Nothing is bound to it until the reports exist.

## Why this run exists

`../product-path-web-page/` (commit `59b3fb4c`) measured the cutover's page at `3cf01330…`. Commit `c50c7789` then changed that page twice (spec §23 note: a repaint rejected with `ENGINE_DISPOSED` no longer toasts; a BUSY retry no longer lets two repaint loops run). The page the cutover would ship is now `b003534c51fbbaf42e6195c8f644065d155b84ec177b16a8dd0ee3a173ab4e9d` (`tools/build_cutover_page.py --profile e2-editor-v16`, no `--write`, at `f488103b`). The earlier result may not be cited for the v56 freeze (handoff 2026-10-07c, "Next" item 1). The runner also changed since (`8ef4c5f8`, `shell_lagging_source` moved into a shared function): sha256 now `b52779e498ae33cffea5970ad9a6f8cdf49b03240ef1211905ebc68f975c940c`, so both arms are re-run.

## State at the time of writing

- `dist/e2-editor-app.js` (v8 arm's page): `e97d6e035d8f84efc2c9b8833e4b5ac1dc0c3b15ad1d3d9a9c861eea8c542e1f`.
- `web/e2-editor-app.js` before repoint: `a3fd9ac1d057eea22fa1af0d359d1760b5f211dead6af1db8ac010cc473aa7bc`.
- `shell_lagging_source(dist/)` returns `[]` (rest of the shell in `dist/` equals source).

## Design (same as `59b3fb4c`)

- One runner sha for both arms; one run at a time; interleaved: Chrome v8 r1, v16 r1, v8 r2, v16 r2, v8 r3, v16 r3, then the same six on Firefox.
- v8 arm: no profile flag. v16 arm: `--candidate-profile e2-editor-v16`. No `--write` anywhere; no `make`; nothing under `dist/` or `web/` is touched.

## Predictions

- **P1.** All 12 reports `complete: true`, `liveness.lastState: ready`, `pageErrors: null`.
- **P2.** Every v16 report: `candidateSource.page == "web/e2-editor-app.js"`, `candidateSource.sha256BeforeRepoint == a3fd9ac1…`, `candidateSource.distPageWasTheSame == false`, `candidateSource.restOfShellEqualsSource == true`, and `servedShell.entrypointSha256 == candidateCutover.pageSha256 == b003534c…`. Every v8 report: `servedShell.entrypointSha256 == e97d6e03…`.
- **P3 (the judged one, spec §23 verbatim).** Per check, per browser: where v8 PASSes every round, v16 PASSes every round; where v8 has a FAIL, v16 has no more FAIL rounds than v8; where v8 has NE and no FAIL, v16 has no FAIL. Basis: `59b3fb4c` already satisfied this on all 84 cells on the previous page (the one count difference was PASS/NE only), and the two `c50c7789` changes act only when a repaint is in flight during the page's own dispose or when the engine answers BUSY.
- **P4 (descriptive, not judged).** Count equality in at least 83 of 84 cells; if a cell differs it is again Firefox `clear-format-removes-every-inline-format` (precondition `allOnWhenTyped`, which varied per round on both profiles in `59b3fb4c`). Firefox `an-inline-format-reaches-a-selection` FAILs on both profiles as before.

## What a miss means

- P1 or P2 missing: the run is not evidence about `b003534c…`; stop and diagnose before anything else in this directory is read as a result.
- P3 missing: a §23 red cell. It blocks the v56 freeze until diagnosed; first suspects are the two `c50c7789` hunks (`git show c50c7789 -- wasm_sdk_probe/web/e2-editor-app.js`).
- P4 missing alone: listed in the README, not a verdict.
- If this run is never made: v16 has no product-path verdict on the page the cutover would ship (spec §23, "從來沒做時").
