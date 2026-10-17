# SPEC M3：連結批次 v21——Ctrl+Home／End（finding 142）、貼上為 Markdown、宣告 C 的 manifest 欄位

狀態：**判準已釘死（2026-10-16，`523871fa`）**：兩輪兩席審核已處置（§9、§10），§11 是唯一的判準總表。之後只准追加更正。

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

## 9. 審核 1 的處置（2026-10-16，只追加；取代下列被點名的句子）

兩席：`handoff/link-batch-v21/review-1-opus.md`（B1–B4、S1–S17、N1–N12）、`review-1-codex.md`（R1–R12）。主 session 對每一項讀了引用的原始碼才處置。三題擁有者的決定標為 **OD**，答覆之前照「推薦」寫、標「待擁有者」。

### 9.1 產品引擎不是 unipoll（opus B1、codex R1；兩席獨立指出，主 session 讀原始碼確認）

- **撤回** §3.1 最後一點的「這不轉移到 WASM……一律不拿來當 WASM 的證據」與 §8 Q3 的「unipoll 推論是」。正確（讀原始碼）：設 unipoll 的程式只在 `OXSDK_MAINLOOP_ENGINE` 之下（`probe_engine.cpp:6656-6683`、`:6756-6760`），產品規則不帶、也不能帶（`:15-17` 的 `#error`）；產品是 `std::thread` 上的 `engineLoop`，LOK 走多執行緒。原生的排序結果描述的就是產品的拓撲。原生 README 已追加英文更正。
- **Ctrl+Home 是兩跳**：KeyInput 使用者事件 → `AsyncAccelExec`（`svtools/source/misc/acceleratorexecute.cxx:213-226`），只與其他加速鍵 FIFO。產品在移動完成之前不送下一個指令，所以重排要靠**提早完成**：核心停頓超過 250 ms 時，`verified-move-readback` 以快取完成（它序列化的是快取，不讀核心，opus N5），接著送出的同步指令（打字的 `paste`、Markdown 的 `paste`、`.uno:` 格式、`.uno:Delete`）搶在 `GoToStartOfDoc` 之前執行。具名 **L-142-readback-overtaken**：後果是文字落在移動前的游標處，可能在文件任何地方。finding 137 那一類，發佈說明與 137 並列。
- **OD1（待擁有者）**：A（推薦）讀回期限照 250 ms，與六個移動相同；根治在「有序指令」。B：24／25 用較長期限，代價是每次在邊界上按都要等那麼久，而且停頓更長時一樣會發生。
- **新判準 D2′（取代 D2 只在完成後才按的寫法；D2 保留）**：產品頁以真鍵（CDP）連送 Ctrl+Home、Backspace，不等待；起點是原生 `b2b-home-bksp-at-num` 的 fixture（游標在有編號的第二段開頭，第一段是普通段落）。期望：Ctrl+Home 先生效，Backspace 落在文件開頭，以 `verified-boundary-noop` 完成，存檔文字與編號都不變。紅：第二段的編號被關掉，或文字被併段。N=3、兩個瀏覽器、N/N。**若紅或沒做**：第 1 項不出貨。
- **新臂 D6（記錄，不判）**：N=3、兩個瀏覽器：貼上 M6 的語料之後立刻 Ctrl+End、打一個標記，不等待；記下完成種類與標記落點。

### 9.2 Markdown 的出貨開關放在殼層（opus B2、codex R6）

- **取代** M1–M4 的「若沒做：manifest 不宣告」與 M6 的「降成 16 KiB」。manifest 照樣宣告 `pasteMarkdown`：它說的是這個 artifact 有這個匯出，是事實。**產品提供不提供，由頁面入口決定**（殼層 generation，不用連結）。
- **兩層上限**：引擎 64 KiB 是硬上限（連結時定死）；**實際生效的上限在 SDK**（`DocumentHandle.pasteMarkdown` 先檢查 UTF-8 位元組數），初值 64 KiB。M6 紅 → SDK 上限降到 16 KiB（新殼層，不連結），重跑 M6；16 KiB 也紅，或量不出來 → 頁面沒有入口。
- **新的預設**：M1–M6 任一條紅或沒做 → 頁面沒有入口；SDK 路徑仍可被直接呼叫，具名 **L-md-sdk-callable**。所有後備修改都在凍殼層、做宿主、綁定、計數之前完成。I1 依實際的後備狀態列出宣告差異。

### 9.3 遠端圖片：引擎先用 md4c 掃（opus S6、codex R5；取代 §4.2「遠端圖片」一點與 M5 的「若紅」改寫）

- 引擎在 `paste` 之前，用核心同一個 `md_parse`、同一組旗標（`MD_DIALECT_GITHUB | MD_FLAG_WIKILINKS`，`swmd.cxx:951`）掃一次輸入：
  - 任何 `MD_SPAN_IMG` 的 src 不是 `data:` → 拒絕、不派送，錯誤碼 `MARKDOWN_REMOTE_IMAGE`；
  - 掃不出任何區塊文字 → 拒絕、不派送（`INVALID_ARGUMENT`）。這同時**關掉 L-md-noop-input**，並把「空白」定義交給解析器本身（codex 與 opus S5 指出原本的「空白」沒有定義）。
- 「什麼算圖片」由解析器定義（工具封閉）：參照式圖片（`![a][r]`＋`[r]: url`）、多張圖片都涵蓋。直接呼叫 SDK 也一定經過引擎，所以也涵蓋。
- 標頭 `md4c.h` 取自核心的 `workdir/UnpackedTarball/md4c/src/`（與連結的 `libmd4c.a` 同一份 tarball）；`md_parse` 本來就在連結裡（`swmd.cxx:960` 用它）。掃描寫成純函式，另以原生編譯的 md4c 做模型測試，逐項跑原生語料與第 9.3 節的新語料。
- 具名 **L-md-no-remote-images**：含遠端圖片的 Markdown 整段拒絕，頁面顯示「Markdown 裡有網路圖片，尚不支援；請先移除圖片」。
- **M5 改寫**：行內 http、https 主機名、參照式、多張圖片、程式碼區塊裡「看起來像」圖片的文字（應該**不**拒絕：解析器知道那不是圖片）。前四項 → `MARKDOWN_REMOTE_IMAGE`，revision 不變，Undo 不變，瀏覽器網路紀錄裡對那個主機 0 個請求；最後一項 → 正常貼上。N=3、兩個瀏覽器、N/N。**若紅或沒做**：頁面沒有入口。

### 9.4 Markdown 的後置條件與失敗語意（opus S4、codex R4）

- 判定寫成純標頭函式（`src/markdown_paste.hpp`）加模型測試：
  - 派送前讀 `.uno:Undo` 失敗 → 拒絕、不派送；
  - 派送後讀失敗，或內容沒變，或變了卻解析出 0 個動作 → **派送後未確認**，錯誤碼 `MUTATION_OUTCOME_UNKNOWN`。它已經在 session 的復原清單裡（`narrow-editor-v2-session.js:1022`），走 manifest 的 `postDispatchFailureDisposition: "rollback-to-checkpoint"`。**不得宣稱文件沒變**；
  - 變了且至少一個動作 → 完成，revision +1。
- **撤回**「Undo 數量到上限時也成立」的無條件說法（codex R4）。payload 每項有 `index`、`comment`、`viewId`、`dateTime`（`svl/source/undo/undo.cxx:1310-1335`）；到上限時舊項被移除、整串位移。理論上的碰撞會被判成「未確認」而走回復，**方向是安全的**（只會誤判失敗，不會誤判成功）。具名 **L-md-undo-collision**。
- 反向的誤判（內容因為別的東西變了）：`handleInsertText` 的 `postKeyEvent` 退路排進去的鍵，可能在兩次讀取之間加入一個「Typing」動作（opus N11）。屬 finding 137 那一類，罕見，具名 **L-md-undo-foreign**。
- **WASM 上的紅案**：原生先找一個「paste 不產生 Undo 動作」的輸入或位置（候選：游標在受保護的區段裡）。找到就成為 M9：v21 上它回 `MUTATION_OUTCOME_UNKNOWN` 並回復。找不到就照 `CLAUDE.md`「有行為而沒有東西守著」登錄：判定只有模型測試守著。

### 9.5 D 的母數由腳本文法產生（opus B3、codex R2；取代 D1 的「本文可達」與 §8 Q2）

