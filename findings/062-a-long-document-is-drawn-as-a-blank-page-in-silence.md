# 062 — 文件夠長的時候，編輯器給你一張空白畫布，而且什麼都不說

| | |
|---|---|
| **狀態** | **兩半都已修（2026-08-19）**——空白頁走殼層 v19 的分段繪製（不需連結），成長那一半走連結（artifact `296f3ea727725fbb`）。層級已確立：引擎側（LAYER-ESTABLISHED，`evidence/062/layer/`） |
| **Bugzilla** | —（**我方產品缺陷，不是上游**，不送出） |
| **發現日** | 2026-08-19 |
| **嚴重度** | **嚴重**——使用者看到的是一份空白文件，而產品回報一切正常 |
| **可重現** | 100%（Chrome，dpr 1 與 dpr 2 各 1/1；畫布高度掃描 8/8 單調） |
| **是否上游** | **未確認**——引擎回了一張沒有畫進去的 buffer 並回報成功；那個 2^15 是核心還是我們的引擎，沒有讀過原始碼 |

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

### 層級：**引擎側**（2026-08-19 量完，`evidence/062/layer/`）

> **本節在同一天被更正過一次。** 第一版寫「頁面側」，而且**錯了**。錯法比結論值錢，
> 寫在〈我第一次判錯的原因〉。

**一次冷啟動的 render，只要 tile 高過 32,767 px，回來的 buffer 尺寸正確、內容全零、
而且回報成功。** 每一列都是一次新載入頁面裡的第一次 render，前面什麼都沒做：

| 寬 | 高 | buffer | 有畫嗎 |
|---|---|---|---|
| 362 | 32,767 | 45.2 MB | **有**——41,762 個深色像素、347 欄 |
| 362 | **32,768** | 45.2 MB | **沒有**——0 |
| 362 | 34,847 | 48.1 MB | 沒有 |
| 362 | 65,000 | 89.8 MB | 沒有 |
| 725 | 32,767 | 90.6 MB | **有**——70,209 個、694 欄 |
| 725 | 34,847 | 96.4 MB | 沒有 |

**是高度，不是大小。** 兩個寬度在**同一個高度**翻面，而它們的 buffer 差兩倍——
45 MB 在 32,767 畫得出來，45 MB 在 32,768 是空的。記憶體上限做不到這件事。
32,767 = 2^15 − 1。

### 頁面那三步都量過，都沒問題

- **產品的 paint 是忠實的**：包住 `putImageData` 看到產品交給畫布的是一張
  101,056,300 位元組、抽樣 2,105,340 個像素裡 **2,105,295 個完全透明**的圖——
  它把拿到的「什麼都沒有」原原本本畫上去了。16,934 那次同一個包裝顯示進去 13,544
  個深色像素、畫完畫布上也是 13,544。
- **畫布沒問題**：產品停在空白狀態時，由 harness 往同一張畫布塗一塊黑，
  36,250 個像素一個不差。
- **請求也沒問題**：包住 `Worker.prototype.postMessage` 看到產品送出的是
  `{"operation":"paint","payload":{…,"canvasWidthPx":725,"canvasHeightPx":34847}}`
  ——和本檔探針送的一模一樣。

### 對修法的意義：**引擎側的缺陷，但不需要等連結**

沒有任何東西逼產品把整份文件要成一張 tile。分段繪製（不超過 32,767），或用
`editor-session.js` 已經匯入的 `TileScheduler`，就完全避得開這個上限，而那是**頁面
側的改動**。所以這一項**不擋下一次連結**。

它真正的意思是：「引擎你要多大它就畫多大」這句話是假的，而目前**只有頁面知道自己
要了多高**。

### 我第一次判錯的原因（留著，因為這才是可重用的部分）

第一版探針把一串高度**由小到大、在同一個 session 裡**掃過去。第一次 render 永遠
在上限以下、畫得出來，後面超過上限的每一臂也都回來有內容——於是引擎看起來清白，
損失看起來在頁面。接著我把頁面那三步逐一量過，每一步都好，結論就顯得很有依據。
**它確實有依據，而且是錯的**，因為被它洗清的那個東西，是被探針自己前面幾臂**熱身**
過的。

**可重用的教訓：一個在同一個 session 裡掃參數的探針，會在臂與臂之間帶狀態；而由小
到大掃，正好是最能藏住冷啟動上限的順序。** 打開它的對照是「一次載入只做一次
render」。這棵樹自己也有同型的前例——探針殺死了它要觀察的東西（finding 038）——
值得同一種懷疑：**我前面幾臂，對這一臂要問的東西做了什麼？**

