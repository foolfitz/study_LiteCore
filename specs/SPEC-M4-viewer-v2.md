# SPEC-M4-viewer-v2：檢視引擎 v2——核心批次（159、158-B）與檢視連結（157、160）

> 建立：2026-10-21。上游：`specs/SPEC-M4-ods-in-nextcloud.md`（v1 的規格與追加 1–10）。
> 本檔第一次 commit 只有 §0–§2（核心）；§3 以後（引擎、殼層、判準）在**連結之前**追加，照 CLAUDE.md §10 只 append。

## 0. 來源與範圍

**擁有者的決定**（照時間）：

- 2026-10-20 深夜「三件事照你建議」：157（隱藏表）與 160（SelectAll 等待）併進 v2；159 先診斷、修法是核心重建，併進 v2；
  158 先做 A（型別化拒絕，已落地，SPEC-M4 追加 8），B（核心有表單元件）留在 v2 的核心批次。
- 2026-10-21：我回報 158-B 的代價比原估大（Emscripten 上 `configure.ac` 兩處無條件關掉 DB connectivity，要改 configure、整顆重編，
  forms／connectivity 從沒在這棵樹的 wasm 上編過，fs image 會變）並建議拆出去；擁有者答「重編其實無所謂」。**158-B 留在 v2**（D-1）。

**在範圍內**：新核心樹 `wasm-lite/build-ods-viewer-v2`；新 profile `ods-viewer-v2`；檢視殼層為 `part_info` 與表單控制項做的改動；v2 上的 Phase E。
新 package 與 Phase H 是之後的事，另寫。

**一個位元組都不動**：`e2-editor-v22` 與它的核心 `build-headless-probe`；`ods-viewer-v1`（凍結、已封存）與它的核心 `build-a11y-gate0`
（不重建）；宿主 0.2.31 與 package `1b4d6a1fc905fb8a`（v2 的 package 通過 Phase H 之前，ddev 上的就是它）。

**160 的嚴重度更正**（已觀察，2026-10-21）：產品頁面（`web/ods-viewer-app.js`、`viewer-shell/ods-viewer-session.js`、`w7-adapter.js`）
**沒有任何地方呼叫 `partText`**；呼叫它的只有 Phase E 的 E3。所以 160 是 E3 的量測儀器與 SDK 能力 `part-text` 的正確性問題，
不是使用者會看到的錯字。finding 160 寫的「在產品路徑上就是讀到錯的文字」以此為準修正。

## 1. 一次兩個變因：取捨與預先寫好的讀法

這顆核心同時改兩件事（159 的 bridge 簽章、158-B 的 DB connectivity）。擁有者接受了重建的代價；歸因靠的是：

- 每件事有**自己的**證人：159 是 K-2 的簽章集合與 V2-159 的格子；158-B 是 K-2 的元件清單與 V2-158B 的五份檔。
- **預先寫好的讀法**：v2 的 Phase E 若在 157／158／159／160 以外的檔上出現 v1 沒有的紅，第一個診斷動作是**一顆只帶 159 的核心**
  （`build-a11y-gate0` 增量，§2.5 的 F 路線，幾分鐘），不是推理哪一個變因比較可疑。

## 2. 核心（K）

### 2.1 新樹與它的輸入

- 目錄：`wasm-lite/build-ods-viewer-v2/`（新建；`build-a11y-gate0` 不動，理由同 2026-08-22 a11y 閘門 0：原地重建會毀掉 v1 的核心，
  而 wasm 建置不可重現）。
- `autogen.input`：`build-a11y-gate0/autogen.input` 的 10 行**原樣**，加 4 行：

  ```
  --enable-database-connectivity
  --disable-firebird-sdbc
  --disable-mariadb-sdbc
  --disable-postgresql-sdbc
  ```

  後三行的理由：DB connectivity 一開，`disable_database_connectivity_dependencies` 就不會被呼叫，三個驅動在 Emscripten 上的預設是開
  （`configure.ac` 的 `libo_FUZZ_ARG_ENABLE`，以及 firebird 的 `enable_firebird_sdbc=yes` 預設），它們要外部函式庫。
  report builder 不用另外關（`with_java=no` 在 `DISABLE_DYNLOADING` 區塊照舊成立）。galleries 不用另外關（`enable_wasm_strip` 區塊的
  `with_galleries=no` 照舊）。dbaccess 仍由 `ENABLE_WASM_STRIP_DBACCESS` 拿掉。
- `env.sh`：`build-a11y-gate0/env.sh` 只改 `LO_BUILD`。emsdk 4.0.10、`LITE_EXTRA_FONTS_DIR` 照舊。
- 原始碼 patch：`wasm-lite/patches/INVENTORY.md` 的八份；這次新增兩份——`wasm-bridge-scaddins-signatures`（159）與
  `wasm-explicit-database-connectivity`（158-B）。兩份都改共用的 `libreoffice-26-8`；另外兩棵樹下次 `make` 會先重跑一次 autogen，
  結果應該不變（INVENTORY 有寫）。

### 2.2 159 的修法在建置之前已經量過一半

`findings/evidence/m4-ods/phase-e/159-diagnosis/bridgegen-offline/`：用 `build-a11y-gate0` 已建好的 build-side `wasmbridgegen`
離線跑——不加 scaddins 時輸出與核心現有的三個檔**逐位元相同**（正向對照），加了之後簽章 55 → 80，SERIESSUM／MULTINOMIAL／YEARFRAC／
COUPDAYS 的 `didddi`／`diiii`／`diiiii`／`diiiiii` 都進表。**順帶更正 finding 159**：SERIESSUM 的簽章是 `didddi` 不是 `didddd`，
而原本「`generated-cxx.cxx` 裡出現 `didddd`」的子字串檢查會被另一個方法的 `didddddd` 滿足——對的結論、錯的理由。

### 2.3 K-1：configure 之後、`make` 之前（判偽器）

工具：`wasm_sdk_probe/tools/check_ods_viewer_v2_core.py --stage configure --build DIR`。全部成立才開始 `make`：

| # | 讀什麼 | 要求 |
| --- | --- | --- |
| K-1a | `config_host/config_features.h` | `#define HAVE_FEATURE_DBCONNECTIVITY 1` |
| K-1b | `config_host.mk` 的 `BUILD_TYPE` | 含 `DBCONNECTIVITY` |
| K-1c | `config_host.mk` | `ENABLE_WASM_STRIP_DBACCESS=TRUE`；`ENABLE_FIREBIRD_SDBC`、`ENABLE_MARIADBC`、`BUILD_POSTGRESQL_SDBC` 為空 |
| K-1d | `config_host.mk`、`config_host/config_wasm_strip.h` | `ENABLE_WASM_STRIP_CALC`、`ENABLE_WASM_STRIP_ACCESSIBILITY` 為空；巨集 `ENABLE_WASM_STRIP_ACCESSIBILITY 0`（與 `build-a11y-gate0` 相同） |
| K-1e | `autogen.input` 對 `build-a11y-gate0/autogen.input` | 差異恰好是 §2.1 的 4 行，沒有別的 |

