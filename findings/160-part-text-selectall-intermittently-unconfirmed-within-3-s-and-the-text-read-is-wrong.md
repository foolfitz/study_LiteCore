# 160 — `part_text` 的 `.uno:SelectAll` 間歇性在 3 秒內沒等到命令結果；那一次讀到的文字是錯的（全語料 482 次讀取中 2 次）

| | |
|---|---|
| **狀態** | **已觀察、間歇**（2026-10-20）；未修 |
| **Bugzilla** | 無 |
| **發現日** | 2026-10-20（`phase-e/report-2026-10-20T133240Z.json`） |
| **嚴重度** | 一般：E3 會抓到（`selectAllConfirmed: false` 加文字不等）。~~但在產品路徑上就是讀到錯的文字~~（2026-10-21 更正：產品頁面、session、adapter 沒有任何地方呼叫 `partText`，呼叫它的只有 E3；所以這是 E3 的量測儀器與 SDK 能力 `part-text` 的正確性問題，使用者看不到。`SPEC-M4-viewer-v2` §0） |
| **可重現** | **2／482**（全語料那一輪：`tdf160329_sortWithHiddenRows.ods` 讀到 1 個字、`tdf139258_rotated_image.ods` 讀到空）；診斷重跑同兩筆 **0／2**（都 `true`、文字正確）。次數就是量測，別拿單次下結論 |
| **是否上游** | 否（我們的引擎，`probe_engine.cpp:2632-2690`） |

## 現象

A4.7 把 `part_text` 改成「最多等 SelectAll 的 `UNO_COMMAND_RESULT` 3 秒，等不到也照讀、照取消、照切回，回覆 `selectAllConfirmed: false`」。
全語料的 10 分鐘 sweep 裡有 2 次走到這條路：`tdf160329` 期望 74 字讀到 1 字（選取還沒落地就讀）、`tdf139258` 期望空讀到空（碰巧對）。
兩筆單獨重跑都在 3 秒內確認。

## 讀法

- 這不是 A4.7 的錯——它如實說了原因，E3 也因此紅在對的地方。**是 3 秒在負載下不夠**，或 SelectAll 在某些文件（隱藏列、只有圖片的表）
  上偶爾不回 `UNO_COMMAND_RESULT`。兩個假說都沒證據，不指認。
- 不在 harness 裡重試：重試會把產品的時間弱點藏起來。E3 對未確認的讀取保持紅，次數記在 handoff。

## 下一步

- 把 `kPartTextSelectAllDeadlineMs` 拉長或改成「等到選取真的存在」（讀回 `getTextSelection` 非空或 `SelectAll` 的 state 變化）要**連結**；
  排進下一個檢視連結（與 finding 157 的 `part_info` 同批）。
- 在那之前，若要量發生率：同一份全語料再跑 N 次、數 `selectAllConfirmed: false` 的次數。
