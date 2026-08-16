# 050 — 一個 session 裡只能打一次中文：第二次之後的 IME commit 全部被當成緩衝區不一致丟掉

| | |
|---|---|
| **狀態** | **已修**（2026-08-16，同日；單元層重現＋突變驗證） |
| **Bugzilla** | —（**不是上游**，是我方輸入介面卡的缺陷） |
| **發現日** | 2026-08-16 |
| **嚴重度** | **阻斷**（中文輸入在一個 session 裡只能用一次） |
| **可重現** | 100%（人工輪三次、單元測試三次） |
| **是否上游** | **否**——`input/input-adapter.js` |

## 現象

用新酷音在產品頁面輸入中文：**第一次成功，之後每一次都沒有反應。**
文件不變、修訂號不動、畫面沒有任何錯誤。

operator 回報的說法是「可以輸入中文，但選取後再輸入，沒有取代被選取的文字」——
**取代沒有壞**，壞的是「第二次」。第二次剛好就是那個要取代選取的動作。

## 重現步驟

1. 開產品頁面，在文件上點一下
2. 用 Fcitx5 新酷音輸入一次中文並確定 → **成功**
3. 再輸入一次（在哪裡、有沒有選取都一樣）→ **什麼都沒發生**

**預期**：每一次確定都把字送進文件
**實際**：只有第一次進得去；修訂號在三次 commit 之後只前進 1

## 證據

- `findings/evidence/sdk-e2/e2-c-validation/d5/operator/round-5-firefox/` ——
  三次真人 commit（`你好`／`取代`／`取代二`），**全部 `isTrusted: true`**，
  修訂號 `0 → 1`，存出來的文件裡只有 `E1-LC-BETWEEN你好`
- 前幾輪同樣的形狀：round 3 四次 commit → 修訂號前進一次
- `input/tests/input-adapter.test.mjs` —— 單元層重現，**拿掉修法會紅**

## 分析

根因在 `input/input-adapter.js` 的 `handleCompositionEnd()`：

```js
const sinkText = typeof this._target?.value === "string" ? this._target.value : "";
…
if (sinkText && sinkText !== text) {
  … INPUT_COMPOSITION_MISMATCH …   // 拒絕，零變更
}
```

這個比對是防呆用的：`compositionend` 帶的字要和宿主緩衝區（那個隱藏的
`<textarea id="sink">`）一致，不然表示 IME 與頁面失去同步。

**但全樹沒有任何地方清空那個 textarea**（`grep` 只有這一處讀它，零處寫它）。而
`beforeinput` 的 `insertCompositionText` 在組字期間**是不可取消的**，所以 IME
確定之後那串字會留在 textarea 裡。於是：

| 第幾次 | sink 內容 | commit 的字 | 結果 |
|---|---|---|---|
| 1 | `""` | `你好` | 通過（`sinkText` 是空字串，短路） |
| 2 | `你好` | `取代` | **不一致 → 拒絕** |
| 3 | `你好取代` | `取代二` | **不一致 → 拒絕** |

單元層完全重現（`commits that reached the session: ['你好']`）。

**而且拒絕是隱形的**：`EditorSession` 收 `onInputTrace`，`web/e2-editor-app.js`
沒有接。這一層是唯一會發生這件事、又剛好沒有人記錄的一層。

## 為什麼一直沒被抓到

和 [finding 049](049-the-product-save-button-writes-fifteen-bytes-of-object-object.md)
同一個形狀：**所有自動化輪次都直接呼叫 `session.commitText()`**，
從來沒有一輪走過 adapter 的 composition 路徑。它要一個人、用真的輸入法、
**打第二次**才會出現。

## 修法

```js
if (this._target && typeof this._target.value === "string") {
  this._target.value = "";
  this._trace(event, "sink-cleared", { compositionId });
}
```

**只在成功路徑上清**：真正的組字期不一致仍然會被擋下來——這一點有獨立的測試釘住
（`clearing the sink does NOT disarm the mismatch guard`），因為「修法把檢查改成
裝飾」是這棵樹反覆記過的失敗形狀。

**驗證**：三次 commit 全部送達（單元）；拿掉修法那條測試會紅（突變驗證）。

## 綁定的後果

`input/input-adapter.js` 同時被 E1-C 與 E2-C 的殼層 bundle 綁著：

- **E2-C**：照 E2-C 的慣例開新一代 —— **v5 = `7aed72ef…`**（v4 `85795b80…` 凍結）。
- **E1-C**：manifest 不改寫，**申報 divergence**（`e1/editor-shell-bundle-v1-divergence.json`）。
  E1-C 的殼層綁定本來就已經因 048 斷開，這一項併入同一次收復，不是新的成本。

## 同日一併修掉的兩件（都是這一輪人工輪逼出來的）

**一、Ctrl+C 從來沒有複製到文件的選取。** adapter 綁的是 composition／beforeinput／
paste，**沒有 `copy`**；而殼層一直有 `copySelection()`（它會去問引擎要選取的文字），
產品從來沒呼叫過（`grep` 零筆）。文件是畫布，所以瀏覽器的預設複製沒有 DOM 選取可以
拿——四輪剪貼簿格裡唯一貼得出東西的那一輪，是 operator 早先從別的程式複製過東西。

已接上 `copy` → `session.copySelection()`。**驗到哪裡要說清楚**：處理器會觸發、
而且會回報有型別的錯（沒有選取時現在說 `CLIPBOARD_EMPTY_SELECTION`，以前完全沉默）；
**真正的剪貼簿寫入 headless 驗不了**（WebDriver 擋掉 clipboard 讀寫，`NotAllowedError`），
那一半由人工輪確立——而那正是 D5 存在的理由。

**二、adapter 的 trace 產品沒有接。** `EditorSession` 收 `onInputTrace` 與
`onClipboardTrace`，產品兩個都沒給。**050 之所以能存在這麼久，就是因為它們哪裡都沒去。**
已接上，且**只有失敗才彈提示**（每次按鍵都彈提示是另一個缺陷）。

## 順帶修掉一個建置缺口

`make e2-c-assets` **沒有負責 `dist/input/input-adapter.js`**——E2-C 綁著那個檔，
卻不更新它在 `dist/` 的副本（serve.py 服務的是 `dist/`）。bundle 工具因此拒絕凍結
v5，而那個拒絕是對的。已把兩個 input 模組加進 `e2-c-assets` 的相依。
