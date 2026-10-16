# SPEC M3：連結批次 v21——Ctrl+Home／End（finding 142）、貼上為 Markdown、宣告 C 的 manifest 欄位

狀態：**草稿，未審核**（2026-10-16 起草）。這份規格在兩席審核之前不約束任何實作；審核之後，第 5 節的判準在任何實作與執行之前釘死。

依據：`handoff/PLAN-2026-10-16-link-batch-v21.md`（§3 的範圍 A，擁有者 2026-10-16「好，請開始」，計畫 §6）；三份事實整理 `handoff/link-batch-v21/facts-*.md`；原生量測 `findings/evidence/link-batch-v21/native/`（142、Markdown、`Language=` 三組）。

證據標記：**已觀察**＝量過或在產物上讀到；**讀原始碼**＝沒量；**推論**＝從前兩者推出；**未量**＝沒有人量過，後面寫怎麼量。

## 1. 為什麼要有

- **finding 142 會刪錯字（已觀察）**：Ctrl+Home／Ctrl+End 被頁面交給隱藏的輸入框吃掉，文件游標不動；接著按 Backspace，刪的是游標實際所在處的字（任務 10-14n `press-after-ctrl-home` 臂：「LD-PAGE-01」少一個字，revision 0→1）。0.2.24 發佈說明 §4.7 寫明「正解是引擎動作，進下一批連結」。
- **貼上為 Markdown 是擁有者的需求**（2026-10-14 裁示 A：明確的「貼上為 Markdown」，Ctrl+V 照舊純文字；`research/RESEARCH-2026-10-14-markdown-paste.md`）。引擎把貼上的 mimetype 寫死成 `text/plain`（`probe_engine.cpp:3239`），不連結做不到。
- **C 沒有宣告**：四支工具靠 wasm 裡的字串判斷 profile 有沒有 C（事實整理 markdown-cfield ITEM 2(b)；交接 10-14b 寫「兩支」，10-15 又多兩支）。下一個 profile 是補宣告的時機。
- 這三項都要連結；連結一次的固定成本（新 profile、殼層 generation、宿主、整條計數鏈）只付一次。其餘四項（`Language=`、D12、placeCaret 收 `TEXT_SELECTION`、文件起訖立即回答）不在這一批，理由在計畫 §2.4–2.7。

## 2. 範圍

| # | 項目 | 動到 | 來源 |
|---|---|---|---|
| 1 | `move-document-start`／`move-document-end`，頁面把 Ctrl+Home／Ctrl+End 綁上去 | 引擎、編輯器 ABI 4→5、worker、manifest 產生器、client、session、頁面 | finding 142、計畫 §2.1 |
| 2 | 貼上為 Markdown | 引擎（新的文件層匯出）、worker、SDK、manifest、client／session、頁面 | 擁有者 2026-10-14 A、計畫 §2.2 |
| 3 | manifest 宣告 C | manifest 產生器（引擎不動） | 交接 10-14b、計畫 §2.3 |
| 4 | 0.2.24 之後所有未計數改動的完整計數 | — | 記憶 `release-count-batched` |

**不在這一批**：`Language=`、finding 031、D12（原生已量，`findings/evidence/link-batch-v21/native/language/`，之後再決定）；placeCaret 收 `TEXT_SELECTION`、文件起訖立即回答（移到「有序指令」那一批，SPEC-M3-link-batch §14）；Shift＋方向鍵；ODS／Calc；字型與資料包（沿用 v20 的，**不換**）。一次連結一個變因：核心不換，只換我們的引擎原始碼。

**身分**：新 profile `e2-editor-v21`＝v20 的連結輸入＋本批引擎改動，全部放在新的 define `OXSDK_E2_V21_LINK_BATCH` 之下（v20 的 define 照舊也帶）；編輯器 ABI 4→5；新殼層 generation（v74 起）；新宿主版本（0.2.25 起）。連結是擁有者的步驟（第 6 節）。

## 3. 現況

### 3.1 Ctrl+Home／End

