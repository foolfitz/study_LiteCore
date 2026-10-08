# SPEC M3：段落交界的 Delete／Backspace 交給 Writer 自己的鍵，用復原堆疊證明（選項 B，v15）

> 2026-10-06 立。只准追加（`CLAUDE.md` 第 10 節）：更正寫在後面並指名它取代什麼。
> 證據標記照 `doc-conventions`：**已觀察（原生）**＝原生 LibreOffice 量過、**讀原始碼**＝沒量、**推論**。
> **WASM 上什麼都還沒量。**本文件 commit 之前沒有任何引擎、worker、殼層、頁面、宿主的位元組為 B 改過；判準的滿足只能來自本文件
> commit 之後的執行。設計與判準的初稿寫在 `handoff/HANDOFF-2026-10-06f-…`；本文件取代那兩節，不同之處以本文件為準
> （差異列在第 9 節）。

## 1. 為什麼要有

- 擁有者 2026-10-06 要**真的併段**（不再只是 109 那種「拒絕＋保住內容＋重新載入」），只改 v8 這條線
  （`handoff/HANDOFF-2026-10-06d-…`）。之後在 A／B／C 三案中選 **B′**：先在原生量 B 可不可行，可行就做 B
  （`handoff/HANDOFF-2026-10-06e-…`）。
- **B**＝段落內的刪除照舊走 selection barrier；遇到交界，把單位選取退回去，按**使用者自己那一鍵**，再用 `.uno:Undo` 的
  payload 證明這一鍵做了什麼。結果就是 Writer 自己那一鍵的結果，不是我們重組出來的近似。
- 原生六輪的結論是**可行**（第 2 節）。本規格把它變成 v15：一次引擎連結＋worker＋殼層＋頁面＋宿主 0.2.8，以及 M3 的重新計數。

不在本輪：Enter／Tab 走 B、文件兩端的「沒有東西可刪」不重開、111（刪除插隊）、v14 拿到 B、主迴圈模型（第 8 節）。

## 2. 事實（全部來自 `findings/evidence/merge-native/README.md`，每一輪的預測都 commit 在該輪之前）

- **已觀察（原生）**，第四、六輪：B 的序列（單位選取 → 不按 Shift 的反方向鍵，至多兩下，第二下只在第一下沒回到原位時才按 →
  使用者那一鍵）在**每一個量過的段落交界、兩個方向**，存出來的 `content.xml` 與 Writer 自己那一鍵**逐位元組相同**，各 3/3：
  合成文件 19 個 case、擁有者文件 11 個 case（逐格列在 README「What rounds four to six say for B, together」）。
- **已觀察（原生）**，第六輪：下一段帶**可見標號**（編號標題、項目符號、編號項目）時，第一下左鍵只設定 Writer 的「在標號前」
  旗標（`SwCursorShell::LeftRight`，`crsrsh.cxx:326–380`，讀原始碼），第二下才回到原位；其餘交界一下就回來。
  **每一個還原步驟都改變了畫出的游標**（單位選取後的游標 → 第一步 → 第二步，沒有一步原地不動；第六輪全部 b 臂）。
- **已觀察（原生）**，第六輪 6b：在表格（C15、C16）兩下都回不來，探針接著按的鍵刪掉了儲存格裡的一個字——**還原不回來時引擎
  必須拒絕、什麼都不按**；6b 就是這個檢查的紅案。C17（儲存格尾）一下回來、鍵什麼都沒做；C29、C30（文件兩端）什麼都沒選到。
- **已觀察（原生）**，第四到六輪：復原堆疊的 payload 在**每一次** `content.xml` 有變時變、沒變時不變（交界批次 324 次、第五輪 72 次、
  第六輪 183 次，0 不一致）。只看 `.uno:UndoCount` 是錯的：到上限就不動（第五輪錯 36 次），上限以下也會因為段落內的刪除被併進前一個
  動作而錯（第四輪 15 次）——**B 只用在交界**，段落內連續刪同一個字從第 20 下起 payload 不再變（G10、G11）。
- **已觀察（原生）**，第五輪：上限（預設 100，`Common.xcs`，讀原始碼）時，最新幾個動作註解相同的話，payload 只在最新動作的
  `dateTime` 上變。**讀原始碼**：原生是奈秒，WASM 是 `Date.now()` 的整毫秒
  （`wasm-lite/tools/emsdk/upstream/emscripten/src/lib/libwasi.js:162–170`）。
- **讀原始碼**：今天的 barrier（`wasm_sdk_probe/src/probe_engine.cpp:3241–3560`）對含 `\r`、`\n`、`\t`、U+2028、U+2029、U+FFFC 的單位
  一律 `EDITOR_BOUNDARY_UNSUPPORTED`；250 ms 什麼都沒選到也是同一個代碼。它的 deadline 接在**兩個** engine loop 裡
  （阻塞式 `engineLoop`，`:5548`；主迴圈 `mainLoopDrainCommands`，`:5725`、`:5829`）。v8 不定義 `OXSDK_MAINLOOP_ENGINE`
  （`Makefile` 的 v8 規則），走阻塞式那一個。
- **讀原始碼**：worker 對產品操作只轉送 `formatBarrier`（完成 `sdk/sdk-worker.js:865`、錯誤 `:1072`），不轉送 `selectionBarrier`；
  殼層的刪除後置條件只收 `verified-selection-delete`（`editor-shell-v2/narrow-editor-v2-client.js:276`）；
  `recoveryFor` 把 `EDITOR_BOUNDARY_UNSUPPORTED` 對應到 `restart`、未知的代碼（含 `MUTATION_OUTCOME_UNKNOWN`）落到 `rollback`
  （`editor-shell-v2/paragraph-editor-session.js`）。頁面寫死 v8 的 worker（`web/e2-editor-app.js:1915`）與 wasm 釘選
  （`:49`），拒絕的 toast 寫「文件沒有被改動」（`:1019`）。
- **讀原始碼，本文件新增**：LOK 的游標回呼不帶「這是哪一下按鍵的結果」。`editorStateChanged` 只表示**解析成功**，不表示值變了
  （`probe_engine.cpp:2494`），同一個游標被重送一次也會讓 `sourceSequence` 前進。這是第 3.2 節「歸屬」那一條的來源。

## 3. 設計

### 3.1 引擎（新巨集 `OXSDK_MERGE_KEY_UNDO`，只有 v15 的物件檔定義）

1. 單位不含分隔符號 → 今天的 barrier（`verified-selection-delete`），一個位元組都不改。
2. **只有單位含段落／換行分隔符號（10、13、U+2028、U+2029）才進 B。**只含 `\t` 或 U+FFFC 的單位照舊拒絕
   （行內物件、定位字元沒量過）。表格的單位含分隔符號，會進 B，然後在還原那一步被拒（6b）。
3. 什麼都沒選到（250 ms）→ 照舊拒絕，錯誤多帶 `mergeKey{keyPosted:false, stage:"nothing-selected"}`，讓頁面能說「已在文件開頭／結尾」。
4. **單位游標**：進 B 之前要先看到單位選取**自己的**游標回呼（游標不等於放置時的游標）。沒看到就等，至多一個步驟上限
   （2000 ms）；逾時 → 拒絕，`stage:"unit-caret"`。
5. **還原**：反方向鍵、不按 Shift；**至多兩下**；第二下只在第一下的證據是「沒回來」時才按。判定用第 3.2 節的歸屬規則。
   回到原位＝游標矩形等於放置時的游標、型別化選取是收合的、`readSelection()` 是 NONE。沒回來 → `EDITOR_BOUNDARY_UNSUPPORTED`，
   要求重開，`mergeKey{keyPosted:false, stage:"restore", restorePresses}`。每一下的等待上限 2000 ms，逾時同樣拒絕。
6. 讀 `.uno:Undo` payload P0；讀不到 → 拒絕，`stage:"undo-read"`，`keyPosted:false`。
7. **時鐘守衛**：等到牆上時鐘的毫秒晚於讀 P0 的那一毫秒，才送鍵。理由（讀原始碼）：新動作的 `dateTime` 在送鍵之後才產生，
   而舊的最新動作在讀 P0 時已經存在，所以新的最新 `dateTime` 一定嚴格大於舊的——「同註解的新動作一定改變 payload」在 WASM 上
   從機率變成保證。兩邊讀的是同一個時鐘（`std::chrono::system_clock` → `Date.now()`），所以瀏覽器把時鐘降精度時守衛照樣成立，
   只是等得比較久（`clockWaitMs` 記下來）。
8. 送使用者的鍵（KEYINPUT＋KEYUP，charCode 0，鍵碼同原生探針）。之後每一個回呼都排一次**不可重入**的讀取步驟（合併），
   重讀 payload；**整份 payload** 與 P0 不同 → 完成 **`verified-key-undo`**，`changed:true`，修訂號＋1，帶
   `keyUndo{comment, actionsBefore, actionsAfter, restorePresses, keyToUndoMs, clockWaitMs, topDateTimeBefore, topDateTimeAfter, codePoints}`。
9. **送鍵之後的 deadline**（2000 ms）：到點時**再讀一次**；仍與 P0 相同 → `EDITOR_BOUNDARY_UNSUPPORTED`，
   `mergeKey{keyPosted:true, stage:"key-deadline"}`。**B 永遠不回報 `changed:false`**——晚到的鍵會讓那句話變成謊話（016 的形狀）。
   不用 `MUTATION_OUTCOME_UNKNOWN`：它落到 `rollback` → `recoverable-error` →「回到檢查點」開的是**較舊**的檢查點，會丟掉未存的打字
   （109 的形狀再來一次）。邊界代碼走的是 109 的修法：把**當下**的文件存成檢查點、重開——照實。
10. 編譯期守衛：`OXSDK_MERGE_KEY_UNDO` 與 `OXSDK_MAINLOOP_ENGINE` 同時定義、或沒有 `OXSDK_FINDING_016_SELECTION_BARRIER` → `#error`。
    B 的 deadline 只接進阻塞式 `engineLoop`；不支援的組合要在編譯時失敗，不是在使用者面前靜靜不等。
11. **純邏輯放進標頭檔** `src/merge_key_undo.hpp`（同 `format_readback_text.hpp` 的作法）：單位分類、還原證據的歸屬、payload 比較、
    最新動作的解析、時鐘守衛。引擎只負責把 LOK 的事件餵進去、照它的決定按鍵。這樣第 4.1 節的 M1-2 才能在本機用合成的回呼序列測。

### 3.2 還原證據的歸屬（本文件新增，交接初稿沒有）

交接把「Shift＋方向鍵的游標回呼晚到、被當成還原那一下的」列為**安全方向**的風險（多按一下 → 誤拒）。照順序推一遍，**它不安全**：

> 還原第一下送出 → 晚到的單位游標（不是原位）被當成第一下的證據 →「沒回來」→ 送第二下 → 第一下真正的結果（原位）這時才到，
> 被當成第二下的證據 →「回來了」→ 讀 P0、送鍵——而 LibreOffice 會先處理第二下，游標已經不在原位。鍵按在錯的地方，
> payload 照樣會變，回報 `verified-key-undo`。

所以規則是：**第 N 下的證據，只能是送出第 N 下之後、游標矩形與送出當時已知的游標不同的那一個回呼**（重送的同一個游標不算）；
第一下另外要看到選取收合。配合第 3.1 節第 4 條（還原之前已看過單位自己的游標），一個「變了」的游標只可能來自還沒被計入的那一下
按鍵——**前提是 LibreOffice 對一下按鍵只送一個游標結果、而且不會把較舊的游標排在較新的後面**。這個前提目前是**推論**：
原生第六輪每一步都改變了游標、沒有中間值，但原生探針每步之間有固定等待，看不到同一下按鍵的多個回呼。

**實作之前要做的事（寫進第 6 節順序）**：讀 LOK 的 `CallbackFlushHandler`（佇列與去重），在本文件追加段寫出順序論證並引用行號。
論證不成立時，改用「保證排在該按鍵之後」的柵欄（候選與其讀原始碼狀態一併追加），而不是加等待時間。

### 3.3 Worker、殼層、頁面

- **Worker**（`sdk/sdk-worker.js`）：產品操作的完成轉送 `keyUndo`，錯誤轉送 `mergeKey`（各自只轉白名單欄位，同 `productFormatBarrier`）。
- **殼層**（`editor-shell-v2/narrow-editor-v2-client.js`）：`DELETE_ACTIONS` 另收 `verified-key-undo`，條件：`changed === true`、
  修訂號＝前＋1、`keyUndo.comment` 是非空字串。→ 新殼層 generation（v56）。E1-C 綁定的五個檔案一個都不碰。
- **頁面**（`web/e2-editor-app.js`）：`workerUrl` **與** `PINNED_WASM_SHA256` 一起改到 v15（同 v8 cutover，兩行一起）——所以頁面
  commit 跟在連結之後；`mergeKey.keyPosted` 為真時**不得**顯示「文件沒有被改動」；剩下的拒絕（文件兩端、表格、行內物件）的措辭
  不再說「不能在段落交界刪除」。

### 3.4 考慮過、不採用

- **用註解白名單當執行期守衛**（6b 的錯位鍵產生 `Delete “o”` 這種字元刪除註解）：手工枚舉（第 1 節形式三），而且守衛跳了之後
  沒有比「回報成功、讓使用者自己按復原」更好的出路——拒絕＋重開會連復原堆疊一起丟掉。歸屬問題在來源處理（3.2）。
- **把單位大小設上限**：B 的安全不靠單位長得怎樣，靠還原檢查與 payload 證明；表格的單位很大，正是要被還原檢查擋下的那一種。

## 4. 判準

形式欄照 `CLAUDE.md` 第 1 節：逐實例／工具封閉／一次量測（登錄）。數字（2000 ms、1000 ms、3/3、105）在第一次**計數**執行之前
只能以追加段修改，而且要寫出是哪一次開發量測逼出來的。

### 4.1 連結之前（靜態與本機）

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **M1-1** | B 只在 v15：Makefile 裡每一組編譯 `probe_engine.cpp` 的旗標（由工具從 Makefile 取出，不手列），B 的 commit 前後的前處理輸出逐位元組相同，只有 v15 不同。紅案：在一份旗標副本裡給 v8 加上 `-DOXSDK_MERGE_KEY_UNDO` → 紅 | 工具封閉 | 不得宣稱「v8／v14 不受 B 影響」，v14 之後若重連要逐行重讀 |
| **M1-2** | `merge_key_undo.hpp` 的本機單元測試，至少涵蓋：單位分類（10／13／U+2028／U+2029 進 B；只有 `\t`、U+FFFC 不進）；還原的五種回呼序列——一下回來、兩下回來、兩下都沒回來、**單位游標在第一下之後重送**、**第一步的游標在第二下之後重送**；payload 只差 `dateTime`；時鐘守衛的邊界（同一毫秒不放行）。**每一個「送鍵」的決定，都要在測試的模型裡滿足「已送出的每一下都已看到它自己的結果、最後一下是原位」**。紅案：把歸屬規則換成「送出之後的第一個游標回呼」→ 重送那兩條序列紅；把 payload 比較換成只比數量 → 上限那條紅 | 逐實例（每條序列） | 3.2 的歸屬只算推論，v15 不得連結 |
| **M1-3** | 殼層單元測試：`verified-key-undo` 只在三個條件都成立時被收；三個條件各一條紅案（拿掉一個條件 → 對應測試紅）；`verified-selection-delete` 的既有測試不變 | 逐實例（每個條件） | 殼層 v56 不得凍結 |
| **M1-4** | Worker 測試（假引擎事件）：產品操作的完成帶 `keyUndo`、錯誤帶 `mergeKey`；白名單外的欄位不轉送。紅案：拿掉轉送那一行 → 紅 | 逐實例 | 頁面不得依 `mergeKey` 改措辭（它拿不到） |
| **M1-5** | 頁面措辭的單元測試：`mergeKey.keyPosted === true` 的錯誤**永遠**不產生「沒有被改動」的字樣；`stage:"nothing-selected"` 產生文件兩端的說法。紅案：把判斷拿掉 → 紅 | 逐實例 | 頁面不得移到 v15 |

### 4.2 原生參考輪 R0（連結之前，WASM 量測的對照）

- **輸入**：WASM 會載入的**同一份 `.odt` 位元組**——合成 `.fodt` 用原生轉一次成 `.odt`，sha256 記進 R0 的預測檔；擁有者那份
  `PMPC指南.odt` 原檔（不進 repo，sha256 記下）。
- **母體**：第四、六輪用過的交界 case 檔（R0 的預測檔逐一列檔名，**在 R0 執行之前**）。這是手工母體，所以本規格對 B 的宣稱只到
  「這些形狀」為止（形式三，登錄於第 8 節）；母體到 WASM 清單的對應則是工具封閉的（下一點）。
- **分類由工具從 R0 的輸出產生**（`MERGE_RESTORE_PRESSES=2`、PRESSES=1、3 輪）：b 臂＝鍵臂 3/3 → M2-1；還原回不來 → M2-3a；
  回來了但鍵沒動 → M2-3b；什麼都沒選到 → M2-3c。**任何一個 case 的 b 臂≠鍵臂，整個流程停下來**，不是把它從清單拿掉。
- R0 的工具、預測先 commit，才跑。

### 4.3 WASM（連結之後；獨立頁面＋假宿主，Chrome 與 Firefox，真鍵：Chrome＝CDP `Input.dispatchKeyEvent`、Firefox＝WebDriver actions）

放游標的方法由 runner 決定、記進報告；併段的 case 用不著另外驗放置——放錯交界存出來的文件就不同，是紅不是綠。
runner 在按刪除鍵之前要等輸入轉接器清空（避開 111，那不是本輪要量的東西）。

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **M2-0** | 對照先跑：每一份輸入不做任何編輯、載入＋存檔，WASM 的 `content.xml` 等於原生的。不等時，只能**從那份差異**推出一個化約並以追加段寫進本文件，而且在任何計數執行之前 | 一次量測（每份輸入） | M2-1 的「等於原生」無從比較，M2-1 不得開跑 |
| **M2-1** | 工具從 R0 產生的每一個 M2-1 case，每個瀏覽器 **3/3**：完成是 `verified-key-undo`；`keyUndo.comment` 等於原生的；`restorePresses` 等於 R0 的；**沒有重開**（世代不變）；存出來的 `content.xml`（化約後）等於原生鍵臂的 | 工具封閉（清單由 R0 產生）＋逐實例 | v15 不可出貨；產品維持 109 的「拒絕＋保住＋重開」 |
| **M2-1 紅案** | 同一支 runner 對 v8 跑，每個瀏覽器三個 case（R0 清單的前三個），必須紅（拒絕＋重開，不是 `verified-key-undo`） | 先紅一次 | runner 不得用來宣告 M2-1 |
| **M2-2** | M2-1 所有完成裡，`keyToUndoMs` 的最大值 < 1000 ms（deadline 的一半）；每一下還原的等待也都 < 1000 ms | 逐實例（每個完成） | deadline 不得宣稱有餘裕；key-deadline 的拒絕可能是慢而不是沒動 |
| **M2-3** | 拒絕照實（每個瀏覽器各 3/3）：**a** 還原回不來（C15、C16 型）→ `stage:"restore"`、`keyPosted:false`；**b** 鍵沒動（C17 型）→ `stage:"key-deadline"`、`keyPosted:true`；**c** 什麼都沒選到（C29、C30 型）→ `stage:"nothing-selected"`。每一臂先打一個標記不存：重開之後標記還在（109 的保證）；`keyPosted:true` 的那一臂 toast **沒有**「沒有被改動」 | 工具封閉（清單由 R0 產生）＋逐實例 | B 的拒絕路徑不得宣稱照實；v15 不可出貨 |
| **M2-4** | 復原上限：同一份文件經頁面連續 ≥105 次同註解的併段（H02 型，fixture 新增），每一次都是 `verified-key-undo`；`actionsAfter` 確實到 100（非空洞）；`topDateTimeAfter` 每一次都嚴格大於前一次 | 一次量測（每個瀏覽器一輪） | 「到上限仍可靠」只在原生成立 |
| **M2-5** | 產品路徑回歸網 v15 對 v8 逐格相同（含 PASS／NE 的分佈） | 既有協定 | v15 帶著的另外 20 個 hunk（082、096 等）不得宣稱無副作用 |

### 4.4 重新計數 R

- 宿主 0.2.8 打包 v15＋新頁面；六支 M3 runner 改綁新頁面並重新計數全過、紅案全紅；產品路徑網照 M2-5；`make test-e2-c-static` 結束碼 0。
- `check_m3_production_ui.py` 的 B-del／B-bs（標題尾、段首）在 v15 上**不再是拒絕**：改成宿主上的併段臂（`verified-key-undo`、沒重開、
  標記在伺服器上），109 的拒絕臂移到文件開頭的 Backspace（C29 型，250 ms 拒絕）。PMPC 上的 Delete 拒絕臂要先在原生量過才能選
  （文件結尾，或受保護的目錄項目——後者需要 TSV 能放定位字元）。這個改綁以追加段寫進 `SPEC-M3-production-ui.md`，在計數之前。
