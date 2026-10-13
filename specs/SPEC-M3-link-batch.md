# SPEC M3：連結批次——Shift＋方向鍵、範圍上的方向鍵、頁碼、C、136 的兩個引擎項目，與 127–136 的計數

> 2026-10-13 立（**草稿**，未經審核）。判準（第 5 節）寫在任何實作與執行之前；之後只追加，更正寫在後面並指名取代什麼。
> 證據標記照 `doc-conventions`：**已觀察**＝量過、**讀原始碼**＝沒量、**推論**。
> 起點：0.2.18（未計數候選；頁面 `b24d754a…`、殼層 v66、宿主 `96a87d8`、profile `e2-editor-v19`、writer-only 核心 `wasm-lite/build-headless-probe`）。名義上的出貨版本仍是 0.2.12。
> 來源：`handoff/PLAN-2026-10-12-link-batch-shift-selection-and-page-number.md`（含附錄）、SPEC-M3-held-key §14 的 C 與 §17 條件 8、SPEC-M3-production-ui §17.25–17.26、SPEC-M3-autosave §8.2／§9.21、交接 10-13d 附錄 2。

## 1. 為什麼要有

擁有者 2026-10-12 提出兩項需求（「新需求：沒關係你再安排開發時程」、「頁碼：照collabora做法」），10-13 手測 0.2.18 之後再催一次，並選 C＝並行：連結批次照排、ODS 的準備另一條線。這一批是**下一個會改引擎的版本**，所以照 SPEC-M3-autosave §9.21 帶著 127–136 的完整計數。

## 2. 範圍

| # | 項目 | 動到 | 來源 |
|---|---|---|---|
| 1 | Shift＋←→↑↓／Home／End 從游標或範圍延伸選取 | ABI、引擎、manifest、client、頁面 | 計畫 item 1 |
| 2 | 範圍上的方向鍵交給 Writer（129 的精確處方） | manifest、頁面（引擎同第 1 項） | 計畫 item 3、129 附錄 |
| 3 | 頁碼：狀態列「第 N 頁，共 M 頁」，N＝畫面所在的頁 | 引擎（新操作）、worker、SDK、頁面 | 計畫 item 2 |
| 4 | C：段首按住 Backspace 撞到文件開頭不再拒絕 | 引擎 | held-key §14 條件 8 |
| 5 | 136 的兩個引擎項目：拒絕不留選取、拒絕帶 barrier 之前的游標 | 引擎、頁面 | held-key §17 條件 8 |
| 6 | 127–136 加本批的完整計數 | — | autosave §9.21 |

**不在這一批**：ODS／Calc（換 writer+calc 核心是連結批次之後獨立的一步，autosave §8.2、計畫 Order 3）；block identity；字型與資料包（沿用 v19 的 `cjk-sub-e10`、`base-r5-no35`，**不換**）。一次連結一個變因：核心不換，只換我們的引擎原始碼。

**身分**：新 profile `e2-editor-v20`＝v19 的連結輸入＋本批引擎改動；ABI 4 → 5（extend 接受的動作變寬、多一個操作，版本是身分）；新殼層 generation；新宿主版本。連結是擁有者的步驟（第 6 節）。

## 3. 現況（讀原始碼，2026-10-13）

- **extend 已經存在一半**：ABI 的 `oxsdk_editor_action` 接受 `extend_selection`，但只給兩個字元移動（`src/editor_api.cpp:159`；`editor_api.h` 說四個行移動「刻意收窄」）；引擎把 Shift 加進按鍵碼（`probe_engine.cpp` ~5463），extend 的完成條件是第一個 `LOK_CALLBACK_TEXT_SELECTION`（~5470）；client 的 `MOVE_ACTIONS` 只有兩個字元移動（`narrow-editor-v2-client.js:80–95`）；頁面看到 `shiftKey` 就不送（`web/e2-editor-app.js:2596`，finding 129 的註解）。
- **gesture 閘門按動作判、不分 extend**（`probe_engine.cpp` ~5262–5300）：v19 的六個移動只有 `collapsed`。所以只要範圍上要能延伸，就**必須**給六個移動 `range-single`＋`range-cross`；而同一個授權也讓不帶 Shift 的移動在範圍上進到 Writer。**第 1 項與第 2 項在引擎端是同一件事**，分開的只有頁面送不送。
- **完成時序列化的是引擎的快取**（`completePendingEditorOperation` ~2155）：在第一個符合的回呼就完成。若之後還有改變快取的回呼（例如游標晚於選取到），回報的狀態就是舊的——084 的形狀。這一點要原生先量（工單 10-13h），第 4.1 節的 barrier 依量測寫。
- **頁碼**：LOK 有 `getPartPageRectangles`（twips 字串）；原生量過（已觀察，`findings/evidence/link-batch/page-rectangles/`）：60 頁 60 個矩形、每次 < 0.03 ms、加一頁會多一個矩形並在 1.3–1.8 ms 後有 `DOCUMENT_SIZE_CHANGED`、沒加頁的編輯字串不變也沒有回呼。引擎今天沒有任何頁面幾何；paint 回覆已經帶 `documentSizeChanged`（`probe_engine.cpp:3129–3149`，finding 062）。
- **C 的風險（讀原始碼）**：`nothing-selected` 是「250 ms 內讀回 NONE」，原始碼自己的註解寫著「250 ms 的 NONE 也可能是一個還沒執行的 Shift」（~3860）。把它改成「成功、沒改東西」之後，若那個 Shift 晚到，會在文件開頭留下一個選取——這正是第 5 項 (1) 要擋的。

