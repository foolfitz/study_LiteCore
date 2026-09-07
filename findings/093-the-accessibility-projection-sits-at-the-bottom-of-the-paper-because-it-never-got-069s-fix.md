# 093 — 無障礙投影節點躺在紙張底部，因為它沒有拿到 069 的那個修法

**狀態**：機制已由原始碼確認，**行為量測未做**（phase 2 待跑）。
**發現者**：擁有者，2026-09-08 00:09–01:00 CST 的 T4 人工輪，用眼睛抓到。
**證據**：`findings/evidence/manual-round-v12e-9b29e39b/`（擁有者筆記、兩趟
Orca 語音記錄）。

## 現象（擁有者原話）

> 好像只要用鍵盤方向鍵就會捲到頁面底部，沒辦法使用。

追問「畫面捲到底時編輯器還看得到嗎」，答：**「捲過頭」**——編輯器還在畫面上，
是視窗捲得太遠。

**而同一段時間裡朗讀是對的。**第二趟 00:57:39–00:58:47，Orca 依序唸出
heading 1 →內文→ heading 2 →內文→ heading 2，順序與角色都正確
（`orca-speech-t4-4b-round2.txt`）。**朗讀游標在文件裡正常前進，視窗卻停在
頁面底部**——兩件事同時為真，那個落差就是這張單。

對只用耳朵的人這一頁也許還能用；對**同時用眼睛看又開著螢幕閱讀器的人**
（低視力使用者）它是不能用的：看不到它正在唸哪一行。

## 機制（原始碼確認，非推測）

`wasm_sdk_probe/web/e2-editor.html`：

- 第 65–70 行，`.a11y-only` 是 `position: absolute`，**沒有 `top`／`left`**。
- 第 236 行，`#a11y-doc`（承載整個結構投影的容器）用的就是 `.a11y-only`，
  而它在 DOM 裡排在 `#canvas`（第 228 行，`display:block`、整份文件的高度）
  之後，容器是 `.paper`（`position:relative`）。所以它的靜態位置**就在紙張
  的最底部**。JS 從來沒有替它定位過。
- 第 82–95 行——**距離上面那條規則只有四條規則**——有一段註解，逐字寫著這件事
  為什麼要命：

  > `top`/`left` are not decoration. Without them an absolutely positioned
  > element sits at its STATIC position -- which for this one is directly
  > after the canvas, and the canvas is the whole document's height. The
  > input sink was therefore lying at the bottom of the page, and every time
  > an IME began composing, the browser scrolled the focused element into
  > view and took the whole desk with it. Reported by an operator typing
  > Chinese with 新酷音, 2026-08-22.

  那就是 **finding 069**。
- 第 98 行，`#sink` 拿到了修法：`position: absolute; top: 0; left: 0`，
  並由 `paint()` 持續騎在游標上。

**`#a11y-doc` 從來沒有拿到同一個修法。**同一個檔案、相隔約一百四十行、成因
寫在註解裡。

## 為什麼現在才被看到

`e2-editor.html` 是**兩個 profile 共用的同一個檔案**——出貨的 `e2-editor-v8`
與候選的 `e2-editor-v12` 在 DOM 與 CSS 上逐位元相同（候選頁面與出貨頁面的差異
是 `e2-editor-app.js` 裡的**兩行、一個位元組**：wasm pin 與 worker URL）。

差別在**可達性**：v12 的 manifest 提供 `caretParagraphText` 與
`documentOutline`，所以 `#a11y-structure` 裡每一段都有一個節點；v8 兩者皆無，
`#a11y-structure` 是 `aria-hidden`、沒有子節點。**同一個缺陷在 v8 上大概只有
一個停靠點，在 v12 上是每一段都有一個**——於是走訪全程視窗都被釘在底部。

**這是預測，不是量測**（phase 2 的第一項就是量它）。

## 這不是「候選帶進來的退步」，也不是「兩邊都有所以不算」

**是第三種**：缺陷躺在兩個 profile 共用的位元組裡，而**只有候選讓它在日常使用
中會被走到**。分類的後果由閘門擁有者裁定，不由起草方裁定（AGENTS.md §8）。

## 069 的回歸網沒有涵蓋這條路

`sink-does-not-drag-the-page` 只讀 `#sink`，而且是用 IME 上屏驅動的；
`arrow-keys-match-the-profile` 量的是按鍵有沒有被吃掉、游標、toast，**從不量
捲動**。兩者都沒有讀過 `#a11y-doc` 的幾何。**069 修好的是一個元素，不是一個
類別**，而回歸網跟著只守那一個元素。

## 未做

- `#a11y-doc.offsetTop` 與 `.desk` 的捲動比例，兩個 profile 都要量。
- v8 是不是真的把 `#a11y-structure` 留在 `unavailable`（預測，未量）。
- 正對照：把 `.a11y-only` 補上 `top:0;left:0`，捲動比例應該塌掉。**沒有塌掉
  就表示上面整套判讀是錯的。**
- 「捲到底之後按 Tab 看焦點落在哪裡」這個直接區辨也沒做。

## 一併記下的另一個現象，**不要跟上面併成一句**

按到文件第一行再往上，焦點會離開文件區域跑到工具列。整晚 log 裡
`leaving panel` 出現三次（00:10:42.301、00:12:13.462、00:58:20.269），全部在
頂端邊界。頁面裡**沒有任何焦點圍堵**（沒有 `tabindex`、沒有 focusin/focusout
陷阱、唯一的 `keydown` 監聽在 `#sink` 上），而這些位元組兩個 profile 共用。

主 session 一度把這兩個現象併成同一個假說，**那是推論不是量測，已在筆記裡
更正並保留**。
