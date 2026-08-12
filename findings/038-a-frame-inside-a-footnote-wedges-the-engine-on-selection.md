# 038 — 選取涵蓋「本文裡有 as-char frame 的註腳」的引用記號時，引擎卡死；037 的擋法擋不到

> **2026-08-12 收窄**：初版說法是「段落的註腳裡有 frame 就會卡」。
> 實測後**兩個條件缺一不可**——選取要**涵蓋引用記號**，而那個註腳本文裡要**有 frame**。
> 四格全部有實測，見〈兩個條件，缺一不可〉。

| | |
|---|---|
| **狀態** | **已確認（2/2）／未修**——**037 的擋法涵蓋不到這條路** |
| **Bugzilla** | —（與 [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)／[012](012-r6-styled-document-close-timeout.md) 同族，未送） |
| **發現日** | 2026-08-12 |
| **嚴重度** | **嚴重**——引擎執行緒之後不再回應任何命令，只有重啟 worker 能救 |
| **可重現** | Chrome 2/2；Firefox 1/1；三種選取方式各 1/1；尾註 1/1；派送動作 1/1；靜置 8 秒一樣死 1/1；**出貨 artifact `835b453d` 上 1/1** |
| **是否上游** | **是**（我方只發了一個滑鼠拖曳選取） |

## 摘要

一個段落，它的**註腳本文裡**有一個 as-char `draw:frame`。對**那個段落**做一次
滑鼠拖曳選取（`editorDiscoverySelect` 的 `mouse-drag`，就是 E1-D 出貨的範圍選取），
選取本身**回報完成**，然後**引擎再也不回應任何命令**：

```
FX-NOTE  drag-select          completed    39 ms   ← 選取自己回來了
         selection-rectangles failed    10001 ms   editorDiscoveryGetState 逾時
         get-selection-text   failed    10000 ms   getSelection 逾時
         selection-reset      failed    10000 ms   editorDiscoverySelect 逾時
FX-TAIL  locate               failed    10000 ms   search 逾時（下一列連錨點都找不到）
```

活性梯與 037 完全同型：**worker JS 活著、wasm 模組從主執行緒仍可呼叫、只有引擎 pthread 不動**。

## 為什麼這一單要跟 037 分開

**037 的擋法在 barrier 的讀取那一步**——讀之前先問 selection type，非 `TEXT` 就具名拒絕。
**這一條路上根本沒有讀取。** 卡死發生在一次選取之後，而選取是產品surface
（E1-D 的範圍選取，`E1_GO_ODT_EDITOR` 出貨的 48 個綁定之一）。

所以：**擋法沒有壞，但它的涵蓋範圍不包含這裡。** 這是一個開著的產品洞。

## 鑑別：是註腳，還是註腳裡的 frame

| 錨點 | 形狀 | 選取型別 | 結果 |
|---|---|---|---|
| `PC-FOOTNOTE`（`paragraph-content`） | 註腳，**裡面沒有 frame** | `text` | **正常**，讀得回文字 |
| `FX-NOTE`（`frame-contexts`） | 註腳，**裡面有 as-char frame** | 讀不到（getState 逾時） | **卡死** |
| `FX-CELL` | 表格儲存格裡的 as-char frame | `complex` | 正常（拒絕由 037 的擋法處理） |
| `FX-PLAIN`／`FX-TAIL` | 沒有 frame | `text` | 正常 |

**所以不是註腳本身**——沒有 frame 的註腳選得好好的。是**註腳本文裡的 frame**。

順帶一提：`FX-CELL` 證明**表格儲存格裡的 frame 走 037 的既有路徑**（`complex` → 被擋），
那是 037 原本列為「沒量過」的兩個情境之一，現在量過了。

## 錨點文字在段落裡，frame 在註腳裡

值得記一筆：被拖曳選取的是**段落本身**，`draw:frame` 在**註腳本文**裡——
兩者不在同一個 `text:p`。所以觸發它不需要選到 frame，
只要選到「有註腳、而註腳裡有 frame」的那個段落。

## 範圍已量（2026-08-12，證據 `038-scope/`）

**觸發它的是「做出一個範圍選取」，不是某一種輸入方式。** 三種互不相同的選取路徑
全部卡死，而**只放游標不會**：

| 選取方式 | 底層 | `FX-NOTE` | 事後引擎 |
|---|---|---|---|
| mouse-drag | `postMouseEvent` ×3 | **卡** | 逾時 |
| text-handles | `setTextSelection` RESET＋END | **卡** | 逾時 |
| keyboard | `move-line-end` ＋ `extendSelection` | **卡** | 逾時 |
| caret-only | 只放游標 | 不卡 | **alive** |
| reset-only | 只 `setTextSelection` RESET | 不卡 | **alive** |

**Firefox 153.0.1 同一形狀**（`FX-NOTE` 同一步失敗、事後引擎逾時、下一列 `search` 也逾時）。

