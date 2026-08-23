# 080 — 一個檢查棄權了兩天，而它自己寫下的棄權理由指錯了對象：它怪 harness，實際上是它正在檢查的那個頁面壞了

| | |
|---|---|
| **狀態** | **已確認並已修**；但改好之後的那格檢查**其綠不足以背書中止接線**，見末節 |
| **發現日** | 2026-08-23，在修 finding 079 的路上掉出來 |
| **嚴重度** | **中**：一個永遠 NOT_ESTABLISHED 的檢查看起來像「還沒做好」，實際上是「它要檢查的東西壞了，而它有能力說出來卻沒說」 |
| **可重現** | 是，結構性的，不是間歇 |
| **是否上游** | **否，是我們自己的回歸網** |

## 一句話

`an-aborted-gesture-stops-selecting` 問「有沒有選到一段？」的方式是問
「那四個樣式按鈕是不是灰的？」——而那四個按鈕會不會變灰，取決於
`lastSelectionShape`，也就是 **finding 079 壞掉的那個值**。
於是它的正向對照永遠不成立，檢查永遠棄權，而棄權的宣告把原因寫成了
「這個 harness 拖不出會延伸的選取」。

## 兩層原因疊在一起，而且是先後發生的

| 時間 | 原因 | 效果 |
|---|---|---|
| 2026-08-21 起 | **finding 079**：`lastSelectionShape` 每次拖曳後都算成 `collapsed` | 四個樣式按鈕（當時只提供給 `collapsed`）永遠不會變灰 ⇒ 對照永遠 false |
| 2026-08-23 起 | **`e2-editor-v7` 出貨**：四個樣式按鈕改成三種手勢都提供 | 就算 079 修好，它們**還是**永遠不會變灰 ⇒ 對照永遠 false |

第二層是**清單放寬把一個檢查靜默地拆了**。這值得單獨記著：這棵樹已經有
「harness 把產品自己的宣告當成規格」的教訓（finding 078），而這是**同一件事的反面**
——harness 把**宣告的窄**當成儀器，於是**放寬宣告就是拆儀器**，而且沒有任何東西會叫。

## 宣告本身是錯的，而它的最後一句話就寫著正解

`MUTATIONS["gesture-abort-not-wired"]` 上掛著 `expectedToBeDetected: False`，
理由原文（2026-08-21）：

> the check's positive control cannot start an extending drag through this
> harness … The observable, not the gesture, is what is missing: copy and cut DO
> produce a range at their own named line, so the next step is a direct
> selection observable (the copy path reports codePoints) rather than reading
> button.disabled.

**前半句是錯的。**這個 harness 拖得出來。用**同一支 `DRAG`**、同樣的座標推導，
2026-08-23 量到：一行之內 12 個碼點，跨兩行 34 個碼點，直接來自引擎的複製路徑
（`tools/probe_079_selection_shape.py`）。手勢從來沒有問題。

**後半句是對的**，而且它就是正解——只是被寫在一個把責任推給 harness 的句子後面，
所以看起來像「未來的改進」而不是「現在就在騙人的東西」。

## 教訓：棄權的理由要能被否證，否則它會替缺陷擋一年

`NOT_ESTABLISHED` 是這棵樹用來分辨「前提沒到」與「產品壞了」的機制，它是對的。
但這一次前提沒到**正是因為產品壞了**，而檢查有能力看見那件事——它只是透過一個
被同一個缺陷污染的代理去看。

⇒ **一個檢查長期棄權，要當成「它想量的那件事壞了」的假說去查，不是當成待辦事項。**
這裡的成本是兩天，而 079 在那兩天裡對每一個使用者的每一次拖曳都成立。

順帶，**它寫下自己的理由這件事救了它**。理由裡那句「copy and cut DO produce a
range」是可否證的宣稱，一量就翻。若當時只寫「這個檢查還不能用」，就沒有東西可以查。

## 修法

觀測改成問頁面自己：`#toolbar[data-selection-shape]`，由
`updateGestureAffordance()` 每次更新時寫上。

這個讀法**不隨 manifest 提供什麼而變**，所以下一次放寬手勢不會再拆掉它——
上面第二層那個原因被結構性地移除，而不是這次修好而已。

同時 `format_buttons_disabled()` 這個函式名改成 `a_range_is_selected()`，
報告欄位 `formatButtonsDisabled*` 改成 `aRangeIsSelected*`：
**名字要說它現在量的是什麼**，否則下一個人會再從按鈕去推一次。

## 換上觀測量之後第一次紅，而那個紅是判準自己（2026-08-23）

改瞄準之後它**史上第一次說了話**：control 為真、**兩個中止臂也為真**，FAIL。

那個紅不是產品。`ABORT_DRAG` 在中止**之前**先動了一次，所以「起點到那個中點」的選取
在**每一個臂上都是正確行為**——中止要擋的是**下一次**移動，不是收回上一次。
⇒ **「存在一段選取」在接線好與壞的世界裡都為真**，而那正是這格要分開的兩件事。
判準因此改成**範圍**：中止臂的選取文字必須是 control 的**嚴格前綴**。