- 從來沒做時：0.2.8 不得稱為已計數；既有判定只綁 0.2.7。

## 5. 預測（寫在任何執行之前）

- R0：在 `.odt` 輸入上重現第四、六輪——每一個交界 case 的 b 臂＝鍵臂、還原下數與第六輪相同；表格兩下回不來；C17 鍵沒動；兩端沒選到。
- M2-0：合成文件相同；擁有者文件**可能**有差（WASM 核心的設定較少），若有，差異落在自動樣式或字型宣告，不在段落結構。
- M2-1：全部過；`restorePresses` 與原生相同（標號的「在標號前」旗標是 core 的邏輯，與平台無關）。
- M2-2：`keyToUndoMs` Chrome < 300 ms、Firefox < 600 ms；整個 B 的完成 150–800 ms（今天段中的 Backspace 約 95 ms）。
- M2-3：照第 2 節的原生結果；C17 型每次都要等滿 2000 ms 才拒絕（已知代價，第 8 節）。
- M2-4：`clockWaitMs` 幾乎都是 0（每一下之間遠超過 1 ms）；守衛在這裡證明不了什麼，只證明它跑了——它的正確性靠 M1-2。
- M2-5：逐格相同（網裡沒有格踩到交界）。

## 6. 順序

1. 本文件 → **opus 對抗性審核**（打判準與 3.2 的論證，不打結論）；`codex exec -s read-only` 做第二席（本 session codex MCP 連不上）。
2. 讀 `CallbackFlushHandler`，3.2 的順序論證以追加段寫進本文件；不成立就換柵欄。
3. R0：工具＋預測先 commit，跑，分類。
4. 引擎標頭＋M1-2；引擎、worker、殼層、頁面＋M1-1、M1-3～M1-5 與紅案。`RUNBOOK-relink-v15`（v8 的規則複製＋新巨集）；
   **先確認 `c41e8582` 是 v8 的連結 commit**（交接記為推論）；`what_the_link_ships.py --since <確認後的 commit>` 的結果寫進手冊。
   擁有者連結（先 archive）。
5. WASM 開發 shakedown（不算數）→ 必要的數字修改以追加段寫入 → 綁定 → 計數執行 M2-0～M2-5 → 宿主 0.2.8 → R。

## 7. 綁定（任何計數執行之前寫進 runner 常數）

v15 的 wasm sha256、worker sha256、殼層 generation v56 的 session sha、頁面 `e2-editor-app.js` 的 sha、R0 的報告目錄與輸入 sha256。

## 8. 登錄（不在本輪）

- **B 的「等於 Writer」只在量過的形狀上有證據**（第 4.2 節的母體）。沒量過：巢狀清單、追蹤修訂、欄位、註腳、從右到左、圖片標號、
  區段邊界、分頁、隱藏文字、零寬度的欄位或錨點——後幾種可能讓**不同的邏輯位置畫出同一個游標**，還原檢查會被騙過。
  B 的**安全性**不靠形狀清單（還原檢查＋payload 證明），但「結果等於使用者在原位按那一鍵」靠游標矩形相等代表同一個位置。
- 游標已經在標號前（使用者在項目開頭先按了左鍵）：原生探針支援負的 `offset`，但 TSV 把放置邊與鍵綁在一起，沒量。
- Enter、Tab／Shift+Tab 走 B：各自一輪量測。
- 文件兩端仍是拒絕＋重開（現在是最常見的剩餘拒絕），可以改成在 session 層回報「沒有東西可刪」、不重開。
- C17 型（儲存格尾的 Delete）每次等滿 2000 ms 才拒絕＋重開：比今天的立即拒絕慢，但照實。
- 牆上時鐘往回撥（NTP）落在 P0 與送鍵之間：同註解的併段可能看不出來 → key-deadline 拒絕（安全方向：存當下、重開，不會謊報成功）。
- v14 沒有 B；a11y cutover 若恢復，合併能力會比 v15 退一步。
- 受保護目錄項目上 barrier 的證明在什麼都沒變時也成立（finding 候選，只有第一次嘗試）。
- 111（刪除插隊）未修；B 讓交界的刪除變慢，被插隊的窗口推論會變大，量 111 時一併看。
- **效能與主迴圈模型**：沒有任何量測，從來沒登錄過——在此登錄。021 的 `e2-mainloop-attribution` 只量了狀態新鮮度；換模型屬重構，B 不需要它。
- 復原（↶）一個 B 的併段之後文件回到原狀：原生量過（第 E 輪 54/54），WASM 沒有列為判準。

## 9. 與交接初稿的差異

- 新增 3.1 第 4 條（還原前先看到單位自己的游標）、3.2（歸屬）、3.1 第 10 條（編譯期守衛）、3.1 第 11 條與 M1-2（純邏輯標頭與本機測試）、
  M1-4（worker 轉送）。
- 交接說晚到的單位游標是「安全方向」——改判為**不安全**（3.2）。
- deadline 到點時再讀一次 payload 才決定（交接只說「到點且沒變就拒絕」）。

## 10. 追加（2026-10-06，opus 與 codex 兩席對抗性審核之後、任何程式碼之前）

審核題目：`handoff/tasks/REVIEW-2026-10-06-paragraph-merge-spec.md`。兩席都打判準與論證、不打「要不要做 B」。每一條在採用之前，
主 session 都讀了它引用的原始碼；「已核對」＝主 session 讀過，「審核者讀」＝只有審核者讀過、主 session 沒有重讀。
以下**取代**前文對應的條目；前文原樣保留。

### 10.1 設計更正

**(a) 3.2 的歸屬規則整條取代（opus #1、#2；codex B）。**前文的規則有兩個反例，兩個都會把鍵按在錯的地方並回報成功：

- **過期的 P**（已核對）：`handleInsertText` 呼叫 `paste()` 之後**立刻**回報完成（`probe_engine.cpp:3118–3155`），而那次貼上的游標
  只是立旗標，真正的回呼要等一個排隊中的 flush（`init.cxx:2578–2582` 用 `PostUserEvent` 排 flush；`viscrs.cxx:238–248` 只記矩形、
  立旗標）。「打一個字、立刻按 Delete 併段」時，交易開始時 `gEditorState` 裡的游標是打字**之前**的。第一下還原回到真正的位置（≠ 過期的 P）
  →「沒回來」→ 第二下剛好落在過期的 P →「回來了」→ Delete 刪掉剛打的字，payload 變了，回報 `verified-key-undo`。
- **未經請求的游標**（已核對形狀）：閒置排版會對每個游標 shell 做 `SttCursorMove`／`EndCursorMove`（`layact.cxx:2498–2530`），
  矩形若被排版移動就送出一個不同的游標。它若在第一下的 flush 之前到，前文的規則就把它當成第一下的證據。

取代為（判定一律在 **LOK 執行緒處理回呼的當下**做，`handleSelectionBarrierStateCallback` 本來就在那裡；交給引擎執行緒時在
`gState.mutex` 之下——也一併解掉 opus F3 指出的「`gEditorState` 跨執行緒無鎖讀」）：

- **P**＝單位那個非空 `TEXT_SELECTION` 送達之前、**最後一個送達的游標**，不是交易開始時的快照。
- **U**＝那個 `TEXT_SELECTION` 之後第一個送達的游標（前文 3.1 第 4 條的「單位自己的游標」）。
- **第一下的證據**＝**收合回呼之後**第一個送達的游標；收合之前到的游標一律不算（那時選取還在，未經請求的游標就在這裡被擋掉）。
- **第二下的證據**＝送出第二下之後、第一個與已知游標不同的游標。未經請求的游標在這裡只會造成誤拒；唯一的例外是剛好落在 P 的矩形，
  屬於第 8 節已登錄的「同矩形、不同邏輯位置」那一類。
- **insert 的退路**：`paste()` 失敗時改送字元鍵（`probe_engine.cpp:3126–3139`）且**同樣立刻回報完成**；那些字元鍵可能和 Shift＋方向鍵
  落在同一次 flush，P 仍會過期。最近一次 insert 走了退路時，B 拒絕（`keyPosted:false`，`stage:"insert-fallback"`）。

這條規則依賴的前提，明寫：

| 前提 | 狀態 |
| --- | --- |
| P1 鍵事件與 flush 都是 VCL user event，在 LOK 那條執行緒上 FIFO 處理 | 已核對：`init.cxx:2578–2582`；鍵 → `lokhelper.cxx:1286–1290`（v8 非 unipoll） |
| P2 游標 payload 在 flush **當下**才取（`m_aLastLOKRect`），一次 flush 至多一個、而且是當下的游標；與上次送出的相同就不送 | 已核對：`viscrs.cxx:243–248`、`:280–290`；`init.cxx:2448–2462`；去重 `init.cxx:1591–1594`、`:2525–2537` |
| P3 同一次 flush 內選取在游標之前 | 已核對：`init.cxx:2395–2412`（選取類先處理）；opus 另指出 `SwShellCursor::Show` 走一般佇列，同樣排在 flush 時才附加的游標之前（審核者讀） |
| P4 **一下方向鍵的處理過程中不會跑 flush**（不 Yield／Reschedule） | **未核對**。不成立時，第一下內部的中間游標可以在收合之後送達（codex 的 I→P 序列），規則會被騙。**實作之前要讀完 Writer 方向鍵的 KeyInput 路徑**；讀不完或不成立，改用柵欄，不加等待時間 |

**(b) 時鐘守衛撤銷（取代 3.1 第 7 條；opus #8、codex F1、codex C、opus C）。**理由（讀原始碼，`undo.cxx:1310–1335`）：payload 列出每個動作的
`index`（依位置）、`comment`、`viewId`、`dateTime`。未到上限時，新動作讓清單變長，payload 一定變；到上限時，最舊的被丟掉、整串往後移一格，
新舊清單相等**必須整條 100 筆動作的註解與時間戳全部相同**——一百次同註解的動作落在同一個時鐘刻度內，人的速度做不到（就算瀏覽器把時鐘
降到 100 ms 的精度）。守衛維持的是一個比需要更強的宣稱（「新的最新 `dateTime` 嚴格較大」），兩席各自把它打穿（兩個 Worker 各自的
`Date.now()`、本地時間經快取 6 分鐘的 UTC 偏移、DST、時鐘往回撥），而且帶進一個**沒有上限的等待**——等過 SDK 的 30 秒就是 `TIMEOUT` →
rollback → 丟資料。照 `CLAUDE.md` 第 4 節：撤回宣稱，不造機械去維持它。`keyUndo` 拿掉 `clockWaitMs`、`topDateTimeBefore`、`topDateTimeAfter`。

**(c) 就地修改的動作（codex C，已核對）。**段落合併跨兩個節點，`SwUndoDelete::CanGrouping` 一律不併（`undel.cxx:530–545`）。**手動換行不同**：
它是同一個節點裡的一個字元，可以被併進前一個 `SwUndoDelete`（`DocumentContentOperationsManager.cxx:4648–4663`；條件 `undel.cxx:536–570`），
只改註解、不產生新動作、不改 `dateTime`。註解變了 payload 就變；但註解經 `ShortenString` 只留頭尾（`undobj.cxx:1630–1645`），可能兩次相同
→ 文件變了、payload 沒變 → key-deadline 拒絕。方向是**誤拒**，前提是 (d) 的承諾成立。R0 加一個 case 去量它（10.3）。

**(d) key-deadline 的承諾改寫（取代 3.1 第 9 條的「把當下的文件存成檢查點」；codex D BLOCKING、opus D）。**核對結果（已核對）：
`_checkpointBeforeSelection` 在乾淨、或戳記與檢查點相同時直接返回（`editor-session.js:472–474`），而戳記只在**成功**的 mutation 之後前進
（`editor-session.js:299–310`）。所以 `keyPosted:true` 被拒時：乾淨或同戳記 → 重開的是**送鍵之前**的內容；有新戳記的未存修改 → 存的是引擎
**當下**的內容，可能含、也可能不含那一鍵。**兩種情形打過的字都不會掉**；不確定的只有那一鍵自己的效果。codex 提的「強制再存一次」給不出確定
的答案（晚到的鍵可能落在存檔之後），所以不加這個機械。承諾改成：**打過的字保住；那一鍵有沒有生效不確定，頁面照實這麼說**（「這一鍵送出了，
但沒能確認它做了什麼；已重新載入，請看一下那個位置」之類）。另外：

- 引擎在 `keyPosted:true` 時的訊息**不得**含 `no mutation was dispatched`（`finishSelectionBarrierError` 在要求重開時會自動加上，
  `probe_engine.cpp:3256–3266`，已核對）。
- **送鍵之後的每一個出口**（排程失敗、步驟裡的例外、讀 payload 失敗）都要是 `EDITOR_BOUNDARY_UNSUPPORTED`＋`keyPosted:true`；今天的
  `EDITOR_STATE_UNAVAILABLE`（`:3349–3356`）會落到 rollback（opus D-4）。
- `narrow-editor-v2-session.js:380–384` 註解的前提（「每一個拒絕都在派送之前」）在 v15 不再成立，要改寫。

**(e) 殼層的第三個條件撤銷（opus #5，已核對）。**`keyUndo.comment` 非空這一條，失敗時是 `EDITOR_RESULT_INVALID`，在 `RECOVERY_ERRORS` 裡
（`editor-session.js:14–21`），落到 rollback——而那一刻文件**已經**被改了。這正是 3.4 拒絕的「註解白名單」，出口還更差。改成結構檢查：
`keyUndo` 是物件、`actionsAfter` 是 ≥ 1 的整數。

**(f) 還原沒有改到文件（opus F4）。**交易開始時另讀一次 payload（P_start），送鍵之前要求 P_start＝P0；不等 → 拒絕，`keyPosted:false`，
`stage:"restore-mutated"`。這讓「還原的方向鍵什麼都沒改」對每一次執行都成立，代價是一次 LOK 呼叫。

**(g) BUSY 重繪（opus #12，已核對）。**barrier 進行中每個命令都回 BUSY（`probe_engine.cpp:5376–5383`），頁面的重繪只重試 6 次 × 120 ms
就跳「重繪失敗」（`e2-editor-app.js:795`、`:853–862`）。B 的窗口最長約 8 秒（單位游標 2000＋還原 2×2000＋鍵 2000）。頁面的 BUSY 重試要涵蓋
B 的最壞情形；判準見 M2-1、M2-3。

**(h) 措辭（codex F3、opus #7、codex M1-4，已核對）。**`nothing-selected` 證明不了在文件兩端（250 ms 讀到 NONE 也可能是 Shift＋方向鍵還沒被處理），
改說「這一下沒有取得可刪除的內容」。`reopenAfterBoundaryRefusal()` 目前不收錯誤（`e2-editor-app.js:1165`），四處 toast 都接 `BOUNDARY_TEXT`
（`:1032`、`:1037`、`:1041`、`:1066`），要把錯誤一路傳進去。SDK 把遠端錯誤的欄位放在 `error.details`（`document-sdk.js:70–79`），頁面讀
`error.details.mergeKey`。

**(i) 範圍補述（opus E，審核者讀，未核對）。**向前的單位旁邊有字元錨定或段落內錨定的物件時，`readSelection()` 回 `LOK_SELTYPE_COMPLEX`
（`swdtflvr.cxx:440–470`），B 看不到文字，照舊拒絕；向後的單位沒有這個檢查。安全，但要寫進範圍。

### 10.2 判準更正

| 判準 | 更正 |
| --- | --- |
| **M1-1** | 母體改成**每個 profile 規則的每一個翻譯單元**（產品連結四個：`sdk_api`、`probe_engine`、`unoembind_stub`、`editor_api`），`$(EXTRA_DEFINES)` 展開為空；工具找不到 v8、v14、v15 三條規則時自己紅（非空洞）。另加：`OXSDK_MERGE_KEY_UNDO` 配 `OXSDK_MAINLOOP_ENGINE`、或缺 `OXSDK_FINDING_016_SELECTION_BARRIER`，前處理必須失敗（3.1 第 10 條那個守衛的紅案）。宣稱縮限為「引擎翻譯單元」；worker 是共用的，B 對它的改動是附加的轉送（第 8 節） |
| **M1-2** | 序列改由**工具從事件模型產生**，不手列：每一下一次 flush、順序 [選取, 游標]；交易開始之前的游標在開始之後才送達；每個位置 0–1 個矩形不同的未經請求游標；只有旁欄不同的重送；insert 退路。至多兩下，約數百條。斷言：每一個「送鍵」的決定，在模型裡都滿足「已送出的每一下都已看到它自己的結果、最後一下的結果是 P、P 是 LOK 實際的起點」。紅案：前文的規則（「第一個不同的游標」）、交易開始快照當 P——兩個都要在產生出來的序列裡找得到反例。模型另有一個開關「一下按鍵的處理中跑 flush」（P4 不成立）：開著時**預期**找得到反例，用來證明規則確實依賴 P4。另加：送鍵之後的每一個出口都產生 `EDITOR_BOUNDARY_UNSUPPORTED`＋`keyPosted:true`。形式改為**工具封閉（對模型）**；模型對 LOK 的忠實度＝10.1(a) 的前提表 |
| **M1-3** | 經公開的 `action()` 測，母體由 `DELETE_ACTIONS` 產生，兩種 completion 都測；條件換成 10.1(e) 的結構檢查。另加 `keyPosted:true` 拒絕在三種起始狀態（乾淨、有未存且無檢查點、有未存且檢查點同戳記）：假引擎記錄內容，斷言重開的內容含全部打過的字 |
| **M1-4** | 白名單逐欄位測 true／false／缺／型別錯；一個假引擎錯誤經 SDK 的 `remoteError` 走到頁面真正的入口 |
| **M1-5** | 以 `keyPosted:true` 驅動 `reopenAfterBoundaryRefusal` 的**每一個出口**（四處）；另加靜態檢查：字面「沒有被改動」只出現在 `keyPosted !== true` 的分支上。`nothing-selected` 的措辭照 10.1(h) |
| **R0** | 分類順序改成：單位屬不屬 B → 有沒有選到 → 還原回不回得來 → 鍵臂有沒有改文件。**只有「屬 B、還原回來了、b 臂≠鍵臂」才停下全部流程**；C15／C16 是還原回不來，進 M2-3a。G01（單位 `[48]`）是段中對照，進新類別「barrier」：WASM 上預期 `verified-selection-delete`。工具核對**全部 case × 輪 × 臂**：缺臂、fatal、未知類別、任何類別為空 → 不產生清單；同一 case 三輪的還原下數不一致 → 停。新增 case：**G13**（同一段先連刪一串非字母字元、再刪手動換行，鍵臂逐下記錄 payload 與 `content.xml`，量 10.1(c)）、**打字後 Delete 的原生參考**（給 M2-1b）。每一臂在鍵之後**再打一個字**（原生與 WASM 都打），存檔比較同時驗游標。**從來沒做時**：沒有清單，M2 不得開跑 |
| **M2-0** | 化約被追加時，工具要同時證明：每一個 M2-1 case，化約後的原生「按鍵前」與「鍵臂」文件仍然不同；有一對變成相同，這個化約就被拒絕 |
| **M2-1** | 加：鍵之後打的那個字落點與原生相同（同一份 `content.xml`）；這一臂除了預期的 toast 之外沒有其他 toast（10.1(g)）。**比較器的紅案**，每個斷言各一：把 C03 原生 select 臂的文件當成預期文件（select≠key）→ 紅；竄改一個預期註解 → 紅；竄改一個預期還原下數 → 紅。runner 拒絕預期文件與候選輸出落在同一個目錄樹下 |
| **M2-1b（新）** | 使用者的路：真鍵打一個字，輸入轉接器把它交給 session 之後**立刻**在段尾按 Delete（不等引擎的游標），每個瀏覽器 **N≥20**，每一次存出來的文件等於原生「打字後 Delete」的參考。形式：逐實例（次數就是量測）。從來沒做時：v15 不可出貨（這是最常見的併段手勢，過期的 P 就住在這裡） |
| **M2-2** | 延遲由 **runner 自己量**（送出真鍵 → 收到完成事件），不只看引擎回報的 `keyToUndoMs`；完成數必須等於 M2-1 case 數 × 3 × 2（非空洞）；單位游標與每一下還原的等待都算進去 |
| **M2-3** | 每一臂比較**整份文件**：a、c 重開之後化約的 `content.xml`＝按鍵前的文件＋標記；b 可以是按鍵前＋標記，或原生鍵臂＋標記（10.1(d)）。這一臂除了預期的 toast 之外沒有其他 toast |
| **M2-4** | 「`topDateTimeAfter` 嚴格遞增」撤銷（10.1(b)）；改成每一次的 payload 都變了，而且最終文件等於原生按同樣次數之後的文件（獨立於引擎回報） |
| **M2-5** | 形式寫明：對網裡宣告的 check id 做工具封閉的逐格比較；NE 維持 NE、不因分佈相同變成已驗證；「另外 20 個 hunk 無副作用」只到網裡那些格為止（形式三，登錄） |
| **R** | 宿主上的併段臂比較伺服器上的 `content.xml`（化約後）＝原生鍵臂；不只看標記 |

