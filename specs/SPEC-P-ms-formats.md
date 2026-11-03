# SPEC-P-ms-formats：開啟微軟文件

2026-11-02 擁有者的 demo 清單第 3 項原文：

> 開微軟文件（可參考 Collabora）

2026-11-03 18:45 擁有者選它當下一個 session 的工作（`handoff/HANDOFF-2026-11-03g-calc-undo-shipped-0255.md` 最後一節）。

本文件先釘**事實**（第 1～3 節：讀碼、Collabora 的作法、連結前的量測），再列**要擁有者決定的事**（第 4 節）。設計與判準等裁示後 append，判準在實作前釘死。本文件只准 append。

## 1. 現況（讀碼，2026-11-03）

### 1.1 宿主（`/home/jiajun/Projects/Nextcloud_Apps/litecore` @ `5db53ac`，0.2.55）

- `src/files.js`：檔案動作 `litecore-open` 只認 ODT 與 ODS 兩個 mime（`PAGES` 對照表），DOCX／XLSX 在 Files 裡根本不會出現「Open in LiteCore」。
- `lib/Controller/EditorController.php`：頁面表每頁**一個** mime（`e2-editor.html` → ODT，`ods-editor.html`／`ods-viewer.html` → ODS），`resolve()` 對不上就回 `not an ODT file`。
- `js/litecore-editor.js`：`documentFormat()` 由**頁面名稱**推出 mime 與副檔名，存檔的 PUT、衝突副本的檔名（`stem.replace(/\.(?:odt|ods)$/i, '')` 加 ODF 副檔名）都用它。
- 新增選單（0.2.54）只建 ODT／ODS，與本項無關。

### 1.2 頁面

- 有宿主時，頁面把 `HOST.load()` 給的檔名原樣交給引擎（Writer `openFromHost()`，Calc 第 638 行）。
- 沒有宿主時（鏡像）：檔案選擇器 `accept` 只有 `.odt`／`.ods`；Writer 下載檔名固定 `-v2.odt`，Calc 的 Blob 型別固定 ODS。
- Calc session 存檔固定 `format: "ods"`（`spreadsheet-shell/calc-editor-session.js:378`）；SDK 的預設是 `"odt"`（`sdk/document-sdk.js:772`）。

### 1.3 引擎（我們自己的程式碼）

- **開檔**：`oxsdk_document_open`（`src/sdk_api.cpp:117-141`）在進佇列之前就拒絕檔名——Writer 只收 `.odt`，Calc 的 profile 只收 `.odt`／`.ods`（`src/ods_viewer.hpp` 的 `acceptedSuffix`）。Writer 寫進 MEMFS 的輸入檔名固定 `.odt`（`src/probe_engine.cpp` 的 `writeInputFile`）。
- **存檔**：`oxsdk_document_save` 只收 `odt`（Writer）或 `ods`（Calc），之後 `saveAs(url, format)`；LOK 把 `docx` 對到 `Office Open XML Text`、`xlsx` 對到 `Calc Office Open XML`、`doc`／`xls` 對到 `MS Word 97`／`MS Excel 97`（`libreoffice-26-8/desktop/source/lib/init.cxx:298-334`）。
- 這就是 **finding 013**（2026-08-02，至今未關）：同一份合法 DOCX，名字叫 `.docx` 在 C ABI 前被拒，名字假裝 `.odt` 卻能開。當時的決定：**不准用假檔名宣稱支援**，要支援就做窄的 `format` 介面，讓驗證、MEMFS 路徑、manifest capability 三者一致。本文件沿用這個決定。

### 1.4 引擎裡**已經有**的（不用重編 core）

