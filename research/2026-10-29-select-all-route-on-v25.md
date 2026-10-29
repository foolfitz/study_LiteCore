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

（2026-10-30 更新：第 2、3 題已量，結果見下面「第二部分」；第 4 題仍是規劃，也在第二部分。本節保留為量測前的計畫。）

**第 2 題：「成功」的意思要量，不要假設。**在一份**不放進 `dist/`** 的 scratch manifest（其他位元組等於 v25）上把三個 gesture 都給全選，鏡像量：

- 引擎的選取狀態（`state.selection` 兩端、是否 collapsed）、畫面上有沒有畫出選取底色；**收到的 callback 與回覆是否在同一次 poll**（上面的推論）。
- 全選之後接著：打字取代（typed-insert 路徑，finding 168 的教訓）、`delete-selection`（v25 對 `range-cross` 有限制 `not-characterised-in-tables-or-note-apparatus`）、行內格式、複製／剪下、復原。
- 文件：含表格、frame、註腳的，以及**空白文件**（finding 173 那一種）。
- 先要過的形式條件：2026-08-19「回報成功、什麼都沒選」的形狀必須能被這個量測抓成紅（正向對照：用幾何範圍的舊作法當反例）。

**第 3 題**：全選要給哪些 gesture，以及整份文件的範圍會撞上哪些既有限制（表格、註腳、frame 內的範圍）。由第 2 題的結果決定。

**第 4 題：頁面的綁定。**Ctrl+A／Cmd+A 只在 `session.offers("select-all")` 為真時綁；不提供它的 profile 上必須仍然什麼都不綁（今天不綁的理由在每個扣住它的 profile 上要繼續成立）。

## 第二部分（2026-10-30）：第 2、3 題的量測，與第 4 題的規劃

證據：`findings/evidence/select-all-v25/`（工具 `measure_select_all.py`、`run-01`（46 格）、`run-02`（粗體，8 格，存檔的 ODT 都留著）、`README.md`）。Chrome、鏡像，不碰 `dist/` 與 ddev。

### 量法，以及它不是產品路徑

〔已觀察〕殼層 client 在送出前就拒絕 `select-all`，所以這次是 **harness 路徑**：頁面裡的觀察器直接對文件 worker 送 `editorActionV2 select-all`（request id 從 2,000,000,000 起；SDK client 會忽略不是它發的回覆）。引擎推給頁面的 editor-state 照常到達，所以**頁面畫的選取底色、之後頁面自己的按鍵與按鈕都是產品的**；但「頁面按 Ctrl+A 會怎樣」這條路還不存在，沒有量。

〔已觀察〕三個產品，都是 `dist/` 的鏡像、逐檔核對身分：`grant`（scratch manifest 把三個 gesture 都給 `select-all`，其他欄位與 v25 相同）、`grant-collapsed`（只給 `collapsed`）、`withheld`（出貨的 manifest，`gestures: []`）。scratch manifest 只存在於 `wasm_sdk_probe/build/` 底下的鏡像，跑完就刪。

### 第 2 題：「成功」是什麼——量到的

〔已觀察〕**游標在本文時，全選選到整份文件。**五份有文字的文件（清單、表格、腳註＋frame、尾註、文字框）各 6 格全部一樣：回覆 ok、`changed: false`、修訂號不變；選取兩端＝`move-document-start`／`-end` 的游標位置；複製（`getSelection`，也就是頁面 Ctrl+C 拿到的東西）依序含每一個本文段落與表格格子；頁面畫出了底色。

〔已觀察〕**回覆在選取 callback 之後、同一次 poll 組成。**worker 的紀錄：editor-state seq 13–16 先到（seq 15 起是範圍），約 10 ms 後 `editor-action-completed` 帶 `callbackSequenceAfter: 16`。回覆裡的選取＝之後再讀的狀態，59 次 ok 的選取請求全部成立。第一部分的推論（N1a 對 post 出去的按鍵也成立）在這裡被量到了。

〔已觀察〕**2026-08-19 的「回報成功、什麼都沒選」在 v25 上不重現。**同一個構造——幾何範圍 (0,0)–(寬−1,高−1)——在有序引擎上也選到整份（清單 9/9、表格 6/6）。所以正向對照改用構造的：(0,0)–(1,1) 回 ok、collapsed、什麼都沒複製、沒有底色——這就是那個形狀，判讀把它判成「不是整份」；只選第一行的範圍回 ok、有底色但缺 8 個錨點，也判成「不是整份」。頁面今天不綁 Ctrl+A 的那個理由（幾何範圍騙人）在 v25 上已經不成立；但頁面要綁的是全選動作，不是幾何範圍，所以這個改變只影響「為什麼不綁」的那段註解，不影響做法。

〔已觀察〕**接著的動作**（每格最後存檔讀回）：

| 動作 | 結果 |
|---|---|
| 打字（真的鍵盤，頁面走 `uno-insert-text`，6 次全 ok） | 整份被取代成打的字；表格、frame、腳註、尾註都一起被刪；留下**第一段的段落樣式**（清單那份第一段是標題，整份變成一個標題） |
| Backspace（真的鍵，頁面送出 `delete-selection`） | 整份清空，剩一個空段落 |
| `delete-selection`（harness） | ok、`uno-command-result`、修訂號 0→1；整份清空 |
| 打字後按頁面的復原 | **兩次**回到原文（一次撤銷打字、一次撤銷取代），表格、frame、附註都回來 |
| 粗體（真的點 B，run-02） | 每一個本文段落與表格格子都變粗體（清單那份的標題也是，以自動樣式寫入） |
| 空白文件（173 那份） | 全選回 ok、collapsed、`verified-move-readback`；打字正常、復原一次回原樣、Backspace 送 `delete-backward` 不改東西。**沒有任何東西壞掉** |

