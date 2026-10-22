# 發佈說明（草稿）：0.2.32（ODS 檢視器換成第二顆引擎 ods-viewer-v2；未計數候選）

> **讀者是擁有者**，所以用 zh-TW。這是 `AGENTS.md`「`handoff/**` 用英文」那條的明示例外，前例是 `RELEASE-TEXT-DRAFT-0.2.29.md`。
>
> 怎麼讀：每一句宣稱後面附依據。**「已觀察」＝量過；「讀原始碼」＝沒量；「推論」＝從量過的東西推出來；「未量」＝沒有人量過。**
>
> **這是草稿，因為三件事還沒做：**
> - ~~0.2.32 還沒裝到 ddev，Phase H 還沒跑~~ → **2026-10-23 01:40 已裝，Phase H（H1–H4、H6）全過**（第 5 節）。
> - **H7（擁有者親手點 .ods）還沒做。**
> - **計數鏈 K 延後併批**：名義出貨版本仍是 **0.2.26**。
>
> 本檔是 `RELEASE-TEXT-DRAFT-0.2.29.md` 的後繼，那份照原樣留著。下面只寫 0.2.32 與 0.2.31 的差別；沒提到的（唯讀、只開 `.ods`、加密檔拒絕、編輯器那一半）**全部照舊**。
> 規格：`specs/SPEC-M4-viewer-v2.md`（§9 頁面改指 v2、§10 這個 package）。

## 1. 版本一覽

| 版本 | 宿主 commit | 引擎包 buildId | 檢視引擎 | 狀態 |
|---|---|---|---|---|
| 0.2.26 | `3c01876` | `f5f0df762e1855f2` | （沒有） | **名義出貨版本** |
| 0.2.31 | `421f4b8` | `1b4d6a1fc905fb8a` | `ods-viewer-v1`（wasm `f6ab3cdb…`） | 前一個未計數候選（10-21 06:19 – 10-23 01:40 在 ddev 上） |
| **0.2.32** | `bffc7dc` | **`80349a1a24cecb17`** | **`ods-viewer-v2`（wasm `aa576ce7…`）** | **未計數候選**。2026-10-23 01:40 裝在 ddev；Phase H 全過；取代 0.2.31 |

- **宿主程式碼沒有改**，只改了版本號。〔已觀察：`git diff 421f4b8 bffc7dc` 只有 `appinfo/info.xml` 一行〕
- **ODT 編輯器一個位元組都沒動**：編輯器頁、`e2-editor-v22` 的 profile、共用的 SDK 與字型包，共 25 檔與 0.2.31 的 package 逐位元相同。〔已觀察：`findings/evidence/host-0.2.32/manifest-diff.txt`〕
- 換掉的只有檢視器：頁面 1 檔、殼層 3 檔、檢視引擎的 profile 6 檔。〔已觀察：同上〕

## 2. 使用者看得到的改變

### 2.1 Add-in 函數不再是 `#VALUE!`（finding 159 修好）

- 0.2.31 上 Analysis／Date／Pricing 三組 add-in 的函數（YEARFRAC、COUPDAYS、CONVERT、ACCRINT…）一律 `#VALUE!`；v2 的核心把 scaddins 的呼叫簽章放進了 wasm 的 UNO bridge，這些格現在顯示的值與桌面 LibreOffice 26.8 相同。
- 語料裡受影響的 2 份（`date-time-functions.ods`、`functions.ods`）在 v2 上每張表的文字都與桌面逐位元相同。〔已觀察：`findings/evidence/m4-ods/viewer-v2/160-fix-phase-e/full-corpus/`，E3 三趟只紅在 4.1 那一份〕
- `L-addin-functions-value-error` 這條限制在 0.2.32 撤銷。

### 2.2 隱藏的工作表，分頁是灰的（finding 157 修好）

- 0.2.31 上檔裡隱藏的工作表仍顯示成可點的分頁，點了會被拒絕（`PART_READBACK_MISMATCH`）。v2 的引擎會回報每張表可不可見，頁面把隱藏表的分頁**停用**，點不下去。例：`fdo67682-2.ods` 的 12 張隱藏表。〔已觀察：V2-157，全語料三趟都過〕
- `L-hidden-sheet-tabs-enabled` 這條限制在 0.2.32 撤銷。

### 2.3 看不到、但修了：讀表格文字的等待（finding 160）

- SDK 的 `partText` 偶爾在全選還沒派送成功時就讀，讀到錯的文字（0.2.31 上 482 次裡 2 次）。v2 的引擎在派送失敗時停 50 ms 重送。全語料三趟，未確認 0 次；6 次派送失敗都被引擎記下、重送後確認。〔已觀察：V2-160、V2-160-D〕
- **檢視頁畫面不走這條路**（它畫 tile、不讀文字），所以使用者在 0.2.32 上看不到差別；受惠的是用 SDK 讀文字的程式與我們的量測。〔讀原始碼：`web/ods-viewer-app.js` 沒有呼叫 `partText`〕

## 3. 下載

