# REVIEW 2026-10-20 (fable, adversarial, read-only): 「Nextcloud 裡點 .ods 就能開」計畫

Reviewed: `handoff/PLAN-2026-10-20-nextcloud-opens-ods.md` at `3e2d89c5`. Nothing was run, linked, installed or written; every line cited below was read in the source named. Inferences are marked.

---

## §1 給擁有者（白話）

**結論：計畫成立，但要先改幾處再連結。** 方向（第二顆唯讀引擎、ODT 編輯器一個位元組都不動、宿主加一條檢視路由）是對的；問題出在「引擎底座」跟「打包／宿主」兩段，計畫寫的東西跟原始碼對不上。這些全是**讀程式碼就查得出來**的，不用等你連結之後才發現。

**最重要的三件事：**

1. **計畫選的引擎底座（唯讀 reader 規則）缺它自己的驗收要用的兩樣東西。**
   - E3 要「把每一張工作表的文字讀出來跟答案比」——但 reader 規則**沒有讀文字的出口**（`get_selection` 整段被 `#ifndef OXSDK_READER_PROFILE` 關掉，匯出清單也沒有）。照 E3 自己寫的預設，「沒量到＝停」，所以每一次連結都會在 E3 停住。
   - E4 要「第二次畫圖時 `documentSizeChanged == false`」，而且檢視頁要靠畫圖回報的尺寸來修那 12 px 沒畫到的邊——但這三個欄位只在編輯器的 define 底下才會送出，reader 規則沒有。檢視頁拿到的會是空值，修不了邊，E4 也判不了。
   - 處方：W7 多加兩小項（一個「讀第 k 張表文字」的出口、畫圖回覆帶尺寸），各自先寫紅案。D2 的「只加 W7、其餘不動」要改成「W7 加這兩項」。

2. **第二顆引擎的下載量不是 36 MB，是約 55 MB。** Calc 核心的資料包（base pack，40 MB 原始）跟現在出貨的那份不是同一份，一定要另外帶；而且 E8 釘的是 v14 的包，等於釘到**舊的、沒瘦身的 CJK 字型包**（zstd 12.2 MB），現在編輯器出貨的是瘦身版（5.7 MB）。改 E8 釘「這顆核心切出來的 base 包＋現在出貨的 `cjk-sub-e10`」，可省約 6.5 MB、少一個檔，字型包還能跟編輯器共用快取。

3. **宿主跟打包那一段，照現在的草稿頁會直接失敗。**
   - 宿主把頁面包進 Nextcloud 的那段程式要求樣式裡 `:root {` 只出現一次；草稿頁出現兩次（深色模式那段）→ 回 500。
   - 打包工具只認**一個**頁面、**一個**寫死的 `workerUrl: "./…"` 字串；草稿頁的 workerUrl 是從網址參數組出來的 → 打包工具直接報錯。MANIFEST 的 `profile`、`wasmSha256` 也都是單數欄位。
   - 這些改計畫文字跟草稿頁就能排掉，但要寫進 O6，而且 H4「既有宿主臂全部照過」對資產那一臂不會字面成立（它自己會重算閉包），要重判並寫理由。

**另外兩個要你選的：**

- **D3（檢視頁的 SDK 模組）** `document-sdk.js` 的 `DocumentEngine` 可以直接用子類別延伸（它有通用的 `_request`），不用複製一份、也不用重綁殼層。
  - A：子類別（我建議；零位元組改到綁定的檔案，沒有兩份協定要守）
  - B：照計畫複製一份＋比對原始碼的守衛測試（守衛守的是錯的那一對，見 §2 C5）
  - C：改 `document-sdk.js`、殼層升 v76、編輯器重綁
- **D5（gzip 上限）**「zstd 上限 × 1.4」不是量出來的數字，它剛好放得下手上這顆 wasm而已。
  - A：量一次——Firefox 對 48 MB 的 gzip 檔留不留快取（一次瀏覽器量測，主 session 自己能做，不用 ddev）
  - B：gzip 不設上限，改登錄成已知限制（Firefox 關掉 zstd 那一臂明寫「不在檢視頁上跑」）
  - 我傾向 A。

