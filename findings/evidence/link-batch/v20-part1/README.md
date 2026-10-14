# v20, part 1 — engine, worker, SDK and shell client for the reduced scope

## SUMMARY

- Task: `handoff/tasks/TASK-2026-10-13k-v20-engine-sdk-client.md` (commit `ee7923f9`). Scope: spec §13.3 only (page number §4.3/§10.8/§12.3; C = §10.5 minus every flag clause; `caretBefore` data §4.5(2)/§10.6). Editor ABI stays 4; `kMaxExternalAction`/`kMaxInternalEditorAction` untouched; manifest moves untouched; no deadline on `AwaitingDeleteCompletion`; `editor_api.cpp` untouched. Nothing linked, no make target run, no `dist/`, profile, pin or binding edited.
- Define: **`OXSDK_E2_V20_LINK_BATCH`**. Every engine, header and C-export change is under it. `tools/check_merge_key_undo_scope.py --base 5d77dc84`: exit 0, `failures []`, 100 objects, only `E2_V15`/`E2_V19` `probe_engine.o` differ from base (option B, as at HEAD) — v15 and v19 objects rebuilt from this source preprocess byte-identically.
- Engine (`src/probe_engine.cpp`, `.hpp`): C's window in `rejectSelectionBarrierAtDeadline` (first NONE re-arms `boundaryDeadline` by `MergeStepDeadlineMs`, stays `AwaitingUnitSelection`; expiry with NONE + collapsed → `verified-boundary-noop`, `changed:false`, revision unchanged, `boundaryNoop:{waitedMs}`; `unit-late`/`EDITOR_STATE_UNAVAILABLE` exits unchanged); `caretBefore:{rect,sourceSequence,source}` on `finishMergeKeyError` and `finishSelectionBarrierError` (`attribution-P` when P is established, else `cache`); `documentSizeChangedCount` incremented and pushed on every `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`, serialised top-level in editor state; `page-rectangles` as `CommandType::PageRectangles` (raw string + size + `getParts()`), through the queue like `GetSelection`.
- C export: `oxsdk_document_page_rectangles` in `src/sdk_api.cpp`/`.h` (guarded). Export-list source = the Makefile's per-profile `exports.txt` recipe (`$(E2_V19_BUILD)/exports.txt`, Makefile 1469–1481); not edited here — part 3 adds `_oxsdk_document_page_rectangles` to v20's.
- Worker (`sdk/sdk-worker.js`): tree copy was byte-identical to the v15 archive (`00882139…`), so the diff against the archive is exactly this part's 9 hunks (listed in §3); new sha256 `478d0da1…`. Adds `pageRectangles` dispatch + `page-rectangles` reply, a contract-field gate, `documentSizeChangedCount` in all three editor-state projections, `boundaryNoop` on completions and `caretBefore` on errors (named fields only).
- SDK (`sdk/document-sdk.js`, `.d.ts`): `handle.pageRectangles()` → `{rectangles:[{x,y,width,height}], parts, widthTwips, heightTwips, revision}` in twips; `PageRectanglesError` (`PAGE_RECTANGLES_INVALID`) on any malformed string or rectangles ≠ parts, never `[]`; gated on manifest field **`editorContract.pageRectangles === "document-sdk-page-rectangles"`** (UNSUPPORTED_OPERATION before any request otherwise).
- Client (`editor-shell-v2/narrow-editor-v2-client.js`, `.d.ts`): the two caret-relative deletes accept `verified-boundary-noop` only with `changed === false` and `revision === expectedRevision`; `offersPageRectangles()` reads the contract field like `offersRedo()`.
- Tests: 81 new cases in `sdk/tests/page-rectangles.test.mjs` (38), `editor-shell-v2/tests/boundary-noop.test.mjs` (30), `sdk/tests/sdk-worker-v20.test.mjs` (11), `offers.test.mjs` (+2), plus 3 reply mutations and one `DECLARED_DIVERGENCE` entry in the v1-vs-v2 matrix. Shown red first against the unmodified sources (SDK file fails at import; 11 client/matrix failures; worker 0/11), then `node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs`: **344 pass, 0 fail**.
- Compile check: v19's exact compile command (`make -n -B EXTRA_DEFINES= build/e2/editor-v19/probe_engine.o`) run as `-fsyntax-only` on `probe_engine.cpp` and `sdk_api.cpp`, with and without `-DOXSDK_E2_V20_LINK_BATCH`: all four exit 0. `-Wall -Wextra`: 36 → 37 warnings, the one addition being the same `missing field 'text' initializer` every `Command command{CommandType::X}` already produces. Model tests: extend `ok`, merge `ok`. Lock scopes: `gState.mutex 12 → 12`, `gMergeMutex 11 → 13`, tainted 97 → 99 (both new scopes and both new tainted functions named in §7).
- Pins that go red: `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree` (dist copies of `narrow-editor-v2-client.js` and `document-sdk.js` differ from source; `e2/editor-shell-v2-bundle-v66.json` out of date for those two) — part 3's freeze. Everything else checked stays green (§8).
- Spec: nothing found unimplementable or contradictory. Eight judgement calls where the spec leaves a choice are written out in §9; two of them widen the worker beyond the task's list (`boundaryNoop`, `caretBefore` forwarding) because C1's `waitedMs` and §10.6's data cannot reach a page the worker does not forward them to.
- Not executed anywhere: the engine paths are compile-checked only (no link); the window's first execution is the v20 shakedown.
- Commits: see §10.