### 還沒確立的

- **引擎裡的哪一行。** 2^15 這個數字讓人聯想到 16 位元，但那是**從數字推的**，
  不是量到的；本輪沒有讀核心或引擎在那一點的原始碼。
- **熱身過的 session 在上限之上回的是什麼。** 前面做過較小的 render 之後，超過上限
  的 render 會回來有內容，而它頂端的墨水欄數和**前一次較小的 render 完全相同**
  （464 對 464，而同一份文件在不同高度本來會給出 694／443／464）。這和「buffer 被
  重用而且從來沒有被重畫」一致，也就是一張**靜靜過期**的圖，比空白更糟。
  有跡象，未確立。

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

## 修法：一半當天修好了，另一半頁面修不了

### 已修：空白頁（殼層 v19，**不需連結**）

`renderDocument()` 改成**分段要圖**——每一段不超過 `MAX_TILE_HEIGHT = 32767`，
各自貼在自己的 y。文件短到裝得下時就是一段、涵蓋整張畫布，也就是這一頁一直以來
送出的那個請求，所以**常見情況一點都沒變**。

實測：35 頁在 dpr 1（畫布 34,847）與同一份 20 頁在 dpr 2（39,839）**都畫得出來**了，
兩者原本都是全白。**沒有接縫**——在 32,300／32,600／32,900 與最底下各取一條帶，
全部完全不透明而且都有墨水。

**外加誠實那一半**：`renderDocument()` 現在會拒收一張引擎沒有畫進去的圖
（`TILE_NOT_PAINTED`），判準是**抽樣 alpha**——沒畫過的 buffer 連 alpha 都是 0，
而一張真的空白的頁面是**不透明的白**，所以兩者分得開，而且只要幾百次讀取就夠
（那個 buffer 可以有一億位元組）。突變 `one-tile-for-the-whole-document` 把上限拿掉
之後，產品現在會說「重繪失敗：TILE_NOT_PAINTED：引擎回了一張沒有畫進去的圖」，
而不是靜靜給一張白紙。

> **判準第一版是錯的，而且是突變抓出來的。** 它「只要有一個 alpha 不是 0 就算畫過」，
> 而沒畫過的 buffer **不是均勻全零**——抽樣的 2,105,340 點裡有 88 點不是，
> 靠近開頭的一點就足以騙過整個判準。改成**多數決**（一半以上的取樣點不透明）：
> 畫過的圖約 90% 不透明，沒畫過的是 0%，兩邊各留兩個數量級的餘裕。

### 已修（連結，2026-08-19）：變高的編輯，畫布跟上了

`getDocumentSize` **只在開檔那一刻被呼叫過**（`probe_engine.cpp:2520`），
而 SDK 的操作裡（open／paint／click／insertText／search／getSelection／
replaceSelection／undo／save／註解／追蹤修訂）**沒有任何一個會回報尺寸**。
所以沒有東西能告訴頁面文件變高了——在 `document-invalidated` 裡呼叫 `layoutCanvas()`
也沒用，它只會拿同一個過期的數字重算一次。

**修法就是那個很小的引擎改動**，而它搭上了 2026-08-19 的連結：
`handlePaintTile` 現在會重讀 `getDocumentSize`，並在回覆裡帶上
`documentWidthTwips`／`documentHeightTwips`／`documentSizeChanged`；
worker 把它們轉出去（**它的回覆是白名單**——只改引擎的話這些欄位對所有 client 都是
隱形的，這一點值得記住）；`DocumentHandle.render()` 順手更新 handle；頁面看到尺寸
變了就重新 layout 並重畫，走的是它本來就有的 `renderAgain` 合併路徑。

一樣用 `OXSDK_E2_FORMAT_BARRIER` 包住：`handlePaintTile` 是所有 profile 共用的，
而凍結的那些是在特定回覆形狀上驗過的。

`the-canvas-follows-a-document-that-grew` 從 KNOWN_RED 變綠，由
`ignore-a-document-that-grew` 突變守著。

**留著的具名極限**：引擎本身仍然不會畫高過 32,767 的 tile，而且會回報成功。產品是
繞開它，不是它被修好了——佇列項 `queue-engine-reports-success-for-an-unpainted-tile`。

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
