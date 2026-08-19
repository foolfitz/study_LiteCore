# 062 — 文件夠長的時候，編輯器給你一張空白畫布，而且什麼都不說

| | |
|---|---|
| **狀態** | **已確認／未修**——**層級未確立**（見〈分析〉），修法可能在引擎側也可能在頁面側 |
| **Bugzilla** | —（**層級未確立之前不得送出**，040／048 的前例） |
| **發現日** | 2026-08-19 |
| **嚴重度** | **嚴重**——使用者看到的是一份空白文件，而產品回報一切正常 |
| **可重現** | 100%（Chrome，dpr 1 與 dpr 2 各 1/1；畫布高度掃描 8/8 單調） |
| **是否上游** | **未確認** |

## 現象

打開一份夠長的 .odt，畫面是**全白的**。狀態列寫著「就緒」，沒有任何錯誤訊息，
沒有 toast，文件標題正確顯示。存檔存得出完整的內容——文件是好的，**只有畫面是空的**。

「夠長」不是文件的性質，是**文件乘上螢幕**的性質：

| | 畫布高度 | 畫面 |
|---|---|---|
| 20 頁 A4，dpr 1 | 19,919 px | 正常 |
| 35 頁 A4，dpr 1 | 34,847 px | **全白** |
| **同一份 20 頁**，dpr 2 | 39,839 px | **全白** |

第三列是重點：**同一份文件**，在 1× 螢幕上正常、在 2× 螢幕上空白。使用者換一台
筆電就會遇到，而文件一個位元組都沒變。

## 重現步驟

1. 用 `tools/create_long_document.py --pages 35` 產一份 35 頁的 ODT。
2. 在產品頁（`web/e2-editor.html`）用「開啟檔案」開它。
3. 看畫布。

**預期**：畫得出來，或者產品說它畫不出來。
**實際**：全白，狀態 `ready`，沒有任何訊息。

dpr 的那一列：任何 20 頁以上的文件，在 `devicePixelRatio` 2 的螢幕上重複第 2 步。

## 證據

`a-long-document-is-drawn-or-the-product-says-it-is-not`（`tools/run_e2_c_product_path.py`）：

```
one-page                            pages= 1 h= 1012 dpr=1 drawn=True  cols=694
five-pages                          pages= 5 h= 4992 dpr=1 drawn=True  cols=694
below-the-wall                      pages=20 h=19919 dpr=1 drawn=True  cols=694
above-the-wall                      pages=35 h=34847 dpr=1 drawn=False cols=1
the-same-document-on-a-2x-display   pages=20 h=39839 dpr=2 drawn=False cols=2
```

`cols` 是頂端 400 列裡有墨水的**欄數**。文字會鋪滿 694 欄；空白畫布上剩下的
1–2 欄是游標——它照畫，所以「有沒有畫東西」不能用像素總數問，第一版就是這樣被
騙過去的（56 個深色像素的游標通過了「超過 50 個像素」的判準）。

**牆在畫布高度上，量得很窄**。固定同一份文件、只掃 `devicePixelRatio`
（1.00→1.15，畫布高度連續移動）：

```
dpr=1.00 canvas=725x31048  DRAWN
dpr=1.02 canvas=739x31648  DRAWN
dpr=1.04 canvas=754x32290  DRAWN
dpr=1.05 canvas=761x32590  DRAWN
dpr=1.06 canvas=768x32889  BLANK
dpr=1.08 canvas=783x33532  BLANK
dpr=1.10 canvas=798x34174  BLANK
dpr=1.15 canvas=834x35716  BLANK
```

⇒ 牆落在 **32,590 < H ≤ 32,889**。**32,767 = 2^15 − 1 就在這個區間裡。**

**而這不是 canvas 元素自己的上限。** 同一台機器、同兩個瀏覽器，用二分法直接量
（`tools/probe_canvas_limit.py`）：

```
chrome  725/1450/2175 px 寬 -> 最高可用 65535（65536 起底部像素畫不進去）
chrome  2400 px 寬       -> 最高可用 65234
firefox 725/1450/2175/2400 -> 最高可用 65535（65536 起 NS_ERROR_FAILURE）
```

**65,535，不是 32,767。** 所以這道牆是 render 這條路上自己的 16 位元限制，
不是瀏覽器的畫布上限。

### 沉默是被量過的，不是被推測的

`renderDocument()` 有 `toast("重繪失敗：…")` 這條路（`web/e2-editor-app.js:199`），
所以第一個要排除的是「它其實說了，只是被之後的成功訊息蓋掉」——`openDocument()`
先重繪、它的呼叫端再 toast「已開啟」。裝了一個把**每一則** toast 都記下來的
MutationObserver 之後：

```
dpr=1.06 canvas=768x32889 BLANK
   開檔期間的 toasts: ['已開啟 wall-1.06.odt']
   點一下之後: state='ready' latency='定位游標 152 ms' toast=''
   點擊期間的 toasts: []
```

一則都沒有。`render()` 沒有丟例外——丟了就會有 toast——所以它**回報成功**。

