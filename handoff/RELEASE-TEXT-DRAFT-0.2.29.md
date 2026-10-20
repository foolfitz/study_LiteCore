# 發佈說明（草稿）：0.2.29–0.2.31（ODS 唯讀檢視器；未計數候選）

> **讀者是擁有者**，所以用 zh-TW。這是 `AGENTS.md`「`handoff/**` 用英文」那條的明示例外，前例是 `RELEASE-TEXT-DRAFT-0.2.27-0.2.28.md`。
>
> 怎麼讀：每一句宣稱後面附依據。**「已觀察」＝量過；「讀原始碼」＝沒量；「推論」＝從量過的東西推出來；「未量」＝沒有人量過。**第 6 節把「未量」集中列一次。
>
> **這是草稿，因為三件事還沒做：**
> - **計數鏈 K 延後併批**（SPEC-M3-link-batch-v22 §13；`release-count-batched`）：名義出貨版本仍是 **0.2.26**，0.2.29 是未計數候選。
> - **Phase H 的 H7（擁有者親手點 .ods）還沒做**（第 6 節）。
> - **v2 的核心重建還沒做**：第 4 節的 4.1、4.3、4.4 要等它。
>
> 本檔是 `RELEASE-TEXT-DRAFT-0.2.27-0.2.28.md` 的後繼，那份照原樣留著；編輯器那一半的說明（Markdown 貼上、finding 152–155）**全部照舊**，這裡不重複。
> 規格：`specs/SPEC-M4-ods-in-nextcloud.md`（追加 1–9）。

## 1. 版本一覽

| 版本 | 殼層 | 宿主 commit | 引擎包 buildId | 內容 | 狀態 |
|---|---|---|---|---|---|
| 0.2.26 | v74 | `3c01876` | `f5f0df762e1855f2` | 引擎 v21 | **名義出貨版本**（2026-10-19 計數成立） |
| 0.2.28 | v75 | `0870695` | `817413d5ad5bd502` | 引擎 v22、貼上為 Markdown、finding 152–155 | 前一個未計數候選（2026-10-20 14:33–23:39 在 ddev 上） |
| 0.2.29 | v75（不變） | `9a349f6` | **`1b4d6a1fc905fb8a`**（schema `litecore-engine/3`） | **Nextcloud 裡點 .ods 就開：唯讀檢視器，另一顆引擎** | 2026-10-20 23:39 裝在 ddev；**每條路由 500**（finding 161），同晚被 0.2.30 取代 |
| 0.2.30 | v75 | `e6e325a` | 同上 | 控制器一行：頁面表比對 module 用 manifest 的鍵（161） | 2026-10-21 00:13 裝；編輯器回來、**檢視文件仍 500**（finding 162），被 0.2.31 取代 |
| **0.2.31** | **v75** | `421f4b8` | 同上 | `scopedStyle()` 允許 `:root` 規則前有註解（162） | **未計數候選**。2026-10-21 06:19 裝；**H1／H2／H3／H6 全過**（第 5 節）；H4 見同節 |

- **ODT 編輯器一個位元組都沒動**：profile `e2-editor-v22`（wasm `f7a40bcc…`）、殼層 v75、頁面 `e2-editor-app.js`（`3b96cb16…`）與 0.2.28 的相同。〔已觀察：package manifest `source.pages`；`findings/evidence/host-0.2.29/README.md`〕
- **引擎包多了檢視引擎**：35 個檔、340,254,512 B；gzip 116,501,319 B、zstd 83,955,910 B。新的是 profile `ods-viewer-v1`（wasm `f6ab3cdb…` 135,185,771 B，gzip 47,972,102 B、zstd 36,050,365 B）和它的資源包 `base-a11y-no35`（39,892,028 B，zstd 5,647,568 B）。〔已觀察：`MANIFEST.json`〕
- 檢視引擎連在 `build-a11y-gate0` 核心（writer＋calc）上；編輯器仍連寫作核心。兩顆引擎、兩條血統。〔已觀察：規格 §3.1、`o4-post-link/README.md`〕

## 2. 新功能：Nextcloud 裡點 .ods 就開（唯讀）

