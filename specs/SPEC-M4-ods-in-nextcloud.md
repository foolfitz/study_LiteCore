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

## A4.7（同晚，擁有者執行之前）`part_text` 不再因為沒等到 SelectAll 的通知而失敗

連結前把第一次執行最可能出事的地方再讀一遍：`part_text` 只靠 `.uno:SelectAll` 的 `UNO_COMMAND_RESULT` 當屏障。萬一 Calc 在 LOK 下
不回這個通知，每次呼叫都會等滿期限再失敗，而**修它要再連結一次**。改成：最多等 **3 秒**；等不到也照樣讀、照樣取消選取、照樣切回，
回覆帶 `selectAllConfirmed: false`。不會遮住錯誤：讀到還沒落地的選取就是錯的文字，E3 比文字會紅，這個旗標說明原因。`PART_TEXT_TIMEOUT`
這個錯誤碼因此撤掉。`textNull` 與 `selectAllConfirmed` 由 worker 具名轉給頁面——**worker pin 改成 `cc2d6514…`**（取代 A4.1 與手冊
原本寫的 `d1de2dfd…`；擁有者尚未連結）。模型 15 個突變、worker 7 個、SDK 6 個全紅；JS 704/704；連結前的閘門在這份原始碼上重跑過。

---

# 追加 5（2026-10-20 晚，任何 Phase E 執行之前）：Phase E 的 runner，以及三處讀法先釘死

只 append。runner `tools/run_ods_viewer_phase_e.py`＋harness 頁 `web/ods-viewer-e-harness{.html,-app.js}`；判讀器是報告的純函式，
`--selftest` 25/25（每條判準至少一個紅案，含 E1 的「空目錄」與「少一筆紀錄」）。harness 經由產品自己的 `OdsViewerSession`＋
`OdsViewerEngine` 開每一筆，攔下 handle 做 E3 的 `partText`、E4a 的兩次畫圖、E5 引擎層的越界拒絕；大文字只回正規化（CRLF→LF）後
的 sha256 與長度，期望文字由 runner 用同樣的正規化算 sha。E4b 與 E9 走真的檢視頁，另做。

**三處讀法**（不是新判準；是把 §4 已經寫的話落成可判的條件，寫在能滿足它的執行之前）：

1. **E4a「manifest 說那一區有內容／是空的」**：manifest 不記錄儲存格的位置。所以——生成的（`ladder/`，`expectedFrom: generator`）
   一律從 A1 寫起，`cells > 0` 就是第一塊 tile 裡有內容，必須與同輪的空表對照**不同**；期望文字是 `""` 的表必須**相同**。
   上游檔（`expectedFrom: native-oracle`）的 manifest 對位置沒有宣稱，所以只套 E4a 的「畫圖 OK、尺寸欄位的型別、第二次
   `documentSizeChanged == false`」三項。**永遠沒做的預設**照 §4。
2. **E2 的 `view-ready ≤ 60 s`**：從該筆開始（取檔、建引擎、開檔）算起，比只算開檔嚴。
3. **E3 的期望文字**：manifest 的 `expectedText` 是 `null` 的（十萬格之類），取原生 oracle 的 `oracle.jsonl` 同一份檔、同一個 part 的
   文字；oracle 那裡是 `null` 的（空表），期望是 `""`（A4.6）。

**E6 的洩漏界限 B 還沒定**：要先在檢視連結上開機 5 次量雜訊底（§4 E6），量完寫進本檔，之後的 E6 才算數。這一輪的 runner 判的是
峰值與 `document-destroy-enter`；B 那一半另做。

---

# 追加 6（2026-10-20 夜，ladder 全綠之後、E6 的 B、E4b、E9 任何執行之前）：四處讀法先釘死

只 append。Phase E 的 ladder（10 筆＋ODT 負對照）在 `ods-viewer-v1`（wasm `f6ab3cdb…`）上第一次執行 E1–E6 全綠（`findings/evidence/
m4-ods/phase-e/report-2026-10-20T133003Z.json`，28 秒）；全語料的執行在寫本段時還在跑。下面四處是把 §4 已經寫的話落成可判的條件，
寫在能滿足它的執行之前；**不是新判準**，形式照舊。

## A6.1 E6 的 B（M8）怎麼量

- **一份檔、五顆引擎**：`ladder/one-cell-a1.ods` 的位元組，在同一個頁面上開 5 顆新的 `OdsViewerEngine`（5 個 worker＝檢視連結開機
  5 次），每顆 open → `handle.close()` → `dispose()`。**B := max |open.begin[n+1] − open.begin[n]|**，n = 1..4。
- 為什麼要同一份檔（**讀原始碼**）：`open.begin` 在引擎把輸入位元組寫進 MEMFS **之後**才發（`probe_engine.cpp:3190-3197`），所以
  ladder 那一輪不同大小的檔給出不同的 `open.begin`（236,523,520 到 248,664,064），那是檔的大小，不是雜訊；只有同一份檔的
  `open.begin` 可比。
- 工具：`tools/run_ods_viewer_e6_leak.py`＋harness 頁 `web/ods-viewer-e6-harness{.html,-app.js}`（只寫進鏡像）。量到的 B 寫進
  追加 7；之後的 E6 才算數（§4 計數語意）。

## A6.2 E6「同一筆開 5 次」的形狀

- **一顆引擎、五次 (open → 每張表一塊 1024×1024 tile → `handle.close()`)**，Δ_n := open.begin[n+1] − open.begin[n]，n = 1..4，
  每個 Δ_n ≤ B。這是 **SDK 層**驅動並如此宣告：產品的 session 在 close 時 dispose 引擎（`OdsViewerSession._release`），產品路徑開
  不出第二次；`e2-c-d4-heap` 的 shared 臂用的是同一個宣告。SDK 的 open 沒有 `open.close-previous`（只在 `!command.sdk` 時發，
  `probe_engine.cpp:3205`），所以每次重開之前要先 `close()`，關檔的 `document-destroy-*` 行就在每一輪裡。
- **先登錄的事實**（d4 heap，編輯器核心 `e2-editor-v2`，shared-nosearch 臂，Firefox）：同形序列的 `open.begin` 是
  287,248,384 → 330,088,448 → 338,935,808 → 之後五輪不變；fresh 臂八輪逐位元相同。也就是說重開在那顆核心上前兩輪各漲
  43 MB、9 MB 然後持平。若檢視連結是同一個形狀而 B = 0，E6 的洩漏半照字面是**紅**。**紅就是量測**：不預先改判準；要改要寫理由
  （CLAUDE.md §4），而且 E6 已有的執行歸零（§4 計數語意）。

