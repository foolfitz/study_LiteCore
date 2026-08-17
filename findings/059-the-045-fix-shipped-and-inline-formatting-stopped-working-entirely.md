# 059 — finding 045 的修法出貨之後,**四個 inline 格式全部失敗**:`LOK_COMMAND_FAILED`

| | |
|---|---|
| **狀態** | **已確認（產品頁實測,2026-08-17)／機制未定／未修** |
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

## 機制:**不指認**

`LOK_COMMAND_FAILED` 是引擎在 `postUnoCommand` 那條路回報失敗時發的。
為什麼核心拒收帶參數的 `.uno:Bold`,**沒有量到,所以不寫**。
finding 040 與 048 是先例。

**要查的方向**（是方向,不是結論）:
- 原生對照——同一個參數形式在 native 上是否也失敗。045 的原生證據說可以,
  但那一輪的呼叫方式要逐行比對過才算數。
- 清單動作用的是同一個參數機制而且能用,所以差別不在「帶不帶參數」,
  而在**這個 slot 的參數名稱/型別**。

## 後果與處方

- **短期目標的「格式」那一整格是 blocked 的**,不是 unverified。
- **修要一次連結**,兩個候選:把 `inlineFormatArgument` 撤回(回到 v2 的行為:
  能開不能關),或找出正確的參數形式。**兩個都要先有原生量測。**
- 產品端沒有可做的事:頁面送 `enabled: true` 或 `false` 都一樣失敗。
- **回歸網會是紅的,而且應該是紅的**:`bold-can-be-turned-off-again` 紅著,
  直到這一格修好。

## 判準

`bold-can-be-turned-off-again`(`tools/run_e2_c_product_path.py`)。
今天它紅在第一次按下去就失敗;修好之後,它要求的是**按兩次之後引擎回報不是粗體**。