### 10.3 第 2 節的事實更正

- 「合成文件 19 個 case」→ **18 個交界 case＋1 個段中對照**：G01 的 b 臂單位是 `[48]`、註解 `Delete “0”`（已核對，
  `undo/round-20261006T081216Z/arms.jsonl` 第 36 行）。
- 「每一步都改變了游標、沒有中間值」→ **量到的各步在固定等待之後的快照都不同**（opus 重算：90 步、0 步不變）；中間的回呼沒有記錄
  （原生探針只留最後一個游標，codex 指出），不能拿來支持 P4。
- 「payload…0 不一致（交界批次 324 次…）」：第四、六輪的讀取工具比的是（`UndoCount`, payload）這一對（`analyze_merge_undo.py:52`，審核者讀）。
  在上限以下兩者等價——數量一變，清單長度就變，payload 就變；第五輪單獨比 payload。結論不變，出處說明補上。
- 「上限以下也會…而錯（第四輪 15 次）」的出處是 `PREDICTION-5.md`，不是 README。
- 「兩邊讀的是同一個時鐘」：隨時鐘守衛一起撤回（10.1(b)）。
- 3.2「一個『變了』的游標只可能來自還沒被計入的那一下」：**錯**，由 10.1(a) 取代。
- 第 2 節最後一點的危險指錯了：LOK 會丟掉與上次送出相同的游標（10.1(a) P2），真正的危險是**沒有按鍵卻送來的、矩形不同的游標**。
- 4.3「放錯交界存出來的文件就不同」只對單一錨點的 fixture 成立；H02 那種一整串相同的空段落不成立（M2-4 因此改比最終文件與次數）。

### 10.4 第 8 節的登錄追加

- **111 在交界上換了類別**：B 之前，搶在打字前面的 Backspace 在交界被拒、頁面照實說；有了 B，它會**真的併段**，晚到的字落在併段之後——
  一份靜靜錯掉的文件，回報成功。不再只是「窗口變大」。
- 真宿主上沒有任何計數臂走到 `keyPosted:true`（R 的 109 臂移到 C29，`keyPosted:false`）；這條路只在獨立頁面＋假宿主上量（M2-3b）。
- 手動換行被併進前一個刪除動作時的誤拒（10.1(c)），等 R0 的 G13。
- `LOK_SELTYPE_COMPLEX` 的單位不進 B（10.1(i)）。
- P4 在讀完之前是推論（10.1(a)）。
- 引擎的接線（模型的決定 → 實際送出的鍵）沒有單獨的測試，由 M2 的整份文件比較承擔。
- B 之後的復原／重做（WASM）仍不列判準；原生量過（第 E 輪 54/54）。

### 10.5 順序更新（取代第 6 節第 2 步）

2. 讀 Writer 方向鍵的 KeyInput 路徑確認 P4（沒有 Yield／Reschedule），結果以追加段寫進本文件；不成立就設計柵欄並先讀原始碼證明它
   「排在該按鍵處理完之後」。

## 11. 追加（2026-10-06）：P4 的讀原始碼結果——成立（有界）

10.1(a) 的前提 P4（處理一下方向鍵的過程中不會跑 flush）。主 session 讀的，全部是**讀原始碼，沒量**：

- **flush 只有一個入口**：`CallbackFlushHandler::invoke()` 只被 `FlushQueue` 呼叫（`init.cxx:2584–2588`），而 `FlushQueue` 只由
  `scheduleFlush()` 用 `Application::PostUserEvent` 排進去（`init.cxx:2578–2582`）；`libreOfficeKitViewAddPendingInvalidateTiles` 也只是
  `scheduleFlush()`（`:1765–1768`）。LOK 的 API 呼叫不會同步觸發 flush。所以 flush 要在一下按鍵的處理中途跑，只能是那段處理自己跑了巢狀的
  事件迴圈。
- **user event 是 FIFO**：`SalUserEventList::DispatchUserEvents` 從前端取（`vcl/source/app/salusereventlist.cxx:65–92`）。鍵事件
  （`lokhelper.cxx:1286–1290`）和 flush 進的是同一個佇列。
- **鍵事件直接進 `SwEditWin::KeyInput`**：`LOKPostAsyncEvent` 呼叫 `pFocusWindow->KeyInput(singlePress)`（`lokhelper.cxx:1186–1222`），
  不經過 `winproc.cxx`。
- **方向鍵經過的模組裡沒有巢狀事件迴圈**：在 `sw/source/uibase/{docvw,wrtsh,uiview}`、`sw/source/core/{crsr,view,layout,text}`、
  `sfx2/source/{control,view}`、`vcl/source/window/{winproc,window}.cxx` 搜 `Application::Reschedule`／`Application::Yield`／
  `ProcessEventsToIdle`／`DoYield(`，只有兩處，都不在方向鍵的路上：
  - `winproc.cxx:1389`：IME 的 ExtTextInput，而且 LOK 下在它之前就 `break`（`:1383–1387`）。
  - `sfxbasecontroller.cxx:158–166`：狀態列進度指示器的 `reschedule()`。
- **版面配置的 Reschedule 不讓出**：`SwLayAction::CheckWaitCursor` 的 `RescheduleProgress`（`layact.cxx:76–81`）最後呼叫
  `SfxProgress::Reschedule()`，那是一個空函式（`sfx2/source/bastyp/progress.cxx:329–338`）。LOK 下的中斷檢查
  `Application::AnyInput`（`layact.cxx:89–99`）只問有沒有輸入，headless 的實作只看計時器（`vcl/headless/svpinst.cxx:549–554`），不處理事件。

**界線（推論，寫明）**：這是在上列模組裡搜尋，不是把方向鍵的呼叫圖遞移地走完。已知的一條會碰到進度指示器的路是 `UpdateCursor` 遇到游標所在節點
**沒有版面框**時呼叫 `CalcLayout()`（`crsrsh.cxx:2310–2326`），`CalcLayout` 會開進度（`viewsh.cxx:1245–1275`），進度的 `setValue` 可能走到上面
那個 `reschedule()`。B 的還原兩端（U 與 P，以及標號前的中間位置）都是**畫出來過的游標**，所以都有版面框——這是推論。WASM 核心若沒有狀態列進度
指示器，這條路也不會讓出，沒查。

**結論**：P4 以「讀原始碼、有界」成立，10.1(a) 的規則照用，不改柵欄。M1-2 事件模型裡「一下按鍵的處理中跑 flush」那個開關保留，作為規則依賴
P4 的紅案。

## 12. 追加（2026-10-06，做 R0 儀器時發現、任何執行之前）：有打字的比較不能比位元組

**讀原始碼**：打進去的字經 `SwEditShell::Insert2` 呼叫 `SwDoc::UpdateRsid`（`sw/source/core/edit/editsh.cxx:105–120`），在設定開著時把當下
session 的 rsid 寫成字元屬性（`sw/source/core/doc/docfmt.cxx:429–445`）；rsid 在每次載入時加一個隨機數（`sw/source/core/doc/doc.cxx:223–235`，
只有環境變數 `LIBO_ONEWAY_STABLE_ODF_EXPORT` 能關掉，WASM 產品上不能設）。WASM 的打字走 `paste()`（`probe_engine.cpp:3118–3125`），原生探針
走鍵——連寫入路徑都不同。所以 10.2 裡三個**有打字**的比較，跨 session、跨平台都不可能逐位元組相同：M2-1 的「鍵之後打一個字」、M2-1b 的
「打字後 Delete」、M2-3 的「按鍵前＋標記」。

更正（取代 10.2 對應三格的比較方式；沒有打字的比較照舊比 `content.xml` 位元組）：

- **M2-1 的續打、M2-1b**：比**段落文字序列**——工具依文件順序取出每個 `text:p`／`text:h` 的純文字（展開 `text:span`，手動換行記成 U+2028），
  兩邊的序列必須相同。它驗的是「字落在哪一段的哪個位置」，正是這兩格要驗的東西；格式差異由同一 case 不打字的那份位元組比較負責。
- **M2-3**：參考文件改在**同一個 session** 取——打好標記之後、按鍵之前，runner 直接呼叫引擎的存檔（不經 session，不改變 dirty 與檢查點，
  同檢查點自己的作法）得到 X；重開之後由 session 存檔得到 Y；要求 `content.xml`(X)＝`content.xml`(Y)。標記的 rsid 隨文字存進檔案，所以同一
  session 內可以比位元組。開發 shakedown 若量到「載入 X 再存」本身就不穩定，改比段落文字序列，並以追加段寫明是哪一次量測逼出來的。
- 段落文字序列的比較器要有自己的紅案：把一個字挪到同一段的另一個位置 → 紅；把一段拆成兩段 → 紅。

## 13. 追加（2026-10-06，opus 第二輪聚焦審核之後、任何引擎程式碼之前）

題目：只打 10.1(a) 的新規則與 §11 的 P4 論證。報告的 BLOCKING 一條、SHOULD 一條、NOTE 五條；主 session 核對了 BLOCKING 與柵欄的原始碼。

### 13.1 過期的 P 還有一類：還排在 LOK 佇列裡的事件（BLOCKING，已核對）

P1–P4 都成立時 P 仍可能過期：`scheduleFlush` 只在沒有待處理的 flush 時才排一個（`init.cxx:2578–2582`），所以某個會移動游標的事件 E
若在引擎送出 Shift＋方向鍵（K）時**還在 LOK 的佇列裡**，E 的 flush 會排在 K 後面、和 K 的選取與游標併成同一次——E 的游標從來不會單獨送達，
「單位的 `TEXT_SELECTION` 之前最後一個送達的游標」就是 E **之前**的游標。E 的來源不只 insert 的退路：`handleClick` 送出滑鼠事件後**立刻**
回報（`probe_engine.cpp:3095–3116`），`placeCaret` 在「游標本來就在被點的那一行，而且任何回呼讓序號前進」時就返回
（`editor-session.js:404–426`；序號會被 tile 失效推進），滑鼠事件可能還沒被處理。「游標在句點前、使用者點句點後、立刻按 Delete」
→ 第二下落在過期的 P →「回來了」→ 刪掉句點，回報成功。需要 LOK 在點擊到 Delete 之間忙著、而且點在舊游標右邊一格；都沒量過。

**柵欄（採用；取代 10.1(a) 的「insert 的退路」那一條，它被涵蓋了）**：K 自己那次 flush 帶著選取的**錨點側**矩形——Shift＋Right 是
`TEXT_SELECTION_START`、Shift＋Left 是 `TEXT_SELECTION_END`。它在 flush 當下由當下的選取算出（`SwShellCursor::FillStartEnd` →
`lcl_getLayoutRect(Start()/End())`，`viscrs.cxx:536–563`），排在 `TEXT_SELECTION` 與游標之前（`init.cxx:2395–2412`、`:2461`），引擎已經
解析它（`probe_engine.cpp:2504–2511`）。錨點就是 K 被處理時游標所在的位置——**不管之前的事件有沒有單獨送達**。規則：錨點側矩形的
（x, y, 高）必須等於 P 的；不等、或那個矩形沒送來（`HasArea` 為假時不送，`viscrs.cxx:511–514`）→ 拒絕，`keyPosted:false`，
`stage:"anchor-mismatch"`。

**前提要量**：游標矩形（`m_aLastLOKRect`，寬 0）與選取起點／終點矩形（`GetCharRect` 的版面矩形）在段落尾端、段落開頭、標號前這幾種位置，
（x, y, 高）是不是相同。**讀原始碼回答不了，R0 也沒記錄這兩個回呼**（探針只留游標與選取矩形）。所以加一輪 **R0b**：探針在每一臂的單位
讀回裡另記最後送達的 `TEXT_SELECTION_START`／`_END`，R0 的三個 case 檔全部、每個 case 一輪；工具對每一個 B 單位比錨點側矩形與放置時的游標。
預測與工具先 commit。**全部相等**才照上面的規則實作；有任何一格不等，設計回到這裡（例如改用量到的對應，或改用別的柵欄），不得先寫程式。

### 13.2 鎖的順序寫成不變式（SHOULD，審核者讀）

10.1(a) 說「判定在 LOK 執行緒做、在 `gState.mutex` 之下交給引擎執行緒」，但沒寫它依賴的順序。今天的順序是 SolarMutex → `gState.mutex`
（LOK 執行緒在 `invoke()` 裡持有 SolarMutex，經 `submit()` 取 `gState.mutex`）。兩條不變式：

- 引擎執行緒**持有 `gState.mutex` 時不得呼叫任何 LOK API**（`postKeyEvent`、`getCommandValues`、`getTextSelection` 都取 SolarMutex → ABBA）。
- **任何執行緒持有 `gState.mutex` 時不得呼叫 `emitJson`** 或其他 `MAIN_THREAD_*` 代理：主執行階段執行緒是 SDK Worker，它的入口會
  `submit()` 取這把鎖；Worker 裡的 futex 等待不處理被代理的呼叫，會死鎖。

加入 M1：一支靜態檢查，`gState.mutex` 的每一個鎖範圍內不得出現 `pClass->` 或 `emitJson`／`MAIN_THREAD_`；紅案：在一個鎖範圍裡放一行
`pClass->` → 紅。

### 13.3 其餘（NOTE）

- **B 只能從 `TEXT_SELECTION` 回呼那一支進入**，不得從 250 ms deadline 讀到交界文字的那一支進入（`probe_engine.cpp:3433–3445`）——那裡沒有
  錨定的 P。
- **EditEngine 的文字**（註解、繪圖物件裡的文字）把游標當一般回呼排隊（`lokhelper.cxx:692`、`impedit.cxx:1481–1483`，審核者讀），P3 在那裡
  不成立。產品頁面推論上進不去（點擊一律單擊、Enter 走 `.uno:InsertPara`），但這是推論。實作時用可觀察的狀態擋（例如圖形選取不為空就不進 B）；
  擋不了就登錄成具名極限。
- LOK 忙的時候 250 ms 會先到，B 退化成拒絕＋重開，而每次重開吃掉一個 Worker 世代（上限 3）。M2-1b 會量到這件事；登錄。
- §11 對 `CalcLayout` 的界線**大概太悲觀**：審核者追到 `SfxProgress` 用的是版面管理器的進度條元件，那兩處 `Reschedule` 都不是它的
  （`progress.cxx:195–239`、`workwin.cxx:1108–1133`，審核者讀、未核對）。界線的形式不變（有界、手搜），措辭以此為準。
- 「畫過所以有版面框」沒有反例；隱藏修訂模式下跨隱藏刪除合併的段落未讀。登錄。

## 14. 追加（2026-10-06，R0b 之後、任何引擎程式碼之前）：柵欄改成「x 相等＋游標落在錨點那一行裡」；儲存格選取沒有錨點

證據：`findings/evidence/merge-native/README.md`「R0b」節；預測 `PREDICTION-R0b.md`（`596443ba`，執行之前 commit）。

### 14.1 量到的

- 68 列（三個 R0 case 檔、select 與 b 兩臂、每檔一輪）。**x 在 66 列有錨點的格子上全等；高度 0／66 相等**：60 列錨點＝游標 − 1——游標的
  payload 是 `(x, y, x+w, y+h)` 以開區間印出，錨點走 `SwRect::SVRect()`，每一維少 1；P27／P62／P63 的 6 列錨點是整行（高 399）、游標是
  游標那個 portion（高 348），y 差 52、底邊重合（42820 + 348 = 42768 + 399 + 1）。**13.1 的規則照寫會拒絕每一次合併。**
- **C17（下一格存在的儲存格尾）沒有錨點。**讀原始碼（執行之後）：儲存格選取時 Writer 建 `m_pTableCursor`、刪掉一般游標的 mark 並清空它的
  矩形（`crsrsh.cxx:2104–2108`）；START／END 的 payload 從一般游標取（`wrtsh4.cxx:273–275`），空的一般游標什麼都不回（`viscrs.cxx:550–551`）。
  所以**每一個儲存格選取**都不送錨點，不只 C17（原始碼；量到一格）。C15、C16 是文字選取（單位吞進一整列），有錨點。預測說 absent 0，錯在這一格。

### 14.2 柵欄（取代 13.1「錨點側矩形的（x, y, 高）必須等於 P 的」那一句）

錨點側矩形 A＝(x_a, y_a, w_a, h_a)，P＝(x_p, y_p, 0, h_p)，**x_a = x_p，且 y_a ≤ y_p，且 y_p + h_p ≤ y_a + h_a + 1**。不成立、或 A 沒送來 →
拒絕，`keyPosted:false`，`stage:"anchor-mismatch"`（同 13.1）。這是執行前登錄的候選對應，R0b 在 66／66 有錨點的列上成立。

放棄了什麼：同一行、同一個 x 的兩個不同模型位置（中間夾零寬的 portion：書籤、隱藏文字、空欄位）過得了柵欄。這不是放寬造成的——兩者的錨點
矩形本來就相同，任何以矩形為準的柵欄都分不出來。另外，兩塊會重疊的文字區域（浮在本文上的文字框）裡，另一塊的游標若 x 相同、垂直範圍重疊，
也過得了。都登錄（14.5），不修。

### 14.3 錨點只能取自單位那一次 flush（實作約束）

引擎的 `gEditorState.selectionStart／End` 只在收到時覆寫（`parseEditorRectangle`，`probe_engine.cpp:2504–2511`），沒收到就留著舊值。儲存格
選取不送錨點，不限定的話柵欄讀到的是更早某次選取留下的錨點，可能據此放行。規則：

- 引擎**送出 K 時**清掉兩個錨點欄位；**每處理完一個 `TEXT_SELECTION` 回呼**也清掉。START／END 在同一次 flush 裡排在 `TEXT_SELECTION` 之前
  （`init.cxx:2395–2412`），所以單位的 `TEXT_SELECTION` 送達時，留著的錨點只會是同一次 flush 的，或者沒有。
- 只在送出 K 時清不夠：`TEXT_SELECTION` 對上一次送出的值去重（`m_states`，`init.cxx:1592`），START／END 不去重（14.1 的預測讀過），一次
  flush 可能送了 START 而 `TEXT_SELECTION` 被去重掉，那個 START 會留到下一次。
- 清除與讀取遵守 13.2（持 `gState.mutex` 時不呼叫 LOK API、不 `emitJson`）。
- 不增加新前提：「哪一個 `TEXT_SELECTION` 是單位的」本來就是 barrier 的判定（P1–P4）；錨點跟著那個判定走。

### 14.4 判準更正

- **M2-3b**（取代 4.3 表中 M2-3 的 b 臂）：C17 型（下一格存在的儲存格尾）→ `stage:"anchor-mismatch"`、`keyPosted:false`，toast 說「文件沒有
  被改動」（頁面白名單 `MERGE_KEY_UNCHANGED_STAGES` 已含 `anchor-mismatch`，M1-5）。理由：處方換了——柵欄在送鍵之前，而儲存格選取一定沒有
  錨點（14.1）。原判準（`key-deadline`、`keyPosted:true`）是為「沒有柵欄、鍵送出後等 payload」那個處方寫的。新的期望比較強（鍵沒送、可以說
  沒改），不是放寬。若沒有改這條，v15 在 C17 上的正確行為會被判紅。
- M2-3 的清單由工具從 R0 產生（4.3 表的「工具封閉」）。期望的 stage 不能只看 R0 的類別：**key-noop 而 R0b 沒有錨點 → `anchor-mismatch`；
  key-noop 而有錨點 → `key-deadline`、`keyPosted:true`**（今天沒有這種 case）。產生清單的工具要讀 R0b 的 `anchor-rect.json`；某個 case 沒有
  R0b 的列就停下來，不得猜。
- 第 5 節對 M2-3 的預測「C17 型每次都要等滿 2000 ms 才拒絕」隨之撤回；第 8 節同名的登錄撤回。
- **連帶的覆蓋缺口**：M2-3 原本靠 C17 型走到 `keyPosted:true`；改了之後**沒有任何 R0 case 會在 WASM 上走到 `keyPosted:true`**（10.4 已登錄
  「`keyPosted:true` 從未在真宿主上被觸發」，現在 M2 也不觸發）。這是工作項，不進閘門（第 1 節的形式還沒有）：M2 計數之前要另找一個誘因。
  候選是 G13 型（第三個被併進同一個刪除動作的手動換行，原生 3／3 文件變了 payload 沒變）；它的前提——WASM 上第 1～30 下走的是 barrier 路徑
  （選取＋`.uno:Delete`），而不是鍵，Writer 合併 undo 動作的方式是否相同——沒量過。