- 兩顆出貨的 wasm 都帶著 `com_sun_star_comp_Writer_WriterFilter_get_implementation`（DOCX／RTF 匯入）、`..._DocxExport_...`、`..._RtfFilter_...`、`com_sun_star_comp_oox_FormatDetector_...`；Calc 的 `ods-editor-v4` 另有 `com_sun_star_comp_oox_xls_ExcelFilter_...`（XLSX 匯入匯出）與 `..._ExcelBiffFormatDetector_...`。三棵 core 樹的 `soffice.js.linkdeps` 都有 `-lmswordlo -lsw_writerfilterlo -looxlo`，Calc 的另有 `-lscfiltlo -lscdlo`。
- 兩顆的檔案映像（`base-r5-no35`、`base-viewer-v3-no35`）的 registry 都有 `MS Word 2007 XML`、`Office Open XML Text`、`MS Word 97`、`Calc MS Excel 2007 XML`、`MS Excel 97` 的類型與濾鏡定義。
- 所以要改的只有**我們自己的引擎程式碼**（開檔、存檔的允許清單與 capability），要**連結**（Writer 一次、Calc 一次），不用重編 core。

## 2. Collabora 的作法（讀碼，2026-11-03）

來源：`cool-26-04`（COOL co-26.04）、`/home/jiajun/OSSII/ncdev_env/apps/richdocuments`（richdocuments 31.1.1，OSSII 的 fork；fork 自己改的地方另外標出）。逐條出處在 `findings/evidence/ms-formats/collabora-reading.md`。

- **哪些格式能編輯**：discovery 裡 doc、docx、docm、dotx、rtf、xls、xlsx、xlsb、xlsm、xltx、csv、ppt、pptx 都有 `edit`；dot、pot 只有 `view`。不在 `edit` 清單裡的副檔名一律唯讀。
- **存回什麼格式**：**原格式**。一般存檔與自動存檔都是 `.uno:Save`，不帶 FilterName，沿用文件開啟時的濾鏡，再用 WOPI PUT 寫回**同一個檔案**。只有使用者自己按「另存新檔」才會換格式。
- **格式警告**：COOL 前端只對 txt、csv、xlsb 一開始唯讀並提示「可能有內容無法以目前格式儲存，要不要存成 ODF」；**docx／xlsx／doc／xls 沒有任何警告**。core 的「保留目前格式」對話框在 LOK 下會不會跳出來，讀碼沒有定論。
- **舊式二進位格式（.doc／.xls）**：開檔不轉換，照樣編輯、存回原格式。
- **新增選單**：預設 ODF；管理員勾選 `doc_format = ooxml` 才改成建 docx／xlsx／pptx。
- **OSSII fork 自己加的**：`saveToOdf` 設定（預設 `yes`，管理介面叫「Automatically convert Microsoft Office files to ODF files」），在 CheckFileInfo 送出 `SaveToOdf = odt|ods|odp`。**原版 COOL 不讀這個欄位**，要配 OSSII 自己的前端才會生效。
- 密碼文件：開檔時詢問密碼；巨集：預設不執行。

## 3. 連結之前的量測（2026-11-03）

證據 `findings/evidence/ms-formats/`（英文 README）。兩支工具：

- **M0 原生**：`wasm_sdk_probe/tools/msformat_native.cpp`（LOK，原生 core 26.8 `build-native-26-8`，單檔 g++ 3 秒）與驅動 `tools/run_msformat_native.py`。每份檔案兩臂：真檔名、改成 `.odt`／`.ods`（現行引擎能接受的名字）。真檔名臂存三次——LOK `saveAs(原格式)`（引擎的存法）、用**匯入時的濾鏡** `storeToURL`（Collabora `.uno:Save` 的存法）、ODF——每份輸出再開一次。內容比對：Writer 依序的段落字串與表格儲存格，Calc 每張表每個非空格的 `getFormula()`。
- **M1 WASM**：`tools/run_msformat_wasm.py`，**現行出貨**的頁面與凍結 profile（Writer `e2-editor-v32`、Calc `ods-editor-v4`），不連結。因為 finding 013，每份都用 ODF 檔名交給頁面（**量測，不是產品路徑**）。透過頁面自己的宿主介面（`globalThis.liteCoreHost`，假宿主由 CDP 在頁面載入前放進去），按頁面的存檔鈕，把存出的 ODF 交給 M0 的原生 harness 讀，再和 M0 的「原生 ODF 來回」逐行比。只有 Chrome（Firefox 的 WebDriver 沒有載入前注入）。