## 4. 設計

### 4.1 Shift＋方向鍵（第 1 項）

- **ABI 5**：`extend_selection` 接受六個移動（兩個字元、四個行）。其他動作照舊必須是 0。
- **manifest**：六個移動的 `gestures` 改成 `["collapsed","range-single","range-cross"]`；四個行移動的 `limits` 拿掉 `no-extend-selection`。
- **client**：`extendSelection` 接受六個移動。
- **頁面**：`keydown` 的六個鍵帶 `shiftKey` 時送 `extendSelection: true`；不帶就照第 4.2 節。工具列與 `lastSelectionShape` 讀引擎回報的狀態，不自己推。
- **引擎的完成條件（待定，依工單 10-13h）**：候選是 (a) 第一個 `TEXT_SELECTION`（今天）、(b) `TEXT_SELECTION` 與 `INVALIDATE_VISIBLE_CURSOR` 都到、(c) 最後一個回呼之後一段安靜窗、(d) 完成時主動讀回（`getTextSelection` 與游標）而不是用快取。**選哪一個由量測決定，不是由偏好決定**：若原生每一格游標都先於最後一個選取到、且只有一個選取回呼，(a) 就夠；否則不夠。沒有回呼的格走既有的 `verified-move-readback`（096）。這一小節在 10-13h 的 README 進來之後追加，並在第 5 節補上對應判準的門檻；**在那之前不寫引擎碼**。

### 4.2 範圍上的方向鍵（第 2 項）

引擎授權同第 4.1 節。頁面：範圍上不帶 Shift 的六個鍵**直接送移動**，由 Writer 決定游標落點；0.2.13 的「先在點的位置按一下再移動」拿掉。這是 129 的精確處方（129 README「native point-click」節：頁面處方在 42 格裡與 Writer 相同，但下鍵在選取的點**顯示在**折行行尾時不同——那是 L-129）。

### 4.3 頁碼（第 3 項）

- **引擎**：新操作 `page-rectangles`，回覆 `getPartPageRectangles()` 的原字串（不在引擎裡解析）與 `documentWidthTwips`／`documentHeightTwips`。
- **SDK**：`handle.pageRectangles()` 解析成 `[{x,y,width,height}]`（twips）；格式不符就丟例外，不回空陣列。
- **Collabora 實際怎麼做（讀原始碼，2026-10-13 更正計畫 item 2 的說法）**：編輯模式下狀態列顯示的是**核心**推來的 `.uno:StatePageNumber` 原字串（`cool-26-04/browser/src/control/Control.StatusBar.js:681`）；核心依 Collabora 回報的可見區域算（Writer 26.8 `sw/source/uibase/uiview/view2.cxx:1797` → `SwViewShell::GetFirstLastVisPageNumbers`，`sw/source/core/view/viewsh.cxx:2964`）：第一個「扣掉下邊界之後與可見區重疊」的頁到最後一個「扣掉上邊界之後重疊」的頁；只有一頁就是「Page N of M」，兩頁以上是「Pages N - L of M」。唯讀模式才在客戶端用頁面矩形算（`Parts.js:306–322`，取第一個可見的頁）。計畫附錄說「Collabora 的 N 是畫面的頁」方向對，但它是核心算的、而且是範圍。我們的引擎沒有把可見區告訴核心（推論：所以原生量到的 N 跟著游標）。
- **頁面**：開檔後讀一次；之後**只在** paint 回覆帶 `documentSizeChanged: true` 時重讀。照 Writer 那條規則在頁面端算：N＝第一個與可見區重疊的頁、L＝最後一個；N＝L 顯示「第 N 頁，共 M 頁」，否則「第 N–L 頁，共 M 頁」。矩形不含頁邊界，所以用整頁矩形判重疊（與 Writer 的差別：只露出上一頁下邊界的那幾行時，我們會多算一頁；登錄為 L-page-margin）。M＝矩形數。捲動只重算、**不呼叫引擎**。位置見第 8 節 Q-A。**絕不由「頁高相同」推頁碼**（橫向頁、分節會破）。
- **頁碼只有實體頁號**：自訂起始頁號、羅馬數字頁碼（Writer 會顯示「Page 3 of 18 (Page ii)」）我們不知道，登錄為 L-page-virtual。

