# Task 2026-10-16: link v21, implementation (parts E and S, run in parallel)

Repo: `/home/jiajun/LibreOffice/study_LiteCore`. The source of truth is `specs/SPEC-M3-link-batch-v21.md`, pinned at `523871fa`.

- **§11 is the only criteria table.** §4, §9 and §10 give the design; where they differ, the later section wins.
- Read the whole spec first, then `handoff/PLAN-2026-10-16-link-batch-v21.md`, then the pin list `handoff/link-batch-v21/pin-list-grep.txt`.

The batch ships two items:
1. **Finding 142**: `move-document-start` / `move-document-end`.
2. **Markdown paste**: a document-level export, gated by a manifest declaration.

The engine runs **threaded LOK, not unipoll**. See spec §9.1.

## Hard rules (both parts)

- **Never run a compiling `make`.** The owner runs every compiling make (global rule). Test-only targets such as `make test-e2-c-static` are allowed, and so are single-file `c++`/`cc` compiles of model tests and native harnesses into `build/` or a scratch directory.
- **Do not touch:**
  - `dist/`;
  - `build/archive/`;
  - any frozen profile;
  - the E1-C-bound files: `editor-shell/*` and `input/*`. `python3 tools/check_e1_c_bundle_intact.py` must keep printing `"intact": true`;
  - the v4 builder `tools/build_e2_editor_v4_profile.py`.
- **Keep older builds byte-identical.** Every engine change, new `#include` and new constant goes under `#ifdef OXSDK_E2_V21_LINK_BATCH`, so v8–v20's preprocessed output stays the same.
- **Do not commit.** The main session reviews your diff and commits it. When you finish, report:
  - the list of changed files, with a one-line reason per file;
  - the tests you ran and their exact results;
  - anything in the spec that you could not implement as written. Stop and report instead of improvising new mechanism (CLAUDE.md §4).
- **Red first.** Every new test must be shown red on a deliberate mutation before you call it green. Record the mutation and its output.
- Both parts edit disjoint files. If you need a file the other part owns, stop and report.

## The interface both parts code against (fixed here; do not change it)

### Wire and internal ids

| | `move-document-start` | `move-document-end` |
|---|---|---|
| wire id | 22 | 23 |
| internal id | 24 | 25 |

- Editor ABI 5 (`OXSDK_EDITOR_ABI_VERSION 5u` under the v21 define).
- Bounds: `kMaxInternalEditorAction` becomes 25, `kMaxExternalAction` becomes 23, both under the define.
- `editorActionMutates` excludes 24 and 25.

### Key path

- `Key::HOME | EditorMod1Modifier` and `Key::END | EditorMod1Modifier`, posted the way select-all posts its key.
- `mutation = false`.
- Completion: `EditorCaretOrSelectionCallback`.
- The 250 ms readback is always armed.
- Completion strings are the same as for the six moves.

### Manifest

- **Actions:** `{"move-document-start": {"id": 22, "gestures": ["collapsed"], "limits": ["no-extend-selection"]}, "move-document-end": {"id": 23, …}}`.
- `editorContract.abiVersion = 5`.
- `editorContract.pasteMarkdown = "document-sdk-paste-markdown"`, declared only with builder flag `--paste-markdown`. The builder refuses the flag unless the export list holds `_oxsdk_document_paste_markdown`.

### C export

`int32_t oxsdk_document_paste_markdown(oxsdk_request_id request_id, uint32_t document_handle, const char *utf8, uint32_t utf8_length)`

- Same shape as `oxsdk_document_insert_text`.
- Exported as `_oxsdk_document_paste_markdown`.
- Engine function: `probe::pasteMarkdown`, following `probe::pageRectangles` (`probe_engine.cpp:6924`).

### Engine reply

- **Success:** `{"type":"markdown-pasted","revision":<new>, …}` with revision +1.
- **Errors:** `emitCommandError(command, "paste-markdown", CODE, msg)`, where every pre-dispatch refusal also carries `"dispatched": false`.
- **Pre-dispatch codes**, checked in this order, nothing dispatched:
  1. `INVALID_ARGUMENT` for NUL, more than 65,536 UTF-8 bytes, a parse failure, or no block other than `MD_BLOCK_DOC`;
  2. `MARKDOWN_ENCODING_UNSUPPORTED` when `osl_getThreadTextEncoding()` is not UTF-8;
  3. `MARKDOWN_NEEDS_CARET` for the §10.2 collapsed rule;
  4. `MARKDOWN_REMOTE_IMAGE` for an `MD_SPAN_IMG` whose src is not `data:` (case-insensitive);
  5. `MARKDOWN_HTML_UNSUPPORTED` for `MD_BLOCK_HTML` or `MD_TEXT_HTML`;
  6. the `.uno:Undo` read before the paste fails.
- **Post-dispatch:** `MUTATION_OUTCOME_UNKNOWN` when the read after the paste fails, the payload is unchanged, or there are 0 actions.
- **Session-only code:** `MARKDOWN_CHECKPOINT_FAILED` (`dispatched: false`).

### Worker and SDK

- Worker operation `pasteMarkdown`, gated the way `pageRectangles` is (`sdk-worker.js:205-223`, `:1418`).
- SDK `DocumentHandle.pasteMarkdown(text)`:
  - throws `UNSUPPORTED_OPERATION` unless declared;
  - checks the UTF-8 byte length against `MARKDOWN_PASTE_LIMIT_BYTES = 65536`, the operative limit (§9.2);
  - over the limit gives `INVALID_ARGUMENT` with no worker request.

## Part E: engine, ABI, builder, X1, Makefile block, model tests

