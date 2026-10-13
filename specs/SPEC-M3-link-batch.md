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

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-13 | 草稿：範圍、現況、設計（4.1 的完成條件待 10-13h）、判準 S1–S4／R1／P1–P3／C1／E1–E3／K、連結與計數的形狀、開放問題 Q-A–Q-D。4.3 在 commit 前讀過 Collabora 與 Writer 原始碼後改寫：頁碼是可見頁範圍、編輯模式由核心算（計畫附錄的說法不完整） |
