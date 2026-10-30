# v28 page cutover (2026-10-30)

Spec `specs/SPEC-M3-v28-last-line-fallback.md` 4.3 item 4 and 7.3 「切頁」. Generation 82 is NOT frozen yet; it is frozen after S4 (7.3, 11 step 8).

- **Dry run.** `python3 -I tools/build_cutover_page.py --profile e2-editor-v28 --out <scratch>` printed pin `c089dfd699d646e3` -> `13f674e498a56c8a` and `pageSha256 3b0a2ebb...`. Its diff against the live page was exactly two lines: the pin (line 53) and the worker URL (line 3859).
- **Write.** `--write --expect-sha256 3b0a2ebb...` performed it (`cutover-write.txt`); `node --check` passes. The page moved from `3aa2d931...` (generation 81's page + the v28 shell half `0763ed918`) to `3b0a2ebb...`.
- **Assets.** `make -n e2-c-assets` printed exactly two `cp` lines: the page and the client (the client carries the v28 shell half, 4.3 items 1-2, which was never copied to `dist/` before today). `make e2-c-assets` ran them. Both dist copies are `cmp`-equal to their sources; `dist/sdk/document-sdk.js` is unchanged (`afdff2d4...`). Hashes: `hashes-before.txt`, `hashes-after.txt`.
- **Shell digest** (`digest.py` -> `shell-digest-vs-81.txt`, `build_e2_c_shell_bundle.compute` against `e2/editor-shell-v2-bundle-v81.json`): nothing added, nothing removed, changed exactly `editor-shell-v2/paragraph-editor-client.js` and `web/e2-editor-app.js` (the spec's closed list), no dist copy differs from its source. The one other problem the builder reports is `sdk/v28-last-block-worker.js` in scope but uncovered -- the exclusion 7.3 declares for the freeze. Candidate digest `a02673fa0dd34b6b`.
- **E1-C** before and after: `intact: true`.

Since this cutover, `dist/` serves the generation-82 candidate (profile v28). Generation 81 and v27 are served only from their own bytes: the page and client from git at generation 81, the v27 archive's profile.