- **頁面（讀原始碼）**：`web/e2-editor-app.js:2950` 的 `if (accel) return;` 在查 `KEY_ACTIONS`（`:2835-2842`）之前；Ctrl／Cmd 組合鍵除了 Ctrl+Z／Y／S／B／I／U 與 Enter 之外都不處理。finding 142 引的 `:2679` 已過時。
- **引擎（讀原始碼）**：沒有「移到文件開頭／結尾」的動作。六個移動走按鍵路徑（`handleEditorAction`，`probe_engine.cpp:5654-5743`）：`mutation=false`，完成條件 `EditorCaretOrSelectionCallback`，讀回期限 250 ms 一律武裝；邊界上沒有回呼時以 `verified-move-readback` 完成（finding 096）。全選已經用 `Key::A | EditorMod1Modifier`（`:5674-5691`，Mod1＝0x2000）。
- **原生（已觀察，`findings/evidence/link-batch-v21/native/142-ctrl-home-end/`，81 臂 × 3 回，全部 3/3）**：
  - 文中：Ctrl+Home／End 各一個 `INVALIDATE_VISIBLE_CURSOR`，按鍵後 0.3–0.9 ms，之後至少 2 s 沒有任何回呼；沒有 `TEXT_SELECTION`。252 次按壓的 Undo 都沒變。
  - 已在邊界（剛開檔、第二次按、在結尾按 End）：至少 2 s 完全沒有回呼——096 的形狀。
  - 表格、頁首頁尾、區段：**要按兩到三下**。B2 中間 Ctrl+Home：儲存格開頭 → 表格開頭（A1）→ 文件開頭；頁首裡：頁首開頭 → 本文開頭。每一下中間步看起來都是普通的移動；離開表格那一下多帶 `TABLE_SELECTED`、`CONTEXT_CHANGED` 與尺規，最晚約 765 ms。
  - 文件以表格開頭：Ctrl+Home 落在 A1 開頭，再按無聲。文件以表格結尾：Ctrl+End 落在表格後面的空段落（那個空段落是 Writer 匯入時加的，存檔裡有，Undo 是空的）。
  - **範圍**：單段、跨段、反向的選取，Ctrl+Home／End 都收合並跳到文件開頭／結尾；回呼是空的 `TEXT_SELECTION`，然後 `INVALIDATE_VISIBLE_CURSOR`，相隔最多 0.005 ms。
  - **finding 142 的紅案序列**：Ctrl+Home 之後按 Backspace 是 no-op（沒有回呼、Undo 不變、存檔文字等於 fixture）；Ctrl+End 之後按 Delete 同。K1 在 Ctrl+Home／End 之後 +250 ms 與 +2250 ms 都沒有選取。**只在第一段是普通段落時成立**：第一段有項目符號或編號，Ctrl+Home 再 Backspace 是 `Number On/Off`；有首行縮排是 `Apply attributes`，游標會動——SPEC-M3-link-batch §15.1 的第 2、3 個位置（L-C-number-or-indent），現在一個鍵就到得了。
  - **Writer 的按鍵處理沒有 Ctrl+Home 的分支**（讀原始碼）：這個鍵掉到加速鍵表，`HOME_MOD1`＝`.uno:GoToStartOfDoc`、`END_MOD1`＝`.uno:GoToEndOfDoc`（`officecfg/…/Accelerators.xcu`）。所以按鍵路徑和 `.uno:` 路徑在 Writer 裡跑的是同一個指令；差別在我們引擎的記帳（見 4.1）。
  - **原生多執行緒 LOK 下的排序意外（已觀察 3/3）**：游標在有編號的 P2 開頭，Ctrl+Home 後緊接一個 Backspace，P2 的編號先被關掉、游標才移動。**這不轉移到 WASM（讀原始碼，未在 WASM 量）**：引擎設 `SAL_LOK_OPTIONS=unipoll`（`probe_engine.cpp:6667-6680`），unipoll 下 `postKeyEventAsync` 直接同步處理（`sfx2/source/view/lokhelper.cxx:1283`）。原生的時序與排序結果一律不拿來當 WASM 的證據。

### 3.2 Markdown

原生量測（**已觀察**，`findings/evidence/link-batch-v21/native/markdown-paste/`，152 個 process，每臂 3/3；安裝與 WASM 核心同一個 commit `671c848b`）：

