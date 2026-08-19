# 059 — finding 045 的修法出貨之後,**四個 inline 格式全部失敗**:`LOK_COMMAND_FAILED`

| | |
|---|---|
| **狀態** | **已確認／機制已定（原生＋WASM 兩側都量過)／未修——修法要一次連結** |
| **Bugzilla** | —（未判定是否上游;**在指認機制之前不得送出**) |
| **發現日** | 2026-08-17(短期目標驗收清單第一次驅動 `action:set-bold`) |
| **嚴重度** | **阻斷**——四個 inline 格式一個都不能用;而且 2026-08-18 量到**核心其實照做了**,所以產品是在叫使用者回滾一個成功的動作 |
| **可重現** | 100%（Firefox,artifact `d538ce0b`,收合游標,純文字段落) |
| **是否上游** | **未確認** |

## 現象

在出貨的 v3 artifact 上,把收合游標放在一段純文字上,按工具列的 **B**：

```
B：LOK_COMMAND_FAILED：LibreOfficeKit rejected the fixed editor command
（可能已經改到文件：請回到檢查點）
state: recoverable-error
```

**I 與 U 逐字相同。** 清單動作(`.uno:DefaultBullet` 等)**照常運作**——所以不是
派送機制整個壞掉,是**這四個**。

原始輸出:[`evidence/059/format-actions-on-a-collapsed-caret.json`](evidence/059/format-actions-on-a-collapsed-caret.json),
重跑腳本在同一個目錄。

## 這是 045 修法造成的迴歸

| artifact | 行為 |
|---|---|
| **v2 `572035ac`** | 粗體**會套用**,但忽略 `enabled`——**那正是 finding 045 的內容** |
| **v3 `d538ce0b`** | 粗體**完全失敗** |

兩者之間的差異就是 045 的修法:`inlineFormatArgument()` 把
`.uno:Bold` 從**不帶參數**改成帶
`{"Bold":{"type":"boolean","value":true}}`(`probe_engine.cpp:3262-3265`)。

**045 修法的意圖是對的**（不帶參數的 slot 宣告 `Toggle = TRUE`,所以會切換而不是
設定),而且它在原生上量過。但在**出貨的 WASM build 上,核心拒收**。

## 為什麼兩天沒人發現

`action:set-bold`／`set-italic`／`set-underline`／`set-strikethrough` 四格,
在 `e2/product-path-coverage.json` 裡全部登記為 **uncovered——按鈕在,沒有人按過**。

這是同一種病的第五次:

| | 沒被量到的是 |
|---|---|
| 049／050／Ctrl+C | 按鈕沒人**按**過 |
| 056 第一次連結 | 機制沒人確認**編進去**沒 |
| 058 | 畫面**沒人看**過 |
| **059** | **修法出貨之後沒人按過那顆按鈕** |

**修法有原生證據、有靜態檢查、進了佇列、擋了連結、跟著連結出貨——中間沒有任何
一格是「在產品上按一下它」。**

## 機制（同日補完,原生對照)——**而且它推翻了本篇原本的標題假設**

原文寫「核心拒收」。**核心沒有拒收,核心照做了,然後回報失敗。**

原生量測（[`evidence/059/native/`](evidence/059/native/)),每一臂放游標、派送、
**打一個標記**,判準讀存檔出來的 ODT——不是讀命令結果:

| 臂 | 標記 | 存檔裡的樣式 | 粗體? |
|---|---|---|---|
| 對照,不派送任何命令 | `AAA` | `T2` | 否 |
| **`.uno:Bold` ＋ 參數 `true`** | `BBB` | **`T1`**——`fo:font-weight="bold"` | **是,成功了** |
| `.uno:Bold` 不帶參數 | `CCC` | `T4`——`normal` | 否 |
| `.uno:Bold` ＋ 參數 `false` | `DDD` | `T4`——`normal` | 否 |

**帶參數的形式完全照 045 的意圖運作。** `true` 出粗體,`false` 出 normal。

而同一臂的命令結果是:

```json
{ "commandName": ".uno:Bold", "success": false, "wasModified": true }
```

**做對事情的那一臂回報 `success: false`;回報 `true` 的那一臂(不帶參數)反而沒有
變粗體。** 所以 `success` 在這裡不代表「命令成功」。

