# 交接 — 2026-08-15（下半場：#50 完成、#49 找到根因並修好、新開 finding 043）

接手前先讀[同日上半場那一份](HANDOFF-2026-08-15-session-state.md)，本份只增補與更正。
[中斷點那一份](RESUME-2026-08-15-049.md)已經被本份取代。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨 |
| **E1 出貨編輯器** | `835b453d…`＋殼層 `f9b1a52f…`，`E1_GO_ODT_EDITOR` **不變** |
| **E2 出貨引擎** | `c89f069e…`，**E2-A ＝ `PARTIAL_GO_TO_E2_B` 不變** |
| **組合 artifact** | **`e2-combination` ＝ `940b7723…`**（前一顆 `ba1a5dd5…` 已封存）。**永不出貨** |
| **新的上游 finding** | **043**——`FN_SELECT_PARA` 的 `SttSelect()` 沒有配對的 `EndSelect()`。草稿 `findings/drafts/043-bugzilla.txt`，**未送** |

**三顆凍結 artifact 全程未動**：`835b453d`／`679def61`／`c89f069e`，每次動作前後都核對過。

## 短期目標（demo）的四項出場條件：**第 1 項已解決**

| # | 事情 | 狀態 |
|---|---|---|
| 1 | **拖曳選一段再按按鈕會失敗** | **已修**（任務 #49，見下）。根因是上游，我方加了標註過的 workaround |
| 2 | **`demo-structure` 沒有 undo** | **已完成**（任務 #50） |
| 3 | heading／list 跑在診斷 artifact 上 | **仍開著**——整個 E2-B（#48 ＋ 實作 ＋ relink ＋ 重驗），這是長尾 |
| ~~4~~ | ~~註腳裡有 frame~~ | 使用者已判定太冷門，移除 |

**所以剩下的只有第 3 項。** #49 一解決，#48（寫 SPEC-E2-B）就不再被擋。

## #50：`demo-structure` 的復原鈕（`21e95a5`）

按鈕走 **Document SDK 的 `document_.undo()`**，也就是出貨編輯器那顆「復原」的同一支；
診斷 ABI 自己的 undo 動作留在 `FORBIDDEN` 裡沒動。
判準是存出來的 ODT：標題 → 復原、移除清單 → 復原，兩次的 `<office:body>` 都與原始逐位元組相同；
沒東西可復原時多按兩次，body 仍相同且不會往前吃掉別的東西。
證據＋可重跑的 `check.py` 在 `findings/evidence/sdk-e2/discovery/demo-structure-undo/`。

順帶更正 `demo-structure.html` 一句過時的話（「E2-A 還沒有總判定」），
並補上手勢說明與縮限 4／7 兩句。

> **第一版的比對沒有鑑別力**：namespace 抓錯，每段的 `style-name` 都讀成 `None`，
> 於是「復原後 == 原始」通過，**但「按標題後 == 原始」也通過**。是正對照抓到的。

## #49：格式動作之後選不到東西——**根因在上游**

### 機制（原始碼層，逐行出處在 finding 043）

引擎的範圍選取送 **`RESET` ＋ `END`，沒有 `START`**。而 barrier 用的 `.uno:SelectText`
→ `FN_SELECT_PARA` → `EndPara(true)` → `MoveCursor(true)` → **`SttSelect()` 設
`m_bInSelect`，這條路徑沒有任何地方呼叫 `EndSelect()`**；兩個 `RESET` 都走 `bClearMark`
那一支、不碰旗標；最後呼叫端的 `END` 呼叫 `SttSelect()`，被 `if (m_bInSelect) return;`
擋掉，**`SetMark()` 從未執行**。沒有 mark 就沒有選取，也就沒有回呼。

### 這不是我們誤用 API——**上游自己的測試就是這樣用的**

`sw/qa/extras/tiledrendering/tiledrendering.cxx:151`：
「`// Next: test that LOK_SETTEXTSELECTION_RESET + LOK_SETTEXTSELECTION_END can be used to create a selection.`」
＋ `CPPUNIT_ASSERT`。**這條是 codex 覆核找到的，不是我。**

### 量了四輪原生 ＋ 一輪 WASM，每一輪的預測都在該輪之前 commit

| 輪 | 問什麼 | 結果 |
|---|---|---|
| 1 | 哪個前置動作會壞 | **起因是 `.uno:SelectText`，不是格式指令**（做了格式但不做 SelectText 的臂選得到；做 SelectText 但不做格式的臂選不到） |
| 2 | 機制的可觀測簽名 | **同一組座標連選兩次，第一次空、第二次成功**——失敗的那一次自己燒掉旗標 |
| 3 | 還有別的指令嗎 | 引擎派送的 **20 個 uno 指令裡只有 `.uno:SelectText`** 毒化。**`.uno:Undo` 乾淨**（就是 #50 那顆按鈕） |
| 4 | 覆核指名的分離臂 | 拿掉 readback 與等待**照樣治好**；換成不呼叫 `EndSelect()` 的同一個 `SetCursor` **治不好**；端點在壞狀態與正常狀態**選到同一串**，正反向都是 |
| WASM | 修法在 artifact 上成不成立 | **成立**，兩瀏覽器逐格相同 |

