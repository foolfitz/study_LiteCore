# 096 — 在文件邊界按方向鍵會打死 session，而且沒有檢查點

**狀態**：擁有者目擊，**尚未重現、尚未區辨**。成因不明。
**嚴重度**：**資料遺失**——提示自己說「自上次儲存以來的內容不會回來」。
**發現**：2026-09-09 的 T4 第二次人工輪，`findings/evidence/manual-round-v13-31787584/notes-owner-T4.md`。

## 現象（擁有者原話）

> 走到最上面再按上：**會掛掉！**狀態變成「處理中」，不久跳出「引擎需要重新
> 開啟。沒有檢查點，所以自上次儲存以來的內容不會回來。」提示
>
> 走到最下面再按下：同上

同一輪還記下：

> 用方向鍵在文件裡上下走，畫面有沒有跟著：**沒有跟著**

## 條件

- profile **`e2-editor-v13`**，候選頁面
  `31787584290e42bdca41f95949887dedbc39ba51386439cd8c4d2914d056a79a`
  （server 送出的位元組在開始前用 HTTP 抓下來重算過）。
- **v13 是這棵樹自 a11y build 以來第一顆真的連結出來的引擎**
  （`probe.wasm` `0fe25650bec1bac5…`；v9–v12 全是同一顆的重新打包）。
- 真實文件 `~/Documents/SLAT/e20-專訪瓦特老師.odt`，比視窗長。
- **沒有開螢幕閱讀器。**方向鍵移動的是編輯游標，不是瀏覽游標。

## 為什麼這**不是**上一輪那個現象，不得合併

2026-09-08 那一輪記下的邊界行為是**焦點逃逸**：走到頂端按上，焦點離開文件
區域跑到工具列（`leaving panel` ×3），**session 活著**。今天是 **session 死掉**，
而且是沒有檢查點的那一種。**兩者形狀不同、後果不同，分開記。**

同樣不得與 finding 095 合併（ArrowDown 之後點畫布放不了游標，觀察未調查）。

## 那句「畫面沒有跟著」與今天稍早的確認不矛盾

今天稍早擁有者在**開著 Orca** 的情況下確認過「方向鍵往下時捲軸有跟著」，
而 093 的修法定位的是**無障礙投影節點**——那是螢幕閱讀器的瀏覽游標會走的東西。
**沒有螢幕閱讀器時，方向鍵移動的是編輯游標**，視窗跟不跟得上走的是另一條路
（`paint()`／`moveSinkToCaret` 之於 `#sink`）。

所以「沒有跟著」**可能是另一個缺陷，而不是 093 沒修好**。這句話是假說，未量測。

## 決定後果的那一題：出貨的 v8 會不會也這樣

- **會** → 與 086 同類：兩邊都有、非退步、修法可延後，soak 計數的處置另議。
- **不會** → **這是候選帶進來的退步**，而且是資料遺失級的，cutover 前必須處理。

而 v13 是新連結出來的引擎，所以要問的是**三個**而不是兩個：v13（新引擎）、
v12（舊引擎、舊頁面）、v8（出貨）。三者的差異能把「新引擎造成的」與
「頁面改動造成的」分開。

## 對閘門的後果（記下，裁定不在起草方）

閘門文件第 31 行：**「When they produce a finding, the clock restarts from zero
and the finding gets a number.」**T4 是閘門條件 3 的那一輪。soak 目前是
**6 of 12**。這一張是否讓它歸零，**由裁定的人決定，不由起草方宣告**——但
不得假裝沒發生。

## 未做

- 重現一次（agent，帶儀器）。
- v8／v12／v13 的區辨。
- 問**引擎**那一側崩在哪裡；`#s-latency`／toast 是頁面的觀測，不是引擎的狀態。
- 「畫面沒有跟著」與「session 掛掉」是不是同一個成因——**沒有理由假設是**。

---

# 追記（2026-09-09，agent 帶儀器）：三支臂全中，出貨的 v8 也一樣

**狀態改判**：**已重現、已區辨。成因仍不明，且本輪不指認成因。**

證據：`findings/evidence/096/`（`RESULT.md`、四份 `boundary-arrow-*.json`、
`probe_096_boundary_arrow.py`）。量測協定
`handoff/tasks/TASK-2026-09-09-096-which-profiles-kill-the-session.md`
（commit `a0f098b5`）**寫在任何一次計數的嘗試之前**，每個結果准許什麼也寫在那裡。

## 結果

| 臂 | 頁面 sha256 | probe.wasm | 上 | 下 |
| --- | --- | --- | --- | --- |
| A — `e2-editor-v13`（候選） | `31787584290e42bd…` | `0fe25650bec1bac5` | **5/5** | **5/5** |
| B — `e2-editor-v12` | `db2ed393f3433e2e…` | `4ec1e389aaab3b03` | **5/5** | **5/5** |
| C — `e2-editor-v8`（**出貨的位元組**） | `1ec7baf9fb53c808…` | `4a2710bba1ef07d9` | **5/5** | **5/5** |
| D — 093 之前的頁面＋出貨引擎 | `df5f3b6c7dde0b2e…` | `4a2710bba1ef07d9` | **5/5** | **5/5** |

**40 次嘗試、40 次重現、0 次沒重現、0 次 VOID。**沒有間歇性，沒有哪一次不一樣，
也沒有哪一次被略過不報。用的是擁有者自己那份文件
（`~/Documents/SLAT/e20-專訪瓦特老師.odt`，sha256 `63bf89cb…`），真的方向鍵
（CDP `Input.dispatchKeyEvent`），游標用畫布 pointerdown 放。

## 本張最上面那一題（「出貨的 v8 會不會也這樣」）的答案

**會。**照這張自己寫的判準，這是**與 086 同類：兩邊都有、非退步**。
**它不是候選帶進來的，也不是 v13 那次連結造成的。**

臂 D 再補一刀：**頁面改動也不是必要條件**——093 頁面那一半（`18eefcce`）
還沒進去之前的頁面，配出貨引擎，一樣 10/10 死。

## 引擎那一側說了什麼（原文，不是摘要）

`#s-latency`、狀態球、toast 都是**頁面的**觀測。以下不是。

SDK 自己那顆 error 物件（`run()` 印成 `${code}：${message}`）：

```
上移一行：TIMEOUT：editorActionV2 timed out after 30000 ms（可能已經改到文件：請回到檢查點）
```

狀態轉移的時間戳（頁面裡的 MutationObserver 記的）：`ready → busy` 發生在邊界
那一按，然後 v8 隔 **30002 ms**、v12 隔 **30003 ms**、v13 隔 **30003 ms** 轉進
`recoverable-error`。**它不是失敗，是把 SDK 那個 30 秒的期限一毫秒不差地等完。**
後續每按一次，`pending` 就往上加一（1→6）——佇列塞在一個永遠不回來的操作後面。
`revision` 全程 `0`：沒有東西被寫進文件。

**沒有任何東西崩潰。**四十次裡沒有 `Inspector.targetCrashed`、沒有
`Target.targetCrashed`、頁面與 worker 都沒有 `Runtime.exceptionThrown`，頁面自己的
`window.onerror`／`unhandledrejection` 是空的。worker 的 console 只有開機那兩行
（`Thread name: "configmgrWriter"`／`"lo_startmain"`），邊界那一按的當下**一個字都沒有**。

