# 062 — 文件夠長的時候，編輯器給你一張空白畫布，而且什麼都不說

| | |
|---|---|
| **狀態** | **已確認／未修**——**層級已確立：頁面側，不需要 relink**（LAYER-ESTABLISHED，2026-08-19，`evidence/062/layer/`） |
| **Bugzilla** | —（**我方產品缺陷，不是上游**，不送出） |
| **發現日** | 2026-08-19 |
| **嚴重度** | **嚴重**——使用者看到的是一份空白文件，而產品回報一切正常 |
| **可重現** | 100%（Chrome，dpr 1 與 dpr 2 各 1/1；畫布高度掃描 8/8 單調） |
| **是否上游** | **否**——引擎回的 tile 是對的，是頁面沒有把它畫上去 |

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

### 層級：**頁面側**（2026-08-19 量完，`evidence/062/layer/`）

本檔初版刻意不指認層級，因為那決定要不要 relink。**現在量完了，答案是頁面側。**
同一個 artifact、同一份 17 頁文件、跨過牆的幾個高度，一步一步問：

| 這一步 | 結果 |
|---|---|
| 引擎 `document.render()` 回的 tile | **對的**——位元組數正好是 `寬×高×4`，而且有墨水，34,847 也一樣 |
| `new ImageData(...)` | **建得起來**，每一個高度都是 |
| `putImageData` 到一張同尺寸的畫布（掛在 DOM 上與不掛，各一次） | **畫得上去**，每一個高度都是 |
| **產品自己那張空白的畫布**，由 harness 直接塗一塊黑 | **吃得下**——36,250 個像素，一個不差 |
| **產品自己把 tile 畫上去** | **從來沒發生** |

最後兩列是同一張畫布、同一個尺寸、同一個時刻：產品自己的墨水是 **1 欄**，
harness 塗的那一塊是**滿的**。所以畫布沒問題，引擎沒問題，是**產品沒有畫**。

⇒ **不需要 relink。** 這一項不屬於被擋住的連結佇列。

### 還沒確立的：是頁面裡的哪一步

這一輪講的是**哪一層**，不是哪一行。兩個候選，都只是候選：

- `paint()` 開頭就是 `if (!lastTile) return;`，而 `layoutCanvas()` 會把
  `lastTile` 設成 null（`web/e2-editor-app.js:171`）。任何在 render 之後又跑一次
  `layoutCanvas()` 的東西，會同時清掉畫布與快取的 tile——而一張幾萬像素高的畫布
  會改變 desk 有沒有捲軸，捲軸會改變 `el.desk.clientWidth`，那正是
  `layoutCanvas()` 讀的東西。
- `renderDocument()` 用 `renderAgain` 做合併，所以一個在飛行中抵達的重繪會**取代**
  而不是接在後面。

不量就指名，正是這一輪存在的理由要避免的事。後續在佇列項
`queue-long-document-blank-page-is-page-side`。

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