對照排除了「這是 bold 特有的」:`.uno:DefaultBullet` ＋ `{"On":…}`——**產品自己的
format barrier 用的就是這個形狀,而且它能用**——同樣回 `success: false`、
`wasModified: true`。

### 所以缺陷在我們這邊

`probe_engine.cpp:1696` 的 `commandResultSucceeded()` 要求 `success: true`,
`:2286` 把其他一切變成 `LOK_COMMAND_FAILED`。**barrier 那條路不是這樣判的**,
這就是清單動作照常運作、而四個 inline 格式停擺的原因。

**045 的修法是對的。** 壞掉的是:它把這四個命令換到一種「結果酬載會被我們自己的
判準讀成失敗」的參數形式上。

**仍然不指認的**:核心為什麼對一個做成了的命令回報 `false`。沒量到,不寫。

## 後果與處方

- **短期目標的「格式」那一整格是 blocked 的**,不是 unverified。
- **修要一次連結**,而且原生量測之後候選變了:**不要撤回 `inlineFormatArgument`**
  ——那會把一個正確的修法丟掉。要改的是**判準**:對這四個命令不要用 `success`
  判成敗。**判準已經量出來了(2026-08-18),見〈判準:量完了〉。**
- 產品端沒有可做的事:頁面送 `enabled: true` 或 `false` 都一樣失敗。
- **回歸網會是紅的,而且應該是紅的**:`bold-can-be-turned-off-again` 紅著,
  直到這一格修好。

## 修訂 2026-08-18 —— **`wasModified` 出局,而且不需要量**

本篇原本寫「`wasModified` 是明顯的候選」。**那句話是錯的,讀核心的原始碼就知道。**

```
desktop/source/lib/init.cxx:5517-5518
    new DispatchResultListener(pCommand, pDocument->mpCallbackFlushHandlers[nView],
                               pDocSh && pDocSh->IsModified()));
```

那個布林是 `DispatchResultListener` **建構時**捕捉的 `IsModified()`,而建構發生在
`comphelper::dispatchCommand()` 被呼叫**之前**——它是那一行的引數。成員自己的註解
就寫著 `//< Whether or not the document was modified **before** saving`
(`:5073`),`dispatchFinished()` 只是把同一個值原樣寫回酬載(`:5098`)。

⇒ **`wasModified` 說的是「這個命令跑之前,文件是不是已經髒了」,不是「這個命令
改了東西沒有」。** 一份先前被編輯過的文件,會讓一個什麼都沒做的命令回報 `true`;
一份剛存過的乾淨文件,會讓一個成功的命令回報 `false`。

本篇上面那個表裡的 `wasModified: true`,**完全可以只是因為探針在每一臂之前都先
打了一個標記**(`evidence/059/native/f059_native_inline_format_argument.cpp`:
共用一份文件、每臂先打字、全部跑完才存檔)。它不是那一臂的證據。

**這一段沒有推翻本篇的機制**——「核心照做了、然後回報失敗」仍然成立,那是靠
存檔裡的 `fo:font-weight` 判的,不是靠 `wasModified`。被推翻的只有「處方」。

由 codex 對抗性審查(2026-08-18)指出,`init.cxx` 三處與 `dispatchcommand.cxx`
的行為本人已逐條回讀核對。

### 連帶:拒絕臂不可以用「核心不認得的 slot」

`comphelper::dispatchCommand()` 在 `queryDispatch()` 回 null 時直接 `return false`
(`comphelper/source/misc/dispatchcommand.cxx:48-50`),**listener 不會被呼叫,
`LOK_CALLBACK_UNO_COMMAND_RESULT` 根本不會發**。用不存在的 slot 當「失敗對照」
的臂什麼都沒量到,而一個「欄位缺席就給預設值」的分析器會讓它看起來通過。
拒絕臂必須是**核心認得、但當下不能跑**的命令,而且每一臂都要證明自己收到了一次
新的回呼。

## 判準:量完了（2026-08-18,原生,`evidence/059/native/predicate/`)