語料 33 份（清單在 `run_msformat_native.py`，sha256 在報告裡）：LibreOffice QA 樹中 `docProps/app.xml` 寫著 Microsoft 的 7 份 DOCX、10 份 XLSX（表格、頁首、清單、圖、修訂、中日文；多工作表、公式、合併格、圖表、條件格式，一份 24 張表），QA 樹的 3 份 DOC、3 份 XLS，R7 留下的 10 份 DOCX（含一份截斷的負向對照）。

### 3.1 M0 原生的結果

- **開檔**：32／33；截斷的那份照預期失敗。開檔 28–241 ms。
- **類型偵測**：DOCX 15 份 `Office Open XML Text`、1 份 `MS Word 2007 XML`；XLSX 8 份 `Calc Office Open XML`、1 份 `Calc MS Excel 2007 XML`（第 10 份見下）；DOC `MS Word 97`；XLS `MS Excel 97`。
- **改成 ODF 檔名**：DOCX、XLSX、DOC 選到同一個濾鏡，內容相同；**XLS 選到範本變體** `MS Excel 97 Vorlage/Template`（內容相同）。所以 M1 對 DOCX、XLSX 有代表性。
- **存回原格式再開**：內容相同 30／32。不同的兩份：`n830205.docx` 多 2 個空段落（LOK `saveAs` 與沿用匯入濾鏡兩種存法一樣，位元組數相同——**濾鏡選擇不是原因**，引擎直接用 LOK 的 `saveAs` 即可）；`XlStartupExternal.xls` 的 54 格外部增益集公式變成 `=NA()`。Writer 頁數 16／16 不變。存 DOCX 4–37 ms、XLSX 11–269 ms。
- **存成 ODF 再開**：內容相同 29／31；不同的是公式參照大小寫（`a3:m25` → `A3:M25`，計算不變）與 100 格日期時間值的第 16 位數字。但**版面**：`n830205.docx` 從 7 頁變 11 頁；4 份 XLSX 的列高總和變了。存 ODT 91–859 ms、ODS 109–726 ms。
- **一份 XLSX 存成 ODS 後重開不會結束**：`forum-mso-en4-134670.xlsx` 匯入、存 XLSX、存 ODS 都在幾秒內完成，但重開那份 ODS，原生 LOK 跑滿 25 分鐘被砍；主執行緒在 `ScXMLImport::endDocument` → 列高 → `ScInterpreter::ScCountIf`，整欄範圍的 `COUNTIFS` 被逐格重算。桌面版 26.8.1.1 同一份檔也超過 14 分鐘、CPU 100%。上游的效能斷崖，記為 finding 184。

### 3.2 M1 WASM 的結果（現行出貨的引擎，不連結）

- 可開的 32 份**全部**打開，從導覽完成到就緒約 1.2–5.3 秒；截斷的 DOCX 進 `stopped`，通知列是技術字串 `LOK_ERROR：loadComponentFromURL returned an empty reference`。
- 存出的 ODF 與原生 ODF 來回**逐行相同**：可比的 31 份全部（DOCX、XLSX、DOC、XLS 都有）。`forum-mso-en4-134670.xlsx` 在 WASM 上 5 秒開好、存檔正常，比不了是因為讀它存出的 ODS 會撞上 finding 184。工具第一次跑時，取回內嵌字型那份 12.5 MB 的存檔撞到 CDP 1 MiB 上限（是工具的問題，頁面本身已經存好）；改成分段取回後，正式證據裡那份也相同。
- **結論**：出貨引擎的匯入不用改，濾鏡、類型偵測、執行緒都沒有問題。要改的是第 1.3 節的兩道邊界。**DOCX／XLSX 存回原格式在 WASM 上還沒量過**（存檔允許清單擋住），連結後才能量。

