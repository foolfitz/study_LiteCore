# v27 page cutover (2026-10-30)

Spec `specs/SPEC-M3-v27-finding-176.md` 4.3 item 2 and 7.3 「切頁」. Generation 81 is NOT frozen yet; it is frozen after every shell change of this batch (7.3).

- **Dry run.** `python3 -I tools/build_cutover_page.py --profile e2-editor-v27 --out <scratch>` printed pin `44cb15ea8d36f0e0` -> `c089dfd699d646e3` and `pageSha256 b63d8ee5...`. Its diff against the live page was exactly two lines: the pin (line 53) and the worker URL (line 3850).
- **Write.** `--write --expect-sha256 b63d8ee5...` performed it (`cutover-write.txt`); `node --check` passes. The page moved from `a2912310...` to `b63d8ee5...`. The starting page is generation 80's page plus the shell item `9fbbb9b93` (4.3 item 1 and the comment of item 3).
- **Assets.** `make -n e2-c-assets` printed exactly one `cp` (the page); `make e2-c-assets` ran it. `dist/e2-editor-app.js` is `b63d8ee5...`, `cmp`-equal to the source, and `dist/sdk/document-sdk.js` is unchanged (`afdff2d4...`). Hashes: `hashes-before.txt`, `hashes-after.txt`.
- **Shell digest.** The live shell (`build_e2_c_shell_bundle.compute`) differs from frozen generation 80 in exactly `web/e2-editor-app.js`: nothing added, nothing removed, and no dist copy differs from its source. Candidate digest `6eb7ca108ea77c4a`.
- **E1-C after the cutover.** `intact: true` (`e1-c-after-cutover.txt`).

Since this cutover, `dist/` serves the generation-81 candidate (profile v27). Generation 80 and v26 are served only from their own bytes: the page from git at generation 80, the v26 archive's profile.
