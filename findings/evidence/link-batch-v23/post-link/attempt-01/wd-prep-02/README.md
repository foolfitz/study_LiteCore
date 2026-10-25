# W-D N=1 preparation, attempt 02

The first case, d1, ran in Chrome and Firefox with the original native FODT bytes under alias wd-d1.odt. Both individual pages passed the W-D reader, and the 18-file instrument source/copy binding checks passed. The full browser report and individual verdicts are under `d1/`.

The next case, d2, was refused before any browser started because the runner's foreign CPU guard measured an external process above its 50% limit. It has zero page records. The refusal is preserved under `d2/`. No retry or later case was run.

This is preparation only (N=1 per browser for d1), not the 120-cell N=5 W-D population. See `index.json` for case order and exact run records. Per-case generated mirror symlinks are retained locally and ignored in Git.
