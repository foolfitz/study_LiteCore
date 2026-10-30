# SPEC-M3-v28-last-line-fallback：文件最後一行的空段落改用「往回選一格」核對（引擎 `e2-editor-v28`、殼層 generation 82、宿主 0.2.44）

> 狀態：**草案**（未釘死；對抗性審核前）。釘死之後只准追加（CLAUDE.md 第 10 節）。
> 依據：finding 176、finding 083；fable 裁決 3（`findings/evidence/176/RULING-fable-2026-10-30-c.md`，Q5）；fable 裁決 4（`findings/evidence/176/RULING-fable-2026-10-30-d.md`，以下寫成「裁決 4 Q3.2」；§4 是本規格的檢查清單）；原生臂 `findings/evidence/176/native-q52/`（V1–V7，`15cd044a1`…`2939814ae`）。
> 擁有者 2026-10-30：「A. 量 083 那格」→「A. 做多段文件最後一行（推薦）」（v28：選不到東西時改成往回選一格、判斷看最後一段；空白文件照舊跳提示；設計先交 fable；規格前補量另外四個動作）→ 裁決 4 之後兩題都選 A：游標放不回去「照引擎原本規則」（rollback）、表格那格「新寫一句」。

## 1. 為什麼要有

v27 之後，文件中間的空行按清單已經會被核對（finding 176 的 046 那格）。但**最後一行**的空段落照舊跳 083 那句「這一段是空的，檢查要用的選取取不到任何內容……」：`.uno:SelectText`（`FN_SELECT_PARA`）在空段落上要往下跳一個內容節點，最後一段後面沒有節點，什麼都選不到（`select-text-returned-none`）。最常見的兩條使用者路都會走到這裡：打一行字、Enter、按項目符號；以及全新的空白文件按項目符號。

原生量測（`native-q52/README.md`，判準都在執行前登錄）：