**紅案**：同一支工具對 `build-a11y-gate0` 必須紅在 K-1a／K-1b（那顆核心 `HAVE_FEATURE_DBCONNECTIVITY 0`），否則工具本身壞了
（CLAUDE.md §6）。**如果 K-1 永遠沒做**：不開始 `make`。

### 2.4 K-2：`make` 之後、連結之前

同一支工具 `--stage built`：

| # | 讀什麼 | 要求 | 形式 |
| --- | --- | --- | --- |
| K-2a | `workdir/CustomTarget/bridges/gcc3_wasm/generated-cxx.cxx` 的 `callVirtualFunction_*` **完整符號**集合 | 含 `didddi`、`diiii`、`diiiii`、`diiiiii`（逐字比對，不准前綴） | 硬性 |
| K-2b | 同上 | 等於 `bridgegen-offline/signatures-scaddins.txt`（80 個） | 登錄；不等就先讀差在哪再連結 |
| K-2c | `workdir/CustomTarget/postprocess/services_constructors.list` | 含 `com_sun_star_form_OFormsCollection_get_implementation`，以及 scaddins 的三個（`scaddins_AnalysisAddIn_get_implementation`、`scaddins_ScaDateAddIn_get_implementation`、`scaddins_ScaPricingAddIn_get_implementation`，`build-a11y-gate0` 也有） | 硬性 |
| K-2d | 同上 | 不含任何 `com_sun_star_comp_dba_` 開頭的（dbaccess 應被 strip） | 登錄 |
| K-2e | `instdir/program/soffice.js.linkdeps`、`soffice.data`、`soffice.data.js.metadata`、`workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link`、`workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports` | 都存在且非空；sha256 與大小登錄 | 硬性（存在）＋登錄 |
| K-2f | `instdir/program/soffice.wasm` 與 `soffice.data` 的大小 | 與 `build-a11y-gate0` 並列登錄 | 登錄（判在 §2.5 F-2，連結時） |

**紅案**：對 `build-a11y-gate0` 必須紅在 K-2a 與 K-2c。**如果 K-2 永遠沒做**：v2 不連結。

### 2.5 預先宣告的退路（F）

三種情況走同一條退路，**預設**如下；擁有者當時可以改：

- **F-1**：DB connectivity 那幾個模組編不過（finding 003 的重試一次之後仍失敗）。
- **F-2**：連結出來的 v2 wasm 經 gzip 超過 **52,428,800**（SPEC-M4 追加 2 量到的 Firefox 快取上限；packager 會拒絕）。v1 是 47.97 MB，
  餘裕約 4.46 MB；forms＋connectivity 的體積**未量**。
- **F-3**：V2-158B 那一臂失敗（核心有 forms，但控制項畫不出來或畫錯）。

**退路**：v2 改成只帶 159——在 `build-a11y-gate0` 上刪掉 `workdir/CustomTarget/bridges/gcc3_wasm/` 的三個產物再 `make`
（patch 已在原始碼裡；`scaddins.rdb` 比產物舊，不刪不會重產），檢視 v2 改連這顆。K-2a／K-2b 照判，K-2c／K-2d 免判；158-A 的型別化拒絕
繼續是產品的答案；158-B 另立工作項並把失敗的那一步寫成 finding。**原則：v2 要嘛帶著畫得出來的表單控制項出貨，要嘛完全不帶 DB connectivity**——
不出貨「核心有 forms、殼層卻還在拒絕」或反過來的組合。

### 2.6 修訂紀錄

| 日期 | 變更 |
| --- | --- |
| 2026-10-21 | 建立 §0–§2（核心）；§3 起在連結前追加 |

---

## 3. 引擎與殼層（2026-10-21 追加；任何 v2 連結之前）

### 3.1 引擎介面

- 新 define **`OXSDK_ODS_VIEWER_V2`**，疊在 v1 的 `OXSDK_READER_PROFILE`＋`OXSDK_ODS_VIEWER` 之上；單獨使用是編譯錯誤（`probe_engine.cpp`、
  `sdk_api.cpp` 各一個 `#error`，紅案已試）。**v1 的 define 下兩個原始檔前置處理後的 token 與 HEAD（`17c5d50b`）相同**：`sdk_api.cpp`
  逐位元相同，`probe_engine.cpp` 只差一個空行（`diff -B` 相同）〔已觀察，2026-10-21，對 `build-a11y-gate0` 的標頭〕。
- 新匯出 **`oxsdk_document_part_info(request, handle, part)`** → 回覆 `part-info`，欄位 `part` 與 `info`（LOK `getPartInfo` 的 JSON，原樣
  當字串；SDK 解析，同 page-rectangles 的前例）。`getPartInfo` 回空字串（`ScDocShell::GetViewData()` 沒有 view）算 `LOK_ERROR`，不算可見。
- 能力位元：`PART_INFO = 1<<14` 一律有；**`FORM_CONTROLS = 1<<15` 只在編譯時核心的 `config_features.h` 說 `HAVE_FEATURE_DBCONNECTIVITY 1`
  時才有**——引擎讀的是規則 `-I` 進來的那棵核心的標頭，不是任何人宣告的。退路 F（連在 `build-a11y-gate0`）自動沒有這一位。
- worker：`partInfo` 由能力 `part-info` 閘住；`part-info` 回覆只轉具名欄位；`part-text` 的三個新欄位只在引擎送了才轉（v1 的回覆鍵不變）。

### 3.2 隱藏表（finding 157）

- SDK（`viewer-shell/ods-document-sdk.js`）：profile 宣告 `part-info` 時，開檔時在名字之後對每張表問一次，`visible` 只接受 0／1（數字或字串），
  得到 `handle.partVisible`（布林陣列）。**任何一張失敗都不讓開檔失敗**：handle 沒有 `partVisible`，`partInfoProblem` 寫原因。
- adapter：`partVisible` 合格（長度＝parts、全是布林）才用；否則 fallback **`part-visibility-unknown`**（全部當可見，即 v1 的行為），
  問題寫進 `partVisibilityProblem`。停用理由「隱藏的工作表」住在 adapter（session 的詞彙掃描不准別處有「工作表」）。
- session：隱藏表的 tab `enabled: false`、`hidden: true`、`disabledReason` 為上述理由；`showPart(隱藏表)` 在問引擎之前拒絕 **`PART_HIDDEN`**。
- 對 v1 profile 的影響（**已知、刻意**）：新殼層配 v1 引擎時 state 會多一個 fallback、`evidenceClass` 變 `diagnostic`——那是誠實的，
  v1 引擎確實沒說哪張是隱藏表。出貨的組合（package 的頁面表）是新殼層配 v2。

### 3.3 SelectAll 的等待（finding 160）

- 期限 3 s → **10 s**（只在 V2）。`part-text` 回覆加 `selectAllWaitMs`（實際等了多久；-1 表示沒走到）、`selectAllDeadlineMs`、
  `lateSelectAllResults`（自上一次 `part-text` 回覆以來，沒人在等時到達的 SelectAll 結果數）。
- **預先寫好的讀法**：某次 `selectAllConfirmed: false`，而**下一次**回覆的 `lateSelectAllResults > 0` → 結果是晚到（期限仍短）；
  整輪結束都沒有晚到的 → 結果沒來。兩者都不在 harness 裡重試（finding 160 的原則照舊）。
