# 018 — Writer line navigation callback completion不具重複執行確定性

| | |
|---|---|
| **狀態** | **已確認／E1-A部分GO限制；2026-08-06 已歸因（見末節）** |
| **Bugzilla** | — |
| **發現日** | 2026-08-05 |
| **嚴重度** | 一般 |
| **可重現** | Chrome 150；2026-08-06 在 Firefox 153 上以 profile 對照穩定重現（無活迴圈 18 輪中 14 輪於第一個 End 逾時；活迴圈 6/6 全過） |
| **是否上游** | 未確認；目前分類為LOK callback到SDK completion的邊界問題 |

## 摘要

E1-A用closed `move-line-up/down/home/end`映射到固定Writer key event，並等待文件化visible-cursor或
text-selection callback。Up／Down及Home／End曾在同一次run各3/3完成；下一次相同artifact、相同fixture與交替
Home→End流程中，第一個End在30秒內沒有可歸屬callback，後續同Worker只可回`BUSY`。文件沒有mutation，不能用
revision或save內容補成completion，也不能以任意delay宣稱no-op。

因此E1-A不把line navigation升格為產品能力；character left/right及Shift selection仍成立。此限制不阻斷基本
文字編輯，但使E1-A只能`PARTIAL_GO_TO_E1_B`。

## 最小重現

1. 用`e1-editor-discovery`開啟`multi-paragraph.odt`。
2. search `第二段中文 beta`，用closed selection reset把caret放到rectangle末端。
3. 交替執行三輪Home／End並等待typed cursor callback。
4. 比較兩次獨立Chrome run。

**預期**：每個移動都回typed完成，或可安全判定為文件邊界no-op。

**實際**：`attempt-03`的Up／Down／Home／End皆3/3成功；`attempt-04`的第一個End回`TIMEOUT`，其後Home／End回
`BUSY`。Harness沒有retry mutation，也沒有把timeout當成功。

## 證據

- 全部line action通過：
  `findings/evidence/sdk-e1/discovery/browser/chrome/multi-paragraph/attempt-03/result.json`
- 相同流程End逾時：
  `findings/evidence/sdk-e1/discovery/browser/chrome/multi-paragraph/attempt-04/result.json`
- 更早的同座標selection reset no-callback：
  `findings/evidence/sdk-e1/discovery/browser/chrome/multi-paragraph/attempt-02/result.json`
- E1-A最終summary：`findings/evidence/sdk-e1/discovery/summary.json`
- Core：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- E1 artifact：loader `43a26f0520a7da5a31de219977cf9c64a8bc97581cd4e6619bc0673930f4240b`、
  WASM `679def61e7848a6d678b6bcc2b4fad7acb37904cdcd0e615afb3405fb5afb634`

## 已觀察／推論／待驗證

### 已觀察

- 非mutation line action不改產品revision；completion只能依賴與request相關的typed cursor／selection callback。
- 同一個End action有成功與逾時兩種結果；逾時後pending operation會阻擋同Worker後續editor action。
- 未使用raw callback、任意key code、任意UNO或sleep fallback。

### 推論

- 某些視覺位置的移動可能被Writer視為no-op，或callback在request correlation建立前／之外送達；現有文件化surface
  無法可靠區分這兩者。
- 問題與Finding 016不同：016是mutation completion，已用verified-selection transaction修復；本finding是
  非mutation line navigation，不能照搬selection-delete barrier。

### 待驗證

- 在Firefox與不同zoom／wrap位置重現，確認是否browser-independent。
- 評估是否有文件化狀態readback能在不靠任意delay的情況下證明line-position postcondition。
- 未有確定barrier前，E1-B只承諾character navigation，不提供Up／Down／Home／End。

## 判定

`CONFIRMED_CAPABILITY_REDUCTION`。不阻斷E1-B窄版編輯器，但line navigation需保持unsupported；若未來要加入，應另做
最小contract實驗，不得把本次偶發3/3成功當成已解決。

## 2026-08-06 判別實驗：不是移動問題，是完成訊號問題

本 finding 原本推論「某些視覺位置的移動可能被 Writer 視為 no-op，或 callback 在
request correlation 之外送達」。實驗把兩者都排除了，答案是第三種。

### 方法