- **第一次開 .ods 要再下載一次檢視引擎**：v2 的 wasm 36.05 MB zstd＋資源包 5.65 MB zstd，約 **41.7 MB**（與 v1 幾乎一樣大）。〔已觀察：`MANIFEST.json`〕
- **裝上 0.2.32 之後，第一次開 ODT 也會重抓一次編輯器的引擎檔**（`L-ods-editor-redownload-once` 再發生一次）：buildId 換了，暖快取的瀏覽器會到新位址抓。內容沒變，只是位址變了。〔推論：SPEC-M3-zstd §3.2；0.2.29 安裝時發生過〕

## 4. 沒變的限制（照 0.2.29 的說明）

### 4.1 Basic 的使用者函數顯示 `#NAME?`（`L-no-basic-udf`）

- v2 的核心一樣沒有 Basic。語料 1 份：`user-defined-function.ods`。〔已觀察：E3 三趟都紅在這一份，也只紅在這一份〕

### 4.2 含表單控制項的檔整份拒絕（`FORM_CONTROLS_UNSUPPORTED`，finding 158）

- **v2 沒有修 158。**原本計畫讓 v2 的核心帶表單元件（158-B），但那顆核心讓含表單的 6 份檔開不了，擁有者選了退路：v2 連在與 v1 相同的核心上，只多 159 的修法（規格 §7.1）。
- 所以和 0.2.31 一樣：檔裡有控制項的 `.ods` 在啟動引擎之前就型別化拒絕。語料 5 份（`tdf134161.ods` 等）。158-B 是另外的工作項。〔已觀察：§8.5 定向執行，5 份照 158-A 拒絕〕

### 4.3 其餘

- 唯讀（`L-ods-read-only`）、只開 `.ods`（`L-ods-one-file-type`）、加密檔拒絕、`TODAY()` 類的表只記錄不判（`L-volatile-sheets-not-compared`）、依賴 SDK 的底線成員（`L-viewer-sdk-private-surface`）：照舊。

## 5. 這一版證明了什麼、沒證明什麼

- **鏡像上（不經 Nextcloud），`aa576ce7`**：E1、E2、E4a、E5、E6、V2-157、V2-160、V2-160-D 全語料三趟都過；E3 只紅在 4.1 那一份；**E4b、E9 在產品頁自己的路上過**（頁面改指 v2 之後），E4b 的紅案在 v2 上照樣重現。〔已觀察：`160-fix-phase-e/README.md`、`160-fix-phase-e/e4b-e9/README.md`〕
- **離線（H5）**：打包工具 selftest 13／13；K0／Z0／H5-1 對這份 package 0 個問題、22 個紅案全紅；同一支檢查對 0.2.31 的 package 紅 22 條（負對照）。〔已觀察：`findings/evidence/host-0.2.32/`〕
- **Nextcloud 上（0.2.32）**，Phase H（`findings/evidence/host-0.2.32/README.md`、`m4-ods/phase-h/shakedown/2026-10-22T174116+0000.json`）：
  - **H1 過**：ODS 與 ODT 的列選單有 LiteCore 的動作，XLSX 與 PDF 沒有。
  - **H2 過**：點 .ods 落在新位址的檢視路由；Apache log 對那個檔只有 GET 與 PROPFIND，瀏覽器只送 GET，ETag 與版本數不動。正對照：開 ODT 有 LOCK。紅案：偷拿鎖的宿主讓 H2 紅。
  - **H3 過**：分頁 Alpha／Beta／Gamma 來自引擎、三個都可用，點 1、2、0 讀回 1、2、0。
  - **H6 過**：檢視頁與編輯器頁都 200，COOP／COEP／CSP（去 nonce）相同。
  - **宿主送的真的是 v2**：Apache log 在那個時窗只有 `profiles/ods-viewer-v2/` 的檔，沒有 v1 的請求。〔已觀察：`access-log-viewer-engine.txt`〕
  - **H4 過**（編輯器那一半不變）：H-154c／H-154o／H-155 兩個瀏覽器各 3 輪全 PASS；`check_m3_host_entry.py`：HOST_ENTRY LANDS。
- **沒證明**：「沒改的東西沒有被弄壞」——那是計數鏈 K，延後併批。〔未量〕

## 6. 「未量」彙整

| 項目 | 怎麼量 |
|---|---|
| **H7：擁有者親手點 .ods** | 上傳 `wasm_sdk_probe/test-docs/ods/ladder/three-sheets-distinct.ods`，點它：三個分頁 Alpha／Beta／Gamma，點 Beta 換成第二張。想看這一版的差別，再開 `upstream/functions.ods`（add-in 函數的格有值了）與 `upstream/fdo67682-2.ods`（隱藏表的分頁是灰的） |
| 計數鏈 K | 擁有者排時段，延後併批 |
| 158-B（表單控制項） | 另外的工作項（finding 158） |

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-23 凌晨 | 初稿：0.2.32 建好、離線檢查過、未安裝 |
| 2026-10-23 01:50 | 0.2.32 已裝（01:40），Phase H 全過；版本表、第 5、6 節更新 |
