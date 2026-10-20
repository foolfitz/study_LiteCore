# O2: the viewer's engine source, worker half and SDK, before any link

Spec: `specs/SPEC-M4-ods-in-nextcloud.md` §3.2, §3.3, addenda 1 and 3. Nothing here was linked or built
with `make`; the engine paths are **syntax-checked only** and their first execution is the owner's
link of `ods-viewer-v1` (O4) and E2 after it.

## What landed (all under `OXSDK_ODS_VIEWER` unless said otherwise)

| item | where |
| --- | --- |
| the pure rules: accepted names (`.ods`/`.odt`, any case, a stem required), the document type's spelling, the part range, and part_text's order (switch, select all, read, deselect, switch back) | `src/ods_viewer.hpp` (new; included only under the define) |
| W7a open accepts `.ods`; M1 the input file's suffix follows the accepted name | `src/sdk_api.cpp` (open), `src/probe_engine.cpp` (`inputSuffixFor`, `writeInputFile`) |
| W7b `documentType` and `inputSuffix` on `opened` | `src/probe_engine.cpp` (`handleOpen`) |
| W7c–e `set_part`, `current_part`, `part_name`; B1 `part_text` | `src/probe_engine.cpp` (handlers, dispatch, submit), `src/probe_engine.hpp`, `src/sdk_api.h`, `src/sdk_api.cpp` |
| B2 the tile reply's three size fields | `#if defined(OXSDK_E2_FORMAT_BARRIER) \|\| defined(OXSDK_ODS_VIEWER)` |
| addendum 1: the two close stages | `#if defined(OXSDK_DIAGNOSTIC_CLOSE_STAGES) \|\| defined(OXSDK_ODS_VIEWER)` |
| M2 no save: `oxsdk_document_save` not compiled (EMSCRIPTEN_KEEPALIVE exports whatever the list says); capability bits without SAVE_ODT, with OPEN_ODS (1<<11), PART_SWITCH (1<<12), PART_TEXT (1<<13) | `src/sdk_api.cpp`, `src/sdk_api.h` |
| a compile guard: the define requires `OXSDK_READER_PROFILE` and refuses every editor define | `src/probe_engine.cpp` (`#error`) |
| **not under the define:** three use sites of editor-only names wrapped in `#ifdef OXSDK_EDITOR_DISCOVERY` (see below) | `src/probe_engine.cpp` |
| the worker half: four operations gated on `part-switch` / `part-text`, a non-integer part refused before the engine, four reply cases with named fields, the open reply's two fields only when sent | `sdk/sdk-worker.js` (excluded from the shell bundle; bound per profile) |
| D3 = A: `OdsViewerEngine extends DocumentEngine` | `viewer-shell/ods-document-sdk.js` (new) |
| the page uses it; E4b's page half: `session.refit()` after the first paint | `web/ods-viewer-app.js`, `viewer-shell/ods-viewer-session.js` |

### `part_text` waits on the engine thread

`.uno:SelectAll` is posted with `bNotifyWhenFinished`; its `LOK_CALLBACK_UNO_COMMAND_RESULT` is queued on
the view's callback flush handler (`desktop/source/lib/init.cxx`, `DispatchResultListener::dispatchFinished`)
and arrives from LOK's thread. The engine thread waits for it (10 s deadline, its own mutex) instead of
returning to its queue, so no paint runs between the switch, the selection and the switch back. On a
timeout the selection is reset and the part restored anyway (`readPartText`), and a SelectAll that lands
after the deadline finds the wait inactive (registered in the spec).

## Found on the way: the reader shape did not compile

`em++ -fsyntax-only` of today's `probe_engine.cpp` with the reader shape (`-DOXSDK_READER_PROFILE`, no
editor define) and the a11y core's flags fails at HEAD `fe8722df` with 16 errors, before any of this
work (`syntax-checks.txt`). The reader profiles in `dist/` were linked in August; since then three use
sites of names declared only under `OXSDK_EDITOR_DISCOVERY` became unconditional:

- `refreshEditorAccessibility()` at open (made unconditional on 2026-08-17, the comment above it says why);
- `readSelection()` / `handleGetSelection()` (the `SelectionReadback` type);
- the engine loop's `gEditorPending` deadline arm.

Each use site is now inside `#ifdef OXSDK_EDITOR_DISCOVERY` (the GetSelection dispatch answers
`UNSUPPORTED_OPERATION` in a build without it). **Consequence for the viewer: it switches no accessibility
on at open**, which is what the plan's D2 said and what W2, W5 and step 1 did not measure (they ran on
editor profiles, accessibility on). Registered in spec addendum 3.

The plain `CPPFLAGS` of the old reader rules has no boost include, so those rules cannot compile today's
engine either way; the viewer's rule uses `E2_V5_CPPFLAGS`.

## Evidence

- `syntax-checks.txt`: the viewer's two translation units and the reader shape, exit 0, 0 errors,
  0 warnings; the red copy (an undeclared call injected into `handlePartText`) fails with the define;
  HEAD's 16 errors listed.
- `preprocess-identity-base-fe8722df.json` (`preprocess_identity.py --base fe8722df`, a one-shot
  measurement reusing `tools/check_merge_key_undo_scope.py`'s machinery: the Makefile's own compile
  command per object from `make -n -B`, preprocessed from a scratch tree at BASE and one as now):
  **28 rules, 112 objects: 111 identical token streams, 1 unbuildable on both sides
  (FINDING_012_DIAGNOSTIC, no boost include), 0 different.** The three rules outside that pattern
  (`src/%.o`, R5 writer-review, R5 writer-reader) were preprocessed by hand: `probe_api`, `sdk_api` and
  `unoembind_stub` identical; `probe_engine` unbuildable on both sides (boost).
- Native model test `tests/ods_viewer_test.cpp`: ok; `tests/ods_viewer_mutations.py`: 10 mutations of
  the header, each red in its named check.
- Worker: `sdk/tests/sdk-worker-ods-viewer.test.mjs` 7/7; `tests/sdk_worker_ods_viewer_mutations.py`:
  7 mutations, each red in its named test. The first run had one NOT RED: the "exact keys" test compared
  keys after a JSON round trip, which drops a key whose value is undefined; it now reads the raw message.
- SDK: `tests/ods-document-sdk.test.mjs` 7/7 (the last one drives the real `OdsViewerSession` through
  the subclass); `tests/ods_document_sdk_mutations.py`: 6 mutations, each red in its named test.
- Session: `tests/ods-viewer-session.test.mjs` 24/24; `findings/evidence/m4-ods/W9-viewer-draft/red-cases.py`:
  38 mutations (M36–M38 for the refit), `problems: none`.
- Existing suites: `node --test editor-shell-v2/tests sdk/tests editor-shell/tests` 673/673; the Python
  tests in `wasm_sdk_probe/tests/` all OK except `test_e1_corpus.py` (the E1 corpus generator; it reads
  neither `src/` nor `sdk/`, not investigated here); E1-C `intact: true`; shell bundle v75 unchanged.
- `tests/test_e2_profile.py`: two source-text tests were misjudging the new code and were changed, each
  with the reason in the test: a fixed 6000-character window that held its guard with 26 characters to
  spare (now the whole function), and the `getTextSelection` call-site census (now counted outside the
  viewer's region, with the region's own count pinned to one and the compile guard asserted whole).
