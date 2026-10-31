# SPEC-M3-v28-last-line-fallback：文件最後一行的空段落改用「往回選一格」核對（引擎 `e2-editor-v28`、殼層 generation 82、宿主 0.2.44）

> 狀態：**釘死**（2026-10-30，任何實作與連結前的執行之前；原生量測 N-q52 是釘死前的量測）。草案經一次對抗性審核（opus，2026-10-30），20 項併入，見 §12；不再開第二輪。釘死之後只准追加（CLAUDE.md 第 10 節）。
> 依據：finding 176、finding 083；fable 裁決 3（`findings/evidence/176/RULING-fable-2026-10-30-c.md`，Q5）；fable 裁決 4（`findings/evidence/176/RULING-fable-2026-10-30-d.md`，以下寫成「裁決 4 Q3.2」；§4 是本規格的檢查清單）；原生臂 `findings/evidence/176/native-q52/`（V1–V7，`15cd044a1`…`2939814ae`）。
> 擁有者 2026-10-30：「A. 量 083 那格」→「A. 做多段文件最後一行（推薦）」（v28：選不到東西時改成往回選一格、判斷看最後一段；空白文件照舊跳提示；設計先交 fable；規格前補量另外四個動作）→ 裁決 4 之後兩題都選 A：游標放不回去「照引擎原本規則」（rollback）、表格那格「新寫一句」。

## 1. 為什麼要有

v27 之後，文件中間的空行按清單已經會被核對（finding 176 的 046 那格）。但**最後一行**的空段落照舊跳 083 那句「這一段是空的，檢查要用的選取取不到任何內容……」：`.uno:SelectText`（`FN_SELECT_PARA`）在空段落上要往下跳一個內容節點，最後一段後面沒有節點，什麼都選不到（`select-text-returned-none`）。最常見的兩條使用者路都會走到這裡：打一行字、Enter、按項目符號；以及全新的空白文件按項目符號。

原生量測（`native-q52/README.md`，判準都在執行前登錄）：

- **空白文件（只有一個空段落）救不了**：`.uno:SelectAll`、`.uno:CharLeftSel` 都讀 NONE（5/5，五個動作、sham、no-op 都一樣）；沒有非空的選取存在（V1 `ONE-BLOCK-DOES-NOT-VERIFY`）。
- **多段文件的最後一行讀得到**：從空的最後一段往回選一格（`.uno:CharLeftSel`），剛好跨過一個分段，讀回兩段：上一段的尾巴（不含任何字）與派送那一段；**最後一段**的清單狀態與段落標籤在每一輪都等於存檔（V3、V7）；五個動作都成立（項目符號 V3、編號／取消清單 V6、標題／內文 V5），在有效的夾具上各自的反例沒有一個被說成成功（V4 照登錄判 `LAST-UNSAFE`，成因是偽標題夾具，amendment 3 的前提段）。
- **現有判斷式（看第一段）在這條路上看錯段**：已套用的格子幾乎都會報 postcondition-not-met，而「上一段是清單項目、這一段 sham」會被誤判成功（`cl-n8`、`cl-nnum-after-number`）。所以要一個「最後一段」的判斷式。
- `.uno:SelectAll` 不採用：純文字超過 10,000 字元就回 COMPLEX（`desktop/source/lib/init.cxx:6023-6024`，300 行 5/5），而且整份讀回會碰到文件裡每一張圖、每一個附註（finding 037／038）。往回選一格的讀回與文件長度無關（300 行的文件 577 bytes，V7）。

## 2. 範圍

**做**：

1. 引擎（collapsed 路徑、只在 `.uno:SelectText` 的同步讀取是 NONE 時）：同一個指令裡、Q 還原之前，加一次 `.uno:CharLeftSel` 選取與讀回；以新的最後一段判斷式判（§4.1）。適用動作：**五個段落動作全部**（裁決 4 Q4）。
2. 一個新的結束形狀 `fallback-readback-refused`（後援讀到內容但不能判，例如前面是表格），殼層把它對到 `review`，頁面給它自己的一句提示（§4.3；擁有者「新寫一句」）。
3. 引擎 profile `e2-editor-v28`（v27 的後繼，**要重新連結**，擁有者跑）、worker、manifest、連結機械。
4. 殼層 generation 82；宿主 0.2.44。

**不做**：

- **空白文件不變**（裁決 4 Q6；裁決 3 Q5.1 照舊）：後援仍會跑、讀到 NONE，結束形狀照舊 `select-text-returned-none`、提示照舊 083 那句，殼層與頁面的路逐位元組不變。
- RangeSingle、RangeCross 不改（裁決 4 Q9）：後援只在 collapsed。
- 不用 `.uno:SelectAll`（裁決 4 Q1.2–Q1.3）。
- `formatBarrierReadbackSatisfied()`（第一段判斷式）不改；SelectText 讀到內容時 v27 的判法逐位元組不變。
- 游標放不回去照舊 `selection-not-restored`（rollback）——擁有者選 A（裁決 4 Q3.3 的預設）。
- L-pseudo-heading-reads-as-body 只具名、不修（裁決 4 Q5.1）。
- K、計數鏈（擁有者 10-12 的併批規則；§11 列累積的未計數改動）。

## 3. 決定紀錄

