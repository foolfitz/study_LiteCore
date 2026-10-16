# Facts for the next link batch: Markdown paste (A) and a manifest field that declares C

Gathered 2026-10-16, read-only. Nothing was built, linked, run in a browser, edited or committed in the repo.
Repo HEAD at the time: `338b8ddb`. Paths are relative to `/home/jiajun/LibreOffice/study_LiteCore/` unless absolute.

Evidence labels used on every claim:

- **[SRC]** read in source (file:line given);
- **[DOC]** stated in a spec, handoff, finding or README (file:line given), not re-verified unless also [SRC];
- **[BYTES]** a static byte search of a committed artifact done in this task (command shape given), no execution;
- **[INF]** my inference; it needs a measurement or a ruling before anyone relies on it.

---

## ITEM 1 — Markdown paste (A)

### 1(a) Origin

- **The ruling, verbatim** [DOC] `research/RESEARCH-2026-10-14-markdown-paste.md:5`:
  「**擁有者裁示（2026-10-14）**：**A：明確的「貼上為 Markdown」**。Ctrl+V 照舊貼純文字，另外提供一個「貼上為 Markdown」，不自動猜。要改引擎，排進下一批連結（和 `Language=`、finding 031 的修法一起）。」
- **Trigger** [DOC] same file `:3`: the owner pasted Markdown into a new document while hand-testing 0.2.19, it was not converted, and called it 「libreoffice 26.x 原生的功能」.
- **Handoff record** [DOC] `handoff/HANDOFF-2026-10-14-v20-linked-v67-frozen-new-document-0.2.19.md:107-110`: "Markdown paste: the owner chose A, an explicit 「貼上為 Markdown」 command; Ctrl+V stays plain text … Our WASM core has md4c and the sw markdown filter compiled in. The engine hard-codes `text/plain` at `probe_engine.cpp:3239`. A fix therefore needs an engine change, and it goes into the next link batch".
- **Still queued** [DOC] `handoff/HANDOFF-2026-10-16-0.2.24-count-holds-release-text-revised-makefile-a.md:97-104` (Next 3, "Markdown paste (A)").
- **Draft scope, explicitly not yet a spec** [DOC] research doc `:26-31` ("草稿，尚未成為規格"): (1) an engine paste that carries a mimetype or a dedicated `paste-markdown` command calling `paste(document, "text/markdown", …)`, "ABI 與 action 清單怎麼擴充由規格決定"; (2) a page entry point that reads the clipboard ("`navigator.clipboard.readText` 需要使用者手勢，Firefox 另有限制，要先量"); (3) criteria: headings, bold, italic, lists, code, tables; paste-into-existing-paragraph identical to native 26.8; Ctrl+V unchanged (red case); (4) native first.
- **No spec exists yet.** `grep -rli markdown specs/ handoff/tasks/` finds no link-batch or M3 spec text for it [SRC: grep]. Older, unrelated-but-adjacent specs exist:
  - `specs/SPEC-E4-000-overview.md:1-4` "Markdown 讀寫（候選）… 尚未執行，未取得執行授權" (open/save, not paste); its gate G0 is "WASM reachability" `:66-100`.
  - `specs/SPEC-R6+-roadmap.md:195-217` (§6.3) lists the filter files and says reachability in WASM is "完全未測".
  - `specs/SPEC-E2-000-overview.md:190` lists "markdown 語法輸入或輸出" as out of E2's scope.
  - `specs/SPEC-R10-000-overview.md:26` P3: "E4 判定完成，markdown 濾鏡去留凍結" — shipping Markdown paste puts the md filter into the irremovable set for R10 [INF].
- **Defect in the research doc itself** [SRC]: the committed version (`f3999ead`) had a stray `EOF` line and the full `git add … && git commit …` command at the end of the file body (heredoc accident). While this task ran, the working tree was edited to remove them (uncommitted at the time of writing; the file now ends with a 修訂紀錄 row dated 2026-10-16, `:33-37`). Still stale in it: the `web/e2-editor-app.js:2392` citation (`:24`); the comment is now at `:2544-2560` [SRC].

### 1(b) Current behaviour, read in source

**Engine (C++, relink needed for any change).**
- `handleInsertText` [SRC] `wasm_sdk_probe/src/probe_engine.cpp:3234-3268`: the only text-entry path. It calls `gState.document->pClass->paste(gState.document, "text/plain;charset=utf-8", command.text.data(), command.text.size())` (`:3239-3241`); only if `paste()` returns false does it fall back to one `postKeyEvent` per code point (`:3242-3256`). Then it unconditionally `++gState.revision` (`:3258`) and replies `{"type":"inserted","method":"paste"|"postKeyEvent"}` (`:3260-3267`). No postcondition, no readback.
- `handleReplaceSelection` [SRC] `probe_engine.cpp:4313-4330` also hard-codes `text/plain;charset=utf-8` (`:4316-4318`).
- Dispatch [SRC] `probe_engine.cpp:6125-6127` (`CommandType::InsertText → handleInsertText`).
- C ABI export [SRC] `wasm_sdk_probe/src/sdk_api.cpp:113-123` `oxsdk_document_insert_text(requestId, documentHandle, utf8, utf8Length)` — no mimetype parameter. SDK ABI is `0x00010001` (`src/sdk_api.h:10-13`, `sdk_api.cpp:14`).
- Finding 067 is the known blind spot of this path [DOC] `web/e2-editor-app.js:2911-2917`: the engine's `paste` accepted `"\n"`, did nothing, and incremented revision anyway.
- Upstream fact relevant to verification [SRC] `libreoffice-26-8/desktop/source/lib/init.cxx:6165-6192`: `doc_paste` returns false only if `doc_setClipboard` fails or `.uno:Paste` cannot be dispatched; it returns **true regardless of whether the import produced anything**. So the engine cannot learn "Markdown import failed" from `paste()`'s return value [SRC + INF].

