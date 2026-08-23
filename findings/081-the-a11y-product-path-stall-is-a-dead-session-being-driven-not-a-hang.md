# 081 — a11y core 上「產品路徑會停住」不是卡在引擎，是一個**已經死掉的 session 被繼續驅動**

| | |
|---|---|
| **狀態** | **現場量到了**（活的停住現場，2026-08-24）。**第一個失敗的成因未確立** |
| **發現日** | 2026-08-24，接手 `HANDOFF-2026-08-23c` 開放項目 2「attach 到一個停住的 run，問它在哪裡」 |
| **嚴重度** | **高（對 a11y 產品線）**：它讓每一輪 a11y 產品路徑花 20–50 分鐘產出零，而且**看起來像引擎在 hang** |
| **可重現** | 這一輪重現了（`a11y-calloc`）。歷史上 8 輪裡 4 輪，出貨那顆 core 從未發生 |
| **是否上游** | **未定**：第一個失敗是什麼還沒確立 |

## 一句話

到某一格為止一切正常，然後**一次存檔失敗**把 session 推進 `recoverable-error`
而且**沒有檢查點**；此後每一個動作都被 `EDITOR_NOT_READY` 立刻拒絕，
而 harness 繼續一格一格驅動下去，**每一格燒掉自己的逾時**。
牆上的時間看起來像 hang，實際上**沒有任何東西在等引擎**。

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

- **第一個失敗是什麼。**`latency` 只留下最後一筆（儲存 失敗），而在 `recoverable-error`
  裡連存檔都被拒，所以那一筆本身可能已經是**後果**不是**原因**。
- **為什麼沒有檢查點。**`_checkpointBeforeSelection` 應該在選取手勢前寫一個。
  `checkpoint: 無` 代表它沒寫成或寫失敗了，兩者後果不同。
- **是不是 calloc 之後才這樣。**這一輪跑的是 `a11y-calloc`。v5 上的停住是同一個形狀
  但沒有人抓過現場，所以**不能說 calloc 沒有改善它、也不能說有**。
- **和 v5 被退回的另外兩個紅的關係。**「粗體沒到文件」在這一輪的前 132 秒是**通過的**
  （`a-format-that-worked-is-not-reported-as-failed`、`bold-can-be-turned-off-again`），
  但那是在 session 死掉之前。

## 處方（未做）

1. **harness 側，便宜且立刻有用**：`finish()` 之前每一格檢查先問 session 狀態，
   一旦是 `recoverable-error` 就**停止驅動並把報告寫出來**，把整格標成
   `NOT_ESTABLISHED` 並指名「session 在第 N 格死掉」。
   現在的行為是丟掉整輪 20–50 分鐘**而且不留報告**——報告只在最後才寫。
   這一條和 finding 080 同源：**一個永遠不會成立的前提被一格一格重試**。
2. **產品側**：沒有檢查點時進入 `recoverable-error`，使用者被告知「內容不會回來」。
   在 a11y core 上這條路顯然走得到，值得單獨查。

## 證據

- `findings/evidence/f076-calloc-on-the-core-that-showed-it/a11y-stall-live-page-state.json`
- `findings/evidence/f076-calloc-on-the-core-that-showed-it/a11y-stall-step-trace.txt`
