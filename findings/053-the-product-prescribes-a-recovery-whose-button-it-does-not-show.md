# 053 — 產品叫使用者「回到檢查點」，而那顆按鈕在那個狀態下不會出現

| | |
|---|---|
| **狀態** | **已確認（讀原始碼＋已記錄的錯誤實例）／產品頁端到端重現未做** |
| **Bugzilla** | —（我方產品層，不是 core） |
| **發現日** | 2026-08-16（產品路徑覆蓋率清單把 `listener:click#notice-action` 標 HIGH 之後，第一次去驅動它） |
| **嚴重度** | **嚴重**——處置欄位是 SPEC E2-B 5.13 規定 host 必須遵守的，而 host 在這一類錯誤上遵守不了 |
| **可重現** | 錯誤本身 100%（D2 presweep 兩瀏覽器已記錄）；「使用者看到處方卻沒有按鈕」尚未端到端重現 |
| **是否上游** | **否**——是我們的產品頁與殼層狀態機之間的縫 |

## 現象

格式動作失敗、而 barrier 說**已經派送出去**的時候，產品會 toast：

```
…（可能已經改到文件：請回到檢查點）
```

**但那個「回到檢查點」按鈕不會顯示。** 它在 `#notice` 裡，而 `#notice` 只在
session 狀態是 `recoverable-error` 或 `restart-required` 時才顯示；
`EDITOR_FORMAT_POSTCONDITION_FAILED` 兩者都不是，session 留在 `ready`。

使用者被告知文件**可能已經被改到而且無法驗證**，然後沒有被給任何回去的路。

## 重現步驟——**這是路線，不是已經跑過的紀錄**

對抗性審查（2026-08-16）指出前一版把這一段寫成好像實測過。**沒有。**
底下三步是**要去跑的**，兩個已經量到的半邊在「證據」那一節。

1. 開產品頁 `e2-editor.html`，選 `empty-paragraph` 語料。
2. 把游標放到那份語料的**空段落**上。
3. 按「項目符號」。

**預期**：要嘛動作成功，要嘛失敗並且**提供**它自己開的處方。
**推論出來的實際**（來自原始碼與兩個已量到的半邊，**不是**跑這三步得到的）：
toast 說「請回到檢查點」，而 `#notice` 的 `data-show` 會是 `0`，按鈕不顯示。

## 證據

### 一、這個錯誤在出貨的 artifact 上確實會發生，而且處方就是 rollback

`findings/evidence/sdk-e2/e2-c-validation/d2-presweep/e2-editor-v2-572035ac/firefox/result.json`，
格 `d2-refused-no-mutation-engine`（Chrome 那一份相同）：

```json
{"code": "EDITOR_FORMAT_POSTCONDITION_FAILED",
 "message": "the document does not show the state this action asked for",
 "recovery": "rollback",
 "disposition": "dispatched-rollback",
 "formatBarrier": {"failureShape": "postcondition-not-met", "dispatched": true}}
```

### 二、`ready` 狀態下按鈕不顯示、而且按不動——2026-08-16 在產品頁量到的

`tools/run_e2_c_product_path.py` 的第一版 rollback 檢查從 `ready` 按下去，得到：

```
回到檢查點：editor cannot restart from ready
```

那一次是**檢查寫錯**（產品在那個狀態下本來就沒有提供這顆按鈕），但它把
`restart()` 的前置條件量了出來。

## 分析

四段程式碼，兩個集合對不上。

**處方是怎麼開出來的**——`editor-shell-v2/paragraph-editor-session.js`
`recoveryFor()`：barrier 說 `dispatched: true` → disposition `dispatched-rollback`
→ 回傳 `"rollback"`。沒有 barrier 欄位時回傳 `"unknown-rollback"`，也是 rollback，
而且註解寫明是刻意 fail closed。

**產品怎麼把處方講給使用者**——`web/e2-editor-app.js`：

```js
(recovery === "rollback" ? "（可能已經改到文件：請回到檢查點）" : …)
```

**按鈕什麼時候出現**——同一個檔案：

```js
const recoverable = ["recoverable-error", "restart-required"]
  .includes(snapshot.state);
el.notice.dataset.show = recoverable ? "1" : "0";
```

**狀態什麼時候會變成那兩個**——`editor-shell/editor-session.js` 的佇列 drain：

```js
} else if (error?.code === "EDITOR_BOUNDARY_UNSUPPORTED") {
  this._blockQueue(error, "restart-required", "editor-boundary");
} else if (RECOVERY_ERRORS.has(error?.code)) {
  this._blockQueue(error, "recoverable-error", "editor-recovery");
}
```