## A6.3 E4b 的頁面半

- runner 自己從 DOM 讀，不用頁面的 `run.fit`（紅案那一版沒有它）：surface 的 CSS 寬＝`#surface.getBoundingClientRect().width`、
  最右邊畫到的 x＝所有 tile canvas 的 max(left + width)。開檔後讀一次；再把 viewport 捲到最右（`scrollLeft = scrollWidth`），
  等頁面自己的 scroll handler 排完、`session.drain()` 回來，讀第二次。
- **判**：`surfaceCssWidth == ceil(widthTwips_after_first_paint / 15)`，且捲到最右之後 `rightmostDrawnPx ≥ surfaceCssWidth`
  （「畫過一塊涵蓋 x = 寬 − 1 的 tile」）。捲動後引擎若再報更寬的尺寸，記錄，不判（那是另一張 finding，不是 E4b）。
- **紅案**（§4 注入 7，「今天的草稿（不重新量尺寸）」）：鏡像裡的頁面把 `if (session.refit()) {` 改成 `if (false && session.refit()) {`
  （錨點恰一次），其餘逐位元相同；它要在 E4b 紅，報告放 `red-cases/`，`evidenceClass: "red-case"`。
- 兩筆：`ladder/three-sheets-distinct.ods`（W9 smoke 看到 26,593 → 26,775 twips 的那一份）與 `upstream/tdf149752.ods`（089）。

## A6.4 E9 的「各自的第一塊 tile 是 E5 的那塊」與 read-back

- 頁面自己的 tile 是 256 px，E5 的是 1024×1024，位元組不可能相等。**讀法**：點 tab k、頁面畫完之後，runner 經頁面的 live
  session（`window.__odsViewer.session._view.render`——私有面，只給 runner 用）向**同一顆引擎**要 E5 那一塊
  （(0,0)、1024×1024、15 twips/px），其 sha256 要等於指定的 Phase E 報告裡該筆 part k 的第一次畫圖；報告以路徑＋sha256 記進
  E9 的報告。頁面自己 (0,0) 的 256 px canvas 的 sha 與 non-paper 像素數另外記錄，不判。
- read-back：點 tab k 之後 `state.currentPartReadBack == k`。這個值是 session 由 `setPart` 的回覆設的，回覆的 `part` 是引擎在
  切換後讀回的（`ods-document-sdk.js` `handle.setPart`），不是請求的 k；上面那塊 tile 相等是第二個、獨立的證人。
- 其餘照 §4：`parts == 3`、三個 `.ods-tab` 的文字＝`state.partNames`＝manifest 的 `sheetNames`、`namesFromEngine == true`、
  `adapterFallbacks == []`。點 tab 走 DOM 的 click（使用者的路），不直接呼叫 `switchPart`。
- 工具：`tools/run_ods_viewer_e4b_e9.py`，`--selftest` 先紅。E5 的參照報告找不到或少那一筆時要**紅**，不是空洞的綠。

## A6.5 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-20 夜 | 追加 6：A6.1 B 的量法（同一份檔、五顆引擎）；A6.2 重開序列的形狀與先登錄的 d4 事實；A6.3 E4b 的 DOM 讀法與 no-refit 紅案；A6.4 E9 的 1024 tile 讀法與 read-back 的來源 |

---

# 追加 7（2026-10-20 夜，全語料第一次執行與 E6 兩臂之後）：B = 0、重開序列的更正、兩類工作表的讀法、全語料逼出的四張 finding

只 append。全語料（306 筆＋ODT 負對照）第一次執行：`findings/evidence/m4-ods/phase-e/report-2026-10-20T133240Z.json`（598 秒，
Chrome 151）——E1、E2、E6 全綠（303 筆開檔、3 筆加密拒絕且沒有引擎；`view-ready` p50 0.93 s、最大 31.0 s（`tdf37341.ods`）；
峰值最大 553,447,424（`many_charts.ods`））；**E3 紅 17／303、E4a 紅 6／304、E5 紅 1／305**。第一次紅是量測：每一條都先判是紅在
產品還是紅在判讀器，判法寫在下面，引擎的實際文字用 harness 的 `?recordText=1`（診斷開關，`diagnostic-text/report-2026-10-20T134644Z.json`）
讀出來比對過。

## A7.1 E6 的 B，與洩漏半句的更正

**量到的**（`e6-leak/report-2026-10-20T134946Z.json`，工具 `run_ods_viewer_e6_leak.py`，A6.1／A6.2 的形狀）：

| 檔 | boots 臂 `open.begin` ×5 | reopen 臂 `open.begin` ×5 | Δ_1..Δ_4 |
| --- | --- | --- | --- |
| `one-cell-a1.ods` | 236,523,520 ×5 | 236,523,520 → 246,259,712 → 250,454,016 → 250,454,016 → 250,454,016 | +9,736,192、+4,194,304、0、0 |
| `three-sheets-distinct.ods` | 236,523,520 ×5 | 236,523,520 → 246,288,384 → 250,478,592 → 同 → 同 | +9,764,864、+4,190,208、0、0 |
| `numeric-100k.ods` | 237,752,320 ×5 | 237,752,320 → 261,304,320 → 279,339,008 → 同 → 同 | +23,552,000、+18,034,688、0、0 |

- **B = 0**（五次開機逐位元相同；三份檔都是）。
- **洩漏半句的前提被證偽**：§4 寫「第 n+1 次的 `open.begin` 減第 n 次 ≤ B」，前提是關檔後 break 會回到關檔前。量到的是
  **`open.begin[n+1] == 第 n 輪的峰值`**（每一列都成立）：break 是高水位、只升不降（dlmalloc 不把頂端還回去），所以 Δ_1、Δ_2 是
  第一、二輪把高水位推上去的量，不是洩漏；A6.2 先登錄的 d4 事實（編輯器核心）是同一個形狀。**撤回原句、改寫如下**（CLAUDE.md §4；
  理由就是上表）：
  - **E6 洩漏半句（取代）**：一顆引擎、同一份檔 5 輪（open → 每張表一塊 tile → close），`open.begin` 的序列在第 3 輪起**不再
    上升**：Δ_n ≤ B（= 0）對 n = 3、4 成立；Δ_1、Δ_2 **記錄不判**（它們是高水位的建立）。每輪都要有 `document-destroy-enter`，
    每輪峰值 < 939,524,096。
  - 工具的判讀器照這句改（尾段判、頭段記錄），紅案：尾段任一步 > B 要紅、頭段的步**不**讓它紅。改在這一輪算數的執行之前；
    這一輪（上表）是逼出改法的執行，本身不算數。