- 一臂進 D1，若且唯若它每一步都是產品送得出的：`k1024|1025|1027|1028|1029`、經 select-range 的 `r…`／`s…` 範圍、經 place-caret 的 `c…` 點擊、`M…=9220|9221`。含 `bksp`、`del`、`K`、`J`、`B`、`Q`、`u.` 步驟的臂不進 D1。每一個被排除的臂與排除它的規則一起列出；未知步驟或零臂 → 工具紅。
- 所以 `sec-*` 與 `hf-home-hdr-click` **在**母數裡（產品到得了），`ctl-*`、`red-*-k1*`、`b2b-*`、`q-*`、`place-*` 不在。
- D1 只比落點；**不擴張成**對已登錄 C 殘留的「與 Writer 完全相同」（codex R2）。

### 9.6 M1 的母數由規則產生（opus B4、codex R3）

- 由原生臂的 metadata 產生角色：Markdown 正向構造 → M1；`text/plain` 控制（C1）→ M7；非文字（`*.bin`）→ 不是字串輸入，排除；超過生效上限 → M3／M6；遠端圖片 → M5；空輸入 → M3。未分類的語料或零項 → 工具紅。分類在任何 v21 執行之前 commit。
- 輸入文件以 sha 釘住（`tool/inputs/empty-template.odt`，`a3354bae…`）。

### 9.7 完成回覆、遮罩與記帳（opus S1–S3、codex R7、R9）

- **新判準 D7（取代 D3 只挑兩個位置的寫法；D3 保留）**：由 `arms.json` 產生，對 D1 母數裡每一下按壓：
  - 原生有游標回呼的那一下 → 以 `documented-callback-*` 完成；
  - 原生無聲的那一下 → 以 `verified-move-readback` 完成，在 1000 ms 之內；
  - 每一下，回覆裡的游標等於 ≥500 ms 之後 `editor-get-state` 讀到的引擎游標（SPEC-M3-link-batch §10.2 S2 的參照）。
- **worker 初始化時檢查遮罩的回傳狀態**（`sdk/sdk-worker.js:1253-1254` 今天忽略它）：不是 OK 就初始化失敗。這樣 `kMaxExternalAction` 沒動、22／23 的遮罩寫不進去時會當場紅。另加 SDK 臂：在範圍上直接呼叫 `move-document-*` → `EDITOR_FORMAT_GESTURE_UNSUPPORTED`、文件不變。`e2/expected-gesture-offers.json` 改指 v21，兩個動作都是 `["collapsed"]`。
- **封閉清單的單元測試（形式二）**：每一個 ABI 5 追加的動作恰好屬於一個後置條件類別；`BOUNDARY_CAPABLE_MOVES` 等於後置條件是移動完成的那個集合。`_validateInherited` 加最後一個分支：不屬於任何類別的動作一律拒絕（opus S3）。
- **記帳臂**：在唯讀（view-only）文件按 Ctrl+End，游標會動、`dirty` 仍是 false；在乾淨文件與髒文件各按一次，`dirty`、內容 stamp、檢查點的斷言照 096／098。`editorActionMutates` 排除 24／25 照做，另經 SDK 送一個過時的 `expectedRevision`，驗證它照移動的語意處理（codex R7；opus N1 指出一般路徑看不出差別）。

### 9.8 刪除暫存帳與按住（codex R8、opus S7、N3）

- **頁面修法**：`holdsDelete` 只在「第一下尚未回答之後，**沒有送過任何其他動作**」時才扣住同方向的刪除；中間送過移動，就不扣，照常送出。新判準 D8：文件開頭 Backspace（進入 C 的窗）→ Ctrl+End → Backspace：第三下在文件結尾刪掉一個字。N=3、兩個瀏覽器、N/N。另外把 141／144／145 的頁面測試全部重跑。
- **按住 Ctrl+Home／End**：22、23 丟掉 `event.repeat`，具名 **L-142-no-repeat**（在表格裡按住只會走一層）。判準 D9：按住 1 秒 → 引擎恰好收到 1 個移動。
- 範圍上 Ctrl+Home 之後很快按 Backspace：送出時讀到的形狀還是範圍，所以送出 `delete-selection`，在收合的游標上被拒絕並跳提示；不會掉資料。具名 **L-142-shape-at-send**（opus N3）。

### 9.9 範圍與長文件（opus S11、S12）

- **D4 的預設改寫**：若紅，頁面在範圍上仍然**攔下** Ctrl+Home／End，提示「範圍上尚不支援」，不送出。**絕不讓隱藏輸入框吃掉這個鍵**（那會把 142 帶回來）。
- **新判準 D10**：60 頁 fixture（`tools/create_long_document.py --pages 60`）按 Ctrl+End 之後，引擎游標的矩形落在畫面的可視區內，`#page-status` 顯示最後一頁。判狀態，不數像素。N=3、兩個瀏覽器。

### 9.10 跨層閘控、釘選清單、身分（opus S8、S9、N2、N12；codex R9、R11）

- **釘選清單由 grep 產生**（照 SPEC-M3-link-batch §12.5），指令與輸出 commit。已知的：`tests/editor_abi_header_test.cpp:20`（`== 4u`）、`e2/relink-queue-v3.json` 的兩列、`e2/expected-gesture-offers.json`、`tools/check_e2_b_inventory.py`、`editor-shell-v2/tests/manifest-reachability.test.mjs`、三個 `.d.ts` 與 `declaration-drift.test.mjs`、`tests/test_e2_editor_v4_profile.py`、session 的 `ACTIONS`。
- **放在 `OXSDK_E2_V21_LINK_BATCH` 之下**：ABI 常數、新的 wire enum、discovery enum、`sdk_api.h` 的新宣告。M1-1 的兩個 base 與預期的載體（`probe_engine`、`sdk_api`、`editor_api`）在實作前寫下。
- **v5 產生器的機制**（opus S9）：import v4 → 換掉 `v4.ABI_VERSION` 與 `v4.action_map` → 從 `argv` 拿掉自己的旗標再呼叫 `v4.main()` → 加上自己的葉、重寫 manifest、重印摘要。v21 的 manifest 規則把兩個產生器都列為前置檔。
- **X1 的 `--declared-changed-leaf`**：寫成三個參數（`PATH OLD NEW`），避開值裡含 `->` 的解析問題；路徑是 `.editorContract.abiVersion`（頂層的 `abiVersion` 是 SDK ABI）。紅案：沒宣告的改變、宣告了卻沒變、OLD 錯、NEW 錯、葉不存在、型別不符。兩個新動作是六個新葉（各自的 `id`、`gestures[0]`、`limits[0]`），六個 `--declared-new-leaf` 在 runbook 裡先寫好。
- **跨層負向矩陣**（codex R9）：由實際的按鍵綁定表、動作表、文件匯出表產生，涵蓋宣告缺席、扣住（`gestures: []`）、宣告值錯誤、直接對 worker 送請求。兩個動作與 `pasteMarkdown` 都要。頁面綁定排除 Shift 與 `isComposing`（opus N2）；D5 改用**真的** v20 manifest。D5 與 M8 的限制對象改成「最終候選殼層」，不寫死 v74。
- **證據的身分**（codex R11）：每份 D／M 報告都帶受測的 wasm、worker、頁面、殼層、輸入與參照的雜湊；與最終候選不符的報告作廢。merge 的第十個 `BOUND_KEY` 不需要。

### 9.11 C 的宣告（opus S10、N10；codex R12）

- **OD3（待擁有者）**：A（推薦）第 3 項**撤出 v21**。理由：
  - 這一批沒有任何東西讀它（工具不改、產品不讀），所以宣稱的價值（工具誠實）並沒有交付；
  - 位元組閘門證明不了窗長（codex R12：把窗從 2000 改成 3000 ms，C1 照樣綠）；
  - C 的語意在「有序指令」那一批本來就會變，到時候工具也要重新期望。
  
  宣告跟著它的第一個讀者一起做。B：照留，登錄為「沒有東西可守」（`CLAUDE.md` §3），閘門的承諾縮成「這個字串存在」，具名 **L-C-decl-variant**。

### 9.12 其餘