**worker 的 JavaScript 執行緒活著。**判定之後對活著的那個 worker 自己的 CDP session
送一次 `Runtime.evaluate`，四十次全部在 **0.0 秒**回答
`{"now":37420,"post":"function","onmsg":"object"}`。所以「worker 的 JS 執行緒卡住」
被排除；沒有回答的是它後面那一層。

**到此為止。本輪不指認成因**（協定明文禁止，040 的前例）。特別是：
`boundaryRejectionRequiresFreshWorker` 三個 manifest 都宣告 `true`——那是一句**宣告**，
不是一次量測，不得拿來當結論。

## 這一輪順帶量到、但**不得合併**的

- 觸發成本是零：文件 `revision: 0`，沒存過、沒改過，**一個方向鍵就夠**。
  提示是沒有檢查點那一種（`data-rescue: "none"`、`#s-checkpoint` 是「無」、
  按鈕寫「重新開啟」而不是「回到檢查點」）。使用者打了一小時再按一次上，就是一小時。
- 使用者體感的 30 秒：按下去、「處理中」三十秒、然後 session 沒了。
- 下臂的原始數字裡，游標在 `sinkTop` 3142 而 `#desk` 的 `scrollTop` 是 0
  （可視高 864）。形狀像擁有者那句「畫面沒有跟著」，但**本探針從沒要求頁面跟過去**，
  所以這個數字對任何解釋都不構成支持。**只登錄，不合併**（093 已經更正過一次同型的錯）。

## 仍未做

- **成因。**沒有量，因此沒有寫。
- **從什麼時候開始有的。**四顆 artifact 不是二分搜尋；本輪最早只測到 `e2-editor-v8`。
- **這張是否讓 soak 計數歸零**——由裁定的人決定，起草方不宣告（AGENTS.md §8）。

---

# 擁有者的兩個裁定（2026-09-09，append-only）

區辨的結果先擺著：**四臂 40/40 全中**，包含逐位元的出貨位元組
（`1ec7baf9…`，與 `dist/e2-editor-app.js` 相同）與 093 之前的頁面。
**096 不是候選帶進來的、不是 v13 的連結、不是 093 的頁面改動。**

## 裁定一：soak 計數**不**因這張 finding 歸零

擁有者的回覆，逐字：「不要」。

閘門文件第 31 行寫「產生 finding 就從零重來」，而這一張是 T4 產生的。裁定是
**不歸零**，理由與 086 同型：**兩邊都有、非退步**，而且**乾淨判準沒有改變、
沒有任何身分綁定的位元組移動**。086 當初也不是因為自己讓計數歸零的——歸零的
是頁面移動。

`handoff/PLAN-2026-09-06-after-the-page-moved-twice.md` 裡「soak 按住不跑」
那一節的**按住原因因此解除**，計數維持 **6 of 12**。

## 裁定二：現在就修（選項 B）

擁有者的回覆，逐字：「B」。理由不是 cutover，是**今天出貨的產品上就有一個
零成本觸發的資料遺失**：`revision: 0`、沒有編輯、沒有存檔、**一次方向鍵**，
而提示自己說「自上次儲存以來的內容不會回來」。

## 這兩個裁定之間的張力，寫下來免得被誤讀成矛盾

**計數不因 finding 歸零，但修法很可能讓它歸零。**這兩句都成立：裁定一講的是
「這張單本身」，裁定二引進的是「一次會移動位元組的改動」。哪些檔案會被動到
決定代價，而**那還沒有查**。

所以下一步**不是落地修法**，是先查清楚：這個修法非得住在哪一層（引擎／worker／
殼層／頁面），因而會移動哪些身分、作廢哪些證據。**在那個答案出來之前不動任何
原始碼**——`wasm build 不可重建`，而已經押了六趟。

---

# 追記（2026-09-09，agent）：三個解釋剩一個——引擎活著，而核心從沒廣播那一則

**狀態改判**：**已重現、已區辨、三個解釋收斂到一個。成因的下一層仍未指認。**

證據：`findings/evidence/096/RESULT-engine-side.md`、`README-engine-side.md`、
`engine-side-e2-editor-{v8,v13}.json`、`probe_096_engine_side.py`、
`summarise_engine_side.py`。量測協定
`handoff/tasks/TASK-2026-09-09-096-does-the-engine-thread-still-answer.md`
（commit `ed7568dd`）**寫在探針存在之前**，每個觀測准許什麼也寫在那裡。
**沒有建置、沒有連結、沒有移動任何產品位元組。**

這是 `handoff/DECISION-2026-09-09-which-layer-can-carry-096s-fix-and-what-each-costs.md`
§2.3 指名的那一次量測。它問的是上一輪明文不問的那一題：**判定之後，引擎執行緒
還答不答；而那一按前後，核心到底廣播了什麼。**

## 做法：注入到活著的 worker 自己的 realm

頁面、殼層、SDK 這三層，上一輪的證據已經證明是塞住的——問它們是問錯邊。所以三件
事都在 worker 自己的 JavaScript realm 裡做：包 `globalThis.__probe_on_event`
（`emitJson` 唯一的 JS 出口，而且是呼叫時才查名字）、包 `self.postMessage`、
用 `dispatchEvent` 把三個請求送進 `handleRequest`。

三個注入，順序固定：

- **C** `f096ControlNoSuchOperation`——**注入路徑的對照組**，由 worker 自己的
  switch default 答 `UNKNOWN_OPERATION`，**完全不碰引擎**。沒有它，「引擎沒答」
  和「我的注入根本沒到」是同一種沉默。
- **G** `editorGetStateV2`——走引擎的命令佇列，由 `handleEditorGetState` 同步回答，
  **不碰 `gEditorPending`**。
- **P** `editorActionV2`（同一個方向的動作）——**正向對照**，必須答 `BUSY`。

`documentHandle` 與 `expectedRevision` 是從 **worker 自己的 `pending` map** 讀的
（那筆卡住的 `editorActionV2` 的 payload），不是從頁面拿的。

## 結果：20 次計數嘗試，20 次重現，0 VOID

| 臂 | probe.wasm | 上 | 下 | §2.1 | §2.2 |
| --- | --- | --- | --- | --- | --- |
| C — `e2-editor-v8`（**出貨的位元組**） | `4a2710bba1ef07d9` | 5/5 | 5/5 | `C_EXCLUDED` ×10 | `A` ×5／`B` ×5 |
| A — `e2-editor-v13`（候選） | `0fe25650bec1bac5` | 5/5 | 5/5 | `C_EXCLUDED` ×10 | `A` ×5／`B` ×5 |

**兩顆引擎逐格一致。**

### (c) 出局：引擎執行緒在跑，而且在執行命令

20 次全部，判定之後：C 答 `UNKNOWN_OPERATION`（0.0 秒）、G 答出完整的 state
（0.0–0.3 秒）、**P 答 `BUSY`：「another callback-correlated editor operation is
in flight」**（0.0 秒）。`getStateDispatchReturned` 20/20 為真，所以連「呼叫進
wasm 沒回來」那一格都沒觸發。

**正向對照 20/20 成立**，所以本輪不 VOID，而且引擎的狀態就是靜態追蹤預測的那個：
`gEditorPending.requestId != 0`，一個 cancel 清不掉的格子。

