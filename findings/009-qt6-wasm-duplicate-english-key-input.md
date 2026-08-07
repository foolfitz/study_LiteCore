# 009 — Qt6-WASM Writer 英文按鍵重複輸入

| | |
|---|---|
| **狀態** | 待驗證（首度觀察） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-08-01 |
| **嚴重度** | 嚴重（Writer 可執行，但英文文字輸入不可正常使用） |
| **可重現** | 1/1（單次手動驗證） |
| **是否上游** | **未確認**（只在自訂 Qt6-WASM/JSPI 組態與本地修補後觀察） |

## 現象

finding 008 的主執行緒代理修補後，Writer 能開啟且中文輸入成功；但手動按下一次英文
按鍵時，文件中會出現兩個字元。

## 重現步驟

1. 使用 finding 008 驗證所記錄的 LibreOffice 26.8、Qt 6.10.2 WASM 與 Emscripten 4.0.10
   產物。
2. 以具備 COOP/COEP headers 的本機 HTTP server 開啟 `qt_soffice.html`。
3. 從 Start Center 開啟 Writer。
4. 在文件中按下一次英文按鍵。

**預期**：文件插入一個英文字元。

**實際**：初次手動觀察中，文件插入兩個字元。

## 證據

- [`evidence/009/manual-observation.txt`](evidence/009/manual-observation.txt) — 操作者原話、產物
  雜湊、版本與本地修補邊界
- [`evidence/008/main-thread-proxy-validation.txt`](evidence/008/main-thread-proxy-validation.txt) —
  產生本次測試產物的完整建置資訊與 finding 008 執行期結果

## 分析

### 已確認的事實

1. 同一產物能開啟 Writer，不再立即退出。
2. 中文輸入在該次手動測試中成功。
3. 英文按鍵在該次測試中一次產生兩個字元。
4. 尚未擷取 `keydown`、`beforeinput`、`input`、composition 或 Qt key event 的事件數量與順序。

### 推論（NOT VERIFIED）

- 可能是瀏覽器 DOM input path、Qt key event path 或 LibreOffice 事件轉送中的兩條路徑都提交
  同一英文字元；目前沒有事件 trace，不能判定發生在哪一層。
- 中文輸入沒有同樣的表面症狀，可能只是 composition path 不同；單次觀察不足以證明問題只影響
  非 IME 輸入。

## 本地修改揭露

本次觀察不是 stock 組態，至少包含：

- finding 007 的 Qt pointer-enter null DOM guard
- Qt suspend/resume 重入佇列回補
- finding 008 的 LibreOffice `QtFrame::SetInputContext()` 主執行緒代理

完整產物雜湊與 patch 路徑見 evidence。

## 驗證計畫

- [ ] 在相同產物重新驗證至少 3 次
- [ ] 分別測試 `a`、`Shift+A`、數字、空白、Enter、Backspace
- [ ] 分別測試啟用與停用 IME 的英文輸入
- [ ] 擷取 browser `keydown`／`keyup`／`beforeinput`／`input`／composition event 時序
- [ ] 擷取 Qt 與 LibreOffice key/input event 時序
- [ ] 判斷重複發生在 DOM、Qt WASM QPA 或 LibreOffice VCL 哪一層
- [ ] 建立最小 stock Qt6-WASM reproducer

## 還缺什麼才能送

- [ ] 穩定重現與精確按鍵／IME 條件
- [ ] 原始事件時序證據
- [ ] stock Qt6-WASM 最小重現或證明只出現在 LibreOffice
- [ ] 搜尋 LibreOffice Bugzilla、Qt Bug Tracker／Gerrit 是否已有重複
- [ ] 確認應回報 LibreOffice、Qt 或 Emscripten

## 時間軸

- 2026-08-01 finding 008 主執行緒代理修補完成增量建置
- 2026-08-01 手動驗證 Writer 可開啟且中文可輸入；同時首次觀察英文按鍵一次產生兩個字元
