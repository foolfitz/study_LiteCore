# 上游報告草稿：unipoll ＋ emscripten system loop 下，LOK 狀態更新收斂不到 process-to-idle 的結果

> **狀態**：草稿，**尚未送出**。2026-08-06 使用者決定整組實驗結束後再評估是否送出。
> **不要因為這份草稿存在就送出**——送出前的必要條件列在第 7 節，目前一項都沒完成。
> **來源**：[finding 021](findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)。
> 該 finding 是 canonical，本檔是它的對外裁剪版；兩者衝突時以 finding 為準。

## 1. 一句話

在 `SAL_LOK_OPTIONS=unipoll` ＋ emscripten system event loop 的組態下，
`SvpSalInstance` 每個 tick 呼叫的 `ImplYield(…, bHandleAllCurrentEvents=false)`
跑不出 `Scheduler::ProcessEventsToIdle()` 能跑出的 LOK 狀態更新：純 caret 移動之後，
被監看命令的 `LOK_CALLBACK_STATE_CHANGED` **要嘛不抵達、要嘛落後一個定位點**，
因此 LOK host 無法在動作前讀到當前段落的格式狀態。

## 2. 環境

- LibreOffice `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`（26.8）
- Emscripten SDK 4.0.10，`-pthread`，無 JSPI，無 PROXY_TO_PTHREAD
- LOK host 為核外連結的探針（自帶 `main()`），`SAL_LOK_OPTIONS=unipoll`，
  主迴圈經 `Application::Execute()` → `SvpSalInstance::DoExecute` →
  `emscripten_set_main_loop_arg(loop, this, 100, 1)`
- Chrome 150.0.7871.128 與 Firefox 153.0.1，逐項相同

## 3. 相關程式碼

| 位置 | 內容 |
|---|---|
| `vcl/headless/svpinst.cxx:303-305` | `loop()` 每 tick 呼叫 `ImplYield(comphelper::LibreOfficeKit::isActive(), false)` |
| `vcl/headless/svpinst.cxx:315` | `emscripten_set_main_loop_arg(loop, this, 100, 1)` |
| `vcl/headless/svpinst.cxx:442-444` | `ImplYield` 中 `DispatchUserEvents(false)` 若派掉事件即**提早 return**，跳過下一行 |
| `vcl/headless/svpinst.cxx:446` | 該行的上游註解：`CheckTimeout() invokes the sal timer, which invokes the scheduler` |
| `vcl/source/app/svapp.cxx:441-455` | `Scheduler::ProcessEventsToIdle()` ＝ `while (InnerYield(false, true))` |
| `vcl/headless/svpinst.cxx:103` | `__EMSCRIPTEN__` 下無條件 `m_bUseSystemLoop = true` |

## 4. 觀察到的行為

### 4.1 主要現象

以 `.uno:DefaultBullet`、`.uno:DefaultNumbering`、`.uno:StyleApply` 三個被監看命令為例，
在 fixture 的四個定位點（heading、一般段落、清單項、清單後段落）之間移動 caret 後讀狀態：

| 定位點 | raw STATE_CHANGED 抵達數（Chrome／Firefox） | 讀到的值 |
|---|---|---|
| heading | 1／1 | 未知 |
| 一般段落 | 2／2 | heading 的值 |
| 清單項 | 15／52 | 一般段落的值 |
| 清單後段落 | 5／5 | 清單項的值 |

即每個位置讀到的是**前一個位置**的值。

### 4.2 同一組態下 `ProcessEventsToIdle()` 是正確的

在同一個活迴圈組態下，每次定位後多呼叫一次 `Scheduler::ProcessEventsToIdle()`：
四個定位點全部讀到**當前段落**的正確值（清單項 `DefaultBullet=true`、
清單後段落 `false`），Chrome 與 Firefox 逐欄相同。

因此差異不在初始化、不在 caret 定位路徑，而在推進方式本身。

### 4.3 已排除的兩個解釋

- **`Desktop::Main` 初始化差異**：否。複合 profile 在活迴圈組態下 PEI 照常有效。
- **API 定位 vs 真實輸入路徑**：否。在 API 定位後加派一個真的游標命令
  （`move-character-left`，走完整 `SfxDispatch`）仍不觸發對位重算。

## 5. 機制假說（未隔離，送出前應補）

`ImplYield` 在 `bHandleAllCurrentEvents=false` 時，只要 `DispatchUserEvents` 派掉一件
user event 就提早 return，**跳過 `CheckTimeout()`**——而該行正是把 sal timer、進而把
scheduler 帶起來的地方。`ProcessEventsToIdle()` 則以 `bHandleAllCurrentEvents=true`
迴圈到靜止，不會有這個提早出口。

**注意**：`loop()` 與 PEI 之間有**三個**差異未隔離：
`bWait`（`isActive()`＝true vs false）、`bHandleAllCurrentEvents`（false vs true）、
以及 PEI 的外層迴圈。本節只是最有可能的一個，**不得寫成已確認**。

## 6. 可提的修法方向

1. emscripten 的 `loop()` 改傳 `bHandleAllCurrentEvents=true`，或改為迴圈到靜止。
2. 或提供一個受支援的 LOK 入口做等價的 process-to-idle。

> **不要寫成「LOK host 沒有受支援的入口」。** `Scheduler::ProcessEventsToIdle()`
> 本身是公開 API（`include/vcl/scheduler.hxx:65`，`class VCL_DLLPUBLIC Scheduler final`），
> 且有產品呼叫者（`sw/source/uibase/dbui/dbmgr.cxx:1375`、
> `sw/source/ui/dbui/mmresultdialogs.cxx:712`、`vcl/source/app/svmain.cxx:438`）；
> 被標為 unit-test 的只有 C 包裝 `unit_lok_process_events_to_idle`
> （`vcl/source/app/svapp.cxx:485-491`）。本報告的訴求是**每 tick 的迴圈語意**，
> 不是「缺入口」。附帶可提：該 API 的 doc comment 寫它呼叫
> `Application::Reschedule(true)`，與實作（`InnerYield(false, true)`）不符。

## 7. 送出前必須完成（目前 0/4）

1. [ ] 在**完全未修改**的上游 build 上重現（同 finding 020 的紀律）。目前所有證據都
   來自帶有我方診斷程式碼的隔離 profile。
2. [ ] 搜重複單。
3. [ ] 隔離第 5 節的三個因素，至少確定「改傳 `true`」是不是必要且充分——最省的做法是
   自己先打那一行 patch 重建再跑一次對照。
4. [ ] 確認 finding 020 的送出順位（它已有原生＋兩瀏覽器證據，較成熟）。

## 8. 最小重現素材

- 壞：隔離 profile `e2-mainloop-attribution`
- 好：隔離 profile `e2-mainloop-pei-attribution`（同組態＋每次定位後一次 PEI）
- 兩者的完整讀數在 `findings/evidence/sdk-e2/discovery/state-readback/` 下的同名目錄，
  各 attempt 實跑的 build 以其 `manifest.diagnostic.wasmSha256` 為準

## 9. 不屬於本報告的東西

- [finding 022](findings/022-e1-release-set-bold-false-noop.md)（我方 SDK 的假 no-op）
  是**我方缺陷**，與上游無關，不得混入。
- 產品路線 C（不讀前置狀態）是我方決定，與上游訴求無關。