**便宜的第一步（不用連結、不用 ddev）：** 用已經連好的 `e2-editor-v14`（同一顆 Calc 核心）＋ 089 那支改堆疊常數的工具（調到 1 MiB），走草稿頁自己的開檔路，開 `tdf149752.ods`、三張表、10 萬格——E2 的開檔／分頁數、E6 的記憶體、089 在 1 MiB 上的結果就有了。它量不到「reader 物件集在這顆核心上開不開得了」，那一題只有連結能答，所以連結後第一件事就是 E2。

---

## §2 Findings (English)

Severity: **blocks** = a criterion cannot be satisfied as the plan stands; **changes the plan** = a section must be rewritten before O1; **minor** = precision or a registered cost.

### B1 — blocks — D2's base has no text read-back, so E3 is unmeasurable by construction
- **Attacks:** D2 ("the read-only R5 rule shape … adding W7 and nothing else") and E3 ("`set_part(k)` + SelectAll + `getTextSelection` equals the manifest text").
- **Evidence:** `wasm_sdk_probe/src/sdk_api.cpp:159-242` wraps `oxsdk_document_get_selection` (and replace/undo/redo/comments/track-changes) in `#ifndef OXSDK_READER_PROFILE`; `:44-47` the reader's `oxsdk_capabilities()` returns OPEN_ODT|RGBA_TILE|SAVE_ODT|CANCEL_QUEUED|SEARCH, no SELECTION_TEXT; `wasm_sdk_probe/Makefile:825-840` the `writer-reader` export list has no `_oxsdk_document_get_selection`; `sdk/sdk-worker.js:30` gates `getSelection` on `"selection-text"`; `tools/build_r5_profiles.py:36-42` `READER_CAPABILITIES` lists no `selection-text`. SelectAll in the editor is an action under `OXSDK_EDITOR_DISCOVERY` (`probe_engine.cpp:44, 79, 216 …`), which D2 explicitly excludes.
- **Consequence:** E3's own default is "fidelity unmeasured; stop". Every link of the viewer as specified stops at E3. 09-03's G3 was written for an *editor* relink (`e2-editor-v13`), where `getSelection` existed; the plan inherited the criterion and changed the recipe without changing the criterion.
- **Fix:** add to `OXSDK_ODS_VIEWER` one read-back export, e.g. `oxsdk_document_part_text(handle, k)` → engine thread does setPart(k), `.uno:SelectAll`, `getTextSelection("text/plain")`, deselect, replies the text; no selection state reaches the page; a capability string `part-text`; red case: the export absent → E3 red, not vacuous. Rewrite D2 to "W7 plus the one read-back E3 needs" and say why.

### B2 — blocks (for E4) / changes the plan (viewer refit) — the tile reply carries no size on the reader base
- **Attacks:** E4 ("`documentSizeChanged == false` on the second paint after the viewer's refit") and §1 "it does not refit after the first paint's `documentSizeChanged`".
- **Evidence:** `probe_engine.cpp:3211-3224` emits `documentWidthTwips/documentHeightTwips/documentSizeChanged` only under `#ifdef OXSDK_E2_FORMAT_BARRIER`, `#else (void)documentSizeChanged`; the reader rule (`Makefile:623-624`) defines only `OXSDK_READER_PROFILE`; the worker forwards the fields as they are (`sdk-worker.js:836-838`), so they arrive `undefined`; `sdk/document-sdk.js:516-519` updates the handle's size only when the field is a number; the viewer records `documentSizeChanged ?? null` (`web/ods-viewer-app.js:195-197`). Separately, the engine updates its remembered size on every paint (`probe_engine.cpp:3204-3205`), so the second paint says `false` whether or not the page refits.
- **Consequence:** on D2's engine E4 compares `null` to `false` (red or vacuous depending on the comparator), the viewer has no input for the refit the plan requires, and the "after the viewer's refit" clause measures the engine's bookkeeping, not the refit.
- **Fix:** (a) `OXSDK_ODS_VIEWER` also enables the three tile fields (same `#if defined(OXSDK_E2_FORMAT_BARRIER) || defined(OXSDK_ODS_VIEWER)`); (b) split E4: engine half as written; page half as a page-side observable — after the first paint the surface's CSS size equals `documentCssSize` from the post-paint `widthTwips`, and a tile whose span covers `x = widthPx − 1` was drawn; the current draft is the red case (it reproduces the 12 px gap).

