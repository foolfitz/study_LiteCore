# Four-arm integration: compatibility preparation

The four-arm block is integrated in `c6213c85`; mirror materialization is corrected in `6c1640f6`. No product, SDK, frozen worker, profile, WASM or shell-generation bytes changed. This directory is the compatibility preparation, not the subsequent qualifying cohort required by `../product-four-arms-source/README.md` (two-stage integration sequence).

## Result

`existing-checks.comparison.json`: **UNCHANGED**, all 42 original checks in their original order, separately in Chrome and Firefox. The population is derived from the bound original runner source and checked against both complete reports; it is not a new handwritten list. The comparison reads the runner versions from Git, verifies their source hashes, binds all four reports by hash, and refuses missing/duplicate/unreached checks. `comparison-controls.json` records a positive model and five red controls (changed outcome, missing check, incomplete run, duplicate check, missing outcome).

Observed original-check outcomes, unchanged after integration:

| Browser | PASS | FAIL | NOT_ESTABLISHED |
| --- | ---: | ---: | ---: |
| Chrome | 36 | 3 | 3 |
| Firefox | 29 | 2 | 11 |

These are measurements, not an all-green product acceptance. Existing FAILs are blank-line bulleting and selection formatting in both browsers, plus the terminal boundary arrow in Chrome; Firefox's boundary arrow remains NE. No existing failure was relabelled.

`preparation-four-arms.judge.json`: the independent reader finds all **24/24 PASS**, four arms × two real browsers × three distinct fresh cells, with no population problems. Each browser preserves 12 measured rows, its readiness/reference, and 13 raw ODT saves. Both complete product runs still reach the terminal boundary check after neutral restoration.

## Preserved failure and fix

`patched-chrome.json` is the first integrated attempt, which timed out at boot with zero checks. `patched-chrome.boot-diagnostic.json` independently records the observation entry returning HTTP 404 and no installed page observer. The old `build_mirror()` iterated only source entries, so the two new override files were absent from the served tree even though the transformed HTML referenced them.

The new regression test `TableAndMirror.test_runner_materializes_the_new_observer_files_in_the_served_mirror` was red for both missing files before the fix. Overrides are now materialized after the mirror walk, including new files. The original tree remains unchanged; the tests verify that the new files are real mirror files and the unchanged app bytes are preserved. The failed report is not overwritten. Corrected preparations use the separate `patched-r2-*` names.

## Reproduction

From the repository root:

```bash
python3 -I findings/evidence/link-batch-v23/feature-protocol/product-four-arms-integration-01/compare-existing-checks.py
```

From `wasm_sdk_probe/`:

```bash
python3 -I tools/judge_v23_product_four_arms.py ../findings/evidence/link-batch-v23/feature-protocol/product-four-arms-integration-01/patched-r2-chrome.v23-four-arms ../findings/evidence/link-batch-v23/feature-protocol/product-four-arms-integration-01/patched-r2-firefox.v23-four-arms --out /tmp/four-arms-preparation-reread.json
```

The canonical reports are `unpatched-{chrome,firefox}.json` and `patched-r2-{chrome,firefox}.json`; source receipts are `unpatched-source.json` and `patched-r2-source.json`. `commands.json` records invocation, source identity, actual timestamps, and exit status. Product runner exit 1 reflects the retained pre-existing FAILs; the two independent preparation readers exit 0.

## Verification before the qualifying run

All exit 0 on the integrated source: four-arm host tests 49, original product-mutation static tests 10, Node observer tests 11, selection tests 50, R1 tests 50, native S5 type/boundary tests 12. The first sandboxed Node invocation exposed only one file-level result and stream-fd errors; it is not used as the 11-case proof. Running after the permission change reported all 11 internal cases explicitly.

The import closure is fixed before the fresh qualifying cohort. This preparation's 24 green rows are not retroactively counted as that cohort.
