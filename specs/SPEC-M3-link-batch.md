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

## 12. 第二輪審核的處置（fable 代擁有者裁決 3，2026-10-13，只追加；**不再有第三輪**）

審核：`review-3-focused.md`（`6370916e`）。結論是 Q1、Q2、Q4、Q5 各有反例，Q3 是 SHOULD。裁決：`ruling-3.md`（`1b38f6c0`），條件 16–28 以那份為準，這裡寫成規格。白話理由見該檔的「WHY (for the owner)」。

### 12.1 L-extend-prior-flush 的母數由模型測試定義（Q1；更正 §10.1）

- 母數＝模型測試印出的序列。LOK 模型要加兩種事件形狀：
  - 「命令結果排在 flush 前面」：`startEditorUnoAction` 系列的完成，在 `UNO_COMMAND_RESULT` 就序列化，早於自己的 SEL／CUR；
  - 「三次 `setTextSelection` 的範圍選取」。

  §10.1 列的兩項改成「例子」，不再是母數。
- **§10.1 的「文件不會被改錯」刪除。** 一次偽造的完成之後，有可能接著一次疊上去的刪除（見 12.2）。

### 12.2 帶旗標的刪除（Q2；資料會被改錯，已在原始碼確認）

**洞**：非併段的單位刪除（Barrier 類）走 `geometrySafe`／`textSafe`（`probe_engine.cpp` ~3809–3840），沒有歸屬柵欄，核心選到什麼就刪什麼。路徑是：
1. 一個延伸靠 250 ms 讀回完成，但它的鍵還沒執行；
2. 緊接著按 Backspace，刪除形式在執行時決定，看到的快照是收合的；
3. barrier 自己送的 Shift＋左疊在那個延伸鍵上，刪掉兩個字，而 Writer 只刪一個。

反方向則是在段落中間靜默地回 `verified-boundary-noop`。**沒有延伸時，今天到不了**：一般的左鍵加 K1 疊起來，結果等於 Writer 的「左、Backspace」；併段那條路會因為 `anchor-mismatch` 而安全。

**處方 (i′)，帶旗標的刪除**：
- **設旗標**：延伸靠讀回完成時，引擎設 `extendUnconfirmed`。
- **清旗標**，只有這幾種情況：
  - 一次規則 (a) 的完成；
  - 一次帶旗標的刪除帶著證明完成；
  - 關檔、換新 worker。

  從游標出發的一般移動不清（它在第一個游標就完成，那個游標可以是偽造的）。
- **旗標在的時候**：
  - `delete-selection` 在派送之前就拒絕（`.uno:Delete` 是同步的，會插到已送出的鍵前面）；
  - Barrier 類的 K1 只接受**恰好一個碼位**；
  - 併段（MergeKey）照舊用柵欄加 K2；
  - 時間窗到期**不判** `verified-boundary-noop`，改為拒絕。
- **拒絕的形狀**：階段名 `prior-key-unconfirmed`，`keyPosted:false`，和其他邊界拒絕一樣重開。頁面的「沒改動」階段集合，以及 M1-5 那類測試，都要納入這個階段。
- 日常的「行尾按 Shift＋End，再按 Backspace」不受影響。
- **判準就是模型測試**，接線之前 commit 並先紅：
  - 疊上去的延伸序列必須拒絕；活性序列必須真的刪；
  - 紅案一：拿掉旗標 → 印出刪兩個單位與靜默 no-op 的序列；
  - 紅案二：不帶旗標地套用「一個碼位」規則 → 誤拒。
- **WASM 上的停頓誘發不了**：登錄為具名限制，不為它造儀器。
- **具名代價與殘留**：
  - **L-flagged-delete-grapheme**：旗標在時，多碼位的字素被誤拒。
  - **偽造完成的殘留**：若一次規則 (a) 的完成本身是偽造的（L-extend-prior-flush），鍵還在佇列中而旗標沒設，就可能刪錯一個單位。這要三件事同時發生，母數由模型印出。
  - **兩種關法登錄為擁有者的選擇，這一批不採用**：一是不帶旗標的「一個碼位」規則（代價是多碼位字素的功能退步）；二是 FIFO 標記（要先做 §16.1 的偽造分析與原生量測）。
- 被駁回的處方：(ii) 延伸也等 2 秒窗、(iii) 刪除等下一次推播、(iv) 拿掉 Shift＋方向鍵、審核提出的 (a)。理由見裁決。
- **更正 §10.5**：「晚到的 K1 是同一個 K1、帶同樣的證明」只對併段（MergeKey）成立。

### 12.3 頁碼的計數器（Q3；補 §10.8）

- `DOCUMENT_SIZE_CHANGED` 計數器**每個回呼都加一**，不是酬載變了才加。它一到就**自己**推送 editor-state；今天的回呼 switch 只推七種，不包括這一種。
- **P2 要一支有鑑別力的臂**：一次 flush 裡只有大小改變、沒有游標、選取或 tiles 回呼，並由 `lok` 事件記錄斷言這一點。候選是開檔之後的閒置排版完成：開檔時讀到的 `getParts` 小於穩定之後的值。若產生不出這種 flush，記為 NOT_ESTABLISHED，「自己推送」只由讀原始碼涵蓋。
- 登錄 **L-page-size-invariant**。

