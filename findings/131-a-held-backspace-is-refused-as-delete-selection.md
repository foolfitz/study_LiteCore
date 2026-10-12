# 131 — 連按 Backspace，有幾下被當成「刪除選取」拒絕：跳出開發用的句子、字留在原地

| | |
|---|---|
| **狀態** | **已修，判準成立**（頁面 `d761f1ce…`＝規則 A，`6326d31b`；131-B 兩個瀏覽器各 6 次全乾淨、紅色對照紅）。隨 0.2.13 出貨；0.2.13 的計數鏈在寫這份檔時還沒跑，發佈與否看 `RESULT-0.2.13` |
| **所在** | 我們的頁面 `wasm_sdk_probe/web/e2-editor-app.js` 的 `beforeinput` 刪除監聽器（finding 121 的 `deleteActionFor`）＋引擎的刪除閘門 `probe_engine.cpp:5277-5303`（以 `selectionRectangles.empty()` 拒絕） |
| **發現日** | 2026-10-12（128-B 第一輪的連按臂，`3d45e895`；同儀器 A/B，`87b38132`） |
| **嚴重度** | 高：按住或連按 Backspace 是每個人刪幾個字的方式。修法前的 0.2.13 大約每四下就有一下被拒絕（19/80）、跳出開發用的英文句子（`EDITOR_FORMAT_GESTURE_UNSUPPORTED`）、字留在文件裡；出貨中的 0.2.12 也有，大約每二十下一下（4/80） |
| **可重現** | 已量：`probe_hand_test_0212.py`，20 下真的 Backspace、間隔 50 ms。0.2.12 頁面 4/80、0.2.13 修法前 19/80（`evidence/128/rapid-ab/`）；修法前的引擎包換回宿主當紅色對照，每個瀏覽器 1 次連按各 5/20 被拒（`evidence/131/red-control/`） |
| **是否上游** | 否 |

## 現象

連按 Backspace 時，偶爾有一下變成「刪除選取 失敗」，畫面跳出 `EDITOR_FORMAT_GESTURE_UNSUPPORTED`，那個字沒有被刪。

## 機制（fable 裁決讀碼確認，`evidence/128/ruling/fable-ruling.md`）

- 引擎對每一個改變狀態的回呼都送 `editor-state`，包括刪除 barrier 自己選一個字時的那一次 TEXT_SELECTION（`probe_engine.cpp:2648`，沒有抑制）。
- session 在 `sourceSequence` 前進時轉送（`narrow-editor-v2-session.js:280-300`），刪除監聽器讀的就是這份即時快照。所以前一下的 barrier 還在途時，監聽器看到的是「有一個字被選取」。
- finding 121 的規則照引擎的形狀決定：形狀是範圍就送 `delete-selection`。
- 動作在頁面那一側序列化（`editor-session.js:290-314`）：這一下要等前一下回來才送出，那時游標已經收起，閘門以 `selectionRectangles.empty()` 拒絕。

0.2.13 讓它變多約五倍。推論（未單獨量）：128 的處方 B 讓動作一結束就重畫，連按時每一下刪除在途更久（中位數 46–49 → 63.5–67 ms），窗口跟著變大。

## 修法：規則 A（SPEC-M3-autosave §9.12）

- 頁面計數「自己送出、還沒結算」的刪除（`deletesInFlight`，宣告在 `engineActionsOut` 旁）：呼叫 `editorAction(...)` 之前 ＋1，在 `.finally` −1。
- 計數 > 0：照這一鍵自己的收起形式送出（`delete-backward`／`delete-forward`），不看引擎此刻的形狀——在途的那一下回來時只可能是游標，此刻的範圍是 barrier 的，不是使用者的。
- 計數 = 0：照 finding 121。
- 刻意不放寬成 `engineActionsOut > 0`：真的選取範圍＋Ctrl+B＋Backspace 仍要以 `delete-selection` 送出。

## 判準與量測

- **131-B 成立**（`c6975615`，`evidence/131/131-B/`）：每個瀏覽器 6 次 × 20 下，12/12 `deleted 20`、`refused 0`、`other []`；同一次執行 `high`／`low` 四臂 `persistent.differing` 0 ×4（修法前 21778／13843／0／13843）。
- **紅色對照紅**（`85a20adb`）：修法前的引擎包換進宿主，兩個瀏覽器各 5/20 被拒；換回之後 `check_engine_decoded.py` 通過。讀取器 `evidence/131/judge_131b.py`。
- **121 沒有壞**：121-U 215/215；121-B 4/4（兩個瀏覽器 × Backspace／Delete，「刪除選取 9–15 ms」，§9.13）。

## 登錄的邊界（不是判準）

- 真範圍上的第一下刪除本身被拒絕時，它窗口內的下一鍵會以 `delete-backward` 送到範圍上，也被拒絕：兩個 toast、不丟資料（§9.12）。
- 段落格式動作的 barrier 也會選文字（`.uno:SelectText`，finding 083），那個窗口內按 Backspace 可能用同樣的方式讀到範圍。規則 A 刻意只管刪除；未量（§9.12 工作項）。
- 範圍刪除之後立刻再按一下 Backspace，應以 `delete-backward` 送出而不被拒：未量，NOT_ESTABLISHED（§9.16）。

## 相關

- 修好之後，長按的殘影與佇列落後是另一張：finding 132；畫面那一半的具名限制是 L-128-rapid（§9.15）。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-12 | 初版：128-B 第一輪掉出、同儀器 A/B、fable 裁決（凍結前修頁面）、規則 A、131-B 成立與紅色對照；之前只登錄在規格（§9.12–§9.16）、裁決與 commit 訊息裡 |