### 14.5 登錄追加（第 8 節）

- 零寬 portion 兩側矩形相同的兩個位置過得了柵欄（14.2）。
- 會重疊的文字區域（文字框浮在本文上）：另一塊裡 x 相同、垂直範圍重疊的游標過得了柵欄。
- 游標在標號前（`IsInFrontOfLabel`，`m_pSpecialPos` 會改游標的 x，`crsrsh.cxx:2383–2388`）R0b 沒量到（探針用 `GoTo…` 放游標）。若產品的
  點擊能把游標放到標號前，柵欄會在那裡誤拒（拒絕＋重開：照實，但多吃一個 Worker 世代）。M2 遇到就立 finding。
- `keyPosted:true` 在 WASM 上沒有誘因（14.4）。

### 14.6 M1-2 事件模型測試要有的格（加在 10.2／13 已列的之上）

錨點高度少 1 → 過；更高的行（游標較低、較矮、底邊重合）→ 過；x 差 1 → 拒；錨點在另一行 → 拒；沒有錨點（儲存格選取）→ 拒；送出 K 之前
留下的錨點（一次只送了 START、`TEXT_SELECTION` 被去重的 flush）→ 不得被讀到，拒。

## 15. 追加（2026-10-06，M1-2 事件模型測試第一次跑之後、任何引擎接線之前）：第二下還原有一個沒登錄過的反例族

標頭 `wasm_sdk_probe/src/merge_key_undo.hpp`、測試 `wasm_sdk_probe/tests/merge_key_undo_model_test.cpp`（工具從 LOK 模型產生序列：FIFO、flush
合併與去重、R0b 的矩形對應、排隊／跨在交易開始兩側的事件、表格選取、重新排版、引擎送出的延遲、只有旁欄不同的重送）。不變式在 LOK **處理那一鍵的當下**
檢查（游標在 Shift 跑的位置、沒有選取），另加活性（沒有干擾的情境必須合併；只驗安全的話，一條全部拒絕的規則也會過）。

### 15.1 量到的

- 三條被否決的規則都找得到反例：3.2 原文、P＝交易開始快照（第一個反例是「事件已處理、它的 flush 跨到交易開始之後」＝10.1(a) 的打字後立刻 Delete）、
  沒有柵欄（第一個反例是排隊中的事件＝13.1）。P4 不成立時真規則也找得到（第一個反例＝codex 的 I→P）。
- **真規則在忠實的模型上有反例，19,800 條，全部屬於同一族：暫時性的重新排版。**第一下其實回到原位，但一次把行移走的排版跟它併在同一次 flush，
  證據看起來「沒回來」→ 送第二下 → 排版移回來時送出的游標等於 P，在第二下**還排在佇列裡**的時候送達 → 判「回來了」→ 鍵會在第二下移過去的位置執行。
- **10.1(a) 那句「未經請求的游標在第二下只會造成誤拒；唯一的例外是剛好落在 P 的矩形，屬於已登錄的『同矩形、不同邏輯位置』」是錯的。**這一族的
  游標落在 P 的矩形上、而且邏輯位置也**是** Q——錯的是第二下還沒被處理。
- 找乾淨修法的第一個候選不成立：`postUnoCommand` 帶完成通知時被強制同步（`unoctitm.cxx:654–657`），在引擎執行緒當場執行、不排在已送出的按鍵後面，
  不能當「第二下已處理完」的柵欄。
- 柵欄改在單位的 `TEXT_SELECTION` 當下判（不等 U）：排隊事件的起點剛好是單位另一端時，U 會被去重掉，原本要等 2000 ms 才以 `unit-caret` 拒絕。
  改了之後同一類直接 `anchor-mismatch`。U 的定義照 10.1(a)（之後第一個游標），拿掉從 3.1 第 4 條帶進來的「≠P」。
- 突變（對標頭）：柵欄只比 x、不比 x、照 13.1 嚴格相等、不在游標回呼清錨點、交易開始不清錨點、向後讀 START、未解析也算驗證、key-deadline 標成沒送鍵、
  忽略 restore-mutated、第一下不等收合、第二下不要求「與已知不同」、P 用開始時的快照——都會讓測試的輸出與基準不同。**在 `TEXT_SELECTION` 回呼
  清錨點**那一條與基準完全相同：等價（錨點只在交易開始後第一個非空 `TEXT_SELECTION` 讀，在它之前的 `TEXT_SELECTION` 只能是空的，而沒有選取的
  flush 不帶 START）。照 14.3 留著，當防禦。

### 15.2 待擁有者決定（測試在決定之前維持紅）

- **A**：交易期間的排版守衛——從擷取 P 到送鍵之間，任何 `LOK_CALLBACK_INVALIDATE_TILES` 送達就拒絕（`keyPosted:false`）。前提要先在原生量：
  Shift、還原的方向鍵、收合本身都**不**產生 tile 失效（LOK 的選取是客戶端畫的，推論，未讀）。前提不成立，A 就會拒絕一切，退回 B 或 C。
- **B**：登錄成具名極限，不寫程式。出事時是一份靜靜錯掉的文件、回報成功（同 111 換類別之後那一型）。
- **C**：拿掉第二下：第一下沒回來就拒絕＋重開。R0 的十個兩下才回來的 case（下一段帶標號）全部變成拒絕。

## 16. 裁決（2026-10-06，擁有者交 fable 裁決 §15.2）：E 形——不再有任何不帶選取的方向鍵

擁有者把 §15.2 交給 fable 裁決。fable 兩輪：第一輪提出「改形」（向前改成 [右, Shift＋左]），主 session 指出缺口後撤回，第二輪定為 E 形。
主 session 在採用前讀過它立論的原始碼（下列「已核對」）。

### 16.1 裁決與白話理由

**A、B、C 都不採用。**缺陷的形狀是「一下沒有痕跡的按鍵」：第一下還原會把選取收合，`TEXT_SELECTION` 從非空變空，這在 flush 當下算出、只對上一次送出
的值去重，偽造不了也丟不掉；每一個 Shift 按鍵也都留下 flush 當下算的選取。**第二下還原是在沒有選取的狀態下按的，它唯一的痕跡是一個游標，而任何
矩形的變動都能偽造一個游標。**所以修法不是證明第二下、也不是猜哪些排版會偽造它，而是讓每一步都留下痕跡。

- A 不採用：守衛是代理（「每個偽造者都會重繪」是手工清單），窗口是整筆交易（最長約 8 秒），每次誤拒都是重開（吃一個 Worker 世代）；閒置拼字的重繪
  在這顆 core 上活著（`config_wasm_strip.h:8`、`layact.cxx:2171–2175`，fable 讀），會打在「打字後立刻 Delete」上。
- B 不採用：登錄一類靜靜改錯的文件（111 型），而觸發條件「Writer 的排版會不會在沒有文件改動下把游標的矩形移走再移回」是手工枚舉，既不能證明會、
  也不能證明不會。fable 在原始碼裡找不到這樣的機制（`SwLayAction` 在一個動作內迭代到不動點、游標只在結尾更新一次），但這不能當判準。
- C 不採用：九個量到的 case（刪進帶標號的段落）每次都變成重開。
- 第一輪的改形（向前 [右, Shift＋左, Escape, 鍵]）**撤回**：兩個鍵各自 `doc_postKeyEvent`，每次各拿一次 SolarMutex（`init.cxx:4813`，已核對）；
  VCL 的迴圈跑在 LOK 自己的執行緒上，被 `PostEvent` 喚醒（`svpinst.cxx:130–149`，fable 讀），第一鍵送出之後兩邊搶鎖。LOK 若先處理第一鍵並跑掉它的
  flush，第一鍵的游標就會先送達 → P 變成它 → 柵欄誤拒。放寬柵欄救不了：那個簽名與「在文件尾端打一個字再按 Delete」完全相同，放寬的話會把剛打的
  字當成單位刪掉。

### 16.2 E 形（取代 3.1 第 5 條的還原、10.1(a) 的第一下與第二下證據）

向前（Delete，單位含分隔符號）：

1. **K1＝Shift＋右**（照今天）。處理的證據：非空 `TEXT_SELECTION`。位置：START 對 P 用 14.2 的對應。讀單位、分類照舊（Barrier → `.uno:Delete`；
   兩端 → `nothing-selected`；表格沒有 START/END → `anchor-mismatch`）。
2. **`.uno:Escape` #1**：只在看到 K1 的 flush、讀完單位之後送。路徑 `FN_ESCAPE` → 有選取時 `LeaveDrawCreate`、`SelectObj(LONG_MIN, SW_LEAVE_FRAME)`、
   `EnterStdMode()`（`view2.cxx:1220–1252`，已核對）；`SelectObj` 在原本沒有選取物件時不移動文字游標（唯一的 `SetCursor` 在 `if (bHadSelection)`
   裡，`feshview.cxx`，已核對）；`EnterStdMode` 用 `ClearMark()` 收合、point 留在原處、`m_bInSelect=false`（`select.cxx`，已核對）。
   證據：`TEXT_SELECTION` 由非空**變成空**。
3. **K2＝Shift＋左**：只在看到 #1 的空之後送。有 mark，所以不會停在標號前（`crsrsh.cxx:351–360` 要求 `!HasMark()`，已核對）。證據：非空
   `TEXT_SELECTION`。位置：**point 那一側（START）對 P 用 14.2 的對應**；選到的文字必須逐位元組等於 K1 的。任一不成立 → 拒絕，`keyPosted:false`。
4. **`.uno:Escape` #2**：只在看到 K2 的 flush 之後送。證據：**變成空**。之後的游標在一般行上會被去重、不一定送達，不拿來當證據（位置已在第 3 步證過，
   `ClearMark` 不移動 point）。
5. P_start＝P0，然後送使用者的鍵（照舊）。

向後（Backspace）：鏡像——Shift＋左、Escape、Shift＋右（不會停在標號前：那一支要旗標已經立起來）、Escape、鍵，point 那一側是 END。
（今天的「不按 Shift 的右鍵還原」在拿掉第二下之後也是對的；為了一條規則、一個模型，採用鏡像。）

**不變式：我們的事件永遠只有一個在飛**——每一次送出都在前一步的證據送達之後。所以不需要原子性、不需要 VCL 的綁定、整個流程沒有不帶 Shift 的方向鍵。
引擎要盯的是**空／非空的轉換**，不是「來了一個 `TEXT_SELECTION`」：重新排版會重送一個非空、矩形移動過的 payload（START/END 不去重，14.1）。
同理，#2 若和 K2 併進同一次 flush，那次 flush 算出來的是空選取，什麼都證明不了——「看到 K2 的 flush 之後才送 #2」讓它不可能發生，而不是不太可能。

### 16.3 R0c（原生，預測先 commit，三輪；方括號是殺死條件）

- (a) 向前（含九個帶標號的 case）：#1 之後 `TEXT_SELECTION` 空、沒有 START/END、`.uno:Undo` payload 不變、游標＝origin＋1 的 no-mark 矩形
  〔payload 變了，或游標移動〕；K2 之後非空、START 對 P 每一列都滿足 14.2、選到的文字與 K1 逐位元組相同〔文字對而 START 不滿足，或文字不同〕；
  #2 之後空、payload 不變、游標若送達則＝P〔payload 變了，或游標移動〕；鍵臂的 `content.xml` 與原生鍵臂逐位元組相同、零個不帶 Shift 的方向鍵〔任何不同〕。
- (b) 向後：鏡像，point 那一側＝END〔同上〕。
- (c) C29／C30：K1 什麼都沒選到 → `nothing-selected`，不送 #1／K2，文件不變〔選到了東西〕。
- (d) C15–C17：送鍵之前就拒絕（C17 在 K1 沒有錨點；C15／C16 在 K2 的柵欄或文字比對）〔送了鍵〕。
- (e) 讀原始碼項（不量）：`SwView::Execute(FN_ESCAPE)` → `AttrChangedNotify` 沒有巢狀事件迴圈（P4 對 Escape 這條路）。
- **從來沒做時的預設**：第二下不送（等於 C），v15 不連結，模型測試維持紅。B 永遠不是預設。

### 16.4 模型與測試要改的

`Attribution` 拿掉 `NeedSecondPress`／`AwaitRestore2`；新增 Escape #1、K2、Escape #2 的階段。產生器加上同步的 Escape（決定當下套到 LOK 狀態＋排一次
flush）。不變式不變。紅案保留（3.2 原文、快照 P、沒有柵欄、P4 不成立），另加「#2 在 K2 的 flush 被看到之前就送」——預期是「什麼都沒證明到 →
deadline」（活性，不是安全）。兩個順帶的修正：游標的形狀依 `HasMark()` 決定（`crsrsh.cxx:2402–2409`），不是依「選取非空」；同矩形那一輪的
sweep 換規則之後只應報同矩形這一族。另：§15 說「十個兩下才回來的 case」，第六輪的表列的是九個（I02 C08 C10 I03 I01 P27 E13 P62 P63），以九為準。

## 17. 追加（2026-10-06，R0c 之後）：E 形採用；C15／C16 成為 `keyPosted:true` 的誘因

證據：`findings/evidence/merge-native/README.md`「R0c」節；預測 `PREDICTION-R0c.md`（`cfc41b55`，執行之前）。

- **16.3 的殺死條件一條都沒成立**（三個 case 檔各三輪，0 KILL、0 STOP）。29 個合併 case（含九個帶標號的）與兩個打字後合併，E 形的文件都等於
  Writer 自己的鍵；兩次 Escape 都沒改 undo payload、都沒移動 point；Escape #2 之後的游標只在 P27／P62／P63（較高的行）送達且等於原點，其餘被去重——
  與預測逐格相同。**E 形採用**，引擎照 16.2 實作。
- **預測錯一處**：C15／C16 不是在 K2 因文字不同而拒絕。K2 把整列選了回來（文字、START、END 都與 K1 相同），point 那一側通過柵欄，回到原位；而
  Writer 自己的鍵在這兩個位置什麼都沒做。所以 v15 在這兩格會送鍵、到 key deadline 以 `keyPosted:true` 拒絕（照實：鍵送出了、沒有效果可證）。
- 判準更正（取代 14.4 的 M2-3b 段與「連帶的覆蓋缺口」）：M2-3 每一臂的期望 stage 由工具從 **R0c 的判讀結果**（`r0c/eshape.json`）產生，不再從 R0 的類別：
  `nothing-selected` → `nothing-selected`；`refused-k1-anchor`／`refused-k1-fence` → `anchor-mismatch`；`refused-k2-*` → `return-mismatch`；
  `key-noop` → `key-deadline`＋`keyPosted:true`。今天的清單：C29／C30、C17、C15／C16。**WASM 上 `keyPosted:true` 有誘因了**（C15／C16），14.4 登錄的
  缺口關閉；10.4「真宿主上沒有計數臂走到 `keyPosted:true`」不變（R 臂在宿主上，M2-3 在獨立頁面＋假宿主）。
- 新 stage `return-mismatch`（K2 的文字或 point 柵欄不成立，送鍵之前、沒有改動）尚未加進頁面的「沒有被改動」白名單；在加之前頁面對它說不確定的那一句
  （fail-closed）。加進去時要有 M1-5 的紅案。
- 仍未量：16.3(e) Escape 路徑的 P4（讀原始碼項）；游標在標號前（14.5）。

## 18. 追加（2026-10-06，引擎接線的 opus 對抗性審核之後、連結之前）

審核對象：`06e61634`（標頭＋模型測試）、`4863f593`（引擎接線、v15 規則、M1-1、鎖範圍）。結論：**沒有 BLOCKING**——找不到非競態的路徑能讓 v15
把鍵按在 P 以外而回報 `verified-key-undo`；送出順序、鎖順序、完成與錯誤的 JSON 形狀都核對過。主 session 讀過每一條依據的程式碼。

### 18.1 處置

- **S1（修，改設計）**：`gSelectionBarrier.stage` 被 LOK 執行緒讀改寫，與引擎執行緒的重設沒有共用的鎖；證據與 2000 ms deadline 同時到達時，重設之後
  被寫回一個非 Idle 的 stage，所有命令（含存檢查點與關閉）永久 BUSY。改成：LOK 執行緒**只**在 `gMergeMutex` 底下餵 tracker、讀一張「票」
  （`MergeTicket`：serial、requestId、documentHandle、是否已送鍵、是否已有步驟在排），在鎖外 `submit()` 一個步驟（`values[0]=3`）；merge 的
  stage 只由引擎執行緒寫（`advanceMerge` 依 tracker 的 phase 與目前的 stage 決定）。中間那四個「Queued」stage 拿掉。
- **S2（修）**：merge 步驟裡的例外原本落到 engineLoop 的通用 catch（非 SDK 命令→沒有 requestId 的錯誤）→ BUSY → SDK 30 秒逾時 → rollback；
  送鍵之後那就是一個沒有 `keyPosted:true` 的出口（10.1(d) 點名過）。merge 步驟與 B 的入口包上 try/catch，一律走 `finishMergeKeyError`
  （送鍵之後 `key-step`）。
- **S3（登錄）**：13.3 要求的 EditEngine 守衛沒有做。登錄成具名極限（第 8 節）：**在繪圖物件或註解的文字編輯模式裡按 Delete／Backspace，B 的
  Escape 會先離開文字框（`SelectObj(…, SW_LEAVE_FRAME)`），K2 落在本文；擋住它的只有柵欄的座標比對（14.5 已登錄的重疊區域極限）**。產品頁面
  推論上進不去（點擊一律單擊、打字走 `paste()`），這是推論。
- **N1（登錄，WASM 上量）**：柵欄依賴「同一次 flush 裡 START／END 在 `TEXT_SELECTION` 之前」。Writer 在文字框（fly frame）裡會把
  `TEXT_SELECTION` 走一般佇列先送（`move.cxx:57–69` → `crsrsh.cxx:283–294` → `viscrs.cxx:1010`，審核者讀），START／END 在 flush 時才附加、排在後面。
  影響只在活性：那裡的每一次合併都被拒（審核者把模型改成這個順序跑過：0 合併、0 反例）。R0b／R0c 只記最後一次送達的值、沒記順序。M2 的 WASM 量測
  要包含文字框裡的一格，預期 `anchor-mismatch`。
- **N2（修）**：步驟的 deadline 改在送出（會等 SolarMutex）之後才起算；K1 的 250 ms 改在讀 P_start 之後起算。
- **N3（修）**：送鍵之後，「已有步驟在排」的旗標在讀 payload **之前**清掉，期間送達的回呼會排下一個步驟，不會被吸收。
- **N4（登錄，無害）**：deadline 拒絕之後才到的 `.uno:Escape` 結果會落到通用的 UNO 處理器；那時 `gUnoRequestId` 是 0，被忽略。
- **N5（修）**：v15 在 250 ms 那一支看到分隔符號時，舊的訊息讓頁面說「目前還不能在段落交界刪除」——在會合併的 build 上那是錯的能力宣稱。改走
  `finishMergeKeyError("unit-late")`（送鍵之前、沒有改動；頁面白名單同步加入，M1-5 的推導測試要求兩邊一致）。B 仍然不從這一支進入（13.3）。
- **N6（修）**：關閉文件時重設 tracker 與票，前一份文件的游標不會變成下一份的 P。
- **N7（更正）**：`4863f593` 的註解與 commit 訊息說「編輯器狀態只在矩形改變時才往下傳」——不對，`parseEditorRectangle` 解析成功就回 true。
  獨立餵 tracker 的做法不受影響；錯誤的註解已隨 S1 的改寫移除。

### 18.2 仍然存在（登錄）

- 舊 barrier 自己的同型競態：LOK 執行緒在 `AwaitingUnitSelection` 把 stage 改成 `UnitVerificationQueued`，與 250 ms deadline 的重設之間沒有鎖
  （opus F3 早已登錄；B 的入口沿用這一步）。
- 模型測試不模擬 stage 機、執行緒與 deadline（10.4 已登錄「引擎的接線沒有單獨的測試，由 M2 的整份文件比較承擔」）。

## 19. 追加（2026-10-07）：v15 同時換上 CJK 字形子集（擁有者選 D、E 級）

不屬於併段，但跟 v15 同一次身分變更出貨（擁有者裁示：一次變更付清）。證據：`findings/evidence/cjk-subset/README.md`；研究：
`research/RESEARCH-2026-10-06-wasm-size-status.md` 第 7–8 節。

- v15 的 profile 從 `sdk/v15-writer-review-manifest.json` 打包＝r6 的來源 manifest 只把 `cjk-r5` 換成 `cjk-sub-e`（Noto Sans CJK TC 的 E 級子集：Big5、
  HKSCS、U+4E00–U+9FFF、假名；7,200,632 位元組原始、5.60 MB zstd；原本 19,484,784／12.17 MB）。打包規則先跑 `build_cjk_subset_pack.py --check`。
