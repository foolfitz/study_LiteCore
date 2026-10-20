# SPEC M4：Nextcloud 裡點 .ods 就能開（唯讀檢視）

> 2026-10-20 立。來源：計畫 `handoff/PLAN-2026-10-20-nextcloud-opens-ods.md`（`3e2d89c5`）、fable 的對抗性審查
> `handoff/REVIEW-2026-10-20-fable-ods-in-nextcloud.md` 與計畫的修正段（`5c89bc27`）。**本檔取代計畫正文與修正段裡的判準；
> 計畫留作來由。**
> 判準寫在任何會滿足它的執行之前（CLAUDE.md §9.1）。**本檔 commit 之後只准 append**：更正寫在後面並指名它取代什麼。
> 證據標記照 `doc-conventions`：**已觀察**＝量過或讀產物確認、**讀原始碼**＝沒量、**推論**。

## 0. 決定

- **擁有者的目標**（2026-10-20 約 18:45）：「Nextcloud 裡點 .ods 就能開」。同一晚擁有者選 A「試算表先做」，v23 暫停
  （`handoff/HANDOFF-2026-10-20e-…`），理由是「我主要想早點做出一個成果（可以開試算表）」。
- **「開」＝讀，不編輯。**沿用 09-03 的路線 B（另一顆唯讀檢視引擎，`handoff/PLAN-2026-09-03-ods-reading.md` §0）。
  編輯試算表是 M5，不在本檔。XLSX、ODP、ODG 不在本檔。
- **兩個待決事項，擁有者 2026-10-20 交代「待決事項皆依 fable 建議進行」：**
  - **D3＝A**：檢視頁的 SDK 用子類別延伸已出貨的 `DocumentEngine`（§3.3）。
  - **D5＝A**：量一次 Firefox 對 48 MB gzip 檔留不留快取，gzip 上限照量到的定（§3.5、§6）。量測若不成立（§6.4），退回 B。
- 從 10-20e 帶過來、本檔**不處理**：產品要不要改成「一顆 Calc 核心引擎同時開 ODT 與 ODS」（登錄在 §8）；L-C 的 A3。

## 1. 範圍：動什麼、不動什麼

**不動（逐位元）**：
- ODT 編輯器的 profile `e2-editor-v22`（wasm `f7a40bcc…`、worker `0d55bcfa…`）與它的五個綁定身分；
- 殼層 generation v75（`e2/editor-shell-v2-bundle-v75.json` 的 13 個路徑），**含 `sdk/document-sdk.js`**；
- 編輯器頁 `web/e2-editor.html`／`e2-editor-app.js`。

**動**：
- 引擎原始碼：新 define `OXSDK_ODS_VIEWER` 底下的東西（§3.2）。編輯器的 rule 不定義它，所以編輯器的物件不變（**推論**，O2 的紅案證明）。
- `sdk/sdk-worker.js`：W7 的 worker 那一半（§3.2）。這個檔**不在**殼層 bundle 的雜湊裡（v75 `excluded`：「bound separately …
  as workerSha256」，**已觀察**），每個 profile 帶自己的一份。改了它，凍結的 v21／v22 Makefile rule 的 `E2_V2x_WORKER_SHA256`
  檢查會在**重連結**時擋下來——那正是那道守衛的用途，不是副作用。
- 新檔：`viewer-shell/` 底下的模組、`web/ods-viewer{.html,-app.js}`、新 profile `ods-viewer-v1`、宿主的檢視路由。

## 2. 事實（每條附出處）

**核心**
- 出貨線 v8–v22 連的是 `wasm-lite/build-headless-probe`：`--with-wasm-module=writer`、`ENABLE_WASM_STRIP_CALC=TRUE`、
  沒有 a11y。v22 的 `probe.wasm` 裡 `ScDocShell` 出現 0 次。**它開不了試算表。**（**已觀察**，10-20e）
- `wasm-lite/build-a11y-gate0` 是 `writer calc`，Calc 與 a11y 都在。v9–v14 這條 a11y 候選線連的就是它。
  `e2-editor-v14/probe.wasm` 135,237,060 B，gzip -9 47,987,197 B，zstd -19 36,078,637 B（`specs/SPEC-M3-zstd.md` §1）。
- **ODS 在這顆核心上（診斷，檔名偽裝成 `.odt`，finding 013）**：W2 開得了、`parts == 3`、`view-ready` 會來；W5：十萬格
  `numeric-100k.ods` 在最後一個 open stage 的 `sbrk` 是 314,814,464（比 W1 的開機 290,066,432 多 23.6 MiB）；306 份語料開
  303 份，三份失敗都是加密檔；`tdf149752.ods` 是 finding 089（`findings/evidence/m4-ods/RESULT-W1…`、`RESULT-W5…`、`04-sweep-v12.json`）。
- **Finding 089**：開關是預設 64 KB 的 pthread 堆疊。在 v12（同一顆 a11y-gate0 核心）的鏡像裡改載入器字面量，256 KB、1 MB、
  8 MB 都 3/3 開得了（outcome O-S）。v22 起連結帶 1 MiB（`link_product_stack_1m`）。**已量**：經字面量、在這顆核心上；
  **沒量**：reader 物件集在這顆核心上、以連結帶 1 MiB（審查 M7）。

**引擎**（**讀原始碼**）
- `oxsdk_document_open` 拒絕檔名不以 `.odt` 結尾的請求（`src/sdk_api.cpp:77`）。
- `writeInputFile` 一律寫 `/tmp/oxsdk-input-<id>.odt`（`probe_engine.cpp:2951-2954`），所以只放寬 ABI 那一層，
  `documentLoad` 看到的仍是 `.odt`（審查 M1）。
- 引擎沒有 `setPart`／`getPartName`／`getDocumentType` 的匯出。
- reader 規則（`writer-reader`）：`oxsdk_document_get_selection` 整段在 `#ifndef OXSDK_READER_PROFILE` 裡（`sdk_api.cpp:159`），
  匯出清單沒有選取（`Makefile:825-840`）——**reader 底座沒有讀文字的出口**（審查 B1，主 session 抽查屬實）。
- 畫圖回覆的三個尺寸欄位只在 `#ifdef OXSDK_E2_FORMAT_BARRIER` 底下送出（`probe_engine.cpp:3211`，審查 B2，抽查屬實）。
- reader 規則的匯出與能力位元帶著 save（`Makefile:834`、`sdk_api.cpp:45-46`）；`refreshEditorAccessibility()` 在每次開檔
  無條件執行（`probe_engine.cpp:3066`），這顆核心編進了 a11y（審查 M2）。
- 能力位元用到 `1u << 10`（`src/sdk_api.h:30-40`）。

**worker 與 SDK**（**讀原始碼**）
- worker 的回覆是白名單：`opened` 只轉 `documentHandle/revision/parts/width/height/tileMode`（`sdk/sdk-worker.js:619-636`）；
  沒列在 `OPERATION_CAPABILITIES` 的操作一律拒絕（`:24-55`）。
- `sdk/document-sdk.js` 的 `DocumentEngine` 有通用的 `_request(operation, payload, options, transfer)`；`open()` 回
  `new DocumentHandle(this, this._generation, result)`（審查 C5）。

**資源包**（**已觀察**，2026-10-20 讀 metadata）
- `e2-editor-v22` 用 `../resources/base-r5-no35.65e8acbb…`、`cjk-sub-e10.06976180…`（loadAtStartup）、
  `fallback-fonts-r5.33856e2a…`（只宣告）。
