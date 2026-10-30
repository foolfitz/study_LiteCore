# Generation 81 frozen (2026-10-30), by `--manifest`, the bound tool unchanged

Spec `specs/SPEC-M3-v27-finding-176.md` 7.3 「切頁」 and section 11 step 8. Generation 81 is frozen after every shell change of this batch was in:
- the shell item `9fbbb9b93`;
- the cutover `bbee9b040`.

Gates before the freeze:
- P-v27 (`../post-link/`);
- S3 run-01 `S3_HOLDS` 12/12, with three mutations caught (`../s3/`);
- S2′ run-01 `S2P_HOLDS` 24/24 (`../s2p/`).

Precedent: `../../select-all-v26/freeze-80/`.

**Dry run** (`dry-run.*`, no `--write`). Exit 1, as expected for an unwritten generation. The uncovered list is exactly generation 80's nine excluded paths plus `sdk/v27-first-block-worker.js`, nothing else.

**Write** (`freeze-command.json`, `freeze.stdout.txt`).
- The argv is generation 80's from `../../select-all-v26/freeze-80/freeze-command.json`, with the manifest name changed and a tenth `--exclude` appended for `sdk/v27-first-block-worker.js`. That file is the v27 profile worker source, bound by the profile manifest's `workerSha256` `8152448a…`; the page creates its worker from the profile. The frozen date is the same day.
- Result: `bundleSha256` **`6eb7ca108ea77c4a…`**, `problems: []`, `written: true`. `build_e2_c_shell_bundle.py` is not edited.
- File `wasm_sdk_probe/e2/editor-shell-v2-bundle-v81.json`, sha256 `91f180232b33f2ad…`.

**Contents** (`v81-vs-v80.txt`):
- The same 13 included paths.
- Generation 80's nine exclusions are carried verbatim, path and reason, plus the tenth.
- Exactly one included file differs, the closed list of spec 7.3: `web/e2-editor-app.js` `3b6c023e…` -> `b63d8ee5…`. That is the page S3 run-01 and S2′ run-01 recorded as served for the after product.
- The digest equals the candidate digest computed at the cutover (`../cutover/README.md`).

**The Makefile bundle line** (now `Makefile:5067`) passes `--manifest e2/editor-shell-v2-bundle-v81.json` (`bundle-line-witness.txt`):
- the line as it ran before the change (v80): exit 1 on the live tree;
- as it runs now (v81): exit 0;
- pointed back at v80, rerun after the edit: exit 1;
- the tool default: exit 1.

**Assets.** `make -n e2-c-assets` says "Nothing to be done" (`make-n-e2-c-assets.txt`): `dist/` already holds the page, copied at the cutover and `cmp`-equal.

**Reachability.** `make test-e2-c-reachability` stays red as a whole (`reachability-after.*`, exit 2). It is the pre-existing coverage-audit line, now `Makefile:5028`: the line number moved with the v27 block. `coverage-audit-after.txt` is field-for-field identical to `../../select-all-v26/freeze-80/coverage-audit-after.txt`.

**E1-C** (`e1-c.txt`): exit 0, `intact: true`, `187706b2dcb07d2b`, byte-identical to `../../select-all-v26/freeze-80/e1-c.txt`.

From here the generation-80 readers are NE on the live tree by construction: B1-79/S2-80's products, F3-80, F4-80. V0′-81 re-reads them by putting the declared file back. Any later shell change is generation 82; 81 is never rewritten.