### (b) 在它承重的那個形式上出局：沒有任何一則「能完成它」的 callback 到過

這條路上 `requiredCallback` 是 `EditorCaretOrSelectionCallback`（`= -2`），
`completePendingEditorOperation` 只接受 LOK id **1**
（`INVALIDATE_VISIBLE_CURSOR`）或 id **2**（`TEXT_SELECTION`）。

**20 次裡，邊界那一按到判定之間，id 1 與 id 2 各出現 0 次。**視窗裡的 id 是：
上臂**一則都沒有**（10/10），下臂三則 id **8**（`STATE_CHANGED`，10/10），酬載逐字是
`.uno:LanguageStatus=English (USA);en-US`、`.uno:CharFontName=Liberation Serif`、
`.uno:FontHeight=12`——`completePendingEditorOperation` 對這個型別**根本不會被呼叫到**
（它只在 `if (editorStateChanged)` 裡面）。`sourceSequence` 在邊界那一按之前與
判定之後**完全相同**（20/20）。

**探針自己的正向對照就在同一份擷取裡**：前一按（會動的那一按）產生
`lok id=1` → `editor-state source=visible-cursor` → `editor-action-completed`
`completion: "documented-callback-visible-cursor"`，**37–39 毫秒**完成，20/20。
同一支包裝、同一個 session、同一顆按鍵，前一按有，後一按沒有。

### 剩下的是 (a)：那一則廣播從來沒發生

依決策文件 §2.3 的表，這一格准許的是「修法必須提供 callback 給不了的完成，
那是**引擎**的修法或撤回能力」。**那是一張准許證，不是一個決定**——選哪一列屬於
裁定的人（AGENTS.md §8），本輪不選。

## 順帶更正一件我自己寫錯的事

協定 §2.3 原本說：要把 (a) 和「核心廣播了一個這顆 build 不看的型別」分開，得在
LOK 的 trampoline 加計數，也就是改引擎、連結、付決策文件 row A 的價。

**那個計數已經在出貨的引擎裡。**`onLokCallback`（`src/probe_engine.cpp:2372-2381`，
`registerCallback` 交給 LOK 的就是它，`:2801`）第一件事就是**無條件、在型別 switch
之前、在所有 `#ifdef` 之外**，把每一則 callback 原樣吐成
`{"type":"lok","id":…,"payload":…}`。所以這條界線上分得乾淨，**不需要動引擎**。
更正寫在協定的執行紀錄裡（append-only）。

## 這一輪分不開的，指名寫下來

1. **下臂那三則 `STATE_CHANGED` 到底是回答邊界那一按，還是前一按的尾巴。**量到的
   延遲：它落在前一按 id 1 之後 **302–306 ms**，而同一次嘗試裡「點擊 → STATE_CHANGED
   爆發」的參照是 **293–299 ms**，兩者差約 7 ms，10/10、跨兩顆引擎；落在邊界那一按
   之後則是 184–186 ms，對不上任何參照。**形狀像尾巴**——但本探針是用 mark 索引歸屬的，
   **它不把 callback 對應到造成它的命令**，所以登錄的格子仍然照登錄的算（`B`），
   這段是量測、不是改判。能分開它的：引擎那一側做 callback↔命令的對應（要連結），
   或決策文件已經指名的 native LOK harness（`tools/f059_native_*.cpp` 對
   `native-lok-26-8/`，**不用連結**）。
2. **核心為什麼沒廣播。**計數為零只說核心沒有呼叫註冊的 callback，不說核心裡是誰
   決定的。
3. **Home／End。**018 量的是 `End`，096 與本輪量的是 Up／Down。四個是不是同一回事，
   **兩個方向都沒量過**。
4. **判定之後才送達的 callback。**視窗在判定收尾。

## 也登錄、但**不得合併**

**上臂整場沒有出現過任何 `LOK_CALLBACK_STATE_CHANGED`**，而下臂在點擊之後與
前一按之後都有爆發。兩臂點的是擁有者那份文件裡不同的段落，所以這只是一份檔案裡
兩個位置的差別，本輪沒有任何東西說它代表什麼。**登錄，不解釋。**

---

# 成因區辨的結果，與擁有者的處置裁定（2026-09-09，append-only）

## 三個解釋剩一個：core 什麼都沒有廣播

證據 `findings/evidence/096/RESULT-engine-side.md`，判準
`handoff/tasks/TASK-2026-09-09-096-does-the-engine-thread-still-answer.md`
（commit `ed7568dd`，**寫在探針存在之前**）。兩個引擎各 10 趟，逐格一致：

| 注入 | 回答 | 意義 |
| --- | --- | --- |
| 控制組 `f096ControlNoSuchOperation`（從不碰引擎） | `UNKNOWN_OPERATION` 20/20 | 注入真的到了 worker |
| `editorGetStateV2`（同步、不碰 `gEditorPending`） | 完整 state 20/20 | **引擎執行緒還在跑** |
| 第二個 `editorActionV2`（正對照） | **`BUSY` 20/20** | 「另一個回呼相關的編輯操作在途中」 |

- **(c) 排除**：`engineCell: C_EXCLUDED`——引擎執行緒在判定之後照樣彈出並執行命令。
- **(b) 在承重的形式上排除**：`EditorCaretOrSelectionCallback` 只收 LOK id 1 或 2，
  而視窗內**這兩種一個都沒到**（上鍵臂 10/10 完全沒有任何 callback）。
- **(a) 存活。**

對照很鋒利：**前一次按鍵**（還沒到邊界）產生 id 1，**37–39 毫秒**回來。
機制平常正常，只有邊界那一下 core 靜默。

## 因此的形狀，而且 core 可能根本沒有錯

游標在邊界動不了 → **沒有東西可廣播，所以不廣播** → 引擎的移動路徑等一個
永遠不來的回呼，**而它是三條姊妹路徑裡唯一沒有 arm 期限的**
（`readbackDeadlineArmed` 於 `src/probe_engine.cpp:4941`、`:5070` 有，這條沒有）
→ 永久楔住，`cancel` 回 `NotCancellable`（`:6198-6209`），之後一切答 `BUSY`
→ 30 秒後 SDK 放棄，頁面跳「沒有檢查點」。

**缺陷是引擎把「沒有移動」當成「還在等」。**那條路自己的註解早就寫著等一個
不來的廣播會「把操作永久楔住——finding 018 的形狀」。

## 未分離（不得被上面的清楚蓋過去）

- 下鍵臂那三筆 id 8 `STATE_CHANGED` 是回答邊界那一下，還是前一下的尾巴。
  這支探針不做 callback 與 command 的相關性配對。
- **為什麼 core 沒有廣播**。名指的兩條補法：引擎側相關性（要重連結）或
  免瀏覽器的原生 LOK 治具（`tools/f059_native_*.cpp`，不用重連結）。

## 擁有者的裁定：**A ＋ C**

逐字：「A + C」。

- **A —— 引擎**：替這條移動路徑 arm 期限，比照兩條姊妹路徑。邊界那一下要
  **回答「什麼都沒動」**而不是楔住。要一次重連結（擁有者手動）。
- **C —— 殼層**：手勢之前先存檢查點，移掉「資料遺失」那一半。

