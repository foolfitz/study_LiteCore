# ods-viewer-v1, first link (2026-10-20, 21:16-21:18, the owner's make)

- Source: study_LiteCore b91cee62 (O2 762296f8, O3 9edd8f9e, fixes 9f90d55d and a344c8aa); rule `ods-viewer-v1` in wasm_sdk_probe/Makefile.
- Core: wasm-lite/build-a11y-gate0 (writer+calc+a11y), not rebuilt; its link inputs were not newer than e2-editor-v14's probe.wasm.
- Every file here is byte-identical to dist/profiles/ods-viewer-v1/ at archive time (SHA256SUMS); exports.txt is build/ods/viewer-v1/exports.txt.
- Worker cc2d6514 = sdk/sdk-worker.js at a344c8aa. Base pack 6f7424a1 = e2-editor-v14's 9901e9be minus 35-lang-normalize.conf.
- Finding 036: the wasm is not a function of the source; this archive is the only way back to these bytes.
