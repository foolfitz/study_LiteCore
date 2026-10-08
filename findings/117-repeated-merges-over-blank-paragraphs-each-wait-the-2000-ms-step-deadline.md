# 117 — 在連續空段落上重複併段：幾乎每一下都要等滿 2000 ms 的步驟期限才確認，並跳出一次「重繪失敗」

| | |
|---|---|
| **狀態** | **已確認、未診斷**（2026-10-08）：兩個瀏覽器、儀器版與對照組都重現；成因只有讀原始碼得到的假說，未量 |
| **所在** | 我們自己的引擎：選項 B 的併段（`OXSDK_MERGE_KEY_UNDO`，`wasm_sdk_probe/src/probe_engine.cpp`）——送出按鍵之後，要等**任何一個** LOK 回呼排進一個步驟，才去讀 `.uno:Undo` 比對；沒有回呼就只能等期限到了自己讀 |
| **發現日** | 2026-10-08（規格 §30.2 的 M2-4 第一次在 WASM 上跑，`evidence/v18/m2-shakedown/`，不算數的 shakedown） |
| **嚴重度** | 一般：沒有資料遺失，105 下最後的文件逐位元組（化約後）等於 Writer 自己按 105 下的結果；但使用者在空白行上連按 Delete，每一下要 **2.1 秒**才回應，中間還會看到一則錯誤 toast |
| **可重現** | 決定性：Chrome 與 Firefox 都是同樣三下快（第 1、3、55 下）、其餘 102 下都等滿期限；儀器版與對照組（不記回覆的觀察器）同樣出現那則 toast |
| **是否上游** | 否（我們的引擎怎麼等證據；LOK 去重回呼若是觸發條件，那是 LOK 照設計運作） |

## 現象

fixture `test-docs/merge/odt/undo-limit-105.odt`（`09b5ced0…`，R0 第 4 輪的 H03）：游標放在 `S01` 段尾，後面是一長串空段落。透過產品頁面連按 105 下真鍵 Delete，每一下等到該刪除的回覆才按下一下。

- 105 下全部回 `verified-key-undo`，comment 都是 `Delete paragraph`，`restorePresses` 0，沒有重開（generation 不變）。
- `actionsAfter` 從 1 數到 100，之後維持 100：復原上限有到。
- 最終文件化約後的 `content.xml` 與段落文字都等於原生第 105 下（107 段 → 2 段）。
- **但是**：引擎回報的 `keyToUndoMs` 中位數 2001 ms，只有第 1、3、55 下是 37 ms 左右，其餘 102 下都是 2000 或 2001。runner 量到的延遲最多 2103 ms。
- 跑完時頁面上有一則 toast：「重繪失敗：TILE_NOT_PAINTED：引擎回了一張沒有畫進去的圖」。是第幾下出現的沒有記錄。

對照：同一個引擎上，一般併段的 `keyToUndoMs` 是 28–49 ms；打字後立刻併段（Y01／Y02，M2-1b）是 628–633 ms，而且每次都是這個數字。

## 量到的（`evidence/v18/m2-shakedown/`，runner `927e2863…`，v18、頁面 `cfc8ba1d…`）

| 執行 | 瀏覽器 | 105 下都 verified | 快的幾下 | `keyToUndoMs` 中位數 | toast | 終態＝原生 |
|---|---|---|---|---|---|---|
| `m2-4-chrome.json` | Chrome | 是 | 1、3、55 | 2001 | 重繪失敗 ×1 | 是 |
| `m2-4-control-chrome.json` | Chrome（對照） | （儀器條款 NE） | — | — | 重繪失敗 ×1 | 是 |
| `m2-4-firefox.json` | Firefox | 是 | 1、3、55 | 2001 | 重繪失敗 ×1 | 是 |
| `m2-4-control-firefox.json` | Firefox（對照） | （儀器條款 NE） | — | — | 重繪失敗 ×1 | 是 |

## 讀原始碼得到的假說（未量）

- 引擎在按鍵送出後進入 `MergeAwaitingKey`。在這個階段，`feedMergeAttribution` 收到**任何** LOK 回呼都會排一個步驟（`probe_engine.cpp` 約 3510–3560 行，`gMergeTicket.afterKey`）。步驟裡的 `verifyMergeKey(false)` 讀一次 `.uno:Undo`，跟按鍵前的 P0 比：變了就完成，沒變就繼續等。
- 期限到時（`MergeStepDeadlineMs`＝2000）由 `handleMergeDeadline` 呼叫 `verifyMergeKey(true)`；這時讀到 payload 已經變了，就照樣完成成 `verified-key-undo`。所以 102 下都是「證據其實早就在，但沒有人叫引擎去看」。
- 推論：在同一個游標位置、刪掉一模一樣的空段落時，鍵處理完**之後**沒有新的回呼被送出。可能是 LOK 的 `CallbackFlushHandler` 把和上一次相同狀態的回呼去重了（`desktop/source/lib/init.cxx` 的 `m_states`，對 `TEXT_SELECTION`、`INVALIDATE_VISIBLE_CURSOR` 等），或是回呼在復原紀錄寫入之前就已送出。第 1、3、55 下為什麼不同（例如第 55 下附近文件從兩頁變一頁、送出文件大小改變的回呼）**沒有查**。
- 「重繪失敗」與上面的延遲是不是同一個成因，**未知**。

## 影響

- M2-4（§30.2）照字面：除了「沒有 toast」以外每一條都過；**因為那則 toast，M2-4 是紅的**，而且紅在產品上，不是紅在門檻上（對照組也有）。
- 每下 2 秒的延遲**沒有任何判準在守**：M2-2 只涵蓋 M2-1 的完成。
- M2-1（20 個合成 case）與 M2-1b 不受影響，都是快的。

## 未做

- 第 1、3、55 下為什麼快；鍵之後到底有哪些回呼、何時到（需要在引擎記錄回呼序列，或在原生 LOK 上量）。
- 「重繪失敗」是第幾下出現、對應哪一張圖塊。
- v15–v17 是否相同（推論相同：引擎沒變，wasm 都是 `ad3f68bb…`）。
- 修法：要動引擎就要重新連結（v19），由擁有者決定。

## 時間軸

- 2026-10-08 10:27–10:52：M2-4 在 v18 上第一次執行（Chrome、Firefox，各加對照組）；四份都有那則 toast，兩個 `--pair` 都是 0 差異。