- **v15 出貨的東西因此是四塊**：B、096 的引擎那一半、082 的修法、CJK 包。連結手冊同步更新。
- 判準追加（形式一，逐實例）：WASM 驗證時，同一顆 v15、只差 CJK 包（另以 r6 manifest 打一份不出貨的對照 profile）的語料頁面，tile 逐張相同——只要那頁的字都在
  E 級裡。不同的那一張要查是哪個字（預期只會出現在韓文或擴充 A 的測試檔）。
- 登錄：日文／韓文／簡中標記的文字改用繁中字形；字型名稱點名可選 feature（`:fwid` 等）時拿到預設字形；E 級以外的字畫成缺字方塊而沒有回報（085）。
- 宿主：`tools/check_m3_assets.py` 的 Z2-2 與「Z2 D」兩個紅案寫死了 `cjk-r5` 的檔名，v15 進宿主（0.2.8）時要改——依既有規矩，runner 改了就是新的 pin。

## 20. 追加（2026-10-07，v15 產品路徑網之後）：v15 的 CJK 包改變了行高（finding 113）；擁有者選 A，出貨身分改為 v16

證據：`findings/evidence/v15-shakedown/cjk-ab/README.md`；finding：`findings/113-the-v15-cjk-subset-has-one-family-so-cjk-lines-get-a-latin-line-height.md`。

### 20.1 量到的

- v15 產品路徑網的兩處紅（Chrome 第 42 格、Firefox 兩個游標格）**都是 CJK 包造成的**：同一顆 v15 連結只把 CJK 包換回完整 `cjk-r5`，兩個瀏覽器每一格回到 v8。
  B、096 的引擎那一半、082 的修法在這些格上乾淨；Chrome 上 096 的效果看得到（交界方向鍵被引擎回應、session 維持 `ready`、B4 由 worker 誘因量到）。
- 成因：E 級子集只有 `Noto Sans CJK TC` 一個家族名，原 TTC 有 JP／KR／SC／TC／HK。預設亞洲字型（引擎寫下的：v8 `Noto Sans CJK KR`、v15
  `Liberation Sans`）與指名 SC／JP／KR 的段落在 v15 落到 Liberation Sans，**含中文的行高約為 v8 的 0.8 倍**（探針 20 對 15–16 px），文件重排。
  第 19 節登錄的「日韓簡標記的文字改用繁中字形」**沒有發生**——實際發生的是拉丁行高，這一條當時沒有登錄。
- 不是 v15 的差異：台灣文件常用的字型名（思源黑體、PMingLiU、新細明體、Microsoft JhengHei、AR PL UMing TW、標楷體）在 v8 上就是拉丁行高。未診斷、未判定是否為缺口。

### 20.2 裁決與身分（擁有者 2026-10-07 選 A）

- CJK 包改為 `cjk-sub-e5`：同一份 E 級字型（重建後與 v15 出貨的逐位元相同）依原 TTC 的 face 順序放五次，只有 `name` 表不同，存成表格共用的
  collection，7,210,328 位元組（＋9,696）。工具 `tools/build_cjk_subset_ttc_pack.py`（`--check` 有兩個紅案）。
- **出貨身分改為 `e2-editor-v16`＝v15 的連結（wasm `ad3f68bb…`、loader、worker、export list 全同）＋`cjk-sub-e5`**，manifest `99cf5f13…`；
  不連結，從 v15 的封存打包（Makefile「v16」區塊）。封存：`wasm_sdk_probe/build/archive/e2-editor-v16-ad3f68bb-worker-00882139-cjk-e5-ce59153d/`。
- v15 原樣封存，標為「已連結、因 113 不出貨」。v15 名下的量測（產品路徑網、連結紀錄）照舊綁在 v15 的 manifest 上，不重新歸屬。
- 第 19 節的損失因此**照字面成立**：指名 SC／JP／KR／HK 的文字畫繁中字形、行高與 v8 相同。另補一條登錄（**推論**，未逐像素驗證）：沒有語言標記的中文在 v8 是用 KR face
  的字形畫的（量到的：預設亞洲字型解析到 KR；推論的部分：KR face 的 cmap 把漢字對到韓國字形），v16 改為繁中字形——對台灣使用者是預期中的改善，但它是一個像素差異。

### 20.3 判準更正：第 19 節的 tile 判準撤回

第 19 節「同一顆連結、只差 CJK 包的對照 profile，語料頁面 tile 逐張相同——只要那頁的字都在 E 級裡」**前提不成立**：完整 TTC 上沒有語言標記或標
日韓簡的漢字本來就畫成非繁中字形，所以大部分語料頁面在任何單一家族或五家族子集上都不會逐張相同。依「撤回宣稱，不要造機械去維持它」，撤回該條，
不補機制。

取代它的（形式一，逐實例；**草案，在任何會算進它的執行之前定稿**）：語料裡每一份文件，在 v16 與完整 TTC 的對照 profile 上，**每一頁的行位置相同**
（以畫布逐列墨帶的上緣比對，容差在定稿時依一次空跑量到的同 profile 重複差異決定）。它抓得到 113 這一類（行高或換行改變），而不被字形差異淹沒；
字形涵蓋（E 級以外的字畫成缺字方塊）照舊由 `build_cjk_subset.py` 的語料覆蓋檢查負責。若這條永遠沒跑：結論是「v16 的版面只在探針 fixture 與
產品路徑網的 fixture 上量過與 v8 相同」，不得外推到語料。

### 20.4 順序更新（取代 runbook 第 4 節的 profile 名）

第 4 節的 1、2、2b、3 改在 v16 上做：WASM 驗證（B 的 merge shakedown）、產品路徑網 v16 對 v8（v15 那一輪的兩處紅已歸因，v16 要重跑才算數）、
20.3 的語料版面比對、凍殼層 v56、計數。宿主 0.2.8 的 `check_m3_assets.py`（Z2-2、「Z2 D」寫死 `cjk-r5`）要改成 v16 的包名。頁面的 `workerUrl`
與 `PINNED_WASM_SHA256` 最後一起改到 v16（wasm 與 v15 相同，pin 值不變，變的是 worker 路徑）。

## 21. 追加（2026-10-07，任何語料版面執行之前）：20.3 的定稿方式、候選量測的頁面

### 21.1 候選量測改讀 cutover 的頁面（擁有者選 A）

產品路徑 runner 的 `--candidate-profile` 原本 repoint `dist/e2-editor-app.js`（v8 時代的頁面），`build_cutover_page.py` repoint
`web/e2-editor-app.js`；兩份差 63 行 diff。`3ab4f04a` 起兩者 import 同一個常數 `CUTOVER_PAGE_SOURCE`，候選模式另外要求其餘殼層模組與
`e2-editor.html` 在 `dist/` 的那份等於原始碼，否則拒跑。所以 20.4 的「產品路徑網 v16 對 v8」在 `3ab4f04a` 之前的報告**不算** B 的頁面的量測。
merge runner 與 `compare_layout_corpus.py` 也改讀同一個常數。

### 21.2 20.3 的定稿方式（寫在空跑之前）

20.3 的容差「依一次空跑量到的同 profile 重複差異決定」**不夠**：v16 的五家族子集把每個家族都畫成同一套 E 級字形（繁中字形），完整 TTC 的對照
profile 依語言標記畫日、韓、簡字形，墨帶上緣可能因此差一兩個像素——這個差異同一個 profile 重跑量不到。113 那一類（行高、換行改變）是**逐行累積**
的（第 n 行約偏 0.2 × n × 行高），字形差不累積。定稿：

| 項 | 內容 |
| --- | --- |
| 比較單位 | 每一份可比的文件（語料 76 份；打不開的三份壞 zip 與任何打不開的文件列為不可比，**兩臂的不可比集合必須相同**） |
| 判準（形式一，逐實例） | 墨帶數相同，且每一條墨帶上緣的差 ≤ T |
| T | 空跑（同一個 profile 量兩次，不同的瀏覽器 session）量到的最大上緣差 ＋ 2 px。2 px 是字形差的容許，**不是量出來的**；超過它的差異在計數比較裡就是紅，要看過才能說是什麼 |
| 非空洞（紅案） | 同一次空跑另量 v15（一個家族的子集＝113 的成因，wasm 與 v16 相同）：在 T 之下，**至少一份含中日韓字元的文件**對 v16 必須不同；**不含**中日韓字元的文件預期全部相同（若有不同，那是第二個變因，要登錄並解釋，不是藏起來） |
| 紅案不紅時 | 本判準不得使用；結論退回 20.3 的「從來沒做時」 |
| 計數比較 | v16 對 `e2-editor-v15-cjk-r5-ab`，每一份可比文件都過 |

T 由空跑決定之後，**以追加段寫進本文件、commit，才跑計數比較**。空跑本身不算數。

## 22. 追加（2026-10-07，merge WASM runner 的 opus 對抗性審核之後、任何計數 M2 之前）

審核對象：`tools/run_merge_wasm_shakedown.py`（`5555e554`）的設計。五個 BLOCKING 都經主 session 對原始碼與資料核對成立（B1 清單手寫且只有兩份文件；
B2 只判 outcome／stage／keyPosted；B3 目標段落不在時標記檢查反轉——run 2 的 F01 就是 `textIsOriginalPlusMarker: true`、`markerSurvived: false`；
B4 toast 在 0.5 秒安靜後就讀，C15 的第二句沒讀到；B5 見下）。這一節只寫判準層的處置，runner 照它改；改完之前 runner 只能做不算數的 shakedown。

### 22.1 判準更正（取代 4.3 與 10.2 的對應文字）

| 判準 | 更正 | 理由 |
| --- | --- | --- |
| M2-1「`restorePresses` 等於 R0 的」 | **撤回**，改為每一個完成的 `restorePresses` **等於 0**（欄位缺 → 紅） | E 形（16.2）沒有不帶 Shift 的還原鍵；R0 的「2 下」屬於被取代的處方。照字面，九個帶標號的 case 在正確的 v16 上會紅（run 2 的 I02＝0）。等於 0 守的是「舊處方沒有回來」 |
| M2-2「每一下還原的等待也都 < 1000 ms」 | **撤回** | 引擎不回報逐步等待，E 形也沒有還原下數。延遲照 10.2：runner 自己量送鍵（**緊接在刪除鍵之前**取起點，Y 型的 `x` 不算進去）→ 完成事件，加上 `keyToUndoMs` |
| M2-1／M2-3 的清單 | 由工具從 `merge-native/r0c/eshape.json` 產生（三輪：boundaries、boundaries-indent、PMPC，共 37 個 case）：`merge`／`typed-merge` → M2-1（31 個）；`nothing-selected`、`refused-k1-*`、`refused-k2-*`、`key-noop` → M2-3（今天 C15 C16 C17 C29 C30）；`barrier`（G01）→ 期望 `verified-selection-delete`（10.2 R0）；**其他任何判讀 → runner 停下**。計數執行不接受 `--cases` | 4.3 的形式本來就是「工具封閉（清單由 R0 產生）」 |
| PMPC 那一輪 | 照跑。文件只從 `wasm_sdk_probe/build/` 讀；存下來的文件只放在 `build/`；報告與證據裡**只有雜湊與段落序號，沒有段落文字** | 擁有者的文件不進 repo（常設規則） |
| 每一條各自判（B2） | M2-1：`verified-key-undo`；`keyUndo.comment`＝原生鍵臂 `undoAfter` 最上面那筆的 comment；`restorePresses`＝0；generation 不變；鍵後文件＝原生鍵臂（位元組比較等 M2-0 的化約落地，之前那一條記 NE，段落文字照比）；續打 `Z` 的段落文字＝原生 key-follow；沒有任何 toast。M2-3：stage／keyPosted；generation ＋1；重開後的段落文字＝原文＋標記（標記目標段落必須恰好出現一次，否則停下）；`#s-checkpoint` 的 revision 等於按鍵前的 revision；toast 序列見下一列 | 審核 B2 |
| toast 的讀取窗（B4） | 以正向事件關窗：generation 已前進，**而且**重開那一句的結尾句（「已重新載入」或世代上限那一句）已出現；逾時（90 秒）該 case 紅。關窗後：`keyPosted:true` 的那一臂沒有任何一句含「沒有被改動」；除了重開流程自己的兩句，沒有別的 toast | 審核 B4 |
| 比較器紅案（10.2 M2-1） | 照 10.2，第三個改成「把一個預期的 `restorePresses` 竄改成 2 → 紅」 | 隨上面第一列 |

### 22.2 縮限（撤回宣稱，不造機械）

- **§12 的同 session 位元組比較不可實作，撤回**：產品頁面不公開引擎 handle，「不經 session 的引擎存檔」拿不到；若在按鍵前用產品的存檔，重開會讀到
  權威位元組而不是拒絕當下的檢查點（`narrow-editor-v2-session.js` 的 `_openFresh`），比較就被自己破壞。M2-3 改為：段落文字＝原文＋標記，**且**
  generation ＋1，**且**檢查點 revision＝按鍵前的 revision。登錄極限：重開前後的非文字損失（樣式、清單、框）M2-3 看不到。
- **4.3「獨立頁面＋假宿主」→ 獨立頁面、不接宿主**（檔案選取開檔、下載存檔）。假宿主是新機制；宿主的存檔路徑是 R 的事（4.4，`check_m3_production_ui.py`
  在真宿主上的併段臂）。登錄：M2 對宿主存檔路徑不作任何宣稱。
- **文字框（18.1 N1）不進 M2-1／M2-3 的清單**，改為登錄的一次性量測（形式三）：`text-frame.odt`（綁 fixture 雜湊與 `r0c-frame` 那一輪）的 F01、F02，
  預期 `anchor-mismatch`、`keyPosted:false`，重開後標記還在。逼出它的量測：shakedown 第 1、2 次的 F01（Chrome）。從來沒量時的結論：「B 在文字框裡
  不合併；不作宣稱」。runner 在框內 case 的原生判讀不是 `merge` 時停下（那表示原生那一側變了，這條登錄的前提跟著失效）。
- **儀器（審核 Q1／S6）**：計數執行在加了觀察器的頁面上跑；只有觀察器看得到的條款（completion、comment、stage、keyPosted、restorePresses）在報告裡標成
  「在加了儀器的頁面上觀察」。每個瀏覽器做一次**不加觀察器**的配對對照（同順序；比 generation 的轉換、關窗後的 toast 序列、存下來的文件的段落文字），
  登錄為一次性量測；對照與儀器版不一致時，計數結果不得引用。觀察器只保留最近的回覆（有總數）並且只在內容改變時才寫 DOM。

### 22.3 更正 22.2 的「不加觀察器的配對對照」（同日，實作時發現）

「不加觀察器」做不到：放置游標（`place()`）判斷落點用的是觀察器回報的引擎游標，拿掉觀察器就沒有任何一格能放到原生的位置。改為：對照組的觀察器
**只記游標與文件大小**——不包 `postMessage`、不記任何回覆（`--control`）。審核擔心的兩件（每則訊息的序列化成本、請求的包裝）都在對照組裡拿掉；
留下的游標監聽兩組相同，所以對照證明的是「回覆記錄與請求包裝沒有改變行為」，不是「觀察器整個不存在時也一樣」——後者登錄為量不到。
比較由 `run_merge_wasm_shakedown.py --pair 儀器版.json 對照.json` 離線做：每個 case×輪的 generation 轉換、關窗後的 toast 序列、存下來的文件的段落文字。
對照組裡只有儀器看得到的條款（outcome、stage、keyPosted、comment、restorePresses）記 NE。

## 23. 追加（2026-10-07，產品路徑網第一次量 B 的頁面之後、任何計數 M2-5 之前）：M2-5 改成逐格判準

逼出它的量測：`59b3fb4c`（同一個 runner sha、v8 與 v16 交錯、各三輪）。Firefox 的 `clear-format-removes-every-inline-format`：v8 1 PASS／2 NE，
v16 3 NE；同一格在當天早上的 v8（另一個 runner sha）是 3 NE。NE 是前置條件沒成立而放棄判斷（`everyFormatWasOn`：打字當下四種格式全開），
`allOnWhenTyped` 每一輪都不同、兩個 profile 都如此。放棄的分佈在 v8 自己身上就不穩定，所以 4.3 的「含 PASS／NE 的分佈逐格相同」在三輪的計數裡
是擲骰——它會讓正確的 v16 紅，也可能讓有問題的 v16 碰巧綠。

更正（取代 4.3 M2-5 的「含 PASS／NE 的分佈」；形式一，逐格、每個瀏覽器）：

| v8 在該格 | v16 必須 |
| --- | --- |
| 每一輪都 PASS | 每一輪都 PASS |
| 有 FAIL | FAIL 的輪數不多於 v8 |
| 有 NE、沒有 FAIL | 沒有 FAIL（PASS／NE 的比例列出、不判） |

任何一格出現 v8 沒有的 FAIL → 紅。登錄極限：v8 會放棄判斷的格子（Firefox 上沒有 CDP 的 11–12 格、以及上面這格）對 v16 不作宣稱——若 v16 的退步
正好表現成「前置條件更常不成立」，這條看不到。從來沒做時：v16 沒有產品路徑的判定。

## 24. 追加（2026-10-07，任何計數 M2 之前）：M2-0 的結果與化約

**量到的**（`findings/evidence/v16-shakedown/merge/shakedown-chrome-3`，v16、Chrome、頁面 `b003534c…`；WASM 載入＋存檔、不編輯，對原生 R0c 那一輪的
`original.odt`）：四份輸入的 `content.xml` 都**位元組不同、段落文字相同**。差異（`xmllint --format` 之後逐行比）：

| 輸入 | 差異 |
| --- | --- |
| boundaries、boundaries-indent、text-frame | 只有一處：根元素 `office:document-content` 上 namespace 宣告的**順序** |
| 擁有者的文件 | 同上，加上：原生多一個空的 `<office:forms form:automatic-focus="false" form:apply-design-mode="false"/>`；`<text:soft-page-break/>` 的位置不同（約二十處——分頁點是版面，WASM 用的字型不同） |

**第 5 節的 M2-0 預測錯兩處**：「合成文件相同」不成立（三份都差在 namespace 順序）；擁有者文件的差異不在「自動樣式或字型宣告」，在表單宣告與分頁點。

**化約**（只從上表推出，`run_merge_wasm_shakedown.reduce_content`）：①根元素的 `xmlns:*` 依名稱排序（其餘屬性原順序）；②移除空的 `<office:forms …/>`；
③移除 `<text:soft-page-break/>`。化約後四份 M2-0 位元組相等。

**非崩塌證明（10.2）**：工具封閉的 32 個 case（M2-1 31＋barrier 1）裡，化約後原生「按鍵前」與「鍵臂」文件**沒有一對變成相同**
（`reduction_collapses()` 回空；單元測試 `Reduction.test_no_case_collapses`）。化約本身的紅案：namespace 的值、段落文字、根元素的其他屬性、段落的樣式屬性，
任何一個改了都還是不同；兩個突變（排序拿掉、把根元素屬性全丟）都被測試抓到。

**於是**：M2-1 的「存出來的 `content.xml`（化約後）等於原生鍵臂的」從 NE 變成一條會判的條款（`afterKeyBytes`）。同一次執行的前 14 個 merge／barrier case，
化約後**逐位元組等於 Writer 自己按鍵的文件**（未計數的 shakedown，只是這條判準第一次有資料，不是它的判定）。登錄極限：③讓 M2-1 看不到分頁點的差異——
那是版面的事，由 20.3／21.2 的語料版面比對負責，不由 M2 負責。

## 25. 追加（2026-10-07，任何計數 M2 之前）：擁有者文件移出 M2-1（擁有者選 B，依事先寫好的規則退回 A）

逼出它的量測：merge shakedown 第 3 次，擁有者文件 11 格全部 `placement-mismatch`——WASM 上同一位置的行高與原生不同（276／414 對 348／521 twips），
原生座標放不回去，沒有按鍵。擁有者選 B：原生 R0c 改用 v16 profile 的字型與 fontconfig 重跑（`findings/evidence/merge-native/r0c-wasmfonts/`，
預測先 commit）。結果：W1 命中（合併判讀不因字型改變，11 格 `merge`、0 KILL）；**W2 沒中**——原生在 WASM 的字型下 11 個游標與系統字型那一輪逐 twip
相同，正向對照（`strace`：帶設定只開了 WASM 那 7 個字型檔）證明設定確實生效。差異在 WASM 引擎那一側，登錄為 finding 114。依預測寫好的規則，B 退回 A：

- **M2-1 的母體縮為兩份合成文件**（boundaries 16＋boundaries-indent 4＝20 個 merge，加 barrier G01）；M2-3 不變（5 個，都在 boundaries）。
  22.1 的「三輪 37 個 case」改為「兩輪 26 個 case」。runner 以 `--owner-document` 仍可跑擁有者文件，只作診斷，不進任何判準。