Files you own:
- `src/*`;
- `tests/*.cpp`, plus new model-test files;
- `tests/editor_abi_header_test.cpp`;
- `tools/build_e2_editor_v5_profile.py` (new);
- `tools/check_profile_identity.py` and its tests;
- `tests/test_e2_editor_v4_profile.py`, only where the pin list requires it;
- a new `tests/test_e2_editor_v5_profile.py`;
- `e2/relink-queue-v3.json` rows the pin list names;
- `Makefile`: the new v21 block only.

Order:

1. **M0 fixture first, committed by the main session before step 3.**
   - Write `tests/markdown_paste_corpus/`: both native rounds' corpora, copied, plus the new items in §11 M0.
   - Write `tests/markdown_paste_expected.json`: one expected verdict per item, from the §10/§10.4 rules.
   - Stop and report when it is written. The main session commits it before any scanner code exists.
2. **`src/markdown_paste.hpp`**, a pure header with no LOK:
   - the scan, over the md4c callbacks, with flags copied from `libreoffice-26-8/sw/source/filter/md/swmd.cxx:950-958`;
   - the size, NUL and encoding checks;
   - the post-dispatch judge, reusing `summarizeUndoPayload`.

   Include `<md4c.h>` only when the define is set. The model test compiles it natively together with the core's `md4c.c`, as a native test only. **Never compile `md4c.c` into the engine.**
3. **Model test `tests/markdown_paste_model_test.cpp`** over the fixture. It needs §11 M0's three red mutations.
4. **Engine:**
   - the two actions;
   - the paste handler;
   - the §10.2 collapsed rule, read at dispatch;
   - the bounds;
   - the ABI constant and enums, all under the define;
   - `sdk_api.{h,cpp}` export.
5. **`tools/build_e2_editor_v5_profile.py`** by spec §9.10's mechanism:
   1. patch `v4.ABI_VERSION` and `v4.action_map`;
   2. strip own flags from argv and call `v4.main()`;
   3. add leaves, rewrite the manifest and reprint the digest.

   Plus its tests, including the `--paste-markdown` refusal.
6. **X1 `--declared-changed-leaf PATH OLD NEW`**, with §11 X1-cl's six red cases.
7. **The Makefile v21 block**, modelled on v20's (`Makefile:1525-1603`):
   - v20's defines plus `-DOXSDK_E2_V21_LINK_BATCH`;
   - `-I$(LOBUILD)/workdir/UnpackedTarball/md4c/src` on the v21 rule only;
   - `src/markdown_paste.hpp` as a prerequisite of v21 objects only;
   - exports: v20's plus `_oxsdk_document_paste_markdown`;
   - the worker pin, as a placeholder the main session fills after part S;
   - the v5 builder with `--page-rectangles --paste-markdown`;
   - `ALLOW_FROZEN_RELINK` guarded like v20.

   **Do not run it.** Show `make -n dist/profiles/e2-editor-v21/sdk-manifest.json` output only. `make -n` does not compile.
8. Run the existing engine model tests, the lock-scope check and the unit tests `RUNBOOK-relink-v20.md` §0 item 9 lists. Report the results.

## Part S: worker, SDK, shell, page, unit tests

Files you own:
- `sdk/sdk-worker.js`, `sdk/document-sdk.js`, their `.d.ts` files and `sdk/tests/*`;
- `editor-shell-v2/*` and its tests;
- `web/e2-editor-app.js`, `web/e2-editor.html` and the page tests;
- `e2/expected-gesture-offers.json`.

Do not touch `editor-shell/` or `input/`.

1. **Worker:**
   - ids 22/23 in a successor table;
   - fail init on a non-OK `oxsdk_editor_set_action_gestures` status (§9.7);
   - the `pasteMarkdown` operation with its declaration gate.
2. **SDK:** `pasteMarkdown` with the operative limit (§9.2). Update the `.d.ts` and `declaration-drift` tests.
3. **Client/session:**
   - the ABI 5 action list;
   - postcondition classes, plus a final branch that rejects an unknown action;
   - `BOUNDARY_CAPABLE_MOVES` gains 22/23;
   - `pasteMarkdown` as a mutation, with `_checkpointBeforeBoundaryMove` before dispatch. A checkpoint failure gives `MARKDOWN_CHECKPOINT_FAILED` and no dispatch (§10.1);
   - every pre-dispatch code in `PRE_DISPATCH_CODES`, so it gets `recovery: "none"` (§10.4);
   - the enqueue counter in the v2 `_enqueue` (§10.3).
4. **Page:**
   - Ctrl/Cmd+Home/End bound before `if (accel) return;`, only when `session.offers()`. Shift and `isComposing` excluded. `preventDefault`. Drop a same-key press while a move is unanswered, and drop `event.repeat` (§11 D9);
   - `ACTION_LABELS`;
   - D4's range path;
   - the Markdown dialog, entry A: toolbar button 「貼上為 Markdown…」, a textarea, 「插入」 and 「取消」. Cancel enqueues nothing. Insert with a range selected shows 「請先取消選取」. Show the refusal messages from spec §9.3, §10.4 and §9.14;
   - the hold rewrite exactly as §10.3 items 1–4.
5. **Unit tests**, red first:
   - D5's matrix;
   - D13's closed lists;
   - M8's matrix;
   - M11's cancel arm;
   - the hold sequences of §11 D8 (a)–(e) against a fake engine, with (c)(d)(e) shown red on today's page logic first;
   - every existing page, session and client test, which must still pass. Expect `place-caret-second-pass` "defect 2" to flake (24 ms against `>= 25`); report it, do not fix it.
6. Run:
   - `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`;
   - `python3 tools/check_e1_c_bundle_intact.py`.

   Report the exact counts.
