# 078 — 選起來的文字不能變粗體，而回歸網全綠，因為它問清單該測什麼

| | |
|---|---|
| **狀態** | **已修在 `e2-editor-v7`，使用者真滑鼠複驗通過；尚未出貨** |
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

## 處方：**不需要重新連結**（已由量測證實）

`tools/build_e2_editor_v4_profile.py` 的模組說明講得很清楚：

> a later profile can grant these **WITHOUT ANOTHER RELINK**, on the strength of
> a measurement.

二進位檔已經實作，是遮罩把它扣住的。所以工作是**量測**，不是連結：

1. 特徵化「range-single 上套四個內嵌格式」——套上去了嗎？範圍對嗎？跨段呢？
2. 量到了就在清單裡把 `range-single`（以及量到的話，`range-cross`）加上去。
3. 回歸網加一格**用選取**去套粗體的檢查，並且要有能讓它紅的突變。

順序不能反：先量再宣稱，這正是當初把它縮成 collapsed 的那條規矩。

## 特徵化結果（2026-08-23）：引擎兩種選取都做得對

量測在 `e2-inline-range` 上——**用出貨那顆逐位元相同的 loader／wasm／worker
（`f923cfa5…`）**，只有清單開了 range 手勢。**沒有重新連結**，這本身就證明了處方成立。

兩輪逐字相同：

| 臂 | 選取的字串 | 存出文件裡粗體的字串 | 判定 |
|---|---|---|---|
| 前置（什麼都沒按） | — | 文件裡沒有任何粗體 | 乾淨 |
| `range-single` | `1-LC-NUMBER-TW` | `1-LC-NUMBER-TW` | **一字不差** |
| `range-cross` | `␣␣␣␣␣1-LC-NUMBER-TWO\nE1-LC-END` | `1-LC-NUMBER-TWOE1-LC-END` | **一字不差**（去空白後） |
| 出貨 profile（對照） | 同樣的拖曳 | 沒有粗體，兩臂都被拒 | **擋住的是遮罩** |

`range-cross` 上那個**被完整選取**的第二段，回來的是**段落層**粗體而不是 span。
視覺相同；但之後打進那一段的字會繼承，而**這是否與原生 LibreOffice 一致沒有查**。

## 這一段先產生了兩個錯的結論，兩個都是我的判讀工具

**兩個都留在證據裡**，因為它們是這一段最有價值的部分。

**錯誤一：「粗體會把兩個不相干的清單段落整段變粗體。」**段落樣式的正則要找
`</style:style>` 才收尾，而那兩段用的是**自閉合**的樣式元素、完全沒有 text-properties
——正則於是一路吃過去，把**後面某個文字樣式**的 `fo:font-weight="bold"` 算到它頭上。
**兩輪逐格相同**，也就是一個**穩定的**錯誤，而穩定的錯誤看起來完全像一個真實的發現。
抓到它的是「把樣式自己的原始標記放進證據」；**沒有**抓到它的是我的單元測試——
因為測試資料是我自己編的，裡面沒有自閉合樣式。**測試只證明了它在我想得到的形狀上對。**

**錯誤二：「`range-cross` 少套了四分之一。」**判準拿引擎回報的選取**長度**（30）
去比粗體**字數**（24）。兩個數字都對，錯的是這個比法：引擎的選取字串在**跨段時**
多帶 5 個字元的**清單前綴**，再加一個 `\n` 分隔——兩者都不是文件內容。
30 − 5 − 1 = 24，剛好。fixture 裡那一段是 `E1-LC-NUMBER-TWO`，**沒有**前導空白，
這是前綴被指認出來的方式。

判準因此改成**比字串**，不是比數字。**字串不會被前綴騙。**

## 處方最後長這樣：兩個 range 手勢**都**開（2026-08-23）

原本的計畫（也是外部裁決的第一版）是「只開 `range-single`、扣住 `range-cross`」。
**建不出來**：引擎對一個**還沒分類**的選取要求**兩個 range 位元都在**，因為要分辨
single 與 cross 得做 HTML 讀取，而那是 findings 037／038 的引擎卡死風險——那個關卡
刻意保守。三顆 profile 量出來的：

| profile | 開了什麼 | 一行之內的拖曳 |
|---|---|---|
| `e2-inline-range` | single ＋ cross | 套上，文字相等 |
| **`e2-editor-v6`** | **只有 single** | **被拒** |
| `e2-cross-only` | 只有 cross | 被拒 |

⇒ **只開一個等於什麼都沒開。**而在 AND 語意之下，「扣住 cross」的清單等於對一個
**可量測地做得到**的二進位檔宣稱「不支援選取」——那正是當初那條誠實規矩的反面。
這個 schema 限制已寫進 `e2/expected-gesture-offers.json` 的 `andSemantics`。

### 開放前到期的三個條件，全部完成

1. **原生比對**（本來可以等，開放之後變成阻擋）。`tools/f078_native_range_format.cpp`：
   **整段被選 → 段落層粗體、沒有 span；只選一部分 → span**，範圍相同。
   **跟 WASM 引擎寫出來的一模一樣**，連要記進 limits 的分歧都沒有。
2. **在鑄出來的身分自己身上重跑**。`e2-editor-v7`：四個格式 × 兩種選取**八格全部
   文字相等**；產品路徑 **36 PASS / 3 NOT_ESTABLISHED / `ok: true`**，比 v4 多一格。
   先前所有「正確」的量測都在**診斷** profile 上取——移植論證是好的，但不接受它當
   出貨的宣稱。
3. **使用者真滑鼠複驗**：**2026-08-23 通過，四個樣式按鈕都可用。**
   這是這棵樹認的結案標準——harness 綠不算結案，因為 harness 走的不是使用者那條路。

### 回歸網那一格

`an-inline-format-reaches-a-selection`，突變 `format-ignores-a-selection` 把它從
PASS 打成 FAIL。**具名弱點**：波及範圍大，所以它證明的是「這格能紅」，不是「只有它
會注意到」。更緊的突變試過而且**什麼都沒發生**——那買到了 **finding 079**。

## 沒有量的（因此不指認）

- ~~**引擎在一段選取上到底做不做得對。**~~ 已量：兩種選取都對（見上）。
- **只量了粗體。**斜體、底線、刪除線一次都沒跑過。
- **只有一份 fixture、每臂一種選取幾何、只有 Chrome。**
- **拖曳是合成的 PointerEvent，不是真的滑鼠。**
- **那 5 個字元的清單前綴沒有解釋。**只在跨段選取時出現。finding 074 談的是同一顆
  引擎把「第一個屬性 run」當成清單前綴——**是不是同一個機制沒有問過**。
- **回歸網還沒有任何一格用選取去套格式**，也就沒有能讓它紅的突變。
- **鍵盤路徑。**使用者按的是工具列按鈕；Ctrl+B 是否走同一條路沒有查。

## 附帶

這一格是**使用者一輪手動測試掉出來的第二個東西**（第一個是 finding 076 的雜訊被
確認看得見）。2026-08-22 那一輪也是一次手動測試撤掉了兩張 finding。
**人是唯一不共用我判讀工具的觀測者**，而這一次連清單都是我的判讀工具。

## 證據

- `findings/evidence/f078-inline-format-on-a-selection/`（兩輪量測、出貨對照、
  以及**產生過兩個錯誤結論的那一輪**）