而 `RECOVERY_ERRORS` 是 `TIMEOUT`、`WORKER_CRASHED`、`WORKER_RESTARTED`、
`STALE_DOCUMENT`、`MUTATION_OUTCOME_UNKNOWN`、`EDITOR_RESULT_INVALID`。

**`EDITOR_FORMAT_POSTCONDITION_FAILED` 不在裡面。** 所以：處方開了、話講了、
狀態沒有變、按鈕沒有出現。

**兩個集合的判準不一樣，而它們應該一樣**：一個問「引擎還能不能用」，另一個問
「文件可能已經被改到了嗎」。**回到檢查點是為了後者存在的**——SPEC E2-B 5.13 的
用語就是 dispatched failure。

### 哪一邊該改：**規格早就決定了**（2026-08-16 外部裁決，我逐條核對屬實）

我原本把這寫成一個開放的取捨，還傾向改頁面那一邊。**那是錯的**，而且錯在沒有回去
讀契約。SPEC E2-B 5.13 第三條寫著：

> **三、B 的處置是 rollback，不是 undo。** host 進 `recoverable-error`，
> 從**上一個 checkpoint bytes**（沒有就 authority bytes）重開。

規格要求的不只是「處方是 rollback」，是**進 `recoverable-error`**。所以：

- **`#notice` 的顯示條件（看 session 狀態）是對的**，改它等於把對的那一邊接到壞的
  那一邊去。
- **這是殼層的規格不符，不是產品頁的缺陷。**
- 而且 5.13 第二條把「B 會擋 queue」當成明文前提（「擋了 queue 就沒有『下一個
  mutation』」），所以「留在 `ready` 讓使用者重試」不是另一種合理語意——**它正是
  5.13 要防的那個疊加**：在一個沒被驗證的變更上面再疊一個。

**我另一個被推翻的前提**：以為修 `RECOVERY_ERRORS` 一定要動
`editor-shell/editor-session.js`（E1-C 雜湊綁定，動了就解除 `E1_GO_ODT_EDITOR`）。
**不必。** 逐項核對過：

| | |
|---|---|
| E1-C 的 bundle（v2） | **5 個檔案，沒有一個在 `editor-shell-v2/`** |
| E2-C 的殼層 bundle（v8） | 12 個檔案，**四個 `editor-shell-v2/` 檔案與 `web/e2-editor-app.js` 都在裡面** |

所以修在 `NarrowEditorV2Session.action()` 的 catch 裡——算出 `recoveryFor(error)`，
是 `"rollback"` 就在重新丟出之前呼叫 `this._blockQueue(error,
"recoverable-error", "editor-recovery")`——**不會動到 E1-C 綁的任何一個位元組**。
那也是這棵樹自己的既有做法：`paragraph-editor-session.js` 開頭就寫著
`editor-shell-v2/` 存在的理由**正是**「在 `editor-shell/` 加東西會解除已出貨的判定」。

**還是有代價，而且要說清楚**：`editor-shell-v2/` 在 **E2-C 殼層 bundle 裡**，
所以這個修法會把 E2 殼層從 **v8 推到 v9**，今天的 D5 第七輪就綁在 v8 上——
**與今早 E1-C 那次同一個形狀**，處方也一樣（重新綁定，不是繼續申報）。
兩條候選路線在這一點上代價相同，所以它不構成選擇的理由。

### 仍然不確定的部分

- **`unknown-rollback` 那一路更常見還是更少見，沒有量過。**
- **`unknown-rollback` 那一路更常見還是更少見，沒有量過。**
- **端到端重現還沒做。** 路線是清楚的：在產品頁上把游標放到一個空段落再按項目
  符號（finding 046 的那一格）。用點擊座標去找空段落需要文件的 twips，而頁面沒有
  對外露出；比較穩的走法是先點在一行文字的最右邊（會夾到行尾，已量），按
  `insert-paragraph-break` 造出一個空段落，再按項目符號。

## 為什麼到今天才看到

`e2/product-path-coverage.json` 2026-08-16 把 `listener:click#notice-action`
標成 **HIGH／從來沒有被驅動過**，理由寫的是：

> 這是**產品的復原路徑**（`session.rollback()`）……而沒有任何一輪按過它。
> 一條從來沒被走過的復原路徑，就是一條沒有人知道會不會動的復原路徑。

第一次去按它，就掉出這個。**清單預測對了。**

## 還缺什麼

- [ ] 產品頁端到端重現（上面那條路線）
- [x] ~~決定要改哪一邊~~ —— **決定了：改殼層，在 `NarrowEditorV2Session.action()`
      的 catch 擋 queue**（規格已決定，見上）。**尚未執行**：它把 E2 殼層推到 v9，
      而今天的 D5 第七輪綁在 v8，所以那是一次有計畫的動作，不是順手改。
- [ ] 修好之後，`run_e2_c_product_path.py` 要有一格會紅的檢查
