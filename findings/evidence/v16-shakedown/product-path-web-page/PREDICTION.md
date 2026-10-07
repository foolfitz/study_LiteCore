# Prediction, before the run: the product-path net on the page the cutover ships

Written 2026-10-07, before any run in this directory. Not counted; nothing is bound to it.

## Why this run exists

The v15 and v16 product-path "candidate" reports measured `dist/e2-editor-app.js` (the v8-era page) with the new engine, while the cutover repoints `web/e2-editor-app.js` (handoff 2026-10-07b, "Which page was measured"). The owner chose A: the runner's candidate mode now reads the cutover's source (`3ab4f04a`, runner sha256 `e31901440c75dc0c…`). This run is the first product-path measurement of B's page (paragraph merge, refusal wording, BUSY budget 6 -> 84).

## Design

- Same runner sha for both arms: v8 is re-run, not reused from the 2026-10-07 morning (those used runner `5900ce87…`).
- Interleaved, one run at a time: Chrome v8 r1, Chrome v16 r1, Chrome v8 r2, Chrome v16 r2, Chrome v8 r3, Chrome v16 r3, then the same six on Firefox.
- v8 arm: no profile flag (the shipped page in `dist/`). v16 arm: `--candidate-profile e2-editor-v16`.

## Predictions

- **P1.** All 12 reports `complete: true`, `liveness.lastState: ready`, `pageErrors: null`.
- **P2.** Every v16 report has `candidateSource.page == "web/e2-editor-app.js"`, `candidateSource.distPageWasTheSame == false`, and `candidateCutover.pageSha256 == 3cf0133033e449ebd553c0ee64e7cbe2ef411e33c6013a4964c2b6123cf11b8f`, which is what `tools/build_cutover_page.py --profile e2-editor-v16` prints at `3ab4f04a`; `servedShell.entrypointSha256` equals it. The old runner served `cc523c9c…` (dist's page) for the same flag.
- **P3.** For each of the 42 checks, per browser, the v16 outcome counts equal the v8 outcome counts. Basis: the product-path net has no arm known to me that presses Backspace or Delete at a paragraph boundary, which is the only path where B's engine behaviour differs; the page's other changes (refusal wording, a longer BUSY retry budget) only act when the engine refuses or is busy. I have not read every arm, so P3 is a prediction, not a derivation.

## What a miss means

- P2 missing: the runner change does not do what `3ab4f04a` says; stop, nothing else in this directory is evidence about B's page.
- P3 missing: a cell differs. That is not by itself a defect; the first suspects are the eight hunks between dist's page and web's page (`diff dist/e2-editor-app.js web/e2-editor-app.js`). It must be diagnosed before shell generation v56 is frozen.
- If this run is never made: no product-path result covers the page the cutover would ship, and the v56 freeze may not cite the product-path net.
