# 182 — 從段落中間跨段選取再按標題：文件其實改了，session 卻要求重新開啟，未存的內容回不來

| | |
|---|---|
| **狀態** | 已修，等擁有者手測：e2-editor-v32（`specs/SPEC-P-demo-batch-4.md` 第 5 節）；宿主 0.2.52 已裝，P4 的 T6 與 `H4/finding-182-both-paragraphs`、`H4/range-keeps-the-session` 都過。出貨中的 0.2.45 仍帶這個缺陷 |
| **Bugzilla** | 不適用 |
| **發現日** | 2026-11-03（N3 看到 HTML 第一塊沒有段落樣式，出貨頁面重現） |
| **嚴重度** | **高**：很普通的操作，結果是 `recoverable-error`、不能存檔、提示「自上次儲存以來的內容不會回來」 |
| **可重現** | 出貨頁面 2/2（Chrome、Firefox） |
| **是否上游** | 否（我方讀法的盲點） |

## 現象

游標放在第一段中間，Shift＋↓ 選到第二段，按「標題」。頁面：`EDITOR_FORMAT_POSTCONDITION_FAILED`，狀態 `recoverable-error`，通知列「引擎需要重新開啟。沒有檢查點，所以自上次儲存以來的內容不會回來」。`evidence/demo-batch-4/before-v31/run-01/`。

內文按鈕走同一條路。清單不受影響：清單標籤在跨段讀回裡看得到。

## 分析

跨段路線讀的是選取的 HTML，`everyBlockHasTag` 要求每一塊都是目標標籤。選取從段落中間開始時，第一個節點是部分拷貝，不帶段落樣式，讀回是 `<p>…</p><h1>…</h1>`（N3 `native-toggle/range`）。樣式其實兩段都套上了，後置條件判失敗，處置是 `dispatched-rollback`。

這不是 v31 才有：跨段路線的判讀從 E2-B 起就是這樣，名義出貨版 0.2.45 帶著。

## 修法

v32 改讀文件本身（`src/writer_caret_bridge.cpp`），每段讀到的是整段的狀態，判準 T6。

## 暫時的避法

連結之前：跨段選取要從段落開頭開始，或先存檔。