- v14 的 base 包 `base-e2-editor-v14.9901e9be…`（39,940,977 B，1,489 個檔）＝`base-r5` 的 1,241 個檔**全部**再加 248 個 Calc 檔。
  **所以它帶著 `/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`**——finding 114 的成因（`zh-tw` 被子字串比對改寫成
  `tw`，中文排成拉丁行高）。編輯器從 v17 起用的 `base-r5-no35` 就是 `base-r5` 減掉這一個檔（`tools/build_base_no35_pack.py`）。
  **審查 C1 與計畫修正段的 E8 都釘 `9901e9be…`，照做會把 114 帶回檢視頁。**本檔 E8 改成「`9901e9be` 減掉那一個檔」（§3.2、§4）。
- `cjk-sub-e10` 只有一個檔 `/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E10.ttc`，與 a11y base 包的檔名不相交。

**宿主**（`~/Projects/Nextcloud_Apps/litecore`，已裝 0.2.28 `0870695`；**讀原始碼**）
- `scopedStyle()` 要求 `:root {` 與 `body {` 各恰好一次，否則 `editor()` 回 500（`EditorController.php:197-212`）；
  草稿頁有兩個 `:root`（審查 C2，抽查屬實）。
- 打包工具只認一個頁面、一個寫死的 `workerUrl: "./…"`（`tools/probe_m3_assets.py:56,59,130-132`）；草稿頁的 workerUrl 是
  從網址參數組出來的（審查 C3，抽查屬實）。
- 編輯器的 `load()` 先拿鎖再 GET（`js/litecore-editor.js:416-417`）。

## 3. 設計

### 3.1 兩顆引擎（D1，照計畫）

新 profile `ods-viewer-v1`，連在 `build-a11y-gate0` 上；ODT 編輯器一個位元組都不動。理由見計畫 D1（一次連結一個變因；v23
停在寫作核心的紅案上）。代價：第一次開 `.ods` 多下載約 43 MB zstd（§8 L-ods-second-engine-download）、package 帶兩顆 wasm、
兩條血統。

### 3.2 檢視引擎的內容（D2，依審查修正）

**底座**：reader 規則的形狀（`$(R5_CXXFLAGS) -DOXSDK_READER_PROFILE`，沒有 `OXSDK_EDITOR_DISCOVERY`），include 路徑用
**`E2_V5_CPPFLAGS`（a11y 核心）**，連結帶 `link_product_stack_1m`。`LOBUILD` 預設是寫作核心（`Makefile:2`），新 rule 一律明寫
`E2_V5_CORE`——這是 09-03 踩過的坑。

**新 define `OXSDK_ODS_VIEWER` 加的東西（每一項先寫紅案）**：

| 項 | 匯出／欄位 | 引擎執行緒上做什麼 | 回覆事件 | 能力字串（位元） |
| --- | --- | --- | --- | --- |
| W7a 開 `.ods` | `oxsdk_document_open` 在 define 下接受 `.ods` 與 `.odt` | 輸入檔副檔名**跟著**被接受的名字（M1） | `opened` 加 `documentType`、`inputSuffix` | `open-ods`（`1u << 11`） |
| W7b 文件型別 | — | `getDocumentType` 對到 `text`／`spreadsheet`／`presentation`／`drawing`／`other` | 在 `opened` 裡 | 同上 |
| W7c 切換工作表 | `oxsdk_document_set_part(req, handle, part)` | 界限檢查（越界回 `INVALID_ARGUMENT`，不碰 core）→ `setPart` → 讀回 `getPart` 與文件尺寸 | `part-set`：`part`（讀回）、`width`、`height`、`revision` | `part-switch`（`1u << 12`） |
| W7d 目前工作表 | `oxsdk_document_current_part(req, handle)` | `getPart` | `current-part`：`part` | 同上 |
| W7e 工作表名稱 | `oxsdk_document_part_name(req, handle, part)` | 界限檢查 → `getPartName` | `part-name`：`part`、`name` | 同上 |
| B1 讀第 k 張的文字 | `oxsdk_document_part_text(req, handle, part)` | 記下目前的 part → `setPart(k)` → `.uno:SelectAll` → `getTextSelection("text/plain")` → 取消選取 → `setPart(原本的)` | `part-text`：`part`、`text`、`partAfter`（讀回） | `part-text`（`1u << 13`） |
| B2 畫圖回覆帶尺寸 | `#if defined(OXSDK_E2_FORMAT_BARRIER) \|\| defined(OXSDK_ODS_VIEWER)` | 不變 | `tile` 的三個尺寸欄位 | — |

- **拿掉 save**（M2）：檢視 profile 的匯出清單沒有 `_oxsdk_document_save`，`oxsdk_capabilities()` 在 define 下不含
  `SAVE_ODT`，manifest 不列 `save-odt`。worker 的 `expectedCapabilityBits` 守衛（`sdk-worker.js:792-795`）強迫兩邊一致。
- **worker 那一半**（M2）：`OPERATION_CAPABILITIES` 加 `setPart`／`currentPart`／`partName` → `part-switch`、`partText` →
  `part-text`；四個回覆事件各一個 `case`；`opened` 白名單加 `documentType`、`inputSuffix`。`open`／`close` 仍掛在 `open-odt`
  （檢視引擎也開得了 ODT，由 session 以 `documentType` 拒絕，E2 的負對照就是它）。
- **`part_text` 不留副作用**：它結束時把 part 切回呼叫前的那一張，回覆帶 `partAfter`，E3 檢查 `partAfter` 等於呼叫前的
  `current_part`。選取狀態不回到頁面。
- **登錄、不設閘門**：開檔時的 a11y 開關（`refreshEditorAccessibility()`）在 Calc view 上照跑——W2／W5 是開著它量的，成本已含；
  行為用不到（M2）。

**資源包（E8 依 §2 的事實改寫）**：
- base：`9901e9be…` 的 1,489 個檔**減掉** `/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`，其餘逐位元相同。
  建法比照 `build_base_no35_pack.py`：從 `9901e9be` 的 data 切一次、從 a11y 核心的原始映像切一次，兩次 sha 要相同。
  **新工具，先寫紅案**（審查 C1：沒有現成工具做「reader 形狀＋a11y 切片」）。
- CJK：出貨中的 `cjk-sub-e10.06976180…`，package 裡與編輯器**同一個檔**（同一個路徑 → 同一個快取項）。
- `fallback-fonts-r5.33856e2a…`：照今天，只宣告不載入。

### 3.3 檢視頁的 SDK（D3＝A）

- `viewer-shell/ods-document-sdk.js`：`class OdsViewerEngine extends DocumentEngine`。`open()` 拿到 `DocumentHandle` 之後，
  用 `this._request(...)` 在 handle 上裝 `documentType`、`partNames`、`setPart(k)`、`currentPart`、`partText(k)`。
  `sdk/document-sdk.js` **零位元組改動**，不產生新的殼層 generation。
- 協定只有一份。守它的是既有的三道：worker 的回覆白名單、`tests/ods-viewer-session.test.mjs` 的假 worker、真 worker 上的
  E5／E9。計畫 D3 原本的「比對原始碼形狀」守衛**不寫**（審查 C5：子字串斷言、守錯的那一對）。
