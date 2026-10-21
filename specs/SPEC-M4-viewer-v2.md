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