**C 單獨是半個修法**（動作照樣掛 30 秒），A 是唯一讓那一下被回答的。兩個一起
落地、一起量。這棵樹 2026-08-22 為「交出半個修法」付過一次錢，那一次的兩半
一半在 `dist/` 一半在凍結的 profile 裡，使用者測到的行為完全沒變。

---

# 修法落地（2026-09-09，append-only）：A 與 C 的原始碼都在了，只等擁有者跑那一次連結

**狀態**：**A 與 C 兩半都已落地在原始碼**。**C 已在出貨的位元組上量過並且分得開；
A 在連結之前量不到，這裡不假裝量得到。**

**沒有連結、沒有產出 wasm、`dist/profiles/**` 一個位元組都沒動**——實測：
`dist/profiles` 與 `build/e2` 底下 334 個檔的 sha256 在整輪改動前後完全相同。

貨載：`761fc80d`（引擎＋殼層＋單元測試＋殼層 generation）、`bf894bba`（generation
改名 v50→v51）、`85c8710b`（閘門 amendment，寫在檢查存在之前）、以及本輪最後一個
commit（第 42 道檢查、突變、liveness 宣稱、證據）。

## A —— 引擎：那條路現在 arm 期限，而且**回答**而不是報錯

`handleEditorAction` 的按鍵路徑 arm `readbackDeadlineArmed`，到期由新的
`completePendingEditorActionByReadback()` 從讀回回答，completion 是
`verified-move-readback`，`changed: false`、revision 不動。

**回答不是錯誤，而這是先查過才選的。**`narrow-editor-v2-client.js` 要求移動的
completion 以 `documented-callback-` 開頭，而 `EDITOR_RESULT_INVALID` 在
`editor-session.js` 的 `RECOVERY_ERRORS` 裡——所以若引擎改了而客戶端沒有一起改，
邊界那一按會在 250 ms 被回答、被判無效、session 照樣死，只是**早 29.75 秒**。
兩半一起落地，就是為了這個。

**期限的數字**：250，來自 `EditorSelectReadbackDeadlineMs`；而它在這裡有自己的
理由——這條路要蓋住的東西是**在這條路上量的**：邊界前一按 37–39 ms，20/20，兩顆
引擎（`RESULT-engine-side.md` §2）。250 是那個帶上緣的 **6.4 倍**，不是姊妹路徑對
finding 048 的 22–28 ms 的約 10 倍。**這個比值寫在程式碼裡沒有被四捨五入掉**，
以及它的代價：比 250 ms 慢的一按由讀回回答，而讀回報告游標**實際在哪裡**，從不
宣稱移動發生過；晚到的 callback 這時 `gEditorPending` 已清空，仍會更新
`gEditorState`，頁面的游標由一般的 editor-state 公告追上。

**`mainLoopDrainCommands` 刻意不動**：`EditorPendingOperation` 自己的註解早就寫著
「診斷 profile 保留純 callback 語意」，而 018 的歸因正是靠那個差別。出貨與候選都
沒有 `OXSDK_MAINLOOP_ENGINE`。**預設結論（若這件事永遠沒有再議）**：將來重連的
attribution profile 在邊界仍然會楔住，而那是刻意的。

**具名代價**：v1 客戶端（`editor-shell/editor-client.js`）被 E1-C 綁著不能改，
它會把 `verified-move-readback` 判成 `EDITOR_RESULT_INVALID`。將來若有 v1 profile
重連，邊界 ArrowLeft 會早 30 秒死、代碼比較不準。**本次沒有任何 v1 artifact 移動。**

## C —— 殼層：手勢之前先存檢查點，而且**有人從裡面回復過**

`NarrowEditorV2Session.action()` 在六個按鍵路徑動作之前呼叫
`_checkpointBeforeBoundaryMove()`，重用基底類別的 `_checkpointBeforeSelection`
（E1-C 綁定，不能改但可以叫）。revision 守衛擋掉「按住方向鍵每按一次存一次」——
因為 `action()` 把十五個動作全都用 `mutation: true` 入列，基底類別自己的 stamp
守衛在這裡擋不住。

### 量了什麼（出貨的 `e2-editor-v8` 位元組，兩臂只差那兩行）

`findings/evidence/096/checkpoint-before-the-gesture.json`（判準寫在探針裡、
探針寫在跑之前；`checkpoint-before-the-gesture-shakedown-1.json` 是先跑的一趟
`--attempts 1`，**沒有逼出任何改動**）。

| 臂 | 判定 | `data-rescue` | `#s-checkpoint` | 打進去的字回來了 |
| --- | --- | --- | --- | --- |
| `without`（今天早上的產品） | **WORK_LOST** 3/3 | `none` | `無` | **沒有** |
| `with`（現在這棵樹） | **RECOVERED** 3/3 | `checkpoint` | `有（r1）` | **有** |

`without` 那一臂**逐字重現擁有者的句子**（`noticeMatchesOwnerQuote: true` 3/3）。
判定讀的是**產品自己的存檔鍵**在**產品自己的回復鍵**之後吐出來的 `content.xml`——
不是 `hasCheckpoint`、不是狀態球、不是提示文字。**沒有人從裡面回復過的檢查點不是
檢查點。**探針在突變比對不到東西時會拒絕執行：比對不到就等於兩臂服務同一份修好的
產品，然後回報「兩個一模一樣的鏡像意見一致」。

**這一輪量到而 A 沒有動的**：`boundaryPressAnsweredSeconds` 在 6 次裡**都是 null**。
兩臂的那一按都照樣楔住、照樣等完 30 秒。**C 拿掉的是資料遺失那一半，不是掛住那一半。**

## 回歸網：第 42 道檢查

`a-boundary-arrow-press-does-not-cost-the-work`，四條子句分開回報，
突變 `boundary-move-takes-no-checkpoint`（就是那兩行）。入閘資格與計數語意
（39 PASS / 2 NE → **40 / 2**）寫在
`handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` 的 2026-09-09 amendment 裡，
**寫在檢查的程式碼之前**。

**B2 是逐實例的**（AGENTS.md §1 形式一）：那一按**如果**被回答了，session 要留在
ready、revision 不動。今天沒有任何 artifact 會回答，所以它對空集合成立，
`clausesExercised` 會說它沒被執行過——一次綠燈不能拿去當它的證據。**連結之後它
自己開始咬，沒有東西要改。**

## 連結之前量不到的（不得被上面的綠燈蓋過去）

1. **A 的效果。**這棵樹沒有任何 artifact 帶著移動路徑的期限。邊界那一按在**每一次
   量測裡**都照樣楔住。
2. **250 ms 夠不夠。**37–39 ms 是在**沒有負載**的情況下、用這支儀器、在這份文件上
   量的。長文件、其他工作在跑的時候會不會超過 250 ms，**沒有量過**。超過的後果已經
   寫在上面（由讀回回答，不會謊報移動），但**發生率是未知的**。
3. **Home／End 與兩個字元移動。**期限 arm 在整條按鍵路徑上，但 096 量的是上／下、
   018 量的是 End，Home 與字元移動**兩個方向都沒量過**。
4. **`verified-move-readback` 有沒有真的被產生過。**沒有。連結之前它是一個沒有
   任何引擎會吐的字串。

## 順帶量到、**不修、送裁定**：提示的句子現在指名了錯的手勢