- **登錄的耦合**：`L-viewer-sdk-private-surface`——檢視頁依賴已出貨模組的底線成員 `_request`、`_initialize`、`_generation`
  與 `DocumentHandle` 的建構子。草稿頁今天就已經依賴 `_initialize`（`web/ods-viewer-app.js:86`）。`document-sdk.js` 哪天改了
  這幾個成員，E5／E9 會紅；不另寫守衛。

### 3.4 宿主（D4，依審查修正）

- **Files 動作**：**一個**動作，`enabled` 收 ODS 與 ODT 兩種 mime，`exec` 依 `nodes[0].mime` 選路由（M3：重複的 id 會被
  `@nextcloud/files` 默默丟掉）。`js/litecore-files.mjs` 重建並 commit。
- **路由**：`asset()` 改成頁面表（頁面 → 腳本常數、`resolve()` 接受的 mime、樣板）；`resolve()` 在檢視路由**只**收 ODS、
  在編輯器路由只收 ODT。新樣板 `templates/viewer.php`，藏起開發用的控制項（§5.1 的 `data-dev-only`）。
- **宿主契約**：檢視頁的宿主腳本 `js/litecore-viewer.js` 提供 `globalThis.liteCoreViewerHost = { load }`，**沒有 save、不拿鎖、
  不寫任何東西、不建版本**。名字與編輯器的 `liteCoreHost` 分開，檢視頁自己檢查它的形狀（帶 `save` 就拒絕啟動）。
- 宿主版本 **0.2.29**，未計數候選；計數鏈照舊併批（`release-count-batched`）。

### 3.5 打包與 K0-5（D5＝A）

- 打包工具改成頁面表 `PAGES = {"e2-editor.html": "e2-editor-app.js", "ods-viewer.html": "ods-viewer-app.js"}`，每頁從自己的
  靜態 import 圖與自己唯一的寫死 `workerUrl` 算閉包，聯集成 package。manifest 升 `litecore-engine/3`，
  `source.pages: {page: {module, profile, wasmSha256}}`。控制器的 `engine()`、`check_m3_assets.py`、發佈工具跟著改（C3）。
- 檢視頁寫死 `workerUrl: "./profiles/ods-viewer-v1/sdk-worker.js"`，**不再**讀 `?profile=`。
- **K0-5 重判**：zstd 上限維持 45,000,000（兩個瀏覽器都量過會留）；**gzip 上限照 §6 量到的數字定**，不寫「×1.4」。
  §6 若不成立，退回 D5-B：gzip 不設上限，登錄 `L-ods-gzip-fallback-uncached-in-firefox-nozstd`，並寫明 Z2-2（關掉 zstd 的
  Firefox 那一臂）不在檢視頁上跑。
- 打包 staging：`web/ods-viewer*`、`viewer-shell/`、`dist/profiles/ods-viewer-v1/` 進 `dist/`。只新增檔案；
  `served_shell_identity()` 雜湊的是 13 個 bundle 路徑，所以 E7 不受影響（C3）。

## 4. 驗收判準（釘在任何會滿足它的執行之前）

形式照 CLAUDE.md §1：1＝逐實例性質、2＝工具封閉的枚舉。每條附「如果永遠沒做」的預設結論（§2）。
真值源：`test-docs/ods/manifest.json`，由 `tools/create_ods_corpus.py` 從目錄內容生成（306 筆；`expect: "refused"` 三筆，
都是加密檔）。

### Phase E：檢視引擎，在鏡像上，不碰宿主

| id | 判準 | 形式 | 永遠沒做的預設結論 |
| --- | --- | :---: | --- |
| **E1** | 語料封閉：`test-docs/ods/` 下每個 `.ods` 在 manifest 有一筆且 sha256 相符；每筆都有檔；sweep 報告以 sha256 為鍵，每筆恰好一筆紀錄 | 2 | 沒有語料宣稱；Phase H 不開始 |
| **E2** | 開檔，**以真正的 `.ods` 名字**：每筆 `expect: "opens"`：`opened` 到、`view-ready` ≤ 60 s、`documentType == "spreadsheet"`、`parts == manifest.sheets`、`inputSuffix == ".ods"`、`nameSpoofed == false`，沒有 `LOK_ERROR`／`BUSY`／卡死；`tdf149752.ods`（089）在內。每筆 `expect: "refused"`：**引擎佇列之前**的型別化拒絕 `ENCRYPTED_DOCUMENT`，且這次開檔沒有建立引擎（session 的 `engineFactory` 沒被呼叫）。**負對照**（同一輪）：一份 ODT 經檢視頁 → `DOCUMENT_TYPE_REFUSED`，`documentType == "text"` | 1 | 沒有任何檔被證明開得了；停 |
| **E3** | 內容：每筆、每張表：`part_text(k)` 等於 manifest 的期望文字（inline 或它指名的原生 oracle 輸出），CRLF 正規化後逐位元相等；回覆的 `partAfter` 等於呼叫前讀回的 `current_part` | 1 | 保真度沒量；停。**這是空白畫布滿足不了的那一條** |
| **E4a** | 畫圖（引擎）：每筆、每張表：(0,0) 的 1024×1024 tile 回 OK；回覆的 `documentWidthTwips`／`documentHeightTwips` 是數字、`documentSizeChanged` 是布林；第二次畫同一塊時 `documentSizeChanged == false`；manifest 說那一區有內容的 tile 與同輪的空表對照**不**逐位元相等，說空的**相等** | 1 | 停 |
| **E4b** | 畫圖（頁面）：第一次畫完之後，surface 的 CSS 寬等於 `ceil(畫圖後的 documentWidthTwips / 15)`，且畫過一塊涵蓋 `x = 寬 − 1` 的 tile。**紅案**：今天的草稿（不重新量尺寸）重現那 12 px 的空白 | 1 | 停 |
| **E5** | 切換：`three-sheets-distinct.ods` 的 part 0/1/2 tile 兩兩不同；`three-sheets-identical.ods` 兩兩相同；`part_name` 清單等於 manifest 的名字；每次 `set_part(k)` 之後讀回的 `current_part == k`；`set_part(目前那張)` 讀回不變；`set_part(parts)` 被拒（型別化），讀回不變 | 1 | 停 |
| **E6** | 記憶體：每筆：開檔＋每張表一塊 tile＋關檔期間，所有 stage 行（含 `document-destroy-enter`）的 `sbrk` 最大值 < 939,524,096（896 MiB）。洩漏界限：同一筆開 5 次，第 n+1 次的 `open.begin` 減第 n 次，≤ B；**B 在任何 E6 執行算數之前，先由檢視連結自己開機 5 次的雜訊底定下**（M8），寫進本檔 append 段 | 1 | 不准帶著記憶體問題出貨；停 |
| **E7** | ODT 那邊位元組相同：`e2-editor-v22` 的五個綁定身分、殼層 v75 的 13 個路徑（`served_shell_identity()`）照舊；編輯器頁的閉包與 0.2.28 的相同 | 2 | 假設 ODT 不受影響；Phase H 不開始 |
| **E8** | 核心身分：base 包的檔案清單＝`9901e9be…` 的清單減掉恰好 `/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`，其餘每個檔逐位元等於 `9901e9be` 的；兩次切（data／原始映像）sha 相同；CJK 包是 `cjk-sub-e10.06976180…` 的位元組；`fallback-fonts-r5` 只宣告；`soffice.js.linkdeps` 是 `build-a11y-gate0` 的；`check_core_build_provides.py --capability calc-spreadsheet` 對它指名的核心通過 | 1 | profile 可能帶錯核心或帶回 114；停 |
| **E9** | 使用者的路，在鏡像頁上：經頁面自己的 file input 開 `three-sheets-distinct.ods`：`parts == 3`、三個 tab 的文字等於 `part_name`、`namesFromEngine == true`、點 tab k 讓**引擎的** current part 變成 k（讀回）、各自的第一塊 tile 是 E5 的那塊；`adapterFallbacks` 是空的 | 1 | 只量了 harness 的路；Phase H 可以開始，並記下這件事 |