- **N（執行次數，opus S13）**：D、M 的每一臂在每個瀏覽器跑 N=3，過＝N/N。
- **Markdown 沒量過的位置（opus S14）**：表格儲存格（含把 GFM 表格貼進儲存格）、頁首頁尾、跨儲存格的範圍。在實作之前先跑原生臂；跑之前具名 **L-md-unmeasured-positions**。
- **Q1 在釘死判準之前定案（opus S15、codex）**：A 加一臂「在對話框裡打標記、取消、存檔 → 沒有標記」，並寫明對話框的輸入不經過 E1-C 的 adapter；B 加每個瀏覽器在宿主路由上的權限臂。
- **貼上的記帳（opus S16）**：貼上之後 `dirty` 是 true，自動儲存會觸發（`editor-session.js:299-310`）。
- **一個鍵就到的既有殘留（opus S17）**：在 v21 上記錄（不判）兩臂：x-lc（Ctrl+Home 之後在有項目符號、編號、縮排的第一段按 Backspace）、表格裡（Ctrl+Home 到儲存格開頭再按 Backspace＝finding 136 的儲存格邊界拒絕與重開）。發佈說明與 L-142-steps 一起列。
- **比較器（codex R10、opus N8）**：在首次使用之前固定 ODT／FODT 的正規化：合併 ODT 的樣式與圖片資源；圖片比資料雜湊，不只比「有沒有嵌入」。紅案：跨容器相等、缺樣式、圖片壞掉。M4 改比還原後的正規化結構（含原有格式與跨段選取），位置由原生的位置臂產生；M7 比純文字控制的結構。這是比較器的新用途，綁定之前完成。
- **M3／M6 的邊界（opus S5、codex R6）**：語料產生器產生**恰好** 65,536 與 65,537 個 UTF-8 位元組，由 3 位元組的中日韓字元組成，附長度斷言與雜湊。M3 驅動的是 SDK（生效上限所在的那一層），另一臂直接對引擎送 65,537 驗硬上限。M6 計時的是頁面從忙碌到就緒的時間；10 秒是給擁有者的等待上限，SDK 自己的逾時是 30 秒（`document-sdk.js:151`）。另外記下 `CORE_LOG` 回呼的數量（opus N9：64 KiB 約一萬個）。
- **opus N6**：v20 的 manifest 規則釘的是樹裡的 worker，改了 worker 它就會拒絕——這是預期的，在 runbook 裡註明。
- **opus N7**：SPEC-M3-link-batch §10.8／§12.5 寫的「extend 用 ABI 5」被這一批用掉了，extend 現在要 ABI 6；在那份規格追加一行更正。
- **opus N4**（C 的窗開著時按 Ctrl+Home 會排在刪除後面）：同意，屬既有行為，不另立判準。

### 9.13 擁有者的三題（2026-10-16，只追加）

擁有者三題都選 A：

- **Q1＝A**：「貼上為 Markdown」的入口是對話框加文字框。§4.2 的入口定案，§9.12 的 A 臂（打標記、取消、存檔 → 沒有標記）成為判準，B 的權限臂不做。
- **OD1＝A**：Ctrl+Home／End 的讀回期限照 250 ms。L-142-readback-overtaken 照 §9.1 登錄，根治留給「有序指令」。
- **OD3＝A**：第 3 項（宣告 C）**撤出 v21**。§2 的範圍只剩第 1、2、4 項。§4.3 與 C1 不適用；I1 的宣告差異裡沒有 `boundaryNoop`；產生器不加 `--boundary-noop`。四支工具照舊用位元組判斷，宣告留給「有序指令」那一批，跟它的第一個讀者一起做。

### 9.14 第二輪原生量測的處置（2026-10-16，只追加）

依據：`findings/evidence/link-batch-v21/native/142-ctrl-home-end/d1-marker/` 與 `…/markdown-paste/round-2/`。兩份的判讀工具主 session 都重跑過，輸出逐位元組相同。

- **D1 的母數（更正 §9.5 一句）**：`hf-home-hdr-click` 用 `.uno:JumpToHeader` 進頁首，照 §9.5 自己的規則是**排除**，不是納入。§9.5 說它「在母數裡」是錯的。結果是 D1 沒有頁首頁尾的臂：WASM 上頁首裡的 Ctrl+Home 列為未量，併入 L-142-steps。量測工具另外補了兩條規則，照收：
  - 沒有任何 `M…=9220|9221` 按壓的臂排除（`no-ctrl`）；
  - 最後一次 Ctrl 按壓之後還有產品步驟的臂，工具拒絕。
  
  母數 38 臂納入、43 臂排除，由 `tool/d1_population.py` 產生；原生參照是「最後一次 Ctrl 之後打一個 `Z`、存檔、讀落點」，38 臂都 3/3。WASM 端用產品的打字路徑打同一個 `Z`。
- **預先掃描改成三條規則（取代 §9.3 的兩條；理由：原始 HTML 會被 Writer 的 HTML 匯入處理並抓網路，`swmd.cxx:591-603`，原生 H4／H7 臂 3/3 有 OPTIONS＋GET）**：
  1. 任何 `MD_SPAN_IMG` 的 src 不是 `data:`（**不分大小寫**；原生 S15：`DATA:` 會被嵌入）→ `MARKDOWN_REMOTE_IMAGE`；
  2. 任何 `MD_BLOCK_HTML` 或 `MD_TEXT_HTML`（原始 HTML）→ `MARKDOWN_HTML_UNSUPPORTED`，具名 **L-md-no-html**（含 `<br>` 的 Markdown 也會整段拒絕）；
  3. 除了 `MD_BLOCK_DOC` 之外沒有任何區塊 → `INVALID_ARGUMENT`。這條取代「掃不出任何文字」：原生 N1（只有 `---`）與 S14（空 alt 的 `data:` 圖片）會被舊規則誤拒，而 Writer 其實會貼上。
  
  三條都在派送前，都不動文件。md4c 版本：三棵核心樹都是 0.5.3，與 `download.lst` 指名的 tarball 逐位元組相同，沒有 patch（原生 T3）。
- **只在收合的游標上貼（新增）**：引擎在選取不是收合時拒絕（`MARKDOWN_NEEDS_CARET`，不派送），頁面的對話框在「插入」時若有選取，就提示「請先取消選取」。理由：跨兩個儲存格的選取上，原生把內容附加到每一格，第二格是原文加亂碼（**finding 148**）。單段與跨段的範圍原生雖然正常，但引擎分不出跨儲存格，收合是能封閉的規則。具名 **L-md-collapsed-only**。M4 的位置改成 P1、P3、P4、P8（儲存格中）、P9（空儲存格）、P10（頁首）；P6、P7、P11 改成拒絕臂。
- **M9（後置條件在 WASM 上的紅案）**：游標在受保護的區段裡貼上。原生是 `paste()` 回 true、沒有 Undo 動作、payload 逐位元組相同（3/3）。v21 上期望：`MUTATION_OUTCOME_UNKNOWN` → session 回到檢查點，文件不變。N=3、兩個瀏覽器、N/N。**若紅**：第 2 項頁面沒有入口。具名 **L-md-protected**：在受保護的內容裡貼上會觸發一次回復重開，不會掉資料。
- **finding 147（text input 欄位）**：在 `text:text-input` 欄位裡貼上，原生會弄亂文字，而且一次 Undo 還原不回來；**用 `text/plain` 貼（今天的 Ctrl+V）也一樣**。v21 不修（引擎看不出游標在欄位裡），具名 **L-md-input-field**，發佈說明與 Ctrl+V 一起列。WASM 上是否相同：未量，列在後續工作。

## 10. 審核 2 的處置（2026-10-16，只追加；最後一輪）

兩席：`handoff/link-batch-v21/review-2-{opus,codex}.md`。第一輪各項的判定：codex 26 項解決、7 項部分解決；opus 17 項解決、10 項部分解決；兩席都沒有「沒處置」的項目。部分解決的項目在本節收尾。擁有者對「Writer 處理不好的寫法」選 B（照貼，登錄成限制）。

### 10.1 派送前先存檢查點（opus B1、codex B1；兩席都列 BLOCKING）