- **計數語意**：E6 峰值半句的執行（Phase E 的兩次）不受影響；洩漏半句之前沒有算數的執行，沒有東西歸零。

## A7.2 隱藏工作表（E3／E4a／E5 的讀法；finding 157）

`fdo67682-2.ods` 31 張，`Table`…`Table_12`（part 12–23）的表樣式是 `table:display="false"`。引擎對 `set_part(12..23)` 全部讀回 11
（**讀原始碼**：`ScModelObj::setPart` → `ScTabView::SelectTabPage(nPart+1)`，而 `ScTabControl` 只為 `IsVisible()` 的表插頁，
`tabcont.cxx:60`；切到沒有頁的 id 什麼都不做）。session 因此丟 `PART_READBACK_MISMATCH`，E3／E4a／E5 對那 12 張紅。

- **紅在判準的前提**：「每張表」假設每張表都能被顯示。隱藏表在桌面 Calc 也不能切過去。
- **讀法**（runner 自己從檔案推：content.xml 的表樣式 `table:display="false"`，記進 `staged[].hiddenParts`，形式二）：E3、E4a
  **略過**隱藏的 part；E5 對隱藏的 part 要求**拒絕**（session 的 `showPart` 丟錯）且引擎讀回**不是它**；E2 的 `parts == manifest.sheets`
  不變（計數含隱藏）。原生 oracle 對隱藏表讀到的是前一張可見表的文字（同一個機制），它給的期望本來就不是那張表的。
- **產品缺口登錄為 finding 157**：檢視頁把隱藏表畫成可點的 tab，點了只得到 `PART_READBACK_MISMATCH`。修法要引擎多一個查詢
  （LOK `getPartInfo` 的 `visible`）→ 下一個檢視連結；頁面已有 `tabs[].enabled/disabledReason` 的位子。
- **計數語意**：E3／E4a／E5 的「乾淨」定義改了（略過隱藏表）；全語料要**重跑**一次，重跑那份才是這三條的執行。

## A7.3 揮發性工作表（E3 的讀法）

E3 的 11 處文字差異中 **7 處**是 `TODAY()`／`NOW()`／`RAND()`／文字欄位 `text:date` 的結果：oracle 是 2026-09-03 跑的，期望裡是
`09/03/26`，引擎今天讀到 `10/20/26`（`cachedValue` p1、`dependencyTree`、`tdf149484`、`tdf160003` p1、`rich-text-cells`、
`tdf36038_ExtendedLCID`、`tdf118624`（RAND））。

- **紅在 oracle 的前提**：「期望文字是檔案的函數」對揮發性儲存格不成立。
- **讀法**（runner 從 content.xml 推：該表的 `table:formula` 含 `TODAY(`、`NOW(`、`RAND(`、`RANDBETWEEN(`，或表內有 `text:date`／
  `text:time` 欄位，記進 `staged[].volatileParts`）：這些 part 的 E3 **記錄不判**（sha 與長度照記，差異列在 verdict 的 `recorded`），
  其餘 part 照舊逐位元。登錄 `L-volatile-sheets-not-compared`：482 張裡 7 張的保真度沒有逐位元證據。
- **計數語意**：同 A7.2，隨全語料重跑。

## A7.4 全語料殘餘的紅（產品側；不改判準）

1. **finding 158 — 表單控制項的檔畫不出來**：`move-cell-anchored-shapes`、`tdf106181`、`tdf121963`、`tdf134161`、`tdf154005`
   （都含 `<form:form>`／`<draw:control>`）每一塊 tile 都 `UNO_EXCEPTION: component context fails to supply service
   com.sun.star.form.Forms`。**讀原始碼**：`FmFormPageImpl::getForms` 呼叫 `css::form::Forms::create`；其實作
   `com_sun_star_form_OFormsCollection_get_implementation` 在 `native-code.py:186` 被 `HAVE_FEATURE_DBCONNECTIVITY` 閘住，
   而 `build-a11y-gate0/config_host/config_features.h:27` 是 `0`（原生 oracle 的 build 是 `1`）。核心層的缺口，不是連結層；
   編輯器 profile 同一顆核心，ODT 含控制項**未量**。
2. **finding 159 — 載入時重算的函數給 `#VALUE!`**：`date-time-functions`（`TIMEVALUE("6:45 PM")` 一類 5 格）、`functions.ods`
   p2（`MULTINOMIAL`、`SERIESSUM`、`CONVERT`…）與 p6（整欄財務函數 `ACCRINT`…）在引擎讀到 `#VALUE!`，桌面 oracle 是數值；
   檔內有快取值（`office:value`）。`scaddins` 三個 add-in **在**核心的 `services_constructors.list`（查過），所以不是少 add-in；
   成因未定（候選：字串→數值轉換設定、locale 資料被 `ENABLE_WASM_STRIP_LOCALES` 砍掉、載入時重算而非用快取）。E3 對這 3 張保持紅。
3. **`user-defined-function.ods`**：引擎 `#NAME?`、oracle `#VALUE!`——檢視核心沒有 Basic（`ENABLE_WASM_STRIP_BASIC_DRAW_MATH_IMPRESS`），
   登錄 `L-no-basic-udf`，E3 對它保持紅（1 張）。
4. **finding 160 — `part_text` 的 SelectAll 間歇沒確認**：全語料那一輪 482 次讀取中 2 次 `selectAllConfirmed: false`
   （`tdf160329_sortWithHiddenRows` 讀到 1 個字、`tdf139258_rotated_image` 讀到空），診斷重跑同兩筆都 `true`、文字正確。
   A4.7 的設計如實說明了原因，但使用者路徑上會是錯的文字。E3 對未確認的讀取**保持紅**（不重試、不放寬），次數記在 handoff。

## A7.5 runner 因執行而修（§34，證人在括號內）

- `--only` 的執行一律加入三個 ladder 對照（empty、distinct、identical）；之前只加 empty，E5 的兩條對照在局部執行上紅且 detail 是空的
  （證人：`diagnostic-text/report-2026-10-20T134644Z.json`，E5 「tiles pairwise distinct: []」）。