E3、E4a、E5 用 1024×1024 的 tile 與同輪對照，**不**與原生比幾何（09-03 修正段：文件寬度只記錄不比較）。

**E6 的「peak」是什麼**：引擎只在開檔與關檔發 stage 行，畫圖時不發（`probe_engine.cpp` 的 `emitStage` 呼叫點，**讀原始碼**）。
`document-destroy-enter` 在每張表畫完之後，`sbrk` 不往回縮時它就是畫圖階段的上界；dlmalloc 若在中間把頂端還回去，短暫的峰值
會漏掉（**推論**，登錄，不另寫儀器）。

### 注入測試（在第一次綠之前先做出紅）

1. 加一個 `test-docs/ods/zzz.ods` 不重新生成 → **E1 紅**
2. 一份 ODT 走 ODS 的路 → **E2 紅**在 `documentType`（就是 E2 的負對照）
3. 把三張表那筆的 `sheets` 改成 1 → **E2 紅**
4. 對調兩張表的期望文字 → **E3 紅**
5. 拿掉 `part_text` 匯出（或能力字串）→ **E3 紅**，不是空洞的綠
6. sweep 指向空目錄 → **E1 紅**；「零個檔」必須是紅，不是「零個問題」
7. E4b 用今天的草稿頁 → **紅**（12 px）

### Phase H：宿主（擁有者的 ddev 時段）

| id | 判準 | 形式 | 永遠沒做的預設結論 |
| --- | --- | :---: | --- |
| **H1** | Files 動作依 mime：同一個清單裡 ODS、ODT、XLSX、PDF 各一份：ODS（檢視路由）與 ODT（編輯器路由）有 LiteCore 動作；抽樣的另兩種沒有。ODS 那一列就是正對照 | 1 | 入口沒量；不出貨 |
| **H2** | 點 ODS 會進檢視路由且帶那個 `fileId`；頁面報 `parts == manifest.sheets`、`documentType == "spreadsheet"`；**沒有任何寫入到伺服器**：該 session 的時間窗內，容器 Apache `access.log` 沒有 LOCK／PUT／MOVE／PROPPATCH，檔案的 ETag 與版本數不變。**正對照**（同一輪、同一份 log）：一次 ODT 編輯器開檔看得到 LOCK。**紅案**：一支會呼叫 `takeLock()` 的檢視宿主腳本 → H2 紅 | 1 | 唯讀只是假設；不出貨 |
| **H3** | E9 的 tab 讀回，經宿主頁 | 1 | 不出貨 |
| **H4** | 宿主裡的 ODT 不變：0.2.28 的宿主臂在 0.2.29 上照過；**資產臂的 K0 閉包重判**，理由寫明（多了檢視頁的閉包，C3）；E7 的身分在裝好的 package 裡成立 | 2 | 不出貨 |
| **H5** | 打包規則：每個檔 zstd ≤ 45,000,000、frame window ≤ 8 MiB；gzip ≤ §6 定的上限（§6 不成立時：無上限＋登錄 L-…）；manifest 是 `litecore-engine/3`、兩頁都在；紅案：各超過一個上限的合成檔、零個／兩個 worker 字面量、schema 3 底下只有一頁的 manifest | 1 | 不打包 |
| **H6** | 檢視頁的 COOP、COEP、CSP 等於同一輪編輯器頁的（nonce 除外）；編輯器頁是正對照 | 1 | 不出貨 |
| **H7** | **擁有者那一輪**：擁有者在真瀏覽器裡點 Nextcloud 的一份 `.ods`，看到它的工作表。機械那一半：頁面狀態符合 H2／H3。判斷那一半：照記 | 1／記錄 | 0.2.29 留在未計數候選；不宣稱結果 |

### 計數語意

- E1–E9 是對**一個**檢視連結的判準；連結換了（wasm sha 變），全部重來。
- E6 的 B 是在第一次 E6 算數之前、由那一個連結量出來的；之後若改 B，算「改動乾淨的定義」，E6 已有的執行歸零。
- 本檔之後追加的判準照 CLAUDE.md §9 的四個條件；它們不讓已有的 E／H 執行歸零，除非追加段明寫。

## 5. 第 0 步：草稿頁的修正（讀原始碼就做，現在）

### 5.1 頁面（`web/ods-viewer.html`、`web/ods-viewer-app.js`）

1. **一個 `:root`**：深色模式的覆寫改用 `light-dark()`，`@media` 裡不再有 `:root`（C2）。
2. **寫死 `workerUrl: "./profiles/ods-viewer-v1/sdk-worker.js"`**，拿掉 `?profile=`（C3）。在 `ods-viewer-v1` 連結之前，鏡像量測
   由 runner 在**鏡像的頁面副本**裡改這一個字面量（錨點恰好一次，報告帶兩個雜湊），不寫到原始碼。
3. **開發用的外觀在產品裡藏起來**：標題與草稿說明、file input、關閉鈕、狀態列加 `data-dev-only`，`templates/viewer.php` 藏它們
   （宿主那一半是 O6）。runner 照舊能驅動被藏起來的控制項（編輯器的前例）。
4. **診斷開關**：`?diagnostics=1` 讓引擎以 `debug: true` 建立，頁面把 stage 行（帶 `sbrk`）與去重的 stderr 記進該次開檔的紀錄。
   只影響紀錄，不改路徑、不選檔。第 1 步與 E6 都要它。
5. 頁面紀錄加 `close()`，讓 runner 能在最後一份檔關檔並收到 `document-destroy-*` 的 stage 行。

### 5.2 Session 的加密偵測（`viewer-shell/`，C6）

- 新模組 `viewer-shell/odf-package-probe.js`：從 zip 的 central directory 找 `META-INF/manifest.xml`，解開（stored 或 deflate，
  用 `DecompressionStream("deflate-raw")`），看有沒有 `encryption-data` 元素（任何前綴）。
- `OdsViewerSession.open()` 在**呼叫 `engineFactory` 之前**先問它：加密 → `ViewerError("ENCRYPTED_DOCUMENT")`、狀態 `refused`、
  不建引擎。讀不懂這個 zip（找不到 central directory、沒有 manifest、解壓失敗）→ **不拒絕**，照舊交給引擎（引擎自己的錯誤照實
  回報），並把讀不懂的原因記在狀態裡。理由：自己的 zip 讀取器不該變成第二個、比 LibreOffice 更嚴格的格式檢查。
- **已觀察**（2026-10-20，Python `zipfile` 重做同一個判斷）：306 份語料裡判成加密的恰好是 `expect: "refused"` 的那三份，
  0 份誤判，0 份讀不懂。