- **每一種構造都會轉**：標題 1–3、粗體、斜體、行內程式碼、程式碼區塊、巢狀與編號清單、3×2 GFM 表格、連結、引言、水平線、中日韓、複雜文字、`data:` 圖片（嵌入）、遠端圖片（保留為連結圖片）。紅案 C1（同一段文字用 `text/plain` 貼）照字面留著。
- **一次貼上＝一個 Undo 動作**（`Paste clipboard`），一次 `.uno:Undo` 還原，152/152，範圍也一樣。
- **`paste()` 152/152 回 true，空輸入也一樣**：空輸入不改文件，但仍然多一個 Undo 動作、送 `.uno:ModifiedStatus=true`。
- **位置**（Writer 的行為，也是 cool#15535 上游測試的意圖）：段首貼上→變成前面的新段落，原段落不動；段中貼上→原段落被切開，**第一個區塊併進左半、失去自己的格式**（標題變本文、清單項不再是清單）；選取上貼上→先取代選取，再照段中；項目符號段首→併進那個清單。
- **編碼**：位元組旗標用執行緒的 codeset 解碼：`zh_TW.UTF-8` 與 `C.UTF-8` 正確，`LANG=C` 變成亂碼（ISO-8859-1）；`charset=` 參數被忽略。**WASM 上推論是 UTF-8**（讀原始碼，未量）：Emscripten 把 `LANG` 設成 `<navigator.language>.UTF-8`（v20 的 `probe.js` 帶這個預設，位元組搜尋），LibreOffice 從不呼叫 `setlocale`，musl 的 `nl_langinfo(CODESET)` 除了剛好是 `C`／`POSIX` 之外都回 `UTF-8`。
- **遠端圖片在 `paste()` 裡面就去抓**：OPTIONS 再 GET；對一個接受連線卻不回應的伺服器，`paste()` 卡 5,003 ms（UcbLockBytes 的 5 秒逾時）。核心的開關 `BlockUntrustedRefererLinks`（`unotools/source/config/securityoptions.cxx:162-167`、`swmd.cxx:71-80`）是全域的，連開啟文件裡的連結圖片也會擋。WASM 上會怎樣：未量（`probe.wasm` 帶 WebDAV／curl 的路徑，位元組搜尋）。
- **空輸入原生不會卡**：Writer 建了錯誤對話框，但沒有 LOK notifier，`Dialog::ImplStartExecute` 回 0。Collabora 在大小 0 時直接跳過（`ChildSession.cpp:1887`）。
- **`[[頁面]]`** 變成 `https://zxx.wikipedia.org/…`（沒有 `Language=`，LOK 的語言標籤是空的）。
- **`**粗體中文**` 只有西文字重是粗的**：存檔只有 `fo:font-weight`，沒有 `style:font-weight-asian`。讀原始碼確認：`mdcallbcks.cxx` 的 `MD_SPAN_STRONG` 只放 `RES_CHRATR_WEIGHT`、`MD_SPAN_EM` 只放 `RES_CHRATR_POSTURE`，整個 `sw/source/filter/md/` 沒有任何 CJK／CTL 的字重或斜體。所以中文的粗體、斜體不會顯示（顯示未量）。**上游缺陷**，登錄成 finding。
- **大小與時間**：145 位元組以內 1–8 ms；16.6 KB 81–111 ms；262 KB 3.0–3.1 s，外加 40,268 個 a11y 的 `CORE_LOG` 回呼。

讀原始碼已知的部分（事實整理 markdown-cfield ITEM 1）：

