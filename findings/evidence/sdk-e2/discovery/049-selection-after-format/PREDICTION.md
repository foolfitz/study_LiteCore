# 預測：格式動作之後選不到東西，是 `m_bInSelect` 沒有被關掉

**寫在任何一次執行之前。** 任務 #49。
提交時間見這一份的 commit；量測的輸出在同目錄的 `native/`。

## 這一份要回答什麼

P2 量到：同一顆 artifact、同一份文件、同一組座標，
**做過一次格式動作之後**，範圍選取回報 `none`、空字串（產品路徑 251 ms 的 bounded readback）；
**不先做格式動作**的同一個選取，20 ms 選到 `"moji 😀 graphe"`。
[P2 的證據](../039-combination/p2-composition-scan-ba1a5dd5/README.md)。

「為什麼」當時沒有答案。這一份提出一個**原始碼層讀出來的機制**，
並且**在量之前**寫下它預測每一臂會看到什麼。

## 機制（目前只是推論，還沒有量到）

引擎的範圍選取送的是 **`RESET` ＋ `END`，沒有 `START`**
（`wasm_sdk_probe/src/probe_engine.cpp:3805`–`3812`，`text-handles-unstable`）。

核心那邊（`libreoffice-26-8`，`coreCommit 671c848b`）：

| # | 呼叫 | 檔案：行 | 做了什麼 |
|---|---|---|---|
| 1 | barrier 的 `.uno:SelectText` | `sw/sdi/swriter.sdi:5649` → `FN_SELECT_PARA` | `sw/source/uibase/shells/textsh1.cxx:1975`：`SttPara()` 之後 `EndPara(true)` |
| 2 | `EndPara(true)` | `sw/source/uibase/wrtsh/move.cxx:402` | `ShellMoveCursor(this, true)` → `MoveCursor(true)` |
| 3 | `MoveCursor(true)` | `move.cxx:84` | 呼叫 `SttSelect()` |
| 4 | `SttSelect()` | `sw/source/uibase/wrtsh/select.cxx:407` | **設 `m_bInSelect = true`**。`FN_SELECT_PARA` 這條路徑**沒有任何地方呼叫 `EndSelect()`**——`ShellMoveCursor` 的解構子只做 `StartAllAction`／`EndAllAction` |
| 5 | barrier 的還原 `setTextSelection(RESET)` | `sw/source/uibase/docvw/edtwin.cxx:7105` | `bClearMark` 為真 → `ClearMark()`；**`bCreateSelection` 維持 false**，所以 `SttSelect()`／`EndSelect()` 兩個都不會被呼叫。`m_bInSelect` **仍然是 true** |
| 6 | 呼叫端的 `RESET` | 同上 | 同上，`m_bInSelect` 仍然 true |
| 7 | 呼叫端的 `END` | `edtwin.cxx:7107`–`7111` | `HasMark()` 為 false → `bCreateSelection = true` → 呼叫 `SttSelect()` |
| 8 | `SttSelect()` 這一次 | `select.cxx:409` | **`if (m_bInSelect) return;`——直接返回，`SetMark()` 從來沒有執行** |

沒有 mark 就沒有選取範圍，第 7 步的 `SetCursor()` 只是把游標移過去。
`getTextSelection` 因此回空字串，`LOK_CALLBACK_TEXT_SELECTION` 也不會廣播
（選取確實沒有改變），於是 discovery 那條等回呼等到逾時、
產品那條在 250 ms 的 bounded readback 期限誠實回報「沒選到」。

**關掉 `m_bInSelect` 的已知路徑**：`EnterStdMode()`（`select.cxx:584`）。

> **這一整段是推論，不是量測。** 上一輪有四句同樣形狀的話被對抗性覆核打掉，
> 理由都是「原始碼看起來會這樣」不等於「它就是這樣」。所以下面每一臂都要真的跑。

## 臂與預測

原生 LOK，`test-docs/e1/list-contexts.odt`，同一份文件、同一組座標。
每一臂結尾都是同一件事：`setTextSelection(RESET, x1,y1)` → `setTextSelection(END, x2,y2)`
→ `getTextSelection("text/plain;charset=utf-8")`，並記 `LOK_CALLBACK_TEXT_SELECTION` 次數。

