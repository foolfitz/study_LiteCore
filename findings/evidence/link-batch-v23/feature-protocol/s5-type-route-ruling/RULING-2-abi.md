# Editor ABI for the typed-insert export: fable ruling 2 (2026-10-28)

Requested by the owner, who chose "ask fable to rule" (option C) when offered A (keep editor ABI 6 with a contract declaration leaf), B (bump to 7 as ruling 1 wrote) or C. Forcing fact: ruling 1 (`RULING.md`) says "ABI 6→7", but the editor ABI versions the action allowlist and ten product gates hard-code `abiVersion === 6`. The brief sent is `BRIEF-2-abi.md`. Fable read the named files read-only; it ran no build, browser or native process. The owner decided in the same exchange that the v24 batch carries only this typing route.

## The ruling, verbatim

> ## SUMMARY
>
> **Ruling: A — keep editor ABI 6 and declare the export with a contract leaf, exactly as page-rectangles and paste-markdown were.** My earlier "ABI 6→7" was wrong and is withdrawn. The editor ABI versions the ACTION allowlist (`src/editor_api.h:12-65`: 3 = field semantics of actions, 4/5 = appended action ids, 6 = extend on six existing actions). `oxsdk_document_insert_typed_text` is a document-level export: on v24 no action id, gesture, limit or field meaning changes, so ABI 7 would assert a change that did not happen. The precedent is this case verbatim: `src/sdk_api.cpp:327-335` ("never an editor action. No wire id, no gesture; the editor ABI stays 4 ... gates the call on the manifest's declaration"), paste-markdown at `:345-363`, worker `DOCUMENT_EXPORT_OPERATIONS` `:228-257`, spec `SPEC-M3-link-batch.md:204`; v21's 4→5 was for its two action ids (`v21.md:20,81`), the Markdown export rode a leaf (`:390`).
>
> B also costs what it looks like: ten `=== 6` gates (page 2978/3016/3203/3327/3333/3341, client 241/428, session 1036, worker 156) would become "6 or 7" — the identity turned into a range inside the product code, the thing the header rejects — and every later bump widens all ten again.
>
> What ABI 7 would genuinely have bought: a stale v23 wasm beside a v24 manifest is refused AT INIT by the exact match. Under A nothing else catches that at runtime: the page pin (`web/e2-editor-app.js:3851`) compares the MANIFEST's `wasmSha256` claim against the page, not the loaded bytes, and the worker never reads `wasmSha256`. So A carries one condition: the v24 worker checks at init that the symbol of every export the manifest declares is present in the binary, and refuses init with a named code (e.g. `DECLARED_EXPORT_MISSING`) when the manifest declares what the binary lacks. That is the existing declaration rule ("refuse before reaching for the symbol") moved from first use to init — not a new concept, and it is the gate that must be shown red before it is relied on (§3 c).
>
> Correction to the brief: under A the worker gate IS edited. `featureExtendPermitted` (`sdk/v23-feature-worker.js:155-156`) requires `profile === "e2-editor-v23"` AND ABI 6; on `e2-editor-v24` extend switches off under A exactly as under a missed gate under B unless the successor's worker names its own profile. Same silent-failure class; red case §3 e.
>
> ## 1. Facts verified (reading only; no build, browser, native run, no repo-wide search)
>
> 1 yes (`editor_api.h:12-65`; worker `:1270-1278` exact equality). 2 yes (`sdk_api.cpp:327-335, 345-363`; worker `:228-257`; spec `:204`; v21 `:20, 81, 390`). 3 yes, all ten lines read; plus the profile term at worker `:155` noted above. 4 yes (`v23_feature_selection_cases.py:490`, `judge_v23_product_four_arms.py:198`, `check_v23_feature_contract.py:28`, `build_e2_v23_feature_profile.py:44` all pin 6 and the v23 PROFILE, so v24 cannot pass them: new wrappers either way). 5 yes, and more: bundle v76 binds `sdk/document-sdk.js` (line 54) AND `sdk/v23-feature-worker.js` (line 84); the v23 Makefile copies that source into v23's profile (`Makefile:2083`), so the successor needs a NEW worker source file, not an in-place edit of v23's. 6 partly: X1 has `--declared-new-leaf`, `--declared-export`, `--declared-worker`, `--declared-changed-leaf` (`check_profile_identity.py:30-60`); but "the page pins the WASM sha256" is a manifest-claim check, not a binary check (above).
>
> ## 2. Consequences for the earlier ruling
>
> - Withdrawn: "ABI 6→7". Kept and now consistent: new appended export, fresh successor identity, "not an editor action: do not touch `kMaxInternalEditorAction`/gesture tables". T1–T5, M0–M2, §4 revalidation list and the counting rule: unchanged.
> - One clarification of the SDK mapping: typed origin on a manifest WITHOUT the leaf → `UNSUPPORTED_OPERATION` with `dispatched:false` (pasteMarkdown's shape, `document-sdk.js:661`), never a fallback to the paste export — that would be the silent paste T2 forbids.
> - Red controls: (vi)–(viii) = §3 c, d, e added to the list before any counted S5 run.
>
> ## 3. Identity statement under A, and the red cases
>
> X1 on candidate `e2-editor-v24` vs reference `e2-editor-v23` prints VERDICT PASS with the differences EXACTLY: `profile`/`sdkVersion` name swap; wasm hash (differs); loader hash (printed); `--declared-worker <sha>` (licenses `.editorContract.workerSha256`); `--declared-new-leaf .editorContract.typedInsert="document-sdk-insert-typed-text"`; `--declared-export _oxsdk_document_insert_typed_text`. NO `--declared-changed-leaf`: `.editorContract.abiVersion` stays 6; every action's `id`/`gestures`/`limits`, `pageRectangles`, `pasteMarkdown` and all other leaves equal. Runtime: `oxsdk_editor_abi_version()` = 6 = manifest (existing check) and the init presence check for `typedInsert`.
>
> Red cases, each run and recorded before the link is bound:
> - (a) v24 manifest edited to `abiVersion: 7` → X1 manifest clause red (proves "stays 6" is checked, not assumed).
> - (b) leaf declared but absent from the manifest; export declared but `exports.txt` unchanged → X1's declared clauses red (its documented reds, re-run on these inputs).
> - (c) v24 manifest + the archived v23 `probe.wasm` → worker init refused with the named code, not a later `WORKER_EXCEPTION` at the first typed character. This is the gate that replaces ABI 7's init refusal. Default if never run: the stale-wasm hazard is OPEN on v24 and the link is not bound.
> - (d) v24 manifest with `typedInsert` removed → typed `x` answers `UNSUPPORTED_OPERATION`; no reply with `method:"paste"` exists for the cell.
> - (e) v23 manifest fed to the v24 worker's `featureExtendPermitted` → false; v24's → true (the profile term is live, so a missed rename cannot pass silently).

## Main-session verification (2026-10-28)

Checked by reading before acting on the ruling:

- The page pin compares a manifest claim: `web/e2-editor-app.js` reads `session.engine.manifest?.editorContract?.wasmSha256` and tests `startsWith(PINNED_WASM_SHA256)` after open; `PINNED_WASM_SHA256` is a 16-hex prefix (`:50`). `sdk/v23-feature-worker.js` has no occurrence of `wasmSha256`. So the stale-wasm hazard under A is as stated, and the init presence check is the gate that closes it.
- `tools/check_profile_identity.py` documents `--declared-worker`, `--declared-new-leaf`, `--declared-export` and `--declared-changed-leaf` in its header, with "a declared delta that did not move fails its clause, like an undeclared one".
- `build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/`: `sha256sum -c SHA256SUMS` 5/5 OK; the four profile files `cmp` equal to `dist/profiles/e2-editor-v23/`, `exports.txt` equal to `build/e2/editor-v23/exports.txt` (36 lines). `sdk/v23-feature-worker.js` hashes to the archived worker `3fd3e1e6…`.

The successor spec (`specs/SPEC-M3-link-batch-v24.md`) applies this ruling; where it and ruling 1 differ, this ruling governs the ABI and the declaration, ruling 1 everything else.

## Follow-up: where "no silent paste on v24" lives (2026-10-28, verbatim)

While writing the spec, the main session found that ruling 2 §2's clarification ("typed origin on a manifest WITHOUT the leaf → `UNSUPPORTED_OPERATION`") would break typing on every non-v24 page that shares `sdk/document-sdk.js`. The question sent to the same fable agent, verbatim:

> Fact (read just now): `sdk/document-sdk.js` is shared by many pages besides the v24 product page — `web/e1-editor-app.js`, `web/demo-editor-app.js` and the E1/E2 harness pages (`web/e1-*-app.js`, `web/e2-c-*-app.js`) all `import { createDocumentEngine } from "./sdk/document-sdk.js"` and drive the same `input/input-adapter.js` (source `beforeinput`/`composition`) into `DocumentSdk.insertText`. Their profiles (v1…v23, E1) will never declare `typedInsert`. Calc is NOT affected (`spreadsheet-shell/calc-document-sdk.js` has its own engine class and imports only `DocumentSdkError`). Applied literally, the clarification makes every typed character on every non-v24 page answer UNSUPPORTED_OPERATION, i.e. typing breaks on all of them the next time they are assembled from the live SDK.
>
> Proposed instead (please accept, amend or reject):
> 1. SDK: if the manifest declares `typedInsert`, route = `uno-insert-text` for beforeinput/composition text without LF/CR/NUL, `paste` otherwise; the wire payload carries `route`. If the manifest does NOT declare it, the request is byte-identical to today's (`{documentHandle, text}`, no `route`) — that profile's shipped and measured route. Unknown non-empty `metadata.source` → `INSERT_ORIGIN_UNKNOWN`, `dispatched:false`, on every profile.
> 2. The "no silent paste on v24" property moves to the v24 product page: at open, beside the existing `PINNED_WASM_SHA256` check (`web/e2-editor-app.js` ~3851), the page also requires `editorContract.typedInsert === "document-sdk-insert-typed-text"` and otherwise refuses with the same `PAGE_BUILD_MISMATCH` path, so no typed character is ever sent. Your red case (d) becomes: v24 manifest with the leaf removed → page refuses at open; zero insert requests in the window.
> 3. Worker (v24): `route:"uno-insert-text"` → new export (after the init presence check); `paste` or absent → old export; any other `route` value → INVALID_ARGUMENT, dispatched:false. The reply's `method` names what the engine did, so T2/T4 can compare request `route` with reply `method` per request.
>
> Is (2) an acceptable replacement for the SDK-level refusal, and does anything in T1–T5 or (i)–(viii) change?

The answer, verbatim:

> ## Follow-up ruling (ABI ruling 2, §2 clarification): ACCEPT (2) as the replacement, with three amendments
>
> Verified by reading: 28 pages under `web/` import `./sdk/document-sdk.js` (the e1/demo/e1-*/e2-c-* set you named); `spreadsheet-shell/calc-document-sdk.js` imports only `DocumentSdkError`; `document-sdk.js:533-541` sends `{documentHandle, text}` and drops metadata; the worker maps `insertText` to `oxsdk_document_insert_text` (`:1423-1426`). Your fact stands, and my §2 line applied literally would indeed break typing on every non-v24 page assembled from the live SDK. It is withdrawn; the property belongs to the v24 page, as you propose.
>
> Amendments:
> A1 (to item 1). On a manifest WITHOUT the leaf the SDK must ignore `metadata` entirely — request byte-identical to today, no new error either. `INSERT_ORIGIN_UNKNOWN` fires only when the manifest declares `typedInsert`. Reason: a new error on frozen, measured profiles is a behaviour change on exactly the paths item 1 promises not to touch, and no census of non-adapter `metadata.source` callers (harness pages, tools) exists; I may not run one read-only. T3's dynamic check therefore runs against a leaf-declaring manifest. When the leaf IS declared, every insertText carries `route` (typed → `uno-insert-text`; paste, no metadata, or typed text containing LF/CR/NUL → `paste`), so on v24 an absent `route` can only come from a foreign SDK and is visible as such.
> A2 (to item 2). Red case (d) is a real page run, not a predicate unit test: leaf removed → open refused on the `PAGE_BUILD_MISMATCH` path, zero `insertText` requests in the window; plus its positive control: leaf present → open succeeds and the first typed character's request carries `route:"uno-insert-text"`. Keep the worker honest independently of the page: `typedInsert` joins `DOCUMENT_EXPORT_OPERATIONS`, so `route:"uno-insert-text"` on a leafless manifest answers `UNSUPPORTED_OPERATION` from the existing `documentExportDeclared` gate (worker-level (d′), scratch manifest). The init presence check (c) is unchanged and still mandatory.
> A3 (to item 3). Accepted as written. The reply's `method` is the engine's statement; the request's `route` is the SDK's. Both are recorded per request.
>
> T1–T5 and controls: T1, T4, T5 unchanged in substance; T4 note: if any paste/replace-selection/paste-markdown check compares request PAYLOAD bytes, the added `route:"paste"` field on v24 is a declared delta, not a regression — outcomes (saves, replies) must still be byte-identical. T2 tightens to per-request: every counted type cell has request `route:"uno-insert-text"` AND reply `method:"uno-insert-text"` AND `completion:"uno-command-result"`; a type-cell request without `route`, or any `method:"paste"`, is FAIL for that cell. T3: literal extraction unchanged; runtime arm per A1. Controls (i)–(iii), (v), (vi)=c, (viii)=e unchanged; (iv) per A1; (vii)=d replaced by A2's page run + positive control + (d′). Default verdicts unchanged.