- 更正（§0）：產品頁面不呼叫 `partText`，這是 E3 儀器與 SDK 能力的問題。

### 3.4 表單控制項（finding 158-B）的殼層

- session 新選項 **`formControlsSupported()`**：**只在** package probe 說這份檔有 `<draw:control` 時才問、而且在建立任何引擎之前問；
  回 `true` 才繼續開，其他任何答案（含丟例外）都照 158-A 拒絕 `FORM_CONTROLS_UNSUPPORTED`、`engineRequested: false`。
  state 加 `formControlsDrawable`（沒問是 null）。沒給這個選項＝不支援（158-A 不變）。
- 頁面（`web/ods-viewer-app.js`）的實作：讀 worker 旁邊的 `sdk-manifest.json`，看 `capabilities` 有沒有 `form-controls`。worker 在 init 時
  要求 manifest 的 `expectedCapabilityBits` 等於引擎回報的位元，所以 manifest 宣告了核心沒有的 forms，**每一份檔**都會在 init 失敗，
  不會變成「只有這份是空白畫布」。頁面的 worker 字面值仍是 v1 的；換成 v2 是打包時的事（照 v1 的前例，鏡像執行改自己的副本）。

### 3.5 profile 建構（E8′，取代 E8 對 v2 的讀法）

`tools/build_ods_viewer_v2_profile.py`：

- **程序**是 v14 的：`build_r5_profiles.classify()` 對核心 fs image 分出的 base 群組。**正向對照每次都跑**：同一程序在 `build-a11y-gate0`
  上必須重現 `9901e9be`（2026-10-21 實測：1,489 檔，逐位元相同）。
- v2 的 base＝v2 核心的 base 群組減 `35-lang-normalize.conf`（與 v1 相同的那一個檔，必須恰好出現一次）。
- **與 v1 base 的差異只登錄不判**（新增／移除／內容變動的檔名與大小，寫進 `--report`），連結交出去之前讀過、寫進 §5。
  第二個正向對照：`--core build-a11y-gate0` 時差異必須是 0／0／0，sha 等於 v1 的 `6f7424a1…`（實測成立）。紅案：`--red-drop` 多拿掉一個檔，
  差異的 removed 必須看得到它（實測成立）。
- CJK／fallback 包是 v1 的（路徑引用）。manifest：v1 的形狀＋`part-info`，核心有 forms 時＋`form-controls`（與 3.1 讀同一個標頭）。

### 3.6 Makefile 與靜態檢查

- 規則 `ods-viewer-v2`（`wasm_sdk_probe/Makefile`，v1 規則之後）：v1 的連結行逐 token 相同，只有核心路徑跟著 `ODS_VIEWER_V2_CORE`
  （預設新樹，退路 F 用 `ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0`）、define 多一個、匯出多一個；第一次就有凍結守衛。
  連結後的位元組檢查：`search-result`（正向對照）、`partBefore`、`lateSelectAllResults` 必須在，`verified-caret-readback` 必須不在；
  並**印出** wasm 的 gzip 大小（packager 的量法：level 9、mtime 0），F-2 當場就看得到。
- worker 釘在 `9c85043a…`。
- `test-e2-c-static` 的 carrier 宣告加 `ODS_VIEWER_V2=probe_engine,sdk_api`；宣告前且核心未 configure 時它紅在恰好 v2 的物件上
  （證人 `findings/evidence/m4-ods/viewer-v2/pre-link/test-e2-c-static-red-v2-not-declared-core-not-configured.txt`）。
  **核心 configure 之前它會一直紅**（`config_features.h` 不存在）——這是真的紅，不是要繞過的東西。

### 3.7 測試與紅案（2026-10-21）

| 範圍 | 綠 | 紅案 |
| --- | --- | --- |
| worker（`sdk/tests/sdk-worker-ods-viewer.test.mjs`） | 11／11 | 新 4 條在 HEAD 的 worker 上全紅；把「有才轉送」改成一律轉送，那一條紅；既有 7 個 mutation 全部 red as required |
| SDK＋session（`tests/ods-document-sdk.test.mjs`、`tests/ods-viewer-session.test.mjs`） | 45／45 | 新 10 條在 HEAD 的殼層上全紅，其餘 35 條在 HEAD 上照過；`ods_document_sdk_mutations.py` 全部 red as required |
| 核心判偽（`check_ods_viewer_v2_core.py --self-test`） | — | gate0 上紅在 K-1a／K-1b、K-2a／K-2c；用離線 bridge 輸出拼的假樹全綠 |
| 引擎 | `em++ -fsyntax-only` 兩種 define 都過 | V2 單獨使用 → `#error` |

§34 計數：`tests/sdk_worker_ods_viewer_mutations.py` 的 `reply-forwarded-whole` 錨點因產品改動失效（0 次）→ 改成新原文的前四行、
替換成 `{ ...event,`（意圖不變）——**因執行而修 +1**，證人 `findings/evidence/m4-ods/viewer-v2/pre-link/sdk-worker-mutations-red-anchor-drift.txt`。
另外**登錄、不修**：`findings/evidence/m4-ods/W9-viewer-draft/red-cases.py` 的 M31–M35 錨點從 158-A（`f0351130`）起就對不上了（不是本輪造成；
本輪誤跑了一次，它覆寫的兩個證據檔已還原成 commit 的版本）。

## 4. v2 的判準（Phase E 在 `ods-viewer-v2` 上；釘在任何 v2 執行之前）

SPEC-M4 §4 的 E1–E9 照舊，在 v2 的連結上全部重跑（連結換了，計數歸零）。改了讀法的只有下列各條；新增的照 CLAUDE.md §9 的四個條件
（先於滿足、由 157–160／158-B 逼出、形式一或二、第一筆乾淨的 v2 Phase E 落地即封閉）。

| id | 判準 | 形式 | 永遠沒做的預設結論 |
| --- | --- | :---: | --- |
| **V2-157** | 每筆、每張表：`state.partVisible[k] === !hiddenParts.includes(k)`（`hiddenParts` 由 runner 從 content.xml 推，A7.2 的同一支）。隱藏的 k：tab `enabled === false`、`showPart(k)` 拒絕 `PART_HIDDEN`、讀回不變、這一次沒有 `setPart` 到 worker。**取代** A7.2 對隱藏表的 E5 讀法（v1 是「拒絕且讀回不是它」＝`PART_READBACK_MISMATCH`）；E3／E4a 照舊略過隱藏表 | 1 | v2 不打包 |
| **V2-159** | E3 對 `upstream/date-time-functions.ods`、`upstream/functions.ods` **綠**（`L-addin-functions-value-error` 解除）。登錄（不判）：`probe-159.ods` 的 20 格引擎文字，與 finding 159 表中桌面那一欄並列 | 1 | 159 沒修；`L-addin-functions-value-error` 留著 |
| **V2-158B** | profile 宣告 `form-controls` 時：每筆 `formControls === true` 的檔（runner 從 package probe 推；目前是 finding 158 的 5 份）**開得了**（E2 的開檔條件）、E4a（每張表的 tile OK）與 E3（文字＝期望）成立。**取代**追加 8 對這幾份的 E2 期望（拒絕）。失敗 → 退路 F-3 | 1 | 158-B 沒修；退路 F |
| **V2-160** | 全語料 E3 跑 **N＝3** 次：每次 `selectAllConfirmed: false` 為 0。每次登錄 `selectAllWaitMs` 的最大值與 p99、`lateSelectAllResults` 的總和。不是 0 的那一次照 3.3 的讀法定性，E3 在那些讀取上照舊紅 | 1 | 160 只是把期限拉長，沒量 |
| **E8′** | 3.5：正向對照成立、DROP 恰好一次、差異已登錄並讀過；CJK／fallback 包是 v1 的位元組；`soffice.js.linkdeps` 是規則指名的核心的；`check_core_build_provides.py --capability calc-spreadsheet` 對它通過 | 1 | profile 可能帶錯核心；停 |
| **F-2** | 連結後印出的 wasm gzip ≤ 52,428,800 | 1 | 退路 F |