### C1 — changes the plan — the second engine costs ~55 MB zstd, not ~36, and E8 pins the wrong packs
- **Attacks:** D1 "about 36 MB zstd", L-ods-second-engine-download, E8 "packs byte-identical to v14's".
- **Evidence:** installed `engine/MANIFEST.json` (buildId `817413d5ad5bd502`, profile `e2-editor-v22`): base pack `profiles/resources/base-r5-no35.65e8acbb….data` 34,129,451 B / zstd 5,529,810; CJK `cjk-sub-e10.06976180….data` 14,384,632 B / zstd 5,748,639. `dist/profiles/e2-editor-v14/`: `base-e2-editor-v14.9901e9be….data` 39,940,977 B; `cjk-e2-editor-v14.b76b0433….data` 19,484,784 B (= `cjk-r5.b76b0433…`, zstd 12,170,785 per `findings/evidence/m3-zstd/offline-sizes-2026-09-30.json`); wasm 135,237,060 B / zstd 36,078,637 (SPEC-M3-zstd §1). `Makefile:2455` asserts `9901e9be29c9ded2` is the a11y core's slice ("the base pack hash says WHICH core image was sliced"). `dist/profiles/e2-editor-v22/sdk-manifest.json` uses `base-r5-no35` + `cjk-sub-e10`; v14's uses the pre-subsetting packs.
- **Consequence:** the viewer cannot share the editor's base pack (different core image) — unavoidable, ~6.5 MB zstd (inference: base-r5 packs at 16.2%; v14's base not measured). E8 as written also forces the old 12.2 MB CJK pack where the shipping 5.7 MB `cjk-sub-e10` is core-independent (fonts). As written: 36.1 + ~6.5 + 12.2 ≈ 55 MB on first `.ods`. With `cjk-sub-e10` shared: ~42.6 MB new bytes, one fewer file, and the CJK pack already cached after any ODT open.
- **Fix:** E8 → "base pack sliced from `build-a11y-gate0` (hash `9901e9be…`), CJK pack = the shipping `cjk-sub-e10` bytes (one file in the package), `fallback-fonts` as today (declared, not loaded)". Also O3 must name the builder: `build_r5_profiles.py` takes one core's `--data/--metadata` and emits reader capabilities (`:277-287`, `:36-42`); the a11y-core slicing lives in `build_e2_editor_v5_profile.py` with an editor contract (`Makefile:2552-2553`). No existing tool does "reader shape + a11y slice" (inference from the Makefile; I did not read the v5 builder's body).

### C2 — changes the plan — the host's re-wrap refuses the draft page (§6 Q6)
- **Attacks:** D4 "a viewer route, which re-wraps `ods-viewer.html` the way `editor()` re-wraps the editor".
- **Evidence:** `app/lib/Controller/EditorController.php:197-212` `scopedStyle()` returns null unless `:root {` and `body {` each occur exactly once; `web/ods-viewer.html:8-9` has `:root { … }` and `@media (prefers-color-scheme: dark) { :root { … } }` → two → `editor()` answers 500 "the shipped page's style no longer has the shape this app scopes" (`:155-158`). `PRODUCT_SCRIPT` (`:55`) and the `substr_count === 1` check (`:152`) are editor constants; `asset()` hard-codes `e2-editor.html` at `:110-111, :120-121, :127-128` (old-address redirect only for the editor). `templates/editor.php:36-51` hides editor-specific selectors; the viewer's draft chrome (`ods-viewer.html:34-35` h1/`<p>` "草稿", `:39` file input, `:45-51` diagnostic status fields, `:24` `#viewport{height:60vh}`) has no equivalent and would show under Nextcloud's header in H7.
- **Fix:** viewer page keeps one `:root` rule (`light-dark()` or drop the override); `asset()` gets a page table `{page → script constant, resolver mime, template}`; a `templates/viewer.php` that hides the dev input and draft chrome; red case: a page with two `:root` → 500 (so the refusal is proven live, not inferred).

