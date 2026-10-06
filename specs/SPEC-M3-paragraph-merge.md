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
