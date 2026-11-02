# Host 0.2.46: not a candidate

Spec `specs/SPEC-P-demo-batch-1.md` section 4 and append 1. Packaged, installed on the own stack 2026-11-02 12:58 +0800 and replaced by 0.2.47 53 minutes later. Nobody used it.

- `prepare-release.py` is hand-written: 0.2.45 is counted, so the gate reads that verdict and then this batch's results. The packaging half is 0.2.45's. The five small scripts are derived by `derive_host_0246.py`.
- Host `b9d33d7`, engine `99fd34739f4f68a9`. Delta against 0.2.45: `e2-editor-app.js`, `e2-editor.html`, `ods-editor-app.js`, `ods-viewer-app.js`, `spreadsheet-shell/calc-editor-session.js`, nothing else. `DELTA_HOLDS`, `PACKAGE_HOLDS`, `CANDIDATE_INSTALLED`, Files 52/52, post-install `holds: true`.
- **`host_batch.py` found a regression of this batch** (`host-batch/`, first run; `z10-red-on-0246/`, the same read with Z10 named). Chrome at a 780 px viewport: a horizontal scrollbar 0.2.45 does not have, `scrollWidth` 780 against `clientWidth` 765, and the fit opening at 89% and returning at 87%. On an empty desk the first layout runs before the vertical scrollbar exists; `flex: none`, added for the zoom, stopped the shrinking that had hidden those 15 px. The mirror cannot reach this: its desk already has the scrollbar when the measured document opens.

`host_batch.py` stays here and 0.2.47 runs it with `--out`.