### C3 — changes the plan — the packager accepts one page, one worker literal, one profile
- **Attacks:** D5 "the closure becomes the union … each from its own static graph and its own `workerUrl`"; H4 "existing host arms for 0.2.28 pass on 0.2.29 as they did".
- **Evidence:** `tools/probe_m3_assets.py:56` `PAGE_MODULE = "e2-editor-app.js"` (module constant), `:59` `WORKER_URL` regex requires `workerUrl: "./…"` double-quoted, `:130-132` raises unless exactly one match; `web/ods-viewer-app.js:17-19, 82` builds `workerUrl` as a template literal from `?profile=` (zero matches → RuntimeError; in the host a user-selectable profile path, 404 by the manifest but silently the wrong default `e2-editor-v14`). `tools/package_m3_engine.py:149-151` `source.page`, `source.profile`, `wasmSha256 = next(… endswith("/probe.wasm"))` are singletons (two wasm → the first in sorted order, no error). `tools/check_m3_assets.py:137` recomputes `closure(DIST)` for K0; `:100` pins schema `litecore-engine/2`; the controller checks the same string (`EditorController.php:341`).
- **Consequence:** D5 touches the packager, the manifest schema (→ `/3`), the controller's `engine()`, `check_m3_assets.py` (K0/Z0-1) and the release tools; H4 cannot be literally true for the assets arm — K0 must be re-judged with the reason written. O6 must also stage `web/ods-viewer*`, `viewer-shell/` and `dist/profiles/ods-viewer-v1/` into `dist/` (the packager reads `DIST`, `package_m3_engine.py:115-123`; `dist/viewer-shell/` does not exist today). New files only; `served_shell_identity()` hashes the 13 bundle paths in dist (`tools/run_e2_c_product_path.py:2649-2655`), so E7 is unaffected.
- **Fix:** `PAGES = {"e2-editor.html": "e2-editor-app.js", "ods-viewer.html": "ods-viewer-app.js"}`; manifest `source.pages: {page: {module, profile, wasmSha256}}`, schema `litecore-engine/3`; the viewer hard-codes `workerUrl: "./profiles/ods-viewer-v1/sdk-worker.js"` and drops `?profile=`; red cases: zero/two worker literals, a one-page manifest under schema 3.

### C4 — changes the plan — the gzip re-judgement is a fit, and two populations still get gzip
- **Attacks:** D5 "lift the cap for gzip to ≤ the zstd cap × 1.4"; "K0-5's basis, Firefox's cache, no longer applies to it".
- **Evidence:** `package_m3_engine.py:43-47`: the measured points are 45 MB kept, 60 MB not; 48.0 MB (v14 gzip, SPEC-M3-zstd §1) is inside the unmeasured interval. SPEC-M3-zstd Z2-2 (`specs/SPEC-M3-zstd.md:159-162`) keeps a `firefox-nozstd` arm on which K2 "second open does not refetch" must hold, justified by "40.9 MB gzip wasm is within Firefox's retention"; §5 (`:94, :201`) Safari's zstd support is unverified. The 1.4 is the ratio of this one artefact (`47,987,197 / 36,078,637`), not a browser measurement.
- **Consequence:** "× 1.4" admits exactly the wasm at hand and reads as a rule. The nozstd arm would be red on the viewer wasm if it were run; the plan does not say whether it is run.
- **Fix:** A) measure once (X1 instrument: serve a 48 MB gzip file, Firefox warm profile, two opens, count the second fetch) and set the gzip cap to the measured retention — that is re-judging with the recipe; B) drop the gzip cap as a criterion, register `L-ods-gzip-fallback-uncached-in-firefox-nozstd`, and write that Z2-2 is not run on the viewer page and why (default Firefox takes zstd; logout clears the cache anyway, §5). Never write "× 1.4".

### C5 — changes the plan — D3's duplication is unnecessary; subclass the shipped SDK
- **Attacks:** D3 ("a separate module that speaks the same worker protocol … the duplication is the price, and it is guarded: a test asserts that the shared message shapes match `document-sdk.js`'s, read from the source").
- **Evidence:** `sdk/document-sdk.js:154` `export class DocumentEngine` with a generic `_request(operation, payload, options, transfer)` (`:236-313`); `:418-432` `open()` returns `new DocumentHandle(this, this._generation, result)`; `:466` `export class DocumentHandle`. The W9 page already imports the shipped module (`web/ods-viewer-app.js:13`) and already relies on the underscore method `_initialize()` (`:86`). The bundle scope is the five directories (`tools/build_e2_c_shell_bundle.py:835-841`); `viewer-shell/` is outside, and `e2/editor-shell-v2-bundle-v75.json` hashes exactly 13 paths.
- **Consequence:** a `viewer-shell/ods-document-sdk.js` that does `class OdsViewerEngine extends DocumentEngine` and decorates the handle with `setPart/partName/currentPart/documentType` via `this._request(...)` changes zero bytes under `sdk/`, mints no shell generation, and has one protocol, not two. The plan's source-shape guard is a substring assertion (the kind CLAUDE.md records as "值這麼多"), and it guards the wrong pair: the drift that matters is SDK ↔ *its own* worker, and the viewer's worker is new (W7). The guards that exist already cover that pair: the worker's reply allowlist, the W9 unit test with a fake worker (18/18, 27 mutations), and E5/E9 on the real worker.
- **Fix:** option A in §1; register the `_request`/`_initialize` coupling as a named dependency on the shipped module's private surface (it exists today).