- `hiddenParts`／`volatileParts` 的推導與 A7.2／A7.3 的判讀；`--record-text`／`recordText=1` 診斷開關；E6 工具的尾段判讀。

## A7.6 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-20 夜 | 追加 7：B = 0；E6 洩漏半句撤回改寫（高水位）；隱藏表與揮發表的讀法（runner 從檔案推）；finding 157–160 與兩條 L 的登錄；runner 的三處修 |

---

# 追加 8（2026-10-20 深夜，擁有者裁示 158-A 之後、任何算數的執行之前）：含表單控制項的檔在引擎之前型別化拒絕

只 append。擁有者 2026-10-20 深夜：「三件事照你建議」——158 走 A（引擎之前拒絕，不連結）、159 先診斷、157＋160 併進 v2。

## A8.1 偵測條件（從語料量出來的，不是想出來的）

306 份裡 49 份 content.xml 有 `<office:forms`（LO 一律寫空元素）、6 份有 `<form:form`、**5 份有 `<draw:control`**——而且畫不出來的
**正好是這 5 份**（`tdf138507.ods` 有 `<form:form` 沒有 `<draw:control`，畫得出來）。所以判別子是 **`<draw:control`**（控制項圖形，
`SdrUnoObj`，它才會逼 `FmFormPageImpl::getForms(true)` 去建 `Forms`），不是 `<office:forms`、不是 `<form:form`。

## A8.2 處方

- `viewer-shell/odf-package-probe.js` 多回答一題：`formControls`——把 content.xml **串流**解壓、逐塊找 `<draw:control`，找到就停；
  找不到要讀完（`numeric-1m.ods` 的 content.xml 解開是 192,781,261 B，這是最貴的一份，成本記在 `packageProbe.probeMs`，
  E2 的 `view-ready` 從該筆開始算、本來就包含它）。讀不了的照舊 `formControls: null`、交給引擎。
- session：加密之後、引擎之前，`formControls === true` → `ViewerError("FORM_CONTROLS_UNSUPPORTED")`，state `refused`，
  `engineRequested` 維持 false。整份文件拒絕，不分哪張表（混合文件裡沒有控制項的表能不能畫**未量**，登錄 `L-mixed-form-control-sheets-unmeasured`）。
- 頁面照舊顯示 `已拒絕（FORM_CONTROLS_UNSUPPORTED）：…`。

## A8.3 E2 的讀法（取代 §4 E2 對這 5 筆的期望）

runner 從檔案推 `staged[].formControls`（content.xml 含 `<draw:control`，形式二，與 A7.2 的 `hiddenParts` 同一條路）。
`formControls` 的筆：E2 期望**拒絕** `FORM_CONTROLS_UNSUPPORTED` 且 `engineCreated == false`（manifest 的 `expect: "opens"` 被這個推導
蓋過，因為 manifest 的 `opens` 說的是原生 oracle 開得了）；E3–E6 對沒開的筆本來就不判。

## A8.4 紅案（先紅再綠）

1. 單元測試（`tests/ods-viewer-session.test.mjs`）：記憶體裡組一個 content.xml 含 `<draw:control` 的包 → 拒絕、`engineRequested false`、
   `packageProbe.formControls true`；只含 `<form:form` 的包 → 照開（`formControls false`）；既有的加密／STORED／截短案照過。
2. runner selftest：`formControls` 的筆若開了 → E2 紅；拒絕碼不對 → E2 紅。
3. 全語料：5 份拒絕、298 份照開（就是負對照；少一份都紅）。

## A8.5 計數語意

E2 對這 5 筆的「乾淨」定義改了；全語料要再跑一次，那一份才是 E2 的算數執行。E3／E4a 因此少 5 筆紅（它們不再是「開了但畫不出來」），
殘餘的紅只剩 finding 159 的 2 份與 UDF 1 份。

## A8.6 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-20 深夜 | 追加 8：158-A——`<draw:control` 為判別子、串流 probe、`FORM_CONTROLS_UNSUPPORTED`、E2 讀法、三層紅案、L-mixed-form-control-sheets-unmeasured |

## A8.7 結果（同晚，158-A 落地後的全語料執行）

`findings/evidence/m4-ods/phase-e/report-2026-10-20T144351Z.json`（598 秒）：**E1、E2、E4a、E5、E6 全綠**——5 份 `<draw:control` 的檔
`FORM_CONTROLS_UNSUPPORTED`、`engineCreated false`，3 份加密照舊，298 份開得了。E3 紅 3／298：`date-time-functions.ods`、`functions.ods`
p2／p6（finding 159）、`user-defined-function.ods`（`L-no-basic-udf`）。probe 的串流掃描：中位數 1 ms，最貴 `numeric-1m.ods` 341 ms
（content.xml 解開 192 MB；該筆 `view-ready` 4.7 s），298 份合計 787 ms。單元測試紅案證人：`phase-e/158-a/`（舊 shell 7 紅／21 綠，新 shell
28／28；第一次紅是 import 路徑的意外，錯誤訊息帶酬載所以當場抓到、重做）。`selectAllConfirmed` 464 true、0 false。

**這一輪之後 Phase E 的狀態**：E1、E2、E4a、E4b、E5、E6、E9 綠；E3 只剩 finding 159 的 2 份與 UDF 1 份紅。E7、E8 本輪未重跑（連結沒變）。

## A8.8 finding 159 的成因（同晚，診斷不連結）

探針檔（`findings/evidence/m4-ods/phase-e/159-diagnosis/`）：核心函數全對、Analysis add-in 的 5 格全 `#VALUE!`、快取值改成 3 的副本仍顯示 2
（載入時重算）。**成因（靜態讀出）**：`gcc3_wasm` bridge 的呼叫簽章表由 `wasmbridgegen` 只從 udkapi＋offapi 產生（本核心 55 個），
scaddins 的介面在它自己的 `InternalUnoApi`，`getSeriessum` 的 `didddd` 不在表裡 → bridge 丟 `RuntimeException("Wasm bridge cannot call
virtual function with signature …")` → `ScUnoAddInCall` 收成 `FormulaError::NoValue` = `#VALUE!`。修法是核心重建（`CustomTarget_gcc3_wasm.mk`
多餵 scaddins 的 rdb），併進 v2 的核心批次；在那之前 E3 對這 2 份保持紅、登錄為 v1 的具名限制 `L-addin-functions-value-error`（擁有者裁示：
159 先診斷，已診斷）。