計數語意：V2-* 與 E8′ 只對 v2 的連結；v2 換連結（wasm sha 變），全部重來。E6 的 B 在 v2 上重新量（M8 的程序）再算數。

### 4.1 修訂紀錄（續）

| 日期 | 變更 |
| --- | --- |
| 2026-10-21 | 追加 §3（引擎、殼層、profile、靜態檢查、測試）與 §4（V2-157／159／158B／160、E8′、F-2），任何 v2 連結與執行之前 |

## 3.8 Phase E 的 runner 與 harness（2026-10-21 追加；任何 v2 執行之前）

- SDK 的 `partText()` 也要轉出三個等待欄位（引擎有送才轉），否則 V2-160 在 SDK 這一層就讀不到；測試 46／46，新的一條在 HEAD 殼層上紅。
- harness 頁面（`web/ods-viewer-e-harness-app.js`）：worker 字面值抽成單一常數（仍是 v1 的；runner 對別的 profile 只改**鏡像副本**，且要求恰好
  一個）；給 session `formControlsSupported`（同產品頁的讀法）；每次 `showPart` 記 `setPartCalls`（實際打到 handle 的切換數）；切換失敗時記
  `readBackAfterError`；`part-text` 的三個等待欄位。
- runner（`tools/run_ods_viewer_phase_e.py`）：`--profile`，報告記 `profileCapabilities`；**讀法跟著 profile 宣告的能力走**——有 `part-info`：
  E5 對隱藏表要 `PART_HIDDEN`＋`setPartCalls 0`＋讀回不是它，並跑 V2-157、V2-160；有 `form-controls`：含控制項的檔照一般檔判（E2–E6），
  並跑 V2-158B 列出它們。沒宣告的 profile 不跑任何 V2 判準（空的判準清單在 `judge()` 是 FAIL，所以不能讓它空跑）。
  selftest 31 → **43**：v2 控制組全綠、10 個 v2 紅案各紅在該紅的判準。
- **在 v1 上實跑過一次**（鏡像，不碰 ddev；證據 `findings/evidence/m4-ods/viewer-v2/pre-link/v1-shakedown-new-shell/`）：E1–E6 PASS；
  新殼層配 v1 引擎報 `part-visibility-unknown`；隱藏表照 v1 的路被引擎讀回 11（`setPartCalls 1`），含控制項的檔 `formControlsDrawable: false`。
- §34：這是把 §4 釘好的讀法落地，**不是**因執行或因審核而修（沒有被誤判的報告）。runner 曾審過一次；這次的增量是否需要審，交下一個
  session 或審核席決定（登錄在交接）。

## 2.7 第一次建置：F-1 被觸發，擁有者覆寫（2026-10-22 追加）

- 10-21 10:43 第一次 `make`：0 分鐘死在 `workdir_for_build/UnpackedTarball/dragonbox.version`，與 finding 003 逐字相同（同檔、同行）。K-1 全綠
  （`findings/evidence/m4-ods/viewer-v2/core/k1-configure.json`）。
- 10-21 10:53 `--make-only`（003 允許的那一次重試）：2 分鐘後失敗；**它的 log 被下一次執行覆寫，已遺失**。腳本已改成每次一份 log、失敗時自動存最後 200 行。
- 10-22 00:26 再一次 `--make-only`：`LinkTarget.mk: *** used LinkTarget Library/libdbulo.a not defined`（`…/core/build-20261022T002600-dbu-tail200.txt`）。
  成因（讀原始碼）：reportdesign 在 DB connectivity 打開時被加進模組清單，它的 `Library_rpt`／`Library_rptui` 連 dbaccess 的 `dbu`，而 dbaccess 被
  `ENABLE_WASM_STRIP_DBACCESS` 拿掉——**上游 DBCONNECTIVITY＋WASM_STRIP_DBACCESS 的組合本身不一致**。普查：dbaccess 的五個函式庫在 dbaccess 以外只有
  reportdesign 用到。
- 這是 §2.5 的 **F-1**（DB connectivity 那組在 003 重試之後仍建不過）。擁有者選 **A：補一行再建**（覆寫預設）。patch
  `wasm-lite/patches/libreoffice-26.8-wasm-reportdesign-follows-dbaccess-strip.patch`：reportdesign 與 dbaccess 同進退（只影響開了 DB connectivity 的 wasm 建置）。
  不是 configure 的輸入，K-1 仍成立。
- **下一次的讀法（先寫好）**：再失敗、且失敗點在 DB connectivity 帶進來的模組（forms、connectivity、dbtools、reportdesign 以外任何因 DBCONNECTIVITY
  才進來的）→ 直接走 F-1，**不再逐一補洞**，除非擁有者當場另說；失敗點在別處（例如 159 的 bridge）→ 先讀 log 再判。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §2.7：F-1 觸發與擁有者覆寫、第三個核心 patch、下一次的讀法 |

## 5. 核心建好之後、連結之前（2026-10-22 追加）

### 5.1 K-2

`build-ods-viewer-v2` 第四次 `make`（§2.7 的 patch 之後）45 分鐘，exit 0；K-1、K-2 全綠（`findings/evidence/m4-ods/viewer-v2/core/k2-built.json`）：

- K-2a／K-2b：bridge 簽章 **80 個，與離線輸出的集合完全相同**（K-2b 原本只登錄不判，結果也相等）。
- K-2c／K-2d：元件建構子 700 → **783**，含 `OFormsCollection` 與 scaddins 三個；沒有任何 `com_sun_star_comp_dba_`。
- K-2f（登錄）：`soffice.wasm` 149,208,138 → 153,330,836（+4.12 MB）；`soffice.data` 108,527,803 → 108,568,339（+40 KB）。樹 6.0 GB。

### 5.2 E8′ 的差異讀過了（3.5 要求連結前讀）

`build_ods_viewer_v2_profile.py --check`：正向對照成立（9901e9be），base `07ef15cd857a404b`（1,488 檔），對 v1 的 base：0 新增、0 移除、**9 變動**、1,479 相同
（`…/viewer-v2/pre-link/base-pack-check.json`）。逐個判讀：

