# 184 — 整欄範圍 `COUNTIFS` 很多的 ODS 開不起來：載入時算列高，逐格重算公式

| | |
|---|---|
| **狀態** | 已確認，成因定位到函式層級，未修、未送 |
| **Bugzilla** | 未查重複單（上游送出擱置中，重啟時先查） |
| **發現日** | 2026-11-03（`SPEC-P-ms-formats` 的 M0 原生量測） |
| **嚴重度** | 中：檔案本身完全打不開（不是慢一點），但要特定形狀的試算表才會觸發 |
| **可重現** | 原生 LOK 26.8（`build-native-26-8`）、桌面 LibreOffice 26.8.1.1、OxOffice 12.0.1.1（co-25.04 基底）三者都重現，各 1／1 |
| **是否上游** | 是（三個不同 build 都一樣，與我們的引擎程式碼無關） |

## 現象

LibreOffice QA 樹的 `sc/qa/unit/data/xlsx/forum-mso-en4-134670.xlsx`（108 KB，Excel 產生，5 張工作表）本身開得很快：原生 LOK 匯入、存回 XLSX、存成 ODS 都在幾秒內完成，現行出貨的 WASM Calc 引擎 5 秒開好。

**但它存出的那份 ODS 開不起來**：

| 開那份 ODS 的程式 | 結果 |
|---|---|
| 原生 LOK 26.8（`tools/msformat_native.cpp`） | 跑滿 25 分鐘被 `timeout` 砍掉，RSS 513 MB |
| 桌面 LibreOffice 26.8.1.1 `--headless --convert-to csv` | 跑滿 25 分鐘被砍，CPU 100%，沒有輸出 |
| OxOffice 12.0.1.1 `--convert-to csv` | 跑滿 5 分鐘上限被砍，沒有輸出 |

那份 ODS 是 LibreOffice 26.8 自己寫的（generator `LibreOfficeDev/26.8.0.1.0`），公式都有快取值（例如 `office:value="41"`）。裡面有 50 個 `COUNTIFS`、4 個 `COUNTIF`，條件範圍是整欄（`[$'Data Dump'.$A:.$A]`）。

## 卡在哪裡

開檔第 40 秒用 gdb 停下來看主執行緒（`evidence/ms-formats/f184-ods-reload/native-lok-main-thread.txt`）：

```
mdds::mtv::soa::multi_type_vector<sc::CellStoreTraits>::cend()
ScQueryCellIteratorBase<...>::PerformQuery()
ScCountIfCellIterator<...>::GetCount()
ScInterpreter::ScCountIf()
ScFormulaCell::InterpretTail / Interpret / GetErrCode()
ScCellFormat::GetString(...)
ScColumn::UpdateScriptType / GetRangeScriptType / HasEditCells
ScColumn::GetOptimalHeight
ScTable::SetOptimalHeight
ScDocRowHeightUpdater::update
ScXMLImport::endDocument()
```

不是死結：當時共 24 條執行緒，只有主執行緒在 Calc 的程式碼裡（另外 12 條是 thread pool 在等工作，其餘是 configmgr、喚醒之類的背景執行緒）。它是在**算**：匯入結束時要算最佳列高，算列高要知道每格文字的書寫系統，於是去拿公式格的字串，公式格在這個時間點被當成要重新計算，每個整欄 `COUNTIFS` 都走一遍整欄。

## 推論（未驗證）

- 公式有快取值，`ScDocShell::LoadXML` 的「要不要整份重算」（`ODFRecalcMode`）是在匯入**之後**才決定的；但列高更新發生在 `ScXMLImport::endDocument` 裡，也就是決定之前。為什麼此時公式格是 dirty、會被 `GetErrCode()` 觸發計算，還沒查。
- 同一份檔的 XLSX 版本不會這樣，所以差別在 ODS 匯入路徑（或 ODS 存出了什麼），不是公式本身。
- OxOffice 12 也重現，所以不是 26.x 新近的退化。

## 對本專案的影響

- `SPEC-P-ms-formats` 的「另存新檔成 ODF」會把這類 XLSX 變成開不起來的 ODS（限制 `L-ods-reload-cliff`）。存回 XLSX 不受影響。
- 任何使用者自己帶來的、同樣形狀的 ODS，在我們的 Calc 頁面上也會開不起來（引擎是同一份 core）。M1 沒有在 WASM 上實際開那份 ODS（只讓原生 harness 讀過）；WASM 上的表現未量。

## 證據

`evidence/ms-formats/f184-ods-reload/`：

- `reload-cliff.ods`（sha256 `78bf5072…15e4`），由原生 LOK 26.8 從 `forum-mso-en4-134670.xlsx`（sha256 `e54cd64b…2e`）存出；
- `native-lok-main-thread.txt`：上面那段 backtrace 全文；
- `native-lok-time.txt`、`desktop-26.8.1.1-time.txt`、`oxoffice-12-time.txt`：`/usr/bin/time -v` 的耗時與結束碼。

## 還缺什麼

- [ ] 縮小重現：最少幾個 `COUNTIFS`、多大的資料表才會觸發；是不是整欄範圍才會。
- [ ] 查為什麼公式格在 `endDocument` 時是 dirty。
- [ ] WASM 上開這份 ODS 的實際表現（預期一樣卡住，未量）。
- [ ] 送出前查 Bugzilla 重複單（上游送出擱置中）。

## 時間軸

- 2026-11-03 19:42：M0 第一次跑，這份檔的兩臂都在 180 秒逾時；看輸出才知道卡在重開 ODS。
- 2026-11-03 19:52–20:24：gdb backtrace；原生 LOK 與桌面 26.8.1.1 各跑滿 25 分鐘。
- 2026-11-03 20:24–20:29：OxOffice 12 跑滿 5 分鐘。