## A8.9 §8 的登錄（append；擁有者不在座位，依已裁示的處方登錄，不新增判準）

- **L-addin-functions-value-error**：Analysis／Date／Pricing add-in 函數（YEARFRAC、SERIESSUM、MULTINOMIAL、財務函數…）在檢視引擎一律
  `#VALUE!`；檔開得了、畫得出來，只有那些格錯。成因 A8.8，修法是核心重建（v2 批）。語料 2／298 份受影響。
- **L-mixed-form-control-sheets-unmeasured**：含 `<draw:control` 的檔整份拒絕（A8.2）；控制項只在某一張表時其餘的表能不能畫，未量。
- **L-no-basic-udf**：檢視核心沒有 Basic，Basic 的使用者函數讀到 `#NAME?`（桌面是函數自己的結果）。語料 1 份。
- **L-volatile-sheets-not-compared**：`TODAY()`／`NOW()`／`RAND()`／`text:date` 的表，E3 只記錄不判（A7.3）；482 張裡 10 張（7 張在第一輪
  實際不同）。保真度在這些表上沒有逐位元證據。
- **L-hidden-sheet-tabs-enabled**（finding 157）：隱藏表的 tab 在 v1 可點、點了得到 `PART_READBACK_MISMATCH`；v2 加 `part_info`。
- **L-part-text-selectall-unconfirmed**（finding 160）：`part_text` 的 SelectAll 間歇沒在 3 秒內確認（2／482 一次、0／464 兩次）；v2 改等待。

---

# 追加 9（2026-10-20 深夜）：fable 裁決——今晚安裝 0.2.29 並跑 H1–H6；Phase H 在 E3 紅 3 筆的登錄限制下開始

只 append。擁有者不在座位，留言「有問題就發給fable，我授權他帶我決定」；主 session 把兩題交給 fable（brief 在 handoff 10-20j），
裁決 2026-10-20 23:30 CST。原文（英文）存在 handoff 10-20j 的裁決段；本段是它對本檔的效力。

## A9.1 Q1 ＝ A：今晚裝 0.2.29、跑 H1–H6、留著當未計數候選（一次性的受託時段）

條件（任一不成立 → 走 C：ddev 什麼都不碰，交接時附上安裝指令）：

1. **順序**：離線閘門綠（打包工具 selftest；K0／H5 評分，H5 的三個紅案先紅；單元測試）→ 分支 `host-0.2.29` 與 study 樹的六個檔
   先 commit（署名規則照舊）→ 本追加 commit → 之後才第一個 ddev 指令。〔已成立：selftest 13/13、K0/Z0/H5-1 clean、22 紅案、
   單元測試 28/28、`9a349f6`、`b70c12b2`；本追加即是。〕
2. **時段**：從本追加的 commit 起，到「10-21 07:00 CST」「擁有者在 session 裡打任何字」「第一個 ddev 指令之後 3 小時」三者最早者。
   時段內只做 O7：不跑 K／計數鏈、不裝第二個宿主版本、不對任何專案 `ddev start/stop/restart`。v22 規格 item 17 的八個條件照 §14.4
   的用法套用，其中 #1 換成下面第 4 條、#4 讀成「0.2.28 的工具在編輯器那一半不變（`http_served_page.py` 照舊，餵 H4）；檢視那一半
   由 H5／H6 自己的檢查判；打包工具的改動就是受測的產品改動」。
3. **碰活的目錄之前**：`findings/evidence/host-0.2.29/README.md` 要先寫好還原配方（`git checkout 0870695 -- .` 或 revert、把
   `build/archive/host-0.2.27-engine-817413d5ad5bd502/` 複製回 `engine/`、`ddev occ upgrade`；標籤留 0.2.29、位元組是 0.2.28 的）。
   前置檢查：活的 `engine/` 與該封存 `diff -rq` 只差 `ATTRIBUTION.md`，否則停。新 package 先封存到
   `build/archive/host-0.2.29-engine-<buildId>/`＋`ATTRIBUTION.md`。〔已成立：README 寫好、前置檢查只差 ATTRIBUTION.md、
   封存 `host-0.2.29-engine-1b4d6a1fc905fb8a/` 192 MB。〕
4. **ddev 守衛**（取代 v22 §13.1 第 1 步的「只有 litecore」）：安裝前與每個 H 項目前唯讀 `ddev list`；第一次讀到的「正在跑的專案集合」
   記下來；之後集合一變（有專案被啟動或停掉＝擁有者在用 ddev）→ 做完手上那一項、不再開新項、交接。第一次讀到就在跑的專案不算停止理由。
   KWallet 照 §14.5 查；不設桌面閘門（H1–H6 不量時間）。
5. **錯誤或權限拒絕**：item 17 #6 原文——停、還原、交接；不排錯 ddev、不改寫指令。若紅的 detail 是連線失敗／router 404 且與第 4 條的
   集合變化同時發生，不算產品紅：集合穩定後該項重跑一次，兩份報告都留。
6. **H 紅**：H2 FAIL（時段窗內對檢視測試檔的路徑有任何 LOCK／PUT／MOVE／PROPPATCH）或 H4 FAIL（0.2.28 的臂、或裝好的 package 裡
   編輯器的五個身分）→ 今晚照第 3 條還原。H1／H3／H5／H6 FAIL → 0.2.29 留著、記錄、H7 之前停。只有 NE 沒有 FAIL → 留著、
   狀態「not established」、擁有者決定。
7. H2 的判讀鍵在測試檔的路徑／fileId 與時段窗，擁有者自己的流量翻不動它；正對照是同一份 log 裡另一個測試檔的 ODT 開檔。H1 之前記
   `occ app:list`；若別的 office app 擁有 ODS 的預設點擊，H2 改走 LiteCore 自己的動作入口，並把 §8 的風險記為「已發生」，不算 H 紅。
8. 給擁有者的下一則回覆（zh-TW）開頭要寫時段結束時間，以及「若你需要 ddev start/stop 別的專案，不用等我；我的執行會斷，我重跑」。
   交接第一行照 v22 §13.1 的四種形狀 (a)–(d)；累積的未計數清單加上 0.2.29（檢視路由、ODS 的 Files 動作、`litecore-engine/3`
   頁面表、gzip 上限 52,428,800）；K 維持併批。