| 題 | 決定 | 出處 |
|---|---|---|
| 後援指令 | 只用 `.uno:CharLeftSel` | 裁決 4 Q1；V3、V6、V7 |
| 何時跑 | collapsed 路徑、`.uno:SelectText` 的同步讀取是 NONE、**且 `restorePointValid`**；同一個有序指令內、在唯一一組 Q 還原之前；中間不插讀取或 yield。`restorePointValid` 是 false 時不跑後援（還原會是 no-op，後援的選取會留著），照舊走 083 的形狀 | 裁決 4 §1、Q9；審核第 11 項（`ordered_format.inc:11-13`） |
| 判法 | 新判斷式 `formatBarrierFallbackReadbackSatisfied()`：讀 `lastListTag`／`lastBlockTag`。順序：(i) 後援讀 NONE → 照舊 083；**(ii) `restoreConfirmed` false → `selection-not-restored`**；(iii) 不是 TEXT、(iv) 既有四個結構旗標、(v) `blockCount != 2` → `fallback-readback-refused`；(vi) 段落識別；(vii) 判斷式 | 裁決 4 Q2.3–Q2.4；**(ii) 的位置偏離裁決 4 Q2.3**（原本在結構拒絕之後）：被拒的形狀對到 `review`、佇列開著，若還原同時失敗，畫面上留著一段使用者沒做的選取（表格那格，往回選會選到整個格子），下一個按鍵就會取代它。還原失敗先判，與裁決 4 Q3.3 及擁有者的 A 一致（審核第 1 項） |
| `blockCount == 2` | 必要條件；不限制第一段、不限制 `itemCount`、不讀 `multiBlock` | 裁決 4 Q2.4；22 格（18 格正式量測＋4 格 smoke）每輪都剛好 2 段，主 session 重算（裁決 4 檔尾） |
| 後援讀 NONE | 結束形狀照舊 `select-text-returned-none`、訊息照舊；紀錄多 `fallback` 物件 | 裁決 4 Q3.1（finding 173 的教訓：改名就掉出 `EMPTY_SELECTION_SHAPES`） |
| 後援讀到但不能判 | 新形狀 `fallback-readback-refused`，子原因在 `fallback.refusal`（沿用既有名稱，加 `unexpected-block-count`）；殼層對到 `dispatched-unverified`（review） | 裁決 4 Q3.2 |
| 那一句提示 | 新寫一句（§4.3），**不說「最後一段」**：後援在任何 collapsed 的 NONE 都會跑（表格格子、frame、附註裡的空的最後一段，下一個內容節點不相鄰），說「最後一段」在那些位置是假的 | 擁有者「A. 新寫一句」；finding 061 的前例；審核第 9 項 |
| 判了、不符合 | `postcondition-not-met`（rollback），與有字段落相同 | 裁決 4 Q3.4、裁決 3 Q1.2 的對稱；不是「比今天更嚴重」——那條限制管的是「判不了」 |
| 游標放不回去 | 照舊 `selection-not-restored`（rollback） | 擁有者「A. 照引擎原本規則」；裁決 4 Q3.3；原生 0/205 |
| 後援的 UNO 回覆 | 預期它（`expectOrderedUno`：callback 只記錄預期過的名稱，`probe_engine.cpp:3228-3234`）、記錄 `fallback.resultSeen`，**不當判決條件**（它對選不到東西也回 `success:true`，README §7）；讀法直接查 `gOrderedProof.uno`，不呼叫 `orderedUnoResult`：後者讀不到時在 `OXSDK_E2_V23_DIAGNOSTIC` 的 build 會多送一筆 `v23-proof-absent`（`ordered_engine_state.inc:39-53`），而缺席在這裡不是事件 | 裁決 4 Q3.5；審核第 16 項更正理由 |
| worker 投影 | `fallback` 的投影帶 `restoreConfirmed`（取自引擎紀錄 `readback.restoreConfirmed`）；新欄位放在 `productFormatBarrier` 回傳物件的**最後**（F3 的 `WORKER_BARRIER_ANCHOR` 釘著物件開頭，`run_e2_c_product_path.py:287`） | 審核第 7、12 項：S4 要在產品 worker 上讀到還原結果，不能靠診斷 worker |
| 段落識別 | 不改：空段落的指紋是空字串常數，識別判「未檢查」（finding 074），產品 core 也沒有 a11y | 裁決 4 Q2.5 |
| undo 紀錄 | 不改（v27 §4.1 第 4 項）：派送前一次、最後一次還原後一次，後援在兩次之間 | 裁決 4 Q2.6 |
| define | `OXSDK_E2_V28_LAST_BLOCK`，沒有 `OXSDK_E2_V27_FIRST_BLOCK` 就 `#error`；v28 區塊不巢在 v25／v27 區塊裡 | 裁決 4 §4 第 1 項；v27 的寫法 |
| profile | `e2-editor-v28`；`editorContract` 的葉等於 v27；不加 export、ABI 不變；`formatBarrier` 葉名不升 | 裁決 4 §4 第 1 項；v27 §3 的理由 |
| 批次 | v28 單獨一批（gen 82、0.2.44） | 裁決 4 Q8 |
| 回歸基準 | v27 引擎／generation 81／0.2.43 | 記憶「回歸基準＝上一個出貨版」 |

## 4. 設計

### 4.1 引擎（全部在 `#ifdef OXSDK_E2_V28_LAST_BLOCK` 之下）

1. **`editor_api.h`**：`#if defined(OXSDK_E2_V28_LAST_BLOCK) && !defined(OXSDK_E2_V27_FIRST_BLOCK)` → `#error`（帶守衛的 TU 是 `editor_api.cpp`，v27 的教訓）。
2. **`FormatReadback`**（`probe_engine.cpp` 約 781-809）加兩個欄位：`std::string lastListTag;`、`std::string lastBlockTag;`。
3. **`parseFormatReadback`**：在 `depth` 旁加一個「開著的結構標記」堆疊：只在 `depth` 加一時推（自我結束的標記不推）、在 `depth` 減一時彈；每遇到一個**開啟的**區塊標記（`formatTagIsBlock`）就寫 `lastBlockTag = tag`、`lastListTag = 堆疊裡最內層的 ul／ol，沒有就空字串`。`malformedNesting`、`unknownTag`、`footnoteApparatus`、`listTag`、`blockTag`、`blockCount`、`itemCount`、`multiBlock` 的算法不變：不帶 v28 define 時由 V0 守（前置處理逐位元組相同）；**帶 v28 define 時由 E4 的 v27 列守**（v27 的 18 列以 v28 define 重跑，輸出與判斷式結果逐列相同，§7.2）——V0 守不到帶 define 的那份（審核第 5 項）。
4. **`FormatStateBarrier`** 加後援欄位：`fallbackRan`、`fallbackResultSeen`、`fallbackSelectionType`（初值 -1）、`fallbackReadable`、`fallbackReadbackBytes`、`fallbackReadbackHtml`（同一個證據上限 `FormatReadbackEvidenceLimit`）、`fallbackReadback`（`FormatReadback`）、`fallbackRefusal`（字串）。
5. **`formatBarrierFallbackReadbackSatisfied()`**（新函式）：照抄 `formatBarrierReadbackSatisfied()`（約 5747-5769）的結構，改讀 `fallbackReadable` 與 `fallbackReadback` 的 `lastListTag`（空字串讀成 `none`）／`lastBlockTag`。原函式不動。
6. **`ordered_format.inc` `startOrderedFormatAction`** 的 collapsed 分支：在 `.uno:SelectText` 的同步讀取、既有的 `refreshCaretParagraph()`（產品 core 上不呼叫 LOK，`probe_engine.cpp:2135-2146`；a11y core 上是原生 harness 沒有的一次讀取，記下）與既有的 html 讀取之後、`restoreOrderedFormatPoint()` 之前，若 `barrier.route == Collapsed && 主讀的型別是 NONE && gFormatBarrier.restorePointValid`：
   `fallbackRan = true` → `expectOrderedUno(".uno:CharLeftSel")` → `postUnoCommand(".uno:CharLeftSel", nullptr, true)` → `readSelection()` → `fallbackSelectionType` → 若 TEXT：`getTextSelection("text/html")`、`fallbackReadbackBytes`、`fallbackReadbackHtml`、`fallbackReadback = parseFormatReadback(markup)`。中間不插任何讀取、事件迴圈 yield 或等待 callback。之後照舊是唯一一組 Q 還原與它的 NONE 確認、undo 的第二次讀取。SelectText 讀到 TEXT 時不送後援（v27 的呼叫序列逐位元組不變）；RangeSingle 不送後援。
   - **拼字限制**（審核第 17 項）：`tests/test_ordered_format.py:25` 的 `read-NONE-as-TEXT` 突變要求 inc 原文裡 `selected.type == LOK_SELTYPE_TEXT` 恰好出現一次（`#ifdef` 裡的字也算）；後援的型別判斷用別的變數名（例如 `stepBack.type == LOK_SELTYPE_TEXT`），不得含那串字。
   - **選取模式**（審核第 19 項，讀碼）：`.uno:SelectText` 讓殼層進入選取模式；後援的 `SttSelect` 在已經是選取模式時直接返回（`sw/source/uibase/wrtsh/select.cxx:409-410`），所以後援之後的狀態與 v27 在 SelectText 之後的狀態同一種，既有的 Q 序列（量過能清掉 SelectText 的選取模式，inc 檔頭）適用。原生 P3 沒有直接量選取模式；S4-a 在按完之後真的打字，是這一條在使用者那條路上的量測。