- **擁有者文件上的合併**由兩處負責：原生（R0c 與本輪 W1：E 形在這份文件上 11 格都等於 Writer 自己的鍵）；真宿主上的 R（4.4，
  `check_m3_production_ui.py` 的併段臂在這份文件上跑，位置由那支 runner 自己決定、不依原生座標）。登錄極限：WASM 上擁有者文件的 11 種交界
  （含標題、帶標號段落）沒有逐格的 WASM 量測。
- 非崩塌證明（24）照舊涵蓋擁有者文件（文件在本機時）：`reduction_collapses()` 仍回空。

## 26. 追加（2026-10-07，任何 v17 的建置與量測之前）：finding 114 的修法；擁有者選「現在修、出 v17」，修法形式由 fable 裁決＝拿掉 `35-lang-normalize.conf`

逼出它的量測：finding 114 的判別探針（`findings/evidence/114/fc-debug/`，預測先 commit 於 `58c512cf`）、原生單一變因重現（`native-repro/`）、
opus 對抗性審核（`findings/evidence/114/review/`）。成因：base 包的 `conf.d/35-lang-normalize.conf` 把 LibreOffice 以字串送出的語言用子字串
`contains` 改寫（`zh-tw`→`tw`），字型名不在 profile 裡的 zh-TW 段落主字型落到 Liberation，行高約為桌面版 0.79 倍；LO 能送出的 282 個語言碼有 66 個
被改寫。啟用這份規則的是上游 LibreOffice 的打包（`external/fontconfig/ExternalPackage_fontconfig_data.mk:34`）。v8、v16 都中。

### 26.1 決定

- 擁有者（2026-10-07）：**現在修**，新身分 v17，在 v16 的 cutover（v56 凍結、計數 M2、宿主 0.2.8）之前；今天在 v16 上做過的 shakedown 改在 v17 上重跑。
- 擁有者問我時，我說的修法是「另一個包多放一條規則、不動 base」。審核指出窄規則只修 3 個語言碼、留 63 個；擁有者把修法形式交 fable 裁決。
- **fable 裁決＝拿掉 `35-lang-normalize.conf`**（重建 base 包少這一個檔）。理由：①「小包加規則」的前提在樹上不成立——worker 的資源包載入器只收
  `/instdir/share/fonts/truetype/` 底下的路徑（`sdk/sdk-worker.js:597-603`、`:639-642`；v16 的 worker 就是這份，`00882139…`），要放 conf.d 檔就得放寬
  worker 的允許清單＝換 worker 身分；base 包由 Emscripten 自己的載入器經 `locateFile` 取，沒有這道限制；②35 對 LO 只會是恆等或破壞（LO 只送
  `FcGetLangs()` 的成員；fontconfig 從環境推出的弱綁定預設語言也在規則之前插入、同樣被改寫），普查 66→0；③上游 fontconfig 預設不啟用 35、Ubuntu
  只放 conf.avail，拿掉它就是上游 LO 該有的修法；④另造 66 條規則去抵銷一個不該啟用的檔，是第 4 條（撤回宣稱，不造機械）禁止的形狀；⑤重新下載的代價
  是 base 包 zstd 5.5 MB，cutover 本來就要換 wasm（30.7 MB）與 CJK 包。
- **我先前的錯**（登錄）：我說「CJK 包能多放一個 conf.d 檔在技術上可行」，只讀了 `create_pack` 能放多個檔，沒讀 worker 收不收那個路徑。

### 26.2 v17 的定義

v16 的 `probe.js`、`probe.wasm`、`sdk-worker.js`、export 清單（皆為 v15 封存，`SHA256SUMS` 驗證）、`cjk-sub-e5`、`fallback-fonts-r5` 不變；
`artifactFiles` 的 `soffice.data`／`soffice.data.js.metadata` 換成新包 `base-r5-no35`＝`base-r5`（1,241 筆）去掉
`/instdir/share/fontconfig/conf.d/35-lang-normalize.conf`（48,949 bytes）那一筆。名字帶差異（不沿用 `base-r5` 的 stem）。只改這一個變因：
同時「順手」拿掉 `65-khmer.conf` 等其他檔是禁止的。

### 26.3 驗證判準（v17；寫在任何 v17 量測之前）

| 項 | 判準 | 形式 | 紅案 |
| --- | --- | --- | --- |
| V1 對帳 | 新 metadata 的檔案清單＝舊清單恰好少 35 那一筆；其餘每一筆的位元組與舊包對應切片 sha 相同；`remote_package_size` ＝ 34,129,451；從既有 base 包切與從原始 `soffice.data` 切得到同一個 sha | 二 | 以任何其他丟棄清單建的包必須不過 |
| V2 普查 | 從**出貨的包**（metadata＋data，不從建置樹）抽出 fontconfig 設定，以絕對路徑引入 conf.d，用 LO 自帶 fontconfig 2.18.2 跑 `census.py`：改寫 0 | 二 | 同一工具對 v16 的包必須印 66；並證明規則真的載入了（不能是相對路徑又讀到系統規則） |
| V3 引擎側 | `probe_fc_debug.py` 在 v17：conf.d 載入 21 個、沒有 35；思源黑體那次**主字型**查詢（請求沒有 charset）帶 `lang` 含 `zh-tw`、最佳比對是 Noto Sans CJK 的某個 face（記下哪一個；審核 N3 說是 KR／JP 不是 TC，v16 上度量與 cmap 相同） | 一 | v16 同一支探針：主字型查詢 `lang` 是 `tw`、答 Liberation（＝今天的 run1） |
| V4 版面 | 113 的字型槽 fixture，Chrome 在 zh-TW 與 en-US 兩種 locale 各跑一次（以頁面的 `navigator.languages` 與 log 的 `familylang` 證明 locale 真的換了）：TW-SIYUAN／TW-PMINGLIU／TW-XIMINGTI／TW-KAI 由 15–16 變 20；TW-TC、TW-DEFAULT、SLOT-TC 維持 20；LATIN-DEFAULT 維持 16；兩種 locale 的 pitch 表逐格相同 | 一 | v16 同一 fixture 的四列是 15–16（＝run1） |
| V5 擁有者文件 | merge WASM runner `--owner-document`（診斷，不計數）在 v17：引擎游標高度由 276／414 變成原生 R0c 的 348／521 twips；11 格的 `placement-mismatch` 改變類別 | 一 | v16 上是 276／414、11 格 `placement-mismatch` |
| V6 重跑 | 產品路徑網 v8 對 v17（同一 runner sha、交錯、三輪×兩瀏覽器，依 §23 逐格判）；merge WASM shakedown（Chrome 與 Firefox）；語料計數比較的對照組改為 `e2-editor-v17-cjk-r5-ab`（v17 只把 CJK 包換回 `cjk-r5`），以維持 20.3／21.2 的單一變因 | 一 | 各自的判準既有紅案 |

N2 的預測（寫在跑之前；**推論，不是量測**）：弱綁定的預設語言在 zh-TW 瀏覽器上由 `tw` 變成 `zh-tw`；拉丁文字不受影響，因為 `49-sansserif` 一定補上
通用家族、`60-latin` 的偏好清單（Liberation）在 FAMILY_WEAK 排在 `65-nonlatin`（Noto）之前，而 FAMILY_WEAK 的權重高於 LANG_WEAK。V4 的兩種 locale
就是用來量它；拉丁列若移動，那是 finding，不是調整的理由。

登錄極限：其餘 65 個被改寫的語言碼是**由建構**修好的（V2 普查），不是由版面量測；閩南語、客語的文件不在任何 fixture 裡，不得寫成「量過」。
§25 的「退回 A」是在未修狀態下寫的；V5 若讓擁有者文件回到可放置，要不要把它放回 M2-1 另寫追加段並寫理由，不在本節預設。

從來沒做時：v17 沒有驗證，不得 cutover；v16 仍是候選，finding 114 為具名保真極限。

上游（照例擱置送出）：①LO 的 `ExternalPackage_fontconfig_data.mk` 應去掉 35（它的清單由 `find` 讀範本目錄產生，所以 703466d7 說「照 Ubuntu」卻留下了 35）；
②fontconfig：35 的 `contains` 遇到字串型別的 `lang` 是子字串比對（`src/fccfg.c:1134`）；③LO 的 `Substitute` 可改以 langset 加語言（要連結，不在本輪）。

## 27. 追加（2026-10-07，語料空跑之後、任何計數語料比較之前）：21.2 的 T 定稿；零墨帶的讀數不算「相同」

逼出它的量測：`findings/evidence/v16-shakedown/layout-corpus/`（`56888919`；預測先 commit）。L1–L4 全中：v16 對 v16 的 71 份可比文件最大上緣差
**M＝0 px**、墨帶數全同；v16 對 v15 兩組都有 7 份含中日韓字元的文件超過門檻（最大 39 px，`e1/a11y-audible.odt`），27 份不含中日韓字元的全同；
不可比集合三次相同（3 份壞 zip ＋ 2 份開檔 `LOK_ERROR`）。預測點名的 `t1-plain-zh.odt` 沒有動——L2 命中但「哪幾份會動」預測錯，照實登錄。

### 27.1 T

**T＝M＋2＝2 px**（21.2 的定義）。

### 27.2 更正：零墨帶的讀數是「沒量到」，不是「相同」（形式一，逐文件）

同一次空跑裡 **23 份可比文件三次都讀到零條墨帶**（`unsettled: true`、`page: [-1, -1]`、`runs: []`；多數是 `r7-finding-012/t2-*`、
`t2-styled` 系列）。21.2 的判準「墨帶數相同，且每一條上緣差 ≤ T」對兩個空清單**空洞地成立**，所以上面的 L1–L4 其實只建立在 48 份有墨帶的文件上
（在那 48 份上 M 仍是 0）。補（取代 21.2「比較單位」中「每一份可比的文件」的範圍，不改判準本身）：

| 項 | 內容 |
| --- | --- |
| 沒量到 | 任一臂讀到零條墨帶或 `unsettled` 的文件列為**沒量到**，不進「相同」也不進「不同」 |
| 集合條件 | 兩臂的「沒量到」集合必須相同；不同就是紅（一臂畫得出來、另一臂畫不出來本身就是差異） |
| 報告 | 計數比較的結果要寫出「量到的文件數」；判準只對量到的文件下結論 |
| 登錄極限 | 這 23 份文件在這支儀器下沒有版面比較；成因（版面還在變、儀器讀不到頁框，或別的）**未診斷** |

### 27.3 T 套用到 v17 的計數比較

§26.3 V6 把計數比較改為 `e2-editor-v17` 對 `e2-editor-v17-cjk-r5-ab`。T 沿用 2 px：M 是儀器在同一顆 wasm、同一套打包方式下的重複差異，量到 0；
v17 對 v16 只差 base 包裡一個 fontconfig 規則檔（§26.3 V1），不改變儀器讀畫布的方式。紅案（儀器看得見 113）在 v16／v15 上已成立，不重做。
若 v17 對 v17-cjk-r5-ab 的計數比較裡出現「沒量到」集合與本次不同，先當儀器問題查，不得直接判 v17。

從來沒做時（不變）：結論退回 20.3 的「從來沒做時」。

## 28. 追加（2026-10-08，任何 v18 的建置與量測之前）：v17 的 V5／V6 紀錄；語料紅的成因（finding 116）；擁有者選 A＝CJK 包補五個 Mono 面，新身分 v18

### 28.1 v17 的 V5／V6 紀錄（§26.3 不改）

- **V5 中**（11／11，Chrome 一輪，`findings/evidence/v17/v5/`）。E02 的 `afterKeyBytes` 紅是 finding 115，不屬於 V5 的判準。
- **V6 產品路徑網中**（P1–P3；§23 紅格 0／84；P4 是描述性的，有兩格 Firefox 不同）；**merge shakedown 中**（Chrome、Firefox 各 56／56，`--pair` 0 差，兩邊比對到的文件各 98 份）；
  **語料計數比較 VERDICT RED，一份**（`test-docs/e1/paragraph-content.odt`，最大 4 px，`findings/evidence/v17/layout-corpus/`）。
- 所以 **v17 的 V6 未過**，v17 不 cutover。

### 28.2 語料紅的成因（finding 116，已量）

那一段的西文字型是通用字族 `monospace`。fontconfig 標準規則 `65-nonlatin.conf` 的 monospace 偏好清單裡，唯一的 Mono CJK 面是 `Noto Sans Mono CJK KR`。
完整 TTC（對照組、出貨的 v8）有這個面，就答它；v15 起的子集沒有任何 Mono 字族，就答 Liberation Mono。兩臂送出的請求相同、答案不同；把該槽直接指名為 Liberation Mono，兩臂 27 條帶完全相同；
v8 與對照組逐條相同（`findings/evidence/v17/layout-corpus/fc-request/`，預測先 commit）。

**波及範圍是觀察，不是判定**（`findings/evidence/v17/mono-reach/` M2：兩次執行的正向對照各有一條照字面落空，Q2 未正式判定）：宣告為固定字距的 細明體／MingLiU，v17 的兩個槽都答 Liberation Mono。
原因是 fontconfig 2.18 的通用字族準則排在語言之前，而子集裡唯一被歸類為等寬的就是 Liberation Mono。這兩行各矮約 5 px，與 114 的症狀同形（推論）。擁有者的文件與整份語料都沒有固定字距宣告（讀 XML）。

### 28.3 決定（擁有者 2026-10-08 選 A，依據 M1 的代價與 M2 的觀察）

- 新 CJK 包 **`cjk-sub-e10`**，一個 10 面、表格共用的 collection，面的順序同完整 TTC：
  - 前五面：`cjk-sub-e5` 的五個 Sans 面，逐表相同（`head` 除 `checkSumAdjustment` 外也相同）；
  - 後五面：從完整 TTC 的 Mono TC 面（face 8）切**同一份 E 級碼位**、用同一組子集選項，再依 JP KR SC TC HK 命名。每一面的 `name` 記錄要與完整 TTC 對應地區的原始 Mono 面相同。
    沿用 §20.2 的作法：五個名字共用 TC 的字形。
- 字型檔換新路徑 `/instdir/share/fonts/truetype/NotoSansCJK-Regular-subset-E10.ttc`，不沿用 e5 的路徑，避免任何依路徑的快取把新內容當成舊檔。
- **新身分 `e2-editor-v18`＝v17 的一切（wasm `ad3f68bb…`、loader、worker、export 清單，皆為 v15 封存；`base-r5-no35`；`fallback-fonts-r5`），只把 `cjk-sub-e5` 換成 `cjk-sub-e10`。不連結。**
  v17 保留，標為「因 116 不出貨」；v17 名下的量測照舊綁在 v17 的 manifest 上，不重新歸屬。
- 理由：
  1. 代價是 zstd 多 0.14 MB（M1；宿主的參數就是 level 19、8 MiB 視窗）、gzip 多 6.2 MB、檔案系統多 7.2 MB；
  2. 一次修掉語料紅，以及觀察到的固定字距那條路；
  3. 單一變因，不需要連結。
- 單一變因的對照組不變：語料比較仍以 `e2-editor-v17-cjk-r5-ab` 為對照（它與 v18 只差 CJK 包）。

### 28.4 驗證判準（v18；寫在任何 v18 量測之前）

| 項 | 判準 | 形式 | 紅案 |
| --- | --- | --- | --- |
| W1 包 | 建置工具 `--check`：兩次建置逐位元相同；第 28.3 的逐表條件全部成立；Mono 子集通過子集工具自己的 `verify`（對 face 8：cmap、hmtx／vmtx、每一個輪廓）；包的 zstd −19 大小 ≤ `cjk-sub-e5` ＋ 300,000 位元組（超過就停，交回擁有者——決定的依據變了） | 二 | `--check` 對「改掉一個 Sans 面的一個表」與「改掉一個 Mono 面的一筆 name 記錄」都必須不過 |
| W2 身分 | v18 的 manifest＝v17 的 manifest 只差 CJK 包那一筆；profile 的 `probe.js`／`probe.wasm`／`sdk-worker.js` 與 v17 逐位元相同 | 二 | 任何其他差異 |
| W3 引擎側 | fc-request 的 `one_session` 在 v18 開 A：K1 答 `Noto Sans Mono CJK KR`（同對照組）；conf.d 21 個；log 掃描到新路徑 | 一 | v17 答 Liberation Mono（已量） |
| W4 語料 | 語料計數比較 v18 對 `e2-editor-v17-cjk-r5-ab`（同一支工具、同一個判讀器、§21.2＋§27）：VERDICT 不是 RED；「沒量到」的集合與 v17 那次相同 | 一 | v17 那次 RED（已量） |
| W5 固定字距 | mono-reach 的探針在 v18：細明體／MingLiU 每個請求的答案字族與對照組相同；探針六行的帶位與對照組的差 ≤ 2 px、帶數相同。儀器存活條件＝PC-M2a′ 拿掉 Courier New 那一條（它不經 fontconfig，已量），再加 PC-M2b | 一 | v17 在這支探針上兩槽都是 Liberation Mono、少一條帶（已量兩次） |
| W6 重跑 | 產品路徑網 v8 對 v18（同一 runner、交錯、三輪×兩瀏覽器，§23 逐格）；merge WASM shakedown（Chrome 與 Firefox，`--pair` 要寫比對到的文件數）；V5 的擁有者文件在 v18（同 §26.3 V5 的條款） | 一 | 各自既有的紅案 |

- 判準 W4／W5 若有任何一份文件或任何一行紅：先依 116 的方法查（看請求與答案），**不得調整 T 或判準**。
- 從來沒做時：v18 沒有驗證，不得 cutover；v17 依 28.1 也不得 cutover。要不要改走「v17＋116 為具名極限」（選項 B 的形狀），由擁有者另行決定，本節不預設。
- 登錄極限：
  - M2 的 Q2 沒有正式判定；真實文件是否宣告固定字距，未知；
  - Mono 面以 TC 字形帶 JP／KR／SC／HK 的名字（與 §20.2 相同的取捨）；
  - 記憶體多 7.2 MB 與開機時間沒量；
  - 只收 gzip 的瀏覽器下載多 6.2 MB。
- cutover 鏈（交接 Next 4）之後改以 v18 進行：頁面 sha 依 v18 重算，宿主 0.2.8 的 CJK 包 pin 改為 `cjk-sub-e10`。

### 28.5 更正與補登（2026-10-08，opus 對抗性審核之後、W4 與 W6 的 merge／擁有者文件／語料各步開跑之前）

逼出它的是 `findings/evidence/v18/review/opus-review.md`（無 BLOCKING），第 1、5、8、10、14 項。這是在滿足之前新增，依第 9 條；計數語意：不歸零，因為這些條款都還沒有被滿足過。截止：W4 那一次執行落地。

- **W4 更正（取代 28.4 W4 的「VERDICT 不是 RED」）**：判讀器要 **exit 0、VERDICT PASS** 才算過。STOP（exit 2，輸入不是判讀器預期的）＝**沒做**，不是過。
  原文讓 STOP 也滿足判準（審核第 1 項）。
- **W1 補記**：
  - 大小條款是由人比的，工具只印出數字：5,748,639 − 5,604,052 ＝ 144,587 ≤ 300,000，成立（`evidence/v18/w1-w2/README.md`）。
  - `--check` 只比對包的檔名，沒有比對磁碟上的位元組（審核第 5 項）。磁碟上的 `cjk-sub-e10` data 的 sha256 已對過封存的 `SHA256SUMS`，相同（`evidence/v18/identity-during-chain.txt`）。
  - 工具改成真的比 sha、真的比大小，留到串接跑完之後再做。理由：改工具會讓 v18 的 make 目標過期，量測進行中不得重新打包。
- **登錄極限補三條**：
  1. 子集的 Mono KR 面比完整的少涵蓋 5 個語言：`bin gn ig ko miq`（審核第 7、8 項，讀 fontconfig 的 log）。語言標記是這幾個的 monospace／固定字距請求，**推論**在 v18 與對照組會答不同的面（未量）。
     所以 W3／W5 的「v18 與對照組相同」**只對那兩支探針成立**，不是一般性質。韓文（`ko`）在 E 級子集本來就沒有字形，從 v15 起就是這樣。
  2. 「與對照組相同」不等於「與 v8 相同」。v8 在固定字距這條路上因 114 而不同（探針上差到 7 px）。v18 對 v8 在固定字距文字上沒有任何比較（審核第 10 項）。產品路徑網 v8 對 v18 是唯一的 v8 比較。
  3. **大小要和出貨的比**（取代 28.3 理由一與 28.4 登錄極限裡「多 7.2 MB／多 6.2 MB」的說法；那兩個數字是對從未出貨的 v17 而言）。對照的是 v8 的 `cjk-r5`，即宿主 0.2.7 出貨的那一份：
     - 原樣 19,484,784 → v18 的 14,384,632；
     - zstd 12,170,785 → 5,748,639；
     - gzip 約 15.5 MB → 約 12.45 MB（e10 的 gzip 沒有直接量過，用的是 M1 的 E5+M5 數字）。
     **v18 的 CJK 包三種量法都比出貨的小**（審核第 14 項，數字讀自 `~/Projects/Nextcloud_Apps/litecore/engine/MANIFEST.json`）。