| 檔 | 大小 | 讀法 |
| --- | --- | --- |
| `program/services/services.rdb` | +22,903 | 新元件的登錄（forms、connectivity）〔由此推論〕 |
| `share/registry/main.xcd` | +11,045 | postprocess 在 DBCONNECTIVITY 下加入的 `Drivers-dbase/flat/odbc.xcu`（`CustomTarget_registry.mk:444-449`）〔由原始碼推論〕 |
| `share/registry/calc.xcd`、`writer.xcd` | +1,216、+1,217 | 同上的 `Drivers-calc.xcu`、`Drivers-writer.xcu`（`:453-460`） |
| `share/registry/res/registry_{en-US,qtz,zh-TW}.xcd` | +715、+1,736、+1,704 | 上面那些驅動設定的語系字串 |
| `presets/autotext/mytexts.bau`、`share/config/images_colibre.zip` | ±0 | **zip 內容逐項相同**（檔名、CRC、大小），只有建置時間戳不同〔已觀察〕 |

字型、fontconfig、其他設定都沒有變。判讀：差異全部是 DB connectivity 本身帶來的或時間戳，沒有意外。

### 5.3 F-2 的推估（判定在連結後）

兩顆核心的 `soffice.wasm` 以 packager 的量法（gzip 9、mtime 0）：48,418,550 → 49,572,266（+1,153,716）。加到 v1 檢視引擎實測的 47,987,215 上，
**推估 v2 約 49,140,931，離 52,428,800 還有約 3.3 MB**〔推論：檢視引擎的 wasm 不是核心的 `soffice.wasm`，增量假設相近〕。連結規則會印出實際值。

### 5.4 連結前閘門的其餘結果

- `make -k test-e2-c-static` exit 0（`…/pre-link/test-e2-c-static-green-v2-core-built.txt`）：490＋5 條過，carrier 檢查對 ODS_VIEWER_V2 可判，v2 加 merge-key-undo 被拒。
- `check_core_build_provides --capability calc-spreadsheet` 對 v2 核心 exit 0。
- `make -n` 兩條連結指令逐 token：只差物件、核心路徑、匯出清單路徑、輸出路徑（`…/pre-link/link-token-diff-v1-v2.txt`）。
- 以 v2 核心的標頭 `em++ -fsyntax-only` 三個單元 0 錯誤；`HAVE_FEATURE_DBCONNECTIVITY 1` 進到 `sdk_api.cpp`。
- 凍結集合快照 1,517 檔（`…/pre-link/frozen-set-before.sha256`）。
- **我的工具的 bug，第一次用 `--report` 就露出來**：`build_ods_viewer_v2_profile.py` 的報告寫入對 `Path` 序列化失敗（`TypeError`）；打包時也會走這條路，所以若沒在這裡抓到，連結會死在打包。修法：`json.dumps(..., default=str)`。這支工具還沒判過任何東西，不算 §34 的計數。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §5：K-2、E8′ 差異的判讀、F-2 推估、連結前閘門 |

## 6. 連結（2026-10-22 追加）

擁有者連結完成。**`ods-viewer-v2` 的身分：probe.wasm `a6390eef…`**、worker `9c85043a…`、manifest `0bfa28f7…`、base `07ef15cd…`；當下封存於
`wasm_sdk_probe/build/archive/ods-viewer-v2-a6390eef-worker-9c85043a/`。連結後核對全部成立（`findings/evidence/m4-ods/viewer-v2/post-link/`）：凍結集合不變、
堆疊常數、v2 的三個特徵字串在而編輯器的不在、Calc 與 forms 進了 wasm、manifest 宣告 `part-info`＋`form-controls`（63539）、E1-C 完好。

- **F-2 不成立**：gzip 49,153,029（上限內 3,275,771；§5.3 的推估差 12 KB）。
- make 最後以 `Error 1` 結束，是規則**最後一行**印 gzip 大小的 Python 引號錯誤（我寫的）；它在所有檢查之後、只印資訊。已修 Makefile，修好的那一行對這顆 wasm 手動實跑過。
  因為改了 Makefile，v2 的目標此後都「過期」，再連結會被凍結守衛擋下——那正是要的。

接下來：§4 的 Phase E 在這顆連結上跑（計數從這裡開始）。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §6：連結、身分、封存、F-2 不成立、Makefile 印 gzip 那行的修正 |

## 7. v2 `a6390eef` 上的第一次 Phase E：157／159／160 過，158-B 觸發 F-3（2026-10-22 追加）

兩次鏡像執行（`findings/evidence/m4-ods/viewer-v2/phase-e/`，README 有逐項）：

- **V2-157 PASS**、E5 PASS：`fdo67682-2.ods` 的 12 張隱藏表 `partVisible: false`、tab 停用、`PART_HIDDEN`、0 次切換打到 handle。
- **V2-159 的硬性那半 PASS**：E3 對 `date-time-functions.ods`、`functions.ods` 綠。
- **V2-160 PASS**（這兩輪只 49 次讀取；N＝3 的全語料還沒跑）：0 未確認，等待最大 122 ms。
- **V2-158B FAIL，而且有回歸**：5 份含控制項的檔＋`tdf138507.ods`（有表單無控制項，v1 正常）都**開不了**。成因：`ODatabaseForm` 要 dbaccess 的
  `com.sun.star.sdb.RowSet`（`forms/source/component/DatabaseForm.cxx:358`，`UNO_QUERY_THROW`），dbaccess 被 strip 了（finding 158 的 158-B 段）。

這是 §2.5 的 **F-3**（核心有 forms，控制項畫不出來——實際上是連檔都開不了）。依 §2.5 的原則，**這顆核心不能出貨**：它讓 v1 開得了的檔變成開不了。
預設退路：v2 只帶 159（`build-a11y-gate0` 增量）、重新連結、Phase E 從頭；158-B 另立工作項，帶著這次學到的前提（要 dbaccess 的 RowSet）。
擁有者可改；另一條路是讓 dbaccess 也進核心（`ENABLE_WASM_STRIP_DBACCESS` 只有 Make 變數、沒有 C++ 巨集，可只改組態），代價是再建一次與體積
（gzip 餘裕 3.28 MB，dbaccess 含整套資料庫 UI）。`a6390eef` 已封存，作為 158-B 的診斷件保留。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7：v2 第一次 Phase E 的結果、F-3、退路與另一條路 |

### 7.1 擁有者選 A：走退路（2026-10-22）

v2 只帶 159（＋157、160）。步驟與讀法（先寫好）：

1. **核心（擁有者）**：`bash handoff/ods-viewer-v2/build-core-fallback-gate0.sh`——在 `build-a11y-gate0` 刪三個 bridge 產物、`make`（autogen 會先重跑一次）。
   判準：K-2a、K-2b、K-2e 成立；**K-2c 必須不成立**（這顆核心不該有 forms）；autogen 前後的 `config_host.mk` 與 51 個設定標頭逐一比對，
   有變動就先讀再往下（預期全部相同：兩個 configure patch 只在明確下 `--enable-database-connectivity` 時生效）。證據 `findings/evidence/m4-ods/viewer-v2/fallback-core/`。
2. **連結前（我）**：刪掉 `build/ods/viewer-v2/`（物件是對 v2 核心的標頭編的：`HAVE_FEATURE_DBCONNECTIVITY 1`，而物件規則不追蹤 `-I` 底下的標頭，
   換核心不會自動重編）與 `dist/profiles/ods-viewer-v2/`（`a6390eef` 已封存，刪前比對封存）；連結手冊 §0 的閘門對 gate0 重做；新的凍結集合快照。
