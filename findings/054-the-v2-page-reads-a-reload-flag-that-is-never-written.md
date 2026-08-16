# 054 — 產品頁讀一個永遠不存在的欄位，於是「重新開啟」在它必須停用的時候仍然可按

| | |
|---|---|
| **狀態** | **已確認（原始碼三處逐行核對）／未修／產品頁端到端重現未做** |
| **Bugzilla** | —（我方產品層，不是 core） |
| **發現日** | 2026-08-16（外部裁決 fable 在審 [053](053-the-product-prescribes-a-recovery-whose-button-it-does-not-show.md) 時順帶指出，我自行核對屬實） |
| **嚴重度** | **一般**——要先用掉三代 Worker 才走得到，但走到時使用者被送去一個保證拒絕他的控制項 |
| **可重現** | 未實跑；三處原始碼的關係是靜態的 |
| **是否上游** | **否**——我方產品頁 |

## 現象

到達 Worker 世代上限之後，產品頁把「重新開啟」這顆按鈕**顯示成可按**。按下去
會再次走 `restart()` → `_openFresh()`，再次丟 `WORKER_GENERATION_LIMIT`。

**使用者被送去一個保證拒絕他的控制項。** 而這句話正是殼層自己的註解寫的
（`editor-shell/recovery-notice.js:35-37`：「A host that still points at its
restart button here is sending the user to a control that will refuse them.」）。

## 分析：一個欄位，兩個層級

**寫的那一邊**（`editor-shell/editor-session.js:150-156`）把旗標放在 error 的
`details` 裡：

```js
error.code = "WORKER_GENERATION_LIMIT";
error.details = {
  generation: this._generation,
  maximumWorkerGenerations: this._maxWorkerGenerations,
  requiresPageReload: true,
};
```

**v1 的元件讀對了**（`editor-shell/recovery-notice.js:38-39`）：

```js
const exhausted = snapshot.error?.code === "WORKER_GENERATION_LIMIT"
  || snapshot.error?.details?.requiresPageReload === true;
```

**v2 的產品頁讀錯了**（`web/e2-editor-app.js:100`）：

```js
el.noticeAction.disabled = snapshot.requiresPageReload === true;
```

`snapshot` 上**沒有**頂層的 `requiresPageReload`——全樹只有上面三處提到這個名字，
寫入的那一處在 `error.details` 底下。所以那個比較永遠是 `false`，按鈕永遠不停用。

## 與 053 同一個家族

[053](053-the-product-prescribes-a-recovery-whose-button-it-does-not-show.md) 是
「產品開了一個它自己不提供的處方」；這一個是「產品提供了一顆它知道會失敗的按鈕」。
兩個都在**復原路徑**上，兩個都是**沒有人按過**的後果——
`e2/product-path-coverage.json` 把 `listener:click#notice-action` 標 HIGH 的理由
一字未改地適用於這一條。

## 還缺什麼

- [ ] 端到端重現：連續耗掉三代 Worker，看那顆按鈕是不是可按。
- [ ] 修法：讀 `snapshot.error?.details?.requiresPageReload`，或直接沿用 v1 元件
      那一行（它同時看 `error.code`，比單看旗標更穩）。
- [ ] **修好之後要有一格會紅的檢查**——與 053 同一個要求。