## 29. 追加（2026-10-08，W4／W6 判定之後、任何 cutover 動作之前）：v18 的 §28.4 全部成立

依 §28.4（`37525eec`）與 §28.5（`c073478d`）。證據在 `findings/evidence/v18/RESULT.md`；預測與判準在串接開跑前 commit（`15eca506`、Amendment 1 在 `c073478d`）。本節只記錄結果，不改任何判準。

### 29.1 結果

| 項 | 結果 | 依據 |
| --- | --- | --- |
| W1 包 | 過 | `evidence/v18/w1-w2/`（大小條款由人比：＋144,587 ≤ 300,000，§28.5） |
| W2 身分 | 過 | 同上 |
| W3 引擎側 | 過 | `evidence/v18/w3-w5/` |
| W4 語料 | **過**：判讀器 exit 0、VERDICT PASS；「不可比」5 份兩臂相同；「沒量到」23 份與 v17 那次同一組；量到 48 份全在 T＝2 px 內，最大差 1 px | `evidence/v18/layout-corpus/judge-output.txt` |
| W5 固定字距 | 過（只對這支探針） | `evidence/v18/w3-w5/` |
| W6 重跑 | **過**：產品路徑網 §23 紅格 0／84；merge 兩瀏覽器各 56／56、`--pair` 56 對 0 差異（比對文件數兩邊各 42＋42＋14）；擁有者文件 11 格游標高度、x、y 逐 twip 等於原生，合成 26／26 | `evidence/v18/{product-path,merge,v5}/judge-output.txt` |

串接前後各雜湊一次 v18 的 manifest、CJK 包、metadata 與對照組 manifest，四者都等於封存值（`identity-during-chain.txt`、`identity-after-chain.txt`），所以這些執行是關於 v18 的證據。

### 29.2 「過了」的意思

- §28.4 的「從來沒做時」預設不再適用於 v18：v18 有驗證。
- **cutover 不因此自動發生。**它會改產品頁面與宿主，照例要擁有者核可。cutover 鏈照 §28.4 末條：殼層凍新 generation、頁面 sha 依 v18 重算、宿主 0.2.8 的 CJK 包 pin 改 `cjk-sub-e10`。
- 計數的 M2 沒有做：3 輪 × 2 瀏覽器；M2-1b、M2-2、M2-4 還不在 runner 裡。以上 W6 都是未計數的 shakedown。
- 沿用的極限不變：§28.4 的四條登錄極限，加上 §28.5 的三條（`bin gn ig ko miq`；「與對照組相同」不等於「與 v8 相同」；大小對出貨的比）。

### 29.3 判讀工具

merge 與擁有者文件兩段的判讀器（`evidence/v18/merge/judge.py`、`evidence/v18/v5/judge.py`）**不是**在串接前寫的。

- merge 的判讀器寫於 Chrome merge 跑完、看過它 stdout 的結果清單之後；擁有者文件的判讀器寫於該步開跑之前。
- 判準本身沒有在這時候寫或改，兩支判讀器裡的期望值都抄自 `PREDICTION.md`。
- 兩支都先重判 v17 的紀錄，得到與 v17 的 RESULT 相同的結論；紅案各 7 個與 9 個，每個都只紅在它改動的那一格。

## 30. 追加（2026-10-08，任何 M2-1b／M2-2／M2-4 的程式碼與執行之前）：擁有者的兩個決定；三項判準的落地參數

### 30.1 決定（擁有者 2026-10-08）

- **cutover 之前先把計數 M2 補齊**（擁有者選 A）。先把 M2-1b、M2-2、M2-4 寫進 runner，經過紅案自證、對抗性審核與不算數的 shakedown；之後才走 cutover 鏈。
  cutover 鏈的順序是：凍 v56 → `make` dist → 綁定（§7）→ 計數 M2-0～M2-4 → 宿主 0.2.8 → R。
- **擁有者文件維持移出 M2-1**（擁有者選 A，§25 的現狀）。它仍只作診斷、不計數；finding 115 另案處理。§26.3 末段「放回要另寫追加段」因此不寫。

### 30.2 落地參數（判準本身不動，只把它們沒寫死的參數釘住）

| 判準 | 落地 | 從來沒做時 |
| --- | --- | --- |
| **M2-1b**（10.2） | **母體**：工具清單裡判讀為 `typed-merge` 的 case。清單由 `r0c/eshape.json` 產生，不手寫；今天是 Y01、Y02。<br>**次數**：每個瀏覽器、每個 case 各 10 次，N＝20。<br>**手勢**：runner 現有的 Y 型——真鍵打 `x`，緊接著真鍵 Delete，不等輸入轉接器、也不等引擎游標。<br>**每一次各自判 M2-1 的全部條款**（§22.1）：`verified-key-undo`、comment、`restorePresses`＝0、generation 不變、鍵後與續打 `Z` 的段落文字＝原生鍵臂、沒有 toast；位元組照 §12 不比。<br>任何一次拒絕或重開都算紅。§13.3 的「LOK 忙 → 拒絕＋重開」若出現，正是這條要量到的東西。 | 照 10.2：v18 不可出貨 |
| **M2-2**（10.2、22.1） | 讀計數執行的報告，不另外執行。<br>**非空洞**：每個瀏覽器 M2-1 的完成數＝20 個 case × 3 輪＝60，兩個瀏覽器共 120；不等就是沒做。<br>**門檻**：每一個完成的 runner 量測延遲（緊接刪除鍵之前起算，到該刪除的回覆）< 1000 ms，**且**引擎回報的 `keyUndo.keyToUndoMs` < 1000 ms。<br>M2-1b 的 40 次另外列出，用同一門檻判。 | deadline 不得宣稱有餘裕 |
| **M2-4**（4.3、10.2） | **fixture**：`test-docs/merge/odt/undo-limit-105.odt`（`09b5ced0…`），case H03，即 R0 第 4 輪（Steps＝100、PRESSES＝105）。<br>**每個瀏覽器一輪**：先跑 M2-0（載入＋存檔＝原生 `original.odt`，化約後）。再放到原生 H03 的游標，連按 105 下真鍵 Delete，每一下等到該刪除的回覆才按下一下。<br>**每一下都要**：`verified-key-undo`；comment＝`Delete paragraph`；`restorePresses`＝0；generation 從頭到尾不變；沒有 toast。<br>**非空洞**：`actionsAfter` 在第 100 下或更早到達 100，之後每一下都維持 100；沒到達就是「上限沒量到」＝沒做。<br>**最終文件**（獨立於引擎回報）：化約後的 `content.xml` 與段落文字都等於原生第 105 下的鍵臂。原生三輪在第 100、104、105 下的 `content.xml` 逐位元組相同（已核對，原文 107 段 → 105 下之後剩 2 段）。 | 「到上限仍可靠」只在原生成立 |
| **M2-1 紅案**（4.3） | 同一支 runner、同一份 cutover 頁面原始碼，`--candidate-profile e2-editor-v8`。工具清單的前三個 M2-1 case（今天 C01、C02、C03），每個瀏覽器各跑一次；每一個都必須**不是** `verified-key-undo`（109 的拒絕＋重開）。 | runner 不得用來宣告 M2-1 |
| **計數執行**的定義 | `--counted`：工具清單（M2-1 20 個＋M2-3 5 個＋barrier G01）跑 3 輪，Chrome 與 Firefox 各一次。<br>每個瀏覽器配一次參數相同的 `--control` 對照（§22.3），`--pair` 0 差異，比對文件數照常寫明。<br>計數執行不接受 `--cases`、`--frame-cell`、`--owner-document`；文字框是 §22.2 登錄的一次性量測，擁有者文件依 30.1 不計數。<br>綁定照 §7：wasm、worker、v56 的 session、頁面、`eshape.json` 的 sha256，在凍 v56 之後寫進 runner 常數。 | 沒有計數的 M2 |

- 這一節之前沒有任何 M2-1b、M2-2、M2-4 的程式碼或執行；判讀它們的工具要先有紅案。
- 預測另外寫在 `findings/evidence/` 底下，在 shakedown 與計數執行之前 commit。

## 31. 追加（2026-10-08，finding 117 的診斷之後、任何 v19 連結與任何計數 M2 之前）：117 的處置；M2-4 加每下延遲；出貨身分改為 v19

### 31.1 依據

- **擁有者 2026-10-08 確認 fable 對 117 的裁決全部採用**（原文 `findings/evidence/v18/review/fable-ruling-117.md`）。
- **診斷**（`findings/evidence/v18/diag-117/RESULT.md`，預測跑前 commit）：
  - 慢的 102 下，鍵送出之後到期限為止**一個 LOK 回呼都沒有**；
  - 沒有步驟遺失，所以修法只要讓按鍵這一段自己去讀；
  - 打字後併段那 628 ms 是同一件事。
- **引擎修法**：`66e5c0af`，`MergeAwaitingKey` 每 15 ms 重讀 `.uno:Undo`，期限 2000 ms 不變。已做語法檢查與 M1-1，**未連結**。
- **toast 不是 117**，是 finding 118：文件少一頁時，頁面照舊高度要圖，判成沒畫進去；之後畫布也停在舊高度。修在頁面，不進連結。

### 31.2 M2-4 追加一條：每下延遲

- **條款**：M2-4 的 105 下，每一下都要同時滿足：
  - runner 量到的延遲 < 1000 ms（緊接該下 Delete 之前起算，到該刪除的回覆）；
  - 引擎回報的 `keyUndo.keyToUndoMs` < 1000 ms。

  與 M2-2 同門檻、同形式。
- **非空洞**：105 下每一下都要有這兩個數字，少一個就是沒做。
- **第 9 條的四個條件**：
  1. 先於滿足：沒有任何計數 M2 存在，而 v18 上這一條不成立（每下 2000 ms，已量三次）；
  2. 被逼出而且指名：finding 117；
  3. 形式一：逐實例性質，每一下各自成立；
  4. 截止：計數 M2-4 落地即封閉，之後的顧慮寫成 finding。
- **計數語意**：不歸零，因為沒有任何已計數的 M2。
- **紅案**：`evidence/v18/m2-shakedown/m2-4-{chrome,firefox}.json` 與 `evidence/v18/diag-117/m2-4-chrome.json`，照這一條都必須紅（102 下 ≥ 1000 ms）。
- **從來沒做時**：「在空白段落上連按 Delete」只在 v18 量過，每下 2 秒；v19 沒有證明，不得宣稱 117 已修。
- **`noToast` 照 §30.2 原文保留，不收窄**。toast 的處置是修頁面（finding 118），不是改判準。
- **M2-1b 不加新條款**：M2-2 已用同一門檻判它的 40 次（§30.2）。

### 31.3 出貨身分改為 v19（取代 §30.1 (a) 鏈裡的 v18）

- **v19 的組成**：
  - 新連結的 `probe.wasm`／`probe.js`（含 `66e5c0af`）；
  - 其餘與 v18 逐位元相同：`cjk-sub-e10`、`base-r5-no35`、`fallback-fonts-r5` 三個包，`sdk-worker.js`，export 清單。
- **不搭任何其他引擎改動**（裁決 §2）。
- **v18 不得 cutover**：M2-4 照字面在 v18 上是紅的（toast，以及 31.2）。
- **Makefile**：v19 規則照 v15 規則複製，不共用。M1-1 的工具要擴充：v15 與 v19 的 `probe_engine` 物件都必須與 BASE 不同，其他規則的物件都必須相同。
- **頁面**：118 的修法在凍 v56 之前落地，並先在 v18 上用 M2-4 驗。候選頁面的 sha256 依 v19 重算。
- **新順序**（取代 §30.1 (a) 的鏈）：
  1. 118 的頁面修法，並在 v18 上驗；
  2. 計數 M2 的判讀器與紅案；
  3. 對抗性審核：§30、§31、runner 各模式、引擎修法、頁面修法；
  4. 凍 v56，`make` dist；
  5. 擁有者連結 v19，封存（目錄名帶 worker 的 sha）；
  6. 綁定（§7）：`BINDING` 與 `test_nothing_is_bound_before_v56` 在同一個 commit 改；
  7. v19 一輪（31.4）；
  8. 宿主 0.2.8；
  9. R。

### 31.4 v19 的驗證判準（寫在任何 v19 量測之前；預測另寫在 `findings/evidence/` 底下，連結之後、執行之前 commit）

| 項 | 判準 | 形式 | 紅案 |
| --- | --- | --- | --- |
| X1 身分 | v19 的 manifest＝v18 的 manifest，只差 profile 名稱（`profile`、`sdkVersion`）與 wasm 的雜湊（`editorContract.wasmSha256`）。`sdk-worker.js`、三個包、metadata、export 清單與 v18 逐位元相同 | 二 | 其他任何差異 |
| X2 範圍 | M1-1（擴充後）exit 0：只有 v15 與 v19 的 `probe_engine` 物件與 BASE 不同；兩個非法定義組合都必須失敗 | 二 | 既有的 `--inject` 紅案 |
| X3 字型探針 | W3、W5 的探針在 v19 與在 v18 的結果相同（036：wasm 不是原始碼的函數，所以要量，不能推） | 一 | 各自既有 |
| X4 語料 | 語料計數比較 v19 對 v18，用同一支工具、同一個判讀器（§21.2＋§27）：判讀器 exit 0、VERDICT PASS；「沒量到」的集合與 v18 那次相同 | 一 | 既有 |
| X5 產品路徑網 | v8 對 v19，同一支 runner、交錯、三輪×兩瀏覽器，§23 逐格；候選頁面＝含 118 修法、指向 v19 的頁面 | 一 | 既有 |
| X6 擁有者文件 | V5 型診斷（同 §26.3 V5 的條款）在 v19 | 一 | 既有 |
| X7 計數 M2 | M2-0～M2-4 以綁定好的 runner 直接計數，含 M2-1b、M2-2、M2-1 紅案、31.2。<br>3 輪×兩瀏覽器，各配一次 `--control` 與 `--pair`（寫明比對文件數）。<br>判讀器 exit 0 且 VERDICT 行為過 | 一／二 | §30.2 各條的紅案；v18 的報告是 31.2 的紅案 |

- **從來沒做時**：v19 沒有驗證，不得 cutover。
- **X7 作廢的處理**：若 X7 因頁面或殼層的紅而作廢，換新的 generation（v57），不覆寫 v56。
- **預測**（不是判準）：
  - M2-4 105 下全部 `verified-key-undo`，每下引擎延遲 < 300 ms，沒有 toast，終態＝原生；
  - Y01／Y02 的引擎延遲掉到一般併段的 28–49 ms 一帶。

### 31.5 登錄

- **時鐘守衛沒有實作**（R0 第 5 輪只是建議）：同一毫秒按兩下不可能（每下 ≥ 37 ms，已量），所以登錄為具名極限，不是 v19 的項目。輪詢不改變比較（`merge_key_undo.hpp` 的 `judgeAfterKey`）。
- **「鍵沒有效果」（C17 型）仍要等滿期限才拒絕**（§8）：沒有改變這件事無法提早證明。輪詢不改這件事。
- **新的先後順序**：完成可能在鍵的 KEYINPUT 與 KEYUP 之間送出。KEYUP 不改文件，下一個 K1 也排在它後面。審核時要點名這一條。
- **打字後併段那兩個狀態回呼**（`.uno:DocumentRepair`、`.uno:Undo`）為什麼在 628 ms 才送出，沒有查，不影響修法。

## 32. 追加（2026-10-08，判讀器落地之後、任何 v19 連結之前）：X1 更正；判讀器、紅案的計數、M1-1 擴充的落地

### 32.1 X1 更正（取代 31.4 X1「只差 profile 名稱與 wasm 的雜湊」）

- **讀到的**（讀檔，不是量測）：v18 的 manifest 另外記了 `editorContract.loaderSha256`，也就是 `probe.js` 的雜湊。`probe.js` 與 `probe.wasm` 是同一次連結的產物；v8 → v15 那次 `probe.js` 從 `c382b834…` 變成 `46b2f40a…`（`handoff/RUNBOOK-relink-v15.md` 的連結紀錄）。照 31.4 的字面，正確的 v19 只要載入器跟著變就會紅。
- **更正**：v19 的 manifest 與 v18 的逐葉相同，只有四片葉子可以不同：`profile`、`sdkVersion`（只換名字）、`editorContract.wasmSha256`、`editorContract.loaderSha256`；後兩者各自必須等於檔案本身的雜湊。另加一條：**wasm 必須與 v18 不同**——相同就不是新的連結，修法不在裡面。載入器相同與否照實記錄（一次性），不是判準。`sdk-worker.js`、export 清單逐位元相同，目錄裡的檔名相同。
- **工具**：`wasm_sdk_probe/tools/check_profile_identity.py`。形式二：所有葉子由工具比，日後 builder 多寫一個欄位也會被比到，不必有人列。紅案 `tests/test_profile_identity.py` 11 支，其中一支是真的 v16 對 v18（包不同，而且共用 v15 的 wasm）。綠案是合成的。
- **第 9 條**：這是更正不是新增，撤掉的是一個會讓正確產物紅的字面；先於滿足（v19 不存在）；沒有任何計數，所以不談歸零。

### 32.2 判讀器（31.3 第 2 步）

- `wasm_sdk_probe/tools/judge_counted_m2.py`。X7 的「判讀器 exit 0」＝這支**不帶** `--uncounted` 的 exit 0。結束碼：0 全過、1 有 FAIL、3 沒有 FAIL 但有沒做到的、4 `--uncounted` 全過（永遠不是計數判定）。
- 它不讀 runner 的 `pass` 與 `clauses`，文件比較從存下來的文件重算，母體自己從 `eshape.json` 與本文件的數字（20／5／1）重建。
- **跑之前寫下的四個判讀決定**：
  - 30.2 紅案的括號（「109 的拒絕＋重開」）當成條款：放好了、被拒絕、generation ＋1。沒放好的 case 不算紅。
  - M2-4 不讀對照：30.2 只給計數執行配對照。
  - FAIL 先於 NOT DONE（結束碼 1 先於 3）：兩者都不是過，而已知的紅比沒量到的部分更有資訊。
  - 報告檔名由判讀器定，計數鏈照寫：`counted-B.json`、`counted-control-B.json`、`m2-1b-B.json`、`m2-4-B.json`、`red-B.json`。
- runner 的 M2-4 `pass` 也加上 31.2 的條款，免得判準紅的報告寫著 `pass: true`。判讀器不依賴它。
- 紅案：31.2 指名的五份 v18 報告放進合成的綠案目錄，各自 exit 1、只紅 M2-4、慢的 102 下。綠案是合成的（v18 報告的副本，M2-4 每下延遲換掉），已標明。證據 `findings/evidence/v18/counted-m2-reader/`。

### 32.3 紅案的計數（更正 30.2「計數執行的定義」的綁定列）

- 30.2 的紅案在 v8 上跑，而 §7 綁的 wasm、worker、頁面都是 v19 的，所以照原本的比較，紅案的報告永遠是「未計數」。
- 改為：紅案的 session、`eshape.json` 與**頁面原始碼**的雜湊等於綁定，就算計數；wasm、worker、改指過的頁面是 profile 自己的值，本來就不同。綁定因此多一個值 `pageSourceSha256`（改指之前的 cutover 頁面原始碼）。`run_merge_wasm_shakedown.py` 的 `is_counted`，有單元測試。

### 32.4 M1-1 擴充（31.3）

- `tools/check_merge_key_undo_scope.py` 改成「帶 B 的規則」可以有多條（預設 v15、v19），每一條都必須與 BASE 不同，其他規則都必須相同；兩個非法定義組合在每一條帶 B 的規則上都必須失敗。
- 結果（`5d77dc84` 為 BASE）：25 條規則、100 個物件，只有 v15 與 v19 的 `probe_engine.o` 與 BASE 不同。紅案三個都紅：只列 v15（v19 的物件不同）、把 B 注入 v8、把 v8 列成帶 B 的規則。證據 `findings/evidence/v19/pre-link/`。
- 登錄：v19 與 v15 的編譯命令除了目錄名逐字相同（`make -n -B` 比過），所以今天的樹上對 v15 跑 `make` 會編出含輪詢的物件；v15 的連結由 `refuse_unasked_relink` 擋住（`make -n` 讀過）。v8、v15 都不得帶 `ALLOW_FROZEN_RELINK=1`。

## 33. 追加（2026-10-08，v19 連結之前的對抗性審核之後）：判讀與綁定的收緊；登錄

