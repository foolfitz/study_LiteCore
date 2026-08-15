# 第四輪的預測：把對抗性覆核打掉的三句話變成可量的臂

**寫在第四輪任何一次執行之前。** 承第一～三輪。
這一輪的臂**不是我想出來的**，是 codex 對抗性覆核指名要求的分離實驗，
外加它指出我證不足的地方。覆核全文留在
[`codex-review-round1-3.md`](codex-review-round1-3.md)。

## 覆核打掉了什麼（我核對過，三句都成立）

| 我寫的 | 覆核指出 | 我自己核對的結果 |
|---|---|---|
| 臂 G「**中間什麼都沒有派送**」，所以是提前 return 獨有的簽名 | 兩次之間有 **600 ms sleep、`getTextSelection()`、`getSelectionType()`、`SwTransferable` 建立**。「沒派送 uno 指令」是真的，「什麼都沒發生」是假的 | **成立**，`measureResetEnd` 確實這樣寫 |
| 臂 H 在**正常狀態**下「`START` 建的 mark 一直保留到 `END`」 | `R == S` 時 `START` 結束是收合的 mark，`EndSelect()` → `SttLeaveSelect()` 會 **`ClearMark()`**，`END` 才重建 | **成立**，`select.cxx:661`–`667`：`HasSelection()` 為假就落到 `ClearMark()`。**結論對、理由錯** |
| 這是我方要不要修的問題 | **上游自己的測試就保證了 `RESET`＋`END` 能建立選取**：`sw/qa/extras/tiledrendering/tiledrendering.cxx:151`「`// Next: test that LOK_SETTEXTSELECTION_RESET + LOK_SETTEXTSELECTION_END can be used to create a selection.`」並 `CPPUNIT_ASSERT` | **成立**，逐字核對過。所以我方序列合法，壞的是核心的狀態不變式 |

覆核另外指出的過度解讀（一併接受，不另設臂）：
臂 B 固定座標選到的字從 `"C-ISOLA"` 變 `"E1-LC-"`，那是**內容位移**不是「同一個有效範圍」；
臂 C 不是純 `.uno:SelectText`＋`RESET`，它還含前置 RESET、html 讀回、後置 RESET；
臂 F 同時做了三件事，指認不了旗標；
每一臂事後的 `.uno:SelectAll` **發生在失敗的那一次之後**，而依 Claim 2 那一次已經把狀態治好了，
所以它只證明事後可讀，**不證明失敗當下文件是好的**。

## 臂與預測

| 臂 | 做什麼 | **預測** | 它要分開什麼 |
|---|---|---|---|
| **AE** `twice-no-readback` | barrier → `RESET`+`END`（**不 sleep、不呼叫任何讀取**，只被動看回呼數）→ 立刻 `RESET`+`END` → 才讀 | **第一次 0 個回呼、第二次選得到** | 若成立，「治好它的」不是 readback 也不是等待 |
| **AF** `markless-reset-first` | barrier → `setTextSelection(RESET, x2, y)`（同一個直接 `SetCursor`，但**不呼叫 `EndSelect()`**）→ 正式 `RESET(x1)`+`END(x2)` → 讀 | **仍然選不到** | 若它反而救回來，就是游標／版面 priming，我對 Claim 2 的整個說法垮掉 |
| **AG** `endpoints-stuck` | barrier → `RESET(x0)`→`START(x1)`→`END(x2)`，**三個 x 互異**，記精確文字 | 選得到 | 端點語意 |
| **AH** `endpoints-clean` | 同 AG 但**不做 barrier** | **文字與 AG 逐字相同** | 修法在兩種狀態下語意一致 |
| **AI** `endpoints-reference` | 不做 barrier，`RESET(x1)`+`END(x2)` | **文字與 AG／AH 逐字相同** | 證明錨點是 `x1` 不是 `x0`——沒有它，AG＝AH 也可能兩邊一起錯 |
| **AJ** `reverse-stuck` | barrier → `RESET(x2)`→`START(x2)`→`END(x0)`（**反向**） | 選得到 | 覆核指出反向範圍沒測過 |
| **AK** `reverse-clean` | 同 AJ 但不做 barrier | **文字與 AJ 逐字相同** | 同上 |

第三輪當掉沒跑到的四臂（`.uno:InsertAnnotation`／`TrackChanges`／`AcceptTrackedChanges`／`Escape`）
一併重跑，並**把 `InsertAnnotation` 排到最後一個**——它是當掉的那一臂，
排最後才不會再把後面的臂一起帶走。

## 結局

**結局 A（預測命中）**：AE 第二次成功、AF 仍失敗、AG＝AH＝AI 逐字相同、AJ＝AK 逐字相同。
→ Claim 2 的鑑別力縮到「**`EndSelect()` 的副作用**」而不是「什麼都沒發生」，
Claim 3 的**結論**站得住（理由已改正），修法可以往下走。

**結局 B：AF 也救得回來。**
→ 治好它的是直接 `SetCursor` 或版面 priming，**不是 `EndSelect()`**。
Claim 2 撤回，機制重新開放，**不得改產品程式碼**。

**結局 C：AG≠AH，或 AG≠AI。**
→ `RESET`→`START`→`END` 在兩種狀態下語意不同，**不能當修法**，
退回 `.uno:GoLeft` 那條並把游標副作用寫進規格。

**結局 D：AJ≠AK。**
→ 反向範圍不安全，修法要限定方向或改別的做法。

**結局 E：AE 第一次就有回呼。**
→ 沒有 readback 時第一次反而成功，那前三輪的量測方式本身有時序問題，
**在查清楚之前不得引用 G。**

## 這一輪之後仍然沒有的

- **仍然沒有直接量到 `m_bInSelect`。** 覆核指出 `SwWrtShell::IsInSelect()` 是公開的
  （`sw/source/uibase/inc/wrtsh.hxx:154`），但那是 `sw` 模組內部標頭，
  **外部 LOK 探針拿不到**；要直接量就得寫成核心樹裡的 cppunit 測試並重編 `sw`，
  那是長時間編譯，**歸使用者**。這一輪只把外部可觀測的鑑別做到最緊。
- **仍然沒有在 WASM 上量。** 四輪都是原生。