### 12.4 規則 A 移進執行時的 resolver（Q4；更正 §10.4）

- resolver 依「前一個佇列項目是不是刪除」決定：是刪除，就用自己那一鍵的收合形式；否則看快照。131 的各臂在 v20 上要維持綠，證人是既有的 131-B。
- **更正審核 Q4 對序列 B 機制的說法**：閘門讀的是引擎**快取**（`probe_engine.cpp:5285–5300`）。從過時快照選出的 `delete-selection` 會**通過**閘門，`.uno:Delete` 就在已收合的游標上**往前靜默刪一個字**。所以 resolver 的規則是**資料安全**的要求，不只是體驗；有了它，過時的情況最多是一個提示（131 §9.16 的 NE 格）。
- **S5 加兩鍵序列**，以 Table 1 的 84 格工具封閉：同一種刪除按兩次；以及在 Shift＋鍵之前先刪一次。Writer 的參照由原生工具跑。
- **S5 的判法**：
  - 刪除臂比對經 SPEC-M3-paragraph-merge §24 的 `reduce_content` 處理後的結果；
  - 參照套用 §10.3 的排版分法；
  - 每格記錄後續鍵 `beforeinput` 當下的飛行中數量。「有重疊」只對數量 > 0 的格宣稱；這個集合是空的就判失敗；沒重疊的格另外報告。

### 12.5 pin 清單（Q5；更正 §10.9 的 S-1）

- pin 清單在實作時用 grep 產生，指令與輸出記進規格。
- 已知要改的：
  - `e2/expected-gesture-offers.json` 改指 v20，`expected` 與 `rationale` 一起改；
  - relink 佇列加「4→5 取代」的列（取代 `p1-4-abi-3`、`p1-7-header-test`）；
  - 建置器的 ABI 改成依 profile 決定；
  - `editor_api.h:43` 與它的 extend 契約文字；
  - d.ts 的 `moveLine` 多載，以及 client 的檢查放寬；
  - 頁面的 `MOVE_ACTIONS` 拿掉；
  - `DECLARED_DIVERGENCE` 宣告兩個新的完成／階段；
  - `m4-shift-*` 與 129-B 一起退休。

### 12.6 §11：這一批不改堆疊（裁決）

- pthread 預設堆疊**這一批不變**：沒有量到 Writer 失敗，而且一次連結一個變因。
- **W8 之前、不連結**：在出貨的 Writer profile 上，用鏡像補丁（`90fed9b7`），分別在 64 KB 與 256 KB 下跑產品路徑網與併段 shakedown。兩個瀏覽器都跑，並記錄回聲。有差異就是 finding；沒有差異就登錄 **L-writer-stack-64k**。若真找到 Writer 的失敗，可能只要重新打包、不必連結，那時由擁有者決定。

### 12.7 程序與預設

- **不再有第三輪規格審核。** §6 的引擎碼審核，工單固定帶兩題：
  1. 有沒有一個序列，能在疊上去的 K1 執行之前，用一次偽造的確認把旗標清掉；
  2. 有沒有一個常見序列被旗標拒絕，而「一個碼位」規則本該放行。
- **預設結論**：
  - 12.2 的旗標或模型測試若沒做，第 1 項不出貨，頁面不送 `extendSelection`；
  - 12.4 若沒做，規則 A 留在 `beforeinput`、延後決定不出貨，所以第 1 項也不出貨；
  - 12.3 若沒做，第 3 項不出貨；
  - 12.6 若沒做，W8 照 ODS 計畫背義務，這一批不變。

## 13. 範圍變更：Shift＋方向鍵與範圍上的方向鍵撤出這一批（fable 代擁有者裁決 4，2026-10-13，只追加；取代 §2 的範圍與 §12.2）

裁決 4（`5a8d69f1`，條件 29–36 以那份為準）是依模型測試（`fce084d6`）的六個 REPORTED 做出的。裁決者自己用 `EXTEND_MODEL_TRACE` 追過每一項的第一個序列。

### 13.1 被推翻的兩句

- **§12.2「疊上去的序列都會拒絕」**：不成立。「一個碼位」只證明選到的範圍有多大，從來沒證明是哪一鍵選的。
  - 追蹤 1：兩個排隊中的 Shift＋右被 K1 縮成一個單位，於是被放行。
  - 追蹤 4：延伸自己的 flush 被當成 K1 的。其中 128 個序列卡在 `AwaitingDeleteCompletion`，因為那個階段沒有期限。
- **「偽造完成的殘留要三件事同時發生」**：不成立，它是結構性的，偽造的轉移還會清掉旗標（追蹤 3）。

**旗標撤回，不再當成關法。** 純函式標頭留著：規則 (a) 本身是對的；旗標的函式不接線。

### 13.2 單一成因

`.uno:Delete`（同步，`probe_engine.cpp:5352`）與 barrier 自己的 K1（`:4041–4049`）都會繞過已送出按鍵的 FIFO。而引擎有好幾種「鍵還沒跑就回報完成」的情況：
- 250 ms 讀回；
- 一般移動在別人的 flush 上就完成；
- 偽造的規則 (a) 完成；
- 命令結果排在自己的 flush 前面；
- 範圍選取在 END 之前就完成。