### C6 — changes the plan — E2's "typed refusal" for encrypted files is the generic LOK_ERROR (vacuous)
- **Attacks:** E2 "Encrypted files are `expect: "refused"` with a typed refusal".
- **Evidence:** `findings/evidence/m4-ods/04-sweep-v12.json` cases `password.ods`, `passwordOld.ods`, `passwordWrongSHA.ods`: `error.code "LOK_ERROR"`, message "loadComponentFromURL returned an empty reference", 870–937 ms — the same code and message every unloadable file gets (`probe_engine.cpp:3019-3022`). 09-03 G2 required "a typed refusal **before the engine queue**"; E2 dropped that clause. `test-docs/ods/manifest.json` has exactly those three entries with `expect: "refused"`.
- **Consequence:** a truncated zip satisfies E2's refused clause as well as an encrypted file does; the clause distinguishes nothing.
- **Fix:** restore G2's wording and detect encryption before the engine (read `META-INF/manifest.xml` for `manifest:encryption-data` from the zip central directory in the viewer SDK/session; refuse `ENCRYPTED_DOCUMENT`; the W9 session already has the typed-refusal shape) — or lower the claim honestly ("the engine fails typed within N s and the worker stays healthy; the next open succeeds") and say the control cannot separate the two causes.

### M1 — minor — the name spoof moves one layer down
`probe_engine.cpp:2951-2954` `writeInputFile` always writes `/tmp/oxsdk-input-<id>.odt`; W7's `.ods` acceptance at `sdk_api.cpp:77` leaves `documentLoad` seeing a `.odt` URL. Content detection carries it (W2), but E2's "under its real `.ods` name" is true only at the ABI boundary. Fix: derive the suffix from the accepted name (one line) or say what E2 measures. Also §1 says `getParts` is read "at open only (`:3076`)" — a second read is at `:4301` (page rectangles, v20 define, not in the reader); and `Makefile:2298-2317` is v13's link, v14's is `:2508-2527`; `e2-editor-app.js:53-59` is the comment, the read is `:60`.

### M2 — minor — what the reader base keeps that a viewer should not
`_oxsdk_document_save` is in the reader export list (`Makefile:834`) and `save-odt` in its capabilities (`sdk_api.cpp:45-46`, `build_r5_profiles.py:36-42`): a read-only viewer in a host with no `save` ships a dark save, and `save("odt")` on a Calc document is untested. `refreshEditorAccessibility()` runs unconditionally at open (`probe_engine.cpp:3066`) and on this core accessibility is compiled in (`wasm-lite/build-a11y-gate0/config_host.mk:256`), so a viewer that never reads a11y switches it on for a Calc view (W2/W5 measured with it on — cost covered; behaviour unneeded). Fix: drop save from the viewer's exports and bits (the worker's `expectedCapabilityBits` guard at `sdk-worker.js:792-795` forces manifest and engine to agree); register the a11y switch, not gated. Also W7's worker half is larger than D2 lists: each of `set_part`/`part_name`/`current_part` needs an `OPERATION_CAPABILITIES` entry (`sdk-worker.js:24-55`; an unlisted operation is refused at `:1339`) and a reply `case`, not only `documentType` in the `opened` allowlist.

### M3 — minor — Files action id and the built script
`@nextcloud/files` 4.1.0 `dist/index.mjs` `registerFileAction`: a duplicate `id` logs `FileAction ${id} already registered` and returns (second action silently dropped). The second action needs its own id — or one action whose `enabled` accepts both mimes and whose `exec` picks the route by `nodes[0].mime` (simpler; same `order`/`default` semantics). `js/litecore-files.mjs` is an esbuild product of `src/files.js` (`app/package.json` `build`), so O6 must rebuild and commit it; the version bump (0.2.29) covers `?v=`.

