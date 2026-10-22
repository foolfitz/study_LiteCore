# E4b and E9 on the product page, ods-viewer-v2 `aa576ce7` (2026-10-23 01:19-01:20 CST)

The product page `web/ods-viewer.html` after SPEC-M4-viewer-v2 §9 (its one worker literal names `ods-viewer-v2`, study_LiteCore `ffb6fe57`), on a mirror, through the page's own file input and tab buttons. Runner: `tools/run_ods_viewer_e4b_e9.py --profile ods-viewer-v2 --phase-e-report ../full-corpus/report-2026-10-22T032908Z.json --out <this dir>`; selftest 16/16 before the run.

| report | result |
| --- | --- |
| `report-2026-10-22T171944Z.json` | **E4b PASS** (2/2): surface 1785 = ceil(26775 / 15) on `three-sheets-distinct.ods`, 1837 = ceil(27555 / 15) on `tdf149752.ods`; after the scroll the right-most drawn edge reaches the surface width on both. **E9 PASS**: tabs Alpha/Beta/Gamma = partNames = manifest, all enabled, namesFromEngine, no adapter fallback; clicks 1, 2, 0 read back 1, 2, 0; each click's 1024 tile equals that part's first tile in the reference report |
| `red-cases/report-2026-10-22T172002Z.json` (`--red-case no-refit`) | **reproduced**: E4b red on both fixtures with v1's numbers (surface 1773 vs 1785, the 12 px; 1844 vs 1837), E9 still PASS |

Checks the spec asked for by hand (§9.3): the run's `probeWasmSha256` is `aa576ce7…`, worker `9c85043a…`, `pageWorkerUrl` is `./profiles/ods-viewer-v2/sdk-worker.js`; the E9 reference (`e5Reference.probeWasmSha256`) is the same `aa576ce7…`. Tiles: part 0 `1b932354`, part 1 `3635871d`, part 2 `66d2499b` in both.

Preconditions recorded, not refused (no criterion here is a time): no other Chrome, wallet not locked, 1-minute load 1.23 and 1.01 (the gate's own line says "not below 1.0").

Reading (§9.3, the first row): E4b and E9 hold on `aa576ce7`; with §8.5 every E criterion the mirror can measure holds on this link. Next: the host package.