只要刪除可以排在一個沒被確認的按鍵後面，任何規則都是在賭時間；而一個「什麼都沒改」的按鍵根本沒辦法被確認。所以這一批不再補。

### 13.3 這一批（v20）出什麼

- **出**：
  - 第 3 項，頁碼（§4.3、§10.8、§12.3）；
  - 第 4 項，C：照 §10.5，拿掉所有旗標條款。沒有延伸就安全，因為「互相抵消的一對 no-op」與「卡死」都需要延伸才會發生。C1 的逐次判準與 L-C-late-K1 照舊。
  - §4.5 (2) 的資料（`caretBefore`）；
  - 計數 K（127–136 加本批）。
- **不動**：
  - editor ABI 維持 **4**；
  - manifest 的移動維持只有 `collapsed`；
  - 頁面的刪除路由不變；
  - `AwaitingDeleteCompletion` 不加期限。
- **延到「有序刪除」那一批**：第 1、2 項，以及 §10.4／§12.4 的 resolver、S1–S5、R1、S-12、§12.5 的放寬。

### 13.4 下一步的順序（條件 32–34）

1. **條件 32**：模型只用 v20 會提供的鍵重跑（游標起點的一般移動；沒有延伸、沒有範圍起點移動）。印出的「與 Writer 不同」母數附到 finding 137，取代固定在測試裡的 REPORTED 次數。**若出現第 5、6 類以外的種類，連結就停。**
2. 依縮小後的範圍，寫引擎與頁面碼，送 §6 的引擎碼審核，寫 `RUNBOOK-relink-v20.md`，由擁有者連結，再跑計數。
3. **條件 33**：在寫下一份規格之前，模型要加上「排在待確認鍵後面的打字」與「排在待確認鍵後面的行內格式」兩種形狀；只回報，不裁決。
4. **條件 34**：「有序刪除」規格要列出三個候選：
   - A：刪除改送使用者自己的鍵，排在同一個 FIFO 裡，用 `.uno:Undo` 紀錄證明，也就是併段那條路的作法；
   - B：FIFO 標記；
   - C：單執行緒的 unipoll 拓撲，受 finding 040 限制。

   選中的那一個先做原生量測，再由模型把關，才接線。Shift＋方向鍵與範圍起點的移動跟著那一批出。它的第一輪審核固定三題：
   - 有沒有一個序列，讓 FIFO 鍵的 undo 紀錄證明，被另一個變更滿足；
   - 一個什麼都沒做的鍵，頁面怎麼得知；
   - 表格或行內物件的情況下，那個鍵的行為和今天的拒絕不同。

### 13.5 今天兩版就有的洞

模型的 REPORTED 5、6，在 0.2.12 與 0.2.18 上都到得了。已登錄為 **finding 137**（`57d16143`）：會改資料、頻率沒量過、沒有 runner 能誘發；不打臨時補丁，修法歸有序刪除。

**預設結論（條件 36）**：
- 條件 32 沒跑，連結就等；
- finding 137 沒登錄的話，v20 的發佈說明仍必須寫明這兩類（現已登錄）；
- 有序刪除規格沒寫，任何 profile 都不出 Shift＋方向鍵。

**擁有者要知道的**：你點名要的 Shift＋方向鍵，這一批**不會**出。原因是模型證明，在目前的刪除機制下，它會讓「刪錯」變得更容易到達，而且補不住。它會在「有序刪除」那一批出。

## 14. finding 137 擴大，下一份規格改名「有序指令」（fable 代擁有者裁決 5，2026-10-13，只追加）

裁決 5（`b0ca2790`，條件 37–41）。模型（`19cec698`）的條件 33 顯示：打字（同步的 `paste`）與行內格式（同步的 `.uno:Bold`），會和刪除一樣搶在待確認的移動之前執行。裁決判定兩者在 0.2.12 與 0.2.18 上都到得了，前提和 finding 137 相同。

- **finding 137 擴大**：「核心還沒執行的方向鍵後面，接著送出的文件指令會落在錯的狀態上」。一個成因、三種後果：刪錯、字提早一格、格式套錯（finding 137 追加段）。
- **v20 的範圍不變**（§13.3），**計數也不變**。發佈說明必須寫出這一類與三種後果，並註明兩個版本都有。
- **下一份規格改名「有序指令」**，涵蓋刪除、打字與行內格式。候選：
  - **A**：刪除改送使用者自己的鍵，用 `.uno:Undo` 紀錄證明；只涵蓋刪除。
  - **A′**：打字改成送出按鍵事件（引擎既有的退路，`probe_engine.cpp:3195–3207`），格式改成送出加速鍵；每一項都要先做原生量測（IME、122 的延遲、加速鍵）。
  - **B**：FIFO 標記。
  - **C**：單執行緒的 unipoll 引擎拓撲，受 finding 040 限制。

  B 與 C 依構造三者都涵蓋。不論選哪一個，都先原生量測，再過模型（產生器裡要保留條件 33 的兩種形狀），才接線。Shift＋方向鍵與範圍起點的移動跟著那一批出。
