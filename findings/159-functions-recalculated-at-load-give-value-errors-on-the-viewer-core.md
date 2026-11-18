# 159 — Calc 的 add-in 函數（Analysis／Date／Pricing）在 wasm 核心上約一半 `#VALUE!`（2026-11-18 更正：原寫「一律」）：`gcc3_wasm` bridge 的呼叫簽章表只從 udkapi＋offapi 產生，scaddins 自己的 IDL 不在裡面；而且檢視引擎載入時重算、不用檔內快取值

| | |
|---|---|
| **狀態** | **已確認、成因已定（靜態讀出，可查核）**（2026-10-20 深夜）；**2026-11-18 在 stock 上游 master 建置上執行期重現，bridge 的例外訊息原文讀到**（見〈2026-11-18〉）；修法已在我們的產品（0.2.32 起），上游 commit 已備（未推），修法在 master 上的執行期驗證等擁有者重建 |
| **Bugzilla** | 未開。草稿 `findings/drafts/159-bugzilla.txt`（修法段待重建結果）。~~未在上游 build 上重現~~（2026-11-18 已重現） |
| **發現日** | 2026-10-20（`phase-e/report-2026-10-20T133240Z.json`；探針 `phase-e/159-diagnosis/`） |
| **嚴重度** | 高：使用者看到整欄 `#VALUE!`（財務函數、YEARFRAC、SERIESSUM…），而檔案本身帶著正確的快取值 |
| **可重現** | 語料 2 份檔 × 3 次執行；探針檔 1 次，20 格裡 add-in 的 5 格全 `#VALUE!`、核心函數全對 |
| **是否上游** | **是**（2026-11-18：stock master `ac53621f`＋finding 186 的 configure 修正，執行期重現；證據 `findings/evidence/159/stock-runtime/`） |

## 現象

- 語料：`date-time-functions.ods` 一列 5 格（YEARFRAC 的五種 basis：0.5、182/366、182/360、182/365、0.5）、`functions.ods` p2
  （MULTINOMIAL、SERIESSUM、CONVERT…）與 p6（整欄 ACCRINT、ACCRINTM、AMORDEGRC、COUPDAYS…）：引擎 `#VALUE!`，原生 oracle 是數值。
- 探針（`159-diagnosis/probe-159.ods`，桌面 26.8 產生、每格帶快取值；引擎文字在 `report-2026-10-20T145444Z.json`）：

| 格 | 桌面（26.8，zh-TW） | 檢視引擎（wasm，en-US） |
| --- | --- | --- |
| `=1+1`、`=SUM(1;2)`、`=EUROCONVERT(…)`、`=TIMEVALUE("16:00")`、`=DATEVALUE("2001-01-01")`、`=VALUE("1.5")`、`="3"+1`、`=TEXT(…)` | 對 | **對** |
| `=SERIESSUM(2;3;2;3)`（純數值參數） | 24 | **`#VALUE!`** |
| `=MULTINOMIAL(2;3)` | 10 | **`#VALUE!`** |
| `=COUPDAYS(DATE…)`、`=ACCRINT(DATE…)`、`=YEARFRAC(DATE…;1)` | 181、16.67、0.4959 | **`#VALUE!`** |
| `=TIMEVALUE("4PM")`、`"6:45 PM"`、`=DATEVALUE("01/01/2001")` | Err:502（zh-TW 不解析） | 對（引擎是 en-US） |
| `=DATE(2001;1;1)` 的顯示 | `2001/1/1` | `1/1/01` |

- **載入時重算**：把 `=1+1` 的 `office:value` 改成 3 的副本（`probe-159-cache3.ods`），引擎仍顯示 **2**。所以快取值救不了 add-in 格。

## 成因（讀原始碼與建置產物；每一步可查核）

1. `#VALUE!` 是 `FormulaError::NoValue`，在 `sc/source/core/tool/addincol.cxx:1510-1549` `ScUnoAddInCall::ExecuteCallWithArgs`：
   `xFunction->invoke(...)` 丟出 `uno::Exception`（或 `InvocationTargetException` 包著非 IllegalArgument 的例外）時設的。例外被吞掉，
   引擎 stderr 沒有任何一行（探針那一輪的 `messages` 只有 SelectAll 的結果）。
2. `invoke` 走 C++-UNO bridge：`bridges/source/cpp_uno/gcc3_wasm/uno2cpp.cxx:204` `callVirtualFunction(sig, …)`，`sig` 是回傳＋參數的
   字母串（d＝double、i＝int／指標、v＝void…）。
3. 那張表是建置時由 `wasmbridgegen` 產生的（`bridges/CustomTarget_gcc3_wasm.mk`），**輸入只有 `udkapi` 與 `offapi`**。本核心的產物
   `workdir/CustomTarget/bridges/gcc3_wasm/generated-cxx.cxx` 共 **55 個簽章**；沒對上的簽章在第 284 行
   `throw css::uno::RuntimeException("Wasm bridge cannot call virtual function with signature " + …)`。
