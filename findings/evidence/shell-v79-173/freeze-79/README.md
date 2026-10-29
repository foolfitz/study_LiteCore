# Generation 79 frozen (2026-10-29), by `--manifest`, the bound tool unchanged

Spec `specs/SPEC-M3-shell-v79-finding-173.md` 4.3 and 5.6, after U1, U2 and B1 held (`../README.md`, commit `e5170c84d`). Precedent: `../../link-batch-v25/freeze-78/`.

- **Dry run** (`dry-run.*`, no `--write`): the tool's report for a generation not yet written lists exactly the eight paths v78 excludes as uncovered, nothing else.
- **Write** (`freeze-command.json`, `freeze.stdout.txt`): v78's argv from `../../link-batch-v25/freeze-78/freeze-command.json` with only the manifest name changed (eight `--exclude`, paths and reasons verbatim). Result `bundleSha256` **`d07397e7a9c15789…`**, `problems: []`, `written: true`. `build_e2_c_shell_bundle.py` is not edited; its default `MANIFEST` stays v76 by design.
- **Contents** (`v79-vs-v78.txt`): the same 13 included paths and identical exclusions; exactly two differ, `web/e2-editor-app.js` `6e66c930…` -> `9cb6ea1f…` and `editor-shell-v2/paragraph-editor-client.js` `4616ae17…` -> `7d1c1eb2…` (the closed list of spec 2). File `e2/editor-shell-v2-bundle-v79.json` sha256 `9f544fa7…`. B1's after-product served exactly these two sha256s.
- **Makefile:4947** now passes `--manifest e2/editor-shell-v2-bundle-v79.json` (`bundle-line-witness.txt`): the line as it ran before (v78) exits 1; as it runs now (v79) exits 0; pointed back at v78 exits 1; the tool default (v76) exits 1.
- **`make test-e2-c-reachability`** stays red as a whole (`reachability-after.*`, exit 2) at `Makefile:4908`, the pre-existing coverage-audit line; `coverage-audit-after.txt` is field-for-field identical to `../../link-batch-v25/freeze-78/coverage-audit-after.txt` (same 46 paths, same 7 unattributable listeners, same problems).
- **E1-C** (`e1-c.txt`): exit 0, `intact: true`, byte-identical to `../../link-batch-v25/freeze-78/e1-c.txt`.
- **v79 tools** (derived; the v78 tools are bound by committed evidence and not edited; each docstring states its closed list of differences): `tools/run_v79_f3.py`, `tools/run_v79_four_arms.py`, `tools/judge_v79_product_four_arms.py`, `tools/v79_four_arms_identity.py`, and the new reader `tools/read_v79_f3_equal.py` (self-test on v25 F3 run-02 against itself: equal, 5/5 mutations red).
- **F4 preflight** (`../f4/preflight-*`): READY on the live tree; red when pointed at v78 and red without the override, each naming `editor-shell-v2/paragraph-editor-client.js` as not the reported generation.

If anything forces a shell change after this, that is generation 80; 79 is never rewritten.
