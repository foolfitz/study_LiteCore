# Ctrl+A 全選：v25 上動作 21 走哪條路（2026-10-29，工單 v26 select-all 的研究筆記，第一部分）

## 結論與這次的範圍

**v25 的引擎有編進全選，有序引擎也會把它送上按鍵路徑；產品上擋住它的是 manifest（`gestures: []`）與殼層的封閉清單，不是引擎缺路由。**所以「開放全選」原則上**不需要重新連結**：要的是 (1) 一份把全選的 gesture 給出去的新 manifest（manifest 被綁著，所以是新的 profile 身分），(2) 殼層 client 接受 `select-all` 並給它一個 postcondition 類別（殼層的新 generation），(3) 頁面綁 Ctrl+A／Cmd+A。但**能不能開放，要先量它在 v25 上到底做了什麼**（第 2 題），這次還沒量。

擁有者 2026-10-29 決定把全選排進下一個引擎批次（v26）。本筆記回答工單的第 1 題，第 2–4 題列出要量什麼、怎麼量，沒有執行任何量測。路由的逐行追蹤由一個 subagent 做，主 session 讀過下面引用的每一處原始碼後才採用。

## 第 1 題：動作 21 在 v25 上的路

〔讀原始碼〕**define 組**取自 v25 實際的編譯紀錄 `wasm_sdk_probe/build/link-v25-feature-01.log`（四個物件同一組旗標）：`OXSDK_EDITOR_DISCOVERY`、`OXSDK_FINDING_016_SELECTION_BARRIER`、`OXSDK_E2_FORMAT_BARRIER`、`OXSDK_MERGE_KEY_UNDO`、`OXSDK_E2_V20_LINK_BATCH`、`OXSDK_E2_V21_LINK_BATCH`、`OXSDK_MAINLOOP_ENGINE`、`OXSDK_E2_V23_LINK_BATCH`、`OXSDK_E2_V23_FEATURE_ABI6`、`OXSDK_E2_V24_TYPED_INSERT`、`OXSDK_E2_V25_FORMAT_PROOF`。

〔讀原始碼〕產品上的呼叫依序經過三道關，**第一道就停**：

| 關 | 位置 | v25 的結果 |
|---|---|---|
| 殼層 client | `editor-shell-v2/narrow-editor-v2-client.js:414-419`：`select-all` 不在 `INHERITED`／`APPENDED` | 丟 `EDITOR_ACTION_UNSUPPORTED`，不送 request。就算送了，`postconditionClassOf("select-all")` 回 `null`（`:191-198`），回覆會被判 `EDITOR_RESULT_INVALID`；`tests/closed-lists.test.mjs` 斷言這兩件事 |
| worker | `sdk/v25-feature-worker.js:1675` `manifestAllowsAction` | manifest 的 `select-all` 是 `{"id":21,"gestures":[],"limits":["withheld-pending-characterisation"]}`（`dist/profiles/e2-editor-v25/sdk-manifest.json`）→ `UNSUPPORTED_OPERATION`，引擎沒被呼叫 |
| 引擎 | `src/probe_engine.cpp` `handleEditorAction` | worker 初始化時對 id 21 設 mask 0（`editorSetActionGestures`，`:8437-8447`：第一次呼叫把每格初始化成全許可再交集）；閘門在 `:6347-6364` 拒絕，`EDITOR_FORMAT_GESTURE_UNSUPPORTED`，「nothing was dispatched」 |

〔讀原始碼〕**引擎裡沒有擋它的東西**：有序引擎沒有動作白名單，`dispatch()` 照樣進 `handleEditorAction`；`kMaxInternalEditorAction` 是 25，全選的內部編號 23 在界內。gesture 若放行，路徑是：

- `probe_engine.cpp:6508-6526`：`OXSDK_EDITOR_SELECT_ALL` → `Key::A | EditorMod1Modifier`，刻意走**按鍵**路徑而不是 uno-mutation 路徑（後者會為沒發生的編輯推進修訂號，finding 067 的引擎那一半）。註解明寫「postcondition is NOT characterised」。
- `:6587-6590`（`#ifdef OXSDK_E2_V23_LINK_BATCH`，成立）：`dispatchOrderedKey(keyCode, pending)`；`:6248-6254`：登記回覆、`postKeyEvent` KEYINPUT＋KEYUP、`refreshCaretParagraph()`。舊路徑的 250 ms 讀回期限不編進來。
- 回覆（subagent 讀 `ordered_engine_reply.inc:17-52`，主 session 未逐行核對）：下一次 poll 時組成 `editor-action-completed`，`changed: false`、修訂號不變，completion 依收到的 callback 是 `documented-callback-visible-cursor`、`documented-callback-text-selection` 或 `verified-move-readback`（在 v23 上只是標籤，沒有實際讀回）；`state.selection` 帶 `observed`、`collapsed`、`start`、`end`、`rectangles`。

