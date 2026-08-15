# 047 — 存檔之後馬上點一下再按格式鈕，barrier 永遠等不到選取回呼

| | |
|---|---|
| **狀態** | **已確認（兩瀏覽器、四組對照）／機制未定／未修** |
| **Bugzilla** | —（尚未判定是否上游） |
| **發現日** | 2026-08-15（E2-C D3 清單目標格第一次執行） |
| **嚴重度** | **嚴重**——「存檔 → 點一下 → 按項目符號」是最普通的操作順序，而後果是 `MUTATION_OUTCOME_UNKNOWN` ＋ host 回滾 |
| **可重現** | 100%（Chrome／Firefox 各一輪，出貨 profile `e2-editor-v2`） |
| **是否上游** | **未判定** |

## 摘要

在**同一個 session** 裡做這三件事，中間不停：

```text
session.save()            → 244 ms 完成
session.placeCaret(x, y)  → 引擎確認收合游標（selectionType none、collapsed、observed）
session.action("set-list-unordered")
```

barrier 派送出去，然後**永遠等不到選取回呼**，5 秒後以
`stage-deadline:awaiting-selection` 收場：

```json
{"code": "MUTATION_OUTCOME_UNKNOWN",
 "failureShape": "stage-deadline:awaiting-selection",
 "dispatched": true, "preBlocks": 0, "postBlocks": 0}
```

處置是 `dispatched-rollback`，所以 host 會**從 checkpoint 重開、丟掉自那之後的
編輯**——而使用者只是存了個檔、點了一下、按了項目符號。

## 四組對照（Chrome 與 Firefox 逐項相同）

| 動作之前 | 游標確認後等待 | 結果 |
|---|---|---|
| **`save()`** | 0 | **`stage-deadline:awaiting-selection`** |
| 只等 1500 ms（不存檔） | 0 | `verified-format-readback` ✅ |
| **`save()`** | **2000 ms** | `verified-format-readback` ✅ |
| 什麼都不做 | 0 | `verified-format-readback` ✅ |

**排除的解釋：**

| 假說 | 結果 |
|---|---|
| 「動作之前只要花時間就會壞」 | **排除**——只等 1500 ms 會過 |
| 「這一格本來就不會過」 | **排除**——什麼都不做會過 |
| 「瀏覽器差異」 | **排除**——兩瀏覽器逐項相同 |
| 「錨點或語料的問題」 | **排除**——同一格、同一份文件、同一顆 artifact，只換前置動作 |

**所以是存檔特有的，而且是短暫的**：游標確認之後再等 2 秒就好了。

## 最要緊的那一點：`placeCaret` 的確認**不足以**保證下一個動作會成功

產品的 `placeCaret` 會輪詢到引擎回報
`selectionType === "none" && collapsed === true && observed === true` 才返回。
**那個條件在這個情形下會成立，而下一個格式動作仍然會逾時。**

也就是說：**產品目前用來判斷「游標好了」的訊號，並不保證 barrier 的
`.uno:SelectText` 會拿到回呼。**

## 機制：未定

形狀與 [043](043-fn-select-para-leaves-the-shell-in-selection-mode-and-the-next-lok-range-selection-is-silently-dropped.md)
／049 同族——「殼層停在選取模式，下一次選取被無聲丟掉」——但**還沒有證據**說
就是同一個 `m_bInSelect`。已知的是：

- 派送**確實發生**（`dispatched: true`），卡的是它之後的等待；
- 在派送**之前**多等 2 秒就好，但派送**之後**等 5 秒（stage deadline）沒有用
  ——**所以不是「回呼會晚到」，是「回呼不會來」**；
- 存檔本身 215–244 ms 就完成了，所以不是存檔還沒結束。

## 影響

- **產品頁面走的就是這條路**（`web/e2-editor-app.js`：儲存鈕、canvas 點擊放游標、
  工具列格式鈕）。
- **E2-C D3 的八格第一次跑全部因此失敗**——那是這個 finding 的發現方式。
- 對契約的意思：**`MUTATION_OUTCOME_UNKNOWN` 在這裡是誠實的**（引擎確實不知道），
  但它是由一個**沒有任何東西出錯**的操作順序觸發的。

## 還缺什麼

- [ ] **機制**：native 重現，或在 WASM 上抓 `m_bInSelect`／選取回呼的軌跡。
      在那之前不要寫成 043 的實例。
- [ ] **等多久才夠**：2000 ms 會過、0 ms 會壞，中間沒量過。
      產品若要用「等一下」當處置，那個數字必須是量出來的，不是猜的。
- [ ] **是不是只有 save**：其他重的操作（`undo`、`render`、`insertText`）
      是否也會留下同一個狀態，沒量過。
- [ ] 判定要不要進下一次 relink：**如果修法在引擎側，就必須進**。

## 證據

`findings/evidence/047/`（四組對照 × 兩瀏覽器）。
發現於 `findings/evidence/sdk-e2/e2-c-validation/d3-lists/` 的第一次執行。
