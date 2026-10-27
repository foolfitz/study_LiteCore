# Two order-dependent cells, both browsers: preparation only

Invocation from `wasm_sdk_probe/`, outside the sandbox after the local-socket refusal in `../s5-order-prep-01/`:

```bash
python3 -I tools/run_v23_feature_selection.py --population s5 --preparation-only --keep-going --case-id shift-Home@heading-mid/backspace-twice --case-id shift-Home@list-mid/backspace-twice --output ../findings/evidence/link-batch-v23/feature-protocol/s5-order-prep-02
```

Exit 1 as expected: all four complete cells read **NOT_ESTABLISHED: native save not order-independent** under the existing ruling 4. `--keep-going` collects the requested preparation population without relabelling any cell. The runner recorded unchanged `postConfig`; there was no retry. No counted population is claimed.

Both browsers establish the single-line witness and original-document native comparability. Candidate results equal the native every-member-settled saves under ruling 2's native reduction (`strip_ffd(reduce_content(...))`), and equal each fresh settled-WASM arm under full `reduce_content` equality. Both differ from queued-native saves: heading changes paragraph structure; list changes list-item versus list-header while paragraph text remains equal. These four browser observations use two native witness saves, not four independent native repetitions.

The verdicts remain NE. The additional comparisons, timing bindings and lifecycle limitation are in `../s5-order-oracle-review/comparison.json`, reproducible by that directory's `read-prep.py`. Any amendment needs a separate decision; these pages are not retroactively counted.