- 所有文字輸入都以 `text/plain;charset=utf-8` 進核心（`handleInsertText` `probe_engine.cpp:3239`、`handleReplaceSelection` `:4316`）；`oxsdk_document_insert_text` 沒有 mimetype 參數。
- LOK 的 `paste(doc, "text/markdown;charset=utf-8", …)` 經 `doc_setClipboard` → `.uno:Paste` → `SwTransferable::PasteFileContent` → `ReadMarkdown`。Collabora 的 AI 側欄就是這個呼叫（`cool-26-04/kit/ChildSession.cpp:1896`）。
- LOK 的剪貼簿不會替純文字合成 Markdown 格式（`lokclipboard.cxx:176-190`），所以一般貼上依構造不會轉換。
- `doc_paste` 不論匯入產生了什麼都回 true（`init.cxx:6165-6192`），引擎要自己驗。
- 位元組旗標的資料以 `osl_getThreadTextEncoding()` 解碼（`vcl/source/treelist/transfer.cxx:1517`），WASM 的 codeset 沒量過。
- md4c 與 sw 的 markdown 物件在 WASM 核心的連結輸入裡；`mdcallbcks.cxx:227` 獨有的字面字串在 v19、v20 的 `probe.wasm` 裡各出現一次（已觀察，位元組搜尋）。**在 WASM 上從來沒有執行過。**
- E1-C 綁定的輸入與剪貼簿 adapter（`187706b2…`）不能改，新路徑放在 `editor-shell-v2/` 與頁面。

### 3.3 C 的宣告

- C（SPEC-M3-link-batch §10.5）：文件兩端的 Backspace／Delete 等 250 ms＋2000 ms 之後以 `verified-boundary-noop` 完成，不拒絕、不重開（讀原始碼，`probe_engine.cpp:4007-4053`、`:3543-3570`）。
- v19 與 v20 的 manifest 只差三個雜湊、`pageRectangles`、`profile`、`sdkVersion`（已觀察，攤平比對）。沒有任何欄位說 C。`boundaryRejectionRequiresFreshWorker: true` 在 v20 照舊（其他拒絕還在：finding 136、儲存格邊界）。
- 靠字串判斷的四支工具：`run_merge_wasm_shakedown.py:200-206`、`judge_held_into_refusal.py:136-140`（自己一份常數）、`judge_counted_m2.py:144-149`、`check_m3_production_ui.py:635-656`。產品碼不需要宣告：client、session、頁面在執行時看完成名稱反應。

## 4. 設計

### 4.1 `move-document-start`／`move-document-end`（第 1 項）

- **編號（append-only）**：wire id 22＝`move-document-start`、23＝`move-document-end`；內部 id 24、25。ids 1–21 逐字繼承。
- **ABI 5**：`editor_api.h` 的教條（`:30-35`）：往後加 id 要走後繼身分、握手要求完全相等。v20 留在 ABI 4。
- **兩個界限一起動（CLAUDE.md「界限要跟著清單走」）**：`kMaxInternalEditorAction` 23→25（`probe_engine.cpp:7069`）、`kMaxExternalAction` 21→23（`editor_api.cpp:65`）。都在 `OXSDK_E2_V21_LINK_BATCH` 之下，v8–v20 的前處理結果不變。
- **派送：按鍵路徑**。`Key::HOME | EditorMod1Modifier`、`Key::END | EditorMod1Modifier`，與全選同形；`mutation=false`、完成條件 `EditorCaretOrSelectionCallback`、250 ms 讀回期限一律武裝——與六個移動同一套。
  - **不走 `startEditorUnoAction`**：那是變更路徑，會替沒發生的編輯推進 revision（finding 067 的引擎那半，`probe_engine.cpp:5675-5680`）。Writer 裡兩條路最後跑同一個 `.uno:GoToStartOfDoc`（3.1），所以選按鍵路徑的理由是**記帳與排隊**，不是 Writer 行為不同。
