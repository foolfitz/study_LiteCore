# Additional tooling import closure

This evidence supplements, and does not replace or rewrite, `source-inputs.json`, `core-inputs.json`, or any passed check snapshot. The original source inventory recorded the top-level new wrapper and reader but did not enumerate the inherited Python packing/resource-check chain. This addition closes that inventory gap without executing packing, tests, compilation, or linking.

`tooling-inputs.json` is generated from actual Python ASTs by the adjacent read-only `capture_tooling_inputs.py`. Its roots are the exact r2 packer and build/artifact reader, plus every literal Python script invoked by the actual r2 manifest recipe in the Makefile. The collector derives those recipe roots from the file instead of maintaining a second hand-written resource-check list. The observed four roots yield 13 local Python files and 19 local import edges, including the v5/v4/c/b/e1_support chain and both resource-check chains.

For each `Import` and `ImportFrom`, the collector resolves existing local module/package files from the importer directory, the tools directory used by the scripts' bootstrap, SDK root and repository root; it follows resolved edges recursively. It also inspects literal dynamic module-import calls when statically resolvable, and records dynamic import/exec/eval and sys.path mutation sites. Each local file is hashed, then reread and rehashed after traversal to verify the captured bytes remained current. The collector and Makefile identities are recorded too.

No recognized dynamic import/exec/eval site occurred in this observed local closure. This is not a claim about code inside external packages. `notResolvedLocally` retains every ordinary import that did not resolve within the stated local search roots, including standard-library and third-party modules; those packages are not traversed or hashed here. `sysPathMutationSites` records actual path-bootstrap expressions without executing them. Arbitrary runtime path modifications, nonliteral dynamic imports if introduced, subprocess execution, and non-Python resource inputs are outside the static import-closure guarantee. The existing resource checks, manifests and frozen inventories retain their separate responsibilities.

To collect a fresh comparison without overwriting this snapshot, run from the repository root:

```bash
python3 findings/evidence/link-batch-v23/pre-link/diagnostic-r2-01/capture_tooling_inputs.py > findings/evidence/link-batch-v23/pre-link/diagnostic-r2-01/tooling-inputs-check.json
```

The captured hashes were verified at collection time. This addition changes no candidate/core/build input and requires no repetition of the already passed source, causal or syntax checks. Successor browser-reader/cohort composition remains post-link work and is not represented as complete by this inventory.