零重建。`e1-editor-discovery` 與 `e2-mainloop-attribution` 都宣告
`editor-discovery-closed-actions`，後者另有 `mainloop-engine`（`SAL_LOK_OPTIONS=unipoll`
＋ `Application::Execute()` 的活迴圈，見 [finding 021](021-wasm-format-state-not-refreshed-by-caret-movement.md)）。
兩個 profile 的 `diagnostic.scope` 不同，既有的 E1／E2 typed client 都不同時收，
harness 因此照 `FormatDiscoveryClient.nudgeCaret` 的既有作法直接下封閉請求——動作清單
仍封閉在 harness 內，不出現 key code 或 UNO 命令。

序列即本 finding 的最小重現：開 `multi-paragraph.odt`、把 caret 放到
`第二段中文 beta` rectangle 末端、交替三輪 Home／End。每輪用**全新 engine**，因為一次
逾時就會讓 `gEditorPending` 卡住、後續全 BUSY。Firefox 153.0.1，每格 6 輪。

### 已觀察

| profile | 活迴圈 | 模式 | 完整通過的輪 | 動作 | 完成 | 逾時 |
| --- | --- | --- | --- | --- | --- | --- |
| `e1-editor-discovery` | 無 | collapsed | 1／6 | 16 | 11 | 5 |
| `e1-editor-discovery`（重跑） | 無 | collapsed | 2／6 | 20 | 16 | 4 |
| `e2-scheduler-attribution` | 無 | collapsed | 1／6 | 16 | 11 | 5 |
| `e2-mainloop-attribution` | **有** | collapsed | **6／6** | 36 | 36 | **0** |
| `e1-editor-discovery` | 無 | **extend** | **6／6** | 36 | 36 | **0** |
| `e2-mainloop-attribution` | 有 | **extend** | **6／6** | 36 | 36 | **0** |

三件事同時成立：

1. **逾時全部落在第一個 End**（步驟 2），Home 每次都完成。無迴圈的三格共 18 輪、14 輪
   在該步逾時；本 finding 原文寫的「第一個 End 逾時」不是偶發措辭，是穩定的位置。
2. **`e2-scheduler-attribution` 的行為與控制組相同**。它有 `verified-format-state`
   barrier 與相同的 worker patch，只是**沒有活迴圈**。因此差異不能歸給 format barrier
   或 worker patch，只剩迴圈。
3. **加上 Shift 之後，兩個 profile 都 36／36 零逾時**，且選取後置條件逐輪一致：
   shift-Home 選到 `text` 10 個字元、shift-End 收回 `none` 0 個字元。

### 推論

- **移動本身沒有壞。** Shift 模式證明同一個 END key event 在無迴圈的 build 上也確實把
  游標帶到行尾（否則 shift-Home 不會穩定選到 10 個字元、shift-End 不會穩定收回）。
  非 Shift 情形沒有可觀察後置條件，所以這是**推論**而非已觀察——但兩者只差一個修飾鍵。
- **差別在引擎等哪一個 callback。** `extendSelection` 為真時 `requiredCallback` 是
  `LOK_CALLBACK_TEXT_SELECTION`，那個訊號不需要活迴圈就會到；為假時是
  `EditorCaretOrSelectionCallback`（visible cursor），**End 的那一個在沒有活迴圈時不會
  在 30 秒內送達**。這與 finding 021 是同一個成因家族：要經過 VCL scheduler 的東西，
  在我方 engine 迴圈下不會發生。
- **Home 會完成、End 不會**，這個不對稱說明「無迴圈時 callback 一律不到」是錯的，
  發生的是更specific的事。成因未再往下追。

### 待驗證

- 非 Shift 的 End 是否真的移動了游標：需要一個不靠 callback 的位置後置條件。逾時後
  `gEditorPending` 卡住，同 worker 的後續動作只回 BUSY，因此無法在同一輪內補測。
- Home／End 不對稱的成因。
- Chrome 未跑；本輪只有 Firefox 153.0.1。
- Up／Down 未納入本輪序列。

### 對判定的影響

`CONFIRMED_CAPABILITY_REDUCTION` **維持**。line navigation 仍不升格：產品路徑用的是
collapsed caret（非 Shift），而那正是不可靠的那一半。但**修法方向改變了**：不需要等
上游，也不需要在產品裡跑主迴圈——只要completion 不依賴 visible-cursor callback。這與
[finding 022](022-e1-release-set-bold-false-noop.md) 之後採用的產品路線 C 是同一個原則：
不讀不可信的訊號，改用可觀察的後置條件。

證據：`findings/evidence/finding-018-line-nav-attribution/{summary,cells}.json`。
harness：`wasm_sdk_probe/web/f018-line-nav-check.html`、`f018-line-nav-app.js`
（`make f018-line-nav-assets`，**刻意不相依任何 profile**，兩個 profile 都是既有產物）。