- **取代** §9.4「走回到檢查點」與 §9.14 L-md-protected 的「不會掉資料」。前提錯了：session 在 `MUTATION_OUTCOME_UNKNOWN` 時只封住佇列（`editor-session.js:320-325`），回到檢查點是重開「比上次存檔新的檢查點，否則上次存檔」（`:163-167`），而貼上之前沒有人存檢查點。所以髒文件上會丟掉上次存檔之後打的字（finding 119 的形狀）。
- **處置**：`pasteMarkdown` 的佇列操作在派送前呼叫 `_checkpointBeforeBoundaryMove(document)`，乾淨或已存過時它什麼都不做。**檢查點存失敗就拒絕派送**（`MARKDOWN_CHECKPOINT_FAILED`，`dispatched: false`）——不能沿用會吞掉失敗的那個方法照樣派送（`editor-session.js:493`）。
- L-md-protected 改寫成：在受保護的內容裡貼上會觸發一次回復重開，內容回到貼上前那一刻（檢查點）。

### 10.2 「收合」的來源（opus A2、codex B2）

- 引擎在派送那一刻判定：`readSelection().type == NONE` 且不是 `textMissing`，且（從沒觀察過選取，或快取的選取矩形是空的）。其他一律 `MARKDOWN_NEEDS_CARET`。這與 C 用的條件同形（`probe_engine.cpp:4020-4023`）。
- 理由：只看快取，在剛開檔、還沒有任何選取回報時會一律拒絕；只看 `readSelection()`，只選了一張圖片的選取會讀成 NONE。

### 10.3 扣住的刪除按壓（opus A4、codex B3）

- **取代** §9.8 的「第一下尚未回答之後」。新規則：
  1. 一個刪除按壓被扣住，**若且唯若** session 最近一次入列的是一個還沒回答、同一個鍵的刪除。由 session 端的入列計數器讀：v2 session 的 `_enqueue` 是所有入列路徑的唯一入口（`narrow-editor-v2-session.js:1112`），所以打字、點擊、選取、undo／redo、存檔都算到。
  2. 被扣住的按壓屬於它所等的那一次送出，**逐筆記方向**，不再用共用欄位（`heldDeletes.action` 會被後來的送出覆寫，`e2-editor-app.js:2761`）。
  3. 那一次送出結算時：是站得住的邊界 no-op → 丟掉屬於它的按壓；否則依序放行。
  4. 有任何別的東西要入列、而還有被扣住的按壓時，**先把它們依序、照原方向放行，再讓新的東西入列**。代價：在文件邊界上被扣住的按壓（144 的深度規則限制在 2 個以內）各要再付一個 C 的窗，最多約 4.5 秒，具名 **L-hold-release-cost**。
- 144 的深度規則與 145 的無條件結算照舊。

### 10.4 其餘

- **NUL 與編碼（opus A1、codex S2）**：
  - 輸入含 0x00 → 拒絕（Writer 會剝掉尾端的 NUL，掃描不會，兩邊解析的位元組就不同了；opus 舉了一個「參照定義後面接 `\0`」會被抓網路的例子）；
  - 引擎讀 `osl_getThreadTextEncoding()`，不是 UTF-8 就拒絕（`MARKDOWN_ENCODING_UNSUPPORTED`）；
  - `md_parse` 回非零 → 拒絕。
  
  這三條都在派送前。
- **派送前拒絕的處置（opus A6、codex B2）**：所有派送前的拒絕碼都放進 `PRE_DISPATCH_CODES`（或帶 `dispatched: false`），讓 `recovery` 是 `none`。清單由 `markdown_paste.hpp` 產生並做單元測試，避免頁面對一份沒被動過的文件說「請回到檢查點」（finding 063 那一類）。
- **md4c 的接法（opus A5、codex N2）**：`-I…/UnpackedTarball/md4c/src` 只加在 v21 的規則；`#include <md4c.h>` 放在 `OXSDK_E2_V21_LINK_BATCH` 之內；`markdown_paste.hpp` 只當 v21 物件的前置檔。**絕不把 `md4c.c` 編進我們的引擎**，否則就是兩個解析器、不再封閉；`what_the_link_ships` 要斷言我們的物件裡沒有 md4c。
- **擁有者選 B 的兩項**：
  - **L-md-entities**：`&amp;`、`&lt;`、數字參照等實體被 Writer 丟掉（**finding 149**，原生已確認）；
  - **L-md-task-checkbox**：`- [ ]` 變成核取方塊內容控制項，點一下會在 Writer 裡切換並產生 Undo（`wrtsh3.cxx:135-160`），而產品的點擊是不改文件的 `placeCaret`，所以 `dirty` 與自動儲存可能看不到這個改動（推論）。加一個記錄臂，在 v21 上點一下貼進來的核取方塊，記下文件、revision、`dirty` 有沒有變。若改了而 `dirty` 沒變，另立 finding——開啟既有的 DOCX／ODT 裡的核取方塊也會有同一件事。
- **同時具名**：
  - **L-md-softbreak**：軟換行變成 U+00A0，與 L-md-merge 並列；
  - **L-md-no-html 擴寫**：任何在程式碼之外的 `<字>`（例如 `List<T>`）都算原始 HTML，整段拒絕，提示「請用反引號把它包起來」。
- **判準的預設、母數、取樣時點（codex S3–S6、opus C1–C7）**：全部在 §11 總表落定。

## 11. 定稿的判準總表（2026-10-16；取代第 5 節與 §9 中各判準的寫法）

這張表是實作與判讀唯一要看的判準清單。凡是 §5、§9、§10 寫法與這裡不同的，以這裡為準。

### 11.0 通則

- **兩個瀏覽器**（Chrome、Firefox）；**每一臂每個瀏覽器 N=3**，過＝N/N。標為「記錄」的臂沒有通過條件。
- **缺報、缺回、NE 一律等於「沒做」**，套用該條的預設。附帶臂（取消、記帳、拒絕臂）一樣適用。
- **證據的身分**：每份 D／M 報告都帶受測的 wasm、worker、頁面、殼層、輸入與參照的雜湊。與最終候選不符就作廢，等於沒做。
- **第 1 項沒出貨時**：頁面不綁 Ctrl+Home／End（範圍上也不攔，回到今天的行為）；SDK 仍能送 22／23，具名 **L-142-sdk-callable**。
- **第 2 項沒出貨時**：頁面沒有入口，具名 **L-md-sdk-callable**。