審核：opus（BLOCKING 2）與 codex `exec -s read-only`（BLOCKING 8），同一份題目。兩席都**沒有**在引擎修法 `66e5c0af` 與頁面修法 `840794af` 本身找到缺陷；被打穿的全是檢查。逐條處置在 `findings/evidence/v19/review/DISPOSITION.md`，每一條都先由主 session 對原始碼核對過。這一節只寫判準層的部分。

### 33.1 X7「判讀器 exit 0」的意思（更正 32.2）

- 只有 **Chrome 與 Firefox 兩個都判、而且都過**才是 exit 0。少判一個瀏覽器時就算全過，也是 exit 4（「不是計數判定」），與 `--uncounted` 同級。
- 綁定的權威是 **runner 檔裡 commit 的 `BINDING`**，不是報告自己寫的。兩個瀏覽器的每一份報告都要：
  - 帶著這棵樹的 runner 檔雜湊；
  - 綁定等於 `BINDING`，欄位恰為 `BOUND_KEYS`，每個值都是 sha256；
  - 跑的時候服務的值等於綁定（紅案除外 profile 自己的三個值）。
- 事後重判，要 checkout 計數執行那個 commit。

### 33.2 綁定的欄位（更正 §7、32.3）

- 加 `shellSha256`：殼層 bundle 每一個模組服務出去的雜湊，入口頁面除外——它本身就是 `pageSha256`。
- 加 `htmlSha256`：頁面 HTML 在加入儀器之前的雜湊。
- 加 `nativeSha256`：fixture、R0c 兩輪的 arms 與文件、R0 第 4 輪的 arms／fixture／兩份參考文件，以路徑＋雜湊做成摘要。這補上 §7 寫了但一直沒做的「R0 的報告目錄與輸入 sha256」。
- 判讀器另外把 M2-4 的參考文件釘在 `content.xml` 雜湊 `60087d9401a68bf6`。那份檔案只在 `build/`，v18 的每一份 M2-4 報告都記錄了這個值。

### 33.3 條款的收緊（判準字面不動，守衛追上字面）

- **「沒有任何 toast」**（§22.1 M2-1、§30.2 M2-1b／M2-4）：讀取窗延伸到 case 的最後一次存檔之後。在那之前只准出現該 case 自己的存檔確認（`已存出 N KB`，M2-1 兩句、M2-4 一句）。舊的讀取點在第一次存檔之前，續打 `Z` 之後的重繪失敗讀不到。
- **「重開流程自己的兩句」**（§22.1）：必須依序是開始句與結束句，而且兩句的前導相同。不是「兩句都含『重新載入』」。
- **M2-3 的 generation ＋1**：關窗時讀到的值，與 90 秒安靜之後讀到的值，都必須是＋1。
- **配對對照**（§22.3）：比完整的 generation 轉換、關窗與否、讀到存檔之後的 toast、case×輪的順序，不只比最後的 generation。
- **延遲**（§30.2 M2-2、§31.2）：數字必須有限且 ≥ 0。
- **M1-1**（32.4）：逐物件判。帶 B 的規則只有 `probe_engine.o` 可以不同，而且必須不同。
- **X1**（32.1）：空陣列與空物件也算葉子。`gestures: []` 是扣住一個動作的寫法，刪掉它等於放出那個動作，舊的比較看不到。

### 33.4 登錄

- **§31.5 的「完成可能在 KEYINPUT 與 KEYUP 之間送出」**：兩席都讀到不會發生。輪詢只會落在 KEYINPUT、KEYUP 與鍵自己的同步回呼之後，因為三者在同一次 SolarMutex 持有裡跑完。真正換了先後的是 Writer 計時器送出的回呼，例如 D4 那兩個約 628 ms 的回呼，它們現在會在完成之後才到；頁面靠 `document-invalidated` → 重繪吸收。這一條是**審核者的讀法，主 session 沒有讀 LOK 那幾行**。
- **§31.5 時鐘守衛的論證**用的是 v18 的「每下 ≥ 37 ms」，v19 會把這個數字壓低。X7 要印出引擎 `keyToUndoMs` 的最小值，論證拿那個數字重讀。
- **「117 修好了」不等於「按住 Delete 很快」**：M2-4 每下之間至少安靜 0.5 秒，沒有量按住的鍵；M2-4 與 M2-1b 也只在加了儀器的頁面上跑。
- **X1 的 wasm 條款只證明「換了一個檔案」**，修法在不在裡面是 X7 的 M2-4 證明的。
- **v19 的打包規則讀 `build/`**：封存之後若要重新打包，規則要改指封存（像 v16～v18 那樣）。
- **頁面**：尺寸變了之後 `paint()` 在 `layoutCanvas()` 之前跑，IME 的 sink 會停在錯的位置，直到重繪完成。這是 069 那一面、成長路徑上本來就有，這一輪不改。
- **`run_shrink_repaint.py` 的 GREEN** 比 118 的 P3 文字窄。P3 是從報告裡的數字確認的（沒有 toast、1,012／1,256 列）。之後守著 118 的是 X7 的 M2-4。

## 34. 追加（2026-10-08，任何綁定之前）：檢查機械凍結；停止規則（擁有者發問、fable 裁決 A′、擁有者採用）

**依據**：擁有者說「一直在修機械的缺陷」讓他擔心，交給 fable 裁決，原文在 `findings/evidence/v19/review/fable-ruling-machinery.md`；擁有者 2026-10-08 採用。

**裁決**：凍結檢查機械，直接去量，並補一條原本不存在的停止規則。

- **擔心「過程」成立**：審核 → 修 → 再審核沒有終點。題目「構造一個壞了但檢查仍綠的情境」對任何檢查都答得出東西；而每修一次都會移動 runner 的雜湊與綁定，正是讓執行作廢的那種事。
- **擔心「內容」不成立**：
  - 第 33 節修的 16 項，都是守衛追上已寫在本文件的判準，不是新判準；
  - 這套機械三天內抓到 113、114、116、117、118 五個產品缺陷；
  - 工具與產品的行數比反映的是「產品改動小而危險」。
- **不採 B（縮小閘門）**：省不了多少（v18 一整輪無人值守約 2 小時 40 分），又會推翻 30.1 的 A。
- **不採 C（照舊）**：它沒有工具讀得到的終止條件。
- **更正**：33 節處置時把「`close()` 拋例外」歸為偽造，應該歸為意外——收尾時瀏覽器崩潰。

### 34.1 凍結

- **範圍**：從設定 `BINDING` 的那個 commit 起，到讀出 X7 判定為止，不改以下工具：
  - `judge_counted_m2.py`
  - `run_merge_wasm_shakedown.py`
  - `check_profile_identity.py`
  - `check_merge_key_undo_scope.py`
  - 產品路徑 runner
- **例外只有兩個**：
  - (a) 誠實的執行崩潰（traceback、沒有報告）：修好，只重跑那一步。
  - (b) 有一份證人報告證明某個 FAIL 是判讀器的錯：修好，以那份報告當紅案，重判，不重跑。
- **從來沒做時**：X7 的判定照判讀器印出的算，紅的也算。

### 34.2 威脅模型

- **檢查要防的是誠實執行裡的意外**：
  - 旗標給錯；
  - `dist/` 過期；
  - 頁面被移動；
  - 漏跑一步；
  - 只跑一部分；
  - 瀏覽器崩潰；
  - 產生出來的檔案裡少了一個鍵。
- **不防**：
  - 偽造或手改的報告；
  - 被改過的常數；
  - 任何已 commit 的 runner 都產生不出來的報告。
- 需要上述輸入才成立的情境，不算檢查的缺陷，最多在 finding 索引登錄一行 NOTE，不寫程式。
- **從來沒做時**：每一個「壞了仍綠」的情境都要處理，迴圈沒有終點。

### 34.3 審核預算

- 每一支新的判讀工具，在第一次計數使用之前做一次雙席對抗性審核，之後不再審。計數 M2 判讀器這一次已經用掉了（`v19/review/`）。
- 之後的審核只針對產品改動。若要審檢查，題目改成「指出一份已 commit 的報告，它的判定會因此改變」，不再是「構造一個情境」。
- 判讀器被改寫超過一半，算新工具，可以再審一次。
- **從來沒做時**：不審；第一次計數執行就是它的測試，34.1 接受這個結果。

### 34.4 對檢查的意見要有證人

- 必須有一份誠實執行的、已 commit 的報告，證明檢查判錯或錯誤作廢了它，才可以改程式。否則只登錄一行，不寫程式。
- 每一份交接都列兩個數字：
  - 因執行而修的檢查數；
  - 因審核而修的檢查數。
- 34.3 的預算用掉之後，第二個數字不是 0 就是違規，不是 finding。
- **從來沒做時**：兩個數字沒人報，膨脹看不見，只剩 34.3 一道剎車。

### 34.5 綁定欄位停在九個

- `BOUND_KEYS` 維持九個。要加第十個，需要 34.4 的證人：一次因為那個沒綁的東西移動而被誤判的執行。
- 理由：每多一個鍵，就多一種讓執行作廢的方式。
- **從來沒做時**：九個。

### 34.6 判準文字不再長

- 守衛只能追上本文件已寫下的判準（33.3），不能追上新寫的文字；新判準只能照第 9 條的四個條件加。
- 33.4 的八項登錄維持登錄，沒有一項擋連結、綁定或 X7。
- **從來沒做時**：不加、不升級。

### 34.7 具名極限（34.4 套用在自己身上）

- 產品路徑判讀器在 MISS 時也 exit 0（`v18/RESULT.md` 的 Q3），它的判定是 `SUMMARY` 那一行。X5 的串接讀那一行，`judge.py` 的結束碼在那裡不算證據。
- 這一條的證人會是：某條串接把 MISS 當成過了。
- **從來沒做時**：讀那一行，登錄。

### 34.8 對接下來計畫的影響

- **順序不變，X1～X7 全留**：凍 v56 → 擁有者照手冊連結 v19 → 雜湊、X1、封存、M1-1 → 綁定（`BINDING` 與「v56 之前沒有綁定」的測試同一個 commit）→ 預測先 commit → X2～X7 → 宿主 0.2.8 → R。
- **X6 只是診斷**（§25、30.1），從來不擋任何東西；預測裡要寫明，放最後或並行跑。
- X7 若因檢查而紅，走 34.1(b)；真的要重跑，換 v57，不覆寫 v56（31.4）。
- **什麼都不刪**：九個鍵、`toastsAtEnd`、有序的重開兩句、逐物件 M1-1、空容器也算葉子的 X1，都是已測過、守著本文件既有判準的守衛。
- **也不再加**：計數之前不再做 shakedown，沒有第三席審核，不為判讀器再寫判讀器。
- **擁有者看得到的停止條件**：X7 之後交接裡的那兩個數字。「因審核而修」是 0、「因執行而修」很少且每項都有證人，比例就是相稱的。第二個數字往上長，就是規則被打破，擁有者可以直接叫停。

## 35. 追加（2026-10-08，X7 判讀之後、X5／X4／X6 跑完之前）：X7 的配對對照照 34.1 (b) 重判

**依據**：X7 第一次判讀紅在配對對照；擁有者選「先交 fable 裁決」；fable 判定 34.1 (b) 成立，照 A 處理但只限 `toastsAtEnd`（原文 `findings/evidence/v19/x7-counted-m2/fable-ruling-control.md`，`8d9004f8`）。這一節是記錄，不新增判準。

### 35.1 證人與量到的

- **證人**：`b8324a85` 的 v19 X7 報告，在綁定好的 runner 上誠實執行（`73b2e9ff…`）。原判讀器的結果是 exit 1，`VERDICT FAIL: ['chrome control', 'firefox control']`（`judge-output.txt`）。
- **其餘全部 PASS**：M2-1 60／60、M2-3 15、barrier 3、M2-1b 20、M2-2、M2-4、紅案、M2-0、身分，兩個瀏覽器都是。
- **紅的那幾對**：Chrome 2 對（C03 r1、r3）、Firefox 3 對（C10 r1、C03 r2、r3）。每一對唯一的 false 欄位都是 `toastsAtEnd`，內容只差「已存出 14.2 KB」對「已存出 14.3 KB」。
- **成因**（已讀檔）：
  - 頁面印的是 `(bytes.byteLength / 1024).toFixed(1)`。
  - 每次存檔，`meta.xml` 的 `dc:date` 與 `settings.xml` 的 `Rsid` 都不同，壓縮後差一兩個位元組。
  - C03 的檔案在 14,590～14,595 位元組之間，跨過 14.25 KB 的進位界線。
  - 同一臂不同輪也會跳（Chrome 對照組 C03：14.2、14.3、14.3）。
  - fable 核對過：四臂共 252 筆 `toastsAtEnd`，每一筆都等於保留下來那個檔案的大小照同樣算法得到的數字。
- **預測**：`PREDICTION.md:32` 的「pair 0 differ」，在原始配對上 **MISS**，在 34.1 (b) 之後才成立。

### 35.2 處置（只動判讀器）

- **改的範圍**：只有 `judge_counted_m2.py` 的 `control()`。`m.pair` 之後，一列只有同時滿足下面兩個條件才放過：
  - `toastsAtEnd` 是它唯一的 false 欄位；
  - 兩邊的清單把**完整符合** `SAVED` 的元素換成同一個記號之後相等。
  次數、順序、其他 toast 都照舊逐字比。輸出印出放過幾對、是哪幾對，原始差異看得到。
- **不改的**：runner（含 `pair()`）、`BINDING`、報告、保留的文件、`pair-*.stdout.txt`、原判的 `judge-output.txt`。`toasts` 欄位也不比照放寬：它沒有證人。
- **紅案**（`tests/test_judge_counted_m2.py` 的 `V19Witness`，用 commit 的 `BINDING`）：
  - (a) 證人目錄：PASS，exit 0；
  - (b) 一臂多一句「重繪失敗」：control FAIL；
  - (c) 一臂只有一次存檔確認：FAIL；
  - (d) 非存檔的 toast 只差一個數字：FAIL。
  四個測試模組共 119 個測試 OK。
- **重判**（不重跑）：exit 0，`VERDICT PASS (chrome, firefox; runner 73b2e9ff4b1e6fbe; page e00ab76a550dc12f; wasm 1aafd4f9da42fd83)`（`judge-output-rejudged.txt`，`0ce96b32`）。除了兩行 control 和 VERDICT 之外，與原判逐行相同。
- **審核**：不需要。34.3 的預算已經用掉，而這不是新工具，也沒有改寫超過一半；34.4 只要求證人。

### 35.3 具名極限（34.7 的形式）

- **runner 單獨跑 `--pair` 的結束碼不是判定，判讀器的才是。**`--pair` 仍會對這幾對印出 `toastsAtEnd: false`、exit 1（`pair-*.stdout.txt`）。
- 這一條的證人會是：某條串接把 `--pair` 的 exit 1 當成 X7 紅。

### 35.4 34.4 的兩個數字

- 因執行而修的檢查：**1**（證人＝v19 X7 的配對對照）。
- 因審核而修的檢查：**0**。

## 36. 追加（2026-10-08，X5 判讀之後）：§23 第一列更正為 1′；X5 的判定；P2 照 34.1 (b) 類推修正

**依據**：X5 照 §23 第一列紅了一格；擁有者選「交 fable 裁決」；fable 判定 X5 過，原文 `findings/evidence/v19/x5-product-path/fable-ruling-x5.md`（`6847b9ce`）。這一節照第 4 節處理：前提被證偽的判準要撤回或更正，不是補機制。

### 36.1 證人與量到的

- **證人**：`e2-editor-v19-firefox-r1.json`、`judge-output.txt`（`85334a1a`）。`SUMMARY  P1: HIT  P2: MISS  P3: MISS (red cells 1)`。
- **紅的那一格**：Firefox `recovery-returns-what-the-product-promised`，v8 3 PASS、v19 2 PASS 1 NE。
- **NE 的成因**：兩個誘因都沒觸發，回復路徑沒有走到，不是走到了失敗。
  - 038 的拖曳沒有卡住引擎（`finding038Reproduced: false`）。
  - Firefox 沒有 CDP，第二個誘因發不出去（`fallbackInducer.why`）。
- **普查**（`census_recovery_cell.py`，形式二，讀 git 已追蹤的報告；紅案四個 `selftest-census-output.txt`）。
  - Firefox：v8 18 次，16 PASS、2 NE；候選 23 次，21 PASS、2 NE。
  - Chrome：兩臂全部 PASS。
  - 從來沒有 FAIL。每一個 NE 都是兩個誘因都沒觸發，每一個 PASS 都至少觸發了一個，沒有例外。
- **第一列的前提被證偽**：第一列假設「v8 三輪都 PASS ＝這一格穩定會 PASS」。對這一格，本文件自己以前的資料就證偽了它：v15 那輪與 v17 那輪，v8 都在這一格放棄過。
- **推論，未量**：117 的引擎修法只在 `MergeAwaitingKey` 時輪詢；這個誘因只送拖曳和點擊、沒有邊界鍵，碰不到那個狀態。

### 36.2 更正：第一列′（取代 §23 表的第一列）

| v8 在該格 | 候選必須 |
| --- | --- |
| 每一輪都 PASS，**而且**視窗內的 v8 報告在該格沒有 NE | 每一輪都 PASS |
| 每一輪都 PASS，但視窗內的 v8 報告在該格有過 NE | 照第三列：沒有 FAIL；PASS／NE 列出、不判。屬 §23 的登錄極限 |

- **視窗**：git 已追蹤的 `findings/evidence/**/e2-editor-v8-<瀏覽器>-r*.json`，而且該格的紀錄帶有它現行語意的欄位。
  - 本格的欄位是 `observed.finding038Reproduced`（兩個誘因的語意，`ba84ec81` 起）。
  - **不是**裁決建議的 `observed.fallbackInducer`：只有第一個誘因沒觸發的紀錄才帶它，那個視窗裡只會有 NE，FAIL 和 PASS 都進不去。普查工具的第一版就用了它，結果紅案 (2)（放一個 FAIL）仍是綠的；那一版的輸出留著（`*-first-version.txt`）。
- **§23 的盲點照舊**：若候選的退步正好表現成「前置條件更常不成立」，這一條看不到。本格候選 2/23、v8 2/18，沒有顯示這件事。
- **第 9 條**（對這一輪之後的每一輪）：
  1. 先於滿足：寫在之後任何一輪 X5 之前；
  2. 被逼出而且指名：X5 v19 Firefox r1；
  3. 形式二：視窗與次數由普查工具從已 commit 的報告產生；
  4. 截止：下一輪 X5 的判讀器複本在執行前實作 1′，之後不再改這一列（34.6）。
- **計數語意**：不歸零。這一輪是照第 4 節更正，不重跑。
- **不做的**：不改產品路徑 runner、不重跑 X5、不對 NE 比例設門檻（34.6）、不拿這一節去重讀其他格。

### 36.3 X5 的判定

- **X5 過**：被宣稱的格子 0 格紅；1 格不宣稱（Firefox 回復，依 36.2）。判讀器印出的 `P3: MISS (red cells 1)` 留在紀錄上，判讀器的 P3 不改。
- **從來沒做時**：X5 照判讀器印出的算，是紅。

### 36.4 P2（照 34.1 (b) 類推）

- **問題**：本輪的判讀器複本（`v19/x5-product-path/judge.py`）沿用了 v17 的 `distPageWasTheSame is False`。那是 v17 時代的事實（當時 dist 服務的是比原始碼舊的頁面）。v56 凍結並 `make` 之後，dist 等於原始碼，六份 v19 報告都是 True。PREDICTION 的 X5.P2 沒有寫這個欄位，寫了的欄位都照預測成立。
- **處置**：只拿掉本輪複本的那一條，不換成 `is True`（欄位仍列在表裡）。v17 的判讀器與 `tools/` 都不動。
  - 紅案：修過的判讀器在 v18 已 commit 的執行上仍是 `P2: MISS`（`selftest-output-after-p2-fix.txt`）。
  - 重判：`judge-output-rejudged.txt` 是 `P1: HIT  P2: HIT  P3: MISS (red cells 1)`，其餘輸出逐行相同。

### 36.5 預測的不精確（登錄）

- `PREDICTION.md` 的 X5.P4 說這一格在 v18 那輪「已經在輪與輪之間變過」。實際上 v18 那輪兩個瀏覽器都是 3 PASS／3 PASS（`v18/product-path/judge-output.txt:93`）。變過的是 v17 那輪的 v8。不影響判定。

### 36.6 34.4 的兩個數字（到這一節為止）

- 因執行而修的檢查：**2**（X7 的配對對照，§35；X5 的 P2 複本，36.4）。
- 因審核而修的檢查：**0**。
- 普查工具第一版的視窗錯誤，是在第一次使用前被它自己的紅案抓到的，沒有任何執行或審核觸發它，所以不計入這兩個數字；照實寫在 36.2。