3. **連結（擁有者）**：同一條規則加 `ODS_VIEWER_V2_CORE=../wasm-lite/build-a11y-gate0`。預期：manifest 沒有 `form-controls`（引擎讀 gate0 的標頭 0）、
   base 就是 v1 的 `6f7424a1`（`--core gate0` 時差異 0／0／0，§3.5 已量）、gzip 與 v1 相近。
4. **Phase E 從頭**（新的連結＝新的身分，`a6390eef` 上的結果不轉移）：v2 的讀法照 §4，但 `form-controls` 沒宣告，所以含控制項的檔照 158-A 拒絕
   （E2 的 v1 讀法）、V2-158B 不跑；`tdf138507` 要開得了。
5. 158-B 另立工作項，前提寫在 finding 158 的 158-B 段：要 dbaccess 的 RowSet，體積預算未量。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.1：擁有者選 A（退路），步驟與預先寫好的讀法 |

### 7.2 退路核心建好、連結前閘門對 gate0 重做（2026-10-22 追加）

**第 1 步（擁有者，09:15–09:18，`make` exit 0，3 分鐘）**，證據 `findings/evidence/m4-ods/viewer-v2/fallback-core/`（README 有逐項）：

- 照 §7.1 的讀法成立：K-2a、K-2b（80 個簽章，與離線集合相同）、K-2e 成立；**K-2c 不成立**（700 個建構子，沒有 `OFormsCollection`，scaddins 三個在）。
  K-2f 登錄：`soffice.wasm` 149,208,138 → 149,236,537（+28,399）；`soffice.data` 不變。bridge 的 `exports` 雜湊不變，兩個 generated 檔換了。
- **§7.1 預期「52 個設定檔全部相同」沒有逐字成立**：51 個標頭相同，`config_host.mk` 有一行不同，已讀：只有 `export PATH=` 的目錄**順序**
  （擁有者 shell 的 `~/.cargo/bin`、`~/.deno/bin` 排到 nvm 前面）。被挪動的目錄之間沒有同名執行檔，任何查找找到的仍是同一支〔已觀察〕。判讀：不影響建置。
- **預期外的觀察**：除了 bridge，`make` 還重編了 5 個 Writer 原始檔（`pagechg`、`frmform`、`porrst`、`fntcache`、`xmltble`），因為它們的 mtime
  （09-25、09-26）比 gate0 的物件新。五個檔對 LO 的 HEAD `git diff` 都是空的、都不在 patch 清單裡；09-26 那一對正好是 `lo-submit` 的 tdf#173931 commit
  動的原始碼——在這棵 worktree 套上又還原過。判讀：用的是與 v1 核心相同的原始碼〔由此推論：假設八月建 gate0 時它們就是 HEAD；舊物件已不在，無法直接比〕。
  `build-headless-probe` 的這五個物件（08-01）也比原始碼舊，它下一次 `make` 一樣會重編。

**第 2 步（我）**，證據 `findings/evidence/m4-ods/viewer-v2/fallback-pre-link/`：

- 刪除前比對：`dist/profiles/ods-viewer-v2/` 六檔、`build/ods/viewer-v2/` 四個非物件檔與 `a6390eef` 封存逐位元相同，三個物件的雜湊記下。刪除由擁有者手動執行
  （session 的 `rm -rf` 被 auto mode 擋下）。
- **Makefile 的 `ODS_VIEWER_V2_CORE` 預設改成 `../wasm-lite/build-a11y-gate0`**（原本是 v2 樹）。理由：忘了帶變數的連結或 `test-e2-c-static` 不得選到
  F-3 那顆不能出貨的核心（交接文件列的風險）。§7.1 第 3 步的指令照舊明寫變數，與預設相同。
- 閘門全部成立：builder `--check --core gate0` 的正向對照 9901e9be 成立、base `6f7424a1`（v1 自己的 base）、對 v1 差異 0／0／0；`em++ -fsyntax-only`
  三個單元 exit 0，`sdk_api.cpp` 讀到 `HAVE_FEATURE_DBCONNECTIVITY 0`；`make -k test-e2-c-static` exit 0；`check_core_build_provides --capability
  calc-spreadsheet` exit 0；`make -n -B` 連結行與 v1 只差三個物件路徑、匯出清單路徑、輸出路徑（核心路徑已與 v1 相同），編譯行只差
  `-DOXSDK_ODS_VIEWER_V2` 與物件路徑；凍結集合快照 1,527 檔（＝01 點那份 1,517 檔原封不動＋`a6390eef` 封存的 10 檔）。
- 引擎原始碼、worker（`9c85043a`）、三支建構工具自 `a6390eef` 連結以來沒有改；手冊 §0 第 3、4 項沿用。

**第 3 步（擁有者連結）之後的讀法（先寫好）**：

1. 凍結集合 1,527 檔 `sha256sum -c` 通過，新檔只有 `dist/profiles/ods-viewer-v2/` 的六個。
2. manifest：v1 的能力＋`part-info`，**沒有 `form-controls`**，bits **30771**（＝14387＋16384；`a6390eef` 是 63539）。
3. base 是 `base-viewer-v2-no35.6f7424a1c1427ad7.data`。
4. wasm：`search-result`、`partBefore`、`lateSelectAllResults`、`part-info` 在，`verified-caret-readback` 不在；`ScDocShell` 在，**`OFormsCollection` 0**；
   probe.wasm 與 `a6390eef`、v1 都不同。堆疊常數 1,048,576 PASS；E1-C 完好。
5. gzip 接近 v1（規則最後一行印出）。v1 的 `probe.wasm` 用規則那一行的量法今天量是 **47,972,102**；§5.3 引用的 47,987,215 與它差 15,113，出處未查。
6. 以上任一條不成立就停手，先讀再往下。成立則封存為 `build/archive/ods-viewer-v2-<wasm sha8>-worker-9c85043a/`，Phase E 照 §7.1 第 4 步從頭跑。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.2：退路核心的結果（`config_host.mk` 的 PATH 順序、五個 Writer 物件重編）、連結前閘門對 gate0 重做、Makefile 預設改 gate0、連結後的讀法 |

### 7.3 退路的連結：`e96e01ec`（2026-10-22 追加）

擁有者 09:46 連結完成（`bash handoff/ods-viewer-v2/link-gate0.sh`，exit 0）。**新的身分：probe.wasm `e96e01ec…`**、probe.js `fb5fb399…`、worker `9c85043a…`、
manifest `fa54c32c…`、base `6f7424a1…`；封存於 `wasm_sdk_probe/build/archive/ods-viewer-v2-e96e01ec-worker-9c85043a/`。§7.2 預先寫的五條讀法全部成立
（`findings/evidence/m4-ods/viewer-v2/fallback-post-link/`）：凍結集合 1,527 檔不變、只多六個新檔；manifest 沒有 `form-controls`、bits 30771；base 與 metadata
與 v1 逐位元相同；`OFormsCollection` 0、v2 的四個特徵字串在、編輯器的不在、堆疊常數 PASS、E1-C 完好；gzip 47,972,953（v1 同量法 47,972,102，+851）。

