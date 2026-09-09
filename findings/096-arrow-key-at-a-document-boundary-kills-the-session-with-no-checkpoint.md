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
