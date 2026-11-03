# Prediction, committed before the run

Finding 151's arrow half on host 0.2.52's page: `«Bravo|»`, a real Z there, a real ArrowDown, a real Q 30 ms after the arrow's keydown, the file saved and read. V8d of `tools/diag_v21_dirty_move.py`.

- **v32 (`f6fd0b75`)**: Q lands on the line moved to, P3, in every round, Chrome and Firefox. Ground: the ordered commands take away the 250 ms read-back that carried the old caret (`specs/SPEC-M3-ordered-commands.md` section 1, row 3). A checkpoint is still taken before the move.
- **Control, the 0.2.24 page on v20 (`v8d0224`)**: Q lands on P2, the line before the move, as it did 6/6 in `link-batch-v21`. If the control does not go red, the run says nothing about v32 and this finding stays open.

The same for `v1` (dirty, Ctrl+End, Q 30 ms later) and `v7` (save, then Ctrl+End, then Q), which carry L-142 and Ctrl+Home/End: Q at the end of the document, not at the old caret.