- **`editorActionMutates` 排除 24、25**：今天是 `action >= 7`（`probe_engine.cpp:4469-4471`），會把 24、25 歸成要求 revision 的變更動作。它們不改文件，比照 1–6。全選（23）的分類不動。
- **gestures：只有 `collapsed`，limits `no-extend-selection`**。理由（已觀察）：範圍上原生先送空的 `TEXT_SELECTION`、0.005 ms 後才送游標；在第一個 `TEXT_SELECTION` 完成會把移動前的游標序列化進回覆——SPEC-M3-link-batch §9 的缺陷，六個移動也是因此只給 `collapsed`。範圍上頁面照既有路徑 `moveFromPoint`（在點的位置按一下、再移動，`e2-editor-app.js:2973-2979`）。最終落點與原生相同（原生收合後也是文件開頭／結尾），只多一次點擊。
- **Ctrl+Shift+Home／End 不做**（`isMove` 只收兩個字元移動；Shift＋方向鍵在「有序指令」那一批）。
- **表格、頁首頁尾、區段照 Writer**：一下走一層（3.1）。引擎不合併、不模擬「一次到底」。具名：**L-142-steps**——在表格或頁首裡要按兩到三下才到文件開頭，每一下都是普通的移動回覆。
- **worker**：id 表加 22、23（`sdk/sdk-worker.js:87-95` 的後繼表）；新的 worker 雜湊進 Makefile pin。
- **manifest 產生器**：新檔 `tools/build_e2_editor_v5_profile.py`，以 v4 產生器為底（import），`ABI_VERSION = 5`、id 檢查 1..23、兩個新動作 `{"gestures":["collapsed"],"limits":["no-extend-selection"]}`。**v4 產生器一個位元組都不改**：它是 v8–v20 manifest 規則的前置檔，改了 make 會把那些目標當成過期（finding 042）。
- **client／session**：新的 ABI 5 追加清單；兩個動作進移動的後置條件集合（revision 不變、`changed: false`、完成是 `documented-callback-*` 或 `verified-move-readback`，`narrow-editor-v2-client.js:122-124, 297-303`）；進 `BOUNDARY_CAPABLE_MOVES`（髒了先存檢查點、以非變更排隊，`narrow-editor-v2-session.js:75-84`；原生在邊界上無聲，正是那個集合要防的形狀）。`editor-shell/`（E1-C）不動。
- **頁面**：Ctrl／Cmd＋Home／End 在 `if (accel) return;` 之前處理：`session.offers(action)` 為真才 `preventDefault` 並送出；不為真（例如 v20 的 profile）就不攔，照今天的行為（`:2824-2829`「派送不了的鍵不准攔」）。`ACTION_LABELS` 加兩個名稱。macOS 的 Cmd+↑／↓ 不綁（具名 **L-142-mac-arrows**）。

### 4.2 貼上為 Markdown（第 2 項）

- **形狀：文件層匯出**，不是編輯動作。`oxsdk_document_paste_markdown(requestId, documentHandle, utf8, utf8Length)`，回覆形狀比照 `insert-text`。以 manifest 的 `editorContract.pasteMarkdown = "document-sdk-paste-markdown"` 閘控，比照 `pageRectangles`：產生器旗標 `--paste-markdown`，除非匯出表有這個符號否則拒絕；worker 照 `documentExportDeclared` 擋；SDK 的 `DocumentHandle.pasteMarkdown(text)` 沒宣告就丟 `UNSUPPORTED_OPERATION`。不佔 wire id，不需要 gesture（範圍上原生就是先取代、一個 Undo）。
- **引擎**：
  - **送出前拒絕**：去掉空白後是空字串 → `INVALID_ARGUMENT`，不派送（原生：空輸入會多一個什麼都不還原的 Undo，而且 `paste()` 照樣回 true）。超過 **64 KiB**（UTF-8）→ `INVALID_ARGUMENT`。
  - 呼叫 `paste(document, "text/markdown;charset=utf-8", …)`；mimetype 寫死在引擎裡，JS 不能選。
  - **後置條件（不信 `paste()` 的回傳）**：派送前後各讀一次 `.uno:Undo`（`readMergeUndoPayload`），**整份內容不同**且之後至少一個動作（`summarizeUndoPayload`）才算完成，revision +1；否則回錯，revision 不動。沿用 merge 的判法（`merge_key_undo.hpp:391-421`），Undo 數量到上限時也成立。
  - 不 fallback 成逐字打字（`handleInsertText` 的 `postKeyEvent` 退路不適用：那會把 Markdown 原文打進去）。