- **模型的已知限制，記進下一份規格的模型一節**：粗體不會改變模型裡的矩形寬度。實際上，變粗的那一行可能重送選取矩形，所以「範圍上的行內格式」也可能成為 L-extend-prior-flush 的前一個操作。今天兩版是否可達，不依賴這一點。
- **預設**：即使 finding 137 沒有擴大，發佈說明也必須寫出三種後果；「有序指令」規格寫出來之前，任何 profile 都不出 Shift＋方向鍵。

## 15. 審核 6 與 part 2 的處置、Makefile 區塊（fable 代擁有者裁決 6，2026-10-14，只追加）

裁決 6（`2720b642`，條件 42–55）與修正 1（`f9b64221`）。擁有者 2026-10-14 授權 fable 代為決定，**Makefile 草稿也一併交給它**。工單 `findings/evidence/link-batch/review/brief-7-dispositions.md`。

### 15.1 C 的時間窗：登錄具名殘留，不改引擎（Q1，條件 42–44）

- **具名殘留 L-C-number-or-indent**，與 L-C-late-K1 並列。有三個位置，母數是審核 6 §1.2 的原生量測表，每格 3/3：
  1. 游標在編號標籤前按 Delete；
  2. 第一段有項目符號時，在文件開頭按 Backspace；
  3. 第一段有首行縮排時，在文件開頭按 Backspace。

  在這三個位置，K1 不產生 barrier 看得到的變化，而 Writer 自己的鍵會改文件（`Number On/Off`、`Apply attributes`）。v20 等約 2.25 秒後以 `verified-boundary-noop` 完成，不出任何訊息；在第 1 個位置，游標還會跳到標籤後面。
- **能關掉這個殘留的只有一條路**：「有序指令」規格裡把使用者自己的鍵送給 Writer 的候選 A。在 B（FIFO 標記）或 C（單執行緒引擎）之下，barrier 照樣送 K1，殘留還在，要重新登錄。
- **不採「窗到期時游標動過就拒絕」（審核 6 的 B）**，理由有三：
  - 它只換回 v19 對第 1 個位置的回應，也就是重開加提示。那是產品最貴的回應，而且同樣沒做 Writer 的事。
  - 它是審核之後才改的引擎碼。
  - 第 2、3 個位置完全沒有回呼，引擎和頁面都分不出它們和真正的文件邊界。
- **§10.5「具名代價」的更正**：「在文件開頭按 Backspace，Writer 什麼都不做」只在第一段沒有編號、也沒有縮排時成立。
- **v20 的引擎原始碼定在 `82af92ca`**。
- 發佈說明要把 L-C-number-or-indent 與 L-C-late-K1、finding 137 並列寫出。
- 「有序指令」規格的第一輪固定題第 2 題（「沒有作用的鍵，頁面怎麼知道」）要點名這三個位置當測試位置，附上原生的 `.uno:Undo` 頂端。少了它們，那份規格不算定稿。

### 15.2 頁面的三個修法，在凍殼層 v67 之前落地（Q2–Q4，條件 45–48）

- **`placeCaret` 的確認條件（finding 138）**：判定引擎確認了點擊，要同時滿足兩件事：`sourceSequence` 推進了，**而且**游標位置或選取（`collapsed`／`rectangles`）和點擊前不同。等滿 `graceMs` 的同點分支不變；只看序號不算確認。
  - 修法放在 `NarrowEditorV2Session` 的覆寫裡。`editor-shell/editor-session.js` 綁著 E1-C，不動。
  - 測試用裁決 6 §Q2 表上的七種情況：三種在基底上紅，四種相同。
  - 這個覆寫在出貨的 v19 上也會生效（0.2.12／0.2.18 的 tile 觸發源）。
- **`verified-boundary-noop` 不算修改**：照 part 2 README §4 的 `_enqueueOwned`，讓這個操作自己把佇列項的 `mutation` 翻成 false。第二個私有接縫要有 pin 測試。紅案就是 README §4 的那次量測。
- **頁碼讀取失敗之後**：`_settle` 的錯誤分支把 `_issuedAt` 設回 null，下一次任何狀態寫入就會重讀。成本是讀取持續失敗的期間，每次狀態寫入都讀一次。

### 15.3 檢查（Q5，條件 49–51；§34）

- **X1 是給新身分的新用法，不是修檢查**：加上宣告式差異旗標（worker、新的 manifest 葉、匯出），宣告了卻沒變的差異也判紅；不帶旗標時行為逐位元組不變。連結之前寫好，附七個紅案。交接時單獨一行列出，不算進 §34.4 的兩個數字。
- **M1-1 是修檢查**：證人是套上區塊之後第一次誠實執行的紅報告（`f4c1e7ac`，五個物件不同）。
  - 修正 1 的事實：v20 的 `editor_api.o` 也不同，因為兩行宣告經由 header 進來，沒有定義。裁決原本只預測兩個物件。
  - E2_V20 的載體集合因此定為 `probe_engine,sdk_api,editor_api`。
  - 要兩個 base 都綠：`5d77dc84` 與 `82af92ca^`。後者才證明 part 1 沒動到 v15／v19。
  - 紅案五個，包括「宣告了卻沒變」。
  - 計數：因執行而修 1。
- **`what_the_link_ships` 是資料**：加一個 v20 變體。具名限制：這支工具只讀 `.cpp`，兩邊都用樹裡的 header，所以會報 `editor_api` 相同。宣告經 header 進來的那一部分，由 M1-1 在 `82af92ca^` 回答。

