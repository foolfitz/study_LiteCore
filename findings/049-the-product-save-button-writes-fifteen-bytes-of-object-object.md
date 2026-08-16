# 049 — 產品的「儲存 ODT」寫出 15 個位元組的 `[object Object]`

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | —（**不是上游**，是我方產品頁面的缺陷） |
| **發現日** | 2026-08-16 |
| **嚴重度** | **阻斷**（對產品而言：存檔功能等於不存在；對 E2-C 而言：D5 的凍結判準無法達成） |
| **可重現** | 100%（兩個瀏覽器、機器與人工各一次） |
| **是否上游** | **否**——`web/e2-editor-app.js` 的一行 |

## 現象

在產品頁面按「儲存 ODT」，瀏覽器下載一個檔名正確、**大小 15 位元組**的
`.odt`，內容是字串 `[object Object]`。產品自己的提示列同時顯示
**`已存出 NaN KB`**。

沒有任何錯誤：狀態列維持 `ready`，延遲顯示「儲存 211 ms」，一切看起來成功。

## 重現步驟

1. 開啟產品頁面（`e2-editor.html`，profile `e2-editor-v2`），等狀態變 `ready`
2. 按工具列的「儲存 ODT」
3. 看下載的檔案

**預期**：一份可以用桌面版 LibreOffice 開啟的 ODT（本語料約 12–18 KB）
**實際**：15 位元組，`[object Object]`；提示列寫「已存出 NaN KB」

## 證據

- `evidence/049/product-save-output.odt` —— **operator 在 2026-08-16 的 D5 人工輪
  下載到的檔案**，15 位元組
- `evidence/049/measurement.json` —— 在 D5 harness 裡按下產品自己的儲存鈕，
  由**已申報的** `URL.createObjectURL` shim 攔到的東西

```
capturedBytes: 15
capturedContent: "[object Object]"
productToast: "已存出 NaN KB"
```

## 分析

根因是一行，而且旁邊就有寫對的版本。

`EditorSession.save()` 回傳的是**一個物件**：

```js
// editor-shell/editor-session.js:507-513
save(options = {}) {
  return this._enqueue("save", async ({ document }) => {
    const bytes = await document.save({ format: "odt" }, { … });
    return { bytes, revision: document.revision, contentStamp: … };
  }, …);
}
```

而產品頁面把整個結果當成位元組：

```js
// web/e2-editor-app.js:215-217
const bytes = await run("儲存", () => session.save());
const url = URL.createObjectURL(
  new Blob([bytes], { type: "application/vnd.oasis.opendocument.text" }));
```

`new Blob([物件])` 會把物件字串化成 `"[object Object]"`——15 個位元組。
同一行之後的 `bytes.byteLength` 是 `undefined`，所以提示列顯示 `NaN`。

**對照組就在隔壁檔案**：`web/demo-editor-app.js:626-627` 取的是 `saved.bytes`，
是對的。所以這是一個手誤，不是對契約的誤解。

## 為什麼一直沒被抓到（這一條比缺陷本身重要）

**每一個自動化 harness 都自己呼叫 `session.save()` 並解構 `{ bytes }`**——
`e2-c-d4-app.js`、`e2-c-046-empty-app.js`、`e2-c-d3-*` 全部如此。也就是說，
**所有輪次驗的都是殼層的存檔，從來沒有一輪走過產品頁面那顆按鈕。**

它是被**一個人按下去**才掉出來的，而那正是 D5 這個相位存在的理由：
D5 的四格是「非人不可」的那一類，而這個缺陷證明了「非人不可」不只是關於
`isTrusted`。

## 影響

- **產品**：存檔功能等於不存在。使用者拿到的是一個會讓 LibreOffice 開不起來的檔案。
- **E2-C D5**：凍結矩陣對兩格拖曳的 oracle 寫的是「**而且存出來的 ODT 看得到**」。
  存檔壞著就**無法達成**——D5 在修好之前不可能拿到 PASS。
- **不影響既有判定**：所有已記錄的證據都是 harness 自己存的，位元組是好的。

## 下一步

1. **修**：`web/e2-editor-app.js` 改成 `const { bytes } = await run(…)`，
   或 `saveDocument()` 取 `result.bytes`。**不需要 relink**（是 JS，不是 wasm）。
2. **但它會動到殼層 bundle 的摘要**——`web/e2-editor-app.js` 是 E2-C 殼層 bundle
   綁的十二個模組之一，而 E2-C 第一輪的判定綁著那個摘要。處置照 E1-C 的前例：
   **申報 divergence，不就地改寫凍結的 manifest**。
3. **加一格**：矩陣 v2 要有一格**走產品頁面自己的存檔按鈕**並檢查位元組是 ZIP。
   這一輪學到的是：harness 走的路和使用者走的路不同時，只有使用者那條會出事。
4. 修好之後 D5 的人工輪才有意義（**先修再排**，否則兩格必掛）。
