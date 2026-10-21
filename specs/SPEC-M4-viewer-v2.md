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
