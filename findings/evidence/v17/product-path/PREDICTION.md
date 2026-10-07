# Prediction, before the run: the product-path net on v17 (spec 26.3 V6)

Written 2026-10-07, before any v17 product-path run. Judged by spec section 23; nothing else in this file is a criterion.

## State at the time of writing

- v17 = v16 with `base-r5-no35` (spec 26.2; `../v1-v2/`). Loader, wasm (`ad3f68bb…`), worker identical to v16's.
- Candidate page: `tools/build_cutover_page.py --profile e2-editor-v17` (no `--write`) prints `4c0088c7a518bc36b9cc999d2e67796d20a58525355b68ae67881228dc95b498`; `web/e2-editor-app.js` before repoint `a3fd9ac1…`; v8 arm's page `dist/e2-editor-app.js` `e97d6e03…`.
- Runner `tools/run_e2_c_product_path.py` sha256 `b52779e498ae33cffea5970ad9a6f8cdf49b03240ef1211905ebc68f975c940c` (the same runner as `../../v16-shakedown/product-path-b003534c/`).

## Design (same as `../../v16-shakedown/product-path-b003534c/`)

One runner sha for both arms; one run at a time; interleaved Chrome v8 r1, v17 r1, ... r3, then Firefox. v8 arm: no profile flag. v17 arm: `--candidate-profile e2-editor-v17`. No `--write`, no `make`, nothing under `dist/` or `web/` touched.

## Predictions

- **P1.** 12 reports `complete: true`, `liveness.lastState: ready`, `pageErrors: null`.
- **P2.** v17 reports: `candidateSource.page == "web/e2-editor-app.js"`, `sha256BeforeRepoint == a3fd9ac1…`, `distPageWasTheSame == false`, `restOfShellEqualsSource == true`, `servedShell.entrypointSha256 == candidateCutover.pageSha256 == 4c0088c7…`. v8 reports: `servedShell.entrypointSha256 == e97d6e03…`.
- **P3 (judged, spec 23).** 0 red cells over 42 checks x 2 browsers.
- **P4 (descriptive).** Count differences against v8 are allowed only where a fixture paragraph is zh-TW (or carries the default Asian language) with an Asian font the profile lacks, because those lines change height on v17 (spec 26.3 V4); every other cell has v8's counts, except Firefox `clear-format-removes-every-inline-format`, whose precondition varied per round on both profiles before. Not verified fixture by fixture before the run: which fixtures carry such paragraphs is listed in the README after the run, from the fixtures themselves.

## What a miss means

- P1/P2: not evidence about v17's candidate page; stop.
- P3: a red cell blocks the v56 freeze until diagnosed; first suspect is the layout change of 26.3 V4 (a band or caret check whose fixture moved), second the base pack itself (V1 says it differs from v16's only by the one file).
- If never run: v17 has no product-path verdict and may not be cut over (spec 26.3, "從來沒做時").