`a6390eef` 上的結果不轉移。接下來：§7.1 第 4 步的 Phase E 在 `e96e01ec` 上從頭跑。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.3：退路連結的身分、封存、§7.2 讀法全部成立 |

### 7.4 `e96e01ec` 上的 Phase E：定向執行全過、E6 的 B＝0（2026-10-22 追加）

**啟動器**：重開機後沒有桌面 session、錢包服務不存在，runner 的錢包前置條件拒絕執行；擁有者選「現在落地」10-13 選過的
`--password-store=basic`（SPEC-M3-production-ui §17.27 預測、§17.28 見證成立；ODS 工具改成只記錄錢包）。下面每一次執行都在這個旗標下。

**定向執行**（`findings/evidence/m4-ods/viewer-v2/fallback-phase-e/report-2026-10-22T021041Z.json`，37.8 秒；也是 §17.28 的 W1）：
ladder 9 份＋`fdo67682-2`＋159 的兩份＋5 份含控制項＋`tdf138507`＋ODT 控制組。**E1、E2、E3、E4a、E5、E6、V2-157、V2-160 全 PASS**。
照 §7.1 第 4 步的讀法：`form-controls` 沒宣告 → 5 份含控制項的檔 `FORM_CONTROLS_UNSUPPORTED`（158-A），V2-158B 不跑；**`tdf138507` 開得了**
（`a6390eef` 上的回歸不在了）；E3 的 13 筆含 159 的兩份，0 失敗；V2-160：50 次讀取、0 未確認、等待最大 83 ms、0 筆遲到。

**E6 的 B（A6.1 的程序，`--profile ods-viewer-v2`）**：`e6-leak/report-2026-10-22T021348Z.json`。`one-cell-a1.ods` 開機 5 次 `open.begin`
236,523,520 ×5 → **B = 0**（另兩份也是 ×5 相同）。重開序列與 v1 同形：頭兩步建立高水位（+9,736,192、+4,194,304；`numeric-100k` +23,552,000、
+18,034,688），第 3 輪起 0。**B 釘為 0**；之後帶 `--bound 0` 的 E6 執行才算數。工具為此加了 `--profile`（比照 Phase E runner，只改鏡像副本裡 harness 的
worker 字面值、要求恰好一個；預設仍是 v1）——這是把 §4「E6 的 B 在 v2 上重新量」落地，不是因執行或因審核而修。

接下來：帶 `--bound 0` 的 E6、全語料 ×3（V2-160）。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.4：啟動器旗標、定向執行全過（`tdf138507` 開得了）、E6 的 B＝0 並釘死 |

### 7.5 E6 的洩漏半句：第一次算數的執行紅了，重複量測顯示 v1 也會（2026-10-22 追加；不含決定）

- **算數的那一次**（`fallback-phase-e/e6-leak/report-2026-10-22T021502Z.json`，`--bound 0`）：`one-cell-a1.ods` 的重開序列
  236,523,520 → 246,259,712 → 246,288,384 → 246,296,576 → 246,304,768，尾段 +8,192、+8,192 ＞ B＝0，**E6 洩漏半句 FAIL**；另兩份過。
  這一次照規則就是紅，不改判準。
- **診斷**（不算數；判讀在執行前寫好並 commit，`fb88a4e3`；`fallback-phase-e/e6-repeat/`）：v2、v1 交替各 5 趟。`one-cell-a1` 尾段上升：
  **v2 合計 3/7、v1 合計 2/7**（含量 B 那趟與 10-20 的兩趟）；另兩份 14 趟全平。上升的那幾趟形狀兩邊相同：第 2 輪的 tile 緩衝區（4,194,304）
  落進釋放出來的空洞、沒有推高 break，之後每輪 +8,192；有兩趟到最後一輪才補上那 4 MiB。
- **判讀**（照先寫好的第一條）：**不是 v2 的回歸**。但 A7.1 改寫後的洩漏半句（「第 3 輪起不再上升」）的前提——break 在第 2 輪之後就到頂——
  在重複量測下兩個連結都不成立；**v1 10-20 的 PASS 是單趟的結論**。每輪 8 KB 是真的增長還是配置器的漂移，`sbrk`（高水位）分不出來〔推論：要
  活位元組數（例如 `mallinfo`）才分得出，那要改引擎、要連結〕。
- 停手，交擁有者決定。在決定之前，E6 對 `e96e01ec` 是紅的，§4 E6 那一列的預設結論（「不准帶著記憶體問題出貨；停」）照字面適用；它同樣適用於 v1。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.5：算數的 E6 紅、十趟診斷（v2 3/7、v1 2/7）、判讀，不含決定 |

### 7.6 E6 照 SPEC-M4 追加 12（2026-10-22 追加）

擁有者同意 fable 裁決 1（`fallback-phase-e/e6-repeat/RULING-fable-1.md`）：E6 的洩漏半句撤回（SPEC-M4 追加 12、finding 164）。對 `e96e01ec`：

- E6＝峰值半句＋重開的形狀＋重開序列只記錄。`021502Z` 的 `E6 reopen bound` 作廢，它的開機與形狀判定成立；B＝0 不變。
- 定向執行（`report-2026-10-22T021041Z.json`）的 E6（峰值）PASS 照算。
- 20 輪診斷（擁有者選「跑」）在全語料 ×3 跑完之後開始，判讀照裁決書 §3，只決定 finding 164 的措辭。
- 其他 v2 判準不受影響；V2-160 的全語料 ×3 已在跑。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.6：E6 照 SPEC-M4 追加 12 |

### 7.7 全語料 ×3：V2-160 FAIL（2026-10-22 追加；不含決定）

`fallback-phase-e/full-corpus/`（`run-x3.sh`，306 份，每趟約 10 分鐘，都在啟動器旗標下）：

| 報告 | E1 E2 E4a E5 E6 V2-157 | E3 紅 | 未確認／讀取 | 已確認的等待最大 |
| --- | --- | --- | --- | --- |
| `022420Z` | 全 PASS | `user-defined-function.ods`（`L-no-basic-udf`，`#NAME?` 對 `#VALUE!`） | 0／464 | 106 ms |
| `023406Z` | 全 PASS | 同上＋`tdf125938_anchor_after_copy_paste.ods`（未確認的那一讀） | **2／464** | 104 ms |
| `024415Z` | 全 PASS | 同上 | **1／464** | 102 ms |

- **V2-160 FAIL**（第 2、3 趟不是 0）。三筆未確認：`tdf115655_HideDetail.ods`、`tdf125938_anchor_after_copy_paste.ods`、`tdf137082_LTR_arrow_image.ods`，
  都是 part 0、都等滿 10,001 ms；兩趟的 `lateSelectAllResults` 加總都是 0。
- E3 紅只剩 `L-no-basic-udf` 那一筆和未確認的那一讀：159 的兩份在三趟都綠，v1 的三筆紅少了兩筆。
- **照 §3.3 的讀法定性**：整輪都沒有晚到的 → 字面上是「**結果沒來**」。**但那個讀法的前提只部分成立**〔已觀察，讀原始碼與報告〕：晚到的結果要被數到，
  得在**同一顆引擎**上還有下一次 `part-text` 回覆；兩份單表的檔之後沒有下一次讀取（每份檔一顆新引擎，關檔就 dispose），`tdf125938` 的下一讀
  （part 1）期間若晚到，會被當成 part 1 自己的確認（`notePartTextUnoResult` 只看 payload 裡有沒有 `.uno:SelectAll`）。計數器在每份檔的尾端是瞎的。
