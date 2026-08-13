# DEVLOG 2026-08-05 — LOK selection readback 修復與 forward delete completion 兩次根因改判

給一起研究的同事：這份是本輪的交接摘要。兩件事，一件修好了，一件**歸因錯了而且已經改判**。

完整證據在對應的 finding；這裡只寫「發生什麼、為什麼、接下來卡在哪」。

- Finding 017：`findings/017-lok-collapsed-selection-readback.md` — **已修（SDK側），實測通過**
- Finding 016：`findings/016-lok-forward-delete-completion-gap.md` — **scheduler假說已否證；SDK歸屬缺口，不可送單**

Core 基線：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`（LibreOffice 26.8）。

---

## 一、Finding 017：空 selection 無法表達（已修）

### 症狀

搜尋選取後把 selection 收成 caret，第一個公開 readback `DocumentHandle.getSelection()` 不是回空字串，而是：

```text
LOK_ERROR: Flavor text/plain;charset=utf-16 is not supported
```

E1 人工刪除流程因此在 delete 之前就停住。

### 根因（已觀察）

錯誤訊息裡的 UTF-16 不是誰偷改了 MIME type。鏈條是：

1. SDK 送的是 `text/plain;charset=utf-8`
2. `getFromTransferable()` 把它 canonicalize 成內部 `text/plain;charset=utf-16`（`init.cxx:5844`）
3. caret-only selection 的 transferable 沒有這個 flavor → 回 false（`init.cxx:5873`）
4. `doc_getTextSelection()` 因此回 `nullptr`（`init.cxx:5941`）
5. 我方 `handleGetSelection()` 把**任何** nullptr 都升格成 `LOK_ERROR`

於是「沒有選取」這個完全正常的狀態，跟「真的讀取失敗」共用同一個結果。

最能說明問題的是：同一份 `probe_engine.cpp` 裡，`handleEditorGetState()` 拿到**一模一樣的** nullptr，卻安靜地
序列化成 `selectionText:""`。**兩個 readback contract 對同一件事的處理互相矛盾**——這才是缺口所在。

### 修法

改用 `getSelectionTypeAndText()`，`none`／`text`／`complex` 三態分流。**不需要修改 LibreOffice core。**

但要注意它有效的原因跟直覺不同：這個 API 走的是**同一條** `getFromTransferable()` 路徑（`init.cxx:6019`），
一樣會踩到缺失的 flavor。差別只在錯誤對應——`!bSuccess` 時回 `LOK_SELTYPE_NONE` 而非 nullptr。

### 一個做不到的要求，以及繞法

原本待辦寫著「區分真正沒有 selection 與 flavor 意外缺失」。**在 LOK C API 層做不到。** core 自己已經先把三種
狀態塌成同一個 `NONE`（`init.cxx:6019-6026`）：

1. `getSelection()` 回 null
2. flavor 查不到
3. 讀取成功但字串為空

已排除的替代路徑：`getSelectionType()` 同樣合併；直接要求 utf-16 命中同一 flavor；`doc_getClipboard()` 雖會列舉
flavor 但讀的是**剪貼簿**不是 selection，還得先 copy 造成 mutation。

**改用兩條獨立路徑交叉驗證**——不要求單一 API 自我區分：

| 路徑 | 判準 |
|---|---|
| transferable | `selectionType === "none"` |
| callback | `selection.observed && selection.collapsed` |

兩者一致才視為 caret；不一致就是「flavor 缺失但 selection 還在」，拒絕 dispatch。callback 路徑走的是
`LOK_CALLBACK_TEXT_SELECTION`，與 transferable／flavor 邏輯完全無關。

### 實作時發現的三個坑（都會咬人）

1. **`kitError()` 有陳舊訊息。** `getFromTransferable()` 設了 last-exception 後，`getSelectionTypeAndText()`
   在回傳 `NONE` 前**沒有清掉**。照舊習慣讀 last-error 判斷成敗，會原地再噴同一個 `LOK_ERROR`。
   **一律以回傳值為準。**

2. **`text === ""` 不足以判斷空選取。** `complex` selection 的 text 同樣是空字串。必須判斷 `selectionType`。

3. **`collapsed` 在首個 callback 到達前只代表「未知」。** 初始狀態下矩形本來就是空的。因此新增
   `selection.observed`；沒有它，交叉驗證從一開始就是假的。

同理，worker 在欄位缺失時預設 **`"unknown"` 而非 `"none"`**——舊 engine 不送此欄位，預設成 `none` 會讓 caret
前置條件在 selection 仍存在時通過，正是最危險的方向。

### 驗證狀態

編譯兩種組態通過、SDK 單元測試 16 項、`make test-e1-a-static` 全套通過、artifact 已重建並在 Chrome 150 /
Firefox 153 實測通過。

**證據強度限制**：只有一輪逐字 log，且該 excerpt 未標示瀏覽器；「兩個瀏覽器都通過」為操作員回報。已跑情境只有
`delete-backward`；`delete-forward`、`complex` selection、段落邊界都還沒跑。

---

## 二、Finding 016：completion callback 缺口（原生對照後的中間歸因，後續再修正）

### 原本的結論

forward delete 確實改了文件，但沒有可歸屬的 completion callback，SDK 只能等 30 秒 timeout。先前記為
「LibreOfficeKit 公開能力缺口」，`是否上游` 標「未確認」。

### 本輪新增的觀察

017 修好後回來測，同一份 log 再次證實缺口仍在，而且比原本更嚴重——delete 前後兩次讀取之間：

```text
sourceSequence          8 → 8      任何 callback 都沒有
documentChangeSequence  0          從未收過 INVALIDATE_TILES
a11y.observed           false
```

但文件確實改了（`revision 0→1`，字串驗證通過）。

### a11y 路線：試過，不通，而且知道為什麼

`LOK_CALLBACK_A11Y_FOCUS_CHANGED` 的 payload 帶完整段落內容，且**只在段落文字真的不同時才發**
（`sfx2/source/view/viewsh.cxx:1205`，`if (m_sFocusedParagraph != sText)`）。看起來正是需要的權威判準。

實測完全沒有抵達（`observed:false`、`changeCount:0`、`unparsedCount:0`——`unparsedCount` 是刻意分開計的，
否則「沒有內容變更」會跟「callback 有來但讀不懂」混在一起）。

順帶查明了**為什麼 016 的 attempt-03 到 05 會白費力氣**：

- `SetLOKAccessibilityState()` 有兩處**靜默** early return（`viewsh.cxx:3486` 的 `!pWindow`、`:3492` 的
  `!xAccessible.is()`），呼叫端無從得知 listener 有沒有掛上
- `getA11yFocusedParagraph()` 只序列化 listener 的快取成員，未掛上時回
  `{"content":"","position":0,"start":-1,"end":-1}`

**「listener 沒掛上」與「段落真的是空的」在輸出上完全一樣。** 那三輪等於在跟一個測不出來的東西搏鬥。

### 原生對照：結論反轉

所有證據都來自 headless WASM profile，而 `findings/README.md` 送單第一條要求在上游預設組態重現。因此建置了
原生 26.8（刻意停用 qt5／qt6，確保 `vcl/qt5/QtFrame.cxx` 的既存本地修改不入編；其餘本地修改都是 emscripten
專屬。**對照組不含任何我方 patch**）。

原生結果：

```text
.uno:StateWordCount=20 words, 94 characters    ← delete 前
.uno:StateWordCount=20 words, 93 characters    ← delete 後
```

原生發出 **185 個** `STATE_CHANGED`，含這個內容衍生訊號。而我方 WASM profile 整場 session `format` 都是
`{bold:null, italic:null}`——原生明確發出 `.uno:Bold=false`，**代表整條延遲型 STATE_CHANGED 串流沒有抵達
WASM 側**。

關鍵在時間戳：

| 事件 | 時間 |
|---|---|
| delete 送出 | 2268 ms |
| `UNO_COMMAND_RESULT` | 2269 ms |
| 大量 `STATE_CHANGED` | **2870 ms**（晚 600ms） |

這些是 idle／scheduler 驅動的延遲回呼。而 `probe_engine.cpp` 裡 `runLoop`、`unipoll`、`Yield`、`Scheduler`
**一個都沒有**——引擎同步呼叫完 LOK 就回去等下一個命令，主迴圈從未執行。

COOL 怎麼做（唯讀參考 checkout `cool-26-04`）：

- `kit/SetupKitEnvironment.hpp:66`：`options = "unipoll"`
- `kit/Kit.cpp:3561`：`loKit->runLoop(pollCallback, wakeCallback, mainKit.get())`
- `Kit.hpp` 註解：「Handle the poll from the unipoll callback」

（名稱有出入：COOL 設 `SAL_KIT_OPTIONS`，26.8 core 讀的是 `SAL_LOK_OPTIONS`（`init.cxx:8083`）。實作以 core
為準。）

### 改判

> 以下是原生對照完成當下的中間結論；本文件第五節已用WASM直接實驗否證主迴圈部分。

**LibreOfficeKit 並不缺 mutation acknowledgement；是我方執行模型缺少 LOK 預期的主迴圈。** 同步發出的 callback
照常抵達，延遲型的永遠不會 flush——這與所有既有觀察吻合，也解釋了初期那次 30 秒 timeout。

`是否上游` 已改為 **否**，**不可送 Bugzilla**。先前若照原定位送出，會是一張站不住腳的單。

一次隔夜建置的成本，遠低於送錯單對後續回報可信度的損害。

### 未解問題

原生在 drain 1500ms 後**同樣**完全沒有 `INVALIDATE_TILES`。COOL 顯然依賴它重繪，這裡仍有沒搞懂的地方。
**本輪結論不建立在 tile invalidation 上**，而是建立在 STATE_CHANGED 串流的有無對比。

---

## 三、當時接下來卡在哪（下方第五節已完成）

### 下一個最小測試

在 WASM 引擎裡讓 LO scheduler 實際跑一次，看 `STATE_CHANGED` 會不會出現。這是把上面的**推論**升格為**已觀察**
的最小成本實驗。在它通過之前，不要據此改架構。

### 如果成立，規模不小

`runLoop` **不會返回**——它接管執行緒。所以不是「加一行 Yield」，而是控制反轉：LOK 主迴圈擁有 Worker 執行緒，
命令處理搬進 `pollCallback`。會影響 request 序列化、`BUSY` 語意、close／teardown 路徑。

好消息是不用自己摸索：COOL 的 `kit/Kit.cpp` 是同一個 monorepo 裡的可運作範例，而且 `cool-26-04/wasm/` 還有
COWASM host 層可以參照。

### 待確認

`.uno:StateWordCount` 是否足以承擔 per-operation 的 changed 判定，還是需要搭配其他訊號。注意
`.uno:ModifiedStatus` 是 latch（一旦 true 就不再變），不能當 per-operation 訊號。

`UNO_COMMAND_RESULT` payload 裡有個 `wasModified` 欄位，本輪觀察到它在文件確實被改的情況下仍為 `false`。它
緊鄰 `saveDurationMics`，推測描述的是儲存狀態而非內容變更。**未加採用，也未深究。**

---

## 四、方法上的兩點，值得帶到下一輪

**一、負面結果要能證明自己有效。** 原生探針刻意先讀全文長度、刪除後再比一次，delete 沒執行就標 `DISCARD`。
否則「沒有 callback」會是假陽性——看起來證實了假設，其實什麼都沒證明。這是這類實驗最容易騙人的地方。

同理，`a11y.unparsedCount` 與 `selection.observed` 都是為了讓「沒觀察到」與「觀察到空值」不會混為一談。

**二、送單前的上游對照不是形式。** 016 差一點就以錯誤定位送出去。真正翻案的不是更用力測 WASM，而是花一晚
建一個乾淨的原生對照組。

---

## 附：本輪改動的檔案

**Finding 017 修正**

- `wasm_sdk_probe/src/probe_engine.cpp` — `readSelection()`／`selectionTypeName()`；`handleGetSelection()`
  三態分流；`handleEditorGetState()` 語意對齊；`EditorState.selectionObserved`
- `wasm_sdk_probe/sdk/sdk-worker.js` — 轉發 `selectionType`／`selectionTextMissing`，缺失時預設 `"unknown"`
- `wasm_sdk_probe/sdk/document-sdk.d.ts` — `SelectionType`
- `wasm_sdk_probe/web/e1-manual-delete-app.js` — 前置條件改用新契約；delete 後加延後狀態讀取
- `wasm_sdk_probe/sdk/tests/document-sdk.test.mjs` — 5 項 selection 契約測試

**Finding 016 診斷（僅觀測，不改行為）**

- `wasm_sdk_probe/src/probe_engine.cpp` — a11y 封閉觀測計數（原始 payload 不外流 JS，維持
  `rawCallbackExposed: false` 不變式）
- `wasm_sdk_probe/tools/finding_016_native_lok.cpp` — 原生對照探針
- `wasm_sdk_probe/tools/run_finding_016_native.sh` — 一鍵重跑
- `build-native-26-8/` — 原生對照建置（out-of-tree，未觸碰 worktree）

---

## 五、Scheduler最小實驗完成：主迴圈假說被否證

本節是本DEVLOG的最新狀態，取代第二、三節對WASM主迴圈的中間推論；原段落保留作失敗歸因歷程。

### 已觀察

- Core已有`unit_lok_process_events_to_idle()`，且符號已在現有WASM linkdeps中；因此只建獨立
  `finding-016-scheduler` profile，未修改或重編Core。
- Chrome 150與Firefox 153都在forward delete後先回command result；immediate typed word-count計數為0。等待
  1000 ms後，尚未進入顯式drain，計數已變1且值為`20 words / 93 characters`。
- 兩邊顯式drain的state與word-count增量都是0；`schedulerHypothesisSupported:false`。
- 兩邊字串均精確由`0123456789`變為`123456789`，輸出ODT ZIP完整，沒有raw callback、任意UNO、任意keycode或retry。
- 第一次Chrome在timer到期前立即drain，未見word-count；第二次已看見自然callback但classifier比較錯誤；第三次修正
  判定後通過。三輪原始結果全數保留，沒有只留最後成功結果。
- Machine summary：`findings/evidence/016/scheduler-wasm/summary.json`，兩瀏覽器皆
  `WORD_COUNT_CALLBACK_DELIVERED_WITHOUT_DRAIN`、整體`pass:true`。

### 推論

- 「WASM沒有驅動LOK scheduler／main loop」不成立，不需為Finding 016導入不返回的`runLoop`控制反轉。
- 舊probe只把少數format state轉成typed state，completion也只接受tile／caret／selection；已抵達的word-count
  state沒有進入request completion。`sourceSequence`不變證明的是**我方分類沒有前進**，不是底層callback不存在。
- Finding 016現在是我方SDK callback分類／completion歸屬問題，仍不可送Bugzilla。

### 待驗證

- `StateWordCount`特定payload是否屬足以承諾的穩定公開契約。這次parser明確限定diagnostic，不得直接升格產品API。
- 若可承諾，下一個remediation是closed、單mutation-in-flight的typed barrier，需涵蓋delete／backspace、no-op、
  段落邊界、stale、timeout及recovery；若不可承諾，縮小delete capability。
- E1維持`STOP_OR_RESCOPE`，E1-B／C仍不啟動。