C 讓邊界那一按走到 `canRescue` 那一格，而那一格的句子是
「這一步可能已經改到文件，而且無法驗證。**回到選取手勢前的檢查點**。」
——**沒有選取手勢**，使用者按的是方向鍵。

這正是 **finding 061 的形狀**（對另一個情況為真的句子＝誤導性歸因，這棵樹已經
把它當缺陷立過一次）。**沒有改**，理由有兩個，都寫下來：

- 它住在 `web/e2-editor-app.js`，也就是殼層 bundle 的 entrypoint。改它會移動
  `candidateCutover.pageSha256`，代價是決策文件 row D 的價碼——而 096 的修法
  **不屬於**頁面那一層。「修法要落在它該在的地方，不是落在最好打字的地方。」
- 一句話同時服務兩個手勢（範圍選取的刪除與方向鍵）。要對兩者都精確，要嘛把句子
  改鬆（會削弱刪除那一格真正需要的警告），要嘛依失敗的手勢分支——那是**新機制**，
  而 AGENTS.md §4 說寫到新機制就該停手回報。

**最小的誠實修法看起來是刪掉「選取」兩個字**（「回到**這個手勢**前的檢查點」），
但那是產品文案的決定，起草方不做（AGENTS.md §8）。**預設結論（若永遠不處理）**：
使用者在邊界按方向鍵、拿回工作，而過程中被告知一個沒發生過的手勢。

---

# 追記（2026-09-09）：第 42 道檢查跑過了，紅案也紅過了

**這一段是 append，上面一個字都沒有改。**

證據：`findings/evidence/096/product-path/`（兩份報告＋README）。兩趟都跑在**出貨的**
`e2-editor-v8` 與殼層 generation **v51** 上（`servedSha256 == declaredSha256 ==
2ffbec81…`，plain 那趟 `differingPaths: []`）。

| 趟 | 組成 |
| --- | --- |
| 無突變 | **40 PASS / 2 NE**，`ok: true` |
| `--mutate boundary-move-takes-no-checkpoint` | **39 PASS / 1 FAIL / 2 NE** |

紅的只有 `a-boundary-arrow-press-does-not-cost-the-work` 一格，NE 那一對沒有變。
組成從 39/2 走到 **40/2**，跟 amendment 寫的完全一樣。

- **無突變**：按鍵前 `#s-checkpoint` 是「無」、按鍵後是「有（r1）」；那一按**沒有
  被回答**（`stateAfterPress: recoverable-error`）；提示給 `rescue: "checkpoint"`；
  按下產品自己的按鈕之後 session 回到 ready，產品自己的存檔吐出的 ODT **含有**
  打進去的標記。`clausesExercised: ["B1","B3","B4"]`——**B2 不在裡面**，因為這棵樹
  沒有任何 artifact 會回答那一按。
- **有突變**：同樣七步，只差那兩行。按鍵前後都是「無」、`rescue: "none"`、提示
  逐字重現擁有者的句子、按下「重新開啟」之後回來的文件**沒有**那個標記。
  `servedShell.differingPaths` 指名被改的那個檔，所以那趟自己的誠實旗標看得到殼層動了。

## 這一輪的檢查自己逼出一次修改，記下來

第一版的檢查在 B1 失敗時**直接返回**，把 session 留在死狀態。`liveness.expecting`
的離場探測因此開火，突變那一趟報成 **STOPPED run** 而不是一格紅——雖然
`0 checks were never reached`（它是最後一格），但那讓這一格的正確性**取決於它排在
最後**。改成**兩個世界都按下產品提供的那顆按鈕**：`回到檢查點` 從檢查點重開、
`重新開啟` 從 authority bytes 重開，兩邊都回到可用的 session。

順帶把 B4 的**反面**變成量測而不是推論：沒有檢查點的產品上，回來的文件不含打進去的
字，報告直接這樣寫（`workCameBack: false`），不用讀的人自己推。

另外補了一個控制組：那一按必須 `defaultPrevented`（抄 `the-vertical-arrows-move-
the-caret`）。少了它，**頁面根本沒接走的按鍵**會讓 session 停在 `ready`，而這一格
會把它讀成「引擎回答了那一按」——正好是這棵樹今天沒有任何 artifact 能滿足的那一格
的假綠燈。

## 這一段仍然不改上面任何一句

**A 的效果還是量不到**：兩趟裡那一按都沒有被回答，`clausesExercised` 都沒有 B2。

---

# 連結之後的量測（2026-09-09，append-only）：那一按被回答了，而對照組照樣死

**這一段是 append，上面一個字都沒有改。**擁有者已經跑完那一次連結，
`dist/profiles/e2-editor-v14/` 存在，`probe.wasm` 是 `5847a1407d3af58f…`。

**判準是連結之前寫的**（`handoff/HANDOFF-2026-09-09-096-is-landed-in-source-and-
waits-on-the-same-link.md` 的「After the link, in this order」），本輪逐條讀回，
不另立驗收。證據：`findings/evidence/096/RESULT-after-the-link.md` 與五份新的 JSON。
**沒有建置、沒有連結、沒有動任何產品位元組**（`git status` 只有新檔）。

## 四條預測，逐條

| # | 預測 | 結果 |
| --- | --- | :---: |
| 1 | A：那一按被回答，session 留在 `ready`，探針報 `NOT_REPRODUCED` | **成立 10/10** |
| 2 | 對照組 v13 與出貨的 v8 照樣死，上下各 5/5 | **成立 20/20** |
| 3 | C 的 `with` 臂報 `ENGINE_ANSWERED` 而不是 `RECOVERED` | **成立，但要先把頁面指過去** |
| 4 | 產品路徑 40 PASS / 2 NE，第 42 道檢查第一次跑到 B2 | **成立，B2 真的被驅動** |

## 1 —— 那一按的數字（產品自己的 `#s-latency`）

| 按 | 次數 | 範圍 | 中位數 |
| --- | ---: | --- | ---: |
| 邊界前那一按（會動的） | 10 | 47–51 ms | 48 |
| **第一次的邊界按** | 10 | **623–958 ms** | **666** |
| 同一場後續的邊界按 | 50 | 259–263 ms | 261 |

261 是 250 ms 期限加上約 11 ms。判定之後（探針等滿 90 秒）的畫面是
`ready`、`revision 0`、`pending 0`、沒有提示、`#s-checkpoint 有（r0）`。
`firstNonMovingPress` 全部是 2，跟連結之前同一個位置。

## 2 —— 對照組：死法沒變，標籤變了，而變的原因量得到

v13 與 v8 各 10/10 進 `recoverable-error`。**但探針記的是
`DIED_WITH_CHECKPOINT` 不是 `REPRODUCED`**，因為 `REPRODUCED` 要求
`data-rescue: "none"`。兩臂的頁面位元組與連結前那兩趟**逐位元相同**
（`31787584…`、`1ec7baf9…`），引擎也相同，所以只差一件事：`dist/` 的殼層
現在帶著 C。

| | 連結前 | 本輪 |
| --- | --- | --- |
| outcome | `REPRODUCED` | `DIED_WITH_CHECKPOINT` |
| `data-rescue` | `none` | `checkpoint` |
| 按鍵後 `#s-checkpoint` | `無` | `有（r0）` |