7. **`deferOrderedFormatReply`**：在既有的 `selectionResultSeen` 之後，若 `fallbackRan`：直接查 `gOrderedProof.uno` 裡 `.uno:CharLeftSel` 那一筆的 `seen` → `fallbackResultSeen`。缺席不是失敗、不呼叫 `orderedUnoResult`（§3）。
8. **`finishOrderedFormatReadback`**：在既有的 `selectionTypeReadable` 檢查（NONE 拒絕，約 30-36 行）**之前**加後援分支：若 `fallbackRan`：
   1. `fallbackSelectionType == LOK_SELTYPE_NONE` → 不做任何事，往下走到既有的 NONE 拒絕（`select-text-returned-none`，訊息不變）；
   2. `!restoreConfirmed` → 既有的 `selection-not-restored`（**先於 3–5**，§3；審核第 1 項）；
   3. 不是 TEXT（例如 COMPLEX）→ 拒絕，形狀 `fallback-readback-refused`，`fallbackRefusal = "selection-type-not-readable"`；**不讀 html**（finding 037 的守則：先看型別，只有 TEXT 才讀）；
   4. `!parsed`／`unknownTag`／`malformedNesting`／`footnoteApparatus` → `fallback-readback-refused`，`fallbackRefusal` 用既有的名稱（`block-extraction-failed`／`unknown-structural-tag`／`malformed-readback-nesting`／`footnote-apparatus-readback`）；
   5. `fallbackReadback.blockCount != 2` → `fallback-readback-refused`，`unexpected-block-count`；
   6. 段落識別：照非 cross 分支今天的寫法算（空段落→「未檢查」）；識別成立而指紋不同 → 既有的 `readback-is-a-different-paragraph`（產品 core 上到不了）；
   7. `!formatBarrierFallbackReadbackSatisfied()` → 既有的 `postcondition-not-met`（`EDITOR_FORMAT_POSTCONDITION_FAILED`）；
   8. 否則 `completeFormatBarrier()`。
   3–5 的錯誤碼是 `MUTATION_OUTCOME_UNKNOWN`（與今天 083 的路相同），訊息是新的一句：「the fallback selection's readback does not provide a supported structural proof; the format mutation outcome is unknown」。回覆組成裡不呼叫任何 LOK（`test_ordered_format_scope.py` 的 `violations()` 守）。
9. **`appendFormatBarrierDetails`**：每一筆紀錄都帶 `fallback`：沒跑 → `{"ran":false}`；跑了 → `{"ran":true,"command":".uno:CharLeftSel","resultSeen":…,"selectionType":…,"readable":…,"readbackBytes":…,"readback":{"parsed","unknownTag","malformedNesting","footnoteApparatus","listTag","blockTag","lastListTag","lastBlockTag","blockCount","itemCount","multiBlock"},"readbackHtml":"…","refusal":"…"}`。主讀回的物件也多 `lastListTag`／`lastBlockTag`（便宜，而且讓證據裡第一段對最後一段看得見，裁決 4 Q2.2）。
   **寫法是規定的**（審核第 4 項）：`readback` 物件與 `formatBarrier` 在 v27 的 `#ifdef … #else … #endif` 裡收尾（`probe_engine.cpp:1753-1769`），v28 區塊不得巢在裡面，也不得把 `<<` 串拆開（那會在 v28 區塊外多出 `;`／`json` 字元，V0 與 hunk 讀取器都會紅）。所以：`lastListTag`／`lastBlockTag` 是 `blockTag` 之後（約 1747 行）串中間的一個 v28 區塊；`fallback` 由一個回傳 `std::string` 的輔助函式 `formatBarrierFallbackJson(barrier)` 產生，在 `,"readback":{` 之前（約 1736 行）串中間的一個 v28 區塊裡呼叫。
10. **前置處理不變（V0-v28）**：以 v23、v24、v25、v27 的 define 前置處理 `E2_C_SOURCES` 的每一個單元（含 `unoembind_stub`），輸出與改動前的 HEAD 逐位元組相同。
11. **宣告的 hunk**（封閉清單）：第 1–9 項，含 `formatBarrierFallbackJson` 輔助函式；`parseFormatReadback` 裡是數個 hunk（堆疊的宣告、推、彈、兩個指派），各自是一個 v28 區塊。不改 `formatBarrierReadbackSatisfied`、`restoreOrderedFormatPoint`、undo 的兩次讀取、RangeSingle 與 RangeCross 的分支。

### 4.2 worker（`sdk/v28-last-block-worker.js`）

由封存的 v27 worker（`build/archive/e2-editor-v27-c089dfd6-worker-8152448a/sdk-worker.js`，`8152448ab83b…`）衍生，差異是封閉清單：

1. `featureExtendPermitted` 的 `"e2-editor-v27"` → `"e2-editor-v28"`（v26 規格 §4.2：不改，行延伸靜默失效）。
2. `productFormatBarrier` 加 `fallback`，放在回傳物件的**最後一個欄位**（F3 的 `WORKER_BARRIER_ANCHOR` 釘著物件的開頭兩行）：`value.fallback` 是物件時投影 `{ran, selectionType, blockCount, lastListTag, lastBlockTag, refusal, restoreConfirmed}`（`blockCount`、`lastListTag`、`lastBlockTag` 取自 `value.fallback.readback`；`restoreConfirmed` 取自 `value.readback.restoreConfirmed`；型別不對的欄 → `null`）；否則 `null`。**不投影 `readbackHtml`**。
3. 檔頭註解說明衍生來源與本節。

### 4.3 頁面與殼層

`editor-shell-v2/paragraph-editor-client.js`：

1. 匯出 `FALLBACK_REFUSED_SHAPES = Object.freeze(["fallback-readback-refused"])`，註解同 `EMPTY_SELECTION_SHAPES` 的「兩個讀者」警告（頁面從同一份清單選句子）。`EMPTY_SELECTION_SHAPES` **不改**（它的單元測試釘著恰好兩個名稱）。
2. `formatFailureDisposition`：在 083 那條分支旁加一條：`dispatched === true && route === "collapsed" && FALLBACK_REFUSED_SHAPES.includes(failureShape) && selectionResultSeen === true` → `"dispatched-unverified"`。其餘不變（沒有這條，新形狀會落到最後的 `dispatched-rollback`，finding 173 的形狀）。

`web/e2-editor-app.js`：

3. `run()` 的 `review` 句子：在 083 那句與 046 那句之間加一個分支：`FALLBACK_REFUSED_SHAPES.includes(shape)` →「動作已送出，但這一段後面沒有可以一起選的段落，檢查改成往前多選一格，碰到了表格或其他讀不了的內容，所以無法核對。請看一下結果，不是你要的就按「復原」。這是檢查的極限，不是文件壞了」。不說「最後一段」（§3）；保留各句共用的「不是你要的就按「復原」」（被綁的 F3 判準讀這幾個字）。呈現照 v26 U3：一般樣式、提示裡沒有錯誤碼與英文、兩者記在 `console.warn`。
   **三支頁面單元測試要跟著改**（審核第 2 項，事先宣告）：`page-review-sentence.test.mjs`、`page-review-presentation.test.mjs`、`page-review-latency.test.mjs` 以 `new Function(…, "EMPTY_SELECTION_SHAPES", …)` 切出 `run()`，參數是 `run()` 自由名稱的手寫清單；`run()` 多讀 `FALLBACK_REFUSED_SHAPES` 之後，不改它們會在 046 那句的案例上丟 ReferenceError。改法：參數清單加這個名稱、傳入 client 匯出的值；改前在改過的頁面上紅（見證 `u-v28/page-tests-red-before.txt`），改後綠。這是規格內宣告的改動，不是釘死後改檢查（§34）。
4. `workerUrl` → `./profiles/e2-editor-v28/sdk-worker.js`；`PINNED_WASM_SHA256` → v28 實際 wasm 的前 16 位（連結後才知道）。

session 不改。動 client 之前與之後各跑一次 `check_e1_c_bundle_intact.py`，都要 `intact: true`（068 的教訓：先問這個檔綁著誰的判定）。

### 4.4 manifest 與身分

profile `e2-editor-v28`；`editorContract` 每一個葉等於 v27；只換 `profile`、`sdkVersion`、`wasmSha256`、`loaderSha256`、`workerSha256`；匯出表等於 v27 封存的 `exports.txt`（`f5b216303fe6…`）。

## 5. 身分與連結的機械（比照 v27 §5，只換名字）

