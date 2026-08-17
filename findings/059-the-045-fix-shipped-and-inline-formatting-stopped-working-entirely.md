# 059 — finding 045 的修法出貨之後,**四個 inline 格式全部失敗**:`LOK_COMMAND_FAILED`

| | |
|---|---|
| **狀態** | **已確認／機制已定（原生對照,同日)／未修——修法要一次連結** |
| **Bugzilla** | —（未判定是否上游;**在指認機制之前不得送出**) |
| **發現日** | 2026-08-17(短期目標驗收清單第一次驅動 `action:set-bold`) |
| **嚴重度** | **阻斷**——粗體/斜體/底線/刪除線**一個都不能用**,而且每按一次就把 session 打進 `recoverable-error` |
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
  判成敗(`wasModified` 是明顯的候選,barrier 的 readback 是另一個)。
  **兩個候選都還沒量過,所以都還不是結論。**
- 產品端沒有可做的事:頁面送 `enabled: true` 或 `false` 都一樣失敗。
- **回歸網會是紅的,而且應該是紅的**:`bold-can-be-turned-off-again` 紅著,
  直到這一格修好。

## 判準

`bold-can-be-turned-off-again`(`tools/run_e2_c_product_path.py`)。
今天它紅在第一次按下去就失敗;修好之後,它要求的是**按兩次之後引擎回報不是粗體**。


## 未確立的一格,而且它很重要

**WASM 上是不是也「照做了但回報失敗」,沒有量。** 產品一按就進 `recoverable-error`,
所以那邊的文件效果沒有被讀過。它回報的 `success: false` 與原生一致,但
**「一致」不等於「量到」**——這棵樹在這道縫裡錯過三次(040、048,以及本篇原本的機制)。

如果 WASM 上也是照做了,那今天的產品是**在一個成功的動作上叫使用者回滾**,
那比「不能用」更糟。
