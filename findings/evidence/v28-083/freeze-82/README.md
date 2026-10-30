# Generation 82 frozen (2026-10-30), by `--manifest`, the bound tool unchanged

Spec `specs/SPEC-M3-v28-last-line-fallback.md` 7.3 「切頁」 and section 11 step 8. Generation 82 is frozen after every shell change of this batch was in:
- the shell half `0763ed918` (client and page, spec 4.3 items 1-3);
- the cutover `fc85cce5a` (spec 4.3 item 4).

Gates before the freeze: P-v28 (`../post-link/`); S4 run-01 `S4_HOLDS` with its self-test and six mutations caught (`../s4/`).

Precedent: `../../v27-176/freeze-81/`.

**Dry run** (`dry-run.*`, the argv without `--write`). Exit 1, as expected for an unwritten generation. The uncovered list is exactly generation 81's ten excluded paths plus `sdk/v28-last-block-worker.js`.

**Write** (`argv.json`, `freeze-command.json`, `freeze.stdout.txt`).
- The argv is generation 81's (`../../v27-176/freeze-81/freeze-command.json`) with the manifest name changed and an eleventh `--exclude` for `sdk/v28-last-block-worker.js` (the v28 profile worker source, bound by the profile manifest's `workerSha256` `a5df83db…`; the page creates its worker from the profile). Same frozen date.
- Result: `bundleSha256` **`a02673fa0dd34b6b…`**, `problems: []`, `written: true`. `build_e2_c_shell_bundle.py` is not edited.
- File `wasm_sdk_probe/e2/editor-shell-v2-bundle-v82.json`, sha256 `da4e595d859c8659…`.

**Contents** (`v82-vs-v81.txt`): the same 13 included paths; exactly two differ, the closed list of spec 7.3 -- `editor-shell-v2/paragraph-editor-client.js` `7d1c1eb2…` -> `d07a58e0…` and `web/e2-editor-app.js` `b63d8ee5…` -> `3b0a2ebb…` (the page and client S4 run-01 recorded as served for after); 81's ten exclusions carried verbatim, plus the eleventh. The digest equals the candidate digest computed at the cutover (`../cutover/`).

**The Makefile bundle line** (`Makefile:5166`) now passes `--manifest e2/editor-shell-v2-bundle-v82.json` (`bundle-line-witness.txt`): the v81 line on the live tree exit 1; the v82 line exit 0; pointed back at v81 exit 1; the tool default exit 1.

**Assets.** `make -n e2-c-assets`: "Nothing to be done" (`dist/` already holds the page and the client, copied at the cutover).

**Reachability.** `make test-e2-c-reachability` stays red as a whole (`reachability-after.*`, exit 2) on the pre-existing coverage-audit line (now `Makefile:5127`); the transcript equals freeze-81's except that line number, and `coverage-audit-after.txt` is identical to `../../v27-176/freeze-81/coverage-audit-after.txt`.

**E1-C** (`e1-c.txt`): `intact: true`, `187706b2dcb07d2b`.

From here the generation-81 readers are NE on the live tree by construction (S3's and S2′'s products, F3-81, F4-81). V0′-82 re-reads them by putting the declared files back. Any later shell change is generation 83; 82 is never rewritten.