- **遠端圖片**：不改核心設定（全域、也會擋開啟文件裡的連結圖片）。WASM 上先量（M5）；量出來會卡就照 M5 的預設處理。
- **SDK／client／session**：`NarrowEditorV2Session.pasteMarkdown(text)` 以**變更**排進同一個佇列（與 `insertText` 同類）；`editor-shell/`（E1-C）不動。頁面的刪除帳（141／144／145）不計它。
- **頁面入口（第 8 節 Q1，擁有者決定；草案用 A）**：
  - **A（推薦）**：工具列按鈕「貼上為 Markdown…」開一個對話框，裡面一個文字框；使用者在框裡按 Ctrl+V（一般的貼上，不需要剪貼簿權限）、按「插入」送出。兩個瀏覽器行為一樣，送出前看得到要轉的文字。
  - **B**：按鈕直接 `navigator.clipboard.readText()` 讀剪貼簿送出。Chrome 第一次會跳權限詢問；Firefox 每次都要再按一下它的「貼上」浮鈕。少一步，但兩個瀏覽器不一樣，而且要量宿主路由上的權限行為。
- **具名限制**：
  - **L-md-merge**：段中或選取上貼上時，第一個區塊併進原段落、失去自己的格式（Writer 的行為，原生已觀察）。
  - **L-md-cjk-bold**：`**中文**`／`*中文*` 的中日韓與複雜文字不會變粗／斜（上游缺陷，見 3.2）。
  - **L-md-wikilink**：`[[頁面]]` 連到 `zxx.wikipedia.org`。
  - **L-md-137**：貼上和今天的打字一樣是同步派送（`doc_paste` 在 SolarMutex 下 `dispatchCommand(".uno:Paste")`），所以 finding 137 那一類（核心還沒執行的方向鍵之後，接著送出的文件指令落在錯的狀態上）它也有，後果與「打字提早一格」同形：貼到移動之前的位置。不是新類，跟著「有序指令」那一批處理。
  - **L-md-noop-input**：非空白、但 md4c 什麼都不產生的輸入（例如只有 HTML 註解）仍算一次貼上：revision +1、一個什麼都不還原的 Undo。

### 4.3 宣告 C（第 3 項）

- **欄位**：`editorContract.boundaryNoop = "verified-boundary-noop-after-window-v1"`。值寫出「是哪一種 C」：今天這種是「等 250＋2000 ms 的窗之後」。若日後「有序指令」那一批換成立即回答，用新的值，不改這個值的意思（版本是身分）。
- **產生器的閘門**：`--boundary-noop` 旗標，**被告知、不推測**（比照 `--page-rectangles`）。產生器拒絕宣告，除非 `--wasm` 的位元組含 `,"completion":"verified-boundary-noop"`。這和工具用的是同一份證據；它守的是「宣告了卻做不到」（2026-08-22 的缺陷），不是獨立的第二個來源——具名。
- **四支工具這一批不改**。v21 的位元組帶那個字串，它們今天的判斷在 v21 上就是對的；改它們沒有執行證人（SPEC-M3-paragraph-merge §34.4），而且等於造新機械（CLAUDE.md §4）。登錄：日後若有工具改讀欄位，規則是「欄位在、字串不在」＝停；v20 永遠沒有欄位，照位元組判。
- **產品碼不讀它**：client 照舊在執行時看完成名稱。
- `boundaryRejectionRequiresFreshWorker` 照舊 `true`（其他拒絕還在）。
- X1 以 `--declared-new-leaf .editorContract.boundaryNoop=verified-boundary-noop-after-window-v1` 宣告。

### 4.4 身分與連結的機械

- **Makefile**：新區塊 `e2-editor-v21`，比照 v20 的區塊（`Makefile:1525-1603`）：v20 的 defines＋`-DOXSDK_E2_V21_LINK_BATCH`；匯出表＝v20 的＋4.2 的新匯出；worker pin；產生器改用 v5 的、帶 `--page-rectangles --boundary-noop`＋4.2 的宣告旗標。區塊先給擁有者看（Makefile 改動會讓依賴它的目標變成過期，finding 042）。
- **X1 新增 `--declared-changed-leaf PATH=OLD->NEW`**：今天 X1 只能宣告新增的葉，`abiVersion` 4→5 是**改變**的葉，沒有旗標可宣告（`check_profile_identity.py:13, 94-95`）。這是 X1 的新用途（與 §15.3 的宣告旗標同類），不是修理；落地前先做紅案：沒宣告的改變要紅、宣告了但沒改也要紅。
- **M1-1、`what_the_link_ships`**：照 v20 的跑法，載體加 `E2_V21`。
- **E1-C**：`editor-shell/`、`input/` 一個位元組都不動；`check_e1_c_bundle_intact.py` 必須 `intact: true`。