**死沒有變，丟工作變了。**這是本輪順帶量到的：C 在兩顆凍結的引擎上，頁面固定不動，
效果分得開。順帶再確認一次那句提示仍然指名錯的手勢（「回到**選取手勢**前的檢查點」）
——**登錄，仍然不修**。

## 3 —— C：探針沒有 `--profile`，所以照字面重跑量的是 v8

`probe_096_checkpoint_before_the_gesture.py` 是拿 `dist/` 直接做鏡像的，而那裡的頁面
釘的是 `e2-editor-v8`。**照字面重跑量的是出貨的引擎**，於是「重跑報 `RECOVERED`
就代表期限不在 artifact 裡」這條推論對它不成立。兩趟都跑了：

- **C on v14**（探針一個位元組沒改，鏡像的 `e2-editor-app.js` 用
  `repointed_page()` 換掉，驅動程式 `run_c_on_v14.py` 一起存進證據）：
  **兩臂都是 `ENGINE_ANSWERED` 3/3**，`boundaryPressAnsweredSeconds` 六次都非 null
  （連結前六次都是 null）。**但那個數字是探針自己的 4 秒觀察窗，不是回答時間**——
  它只說「session 沒死」。`with` 臂照樣存下 `有（r1）`，`without` 停在 `無`。
- **C on 出貨頁面（探針不改）**：`without` **WORK_LOST 3/3**、`with`
  **RECOVERED 3/3**、`armsDisagree: true`——與連結前逐格相同。C 在出貨位元組上仍然成立。

**C 在 v14 上還走得到嗎？這個手勢走不到了。**兩臂都被回答，兩臂都不丟工作，
`armsDisagree` 是 false，紅案在這顆引擎上不再有鑑別力。C 只在沒有移動期限的引擎上
還可證偽。

## 4 —— 第 42 道檢查：B2 第一次真的被驅動

`tools/run_e2_c_product_path.py --profile e2-editor-v14`，無突變：
**42 格 40 PASS / 2 NE / 0 FAIL**，`ok: true`，NE 那一對沒變，
`servedShell` 是 bundle v51、`differsOnlyInTheEntrypoint: true`。

`clausesExercised` 從連結前的 `["B1","B3","B4"]` 變成 **`["B1","B3","B2"]`**。
不是宣告，是量到的：`takenByThePage: [true]`（`defaultPrevented` 對照組有燒過）、
`theEngineAnsweredThePress: true`、`stateAfterPress: ready`、
打字把 revision 推到 1 而那一按沒有再動它、`#s-checkpoint` `無` → `有（r1）`。

## 預測沒有預期到的六件事

1. **第一次的邊界按是 623–958 ms，不是 261 ms。**10/10、兩個方向都這樣，同一場裡
   後續每一按都回到 259–263。那一按仍然被回答、session 仍然可用，所以沒有任何判準
   因此不成立；但「250 ms 回答」不是第一按在做的事。**本輪不指認成因。**
2. **`boundaryPressAnsweredSeconds` 量的不是回答。**它是 `presses[-1]["seconds"]`，
   而邊界的游標永遠不動，所以那個觀察窗一定跑滿。只有它是不是 null 有意義。
3. **A 探針的對照組不再說 `REPRODUCED`。**死法沒變，但拿 outcome 字串去對
   `RESULT.md` 的 40/40 會看到二十格變了，而原因在殼層不在引擎。
4. **B4 在 v14 上不再被執行。**session 不死，就沒有提示可按，也就沒有人問「回來的
   文件含不含打進去的字」。出貨 profile 上這一格跑 B1/B3/B4，v14 上跑 B1/B3/B2——
   **沒有任何單一一趟同時蓋到四條**，而且安靜掉的正好是 C 存在的理由那一條。
5. **後續步驟 3 照字面跑不出它要的答案**（見上）。
6. **`build/archive/` 裡沒有 v14。**手冊的步驟 1（記五個雜湊、立刻 archive）還沒做，
   那是擁有者的步驟，本輪沒有代做。

## 仍未量

第一按為什麼與其餘不同；**這條路在負載下的表現**（本輪刻意一次只跑一顆瀏覽器）；
Home／End 與兩個字元移動；250 ms 在長文件上夠不夠、落到讀回的發生率；任何 v1 profile
（`editor-shell/editor-client.js` 仍然會拒絕 `verified-move-readback`，本輪沒有動過
也沒有量過任何 v1 artifact）。

---

# 追記（2026-09-10）：B4 的缺口由擁有者裁 a，第二個誘因已落地——**但還沒跑**

**這一段是 append，上面一個字都沒有改。**

連結之後那一段的第 4 件「預測沒有預期到的事」登錄的是：**B4 在 v14 上不再被執行**，
`clausesExercised` 在 v14 是 `["B1","B3","B2"]`、在出貨的 v8 是 `["B1","B3","B4"]`，
**沒有任何單一一趟同時蓋到四條，而安靜掉的正好是半 C 存在的理由那一條**。兩個選項是
(a) 補第二個誘因，讓 B4 在修好的 profile 上到得了；(b) 寫下「B4 只在出貨那一側有意義」。

**擁有者 2026-09-10 裁 (a)。**協定
`handoff/tasks/TASK-2026-09-10-096-b4-second-inducer.md`（**寫在 runner 被改之前**）、
閘門 amendment 在 `handoff/PLAN-2026-08-28-the-v11-cutover-horizon.md` 的同日那一段
（append-only，並指名它取代 2026-09-09 那份裡的「**B4 is exercised only while the
press wedges**」那一條——那條預測逐字成立，擁有者裁定它不可接受）。

## 換掉的只有「殺」那一步

誘因沿用 `recovery-returns-what-the-product-promised` 的那一支（`induce_worker_failure`，
worker 裡一個真的未捕捉錯誤，從產品外面誘發，不依賴任何缺陷）。那一按被回答之後：
發火 → 等 `dead_session`（90 秒是上限不是預期）→ **按下去之前先讀宣告** → 按產品
自己的提示 → 等 ready → 走產品自己的存檔鍵 → B4 ＝存出來的 ODT 含不含那個標記。

**手勢照樣先發生、照樣先存它自己的檢查點**，所以受測的性質沒有變：半 C 在**這一按
之前**存的那個檢查點能不能把打進去的字帶回來。

**因此多一條必要條件，而它不是裝飾**：`declaredCheckpointAfterFallback` 要以「有」
開頭且含 `r{revisionAfterTyping}`——**跟 B3 讀 `checkpointAfterTheKey` 是同一個
判別式**，兩格不會各自漂。死是從外面誘發的，「有檢查點」本身**不再**能證明那是方向鍵
存的；不符就 B4 False，`why` 指名「提供的不是這個手勢的檢查點」。

`B1` 仍然是**那一按**的判定。誘發的死不是那一按，不准被讀成那一按。
`b4Inducer` 進 verdict（`"boundary-press"`／`"worker-failure"`／`null`），
**死掉那一支只多這一格**，其餘逐格是 `plain-e2-editor-v8.json` 押下的那些。

AGENTS.md §3：登錄為**設計好的哨兵，不是洞**——帶著 A 的 profile 上那個手勢**殺不死**
session，那正是 A 在做的事。§4：不是新機制，沒有產品位元組、沒有引擎改動、沒有連結。

## 「B4 沒被執行」判 FAIL，不判 NOT_ESTABLISHED

決定與理由都寫下來，因為 §3 要求這兩種登錄不准寫成同一句話：