### 15.4 Writer 堆疊掃描（Q6，條件 52）

照 §12.6 做，排在連結之後：
- 兩個明確標成診斷用的 profile 目錄（`e2-editor-v19-diag-stack-64k`／`-256k`），`probe.js` 由審核過的補丁產生。
- 補丁有沒有生效，靠雜湊把回聲那一趟和受測的那一份綁在一起。
- 跑完就刪目錄。

### 15.5 Makefile 區塊與連結前的順序（Q7，條件 53–54）

- 區塊已套用（`d7d62039`），只改一句註解：原本沒有證據的「v15／v19 物件不變」改成指向檢查。修正 1 之後，那句註解要在 M1-1 擴充的同一個 commit 再改一次，點名三個物件。
- **連結前的順序**：
  1. 區塊；
  2. M1-1 證人；
  3. M1-1 擴充、兩次綠；
  4. X1 的 v20 模式；
  5. `what_the_link_ships`；
  6. 條件 45／47／48；
  7. 凍殼層 v67；
  8. 封存；
  9. `RUNBOOK-relink-v20.md` §0 全綠；
  10. 擁有者連結。

### 15.6 修正 2：引擎定在 `543a5566`（條件 56–61）

M1-1 用 `82af92ca^` 當基準時，第二次本該綠的執行是紅的。原因是 part 1 在 `finishMergeKeyError` 留了一處沒包進 define 的改動：輸出字串相同，但 v15／v19 的預處理結果不同。

裁決採 (i)：沒有 define 的那條路逐字恢復成 part 1 之前的文字（`543a5566`）。量測結果：
- v20 的預處理結果改前改後雜湊相同（`8926e4cb…`），審核 6 看過的物件沒變，不必再審；
- 以 `82af92ca^` 為基準的執行 exit 0；
- 以 `5d77dc84` 為基準的執行與紅案 1–4 判定不變；
- 紅案 5 只紅「E2_V19 沒有變」那一行；
- 鎖範圍 12／13。

**v20 的引擎原始碼定在 `543a5566`**。它對 v20 而言與 `82af92ca` 在預處理後相同。這一條是「M1-1 抓到的產品原始碼衛生缺陷」，§34.4 的數字不變。

## 16. 更正：§4.3「核心依 Collabora 回報的可見區域算」沒有證據（2026-10-14，只追加；取代 §4.3 那半句）

2026-10-14 擁有者問 Collabora 捲動時怎麼顯示頁碼，主 session 重讀 `cool-26-04`：

- **確定的**（與 §4.3 一致）：編輯模式下狀態列的字串是核心推的 `.uno:StatePageNumber`（`browser/src/control/Control.StatusBar.js:681`、`:164`），核心用 `SwViewShell::GetFirstLastVisPageNumbers` 算「可見的第一頁到最後一頁」（`engine/sw/source/uibase/uiview/view2.cxx:1784–1901`）；外觀是底部狀態列最左邊一個可點的徽章（`browser/src/control/jsdialog/Widget.HTMLContent.ts:149–160`，點了開「前往頁面」）。
- **§4.3 說錯或說過頭的**：「依 Collabora 回報的可見區域算」。客戶端捲動時確實送 `clientvisiblearea`（`browser/src/app/ViewLayout.ts:133`），但核心只把它存成 kit 可見區（`SwXTextDocument::setClientVisibleArea` → `setKitVisibleArea`，`engine/sw/source/uibase/uno/unotxdoc.cxx:3502–3516`）；`GetFirstLastVisPageNumbers` 讀的是 view 自己的 `GetVisArea()`（`engine/sw/source/core/view/viewsh.cxx:3023`），而原始碼自己寫著 COKit 下 `VisArea()` 是整份文件（`engine/sw/source/core/layout/layact.cxx:756`；`engine/sw/source/uibase/uiview/viewport.cxx:201`）。**Collabora 的頁碼在捲動時會不會跟著變，讀原始碼無法確定；可能跟著游標（核心把 view 捲到游標處時）**。未實測。要定案的量測：原生 LOK 送 `setClientVisibleArea` 後讀 `.uno:StatePageNumber`。
- **不影響**本規格的設計：v20 的頁碼由頁面用頁面矩形算，捲動時 0 個引擎請求、跟著捲動（任務 10-14n 量過）；Q-D 不採核心字串的理由不變。
- **擁有者 2026-10-14 的決定**：頁碼的**外觀**照 Collabora（底部一條一直看得見的狀態列、頁碼在最左邊、正常字級）；交任務 10-14o 的 finding 143 修法。點了跳頁不在這一版。

## 17. 綁定 v20／宿主 0.2.23（交接 10-15 Next 2；2026-10-15，只追加）

### 17.1 M3 runner 的宿主、session、引擎包、殼層 pin 移到 0.2.23／v72

part P（`findings/evidence/link-batch/pre-binding/README.md` P4）只移了頁面 pin（`ccb67a52…`），其餘還指著 0.2.14／v63。這一步把它們一次移完，前例 `fb839ec1`、`3a6603de`、`05aa0c75`：只動 pin 行，共 13 行，舊值留在註解。