### 修法：`RESET` ＋ **`START`** ＋ `END`

`probe_engine.cpp` 的 `OXSDK_EDITOR_SELECTION_TEXT_HANDLES` 一處，
**註解寫明是版本相容 workaround、上游修好就拿掉**。
產品的 `selectRange` 走的正是這個方法（`editor_api.cpp:121`）。

WASM 上的前後對照（`ba1a5dd5` → `940b7723`）：

| step | 修之前 | 修之後 |
|---|---|---|
| 沒有 bounded readback 的那條 | **逾時 10 001 ms** | **回呼，10 ms** |
| 有 bounded readback 的那條 | 251 ms readback，選取 `none` | **回呼，11 ms，選到文字** |
| `repeat` 三輪 | 251／250／250 ms readback | **10／10／11 ms 回呼** |

**而且比了幾何**：修好之後那一臂的 `collapsed`／矩形數／`start.x`／`end.x`
與**從沒做過格式動作的控制臂完全相同**（false／1／1524／2924，兩瀏覽器）。
「非空」不等於「正確」，這一格是後者。

## 我這一輪的錯，以及誰抓到的

| | 抓到的人 |
|---|---|
| **臂 E 的預測前提讀錯**（`.uno:Escape` 在沒有選取時到不了 `EnterStdMode()`） | 我自己，**在執行之前**，另外 commit 修正 |
| 回呼次數的**絕對值不穩定**（兩輪一致差 1），只能引用同輪之內的差 | 我自己，**複驗抓到的** |
| **`.uno:GoLeft` 救得回來那一格不可重現**（四輪之中翻轉一次） | 我自己，第四輪比對時。**已標註不得引用** |
| 臂 G「中間什麼都沒發生」是假的（還有 sleep、readback、`SwTransferable`），「唯一簽名」過度宣稱 | **codex 覆核**，已補 AE／AF 兩個分離臂 |
| 臂 H 在正常狀態的推理錯（`SttLeaveSelect()` 會清掉收合的 mark）——**結論對、理由錯** | **codex 覆核**，我自己核對 `select.cxx:661` 確認 |
| 上游測試那條決定性證據，我沒找到 | **codex 覆核** |
| 用 `pgrep -f` 等自己的迴圈，永遠不會結束 | 我自己 |
| **誤把 A3 單輪 `exit 1` 當失敗而停掉掃描**——交接文件早就記過這個坑 | 我自己，第二次踩 |

## 動手之前必讀（本輪新增）

1. **`f049_native_select_after_format.cpp` 還沒進 `test-e2-a-static` 的語法檢查清單。**
   **現在不能加**——改 Makefile 就會重連結（finding 042），`940b7723` 的證據會失效。
   **留到下次刻意 relink 時一起做。**
2. **原生探針用固定 sleep**（`post()` 之後只等 400 ms）。臂 F／Y／Z 翻轉就是它的代價。
   要讓那幾格可引用，得改成等待實際完成而不是等計時器。
3. **`libreoffice-26-8` 帶五個本地修改**（四個 Emscripten 建置檔、一個 Qt plugin 的 IME）。
   逐一檢查過都與 `sw/` 無關且對原生 `svp` 執行不可能有影響，
   但**那是檢查過不是重現過**——上游回報前要在乾淨樹上重現一次，那要完整重編，**歸使用者**。
4. **`pgrep -f <pattern>` 會比對到自己所在的 shell**。等待迴圈要用別的判準。

## 還開著的

| # | 事情 | 卡在誰 |
|---|---|---|
| **48** | **寫 SPEC-E2-B** | **#49 已解決，不再被擋**。這是 demo 出場條件的最後一項 |
| **46** | finding 040 上游未送 | 使用者決定。重複單已於 08-15 重查、十組全零；還缺 Component 確認與一支非主執行緒 `doc_destroy` 最小重現 |
| **新** | **finding 043 上游未送** | 使用者決定。送出前清單寫在 `findings/043-*.md`：七組重複單查詢**一組都還沒跑**、Component 待確認、**要在乾淨樹上重現**、cppunit 測試要實際編起來跑紅 |
| — | 039 產品對照那五個數字（`112／19／251／8／10`） | **仍未落地**。這一輪沒動到 |
| — | `doc_getSelectionType` 是不是 040 的第四個入口 | 結構相同、**未量** |