- 前例的規則是「NE 只留給**沒有任何誘因到得了那個狀態**」，而正是那句話判掉了 NE：
  v14 上這一格**報的是 PASS** 而 B4 是安靜的，降成 NE 只會讓**整趟**維持綠燈
  （`report["ok"]` 不算 NE），把同一個洞藏得更安靜一格。2026-08-27 的裁決對**這支
  誘因的出處那一格**就叫過那個形狀「穿著 NE 戲服的 finding」。
- 它也不是「沒量到」：B1、B2、B3 都被驅動、都有回報。這一格是**量到了而沒達到自己的
  要求**，那就是 FAIL。
- 真正到不了的前置條件（沒有 CDP、profile 不提供 `move-line-up`）**在那支函式上游就
  已經是 NE**，所以一趟 Firefox 不可能跑出這種紅。
- `B4` 在那個狀態留 `null` 而不是 `false`：這一趟從來沒有宣稱工作沒回來，只說沒有人問。

**先寫下來的代價**：`induce_worker_failure` 若因為儀器原因失效，這一格會在每一顆修好的
profile 上紅到有人去看。這是 (a) 的標價。

## 三個紅案（欄位值寫在程式碼之前，協定 §4）

| 紅案 | 逼出來的狀態 | 要紅在哪 |
| --- | --- | --- |
| `boundary-move-takes-no-checkpoint`（既有） | 半 C 那兩行拿掉 | **B3 與 B4 都紅**（以前只有 B3） |
| `worker-crash-throws-the-checkpoint-away`（新） | crash 那一支在進 recovery 前把檢查點丟掉 | **B3 綠、B4 紅**——單一子句分不出來的那一對 |
| `worker-crash-is-never-noticed`（新） | 同一支被關掉，誘因發火而產品沒注意到 | **B4 `null`、`clausesExercised` 沒有 B4、這一格 FAIL** |

兩個新的都在 `editor-shell/editor-session.js` 的 `worker-crashed` 那一支，一趟裡沒有
別的東西到得了那裡（`induce_worker_failure` 另一個呼叫點只在 038 不再重現時發火，而
038 在 v8 與 v14 上都還重現）。所以 `alsoRed` 刻意是空的，**紅到別格就是把這個宣稱
證偽**。三個 pattern 在 `dist/` 各比到剛好一次，改完的檔 `node --check` 都過。

## 本輪**沒有**量到的（不得被上面的文字蓋過去）

**一次瀏覽器都沒開。**T8a 是靜態的：協定、amendment、runner、三個 mutation 進樹，
只跑 `make test-e2-c-static`（exit 0）。**三個紅案與三趟 v14 無突變、一趟 v8 對照，
全部是 T8b 的事**，而且在它們跑過之前，這條收緊**不生效**、組成退回 2026-09-09 登錄
的那一版。落地前我只用 stub 把四種呈現的控制流跑過（無瀏覽器）：
`B4` 依序是 `true`／`false`／`null`／`null`，後兩者 `clausesExercised` 沒有 B4、
`ok: false`。**那驗的是判定組成，不是產品。**

四條具名極限也先寫在協定裡：`Target.setAutoAttach` 兩個呼叫點的**順序依賴**（今天只有
一個會發火，因為 038 還重現）；`maxWorkerGenerations` 預設 3 而這一臂用到 2，**不能再
長出第三次回復**；使用者不會故意弄死 worker，所以這一臂量的是「產品在一個它本來就在
處理的崩潰類別之後怎麼做」；以及**v14 上的 B4 比出貨那一側的 B4 弱**——它說的是「手勢
存的檢查點在另一個死因之後還活著」，不是「那個手勢自己的死還回得來」。**不得拿一趟
v14 去引用較強的那個宣稱。**

## 預設結論（若這件事永遠沒做完）

B4——「回來的東西含不含打進去的字」，也就是半 C 存在的理由——**在每一顆帶著 A 的
profile 上都沒有人守**，而且檢查會一直報三條子句的 PASS，讀的人不開 JSON 看不出少了
哪一條。若 T8b 跑了而誘因永遠不發火：射程不存在，這一格在修好的 profile 上是紅的，
決定回到擁有者手上（(b) 或第三個誘因）——**不得靠「把紅留著」偷偷選 (b)**。

---

## T8b 量完了：B4 在修好的 profile 上回到射程內（2026-09-10，只 append）

上一節的預設結論沒有用到。七趟全部押在 `findings/evidence/096/product-path/`，
判讀在 `RESULT-b4-second-inducer.md`；下面的數字是主 session 用自己的讀取器重讀
七份 JSON 得到的，不是抄 T8b 的摘要（第一版讀取器猜錯 schema、每格印出 None，
是印出來的原始值抓到的，照 AGENTS.md §7）。

| 趟 | profile | 突變 | 這一格 | B1–B4 | clausesExercised | b4Inducer |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | v14 | boundary-move-takes-no-checkpoint | FAIL | T T F F | B1 B3 B2 B4 | worker-failure |
| 2 | v14 | worker-crash-throws-the-checkpoint-away | FAIL | T T T F | B1 B3 B2 B4 | worker-failure |
| 3 | v14 | worker-crash-is-never-noticed | FAIL | T T T null | B1 B3 B2 | worker-failure |
| 4–6 | v14 | 無 | PASS ×3 | T T T T | B1 B3 B2 B4 | worker-failure |
| 7 | v8 | 無 | PASS | T T T T | B1 B3 B4 | boundary-press |

**三個紅案各只紅這一格**（`alsoRed: []` 成立，對照組是第 4 趟）。(i) 同時紅 B3
與 B4，這是「B4 回到射程」的可量證明——連結之前它只能紅 B3；(ii) B3 綠而 B4 紅，
死掉時宣告變成 `無`、提示給的是重新開啟——這是任何單一子句的檢查分不出的那一對；
(iii) `B4: null`、`clausesExercised` 沒有 B4、判 **FAIL 不判 NE**，誘因發火了但產品
沒察覺（`stateAfterFallback: ready`）。

**v14 三趟全過**：誘因 6/6 發火（三個紅案加三趟平跑）、死後宣告 `有（r1）` 就是這個
手勢押的、提示給 `checkpoint`、按下去存出來的檔含標記。組成不變，40 PASS／2 NE。

**出貨的 v8 逐格不變**：`clausesExercised` 仍是 `[B1,B3,B4]`，`boundary` 酬載裡只多
一格 `b4Inducer: "boundary-press"`，`savedBytes` 差 1 位元組（平跑之間本來就會差）。
`compare_b4_cells.py` 可重跑。**038 在七份報告都仍重現**，兩個新突變的
`alsoRed: []` 宣稱靠的是這一格。

### 這一格現在能宣稱什麼、不能宣稱什麼

- v14 上的 B4 是**比 v8 上的 B4 弱的宣稱**：它證明的是「手勢押下的檢查點撐得過另一
  種死法」，不是「那一按弄死 session 之後救得回來」——後者在帶 A 的 profile 上由設計
  不可觸及。引用時不得拿前者當後者。
- 誘因是儀器（CDP 的 `Target.setAutoAttach` 送進 worker 的真實未捕捉錯誤），失敗是
  產品自己的。若誘因因儀器原因失效，這一格在每一趟固定 profile 上都是紅的，直到有
  人去看——這是寫在程式碼裡的已接受成本，取代「一趟不能引用 B4 卻不自己講的綠」。