## 4. 擁有者裁示（2026-11-03）

1. **存檔格式：存回原格式**（DOCX 存回 DOCX、XLSX 存回 XLSX，寫回同一個檔，和 Collabora 相同）。**另外新增「另存新檔」，可以轉成 ODF。**
2. **範圍：DOCX＋XLSX。** DOC、XLS、docm、xlsm、rtf、csv、範本檔不在這一批。

## 5. 設計（2026-11-03，裁示之後、實作之前）

### 5.1 引擎（要連結：Writer 一次、Calc 一次；core 不動）

新 profile：Writer `e2-editor-v33`（接 v32），Calc `ods-editor-v5`（接 v4）。改動全部在新定義 `OXSDK_MS_FORMATS` 之下，只進這兩顆新 build。

- **E1 一份格式表**：新標頭 `src/document_format.hpp`，取代 `ods_viewer.hpp` 的 `acceptedSuffix` 在新 build 裡的角色（舊 build 的位元組不動）。封閉清單，大小寫不拘：

  | profile | 開檔接受的副檔名 | 存檔接受的格式 |
  |---|---|---|
  | Writer v33 | `.odt`、`.docx` | `odt`、`docx` |
  | Calc v5 | `.odt`、`.ods`、`.xlsx`（`.odt` 是 v4 既有行為） | `ods`、`xlsx` |

  其餘一律在進佇列前回 `INVALID_ARGUMENT`，`.doc`、`.xls`、`.docm`、`.xlsm`、`.dotx`、`.xltx`、`.rtf`、`.csv` 都在拒絕之列。
- **E2 MEMFS 輸入檔用接受時的副檔名**（Writer 目前固定 `.odt`）。M0 證實副檔名不影響 DOCX／XLSX 的濾鏡，但檔名要誠實，這是 finding 013 的處方。
- **E3 存檔**照舊 `saveAs(url, format)`；`docx`、`xlsx` 由 LOK 對到 `Office Open XML Text`、`Calc Office Open XML`。M0 量過，沿用匯入濾鏡的存法沒有差別。
- **E4 capability**：新位元 `OPEN_DOCX`、`SAVE_DOCX`（Writer），`OPEN_XLSX`、`SAVE_XLSX`（Calc）；manifest 對應 `open-docx`、`save-docx`、`open-xlsx`、`save-xlsx`。worker 的閘門：`save` 帶 `docx` 要 `save-docx`，帶 `xlsx` 要 `save-xlsx`（照 v4 worker 判斷 `save-ods` 的寫法）。
- **E5 開檔回覆帶 `format`**：接受時的副檔名（`odt`／`docx`／`ods`／`xlsx`）。頁面與 session 用它決定存檔格式，不各自從檔名再猜一次。

### 5.2 頁面（Writer 第 89 代殼層；Calc 頁面）

- **存檔用文件自己的格式**：`format` 來自 E5。Writer 工具列「儲存 ODT」改成「儲存」；沒有宿主時的下載檔名保留原副檔名。Calc 的 session 不再寫死 `"ods"`。自動存檔同樣存原格式。
- **另存新檔**：兩個頁面的工具列各加一顆「另存新檔」。按下去是頁面自己的對話框：
  - 檔名欄，預設是原檔名去掉副檔名；
  - 格式：**ODF（.odt／.ods）**，文件本身是 DOCX／XLSX 時另有「原格式」。微軟文件預設選 ODF（擁有者的用途是轉成 ODF）。ODF 文件只有 ODF 一項（等於存一份副本）；ODT 另存成 DOCX 不在這一批。
  - 確定後：引擎用選定的格式存一次，交給 `HOST.saveAs(bytes, { name, format })`。宿主說名字已被占用時，對話框留著並說明，不覆寫。沒有宿主時（鏡像）改成下載。
  - 唯讀文件不提供另存新檔（限制 `L-saveas-readonly`）。
- 檔案選擇器（鏡像）的 `accept` 加上 `.docx`／`.xlsx`。

### 5.3 宿主（0.2.56）