- **獨立的那條證據**：v2 已確認的 1,389 次讀取等待最多 106 ms，沒有任何一次落在 106 ms 到 10 s 之間；期限 3 s 的 v1（`f6ab3cdb`，10-20 三趟）
  未確認 2／1,392，期限 10 s 的 v2 是 3／1,392。拉長期限沒有救回任何一筆。〔推論，強〕finding 160 的假說一（「3 秒在負載下不夠」）被駁倒；
  假說二（SelectAll 偶爾不回 `UNO_COMMAND_RESULT`，或晚得遠超過 10 s）留著。
- 產品頁面不呼叫 `partText`（§0），所以這是 E3 的儀器與 SDK 能力 `part-text` 的問題；v2 在這一點上與 v1 同率，不比 v1 差。

停手，交擁有者決定 v2 帶著 V2-160 紅要不要往下走。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §7.7：全語料 ×3、V2-160 FAIL、§3.3 讀法的盲點、期限無效的獨立證據，不含決定 |

## 8. 擁有者選「先修 160 再出 v2」：第三次連結（2026-10-22 追加；任何這次連結與執行之前）

### 8.1 成因與修法

- **成因**（finding 160 的「成因」段）〔已觀察〕：6 趟全語料的 5 次未確認，每一次引擎 stderr 都有 LOK 的
  `lok exception 'Failed to dispatch .uno:SelectAll'`，其他讀取都沒有——**SelectAll 沒被派送**，不是晚到。暫時性的（同一份檔的下一張表派送成功）。
  派送失敗的原因〔推論〕：`doc_postUnoCommand` 派送到 Desktop 的作用中 frame。
- **修法（只動引擎，`OXSDK_ODS_VIEWER_V2` 底下）**：`src/ods_viewer.hpp` 的 `selectAllUntilDispatched`——每次 post 之後讀 `getError()`，
  是 `Failed to dispatch` 就停 50 ms 再 post，直到 10 s 期限；派送成功的照舊等結果、**不再 post 第二次**。引擎在有過失敗的那一讀之後印一行
  `oxsdk part-text: .uno:SelectAll not dispatched N time(s), then dispatched|never dispatched`，和 LOK 自己的那一行並列在 worker 的 stderr（harness 的 `messages`）。
- **不動**：worker（`9c85043a`，pin 不變）、SDK、殼層、harness、runner、Makefile 的規則；manifest 的能力不變（沒有新的回覆欄位）。
- 核心 patch（`doc_postUnoCommand` 改派送到文件自己的 frame）**不走**：要重建核心，而 LOK 自己的錯誤訊息已經是可用的判別子。若 §8.3 的讀法指向它，才另議。

### 8.2 連結前的閘門（`findings/evidence/m4-ods/viewer-v2/160-fix-pre-link/`）

1. ✅ 主機上的 header 測試：D1（未派送就重送）、D2（到期限就停、什麼都不等）、D3（派送過的不重送）、D4（晚派送的只等剩下的時間）全綠；
   `tests/ods_viewer_mutations.py` 新增 4 個 mutation，連同既有 14 個**全部紅在指定的檢查**（`ods-viewer-mutations.txt`）。
2. ✅ v1 的 token 與 HEAD（`e7694378`）相同（`probe_engine.cpp`、`sdk_api.cpp` 用 v1 的 define 前處理，`diff -B` exit 0）；v2 的有變（84 行）。`tokens.txt`。
3. ✅ `em++ -fsyntax-only` 三個單元、v1 與 v2 兩種 define，對 gate0 的標頭全過。
4. ✅ `make -k test-e2-c-static` exit 0。
5. ✅ 凍結集合快照 1,543 檔（`frozen-set-before.sha256`；含現在 `dist/profiles/ods-viewer-v2/` 的 `e96e01ec` 六檔，連結後只准那六檔被換掉）。

### 8.3 這次連結的判準（Phase E 從頭；釘在任何執行之前）

新的連結＝新的身分，`e96e01ec` 的結果不轉移。§4 的判準全部重跑（E6 照 SPEC-M4 追加 12），**V2-160 原文不變**（全語料 ×3，每趟未確認為 0）。新增一條，照 CLAUDE.md §9：

| id | 判準 | 形式 | 永遠沒做的預設結論 |
| --- | --- | :---: | --- |
| **V2-160-D** | 每一筆（每份檔的 `messages`）：LOK 的 `Failed to dispatch .uno:SelectAll` 行數 ＝ 引擎那一行的 N 乘上它的次數之和；有這種行的檔，每一讀都 `selectAllConfirmed: true`，而且引擎行沒有 `never dispatched` | 1 | 引擎的偵測與 LOK 自己的紀錄是否一致沒有人核對；160 只看 V2-160 |

§9 的四個條件：先於滿足（寫在這次連結之前）；被逼出且指名（V2-160 的 `023406Z`、`024415Z` 與 finding 160 的 stderr 一對一）；形式一（逐筆）；
截止：第三次乾淨的全語料執行落地即封閉。

**預先寫好的讀法**：

- 三趟未確認 0，且有過派送失敗、V2-160-D 成立 → **160 修好**（重送有被走到、也有效）。
- 三趟未確認 0，但三趟都**沒有**任何派送失敗 → V2-160 照字面成立；重送這條路在真引擎上**沒被走到**，登錄為 NOT_ESTABLISHED（「綠燈不是證據」），
  不加跑、不判 160 已修，只判「v2 的 160 不比 v1 差，而且這幾趟沒發生」。
- 有未確認，而引擎行是 `never dispatched` → 10 s 內 Desktop 的作用中 frame 都沒回來；下一步才議核心 patch。
- 有未確認，但沒有任何派送失敗的行 → 另一個機制；finding 160 重開。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §8：160 的修法（重送未派送的 SelectAll）、連結前閘門、V2-160-D 與讀法，任何這次連結與執行之前 |

### 8.4 第三次連結：`aa576ce7`（2026-10-22 追加）

擁有者連結完成（`link-gate0.sh`，exit 0，gzip 47,971,896）。**身分：probe.wasm `aa576ce7…`**、probe.js `820bdbc8…`；manifest、worker、base 與 `e96e01ec` 逐位元相同。
手冊 G2 全部成立（`findings/evidence/m4-ods/viewer-v2/160-fix-post-link/`）：凍結集合只換了 probe.js／probe.wasm；引擎的 `not dispatched` 字串在 wasm 裡；
`OFormsCollection` 0、堆疊 PASS、E1-C 完好。封存於 `wasm_sdk_probe/build/archive/ods-viewer-v2-aa576ce7-worker-9c85043a/`。接下來 Phase E 從頭（§8.3）。

| 日期 | 變更 |
| --- | --- |
| 2026-10-22 | 追加 §8.4：第三次連結的身分、封存、G2 成立 |