### 4.4 C（第 4 項）

merge-key barrier 停在 `nothing-selected` 且 `keyPosted === false` 時，動作以「成功、沒有改動」完成（`editor-action-completed`，`changed: false`，新的 completion 名稱 `verified-boundary-noop`），**不回** `EDITOR_BOUNDARY_UNSUPPORTED`、頁面不重開。完成之前引擎讀回選取：若不是 NONE（晚到的 Shift），先收回成 barrier 之前的游標再完成；收不回就照今天拒絕（重開），並在拒絕裡標明 `late-selection`。

### 4.5 136 的兩個引擎項目（第 5 項）

1. **拒絕不留選取**：每一個拒絕出口（`finishMergeKeyError`、`finishSelectionBarrierError`）在送出之前讀回選取，不是 NONE 就收回成 barrier 之前的游標；收不回要在拒絕裡寫 `selectionLeft: true`，不得默默留著。
2. **拒絕帶 barrier 之前的游標**：拒絕的 JSON 加 `caretBefore`（barrier 開始那一刻引擎快取的游標矩形與 `sourceSequence`）。頁面的自動重開改讀它；附錄 4 的規則 (iii)（引擎最後一次回報、沒有選取的游標）變成退路。L-136-rule-iii-residual 因此應該消失——判準 E3 量它。

## 5. 判準（寫在任何實作與執行之前）

形式照 `AGENTS.md` §1：每條是逐實例性質或工具封閉的枚舉；每條附「若永遠沒做」的預設結論。兩個瀏覽器（Chrome、Firefox 157；Firefox 版本照 10-02 擁有者裁示 B 具名，不設判準）。

- **S1（延伸＝Writer，逐格）**：10-13h 的原生回合裡每一個「Shift＋鍵」格（清單取自原生輸出的 arms，工具封閉），在 v20 上由產品頁面送出之後，引擎讀回的選取文字與原生的 `getTextSelection` 逐字相同；不同的格要列名，不得以比率帶過。**若沒做**：第 1 項不算出貨，頁面不送 `extendSelection`。
- **S2（完成時回報的就是穩定後的狀態，逐格）**：同一組格，完成回覆裡的游標與選取矩形，等於完成後 500 ms 由引擎主動讀回的游標與選取（不是頁面快照，`CLAUDE.md`「去問狀態，問到引擎那一側」）。這一條在第 4.1 節定案之前先釘死，不隨選中的完成條件放寬。**若沒做**：第 4.1 節的完成條件視為未驗證，同上。
- **S3（沒有回呼的格不殺 session）**：原生沒有回呼的格（10-13h 的空格清單），在 v20 上以 `verified-move-readback` 完成、`changed: false`、session 不進 `recoverable-error`。**若沒做**：同上。
- **S4（延伸之後產品的下一個選取照常，039）**：10-13h 的互動臂 (a)–(c) 在 v20 上全過。**若沒做**：同上。
- **R1（範圍上的方向鍵＝Writer，逐格）**：129 的 42 格加 L-129 的折行格，在 v20 上游標落點與原生相同。**若沒做**：第 2 項不出貨，頁面保留 0.2.13 的處方、L-129 維持。
- **P1（頁碼，逐位置）**：60 頁文件（`tools/create_long_document.py --pages 60`）與一份**混合頁面大小與方向**的新 fixture，捲到每一頁中心（位置由引擎回的矩形產生，工具封閉），狀態列顯示「第 k 頁，共 M 頁」，k 是那一頁的序號、M 是矩形數；再捲到每一對相鄰頁的交界（同樣由矩形產生），顯示「第 k–k+1 頁，共 M 頁」。另記原生的頁數，不比對（字型可能不同）。**若沒做**：第 3 項不出貨。
- **P2（加頁）**：插入分頁之後，下一次 paint 之內 M 加 1。**若沒做**：同上。
- **P3（捲動不叫引擎）**：捲過整份 60 頁文件，引擎收到的 `page-rectangles` 請求數＝0。**若沒做**：記為未驗證，不擋出貨。
- **C1（C）**：held-key 探針的 `start-press` 拒絕 0 次、世代 `['1']`；紅案是 run-1 的 `start-press`（今天拒絕 1 次）。另加一臂「忙碌中的段首 Backspace」：若在 12 次裡出現 `late-selection`，照實記，不判失敗。**若沒做**：C 不出貨，L-132 的 (i) 照舊由 B1 的具名限制代表。
- **E1（拒絕不留選取，工具封閉）**：merge 的 stage 表（`merge_key_undo.hpp` 的 `findStage` 那張表）每一個 stage，要嘛有一個在 v20 上量到的實例、拒絕之後引擎讀回選取為 NONE，要嘛登錄為「沒有可達的實例」並寫為什麼。**若沒做**：第 5 項 (1) 不算成立。
- **E2（拒絕帶游標）**：E1 的每個實例，拒絕裡的 `caretBefore` 等於送出那一下之前引擎回報的游標。**若沒做**：頁面不改讀它，規則 (iii) 照舊。
- **E3（L-136-rule-iii-residual）**：在 Escape #1 與 #2 之間誘發一個階段錯誤（若誘發不了，登錄為「沒有可達的實例」），重開之後游標與送出前相同。**若沒做**：L-136-rule-iii-residual 維持。
- **K（計數）**：第 7 節的計數鏈在最終位元組上全過。**若沒做**：本批與 127–136 都是未計數候選，名義上的出貨版本停在 0.2.12。