- **空白文件（只有一個空段落）救不了**：`.uno:SelectAll`、`.uno:CharLeftSel` 都讀 NONE（5/5，五個動作、sham、no-op 都一樣）；沒有非空的選取存在（V1 `ONE-BLOCK-DOES-NOT-VERIFY`）。
- **多段文件的最後一行讀得到**：從空的最後一段往回選一格（`.uno:CharLeftSel`），剛好跨過一個分段，讀回兩段：上一段的尾巴（不含任何字）與派送那一段；**最後一段**的清單狀態與段落標籤在每一輪都等於存檔（V3、V7）；五個動作都成立（項目符號 V3、編號／取消清單 V6、標題／內文 V5），各自的反例沒有一個被說成成功。
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
| 何時跑 | collapsed 路徑、`.uno:SelectText` 的同步讀取是 NONE；同一個有序指令內、在唯一一組 Q 還原之前；中間不插讀取或 yield | 裁決 4 §1、Q9 |
| 判法 | 新判斷式 `formatBarrierFallbackReadbackSatisfied()`：讀 `lastListTag`／`lastBlockTag`；拒絕順序 (i) 不是 TEXT、(ii) 既有四個結構旗標、(iii) `blockCount != 2`、(iv) `restoreConfirmed` false、(v) 判斷式 | 裁決 4 Q2.3–Q2.4 |
| `blockCount == 2` | 必要條件；不限制第一段、不限制 `itemCount`、不讀 `multiBlock` | 裁決 4 Q2.4；22 格（18 格正式量測＋4 格 smoke）每輪都剛好 2 段，主 session 重算（裁決 4 檔尾） |
| 後援讀 NONE | 結束形狀照舊 `select-text-returned-none`、訊息照舊；紀錄多 `fallback` 物件 | 裁決 4 Q3.1（finding 173 的教訓：改名就掉出 `EMPTY_SELECTION_SHAPES`） |
| 後援讀到但不能判 | 新形狀 `fallback-readback-refused`，子原因在 `fallback.refusal`（沿用既有名稱，加 `unexpected-block-count`）；殼層對到 `dispatched-unverified`（review） | 裁決 4 Q3.2 |
| 那一句提示 | 新寫一句（§4.3） | 擁有者「A. 新寫一句」；finding 061 的前例（對別的情況才成立的句子是缺陷） |
| 判了、不符合 | `postcondition-not-met`（rollback），與有字段落相同 | 裁決 4 Q3.4、裁決 3 Q1.2 的對稱；不是「比今天更嚴重」——那條限制管的是「判不了」 |
| 游標放不回去 | 照舊 `selection-not-restored`（rollback） | 擁有者「A. 照引擎原本規則」；裁決 4 Q3.3；原生 0/205 |
| 後援的 UNO 回覆 | 預期它、記錄 `fallback.resultSeen`，**不當判決條件**（它對選不到東西也回 `success:true`，README §7）；讀法直接查 `gOrderedProof.uno`，不呼叫 `orderedUnoResult`（後者讀不到時會設 `missingReported`、蓋掉同一指令裡之後的缺席回報） | 裁決 4 Q3.5；`ordered_engine_state.inc:39-63` |
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
3. **`parseFormatReadback`**：在 `depth` 旁加一個「開著的結構標記」堆疊（只推、彈結構標記，與 `depth` 同步）；每遇到一個區塊標記（`formatTagIsBlock`）就寫 `lastBlockTag = tag`、`lastListTag = 堆疊裡最內層的 ul／ol，沒有就空字串`。`malformedNesting`、`unknownTag`、`footnoteApparatus`、`listTag`、`blockTag`、`blockCount`、`itemCount`、`multiBlock` 的算法逐位元組不變（這些欄位在不帶 v28 define 時與今天相同，V0 守）。
4. **`FormatStateBarrier`** 加後援欄位：`fallbackRan`、`fallbackResultSeen`、`fallbackSelectionType`（初值 -1）、`fallbackReadable`、`fallbackReadbackBytes`、`fallbackReadbackHtml`（同一個證據上限 `FormatReadbackEvidenceLimit`）、`fallbackReadback`（`FormatReadback`）、`fallbackRefusal`（字串）。
5. **`formatBarrierFallbackReadbackSatisfied()`**（新函式）：照抄 `formatBarrierReadbackSatisfied()`（約 5747-5769）的結構，改讀 `fallbackReadable` 與 `fallbackReadback` 的 `lastListTag`（空字串讀成 `none`）／`lastBlockTag`。原函式不動。
6. **`ordered_format.inc` `startOrderedFormatAction`** 的 collapsed 分支：在 `.uno:SelectText` 的同步讀取（與既有的 html 讀取）之後、`restoreOrderedFormatPoint()` 之前，若 `barrier.route == Collapsed && selected.type == LOK_SELTYPE_NONE`：
   `fallbackRan = true` → `expectOrderedUno(".uno:CharLeftSel")` → `postUnoCommand(".uno:CharLeftSel", nullptr, true)` → `readSelection()` → `fallbackSelectionType` → 若 TEXT：`getTextSelection("text/html")`、`fallbackReadbackBytes`、`fallbackReadbackHtml`、`fallbackReadback = parseFormatReadback(markup)`。中間不插任何讀取、事件迴圈 yield 或等待 callback。之後照舊是唯一一組 Q 還原與它的 NONE 確認、undo 的第二次讀取。SelectText 讀到 TEXT 時不送後援（v27 的呼叫序列逐位元組不變）；RangeSingle 不送後援。
7. **`deferOrderedFormatReply`**：在既有的 `selectionResultSeen` 之後，若 `fallbackRan`：直接查 `gOrderedProof.uno` 裡 `.uno:CharLeftSel` 那一筆的 `seen` → `fallbackResultSeen`。缺席不是失敗、不呼叫 `orderedUnoResult`（§3）。
8. **`finishOrderedFormatReadback`**：在既有的 `selectionTypeReadable` 檢查（NONE 拒絕，約 30-36 行）**之前**加後援分支：若 `fallbackRan`：
   1. `fallbackSelectionType == LOK_SELTYPE_NONE` → 不做任何事，往下走到既有的 NONE 拒絕（`select-text-returned-none`，訊息不變）；
   2. 不是 TEXT（例如 COMPLEX）→ 拒絕，形狀 `fallback-readback-refused`，`fallbackRefusal = "selection-type-not-readable"`；
   3. `!parsed`／`unknownTag`／`malformedNesting`／`footnoteApparatus` → `fallback-readback-refused`，`fallbackRefusal` 用既有的名稱（`block-extraction-failed`／`unknown-structural-tag`／`malformed-readback-nesting`／`footnote-apparatus-readback`）；
   4. `fallbackReadback.blockCount != 2` → `fallback-readback-refused`，`unexpected-block-count`；
   5. 段落識別：照非 cross 分支今天的寫法算（空段落→「未檢查」）；識別成立而指紋不同 → 既有的 `readback-is-a-different-paragraph`（產品 core 上到不了）；
   6. `!restoreConfirmed` → 既有的 `selection-not-restored`；
   7. `!formatBarrierFallbackReadbackSatisfied()` → 既有的 `postcondition-not-met`（`EDITOR_FORMAT_POSTCONDITION_FAILED`）；
   8. 否則 `completeFormatBarrier()`。
   2–4 的錯誤碼是 `MUTATION_OUTCOME_UNKNOWN`（與今天 083 的路相同），訊息是新的一句：「the fallback selection's readback does not provide a supported structural proof; the format mutation outcome is unknown」。回覆組成裡不呼叫任何 LOK（`test_ordered_format_scope.py` 的 `violations()` 守）。
