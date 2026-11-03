# Handoff: opening Microsoft documents -- spec pinned, measured, engine ready to link

Checkpoint **2026-11-03 20:50**. Supersedes `HANDOFF-2026-11-03g-calc-undo-shipped-0255.md` (its state and cautions still stand:
0.2.55 installed on the own stack, nothing pushed, the owner's hand test of 0.2.52-0.2.55 not done).

## The owner's rulings (2026-11-03)

1. Save a DOCX/XLSX back **in its own format**, to the same file (Collabora's behaviour). **Plus a Save As that can convert to ODF.**
2. **DOCX and XLSX only** this batch (no DOC, XLS, docm, xlsm, rtf, csv, templates).

Spec: `specs/SPEC-P-ms-formats.md` (zh-TW, append-only from commit `05f311d1f` on). Sections 1-3 facts, 4 rulings, 5 design, 6 criteria
(pinned), 7 named limits, 8 "if never done".

## What is established

- **The shipped engines already import both formats.** Both wasm files carry WriterFilter / DocxExport / (Calc) ExcelFilter, and both
  FS images carry the MS type and filter definitions. M1 (`tools/run_msformat_wasm.py`, shipped pages, Chrome, files handed over
  under ODF names because of finding 013): 32/32 loadable files open, the page's ODF save equals the native ODF round trip in 31/31
  comparable files. What blocks the product is only our own boundary: `oxsdk_document_open` refuses the names and
  `oxsdk_document_save` refuses the formats (finding 013, open since 08-02).
- **Native 26.8 round trips** (M0, `tools/msformat_native.cpp` + `tools/run_msformat_native.py`): own format keeps content 30/32 and
  pagination 16/16 DOCX; LOK `saveAs(docx)` and `storeToURL` with the load filter agree on every file, so the engine uses plain
  `saveAs`. ODF: content 29/31 (cosmetic differences) but one DOCX goes from 7 to 11 pages.
- **Finding 184** (new): an ODS with many whole-column `COUNTIFS` never finishes loading -- native LOK and desktop 26.8.1.1 past 25
  minutes, OxOffice 12 past 5 -- because the row-height update in `ScXMLImport::endDocument` interprets every formula. It is what
  `forum-mso-en4-134670.xlsx` becomes after Save As ODS. Upstream; recorded, not sent (submissions on hold).
- Collabora's behaviour, read and spot-checked: `findings/evidence/ms-formats/collabora-reading.md`.
- Evidence README: `findings/evidence/ms-formats/README.md`.

## Engine, ready to link (not linked)

- `wasm_sdk_probe/src/document_format.hpp`: the one table (open suffixes, savable formats, per profile). Wired into
  `sdk_api.cpp` (open refusal, save refusal, capability bits), `sdk_api.h` (bits 20-23), `probe_engine.cpp` (MEMFS suffix,
  `format` in the `opened` JSON), all under `OXSDK_MS_FORMATS`.
- Workers: `tools/derive_ms_formats_worker.py` from the frozen v32 / v4 workers + `tests/v33-worker-delta.json`,
  `tests/ods-v5-worker-delta.json` (format in the open reply; open-docx/save-docx, open-xlsx/save-xlsx gates). Derived into build/,
  never into sdk/ (generation 88's bundle check).
- Manifests: `tools/build_ms_formats_profile.py` (from the frozen v32 / v4 manifests; development output under build/ only).
- Make: rules at the end of `wasm_sdk_probe/Makefile`; v5 makes its own export list (equal to v4's) so v4's build files are not
  remade.
- Criteria 6.1 hold: F1 (`make test-ms-formats-static`: table test + 18 mutations, 12 generated from the table and 6 rule
  mutations, all red), F2 (`tools/check_ms_formats_syntax.py`; final run `findings/evidence/ms-formats/pre-link/em-checks-02/`, which
  adds the predecessors' token comparison: v32 and v4 preprocess to the same tokens as at `b013dc154`; red case against `bacfd8c84`
  makes Calc's two changed sources differ), F3 (`tests/ms_formats_worker_test.cjs`: each of the three additions removed alone fails
  at its own assertion, both frozen bases fail, an array `format` is refused).
- Codex read-only review (3 min 17 s): `findings/evidence/ms-formats/pre-link/codex/review.md`. Three findings, all taken (below).

## Next, in order

1. **The link (owner's)**: `cd wasm_sdk_probe && bash tools/link_ms_formats_owner.sh` (about 6 minutes, two links). It refuses if
   any attempt exists, logs to `build/link-ms-formats-{writer,calc}-01.log`, and must print `LINKS_AS_SPECIFIED` (capability bits
   2047|bits 20,21 = 3147775 for v33; 1046835|bits 22,23 = 13629747 for v5). If the owner asks the agent to run it: `uptime`,
   `pgrep -a make` first.
2. **Pages** (spec 5.2): format from the open reply drives every save; Writer's "儲存 ODT" becomes "儲存"; Save As dialog (name, ODF /
   original format) in both pages; `HOST.saveAs(bytes, {name, format})`; without a host, a download; file input `accept` gains
   .docx / .xlsx. The Writer page is generation 89: follow the generation-88 freeze (`c3f49e137`,
   `findings/evidence/demo-batch-5/freeze-88/`, its derive tools, V0', units by hand). The Calc page: `web/ods-editor-app.js`,
   `web/ods-editor.html`, `spreadsheet-shell/calc-editor-session.js` (its `format:"ods"` at line 378). Then `make e2-c-assets` /
   `make ods-editor-assets` (cp only).
3. **W tools** (spec 6.2): derive from `tools/run_msformat_wasm.py` but through the page's own file input with true names (so Firefox
   works too), on the development profiles aliased into a mirror (the `mirror()` pattern of `run_calc_editor_browser.py`). W1 own
   format vs M0's own-format round trip, W2 Save As ODF vs M0's ODF round trip (forum-mso-en4 = NOT_ESTABLISHED, finding 184), W3
   refused names, W4 the existing regression nets; red on v32 / v4 first.
4. Freeze v33 / v5 into dist + archive only after W holds; switch the page pointers; teach every mirror tool that aliases a profile
   name the new names (Calc: `run_calc_editor_browser.py`, `check_calc_style.py`, `check_calc_sheet_view.py`, `check_calc_undo_cu.py`;
   grep the Writer tools for `e2-editor-v32`).
5. **Host 0.2.56** (spec 5.3): `src/files.js` mimes, `EditorController` mime sets (read-only XLSX stays on `ods-editor.html`),
   `documentFormat()` by mime, `saveAs` (If-None-Match: *, 412 -> NAME_TAKEN, then open the new file by `OC-FileId`). H8
   (`host_batch8.py`), red on 0.2.55 first; the regression set in 6.3.

## Cautions

- Do not use an ODF name for MS bytes as a product path (finding 013); M1 did it as a measurement only.
- `run_msformat_native.py` and `run_msformat_wasm.py` write lean evidence (profiles and binaries deleted, dumps gzipped); point
  `--out` at scratch for trial runs.
- The M1 tool is Chrome only (Firefox's WebDriver classic has no init script).
- A shell command with a heredoc full of Make syntax was refused by the harness's rm-safety parser (not run); write such fragments to a
  file and append with a script.
- A wait loop with `pgrep -f NAME` matches itself (memory 10-31): this session started one and had to stop it.

## Section 34.4

- **Fixed-by-execution: 7.** The native harness's `Reference(..., UNO_QUERY_THROW)` on a same-type reference (compile error); the corpus
  survey's `testzip()` (returns a name, does not raise); the WASM tool's 1 MiB CDP frame (retrieval in slices); the desktop arm's
  `/usr/bin/soffice` (the install is `/opt/libreoffice26.8`); the worker test's cross-realm `ArrayBuffer`; the Makefile's `$$$$`;
  the evidence chain's packing (profiles and binaries deleted, 96 MB -> 3.7 MB).
- **Found by reading my own code before running: 2** (the WASM tool's gzip loop deleting its own output; v5's export list depending on
  a rule that lists the Makefile).
- **Fixed-by-review: 3** (Codex, all before any link): the Writer manifest kept v32's `editorContract` loader/wasm/worker sha256
  (the builder now recomputes them; exercised with stand-in artifacts: hashes follow the outputs, bits 3147775 / 13629747); the
  Writer save gate compared `payload.format` while the dispatch sends `String(payload.format)`, so `["docx"]` passed (now both use
  the String; red case on the pre-fix gate: Writer red, Calc not -- its fallback row `save-odt` is never granted, so the bypass never
  existed there, recorded in the test); F3's causal control was not gate-specific (now per-addition removals). Codex also noted F2
  did not compare token streams, so the claim "older builds unchanged" was unmeasured: now measured (above).
- **Wrong statements, corrected: 5**, all mine. Commit `05f311d1f`'s message says "18 generated red cases": 12 are generated, 6
  are rule mutations. The other four, all before commit or in this handoff: the spec's "31 of 32 opened" (32 of 32: the
  failure was the tool's retrieval); "Writer pages 15/15" (16/16) in the spec and in the question put to the owner; finding 184's "56
  idle threads" (24 threads in all, one computing).
- Fable rulings: 0.

## Conventions

Replies to the owner in Taiwan Traditional Chinese with A/B/C options. Evidence and handoff in English, specs and findings in zh-TW.
Compiling `make` and links stay the owner's unless the owner asks. Commit messages: `Co-Authored-By` yes, `Claude-Session` never.
Codex through `codex exec` only.