### 附帶：一個變高的編輯，畫布不跟

同一格量到的第二件事，和長度無關：

```
2 頁文件開起來          canvas 725x2007
插入 3,336 個字元       canvas 725x2007   ← 沒動
存檔、把同一份位元組重開 canvas 725x3002   ← 真的變成 3 頁了
（對照）真的 3 頁的文件  canvas 725x3002
```

文件多了一頁，畫面沒有。也沒有任何訊息。原因在原始碼裡看得到：
`DocumentHandle.heightTwips` 只在 open 的 metadata 指派一次
（`sdk/document-sdk.js:374`），而 `document-invalidated` 只呼叫 `renderDocument()`
（`web/e2-editor-app.js:622`）——沒有重讀 metadata，也沒有再 `layoutCanvas()`。

## 分析

`layoutCanvas()`（`web/e2-editor-app.js:158-172`）把**整份文件**放進一張畫布：

```
backingWidth  = min(2400, round(cssWidth * devicePixelRatio))
canvas.height = round(backingWidth * heightTwips / widthTwips)
```

`heightTwips` 是整份文件的高（core：`doc_getDocumentSize` →
`SwXTextDocument::getDocumentSize`），所以畫布高度隨頁數線性成長，而且乘上
`devicePixelRatio`。`renderDocument()` 接著要求一張 `canvas.width × canvas.height`
的 tile。

**在哪一層掉了像素，本檔不指認。** 兩個候選都還站得住：

1. 引擎／LOK 回了一張空的（或短的）bitmap，而 `render()` 仍然回報成功；
2. tile 回來是對的，頁面在 `new ImageData(...)` 或 `putImageData` 這一步掉了它。

分不出來的理由是可以說清楚的：`render()` 沒有丟例外，頁面刻意不公開 session
handle，所以從產品這條路上讀不到 tile 自己回報的尺寸。**分辨的實驗也很明確**：
用 shell 直接呼叫 `document.render()`，`canvasHeightPx` 取 32,590 與 32,889 兩個值，
比對回來的 `width`／`height` 與像素位元組長度。那是下一輪的事。

**為什麼不先猜**：040 的根因花了很久才確立，048 明確寫著「只排除 core 的點擊處理、
不得指認肇因」。這一格照那個規矩走。

> **給做那個實驗的人**：確立之後，改上面的狀態欄，寫下是哪一層，並加上佇列項
> `queue-long-document-renders-blank-in-silence` 的 `checkNote` 指定的那個標記。
> 那一項盯的就是它，會跟著翻。標記寫在佇列裡而不寫在這裡，是因為**被盯的字串不能
> 出現在解釋它的句子裡**——這一段的前一版就是這樣讓那一項當場 DRIFT 的。

**這件事決定要不要 relink**，所以它不是學術問題：如果是第 1 種，修法在引擎側、
要排進被擋住的連結佇列；如果是第 2 種，殼層／頁面就能修（切成多張 tile 或分頁繪製）。

## 事前預測與實際的差距

預測寫在
`findings/evidence/sdk-e2/e2-c-validation/long-document/PREDICTION.md`，
在語料、探針、檢查都還不存在時提交（commit `7b4a38c`）。三條登記的預測：

- **預測 1（撞牆頁數隨 dpr 差 3 倍以上）**：**成立**，而且**機制猜錯了**。預測說
  牆是 canvas 元素 32,767 的尺寸上限；實測 canvas 上限是 **65,535**，而 render
  這條路自己有一道 32,767 的牆。頁數幾乎一樣，理由完全不同。
- **預測 2（幾何不更新那一道最先到、且在任何長度都到）**：**成立**。2 頁就到。
- **預測 3（延遲每頁 150–250 ms，可用性的牆落在 4–7 頁）**：**錯，而且錯兩個量級**。
  實測按鍵到看得見墨水：1 頁 59 ms、5 頁 61 ms、20 頁 127 ms——**每頁約 3.6 ms**，
  預測檔自己寫了「每頁若低於 25 ms，第 3 條就是錯的，照直說」。照直說：**延遲不是
  這裡的問題**，1,000 ms 的門檻在牆之前一次都沒有被逼近。

## 環境

```
產品：wasm_sdk_probe/dist（殼層 v17 34289a7bd8ffc3df…，artifact d538ce0b91478426…）
瀏覽器：Chrome（headless，WebDriver）／Firefox（僅畫布上限那一項）
語料：tools/create_long_document.py（A4，每頁明確分頁符，不進凍結集）
量測：tools/run_e2_c_product_path.py、tools/probe_canvas_limit.py
```

## 內部備註（不送出）

語料第一版**沒有宣告頁面版面**，LibreOffice 就給了一張長寬比 2.52 的紙，一「頁」
裝得下約 83 行——於是「加 3,336 個字元」根本沒有多出一頁，幾何那一格靜靜地量不到
東西。是那一格的 ground truth 條款（存檔、重開、比高度）把它抓出來的：它報
`groundTruthEstablished: false` 而不是通過。**一個沒有 ground truth 就拒絕給判決的
檢查，這一次救了一格。**