**理由（白話，給擁有者）**：ddev 規則是為了不讓量測把你的其他專案鎖住幾小時；今晚的 H 不到一小時、不量時間、你不在，而第 4 條用
「集合有沒有變」偵測你回來，不用猜容器狀態。把未計數候選裝起來日常用是你已經選過的模式；回頭路是三條指令，碰之前就寫好。
這次覆寫了裁決 7 的「只此一次」：那句是擋舊句子變成常設時段，今晚是一次新的、明確的授權；這次仍是一次性，之後的時段仍由你定。

## A9.2 Q2 ＝ A：Phase H 在 E3 紅 3 筆（登錄限制）下開始

條件：

1. H 立在具名報告上：`phase-e/report-2026-10-20T144351Z.json`（E1／E2／E4a／E5／E6）、`e6-leak/report-2026-10-20T135556Z.json`
   （B = 0 的算數執行；逼出改法的是 `134946Z`）、`e4b-e9/report-2026-10-20T135205Z.json`（E4b／E9），以及 E7／E8 的證人：
   `findings/evidence/m4-ods/o4-post-link/README.md` 的凍結集合 1,430 檔不變、E1-C `intact: true`、建構工具配方內的 E8 檢查
   （fable 的 F2：E7／E8 在 `f6ab3cdb` 上不是「從未做」）。
2. `144351Z` 裡 E3 紅的 sha256 集合**恰好**是這三個（已核對，相等）：
   - `upstream/date-time-functions.ods` `e0b2b652459bcaf96db5fb9a83d8b28ba3be1abfd87028ed92fdbf3c06464e89`
   - `upstream/functions.ods` `45b1403f99f1ac6e10cda4c68ddd0b005a19fbfbd07fbd358ceb7e809302d569`
   - `upstream/user-defined-function.ods` `5af67ed3e257ddcc9912aff138ce378c28f297914b5bd054f1cade73c557bbc3`
   且 `selectAllConfirmed` false ＝ 0（已核對：464 true、0 false）。其他任何 E3 紅 → H 不開始。
3. 今晚不為 159 造新機制（probe 不做 add-in 函數偵測——那是手工枚舉，CLAUDE.md §1 形式三／§4）；它是 v2 的工作項。E3 對這三筆保持紅
   到 v2——不重讀、不重試。
4. H7 之前，0.2.29 的發佈說明草稿（`RELEASE-TEXT-DRAFT-0.2.27-0.2.28.md` 的後繼）要點名 `L-addin-functions-value-error`、
   `L-no-basic-udf`、`L-hidden-sheet-tabs-enabled`、`FORM_CONTROLS_UNSUPPORTED` 的拒絕、`L-ods-read-only`（可 grep），
   H7 的訊息要把 `#VALUE!` 的注意事項連同那兩份檔告訴擁有者。
5. 0.2.29 維持未計數候選；名義出貨版維持 0.2.26。

**理由（白話）**：E3 的「停」是為了不讓空白畫布過關；這裡 E3 量了 298 份裡 295 份逐位元相同，剩下三份追到 bridge 的簽章表，
只有重建核心能改——你已經決定把那次重建併進 v2。等下去要花你幾小時的 make，對「點 .ods 就能開」什麼都買不到；限制寫在你和
發佈說明看得到的地方。

## A9.3 Q3（沒問的）

1. **H4 的讀法**：「0.2.28 的宿主臂」＝ H-154c／H-154o／H-155（兩個瀏覽器、N=3、依 §14.5 不設桌面閘門）。D2-v22 與 M11-autosave 不重跑，
   理由是 H4 裡編輯器在裝好的 package 中位元組相同，不是推論。
2. **§34 計數**：`check_m3_assets.py` 與 `probe_m3_assets.py` 是檢查的改動——因執行而修 **+2**，證人是「舊工具對 schema-3 package 必紅」
   （`findings/evidence/host-0.2.29/README.md` 的證人段：舊工具釘 `litecore-engine/2` 與單頁 closure；本 session 未實跑舊工具，靜態陳述）。
3. **登錄**：`L-ods-editor-redownload-once` 今晚實現（新 buildId）；交接第一行要說。
4. 鏡像上的第一次親眼看（10-20i 第 3 步）仍未做；0.2.29 上的 H7 涵蓋它——H7 訊息保留 `fdo67682-2.ods`（隱藏表）與 `tdf134161.ods`
   （控制項，現在會拒絕）的注意事項。
5. 擁有者未決的兩件（一顆 Calc 核心的引擎；L-C 的 A3）不動；其他沒有東西擋 O6／O7。

## A9.4 本 session 的處置

條件 1、3 已成立（見上）；第一個 ddev 指令**沒有**在本 session 發出：context 已超軟上限，安裝與 H1–H6 由下一個 session 依
`handoff/HANDOFF-2026-10-20j-…`＋`RUNBOOK-install-host-0.2.29.md` 執行，時段從它的第一個 ddev 指令起算（條件 2）。

## A9.5 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-20 深夜 | 追加 9：fable 裁決 Q1=A（8 條件）、Q2=A（5 條件）、Q3 五項；sha 三筆核對；H4 讀法；§34 +2 |

---

# 追加 10（2026-10-21 早）：O7 完成——0.2.29 裝上後被 H 抓到兩個宿主 bug（finding 161、162）；0.2.31 上 H1–H4、H6 全過；H7 交擁有者

只 append。證據：`findings/evidence/host-0.2.29/README.md`（時序、三次 H 的判讀、H4）、`m4-ods/phase-h/shakedown/`（三份報告）。

## A10.1 時序與授權（追加 9 的條件怎麼用掉的）

- 23:29:57 第一個 ddev 指令（唯讀 `ddev list`）：集合 **{litecore}**；KWallet `b false`；`occ app:list` 記錄（`office 1.0.0` 是 Nextcloud 的 Office overview，
  不搶 ODS 的點擊，Q1-7 的風險沒發生）；前置檢查重做（活的 `engine/` 與 0.2.27 封存只差 ATTRIBUTION.md）。
- 23:3x 主 session 的安裝指令（runbook 1–4 一次下）被 auto mode 的分類器擋下（「Production Deploy」），什麼都沒跑（核對過）。同一時間擁有者在 session 打字
  （Q1-2：受託時段結束），說「需要的話我可以手動執行」，於是 23:39 親手跑 `install-0.2.29.sh`（runbook 1–4＋Q1-3 前置檢查，舊 package 搬到 git-ignored 的
  `engine.old`）。之後 0.2.30（00:13）、0.2.31（06:19）同樣由擁有者跑一行；06:3x 擁有者裁示「這種很短的指令你就自己跑」（記憶 `short-commands-run-them-yourself`）。
