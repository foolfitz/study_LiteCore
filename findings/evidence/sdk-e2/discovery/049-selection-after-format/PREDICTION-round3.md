# 第三輪的預測：**引擎派送的每一個 uno 指令**，哪些會毒化下一個選取

**寫在第三輪任何一次執行之前。** 承
[第一輪](native-round1/README.md)（起因是 `.uno:SelectText`）與
[第二輪](native-round2/README.md)（機制指認：失敗的那一次自己燒掉旗標）。

## 為什麼要有這一輪

前兩輪只問了 `.uno:SelectText`。但它會壞是因為
**`FN_SELECT_PARA` 呼叫了 `SttSelect()` 而沒有配對的 `EndSelect()`**——
那是一個**通用形狀**，不是那一個指令的特性。任何同樣不配對的指令都會有同樣的後果。

同一份原始碼裡的搜尋**有配對**：`sw/source/uibase/uiview/viewsrch.cxx:773`
的 `m_pWrtShell->SttSelect();` 對上 `:846` 的 `m_pWrtShell->EndSelect();`。
所以 `FN_SELECT_PARA` 是例外，不是常態——**但這只證明搜尋是好的，
不證明其他二十個是好的。**

**還有一個實務理由**：`.uno:Undo` 是**今天剛接上 `demo-structure` 復原鈕**的那條路
（任務 #50）。如果它會毒化選取，那顆按鈕就是我自己裝上去的地雷。

## 受測清單

引擎在 `probe_engine.cpp` 裡派送的全部 uno 指令（`grep` 出來的 22 個），
扣掉純檢視與需要額外前置狀態的，逐一測：

`.uno:SelectText`（正對照，預期會壞）、`.uno:ExecuteSearch`、`.uno:Undo`、`.uno:Redo`、
`.uno:Bold`、`.uno:Italic`、`.uno:Underline`、`.uno:Strikeout`、
`.uno:DefaultBullet`、`.uno:DefaultNumbering`、`.uno:RemoveBullets`、`.uno:StyleApply`、
`.uno:Delete`、`.uno:SwBackspace`、`.uno:InsertPara`、`.uno:InsertLinebreak`、
`.uno:InsertAnnotation`、`.uno:TrackChanges`、`.uno:AcceptTrackedChanges`、
`.uno:Escape`

每一臂：放游標 → **派送該指令** → `RESET` 回原位 → `RESET`＋`END` 範圍選取 →
`getTextSelection`。再加一臂**什麼都不派送**當負對照。

### 判準用第二輪 G 臂的雙次量測，不是「選不到就算毒化」

**寫探針時發現單次量測分不出兩件事**（所以在跑之前先改）：
`.uno:InsertPara` 會把段落切開，`.uno:Delete`／`.uno:SwBackspace` 會改字，
於是同一組座標**可能本來就沒有字了**——那也會回空字串，讀起來和「狀態被毒化」一模一樣。

所以每一個第三輪的臂都**連選兩次**，判準是：

| attempt1 | attempt2 | 判為 |
|---|---|---|
| 空 | **選得到** | **毒化**——失敗的那一次自己燒掉了旗標，這是第二輪指認過的簽名 |
| 空 | 空 | **不是毒化**，是那個座標沒有字可選（該指令改動了內容或版面） |
| 選得到 | — | 乾淨 |

這一格是**單次量測讀不出來的**，補在執行之前。

## 預測

| | 預測 | 理由 |
|---|---|---|
| `.uno:SelectText` | **毒化**（選不到） | 前兩輪已量到 |
| `.uno:ExecuteSearch` | **不毒化** | `viewsrch.cxx:773`／`:846` 有配對 |
| **其餘全部** | **不毒化** | 沒有讀到它們呼叫 `SttSelect()`——**但這是「沒讀到」，不是「讀過確定沒有」**，所以才要跑 |
| 什麼都不派送（負對照） | **不毒化** | 沒有它，「大部分不毒化」可能只是這一輪的量測方式壞掉 |

**這一輪的價值在「有沒有第二個」。** 只有 `.uno:SelectText` 中，
那 finding 的範圍就是 barrier 一處；**多一個中，範圍就完全不同**，
而且如果中的是 `.uno:Undo`，任務 #50 那顆按鈕要跟著處理。

## 結局

**結局 A：只有 `.uno:SelectText` 毒化，負對照乾淨。**
→ 範圍確定，修法照第二輪的 `RESET`→`START`→`END`，
上游那份 finding 就寫 `FN_SELECT_PARA` 一處。

**結局 B：`.uno:SelectText` 以外還有指令毒化。**
→ 逐一列出，並**回頭檢查每一個是否在出貨的 E1 路徑上**。
若 `.uno:Undo` 在內，`demo-structure` 的復原鈕要補處置，任務 #50 不算完。

**結局 C：負對照也毒化。**
→ 這一輪的量測方式壞了（很可能是重複載入或 `.uno:` 派送的時序），
**在修好之前不得引用任何一臂**。

**結局 D：`.uno:SelectText` 這一輪反而沒毒化。**
→ 與前兩輪矛盾，優先查的是這一輪的探針改動，不是推翻前兩輪。

## 不宣稱

- **不宣稱這份清單窮舉了核心裡所有不配對的地方。** 它只涵蓋**這個引擎會派送的**指令。
- 兩個純檢視指令（`.uno:ViewAnnotations`）與需要前置狀態的組合不在這一輪裡，
  跳過的理由就是這一句，不是它們安全。