## 1. The define and the per-object discipline

`OXSDK_E2_V20_LINK_BATCH`, named as the task suggested. No existing Makefile rule defines it, so every rule of `tools/check_merge_key_undo_scope.py`'s population preprocesses this source exactly as before:

```
$ python3 tools/check_merge_key_undo_scope.py --base 5d77dc84 --json …/merge-key-undo-scope.json
{"carriers": ["E2_V15", "E2_V19"], "rules": 25, "objects": 100, "different": 2, "unbuildable": ["FINDING_012_DIAGNOSTIC build/finding-012/diagnostic/probe_engine.o"], "guards": [{"rule": "E2_V15", "variant": "with OXSDK_MAINLOOP_ENGINE", "exit": 1}, {"rule": "E2_V15", "variant": "without OXSDK_FINDING_016_SELECTION_BARRIER", "exit": 1}, {"rule": "E2_V19", "variant": "with OXSDK_MAINLOOP_ENGINE", "exit": 1}, {"rule": "E2_V19", "variant": "without OXSDK_FINDING_016_SELECTION_BARRIER", "exit": 1}]}
exit 0
failures []
different: [('E2_V15', 'build/e2/editor-v15/probe_engine.o'), ('E2_V19', 'build/e2/editor-v19/probe_engine.o')]
```

The two differing objects are the carriers' engine objects, which must differ from the pre-B base; v19's `sdk_api.o` is identical to base, which is the proof that the new export and its header declaration are guarded.

## 2. Per-file changes