**尾註一樣卡**：`endnote-frame`（同一份文件把 `text:note-class` 由 footnote 換成 endnote）
的 `EN-NOTE` 逐項同型。

**派送格式動作也卡，這下是量到的不是推的**：`frame-contexts` 的討論器四列——
`fx-plain` 完成 38 ms、`fx-cell` 被 037 的擋法以 `selection-type-not-readable` 拒絕 29 ms、
`fx-tail` 完成 30 ms、**`fx-note` 20000 ms 逾時、事後 handle 不可用、`selectionType` 根本沒被記下**。
**barrier 在讀取之前就先做選取**，所以 037 的擋法根本輪不到執行——這正是它擋不到的原因，
現在有直接證據而不是只有結構論證。

**一個假訊號，被活性梯擋下來了**：`caret-only` 與 `reset-only` 兩輪裡，
最後那個 `selection-reset` 步驟**每一列都失敗**——包括沒有 frame 的純段落。
那不是卡死，是探針自己的問題：診斷用的 select 路徑刻意不帶 readback deadline
（`boundedReadback=false`），所以「沒有選取可清」的 reset 不會產生 TEXT_SELECTION callback、
永遠不會完成。**分辨它們的是活性梯**——那五列事後引擎都 `alive` 1–3 ms。
**一個不管文件裡有什麼都同樣失敗的步驟，量的不是文件。** 探針已改成對這兩種方式跳過該步並記下理由。

## 兩個條件，缺一不可（2026-08-12，證據 `038-scope/idle-after-select`、`span-2400`）

**選取本身就殺死引擎，不需要下一個命令。** 選好之後**什麼都不做，靜置 8 秒**，
活性梯就已經是 `engine=timed-out`（對照列 `FX-PLAIN` 同樣靜置 8 秒後 `alive` 10 ms）。
所以卡死是選取的後果，不是「下一個命令踩到什麼」——這也解釋了為什麼串流裡
選取的 callback 都出來了、然後才靜默。

**而且選取必須涵蓋註腳的引用記號。** 同一個段落、同一種拖曳，只把範圍縮到 2400 twips
（讀回 `selectionType=text`、文字是 `FX-NOTE paragraph wh…`，確實選到東西了）
——**完全不卡**，靜置 8 秒後引擎 `alive`。

於是兩個條件都是必要的，而且四格都有實測：

| | 註腳本文**有** frame | 註腳本文**沒有** frame |
|---|---|---|
| 選取**涵蓋**引用記號 | **卡死**（`FX-NOTE` 整行） | 正常（`PC-FOOTNOTE` 整行） |
| 選取**沒涵蓋**引用記號 | 正常（`FX-NOTE` 2400 twips） | —— |

**這比初版的說法窄得多**：不是「這個段落有一個裝了 frame 的註腳」，
而是**「選取涵蓋了某個註腳的引用記號，而那個註腳的本文裡有 as-char frame」**。
機制上也說得通——選取涵蓋引用記號時，core 得把註腳內容一起納進選取模型
（那正是複製註腳文字的方式），frame 就是在那裡被碰到的。

**這對修法是壞消息**：要擋就得知道「這個選取有沒有涵蓋一個註腳的引用記號、
而那個註腳裡有沒有 frame」——**光看 selection type 是問不出來的**
（會卡的那一列連 type 都取不到）。

**第一次量這一格量錯了，被 `selectionType` 抓到。** 初版把「部分選取」設成錨點字寬的一半
（約 513 twips），兩列都回 `selectionType=none`——**拖曳距離太短，根本沒有形成選取**。
如果我只看「有沒有卡」，那一輪會被讀成「部分選取不會卡」，而它其實什麼都沒選。
**一個沒有做到事情的探針，看起來和「做了但沒事」一模一樣。**

## 出貨編輯器也會卡——已在它自己的 artifact 上量到（2026-08-12，證據 `sdk-e1/note-frame-select/`）

**在這之前，「出貨的範圍選取會觸發 038」是跨 artifact 的推論，不是量測。** 038 每一格都跑在
`c89f069e`（E2 探索引擎）上，走的是 `editorDiscoverySelect`；而出貨編輯器**根本沒有那條路**
（`e1-editor-v1` 宣告 `narrow-editor-v1`，沒有 `editor-discovery-closed-actions`）。
外部覆核（fable）指出這一點，並要求在動任何修法之前先補這一格——修法一旦上線，
「今天的使用者會遇到什麼」就永遠問不到了（同 037 那一輪「必須在修法之前量」的理由）。

出貨 artifact `835b453d`，出貨客戶端 `NarrowEditorClient.selectRange`
（走 `editorSelectRangeV1`），每個案例各開一個新引擎：

| case | 形狀 | `selectRange` | 事後編輯器 |
|---|---|---|---|
| `plain-full` | 沒有 frame 的段落（對照） | 完成 7 ms | **可用**，讀回段落文字 |
| `note-partial` | 註腳段落，只選到 2400 twips | 完成 6 ms | **可用**，讀回 `FX-NOTE paragraph wh` |
| **`note-full`** | **註腳段落，選取涵蓋引用記號** | **TIMEOUT，15004 ms** | **不可用**（`getState` 也逾時） |