4. Analysis／Date／Pricing add-in 的介面**不在 offapi**：`scaddins/idl/com/sun/star/sheet/addin/XAnalysis.idl` 等，由
   `scaddins/InternalUnoApi_scaddins.mk` 自己編。`getSeriessum(double×3, sequence) → double` 的簽章 `didddi`（**2026-10-21 更正**：原寫 `getSeriessum(double×4)`／`didddd`，第四個參數是 sequence、以指標傳）在產物裡 **0 次**；YEARFRAC、COUPDAYS、
   ACCRINT 的簽章同理。
5. 反證查過：`scaddins_AnalysisAddIn`／`ScaDateAddIn`／`ScaPricingAddIn` 的 constructor 都在 `services_constructors.list`；
   `Introspection`、`CoreReflection`、`InvocationService`、`TypeConverter` 也都在——所以不是少元件、不是少反射，是 bridge 的簽章表。
   `CalcAddIns` 的設定在 `main.xcd`（名字因此解析得到，所以是 `#VALUE!` 不是 `#NAME?`）。

**為什麼核心函數沒事**：`ScInterpreter` 直接呼叫，不經 UNO bridge。**為什麼 EUROCONVERT 沒事**：它是核心函數，不是 add-in。

## 修法（核心重建，擁有者的 make；併進 v2 的核心批次）

- `bridges/CustomTarget_gcc3_wasm.mk` 的 `wasmbridgegen` 輸入加上 `scaddins` 的 `InternalUnoApi`（`+$(call gb_UnoApi_get_target,scaddins)`
  或等價的 rdb），讓 `didddi` 一類的簽章進表。~~要驗：重建後 `generated-cxx.cxx` 裡出現 `callVirtualFunction_didddd`~~（2026-10-21 撤回：簽章寫錯，而且子字串搜尋會被另一個方法的 `didddddd` 滿足——錯的理由也會過）。要驗的是**完整符號**集合含 `didddi`／`diiii`／`diiiii`／`diiiiii`（SERIESSUM／MULTINOMIAL／YEARFRAC／COUPDAYS），規格 `SPEC-M4-viewer-v2` §2.4 K-2a；探針檔 20 格全對。
- **2026-10-21 補充：修法已離線量過一半。**用 `build-a11y-gate0` 已建好的 build-side `wasmbridgegen` 手動跑：不加 scaddins 時輸出與核心現有的三個檔逐位元相同（正向對照）；加了之後簽章 55 → 80，上面四個都在（`findings/evidence/m4-ods/phase-e/159-diagnosis/bridgegen-offline/`）。patch 在 `wasm-lite/patches/libreoffice-26.8-wasm-bridge-scaddins-signatures.patch`（只在有建 Calc 的組態生效）。瀏覽器裡 `#VALUE!` 會不會消失仍要等新核心。
- 載入時重算是另一件事（`ODFRecalcMode`／`ScDocShell::...`）：**不是**這張的修法，先登錄；即使不重算，使用者按 F9 也會回到 `#VALUE!`，
  bridge 才是根。

## 上游

機制在上游樹裡（`CustomTarget_gcc3_wasm.mk` 只餵 udkapi＋offapi 是上游的寫法），上游的 wasm build 理論上同樣出事。缺：上游組態的 build 一次、
Bugzilla 查重複（關鍵字 `wasm` `add-in` `#VALUE!` `wasmbridgegen`）。上游送出擱置（2026-08-15 起）；只登錄。

## 2026-11-18：stock 上游 master 上的執行期重現〔已觀察〕

建置：`wasm-lite/upstream-master/build-186-R`（master `ac53621f`＋finding 186 的 configure 修正，只改 `configure.ac`，沒碰 `bridges/`、`scaddins/`）。證據與工具在 `findings/evidence/159/stock-runtime/`（README 是英文）。

**換了一種問法。**「add-in 在 wasm 上壞了」和「bridge 的簽章表缺簽章」兩種說法，在「add-in 全錯」這個現象上分不開。成因的說法多預測一件事：**簽章剛好在表裡的 add-in 方法應該能算**（因為 udkapi／offapi 裡有別的方法用同一個簽章）。`addin_signatures.py` 照 `uno2cpp.cxx` `call()` 的規則算出 scaddins 全部 114 個方法的簽章，對 stock 的 `generated-cxx.cxx`（52 個簽章）查：**57 個在表內、57 個不在**。預測先 commit（`d71d500b2`）再跑。

**結果**：三次執行（兩次 en-US、一次 zh-TW），打字與 `XCell.setFormula` 兩條路，全部照預測：