〔推論，未對照原生〕「取代時沿用第一段樣式」「附註隨錨點一起刪」「格子裡三段式」都是桌面 Writer 的已知行為；這次沒有跑原生 LibreOffice 對照，所以只能寫成推論。

### 第 3 題：要給哪些 gesture，以及整份範圍會撞上的限制

〔已觀察〕**三個 gesture 都要給。**只給 `collapsed` 時，第一次按成功，第二次（從範圍按）被拒 `EDITOR_FORMAT_GESTURE_UNSUPPORTED`——第一部分讀碼的細節 2 量到了。這不只是「按兩次」的問題：游標在表格格子裡時，全選是**格 → 整張表 → 整份**三步（10、44、74 字），第 2、3 步都是從範圍按。

〔已觀察〕撞上的限制：

1. **含 frame 的文件，複製拿不到文字。**選取是整份（刪除、粗體都作用到整份），但 `getSelection` 回 `complex`、0 字。〔讀原始碼〕引擎只在 `LOK_SELTYPE_TEXT` 時取文字（`probe_engine.cpp` `selectionTypeName`），LOK 對含 as-char frame 的選取回 COMPLEX；頁面的複製會丟 `UNSUPPORTED_CLIPBOARD_TYPE`／`CLIPBOARD_EMPTY_SELECTION`（`input/clipboard-adapter.js:54-72`），剪下先複製、失敗就停，不會刪（`e2-editor-app.js` 的 cut）。這不是全選特有的，任何蓋到 frame 的範圍都一樣；但全選讓它變成常態——**一份有圖的文件，全選→複製就會失敗**。
2. **附註內文不在複製內容裡**（尾註那份的複製有 3 個本文段落、沒有尾註本文）；但打字或刪除會連附註一起刪掉。復原拿得回來。
3. **`delete-selection` 在 manifest 上有限制 `not-characterised-in-tables-or-note-apparatus`。**整份範圍幾乎一定跨表格與附註。這次量到的刪除在表格、frame、附註上都是「整份清空、復原可回」，沒有半刪；但這是 harness 送的、只有單頁 fixture，要不要因此放寬那條限制是規格要決定的，不在這裡決定。
4. 沒量到的：游標在 frame、腳註、尾註**裡面**時按全選；文件以表格開頭或結尾；多頁文件（fixture 都是一頁，底色從沒超出畫布視窗）；Firefox。

### 第 4 題：頁面綁定的規劃（還沒寫任何程式）

〔讀原始碼〕殼層 client：`select-all` 要進 `APPENDED`，postcondition 類別用 **"move"**（修訂號不變、`changed: false`、`documented-callback-*` 或 `verified-move-readback`，`narrow-editor-v2-client.js:118-144`）。這次量到的回覆正好是這兩種 completion：從 collapsed 按是 `documented-callback-visible-cursor`，從範圍再按、或空白文件是 `verified-move-readback`。〔推論〕不需要新的 postcondition 類別；但「move 類」對全選的意思是「文件沒變」，不保證選到了東西——那一半要頁面判。

〔讀原始碼＋已觀察〕頁面要做三件事：

1. **Ctrl+A／Cmd+A 只在 `session.offers("select-all")` 為真時攔下並送出**；不提供它的 profile 上維持今天的不綁（工單第 4 題）。
2. **送出後用回覆更新 `lastSelectionShape`**（像拖曳的 `pumpDrag` 用 `selectionShapeOf(result)`）。這次 harness 選了 53 次，頁面的 `selectionShape` 每次都還是 `collapsed`——工具列的 gesture 判斷（`updateGestureAffordance`）讀的是這個信念；刪除鍵這次會對，是因為它讀引擎推來的狀態（`dispatchDelete`）。
3. **誠實回報兩種「沒有全選到」**：空白文件（回 ok、collapsed：沒有東西可選，不該說「已全選」）；以及非空文件回 ok 卻 collapsed 或範圍不到文件兩端——後者在 v25 上沒量到過，但它就是 08-19 的形狀，要有紅案。

### 對出貨方式的影響

〔推論〕第一部分的結論不變：全選不逼出連結——manifest 的後繼 profile（新身分）＋殼層新 generation＋頁面，就能出。這次量到的行為沒有一項需要改引擎。擁有者 2026-10-29 選了「併進 v26 引擎批次」；這個量測只是讓「不等連結、單獨先出」成為一個有根據的選項，選哪個是擁有者的事。

## 下一步（工單的「Then」）

量完第 2 題之後才寫規格（zh-TW），判準先釘、各附紅案：省略而不是扣住的 manifest 必須紅；在扣住它的 profile 上綁了 Ctrl+A 的頁面必須紅；「回報成功、什麼都沒選」的形狀必須紅。連結（若 v26 有其他引擎改動）仍是擁有者的。

（2026-10-30 補充：第 2 題已量。規格另外要涵蓋：只給 `collapsed` 的 manifest 必須紅（第二次按與表格裡的第 2、3 步會被拒）；頁面送出全選之後 `selectionShape` 仍是 `collapsed` 必須紅；含 frame 的全選→複製要有誠實的失敗說明；Firefox 要跑。）

## 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-10-29 | 第一部分：第 1 題（讀原始碼）。 |
| 2026-10-30 | 第二部分：第 2、3 題的量測（`findings/evidence/select-all-v25/` run-01、run-02）與第 4 題的規劃；「第 2–4 題」一節與「下一步」加註。 |

