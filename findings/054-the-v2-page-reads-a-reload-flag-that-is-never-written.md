# 054 — 產品頁讀一個永遠不存在的欄位，於是「重新開啟」在它必須停用的時候仍然可按

| | |
|---|---|
| **狀態** | **已修（殼層 v9 `eb76c5be…`，2026-08-16）／有一格通則檢查，突變驗證過／端到端重現未做** |
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

## 修法（2026-08-16，殼層 v8 → v9）

改成 v1 元件那一行的形狀——**兩個條件都看**：

```js
el.noticeAction.disabled =
  snapshot.error?.code === "WORKER_GENERATION_LIMIT"
  || snapshot.error?.details?.requiresPageReload === true;
```

**而檢查寫成通則，不是寫成這一個欄位**
（`editor-shell-v2/tests/product-page-calls.test.mjs`）：

> **頁面讀的每一個 `snapshot.<欄位>`，都必須是狀態機真的會發布的欄位。**

那正是這張單子的一般形——「原始碼裡出現一個名字」不等於「有人會寫它」——而且它
與同一個檔案既有的那格（頁面呼叫的每個方法都要存在於類別上）是同一種便宜的通則。
四個產品頁一起檢查。**把修法還原，那一格會紅**（實測 5 → 4 pass、1 fail）。

寫檢查的時候自己踩到一次值得記的：**第一版把註解裡的
`snapshot.requiresPageReload` 也當成讀取**——而那句註解正是在解釋這個缺陷。
所以掃描前要先去掉行註解。

## 還缺什麼

- [ ] 端到端重現：連續耗掉三代 Worker，看那顆按鈕是不是真的變成不可按。
      （靜態上已經對得起來，但沒有人跑過那條路。）