**SDK worker (part of the profile identity; pinned).**
- `insertText` → `oxsdk_document_insert_text` [SRC] `wasm_sdk_probe/sdk/sdk-worker.js:1361-1368`; capability `insert-text` [SRC] `sdk-worker.js:28`; capability gate `:1286-1296`.
- Precedent for a compiled, non-action document export gated by a manifest declaration [SRC] `sdk-worker.js:205-223` (`DOCUMENT_EXPORT_OPERATIONS` = `pageRectangles` only, `documentExportDeclared`), dispatch `:1418-1424`. `pageRectangles` is deliberately NOT in `OPERATION_CAPABILITIES` (`:24-55`), so it needs no capability string.
- The worker bytes are pinned in the v20 recipe [SRC] `wasm_sdk_probe/Makefile:1546` `E2_V20_WORKER_SHA256 := 478d0da1…`, checked at `:1590`.

**SDK (main thread; in the frozen shell bundle).**
- `DocumentHandle.insertText(text)` [SRC] `wasm_sdk_probe/sdk/document-sdk.js:524-535`, no mimetype.
- Gate precedent [SRC] `document-sdk.js:609-618`: `pageRectangles()` throws `UNSUPPORTED_OPERATION` unless `editorContract.pageRectangles === PAGE_RECTANGLES_DECLARATION`.

**Shell / input (E1-C bound files must not change).**
- `EditorSession` wires `HostInputAdapter` (commit → `commitText`) and `PlainTextClipboardAdapter` [SRC] `wasm_sdk_probe/editor-shell/editor-session.js:92-110`; `commitText` enqueues `document.insertText` [SRC] `:511`; `pasteFromClipboard` / `pasteEvent` exist [SRC] `:218-237`.
- `PlainTextClipboardAdapter.pasteFromClipboard` requires `options.userGesture === true`, then `navigator.clipboard.readText()`, then commits through the input adapter as plain text [SRC] `wasm_sdk_probe/input/clipboard-adapter.js:89-117`; `pasteEvent` reads only `text/plain` [SRC] `:119-149`.
- `HostInputAdapter`: `insertFromPaste` is a TEXT_INPUT_TYPE [SRC] `wasm_sdk_probe/input/input-adapter.js:3-7`; `handleBeforeInput` commits `event.data` as text (`:227-260`); `handlePaste` reads `clipboardData.getData("text/plain")` (`:262-272`); per-commit limit `DEFAULT_MAX_UTF8_BYTES = 16 * 1024` (`:1`), enforced in `commitText` (`:324-344`).
- These files are bound to E1-C: `e1/editor-shell-bundle-v2.json` includes `editor-shell/editor-client.js`, `editor-shell/editor-session.js`, `editor-shell/state-machine.js`, `input/clipboard-adapter.js`, `input/input-adapter.js`, `bundleSha256 187706b2…` [SRC: read the JSON]; guarded by `tools/check_e1_c_bundle_intact.py:1-37` [SRC]. Precedent: finding 068's fix moved to a subclass because this check refused an edit [DOC] `editor-shell-v2/narrow-editor-v2-session.js:500-510`.

**Page (in the frozen shell bundle).**
- No paste listener, on purpose [SRC] `wasm_sdk_probe/web/e2-editor-app.js:2544-2560`: Ctrl+V arrives as `beforeinput`/`insertFromPaste` and the input adapter commits it once; a page handler made a second commit (markOccurrences 2). The product-path runner's `ctrl-v-reaches-the-document` requires exactly one occurrence [SRC] `wasm_sdk_probe/tools/run_e2_c_product_path.py:5962-5966`.
- Toolbar dispatcher [SRC] `e2-editor-app.js:2376-2386` (`undo`, `redo`, `insert-text`, `save`, editor actions); buttons [SRC] `web/e2-editor.html:268-294` (no paste button). The page passes `navigator.clipboard` to the session [SRC] `e2-editor-app.js:3357`.

**Net:** every Ctrl+V and every `insertText` reaches the core as `text/plain;charset=utf-8`. There is no path that can produce `text/markdown` today [SRC, above].

### 1(c) How LibreOffice 26.8 core does it (core checkout `libreoffice-26-8`, HEAD `671c848b` = the `coreCommit` in v20's manifest)

