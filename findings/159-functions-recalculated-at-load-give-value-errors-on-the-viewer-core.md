# 159 — 檢視核心載入時重算的函數給 `#VALUE!`：`TIMEVALUE("6:45 PM")`、財務函數、`MULTINOMIAL`／`SERIESSUM`／`CONVERT`；檔內快取值沒被用

| | |
|---|---|
| **狀態** | **已觀察、成因未定**（Phase E 全語料＋診斷重跑，2026-10-20）；未修 |
| **Bugzilla** | 無 |
| **發現日** | 2026-10-20（`phase-e/report-2026-10-20T133240Z.json`；文字在 `phase-e/diagnostic-text/report-2026-10-20T134644Z.json`） |
| **嚴重度** | 一般到高：試算表的**數字錯了**，而且是使用者看得到的那種（整欄 `#VALUE!`）。語料裡 3 張表、2 份檔 |
| **可重現** | 2 份檔 × 2 次執行，逐位元相同的 `#VALUE!` 位置 |
| **是否上游** | 未確認 |

## 現象（引擎文字 vs 原生 oracle，同一 commit `671c848b`）

- `date-time-functions.ods` 一列：oracle `0.5 0.4972677596 0.5055555556 0.498630137 0.5`，引擎 `#VALUE!` ×5。
  該列的公式是 `TIMEVALUE("12PM")`、`ROUND(TIMEVALUE("4PM");10)`、`MINUTE(TIMEVALUE("6:45 PM"))` 一類——**用 locale 解析的時間文字**。
- `functions.ods` p2（Mathematical）：`MULTINOMIAL([.A51:.A52])`（快取 84）、`SERIESSUM(2;3;2;3)`（快取 24）、`CONVERT(10;"km";"mi")`、
  `ORG.OPENOFFICE.CONVERT(100;"ATS";"EUR")`、`EUROCONVERT` 等 → 引擎 `#VALUE!`；另有一列數值不同（`2 2 5 3 5 3 1` vs `1 1 3 2 3 2 1`）。
- `functions.ods` p6（Financial）：整欄 `ACCRINT`、`ACCRINTM`、`AMORDEGRC`、`COUPDAYS`…（參數是 `2001-01-01` 一類的日期文字）→ `#VALUE!`。
- 檔內都有快取值（`office:value="84"` 等）；引擎顯示的不是快取值，所以是**載入時重算**後的結果。

## 已排除

- **不是少 add-in**：`scaddins_AnalysisAddIn`、`ScaDateAddIn`、`ScaPricingAddIn` 三個 constructor 都在核心的
  `workdir/CustomTarget/postprocess/services_constructors.list`〔已觀察〕。
- 不是 Basic：這些不是 UDF（`user-defined-function.ods` 的 `#NAME?` 是另一件事，登錄為 `L-no-basic-udf`）。

## 候選成因（未查，依可能性排）

1. **locale 資料被砍**：核心是 `ENABLE_WASM_STRIP_LOCALES=TRUE`；引擎 stderr 每次都有 `MsLangId::getConfiguredSystemLanguage() - n…`。
   時間文字「6:45 PM」、日期文字「2001-01-01」的解析、以及 add-in 的參數轉換都經 `SvNumberFormatter`／i18n locale data。
2. 字串→數值的轉換設定（`Calc/Formula/Syntax/StringConversion`）在切過的 base pack 裡是預設的 `#VALUE!` 模式。
3. 為什麼載入時重算（而不是用快取）：`ODFRecalcMode` 的判定（檔的 generator 版本）或 add-in 函數在載入時本來就重算。

## 下一步（診斷，不用連結）

一份生成的 `.ods`：`=SERIESSUM(2;3;2;3)`、`=TIMEVALUE("4PM")`、`=TIMEVALUE("16:00")`、`=DATEVALUE("2001-01-01")`、`=1+1`、`=TODAY()`，
各帶快取值；在檢視引擎讀 `part_text`，一格一格對——哪些格錯，直接指向上面 1／2／3 的哪一個。E3 對這 3 張保持紅。