- Makefile 的 v28 區塊接在 v27 之後：`E2_V28_BUILD := build/e2/editor-v28`、`E2_V28_DIST := dist/profiles/e2-editor-v28`；編譯規則逐字照抄 v27，defines 多 `-DOXSDK_E2_V28_LAST_BLOCK`；匯出表取 v27 封存的；worker `cp sdk/v28-last-block-worker.js`，前置檢查驗衍生來源是封存的 v27 worker（`8152448a…`）；連結受守衛（`refuse_unasked_relink`），用 `link_product_stack_1m`。
- 新檔：`tools/build_e2_v28_last_block_profile.py`（v27 的建構換名字）、`tools/check_v28_last_block_contract.py`、`tools/link_v28_last_block_owner.sh`、只跑測試的 `test-v28-last-block-static`。v25–v27 的工具位元組不動。
- `test-e2-c-static` 的 M1-1 載體行加 `--carrier E2_V28=probe_engine,sdk_api,editor_api`，先紅（證人）再綠。
- `tools/what_the_link_ships.py` 加 variant `link-batch-v28`，`--since 3a6998b33`（v27 的連結原始碼：那之後 `wasm_sdk_probe/src` 沒有 commit，連結前以 `git diff 3a6998b33 -- wasm_sdk_probe/src` 只剩 v28 的改動確認）；它看不到 `.inc`，所以另由 hunk 讀取器 `check_v28_ships_confined.py`（`check_v27_ships_confined.py` 的衍生，基準同上）證明 v28 的改動全在 v28 區塊內、恰好是 §4.1 第 11 項的清單。
- 改了 inc 與 `probe_engine.cpp`，v23D 起各個 profile 的物件依 Makefile 都會變舊；擁有者的那一行指令只建 v28 的 manifest，所以連結前記錄那一行的 `make -n`：只有 `build/e2/editor-v28` 的編譯行加一次受守衛的連結。
- 連結前：驗 v27 封存的 `SHA256SUMS`；凍結集合 `findings/evidence/v28-083/pre-link/frozen-set-before.sha256`；確認 `build/e2/editor-v28`、`dist/profiles/e2-editor-v28`、連結 log 都不存在。
- **連結是擁有者的**：`bash tools/link_v28_last_block_owner.sh`（會編譯；agent 只跑 `bash -n`）。

## 6. 普查（裁決 4 §4 第 10 項；2026-10-30，草案階段做完）

一次性量測（CLAUDE.md §1 的形式三），指令與輸出：`findings/evidence/v28-083/census/census.sh`、`census.txt`。搜 `select-text-returned-none`、`EMPTY_SELECTION_SHAPES`、`取不到任何內容`、`L-083-stays-a-toast`、`selectionResultSeen`、`did not provide readable text`、`stage-deadline:awaiting-selection`；範圍：`wasm_sdk_probe/{tools,web,editor-shell-v2,sdk,tests,src}` 與 `findings/evidence/` 裡的 `.py`／`.md`（不含定義候選的 `native-q52/`）。

| 讀的人 | 讀什麼 | v28 之後 |
|---|---|---|
| 被綁的 F3 runner `run_e2_c_product_path.py` 5722、5732 行（`bulleting-a-blank-line…`） | 083 句或 046 句 | 不動：那一格是文件中間的空行（046 的格子），SelectText 讀到內容、不跑後援；v27 已依設計退役（v27 §8 第 1 項） |
| B1 `check_v79_blank_bullet.py`、S2 `check_v80_…`、S2′ `check_v81_…` | 空白文件：`failureShape == select-text-returned-none`、`dispatched`、`route collapsed`、`selectionResultSeen`；083 句 | 不動：空白文件的後援讀 NONE，形狀、訊息、句子都不變；紀錄多 `fallback`，這些工具不讀它 |
| 殼層單元 `page-review-sentence.test.mjs`（`EMPTY_SELECTION_SHAPES` 恰好兩個）、`page-review-presentation.test.mjs`（083 的引擎訊息原文）、`page-review-latency.test.mjs`、`paragraph-editor-client.test.mjs` | 既有三句、兩個空選取名稱、處置 | 斷言不動（`EMPTY_SELECTION_SHAPES` 不改、訊息不改）；**前三支的注入參數清單要加 `FALLBACK_REFUSED_SHAPES`**（§4.3 第 3 項，事先宣告、先紅）；新形狀另寫測試（§7.2 U-v28） |
| F3 runner 的 `WORKER_BARRIER_ANCHOR`（`run_e2_c_product_path.py:287`） | worker `productFormatBarrier` 回傳物件的開頭兩行 | 不動：新欄位放在物件最後（§4.2 第 2 項） |
| 殼層 bundle 的範圍與排除清單（`e2/editor-shell-v2-bundle-v81.json`） | `sdk` 下每一個 `*.js`；每一版的 worker 原始檔排除 | 82 的排除清單＝81 的＋`sdk/v28-last-block-worker.js`（§7.3 切頁） |
| 頁面 `e2-editor-app.js` 2162-2193 | 依形狀選句 | 改（§4.3 第 3 項） |
| 其他 import client 的頁面（`demo-structure-app.js`、`e2b-*-app.js`、`e2-c-d2-app.js`；不在宿主套件裡）與 ods 頁面（不 import） | 處置 | 新分支只對新形狀生效；舊形狀的處置不變 |
| client `paragraph-editor-client.js` 295-364 | 處置 | 改（§4.3 第 1–2 項） |
| worker `v27-first-block-worker.js` 等 | `selectionResultSeen` 投影 | v28 worker 衍生（§4.2）；舊 worker 不動 |
| 引擎測試 `tests/ordered_format_test.cpp:127`（「NONE has precise shape」）、`test_ordered_format.py`、`test_e2_profile.py:370` | NONE 的形狀、`selectionResultSeen` 的程式文字 | 不帶 v28 define 編，不動；v28 的行為由 E1 釘 |
| `diag_format.py`（v25 F1）、`probe_099…`、`e2-c-d3-app.js`、歷史 README／PREDICTION | 歷史 | 本批不跑 |

**結論**：名稱普查找不到讀這些名稱、又走到多段文件最後一行的被綁檢查；但「沒有被綁的格子走到最後一行」是行為的宣稱，名稱普查承載不了（CLAUDE.md §1 形式三）——真正的守衛是 F3-82 對 F3-81 的相等讀取器：**預期沒有任何移動**（§8），有移動就停下查清（審核第 12 項）。

## 7. 判準

證據目錄 `findings/evidence/v28-083/`。每條都有「沒做的話」的預設。

### 7.1 釘死前（已做；原生，agent 自己跑）

- **N-q52**（`findings/evidence/176/native-q52/`）：V1 `ONE-BLOCK-DOES-NOT-VERIFY`（空白文件）；V2、V3 `LAST-HOLDS`；V4 `LAST-UNSAFE`（照登錄；成因是偽標題夾具，amendment 3 的前提段）；V5 標題、內文 IN-SCOPE；V6 編號、取消清單 IN-SCOPE；V7 `V7-HOLDS`（300 行 577 bytes、結尾兩個空行）。所有正式量測的還原：240 輪（135＋40＋30＋35）的 `restoredType` 都是 NONE；其中 a6／n6 兩格只判 `restoredType`，定位的那一半依登錄不判（審核第 15 項）。每一組判準都在執行前 commit（`15cd044a1`、`cce4a7e76`、`e798427f8`、`dd8a74fcd`），結果在之後的 commit。

### 7.2 連結前（原始碼與單元測試，agent 自己跑）

