Read-only review before a WebAssembly link. Do not modify files. Do not run make, em++, or any build.

Repository: /home/jiajun/LibreOffice/study_LiteCore (sub-project wasm_sdk_probe/). Spec: specs/SPEC-P-ms-formats.md, section 5.1 (engine) and 6.1 (criteria F1-F3); the spec is in Traditional Chinese.

The change under review is findings/evidence/ms-formats/pre-link/codex/diff.patch (commits 05f311d1f and 4b4d33cac). It lets two new engine profiles open and save Microsoft formats:

- Writer `e2-editor-v33`: accept `.docx` beside `.odt` at `oxsdk_document_open`, give the MEMFS input file the accepted suffix, accept `docx` beside `odt` at `oxsdk_document_save`, report `format` in the `opened` JSON, add capability bits OPEN_DOCX (1<<20) and SAVE_DOCX (1<<21).
- Calc `ods-editor-v5`: the same with `.xlsx`/`xlsx`, bits OPEN_XLSX (1<<22), SAVE_XLSX (1<<23).
- Everything is under a new define `OXSDK_MS_FORMATS`; older builds must preprocess to exactly the tokens they had before.
- The table lives in wasm_sdk_probe/src/document_format.hpp. Workers are derived from the frozen predecessors by tests/v33-worker-delta.json and tests/ods-v5-worker-delta.json (tools/derive_ms_formats_worker.py). Manifests are derived by tools/build_ms_formats_profile.py. Make rules are appended at the end of wasm_sdk_probe/Makefile; tools/link_ms_formats_owner.sh runs both links.

What was already checked (do not repeat, but say if a check is weaker than it claims):
- F1: tests/document_format_test.cpp passes; tests/document_format_mutations.py: 18 generated mutations, all red.
- F2: tools/check_ms_formats_syntax.py, em++ -fsyntax-only of every compile command `make -n -B` prints for both probe.js targets, with and without -DOXSDK_MS_FORMATS, positive controls inside the new blocks of sdk_api.cpp and probe_engine.cpp, and -E "every exported _oxsdk_ name has a body": all green (findings/evidence/ms-formats/pre-link/em-checks/report.json).
- F3: tests/ms_formats_worker_test.cjs passes, and both frozen base workers fail it.

Questions, in order of what would cost us most after a link (each link takes ~3 minutes and mints a new artifact hash):
1. Anything that makes either link fail or the profile refuse to start (capability bits vs `expectedCapabilityBits`, exports, the worker's init checks against the manifest, the Makefile rules, the link script).
2. Any older build whose preprocessed output changes (an edit outside an `#ifdef OXSDK_MS_FORMATS`).
3. Paths where a `.docx`/`.xlsx` name or format is accepted by one layer and refused by another (sdk_api.cpp, probe_engine.cpp, the worker gates, the manifest), or where the open reply's `format` can disagree with the MEMFS suffix.
4. Save: Writer's save path writes `/tmp/oxsdk-output-<handle>-<id>.<format>` and calls LOK `saveAs(url, format)`; anything wrong for `docx`/`xlsx` (e.g. the Calc build's save, the ordered-reply wrapper in the Writer build, a filter-options requirement)?
5. Anything in the worker deltas that changes behaviour for ODF documents.

Answer in English, concisely: a numbered list of findings, each with file:line, why it matters, and a suggested fix; then a short list of things you checked and found fine. If you find nothing for a question, say so.
