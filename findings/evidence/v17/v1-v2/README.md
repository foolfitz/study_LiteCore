# v17: spec 26.3 V1 (reconciliation) and V2 (census on the shipped bytes)

2026-10-07. No browser. Tools: `wasm_sdk_probe/tools/build_base_no35_pack.py` (V1), `wasm_sdk_probe/tools/check_fontconfig_lang_rewrites.py` (V2, running `findings/evidence/114/review/census.py` with LibreOffice's bundled fontconfig 2.18.2). Profiles built by `make dist/profiles/e2-editor-v17/sdk-manifest.json dist/profiles/e2-editor-v17-cjk-r5-ab/sdk-manifest.json` (no link: loader, wasm, worker copied from `build/archive/e2-editor-v15-ad3f68bb-worker-00882139`, `SHA256SUMS` verified); hashes in `profile-sha256.txt`.

| Check | Result | Red case |
|---|---|---|
| V1: `base-r5-no35` = `base-r5` minus exactly `/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`; every other slice sha-equal; size 34,129,451; same sha (`65e8acbb5f0632be…`) built from `base-r5` and from the original image (`wasm-lite/build-headless-probe/instdir/program/soffice.data`, which first reproduces `base-r5` itself) | PASS (`v1-check.txt`) | dropping `65-khmer.conf` as well fails both the file-list and the size clause (`v1-red-extra-drop.txt`) |
| V2: tags rewritten by the profile's own rules, conf.d included by absolute path, every rule file loaded from the pack | v17 **0**, v17-cjk-r5-ab **0**; 21 of 21 conf.d files loaded, 0 from outside (`v2-e2-editor-v17*.{txt,json}`) | v16 **66**, 22 of 22 loaded (`v2-e2-editor-v16.*`); v16 with the relative include left in place reports 0 rewrites but 63 rule files from `/etc/fonts/conf.d` and fails (`v2-red-relative-include-v16.txt`) -- the mistake of 114's first native rerun, now caught by the tool |

Two corrections made on the way, both recorded in the tools: fable's suggested second source (`wasm-lite/build/instdir/program/soffice.data`) is not the image `base-r5` was cut from (`bootstraprc` differs in size); the Makefile's `CORE_DATA` (`wasm-lite/build-headless-probe/`) is. And the census's own output interleaves with fontconfig's debug lines on one pipe, so the rule-file list is read from a separate run that only calls `FcInit`.

Manifest differences (asserted): v16 -> v17 and v15-cjk-r5-ab -> v17-cjk-r5-ab differ only in `profile`, `sdkVersion`, and `artifactFiles.soffice.data` / `soffice.data.js.metadata`.
