# 129 — 反白選取之後按方向鍵，一律被拒絕，而且畫面跳出開發用的英文錯誤

| | |
|---|---|
| **狀態** | **已確認、未修** |
| **所在** | 兩處。(1) profile `e2-editor-v19` 的 manifest：六個移動動作（`move-character-left/right`、`move-line-up/down/home/end`）的 `gestures` 都只有 `["collapsed"]`，也就是只宣告給「游標」，不給「選取範圍」；引擎的手勢閘門（`src/probe_engine.cpp`）照 manifest 拒絕，什麼都沒送出。(2) 我們的頁面 `wasm_sdk_probe/web/e2-editor-app.js`（`8909564e…`）：方向鍵的 keydown（:2398–2405）只問 `session.offers(action)`，**不問目前的選取形狀**就送出；被拒絕之後，`run()` 把錯誤碼和引擎的英文訊息原樣放進 toast（:1729） |
| **發現日** | 2026-10-12（擁有者手測宿主 0.2.12） |
| **嚴重度** | 一般：不丟資料，文件和工作階段都沒事。但「選了字之後按方向鍵」是最常見的操作之一，現在每次都失敗，而且失敗訊息是給開發者看的英文 |
| **可重現** | 每次（Chrome 與 Firefox 157；◀、下、End 各 1/1，兩個瀏覽器相同） |
| **是否上游** | 否 |

## 現象

擁有者原話：「將文字反白選取的時候，使用方向鍵會報錯」。

## 重現步驟

1. 在宿主 0.2.12 開任何文件，用滑鼠拖曳反白幾個字。
2. 按 ◀（或 ▶、上、下、Home、End）。

**預期**：選取取消，游標移到合理的位置（一般文書處理器的行為；LibreOffice 桌面版的確切行為要先量原生）。
**實際**：選取原地不動，狀態列顯示「◀ 失敗」，toast 顯示：

> `◀：EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of selection in this profile, so nothing was dispatched and the document is unchanged`

（下：「下移一行：EDITOR_FORMAT_GESTURE_UNSUPPORTED：…」；End：「移到行尾：…」。）工作階段維持「就緒」、Worker 世代不變、revision 不變。

## 證據

`findings/evidence/128/` 的 `chrome-1.json` 與 `firefox-1.json`，`selection` 臂（拖曳經過頁面自己的 pointer handler，拖完 `#toolbar[data-selection-shape]` 是 `range-single`，再按一個真的鍵）；說明在 `evidence/129/README.md`。

## 相關：Shift＋方向鍵（擁有者同次要求的功能，見規格 §17.25）

現在按 Shift＋▶，頁面**照樣當成 ▶ 送出**：游標移一格、沒有選取（兩個瀏覽器，3/3 下）。keydown 沒有看 `shiftKey`。這不是 129 本身，但和 129 是同一個缺口——頁面只有「游標」的移動，沒有「選取範圍」的移動與延伸——修的時候要一起想。

## 處置方向（未決，交規格）

- **只動頁面**：選取範圍時，方向鍵先把選取收起來（例如用頁面已有的點擊定位，點到選取的起點或終點），不送移動動作；至少不再顯示開發用訊息。收到哪一端、要不要再移一格，要先量 LibreOffice 原生的行為。
- **放寬 manifest**：把移動動作的手勢加上 `range-single`／`range-cross`，讓 Writer 自己處理選取中的方向鍵。manifest 是 profile 身分的一部分，要換 profile；引擎在選取狀態下的移動屏障能不能驗證，要先量。
- **toast 的措辭**：引擎的英文訊息不該直接給使用者看——這是頁面上所有 `run()` 失敗共用的路徑，範圍要先普查。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-12 | 初版：擁有者手測宿主 0.2.12 回報；同日用 `tools/probe_hand_test_0212.py` 在宿主上兩個瀏覽器重現 |
