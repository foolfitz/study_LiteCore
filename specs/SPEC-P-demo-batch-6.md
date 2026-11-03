# SPEC-P-demo-batch-6：新增試算表、上傳開啟 .ods、LibreOffice 圖示

2026-11-03 擁有者原文：

> 1. 在 Nextcloud 的檔案清單頁面，也要能新增 ods 檔案
> 2. calc 要跟 writer 一樣，能夠上傳並開啟 ods 文件
> 3. 在建立檔案時，"新增文字文件"的圖示不像 libreoffice 風格，幫我找找看有沒有可以用的 odt 跟 ods 圖示

第 2 項擁有者問 Collabora 怎麼做，答案照著做（第 1.2 節）。第 3 項擁有者選實心 mime 圖示（`research/RESEARCH-2026-11-03-odt-ods-icons.md` 的 A）。判準實作前釘死，本文件只准 append。

全部是**宿主**改動（`/home/jiajun/Projects/Nextcloud_Apps/litecore`），引擎與頁面不動，不用連結。出成宿主 0.2.54，接在 0.2.53（demo batch 5）之後。

## 1. 三件事

### 1.1 「+ 新增」裡的新試算表

現況（讀碼）：`RegisterTemplateCreatorListener` 只註冊 `.odt`；`FileCreatedFromTemplateListener` 只寫 ODT；`BlankDocument` 只有 ODT 的檔名。

Collabora（`richdocuments/lib/Listener/RegisterTemplateFileCreatorListener.php:58-69`）的作法：每種文件各一個 `TemplateFileCreator`，`New spreadsheet`、`.ods`，圖示讀 app 內的 SVG。它的空白 ODS（`emptyTemplates/template.ods`）只有 255 位元組的 `content.xml`，沒有 `styles.xml`、沒有工作表，預設值交給 Collabora。

**我們不能照抄空白檔**：Writer 那邊量過，沒寫預設值的文件在這個引擎上會得到 Letter、隨瀏覽器變的亞洲語言和韓文字型（`SPEC-M3-new-document.md`）。試算表的語言還決定數字與日期怎麼解讀。所以空白 ODS 照 ODT 的產生器做：每個（西文語言、亞洲語言、紙張）組合一份，寫明語言、三種字型、字級、紙張，位元組確定、sha256 登錄在 manifest，寫入時比對。挑哪一份沿用 `BlankDocument::choose()` 的規則。

- 產生器：`wasm_sdk_probe/tools/make_new_spreadsheet_templates.py`，共用 ODT 產生器的組合、字型、紙張與打包。西文字型用 Calc 的預設 `Liberation Sans`，字級 10pt。
- 一張工作表 `Sheet1`，和 Collabora、LibreOffice 英文介面相同。工作表名稱不隨介面語言變，登錄為限制 `L-sheet-name`。
- 宿主：`blank-ods/` 放檔案與自己的 `MANIFEST.json`；`BlankDocument` 依副檔名挑目錄；listener 處理 `.ods`；建立器 `New spreadsheet`（zh_TW 翻成「新試算表」）、比例 16:9，和 Collabora 相同。

### 1.2 上傳並開啟 .ods：照 Collabora

Collabora 沒有自己的上傳，也沒有編輯器裡的「開啟檔案」：上傳交給 Nextcloud 檔案清單（上傳鈕或拖放），點開由預設檔案動作負責。我們的檔案動作已經接受 `.ods`（可寫開 `ods-editor.html`，唯讀開檢視器，`src/files.js`）。所以這一項是**量**，不是先改：用 Files 的上傳介面真的上傳一份 .ods，點開，要進 Calc 編輯器並能存檔。量到壞的才修。

### 1.3 LibreOffice 的文件圖示

`libreoffice-26-8/sysui/desktop/icons/hicolor/scalable/mimetypes/oasis-text.svg`、`oasis-spreadsheet.svg`，MPL-2.0。放進宿主 `img/`，去掉 XML 宣告與編輯器註解，附 `img/README.md` 寫出處與授權，並附 MPL-2.0 全文。「新文字文件」與「新試算表」兩個建立器用它們。Files 的「Open in LiteCore」動作圖示不動（同一個動作服務兩種檔案）。

## 2. 判準

**產生器與宿主靜態**：

- G1 `make_new_spreadsheet_templates.py --check blank-ods`：重新產生與磁碟逐位元組相同。
- G2 `--validate`：odfvalidator 每一份都沒有錯誤。
- G3 `php -r` 呼叫 `BlankDocument::choose()`：ODS 的檔名是同一組合的 `.ods`，而且存在 manifest 裡。

**宿主（`host_batch6.py`，真實指標與按鍵，Chrome、Firefox，WebDAV 讀回）**：

- H6/new-menu：「+ 新增」有「新文字文件」與「新試算表」，兩者圖示是第 1.3 節的 SVG（比對 SVG 的填色）。
- H6/create-ods：從選單建立 `.ods`，檔案的 mimetype 與內容等於 `BlankDocument::choose()` 為這個使用者挑的那一份（sha256）。
- H6/opens-in-calc：建立後進 `ods-editor.html`，可編輯，狀態 ready。
- H6/edit-save：在 A1 輸入、存檔，WebDAV 讀回有這個值，語言與紙張仍是空白檔寫明的那些。
- H6/upload-ods：用 Files 的上傳介面上傳一份 .ods，點開進 Calc 編輯器、可存檔。同一流程上傳 .odt 進 Writer 當對照。
- H6/new-odt-still-works：「新文字文件」照舊建出同一份 ODT，開進 Writer。
- **紅案**：同一工具在 0.2.53 上要紅在 H6/new-menu 與 H6/create-ods。

**回歸**：Files 工作流 52/52、`HOST_BATCH_HOLDS`、`LAYOUT_HOLDS`、T6（宿主沒有改頁面，只確認沒有退化）。

## 3. 具名限制

- `L-sheet-name`：工作表名稱固定 `Sheet1`，不隨介面語言。
- `L-ods-template-own`：使用者自己 Templates 資料夾裡的 `.ods` 會出現在選單裡，由 Nextcloud 直接複製，不經過我們的空白檔，和 ODT 相同。

## 4. 如果永遠沒做

新增只能建 `.odt`；.ods 要先在別處做好再上傳。圖示維持單色字形。