## 6. 連結（擁有者的步驟）

照 RUNBOOK-relink-v19 的形狀寫 `handoff/RUNBOOK-relink-v20.md`：先封存（`build/archive/`），`ALLOW_FROZEN_RELINK=1` 只連 v20 一個目標；連結後必做：wasm 雜湊、匯出表含新操作、`ScDocShell` 0 次（仍是 writer-only）、v8／v19 不動。Makefile 改動會重連依賴它的產物（finding 042），所以 Makefile 的改動先給擁有者看。**引擎碼要先過一次對抗性審核才寫 runbook。**

## 7. 計數

連結、頁面改完、凍新殼層 generation、宿主新版本、六支 M3 runner＋production UI＋autosave＋產品路徑網的 pin 改綁之後，計數鏈排夜間、脫離 session（`runs-0.2.13/chain-2026-10-12.sh` 的形狀）。帶的帳：127、128 處方 B、129、130、131 規則 A、133、134、136（與 132 的頁面修法），加本批。紅了先對這張清單歸因。

- **135 的 C2 格**：計數前要定重跑語意（finding 135 的後續）。**若沒定**：照預設，單次規則、旁邊附比率。
- **工單要寫明**：「只有開跑時 load ≥ X 才放棄」或「開跑之後絕不中止」（交接 10-13d 的偏離）。

## 8. 開放問題

- **Q-A（擁有者）**：頁碼放哪裡。我的傾向：照 Collabora，畫面底部一條狀態列，左側「第 N 頁，共 M 頁」；正式介面（宿主）也顯示。替代：放在標題列的 `#state-pill` 旁邊。
- **Q-D（擁有者）**：頁碼要不要做成核心算的（引擎把可見區告訴核心、轉送 `.uno:StatePageNumber`，與 Collabora 編輯模式完全相同，含自訂頁號）。我的傾向：不要——捲動時每次都要呼叫引擎，而且核心的字串語系跟著 build；頁面端照同一條規則算，只差 L-page-margin 與 L-page-virtual。
- **Q-B（量測決定）**：第 4.1 節的完成條件，等 10-13h。
- **Q-C**：第 2 項是否這一批就讓頁面直接送（我傾向是：引擎授權本來就要給，頁面多一條分支反而是兩套行為）。若擁有者要保守，頁面可以先維持 0.2.13 的處方，R1 改成只量不擋。

## 9. 4.1 的完成條件定案（2026-10-13，只追加；取代 4.1 最後一點的「待定」）

**原生量測**（已觀察，工單 10-13h，`findings/evidence/link-batch/extend-signatures/run-20261013T095104Z/`，commit `81eaf66d`；主 session 用自己的讀取器從三輪原始 jsonl 重算，數字相同）：

- 111 格（14 種起始形狀 × 6 個 Shift 鍵＝84，加 4 種範圍 × 6 個不帶 Shift 的鍵＝24，加 3 個無按鍵對照），三輪各自獨立的程序，**沒有一格的回呼序列在三輪之間不同**。
- 有回呼的 98 格（74 格 Shift、24 格範圍上的方向鍵）：**每一格都恰好一個 `TEXT_SELECTION`、恰好一個 `INVALIDATE_VISIBLE_CURSOR`，而且游標回呼永遠在最後**（`SS SE SEL CUR` 71 格、`SEL CUR` 2 格、`SEL0 CUR` 25 格；SEL0＝空酬載）。
- 完全沒有回呼的 10 格，都是選取沒變的：文件開頭的 Shift＋左／上／Home、結尾的 Shift＋右／下／End、空段落的 Shift＋Home／End、折行行尾的 Shift＋End、儲存格尾端的 Shift＋End。
- 時間：選取與游標回呼都在按鍵送出後 1.10 ms 之內；300 ms 之後只有 `STATE_CHANGED` 之類，沒有選取或游標回呼。
- 互動臂（039）27／27 過：Shift 之後產品的點擊、拖曳、文字把手選取都正常。
- 預測 P-a～P-d 全部成立。

**引擎今天的行為**（讀原始碼，`probe_engine.cpp:2655`）：每個回呼先更新快取、**立刻**判斷完成。所以 (a)「第一個 `TEXT_SELECTION` 就完成」在 74 格 Shift 裡都會把**按鍵之前的游標**放進完成回覆；範圍上的方向鍵今天走 `EditorCaretOrSelectionCallback`，先到的是 SEL0，24 格也一樣。之後的游標回呼會再推一次 editor-state，頁面的序號守衛（084）會收斂，但完成回覆本身是舊的，S2 要的就是它不舊。