- **怎麼用**：Files 裡點一個 `.ods`（或列的「⋯」選單裡 LiteCore 的開啟動作）→ 開在檢視頁。頁面下方是工作表分頁，點分頁切換。沒有工具列、沒有游標、不能打字。〔讀原始碼：`web/ods-viewer-app.js`、宿主 `src/files.js`；宿主上的點擊路徑由 H1／H2 判（第 5 節）〕
- **分頁的名字是引擎讀出來的工作表名稱**，不是頁面自己編的「工作表 1、2、3」。測試檔 `three-sheets-distinct.ods` 顯示 Alpha／Beta／Gamma，點第 2、3、1 張，引擎讀回的就是那一張。〔已觀察：鏡像上 E9；宿主上 H3〕
- **保真度**：上游語料 306 份，298 份開得了；其中 295 份每一張工作表的文字與桌面 LibreOffice 26.8 讀到的**逐位元相同**，畫出來的 tile 與鏡像一致。剩下 3 份是第 4 節的 4.1、4.2。〔已觀察：`findings/evidence/m4-ods/phase-e/report-2026-10-20T144351Z.json`，E1–E6〕
- **唯讀是真的唯讀**：不拿鎖、不 PUT、不建版本、ETag 不動。宿主給檢視頁的只有 `load`；帶 `save` 或會拿鎖的宿主，頁面拒絕啟動（`HOST_ENTRY_INVALID`）。〔讀原始碼：`js/litecore-viewer.js`、`web/ods-viewer-app.js`；宿主上由 H2 判，含「宿主偷拿鎖」的紅案〕
- **記憶體**：同一份連結開機五次，第一個 stage 的記憶體逐位元相同（B = 0）；同一檔重開五次是高水位，不是每次都漲。〔已觀察：E6〕
- **畫面大小跟著視窗**：E4b 的兩個尺寸都等於 ceil(文件寬／15)。〔已觀察：E4b〕
- **第一次開 .ods 要多下載一次**（`L-ods-second-engine-download`）：檢視引擎的 wasm 36.05 MB zstd＋資源包 5.65 MB zstd，合計約 **41.7 MB**（不收 zstd 的瀏覽器走 gzip，約 55.6 MB）。中文字型包與編輯器共用，開過 ODT 的瀏覽器已經有。之後走瀏覽器快取。〔已觀察：`MANIFEST.json`；Firefox 對 48 MB gzip 留不留快取量過，上限 52,428,800（規格追加 2）〕
- **升到 0.2.29 之後，編輯器也會重抓一次**（`L-ods-editor-redownload-once`）：引擎包的 buildId 換了，所有暖快取的瀏覽器下一次開 ODT 會把編輯器的引擎檔再抓一次。設計如此，只發生一次。〔推論：SPEC-M3-zstd §3.2〕

## 3. 修好的問題

這一版沒有修編輯器的任何問題：編輯器的引擎、殼層、頁面與 0.2.28 逐位元相同（第 1 節）。0.2.27–0.2.28 發佈說明第 3、4 節照舊成立。

0.2.30 與 0.2.31 修的是 **0.2.29 自己帶進來的兩個宿主 bug**，都是 Phase H 第一、二次跑抓到的（離線閘門看不到它們，因為宿主的檢查在 H 之前沒對真的 package／頁面跑過）：

- **161**：0.2.29 的頁面表檢查拿 `./e2-editor-app.js` 去比 manifest 的 `e2-editor-app.js`，拒絕自己的 package，**編輯器與檢視器都 500**（ddev 上 23:39–00:13 編輯器不能用）。0.2.30 修。
- **162**：0.2.30 的 `scopedStyle()` 不准 `:root` 規則前面有註解，檢視頁偏偏在那裡寫了說明，**檢視文件 500**。0.2.31 修；編輯器頁的輸出逐位元不變。

## 4. 已知、沒修、使用前要知道的

### 4.1 Add-in 函數一律顯示 `#VALUE!`（`L-addin-functions-value-error`，finding 159）

- Analysis／Date／Pricing 這三組 add-in 的函數（YEARFRAC、SERIESSUM、MULTINOMIAL、CONVERT、ACCRINT 等財務函數…）在檢視引擎**一律 `#VALUE!`**。檔開得了、畫得出來，只有那些格錯；核心函數全對。檔內存的快取值不會被用，因為引擎載入時重算。
- 成因找到了：wasm 的 UNO bridge 只有 udkapi＋offapi 的呼叫簽章表，scaddins 自己的介面不在裡面。修法是重建核心（v2 批），不是改頁面。
- 語料 298 份裡 **2 份**受影響：`date-time-functions.ods`、`functions.ods`（第 2、6 張）。〔已觀察：`phase-e/159-diagnosis/`；規格 A8.8〕

