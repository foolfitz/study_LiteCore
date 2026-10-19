# Shell generation v75 frozen, page cut over to e2-editor-v22 (2026-10-20)

This is SPEC-M3-link-batch-v22 §11.7 step 7, as in ruling 5 §4 step 7 and v74's freeze (`4628c9d3`).

It was done after the mirror evidence all passed:
- F3 (§11.3.1);
- E2 and I2-v22 (`../shakedown/item2/README.md`, `63362c9d`);
- I1-rerun with E0-v22 (`../shakedown/item1/README.md`, `98508912`).

## Steps, in order

1. **Backup.** `dist/`'s two v74 copies that the copy overwrites went to `wasm_sdk_probe/build/archive/dist-shell-v74-before-v75-20261020/`, with `SHA256SUMS`: `e2-editor-app.js` `605cf24b…` (= v74's manifest entrypoint) and `e2-editor.html` `1d158149…`.
2. **Cutover.** `build_cutover_page.py --profile e2-editor-v22 --write --expect-sha256 3b96cb16…` changed two lines in `web/e2-editor-app.js`:
   - `PINNED_WASM_SHA256` went from `db3408f55316bf67` to `f7a40bcce073d913`;
   - `workerUrl` went from `./profiles/e2-editor-v21/sdk-worker.js` to `./profiles/e2-editor-v22/sdk-worker.js`.

   The page hash went from `609023fc…` to `3b96cb16…`, which is pageServed, the page every v22 evidence report was taken on.
3. **Relink queue DRIFT.** `queue-v11-cutover-soak-not-started` drifted, by design, the moment the v22 page was written (`check-relink-queue-red-before-reanchor.txt`, exit 1, that item alone).
4. **Copy.** `make e2-c-assets`, cp only, run by the session (the owner authorized it, and no other `make` was running; load 0.25). It copied `web/e2-editor.html` and `web/e2-editor-app.js` into `dist/`. `dist/` now holds `3b96cb16…` and `b9c2b975…`.
5. **Freeze.** `build_e2_c_shell_bundle.py --write --frozen-date 2026-10-20` (`MANIFEST` bumped to v75, with a comment block) wrote `e2/editor-shell-v2-bundle-v75.json` (`bundle-v75-write.txt`).
   - **bundleSha256 `5b14038e8f50e96679392b9c1ca11880c74baf3eafd7ad717775210ebf8a9b28`.**
   - The problems list, rechecked after the write, is empty.
   - It differs from v74 in the entrypoint only. The included set is v74's 13 paths, and the exclusions are v74's three (inherited from v40, equal to v74's).
6. **Gesture offers.** `e2/expected-gesture-offers.json`: only `profile` changed, from `e2-editor-v21` to `e2-editor-v22`.
7. **Relink queue re-anchor.** The incumbent-anchored check now looks for `profiles/e2-editor-v22/sdk-worker.js`, with a CORRECTION appended to the note. v22's manifest has no `documentOutline` (0 matches), so the expectation stays `absent`. `check-relink-queue-after-reanchor.txt` reads 0 drifted, exit 0.
8. **Static tests.** `make test-e2-c-static` exit 0 (`test-e2-c-static-after-freeze-v75.txt`): node 490/490 and 5/5, python 108 and 134 OK.
9. **E1-C and the shell digest.** E1-C `intact: true`. The shell digest over `dist/` and over the tree are both `e35923a0…`, unchanged, as spec §12 (a) says (`e1c-and-shell-digest.txt`).

## What is still ahead

- The host 0.2.27 package and install, and the host arms H-154c, H-154o, D2-v22 and M11-autosave (§11.7 steps 8–9). These touch ddev.
- K and what moves with it (§13).