**定案**：

- extend（不論起點）以及**起點是範圍**的移動（派送當下 `selectionRectangles` 非空），完成條件改成 `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`。
- 起點是游標、不帶 Shift 的移動**不變**（已量過的路，一次一個變因）。
- 沒有回呼的格照舊走 096 的 250 ms 讀回（`verified-move-readback`）。若 WASM 上出現「有選取回呼、沒有游標回呼」的格，它也會在 250 ms 讀回完成，狀態仍是對的、只是慢；S3 的判讀照實記錄這種格。

**S2 在連結之前就能先紅一次**：v19 的 ABI 已經接受兩個字元移動的 extend，完成條件是 (a)；manifest 只給 `collapsed`，所以只有起點是游標的格可達。**預測**：原生清單裡「起點是游標、Shift＋左／右、選取有變」的 18 格（caret-mid ×2、doc-start 的右、doc-end 的左、empty-para ×2、wrap-line-end ×2、cjk-mid ×2、heading-mid ×2、list-mid ×2、cell-end ×2），在 v19 上 S2 **全紅**（完成回覆的游標＝按鍵前的游標）。S2 的判讀工具第一次使用之前，要先在 v19 上跑這 18 格。若有任何一格是綠的，先查 WASM 的回呼順序是不是跟原生不同、還是儀器沒量到，**不往下做**。

## 10. 審核 1 的處置（fable 代擁有者裁決 2，2026-10-13，只追加；取代 §9 的「定案」與下列各節裡被點名的句子）

擁有者原話：「有疑義的發給fable，我授權它代我下決定」。審核：`findings/evidence/link-batch/review/review-1-spec.md`（`cf0e15d2`，3 BLOCKING／12 SHOULD／11 NOTE）。工單 `brief-2-disposition.md`，裁決 `ruling-2.md`（`918c2497`）——條件 1–15 以那份為準，這裡寫成規格。主 session 重新核對過裁決依賴的兩個新事實：

- **F1（讀原始碼）**：LOK 對 `TEXT_SELECTION` 與 `INVALIDATE_VISIBLE_CURSOR` 的去重，比對的是上一次**送出**的酬載（`desktop/source/lib/init.cxx:1592–1594`、`2530–2537`）。所以一個從空到空的操作，不會送出任何 `TEXT_SELECTION`。
- **F2（已觀察＋讀原始碼）**：打字不會送 `INVALIDATE_TILES`。原生的頁面矩形 Edit B 是 0/6，WASM 的 r2-blit-bytes 是 140 下 0 次。而 `documentChangeSequence` 只在 `INVALIDATE_TILES` 時前進（`probe_engine.cpp:2632`）。

### 10.1 延伸與「起點是範圍」的移動，完成條件（B1；**取代 §9 的定案**）

§9 那條「等游標回呼」撤回：它就是 SPEC-M3-paragraph-merge §3.2 已經否決過的規則（審核 B1，主 session 核對過 §3.2、§16.1）。

- **規則 (a)，轉移規則**：適用於任何起點的 extend，以及派送當下引擎快取的 `selectionRectangles` 非空的一般移動。完成要依序看到兩件事：
  1. 一個 `TEXT_SELECTION`，它解析出的矩形清單與派送當下的快取不同（空對非空也算不同）；
  2. 之後的下一個 `INVALIDATE_VISIBLE_CURSOR`。

  序列化的是那個游標之後的快取。
- 250 ms 讀回（`verified-move-readback`）照舊當退路。起點是游標的一般移動**不變**。
- **規則寫成標頭檔裡的純函式**，與 `merge_key_undo.hpp` 同一種寫法。判準就是它的模型測試，形式一，由工具產生。做法是把 `tests/merge_key_undo_model_test.cpp` 的 LOK 模型，加上兩種情況：
  - 一個同步完成、但 flush 還在佇列的插入；
  - 一個以讀回完成、flush 晚到的操作。

  紅案：§9 的規則（第一個游標）與 v19 的規則（第一個 `TEXT_SELECTION`），都必須在「插入之後 Shift＋鍵」與「蓋掉範圍打字之後 Shift＋鍵」上失敗。測試要印出規則 (a) 給出舊狀態的那些序列，那就是下面這個殘留的母數；其餘序列，規則必須完全正確。**這個測試 commit 並做過紅案之前，引擎不接線。**
