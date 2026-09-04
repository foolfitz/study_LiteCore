# 088 — 結構投影每次快照都整棵重建，於是螢幕閱讀器把每一段唸三遍

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | 不送出——`web/e2-editor-app.js`，我方 |
| **發現日** | 2026-09-05 |
| **嚴重度** | 一般（可用性；不擋 cutover，見「對閘門的意涵」） |
| **可重現** | 1/1，而且是逐句可數的 |
| **是否上游** | 否 |

## 現象

**由擁有者用耳朵發現。**在 087 修好之後的 Orca 走查中，他說「清單部份好像有重複的
地方？它是念 living list 嗎？」——那是 `leaving list`（離開清單）。

十段的文件、九次方向鍵，Orca 說了：

| | 次數 | 文件裡實際有幾個 |
|---|---|---|
| 每一段的文字 | **2–6 次**（多數 3 次） | 各 1 |
| `leaving list` | **9** | — |
| `List with 2 items` | **10** | 2 個清單 |
| `文件內容`（區域標籤） | **7** | 1 |
| `Browse mode` | **6** | — |

一秒之內的實際樣子：

```
00:43:48  List with 2 items
00:43:48  1. 編號的部分開始 這裡應該被唸成編號清單的第一項.
00:43:49  leaving list.
00:43:49  List with 2 items
00:43:49  1. 編號的部分開始 這裡應該被唸成編號清單的第一項.
00:43:49  leaving list.
00:43:49  List with 2 items
00:43:49  1. 編號的部分開始 這裡應該被唸成編號清單的第一項.
```

## 分析

`projectStructure()` 在每一次快照都無條件重建整棵子樹
（`e2-editor-app.js:291`，`el.a11yStructure.replaceChildren(fragment)`），而
`updateState()` 每一次狀態更新都呼叫它。所以清單容器、清單項目、以及
`aria-activedescendant` 指向的那個節點，每次都是**新的 DOM 節點**。AT 因此看到
「清單消失、清單出現」並重新報讀。

**產品自己已經知道這個道理，只是沒套用到結構那一半。**即時區域有守衛
（`e2-editor-app.js:176`）：

```js
// updateState runs on every snapshot, and reassigning the same string would be
// a repeat announcement of a paragraph the user is still sitting in
if (el.a11yPara.textContent !== next) el.a11yPara.textContent = next;
```

同一個檔案、同一個函式家族、同一個理由——結構那一半沒有。

## 它為什麼現在才被聽見

**在 087 修好之前沒有任何東西指進那棵子樹**，AT 不會去讀它，所以重建是靜默的浪費。
087 的修法（`aria-activedescendant` 從 sink 指進結構節點）把 AT 的注意力接了進去，
於是那個一直存在的重建變成聽得見的。

**這是修法暴露的，不是修法造成的。**分清楚這件事要緊：回退 087 會讓噪音消失，
也會讓標題重新變成沒有結構的純文字。

## 對閘門的意涵

**不擋 cutover。**4b 的機械（擋門）那半問兩件事——焦點所到之處的段落文字有沒有進
log、標題有沒有被當成標題連層級一起唸——**兩者在同一份 log 裡都成立**
（`heading 1`、`heading 2`、`List with 2 items` 都在）。重複屬於「報讀順序、囉嗦
程度」，那是判準明文歸給**判斷那半、只做記錄**的。

**但它必須寫進 cutover 記錄**，因為擁有者要確認的正是那 ＋24.5 MiB 買到什麼，而
「每一段唸三遍」是使用者真的會遇到的東西。

## 修法方向（未實作、未量測）

把即時區域那條守衛的想法套到結構那一半：只有在投影**內容真的改變**時才重建，
其餘時候只更新 `aria-activedescendant`。

**未量測的部分要先講**：不知道「保留節點、只換 activedescendant」會不會讓 Orca 只
報一次；也不知道 `List with 2 items` 的重複是節點重建造成的，還是 Orca 每次
activedescendant 跨越清單邊界就會重報。**兩者要分開量**——那正是 087 那一輪
（把角色放在即時區域上沒用）的教訓：直覺的機制要先量再信。

## 證據

- `evidence/087/orca-after-fix-2.log`（5,323,841 bytes）
- `evidence/087/TRANSCRIPT-after-fix.md`（逐字稿）
- `evidence/087/4b-arrow-walk-after-fix.json`（九次方向鍵、十段的指標記錄）