- 單元測試加：加密 → 拒絕且 `engineFactory` 沒被呼叫；明文 → 照常開；讀不懂 → 照常開且記原因。每一條先對壞掉的副本紅一次
  （沿用 `findings/evidence/m4-ods/W9-viewer-draft/red-cases.py` 的作法）。

## 6. 第 2 步：D5-A 的量測（一個瀏覽器、不用 ddev）

### 6.1 問題

Firefox 會不會把一個 **47,987,197 B 的 gzip 編碼回應**（v14 的 `probe.wasm` gzip -9，檢視引擎 wasm 的同一顆核心）留在 HTTP
快取裡？09-28 的 X1 量到 45,000,000 會留、60,000,000 不留，中間沒量（`findings/evidence/m3-assets/README.md` S0-4）。

### 6.2 儀器

新工具 `tools/probe_gzip_retention_firefox.py`：X1（`probe_m3_browser_cache.py`）的同一個作法，**換掉伺服器**——不用 ddev，
用本機 `127.0.0.1` 的一支小伺服器，回應頭照 X1 的 lab：`Cache-Control: max-age=15778463, immutable`、
`Content-Type: application/wasm`，編碼檔帶 `Content-Encoding: gzip`；每個請求記一行（路徑、狀態、送出的位元組）當作 access log。
每個 Firefox profile 放在 `/home` 底下（X1 的 `firefox-home`）。一輪＝同源頁面上依序 fetch 每個檔、導航到新文件、再 fetch 一次；
「第二次有沒有到伺服器」讀伺服器自己的紀錄。

檔案（每個以 `<name>?v=1` 取）：
- 正對照（必須留）：`ctrl-1k`、`ctrl-5m`、`rand-20m`、`rand-45m`（09-28 量到會留的上緣）；
- 負對照（必須不留）：`rand-60m`（09-28 量到不留）；
- 受測：`enc-gzip-v14.wasm`（第一次 fetch 解開必須是 135,237,060 B）；
- 定位：`rand-48m`（48,000,000）、`rand-50m`、`rand-52m`、`rand-52.4m`（52,428,800＝51,200 KiB）、`rand-53m`。
  `rand-*` 是亂數，不可壓縮。

**兩輪**，各用全新的 profile。次數就是量測：兩輪任何一個檔的判定不同，就是不成立。

### 6.3 判定（先寫死）

- 一輪**有效**＝正對照全部留、負對照不留、受測檔第一次解碼長度正確。
- 兩輪都有效且一致時：**gzip 上限＝兩輪都留住的最大檔的位元組數**（受測檔與定位檔一起排）。
  例：受測檔與 `rand-52m` 都留、`rand-52.4m` 不留 → 上限 52,000,000。
- 受測檔不留 → gzip 上限維持 45,000,000，而且**檢視引擎的 gzip 包不得出貨給不收 zstd 的請求**——這時退回 D5-B 的登錄，
  寫明是量出來的、不是預設。
- 只量 Firefox：Chrome 在 X1 上 `/tmp`（tmpfs、14 GB 空間）也留到 100 MB，所以限制在 Firefox。

### 6.4 永遠沒做、或不成立時

照 D5-B：gzip 不設上限，登錄 `L-ods-gzip-fallback-uncached-in-firefox-nozstd`，Z2-2 不在檢視頁上跑，理由寫明（預設的 Firefox
收 zstd；登出本來就清快取，SPEC-M3-zstd §5）。

### 6.5 會讓它錯的事（登錄）

- 本機是 `http://127.0.0.1`，X1 是 ddev 的 HTTPS。Firefox 的單筆上限 `browser.cache.disk.max_entry_size` 不分協定（**推論**）；
  正對照與負對照就是為了抓這個：兩者若與 09-28 的判定不同，這一輪無效。
- Firefox 的版本照記；換大版本要重量。

## 7. 第 1 步：不連結、不碰 ddev 的鏡像量測（診斷，不是閘門證據）

- **什麼**：§5 修好的草稿頁，在 `e2-editor-v14`（同一顆 Calc 核心）上，鏡像裡把 v14 `probe.js` 的 pthread 堆疊字面量改成
  1,048,576（`probe_ods_on_profile.py` 的 `patch_pthread_stack`，錨點 `,!ENVIRONMENT_IS_WEB,65536,false);` 恰好一次），經頁面自己的
  file input，依序開 `three-sheets-distinct.ods`、`numeric-100k.ods`、`tdf149752.ods`、`password.ods`，最後關檔。
- **只寫鏡像**：`build_mirror` 只在 override 的上層建真目錄，其餘是 symlink；改過的 `probe.js` 與頁面副本是 override，不經由
  symlink 寫回 `dist/`。runner 結束後比對 `dist/profiles/e2-editor-v14/probe.js` 的 sha 沒變。
- **它量不到**：reader 物件集在這顆核心上（只有連結能答）；W7 的任何東西（檔名仍偽裝、`documentType` 未知）。報告一律
  `evidenceClass: "diagnostic"`、`nameSpoofed: true`。
- **預測**（跑之前寫，落空照實登錄）：
  - 三張表：開、`parts == 3`；
  - 十萬格：開、`parts == 1`；最後一個 open stage 的 `sbrk` 落在 W5 的 314,814,464 加上 7 條 pthread 堆疊的差（約 +7 MiB）之內；
  - `tdf149752.ods`：開、`parts == 2`（089 在 1 MiB 下治好，經頁面的路）；
  - `password.ods`：`ENCRYPTED_DOCUMENT`，沒有建立引擎（沒有任何引擎事件）；
  - 每一份有開引擎的，pthread 回報的堆疊大小裡有 1048576（`[engine-stack]`）。沒有就是 patch 沒生效，該份不算。
- 前置條件照 `run_ods_viewer_draft_smoke.py`：KDE wallet `b false`、沒有別的 Chrome、1 分鐘負載 < 1.0。不滿足就不跑、回報。

## 8. 具名限制與風險（登錄，不設閘門）

- **L-ods-read-only**：不能編輯、不能存檔、不拿鎖。
- **L-ods-one-file-type**：XLSX 不開（這顆核心的 `calc.xcd` 沒有 `calc_MS_Excel_2007_XML`，PLAN-09-03 §1 限制 3）。
- **L-ods-second-engine-download**：第一次開 `.ods` 多約 43 MB zstd（wasm 36.1 MB＋base 包；`cjk-sub-e10` 與編輯器共用，
  開過 ODT 的瀏覽器已經有）；base 包的 zstd 大小沒量（審查 C1 推估約 6.5 MB）。
- **L-ods-editor-redownload-once**：package 加檔案會換 `buildId`，所有暖快取的瀏覽器會把編輯器重抓一次（M6；SPEC-M3-zstd §3.2
  說這是設計如此）。
- **L-viewer-sdk-private-surface**：§3.3。
- **登錄**：開檔時的 a11y 開關照跑（§3.2）。
- **登錄**：E6 的峰值是 stage 行的最大值（§4）。
- **風險**：richdocuments 或別的 office app 與 LiteCore 搶 `.ods` 的預設動作。
- **風險，沒量**：`getDocumentType`／`setPart` 在多執行緒引擎上的行為；`set_part` 之後的畫圖順序（切換之前排進去的 tile）。
- **不在本檔**：v23；產品改成一顆 Calc 核心引擎（擁有者未決，D1 把它排除在外）；ODP／ODG（要擁有者用 `impress` 重建核心）。