| 臂 | 範圍選取**之前**做什麼 | **預測** |
|---|---|---|
| **A** `control` | 什麼都不做 | **選得到文字** |
| **B** `format-only` | 只派送 `.uno:DefaultBullet`（barrier 用的同一組參數） | **選得到文字**——格式指令本身不動 `m_bInSelect` |
| **C** `select-text-only` | 只派送 `.uno:SelectText`，然後 `RESET` 回原位 | **選不到（空字串）** |
| **D** `full-barrier` | `.uno:DefaultBullet` → `.uno:SelectText` → `RESET` → `getTextSelection(html)` → `RESET`，也就是 barrier 的完整形狀 | **選不到（空字串）** |
| **E** `full-barrier + escape` | 同 D，最後多派送一次 `.uno:Escape`（`SID_ESCAPE` → `EnterStdMode`） | ~~**選得到文字**~~ → **改判為「選不到」，見下面的修訂** |
| **F** `full-barrier + go-left` | 同 D，最後多派送一次 `.uno:GoLeft` | **選得到文字**（本次新增） |

### 修訂（2026-08-15，**仍在任何一次執行之前**）

上面那一列 `commit a272f74` 寫的是「臂 E 選得到」，理由是 `.uno:Escape` 會走到
`EnterStdMode()`。**那個前提在寫探針時被讀壞了，所以在跑之前先改。**

`FN_ESCAPE`（`sw/sdi/swriter.sdi:1181`）的處理在
`sw/source/uibase/uiview/view2.cxx:1220`，而 `EnterStdMode()` 只在
**`else if (m_pWrtShell->HasSelection() || IsDrawMode())`**（`:1232`）這一支裡被呼叫（`:1251`）。
barrier 還原完剛好**沒有**選取——那正是還原的目的——所以它會一路掉到最後一支去切換
`SID_WIN_FULLSCREEN`，`m_bInSelect` 原封不動。

**臂 E 的新預測：選不到，與 D 相同。** 保留這一臂不刪，因為它是原判斷的驗證。

新增的 **臂 F** 用 `.uno:GoLeft`（`sw/sdi/swriter.sdi:1467` → `FN_CHAR_LEFT`
→ `SwWrtShell::Left(…, bSelect=false, …)` → `ShellMoveCursor(this, false)`
→ `MoveCursor(false)` → **`EndSelect()`**，`move.cxx:87`）。
它移動一格游標，但 barrier 的還原本來就會把游標放回去，所以副作用可以吸收。

> 這條修訂本身是**第二次**同一形狀的錯：原始碼看起來會走到某個分支，不等於它會走到。
> 上一輪四句被打掉的話也是這樣來的。差別只在這次是在執行之前自己抓到的。

## 結局，以及各自的處置

**結局 A（預測命中）：C、D、E 為空，A、B、F 有文字。**
→ 機制成立：起因是 `.uno:SelectText` 留下的 `m_bInSelect`，**與格式指令無關**
（B 通過就是這句話的憑據）。處置：barrier 收尾補一次 `EnterStdMode` 等效的派送，
重連結**組合** artifact（`e2-combination`，**不是**任何凍結的），重測 P2 那三臂。
另外開一份 finding 記上游那一半。

**結局 B：四臂都選得到。**
→ 原生與 WASM 不一致，機制不是（或不只是）這個。處置：**不改任何程式碼**，
把差異本身當成新的問題，回去做瀏覽器端的鑑別 sweep。

**結局 C：C 選得到但 D 選不到。**
→ 格式指令是必要的共同條件，我的推論不完整。處置：把 D 再拆成
「格式 → SelectText → 選取」與「SelectText → 格式 → 選取」兩臂，先分清楚順序。

**結局 D：F 也選不到。**
→ 連 `MoveCursor(false)` 都關不掉它，我對 `m_bInSelect` 的整條推論就有問題
（或者旗標不是唯一的必要條件）。處置：改用直接讀狀態的方式重問一次
（原生可以在每一步之間呼叫 `getSelectionType()`／看 `HasSelection`），
**先確定壞在哪一步再想修法**；若我方確實無路可走，這件事就只剩上游能修，
**縮限 4 變成永久性的**，E2-B 的範圍要照這個重寫。

**結局 E：A 或 B 為空。**
→ 探針自己就選不到，這一輪什麼都沒證明。處置：先修探針，
**在修好之前不得引用任何一臂的數字**。

## 這一份不宣稱

- **不宣稱這是 WASM 才有的**——原生跑出來的結果只描述原生。
  要說 WASM 上也是同一回事，得回去在 artifact 上量。
- **不宣稱 `.uno:Escape` 是對的修法**，只宣稱它能不能把 `m_bInSelect` 關掉。
  真正要送出去的修法還要過 A3／A4／A5 重掃。
- **不宣稱上游會同意這是缺陷**。`SwEditWin::SetCursorTwipPosition` 先算
  `bCreateSelection = !HasMark()` 再呼叫可能靜默返回的 `SttSelect()`，
  這個內部不一致值得回報，但那是另一份文件的事。