### M4 — minor — H2's positive control and the right log
The same run must include an ODT editor open in the same Apache log (LOCK at open: `app/js/litecore-editor.js:233-236`; UNLOCK at leave: `:305-309`), so "no LOCK/PUT/MOVE/PROPPATCH in the viewer's window" can be red. The log is the container's Apache `access.log` (2xx are not in the router's log — memory note; `probe_m3_assets.py:185-204` already reads it that way). Red case: a viewer host script that calls `takeLock()` (the editor's `load()` locks before GET, `:416-417`) → H2 red.

### M5 — minor — H6 conflates two policies
The editor *page* route's CSP is Nextcloud's `ContentSecurityPolicy` + `allowEvalWasm` (`EditorController.php:178-182`); `'self'` script/worker sources are the *engine file* policy (`SERVE_POLICY`, `:80`). Fix: "the viewer page's COOP/COEP/CSP equal the editor page's in the same run modulo nonce" (editor page = positive control); engine files under the shared address go through the same `serve()`, no new clause.

### M6 — minor — what moves on the ODT side anyway
Adding files changes `buildId` (`package_m3_engine.py:109-112`) → the address moves → every warm browser re-downloads the editor's ~42 MB zstd once (SPEC-M3-zstd §3.2 calls this by design) — register it. `src/files.js`, `EditorController.php` are shared code; H1/H4 cover them. The assets arm's K0 closure: C3.

### M7 — minor — the 089 risk is overstated
089's measurement patched the literal `65536` that `-sDEFAULT_PTHREAD_STACK_SIZE` emits into `probe.js` (`findings/089-…md`, ruling section: "預設值以字面量傳給 `__emscripten_thread_init(…,65536,false)`"), on v12 = the a11y-gate0 core, and v22 then carried the flag as a link (C1 PASS). "Not measured: a calc-core link carrying 1 MiB" should read "measured via the loader literal on this core; unmeasured residual = the reader object set on this core". Not a defect; the register should say what it means.

### M8 — minor — E6's leak bound is inherited from another artefact
"The leak bound comes from W1's noise floor" — W1 measured v12's boot. The viewer link is a different artefact (reader objects, 1 MiB × `PTHREAD_POOL_SIZE=7`); the floor must be re-measured on the viewer link (5 boots) before any E6 run counts, or the bound signs for one artefact with another's number.

---

## §3 Answers to the plan's §6 questions

1. **D1, two engines.** Yes. With v23 paused on the writer core and the one-variable rule, moving the editor is the wrong link. The honest cost is ~55 MB zstd (C1; ~43 MB if `cjk-sub-e10` is shared), plus one editor re-download per warm browser (M6). What is shared and moves: the package address, `litecore-files.mjs`, the controller, and the assets arm's K0 closure (C3). The editor profile's bytes and shell v75 do not move; E7 proves it.

2. **D2, the reader base.** Sound for open/paint/close: `view-ready` is emitted outside every editor `#ifdef` (`probe_engine.cpp:2740-2751`, preprocessor depth 0 — checked), and W2 saw it fire on Calc. Too minimal for the plan's own criteria: no text read-back (B1), no tile size fields (B2). Keeps what it should not: save, a11y-on (M2). "W7 and nothing else" → "W7 + part text + tile size fields", each with a red case.

3. **D3.** Not needed (C5): subclass the shipped `DocumentEngine` from `viewer-shell/`. The source-shape guard is a substring assertion guarding the wrong pair; the existing guards (worker allowlist, fake-worker unit test, E5/E9) are the right ones.

4. **D5.** Not honest as written (C4). "K0-5's basis no longer applies to gzip" is true for default Chrome/Firefox and false for `firefox-nozstd`; Safari is unverified. A: measure 48 MB once; B: registered limit, arm declared not run on the viewer. No "× 1.4".

5. **§3 criteria audit.**
   - E1: form 2, fine; keep 09-03's injection #6 (empty directory is red).
   - E2: refused clause vacuous (C6); "real `.ods` name" only at the ABI (M1); add the negative control for `documentType`: an ODT through the viewer → `DOCUMENT_TYPE_REFUSED` (W9 test M06 shape).
   - E3: unmeasurable on D2 (B1).
   - E4: undefined on D2, and the refit clause measures the engine, not the page (B2). The same-run controls are good.
   - E5: fine; add "ask for the current part again → read-back unchanged" and the out-of-range refusal (W9 M22).
   - E6: re-measure the floor on the viewer link (M8); 1 MiB × 7 threads is +7 MiB, negligible under 896 MiB.
   - E7: form 2, holds (`served_shell_identity()` hashes the 13 paths; new files beside them do not move it).
   - E8: pins the wrong packs (C1).
   - E9: fine on the mirror; in the host the file input is hidden, H3 covers the host path.
   - H1: a sample, not "exactly": "offered for ODS and ODT; not offered for the two sampled other mimes"; the ODS row in the same listing is the positive control.
   - H2: needs the positive control and the container log (M4). The ETag/version-count check is the right state read.
   - H3: fine.
   - H4: not literal for the assets arm (C3); re-judge K0 with reason.
   - H5: good (red case over each cap); "gzip under D5's cap" depends on C4.
   - H6: wording (M5).
   - H7: fine; judgement half recorded.
   - "X did not happen" without a control: H2 (write), E2's refused class (typed), H1's "not offered" (has its control in the same listing).

6. **Host contradictions.** C2 (`scopedStyle`, editor-only constants, old-address redirect), C3 (packager/manifest/controller schema), M3 (action id). The `liteCoreHost` contract: the editor page reads it once at module evaluation (`web/e2-editor-app.js:60`) and SPEC-M3-host-entry §2.4 says "`load` without `save` → refuse to boot"; the viewer's `{ load }` is a *second* contract under the same global name — acceptable if the viewer page defines its own shape check, but name the fact (or use `liteCoreViewerHost`). The editor's `load()` locks before GET (`litecore-editor.js:416-417`); the viewer's script is new, so no inheritance, but H2's red case should prove it (M4). `Util::addScript('litecore-editor')` and the initial-state `editor.module` are editor-specific (`EditorController.php:159-172`); the viewer needs its own.

7. **Order.** See §4.

---

## §4 A cheaper first step

**Step 0 — today, no browser, no link.** Fold B1, B2, C2, C3, C6 into the plan (append-only) and into the draft page: hard-coded `workerUrl`, one `:root`, production chrome hidden, encryption detection in the session. All five were found by reading; left as they are, they would be found after the owner's link, at the price of a second link.

**Step 1 — a browser on a mirror, no link, no ddev.** Run the W9 draft page on `e2-editor-v14` (already linked on `build-a11y-gate0`) with 089's loader patch at 1,048,576 (the stack-arm tool; anchor `,!ENVIRONMENT_IS_WEB,65536,false);` exactly once), through the page's own file input, on `tdf149752.ods`, `three-sheets-distinct.ods`, `numeric-100k.ods`, and `password.ods`. This yields E2's open/`view-ready`/`parts`, E6's peak `sbrk`, 089 at 1 MiB on the calc core via the *page's* path, and the refusal shape C6 is about — and retires "089 on a calc-core link with 1 MiB: unmeasured" to "measured via the literal on this core". It does **not** measure the reader object set on this core; only the link does, so the link's first run is the W2 instrument and E2 stays first.

**Step 2 — offline/one browser, no link.** Decide C4 by measurement (Firefox retention at 48 MB) or by registration, before the packager is touched.

Then O1–O4 as planned, with D2/E3/E4/E8 rewritten, D3 as option A, and O6 extended by C2/C3/M3.

**Sequencing for the owner's "early result"** (no criterion changes): the first visible result is the viewer on a mirror page after O4 + E2 (the owner clicks the file input and sees sheets); the host integration (H) is the second. The plan's phases already allow this; say so in O5 so the owner knows when to look.

---

## The main session's spot check (appended 2026-10-20 ~19:10; not part of the review)

Re-read before the plan is amended:
- **B1:** `wasm_sdk_probe/src/sdk_api.cpp:159` opens `#ifndef OXSDK_READER_PROFILE` before `oxsdk_document_get_selection`, and the `writer-reader` export list (`Makefile:825-840`) has no selection export. As stated.
- **B2:** `probe_engine.cpp:3211` puts the tile reply's three size fields under `#ifdef OXSDK_E2_FORMAT_BARRIER`. As stated.
- **C2:** `web/ods-viewer.html:8-9` has two `:root {` rules, one inside the dark-mode `@media`. As stated.
- **C3:** `web/ods-viewer-app.js:82` builds `workerUrl` as a template literal from the profile. As stated.
- The rest (C1's pack sizes, C4–C6, M1–M8) were not re-read; they are carried into the plan's amendment as the review states them, each to be checked when its work item is done.