## 9. 工作順序

| # | 項 | 誰 | 動到什麼 |
| --- | --- | --- | --- |
| 0 | 本檔；§5 草稿頁與 session 修正＋單元測試＋紅案 | 主 session | 新檔、`viewer-shell/`、`web/ods-viewer*` |
| 1 | §7 鏡像量測 | 主 session | 不動樹（只寫證據） |
| 2 | §6 D5-A 量測 | 主 session | 不動樹（只寫證據）；本檔 append 結果與定下的上限 |
| O2 | W7＋B1＋B2＋拿掉 save，原始碼在 `OXSDK_ODS_VIEWER` 底下，每項先寫紅案；worker 那一半；`viewer-shell/ods-document-sdk.js`（D3＝A） | 主 session | 原始碼（新 define；編輯器 rule 不定義它）、`sdk/sdk-worker.js` |
| O3 | Makefile rule `ods-viewer-v1`（`E2_V5_CORE`、reader 物件集、`link_product_stack_1m`、自己的 build／dist 目錄、從第一次連結就加守衛）；base 包切片工具（§3.2，先紅案）；手冊 | 主 session | Makefile（finding 042：每個舊 target 都會變成 out of date） |
| O4 | **連結（擁有者的 make）**，不重建核心 | 擁有者 | `build/`、`dist/profiles/ods-viewer-v1/` |
| O5 | Phase E（E1–E9）在鏡像上；頁面重新量尺寸（E4b） | 主 session | 不動綁定的東西 |
| O6 | 宿主 0.2.29（§3.4）、打包工具（§3.5）、測試 | 主 session | app repo、打包工具 |
| O7 | **擁有者的 ddev 時段**裝上，然後 H1–H6 | 擁有者＋主 session | ddev |
| O8 | H7 | 擁有者 | — |

**擁有者第一次看得到成果**：O4＋E2 之後，鏡像頁上的檢視器，帶真的工作表名稱與分頁。第二次：宿主整合（H），在 Nextcloud 裡點
`.ods` 就開。

## 10. 修訂紀錄

| 日期 | 改了什麼 |
| --- | --- |
| 2026-10-20 | 立。折入審查 B1、B2、C1–C6、M1–M8 與修正段；D3＝A、D5＝A（擁有者：依 fable 建議）；E8 依 §2 的 metadata 比對改成「`9901e9be` 減掉 `35-lang-normalize.conf`」（審查與修正段都釘 `9901e9be`，會帶回 finding 114） |

---

# 追加 1（2026-10-20 晚）：第 1 步的結果，與 E6 的更正

只 append；上面一字不改。

## A1.1 第 1 步：四項預測全中（診斷）

證據：`findings/evidence/m4-ods/step1-mirror-v14-1mib/`（`report-2026-10-20T113849Z.json`、README）。Chrome 151，headless，
快取關。runner `tools/run_ods_viewer_step1.py`，判讀器自測 12/12 在跑之前。

| 檔 | 結果 | parts | `open.begin` sbrk | 最後一個 open stage | 回報 1 MiB 的 pthread |
| --- | --- | ---: | ---: | ---: | ---: |
| `three-sheets-distinct.ods` | 開 | 3 | 293,015,552 | 298,328,064 | 3 |
| `numeric-100k.ods` | 開 | 1 | 294,244,352 | 317,792,256 | 3 |
| `tdf149752.ods`（089） | 開 | 2 | 293,015,552 | 305,037,312 | 7 |
| `password.ods` | `ENCRYPTED_DOCUMENT`，**沒有建立引擎**、沒有任何 stage 與引擎事件 | — | — | — | — |

- **089**：1 MiB 下經**頁面的路**開得了。§2 的「沒量」縮成：reader 物件集在這顆核心上、以連結帶 1 MiB（只有連結能答）。
- **開機差異全是堆疊**：v14 的 `open.begin` 減 W1 的 v12 開機＝2,949,120＝3 ×（1,048,576 − 65,536），那一輪正好三條 pthread
  回報 1 MiB（**已觀察**）。§7 的預測寫「約 +7 MiB」是七條全起的上界；實際只起三條（`tdf149752.ods` 起了七條，但都在
  `open.begin` 之後）。
- `dist/profiles/e2-editor-v14/probe.js` 跑完 sha 不變。

## A1.2 E6 的更正：關檔的 stage 行在檢視連結上不存在

**被逼出來的量測**：上面那一輪，三顆引擎、四次關檔，**收到 0 行** `document-destroy-*`。原因（**讀原始碼**）：那兩個 stage
只在 `#ifdef OXSDK_DIAGNOSTIC_CLOSE_STAGES` 底下發（`probe_engine.cpp:2548-2553`），沒有任何產品或編輯器的 rule 定義它。
§4 的 E6 寫「所有 stage 行（含 `document-destroy-enter`）的最大值」，在檢視連結上只會看到開檔的 stage——E6 說它涵蓋畫圖
階段，其實不涵蓋。

**處置**（CLAUDE.md §9 的四個條件：先於滿足——還沒有任何 E6 執行；被逼出來且指名——上面那份報告；形式 1；截止——E6 第一次
算數的執行）：

1. §3.2 的表**加一列**：`OXSDK_ODS_VIEWER` 也打開那兩行 stage——
   `#if defined(OXSDK_DIAGNOSTIC_CLOSE_STAGES) || defined(OXSDK_ODS_VIEWER)`。只多兩行 JSON，只在 `debug` 時轉給頁面。
2. **E6 取代為**：每筆：開檔＋每張表一塊 tile＋關檔期間，所有 stage 行的 `sbrk` 最大值 < 939,524,096，**而且該筆的 stage 行裡
   要有 `document-destroy-enter`**；沒有它的那一筆，E6 對它不成立（不是「沒看到超過」）。洩漏界限 B 的寫法不變。
3. **紅案**（O2）：E6 的判讀器拿到沒有 `document-destroy-enter` 的報告要紅。
4. §4 E6 底下「`document-destroy-enter` 在每張表畫完之後……上界」那段的前提，改成在第 1 點落地之後才成立；dlmalloc 中途
   還回頂端會漏掉短暫峰值，仍是**推論**、登錄。

**計數語意**：E／H 都還沒有任何執行，沒有東西歸零。

## A1.3 修訂紀錄（續）

| 日期 | 改了什麼 |
| --- | --- |
| 2026-10-20 晚 | 追加 1：第 1 步四項預測全中；E6 取代為「要有 `document-destroy-enter`」，`OXSDK_ODS_VIEWER` 打開關檔 stage |

---

# 追加 2（2026-10-20 晚）：D5-A 量到了，gzip 上限＝52,428,800

只 append；上面一字不改。

證據：`findings/evidence/m4-ods/d5-gzip-retention/`（`report-2026-10-20T114325Z.json`、README）。工具
`tools/probe_gzip_retention_firefox.py`，判讀器自測 11/11 在跑之前。Firefox 157.0.1（snap），兩輪各一個全新 profile。

- **兩輪都有效、逐檔一致**：正對照（1 k／5 M／20 M／45 M）都留、負對照 60 M 不留、受測檔第一次解碼正好 135,237,060 B。
- **受測檔（v14 的 wasm，gzip 47,987,215 B）會留。**定位檔：52,428,800（＝51,200 KiB）留、53,000,000 不留。
- **依 §6.3：gzip 上限＝52,428,800。**與 Firefox 文件上的預設 `browser.cache.disk.max_entry_size`＝51,200 KiB 一致——
  **一致，不是讀到的**：在 chrome context 讀 pref 要 `-remote-allow-system-access`，這一輪讀失敗，錯誤原樣留在報告裡。
