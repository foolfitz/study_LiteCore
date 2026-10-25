# 152 — Chrome 裡，Markdown 對話框關閉之後，鍵盤打的字不會進到文件

| | |
|---|---|
| **狀態** | **修法 3 已隨 v22 落地，F3 機械判準與擁有者 F3-hand 均成立**（0.2.33，2026-10-25）；Xvfb 原生 X11 鍵盤診斷亦 3／3。這個問題的修復驗收已完成；宿主仍為未計數候選，K 尚未執行 |
| **影響版本** | 只有 v21 未計數候選（頁面 `3d511216…`）。0.2.24 沒有 `<dialog>`（`diag-dirty-move/` V11f）。v21 依規格 §12.3 (e) 不提供對話框入口，所以出貨版**到不了** |
| **所在** | 頁面 `web/e2-editor-app.js` `closeMarkdownDialog`（約 `:2337-2344`）：同一個 task 裡先 `dialog.close()`，再 `sink.focus()` |
| **發現日** | 2026-10-17：item 1 smoke 的 D6（Z 不見了）→ `findings/evidence/link-batch-v21/shakedown/diag-dirty-move/` V5、V11、V11g |
| **嚴重度** | 用過對話框（按「插入」或「取消」都算）之後，鍵盤打字完全沒反應。貼上（Ctrl+V）仍然有效。只有 Chrome |
| **是否上游** | 未定（可能是 Chrome 在 modal `<dialog>` 關閉後的焦點交接）；修法在我們這邊 |

## 現象（量測）

- **headless Chrome**：真鍵到得了輸入框，而且輸入框在焦點上、沒停用、不在 inert 裡，`document.hasFocus()` 為 true，事件也沒被 preventDefault。但瀏覽器**不產生** `beforeinput`，也沒有 `insertText`。
  - V5（插入後 0／300 ms 再打）9/9；V11c（只按取消）3/3；V11d（被拒絕後取消）3/3。
  - 稍晚（約 1.6 秒）再打、或點一下文件再打，都一樣。
- **有視窗的 Chrome**（擁有者桌面上的 Xwayland，螢幕鎖著）：V5 3/3、V11c 3/3 都打不進去；不經過對話框的對照組 1/1 正常。
- **Firefox**：12 輪都正常。
- **救得回來的方法**：Ctrl+V 貼上與 CDP `Input.insertText` 都進得去；從外部對輸入框先 `blur()` 再 `focus()`，之後打字就正常。

## 候選修法（修法 3，只在 mirror 量過）

`closeMarkdownDialog` 裡把 `el.sink.focus(...)` 改成 `el.sink.blur(); el.sink.focus(...)`：

- headless Chrome：V5 3/3、V11c 3/3；
- 有視窗的 Chrome：V5 1/1；
- Firefox（不退化的對照）：V5 1/1。

另一個候選（修法 3b：用 `requestAnimationFrame` 延後 focus）沒有跑，因為修法 3 已經有效。

## 還沒證明的

- 輸入都是 CDP 的鍵盤事件，不是作業系統的真鍵盤。
- 有視窗的那次，視窗在鎖住的螢幕後面。
- 真的 Chrome 手測可以把這兩點補上。

## 裁決（fable 裁決 1，2026-10-17，擁有者授權；原文 `findings/evidence/link-batch-v21/shakedown/review/ruling-fable-1.md` Q3）

**選 C：登錄，v21 不改頁面。**

白話理由（fable 寫給擁有者）：修法 3 的數字很好（headless 6/6、有視窗 1/1、Firefox 1/1），但第 2 項這批不出貨，對話框在 v21 根本開不到，改了也量不到好處。而 `sink.blur()` 對頁面其他和 blur 有關的路徑有沒有副作用，沒有量過，不該把一個沒人能量的改動帶進要凍結的殼層。它跟著第 2 項一起出，到時候由擁有者親手在真的 Chrome 打一次字，當最後一關。

**出第 2 項那一批的判準（現在就寫下）**：

1. V5（關閉後 0 ms、300 ms 再打）與 V11c／V11d，N=3、兩個瀏覽器，打的字都要進到文件。
2. 擁有者在真的 Chrome 手測：按「插入」之後、按「取消」之後各打一次字。
3. 若沒做：不提供入口。

## 2026-10-25：補登錄 v22 的修法與 Xvfb 原生鍵盤診斷

修法 3 已於 v22 的頁面 `3b96cb16…` 落地；`SPEC-M3-link-batch-v22.md` §11.3.1 與 `findings/evidence/link-batch-v22/shell/f3/` 記錄 F3 八格（V5@0／300 ms、V11c、V11d，兩個瀏覽器）各 3／3。前文「候選、只在 mirror」是 10-17 的歷史狀態。

擁有者睡前指示可試 xvfb 後，於 host **0.2.33／a67beefefebe57d6** 的真實 Files 路徑上，以**有視窗的 Chrome**、獨立 Xvfb display／profile，透過 **XTestFakeKeyEvent** 送 X11 原生鍵盤事件。三回皆為：Markdown 插入後焦點回到 sink、打入的標記在存回 ODT 裡；再開框輸入另一標記、取消後焦點回 sink、接著打的標記也在存回 ODT 裡；被取消的框內文字不在存檔。事件皆為 trusted，對話框插入的文字也已存回，GET 200。證據 `findings/evidence/host-0.2.33/count-preparation-2026-10-25/xvfb-focus/`。

這補上了前段「還沒證明」裡**Xvfb／X11 原生鍵盤路徑**的機器證據，不是擁有者實際桌面／IME 的親手回報。既有 F3-hand 仍未收到；不以診斷自動滿足該人工條件。沒有更動產品、共用啟動器或 F3 判準。

## 同日擁有者 F3-hand 成立

擁有者在準備好的實際 Chrome／Files 手測流程後，先回「測試完成」，再對明列四項驗收結果的選項回「A」（A＝「四項都符合預期」）。其中前兩項正是插入後打 A、取消後打 B，兩者均出現在文件。**F3-hand 成立**，取代前段的待回報狀態；證據 `findings/evidence/host-0.2.33/f3-hand-2026-10-25/owner-confirmation.md`。這是獨立的人的回報，沒有拿 Xvfb 代答。F3 的機械與人工兩半皆成立，host 0.2.33 仍須另行完成 K 計數。