〔讀原始碼〕兩個放行時會碰到的細節：

1. **它仍然要求修訂號。**`editorActionMutates`（`:5245-5255`）對全選回 true（v21 的註解：「Select-all (23) keeps its class」），所以送出時要帶目前的修訂號，否則 `STALE_REVISION`；雖然它的 pending 是 `mutation = false`、不推進修訂號。
2. **已有選取時要兩個 range 位元都給。**閘門對非 collapsed 的選取要求 `range-single` **和** `range-cross` 都放行（`:6347-6357`，理由是引擎不讀 html 就分不出兩者）。所以只給 `collapsed` 的 profile，第二次按 Ctrl+A（已經是全選範圍）會被拒；`select-all` 實際要給的 gesture 很可能是三個全給。
3. 另外：`selectionObserved` 為 false 時（文件剛開、還沒收到任何選取回報）一律拒絕（`:6340-6346`）。

〔推論，未驗證〕Writer 把 `0x2200`（Ctrl+A）當成全選快捷鍵；有序引擎「一個指令造成的 callback 在下一次 poll 之前到齊」（`ordered_poll.hpp` 的 N1a）對 post 出去的按鍵也成立。後者若不成立，回覆會帶全選之前的狀態，看起來像「成功了但什麼都沒選」——正是 2026-08-19 那個形狀。

### 身分：開放全選需要什麼

〔讀原始碼〕manifest 的 sha256 被 profile 身分綁著（v25 規格 §4.5、§5；`tools/v25_four_arms_identity.py` 的 `ARTIFACT_PINS`）。「版本是身分」：改 manifest＝新的 profile 名稱與目錄，不能原地改 `e2-editor-v25`。wasm、loader、worker 的位元組可以不變（worker 讀 manifest 決定放行，不需要改）。殼層 client 的改動（`select-all` 進封閉清單、給 postcondition 類別）是殼層的新 generation。

〔推論〕所以出貨方式有兩種：manifest-only 的後繼 profile（不連結），或併進 v26 引擎批次一起出。擁有者 2026-10-29 已決定併進 v26；這裡要記的只是：**全選本身不逼出連結**，若 v26 最後沒有別的引擎改動，它不必等一次連結。

## 第 2–4 題：還沒量，要量的是這些

**第 2 題：「成功」的意思要量，不要假設。**在一份**不放進 `dist/`** 的 scratch manifest（其他位元組等於 v25）上把三個 gesture 都給全選，鏡像量：

- 引擎的選取狀態（`state.selection` 兩端、是否 collapsed）、畫面上有沒有畫出選取底色；**收到的 callback 與回覆是否在同一次 poll**（上面的推論）。
- 全選之後接著：打字取代（typed-insert 路徑，finding 168 的教訓）、`delete-selection`（v25 對 `range-cross` 有限制 `not-characterised-in-tables-or-note-apparatus`）、行內格式、複製／剪下、復原。
- 文件：含表格、frame、註腳的，以及**空白文件**（finding 173 那一種）。
- 先要過的形式條件：2026-08-19「回報成功、什麼都沒選」的形狀必須能被這個量測抓成紅（正向對照：用幾何範圍的舊作法當反例）。

**第 3 題**：全選要給哪些 gesture，以及整份文件的範圍會撞上哪些既有限制（表格、註腳、frame 內的範圍）。由第 2 題的結果決定。

**第 4 題：頁面的綁定。**Ctrl+A／Cmd+A 只在 `session.offers("select-all")` 為真時綁；不提供它的 profile 上必須仍然什麼都不綁（今天不綁的理由在每個扣住它的 profile 上要繼續成立）。

## 下一步（工單的「Then」）

量完第 2 題之後才寫規格（zh-TW），判準先釘、各附紅案：省略而不是扣住的 manifest 必須紅；在扣住它的 profile 上綁了 Ctrl+A 的頁面必須紅；「回報成功、什麼都沒選」的形狀必須紅。連結（若 v26 有其他引擎改動）仍是擁有者的。