- 與 09-28 X1（Firefox 156、ddev 的 HTTPS）重疊的兩點一致，所以換伺服器與協定沒有移動共同的那兩點。

**對 §3.5 與 H5 的效果**（取代 §3.5「gzip 上限照 §6 量到的數字定」與 H5「gzip ≤ §6 定的上限」的未定值）：
- 打包工具的 gzip 上限由 45,000,000 改成 **52,428,800**；zstd 上限維持 45,000,000。理由寫進打包工具的常數旁邊，
  引用這份報告——這是 K0-5「換了處方就重判並寫理由」（SPEC-M3-zstd §5），不是放寬。
- H5 的紅案多一個：gzip 52,428,801 的合成檔要被拒。
- D5-B 的 `L-ods-gzip-fallback-uncached-in-firefox-nozstd` **不登錄**：不收 zstd 的 Firefox 也會留住檢視引擎的 gzip。
- **會讓它失效的事**（登錄）：Firefox 改預設的 `max_entry_size`；使用者自己調小它；換大版本。發佈前的檢查清單要重跑這支工具一次
  （一分鐘內跑完，不用 ddev）。

## A2.1 修訂紀錄（續）

| 日期 | 改了什麼 |
| --- | --- |
| 2026-10-20 晚 | 追加 2：D5-A 成立，gzip 上限 52,428,800；D5-B 的登錄不需要 |

---

# 追加 3（2026-10-20 晚）：O2 落地——引擎原始碼、worker、SDK；以及 reader 形狀本來就編不過

只 append；上面一字不改。證據：`findings/evidence/m4-ods/o2-engine-source/`。**沒有連結、沒有跑 make；引擎路徑只做了語法檢查，
第一次執行是擁有者的 O4 連結之後的 E2。**

## A3.1 被逼出來的事實：reader 形狀在今天的原始碼上編不過

`em++ -fsyntax-only`，a11y 核心的旗標、只帶 `-DOXSDK_READER_PROFILE`：HEAD `fe8722df` 的 `probe_engine.cpp` **16 個錯**，與本輪
改動無關（**已觀察**，`syntax-checks.txt`）。reader profile 是八月連的；之後有三處只在 `OXSDK_EDITOR_DISCOVERY` 底下宣告的名字
被無條件使用：開檔時的 `refreshEditorAccessibility()`（08-17 起）、`readSelection()`／`handleGetSelection()`、引擎迴圈的
`gEditorPending` 期限分支。計畫 D2 與審查都把 reader 形狀當成可建的底座（審查查了 `view-ready` 的前處理深度，沒有編譯）。

**處置**：三處的**使用端**包進 `#ifdef OXSDK_EDITOR_DISCOVERY`（`GetSelection` 在沒有編輯器的建置回 `UNSUPPORTED_OPERATION`）。
- **編輯器那邊不動**：28 條 rule、112 個物件，前處理後 111 個逐 token 相同、1 個兩邊都編不了、**0 個不同**；另三條舊 `CPPFLAGS`
  的 rule 手動補量，同樣沒有可編的物件改變（`preprocess-identity-base-fe8722df.json`、README）。
- **檢視引擎開檔時不打開 a11y。**這是計畫 D2 原文寫的「no a11y refresh」；審查 M2 以為它會照跑而要求登錄——現在它不跑，M2 的
  登錄改成：**W2、W5、第 1 步都是在 a11y 開著的編輯器 profile 上量的，檢視連結不開——這是診斷與連結之間的一個變因，由連結自己的
  E2／E6 量。**

## A3.2 釘下的名字（取代 §3.2 表中「工作名稱」的部分）

- 匯出：`_oxsdk_document_set_part(req, handle, part)`、`_oxsdk_document_current_part(req, handle)`、
  `_oxsdk_document_part_name(req, handle, part)`、`_oxsdk_document_part_text(req, handle, part)`。負的 part 在 ABI 邊界回
  `INVALID_ARGUMENT`（同步）；`part >= parts` 由引擎執行緒回錯誤事件 `INVALID_ARGUMENT`。
- 回覆事件：`part-set {part, width, height}`、`current-part {part}`、`part-name {part, name}`、
  `part-text {part, text, partBefore, partAfter}`；`opened` 加 `documentType`、`inputSuffix`。
- 能力：字串 `open-ods`／`part-switch`／`part-text`，位元 `1u << 11`／`12`／`13`；檢視 profile 的位元**不含** `SAVE_ODT`，
  `oxsdk_document_save` 在 define 下**不編譯**（`EMSCRIPTEN_KEEPALIVE` 不管匯出清單都會匯出）。
- worker 操作：`setPart`／`currentPart`／`partName` 掛 `part-switch`，`partText` 掛 `part-text`；不是整數的 part 在 worker 就拒絕
  （交給 ccall 會變成 0，默默切到第一張表）。
- 編譯期守衛：`OXSDK_ODS_VIEWER` 必須配 `OXSDK_READER_PROFILE`，且不得與任何編輯器 define 或 `OXSDK_MAINLOOP_ENGINE` 同時出現
  （`#error`）。
- `part_text` 在引擎執行緒上**同步等** `.uno:SelectAll` 的 `UNO_COMMAND_RESULT`（期限 10 秒），等的期間佇列不前進，所以不會有
  畫圖插在切換、選取、切回之間。逾時照樣取消選取、切回原本的表，回 `PART_TEXT_TIMEOUT`。**登錄**：逾時之後才到的 SelectAll 會留下
  選取（那時等待已關）。
- E3 的讀法與原生 oracle 相同：`getTextSelection("text/plain;charset=utf-8")`，不是選取型別讀回。

## A3.3 SDK（D3＝A）與頁面

- `viewer-shell/ods-document-sdk.js`：`OdsViewerEngine extends DocumentEngine`；`sdk/document-sdk.js` 零位元組改動，殼層 bundle v75
  digest 仍是 `5b14038e…`。
- **`L-viewer-sdk-private-surface` 的實際內容**：`_request`（另外**覆寫**它，在 `open` 那一次讀回覆的 `documentType`／`inputSuffix`，
  因為出貨的 `DocumentHandle` 只留它認得的欄位）、`_initialize`、`DocumentHandle.handle` 與 `_assertUsable`。
- 沒宣告 `part-switch` 的 profile 拿到原本的 handle，adapter 照舊標出它代答了什麼——所以第 1 步那種 v14 鏡像量測照樣能跑。
- 頁面接上子類別，並做了 **E4b 的頁面那一半**：`session.refit()` 在第一次畫完之後依 handle 的尺寸重設 scheduler（同一張表），頁面
  重排 surface 再畫一次。v14 上重跑第 1 步（`report-2026-10-20T120926Z.json`）：三份都重設一次，surface 寬＝畫完後的
  `documentWidthTwips`／15（1785、1785、1837；`tdf149752.ods` 是**變窄**，27658 → 27555）。**E4b 的「畫到 x＝寬−1」要捲到右緣
  才量得到**——headless 視窗只畫到 1024 px；O5 的 runner 要捲過去。