9. **`appendFormatBarrierDetails`**：每一筆紀錄都帶 `fallback`：沒跑 → `{"ran":false}`；跑了 → `{"ran":true,"command":".uno:CharLeftSel","resultSeen":…,"selectionType":…,"readable":…,"readbackBytes":…,"readback":{"parsed","unknownTag","malformedNesting","footnoteApparatus","listTag","blockTag","lastListTag","lastBlockTag","blockCount","itemCount","multiBlock"},"readbackHtml":"…","refusal":"…"}`。主讀回的物件也多 `lastListTag`／`lastBlockTag`（便宜，而且讓證據裡第一段對最後一段看得見，裁決 4 Q2.2）。
10. **前置處理不變（V0-v28）**：以 v23、v24、v25、v27 的 define 前置處理 `E2_C_SOURCES` 的每一個單元（含 `unoembind_stub`），輸出與改動前的 HEAD 逐位元組相同。
11. **宣告的 hunk**（封閉清單）：第 1–9 項，恰好這些。不改 `formatBarrierReadbackSatisfied`、`restoreOrderedFormatPoint`、undo 的兩次讀取、RangeSingle 與 RangeCross 的分支。

### 4.2 worker（`sdk/v28-last-block-worker.js`）

由封存的 v27 worker（`build/archive/e2-editor-v27-c089dfd6-worker-8152448a/sdk-worker.js`，`8152448ab83b…`）衍生，差異是封閉清單：

1. `featureExtendPermitted` 的 `"e2-editor-v27"` → `"e2-editor-v28"`（v26 規格 §4.2：不改，行延伸靜默失效）。
2. `productFormatBarrier` 加 `fallback`：`value.fallback` 是物件時投影 `{ran, selectionType, blockCount, lastListTag, lastBlockTag, refusal}`（`blockCount`、`lastListTag`、`lastBlockTag` 取自 `value.fallback.readback`；型別不對的欄 → `null`）；否則 `null`。**不投影 `readbackHtml`**。
3. 檔頭註解說明衍生來源與本節。

### 4.3 頁面與殼層

`editor-shell-v2/paragraph-editor-client.js`：

1. 匯出 `FALLBACK_REFUSED_SHAPES = Object.freeze(["fallback-readback-refused"])`，註解同 `EMPTY_SELECTION_SHAPES` 的「兩個讀者」警告（頁面從同一份清單選句子）。`EMPTY_SELECTION_SHAPES` **不改**（它的單元測試釘著恰好兩個名稱）。
2. `formatFailureDisposition`：在 083 那條分支旁加一條：`dispatched === true && route === "collapsed" && FALLBACK_REFUSED_SHAPES.includes(failureShape) && selectionResultSeen === true` → `"dispatched-unverified"`。其餘不變（沒有這條，新形狀會落到最後的 `dispatched-rollback`，finding 173 的形狀）。

`web/e2-editor-app.js`：

