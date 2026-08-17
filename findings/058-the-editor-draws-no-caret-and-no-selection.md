# 058 — 產品編輯器**不畫游標,也不畫選取**:使用者是盲打的

| | |
|---|---|
| **狀態** | **已確認（截圖,2026-08-17)／未修** |
| **Bugzilla** | —（**不是上游缺陷**——我方頁面沒有畫） |
| **發現日** | 2026-08-17（短期目標盤點,外部審查 fable 指出方向,截圖證實） |
| **嚴重度** | **阻斷**——對「能用的編輯器」這個目標而言,這是**第一順位**;點了不知道點到哪,拖了不知道選到哪 |
| **可重現** | 100%（Firefox,殼層 v14,artifact `d538ce0b`) |
| **是否上游** | **否** |

## 現象

放好游標(引擎回報 `定位游標 30 ms`、state `ready`)之後,**畫面上沒有任何游標**。
拖曳選取一整行之後,**沒有任何反白**。三張截圖在
[`evidence/058/`](evidence/058/),文件區域**逐像素看起來一樣**。

- [`01-before-click.png`](evidence/058/01-before-click.png)
- [`02-after-click-caret-placed.png`](evidence/058/02-after-click-caret-placed.png)
- [`03-after-drag-selection.png`](evidence/058/03-after-drag-selection.png)

## 機制:資料都送到了,頁面沒有畫

**不是引擎沒給。** worker 的產品投影同時送出兩樣東西
（`sdk/sdk-worker.js:247-254`)：

```js
caret: value.caret ?? null,
selection: value.selection ?? { observed, collapsed, start, end, rectangles: [] },
```

而產品頁對它們只做一件事——**數數量**,用來判斷手勢形狀
（`web/e2-editor-app.js:286`)：

```js
lastSelectionShape = (result?.rectangles?.length ?? 0) > 1 ? ... : ...
```

頁面**唯一**的繪圖是把 tile 貼上去（`web/e2-editor-app.js:165` 的
`putImageData`)。全檔沒有 `fillRect`／`strokeRect`／任何 overlay。

LOK 的慣例是**游標與選取不畫進 tile**——它們以回呼矩形交給客戶端自己畫。
所以 tile 是對的,少的是客戶端那一步。

## 為什麼到今天才發現

**因為沒有人「看」過它。** 這棵樹所有自動化都從 DOM 與存檔的 ODT 判讀:
`placeCaret` 有沒有確認、revision 有沒有動、存出來的位元組對不對。
**那些全部可以在完全不畫任何東西的頁面上通過。** 產品路徑回歸網九格全綠,
而使用者看不到游標。

這是 [[harness-path-vs-user-path]] 的again,但更深一層:前三次(049／050／Ctrl+C)
是「按鈕沒人按過」,這一次是**「畫面沒人看過」**。截圖不在任何一格檢查裡。

D5 人工輪有真人,而且過了四格——**但沒有一格的判準是「你看得到游標嗎」**,
所以那不算反證。

## 後果

- 「能讀檔、能基本編輯的編輯器」這個短期目標,**這一格沒補起來之前其他都是次要的**。
- finding 046 修法給的新訊息叫使用者「看一下結果」——**他看不到游標在哪。**
- 拖曳選取之後按格式鈕,使用者無從確認選到的是不是他要的那段。

## 修法方向（**未實作,未量測**)

資料已經在 `productEditorState` 裡,所以這是**純殼層**:在 tile 之上疊一層畫
caret 矩形與 selection 矩形。需要注意的是座標換算(twips → CSS 像素,頁面已有
`pointToTwips` 的反向)與重繪時機。

**不承諾這是唯一或最好的做法**,也還沒量過畫上去之後是否與 tile 對齊。

## 判準

要能被證明會失敗:一格截圖比對——放好游標之後的畫面**必須**與放之前不同。
今天它是相同的。
