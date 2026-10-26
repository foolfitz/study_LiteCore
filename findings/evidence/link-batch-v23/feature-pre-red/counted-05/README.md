# Historical v19 pre-red counted cohort 05

This is a fresh unfiltered cohort on the corrected frozen source graph, using explicit v19 WASM SHA256 `1aafd4f9da42fd83d9be4c4e9edfbd818e3c7ea17d62fa1cb1bfbd47d1a32819`. The runner completed all 32 cells (16 source-derived cases in Chrome and Firefox) with exit 0. The actual aggregate reader also exited 0 with `populationComplete: true`, 32/32 cells `EXPECTED_RED`, and stale field `caret`. This is only the historical v19 S2 pre-red result; `featureS1S5Acceptance` remains `NOT_ESTABLISHED` by the reader's explicit scope.

Every raw page SHA matches the runner report. All 32 pages booted, recorded trusted `Z` key input, saved an ODT whose first paragraph begins with the inserted `Z`, and have clean teardown records. The run contains 32 unique page hashes and one recorded user agent per browser. All 17 active Python tool-source pins match `tool-source-bindings-03.json` and current bytes; the 15 served-source mirrors and ten v19 profile artifacts also match their run pins.

The lossless storage pack is isolated to this cohort in `../storage-index-03.json`. Its pack command and verify command both exited 0; the index contains one report and 32 raw payload identities. Original `.json` files remain alongside deterministic `.json.gz` storage copies. `store_payloads.py` is storage-only and supplies no product verdict.

`cohort-summary-initial-path-check.json` preserves the first summary's path-prefix comparison mistake. The storage index roots paths at `counted-05/`, while runner rows are cohort-local; `storage-path-correction.json` records the corrected 32-path and SHA mapping. Final `cohort-summary.json` is PASS. The complete runner, aggregate reader, storage commands, source binding and post-run lock captures are adjacent.