3. `run()` 的 `review` 句子：在 083 那句與 046 那句之間加一個分支：`FALLBACK_REFUSED_SHAPES.includes(shape)` →「動作已送出，但這是文件的最後一段，檢查改用的選取碰到表格或其他讀不了的內容，所以無法核對。請看一下結果，不是你要的就按「復原」。這是檢查的極限，不是文件壞了」。保留各句共用的「不是你要的就按「復原」」（被綁的 F3 判準讀這幾個字）。
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
| 殼層單元 `page-review-sentence.test.mjs`（`EMPTY_SELECTION_SHAPES` 恰好兩個）、`page-review-presentation.test.mjs`（083 的引擎訊息原文）、`page-review-latency.test.mjs`、`paragraph-editor-client.test.mjs` | 既有三句、兩個空選取名稱、處置 | 不動（`EMPTY_SELECTION_SHAPES` 不改、訊息不改）；新形狀另寫測試（§7.2 U-v28） |
| 頁面 `e2-editor-app.js` 2162-2193 | 依形狀選句 | 改（§4.3 第 3 項） |
| 其他 import client 的頁面（`demo-structure-app.js`、`e2b-*-app.js`、`e2-c-d2-app.js`；不在宿主套件裡）與 ods 頁面（不 import） | 處置 | 新分支只對新形狀生效；舊形狀的處置不變 |
| client `paragraph-editor-client.js` 295-364 | 處置 | 改（§4.3 第 1–2 項） |
| worker `v27-first-block-worker.js` 等 | `selectionResultSeen` 投影 | v28 worker 衍生（§4.2）；舊 worker 不動 |
| 引擎測試 `tests/ordered_format_test.cpp:127`（「NONE has precise shape」）、`test_ordered_format.py`、`test_e2_profile.py:370` | NONE 的形狀、`selectionResultSeen` 的程式文字 | 不帶 v28 define 編，不動；v28 的行為由 E1 釘 |
| `diag_format.py`（v25 F1）、`probe_099…`、`e2-c-d3-app.js`、歷史 README／PREDICTION | 歷史 | 本批不跑 |

**結論**：被綁的檢查裡沒有一個讀「多段文件的最後一行」；F3-82 對 F3-81 **預期沒有任何移動**（§8）。

## 7. 判準

證據目錄 `findings/evidence/v28-083/`。每條都有「沒做的話」的預設。

### 7.1 釘死前（已做；原生，agent 自己跑）

- **N-q52**（`findings/evidence/176/native-q52/`）：V1 `ONE-BLOCK-DOES-NOT-VERIFY`（空白文件）；V2、V3 `LAST-HOLDS`；V4 `LAST-UNSAFE`（照登錄；成因是偽標題夾具，amendment 3 的前提段）；V5 標題、內文 IN-SCOPE；V6 編號、取消清單 IN-SCOPE；V7 `V7-HOLDS`（300 行 577 bytes、結尾兩個空行）。所有正式量測的還原 205/205。每一組判準都在執行前 commit（`15cd044a1`、`cce4a7e76`、`e798427f8`、`dd8a74fcd`），結果在之後的 commit。

### 7.2 連結前（原始碼與單元測試，agent 自己跑）