## A3.4 紅案與回歸

- 原生模型測試＋10 個突變、worker 7 個測試＋7 個突變、SDK 7 個測試＋6 個突變、session 24 個測試＋W9 harness 38 個突變，全部紅在
  點名的檢查上。worker 那一組第一次跑有一個**沒紅**：「key 一模一樣」那條在 JSON 來回轉之後比，看不到值為 undefined 的 key；改成看
  原始訊息。
- 既有：JS 673/673；Python 測試除 `test_e1_corpus.py`（E1 語料產生器，不讀 `src/`／`sdk/`，本輪未查）外全過；E1-C `intact: true`。
- **§34 的帳**：因執行而修 **+3**——`tests/test_e2_profile.py` 兩條原始碼字串測試被新程式碼誤判（固定 6000 字元的窗口只剩 26 字元
  餘裕、`getTextSelection` 呼叫點普查），各在測試裡寫明理由；W9 的關檔測試把固定延遲改成「等 factory／open 被呼叫」，因為新的
  package 讀取讓延遲落在別處。因審核而修 **+0**。新判讀工具（第 1 步 runner、D5 工具）都是診斷用、沒有被計數使用；若之後要拿來計數，
  照 §34 先做一次雙席審核。

## A3.5 修訂紀錄（續）

| 日期 | 改了什麼 |
| --- | --- |
| 2026-10-20 晚 | 追加 3：O2 落地；reader 形狀編不過的處置（檢視引擎不開 a11y）；釘下匯出、事件、能力的名字；E4b 頁面那一半已實作 |

---

# 追加 4（2026-10-20 晚）：O3 落地——Makefile rule、profile 建構工具、連結前的閘門；連結交給擁有者

只 append。證據：`findings/evidence/m4-ods/o3-pre-link/`；手冊：`handoff/RUNBOOK-link-ods-viewer-v1.md`。**沒有連結**；只跑了
`make -n`（乾跑）與不編譯的 `make -k test-e2-c-static`。

## A4.1 落地的東西

- **Makefile `ods-viewer-v1`**：物件 `sdk_api`／`probe_engine`／`unoembind_stub`（**不帶 `probe_api`**——它的 `KEEPALIVE`
  `probe_save` 等於暗的 save；也不帶 `editor_api` 與 a11y bridge），`E2_V5_CPPFLAGS`＋reader 形狀＋`OXSDK_ODS_VIEWER`；匯出清單從
  a11y 核心自己的核心匯出清單來（與寫作核心逐位元相同，`e9b54133`），有 save 或編輯器符號就拒絕；link line＝v14 的，只換堆疊那個
  token；從第一次連結就有守衛；打包時核 worker pin（`d1de2dfd…`）、跑建構工具的 `--check`，並在 wasm 上做三個 grep（正對照
  `search-result` 要在、`partBefore` 要在、編輯器的 `verified-caret-readback` 要不在）。
- **`tools/build_ods_viewer_profile.py`**：E8 的 base 包（兩條路、同 sha，`base-a11y-no35.6f7424a1c1427ad7.data`，39,892,028 B、
  1,488 個檔），放在檢視 profile 自己的目錄；CJK 與 fallback 走 `../resources/` 共用；reader 形狀的 manifest。
- **檢視引擎的 `#error`** 多擋 `OXSDK_MERGE_KEY_UNDO` 與 `OXSDK_FINDING_016_SELECTION_BARRIER`（理由見 A4.3）。

## A4.2 量到的數字（取代 §8 L-ods-second-engine-download 的推估）

- base 包 zstd -19：**5,649,371 B**（審查 C1 推估約 6.5 MB）；gzip -9 7,567,047 B。
- 所以第一次開 `.ods` 的新增下載約 **wasm zstd（v14 是 36,078,637 B；檢視 wasm 連結後才知道）＋5.6 MB**，`cjk-sub-e10` 與編輯器
  共用。

## A4.3 M1-1 被改了一處（因執行而修，有證人）

`test-e2-c-static` 的 M1-1 母數是每一條 `$(X_BUILD)/%.o` rule，檢視 rule 加進來之後：
1. 沒宣告 → 紅在它的兩個物件上（證人 `test-e2-c-static-red-viewer-not-declared.txt`）；照 v20–v22 的前例宣告成 carrier。
2. 宣告之後紅在 B 的第二道守衛：對從來沒有 selection barrier 的 rule「拿掉 barrier」什麼都不會變。**B 的兩道守衛只對帶 B 的
   carrier 有意義。**
3. 改法（`guard_variants`）：編譯指令帶 `-DOXSDK_MERGE_KEY_UNDO` 的 carrier 照舊兩道；不帶的改成「注入 B 必須失敗」（B 編不進它）。
   帶 B 的 carrier 若掉了 define，會落到第二種並紅在那裡。離線測試 22/22。
4. 新守衛第一次就紅在誠實的檢視 rule 上：B 自己的 `#error` 包在編輯器 `#ifdef` 裡，reader 形狀下注入 B 只是惰性、不是被拒。
   於是檢視引擎的 `#error` 把 B 與 barrier 列進去，之後綠：29 條 rule、115 個物件、13 個宣告的差異，exit 0。

§34 的帳（這一段）：因執行而修 **+1**（M1-1）；因審核而修 **+0**。本輪合計：因執行 +4（追加 3 的 +3 與這裡的 +1），因審核 +0。

## A4.4 連結（擁有者的 make）

`handoff/RUNBOOK-link-ods-viewer-v1.md` §2：

```
cd ~/LibreOffice/study_LiteCore/wasm_sdk_probe
unset LOSRC LOBUILD EMSDK_ROOT EXTRA_DEFINES EXTRA_OBJECTS HOST_CXX
make ALLOW_FROZEN_RELINK=1 dist/profiles/ods-viewer-v1/sdk-manifest.json 2>&1 | tee build/link-ods-viewer-v1.log
```

預計 3 分鐘左右，給 10 分鐘。連結之後主 session 先核凍結集（1,430 個檔）、堆疊字面量、`ScDocShell` 在不在、E1-C，再封存，
**然後 E2 是連結的第一次執行**。

## A4.5 修訂紀錄（續）

| 日期 | 改了什麼 |
| --- | --- |
| 2026-10-20 晚 | 追加 4：O3 落地；base 包 zstd 實量 5.6 MB；M1-1 的守衛按 carrier 是否帶 B 分開（有證人）；連結交給擁有者 |

## A4.6（同晚，交出連結之後、擁有者執行之前）空白工作表的 `part_text`

讀原生 oracle 的資料（`findings/evidence/m4-ods/01-native-oracle/oracle.jsonl`）時發現：空白表全選之後 `getTextSelection` 回
**null**（`empty-one-sheet.ods` 的 `text: null`），而語料期望 `""`。原本的 `part_text` 把 null 當錯誤（`LOK_ERROR`），E3 會紅在每一張
空表上。改成：null → 空字串，回覆帶 `textNull: true`（worker 只轉具名欄位，不轉它；worker 與 pin 不變）。有內容的表若被讀成空，E3
比文字時照樣紅，所以這不會遮住錯誤。模型測試加兩條、突變加兩個（12 個全紅）；語法、`test-e2-c-static`、未定義符號都重跑過。
**另記**：十萬格那份的期望文字在 manifest 裡是 `null`，E3 要從 oracle 的 jsonl 取（588,890 字元）。
