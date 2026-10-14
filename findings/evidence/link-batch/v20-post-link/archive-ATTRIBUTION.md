# e2-editor-v20, archived 2026-10-14 right after the owner's link (finding 036: the wasm is not a function of the source)

- Linked by the owner on 2026-10-14 at about 10:35–10:38 +0800, from study_LiteCore HEAD `3c9ad3e7` or later. The engine source is final at `543a5566`, and the Makefile v20 block is `d7d62039` plus `543a5566`. The command was `make ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v20/sdk-manifest.json` (`handoff/RUNBOOK-relink-v20.md` §2).
- `probe.wasm` and `probe.js` are the v20 link outputs; `build/e2/editor-v20/probe.wasm` is byte-identical to the dist copy.
- `sdk-worker.js` is the tree's `sdk/sdk-worker.js` (`478d0da1…`, part 1's nine hunks), not the v15 archive's worker.
- `sdk-manifest.json` was packed by `tools/build_e2_editor_v4_profile.py --page-rectangles --inline-range-gestures all` from `sdk/v18-writer-review-manifest.json`.
- The resource packs are v18's (`cjk-sub-e10`, `base-r5-no35`, `fallback-fonts-r5`) under `dist/profiles/resources/`, and they are not copied here.
- `exports.txt` is `build/e2/editor-v20/exports.txt`: v19's list plus `_oxsdk_document_page_rectangles`.
- Post-link checks: X1 v20 mode `VERDICT PASS`; the export mapping in the glue is present; `ScDocShell` occurs 0 times; v8, v15, v18 and v19 are unchanged. The record is in `findings/evidence/link-batch/v20-post-link/`.