| 編號 | 判準 | 紅案（先紅） |
|---|---|---|
| E1 | 新單元測試 `tests/ordered_format_v28_test.cpp`（`test_ordered_format_v28.py` 驅動，前例 v27）：(a) collapsed、主讀 NONE、後援 TEXT、兩段、最後一段符合 → 成功、`completion verified-format-readback`、紀錄 `fallback.ran:true`、`lastListTag`／`lastBlockTag` 有送出；**(b) n8 的陷阱**：第一段 `ul`、最後一段 `none`、目標項目符號 → `EDITOR_FORMAT_POSTCONDITION_FAILED`／`postcondition-not-met`（第一段判斷式會讓它過，所以它是「新判斷式真的被讀」的證人）；(c) 主讀 NONE、後援 NONE → `MUTATION_OUTCOME_UNKNOWN`／`select-text-returned-none`、`fallback.selectionType:0`、訊息與 v27 相同；(d) 後援 `unknownTag:table` → `fallback-readback-refused`、`fallback.refusal:unknown-structural-tag`；(e) 後援三段 → `fallback-readback-refused`／`unexpected-block-count`；(f) 呼叫序列：主讀 TEXT 時沒有後援的 post（與 v27 逐呼叫相同）；後援的 post 在 NONE 讀取之後、唯一一組 Q 序列之前；(g) RangeSingle 主讀 NONE → 沒有後援的 post；**(h)** 後援讀 COMPLEX → `fallback-readback-refused`／`selection-type-not-readable`，**沒有後援的 html 讀取**（037 的守則）；**(i)** `restorePointValid` false → 沒有後援的 post、形狀 `select-text-returned-none`；**(j)** 後援 `unknownTag:table`＋還原失敗 → `selection-not-restored`（不是 `fallback-readback-refused`，審核第 1 項）。假的 harness 要加一個 `gOrderedProof` 的替身（現在只假 `expectOrderedUno`／`orderedUnoResult`，`tests/ordered_format_test.cpp:60-63`）；**後援判斷式從 `probe_engine.cpp` 以正規式切出真的那一份，不假造**（否則 E2 的「判斷式改讀第一段」突變無從變紅；`formatBarrierReadbackSatisfied` 今天是假的，`ordered_format_test.cpp:68`） | 「v27 的行為」＝把 v28 區塊剝掉、**帶著** v28 define 編：必須編得過，且 (a)–(e)、(f) 的後半（後援的位置）、(h)、(j) 印 FAIL。(f) 的前半與 (g)、(i) 在剝掉的版本上本來就成立（沒有後援），各自用突變紅：「後援不看主讀的型別就跑」→(f) 前半紅；「後援不看路徑」→(g) 紅；「後援不看 `restorePointValid`」→(i) 紅（審核第 3 項） |
| E2 | 守住的：v27 的 E2 全部；兩段可判的後援＋還原失敗 → `selection-not-restored`；每一種結果都帶 undo 紀錄；後援的 UNO 回覆缺席 → 判決不變（只記錄 `resultSeen:false`） | 突變：後援分支放在 NONE 拒絕之後 →(a) 紅；`blockCount` 條件拿掉 →(e) 紅；後援判斷式改讀第一段 →(b) 紅；還原檢查移回結構拒絕之後 →(j) 紅；後援不看型別就讀 html →(h) 紅 |
| E3 | 改過的原始碼上：`make test-v27-first-block-static` 全綠；`make -k test-e2-c-static` 除了 v27 前就具名的三個紅（`findings/evidence/v27-176/pre-link/README.md`）之外沒有新的紅；不在任何目標裡的三支 inc 文字測試（`test_ordered_format.py`、`test_ordered_format_scope.py`、`test_ordered_format_v25.py`）逐支跑、各留收據。以目標為單位而不是手列測試名（審核第 5 項：手列漏了 `test_format_readback_v27.py`，它切的正是 v28 改的 `parseFormatReadback`） | — |
| E4 | 正式解析器（帶 v28 define；前例 `format_readback_text_test.cpp`：從 `probe_engine.cpp` 以正規式抽出，不另寫一份；裁決 4 §4 第 4 項：`read_q52.py` 只是移植）跑錄下的 HTML。**列由工具產生**（審核第 10 項）：`native-q52/out/`、`out-actions/`、`out-headings/`、`out-v6/` 裡每一個 `cl-*` 格、`r1.jsonl` 的後援是 TEXT 的，都是一列；**例外**是 `out-actions/` 的三個偽標題格（`cl-body-heading-last`、`cl-nbody-sham-heading-last`、`cl-nhead-after-heading`），它們的期望取自錄下的解析結果並標為 L-pseudo-heading 列，不取自存檔。其餘列的期望：`(lastListTag, lastBlockTag, blockCount, itemCount)` 與最後一段判斷式，判斷式的期望取自存檔裡目標段落的狀態（v27 E4 的作法）。**另外**：v27 E4 的 18 列（`176/native/out*/…` 的 `format.html`，`tests/test_format_readback_v27.py:28-35`）以 v28 define 重跑，`(listTag, blockTag, blockCount, itemCount, multiBlock)` 與第一段判斷式逐列等於 v27 的期望（守「帶 v28 define 時既有欄位不變」，審核第 5 項）。關鍵列：`cl-n8`（第一段 ul、最後一段 none → 項目符號不符合）、`cl-a8`（最後一段 ul → 符合）、`cl-t1`（`unknownTag table`）、`cl-nnum-after-number`（第一段 ol、最後一段 none）、`cl-nhead-after-realheading`（最後一段 p、標題不符合）、`cl-nbody-realheading-last`（最後一段 h1、內文不符合）、`cl-body-realheading-last`（最後一段 p、符合）、`cl-long-300`（兩段、ul） | 改一個期望值要紅（落地前先做） |
| W1 | worker 對封存 v27 worker 的差異恰好是 §4.2 三項 | 多一行要紅 |
| W2 | worker 的 `fallback` 投影：物件 → 七個欄（含 `restoreConfirmed`）；缺 → `null`；型別不對的欄 → `null`；`readbackHtml` **不出現**；`fallback` 是回傳物件的最後一個欄位、`WORKER_BARRIER_ANCHOR` 的字串在 worker 裡恰好出現一次 | 五個反例：缺、型別錯、html 被投影出來、頂層 `fallback`（不在 `formatBarrier` 裡）被讀成投影、`fallback` 插在物件開頭（錨點斷掉） |
| V0-v28 | v23、v24、v25、v27 define 下每一個單元的前置處理輸出與改動前 HEAD 逐位元組相同 | 正向對照：共用段落改一個字，恰好那幾列不同 |
| S | em++ `-fsyntax-only`（v28 define）乾淨，`taskset -c 0`；正向對照：v28 才有的錯在帶 define 時被抓到、不帶時看不到；v28 define 不帶 v27 撞到 `#error`——打在 `editor_api.cpp` | 正向對照本身 |
| M1-1 | 載體行先紅後綠 | 證人 |
| L | `what_the_link_ships --variant link-batch-v28`；`check_v28_ships_confined.py`：改動全在 v28 區塊內、恰好是 §4.1 第 11 項 | 區塊外多一行；少一個宣告的 hunk |
| PL-1-v28 | **連結前的 WASM 觸發條件**（鏡像、v27 profile、不連結、不用 DDEV）：083 的配方（兩段文件，真的點最後一行行尾、真的 Enter、真的按工具列的項目符號），v27 PL-1 的觀察器（Chrome 走 CDP、Firefox 走鏡像診斷 worker），讀取工具 `read_v28_pl1.py`：每一筆是 `route collapsed`、`failureShape select-text-returned-none`、`selectionResultSeen true`；兩瀏覽器 × N＝3。**只證明 WASM 上會觸發後援**；後援的結果 v27 預測不了，本規格不假裝預測得了（裁決 4 §4 第 7 項） | `--self-test`：`route range-single`、`failureShape multi-block-readback`、`selectionResultSeen false`、少一筆，各自要紅 |
| PIN | §10 的原始碼釘選、凍結集合、v27 封存 `SHA256SUMS`、擁有者指令的 `make -n`（§5） | 釘選工具：改一個位元組要紅 |
| U-v28 | 殼層單元（先紅）：client——新形狀（dispatched、collapsed、`selectionResultSeen`）→ `dispatched-unverified`；同形狀 `dispatched:false` → `refused-no-mutation`；同形狀 `range-single` → rollback；同形狀 `selectionResultSeen:false` → rollback；`select-text-returned-none` 照舊 → review；`FALLBACK_REFUSED_SHAPES` 恰好一個名稱、`EMPTY_SELECTION_SHAPES` 照舊恰好兩個。頁面——新形狀 → 新句子（含「往前多選一格」與「不是你要的就按「復原」」，**不含**「最後一段」；一般樣式；提示裡沒有錯誤碼與英文、兩者在 `console.warn`；strip `：待確認`）；既有三句不變；`run()` 讀共用清單；三支頁面測試的注入參數加了新名稱（§4.3 第 3 項） | generation 81 的 client／頁面上，新形狀的處置是 rollback、句子是 046 那句：紅；見證 `u-v28/red-before.txt`；三支頁面測試在改過的頁面上、參數清單未改時紅：見證 `u-v28/page-tests-red-before.txt` |

