# 083 — barrier 把「選取回來是空的」當成卡住，於是對一個空段落上的項目符號開出「回到檢查點」

| | |
|---|---|
| **狀態** | **成因量到、已修、修法量到生效**（2026-08-26）。修在殼層與 worker，**沒有動引擎、沒有連結** |
| **發現日** | 2026-08-26，finding 082 修好之後它成為 a11y 線上唯一一致的紅 |
| **嚴重度** | **高（對 a11y 產品線）**：使用者在空白行上按項目符號，產品叫他把上次存檔以來的東西全部丟掉——而那顆項目符號其實已經套上去了 |
| **可重現** | **3/3**，`e2-editor-v10`；出貨那顆 core 走的是另一條路（見下） |
| **是否上游** | **否**。誤判在我們的 `sdk-worker.js` 投影與 `paragraph-editor-client.js` 的處置 |

## 一句話

`.uno:SelectText` 在**空段落**上，在 a11y core 上**什麼都選不到**；barrier 要「選取指令的
回覆」**和**「非空的選取矩形」兩者才會前進，所以它等滿 5000 ms、報
`stage-deadline:awaiting-selection`，而那個 shape 的處置是 **rollback**。

**引擎其實已經知道答案了**：`selectionResultSeen: true` 配上空矩形，代表引擎**回答了**，
而答案是「沒有東西被選取」。是 `productFormatBarrier` 的白名單把那個欄位丟掉，
所以沒有任何 host 能據以判斷。

## 兩顆 core，同一格，同一支 harness

| | `e2-editor-v8`（產品 core） | `e2-editor-v10`（a11y core） |
|---|---|---|
| `stage` | **`awaiting-restore`**——過得去 | **`awaiting-selection`**——死在這裡 |
| `failureShape` | `multi-block-readback` | `stage-deadline:awaiting-selection` |
| `selectionResultSeen` | true | **true** |
| `selectionType` | **1**（`LOK_SELTYPE_TEXT`） | **-1** |
| `readback.blockCount` / `itemCount` | **2 / 2** | 0 / 0 |
| `readback.bytes` | 592 | **0** |
| 使用者拿到的處置 | **review**——佇列開著、session `ready` | **rollback**——佇列被擋、`recoverable-error` |

**動作本身兩顆 core 完全一樣**：`.uno:DefaultBullet` 都回 `success: false,
wasModified: true`（finding 020 記過的形狀，引擎本來就不採信這兩個欄位）。
**不一樣的是 barrier 自己那次讀**：產品 core 上選取**溢出到下一段**（finding 046，
8 格 × 2 瀏覽器量過），所以讀到兩段；a11y core 上**一段都沒選到**。

## 一張撤銷過的佇列項，原來只對一顆 core 成立

`p1-3b-empty-readback` 在 2026-08-16 被**撤銷**，理由是「量過了：沒有東西可以讓它指名……
沒有任何一支臂產生 parsed 而 zero blocks 的讀回」。那次量測跑在一顆與 `e2-editor-v2`
逐位元相同的診斷 profile 上——**產品 core**。在 a11y core 上它要找的情況**真的發生**，
而且早一個 stage：不是「讀回是空的」，是**根本沒有選取可讀**。
那張撤銷自己留的但書（「若真的出現，round-two 那格會顯示它」）現在生效了。

## 沒有量的（因此不指認）

**為什麼兩顆 core 在那個指令上不一樣。**a11y core 是 `writer calc` ＋ accessibility，
對上一顆 writer-only 且沒有 accessibility 的 build——**兩個差異、一次量測**。
在這裡指認一層就是 finding 040 和 048 的錯第三次。而且哪一邊「對」也不明顯：
**不溢出到鄰段，說不定才是比較正確的那個行為。**

## 修法（不動引擎、不連結）

處置本來就在 **JavaScript** 裡（`editor-shell-v2/paragraph-editor-client.js`），
keyed 在 `failureShape`。所以：

1. **worker 轉發 `selectionResultSeen`**（`sdk/sdk-worker.js`）。引擎一直有送，是白名單
   丟掉的；沒有它就分不出「引擎沒回答」和「回答了，答案是沒有東西被選取」。
2. **處置多一條窄分支**：`dispatched && route === "collapsed" &&
   failureShape === "stage-deadline:awaiting-selection" && selectionResultSeen === true`
   → `dispatched-unverified`（review）。窄在四個條件上，三個都有突變測到：拿掉
   `selectionResultSeen`、放寬成任何 stage deadline、拿掉 route 保護，測試都會紅。
   **一個沒人能歸因的卡住仍然保留它的 rollback**——這和 finding 059 的分支同一個論證：
   引擎回答了，就代表它沒有卡死。
3. **頁面給這個 shape 自己的句子**。只改處置的話，使用者會拿到 review **配一個字面不成立
   的理由**（「涵蓋了不只一個段落」——可是根本什麼都沒選到）。那是 finding 061 的形狀，
   這棵樹已經為它立過一張 finding。新句子說的是實情：這一段是空的，選取取不到內容。

**殼層 generation 凍成 v42**——而且是**凍一次**：我第一次凍太早（頁面那半還沒改），
撤掉重來。這正是這棵樹寫過的教訓。

## 量到的（`e2-editor-v11`，預測寫在跑之前）

v11 是 **v10 的 artifact 重新打包**：同一顆 wasm（`4ec1e389aaab3b03`）、同一個 loader，
**只有 `workerSha256` 不同**（`070229cd` → `03f5b69a`）。沒有連結。

| 預測 | 實測 |
|---|---|
| `bulleting-…` 過，`ready`，不說「請回到檢查點」 | **PASS** |
| toast 帶**新句子**，紀錄 `unverifiedSentence: "empty-selection"` | **是** |
| `notice-action-recovers-the-session` 回到 NOT_ESTABLISHED（**已宣告的代價**） | **是**，而且 `recoveryPairing.held: true` |
| 其他格不動，那一格仍六支臂全過 | **是** |

**整輪 37 PASS / 3 NOT_ESTABLISHED，`ok: true`，一格紅都沒有**——這是 a11y 這條線
**第一份乾淨的產品路徑**。

## 已宣告的代價

`notice-action-recovers-the-session` 在 a11y 線上**失去了它的誘發器**。它在 v10 上會過，
只是因為那顆 core 壞在這一格；修好之後那條路就跟產品 core 一樣不再擋佇列。
這和 2026-08-17 在產品 core 上軟化 046 處置時付的是同一筆代價，
`finish()` 裡的配對關係當場就抓到了。**這不是意外，是帳。**

## 證據

- `findings/evidence/queue-a11y-stage-deadline-awaiting-selection/PREDICTION.md`
  （兩份預測，都寫在跑之前）與 `RESULT.md`
- 同目錄：兩顆 core 的整包 barrier payload

## 修訂紀錄

- 2026-08-26：建檔，同日修好並量到生效。