### 11.1 第 1 項：Ctrl+Home／End

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| D1 | `d1-marker/tool/d1_population.py` 產生的 38 臂：產品頁送同一串步驟，用產品的打字路徑打 `Z`，存成 ODT。`read_marker.py`（加上 ODT 轉接，先做跨容器相等、標記位移、重複標記、缺 XML 四個紅案）讀到的落點等於原生 | 工具封閉 | 第 1 項不出貨 |
| D2 | `press-after-ctrl-home`（宿主）：Backspace 以 `verified-boundary-noop` 完成，revision 不變，存檔文字不變。0.2.24 上照舊是紅的 | 逐實例 | 同上 |
| D2′ | 真鍵連送 Ctrl+Home、Backspace，不等待，起點是 `b2b-home-bksp-at-num` 的 fixture：第二段的編號與文字都不變。只在名目時序下成立，照 `CLAUDE.md`「有行為而沒有東西守著」登錄 | 逐實例 | 同上 |
| D3 | 由 D7 取代，保留為說明 | — | — |
| D4 | `r-*` 臂（含反向）：頁面走 `moveFromPoint` 再移動，標記落點等於原生 | 工具封閉（`r-*`） | 頁面在範圍上攔下按鍵、提示「範圍上尚不支援」，**不讓它落到輸入框** |
| D5 | 按鍵綁定表 ×（宣告缺席、扣住、只扣一個、宣告）的矩陣，用真的 v20 manifest：只有提供的動作才攔鍵；Shift 與 `isComposing` 一律不攔 | 工具封閉 | 最終殼層不得與 v20 搭配 |
| D6 | **記錄**：貼 64 KiB → Ctrl+End → 打標記，不等待；記完成種類與落點 | 記錄 | 未量，不做任何排序宣稱 |
| D7 | D1 母數的每一下：原生有游標回呼 → `documented-callback-*`；原生無聲 → `verified-move-readback`，< 500 ms；回覆裡的游標等於回覆後 **500±50 ms** 的單次 `editor-get-state` | 工具封閉 | 第 1 項不出貨 |
| D8 | 序列 a–e：(a) 開頭 Backspace → Ctrl+End → Backspace，結尾刪一字；(b) 開頭 Backspace → Ctrl+Home → 1 秒內 18 個無旗標的 Backspace，引擎收到的刪除 ≤ 2；(c) 開頭 Backspace → Ctrl+End → 兩下 Backspace，結尾刪兩字；(d) 開頭 Backspace → 點文件中間 → Backspace，刪在點擊處；(e) 文字中 Backspace、Backspace → Ctrl+End → Delete，前兩下刪在原處、Delete 在結尾是 no-op。(c)(d)(e) 先在 0.2.24 上做紅。141／144／145 的頁面測試全部重跑 | 逐實例 | 頁面保留今天的扣住規則，具名 **L-142-held-after-move** |
| D9 | 按住 Ctrl+Home、Ctrl+End 各 1 秒，帶旗標的重複與 30 ms 一下的無旗標按壓各一組：放開後 ≤ 500 ms 回到就緒（同鍵的移動尚未回答時，按下去就丟掉） | 逐實例 | 具名「按住時每個尚未回答的窗會排一個 250 ms 的移動」 |
| D10 | 60 頁 fixture 按 Ctrl+End：在回覆時讀一次、靜止 1 秒後再讀一次，兩次引擎游標都在可視區內、`#page-status` 都是最後一頁；外加 D7 的新鮮度條款 | 逐實例 | 第 1 項不出貨 |
| D11 | 記帳：唯讀文件按 Ctrl+End，游標動、`dirty` 不變；乾淨與髒文件依 096／098 斷言；經 SDK 送過時的 `expectedRevision`，照移動處理 | 逐實例 | 第 1 項不出貨 |
| D12 | SDK 在範圍上送 22／23 → `EDITOR_FORMAT_GESTURE_UNSUPPORTED`、文件不變。worker 在遮罩回傳非 OK 時初始化失敗（單元測試，注入非 OK） | 逐實例 | 第 1 項不出貨 |
| D13 | 封閉清單：每個 ABI 5 追加的動作恰好屬於一個後置條件類別；`BOUNDARY_CAPABLE_MOVES` 等於移動完成類別；未知動作被拒絕 | 形式二 | 第 1 項不出貨 |
| — | **記錄**：x-lc（Ctrl+Home 之後在有編號、項目符號、縮排的第一段按 Backspace）；表格裡 Ctrl+Home 再 Backspace（136 的儲存格邊界） | 記錄 | 列進發佈說明 |

### 11.2 第 2 項：貼上為 Markdown

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| M0 | 掃描模型測試：`markdown_paste.hpp` 以原生編譯的 md4c 0.5.3，跑兩輪原生語料加新語料（NUL、無效 UTF-8、`List<T>`、待辦清單、實體、解析失敗）。每一項的預期判定（PASS／REMOTE／HTML／NO_BLOCK／NUL／PARSE_FAIL）在實作前 commit。紅案：規則 1 改成分大小寫、拿掉規則 2、換回舊的「沒有文字」規則，各自都要紅 | 形式二 | 第 2 項不出貨 |
| M1 | M0 判 PASS 的每一項：在 v21 上經產品對話框貼到釘住的空文件開頭，正規化後的結構等於原生 | 工具封閉（依掃描判定分流） | 同上 |
| M2 | M8（中日韓）的存檔文字等於原生 `zh_TW.UTF-8` 的 | 逐實例 | 同上，另立 finding |
| M3 | 拒絕：M0 判非 PASS 的每一項，經對話框與直接 SDK 兩條路，回預期的碼，`dispatched: false`、`recovery: none`，revision、Undo、內容都不變。大小：SDK 在生效上限 L 與 L+1 各一臂；引擎直接在 65,536／65,537 各一臂（語料是重複的中日韓字元加明定的 ASCII 尾碼，附長度與雜湊）；斷言是哪一層拒絕的 | 工具封閉 | 同上 |
| M4 | 原生位置臂依規則分流：收合的游標 → 貼上之後一次 Undo 還原正規化結構（含原有格式）；範圍 → `MARKDOWN_NEEDS_CARET`；受保護 → M9 | 工具封閉 | 同上 |
| M5 | M3 裡 REMOTE 與 HTML 那幾項（含 NUL 尾碼的參照）：瀏覽器網路紀錄對目標主機 0 個請求。正向對照：同一份紀錄裡有 worker 抓 `probe.wasm` 的請求 | 工具封閉 | 同上 |
| M6 | 64 KiB 的決定性語料：頁面從忙碌到就緒 ≤ 10 秒，一次 Undo 還原，並記下 `CORE_LOG` 的數量。紅 → SDK 上限改 16 KiB 重跑；再紅 → 頁面沒有入口 | 逐實例 | 頁面沒有入口 |
| M7 | Ctrl+V 照舊：`ctrl-v-reaches-the-document` 恰好一個標記；C1 用 Ctrl+V 貼，結構等於原生 `text/plain` 的 | 逐實例 | v21 不出貨 |
| M8 | 宣告狀態 ×（頁面入口、SDK、直接對 worker）的矩陣：只有宣告了才可用 | 工具封閉 | 最終殼層不得與 v20 搭配 |
| M9 | 受保護區段（先確認游標確實在區段內）：乾淨文件 → `MUTATION_OUTCOME_UNKNOWN` → 回復之後文件不變；**髒文件**：打一個不存檔的標記，再到受保護區段貼上，回復之後存檔，標記要在（照 §9 的寫法這一臂會紅）；檢查點存失敗（注入）→ `MARKDOWN_CHECKPOINT_FAILED`，不派送 | 逐實例 | 頁面沒有入口 |
| M10 | 「收合」的來源：開檔後不點直接貼 → 接受；只選一張圖片 → 拒絕；選取一個外框 → 拒絕；跨儲存格的選取（select-range）→ 拒絕 | 逐實例 | 同上 |
| M11 | 記帳：貼上之後 `dirty` 為 true、自動儲存會觸發；對話框打字後取消 → 文件不變、沒有入列 | 逐實例 | 同上 |
| — | **記錄**：在 v21 上點一下貼進來的核取方塊，記文件、revision、`dirty` | 記錄 | 視結果另立 finding |

### 11.3 身分與計數

| # | 判準 | 若沒做或紅 |
|---|---|---|
| I1 | X1 對 v20 印 `VERDICT PASS`，差異**恰好**是：wasm／loader／worker 雜湊；`.editorContract.abiVersion` 4→5（changed-leaf）；兩個動作的六個新葉；`pasteMarkdown` 的宣告葉。匯出表多出 `_oxsdk_document_paste_markdown`。**凍結集合**：連結前後對 `wasm_sdk_probe/dist/profiles/` 與 `wasm_sdk_probe/build/archive/` 底下每一個檔算雜湊，除了 `dist/profiles/e2-editor-v21/` 之外全部相同。`ScDocShell` 0 次。M1-1：base A `5d77dc84`，載體 `E2_V15 E2_V19 E2_V20 E2_V21`；base B＝本節落地的那個 commit，載體 `E2_V21=probe_engine,sdk_api,editor_api`。`what_the_link_ships` 列不出 md4c 物件。E1-C `intact: true` | v21 不綁定 |
| X1-cl | X1 的 `--declared-changed-leaf PATH OLD NEW`：六個紅案（沒宣告的改變、宣告了卻沒變、OLD 錯、NEW 錯、葉不存在、型別不符）先紅 | 不得用來判 I1 |
| K | 計數鏈在最終位元組上成立（J-a.2）。§17.4 的人工讀法照舊，是承襲下來的具名限制 | 本批是未計數候選，名義出貨版本停在 0.2.24 |

釘選清單：`handoff/link-batch-v21/pin-list-grep.txt`（指令在檔頭；88 行、26 個檔）。實作要逐檔處理，或寫明為什麼不動。

## 12. 更正與追加（判準釘死之後，只追加）

### 12.1 派送前加一條：輸入必須是合法 UTF-8（2026-10-16）

依 `CLAUDE.md`「驗收判準的形式」§9 的四個條件追加：