- Worker generation 預算是 3：初開第 1 代、recovery 那格第 2 代、這一格回復第 3 代。
  v8 與 v14 用量相同，七趟沒有一趟撞到 `WORKER_GENERATION_LIMIT`。

### 量到但不解釋

- `savedBytes` 在四次未突變的存檔取了四個值（12895／12897／12899／12899）。
- `offPageInk.scans` 在本應相同的 v14 平跑之間是 38 或 39。

### 還開著的（不因這一節改變）

提示句子指名錯的手勢（061 的形狀）、094／095／097、核心在邊界為何不廣播——
都還是 09-10 交接列的那幾條。closing 這一節唯一關掉的是「B4 沒人守」。

## 主 session 的 pre-read：T10 的判決存活，但它靠的最後一個前提要點名（2026-09-10，只 append）

T10（sonnet）量了四臂，RESULT 判 **M2 confirmed**。照 AGENTS.md §8，終止宣告不由
起草方承載，主 session 用自己的讀取器重讀四份 JSON 的逐按鍵 `pressTrace`，並讀了
RESULT 引用的每一行原始碼。判決存活，下面是核對後要釘死的幾點。

**四臂的引擎側簽名（主 session 讀 `pressTrace`，不是抄 SUMMARY）：**

| 臂 | 受測那一按 | lokIds | 引擎事件索引 | sink | 結果 |
| --- | --- | --- | --- | --- | --- |
| P′ | 第二次 Home | `[5]` | 24→27（動了） | 100→100（不變） | 靜、死 |
| G | 第三次 Home | `[8]` | 30→31（動了） | 100→100 | 靜、死 |
| N | 第二次 ArrowDown | `[5]` | 23→26（動了） | 356→356 | 靜、死 |
| C | 唯一那一按（真邊界） | `[]` | 19→19（**沒動**） | 356→356 | 靜、死 |

**我一度以為 C 和其他三臂矛盾，讀原始碼後解消了。**C 什麼都沒吐（索引凍住、零
callback），P′／G／N 的靜默按鍵卻吐了 id 5 或 id 8。看起來像兩種機制。但
`SwVisibleCursor::SetPosAndShow`（`viscrs.cxx:222-262`）對游標矩形的
`INVALIDATE_VISIBLE_CURSOR` 通知**沒有「矩形沒變就跳過」的守衛**（頁碼通知有，游標
通知沒有）——所以只要 `UpdateCursor` 跑了就會 enqueue 一則 id 1，矩形不變時它在 flush
被當重複丟掉。C 是「孤零零一則被去重的 id 1，旁邊沒有別的事件」；P′／N 的 id 5 來自
`SwCursorShell::ShowCursor`（`crsrsh.cxx:2900`，和 id 1 不同路），且**和存檔活動
（`saved` 事件、半 C 押檢查點）綁在一起**，是順帶的，不是那一按的移動產生的。所以
三臂不是不同機制，都是「id 1 被去重」；C 沒有順帶事件而已。

**判決靠的、而且只靠的最後一個前提：那一按有沒有讓 `UpdateCursor` 跑起來（閘門開）。**
- 直接量到的：每一次靜默按鍵都沒有 id 1／id 2 到達引擎、矩形沒變；每一次被回答的
  按鍵（矩形有變）id 1 在 0.2 秒到達並完成。
- **沒有**直接量到的：那一則 id 1 是「enqueue 了然後被去重」還是「根本沒 enqueue」。
  去重發生在 `CallbackFlushHandler`（`init.cxx:1592-1600,2529-2537`），在 `onLokCallback`
  的**上游**，所以瀏覽器這一側看不到被丟掉的那一則——原理上看不到，不是沒量到。
- 因此「閘門開」這件事，對 C（真邊界）是**純原始碼推論**（tdf#150457 的分支
  `swcrsr.cxx:2117` 在端點呼叫 `UpdateCursor` 再設 `bRet=false`）；對 P′／N 的 id 5
  只是**不乾淨的佐證**（ShowCursor 會呼叫 UpdateCursor，但這裡的 id 5 和存檔綁著）。

**結論：M2 是一個「原始碼支持的推論」，RESULT 的第 138-144 行誠實地這樣標了，沒有
overclaim。**但這份協定已經兩輪在修主 session 的原始碼讀法（Supersession 1／2），把
最終結論壓在「閘門開」這個還沒被直接觀測的前提上，正是這條線最會出錯的地方。直接
把它從推論變成觀測，只差 core 自己那句 `SAL_INFO("lok", "Skipping duplicate …")`
（`init.cxx:2533`）——那要一顆 native core build，而擁有者 2026-09-10 指正過那是
一兩小時、負擔得起的。處置見下一節；**瀏覽器能給的已經到頂**。

## arm U（native）直接觀測：沉默就是 flush 丟掉沒變的游標 callback——前提變成觀測（2026-09-10，只 append）

擁有者裁定跑 arm U。不用 build：既有的 `native-lok-26-8/build` 是 `ENABLE_SAL_LOG=TRUE`。
harness `tools/f096_native_dedup.cpp`（判準先釘在協定的「Arm U is runnable today」）
在 `SAL_LOG="+INFO.lok"` 下跑 `Ctrl+Home → End → Home(A) → Home(B)`，每按鍵前往
stderr 印 marker 以逐按歸屬。三輪一致，證據在 `findings/evidence/096/native/round-*/`
（逐字 `sal.log` ＋ `presses.jsonl`）。

| 受測按鍵 | 矩形 | 交付 type 1 給 callback | 該按視窗內的 `Skipping duplicate [1]` |
| --- | --- | --- | --- |
| A：Home（行尾→行首） | 變 | **有** | **無** |
| B：Home（已在行首） | 不變 | **無** | **有**：`Skipping duplicate [1]: [1418, 1418, 0, 280]` |

那個 `[1418, 1418, 0, 280]` 就是游標矩形，和 press A 的結果一字不差。所以 press B 時
**core 確實 enqueue 了一則 `INVALIDATE_VISIBLE_CURSOR`**（閘門開、`SetPosAndShow`
沒有矩形守衛就通知了），而 `CallbackFlushHandler` 在送到 client 之前把它當重複丟掉
（`init.cxx:2535`）。這正是瀏覽器量到的「沒有 type 1、session 楔住」。

**上一節（pre-read）點名的那個唯一前提「那一按讓 UpdateCursor 跑了」現在是觀測不是
推論**：dedup 的 log 指名它丟掉的型別，而能 log 就代表那則通知被 enqueue 過。儀器
紅案也過：press A（矩形變）的視窗沒有 skip-[1]，三輪皆然。

**結論定案**：096 邊界那一按的沉默＝LibreOfficeKit 自己的 flush 去重把「矩形沒變的
游標通知」丟掉，引擎的移動路徑在等一則永遠不會出來的 callback。**不是上游缺陷**
（去重是刻意的），缺陷在引擎那條移動路徑的契約，半 A（250 ms 期限）就是對的修法。
T10 的 C 臂（零事件、索引凍住）是同一機制——孤零零一則被丟的 id 1，旁邊沒有別的事件。
「核心為什麼在邊界不廣播」這一題到此收掉。

