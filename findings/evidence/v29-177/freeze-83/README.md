# Generation 83 frozen (2026-11-01), by `--manifest`, the bound tool unchanged

Spec `specs/SPEC-M3-v29-tick-pacing.md` section 2 item 3. Generation 83 differs from 82 only by the cutover (`../cutover/`). Precedent: `../../v28-083/freeze-82/`.

**Dry run** (`dry.*`, `freeze.py dry`). Exit 1, as expected for an unwritten generation; the uncovered list is exactly generation 82's eleven excluded paths.

**Write** (`freeze.py write`, `argv.json`, `write.*`). The argv is generation 82's with the manifest name and the frozen date changed. No exclusion is added: v29 reuses `sdk/v28-last-block-worker.js`. Result: `bundleSha256` **`607b280d8ce86b04...`**, `problems: []`. `build_e2_c_shell_bundle.py` is not edited. File `wasm_sdk_probe/e2/editor-shell-v2-bundle-v83.json`, sha256 `98371d7f7479021d...`.

**Contents**: the same 13 included paths; exactly one differs, `web/e2-editor-app.js` `3b0a2ebb` -> `022d0cd0`; 82's eleven exclusions carried verbatim.

**The Makefile bundle line** now passes `--manifest e2/editor-shell-v2-bundle-v83.json` (`bundle-line-witness.txt`): v82 line on the live tree exit 1; v83 line exit 0; pointed back at v82 exit 1; tool default exit 1.

**Assets.** `make -n e2-c-assets`: nothing to be done. **E1-C** (`e1-c.txt`): `intact: true`, `187706b2dcb07d2b`.

From here the generation-82 readers are NE on the live tree by construction; V0′-83 re-reads them by putting the declared files back. Any later shell change is generation 84; 83 is never rewritten.
