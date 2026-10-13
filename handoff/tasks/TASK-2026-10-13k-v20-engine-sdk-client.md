# TASK 2026-10-13k — v20, part 1: engine, worker, SDK and shell client for the reduced scope

**Spec:** `specs/SPEC-M3-link-batch.md`. The scope is **§13.3 only**:
- the page number (§4.3 as corrected, §10.8, §12.3);
- C, which is §10.5 **minus every flag clause** (§13.3, ruling 4 condition 35);
- the `caretBefore` data of §4.5(2) as refined by §10.6;
- nothing from items 1 and 2.

Editor ABI **stays 4**. Manifest moves stay `collapsed`-only. The page's delete routing is unchanged. No
deadline is added to `AwaitingDeleteCompletion`. The rulings are `findings/evidence/link-batch/review/
ruling-2.md`, `ruling-3.md` and `ruling-4.md` (ruling 4 is authoritative for scope).

**This task changes source only.**
- **No link:** the owner links. Do not run any make target that links or that names a frozen profile.
- **No `dist/`, no profile.**
- **The Makefile and the v20 profile builder are part 3**, after the engine-code review. Do not touch them
  here.

## 1. Engine (`wasm_sdk_probe/src/probe_engine.cpp` and its headers)

Every behaviour change goes under a NEW compile-time define, for example `OXSDK_E2_V20_LINK_BATCH`. That
way objects compiled for v15 and v19 stay byte-identical when they are rebuilt from this source. This is
the per-object M1-1 discipline of `tools/check_merge_key_undo_scope.py`. Read that tool and follow how the
v19 change was scoped.

1. **C (§10.5 minus flag).** On a build that can merge, `rejectSelectionBarrierAtDeadline`'s
   `nothing-selected` exit becomes a window:
   - After the first `NONE`, stay in `AwaitingUnitSelection` for one `MergeStepDeadlineMs` (use the existing
     constant; add no new number).
   - If K1's `TEXT_SELECTION` arrives inside the window, it takes the ordinary path
     (`handleSelectionBarrierStateCallback` → unit verification).
   - At expiry, if a second `readSelection()` is still `NONE` and the typed selection is still collapsed,
     complete as `editor-action-completed` with `changed: false`, the revision unchanged, completion
     `verified-boundary-noop`, and `boundaryNoop: { waitedMs }`.
   - The other two expiry exits (`unit-late`, `EDITOR_STATE_UNAVAILABLE`) stay as they are today.
   - Note that the window has to be driven by the engine loop's deadline mechanism the same way the existing
     barrier deadlines are. Find how `rejectSelectionBarrierAtDeadline` is scheduled and reuse it.
2. **`caretBefore` (§4.5(2), §10.6).**
   - Every refusal leaving `finishMergeKeyError` carries `caretBefore: { rect, sourceSequence, source }`.
     `source` is `"attribution-P"` when the merge attribution's P is established, and `"cache"` otherwise.
   - Do the same for `finishSelectionBarrierError` refusals, if the value is well defined there; say in the
     README if it is not.
   - This is data only. No behaviour depends on it in this link.
3. **`DOCUMENT_SIZE_CHANGED` counter (§12.3).**
   - The engine handles `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`. It increments `documentSizeChangedCount` in
     editor state on **every** callback, not only when the payload changes.
   - The arrival **pushes editor-state by itself**: today the callback switch pushes only seven types.
   - Serialise the counter in the editor state.
4. **`page-rectangles` (§10.8, S-11).**
   - A document-level export, **never an action**: `kMaxExternalAction` and `kMaxInternalEditorAction` do
     not move.
   - Its reply carries the raw `getPartPageRectangles()` string (no parsing in the engine), the document
     width and height, and `getParts()`.
   - It goes through the engine queue like other document queries. Add the C export in `src/sdk_api.cpp`
     (or wherever document-level exports live) and to the export list source the profile build reads.
     Name the file in the README; part 3 will regenerate the list.

## 2. Worker (`wasm_sdk_probe/sdk/sdk-worker.js`)

- Pass `page-rectangles` through, and add `documentSizeChangedCount` to the editor-state fields the worker
  whitelists.
- v19's worker is a copy of the v15 archive. **v20's worker is built from this source.** In the README, list
  every behavioural difference between the archived v15 worker (`00882139…`) and this source, not only
  yours, so the review can see what else v20 will carry.

## 3. SDK (`wasm_sdk_probe/sdk/document-sdk.js` and `.d.ts`)

- `handle.pageRectangles()` returns `{ rectangles: [{x, y, width, height}], parts, widthTwips, heightTwips }`
  in twips.
- It throws a typed error on any malformed string, never returns an empty list for a bad string, and checks
  rectangles = parts.
- It is gated: absent unless the manifest declares the capability. Follow how redo is declared and gated
  (`narrow-editor-v2-client.js:233–238`, `web/e2-editor-app.js:950–953`). Choose the manifest field name and
  write it in the README.
- This file is in the shell bundle, so a new shell generation is part 3's job.

## 4. Shell client (`wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js` and its tests)

- The completion whitelist accepts `verified-boundary-noop` only with `changed === false` and an unchanged
  revision.
- Add a red-case test in M1-3's shape: the same completion with `changed: true`, or with an advanced
  revision, must be rejected.
- An `offers`-style gate for `page-rectangles`.

## 5. Tests and checks (run them; record the outputs)

- Node unit tests for the SDK parse (good string, malformed strings, rectangles ≠ parts) and for the client
  whitelist and its red case: `node --test editor-shell-v2/tests/*.test.mjs` plus any new test files. All
  must pass, and every new test must be shown red once.
- The extend model test still ends `ok` (`g++ … tests/extend_completion_model_test.cpp`). The merge model
  test still ends `ok`.
- `tools/check_engine_lock_scopes.py`. If the new paths add lock scopes, record the new counts and why.
- **Compile check without linking:** try an `emcc -fsyntax-only` (or `-c` into a scratch directory outside
  `build/`) of `probe_engine.cpp` with v20's defines and v19's include flags. Take the flags from the
  Makefile's v19 rule; do not edit the Makefile. If this is not feasible without a Makefile target, say so.
- Any static test that pins the engine source or the client (grep `tests/` and `tools/` for the files you
  changed): list what goes red and why. **Do not edit pins or bindings.** Part 3 handles the freeze.

## 6. Deliverables

- Commits touching only `wasm_sdk_probe/src/`, `sdk/`, `editor-shell-v2/` and their tests.
- `findings/evidence/link-batch/v20-part1/README.md` (English), beginning with `## SUMMARY` (≤ 30 lines). It
  holds:
  - the define name;
  - the per-file change list;
  - the worker diff list against the v15 archive;
  - test outputs;
  - the compile-check result;
  - the pins that will go red;
  - anything in the spec you found unimplementable. If you find such a thing, stop and report it; do not
    improvise.

Commit messages are in English and end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`, with
no `Claude-Session:` line. Retry if `.git/index.lock` exists.