- 核心函數 5 格：對。
- 簽章在表內的 add-in 10 格（FACTDOUBLE、SQRTPI、EOMONTH、EDATE、WORKDAY、BIN2DEC、IMABS、DAYSINMONTH、ISLEAPYEAR、ROT13）：與桌面 26.8.1.1 相同。
- 簽章不在表內的 8 格（MULTINOMIAL、SERIESSUM、YEARFRAC、COUPDAYS、QUOTIENT、MROUND、BESSELI、OPT_PROB_HIT）：錯誤碼 519，`#VALUE!`。
- 繞過 Calc、用 `css.script.Invocation` 從 JS 直接呼叫 add-in：表內的回傳正確值；表外的丟 `InvocationTargetException`，包著 `RuntimeException("Wasm bridge cannot call virtual function with signature didd")`（getQuotient；getBesseli 是 `didi`、getOptProbHit 是 `didddddd`）。**bridge 的訊息是讀到的，不是推的**；從例外到 `#VALUE!` 那一步仍是讀 `addincol.cxx`。

判讀工具 `read_159.py` 的期望值由 oracle 與簽章表推出，不是手寫；紅案（`reader-red-cases.txt`）五個都紅在被改的那一格，包括「拿 stock 的結果當成修好的表來判」會紅在 A1–A8、D4–D6。

**這推翻了兩句話**：

1. 本檔標題的「一律」。實際是 113 個 add-in 函數裡 57 個受影響。其中 GCD、LCM、EFFECT、NOMINAL、CUMIPMT、CUMPRINC 這六個在核心也有同名函數，使用者打原名拿到的是核心版，只有 `_ADD`／`_EXCEL2003` 版受影響（`analysishelper.cxx` 標 DOUBLE）。
2. `RESEARCH-2026-11-18-next-upstream-wasm-contribution.md` 寫「EOMONTH、NETWORKDAYS、YEARFRAC、XIRR 這一整類一律 `#VALUE!`」：EOMONTH 簽章在表內、能算；NETWORKDAYS 打原名是核心函數。YEARFRAC、XIRR 確實受影響。

**修法的離線部分**：用 build-186-R 自己的 build-side `wasmbridgegen` 與 rdb 手動跑（0.1 秒，不編譯）。不加 scaddins：三個輸出與建置產物逐位元組相同（正向對照）。加了：52 → 77 個簽章，嚴格超集，`exports` 不變，scaddins 114 個方法全在表內。

**上游 commit**：`wasm-lite/upstream-master/src-186-R` 的分支 `finding159-test-on-R`，現為 `4a59e013bf53`（R 之上一個 commit，只改 `bridges/CustomTarget_gcc3_wasm.mk`）。要推上 Gerrit 時從 `origin/master` 另做一個分支（不帶 186 的 commit；兩者互不相依）。

**codex 審查（一輪）**，原文 `findings/evidence/159/stock-runtime/review-codex-2026-11-18.txt`，對象是第一版 `7a22cea9016c`：

- 成立：gbuild 的目標名與條件（`ENABLE_WASM_STRIP_CALC` 與 scaddins 模組的納入條件一致）、非 Emscripten 不受影響、預設 WASM 組態裡沒有別的 InternalUnoApi 會中同一個 bug。
- **採納（改變行為）**：產生的三個檔原本只依賴 rdb；新加的 `scaddins.rdb` 在既有建置目錄裡比產出舊，**既有的 WASM 建置目錄 `git pull` 之後不會重產簽章表，修法在增量建置裡靜默失效**。加上 `$(SRCDIR)/bridges/CustomTarget_gcc3_wasm.mk` 為前置條件（上游 pyuno、jvmfwk、oox、postprocess 都有這樣做的前例）。重建腳本因此不再先刪產出，順便驗這條增量路徑（`PREDICTIONS-fix.txt` 的 F0）。
- 採納：兩個條件式直接 inline（不用變數與 `foreach`）；commit message 裡 GCD、LCM、EFFECT、NOMINAL 打原名是核心函數，改寫成只有 `_ADD`／`_EXCEL2003` 版受影響；「work only because」改成「簽章剛好已在表內」。
- 未採納：無。

因審核而改的檢查數：0（改的是 diff、commit message、重建腳本的流程）。

**還沒做的**：修法在 master 上的執行期驗證。要重建 `build-186-R`（會編譯，擁有者跑 `findings/evidence/159/stock-runtime/rebuild_159_fix.sh`），之後同一支探針與判讀工具（換成新表的簽章 TSV）再跑一次。重建前的產物已複製到 `wasm-lite/upstream-master/archive-186-R-products-before-159/`。

**沒有涵蓋**：帶快取值的文件（本檔「載入時重算」那一半，另一件事）；其餘 95 個 add-in 函數只有計算分類、沒有實跑；建置組態只有預設模組組合。