1. **先於滿足**：寫在任何掃描程式碼存在之前，M0 fixture 也還沒 commit。
2. **被逼出來且指名**：實作 E 部的 fixture 項 X07（`![a][\xff]` ⏎⏎ `[\xfe]: http://…/x07.png`）。
   - 掃描器在原始位元組上看到 U+00FF 與 U+00FE，兩個標籤不同，所以沒有圖片，照 §11 判 PASS（以核心的 md4c 0.5.3 觀察）。
   - Writer 用 UTF-8 解碼，無效序列換成 U+FFFD（讀原始碼，`sal/textenc/converter.cxx:66-74`），兩個標籤相同，md4c 回報遠端圖片（以同一支解析器、在替換後的位元組上觀察）。
   - 這和 opus 第二輪 A1 的 NUL 是同一類（掃描與 Writer 解析的不是同一份位元組）。審核 2 說「拒絕 0x00 之後兩邊位元組就相同」，對無效 UTF-8 不成立。
3. **形式**：形式一。對每一個輸入都成立，規則由 RFC 3629 封閉：拒絕過長編碼、代理區、超過 U+10FFFF 的值、截斷的序列。
4. **截止**：§11 的判準在 v21 第一筆 WASM 執行之前全部適用。

規則：派送前，在 NUL 規則之後，輸入不是合法 UTF-8 → `INVALID_ARGUMENT`（M0 的判定標籤 `INVALID_UTF8`）。另外兩件同時定案：

- M0 的判定標籤加上 `TOO_LARGE`（M14b，262,262 位元組）。
- `PARSE_FAIL` 由模型測試裡的配置失敗注入產生（`md_parse` 只在配置失敗或回呼中止時回非零，`md4c.c:418-495`），只用在原生的模型測試。

JS 字串經 TextEncoder 一定是合法 UTF-8（孤立代理會被換成 U+FFFD），所以 X05–X07 與 `M8-utf16le.bin` 只能直接對引擎送。M3 把它們分到「直接對引擎」那一條路。

### 12.2 shakedown 臂的讀法（2026-10-16，任何 WASM 執行之前）

寫 shakedown 臂（`findings/evidence/link-batch-v21/shakedown/ARMS-item1.md`、`ARMS-item2.md`）時，有幾處 §11 的字面在出貨組態上沒有唯一讀法。下面每一條都指名是哪個事實逼出來的；臂檔裡的裁決表（item1 §8、item2 §9）是出處。**這些不新增判準，也不移動任何門檻**：(a)–(d) 決定某一格用哪條路、讀哪個欄位，(e)–(g) 寫明字面的讀法。

- **(a) 原始位元組那幾格的載體。**
  - 逼出來的事實：出貨的 worker 拒收非字串，字串一律經 `TextEncoder`（`sdk/sdk-worker.js:1484-1497`），所以沒有任何出貨訊息能把非法 UTF-8 送到引擎。但 §12.1 要求這幾項「直接對引擎送」。
  - 作法：載體是只放在 mirror 裡的檢測版 worker，多一個把 `ArrayBuffer` 原樣交給 `oxsdk_document_paste_markdown` 的訊息。
  - 這種報告的身分：綁 wasm，並寫出兩個 worker 的雜湊。
  - **只判引擎自己的回覆**：碼、`dispatched: false`、revision、內容。
  - X15–X17 依 §12.1 自己的規則（不能解成 UTF-8）一併列入。
  - 非出貨 worker 的報告另外只能帶兩種東西：記錄（`CORE_LOG` 數），以及 M10b／c 的「物件確實被選取」前提。**其他任何判準條款都不能從這種報告來。**
- **(b) X14 不在 M3 的 WASM 母數裡。** 它的非 PASS 判定只在原生模型測試的配置失敗注入下成立（§12.1 最後一條；fixture 的 `verdictWithoutInjection` 是 `PASS`）。在 WASM 上它是 PASS 的輸入。
- **(c) 剪貼簿帶不過去的輸入。** 對話框那條路，以「貼進對話框後讀回的長度與 sha256」為準。某一項在某個瀏覽器讀回不同時，該項在該瀏覽器只判直接 SDK 那條路，報告保留讀回值。產品本來就收不到這樣的文字。
- **(d) 範圍上的 `MARKDOWN_NEEDS_CARET`（M4、M10d）。**
  - 對話框那條路：頁面先以「請先取消選取」攔下，什麼都不送（`web/e2-editor-app.js:2352-2360`），這個碼永遠到不了對話框。
  - 所以碼在直接 SDK 那條路上讀；對話框那條路**另外**要求頁面自己的拒絕：沒有送出、文字留著。
- **(e) D10。**
  - 「在回覆時讀一次」＝頁面把移動標成完成之後的下一個 animation frame。在 worker 回覆的那一刻，頁面還沒套用它。
  - 「都是最後一頁」＝`#page-status` 的最後一頁等於引擎回的頁數。確切文字照記。
- **(f) D11「照移動處理」。** 讀法是：在引擎與 SDK 兩層，結果都和同樣帶過期 `expectedRevision` 的 `move-line-*` 相同；另有一個會變動文件的對照，要回 `STALE_REVISION`。
  - 理由：經 SDK 時，client 對任何帶過期 revision 的移動都會在引擎移動之後回錯（`narrow-editor-v2-client.js:344-347`）。這對 22／23 以外的移動一樣成立，不是本批的缺陷，記為觀察。
- **(g) D6「不等待」。** Markdown 對話框是 modal，貼上完成前不會關（`web/e2-editor-app.js:2358-2361`），按鍵到不了文件。所以 Ctrl+End 在對話框關閉的那一刻送出，那是按鍵最早能到文件的時候。D6 是記錄臂，沒有通過條件。

### 12.3 shakedown 之後的更正與追加（2026-10-17，fable 裁決 1，任何證據執行之前）

出處：`findings/evidence/link-batch-v21/shakedown/review/ruling-fable-1.md`。擁有者睡前授權 fable 代為裁決（「有疑義的地方可以發給fable，我授權它代我決策」）。這一節寫在任何樹上修改與任何證據執行之前。

- **(a) D8 (e) 紅的成因與修法（finding 150）。**
  - 成因：刪除在途時，頁面把 barrier 推來的一字選取當成使用者的範圍。Ctrl+End 因此走「先點再移」，中間按的 Delete 刪在點擊處。方向鍵的範圍路徑也一樣，0.2.24 就有。
  - 修法：把 finding 131 的規則 A（`deletesInFlight === 0`）寫成一個共用的純函式，兩條路徑都用它。
  - **D8 的判準不動，門檻不動。** D8 的預設（保留今天的扣住規則）處理的是 §10.3 的扣住改寫，不處理這個成因，所以採用預設也不會讓 (e) 變綠。
- **(b) 撤回 D11 對 22／23 的「髒文件存檢查點」條款（CLAUDE.md 判準形式 §4）。**
  - 被證偽的前提：22／23 在邊界上會永遠等不到回呼，所以需要 finding 096 的檢查點。
  - 實測：D7 的無聲按壓都以讀回在 250.6–251.2 ms 完成。
  - 這個檢查點正是 finding 151 的觸發：髒文件 V1／V2／V4 共 18/18 落在舊游標；拿掉後 18/18 正確。
  - 取代的讀法，只適用 22／23：髒文件按 Ctrl+Home／End，移動前**不送** `save`，`dirty` 維持 true，`#s-checkpoint` 是「無」。
  - 六個方向鍵照舊。D11 的預設照舊是「第 1 項不出貨」；若沒做＝第 1 項不出貨。
- **(c) 新判準 D14**，照 CLAUDE.md 判準形式 §9 的四個條件追加：
  1. 先於滿足：任何證據執行之前。
  2. 被逼出來且指名：finding 151，`diag-dirty-move/` V1／V2／V4。
  3. 形式一（逐實例）。
  4. 截止：第 1 項的證據執行一落地就封閉。
  - **判準**：plain3 與 long60 各自先在開頭打一個字（文件變髒），真鍵 Ctrl+End，30 ms 內真鍵打一個字，存檔後那個字落在**文件結尾**。N=3、兩個瀏覽器、N/N。
  - **若沒做或紅**：第 1 項不出貨。
  - 計數語意：還沒有任何證據執行，沒有計數可歸零。
- **(d) 更正 §9.1 對 L-142-readback-overtaken 頻率的說法。**
  - 它不是「核心偶爾停頓」。任何一次存檔之後（檢查點、工具列存檔；自動儲存是推論），緊接著送出的移動**每次**都以讀回、帶著舊游標完成。實測：存檔回覆後 2–9 ms 按，6/6；300 ms 以後按就正確，10/10；10–300 ms 之間沒量。類別不變。
  - 修法之後的殘餘：
    - (i) 存檔後不到 300 ms 就按 Ctrl+Home／End；
    - (ii) 改動後的**第一下方向鍵**：檢查點仍在，0.2.24 與 v21 都量到，各 6/6。它被計數中的 `a-boundary-arrow-press-does-not-cost-the-work` 釘著，拿掉要走 §34，留給「有序指令」那一批。
