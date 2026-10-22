# ods-viewer-v2 on the fallback core, after the link (2026-10-22)

The owner ran `bash handoff/ods-viewer-v2/link-gate0.sh` (`make ALLOW_FROZEN_RELINK=1 ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0 dist/profiles/ods-viewer-v2/sdk-manifest.json`), exit 0; `link-ods-viewer-v2-gate0.log` is its whole output. Last line: `probe.wasm gzip: 47972953 bytes (cap 52428800: within)`.

Every reading pre-written in SPEC-M4-viewer-v2 §7.2 holds:

| reading | observed | file |
| --- | --- | --- |
| 1. frozen set | the 1,527-file snapshot checks (exit 0); the only new files are the six of `dist/profiles/ods-viewer-v2/`; none gone | `frozen-set-after.txt` |
| 2. manifest | v1's capabilities + `part-info`, **no `form-controls`**, bits **30771** | `post-link-checks.txt` |
| 3. base | `base-viewer-v2-no35.6f7424a1c1427ad7.data`; data and metadata byte-identical to v1's `base-a11y-no35.6f7424a1…`/`8aae00e7…` | same |
| 4. wasm | `search-result`, `partBefore`, `lateSelectAllResults`, `part-info` 1 each, `verified-caret-readback` 0; `ScDocShell` 18 (v1 18; a6390eef had 11); **`OFormsCollection` 0** (a6390eef 3); differs from a6390eef and from v1; stack literal VERDICT PASS; E1-C intact | same |
| 5. gzip | 47,972,953 (v1 47,972,102 by the same measure: +851) | the log |

Identity: **probe.wasm `e96e01ec…`**, probe.js `fb5fb399…`, worker `9c85043a…`, manifest `fa54c32c…`, base `6f7424a1…`, metadata `8aae00e7…`. Archived at once at `wasm_sdk_probe/build/archive/ods-viewer-v2-e96e01ec-worker-9c85043a/` (with exports.txt, the builder's report, SHA256SUMS, ATTRIBUTION.md).