## 5. 判準（草稿；審核之後、任何實作與執行之前釘死）

形式照 `CLAUDE.md`「驗收判準的形式」：逐實例性質或工具封閉的枚舉；每條附「若永遠沒做」的預設結論。兩個瀏覽器（Chrome、Firefox）。

- **D1（落點＝Writer，逐臂，工具封閉）**：142 原生回合 `arms.json` 裡每一個**本文可達**的臂（頁首頁尾、區段的臂登錄為「產品頁到不了」並寫理由，不算進母數；清單由工具從 `arms.json` 產生），在 v21 上由產品頁送出同一串按鍵之後，**在游標處打一個標記字元、存檔**，標記在存檔文字裡的位置等於原生同一臂「打同一個標記、存檔」的位置。原生的「打標記」變體在實作之前跑完、先 commit。**若沒做**：第 1 項不出貨，頁面不綁鍵。
- **D2（finding 142 的紅案，逐瀏覽器）**：`press-after-ctrl-home` 臂（`findings/evidence/host-0.2.20-hand-test/probe_10_14n.py`）在 v21 的宿主上：Ctrl+Home 完成後 Backspace 以 `verified-boundary-noop` 完成、revision 不變、存檔文字等於原檔。紅案：同一臂在 0.2.24（v20）上照舊是 `verified-selection-delete`、revision 0→1。**若沒做**：同 D1。
- **D3（邊界上不卡，逐瀏覽器）**：游標已在文件開頭按 Ctrl+Home、已在結尾按 Ctrl+End：以 `verified-move-readback` 完成，`changed: false`，回覆在 1000 ms 之內，session 不進 `recoverable-error`。**若沒做**：同 D1。
- **D4（範圍）**：單段與跨段選取上按 Ctrl+Home／End：頁面走 `moveFromPoint`，最終標記位置等於原生的 `r-*` 臂。**若沒做**：範圍上不綁（頁面在範圍上不攔這兩個鍵），登錄。
- **D5（沒有這個動作的 profile 不攔鍵）**：殼層 v74 的頁面載 v20 的 profile 時，Ctrl+Home 不被 `preventDefault`（單元測試，假 manifest）。**若沒做**：v74 不得與 v20 搭配出貨。
- **M1（構造＝原生，逐構造，工具封閉）**：Markdown 原生回合 P1 的每一個語料項（清單由工具從 `tool/corpus/` 產生；M11 系列由 M5 管、M13 由 M3 管），在 v21 上由產品頁的入口貼到空文件開頭、存檔，`md_structure.py` 的結構摘要等於原生同一項（`--compare` 印 SAME）。**若沒做**：第 2 項不出貨——manifest 不宣告 `pasteMarkdown`、頁面沒有入口；引擎帶著匯出出貨（等於扣住）。
- **M2（中日韓在 WASM 上不亂碼，逐瀏覽器）**：M8 在 v21 上的存檔文字等於原生 `zh_TW.UTF-8` 的（`標題 粗體中文 第一項 第二項 第三項`）。這一條直接驗 3.2 的 UTF-8 推論。**若沒做或紅**：同 M1，另立 finding。
- **M3（拒絕不派送）**：空字串、只有空白、超過 64 KiB：回 `INVALID_ARGUMENT`、revision 不變、Undo 內容不變（引擎讀回）。**若沒做**：同 M1。
- **M4（一次 Undo 還原，逐位置）**：P1、P3、P4、P6 各一臂：貼上之後一次 Undo，存檔文字等於貼上前。**若沒做**：同 M1。
- **M5（遠端圖片不卡）**：在 v21 上貼 M11（連線被拒）與 M11c（接受連線、永不回應的本機伺服器）：回覆在 **6,000 ms** 之內、session 不進 `recoverable-error`。**若紅**：頁面在送出前把非 `data:` 的圖片語法改寫成連結（`![alt](url)` → `[alt](url)`，保守比對，程式碼區塊裡的也會被改，登錄為 L-md-image-rewrite），然後重跑 M5 與 M1 的圖片項。
- **M6（大小）**：64 KiB 的決定性語料（工具產生）在 v21 上完成、一次 Undo 還原，記下時間。**若超過 10 s**：上限照預先寫好的規則降成 16 KiB，M6 重跑。
- **M7（Ctrl+V 不變）**：產品路徑網的 `ctrl-v-reaches-the-document` 照舊恰好一個標記；另加一臂：Ctrl+V 貼 C1 的文字，存檔照字面（有 `#`、有 `**`）。**若沒做**：v21 不出貨（這是既有功能的回歸）。
- **M8（沒宣告的 profile 沒有入口）**：載 v20 的 profile 時頁面沒有「貼上為 Markdown」按鈕（單元測試，假 manifest）；SDK 呼叫丟 `UNSUPPORTED_OPERATION`。**若沒做**：v74 不得與 v20 搭配出貨。
- **C1（產生器）**：v19 的 wasm（`1aafd4f9…`，沒有那個字串）加 `--boundary-noop` → 拒絕；v20 的 wasm 加旗標 → 欄位寫入；不加旗標 → 沒有欄位。三個都在單元測試裡。**若沒做**：v21 不宣告 C，四支工具照舊。
- **I1（身分）**：X1 對 v20 印 `VERDICT PASS`，差異**恰好**是宣告的那些（wasm、loader、worker 雜湊；`abiVersion` 4→5；兩個新動作；`boundaryNoop`；4.2 的宣告與匯出），沒有沒宣告的差異。v8、v15、v18、v19、v20 的十六＋四個雜湊與連結前相同。`ScDocShell` 0 次。M1-1 兩次都 exit 0。E1-C `intact: true`。**若沒做**：v21 不綁定。
- **K（計數）**：計數鏈在最終位元組上成立（J-a.2 的讀法）。**若沒做**：本批是未計數候選，名義出貨版本停在 0.2.24。