| 常數 | 新值 | 舊值 | 檔案 |
|---|---|---|---|
| `BUILD_ID` | `c3c22d9294de068a` | `eb3f9408…`（0.2.14） | assets |
| `HOST_COMMIT` | `2ccf1a9` | `237f2cb` | versions、page_honesty、production_ui、autosave |
| `HOST_VERSION` | `0.2.23` | `0.2.14` | same_second、page_honesty、production_ui、autosave |
| `SESSION_SHA256` | `f47c80ec955397c4…` | `62a2a20e…` | page_honesty、production_ui、autosave |
| `SHELL_BUNDLE_SHA256` | `4dc10507565992d5…`（v72） | `318b3bf2…`（v63） | production_ui |

每個新值都有兩個以上的來源：宿主 repo（`git log -1` 是 `2ccf1a9`、`appinfo/info.xml` 是 `0.2.23`、樹是乾淨的）；封存的引擎包 `build/archive/host-0.2.23-engine-c3c22d9294de068a/MANIFEST.json`（`buildId`、session 與頁面的 sha256）與宿主 0.2.23 的證據報告（`findings/evidence/host-0.2.23/`）；session 在樹、`dist/`、封存包三處逐位元組相同；殼層雜湊是 `build_e2_c_shell_bundle.py`（不帶 `--write`，結束碼 0、`problems` 空）自己回答的，與無宿主泡泡見證的報告相同。改綁後 `make test-e2-c-static` 結束碼 0（`findings/evidence/link-batch/binding-v20/test-e2-c-static-after-repin.txt`）。這是綁定，不是修理：§34.4 兩個數字都不加。

### 17.2 merge runner 的 `BINDING` 綁到 v20（手冊 RUNBOOK-relink-v20 §4 第 2 步）

`run_merge_wasm_shakedown.py` 的 `BINDING` 從 v19（`8da777d7`）換成 v20：wasm `313b08d5…`、worker `478d0da1…`、session `f47c80ec…`、殼層（v72 模組）`e7c4eefe…`、html `b1185aaa…`、頁面與頁面原始碼都是 `ccb67a52…`（原始碼本來就指向 v20，不需改指）、eshape 與 native 與 v19 相同。九個值由 runner 自己的 `bound_values()` 不開瀏覽器算出，每一個都有第二個來源（`findings/evidence/link-batch/binding-v20/README.md` 的表）。v8 紅案只差 profile 自己的三個值，仍會被計數。`test_bound_to_v19_after_v56` 改名 `test_bound_to_v20_after_v72`。從這個 commit 到 v20 計數的判讀讀完，runner 不再改（§34.1 的凍結）。

連帶的一件修理（`00903e29`，§34.4 因執行而修 +1）：`V19Witness` 原本只從 git 還原 runner 的身分，`BINDING` 仍向現行模組借；綁到 v20 之後它在 v19 X7 報告上依構造讀成 NOT DONE（修前 2 紅、修後 5/5）。修法是 `BINDING` 也從同一個 commit 還原；判讀器不改。

登錄一件觀察：`test_judge_counted_m2.py` 與 `test_merge_wasm_clauses.py` 不在任何 Makefile 目標裡，綁定後 `make test-e2-c-static` 結束碼 0、同時 V19Witness 是紅的。計數鏈的前置檢查先手跑這兩支；要不要進閘門是擁有者的決定（Makefile 改動）。

### 17.3 §10.7 的清單漏了 production UI 的三臂：Rbs／Rdel 改期望、B3x 自本次計數撤出（2026-10-15，只追加；寫在計數鏈啟動之前）

§10.7 要求在任何計數之前列出「每一支期望寫著 `nothing-selected`、拒絕次數或世代清單的臂」及其在 C 之下的新期望；當時的清單由 held-into-refusal 探針的期望 grep 出來（`start-press`、`start-hold`、…，`269cbc6d` 已改）。**漏了 `check_m3_production_ui.py`（SPEC-M3-production-ui §13.2–13.3）的三支臂**，它們的期望也是拒絕：

- **Rbs、Rdel**（A1-2′ R）：`score_run` 要世代 `1 → 2`（拒絕＋重開），A1-3′ 要至少一筆停下的樣本且每顆按鈕停用；
- **B3x**（A1-5）：三次拒絕到 Worker generation 上限 `1→2→3→3`、`data-limit` 為 `saved`、通知按鈕重載；
- **Bdel、Bbs**（0.2.7 的臂，§13 起不再跑、不計數）：同一個拒絕期望（世代 `1 → 2`）。若有人在 v20 上跑它們，會因同樣的理由紅在 `no refusal-and-reopen happened`——那是期望過期，不是產品缺陷；它們的位置是 v8 的版面，本來就不該在 v19 之後跑。

這一段是在準備 0.2.23 的計數鏈時讀原始碼發現的（`check_m3_production_ui.py` 自 `3a6603de` 起只有 pin 的 commit），不是跑出來的；證人另外跑。

