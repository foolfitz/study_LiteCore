# Explicit r2 bounded and W-D tooling

This is tooling preparation following handoff step3 and the section20 owner-proxy ruling, after the owner linked `e2-editor-v23-diag-r2`. No browser result is claimed here. Build checks, packer, core, SDK and frozen artifacts are unchanged.

The bounded and W-D tools now accept only the explicit original/r2 identities. Omitting `--profile` still selects the original; it does not infer r2 from ABI5 or a directory name. r2 requires the owner-linked four-artifact identity: WASM `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078`, manifest `716620972050c5d55485cb99564102cfe0e749af81457180f7f7a265701709da`, worker `c8a3de873c3fbd61b20cc3404eb582433f0c8b1db2e52be374671c3b8851de50`, loader `f0c77adde7313ece193f16b3a97ea6d539492d282ad787b4f2cdb260c7229fd3`. The reader reads actual files and compares them with browser-fetched artifact hashes. v22 and unintended successors are rejected.

Both tools bind their current local JavaScript import graph and statically reachable local Python tools; readers compare the complete source hash map, the served mirror imports and browser-fetched entry HTML/JS hashes. W-D additionally retains its own module/native-oracle source checks. These are new instrument generations: historical reports remain attributed to their historical source hashes and verdicts; changing a reader does not silently bless earlier records.

## The same24 logical bounded obligations

For r2, `--arm all` runs only smoke/proof/hang: three arms, two browsers, N=3 =18 fresh processes. The runner and page reject r2's old plain-NONE `js-thread` arm. The bounded reader rejects a generic r2 js-thread cell even if someone supplies it in a report.

The remaining six logical js-thread obligations are **references to the actual corrected040 frame-html-js observations**, not six new executions. Supply the negative report with `--corrected-040-report`. The reader independently verifies its r2 identity, full actual remaining-instrument graph, source population and archived fixtures, then rejudges every actual html-negative cell with the corrected040 reader. It retains report path/SHA256, run index and page-record SHA256 as the reference identity. Exactly Chrome/Firefox×rounds1–3 are required; duplicate cells, duplicate report/index references and copied page observations are rejected. A reference cannot use the old candidate or a sibling040 arm. This produces18 direct cells plus6 referenced cells for the fixed24 logical obligations. It does not add repetition counts to the corrected040 population.

Missing references give NOT_ESTABLISHED. A complete population with any failed cell stays failed. Source/mirror/identity mismatch refuses reading. Exact040 still requires its separately declared18-cell r2 population, including destroy and literal engine-thread HTML; a bounded PASS alone does not close040 or all section9.2.

r2 proof/hang also require their actual wire rejection/cancellation evidence. The SDK timer itself is unchanged. The old default identity and original four-arm checks remain explicit; the old failed plain-NONE observations are not rewritten.

## W-D

The fixed12 cases, Chrome/Firefox, N=5 =120 cells, native oracle comparisons and private-input provenance are unchanged. Only explicit identity selection and complete source/executed-module binding are added. `judge_v23_wd.py --profile e2-editor-v23-diag-r2` reads r2; omission keeps the original strict default. A native FODT fixture is served byte-for-byte with an explicit `.odt` loader alias, as already required by the public C suffix gate.

## Preparation commands (run only after coordination)

From `wasm_sdk_probe`, the bounded preparation below creates six cells (N1), not acceptance. Replace only the fresh output directory when repeating preparation; do not overwrite earlier evidence.

```sh
python3 -I tools/run_v23_diagnostic.py --profile e2-editor-v23-diag-r2 --wasm-sha256 683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078 --fixture test-docs/e1/plain-grapheme.odt --rounds 1 --output ../findings/evidence/link-batch-v23/post-link/r2-attempt-01/bounded-prep-01
```

After preparation, the same command with `--rounds 3` and a fresh `bounded-01` directory runs the18 direct cells. Once corrected040 negatives exist, read them by reference:

```sh
python3 -I tools/judge_v23_diagnostic.py ../findings/evidence/link-batch-v23/post-link/r2-attempt-01/bounded-01/report.json --profile e2-editor-v23-diag-r2 --profile-dir dist/profiles/e2-editor-v23-diag-r2 --wasm-sha256 683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078 --corrected-040-report ACTUAL_CORRECTED_040_NEGATIVE_REPORT.json
```

For one W-D preparation case, substitute its already declared native fixture from `v23_wd_cases.FIXTURES`, keep exact bytes, and use the `.odt` alias:

```sh
python3 -I tools/run_v23_diagnostic.py --profile e2-editor-v23-diag-r2 --wasm-sha256 683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078 --fixture ../findings/evidence/link-batch-v23/native/ordered-commands/fixtures/numbered-second.fodt --fixture-name native-input.odt --arm wd --case-id d1 --rounds 1 --output ../findings/evidence/link-batch-v23/post-link/r2-attempt-01/wd-d1-prep-01
```

The W-D acceptance reader command takes the actual12 report paths and explicit r2 flags; N1 intentionally cannot satisfy its120-cell population. All runners still acquire the shared browser lock, apply the existing foreign-load guard and clean up only owned processes. No make, host, service configuration or release-counter operation is part of these commands.