- **Commits.** All twelve commits the research doc names exist and are ancestors of `671c848b` [SRC: `git merge-base --is-ancestor`]: `f8c2fbdbceac` (tdf#162153, author 2025-07-19), `c75975d1ac46`, `a3eb70238396`, `04a253b3c71f`, `1f665988d0b5` (tdf#171481, author 2026-03-31), `d5509c16cafe`, `0c361202d0ee` (tdf#171121), `f12cc758a1a0`, `de87e5b0ae65`, `8f5d83abd4a0` (cool#15535), `1b0c64be44c4` (tdf#172084), `6e28f612c22e` (Calc). Also `517e2fb772ee` (gtk3), `6335b138ba47` (win), `1f52f6507798` (qt dialog).
- **Plain paste never converts.** `PasteFileContent` [SRC] `sw/source/uibase/dochdl/swdtflvr.cxx:2200-2239`: `STRING → ReadAscii`, `MARKDOWN → ReadMarkdown`; both read `rData.GetString(nFormat, …)` into a UTF-16 `SvMemoryStream` with charset `RTL_TEXTENCODING_UCS2` (`:2234-2236`). `MARKDOWN` reaches it via `PasteData` [SRC] `:1887-1896`.
- **Heuristic removed** [SRC] `git show 1f665988d0b5`: "Remove redundant markdown heuristic detection code … because we now have markdown under paste special" (deletes `comphelper/source/misc/markdown.cxx` and the Calc heuristic).
- **Paste Special lists Markdown only if the clipboard has the format.** `aPasteSpecialIds` includes `MARKDOWN` [SRC] `swdtflvr.cxx:3555-3573`; `FillClipFormatItem` adds a format only if `TestAllowedFormat(rData, id, dest)` [SRC] `:3685-3687`. The desktop VCL backends synthesise a `text/markdown` flavour whenever plain text is present (gtk3 `517e2fb772ee` `vcl/unx/gtk3/gtkinst.cxx:768`, qt `vcl/qt5/QtTransferable.cxx:126`, win `vcl/win/dtrans/DOTransferable.cxx:354`, osx `vcl/osx/DataFlavorMapping.cxx:792`) [SRC]. **The LOK clipboard does not**: `LOKTransferable::initFlavourFromMime` only special-cases `text/plain*` and `application/x-libreoffice-tsvc` [SRC] `desktop/source/lib/lokclipboard.cxx:176-190`. So under LOK, Markdown is pasted only when the caller hands `paste()` a markdown mimetype [INF from SRC].
- **What `paste(doc, "text/markdown…", …)` does in core.**
  - `doc_paste` → `doc_setClipboard` with one flavour → dispatch `.uno:Paste` with `AnchorType AS_CHARACTER`, `IgnoreComments true` [SRC] `init.cxx:6165-6192`.
  - The flavour's MIME is kept as given and its DataType is `Sequence<sal_Int8>` (bytes) because it is not `text/plain` [SRC] `lokclipboard.cxx:186-188, 192-210`.
  - Format lookup: `GetFormatIdFromMimeType_impl(mime, allowMoreParams=true)` [SRC] `sot/source/base/exchange.cxx:235-263, 382-385`, `MARKDOWN = 149` [SRC] `include/sot/formats.hxx:182`, entry `{"text/markdown","Markdown",OUString}` [SRC] `exchange.cxx:200`. So both `text/markdown` and `text/markdown;charset=utf-8` map to `MARKDOWN` [INF from SRC: second loop accepts `;params` for ids ≥ RTF].
  - The Writer free-area exchange tables accept `MARKDOWN` [SRC] `sot/source/base/formats.cxx:783, 819, 861` (also text-frame tables `:144, 178, 210`).
  - Decoding: `TransferableDataHelper::GetString` takes the byte sequence and decodes it with `osl_getThreadTextEncoding()` [SRC] `vcl/source/treelist/transfer.cxx:1491-1523` — **not** UTF-8 explicitly. On Linux desktop/Collabora that is UTF-8 by locale [INF]. In our WASM process it depends on the locale codeset (`sal/osl/unx/nlsupport.cxx:285-289` uses `nl_langinfo` on `__EMSCRIPTEN__`) and was never measured; `static/emscripten/environment.js` sets no `LANG` [SRC]. **Risk: non-ASCII (CJK) Markdown could decode wrongly in WASM** [INF; measure].
  - Parser: `SwMarkdownParser::CallParser` converts UCS2 → UTF-8 and calls `md_parse` with `MD_DIALECT_GITHUB | MD_FLAG_WIKILINKS` [SRC] `sw/source/filter/md/swmd.cxx:898-960` (flags `:951`). Empty input returns `ERRCODE_IO_INVALIDCHAR` (`:931-934`).
  - Paste-mode behaviour from cool#15535 [SRC: commit messages]: pasting into an existing paragraph splits/joins like RTF (`f12cc758a1a0`), reuses a matching numbering rule (`de87e5b0ae65`), and keeps the insertion point's paragraph style and margins (`8f5d83abd4a0`); `swmd.cxx:940-945` "Don't touch the paragraph style when pasting".
  - **Images**: `![](url)` → `InsertImage`; for a non-`data:` URL it may open the URL to detect its size (`GraphicDescriptor(aGraphicURL).Detect(true)`) when `allowAccessLink` [SRC] `swmd.cxx:667-700, 71-80`. What a remote URL does in our WASM engine (network, blocking) is unknown [INF; measure or exclude].
  - **Wiki links** use the app language: `"https://" + aLang + ".wikipedia.org/wiki/" + target` [SRC] `sw/source/filter/md/mdcallbcks.cxx:226-227` (ties to `Language=`).
  - **Error dialog**: on `.uno:Paste`, `bMsg = (nullptr == pPt)` is true [SRC] `swdtflvr.cxx:1856`, and a read error runs a modal `MessageDialog` [SRC] `:2310-2316`. What a modal dialog does inside our headless WASM engine is unknown (could block) [INF; measure with a deliberately bad input].
  - Native unit tests to copy as reference cases [SRC] `sw/qa/filter/md/md.cxx:997-1009` (`testPaste`, `SwTransferable::PasteFormat(…, MARKDOWN)`), `:1047-1055` (`testCTLPaste`, the tdf#172084 encoding case).
- **How Collabora does it** [SRC, `cool-26-04` HEAD `c64a7343`, 2026-07-31]:
  - Its only browser-side Markdown paste is the AI sidebar: header `'paste mimetype=text/markdown;charset=utf-8\n'` + body [SRC] `browser/src/control/Control.AIChatSidebar.ts:2491-2509` (header `:2494`). The kit turns that into `getLOKitDocument()->paste(mimeType.c_str(), data, size)` [SRC] `kit/ChildSession.cpp:1853-1905` (call `:1896`). **This is exactly the LOK call our engine would make.**
  - Its Paste Special sends `uno .uno:PasteSpecial` and opens core's dialog [SRC] `browser/src/map/Clipboard.js:363-365, 1528-1531`; `grep -i markdown browser/src/map/Clipboard.js` is empty [SRC]. Combined with the LOKTransferable fact above, Collabora's Paste Special probably does **not** offer Markdown for ordinary browser text [INF; not measured].
  - **Correction** to research doc `:16` / handoff `:107` ("Collabora Online 也走這條路"): cool#15535's three commits are core import fixes for pasting into an existing paragraph; they do not show a COOL "Paste Special → Markdown" UI [SRC: commit messages + grep].

### 1(d) Is md4c / the sw markdown filter in the WASM core? Evidence ladder

| Step | Fact | Label |
|---|---|---|
| Configure | `wasm-lite/build-headless-probe/config_host.mk:58` `BUILD_TYPE=… MD4C …`; `:648` `SRCDIR=…/libreoffice-26-8`; `:825` `MD4C_CFLAGS` | [SRC] |
| Compile | `wasm-lite/build-headless-probe/workdir/CxxObject/sw/source/filter/md/{mdcallbcks,mdnum,mdtab,swmd,wrtmd}.o` (dated Aug 1; `mdnum.o` is 362 B because `mdnum.cxx` is 25 lines) | [SRC: ls] |
| Archive | the five objects are in `workdir/LinkTarget/Library/libswlo.a.objectlist`; `workdir/LinkTarget/StaticLibrary/libmd4c.a` exists | [SRC] |
| Link inputs | `instdir/program/soffice.js.linkdeps` contains `-lswlo` and `…/libmd4c.a`; our product link uses `$(cat $(LINKDEPS))` [SRC] `wasm_sdk_probe/Makefile:20, 841-855` | [SRC] |
| Reader registered | `ReadMarkdown = new MarkdownReader` [SRC] `sw/source/filter/basflt/fltini.cxx:101, 107`; referenced from `PasteFileContent` `swdtflvr.cxx:2238`, which the text/plain path already runs | [SRC] |
| Bytes in the shipped wasm | the C-string `".wikipedia.org/wiki/"` — a string literal **only** at `mdcallbcks.cxx:227` in the whole core tree (`grep -rF '".wikipedia.org/wiki/"'`) — is present once in both `dist/profiles/e2-editor-v19/probe.wasm` (`1aafd4f9…`) and `e2-editor-v20/probe.wasm` (`313b08d5…`, offset 63423019). Also present: UTF-16 `text/markdown` (sot table, `exchange.cxx:200`) ×1 and ASCII `"text/markdown "` (trailing space, from `vcl/source/treelist/transfer.cxx:1296`) ×1 | [BYTES] |
| Runtime | never executed in WASM; the research doc says the same (`:22` "沒有直接驗證過") | [DOC] |

Conclusion: the md import callbacks are almost certainly linked (a literal from `mdcallbcks.cxx` survived `--gc-sections`) [INF, strong]. Whether `paste("text/markdown…")` works end to end in WASM is **not established**; under SPEC-E4's own rule a positive static result "不是決定性的" (`specs/SPEC-E4-000-overview.md:76-77`). Paste does not need the filter registry (`.xcu`) because it calls `ReadMarkdown` directly (`swdtflvr.cxx:2238`) [SRC]; open/save (E4) would.

Side note [SRC]: `transfer.cxx:1296` compares against `"text/markdown "` with a trailing space (since `f8c2fbdbceac`). It only matters on the fallback path after `RegisterFormat` (`:1241`) failed to recognise the MIME, so it does not affect the LOK path [INF]. Possible upstream nit; not a finding here.

### 1(e) Decided vs open

**Decided** [DOC]: explicit command (A); Ctrl+V stays plain text; no auto-detection; it needs the engine; it goes into the next link batch (research doc `:5`; handoff 10-14 `:107-109`).

**Open (precise questions):**
1. **Engine/ABI shape.** (a) A new document-level export, e.g. `oxsdk_document_paste_markdown`, gated by a manifest declaration like `redo` / `pageRectangles` (no wire id, editor ABI unchanged; precedent ruling S-11 `findings/evidence/link-batch/review/ruling-2.md:63`, worker `sdk-worker.js:205-223`); (b) widen `oxsdk_document_insert_text` with a mimetype (SDK ABI change, `sdk_api.h:62`); (c) an editor action with a wire id (editor ABI 4→5; both bounds must move: `src/editor_api.cpp:65` `kMaxExternalAction = 21`, `src/probe_engine.cpp:7069` `kMaxInternalEditorAction = 23`, the 2026-08-22 lesson at `:7062-7068`). Which one? [INF: (a) has the most precedent and keeps capabilities untouched.]
2. **MIME string**: `text/markdown` or `text/markdown;charset=utf-8` (Collabora uses the latter). Both map to MARKDOWN [INF from SRC].
3. **Encoding in WASM**: does the byte flavour decode UTF-8 correctly (`transfer.cxx:1517`, `osl_getThreadTextEncoding()`)? If not, what is the fix without changing core? [INF; measure first.]
4. **Postcondition / honesty**: `paste()` returns true even when nothing was imported (`init.cxx:6185-6191`). What does the engine verify before replying (revision +1 only if the document changed, as 067 showed it can be +1 for nothing)? No fallback to `postKeyEvent` typing the raw Markdown? [INF]
5. **Selection**: what does "paste as Markdown" do on a range — replace it (as `.uno:Paste` does) or refuse? [INF]
6. **Undo granularity**: is one Markdown paste one Undo step natively? [INF; measure native first.]
7. **Size limit**: the input adapter's 16 KiB (`input-adapter.js:1`) does not apply to a new path; what limit applies? [INF]
8. **Hazards in core**: remote image URLs (`swmd.cxx:691-697`), the modal error dialog (`swdtflvr.cxx:2310-2316`), wiki links (`mdcallbcks.cxx:227`). Strip, refuse, or accept and name as limits?
9. **Page entry point**: toolbar button / context menu / shortcut (LibreOffice's Paste Special is Ctrl+Shift+V) and **how the text is read**: `navigator.clipboard.readText()` (needs a user gesture; Chrome permission prompt; Firefox paste prompt — research doc `:29` "要先量"), or an "arm, then Ctrl+V" mode that reads the `paste` event's `text/plain` without any permission [INF]. The E1-C-bound `PlainTextClipboardAdapter` cannot be reused unchanged because it commits as plain text (`clipboard-adapter.js:110-114`) [SRC]; the new path must live in `editor-shell-v2/` or the page.
10. **Host**: does the Nextcloud route need clipboard permissions policy (e.g. iframe `allow`)? Not read here [INF; the M3 route is described as a dedicated route in memory, not verified].

### 1(f) Layers that change and hash bindings touched

| Layer | Change | Binding / identity touched |
|---|---|---|
| Engine C++ (`src/probe_engine.cpp`, `src/sdk_api.{h,cpp}`) | new handler or mimetype parameter | **relink** (owner's step); new profile `e2-editor-v21` (wasm/loader hashes); `check_merge_key_undo_scope.py` define-reach check if behind a new define (Makefile `:3629-3633` precedent); M1-1 per-object diff |
| Export list | new `_oxsdk_…` symbol if (a) | Makefile `exports.txt` recipe (v20 at `:1557-1570`); X1 `--declared-export` (`tools/check_profile_identity.py:37-39`) |
| SDK worker `sdk/sdk-worker.js` | new operation + gate | new worker pin (v20's `Makefile:1546`); X1 `--declared-worker` (`check_profile_identity.py:30-32`); manifest `workerSha256` |
| Manifest | new declaration leaf (if (a)) | builder flag like `--page-rectangles` (`tools/build_e2_editor_v4_profile.py:263-270, 381-385, 559-560`) with its own refusal check; X1 `--declared-new-leaf` (`check_profile_identity.py:33-36`); the host `buildId` (hash of packaged files incl. `profiles/<p>/sdk-manifest.json`, see `wasm_sdk_probe/build/archive/host-0.2.23-engine-c3c22d92…/MANIFEST.json` `files`) |
| SDK `sdk/document-sdk.js` (+ `.d.ts`) | `pasteMarkdown()` | **shell bundle generation** (v73 includes `sdk/document-sdk.js`, `e2/editor-shell-v2-bundle-v73.json`, `bundleSha256 6ab20f68…`; `tools/build_e2_c_shell_bundle.py:757`) |
| Shell `editor-shell-v2/*` | `offers…()` gate + session method enqueuing a mutation | same shell generation (v74+); E1-C (`187706b2…`) must stay intact — do not touch `editor-shell/*`, `input/*` |
| Page `web/e2-editor-app.js`, `web/e2-editor.html` | button/shortcut + clipboard read | shell generation; the served page hash pinned by every M3 runner (`SPEC-M3-link-batch.md` §17.1 table, `:527-533`) and the merge runner `BINDING.pageSha256` (`tools/run_merge_wasm_shakedown.py:173-174`) |
| Host (Nextcloud app) | new engine package; probably no host code | host version bump; `BUILD_ID`/`HOST_*`/`SESSION_SHA256`/`SHELL_BUNDLE_SHA256` re-pins (§17.1 precedent) |

### 1(g) Existing tests/criteria/evidence, and what would show it works

Existing:
- `ctrl-v-reaches-the-document` (exactly one marker) [SRC] `tools/run_e2_c_product_path.py:5962-5966` — the natural home of "Ctrl+V unchanged", but it checks the marker count, not that Markdown syntax stays literal [INF].
- Paste latency instrument: `findings/evidence/paste-latency/` (`probe_paste_latency.py`, a "click resolved" field added) [DOC] handoff 10-14 `:111-115, 123`; native measured paste 7.5–24.8 ms for 40 paragraphs (same `:113`).
- Native LOK paste harness to copy: `wasm_sdk_probe/tools/f059_native_paste_pending.cpp:122` calls `pClass->paste(document, "text/plain;charset=utf-8", …)` [SRC]. Native build has the md objects: `build-native-26-8/workdir/CxxObject/sw/source/filter/md/*.o` [SRC: ls].
- Core reference tests: `sw/qa/filter/md/md.cxx:997, 1047` [SRC].

Measurements that would show it works [INF, draft]:
1. **Native first**: the same Markdown corpus through native LOK `paste("text/markdown;charset=utf-8")` at fixed positions (empty doc, start of a paragraph with text — cool#15535's case, inside a bulleted paragraph, on a selection); keep `content.xml`.
2. **WASM probe before the spec is final** (research doc `:22`): one `paste("text/markdown…")` on the current engine is impossible without a link — the engine hard-codes the MIME — so the first WASM evidence needs either a diagnostic profile or the batch's own link [INF].
3. Per-construct criteria (form one, per instance): heading levels, bold, italic, inline code, code block, ordered/unordered lists, table, link — each compared to native by `content.xml` structure (paragraph style, list, table) rather than bytes (rsid) [INF; `SPEC-M3-paragraph-merge` §12's paragraph comparator is the precedent cited in `SPEC-M3-link-batch.md:171`].
4. **CJK arm** (encoding risk above) and **CTL arm** (tdf#172084's case).
5. **Red cases**: Ctrl+V of `# 標題 **粗**` stays literal in one body paragraph; the button on a profile without the declaration is absent/refused; a mismatched declaration (field on a wasm without the export) is refused by the builder.
6. Hazard arms: a remote-image Markdown, an input that makes `ReadMarkdown` fail (dialog), a large paste near the chosen limit; one Undo restores the original.

### 1(h) Interactions

- **`Language=`**: wiki-link URLs use `GetAppLanguageTag()` (`mdcallbcks.cxx:226-227`) [SRC]; the default character language of pasted text follows the document/app language [INF]. `osl_getThreadTextEncoding()` is a locale codeset, not the LOK `Language=` option [INF].
- **Finding 031** (localized UI style names): any Markdown verification that reads paragraph style **names** hits the same trap [INF]; compare by pool/programmatic names.
- **D12 / new document**: pasting into a blank template document keeps the insertion point's paragraph style (`8f5d83abd4a0`) [SRC: commit message]; native reference cases should include a template-made new document [INF].
- **placeCaret on TEXT_SELECTION (140)**: the paste queues behind a click; 140's diagnosis was exactly "slow paste = the click before it" [DOC] handoff 10-14 `:111-115`. No shared engine code [INF].
- **C / held deletes / 145**: a Markdown paste is a new mutation in the same queue as held deletes (`e2-editor-app.js:2701-2745`) [SRC]; the held-delete accounting must not count it [INF].
- **142 actions / editor ABI**: if Markdown paste is an action (option c), it shares the ABI bump that 142's `move-document-start/end` likely needs [INF].

---

## ITEM 2 — A manifest field that declares C

### 2(a) Origin, and C defined precisely

**What C is** [DOC] `specs/SPEC-M3-link-batch.md`:
- §2 row 4 (`:19`): 「C：段首按住 Backspace 撞到文件開頭不再拒絕」.
- §4.4 (`:57-59`, original): merge-key barrier at `nothing-selected` with `keyPosted === false` completes 「成功、沒有改動」(`editor-action-completed`, `changed: false`, new completion `verified-boundary-noop`), not `EDITOR_BOUNDARY_UNSUPPORTED`, no reopen; the "pull back a late Shift" clause.
- **§10.5 (`:173-184`) supersedes §4.4's pull-back and C1's busy arm**: after the first 250 ms NONE (`rejectSelectionBarrierAtDeadline`) the transaction stays in `AwaitingUnitSelection` for one more `MergeStepDeadlineMs` (2000 ms); a K1 `TEXT_SELECTION` inside the window takes the ordinary path; at expiry, if the second `readSelection()` is still NONE **and** the cached selection is still collapsed, complete `verified-boundary-noop` (`changed: false`, revision unchanged, `boundaryNoop: { waitedMs }`); the other exits (`unit-late`, `EDITOR_STATE_UNAVAILABLE`) unchanged. Named residual **L-C-late-K1**; named cost 「在文件開頭按 Backspace，約 2.25 秒才回應」.
- §10.7 (`:196-200`): every arm that expects `nothing-selected` / refusal counts / generation lists must be re-expected before any count: 「拒絕 0 次、世代 `['1']`、文件與游標不變、打的標記落在游標所在處」.
- §15.1 (`:439-455`): second residual **L-C-number-or-indent** (three positions where K1 shows nothing but Writer's own key would change the document: numbering label + Delete; bulleted or first-line-indented first paragraph + Backspace at start); no engine change; engine source fixed at `82af92ca` (then `543a5566`, §15.6).
- §17.3–17.4 (`:545-567`): production-UI Rbs/Rdel re-expected under C, **keyed on the bytes of the wasm the host serves**; B3x withdrawn from the count; §17.4 named limit: under C the Rbs/Rdel green has no positive control, so the RESULT reader must confirm a ≥ 2,000 ms busy with unchanged `rev` per counted run (done for 0.2.24, `:588`).

**Engine, read in source** (all behind `OXSDK_MERGE_KEY_UNDO` **and** `OXSDK_E2_V20_LINK_BATCH`):
- Window state [SRC] `src/probe_engine.cpp:547-558` (`boundaryNoopWindow`, `startedAt`); constant [SRC] `:579` `MergeStepDeadlineMs = 2000`.
- Entry [SRC] `probe_engine.cpp:4007-4053`: on first NONE + `typedCollapsed`, open the window and push `boundaryDeadline` by 2000 ms (`:4035-4041`); at expiry call `finishSelectionBarrierBoundaryNoop()` (`:4043`). Without the v20 define the same branch is `finishMergeKeyError("nothing-selected")` (`:4045-4048`); without `OXSDK_MERGE_KEY_UNDO` it is `EDITOR_BOUNDARY_UNSUPPORTED` (`:4050-4054`).
- Reply [SRC] `probe_engine.cpp:3543-3570`: `editor-action-completed`, `changed:false`, `revision` = before, `"completion":"verified-boundary-noop"`, `"boundaryNoop":{"waitedMs":…}` measured from K1's post (`:4239-4242`).
- The only compile-time switch is the define; the Makefile says this rule is the only one that defines it [SRC] `Makefile:1525-1526, 1553`.

**Origin of the queue item** [DOC]:
- Task 10-14i asked the runner to key "on something the profile declares (its manifest or ABI), not on a profile name" (`handoff/tasks/TASK-2026-10-14i-merge-runner-c29-c30-under-c.md:13`).
- Finding [DOC] `findings/evidence/link-batch/v20-shakedown/merge/re-expectation/README.md:21`: "**The manifest declares nothing about C.** `editorContract` on v19 and v20 differs only in the three artifact hashes and `pageRectangles` … no flag was added for C"; `:23`: "**Noted for the next link** … a manifest field for C, TOLD to the builder at link time like `pageRectangles`, would be the better declaration; the runner could then read the manifest and STOP when the manifest and the wasm disagree."
- Repeated [DOC] `findings/evidence/link-batch/host-0.2.20/re-expectation/README.md:104`; `handoff/HANDOFF-2026-10-14b-v68-v69-frozen-v20-cut-over-host-0.2.20.md:29` ("For the next link: declare C in the manifest") and `:93` ("a manifest field that declares C (10-14i). Today two tools key on a wasm string."); 10-15 `:74`; 10-15b `:104`; 10-16 `:102`.
- Verified now [SRC: flattened diff of the two manifests]: v19 vs v20 `sdk-manifest.json` differ in exactly `editorContract.loaderSha256`, `.wasmSha256`, `.workerSha256`, `.pageRectangles` (new), `profile`, `sdkVersion`. `abiVersion` 4, `selectionBarrier "verified-single-writer-unit-v1"`, `boundaryRejectionRequiresFreshWorker true` are identical.

### 2(b) Current behaviour, read in source

**The tools that key on the wasm string — four today, not two.** "Two" was true on 10-14b (the merge runner `7e6c9acd` and the held judge `269cbc6d`, both 2026-10-14); two more joined on 10-15 [SRC: `git log -S`].

| # | Tool | How it keys | Since |
|---|---|---|---|
| 1 | `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py` | defines `BOUNDARY_NOOP_FRAGMENT = b',"completion":"verified-boundary-noop"'` and `boundary_noop_declared(wasm) = FRAGMENT in wasm.read_bytes()` (`:200-206`); rationale comment `:177-199`; `expectation(decision, boundary_noop)` (`:217-235`); reads `dist/profiles/<candidate>/probe.wasm` (`:1355-1357`); records `candidate.boundaryNoop` (`:1420-1428`) | `7e6c9acd` 10-14 |
| 2 | `findings/evidence/132/held-into-refusal/judge_held_into_refusal.py` | **its own copy** of the constant (`:136-140`), resolves `static.buildId` → archived host engine package, recomputes buildId, checks page and wasm hashes, gunzips the wasm, then greps (`:155-205`); rationale `:80-95` ("No manifest field declares C, and a name is a convention") | `269cbc6d` 10-14 |
| 3 | `wasm_sdk_probe/tools/judge_counted_m2.py` | `m.boundary_noop_declared` on `dist/profiles/<profile>/probe.wasm` or `--wasm`, whose sha256 must equal every report's `bound.wasmSha256` (`:54-66`, `keying` `:144-149`, `expectation` `:119-134`) | `c8d53f39` 10-15 |
| 4 | `wasm_sdk_probe/tools/check_m3_production_ui.py` | imports the merge runner's constant (`:71-73`); `boundary_noop_keying(engine)` reads the host's `engine/files/<p>/probe.wasm.gz`, checks sha256 against the package manifest, greps (`:635-656`); recorded as `static.boundaryNoop` (`:632`); `engine_keying` for old reports (`:824-840`); `score_noop` (`:842+`) | `65a8ec1c` 10-15 |

Also: two frozen evidence scripts reuse the keying (`findings/evidence/link-batch/v20-shakedown/merge/re-expectation/rejudge.py:63-64`, `findings/evidence/link-batch/host-0.2.20/re-expectation/rejudge.py:302-303`) [SRC]. `run_v20_shakedown.py:795-799` and `judge_v20_shakedown.py` expect the no-op unconditionally (v20-only tools, no keying) [SRC].

**Product code does not need a declaration today** — it reacts to the completion at run time:
- Worker forwards `boundaryNoop` [SRC] `sdk/sdk-worker.js:224-230, 958-959`.
- Client accepts `verified-boundary-noop` with `changed === false` and unchanged revision on any profile; comment: "Engines without OXSDK_E2_V20_LINK_BATCH never send it, so accepting it changes nothing for them" [SRC] `editor-shell-v2/narrow-editor-v2-client.js:305-322`.
- Session marks the queue item non-mutating [SRC] `editor-shell-v2/narrow-editor-v2-session.js:995-996, 1138-1150`.
- Page drops held deletes when a no-op stands [SRC] `web/e2-editor-app.js:2701-2745`.

**Manifest machinery** [SRC]:
- Builder: every behaviour flag is TOLD, refused when the artifact cannot honour it — `--page-rectangles` (`tools/build_e2_editor_v4_profile.py:263-270`), refusal unless the export list has the symbol (`:84-105, 381-385`), written at `:559-560`. `ABI_VERSION = 4` is hard-coded (`:81`).
- Recipe: `Makefile:1582-1603` passes `--page-rectangles` for v20.
- X1: `tools/check_profile_identity.py` compares every manifest leaf (form two); `--declared-new-leaf PATH=VALUE` admits exactly one new leaf per flag (`:33-36`); a **changed** existing leaf (e.g. `abiVersion`) has no declare flag (`:13, 94-95`).
- Tests: `tests/test_e2_editor_v4_profile.py:150-199` (pageRectangles refusal); `tests/test_profile_identity.py:146-289` (declared leaf red cases).

### 2(c) Decided vs open

**Decided** [DOC]: a manifest field, TOLD to the builder at link time like `pageRectangles`; the tools would "read the manifest and STOP when the manifest and the wasm disagree" (10-14i README `:23`; host README `:104`). It is queued for the next link (10-16 `:102`). Name, value and consumers are **not** decided anywhere [SRC: grep of specs/handoffs].

**Open (precise questions):**
1. **Name and value.** By precedent a string declaration in `editorContract` (`redo: "document-sdk-redo"`, `pageRectangles: "document-sdk-page-rectangles"`). What value names C — and does it name the **variant** (2.25 s window vs. the batch's "immediate answer", see 2(f))? A boolean cannot distinguish the two [INF].
2. **What the builder checks before declaring.** For `pageRectangles` it is the export list. For C there is no export; the candidates are (a) the emitted fragment in the wasm bytes (the very key the tools use; then the field is derived from the same evidence, not independent), (b) the compile define recorded somewhere, (c) nothing (TOLD only). [INF]
3. **v20 and older profiles never get the field** (re-minting v20 is excluded, 10-14i README `:23`). So the tools' rule must be explicit: field absent + fragment present (v20) = ?; field present + fragment absent = STOP; both present = C; neither = refusal. Without a rule, adding manifest reading to the tools makes v20 a "disagreement" by construction [INF].
4. **Who consumes it.** Tools only, or also product code (e.g. the client accepting `verified-boundary-noop` only when declared, `narrow-editor-v2-client.js:314-316`)? Product use would be a stricter contract and a shell change [INF].
5. **Procedure under §34.** Changing the four tools to read the field is a check change. `specs/SPEC-M3-paragraph-merge.md:1216-1219` (§34.4): 「必須有一份誠實執行的、已 commit 的報告，證明檢查判錯…才可以改程式。否則只登錄一行，不寫程式。」 On a v21 that carries both the fragment and the field, the existing byte keying judges correctly, so there is no witness for that edit. Precedent that a new identity's mechanics can be a "new use, not a repair": X1's declared-delta flags (`SPEC-M3-link-batch.md:468`, §15.3). Which category is this? [INF — needs a ruling.] §34.5 (`:1225-1229`) is not touched: the field does not add a tenth bound key [INF].
6. **`boundaryRejectionRequiresFreshWorker: true`** stays true on v20 (`dist/profiles/e2-editor-v20/sdk-manifest.json`) although document-end refusals are gone; other refusals remain (finding 136, cell ends, §17.3 point 3 `:559-561`) [SRC/DOC]. Should the new field's text say which boundaries no longer refuse? [INF]
7. **Duplicate constant**: tool #2 keeps its own copy of the fragment (`judge_held_into_refusal.py:136-140`) while #4 imports #1's. If the value or key changes, #2 can drift [SRC + INF].

### 2(d) Layers that change and hash bindings touched

| Layer | Change | Binding |
|---|---|---|
| Engine | none for the field itself (C already compiled under the define) | none; but the batch relinks anyway |
| Builder `tools/build_e2_editor_v4_profile.py` (or a successor if ABI moves, `:81`) | new flag + refusal + leaf | builder file is a Makefile prerequisite of the manifest (`Makefile:1582-1589`); finding 042: a Makefile/prereq change re-links dependants → owner's step |
| Manifest | new leaf | X1 `--declared-new-leaf`; host `buildId` changes (package includes `profiles/<p>/sdk-manifest.json`) |
| Tools (4) + tests | read field, cross-check bytes | merge runner sha256 is recorded in reports (`"runner"`, `run_merge_wasm_shakedown.py` report) and `judge_counted_m2.py`'s `thisRunner` clause requires report runner == live file (`findings/evidence/link-batch/v20-shakedown/merge/re-expectation/README.md:55`); V19Witness tests re-derive the runner and `BINDING` from git (`SPEC-M3-link-batch.md:541`); §34.1 freeze window applies from `BINDING` until the count's read |
| Worker / SDK / shell / page | none unless product consumes the field (open Q4) | if consumed: worker pin, shell generation |
| Host | none beyond the new package | re-pins as §17.1 |

### 2(e) Existing tests/criteria/evidence, and what would show it works

Existing [SRC/DOC]:
- `tests/test_merge_wasm_clauses.py:220` (expectation under C), `:236-246` (synthetic with/without fragment; **real** `e2-editor-v19` false, `e2-editor-v20` true), `:282` (red: a refusal on a C profile).
- `tests/test_judge_counted_m2.py:47-48` (FAKE_WASM_C), `:549-553`, `:861-872` (keying mocked false).
- Production UI: C-branch red cases 6/6 and the re-score of 34 reports (`SPEC-M3-link-batch.md:555`, evidence `findings/evidence/m3-production-ui/witness-c-0.2.23/rejudge-under-c.txt`).
- Held judge red cases R1–R5 incl. "a manifest over another wasm" (`findings/evidence/link-batch/host-0.2.20/re-expectation/README.md:93-98`).
- 10-14i red cases R1–R4 (`v20-shakedown/merge/re-expectation/README.md:46-49`).
- This task's byte count [BYTES]: fragment ×0 in v19 `1aafd4f9…`, ×1 in v20 `313b08d5…`.

What would show the field works [INF, draft]:
1. Builder unit tests mirroring `test_e2_editor_v4_profile.py:150-199`: declared on a C artifact → leaf present; asked on a non-C artifact (v19's wasm) → refused.
2. X1 run on v21 vs v20 with `--declared-new-leaf .editorContract.<C>=<value>`; and red: the leaf missing / wrong value.
3. Tool cross-check table, each a red case: (field, fragment) = (yes, yes) → C; (no, no) → refusal; (yes, no) → STOP; (no, yes) on v20 → the chosen legacy rule; (no, yes) on v21 → STOP.
4. Re-judge every committed report that the four tools have judged (as 10-14i and 10-15 did): verdicts byte-identical.

### 2(f) Interactions

- **"Immediate answer at document start/end without the 2 s window"** [DOC] finding 141 ruling (3) `findings/141-a-held-backspace-at-a-c-boundary-queues-silent-no-ops.md:28`; `handoff/RELEASE-TEXT-DRAFT-0.2.13-0.2.23.md:190`. This changes C's timing, so:
  - §17.4's manual positive control (≥ 2,000 ms busy with unchanged `rev`, `SPEC-M3-link-batch.md:563-567`) would read NOT_ESTABLISHED on every run by construction [INF]; a new positive control is needed.
  - The byte keying cannot tell window-C from immediate-C if the completion string stays the same [INF]; the manifest value could (open Q1).
  - L-C-late-K1 / L-C-number-or-indent (`§10.5`, `§15.1`) exist because the engine waits for K1; an immediate answer must decide "document boundary" before or without K1 — the spec text for that does not exist yet [INF].
  - The release text's 「約 2.25 秒」 and held-key tail statements become stale [DOC] `RELEASE-TEXT-DRAFT…:190`.
- **142 `move-document-start/end`** [DOC] `findings/142-ctrl-home-does-not-move-the-caret.md:15`: its red case is "`press-after-ctrl-home` 臂必須讀成邊界 no-op" — i.e. it depends on C; two new actions also move the editor action bounds (`editor_api.cpp:65`, `probe_engine.cpp:7069`) and probably `abiVersion`, which X1 has no flag to declare as a changed leaf (`check_profile_identity.py:13, 94-95`) and the builder hard-codes (`build_e2_editor_v4_profile.py:81`) [SRC + INF].
- **handleEditorPlaceCaret on TEXT_SELECTION (140 second pass)** [DOC] 10-14b `:27`: no semantic overlap with C [INF].
- **Markdown paste**: if it is declared like `pageRectangles`, it uses the same builder-flag / X1-declared-leaf / gate pattern as the C field; both new leaves go into one X1 invocation (the flag is repeatable, `check_profile_identity.py:24-28`) [SRC + INF].

---

## Cross-item and batch summary

| Batch item | Engine relink | Editor ABI | New manifest leaf | Worker | Shell gen | Tools/judges re-expect |
|---|---|---|---|---|---|---|
| Markdown paste (A) | yes | no if a document export; yes if an action | yes if gated like `pageRectangles` | yes | yes | product-path Ctrl+V arm; new judge |
| C manifest field | no (field only) | no | yes | no | no unless product consumes | 4 tools + tests (procedure open, §34.4) |
| Immediate boundary answer | yes | no [INF] | via the C field's value [INF] | maybe (`waitedMs`) | maybe | §17.4 positive control, held/merge/prod-UI arms, release text |
| 142 move-document-start/end | yes | yes [INF] | yes (actions) | yes | yes (page keys) | `press-after-ctrl-home`, inventory/reachability tests |
| placeCaret on TEXT_SELECTION | yes | no | no | no [INF] | no [INF] | 140's arms |
| `Language=` (+031, D12) | yes | no | no [INF] | maybe | maybe | new-document N-checks (`check_m3_new_document.py`) |

Shared consequences of any link in this batch [DOC/SRC]: new profile identity (v21), archive the current profile first (`handoff/HANDOFF-2026-10-16…:105`), the owner runs every compiling `make`, the v20 `.o` files are already stale so `make -n` will show recompiles (`:105`), X1 with declared deltas, M1-1, a new shell generation for any page/SDK/client change (v73 is current), new host version and the §17.1-style re-pins, merge runner `BINDING`, and a full count chain (owner window, overnight).