| 編號 | 判準 | 紅案（先紅） |
|---|---|---|
| E1 | 新單元測試 `tests/ordered_format_v28_test.cpp`（`test_ordered_format_v28.py` 驅動，前例 v27）：(a) collapsed、主讀 NONE、後援 TEXT、兩段、最後一段符合 → 成功、`completion verified-format-readback`、紀錄 `fallback.ran:true`、`lastListTag`／`lastBlockTag` 有送出；**(b) n8 的陷阱**：第一段 `ul`、最後一段 `none`、目標項目符號 → `EDITOR_FORMAT_POSTCONDITION_FAILED`／`postcondition-not-met`（第一段判斷式會讓它過，所以它是「新判斷式真的被讀」的證人）；(c) 主讀 NONE、後援 NONE → `MUTATION_OUTCOME_UNKNOWN`／`select-text-returned-none`、`fallback.selectionType:0`、訊息與 v27 相同；(d) 後援 `unknownTag:table` → `fallback-readback-refused`、`fallback.refusal:unknown-structural-tag`；(e) 後援三段 → `fallback-readback-refused`／`unexpected-block-count`；(f) 呼叫序列：主讀 TEXT 時沒有後援的 post（與 v27 逐呼叫相同）；後援的 post 在 NONE 讀取之後、唯一一組 Q 序列之前；(g) RangeSingle 主讀 NONE → 沒有後援的 post | 「v27 的行為」＝把 v28 區塊剝掉、**帶著** v28 define 編：必須編得過，且 (a)–(g) 印 FAIL |
| E2 | 守住的：v27 的 E2 全部；後援＋還原失敗 → `selection-not-restored`；每一種結果都帶 undo 紀錄；後援的 UNO 回覆缺席 → 判決不變（只記錄 `resultSeen:false`） | 突變：後援分支放在 NONE 拒絕之後 →(a) 紅；`blockCount` 條件拿掉 →(e) 紅；後援判斷式改讀第一段 →(b) 紅 |
| E3 | 改過的 inc 上，三支既有的 inc 文字測試照舊綠（`test_ordered_format.py`、`test_ordered_format_scope.py`、`test_ordered_format_v25.py`）；`test_ordered_format_v27.py` 不帶 v28 define 照舊綠。逐支跑、各留收據 | — |
| E4 | 正式解析器跑錄下的後援 HTML（前例 `format_readback_text_test.cpp`：從 `probe_engine.cpp` 以正規式抽出，不另寫一份；裁決 4 §4 第 4 項：`read_q52.py` 只是移植）：`native-q52/out/cl-*`、`out-actions/`、`out-headings/`、`out-v6/` 的 `r1.jsonl` 的 `fallback.html`；期望 `(lastListTag, lastBlockTag, blockCount, itemCount)` 與每個目標的最後一段判斷式。關鍵列：`cl-n8`（第一段 ul、最後一段 none → 項目符號不符合）、`cl-a8`（最後一段 ul → 符合）、`cl-t1`（`unknownTag table`）、`cl-nnum-after-number`（第一段 ol、最後一段 none）、`cl-nhead-after-realheading`（最後一段 p、標題不符合）、`cl-nbody-realheading-last`（最後一段 h1、內文不符合）、`cl-body-realheading-last`（最後一段 p、符合）、`cl-long-300`（兩段、ul） | 改一個期望值要紅（落地前先做） |
| W1 | worker 對封存 v27 worker 的差異恰好是 §4.2 三項 | 多一行要紅 |
| W2 | worker 的 `fallback` 投影：物件 → 六個欄；缺 → `null`；型別不對的欄 → `null`；`readbackHtml` **不出現** | 四個反例：缺、型別錯、html 被投影出來、頂層 `fallback`（不在 `formatBarrier` 裡）被讀成投影 |
| V0-v28 | v23、v24、v25、v27 define 下每一個單元的前置處理輸出與改動前 HEAD 逐位元組相同 | 正向對照：共用段落改一個字，恰好那幾列不同 |
| S | em++ `-fsyntax-only`（v28 define）乾淨，`taskset -c 0`；正向對照：v28 才有的錯在帶 define 時被抓到、不帶時看不到；v28 define 不帶 v27 撞到 `#error`——打在 `editor_api.cpp` | 正向對照本身 |
| M1-1 | 載體行先紅後綠 | 證人 |
| L | `what_the_link_ships --variant link-batch-v28`；`check_v28_ships_confined.py`：改動全在 v28 區塊內、恰好是 §4.1 第 11 項 | 區塊外多一行；少一個宣告的 hunk |
| PL-1-v28 | **連結前的 WASM 觸發條件**（鏡像、v27 profile、不連結、不用 DDEV）：083 的配方（兩段文件，真的點最後一行行尾、真的 Enter、真的按工具列的項目符號），v27 PL-1 的觀察器（Chrome 走 CDP、Firefox 走鏡像診斷 worker），讀取工具 `read_v28_pl1.py`：每一筆是 `route collapsed`、`failureShape select-text-returned-none`、`selectionResultSeen true`；兩瀏覽器 × N＝3。**只證明 WASM 上會觸發後援**；後援的結果 v27 預測不了，本規格不假裝預測得了（裁決 4 §4 第 7 項） | `--self-test`：`route range-single`、`failureShape multi-block-readback`、`selectionResultSeen false`、少一筆，各自要紅 |
| PIN | §10 的原始碼釘選、凍結集合、v27 封存 `SHA256SUMS`、擁有者指令的 `make -n`（§5） | 釘選工具：改一個位元組要紅 |
| U-v28 | 殼層單元（先紅）：client——新形狀（dispatched、collapsed、`selectionResultSeen`）→ `dispatched-unverified`；同形狀 `dispatched:false` → `refused-no-mutation`；同形狀 `range-single` → rollback；同形狀 `selectionResultSeen:false` → rollback；`select-text-returned-none` 照舊 → review；`FALLBACK_REFUSED_SHAPES` 恰好一個名稱、`EMPTY_SELECTION_SHAPES` 照舊恰好兩個。頁面——新形狀 → 新句子（含「最後一段」與「不是你要的就按「復原」」，一般樣式，strip `：待確認`）；既有三句不變；`run()` 讀共用清單 | generation 81 的 client／頁面上，新形狀的處置是 rollback、句子是 046 那句：紅；見證 `u-v28/red-before.txt` |