預測先寫（[`PREDICTION.md`](evidence/059/native/predicate/PREDICTION.md)),
再跑探針。十臂,每臂用鍵盤(Ctrl+Home、Down×N、End)走到自己的段落——**不是點
猜出來的 y**,那會讓兩臂共用一段而 pending 屬性互相汙染。判準讀**標記那一段文字
實際掛著的 style**,不是 grep `fo:font-weight`。

| 臂 | 要求 | 核心廣播 | 存檔 |
|---|---|---|---|
| 對照,不派送 | — | — | 無樣式 |
| `.uno:Bold` true | true | `.uno:Bold=true` | **粗體** |
| `.uno:Bold` false | false | **（沒有)** | 不粗 |
| `.uno:Italic` true／false | | `.uno:Italic=true`／**（沒有)** | 斜／不斜 |
| `.uno:Underline` true／false | | `.uno:Underline=true`／**（沒有)** | 底線／無 |
| `.uno:Strikeout` true／false | | `.uno:Strikeout=true`／**（沒有)** | 刪除線／無 |

**九臂的存檔結果與要求完全一致。** 四個 slot 全部照做,`success` 全部是 `false`。

### 掉出來的第一件事:**判準不能是「有沒有收到廣播」**

核心廣播的是**狀態改變**,不是狀態。`value:false` 那幾臂因為游標本來就不是粗體,
**一個廣播都沒有**——而文件結果完全正確。

所以「收到廣播＝成功」會把九臂裡四臂正確的動作judged成失敗。

**站得住的判準是 barrier 已經在用的那一個**:`formatBarrierPostconditionMet()`
(`probe_engine.cpp:1189`)——**比對觀察到的狀態與要求的狀態**,是一個
postcondition,不是一個通知。在這十臂上它九次全對,包含四個沒有廣播的。

### 第二件事:引擎裡有一句關於核心的話是錯的

`probe_engine.cpp:4308-4310` 說底線與刪除線之所以不留 format-state cache,是因為

> Neither command appears in core's `GetKitUnoCommandList()`

**兩個都在那份清單裡**(`sfx2/source/control/unoctitm.cxx:1165ff`,而且沒有旗標
把它關掉),而且本輪實測兩個都會廣播。那個 cache 不是不能有,是沒有人加。

### 第三件事:**拒絕臂沒有拒絕,所以「判準說得出不」沒有被證實**

原本設計用 `setViewReadOnly(doc, 0, true)` 當「核心認得但當下不能跑」。
**核心照樣做了**——廣播到了,標記也真的變粗。所以那一臂不是拒絕臂,P6 未確立。

**欠一個真的負向臂**:每一臂都是成功的動作,所以這一輪證明了判準會同意,
沒有證明它會反對。

### 仍未量的

state cache 要被 primed 才讀得到;從來沒廣播過的游標上 `…Known` 是 false。
finding 021 講的就是這個。本輪沒量。

## 那兩件欠的事量完了（2026-08-19,原生,`evidence/059/native/negative-arm/`)

九臂、一份文件、判準讀標記自己那一段掛的 style。**零個不一致。**

### 判準說得出「不」——兩臂,而且正好落在文件也說不的地方

| 臂 | 參數 | `success` | 廣播 | 判準 | 文件 |
|---|---|---|---|---|---|
| 對照,不派送 | — | — | — | not-met | 沒套用 |
| `{"Bold":{"type":"boolean","value":true}}` | 正常 | false | `.uno:Bold=true` | met | **套用了** |
| **型別錯**:`{"Bold":{"type":"string","value":"true"}}` | | false | **(無)** | **not-met** | **沒套用** |
| **名稱錯**:`{"Bald":{…}}` | | **true** | `.uno:Bold=true` | met | 套用了 |
| **不帶參數** | | **true** | `.uno:Bold=true` | met | 套用了 |
| `setViewReadOnly` | | false | `.uno:Bold=true` | met | 套用了（**還是沒拒絕**) |
| **受保護的 section 裡** | | false | **(無)** | **not-met** | **連字都打不進去** |

刻意問了不只一種拒絕法:037 的教訓是「你以為會拒絕的守衛,可能為了別的理由拒絕、
也可能根本不拒絕」,而 059 自己的第一個拒絕臂就沒拒絕。問四種、報告哪幾種真的拒絕,
才是量測。