- 碰 ddev 的指令：`ddev list` 四次（每個 H 項目前，集合始終 {litecore}）、`occ app:list`、`occ log:tail` 兩次、`occ upgrade` 三次（擁有者）、H runner 三次、
  H-155 chain 一次、host-entry 一次。沒有 `ddev start/stop/restart`。

## A10.2 結果（0.2.31，package `1b4d6a1fc905fb8a` 從 0.2.29 起沒變）

| 判準 | 結果 | 證據 |
| --- | --- | --- |
| H1 | PASS：ODS、ODT 的列選單有 `litecore-open`；XLSX、PDF 沒有 | `phase-h/shakedown/2026-10-20T222047+0000.json`（plain 臂；紅案臂讀到同四份清單） |
| H2 | PASS：落在 `…/1b4d6a1fc905fb8a-90d7bc2c/ods-viewer.html?fileId=…`；`ready`／3 parts／`spreadsheet`；log 窗只有 GET 200、PROPFIND 207；瀏覽器只送 GET；ETag、版本數不動。正對照 ODT 有 LOCK 200。紅案（偷拿鎖的宿主）H2 紅，LOCK 進 log、ETag 也動 | 同上 |
| H3 | PASS：Alpha／Beta／Gamma 來自引擎；點 1、2、0 讀回 1、2、0 | 同上 |
| H4 | PASS：H-154c／H-154o／H-155 兩個瀏覽器各 3 輪（框 Chrome `[605,323,640,335]`／1850×980、Firefox `[605,326,640,342]`／1850×994，與 0.2.28 相同）；`check_m3_host_entry.py --label shakedown` HOST_ENTRY LANDS（Chrome open-save 3/3、conflict 3/3、broken 1/1、broken-no-save 1/1；Firefox open-save 3/3、conflict 3/3） | `host-0.2.29/judge-h155.txt`、`m3-host-entry/shakedown/2026-10-20T222436Z.json` |
| H5 | 離線已過（打包工具 selftest 13/13、K0／Z0／H5-1 clean、22 紅案），本輪沒變 | `host-0.2.29/README.md` |
| H6 | PASS：兩份文件 200，COOP `same-origin`、COEP `require-corp`、CSP 去 nonce 相同 | `2026-10-20T222047+0000.json` `wire` |
| H7 | **交擁有者**（A10.6） | — |

依追加 9 條件 6：沒有 H2／H4 FAIL → 0.2.31 留著當**未計數候選**，取代 0.2.28 日常使用；名義出貨版仍 0.2.26。

## A10.3 兩個宿主 bug，與離線閘門為什麼看不到

- **finding 161（0.2.29）**：`engine()` 拿 `PAGES[*]['module']`（`./e2-editor-app.js`）比 manifest 的 `source.pages[*].module`（`e2-editor-app.js`，`files` 的鍵），
  拒絕自己的 package，**每條路由 500**——編輯器在 ddev 上從 23:39 到 00:13 不能用。修：0.2.30（`e6e325a`，一行）。
- **finding 162（0.2.30）**：`scopedStyle()` 的改寫錨只准 `}` 與 `:root {` 之間是空白；檢視頁依 §5.1 在唯一的 `:root` 規則上方寫了說明註解，**檢視文件 500**。
  修：0.2.31（`421f4b8`）：計數用去註解副本、改寫允許夾註解；對 package 裡兩份頁面重放——編輯器輸出逐位元相同、兩條 `:root` 與「只在註解裡」仍拒絕。
- **為什麼 H5 看不到**：H5-1 用打包工具自己的頁面表判打包工具自己的 manifest；控制器的 `PAGES` 與 `scopedStyle()` 是第二份、手寫的檢查（§1 形式三），在 H 之前
  沒對真的 package／頁面跑過。能抓到的檢查就是宿主上的 H6／H2——追加 9「第一個紅就是量測」成立了兩次。**不為「兩份表要一致」造新機制**（§4）；登錄在這裡。
- 兩次修法都只動 PHP、不動 package、不動頁面；0.2.29→0.2.31 的 buildId 相同，所以 `L-ods-editor-redownload-once` 只發生一次（10-20 深夜的那次）。

## A10.4 runner 因執行而修（§34；證人在括號內）

- 第一次跑（證人 `2026-10-20T154120+0000.json`）：`row_actions()` 點到的是列的第一顆按鈕＝inline 的 `sharing-status`（開了側欄），而且全域查
  `[data-cy-files-list-row-action]`——inline 按鈕也帶這個屬性、關掉的選單 popper 留在 DOM——清單逐列累積（ODS 0、ODT 12、XLSX 23、PDF 35）。改成：
  toggle 用 `button[aria-haspopup="menu"]`、選單項＝點擊前不存在的元素（打標籤）、inline 與選單分開記、經 toggle 關閉並讀回 `aria-expanded`；判讀多一條
  「選單項沒出現」（新紅案）。`open_by_click()` 等到元素後點擊時 null（虛擬捲動重繪）→ 找到即點、同一次 evaluate。
- 第二次跑（證人 `2026-10-20T161522+0000.json`）：plain 臂在根目錄讀到 ODS 列後其餘三列 60 s 找不到（紅案臂四列都讀到）→ 測試檔放進 `M4 phase-h/`
  資料夾（MKCOL，冪等），八列永遠在畫面內。頁面 500 時 `.ods-tab` 為 null 讓臂在 log 窗與正對照之前炸掉 → 只在 `state === 'ready'` 才點分頁，並記錄文件標題
  與前 300 字。
- selftest 22/22。**計數**：因執行而修 **+2**（每一次逼出改動的執行算一筆），因審核而修 +0。**自 10-14b 累計 44 / 27。**

## A10.5 登錄（append 到 §8）

- **觀察（finding 163 候選）**：編輯器宿主離開頁面時送四次 UNLOCK，第一次 204、其餘三次 500——Nextcloud 的 log 是 `files_lock` 的
  `LockNotFoundException` 未捕捉。`js/litecore-editor.js` 與 0.2.28 逐位元相同（設計上在 `beforeunload` 與 `pagehide` 各送一次），這是本 runner 第一次
  把 Apache log 對準編輯器開關才看見。不是 H 判準，今晚不追。