- **具名殘留 L-extend-prior-flush**：
  - 母數（依 F1）：一是對**非空選取**做的 `insert-text`，它同步回報完成，而 paste 會收合選取，所以它的 flush 帶 SEL0；二是以讀回完成、自己的 `TEXT_SELECTION` 卻晚於 250 ms 才到的操作。
  - **不在母數裡**：合併鍵（它的 flush 是空對空，依 F1 不會送 `TEXT_SELECTION`），以及從游標出發的一般移動（沒有 `TEXT_SELECTION`）。
  - 效果：一次完成回覆是舊的，下一個 editor-state 推播會帶較高的 `sourceSequence` 收斂（`narrow-editor-v2-session.js:188–200`）。文件不會被改錯。使用者看得到的，最多是接著的刪除被拒、什麼都沒刪；這個由 S5 逐格數。
- **產品路徑網加三支計次臂**，加在既有的 `run_e2_c_product_path.py`，不另寫 runner：
  1. 插入後不等待，馬上 Shift＋鍵；
  2. 會併段的 Backspace 之後 Shift＋鍵；
  3. Shift＋右按住 1 秒。

  N 在跑之前寫好，過＝N 次全過，並列出舊完成的次數。兩個瀏覽器都要跑，在 v20 上。

### 10.2 S2 與 v19 先紅（S-3、S-4、S-5）

- **S2 的母數**：原生 `arms-r*.jsonl` 的 Table 1 ∪ Table 2，共 84＋24 格。
- **S2 的參照**：完成後至少 500 ms，用 `editor-get-state` 讀到的引擎快取，再加一個主動交叉檢查：完成回覆的 `selection.collapsed` 與 +500 ms 時 `getTextSelection` 讀到的型別一致。§9 那句「狀態仍是對的、只是慢」刪除。S2 的判讀工具要記錄兩件事：同一個請求是否有多個完成，以及讀回之後是否又到了游標。
- **v19 先紅**：是 **16 格**，不是 §9 寫的 18 格。從游標出發的 Shift＋左右共 18 格，要扣掉 `shift-Left@doc-start` 與 `shift-Right@doc-end`，這兩格沒有回呼。這 16 格經 SDK client 送出，因為 v19 的頁面會丟掉 Shift。任何一格是綠的就停手。

### 10.3 S1 的逐格判法（S-6）

WASM 上每一格的判法：錨點不變，而移動的那一端，等於「從該形狀的點按不帶 Shift 的同一鍵」到達的游標（另起一臂量）。只有左右，以及單行段落上的 Home／End，才比對原生的逐字文字（其餘受字型影響）。形狀用同一套按鍵走訪重新找出，並和原生一樣檢查按鍵前的文字。

### 10.4 刪除的形式在執行時才決定（B2）＋ S5

- 頁面送出刪除時不再決定 `delete-backward` 或 `delete-selection`。改由 session 的方法帶一個 resolver，在**佇列項目執行時**用 session 自己的快照決定。佇列一次跑一件，到那時前面的移動與延伸都已完成（`editor-shell/editor-session.js:287–311`）。
- 不用「頁面先等移動的 promise 再排隊」：那樣打字可能插到刪除前面，是 finding 111 的形狀。
- 131 的規則 A 照舊。131 的各臂在 v20 上必須維持綠，證人是既有的 131-B 跑一次。
- **S5（形式二，母數取自 S1 的格）**：Table 1 的 84 格 Shift 格，每格之後不等待，分別接 Backspace、Delete、一個打字字元。Writer 的參照由原生工具跑同樣的序列。判法：兩個刪除臂比 `content.xml` 逐位元組；打字臂用 SPEC-M3-paragraph-merge §12 的段落文字序列比較器（rsid 讓打字的位元組跨 session 不同）。**若沒做**：頁面不送 `extendSelection`。

### 10.5 C 的時間窗（B3；**取代 §4.4 的「收回」與 C1 的忙碌臂**）

- 第一次 250 ms 讀到 NONE（`rejectSelectionBarrierAtDeadline`）之後，交易留在 `AwaitingUnitSelection`，再等一個 `MergeStepDeadlineMs`（2000 ms，沿用既有常數，不新增數字）。
- **窗內到了 K1 的 `TEXT_SELECTION`**：照今天的路走（`handleSelectionBarrierStateCallback` → 單位驗證 → 併段／刪除／那條路自己的拒絕），不拒絕。歸屬的 P 與錨點柵欄在 K1 之前就已設好。
- **窗到期**：
  - 第二次 `readSelection()` 仍是 NONE，而且快取的選取仍是收合的：以 `verified-boundary-noop` 完成（`changed: false`、revision 不變、`boundaryNoop: { waitedMs }`），不回 `EDITOR_BOUNDARY_UNSUPPORTED`、不重開。
  - 另外兩個出口照舊：`unit-late` 與 `EDITOR_STATE_UNAVAILABLE`。
