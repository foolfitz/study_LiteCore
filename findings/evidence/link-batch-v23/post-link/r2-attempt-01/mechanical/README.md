# R2 post-link mechanical audit and archive

The owner-linked R2 WASM and manifest match the explicit pins: `683b7343bd02b432d4a1b0cea0af8c7542b6a0ad84885e8cc5755a4efdfce078` and `716620972050c5d55485cb99564102cfe0e749af81457180f7f7a265701709da`. The build log contains exactly four object compile commands with the required diagnostic definitions and one full link command with the stack overflow flag. The seven linked outputs and the package-generated worker output have recorded sizes, hashes, and modification times.

All 43 source inputs, 189 core inputs, and 15 AST tooling inputs (13 listed files plus Makefile and collector) match the pre-link records. All 2,326 frozen profile/archive rows match; current inventory at the post-link boundary contains those rows plus exactly four new R2 profile files, with no unexpected additions. The 12 recorded pre-link checks all exited 0 and produced nonempty output files.

The explicit build-log reader, actual WASM reader, and E1-C bundle check were captured through `subprocess.run`; all exited 0. The candidate is ABI 5, has the same full semantic editor contract and capabilities as frozen v22 apart from artifact hashes, and exports exactly the v22 list plus `_oxsdk_v23_diagnostic`. Loader, WASM, worker, and manifest bindings match actual bytes. The worker is byte-for-byte the frozen archived v22 worker plus the R2 tail. The frozen base archive's SHA256SUMS check passed.

The exclusive archive `e2-editor-v23-diag-r2-683b7343-worker-c8a3de87` contains the five bound files, `SHA256SUMS`, and `ATTRIBUTION.md`. Each of the five files matches its source byte-for-byte, and the archive checksum verification passed. The pre-archive inventory record is intentionally a snapshot before these seven archive files were added.

See `audit.json` for all row counts, hashes, mtimes, checks, semantic comparisons, and reader captures. `archive-creation.json` records the exclusive archive copy and checksum verification. `link-v23-diagnostic-r2-01.log` is the complete preserved owner link log.
