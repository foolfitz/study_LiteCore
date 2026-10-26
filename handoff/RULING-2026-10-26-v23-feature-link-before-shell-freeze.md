# Feature link before final shell generation

Owner-proxy staging decision by Astra `/root/astra_calc_scope`. Source inspection only; no build, test execution, artifact rewrite, service or host action was performed for this decision. This refines the order already required by the ABI6 design and feature protocol; it does not change a test predicate or declare a failed test passed.

## Concrete boundary

The feature implementation and exact target now exist (page `e3b84b5f`, target `0385405f`, packager `1381a2a0`). The actual feature WASM hash cannot be pinned in the product page before the owner's link produces it. The default page therefore still points to v22, and the current shell manifest remains generation75. Do not freeze generation76 while that page identity remains provisional, and do not rewrite generation75.

`tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree` calls `bundle.compute(PROJECT)` and compares the current source/dist graph to the current generation75 manifest. It is required to report changed client/session/page bytes, stale dist bytes and newly available files not yet covered or excluded by that manifest. Its covered-file, new-file and stale-dist negative controls establish that this is the intended guard, not an unexpected failure to hide. New separately bound profile workers do not silently disappear from coverage merely because their purpose is known to the implementer.

**Permit only the fresh owner-executed feature compile/link at this boundary**, after focused feature controls, applicable older checks, source/core/worker provenance, review and exact dry-run preparation. Retain the literal broad-static shell-binding failure with command, exit, complete problem list and current source/dist/manifest identities. Label it an outstanding final-shell binding obligation. Do not say `test-e2-c-static` passed, skip/xfail this test, relax `problems`, manufacture matching metadata, or revert implementation merely to obtain a green historical bundle.

If the broad target stops at this known failure, run its remaining applicable checks independently with their actual command and exit recorded; a short-circuited target is not evidence that later checks ran. Any other failure needs its own concrete disposition and is not covered by this decision. This ruling does not authorize an agent to run a compiling make, even where a target's name includes “test”. The owner remains responsible for the fresh product link.

## Mandatory order before feature acceptance

1. Read the actual feature link output and all five bound artifact identities; complete the declared audit and preserve the new archive. No diagnostic profile/archive is overwritten.
2. Change the intended product page's URL and WASM pin together to that exact feature identity, complete the source changes and causal checks, and verify that the intended public route actually selects ABI6. A source page still targeting v22 is not ABI6 product evidence.
3. Only then mint the new shell generation (planned76), preserve generation75 unchanged, synchronize every bound dist module, and make the new manifest's source graph coverage explicit. Separately profile-bound workers require an actual reasoned coverage disposition in the new generation; this is not permission to remove coverage checks or to exclude product dependencies that the graph actually uses.
4. Run the unchanged real-tree shell guard against the new final generation and preserve its PASS, along with the applicable static controls. Required acceptance instruments must bind the final page/shell/profile identities and readiness. Until these steps pass, no feature acceptance/counting or claim of a ready product shell follows from successful linking.

The v19 sixteen-cell pre-red and missing S5 reference executions retain the order/defaults in the feature protocol. Diagnostic closure, C2's recorded NE, all frozen identities, existing case populations and thresholds remain unchanged. This decision grants no host installation, live-file mutation, K count or new capability.