- **「收回成 barrier 之前的游標」刪除**：它沒有對應的機制。`setTextSelection RESET` 是同步的，會在佇列中的 K1 之前執行。
- **C1 改成逐次完成的判準（形式一）**：每一個 `verified-boundary-noop` 完成後至少 500 ms，`editor-get-state` 讀到的 `selectionType` 必須是 `none`。每次記下 `waitedMs`。原本的忙碌臂撤回：依構造它不論 C 壞沒壞都會讀到 0。
- **殼層 client** 的完成白名單接受 `verified-boundary-noop`（`changed === false`、revision 不變），並附紅案。頁面遇到它不跳提示、不重開。132 的節流與 134 的 B 照舊。
- **具名殘留 L-C-late-K1**：K1 晚於約 2,250 ms 才到，會在活著的 session 裡留下一個選取；文件到下一鍵之前不變，下一個打字字元會取代那個單位。這個殘留關不掉：在真正的文件兩端，K1 不產生任何回呼（原生 P-b），沒有訊號可等，只能靠時間窗。
- **具名代價**：在文件開頭按 Backspace，約 2.25 秒才回應。`waitedMs` 留作日後追加一節、以量測縮短的依據。窗長對 135 夠用：量到的停頓是 196.6–210 ms。

### 10.6 撤回 §4.5 (1) 與 E1（S-7）

每一種會留下選取的拒絕，都會重開或鎖住佇列（`e2-editor-app.js:1653–1655`；`RECOVERY_ERRORS`，`editor-shell/editor-session.js:319–321`），留下的選取使用者碰不到。而 `kStages` 不涵蓋 `finishSelectionBarrierError` 的出口，所以 E1 原本是手工清單。照 `AGENTS.md` §4，撤回宣稱，不造機械去維持它。唯一還活著的路是 C 的 no-op，由 10.5 的 C1 涵蓋。

**§4.5 (2) 留著，當資料**：
- `caretBefore`：歸屬的 P 已建立時取 P，否則取快取，並帶 `source` 欄位。
- E2 的參照：同一筆交易 K1 的錨點矩形。
- E2 加一臂：「按住跨過一次併段」。
- E3 留著。

### 10.7 計數前要先改的既有臂（S-9）

在任何計數之前，§7 要先列出：每一支期望寫著 `nothing-selected`、拒絕次數或世代清單的臂，以及它在 C 之下的新期望。清單由 grep 探針的期望得出，不是憑記憶。候選有 `start-press`、`start-hold`、`end-hold`、`end-press-type`、`restore-window`、`cell-start-hold`。新期望：拒絕 0 次、世代 `['1']`、文件與游標不變、打的標記落在游標所在處。

v20 第一次 shakedown 這些臂，就是改它們判讀工具的 §34.4 證人，算在「因執行而修」；「因審核而修」維持 0。

### 10.8 頁碼的機制（S-10、S-11；**取代 §4.3 的觸發條件與 P1–P3 的寫法**）

- **`page-rectangles`** 是文件層級的匯出，由 manifest 欄位與 `offers` 把關（比照 redo 的前例），**永遠不是動作**。`kMaxExternalAction` 與 `kMaxInternalEditorAction` 不動，editor ABI 是 5。回覆帶三樣東西：原字串、文件大小、`getParts()`。
- **重讀的觸發**：
  - 引擎把 `LOK_CALLBACK_DOCUMENT_SIZE_CHANGED` 當成計數器，放進 editor state；
  - 加上 paint 回覆的 `documentSizeChanged`（今天已有）。

  **不用 `documentChangeSequence`**（F2：打字不會送 `INVALIDATE_TILES`）。
- **重算**：捲動、視窗大小改變、縮放、worker 重開時，頁面重算 N 與 L，都不呼叫引擎。
- **P1**：60 頁 fixture 上，矩形數＝`getParts()`＝60，由構造決定。頁面中心的參照，由 runner 用矩形與實際使用的視窗大小算出。
- **P2**：編輯後不再有任何輸入，2 秒時 M 必須正確；另加一個刪掉一頁的案例。
- **P3**：計算時排除由大小改變觸發的重讀。
- **更正 §4.3 對 Collabora 唯讀模式的說法**：`Parts.js:307–322` 只服務上一頁／下一頁；Collabora 沒有任何地方是「捲動時在客戶端算頁碼」（審核 N-1）。編輯模式的字串由核心給，這一點 §4.3 寫對了。

### 10.9 其餘 SHOULD

- **S-1**：§2 的範圍要加上以下幾項，並為放寬 extend 加一個證據欄位：
  - worker：要重新建置；v19 的 worker 是 v15 封存的拷貝，而它的 `EDITOR_V1_MOVE_ACTIONS` 也拒絕行移動的 extend；
  - profile 建置器：`build_e2_editor_v4_profile.py` 的 `ABI_VERSION` 與 `no-extend-selection`；
  - 每一個 pin：`tests/test_e2_editor_v4_profile.py`、`src/editor_api.cpp:78–81`、`narrow-editor-v2-client.d.ts:71–74`、`tests/editor_abi_header_test.cpp`。
