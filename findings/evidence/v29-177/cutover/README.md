# v29 page cutover (2026-11-01)

Spec `specs/SPEC-M3-v29-tick-pacing.md` section 2 item 3 and section 10 ("P is done; the cutover is not"). Template: `../../v28-083/cutover/`.

- **Dry run.** `python3 -I tools/build_cutover_page.py --profile e2-editor-v29 --out <scratch>` printed pin `13f674e498a56c8a` -> `e61e5890bac5c1d2` and `pageSha256 022d0cd0...` (`cutover-dry-run.txt`). Its diff against the live page was exactly two lines: the pin (line 53) and the worker URL (line 3859).
- **Write.** `--write --expect-sha256 022d0cd0...` performed it (`cutover-write.txt`); `node --check` passes. Page `3b0a2ebb...` -> `022d0cd0...`.
- **Assets.** `make -n e2-c-assets` printed one `cp` line: the page. `make e2-c-assets` ran it. The dist copy equals its source; the client and `dist/sdk/document-sdk.js` did not move (`hashes-before.txt`, `hashes-after.txt`).
- **Shell digest** (`digest.py` -> `shell-digest-vs-82.txt`): nothing added, nothing removed, changed exactly `web/e2-editor-app.js`, no dist copy differs from its source. Candidate digest `607b280d8ce86b04`.
- **Worker.** `dist/profiles/e2-editor-v29/sdk-worker.js` is `cmp`-equal to v28's (`a5df83db...`), spec section 2.
- **E1-C** before and after: `intact: true`.

Since this cutover `dist/` serves v29. v28 and generation 82 are served only from their own bytes (archive `build/archive/e2-editor-v28-13f674e4-worker-a5df83db`, the page from git).