**預設**：任一條沒做或紅案沒先紅，不交連結。

### 7.3 連結之後（靜態，連結當天；瀏覽器，鏡像，不用 DDEV）

- **P-v28**：五個 artifact 的雜湊、`check_v28_last_block_contract.py`（葉等於 v27、只換三個雜湊與兩個名字）、匯出表等於 v27、封存 `build/archive/e2-editor-v28-<wasm8>-worker-<worker8>`；凍結集合：既有的檔一個都沒變，新增的恰好是 v28 的四個 profile 檔。
- **切頁**：頁面改指 v28；generation 82 等本批殼層改動全部做完才凍：與 81 只差頁面與 client 兩個檔（工具算出的差異＝封閉清單）；排除清單＝81 的十個＋`sdk/v28-last-block-worker.js`（不排除的話差異是三個檔；審核第 6 項，v25 §15.2 是執行後才找到這一條、v27 事先宣告）；Makefile bundle 行改指 82（改前紅、改後綠、指回 81 紅）；`make -n e2-c-assets` 只印一行 `cp`。
- **S4（新，最後一行，使用者那條路）**：`tools/check_v82_last_line_bullet.py`。產品 before＝generation 81（v27），after＝generation 82 候選（v28）；兩瀏覽器 × N＝3；真的點、真的 Enter、真的按工具列、真的打字、按產品的存檔、讀存檔 ODT。
  - **S4-a**（兩段文件 `Plain first`／`E1-EMPTY-AFTER`，由 `native-q52/fixtures/two-plain.fodt` 經原生 core 一次 `saveAs` 成 ODT，收據與 sha 釘在工具裡）：點最後一行行尾、Enter、按項目符號、打一個標記字、存檔。after PASS（每一次）：`state == ready`；`#toast` 空；按鍵期間主控台沒有 `[review]`；strip `^• 項目符號 \d+ ms$`；**worker 回覆列**：回覆 ok、`completion == "verified-format-readback"`、`formatBarrier.fallback.ran == true`、`fallback.blockCount == 2`、`fallback.lastListTag == "ul"`；`fallback.restoreConfirmed == true`（worker 投影，§4.2；裁決 4 Q3.3 的條件：凍 82 之前 N/N；成功本來就隱含它，見 inc 的順序，但照樣讀）；按完之後**真的打一個標記字**，標記落在那一段（同時量到選取模式有清掉，§4.1 第 6 項）；存檔裡標記所在段落在項目符號的 `<text:list>` 裡、前一段文字與種類不變。之後兩次 Ctrl+Z（撤回打字、撤回清單；Enter 不撤）、再存檔：段落數是 3、前兩段的文字與種類不變、最後一段空且不在清單裡（v27 S3 的強度；審核第 13 項）。before 為 083 而紅：提示是 083 那句、`fallback` 不存在。突變：`--mutation press-list-none`（after 紅：沒有清單）；`--mutation cosmetic-review`（頁面變體在 before 上藏提示、不印 `[review]`、strip 寫 `N ms`）必須紅——只有 worker 回覆列抓得到（v27 S3 的教訓）。
  - **S4-b**：同一個配方換成編號、取消清單（最後一行本來是項目符號的文件）、標題、內文（最後一行是真的「標題 1」的文件；夾具由原生 core 套用「標題 1」後存出，前提段同 amendment 3：未動過的標題讀回 `<h1>`）。after：各自的目標狀態、`verified-format-readback`、`fallback.restoreConfirmed == true`、沒有提示、前一段文字與種類不變；一次 Ctrl+Z 撤回。before 為 083 而紅：083 那句、`fallback` 不存在。突變：每個動作一個「按錯按鈕」的變體（例如標題那格按內文），after 必須紅（審核第 13 項）。
  - **S4-c**（空白文件；B1／S2′ 的程序與條件不變）：083 那句、strip `：待確認`、`state ready`、worker 回覆列 `fallback.ran true`、`fallback.selectionType 0`。before 與 after 的使用者可見結果逐字相同。
  - **S4-d**（最後一行前面緊接一個表格；夾具由原生 `native-q52/fixtures/table-then-empty-last.fodt` 經 `saveAs`）：`review` 處置、新句子（含「往前多選一格」）、`state ready`、**沒有「請回到檢查點」**、`fallback.refusal == "unknown-structural-tag"`、`fallback.restoreConfirmed == true`（N/N）；按完之後**真的打一個標記字**、存檔：標記在最後一段、表格格子的文字仍是 `Cell text`（＝沒有留下使用者沒做的選取；審核第 1 項在使用者那條路上的量測）；按「復原」可撤回。before：083 那句（比較用，不判）。
  - **S4-e**（兩個 Enter，裁決 4 Q4.4「擁有者最可能的路」）：兩段文件、點最後一行行尾、Enter、Enter、按項目符號、打標記字、存檔：沒有提示、`verified-format-readback`、標記所在段落在項目符號清單裡、它前面那個空段落**不在**清單裡（原生 V7 的 a6 在 WASM 上的對應）。
  - `--self-test REPORT`：每個子句一個突變，全紅。
- **F3-82**：重新衍生 `run_e2_c_product_path_clipboard.py`（綁 v82 manifest，W-f3 的作法；衍生前後各跑一次舊值掃描）。讀法：`read_v80_f3_equal.py` 的衍生對 F3-81，**事先宣告的移動：無**（§6 的結論）；讀法一（`read_v25_f3.py`）預期與 F3-81 相同（`F3_RED`、同一組四個問題）。有任何移動就停下查清。
- **F4-82**：v80 四臂工具的衍生，兩瀏覽器 24/24。
- **E1-C**：`check_e1_c_bundle_intact.py` `intact: true`。
- **V0′-82**：照 v81 的作法，換回宣告的檔重讀 B1、F3-81 的讀取器，逐位元組相同。
- **預設**：任一條沒跑、NE、或有未宣告的移動，0.2.44 不送裝。

### 7.4 宿主 0.2.44