## 6. 連結（擁有者的步驟）

照 RUNBOOK-relink-v20 的形狀寫 `handoff/RUNBOOK-relink-v21.md`：先封存 v20（`build/archive/`），`ALLOW_FROZEN_RELINK=1` 只給 v21 一個目標，`env -u` 清掉六個 `?=` 變數；連結後必做 I1。v20 的 `.o` 已經比 Makefile 舊（交接 10-16），`make -n` 會先看到重編。**引擎碼先過對抗性審核才寫 runbook。**

## 7. 計數

連結、凍殼層、宿主新版本、pin 改綁、`BINDING` 之後，整條計數鏈排在擁有者的時段、脫離 session。帶的帳：0.2.24 之後的所有改動，加本批。Rbs／Rdel 的正向對照照 §17.4（C 沒變，2,000 ms 的忙碌期仍在）。

## 8. 開放問題

- **Q1（擁有者）**：貼上為 Markdown 的入口用 4.2 的 A（對話框＋文字框）還是 B（直接讀剪貼簿）。草案用 A。
- **Q4**：64 KiB 的上限是估的（原生 16.6 KB 約 0.1 s、262 KB 約 3 s；WASM 未量），M6 量了才知道夠不夠寬。
- **Q2**：D1 的「本文可達」由誰判——建議由 `arms.json` 的 fixture 種類機械地決定（`hf-*`、`sec-*` 不可達），不逐臂人判。
- **Q3**：Ctrl+Home 之後緊接 Backspace，在 WASM 上是否依序（unipoll 推論是）。D2 直接量它；若不依序，是 finding 137 的同一類，不是本批的新類。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-16 | 草稿（opus，主 session）：第 1、3（Markdown 除外）、4.1、4.3、4.4、5 的 D／C1／I1／K。Markdown（3.2、4.2、M 判準）待原生量測。 |
| 2026-10-16 | 補 Markdown（主 session）：3.2 寫入原生量測；4.2 定形狀（文件層匯出＋宣告閘控、送出前拒絕空白與超過 64 KiB、以 `.uno:Undo` 整份內容改變當後置條件、四個具名限制）；M1–M8；Q1 改成擁有者的入口選擇、加 Q4。 |
| 2026-10-16 | 4.2 加 L-md-137（貼上與打字同屬 finding 137 那一類；送審前主 session 自查補上）。 |