- **(e) 第 2 項不在 v21 出貨。**
  - 依據：M3 在已連結的引擎上紅（finding 153：引擎執行緒 64 KiB 的 stack 被一段長段落的排版撐破），套用 M3 的預設。
  - 殼層不提供入口：工具列按鈕與任何通往 `openMarkdownDialog` 的路，**不論 manifest 有沒有宣告**都不出現。具名 **L-md-sdk-callable**。
  - M8 在最終殼層上的頁面格，讀作「被殼層隱藏」；與 v20 搭配的規則不變。I1 的宣告差異中，`pasteMarkdown` 那一葉列在 L-md-sdk-callable 之下。
  - M7（Ctrl+V 照舊；預設「v21 不出貨」）照樣在證據執行裡跑，N=3、兩個瀏覽器。M1–M6、M9–M11 不跑，它們的預設已經採用。
  - finding 152 的修法（對話框關閉後重新聚焦）與 153 的修法（加大 stack，要重新連結），都跟著出第 2 項的那一批。它們的判準寫在各自的 finding 裡。

### 12.4 D7 在 Firefox：儀器校準與停止規則（2026-10-17，fable 裁決 2，A0 與重跑之前）

出處：`findings/evidence/link-batch-v21/shakedown/review/ruling-fable-2.md`（`7a5cc0e9`）。擁有者選擇把這題交給 fable（「D7 發給 fable」）。這一節寫在 A0 診斷與 Firefox D1 重跑之前。**D7 的判準文字、500±50 的窗、judge 都不動。**

- **(a) 逼出這一節的量測。**
  - Firefox D1 跑了兩次（`071208`、`092410`），各有 2／192、6／192 次讀取落在 550 ms 之後，最晚 560.3 ms。游標全部相等，576 次讀取沒有一次不等。
  - Chrome 的 192 次讀取都在 500.1–500.9 ms。
  - 成因是觀察器的 `setTimeout(500)` 在 Firefox 晚響，不是產品。忙碌區段的**結尾**落在 +543–560，**開頭**沒有量過。
- **(b) 先量（A0：診斷，不是證據）。**
  - 用同一支 runner、同一個 mirror。只改觀察器的**複本**：加三個不送請求的哨兵計時器（+440、+455、+470），並記下回覆之後每個 `paint`／`pageRectangles` 回覆的時間。真正的讀取仍在 +500。
  - Firefox，只跑 `t-*` 臂，N=3。
- **(c) 常數怎麼選（現在釘死）。**
  - A0 有鑑別力的條件：至少 3 下的 +500 讀取晚於 +520。
  - 有鑑別力時：
    - 每個 +470 哨兵都在回覆後 ≤ 540 ms → 常數 470；
    - 否則每個 +455 哨兵都 ≤ 540 → 455；
    - 否則沒有常數可用：預設成立，不重跑證據。
  - 沒有鑑別力時：常數 455，登錄為「前提未量，取最大餘裕」。
- **(d) 只改一個常數**：`wasm_sdk_probe/tools/v21_item1_observer.py` 的 `}, 500);`。runner 與 judge 都不動。
  - Chrome 的 D7、兩個瀏覽器的 D10 與 D11a，維持常數 500 的報告，不重跑：它們的讀取都落在窗內。
  - 每份報告用的是哪個常數，由 `pages.v21.snippetSha256[1]` 識別。
- **(e) 停止規則。** 只准重跑**一次** Firefox D1（38 臂、N=3）。judge 不改，以重跑報告上 D7 Firefox 那一行為準：
  1. **PASS** → D7 Firefox PASS。
  2. **任何一次讀取落在 [450, 550] 之外** → NE，套用預設：**第 1 項不在 v21 出貨**。
     - 不做第二次校準，也不跑第三次。
     - 殼層照 §11.0：頁面不綁 Ctrl+Home／End，具名 L-142-sdk-callable。v74 照這樣凍結。
     - 同一天開一張儀器極限的 finding。
     - v22 的任何證據執行之前，追加一節 §12 重寫 D7 的取樣條款。第 1 項跟 v22 一起走。
  3. **讀取全在窗內，NE 只來自外部 CPU（D-18）** → 准再跑一次，僅此一次，之後同樣適用本規則。
  4. **任何 FAIL**（游標不等、完成類別錯、無聲按壓 ≥ 500 ms）→ FAIL，開產品 finding，第 1 項不出貨，不重跑。
  5. **儀器無效**：窗內讀取的 `tPosted − rs.t` 中位數不在 [c, c+1.0]，或最小值 < c − 0.1（c 是新常數）→ 改動沒有到達受測頁面。該次作廢，查明原因後重跑一次，不計入本規則。
- **若這件事永遠沒做：第 1 項不出貨（§11.0 預設）。**
- **桌面條件**（A0 與重跑都適用）：
  - 在 browser lock 之下；
  - 桌面 Chrome 關閉；
  - 開始時 1 分鐘負載 < 1.5；
  - 沒有外部程序超過 50 %；
  - KWallet 沒有上鎖。
- 重跑的結果以追加的方式寫在本節末尾，不改上文。
- **結果（2026-10-17 12:10 追加）：走 (e) 1，D7 Firefox PASS。**
  - **A0**（11:21–11:32，桌面 Chrome 已關）：72 下的 +500 讀取都落在 500.1–501.5，沒有一下晚於 +520。依 (c) 屬於「沒有鑑別力」，常數取 455，登錄為「前提未量，取最大餘裕」（`303e6296`；紀錄在 `review/diag-d7-timer/`）。
  - **Firefox D1 重跑一次**（11:36–12:09，`evidence/item1/report-firefox-d1-20261017T113643.json`）：judge 沒有改，D7 Firefox PASS，整體 `VERDICT PASS (0 criterion cell(s) not PASS)`（`evidence/judge-item1-after-d7-rerun-2.txt`）。
  - **儀器生效檢查（(e) 5）**：192/192 都在窗內，中位數 455.2，最小 455.1。
  - **晚響仍在，只是變少**：晚 15 ms 以上的有 6 筆，最晚 +50.4 ms（t-home-A1-n2 r3 ch2）。常數若仍是 500，這一筆會落在 550.4。
  - 游標 192/192 相等；外部 CPU 超標 0 格。

### 12.5 finding 154：D2 在宿主 0.2.25 上 NE，修在宿主（0.2.26），D2 重跑一次（2026-10-17 追加）

出處：`findings/evidence/link-batch-v21/shakedown/review/ruling-fable-3.md`。擁有者把這題交給 fable（選項 D）。這一節寫在修法動手之前，也寫在任何瀏覽器啟動之前。**D2 的判準文字、judge、預設都不動。**

- **(a) 逼出這一節的量測。** D2 在宿主 0.2.25 上 6/6 NE（「no Backspace response」）：點第一行之後 40 秒內沒有定位游標，Ctrl+Home 與 Backspace 都沒有送出請求。成因是 finding 154：v21 頁面的 `<dialog id="markdown-dialog">` 關著，但 Nextcloud `core/css/server.css` 的 reset（`dialog { display: block }`）讓它一直顯示，蓋住點擊點（`TEXTAREA#markdown-text`）。同一頁只加一條 `#markdown-dialog:not([open]) { display: none }`，點擊點就回到 `CANVAS#canvas`，也會送出 `editorPlaceCaretV2`（兩個瀏覽器，`findings/evidence/154/`）。
- **(b) 修法（A，宿主那一側）。** 在 `templates/editor.php` 宿主自己的 `<style>`（放 production-UI 隱藏規則與 `#page-status[hidden]` 的那一段）加這一條：`#litecore-editor-root dialog:not([open]) { display: none; }`。不加 `!important`，`dialog[open]` 不加任何規則。版本升到 **0.2.26**，和規則放在同一個宿主 commit 裡。engine 封包、頁面、HTML、殼層一個位元組都不動：`engine/MANIFEST.json` 的 sha256 仍是 `54bebc4d…`，buildId 仍是 `f5f0df762e1855f2`，HTTP 送的位址不變。從改模板到 `ddev occ upgrade` 完成之間，不做任何量測。
- **(c) 修法的驗收（先紅後綠，診斷工具不改，sha `757c4476…`）。** 紅案是 0.2.25 上的兩次讀數，已 commit。在 0.2.26 上，兩個瀏覽器的 `asShipped` 都要讀到：
  - `dialog.open` false、`display` "none"、`box` [0,0,0,0]；
  - `rulesSettingDisplay` 裡有一條 inline 規則 `#litecore-editor-root dialog:not([open])` → none（這一條就是「改動生效」的讀數）；
  - 點擊點底下是 `CANVAS#canvas`，`insideDialog` false；
  - 送出 `editorPlaceCaretV2`，標籤出現「定位游標」；
  - 入口按鈕 `hidden`、`display: none`；
  - `hostIdentity.hostVersion` 是 0.2.26。

  任何一項不符就停手：不改工具，也不跑 D2。
