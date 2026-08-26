# 081 — a11y core 上「產品路徑會停住」不是卡在引擎，是一個**已經死掉的 session 被繼續驅動**

| | |
|---|---|
| **狀態** | **處方 1 已做並量到它生效**（2026-08-26）。**第一個失敗的成因：在 2026-08-26 那一輪 v9 上量到了**（見下），但只有一輪，尚未確立它每一輪都是同一格 |
| **發現日** | 2026-08-24，接手 `HANDOFF-2026-08-23c` 開放項目 2「attach 到一個停住的 run，問它在哪裡」 |
| **嚴重度** | **高（對 a11y 產品線）**：它讓每一輪 a11y 產品路徑花 20–50 分鐘產出零，而且**看起來像引擎在 hang** |
| **可重現** | 這一輪重現了（`a11y-calloc`）。歷史上 8 輪裡 4 輪，出貨那顆 core 從未發生。**2026-08-26 在 `e2-editor-v9`（與 `a11y-calloc` 同一顆 wasm `b60cc46f…`）上再現一次** |
| **是否上游** | **未定**。停住本身是 harness 的（已修）；第一個失敗是引擎 barrier 的一個 `failureShape`，只在 a11y core 上出現，成因未查 |

## 一句話

到某一格為止一切正常，然後**一次 format barrier 失敗**把 session 推進
`recoverable-error` 而且**沒有檢查點**；此後每一個動作都被 `EDITOR_NOT_READY` 立刻拒絕，
而 harness 繼續一格一格驅動下去，**每一格燒掉自己的逾時**。
牆上的時間看起來像 hang，實際上**沒有任何東西在等引擎**。

（2026-08-26 就地修訂：這一段原本寫「一次**存檔**失敗」。存檔那一筆是**後果**——
它只是 `latency` 欄裡留下的最後一筆。真正的第一個失敗見下面〈第一個失敗是什麼〉。）

## 現場（CDP 直接問活著的頁面）

```json
{
  "state": "recoverable-error",
  "revision": "1",
  "pending": "0",
  "checkpoint": "無",
  "latency": "儲存 失敗",
  "doc": "format-a-paragraph.odt",
  "toast": "儲存：EDITOR_NOT_READY：editor operation save is unavailable in recoverable-error",
  "notice": { "show": "1", "text": "引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。" }
}
```

**`pending: 0` 是關鍵那一格。**沒有任何請求在飛。所以這不是
「format barrier 的 `stage-deadline` 把引擎卡住」——那個假說會預測 `pending ≥ 1`。

## step 軌跡：慢下來的地方和死掉的地方不是同一格

```
132.4s PASS             a-failed-format-does-not-block-the-session
323.6s NOT_ESTABLISHED  format-a-paragraph-changes-that-paragraph   ← 191 秒
507.2s NOT_ESTABLISHED  cut-removes-the-selected-text               ← 184 秒
507.2s NOT_ESTABLISHED  a-refused-action-is-reported-and-changes-nothing
       （之後 `every-inline-format-reaches-the-document` 再也沒有回報）
```

前 132 秒**全部通過**，包含三格格式檢查。文件名 `format-a-paragraph.odt` 對得上
——存檔是在 `format-a-paragraph-changes-that-paragraph` 那一格失敗的，那格花了 191 秒。

## 這改寫了交接文件裡的那個假說

`HANDOFF-2026-08-23c` 開放項目 2 寫：「format barrier 的 `stage-deadline`……**可能就是
產品路徑在那個 profile 上停住的同一件事**」。

**兩件事都在，但不是同一件。**停住的機制是「死掉的 session ＋ 繼續驅動」，
與 `stage-deadline` 無關；`stage-deadline` 可能是**第一個失敗**的成因，也可能不是
——**沒有量到**。

## 沒有量的（因此不指認）

- ~~**第一個失敗是什麼。**~~ **2026-08-26 在一輪 v9 上量到了**，見下。原文保留：
  「`latency` 只留下最後一筆（儲存 失敗），而在 `recoverable-error` 裡連存檔都被拒，
  所以那一筆本身可能已經是**後果**不是**原因**。」——這個懷疑是對的。
- **為什麼沒有檢查點。**`_checkpointBeforeSelection` 應該在選取手勢前寫一個。
  `checkpoint: 無` 代表它沒寫成或寫失敗了，兩者後果不同。
- **是不是 calloc 之後才這樣。**這一輪跑的是 `a11y-calloc`。v5 上的停住是同一個形狀
  但沒有人抓過現場，所以**不能說 calloc 沒有改善它、也不能說有**。
- **和 v5 被退回的另外兩個紅的關係。**「粗體沒到文件」在這一輪的前 132 秒是**通過的**
  （`a-format-that-worked-is-not-reported-as-failed`、`bold-can-be-turned-off-again`），
  但那是在 session 死掉之前。

## 2026-08-26：處方 1 做了，而且第一次量到它在真的死掉的 session 上生效

`queue-a11y-path-drives-a-dead-session` 已實作（`tools/run_e2_c_product_path.py`
的 `class Liveness`）：每記錄一格檢查就讀一次頁面狀態，`recoverable-error` 或
`restart-required` 就**停止驅動**、指名「在哪一格之後發現的」、依原始碼順序列出
**沒跑到的那些格**，並且 `ok: false`。兩個**故意**把 session 推進那個狀態再救回來的臂
（047 的配方、038 的尾註誘發器）在自己裡面把守衛關掉，離開時**再讀一次**——救不回來的
臂會指名自己停掉整輪，而不是連累下一格。

