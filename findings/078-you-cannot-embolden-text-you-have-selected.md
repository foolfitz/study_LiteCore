# 078 — 選起來的文字不能變粗體，而回歸網全綠，因為它問清單該測什麼

| | |
|---|---|
| **狀態** | **確認**（使用者實測 ＋ 清單逐項核對），**未修** |
| **發現日** | 2026-08-23，使用者手動測 v5 預覽時 |
| **嚴重度** | **高**。這是文書編輯器最被預期的一個操作，而短期目標就是「能用的編輯器」 |
| **可重現** | 是，由契約決定，非間歇 |
| **是否上游** | **否。**二進位檔實作得出來，是我們的清單把它扣住 |

## 一句話

使用者選了一段文字、按下粗體，得到
`EDITOR_FORMAT_GESTURE_UNSUPPORTED：this action is not offered for this kind of
selection in this profile` ——**因為清單只在「游標沒有選取」時提供粗體**。

## 清單怎麼寫的（`dist/profiles/e2-editor-v5/sdk-manifest.json`）

```
set-bold            gestures = ["collapsed"]
set-italic          gestures = ["collapsed"]
set-underline       gestures = ["collapsed"]
set-strikethrough   gestures = ["collapsed"]

set-paragraph-heading  gestures = ["collapsed", "range-single", "range-cross"]
set-list-unordered     gestures = ["collapsed", "range-single", "range-cross"]
```

段落層的動作三種手勢都給，**四個內嵌格式只給游標**。所以這個編輯器現在只能
「先按粗體、再打字」，**不能把已經在文件裡的字變粗體**。

## 這不是疏漏，是這棵樹的紀律產生的副作用

理由寫在 `tools/build_e2_b_profile.py`，而且是對的：

> v1 actions … are caret-only in this contract: range dispatch was characterised
> for the paragraph actions, not for delete or insert, and **declaring a gesture
> nobody measured would be the manifest claiming coverage the evidence does not
> have.**

沒有人量過「一段選取上套粗體」，所以清單不宣稱它。**該這樣做。**

問題在下一步沒有發生：**「沒被特徵化」悄悄變成了「使用者不能用」，而沒有任何東西
在記這筆帳。**清單的誠實是對外的；對內它變成一個沒有人追蹤的產品缺口。

## 為什麼 38 項全綠還是漏掉它

回歸網**問清單該測什麼**。`format_arm` 用的是 collapsed caret，而 runner 自己的註解
就寫著原因：

> A collapsed caret: every one of the four is offered for `collapsed` and for
> nothing else, so this is the only gesture that can drive them.

**harness 知道這個限制，然後把它編進了自己的測試設計。**於是網子裡沒有任何一格在問
「我能不能把選起來的字變粗體」——因為清單說不能，而 harness 把清單當成正確的定義。

⇒ 這是 [[harness-path-vs-user-path]] 的一個新形狀：不是兩條路走的步驟不同，是
**harness 把產品自己的宣告當成了規格**。一個人花三十秒就撞到了。

## 處方：**不需要重新連結**

`tools/build_e2_editor_v4_profile.py` 的模組說明講得很清楚：

> a later profile can grant these **WITHOUT ANOTHER RELINK**, on the strength of
> a measurement.

二進位檔已經實作，是遮罩把它扣住的。所以工作是**量測**，不是連結：

1. 特徵化「range-single 上套四個內嵌格式」——套上去了嗎？範圍對嗎？跨段呢？
2. 量到了就在清單裡把 `range-single`（以及量到的話，`range-cross`）加上去。
3. 回歸網加一格**用選取**去套粗體的檢查，並且要有能讓它紅的突變。

順序不能反：先量再宣稱，這正是當初把它縮成 collapsed 的那條規矩。

## 沒有量的（因此不指認）

- **引擎在一段選取上到底做不做得對。**完全沒量過——這就是第 1 步。
- **四個內嵌格式是不是一樣。**只有粗體被人按過。
- **鍵盤路徑。**使用者按的是工具列按鈕；Ctrl+B 是否走同一條路沒有查。

## 附帶

這一格是**使用者一輪手動測試掉出來的第二個東西**（第一個是 finding 076 的雜訊被
確認看得見）。2026-08-22 那一輪也是一次手動測試撤掉了兩張 finding。
**人是唯一不共用我判讀工具的觀測者**，而這一次連清單都是我的判讀工具。