**證人**（§34.4「因執行而修」的證人）：`findings/evidence/m3-production-ui/witness-c-0.2.23/`（`f3b543c9`；非計數、runner 未改 `bd3a15fb…`、宿主 0.2.23、兩個瀏覧器各一輪）。Rbs／Rdel：世代 `1 → 1`，邊界鍵 busy→ready 2,257–2,261 ms、修訂不變，伺服器檔案恰一個標記、拿掉標記後的序列＝原文，重開等待跑滿 60 s；紅在 `generation 1 -> 1: no refusal-and-reopen happened` 與 `A1-3: no sample outside ready/busy`（第二行在主 session 的預測之外：A1-3′ 預設有一個停下的狀態，同一類，記下）。B3x：三下都沒有世代變化、沒有 `data-limit`，八行紅全在「上限從未到達」的下游；另有一則 toast 「回到檢查點：editor cannot restart from ready」，**只有 harness 到得了**——`#notice` 沒有 `data-show="1"` 就是隱藏的（`web/e2-editor.html:214`），runner 的 `NOTICE_ACTION` 用 JS 直接 `.click()` `#notice-action`（`check_m3_production_ui.py:191`）；ready 狀態下沒有使用者按得到它。不是產品 finding。

**處置**（主 session 代擁有者，擁有者早上確認 B3x 那一項）：

1. **Rbs、Rdel 改期望，鍵在宿主實際送出的引擎位元組上。** 新期望照 §10.7：拒絕 0 次、世代維持 `'1'`、文件不變（伺服器恰一個標記、拿掉標記後的序列＝`ORIGINAL_SEQ`）、沒有停下的樣本（A1-3′ 反過來：離開 ready/busy 的樣本才是紅）。鍵（`boundary_noop_keying`）照 merge runner 的前例 `boundary_noop_declared`（`7e6c9acd`）：讀宿主 `engine/files/<profile>/probe.wasm.gz` **解碼後的位元組**，找引擎**發出**的字串 `,"completion":"verified-boundary-noop"`（常數從 merge runner import，兩支 runner 不可能鍵在不同字串上；不是 profile 名字），解碼後的 sha256 要等於 manifest 宣告的。**讀不到就拒跑**（run），**或該臂判紅**（score 讀到記錄的鍵是 `None`）——不回落到任何一邊的期望。鍵記在報告 `static.boundaryNoop`；沒有這個鍵的舊報告照舊期望判（它們全在 v8／v19 上跑），要用 C 判就給 `--score … --engine <封存的引擎包>`，其 buildId 必須等於報告記的、wasm 必須等於報告記的（若有記）。**沒有 C 的引擎上期望一字不改**：34 份已 commit 的 production UI 報告以新舊 runner `--score` 比對，30 份逐位元組相同，4 份 `no-scope/*.json` 只差 traceback 的行號（它們沒有 `runs`、不是 runner 報告，兩版都丟 KeyError）；0.2.12 三份合併後 `--red-cases` 仍是 `40/40`、結束碼 0。證人報告：改前 Rbs／Rdel 四格 0/1（上述兩行），改後 `--engine build/archive/host-0.2.23-engine-c3c22d9294de068a` 下 4/4 綠（`witness-c-0.2.23/rejudge-under-c.txt`）；C 分支的紅案 6/6 紅：重開（世代 1→2）、停下的樣本（即使所有按鈕都停用）、停下且按鈕未停用、標記 0 個、標記 2 個、序列變成 `MERGED_SEQ`。`wait_reopened` 的 60 s 等待保留：它靠超時結束，只影響時間不影響判分（每個 R 臂每輪多約 60 s）。**§34.4：因執行而修 +1**（證人 `f3b543c9`）；因審核而修 0。
2. **B3x 自 0.2.23 的計數撤出**（AGENTS.md §4：前提被證偽就撤回宣稱，不造機械維持它）。它的前提——這份文件只在兩端拒絕（SPEC-M3-production-ui §13.2）——在 C 之下為假，v20 上這份文件沒有東西能誘發三次拒絕與 generation 上限。**判分不改，只是不跑**：`runs-0.2.23/chain-0.2.23.sh` 不排 B3x，`read-0.2.23.sh` 的合併紅案少它一份——A1-5 的 13 個突變因此找不到 B3x 的執行，runner 的 `--red-cases` 依「每個突變都要找到執行」的規則結束碼 1，讀的時候照這一句解讀（期望 `red cases: 27/27`、13 則 `no passing B3x run`）。
3. **登錄（AGENTS.md §3：「有行為而沒有東西守著」）**：A1-5（Worker generation 上限之後的救援、通知與重載）與 A1-2′ R「跨拒絕的救援」這兩種**行為在 v20 上仍然存在**——拒絕還在（例：表格儲存格尾的 Delete，finding 136），只是這份文件上沒有計數臂能誘發。工作項：在一個有真拒絕的 fixture 上寫一支臂（新機制，所以只登錄、不在本輪做）。**從來沒做時**：這兩種行為自 v20 起**沒有東西守著**；發佈說明 §5「不會證明的」列入。

### 17.4 具名極限：C 之下的 Rbs／Rdel 沒有正向對照（主 session 審核；2026-10-15，只追加）