**所以出貨面確實暴露，而且四格結構與探索引擎上量到的一致。**

**一處自我更正**：我給覆核者的簡報說「產品在死掉之前最後一個對外訊息是 `completed`」。
那對**診斷路徑**成立（`editorDiscoverySelect` 回報完成後引擎才死），**對出貨路徑不成立**——
出貨的 `selectRange` 在請求之後還會讀回選取狀態，所以呼叫端拿到的是 **`TIMEOUT`，不是成功**。
覆核者「文件帶過不可接受」的最強論據因此在出貨面**比我描述的弱**：
使用者的操作會失敗並且說它失敗了，壞的是**之後整個編輯器不再回應、未存檔內容只能靠重啟 worker 拿回**——
那仍然嚴重，但理由不是「謊報成功」。

**順帶再一次確認 [012](012-r6-styled-document-close-timeout.md)**：三個案例（含兩個沒卡的）
`close` 全部走 `document-close-recovery`、各約 10.9 秒——因為這份文件裡有 as-char frame。

**四格已在出貨 artifact 上補齊**（第二輪，`chrome-no-frame-note/`）：
`footnote-no-frame-full`＝註腳但**沒有 frame**、整行選取涵蓋引用記號，
`selectRange` **8 ms 完成、編輯器可用、讀回段落文字**。所以探索引擎上量到的 2×2
在 `835b453d` 上逐格複製成立。

**出貨的鍵盤選取路徑也會卡，但形狀不同**（`chrome-keyboard/`）。出貨客戶端把
`extendSelection` 限制在 `move-character-left/right`，所以出貨的鍵盤選取是**逐字元 shift**。
從 `FX-NOTE` 起點連擴 60 次：**60 次全部成功**，然後**下一次讀狀態（`getState`）逾時**，
編輯器不可用（2/2）。這與拖曳那條路不同——拖曳是**選完之後靜置 8 秒就已經死了**，
逐字元這條是**命令一路都被回應、死在之後的讀取**。兩者最終狀態相同，但**觸發時機不同，
成因是否相同沒有證據**，不要合併敘述。

**那一輪的對照組不乾淨，記在這裡而不是當成通過**：`plain-full` 從 `FX-PLAIN` 起點擴 60 個字元，
**已經擴出那個段落、進到表格**（事後 `selectionType=complex`、4 個矩形、文字為空）——
它沒有卡，但它證不了「純段落的鍵盤選取安全」，因為它選到的不只是純段落。
要有乾淨的對照，得用一份「後面沒有 frame 可以擴進去」的文件重跑。

**沒量到的**：這一輪用的是 `NarrowEditorClient` 直接對 document handle，**沒有跑完整的
`EditorSession` 狀態機**，所以「產品會不會自己升級成 `restart-required`」仍然沒有答案。

## 沒有做的事（誠實界線）

- **不知道卡在哪個呼叫**。選取的 callback 全部出來了、`.uno:SelectText` 的 result 也出來了，
  然後靜默；靜置 8 秒不下任何命令，引擎已經死了。所以卡點在**引擎處理完選取之後**，
  而那之後引擎自己還會做什麼（callback 處理、狀態廣播）沒有一個明顯的 LOK 呼叫可以指。
- **在帶名稱的 build（`150de122`）上重現過一次並取樣**，但那一輪**八條 worker 裡有四條
  的 CDP session 在取樣途中消失**（`Session with given id not found`），所以那一輪的
  「四條 parked」**是不完整的觀察，不是完整的盤點**。可比的只有控制組那一半：
  兩條 `__pthread_cond_timedwait`、五條 idle。
- **沒量「frame 要多深」**：註腳本文只試過一層。表格儲存格裡的 frame 走 037 的擋法
  （型別 `complex`），註腳裡的走這一條——**兩者差在哪還沒有解釋**。
- **沒量產品的 UI 路徑**（editor-shell 的實際手勢），只量了 SDK 這一層的三種選取。

## 相關

- [037](037-a-paragraph-with-an-inline-image-wedges-the-handle.md)——同一個內容特徵
  （as-char frame），不同的入口；037 的擋法在讀取那一步，擋不到這裡。
- [012](012-r6-styled-document-close-timeout.md)——同一個內容特徵的第三個入口（`destroy()`）。
- [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)——
  帶註腳的段落在 barrier 那一側是**具名拒絕**（`footnote-apparatus-readback`），
  那條路徑不碰這個洞；這裡走的是選取，不是 barrier。

## 修訂紀錄

- **2026-08-12（初版）**：`frame-contexts` fixture 量到；2/2 重現；
  `PC-FOOTNOTE`（沒有 frame 的註腳）作為控制組正常。