- **S-2**：頁面的 129 分支由 manifest 決定。129-B 在 v20 上退休，由 R1 取代。工具列的 ◀ ▶ 在範圍上變成可按，這是刻意的，寫進發佈說明。
- **S-12**：按住 Shift＋方向鍵套用 132 的深度規則；為此要計算飛行中的移動與延伸，這是計數唯一的用途。判準在實作之前寫：按住 Shift＋右 2 秒，放開之後選取最多再長出「放開時還在飛行中的延伸數」。**若沒做**：按住 Shift＋方向鍵登錄為具名限制。
- **NOTE**：全部登錄（審核 N-1～N-11；N-2：換 a11y 核心時 S2 要重跑；N-3：同一請求有多個完成，記為 finding 而不是判準）。

### 10.10 擁有者的三題

- **Q-A**：放在畫面底部的狀態列，左側寫「第 N 頁，共 M 頁」或「第 N–L 頁，共 M 頁」。由頁面畫，所以宿主也看得到。在宿主樣式下是否完好（finding 110 的形狀）是擁有者手測項目，不是計數判準。
- **Q-C**：是，第 2 項這一批出貨。R1 量的是 Writer 自己的移動；若 R1 的折行格過，L-129 依構造關閉。
- **Q-D**：不改由核心計算。

### 10.11 第二輪審核（條件 14）

寫碼之前，這一節要再交 opus 做**一輪**有界的審核，只審本節，問題先固定：

1. 找一條「flush 之前就完成」的路徑，它晚到的 flush 帶著不同的 `TEXT_SELECTION`，卻不在 L-extend-prior-flush 的母數裡；
2. 找一條路徑，讓 K1 在 10.5 的時間窗內晚到，走進一般的單位路徑，而它的 P 柵欄攔不住；
3. 找一種頁數變化，既不送 `DOCUMENT_SIZE_CHANGED`，也不讓 paint 回覆帶 `documentSizeChanged`；
4. S5 的母數或判法，能不能讓一個壞掉的產品過關；
5. S-1 的 pin 清單是否完整。

處置只追加一次，沒有第三輪。§6 的引擎碼審核是另一件事，照舊要做。

**預設結論（條件 15）**：
- 10.1 的規則與模型測試若沒做，第 1 項不出貨，頁面永遠不送 `extendSelection`。
- 10.5 若沒做，C 不出貨，134 的 (i) 照舊由 B1 的具名限制代表。
- 10.8 若沒做，第 3 項不出貨。
- 10.11 若沒做，這一批不寫任何引擎碼。

**白話理由**：裁決原文見 `ruling-2.md` 的「WHY (for the owner)」，九句。

## 11. 登錄的問題：pthread 預設堆疊（finding 089，2026-10-13，只追加）

finding 089 的堆疊臂判定 O-S（`4aa84ec2`）。在 writer+calc 的 v12 上，64 KB 的 pthread 預設堆疊就是 ODS 懸崖與崩潰的開關；調到 256 KB 以上，卡住的檔案都打得開。十條連結規則都是 `-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536`（`wasm_sdk_probe/Makefile:483` 等）。我們的引擎在 `std::thread` 上跑 LOK（`probe_engine.cpp:6518`），所以 Writer 的執行緒也有同樣的暴露。

**問題（擁有者，或依授權交 fable）**：這一批連結要不要調大 `-sDEFAULT_PTHREAD_STACK_SIZE`，或為引擎執行緒設明確的大小？
- **若沒決定，預設：不變**；089 的修法跟著 W8（writer+calc 的連結）。
- 記憶體帳（推論）：開檔時大約 7 條 pthread；每條 256 KB 只多約 1.3 MiB，每條 8 MB 多約 55 MiB，都在 1 GB 固定記憶體之內。總執行緒數沒量。
- 一次一個變因：若這一批要調，它就是本批的第二個引擎層變因。發佈說明要寫明，回歸網紅了也要先對它歸因。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-13 | 草稿：範圍、現況、設計（4.1 的完成條件待 10-13h）、判準 S1–S4／R1／P1–P3／C1／E1–E3／K、連結與計數的形狀、開放問題 Q-A–Q-D。4.3 在 commit 前讀過 Collabora 與 Writer 原始碼後改寫：頁碼是可見頁範圍、編輯模式由核心算（計畫附錄的說法不完整） |
| 2026-10-13 | §9：4.1 的完成條件依 10-13h 定案（extend 與範圍起點的移動等游標回呼），並寫下 S2 在 v19 上先紅的 18 格預測 |
| 2026-10-13 | §10：審核 1 的處置（fable 代擁有者裁決 2）。§9 的完成規則撤回，改成轉移規則＋模型測試；B2 改成執行時決定刪除形式＋S5；C 改成時間窗；§4.5(1)／E1 撤回；頁碼改由 DOCUMENT_SIZE_CHANGED 計數器觸發；Q-A 底部、Q-C 出貨、Q-D 不改；寫碼前再一輪有界審核 |
| 2026-10-13 | §11：登錄 pthread 預設堆疊的問題（finding 089 O-S；預設不變、跟著 W8） |