| file | change |
|---|---|
| `wasm_sdk_probe/src/probe_engine.cpp` | `EditorState::documentSizeChangedCount`; `CommandType::PageRectangles`; `SelectionBarrierTransaction::{caretBefore, caretBeforeSequence, boundaryNoopWindow, startedAt}`; `appendEditorState` emits `documentSizeChangedCount` top-level; `onLokCallback` gains `case LOK_CALLBACK_DOCUMENT_SIZE_CHANGED` (count, push, source `document-size-changed`); `appendCaretBefore()`; `finishSelectionBarrierError` emits `emitSdkError`'s exact shape plus `caretBefore`; `finishMergeKeyError` appends `caretBefore`; `finishSelectionBarrierBoundaryNoop()` (merge builds only); `rejectSelectionBarrierAtDeadline`'s NONE branch becomes the window; `startSelectionBarrierDelete` captures the cache and `startedAt` (at K1's post); `handlePageRectangles()`; dispatch case; `pageRectangles()` submit |
| `wasm_sdk_probe/src/probe_engine.hpp` | `pageRectangles(requestId, documentHandle)` declaration |
| `wasm_sdk_probe/src/sdk_api.cpp` | `oxsdk_document_page_rectangles` (EMSCRIPTEN_KEEPALIVE, validates arguments, submits) |
| `wasm_sdk_probe/src/sdk_api.h` | its declaration |
| `wasm_sdk_probe/sdk/sdk-worker.js` | §3 |
| `wasm_sdk_probe/sdk/document-sdk.js` | `PageRectanglesError`; `parsePageRectangles(text, parts)` (exported); `DocumentHandle.pageRectangles()` |
| `wasm_sdk_probe/sdk/document-sdk.d.ts` | `SdkManifest.editorContract?`; `PageRectangle`, `PageRectanglesResult`, `PageRectanglesError`, `parsePageRectangles`; `redo()` and `pageRectangles()` on `DocumentHandle` (`redo` was already in the runtime and undeclared) |
| `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.js` | delete postcondition accepts `verified-boundary-noop` (changed false, revision unchanged) beside the two verified-delete completions, same rejection message; `offersPageRectangles()` |
| `wasm_sdk_probe/editor-shell-v2/narrow-editor-v2-client.d.ts` | `offersPageRectangles(): boolean` |
| `wasm_sdk_probe/sdk/tests/page-rectangles.test.mjs` | new, 38 cases |
| `wasm_sdk_probe/sdk/tests/sdk-worker-v20.test.mjs` | new, 11 cases (the M1-4 vm harness) |
| `wasm_sdk_probe/editor-shell-v2/tests/boundary-noop.test.mjs` | new, 30 cases |
| `wasm_sdk_probe/editor-shell-v2/tests/narrow-editor-v2-client.test.mjs` | 3 reply mutations; `DECLARED_DIVERGENCE["completion verified-boundary-noop, nothing changed"]` (deletes: v1 rejects, v2 ok); the two red shapes are refused by both clients |
| `wasm_sdk_probe/editor-shell-v2/tests/offers.test.mjs` | 2 cases for `offersPageRectangles` |

Untouched on purpose: `src/editor_api.cpp`/`.h` (ABI 4), `src/merge_key_undo.hpp`, `src/extend_completion.hpp`, `Makefile`, `tools/build_e2_editor_v4_profile.py`, `dist/`, `e2/*.json`, `web/`.

### 2.1 How C's window rides the existing deadline

`rejectSelectionBarrierAtDeadline` is only ever entered from the step the engine loop synthesises when `gSelectionBarrier.stage == AwaitingUnitSelection` and `now >= gSelectionBarrier.boundaryDeadline` (the three wait sites: the engine-thread loop, `mainLoopDrainCommands`, `mainLoopPollCallbackImpl`). On the first NONE the window sets `boundaryNoopWindow` and moves `boundaryDeadline` forward by `MergeStepDeadlineMs` (2000 ms, the existing constant; no new number), leaving the stage as it is. The loop therefore waits on the new deadline and synthesises the same `values[0] == 1` step at expiry, which runs the second read. A `TEXT_SELECTION` inside the window reaches `handleSelectionBarrierStateCallback` exactly as today (stage → `UnitVerificationQueued`, the ordinary unit verification, the attribution's P and anchor fence already set before K1). Read, not executed: one consequence is that the `textSafe && !geometrySafe` re-entry into `AwaitingUnitSelection` (`verifyAndDispatchSelectionBarrierDelete`) now waits for the window's deadline rather than the already-passed 250 ms one before taking its unchanged `EDITOR_STATE_UNAVAILABLE`/`unit-late` exit — later, never different.

## 3. Worker: every difference from the v15 archive

`sdk/sdk-worker.js` at HEAD hashes `00882139cd0b2e5898a96b8c7b21a4f8ee1d231ae13da39929e12088e9bb0241`, the archive's hash (`build/archive/e2-editor-v15-ad3f68bb-worker-00882139/sdk-worker.js`); `diff -u` against the archive after this part is 90 changed lines in 9 hunks, all this part's. New hash `478d0da1dbfcf93615a00025c3c2f9b72c3cfa486d04746f03dea5fcf757b099`. So what v20 carries over v15/v19 in the worker is exactly:

| hunk (archive line) | behaviour |
|---|---|
| `@@ -201 +201,50` | new definitions only: `DOCUMENT_EXPORT_OPERATIONS` (`pageRectangles` → contract field `pageRectangles`, declaration `"document-sdk-page-rectangles"`), `documentExportDeclared()`, `productBoundaryNoop()`, `productCaretBefore()` |
| `@@ -323 +367,12` | `productEditorState` names `documentSizeChangedCount` (integer, else `null`) — visible on every product projection, including on a v15/v19 engine, where it is `null` |
| `@@ -837 +887,19` | engine event `page-rectangles` completes its request with `{rectangles, parts, documentWidthTwips, documentHeightTwips, revision}` |
| `@@ -891 +954,9` | `editor-action-completed` forwards `boundaryNoop` as `{waitedMs}` when present |
| `@@ -940 +1006,8` | `editor-state-result` (v2 branch) names `documentSizeChangedCount` (raw; `undefined` on older engines) |
| `@@ -1010 +1078,9` | `editor-state` announcement names `documentSizeChangedCount` (raw) |
| `@@ -1099 +1170,8` | `error` forwards `caretBefore` as `{rect | null, sourceSequence | null, source}` when present |
| `@@ -1243 +1316,17` | request admission: an operation in `DOCUMENT_EXPORT_OPERATIONS` whose declaration is absent from `activeManifest.editorContract` is refused `UNSUPPORTED_OPERATION` before any ccall |
| `@@ -1328 +1412,16` | dispatch `pageRectangles` → `oxsdk_document_page_rectangles(requestId, documentHandle)` |

No existing dispatch, gate, projection or anchor changed. `tests/test_e2_profile.py`'s four patch anchors (`WORKER_GATE_BEFORE`, `WORKER_MESSAGE_BEFORE`, `WORKER_BARRIER_BEFORE`, `WORKER_LOK_TRACE_BEFORE`) still match exactly once; `tests/test_e2_editor_v4_profile.py`'s `!Array.isArray(spec?.gestures)` is untouched.

## 4. SDK: the manifest field and the parser

- Manifest field (the task asked for the name): **`editorContract.pageRectangles = "document-sdk-page-rectangles"`**, the shape of `redo: "document-sdk-redo"`. Part 3's builder sets it for v20; nothing sets it today, so on every existing profile `handle.pageRectangles()` rejects `UNSUPPORTED_OPERATION` before any request and `offersPageRectangles()` is false.
- `parsePageRectangles(text, parts)`: splits on `;`, each piece on `,`, exactly four fields each matching `^(0|[1-9][0-9]*)$`, width and height ≥ 1, count == `parts` (a positive integer). Anything else throws `PageRectanglesError` with `details {text, parts, …}`. Core assembles the string with `"; "` between pages and strips the last separator (`sw/source/core/crsr/crsrsh.cxx:1655`, `SwCursorShell::getPageRectangles`), so a trailing or leading separator is malformed, as is an empty string (a document has ≥ 1 page and `getParts()` ≥ 1).
- The result carries `revision` beside the four named fields, like every other handle result (`RevisionResult`); the handle's `widthTwips`/`heightTwips`/`revision` follow the reply as they follow a paint reply.

## 5. Client

`_validateInherited`, delete branch: `boundaryNoop = completion === "verified-boundary-noop" && changed === false && revision === expectedRevision`; `verifiedDelete` = the previous rule; either passes, otherwise the previous rejection (same message, so the v1-vs-v2 matrix's `deepEqual` holds on the two red shapes and the divergence is confined to the one accepted shape). `offersPageRectangles()` is the `offersRedo()` shape. `offers("page-rectangles")` stays false everywhere: it is not an action.

## 6. Tests

Red first, against the unmodified `document-sdk.js`, `narrow-editor-v2-client.js` and `sdk-worker.js` (outputs kept in the session scratchpad; the lines that matter):

```
$ node --test sdk/tests/page-rectangles.test.mjs editor-shell-v2/tests/boundary-noop.test.mjs editor-shell-v2/tests/offers.test.mjs editor-shell-v2/tests/narrow-editor-v2-client.test.mjs
SyntaxError: The requested module '../document-sdk.js' does not provide an export named 'PageRectanglesError'
ℹ tests 52 / ℹ pass 41 / ℹ fail 11      (exit 1)
  — page-rectangles.test.mjs failed at import; boundary-noop: 2 accept cases + 5 offersPageRectangles cases
    (TypeError: …offersPageRectangles is not a function); offers.test.mjs: 2; the matrix: the declared
    divergence was never exercised
$ node --test sdk/tests/sdk-worker-v20.test.mjs
ℹ tests 11 / ℹ pass 0 / ℹ fail 11       (exit 1)
```

Green after the change:

```
$ node --test editor-shell-v2/tests/*.test.mjs sdk/tests/*.test.mjs
ℹ tests 344 / ℹ suites 0 / ℹ pass 344 / ℹ fail 0 / ℹ cancelled 0 / ℹ skipped 0 / ℹ todo 0   (exit 0)
```

What the new cases pin: the good string and the 60-page native shape parse; 22 malformed shapes each throw the typed error (never `[]`); rectangles ≠ parts in both directions; the gate for five undeclared manifest shapes issues no request; the engine's `boundaryNoop`/`caretBefore`/`documentSizeChangedCount` cross the worker with named fields only and are `null`/absent on a v19-shaped engine event; the worker refuses `pageRectangles` on a v19-shaped contract without touching `moduleInstance.ccall` and reaches `oxsdk_document_page_rectangles` with `[requestId, documentHandle]` on a declared one; the client accepts the no-op completion for the two deletes and rejects seven one-claim-wrong variants of it and its use on eight other actions.

Model tests (built into the scratchpad, not `build/`):

```
$ g++ -std=c++17 -O2 -Isrc -o …/extend_completion_model_test tests/extend_completion_model_test.cpp && …/extend_completion_model_test
ok      (exit 0)
$ g++ -std=c++17 -O2 -Isrc -o …/merge_key_undo_model_test tests/merge_key_undo_model_test.cpp && …/merge_key_undo_model_test
coincident rects (limit, reported)   runs=2703360 merged=57344 refusedK1=2101248 refusedK2=444416 none=100352 counter=0 live=0 escNoSel=0
ok      (exit 0)
```

Neither model covers the new engine paths (the window, `caretBefore`, the counter, the query); they were run to show the headers this part did not touch still pass.

## 7. Compile check and lock scopes

Compile command taken from the Makefile's v19 rule by dry run, never by editing it: `make -s -n -B EXTRA_DEFINES= build/e2/editor-v19/probe_engine.o` → `../wasm-lite/tools/emsdk/upstream/emscripten/em++ -DLOK_USE_UNSTABLE_API -I… -Oz -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm -DOXSDK_EDITOR_DISCOVERY -DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER -DOXSDK_MERGE_KEY_UNDO -c src/probe_engine.cpp -o …`. Run with `-fsyntax-only` in place of `-c … -o …` (no object written, nothing linked):

| run | exit |
|---|---|
| `probe_engine.cpp`, v19 flags + `-DOXSDK_E2_V20_LINK_BATCH` | 0 (1.2 s) |
| `probe_engine.cpp`, v19 flags (define absent) | 0 |
| `sdk_api.cpp`, v19 flags + define | 0 |
| `sdk_api.cpp`, v19 flags | 0 |
| `probe_engine.cpp`, v19 flags + define, `-Wall -Wextra` | 0; 37 warnings vs 36 without the define, the one addition `warning: missing field 'text' initializer [-Wmissing-field-initializers]` for `Command command{CommandType::PageRectangles}` — the same warning the 35 existing `Command command{CommandType::…}` aggregate-inits produce; left in the house style |

`tools/check_engine_lock_scopes.py` (spec 13.2):

```
HEAD:  probe_engine.cpp: lock scopes checked (gState.mutex 12, gMergeMutex 11), 97 tainted functions
now:   probe_engine.cpp: lock scopes checked (gState.mutex 12, gMergeMutex 13), 99 tainted functions   (exit 0)
```

The two new `gMergeMutex` scopes: `appendCaretBefore` (reads `gMergeAttribution.hasP()/p()` into locals; emits outside the lock) and `finishSelectionBarrierBoundaryNoop` (resets `gMergeTicket`, like `finishMergeKeyError`). The two new tainted functions: `handlePageRectangles` and `finishSelectionBarrierBoundaryNoop` (both `emitJson`); neither is called under a lock.

## 8. Pins: red and green

Red (expected; part 3 freezes the next shell generation):

- `tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree` — `bundle.problems()` = `dist copy differs from source: editor-shell-v2/narrow-editor-v2-client.js`, `dist copy differs from source: sdk/document-sdk.js`, `manifest is out of date: changed=['editor-shell-v2/narrow-editor-v2-client.js', 'sdk/document-sdk.js']`; `e2/editor-shell-v2-bundle-v66.json` `bundleSha256 70c34178…` vs current `a151e686…`. The fix is `make e2-c-assets` + a new generation, both outside this part (`dist/`, pins).

Green, run after the change: `tests/test_e2_profile.py` (56, OK), `tests/test_e2_editor_v4_profile.py` (11, OK), `tests/test_finding_016_selection_barrier.py` (5, OK), `tests/test_product_path_mutations.py` (10, OK); `tools/check_relink_queue.py` output identical to HEAD (66 items, 48 present, 18 open, 0 drifted, blocking none); `tools/check_product_build_reaches.py` `"ok": true`; `tools/check_merge_key_undo_scope.py` as in §1; `tools/check_engine_lock_scopes.py` as in §7. Not rerun: `tests/test_profile_identity.py` and `tools/run_merge_wasm_shakedown.py`'s `workerSha256` pin — both read the frozen v19 profile's worker (`dist/profiles/e2-editor-v19/sdk-worker.js`, the archive copy), which this part does not touch; `tests/test_merge_key_undo_scope.py` (offline judgement on rows; the live checker was run instead).

## 9. Spec reading: nothing unimplementable; eight judgement calls, written down

1. **`caretBefore.sourceSequence` under `source: "attribution-P"`** is the cache's `sourceSequence` at barrier start. §10.6 defines the rect's source (P when established, else the cache) but the attribution keeps rectangles only (`merge_key_undo.hpp`, `Attribution::p()`), and recording a sequence there is a header the merge model tests pin. Data only in this link; E2's oracle is K1's anchor rectangle, not this field.
2. **`caretBefore.rect` is `null`** when neither P nor an observed cached caret exists (a barrier started before any `INVALIDATE_VISIBLE_CURSOR`), rather than a zero rectangle; the worker keeps `null` and turns any rect that is not four integers into `null`.
3. **`boundaryNoop.waitedMs` counts from K1's post** (`startedAt` set immediately before `postKeyEvent`), so it is the number L-C-late-K1's "~2,250 ms" and the owner's "about 2.25 s" refer to, not the request's queue time.
4. **`handlePageRectangles` reports the document size but does not refresh `gState.documentWidthTwips/HeightTwips`**: those are what the paint reply's `documentSizeChanged` compares against, and §10.8 keeps that trigger "as today" beside the new counter. The cost is at most one redundant re-read after a size change (P3 already excludes size-triggered re-reads).
5. **The SDK result carries `revision`** beside `rectangles, parts, widthTwips, heightTwips`, like every other handle result.
6. **The worker forwards `boundaryNoop` and `caretBefore`**, which the task's worker list did not name. Without the first, C1's "record `waitedMs` for every completion" has nothing to record on the page side; without the second, §4.5(2)'s data stops in the worker. Both named-field projections, on the M1-4 pattern.
7. **"Absent unless declared"** for `handle.pageRectangles()` is implemented as `UNSUPPORTED_OPERATION` thrown before any request (the method exists on the class, as `redo()` does); the worker gate refuses the same way one layer down so no path reaches a missing symbol.
8. **The export-list source** is the Makefile's `exports.txt` recipe (hard-coded `printf` names per profile rule), not a separate file, so it is named here rather than edited (Makefile forbidden in this part).

For part 2 (page) and part 3 (plumbing), found while reading and not done here: `editor-shell-v2/narrow-editor-v2-session.js:293–311` is an allowlist too — `documentSizeChangedCount` must be named there for the page's `editorState` to carry it; the page must neither toast nor reopen on `verified-boundary-noop` (§10.5); the builder must set `editorContract.pageRectangles`; part 3's `exports.txt` recipe must append `_oxsdk_document_page_rectangles`; §10.7's arms whose expectations say `nothing-selected` become C's new expectation at the first v20 shakedown.

## 10. Commits

| commit | contents |
|---|---|
| `82af92ca` | engine + C export (`src/probe_engine.cpp`, `.hpp`, `src/sdk_api.cpp`, `.h`) |
| `150c1770` | worker + `sdk/tests/sdk-worker-v20.test.mjs` |
| `1b8b7c34` | SDK + `.d.ts` + `sdk/tests/page-rectangles.test.mjs` |
| `44eb15f2` | shell client + `.d.ts` + the three client test files |
| (this commit) | this README |

## 11. Corrections (appended 2026-10-14; ruling 6 conditions 43 and 50)

- **§2.1, "later, never different", is not exact.** Review 6 §1.4 found the gap. If the window is already open, the `textSafe && !geometrySafe` re-entry waits until the window's deadline. A single-rectangle `TEXT_SELECTION` that arrives in that time completes the delete normally, while v19 would have answered at once with `EDITOR_STATE_UNAVAILABLE`, or earlier with `nothing-selected`. So the difference points toward the ordinary path and does no harm. The sentence should read: "later, and in one case completed instead of refused". Nothing in the engine changes.
- **§1 and the SUMMARY, "v15 and v19 objects rebuilt from this source are unchanged", was not established by the run cited.** That run used `--base 5d77dc84`, which predates the merge work. It shows only that the two existing carriers differ from that older base. What establishes "unchanged by part 1" is a run with `--base 82af92ca^`, ruling 6 condition 50.4. Its result is recorded under `findings/evidence/link-batch/v20-part3/` when it exists. The v20 Makefile block's comment no longer repeats the claim (`d7d62039`).
- **Correction 2 (ruling 6 amendment 2, condition 58).** The claim in §1, "v15 and v19 objects rebuilt from this source are unchanged", was **false from `82af92ca` until `543a5566`**. `finishMergeKeyError` contained one change outside the define: the literal `…0}}"` was split into `…0}"` plus an unguarded `json << "}";`. The JSON bytes it emitted were the same, but v15's and v19's preprocessed `probe_engine` was not. M1-1 at `--base 82af92ca^` found it (`v20-part3/m1-1/green-2-*`). `543a5566` restores the exact old text under `#else`, and the run at that base is now exit 0 (`v20-part3/m1-1/after-56/`). The v20 rule's preprocessed `probe_engine` is byte-identical across that commit (`8926e4cb…`). **v20's engine source is therefore final at `543a5566`, not `82af92ca`**, and is the same as `82af92ca` for v20 in preprocessed form.