- Phase H 的測試檔留在 ddev：`M4 phase-h/`（8 個）與根目錄（第一、二次跑的 8 個）。刪除是寫入，本時段不做。
- `engine.old`（0.2.28 的 package，99 MB）留在 app 目錄；還原配方改用它或 0.2.27 封存都行。
- 累積未計數清單加：檢視路由、ODS 的 Files 動作、`litecore-engine/3` 頁面表、gzip 上限 52,428,800、161 與 162 的修法。K 維持併批。

## A10.6 H7（擁有者）

1. 把 `wasm_sdk_probe/test-docs/ods/ladder/three-sheets-distinct.ods` 上傳到 Files，點它：開在檢視頁，標題列有檔名與「唯讀」，下方三個分頁 Alpha／Beta／Gamma，
   點 Beta 畫面換成第二張。第一次會多下載約 42 MB（檢視引擎）。
2. 注意事項（都是 §8／A8.9 登錄過的限制，不是新 bug）：
   - `upstream/date-time-functions.ods`、`upstream/functions.ods`：開得了，但 add-in 函數的格是 `#VALUE!`（`L-addin-functions-value-error`，v2 核心重建才修）。
   - `upstream/fdo67682-2.ods`：有隱藏表，它的分頁可點、點了顯示拒絕（`L-hidden-sheet-tabs-enabled`，v2）。
   - `upstream/tdf134161.ods`：整份拒絕 `FORM_CONTROLS_UNSUPPORTED`（158-A 的處方；158-B 在 v2）。
3. 發佈說明草稿：`handoff/RELEASE-TEXT-DRAFT-0.2.29.md`（可 grep 的五個限制名在第 4 節）。

## A10.7 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-21 早 | 追加 10：O7 完成；161、162；H1–H4、H6 在 0.2.31 全過；runner 兩輪因執行而修 +2（44/27）；163 候選；H7 交擁有者 |

---

# 追加 11（2026-10-21）：v2 另立規格；兩處更正

只 append。

## A11.1 v2 在哪裡

檢視引擎 v2（核心批次 159＋158-B、檢視連結 157＋160）寫在 **`specs/SPEC-M4-viewer-v2.md`**。擁有者 2026-10-21 對「158-B 要不要拆出 v2」
答「重編其實無所謂」，所以 158-B 留在 v2；核心建在新樹 `wasm-lite/build-ods-viewer-v2`，判準 K-1／K-2 與退路 F 在建置之前釘死（該檔 §2）。
本檔的 E1–E9 照舊是 v2 Phase E 的判準，v2 改了哪幾處讀法寫在該檔 §3 以後（連結前追加）。

## A11.2 更正

1. **A8.8 的 `didddd`**（取代該段「`getSeriessum` 的 `didddd` 不在表裡」的簽章）：`getSeriessum(double, double, double, sequence)` 的簽章是
   `didddi`。結論（scaddins 的介面不在 bridge 的表裡）不變；離線實跑 `wasmbridgegen` 量過（`findings/evidence/m4-ods/phase-e/159-diagnosis/bridgegen-offline/`）。
2. **finding 160 的嚴重度**：產品頁面沒有任何地方呼叫 `partText`，只有 E3 用它。160 是量測儀器與 SDK 能力的問題，不是使用者看得到的錯字
   （`SPEC-M4-viewer-v2` §0）。

## A11.3 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-21 | 追加 11：v2 另立 `SPEC-M4-viewer-v2`；A8.8 簽章更正；160 嚴重度更正 |

---

# 追加 12（2026-10-22）：E6 的洩漏半句撤回（fable 裁決 1，擁有者同意）

## A12.1 撤回什麼、為什麼

**撤回 A7.1 改寫後的洩漏半句**（「一顆引擎、同一份檔 5 輪，`open.begin` 第 3 輪起不再上升：Δ_n ≤ B 對 n = 3、4 成立」），依 CLAUDE.md 判準形式 §4：
前提被證偽，不補機制、不另訂 `sbrk` 門檻（不寫「容許 8 KB」「跑到平為止」「查清楚之前算紅」）。證據與理由：finding 164、
`findings/evidence/m4-ods/viewer-v2/fallback-phase-e/e6-repeat/`（README 與 `RULING-fable-1.md`）。

- 前提「break 在第 2 輪之後到頂」14 趟中 5 趟不成立（v2 3／7、v1 2／7，形狀相同）。
- 在常見的「平」形狀裡，這條判準看不到小於一塊 tile（4,194,304）的增長，它的綠燈不是證據（CLAUDE.md §6）。
- 產品的 session 關檔時就 dispose 引擎（`OdsViewerSession._release()`），重開這條路產品走不到。

## A12.2 檢視連結的 E6 從此是

1. **峰值半句**（不變）：每筆的 stage 行 `sbrk` 最大值 < 939,524,096；已算數的執行照算。
2. **重開的形狀**（不變，形式一）：一顆引擎 5 輪，每輪有 `document-destroy-enter`、每輪峰值 < 939,524,096、每輪 tile 數＝表數、無錯誤。
3. **重開序列只記錄、不判**：`run_ods_viewer_e6_leak.py` **不帶 `--bound`**（工具既有的 `notJudged` 路徑）。B 每個連結照量，當開機臂的見證。

登錄：`L-E6-leak-sbrk`（兩個連結）；工作項「單次開檔期間的增長沒人量」（finding 164）。

## A12.3 計數語意

- **什麼都不歸零**：B 沒變（仍是 0），§4「改 B 算改動乾淨的定義」不觸發；峰值半句的執行與洩漏半句本來就分開（A7.1）。
- **作廢、不是失敗**：`e6-leak/report-2026-10-20T135556Z.json`（v1）與 `viewer-v2/fallback-phase-e/e6-leak/report-2026-10-22T021502Z.json`（v2）的
  `E6 reopen bound` 判定作廢；兩份的開機與重開形狀判定照算。
- 追加 9 第 845 行引用 `135556Z` 的那一句，此後只讀它的形狀與 B＝0。
- **0.2.31 不變**：仍是未計數的日常候選；H1–H7 從來沒有依賴重開序列。

**如果這段追加沒有寫**：`021502Z` 照字面是紅，E6 那一列的預設（「停」）對 v1、v2 都適用。

## A12.4 修訂紀錄（續）

| 日期 | 內容 |
| --- | --- |
| 2026-10-22 | 追加 12：E6 洩漏半句撤回（fable 裁決 1，擁有者同意）；E6 的新組成、計數語意、`L-E6-leak-sbrk`、finding 164 |