- 由 `findings/evidence/host-0.2.43/` 衍生（不改那些檔）：父＝`host-0.2.43` 的 `ae8240d`；前身 archive `host-0.2.43-engine-741afd80a36e673b`。套件裡有 `editor-shell-v2/`（所以 client 是一筆改動）；同一個套件的 ods 編輯器與檢視器頁面不 import `paragraph-editor-client.js`〔讀碼：import 它的只有 `e2-editor-app.js`、`narrow-editor-v2-client.js`、`narrow-editor-v2-session.js`、`paragraph-editor-session.js` 與不出貨的示範頁〕。
- 套件判準：對 0.2.43 恰好改 2 筆（頁面、client；裁決 4 §4 第 12 項寫「恰好 1 筆」，這裡更正：0.2.43 的套件 MANIFEST 帶著 `paragraph-editor-client.js`，審核第 20 項）、新增 4 筆（`profiles/e2-editor-v28/`）、移除 4 筆（`profiles/e2-editor-v27/`，工具先確認套件裡沒有別的頁面用 v27）。紅案：多一筆、少一筆、v28 的 wasm 等於 v27 的。
- 安裝要擁有者的時段（DDEV 共用），`slot.json` 有明確的「不開站」回答。
- 裝完：Files 實流程、`capture-after.py`（具名限制照舊）、請擁有者手測：(a) 有內容的文件，最後一行是空的，按項目符號 → 沒有提示；(b) 新的空白文件按項目符號 → 跟現在一樣那句提示；(c) (a) 之後 Ctrl+Z → 清單撤回；(d)（選做）文件最後是一個表格，在表格下一行按項目符號 → 新的那句提示、沒有要你回到檢查點、按「復原」可撤回。
- **預設**：沒有時段就不裝；0.2.43 仍是日常未計數候選。

## 8. 被綁的格子與讀取器：事先宣告的移動

1. **F3**：無。`bulleting-a-blank-line…` 是文件中間的空行，v27 已依設計退役（v27 §8 第 1 項），v28 不碰它；`recoveryPairing.held` 照 v27 是 false。
2. **B1、S2、S2′**：無（空白文件的使用者可見結果逐字不變）。
3. **K 的 `DISPOSITIONS.md`**：無（普查沒有讀最後一行的列）。
4. **殼層單元**：既有的全部照舊綠；新形狀另寫。

## 9. 具名限制與量測範圍外

- **L-083-stays-a-toast（縮小）**：只剩 (i) 只有一個空段落的文件，與往回選一格也離不開的位置（後援讀 NONE）——083 那句；(ii) `fallback-readback-refused`（前面是表格、附註、物件、段數不是 2）——新的那句。
- **L-pseudo-heading-reads-as-body**（兩條路都有、v27 之前就有）：段落的大綱層級只來自直接格式、樣式不是標題時，HTML 匯出寫 `<p>`，不論動作有沒有做都讀成內文。只在派送沒改到這種段落時才會誤判。具名、不修（裁決 4 Q5.1）。
- **L-fallback-rests-on-char-left-sel**：正確性靠 `FN_CHAR_LEFT_SEL` 的語意（§10）；core 升級就要重開。
- **L-noop-verified** 延伸到最後一行：本來就是目標狀態再按一次，判「已驗證」（後置條件成立），不宣稱是這次派送做的。
- **L-no-a11y-identity**：依構造（finding 074），後援不依賴段落識別。
- **L-fallback-html-read-is-new-on-this-path**（裁決 4 Q1.1；審核第 8 項）：今天 083 的路不讀 html（主讀 NONE），v28 在每一次最後一行的按壓都多一次後援的 html 讀取。finding 037／038 那一類（圖片、附註裡的 frame 讓 html 讀取卡住引擎執行緒，`probe_engine.cpp:5550-5560`）作為一類**不是 v28 新增的**（主讀在每個有字段落上都有同樣的曝露），但**在這條路上是新的**：空的派送段落整個在後援的選取裡，錨在它上面的 frame 依構造就在選取裡。沒量；卡住比今天的提示更糟。預設：具名限制（選做：一格 WASM 量測，圖片錨在空的最後一段）。
- **後援也在「不是文件最後一段」的 NONE 位置跑**（審核第 9 項）：表格格子、frame、附註裡的空的最後一段，以及下一個內容節點不相鄰的位置（v27 §9）。在那裡後援可能判出結果、也可能被拒；都沒量。新句子不說「最後一段」就是為此。
- **量測範圍外**（宣告，不是靜默略過）：右到左的最後一段（`Left(…, bVisual=true)` 是視覺方向，`txtcrsr.cxx:95-97`；未量，預期 NONE→083 那句，不在本規格宣稱）；游標在表格格子、frame、附註裡的空的最後一段；隱藏的追蹤刪除與合併段落；不同種類的巢狀清單；上一段結尾是 as-char 的 frame（後援只選分段、不含字，依量測 cl-a4 對 sa-a4，但這個形狀沒量）。

## 10. 原始碼釘選

兩棵樹（連結用的 `LOSRC`＝`../libreoffice-26-8`，由工具從 Makefile 讀出；原生證據用的 `native-lok-26-8/src`）裡下列檔案的 sha256 寫進 `findings/evidence/v28-083/pre-link/source-pin.json`；兩棵一致才算原生證據與連結的是同一份原始碼，不一致就記下差異、交裁決。v27 §10 的六個檔照舊釘，再加：

- `sw/sdi/swriter.sdi`（577：`CharLeftSel FN_CHAR_LEFT_SEL`）、`sw/sdi/_textsh.sdi`（1160）；
- `sw/source/uibase/shells/txtcrsr.cxx`（62-65：`FN_CHAR_LEFT_SEL` → `FN_CHAR_LEFT`＋選取；95-97：`rSh.Left(SwCursorSkipMode::Cells, bSelect, 1, false, true)`）；
- `sw/source/uibase/wrtsh/move.cxx`（55-61：`ShellMoveCursor` 呼叫 `MoveCursor(bSel)`；76-91：`MoveCursor` 在選取時先 `SttSelect()`；112-127：`SwWrtShell::Left`）；
- `sw/source/core/crsr/swcrsr.cxx`（1765 起：`SwCursor::LeftRight`，移動真正發生的地方；「往回一格剛好跨過一個分段」靠它；審核第 14 項）；
- `sw/source/uibase/wrtsh/select.cxx`（409-410：`SttSelect` 在已是選取模式時返回；§4.1 第 6 項的選取模式推論）；
- `sw/source/core/crsr/crsrsh.cxx`（326-380：`LeftRight`；第 2 種情況「在已編號段落開頭往左只設 in-front-of-label」要求 `!HasMark()`，選取時已有 mark，所以走第 3 種一般移動——這是後援在剛套上清單的段落上也會移動的原因，量測一致）；
- `desktop/source/lib/init.cxx`（6023-6024：純文字超過 10,000 字元回 `LOK_SELTYPE_COMPLEX`，`.uno:SelectAll` 不採用的紀錄理由；6026-6027：純文字是空的回 NONE，空白文件讀 NONE 的機制）。

## 11. 順序

1. 本規格草案 → 對抗性審核 → 釘死（commit）。
2. 追加：finding 176；v27 規格（Q6.3 b1 的偽標題前提，裁決 4 Q5.2）；046 若被觸及。
3. U-v28 先紅（見證）→ client、頁面 → U-v28 綠、殼層測試全綠；E1-C 前後各一次。
4. 引擎：E1 先紅（見證）→ 改動 → E1、E2、E3、E4、V0-v28、S 全綠。
5. worker → W1、W2；Makefile／工具／連結腳本 → `test-v28-last-block-static` 綠；M1-1；L；PIN。
6. PL-1-v28（鏡像、v27、兩瀏覽器；可與 3–5 平行，交連結前要成立）。
7. 交擁有者連結（一行指令＋手冊 `handoff/RUNBOOK-relink-v28.md`）。
8. P-v28 → 切頁 → S4 → 凍 generation 82 → F3-82、F4-82、V0′-82、E1-C。
9. 宿主 0.2.44 套件 → 擁有者時段 → 安裝 → Files 實流程 → 事後讀取 → 擁有者手測。

**累積的未計數改動**（計數鏈併批，擁有者 10-12）：0.2.26 之後的 v22–v27 與本批 v28。K 照舊另排。

## 12. §34.4