### 4.2 Basic 的使用者函數顯示 `#NAME?`（`L-no-basic-udf`）

- 檢視核心沒有編進 Basic，`=MYFUNC()` 這類自訂函數讀到 `#NAME?`（桌面是函數自己的結果）。語料 1 份：`user-defined-function.ods`。〔已觀察：E3〕

### 4.3 含表單控制項的檔整份拒絕（`FORM_CONTROLS_UNSUPPORTED`，finding 158）

- 檔裡有控制項圖形（content.xml 含 `<draw:control`：按鈕、核取方塊、下拉…）的 `.ods`，檢視頁在啟動引擎之前就拒絕，畫面顯示 `已拒絕（FORM_CONTROLS_UNSUPPORTED）：…`。不是當掉，也不會白畫面。
- 原因是這顆核心沒有 `com.sun.star.form.Forms`（`HAVE_FEATURE_DBCONNECTIVITY=0`），這種檔一塊 tile 都畫不出來；先型別化拒絕，修法 158-B 是重建核心（v2 批）。
- 語料 306 份裡 **5 份**：`tdf134161.ods`、`tdf106181.ods`、`tdf121963.ods`、`tdf154005.ods`、`move-cell-anchored-shapes.ods`。控制項只在某一張表時其餘的表能不能畫，**未量**（`L-mixed-form-control-sheets-unmeasured`）。〔已觀察：E2；規格追加 8〕

### 4.4 隱藏工作表的分頁可以點、點了會被拒絕（`L-hidden-sheet-tabs-enabled`，finding 157）

- 檔裡隱藏的工作表在 v1 仍然顯示成分頁；點它，引擎切不過去，頁面顯示 `PART_READBACK_MISMATCH` 的拒絕，停在原來那一張。例：`fdo67682-2.ods`。
- v2 會讓引擎回報每張表的可見性（`part_info`），分頁就能停用。〔已觀察：E3／E4a 的讀法，規格 A7.2〕

### 4.5 只讀不寫（`L-ods-read-only`）

- 不能編輯、不能存檔、不拿鎖。要編輯試算表是 M5，不在這一版。〔設計〕

### 4.6 只開 `.ods`（`L-ods-one-file-type`）

- `.xlsx` 不提供 LiteCore 的動作（這顆核心沒有 Excel 匯入濾器）。`.odp`、`.odg` 也不在。〔讀原始碼：宿主 `src/files.js` 只收 ODS 與 ODT 的 mime；H1 判〕

### 4.7 其他登錄

- **加密的 `.ods` 不開**：語料 3 份，型別化拒絕。〔已觀察：E2〕
- **`TODAY()`／`NOW()`／`RAND()` 的表沒有逐位元證據**（`L-volatile-sheets-not-compared`）：這些表的文字是當天的函數，E3 只記錄不判。482 張裡 10 張。〔已觀察：規格 A7.3〕
- **SDK 的 `partText` 偶爾沒等到全選確認**（`L-part-text-selectall-unconfirmed`，finding 160）：482 次讀取裡 2 次，那一次讀到的文字是錯的。檢視頁畫面不用這條路（它畫 tile），受影響的是用 SDK 讀文字的程式。v2 改等待。〔已觀察：E3 第一輪；讀原始碼：頁面〕
- 檢視頁依賴已出貨 SDK 模組的底線成員（`L-viewer-sdk-private-surface`）；那些成員哪天改了，E5／E9 會紅。〔讀原始碼：規格 §3.3〕
- 開檔時的 a11y 開關在檢視引擎照跑，行為用不到。〔讀原始碼：規格 §3.2〕

## 5. 這一版證明了什麼、沒證明什麼