- `src/files.js`：DOCX mime（`application/vnd.openxmlformats-officedocument.wordprocessingml.document`）→ `e2-editor.html`；XLSX mime（`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）→ `ods-editor.html`。**唯讀的 XLSX 也走 `ods-editor.html`**，由 `load()` 的 `readOnly` 開成唯讀，因為檢視器 profile（`ods-viewer-v3`）不收 `.xlsx`，不為它另外連結。
- `EditorController`：每頁從「一個 mime」改成「一組 mime」；`ods-editor.html` 不可寫時轉去檢視器，只對 ODS 這麼做。
- `js/litecore-editor.js`：`documentFormat()` 改看檔案的 mime，不看頁面名稱；PUT 的 `Content-Type`、衝突副本的副檔名都跟著檔案。
- **`saveAs(bytes, { name, format })`**：在原檔同一個資料夾 PUT 新檔，`If-None-Match: *`；412 回 `NAME_TAKEN`，不寫。成功之後：放掉原檔的鎖，**改開新檔**（導向新檔的編輯器路由，`fileId` 取自 PUT 回應的 `OC-FileId`，沒有就 PROPFIND），這次離開頁面不詢問。原檔停在最後一次存檔的樣子。這和 richdocuments 另存新檔之後載入新檔的行為相同；好處是鎖、標題、網址、之後存檔的格式都走既有的開檔路徑，畫面上看到的就是新檔真正的內容（例如 7 頁變 11 頁會當場看到），代價是另存之後的復原紀錄不會留著。

## 6. 判準（實作前釘死）

**每一條都附「如果這件事永遠沒做」的預設結論：該項判 NOT_ESTABLISHED，不判過。**

### 6.1 連結之前（原生與靜態）

- **F1** `tests/document_format_test.cpp`（原生，不連 core）：表 E1 的每一格（接受與拒絕，含大小寫、只有副檔名的名字、比副檔名短的名字）。紅案：`tests/document_format_mutations.py` 逐條改表，每個突變都要有測試轉紅；突變清單由工具從表本身產生，不手列。
- **F2** 照 2026-10-28 的規則跑 `-fsyntax-only`（附正向對照）與 `-E` 的「匯出都有本體」檢查，兩顆 build 都跑。
- **F3** worker：`save` 帶 `docx`／`xlsx` 而 manifest 沒有對應 capability 時回 `UNSUPPORTED_OPERATION`；有的時候放行。node 測試，紅案是把閘門拿掉。

### 6.2 連結之後（鏡像，Chrome 與 Firefox，真檔名，經頁面自己的檔案選擇器與存檔鈕）

語料＝第 3 節 M0 清單裡的 DOCX 與 XLSX（工具自 `run_msformat_native.corpus()` 取得，不手列）。

- **W1 存回原格式**：每一份都打開；頁面存出的位元組是 OOXML（zip 裡有 `[Content_Types].xml`、沒有 `mimetype`）；用 M0 的原生 harness 讀它，內容與 M0 同一份檔的「原生原格式來回」相同。截斷的 DOCX 例外：要得到有型別的錯誤，頁面不卡住。
- **W2 另存成 ODF**：每一份另存出的位元組是 ODF（第一個成員是 `mimetype`，值對）；內容與 M0 的「原生 ODF 來回」相同。`forum-mso-en4-134670.xlsx` 因 finding 184 判 NOT_ESTABLISHED，不判過也不判紅。
- **W3 名字邊界**：`.doc`、`.xls`、`.docm`、`.xlsm`、`.rtf` 名字的檔案在 C ABI 前被拒（`INVALID_ARGUMENT`），worker 仍健康、下一次開正常檔成功。
- **W4 回歸**：兩個新 profile 上既有的 ODT／ODS 回歸網照舊全過（Writer 第 89 代的殼層檢查、Calc 的 cell、range、autosave、P2、C、CU）。
- **紅案**：W1、W2 在 v32／ods-editor-v4 上要紅（真檔名在 C ABI 被拒）。

### 6.3 宿主（`host_batch8.py`，Chrome 與 Firefox，擁有者的路：Files、真指標與按鍵、WebDAV 讀回）

- **H8/action**：Files 對 `.docx`、`.xlsx` 有「Open in LiteCore」並是預設動作，分別進 Writer、Calc 編輯器；`.odt`、`.ods` 照舊。
- **H8/save-docx**、**H8/save-xlsx**：打字（Calc 輸入一格）、存檔；WebDAV 讀回是 OOXML、含剛輸入的內容；檔名與 mime 不變；資料夾裡沒有多出別的檔案。
- **H8/autosave-xlsx**：Calc 自動存檔寫回的是 XLSX。
- **H8/save-as-odf**（Writer、Calc 各一）：另存新檔選 ODF；資料夾多出 `名稱.odt`／`.ods`，是 ODF、含編輯內容；原檔的 sha256 等於它最後一次存檔；頁面改開新檔（網址的 `fileId` 是新檔、標題是新檔名）；再存一次寫的是新檔。
- **H8/save-as-taken**：另存成已存在的名字，那個檔的 sha256 不變，對話框說明名字被占用。
- **H8/read-only**：唯讀分享的 DOCX、XLSX 開成唯讀，不取鎖、不能存、沒有另存新檔。
- **紅案**：同一支工具在 0.2.55 上要紅在 H8/action。
- **回歸**：Files 工作流 52/52、`H7_HOLDS`、T6、`HOST_BATCH_HOLDS`、`LAYOUT_HOLDS`。

## 7. 具名限制

- `L-ms-export-loss`：存回原格式有 LibreOffice 匯出本身的損失（M0：1／16 份 DOCX 多空段落）。Collabora 相同。同一個 session 裡重複存檔不會累積損失（每次都從記憶體的模型匯出，不重新匯入）；關掉再開就會再經過一次匯入。
- `L-no-format-warning`：存回微軟格式不提示「可能有內容遺失」，和 Collabora 相同。
- `L-ods-reload-cliff`：finding 184。整欄範圍 `COUNTIFS` 很多的 ODS 開不起來；另存成 ODS 會把這類 XLSX 變成開不起來的檔案。上游問題，不在本批修。
- `L-legacy-formats`：DOC、XLS、docm、xlsm、rtf、csv、範本檔不支援（M0／M1 量到它們打得開，但不在裁示範圍）。
- `L-saveas-ms-from-odf`：ODT／ODS 不能另存成 DOCX／XLSX。
- `L-saveas-readonly`：唯讀文件沒有另存新檔。
- `L-mislabeled`：副檔名與內容不符的檔案照內容開，照副檔名存（例如內容是 ODT、名字叫 `.docx`，存檔後就是真的 DOCX）。
- `L-corrupt-message`：壞掉的微軟文件，通知列是技術字串（`LOK_ERROR：…`），和壞掉的 ODT 相同。

## 8. 如果永遠沒做

Files 對微軟文件沒有「Open in LiteCore」；要先在別處轉成 ODF 再上傳。同事 demo 時只能開 ODT／ODS。

## 9. 追加 1（2026-11-03 21:15，連結與開發版冒煙）

- 擁有者要我代跑連結：`tools/link_ms_formats_owner.sh`，4 分 27 秒，exit 0，`LINKS_AS_SPECIFIED`。Writer `e2-editor-v33` wasm `444519df`（capability 位元 3147775），Calc `ods-editor-v5` wasm `4faad0af`（13629747）。開發 profile 在 `build/e2/editor-v33/profile`、`build/ods/editor-v5/profile`，**未凍結**。證據 `findings/evidence/ms-formats/link/`。
- 開發版冒煙（**不是第 6.2 節的 W 判準**：頁面仍是第 88 代與 v4 的 Calc 頁面，只會存 ODF）：`tools/smoke_ms_formats_dev.py`，Chrome，鏡像把頁面的 worker 改指開發 profile、Writer 頁面釘住的 wasm 雜湊改成 v33 的。證據 `findings/evidence/ms-formats/post-link-dev/`。
  - 真檔名：可開的 26 份 DOCX／XLSX **全部打開**；頁面存出的 ODF 與 M0 原生 ODF 來回相同 25／25（`forum-mso-en4-134670.xlsx` 依 finding 184 不可比）。截斷的 DOCX 打不開。
  - Calc 經頁面上的 session 直接存 XLSX：10／10 是 OOXML；內容與 M0 原生「存回原格式」相同 9／10。不同的一份是**外部連結**：原檔的目標 `file:///D:/%06personal.xlsx` 存檔時被改寫成相對於存檔位置的路徑——原生寫成 `../../../../../../../D:/%06personal.xlsx`，WASM 寫成 `../D:/%06personal.xlsx`——重開後解析到不同地方。原生也這樣改寫，所以不是 WASM 引擎的差異，是 LibreOffice 匯出把絕對檔案網址相對化的行為。新增限制 `L-external-links`（下）。
  - Writer 存 DOCX 還沒量：第 88 代頁面不對外露出 session，要等頁面改完（W1）。
  - 拒絕的名字 `.doc`、`.docm`、`.xls`、`.xlsm`：打不開，通知列 `INVALID_ARGUMENT：open was rejected before queueing`。
  - **紅案**（同一支工具，出貨的 v32／v4）：真檔名 27 份一份都打不開。