**預設**：任一條沒做或紅案沒先紅，不交連結。

### 7.3 連結之後（靜態，連結當天；瀏覽器，鏡像，不用 DDEV）

- **P-v28**：五個 artifact 的雜湊、`check_v28_last_block_contract.py`（葉等於 v27、只換三個雜湊與兩個名字）、匯出表等於 v27、封存 `build/archive/e2-editor-v28-<wasm8>-worker-<worker8>`；凍結集合：既有的檔一個都沒變，新增的恰好是 v28 的四個 profile 檔。
- **切頁**：頁面改指 v28；generation 82 等本批殼層改動全部做完才凍：與 81 只差頁面與 client 兩個檔（工具算出的差異＝封閉清單）；Makefile bundle 行改指 82（改前紅、改後綠、指回 81 紅）；`make -n e2-c-assets` 只印一行 `cp`。
- **S4（新，最後一行，使用者那條路）**：`tools/check_v82_last_line_bullet.py`。產品 before＝generation 81（v27），after＝generation 82 候選（v28）；兩瀏覽器 × N＝3；真的點、真的 Enter、真的按工具列、真的打字、按產品的存檔、讀存檔 ODT。
  - **S4-a**（兩段文件 `Plain first`／`E1-EMPTY-AFTER`，由 `native-q52/fixtures/two-plain.fodt` 經原生 core 一次 `saveAs` 成 ODT，收據與 sha 釘在工具裡）：點最後一行行尾、Enter、按項目符號、打一個標記字、存檔。after PASS（每一次）：`state == ready`；`#toast` 空；按鍵期間主控台沒有 `[review]`；strip `^• 項目符號 \d+ ms$`；**worker 回覆列**：回覆 ok、`completion == "verified-format-readback"`、`formatBarrier.fallback.ran == true`、`fallback.blockCount == 2`、`fallback.lastListTag == "ul"`；**引擎紀錄** `restoreConfirmed:true`（裁決 4 Q3.3 的條件：凍 82 之前 N/N）；存檔裡標記所在段落在項目符號的 `<text:list>` 裡、前一段不變。之後兩次 Ctrl+Z、再存檔：沒有清單。before 為 083 而紅：提示是 083 那句、`fallback` 不存在。突變：`--mutation press-list-none`（after 紅：沒有清單）；`--mutation cosmetic-review`（頁面變體在 before 上藏提示、不印 `[review]`、strip 寫 `N ms`）必須紅——只有 worker 回覆列抓得到（v27 S3 的教訓）。
  - **S4-b**：同一個配方換成編號、取消清單（最後一行本來是項目符號的文件）、標題、內文（最後一行是真的「標題 1」的文件；夾具由原生 core 套用「標題 1」後存出，前提段同 amendment 3：未動過的標題讀回 `<h1>`）。after：各自的目標狀態、`verified-format-readback`、沒有提示。
  - **S4-c**（空白文件；B1／S2′ 的程序與條件不變）：083 那句、strip `：待確認`、`state ready`、worker 回覆列 `fallback.ran true`、`fallback.selectionType 0`。before 與 after 的使用者可見結果逐字相同。
  - **S4-d**（最後一行前面緊接一個表格；夾具由原生 `native-q52/fixtures/table-then-empty-last.fodt` 經 `saveAs`）：`review` 處置、新句子（含「最後一段」）、`state ready`、**沒有「請回到檢查點」**、`fallback.refusal == "unknown-structural-tag"`；按「復原」可撤回清單。before：083 那句（比較用，不判）。
  - `--self-test REPORT`：每個子句一個突變，全紅。
