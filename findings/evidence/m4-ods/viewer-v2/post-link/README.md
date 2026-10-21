# ods-viewer-v2, after its first link (2026-10-22)

The owner ran `make ALLOW_FROZEN_RELINK=1 dist/profiles/ods-viewer-v2/sdk-manifest.json` (`link-ods-viewer-v2.log`). Compile, link, worker pin, the builder (base `07ef15cd`, positive control 9901e9be, 9 files differing from v1's base as read in SPEC-M4-viewer-v2 §5.2), the copy into `dist/profiles/ods-viewer-v2/` and the silent marker checks all passed. **make then ended "Error 1" on the rule's last line**, a print of the gzip size whose Python one-liner had `\"` inside single quotes (SyntaxError). It is the last line of the recipe and only prints; a failed marker check would have removed the manifest, and it is there. Fixed in the Makefile afterwards and the fixed line run by hand on this wasm: `probe.wasm gzip: 49153029 bytes (cap 52428800: within)`.

`frozen-set-after.txt`: `sha256sum -c` over the 1,517-file snapshot passes; the only new files under `dist/profiles/` and `build/archive/` are the six of `ods-viewer-v2/`; nothing removed.

`post-link-checks.txt`: pthread stack VERDICT PASS (1,048,576); markers `search-result`, `partBefore`, `lateSelectAllResults`, `part-info` present, `verified-caret-readback` absent; `ScDocShell` 11, `OFormsCollection` 3 (v1: `lateSelectAllResults`/`part-info`/`OFormsCollection` all 0); manifest capabilities v1's + `part-info` + `form-controls`, bits 63539; E1-C intact; sha256 of the six files.

Identity: **probe.wasm `a6390eef…`**, probe.js `6bba8e26…`, worker `9c85043a…`, manifest `0bfa28f7…`, base `07ef15cd…`. Archived the same hour at `wasm_sdk_probe/build/archive/ods-viewer-v2-a6390eef-worker-9c85043a/` (with exports.txt, the builder's report, SHA256SUMS, ATTRIBUTION.md).

gzip 49,153,029 bytes: F-2 does not apply (3,275,771 under the cap; the pre-link estimate from the two cores was 49,140,931).