審 §17.3 的改動時發現：`score_noop` 判綠的四個條件（世代仍是 1、伺服器上一個標記、去掉標記後與原文相同、沒有離開 ready／busy 的樣本），在「邊界鍵被頁面吃掉、根本沒送到引擎」時也全部成立——「什麼都沒發生」和「機制沒跑起來」長得一樣而且是綠的。那一鍵真的跑過的證據在時間線裡：一段約 2.26 秒、`rev` 前後不變的 busy（證人四次 2,257–2,261 ms；其他 busy 最長 905 ms，分得開）。

**不改程式**：§34.4 要求一份誠實執行、已 commit、判錯了的報告才能改檢查，現在沒有（§34.3 的審核預算也不適用：這是既有 runner 的一個分支，不是改寫過半的新工具）。處置是讀的那一側：計數後寫 RESULT 時，讀的人逐次確認每個計數的 Rbs／Rdel 都有一段 ≥ 2,000 ms、`rev` 前後相同的 busy，把每次的長度寫進 RESULT；沒有的那一次，該臂讀成 NOT_ESTABLISHED，不是 PASS。**從來沒做時**：Rbs／Rdel 的綠只證明「沒有拒絕、文件沒變」，不證明邊界鍵到過引擎。§34.4 兩個數字都不加。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-13 | 草稿：範圍、現況、設計（4.1 的完成條件待 10-13h）、判準 S1–S4／R1／P1–P3／C1／E1–E3／K、連結與計數的形狀、開放問題 Q-A–Q-D。4.3 在 commit 前讀過 Collabora 與 Writer 原始碼後改寫：頁碼是可見頁範圍、編輯模式由核心算（計畫附錄的說法不完整） |
| 2026-10-13 | §9：4.1 的完成條件依 10-13h 定案（extend 與範圍起點的移動等游標回呼），並寫下 S2 在 v19 上先紅的 18 格預測 |
| 2026-10-13 | §10：審核 1 的處置（fable 代擁有者裁決 2）。§9 的完成規則撤回，改成轉移規則＋模型測試；B2 改成執行時決定刪除形式＋S5；C 改成時間窗；§4.5(1)／E1 撤回；頁碼改由 DOCUMENT_SIZE_CHANGED 計數器觸發；Q-A 底部、Q-C 出貨、Q-D 不改；寫碼前再一輪有界審核 |
| 2026-10-13 | §11：登錄 pthread 預設堆疊的問題（finding 089 O-S；預設不變、跟著 W8） |
| 2026-10-13 | §12：第二輪審核的處置（fable 代擁有者裁決 3）——殘留母數由模型定義、帶旗標的刪除（Q2，資料會改錯）、計數器自推、規則 A 進 resolver（資料安全）、S5 兩鍵序列、pin 由 grep 產生、§11 不改＋W8 前 Writer 堆疊掃描；不再有第三輪 |
| 2026-10-13 | §13：範圍變更（fable 代擁有者裁決 4）——Shift＋方向鍵與範圍上的方向鍵撤出這一批、旗標撤回、§12.2 兩句被推翻；v20 只出頁碼、C（無旗標）、§4.5(2) 資料與計數，ABI 4；今天兩版就有的 REPORTED 5／6 登錄為 finding 137 |
| 2026-10-13 | §14：finding 137 擴大到打字與行內格式（fable 裁決 5，兩版都到得了）；v20 範圍與計數不變、發佈說明要寫三種後果；下一份規格改名「有序指令」（候選 A／A′／B／C） |
| 2026-10-14 | §15：審核 6 與 part 2 的處置（fable 裁決 6＋修正 1）——L-C-number-or-indent 登錄、引擎定在 82af92ca；placeCaret 確認改要游標或選取作證（finding 138）、noop 不算修改、頁碼讀失敗後重讀；X1 新用法、M1-1 修檢查（E2_V20 三個物件）、what_the_link_ships 資料；Makefile 區塊已套用；連結前順序 |
| 2026-10-14 | §15.6：修正 2——part 1 的 `finishMergeKeyError` 有一處沒包進 define，恢復舊文字（`543a5566`），v20 預處理不變；引擎定在 `543a5566` |
| 2026-10-14 | §16：更正 §4.3 的「依 Collabora 回報的可見區域算」——原始碼看不出 Collabora 的頁碼會跟著捲動；擁有者決定外觀照 Collabora 的底部狀態列 |
| 2026-10-15 | §17.1：M3 runner 的宿主、session、引擎包、殼層 pin 移到 0.2.23／v72（13 行；綁定，不是修理） |
| 2026-10-15 | §17.2：merge runner 的 `BINDING` 綁到 v20；V19Witness 連 BINDING 一起還原（因執行而修 +1）；登錄兩支判讀器測試不在任何 Makefile 目標 |
| 2026-10-15 | §17.3：§10.7 的清單漏了 production UI 的 Rbs／Rdel／B3x（Bdel／Bbs 同一期望、不計數）；證人 `witness-c-0.2.23`；Rbs／Rdel 改期望、鍵在宿主送出的 wasm 位元組（因執行而修 +1）；B3x 自 0.2.23 計數撤出（§4）；登錄 A1-5 與跨拒絕救援在 v20 上無計數臂守著（§3）。fable，計數鏈準備工單 |
| 2026-10-15 | §17.4：C 之下 Rbs／Rdel 沒有正向對照，登錄成具名極限；RESULT 時由讀的人手動確認 2.26 秒的 busy（不改程式，§34.4 無證人） |