- 新增具名限制 `L-external-links`：活頁簿指向其他檔案的外部連結，存回 XLSX 時目標被改寫成相對於引擎暫存路徑（`/tmp/oxsdk-output-…`）的相對路徑，在 Excel 裡會失效。LibreOffice 原生也這樣（「相對儲存檔案系統網址」預設開）。不在本批修。

## 10. 追加 2（2026-11-03 22:10，頁面改完、W 跑之前）

### 10.1 實作時定下、5.2 沒寫到的設計

- **Writer 的存檔格式在 `editor-shell-v2` 覆寫。**`editor-shell/editor-session.js` 被 E1-C 判定綁住（`check_e1_c_bundle_intact.py`），它的 `save()` 與 `_checkpointBeforeSelection()` 寫死 `{ format: "odt" }`。`NarrowEditorV2Session` 覆寫這兩個方法：程式碼照抄基底，只把格式換成 `documentFormatOf(document)`（開檔回覆的 `format`，沒有就是 `odt`）；另加 `documentFormat()`、`saveCopy(format)`。基底凍結，所以抄本不會漂移；單元測試把基底的方法與覆寫並排跑在 ODT 文件上，要求同樣的請求與同樣的狀態。
- **checkpoint 也用文件自己的格式。**理由：checkpoint 會用文件的名字重開（`_openFresh` 傳 `_authorityName`），世代上限時 `takeContentForRescue()` 把它交給宿主寫回原檔。ODT 的 checkpoint 會把 ODT 位元組寫進 `報告.docx`。
- **SDK：**`DocumentHandle.format` 收開檔回覆的 E5；不是非空字串就是 `null`，不從檔名猜。
- **Calc：**引擎對 `.odt` 檔名回報 `odt`（v4 既有的路徑，5.1 E1 的表），但 Calc 存不了 `odt`。session 只採用 `ods`、`xlsx`，其餘（含 `null`）照 v4 存 ODS。
- **另存新檔是副本**：不清 dirty、不成為 authority 或 checkpoint，下一次存檔仍存原格式。有宿主時，`HOST.saveAs` 成功之後頁面不再存任何東西（宿主正在放掉原檔的鎖、改開新檔）。
- **另存新檔按鈕**在唯讀文件、以及宿主沒有 `saveAs()`（0.2.55 以前）時隱藏。
- **宿主介面**：`HOST.save(bytes, {…, format})` 多帶 `format`，讓宿主可以拒絕格式與檔案不符的位元組；`HOST.saveAs(bytes, { name, format })` 的 `name` 是完整檔名（含副檔名）。
- **沒有宿主時的下載**：Writer 存檔 `<主檔名>-v2.<格式>`（沿用既有的 `-v2`），Calc 用原檔名；另存新檔 `<輸入的名字>.<格式>`。
- **檔名欄**：去掉頁面認得的副檔名，再加上選定格式的副檔名；空白、含 `/`、`\` 或控制字元時對話框說明，不送出。

### 10.2 單元判準（已跑，2026-11-03 22:00）

- `editor-shell-v2/tests/ms-formats-session.test.mjs` 7 項、`tests/calc-ms-formats.test.mjs` 6 項，全過。
- 紅案 `tools/check_ms_formats_shell_mutations.py`：Writer 9 個、Calc 8 個突變，每個都紅在為它寫的那一項（第一版有一個存活：存檔前沒有 checkpoint，「存檔不清 checkpoint」看不出來；補了之後才全紅）。
- 既有：`editor-shell-v2/tests` 585/585、`tests/` 128/128、`sdk/tests` 131/131、`editor-shell/tests` 全過，E1-C intact，`check_calc_{format_entry,range,autosave}_mutations.py` pass。

### 10.3 W 工具

`wasm_sdk_probe/tools/run_ms_formats_w.py`，一個瀏覽器跑一份檔。鏡像是 dist/，兩個頁面與它們 import 的模組取自原始碼樹，profiles 加上兩個開發版的別名；Writer 頁面指向 v33（worker 網址與 wasm 釘選），Calc 指向 v5。沒有宿主：經頁面自己的檔案選擇器給**真檔名**，存檔是**真的瀏覽器下載**（Chrome `Page.setDownloadBehavior`、Firefox 下載偏好），從磁碟讀回。按鈕用真指標按。`--read` 只讀報告給判定。

### 10.4 W 的判讀（跑之前釘死）

- **W1**：每份可開的 DOCX／XLSX 都開成功；按「儲存」得到一個下載，是 OOXML；原生 harness 讀它，與 M0 同一份檔的原格式來回（`true-name/out/saved.<格式>.dump.txt`）相同。**唯一允許的差異**：兩份 dump 行數相同，且每一行不同的行在兩邊都是外部連結參照（`<格>\t='file:///…'#…`），同一格、檔名相同、`#` 之後相同——這是第 9 節量到的 `L-external-links`（`empty_ext_defined_name.xlsx`），連結目標被解析到存檔位置。其他任何差異都判 W1 不成立。
- **W2**：對話框兩個選項，ODF 在前且預選，原格式在後未選；確定後得到一個下載，第一個成員是 `mimetype`、值對；原生 harness 讀它，與 M0 的 ODF 來回相同。`forum-mso-en4-134670.xlsx` 判 NOT_ESTABLISHED（finding 184）：只驗位元組是 ODF，不讀。
- **截斷的 DOCX**：開不起來，通知列標紅、以 `代碼：` 開頭；之後同一頁開正常檔成功。
- **W3**：`.doc`、`.docm`、`.rtf`（Writer）與 `.xls`、`.xlsm`（Calc），內容是正常檔的位元組：開不起來、通知列含 `INVALID_ARGUMENT`；之後同一頁用真檔名開正常檔成功。
- **紅案**：`--baseline`（同一份頁面原始碼，profile 留在 v32／v4）可開的檔數要是 0、W1 與 W2 都不成立（`W_RED`）。
- **W_HOLDS**＝Chrome 與 Firefox 都是 W1、W2、截斷、W3 成立，而且紅案是 `W_RED`。沒跑或沒跑完：NOT_ESTABLISHED。
- W4（既有回歸網在兩個新 profile 上）在第 4 步凍結之前跑，要先讓那些鏡像工具認得新的 profile 名字。

### 10.5 觀察（不是判準）

- 開檔失敗之後，Writer 狀態列的檔名仍是上一份文件（`#s-doc`）。既有行為，只有鏡像看得到（宿主只開一份）。不在本批修。