改完之後：clean 過（control 11 碼點、兩個中止臂各 10），
`gesture-abort-not-wired` 突變之下紅（control 6、pointercancel 0、blur 3）。
於是 `expectedToBeDetected` 由 `False` 翻成 `True`——**偵測到是事實**。

### 三個數字沒有解釋，而外部裁決指出最大的那個不是我列的那些

裁決說：**先解釋 control 為什麼不可重複**（一輪 11 碼點、一輪 6 碼點），
在那之前任何 margin 都繼承那個雜訊。它是對的，而且答案很難看。

**每一個臂各自呼叫一次 `stable_bands`，各自取「第一個寬於 40px 的帶」。**
那個掃描在這顆 core 上是間歇的（finding 075）。⇒ **各臂瞄的是不同的行。**

只有把**選到的文字**放進紀錄旁邊才看得出來：

| 臂 | 選到 |
|---|---|
| control | `1-LC-H`，帶 `[83,182]` |
| pointercancel | `E1-LC-ISOL` |
| blur | `E1-LC-ISOL` |

**不同的字串、不同的行，根本不可能有前綴關係。**
這一個原因解釋了這格產生過的**每一個**莫名數字——包括**它 PASS 的那一輪是矇到的**。

### 修法三步，每一步都是被一次紅買出來的

1. **瞄準點只推導一次**，四個臂共用——這才讓它們可比。
2. 可比之後，弱判準（嚴格前綴）就沒有藉口了：加第四個 **reference 臂**，
   跑同樣的移動、停在其他臂中止的那一點。**期望值是跑出來的，不是從像素推的**
   ——字是比例寬度，像素換字元會是整條鏈最弱的一環。
3. 第一次跑共用瞄準點又不夠解析（control 只選到 `E1` 兩個字，reference 在一半處
   選到空字串），於是把瞄準點從「第一個 >40px 的帶的一半」改成
   **最寬那條帶的 90%**。

### 三步做完之後量到的（出貨頁面）

| 臂 | 選到 |
|---|---|
| control（不中止） | `E1-LC-ISOLATED 前後都不是清單的` |
| reference（停在中止點） | `E1-LC-ISOLAT` |
| pointercancel | `E1-LC-ISOLAT` |
| blur | `E1-LC-ISOLAT` |

兩個中止臂**逐字等於** reference，margin 是 14 對 9。PASS。

**而突變之下，這一次是照 oracle 說的那個方式紅的：**

| 臂 | 選到 |
|---|---|
| control | `E1-LC-ISOLATED 前後都不是清單的` |
| reference | `E1-LC-ISOLAT` |
| **pointercancel（被拆掉）** | **`E1-LC-ISOLATED 前後都不是清單的`** ← 一路跟到底 |
| blur（還接著） | `E1-LC-ISOLAT` ← 正確 |

**同一輪、同一行，一個接線被拆掉、一個還在，兩者被分開了。**
這正是 oracle 自己那句話。先前那次偵測是紅在空字串的守衛上，那是另一個性質。

### 還欠的（因此佇列項不關）

**每個方向都只有一輪。**這格已經在單輪上給過三個有信心而且錯的答案。
`queue-abort-margins-are-unexplained` 要求 **N 輪連續**才准有人寫下
「pointercancel 與 blur 的接線已驗證」。另外，讀取仍然是靠牆鐘 sleep 同步，
而不是用信封本來就帶著的 `revision`／`callbackSequence`。

## 全網清點過了（2026-08-23）

把 `run_e2_c_product_path.py` 裡所有讀 `button.disabled` 的地方清一遍，
真正拿它去**下判定**的只有兩處：

1. `an-aborted-gesture-stops-selecting` —— 本單，已修。
2. finding 078 那個臂的 `buttonAfterDrag` 前提守衛（「拖出來的形狀這個 profile
   沒提供，所以沒得量」）。在 `e2-editor-v7` 上四個樣式按鈕三種手勢全提供，
   **這個守衛從此永遠不會成立**。它不會造成假綠（守衛失效只會讓檢查更常真的跑），
   但它已經**分辨不出「拖曳做出了沒提供的形狀」**了。旁邊新加的
   `the-page-agrees-with-the-engine-about-the-selection` 蓋住了這個缺口。

其餘兩處（`notice-action-recovers-the-session` 讀通知按鈕自己的 `disabled`、
格式臂把 `buttonOffered` 記進 observed）**不進判定式**，是觀測不是代理。

## 沒有量的（因此不指認）

- **`e2-c-d*` 那些 harness 頁面沒有清點。**只清了產品路徑這一支。
- **中止發生在其他時刻的情形沒有涵蓋。**`ABORT_DRAG` 在中止前固定移動一次，
  所以「在第一次移動當中就中止」「移動好幾次之後才中止」都沒有被量。
- **`stable_bands` 為什麼會間歇**沒有查。這一單只是不再讓它污染比較
  （瞄準點只推導一次），沒有解釋它。

