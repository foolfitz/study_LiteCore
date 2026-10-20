# 159 — Calc 的 add-in 函數（Analysis／Date／Pricing）在 wasm 核心上一律 `#VALUE!`：`gcc3_wasm` bridge 的呼叫簽章表只從 udkapi＋offapi 產生，scaddins 自己的 IDL 不在裡面；而且檢視引擎載入時重算、不用檔內快取值

| | |
|---|---|
| **狀態** | **已確認、成因已定（靜態讀出，可查核）**（2026-10-20 深夜）；未修（要重建核心） |
| **Bugzilla** | 無。**強烈指向上游 wasm 建置**：`bridges/CustomTarget_gcc3_wasm.mk` 在上游樹裡就只餵 udkapi＋offapi 給 `wasmbridgegen`；未在上游 build 上重現 |
| **發現日** | 2026-10-20（`phase-e/report-2026-10-20T133240Z.json`；探針 `phase-e/159-diagnosis/`） |
| **嚴重度** | 高：使用者看到整欄 `#VALUE!`（財務函數、YEARFRAC、SERIESSUM…），而檔案本身帶著正確的快取值 |
| **可重現** | 語料 2 份檔 × 3 次執行；探針檔 1 次，20 格裡 add-in 的 5 格全 `#VALUE!`、核心函數全對 |
| **是否上游** | **未確認**（缺上游 build 的重現；機制本身是上游原始碼的） |

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
   `scaddins/InternalUnoApi_scaddins.mk` 自己編。`getSeriessum(double×4) → double` 的簽章 `didddd` 在產物裡 **0 次**；YEARFRAC、COUPDAYS、
   ACCRINT 的簽章同理。
5. 反證查過：`scaddins_AnalysisAddIn`／`ScaDateAddIn`／`ScaPricingAddIn` 的 constructor 都在 `services_constructors.list`；
   `Introspection`、`CoreReflection`、`InvocationService`、`TypeConverter` 也都在——所以不是少元件、不是少反射，是 bridge 的簽章表。
   `CalcAddIns` 的設定在 `main.xcd`（名字因此解析得到，所以是 `#VALUE!` 不是 `#NAME?`）。

**為什麼核心函數沒事**：`ScInterpreter` 直接呼叫，不經 UNO bridge。**為什麼 EUROCONVERT 沒事**：它是核心函數，不是 add-in。

## 修法（核心重建，擁有者的 make；併進 v2 的核心批次）

- `bridges/CustomTarget_gcc3_wasm.mk` 的 `wasmbridgegen` 輸入加上 `scaddins` 的 `InternalUnoApi`（`+$(call gb_UnoApi_get_target,scaddins)`
  或等價的 rdb），讓 `didddd` 一類的簽章進表。要驗：重建後 `generated-cxx.cxx` 裡出現 `callVirtualFunction_didddd`；探針檔 20 格全對。
- 載入時重算是另一件事（`ODFRecalcMode`／`ScDocShell::...`）：**不是**這張的修法，先登錄；即使不重算，使用者按 F9 也會回到 `#VALUE!`，
  bridge 才是根。

## 上游

機制在上游樹裡（`CustomTarget_gcc3_wasm.mk` 只餵 udkapi＋offapi 是上游的寫法），上游的 wasm build 理論上同樣出事。缺：上游組態的 build 一次、
Bugzilla 查重複（關鍵字 `wasm` `add-in` `#VALUE!` `wasmbridgegen`）。上游送出擱置（2026-08-15 起）；只登錄。