本規格釘死之前：因執行而修 **3**（native-q52：self-test 的 scope 索引、標題讀取器的段落位置、amendment 2 的 UNSAFE 子句方向）；因審核而修 **20**（opus 對抗性審核，2026-10-30，20 項全數採用；主 session 先讀碼確認了第 1、2、4、7、12、14、17 項〔`ordered_format.inc:11-13、328-330`；`page-review-sentence.test.mjs:41-48`；`probe_engine.cpp:1730-1769`；`v27-first-block-worker.js:350-441` 沒有 `restoreConfirmed`；`run_e2_c_product_path.py:287`；`swcrsr.cxx:1765`、`init.cxx:6026-6027`；`test_ordered_format.py:25`〕，其餘是規格文字與判準形式）。其中第 1 項讓 §3 的拒絕順序偏離裁決 4 Q2.3，理由寫在 §3。fable 裁決：本輪 1 次（裁決 4）。

## 13. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-10-30 | 草案。 |
| 2026-10-30 | 草案第二版：併入對抗性審核 20 項（§12）。 |
| 2026-10-30 | 釘死。 |
| 2026-10-30 | 追加 1（§14，S4 執行前）：S4 的程序細節。 |
| 2026-10-31 | 追加 2（§14，量測前）：L-fallback-html-read-is-new-on-this-path 的 WASM 量測判準。 |

## 14. 追加

### 追加 1（2026-10-30，S4 的工具寫好、任何 S4 執行之前）

§7.3 S4 寫的是判準，程序有幾處沒寫死；以下在第一次執行前定下，不改任何判準。

1. **夾具。** S4-a、S4-e、S4-b 的編號與標題：S3 的 `findings/evidence/v27-176/fixture-two-plain/build-01/two-plain.odt`（`56bc01b0…`）——它的來源就是 `native-q52/fixtures/two-plain.fodt`（兩份 `8d996d45…` 逐位元組相同），原生 core 存一次，收據在旁邊；不另存一份。S4-b 的取消清單（`fixtures-v6/bulleted-last.fodt`）、內文（`fixtures-headings/realheading-last.fodt`）與 S4-d（`fixtures/table-then-empty-last.fodt`）：`findings/evidence/v28-083/fixtures-s4/make_s4_odts.py`（S3 製作器的衍生）以原生 core 各存一次，`build-01/receipt.json`；未動過的三份以 S3 儀器的 `odt_reading` 讀過一次（`build-01/instrument-reading.txt`）：取消清單那份最後一段是空的項目符號、內文那份最後一段是空的 `text:h`（樣式 `Heading_20_1`，不是偽標題）、表格那份是 `Plain first`／`Cell text`／空段落。
2. **點的位置。** 一律點在文字下方（PL-1-v28 的點，`#paper` 的 (0.80, 0.15)）：Writer 把游標放在最後一段的結尾。S3 的 `LINE_END` 是第一行的行尾，不用。
3. **Enter。** S4-a 與 S4-b 的編號、標題按一次 Enter（兩段文件新增一個空的最後一段），S4-e 按兩次。**S4-b 的取消清單、內文與 S4-d 不按 Enter**：這三份夾具的最後一段本身就是空的目標段落（原生臂量的就是這幾份夾具的最後一段，沒有 Enter）；在表格那份按 Enter 會多一個空段落，後援就讀到兩個空段落而不是表格（V7 `cl-a6-end` 的形狀），S4-d 就量不到它要量的。
4. **S4-b 不打標記字**：按完就存檔，最後一段依位置讀；之後一次 Ctrl+Z、再存檔，最後一段回到夾具的狀態（取消清單：回到項目符號；內文：回到 `text:h`；編號、標題：回到不在清單裡的 `text:p`）。
5. **S4-b「按錯按鈕」的對應**：編號→按項目符號、取消清單→按編號、標題→按內文、內文→按標題。
6. **S4-d 的「按「復原」」**：打完標記字之後按工具列的「↶ 復原」兩次（撤回打字、撤回清單），再存檔：最後一段空、不在清單裡，表格格子仍是 `Cell text`。
7. **S4-c**：B1 的程序（兩個 arm：noclick、click）照 S2′ 的跑法，兩個產品都用 S2′ 的 `judge_after`（第 81 代本來就是「：待確認」）。after 另讀 worker 回覆列：`fallback.ran == true`、`fallback.selectionType == 0`；before：回覆列沒有 `fallback`。「使用者可見結果逐字相同」＝每一筆的（`pill`、`#toast` 文字、按壓後與打字後的狀態列、檢查點提示是否顯示）在兩個產品的全部執行裡是同一個值。
8. **S4-e 與 S4-d 的 before 只記錄、不判**（§7.3 沒有給它們 before 的判準）。

### 追加 2（2026-10-31，擁有者「請執行A」；任何這一格的執行之前）

§9 的 L-fallback-html-read-is-new-on-this-path 標著「選做：一格 WASM 量測」。擁有者選了做。後援的 `readSelection()` 與 html 讀取，在這條路上第一次碰到錨在空的派送段落上的 frame；finding 037／038 那一類會讓引擎執行緒卡死，比今天的提示更糟。

1. **夾具**（`findings/evidence/v28-083/a-frames/make_frame_fixtures.py`，`build-01/`，原生 core 各存一次；未動過的五份已用儀器的 `odt_reading` 讀過，`build-01/instrument-reading.txt`）：`frame-para-last`（圖片錨在空的最後一段）、`frame-char-last`（錨在字元）、`textbox-para-last`（文字方塊）；§9「量測範圍外」的兩個鄰居：`prev-aschar-image`（上一段以 as-char 圖片結尾）、`prev-note-frame`（上一段以註腳結尾，註腳本文裡有 as-char 圖片，038 的形狀）。
2. **程序**（`tools/check_v82_frame_last_line.py`，S4 的 `one()`，不按 Enter）：開檔、點文字下方、按項目符號、打標記字、存檔。after 產品（generation 82），兩瀏覽器 × 3。
3. **每一筆 HOLDS 要全部成立**：(a) 按壓有回覆（沒有等到逾時）；(b) `state == ready`；(c) 打字成功（引擎還活著）；(d) 存檔成功，標記只在派送段落，其他段落的文字與種類等於夾具；(e) 存檔裡 `draw:frame` 的數量等於夾具；(f) 回覆列 `fallback.ran == true`、`fallback.restoreConfirmed == true`；(g) 若回覆是 `verified-format-readback`，派送段落在存檔裡必須真的是項目符號（不准判對而其實沒套上）。結果是已驗證或 `fallback-readback-refused`（review）都算成立，形狀逐筆記錄：這一格問的是「會不會卡死或判錯」，不是「能不能核對」。
3a. **主讀就是 COMPLEX 的格**（工具 commit 前的第一次 smoke 逼出，那次不計）：`frame-char-last` 的 `.uno:SelectText` 選到字元錨點，主讀回 COMPLEX，finding 037 的守則回 `selection-type-not-readable`，後援根本不跑。那條路不是這一格要量的，第 3 項的 (b)(c)(d)(e)(f) 讀不到它。改判：(a) 有回覆；回覆是 `MUTATION_OUTCOME_UNKNOWN`／`selection-type-not-readable`；`fallback.ran` 不是 true；頁面是 `ready` 或 `recoverable-error`（沒有進 `restart-required`）。另以 `--product before` 在 generation 81 上跑同一格，同樣成立才算「v28 之前就有」。
4. **判定**：五格全 HOLDS → `A_FRAMES_HOLD`，§9 那條限制改寫成量測結果。任一格卡死（a、b、c 任一不成立）或判錯（g）→ `A_FRAMES_RED`，是產品缺陷，先開 finding，修法要新規格，**不進 K**。
5. **正向對照**（否則「沒卡死」與「儀器看不到卡死」長得一樣）：`--mutation swallow-press`，頁面送出的項目符號請求被擋在 worker 之前，從頁面看就是引擎不回。每一筆必須判卡死（兩瀏覽器 × 1）。另有 `--self-test`：每個子句一個突變，全紅。
6. **沒做的預設**：§9 那條照舊是沒量的具名限制。