- **F3-82**：重新衍生 `run_e2_c_product_path_clipboard.py`（綁 v82 manifest，W-f3 的作法；衍生前後各跑一次舊值掃描）。讀法：`read_v80_f3_equal.py` 的衍生對 F3-81，**事先宣告的移動：無**（§6 的結論）；讀法一（`read_v25_f3.py`）預期與 F3-81 相同（`F3_RED`、同一組四個問題）。有任何移動就停下查清。
- **F4-82**：v80 四臂工具的衍生，兩瀏覽器 24/24。
- **E1-C**：`check_e1_c_bundle_intact.py` `intact: true`。
- **V0′-82**：照 v81 的作法，換回宣告的檔重讀 B1、F3-81 的讀取器，逐位元組相同。
- **預設**：任一條沒跑、NE、或有未宣告的移動，0.2.44 不送裝。

### 7.4 宿主 0.2.44

- 由 `findings/evidence/host-0.2.43/` 衍生（不改那些檔）：父＝`host-0.2.43` 的 `ae8240d`；前身 archive `host-0.2.43-engine-741afd80a36e673b`。套件裡有 `editor-shell-v2/`（所以 client 是一筆改動）；同一個套件的 ods 編輯器與檢視器頁面不 import `paragraph-editor-client.js`〔讀碼：import 它的只有 `e2-editor-app.js`、`narrow-editor-v2-client.js`、`narrow-editor-v2-session.js`、`paragraph-editor-session.js` 與不出貨的示範頁〕。
- 套件判準：對 0.2.43 恰好改 2 筆（頁面、client）、新增 4 筆（`profiles/e2-editor-v28/`）、移除 4 筆（`profiles/e2-editor-v27/`，工具先確認套件裡沒有別的頁面用 v27）。紅案：多一筆、少一筆、v28 的 wasm 等於 v27 的。
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
- **量測範圍外**（宣告，不是靜默略過）：右到左的最後一段（`Left(…, bVisual=true)` 是視覺方向，`txtcrsr.cxx:95-97`；未量，預期 NONE→083 那句，不在本規格宣稱）；游標在表格格子、frame、附註裡的空的最後一段；隱藏的追蹤刪除與合併段落；不同種類的巢狀清單；上一段結尾是 as-char 的 frame（後援只選分段、不含字，依量測 cl-a4 對 sa-a4，但這個形狀沒量）。

## 10. 原始碼釘選

兩棵樹（連結用的 `LOSRC`＝`../libreoffice-26-8`，由工具從 Makefile 讀出；原生證據用的 `native-lok-26-8/src`）裡下列檔案的 sha256 寫進 `findings/evidence/v28-083/pre-link/source-pin.json`；兩棵一致才算原生證據與連結的是同一份原始碼，不一致就記下差異、交裁決。v27 §10 的六個檔照舊釘，再加：

- `sw/sdi/swriter.sdi`（577：`CharLeftSel FN_CHAR_LEFT_SEL`）、`sw/sdi/_textsh.sdi`（1160）；
- `sw/source/uibase/shells/txtcrsr.cxx`（62-65：`FN_CHAR_LEFT_SEL` → `FN_CHAR_LEFT`＋選取；95-97：`rSh.Left(SwCursorSkipMode::Cells, bSelect, 1, false, true)`）；
- `sw/source/uibase/wrtsh/move.cxx`（55-61：`ShellMoveCursor` 呼叫 `MoveCursor(bSel)`；76-91：`MoveCursor` 在選取時先 `SttSelect()`；112-127：`SwWrtShell::Left`）；
- `sw/source/core/crsr/crsrsh.cxx`（326-380：`LeftRight`；第 2 種情況「在已編號段落開頭往左只設 in-front-of-label」要求 `!HasMark()`，選取時已有 mark，所以走第 3 種一般移動——這是後援在剛套上清單的段落上也會移動的原因，量測一致）；
- `desktop/source/lib/init.cxx`（6023-6024：純文字超過 10,000 字元回 `LOK_SELTYPE_COMPLEX`，`.uno:SelectAll` 不採用的紀錄理由）。

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

本規格釘死之前：因執行而修 **3**（native-q52：self-test 的 scope 索引、標題讀取器的段落位置、amendment 2 的 UNSAFE 子句方向）；因審核而修：待審核。fable 裁決：本輪 1 次（裁決 4）。

## 13. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-10-30 | 草案。 |