**量到的（2026-08-26，chrome，`e2-editor-v9`）**：

```
132.1s PASS             a-failed-format-does-not-block-the-session
322.3s NOT_ESTABLISHED  format-a-paragraph-changes-that-paragraph
322.3s NOT_ESTABLISHED  the-run-stopped-because-the-session-was-dead   ← 停在這裡
```

報告裡的死亡現場，和 2026-08-24 用 CDP 讀活頁面得到的那一份**逐欄相同**：
`state: recoverable-error`、`pending: 0`、`checkpoint: 無`、`latency: 儲存 失敗`、
toast `儲存：EDITOR_NOT_READY：… unavailable in recoverable-error`。
差別是這一次**它自己寫進報告裡**：`recorded: 17/40`，`neverReached` 列出 23 格。
整輪 5 分 22 秒，不是 20–50 分鐘，而且留下一份可讀的報告。

## 第一個失敗是什麼：這一輪量到了（同上那一輪）

081 原本寫「`latency` 只留下最後一筆，所以那一筆可能是後果不是原因」。
現在整格的逐臂紀錄留在報告裡，順序自己說話——`format-a-paragraph-changes-that-paragraph`
的五支臂：

| 臂 | 動作 | 結果 |
|---|---|---|
| 1 | `set-paragraph-heading` | **PASS**（`標題 36 ms`，讀回 `Heading_20_1`） |
| 2 | `set-paragraph-body` | **FAIL** — `MUTATION_OUTCOME_UNKNOWN`：「the postcondition read describes a different paragraph from the one this action was dispatched on」，處置 rollback |
| 3–5 | 三個清單動作 | **NOT_ESTABLISHED** — `定位游標 失敗`，游標放不上去 |
| 之後 | 存檔 | `EDITOR_NOT_READY` → `latency: 儲存 失敗` |

`MUTATION_OUTCOME_UNKNOWN` 在 `RECOVERY_ERRORS` 裡（`editor-shell/editor-session.js:15`），
所以**臂 2 一失敗，佇列就被擋住、session 就進 `recoverable-error`**。
臂 3–5 的「游標放不上去」和最後那筆「儲存 失敗」都是**後果**。

**所以：這一輪的第一個失敗是臂 2 的 `readback-is-a-different-paragraph`，不是存檔。**
存檔那一筆之所以會被誤讀成原因，只是因為 `latency` 只留最後一筆——正是 081 自己提醒過的陷阱。

**沒有確立的**：這是**一輪**。它是不是每一輪都死在同一格、同一支臂，另外三輪已排隊
（`--barrier-details-diagnostic`，會把 barrier 的型別化 payload 一起收下來）。

## 同一輪裡 session 其實死了兩次

`bulleting-a-blank-line-does-not-demand-a-rollback` 在 108.0s 就 **FAIL** 了，
toast 是另一種 failureShape——`the format barrier stopped advancing before it could
read the paragraph`（`stage-deadline`，2026-08-23 就記過的那個），`state:
recoverable-error`、`queueStillOpen: false`。緊接著 111.3s
`notice-action-recovers-the-session` **PASS**：產品的回復通知按下去，session 回到 ready。

所以 a11y core 這一輪產生了**兩種不同的 barrier 失敗**，都會把 session 推進
`recoverable-error`：第一種被回復臂救回來，第二種沒有人救，整輪就結束在那裡。

## 處方

1. **harness 側，便宜且立刻有用**（**已做，2026-08-26**）：`finish()` 之前每一格檢查先問 session 狀態，
   一旦是 `recoverable-error` 就**停止驅動並把報告寫出來**，把整格標成
   `NOT_ESTABLISHED` 並指名「session 在第 N 格死掉」。
   現在的行為是丟掉整輪 20–50 分鐘**而且不留報告**——報告只在最後才寫。
   這一條和 finding 080 同源：**一個永遠不會成立的前提被一格一格重試**。
2. **產品側**：沒有檢查點時進入 `recoverable-error`，使用者被告知「內容不會回來」。
   在 a11y core 上這條路顯然走得到，值得單獨查。

## 證據

- `findings/evidence/f076-calloc-on-the-core-that-showed-it/a11y-stall-live-page-state.json`
- `findings/evidence/f076-calloc-on-the-core-that-showed-it/a11y-stall-step-trace.txt`

- `findings/evidence/queue-a11y-path-drives-a-dead-session/`（2026-08-26）：
  守衛裝好後的出貨 core 基準線、控制組第一輪為什麼沒有燒起來、
  以及**守衛在 v9 上真的停下一輪**的那份報告與 step 軌跡。

## 修訂紀錄

- 2026-08-24：建檔。CDP 接上一個活的停住現場，`pending: 0` 把「hang」這個說法否證掉。
- 2026-08-26：處方 1 實作完成並量到它在真的死掉的 session 上生效（v9，5 分 22 秒停下、
  留下報告、列出 23 格沒跑到的）。**第一個失敗的成因在那一輪確立**：是
  `set-paragraph-body` 的 `readback-is-a-different-paragraph`，不是存檔；存檔是後果。
  另補記同一輪裡 session 其實死了兩次，兩次的 failureShape 不同。
  仍未確立：這是不是每一輪都一樣（三輪重複已排隊）。