受保護 section 那一臂:游標**進得去**（記到 `.uno:StateTableCell=read-only : …`
與一整片 `disabled` 廣播),派送被拒,而且**連標記都沒打進去**。報成 `not-typed`
而不是「沒樣式」——「什麼都沒打」和「打了但沒變粗」是兩個不同的觀察。

### 快取是 primed 的,而且是**開檔**那一刻,四個 slot 都是

```
"slotsKnownBeforeAnyDispatch": ["bold", "italic", "strikeout", "underline"]
"values": {"bold": false, "italic": false, "strikeout": false, "underline": false}
```

核心在開檔時廣播一份**完整**的狀態(第一臂的 `fromCaretMove` 有約 120 筆),
之後只廣播**改變**。所以 021 的形狀在這裡不咬——**但理由是開檔那一次廣播,不是
游標移動**。實測:游標在兩個狀態相同的段落之間移動,一個廣播都沒有。一個晚一點才
開始聽、或漏掉開檔廣播的引擎,會回到 021 的形狀。

**底線與刪除線也在那份廣播裡**,所以〈第二件事〉那句假話這一輪又被反證一次——
這次是實測,不只是讀核心的原始碼。

### 順帶:`success` 這個欄位是**反相關**的

`success: true` 只出現在**兩臂**——名稱錯的、和不帶參數的——而那兩臂正是核心
**忽略了參數、改成 toggle** 的臂。每一個核心真的照參數做的臂,`success` 都是 false。

所以引擎現在 gate 的那個欄位(`commandResultSucceeded()`,`probe_engine.cpp:1696`)
在這個 build 上不只是沒用:它和「呼叫者的要求有沒有被照做」**方向相反**。
回報成功,是核心沒讀你參數的時候會做的事。

## 判準

`bold-can-be-turned-off-again`(`tools/run_e2_c_product_path.py`)。
今天它紅在第一次按下去就失敗;修好之後,它要求的是**按兩次之後引擎回報不是粗體**。


## 那一格量完了（2026-08-18,`evidence/059/wasm/`)——**答案是壞的那一個**

本篇原本寫「WASM 上是不是也照做了,沒有量」,並且說如果是,那產品就是
**在一個成功的動作上叫使用者回滾**。

**量了。是。四個 slot 全部。**

六臂,每臂各自開一個乾淨的頁面、走產品自己的開檔路徑、放一個**確認過**的收合游標、
按產品自己的工具列鈕、用產品自己的插入鈕打一個標記、按產品自己的存檔鈕,判準是
存出來的 ODT 裡**那個標記那一段掛的樣式**:

| 臂 | 命令結果 | 標記的樣式 |
|---|---|---|
| 對照,不派送 | — | **無樣式** |
| `set-bold` | `LOK_COMMAND_FAILED` | **粗體** |
| `set-italic` | `LOK_COMMAND_FAILED` | **斜體** |
| `set-underline` | `LOK_COMMAND_FAILED` | **底線** |
| `set-strikethrough` | `LOK_COMMAND_FAILED` | **刪除線** |

**每一臂拿到的正好是它按下去的那一個 slot,沒有別的。** 語料本身沒有任何字元樣式
（產生器自帶 self-test),而對照臂——同一份語料、同一個游標、同一次插入、不派送
命令——回來是沒有樣式的。所以樣式是那次派送造成的,而 slot 的一一對應排除了巧合。

⇒ **今天出貨的產品,按下 B 會把字變粗,然後告訴使用者這個動作失敗了、請回到
檢查點。** 它是在叫使用者丟掉工作,去撤銷一個成功的改動。

**範圍選取那條路是關著的,而且是量出來關著的**:把頁面的 gesture mask 拿掉之後,
四個派送全部回 `EDITOR_FORMAT_GESTURE_UNSUPPORTED`——mask 在**引擎那一側也有**
（`editorGesturePermitted`,`probe_engine.cpp:4247-4252`),引擎自己的訊息就寫著
「nothing was dispatched and the document is unchanged」。所以這四個動作在這個
build 上**只可能在收合游標上到得了核心**。

量測用了兩個具名 shim（鏡像,`dist/` 不寫),各自的代價寫在證據裡:
**這一輪不描述產品真正的處置,那仍然是 rollback。**

**仍然不指認**:核心為什麼對一個做成了的命令回報 `success: false`。
