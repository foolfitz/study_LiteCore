# 139 — WASM 開長文件時是延遲排版，排完時引擎沒有發出頁面大小變化的通知；頁碼正確只靠重畫回覆那一條觸發

| | |
|---|---|
| **狀態** | **已登錄，目前不需要修**（2026-10-14）。產品今天不會顯示錯的頁數，原因是 §10.8 在計數器之外保留了「重畫回覆帶 `documentSizeChanged`」這第二條觸發。這一則記的是**依賴**：之後任何改動，只要拿掉那條觸發，就必須另外給延遲排版的完成一條觸發。 |
| **影響版本** | v20（連結批次，引擎 `313b08d5…`，殼層 v67）。頁碼只在 v20 上才有。v19 以前的引擎很可能也是延遲排版，但沒有頁碼可以看出這件事，所以沒有量過。 |
| **所在** | 引擎沒有發出 `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED`：核心的 CalcLayout 路徑不發任何通知（`libreoffice-26-8/sw/source/core/view/viewsh.cxx:1294–1321`，審核 6 §3 讀到的那條「沒有觸發」的路）。頁面這一側，`PageRectanglesScheduler` 在 `editor-shell-v2/narrow-editor-v2-session.js` 裡有三個觸發點：開檔、計數器變動、重畫回覆。 |
| **發現日** | 2026-10-14，v20 第一輪 WASM shakedown 的 P2-c 量測臂（`findings/evidence/link-batch/v20-shakedown/README.md` §4，任務 10-14e）。 |
| **嚴重度** | 低：使用者今天看不到錯誤。風險是將來的改動。 |
| **可重現** | 兩個瀏覽器各一次，結果相同（Chrome 151、Firefox 157）。 |
| **是否上游** | 否。核心在 CalcLayout 時不發通知是它既有的設計；問題在我們的觸發是否夠用。 |

## 量測

60 頁的固定文件，開檔到排版穩定：

- 共 202 個 LOK 事件，**沒有任何一個是 13 號**（`DOCUMENT_SIZE_CHANGED`）；`documentSizeChangedCount` 從開檔到穩定一直是 0。
- 第一次讀 `pageRectangles` 只回 **1 頁、1 個矩形**；穩定之後是 **60 頁**。
- 拿到 60 的那一次讀取，是由**重畫回覆**的 `documentSizeChanged` 觸發的（頁面的 `sizeChangeReported`）。

對照：8 頁的混合紙張文件只有一個畫面高，第一次讀就是 8 頁，沒有延遲排版。原生 26.8 開同一份 60 頁文件時，排版在載入當下就已經完成（審核 6 §3）。

**編輯時的大小變化不受影響**：按 16 下 Enter 再按 16 下 Backspace，共 249 個事件、2 次大小變化。兩次的前後 25 ms 內都同時有 `INVALIDATE_TILES` 和 `INVALIDATE_VISIBLE_CURSOR`，所以 P2-c 判 `NOT_ESTABLISHED`，finding 138 維持 SHOULD 等級。

## 這一則改變了什麼

- 審核 6 §3 原本寫的是「有條件、沒示範過」：要在載入後排版還沒完成的情況下才會發生，原生上排版在載入時就完成，WASM 沒量過。現在量到了：**這條路在 WASM 上真的存在。**
- 規格裡「計數器就是觸發」的說法，以及 L-page-size-invariant 的文字，都應該點名這一則：計數器只涵蓋編輯造成的大小變化，延遲排版的完成要靠重畫回覆。
- 之後的連結批次如果改了重畫回覆的 `documentSizeChanged`，或改了排程器的觸發，這一則就是要先過的紅案：開 60 頁文件，頁碼必須在穩定後顯示「共 60 頁」。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-14 | 登錄（v20 shakedown P2-c）。`findings/README.md` 的索引只到 059，沒有可改的索引行（既有缺口，同 137、138） |