- **(d) 宿主身分的釘子。** D2 的判準寫的是「宿主」，沒寫版號；§1 寫的是「0.2.25 起」。改工具前，先在 0.2.26 上跑 `run_v21_d2.py --identity-only --page v21`，結果必須恰好只有一條 `hostVersion` 不符。接著把 `HOST_EXPECT["v21"]["hostVersion"]` 從 0.2.25 改成 0.2.26，其他什麼都不改（對 `1fe9588d` 的 diff 只有一行）。改完 `--self-test` 要 19/19，`--identity-only` 要 v21 `[]`、0224 四個欄位都拒絕。這是跟著產品版本走的綁定，不是修理。
- **(e) 停止規則（D2 在宿主修好之後只准重跑這一次）。** Chrome N=3，然後 Firefox N=3。用同一個 judge，桌面條件同 §12.4。
  1. 6/6 PASS → D2 PASS。
  2. 任何一輪 FAIL → D2 FAIL，開產品 finding，第 1 項不出貨。不重跑，本批也不出 0.2.27。
  3. 任何一輪 NE → 第 1 項不出貨，v21 不出第三個宿主版本。例外只有兩種，各准該瀏覽器重跑一次：(i) 程式真的崩潰（報告有 `fatal` traceback）；(ii) 報告記下的外部原因（`preRun`、鎖的持有者、別的 ddev 專案讓 router 回 404）。`clickState` 為 null 又沒有外部原因的 NE，不算例外。
  4. 第 1 項若不出貨，就跟 v22 一起走；宿主那條規則保留。
- **(f) 預測（寫在跑之前；ARMS-item1 D2）。** 收到 `move-document-start` 的回覆。Backspace 以 `verified-boundary-noop` 完成，`waitedMs` 約 2,252–2,255，revision 0→0，存檔文字不變，正向對照有差異。
- **(g) 不重跑、不新增的東西。**
  - 0.2.24 的紅案照舊成立（README §5.8）：工具只差那一行，0.2.24 的 HTML 也沒有 `<dialog`。
  - 第 1 項的證據照舊成立：12 份報告的 `htmlSourceSha256` 都是 `1d158149…`，等於封包裡的 `e2-editor.html`。
  - 154 不新增 v21 判準。登錄兩個 v22 工作項：頁面那一側補 `#markdown-dialog:not([open])` 的規則，量對話框關著與打開兩種狀態；宿主 production-UI 臂加一份由 DOM 列舉、讀隱藏部件計算後 display 的檢查。另登錄兩行、不寫程式：NE 的原因沒有帶點擊點的酬載；`HOST_EXPECT` 沒有釘 buildId。
- **(h) §34.4：** 因執行而修 0、因審核而修 0（累計仍是 28／18）。`HOST_EXPECT` 的版號是綁定，診斷工具不是檢查，宿主規則是產品改動，都不計入。
- **若這件事永遠沒做：第 1 項不出貨（§11.0 預設）。**
- 結果以追加的方式寫在本節末尾，不改上文。

## 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-10-16 | 草稿（opus，主 session）：第 1、3（Markdown 除外）、4.1、4.3、4.4、5 的 D／C1／I1／K。Markdown（3.2、4.2、M 判準）待原生量測。 |
| 2026-10-16 | 補 Markdown（主 session）：3.2 寫入原生量測；4.2 定形狀（文件層匯出＋宣告閘控、送出前拒絕空白與超過 64 KiB、以 `.uno:Undo` 整份內容改變當後置條件、四個具名限制）；M1–M8；Q1 改成擁有者的入口選擇、加 Q4。 |
| 2026-10-16 | 4.2 加 L-md-137（貼上與打字同屬 finding 137 那一類；送審前主 session 自查補上）。 |
| 2026-10-16 | §9 審核 1 的處置（主 session）：引擎不是 unipoll 的更正與 L-142-readback-overtaken、D2′／D6–D10、Markdown 的出貨開關移到殼層、引擎用 md4c 先掃遠端圖片與空內容、後置條件的失敗語意走 MUTATION_OUTCOME_UNKNOWN、D1／M1 的母數由規則產生、跨層負向矩陣、X1 changed-leaf 的契約；OD1、OD3 與 Q1 待擁有者。 |
| 2026-10-16 | §9.13：擁有者三題都選 A（對話框入口；讀回期限照 250 ms；C 的宣告撤出 v21）。 |
| 2026-10-16 | §9.14：第二輪原生量測的處置——D1 母數更正（頁首臂排除）、預先掃描改成三條（圖片、原始 HTML、沒有區塊）、Markdown 只在收合的游標上貼（finding 148）、M9＝受保護區段、finding 147 具名。 |
| 2026-10-16 | §10 審核 2 的處置（最後一輪；檢查點、收合來源、逐次扣住、NUL／編碼、派送前碼、md4c 接法、擁有者選 B 的兩個具名限制）；§11 定稿判準總表，取代 §5 與 §9 中各判準的寫法。釘選清單 grep 產物 commit。 |
| 2026-10-16 | §11 I1 的 base B＝`523871fa`（§10／§11 落地的 commit）。從這裡起判準釘死；之後只准追加更正，不得移動。 |
| 2026-10-16 | §12.1：派送前加「必須是合法 UTF-8」（實作 E 部的 X07 逼出；照 CLAUDE.md 判準形式 §9 的四條件追加）；M0 的標籤加 `TOO_LARGE` 與 `INVALID_UTF8`；`PARSE_FAIL` 由注入產生。 |
| 2026-10-16 | §12.2：shakedown 臂的讀法（原始位元組格的載體與非出貨 worker 報告能帶什麼、X14 不進 WASM 母數、剪貼簿帶不過去的輸入、範圍上的碼在哪條路讀、D10／D11／D6 的字面讀法）；不新增判準、不移動門檻。 |
| 2026-10-17 | §12.3：shakedown 之後的更正與追加（fable 裁決 1，擁有者授權）：D8 (e) 的成因與修法、撤回 D11 對 22／23 的髒文件檢查點條款（§4）、新判準 D14（§9 四條件）、§9.1 頻率更正、第 2 項不在 v21 出貨（M3 紅，finding 153）。不移動任何既有門檻。 |
| 2026-10-17 | §12.4：D7 在 Firefox 的儀器校準與停止規則（fable 裁決 2，擁有者交裁）：先做 A0（哨兵計時器 +440／+455／+470，加上 paint 時間），常數依事先釘死的規則選 470、455 或不選；只改觀察器一個常數；Firefox D1 只准重跑一次，任何一次讀取落在窗外就讓第 1 項不在 v21 出貨。不動 D7 的文字、窗、judge。 |
| 2026-10-17 | §12.4 結果（追加）：A0 沒有鑑別力，常數取 455；Firefox D1 重跑一次，judge 沒改，D7 Firefox PASS，整體 VERDICT PASS。走 (e) 1。 |
| 2026-10-17 | §12.5：finding 154（宿主上關著的 Markdown 對話框被 Nextcloud 的 reset 顯示出來，D2 在 0.2.25 上 6/6 NE）；fable 裁決 3，擁有者交裁：修在宿主（0.2.26，一條 `dialog:not([open])` 規則，封包不動），先用診斷工具驗收，`HOST_EXPECT` 只改版號，D2 只准重跑一次。不動 D2 的文字、judge、預設。 |