- **鏡像上（不經 Nextcloud）**，Phase E 的判準：E1、E2、E4a、E4b、E5、E6、E9 全綠；E3 紅的正好是 4.1、4.2 那 3 份（裁決 Q2-2 核對過 sha256）；E7（凍結集合 1,430 檔不變、E1-C intact）與 E8（資源包的切片）在連結時過。〔已觀察：`findings/evidence/m4-ods/phase-e/README.md`、`o4-post-link/README.md`〕
- **Nextcloud 上（0.2.31）**，Phase H（`findings/evidence/host-0.2.29/README.md`、`m4-ods/phase-h/shakedown/2026-10-20T222047+0000.json`）：
  - **H1 過**：ODS 與 ODT 的列選單有 LiteCore 的動作，XLSX 與 PDF 沒有。
  - **H2 過**：點 .ods 落在檢視路由；同一時窗的 Apache log 對那個檔只有 GET 與 PROPFIND，瀏覽器只送了 GET，ETag 與版本數不動。正對照：同一份 log 裡開 ODT 有 LOCK。紅案：偷拿鎖的宿主讓 H2 紅（LOCK 進了 log，ETag 也動了）。
  - **H3 過**：分頁 Alpha／Beta／Gamma 來自引擎，點 1、2、0 引擎讀回 1、2、0。
  - **H6 過**：檢視頁與編輯器頁都 200，COOP／COEP／CSP（去 nonce）相同。
  - **H4 過**（編輯器那一半不變）：0.2.28 的三支宿主臂 H-154c／H-154o／H-155 在 0.2.31 上重跑，兩個瀏覽器各 3 輪全 PASS（`findings/evidence/host-0.2.29/judge-h155.txt`）；`check_m3_host_entry.py --label shakedown`：HOST_ENTRY LANDS，Chrome open-save 3/3、conflict 3/3、broken 1/1、broken-no-save 1/1，Firefox open-save 3/3、conflict 3/3（`m3-host-entry/shakedown/2026-10-20T222436Z.json`）。
  - H5（打包工具的 selftest 13/13、`check_m3_assets.py` 的 K0／H5-1 clean、22 個紅案）：離線已過。〔已觀察：`host-0.2.29/README.md`〕
- **沒證明**：「沒改的東西沒有被弄壞」。那是計數鏈 K 的工作，K 延後併批，所以 0.2.26 的計數不涵蓋 0.2.27–0.2.29。編輯器位元組相同是**已觀察**，但計數沒跑。〔未量〕

## 6. 「未量」彙整

| 項目 | 怎麼量 |
|---|---|
| **H7：擁有者親手點 .ods**（ddev 上的 0.2.29） | 把 `wasm_sdk_probe/test-docs/ods/ladder/three-sheets-distinct.ods` 上傳到 Files，點它：應該開在檢視頁、下方三個分頁 Alpha／Beta／Gamma，點 Beta 畫面換成第二張。約 1 分鐘，第一次會多下載約 42 MB |
| H7 的注意事項（一起看） | `upstream/date-time-functions.ods`、`upstream/functions.ods`：開得了，但 add-in 函數的格是 `#VALUE!`（4.1，不是這一版的 bug 清單以外的事）。`upstream/fdo67682-2.ods`：有隱藏表的分頁，點了會顯示拒絕（4.4）。`upstream/tdf134161.ods`：整份拒絕 `FORM_CONTROLS_UNSUPPORTED`（4.3） |
| 計數鏈 K | 擁有者排時段，延後併批 |
| v2 核心重建（159 的 bridge 簽章表、158-B 的 forms；157 的 `part_info`；160 的等待） | 擁有者的 make，規格 A8.8、handoff 10-20j Next 4 |
| 混合檔（控制項只在一張表） | 158-B 之後 |
| 一顆 Calc 核心同時開 ODT 與 ODS（產品形狀） | 擁有者未決 |
| ODP／ODG | 要用 `impress` 重建核心 |

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-20 深夜 | 初稿（fable，主 session）：裁決 Q2-4 要求在 H7 之前寫好，點名 `L-addin-functions-value-error`、`L-no-basic-udf`、`L-hidden-sheet-tabs-enabled`、`FORM_CONTROLS_UNSUPPORTED`、`L-ods-read-only`。寫成時 0.2.29 已裝（23:39）、H1–H6 正在跑；結果不寫在這裡，寫在證據 README 與規格 A10 |
| 2026-10-21 早 | 版本表加 0.2.30、0.2.31（finding 161、162）；第 3 節記兩個宿主 bug；第 5 節填 H1／H2／H3／H6 在 0.2.31 上全過 |
