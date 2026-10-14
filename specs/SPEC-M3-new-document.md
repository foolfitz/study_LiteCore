# SPEC M3：從 Files 的「＋ 新增」建立新文件——空白範本自己寫明預設（宿主 0.2.19）

> 2026-10-14 立。判準與預測（第 4、5 節）寫在任何**計數**執行之前；本文件 commit 之前沒有跑過任何瀏覽器。
> 證據標記照 `doc-conventions`：**已觀察**＝量過、**讀原始碼**＝沒量、**推論**。
>
> 工單：`handoff/tasks/TASK-2026-10-14d-new-document.md`。分析：`findings/evidence/new-document/analysis-1.md`
> （fable 當分析者，2026-10-14）。擁有者讀過分析後選 **A**：「範本寫明預設＋下批連結補 `Language=`」。
> 擁有者本輪授權 fable 代為決定；每一個代決的點都寫在第 6 節，用白話。

## 1. 為什麼要有

擁有者 2026-10-13 親手測 0.2.18，回報「沒辦法建立新文件」：宿主 app 只在 Files 註冊了「用 LiteCore 開啟」這一個動作
（`src/files.js`），「＋ 新增」選單裡沒有我們的項目。擁有者要「參考 richdocuments 跟 collabora 的做法」。

分析 1 查出來，**一份不帶樣式的空白 ODT 在這顆引擎裡不是中性的**：

- **紙張一律 Letter**（已觀察，原生七臂）：LibreOfficeKit 在 init 時把系統語言釘成 en-US（`desktop/source/lib/init.cxx:8347`），
  紙張由那個鍵算出來（`i18nutil/source/utility/paper.cxx:231`）。瀏覽器、Nextcloud 語言都影響不到它。
- **亞洲語言跟著瀏覽器走**（已觀察）：zh-TW 瀏覽器得到 zh-TW，英文瀏覽器得到 **zh-CN**（`desktop/source/app/langselect.cxx:70-75`
  讀 Emscripten 從 `navigator.language` 拼出來的 `LANG`）。台灣機構裡把 Chrome 設成英文的人，存出去的檔案亞洲文字會被標成 zh-CN。
- **亞洲字型是 `Noto Sans CJK KR`**（finding 113 量到、分析 1 推到 e10）：預設字型用 en-US 查表、整個程序只算一次，
  在這顆影像裡落到替代品。在 LiteCore 裡看不出來（e10 五個家族共用 TC 字形），但檔案拿到別台電腦就可能畫成韓式字形。

`Language=`（Collabora 的路）能修語言與紙張、修不了字型，而且要改引擎＝等 v20 之後的連結。**範本自己寫明預設**是唯一不動引擎、
不動 profile、連字型名字都修對的路；機制上就是 richdocuments 的做法（app 裡放一個空白檔，由 template listener 寫進新檔），只是位元組不同。

## 2. 事實

- **讀原始碼**（Nextcloud 34.0.2，`~/Projects/Nextcloud_Apps/litecore/nextcloud`）：
  - `TemplateManager::createFromTemplate`（`lib/private/Files/Template/TemplateManager.php:144-175`）先 `newFile($filename, $template ? fopen : null)`
    建檔（沒選範本＝0 位元組），再派送 `FileCreatedFromTemplateEvent($template, $targetFile, $fields)`。任何例外被接住、記 log、
    改丟 `GenericFileException('Failed to create file from template')`；`TemplateController::create` 把它轉成 OCS 403。
  - 「＋ 新增」的項目來自 Files 頁面 initial state `templates`（`dist/files-init.js`：`id: template-new-${app}-${index}`，
    `enabled` 要 READ 與 CREATE 權限）。按下去先問檔名（`NewNodeDialog`：`[data-cy-files-new-node-dialog-input]`、
    `[data-cy-files-new-node-dialog-submit]`），再開 `TemplatePicker.open()`：向 `/ocs/v2.php/apps/files/api/v1/templates` 取清單、
    以 `app` 與 `label` 配對；**該 creator 的 `templates` 非空才顯示選擇器**（「空白」＋使用者 Templates 資料夾裡符合 mimetype 的檔案），
    否則直接 `onSubmit()`。已登入的使用者一律走 `POST /ocs/v2.php/apps/files/api/v1/templates/create`（`templatePath` 空字串＝空白）；
    直接 `putFileContents(path, "")` 那條只在**沒有登入者**（公開分享）時走。所以已登入者建立空白文件，伺服器端的事件**一定**會發生。
  - creator 的 `templates`＝使用者 Templates 資料夾裡 `searchByMime(<creator 的每個 mimetype>)` 的檔案（`:220-250`）。
  - `IL10NFactory::getUserLanguage($user)`（`lib/private/L10N/Factory.php:435`）＝`force_language` → 使用者 `core/lang` → 請求語言 → `default_language`。
    `findLocale($lang)`（`:266`）＝`force_locale` → 使用者 `core/locale`（存在才算）→ `default_locale` → **`$lang` 若是 locale 代碼** → `en_US`。
    **`zh_TW` 不是 locale 代碼**（`resources/locales.json` 的是 `zh_Hant_TW`），所以一個語言 zh_TW、沒設 locale 的使用者，`findLocale` 回 `en_US`。
    `localeExists('en')` 寫死 true，所以語言 `en` 沒設 locale 的使用者，locale 是沒有國家的 `en`。
  - `File::putContent` 寫失敗丟 `GenericFileException`、沒權限丟 `NotPermittedException`（`lib/private/Files/Node/File.php:53-64`）。
- **讀原始碼**（richdocuments 8.7.3，`~/OSSII/NC_modules/richdocuments/lib/Listener/`）：`RegisterTemplateFileCreatorListener` 註冊
  `TemplateFileCreator('richdocuments', 'New document', '.odt')`、mimetype odt＋ott、`setRatio(21/29.7)`；`FileCreatedFromTemplateListener`
  在 `template === null` 時 `putContent(getEmptyFileContent(ext))`，再記 `TemplateSource` 交給 Collabora 重新載入。我們沒有伺服器端引擎，
  不做 `TemplateSource`。它的 zh_TW 翻譯把 "New document" 譯成「**新文字文件**」。
- **已觀察**（2026-10-14，`odfvalidator`＝`/usr/bin/odfvalidator`，odfvalidator-lib 2.0.x，可 headless）：richdocuments 的 `template.odt`
  **不過** ODF 驗證——`mimetype` zip 項目帶 extra field（"There shall be no extra field for the 'mimetype' zip entry"）。
  驗證器**錯誤時結束碰也是 0**，所以判「過」要讀輸出：`Validation: Yes` 且沒有 `Error:` 行。對照：`dist/e1-fixtures/multi-paragraph.odt`
  （LibreOffice 存的）印 `Validation: Yes`、無錯誤。
- **已觀察**（2026-10-14，fontTools 讀 `dist/profiles/resources/cjk-sub-e10.*.data` 裡的 `NotoSansCJK-Regular-subset-E10.ttc`）：
  e10 有**十個**家族名——`Noto Sans CJK {JP,KR,SC,TC,HK}` 與 `Noto Sans Mono CJK {JP,KR,SC,TC,HK}`，每個 25,8xx 字形（同一套 TC 字形）。
  `base-r5-no35` 裡的拉丁字型是 `Liberation Serif`／`Liberation Sans`／`Liberation Mono` 各四個面。**範本裡用的名字都在這份清單裡。**
- **已觀察**（分析 1 的原生七臂，`findings/evidence/new-document/probe-1-native-defaults/`）：`Language=zh-TW` 下的「正確」預設是
  W/A/C＝en-US／zh-TW／hi-IN、A4——西文仍是 en-US，這是 LibreOffice 自己對 zh-TW 系統的答案。
- **讀原始碼**：紙張為 Letter 的國家只有 14 個：US、PR、CA、VE、CL、MX、CO、PH、BZ、CR、GT、NI、PA、SV（`paper.cxx:440-500`）；其餘一律 A4。
- **讀原始碼**：`nc-link` 只在執行當下把 app repo 的**頂層項目**逐一 symlink 進 `apps-extra/litecore/`（`.ddev/nextcloud-app/lib.sh:58-94`），
  新增頂層目錄要再跑一次 `ddev nc-link`。宿主 JS 的 `?v=` 是 app 版本的雜湊，本輪 JS 不改，但版本照工單升 0.2.19。
- **讀原始碼**：宿主 `js/litecore-editor.js` 以 fileId 解析 WebDAV 位址、GET 位元組交給頁面、存檔 PUT 帶 `If-Match`；它不讀、不轉換文件。
  新建的檔只是另一個 ODT，開啟路徑不變。

## 3. 範圍與選擇

### 3.1 範圍

- **只有「新文字文件」（`.odt`）**。Calc 還沒就位，不列試算表。
- mimetype 只列 `application/vnd.oasis.opendocument.text`，**不列** `…text-template`（分析 1 Q4：core 會把 `.ott` 位元組原樣寫進 `.odt`，
  要另外設計第一次開檔的轉換）。因此 Nextcloud 的範本選擇器會列：「空白」＋使用者 Templates 資料夾裡的 **`.odt`** 檔；
  使用者的 `.ott` **不會**出現。沒有 Templates 資料夾或裡面沒有 `.odt` 時不顯示選擇器，直接建立空白文件。
- 使用者挑自己的 `.odt` 範本時，core 自己複製位元組，**我們的 listener 不碰它**。

### 3.2 每個使用者的預設怎麼挑（第 6 節裁決 D2、D3、D6）

輸入兩個字串，都在伺服器端讀：**語言**＝`IL10NFactory::getUserLanguage($user)`；**地區**＝使用者**明確**設定的 locale——
`force_locale`、使用者 `core/locale`、系統 `default_locale`，依序第一個有的；都沒有就是「沒設」。
**不用 `findLocale()`**：它對 zh_TW 使用者會補成 `en_US`（第 2 節），照它走擁有者會拿到 Letter。

| 項 | 規則 | 例 |
| --- | --- | --- |
| **西文語言** | 語言在西文表裡→表值；是中日韓語言→`en-US`（LibreOffice 對 zh-TW 系統自己的答案）；其他→`en-US` | zh_TW→en-US；en→en-US；en_GB→en-GB；de／de_DE→de-DE；fr→fr-FR；es→es-ES；es_MX→es-MX；es_EC→es-EC；it→it-IT；nl→nl-NL；pt_BR→pt-BR；pt_PT→pt-PT |
| **亞洲語言** | 語言是中日韓→它自己；**其他一律 `zh-TW`** | zh_TW→zh-TW；zh_HK→zh-HK；zh_CN→zh-CN；ja→ja-JP；ko→ko-KR；en→**zh-TW**；de→zh-TW |
| **複合文字** | 固定 `hi-IN`（LibreOffice 的預設） | — |
| **紙張** | 國家＝地區字串的國家段（`en_US`→US、`zh_Hant_TW`→TW）；沒設地區就用**語言代碼的地區段**（`zh_TW`→TW、`en_GB`→GB、`en`→無）；國家在 14 國 Letter 表裡→Letter，**其餘含「無」→A4** | zh_TW 沒設→TW→A4；en 沒設→無→A4；en＋en_US→Letter；zh_TW＋en_US→Letter；es_MX→MX→Letter |
| **西文字型** | `Liberation Serif` | — |
| **亞洲字型** | 跟亞洲語言的國家：TW→`Noto Sans CJK TC`、HK→HK、CN→SC、JP→JP、KR→KR | en→TC；ja→JP |
| **複合字型** | `Liberation Sans` | — |
| **字級** | 三者都 12pt | — |

為什麼亞洲語言不跟著瀏覽器也不跟著「非中日韓的 Nextcloud 語言」：這顆引擎只有 TC 字形（e10），在 LiteCore 裡打出來的中文**就是**正體字形；
把它標成 zh-CN 是對檔案說謊。產品的買家是台灣機構，而分析 1 指出「員工把瀏覽器留在英文」正是今天掉進 zh-CN 那一格的人。

**不支援的語言**（上表沒列的，例如 `pl`）：西文 `en-US`、亞洲 `zh-TW`、紙張照規則。這是 fallback，不是錯誤，不寫 log。

### 3.3 範本位元組（裁決 D4、D5、D9）

- **一個三元組一個檔**：`<西文>_<亞洲>_<紙張>.odt`，例如 `en-US_zh-TW_A4.odt`、`en-US_zh-TW_Letter.odt`、`de-DE_zh-TW_A4.odt`、`en-US_ja-JP_Letter.odt`。
  3.2 的表能產生的三元組：西文 11 個 × 亞洲 zh-TW × 2 紙張＝22，加上 en-US × 亞洲 {zh-HK, zh-CN, ja-JP, ko-KR} × 2＝8，共 **30 個檔**。
  （zh_TW 使用者與 en 使用者拿到同一個檔 `en-US_zh-TW_*.odt`。）
- **不在伺服器端代換**：PHP 只查表、讀檔、核對 sha256、寫入。理由：位元組可以事先驗證（ODF 驗證器、原生 round trip）並釘死雜湊；
  PHP 動態打 zip 的位元組會跟著 PHP 與 zlib 的版本走，驗不到也釘不住。
- **產生器**：`wasm_sdk_probe/tools/make_new_document_templates.py`（study_LiteCore），表驅動、**決定性**：所有 zip 項目 STORED（不壓縮，
  跟 zlib 版本無關）、時間戳 1980-01-01 00:00、`mimetype` 第一個且沒有 extra field、固定順序。輸出目錄附 `MANIFEST.json`：
  每個檔的 sha256、三元組、產生器自己的 sha256。**同一份原始碼跑兩次位元組相同**（測試 `wasm_sdk_probe/tests/test_new_document_templates.py`）。
- **內容**：`mimetype`、`META-INF/manifest.xml`（ODF 1.3，列 `/`、`content.xml`、`styles.xml`、`meta.xml`）、`meta.xml`（只有 `meta:generator`）、
  `content.xml`（一個空的 `text:p text:style-name="Standard"`）、`styles.xml`：
  - `office:font-face-decls`：三個會用到的字型（`style:font-family-generic` roman／system／swiss、`style:font-pitch="variable"`）；
  - `style:default-style style:family="paragraph"`：`style:paragraph-properties style:text-autospace="ideograph-alpha" style:punctuation-wrap="hanging" style:line-break="strict"`；
    `style:text-properties` 帶 `style:use-window-font-color="true"`、三組 `font-name`／`font-size`／`language`／`country`（西文用 `fo:`，亞洲、複合用 `style:…-asian`／`…-complex`）；
  - `style:style style:name="Standard" style:family="paragraph" style:class="text"`（**標準樣式名保留**，其餘標題、內文等樣式讓引擎從內建池補）；
  - `office:automatic-styles/style:page-layout style:name="Mpm1"`：A4＝`21cm × 29.7cm`、Letter＝`8.5in × 11in`，四邊 `2cm`，`style:print-orientation="portrait"`；
  - `office:master-styles/style:master-page style:name="Standard" style:page-layout-name="Mpm1"`。
- **宿主裡的位置**：`~/Projects/Nextcloud_Apps/litecore/blank/`（新頂層目錄；`MANIFEST.json` 與 30 個 `.odt`）。寫入前 PHP 以 `MANIFEST.json`
  核對位元組的 sha256；不符就當成損壞（3.4）。

### 3.4 宿主改動（0.2.19）（裁決 D7、D8）

- `lib/Listener/RegisterTemplateCreatorListener.php`：`TemplateFileCreator('litecore', $l10n->t('New document'), '.odt')`，只加 odt mimetype，
  `setIconSvgInline`（`src/files.js` 同一個圖示）、`setRatio(21 / 29.7)`。
- `lib/Template/BlankDocument.php`：純函式（不依賴 Nextcloud）——`choose(string $language, ?string $locale): array`（三元組、檔名、理由）、
  `read(string $file): string`（讀檔、核對 MANIFEST 的 sha256、長度 > 0，否則丟 `RuntimeException`）。可以用 `php -r` 直接呼叫，runner 拿它當真值源。
- `lib/Listener/FileCreatedFromTemplateListener.php`：目標 mimetype 不是 odt→不管；`getTemplate() !== null`（使用者自己的範本）→不管；
  否則讀語言與地區（3.2）、`BlankDocument::choose`／`read`、`putContent`。**任何一步失敗（檔不存在、雜湊不符、putContent 丟例外、
  寫完 `getSize()` 不等於長度）：先刪掉剛建立的目標檔，再丟出例外**→core 記 log、使用者看到 Nextcloud 自己的「Failed to create file from template」，
  資料夾裡**不留 0 位元組的檔**。
- `lib/AppInfo/Application.php`：註冊兩個 listener（`RegisterTemplateCreatorEvent`、`FileCreatedFromTemplateEvent`）。
- `l10n/zh_TW.json`＋`zh_TW.js`：`New document`→「新文字文件」（與 richdocuments 的 zh_TW 一致）。只加 zh_TW；其他語言顯示英文。
- `appinfo/info.xml`：0.2.19。JS 不改、不重新打包；`engine/` 維持 0.2.18 的包（buildId `d6d04880f56e31da`）。
- 安裝（dev 實例）：`ddev start`（實例目前是 paused）→ `ddev nc-link`（新頂層目錄 `blank/`、`l10n/`）→ 確認 `config/` 裡 debug 仍 false →
  `ddev occ upgrade` → `occ app:list` 回報 0.2.19。

### 3.5 不改的東西

引擎、profile（`dist/profiles/e2-editor-v19`）、頁面位元組（`e2-editor-app.js` `b24d754a…`）、殼層 generation v66、宿主的 `engine/` 包：**都不動**。
只有宿主 app 改，版本 0.2.19。v20 的連結已發生（wasm `313b08d5`），**與本輪無關**，宿主的引擎包仍是 0.2.18 的。

已知的不一致，登錄不處理：下一批連結的 `Language=` 會把語言 `en` 對到 en-US→引擎自己對**其他**不帶樣式的檔案給 Letter；本輪的空白範本對 `en`
沒設地區給 A4（3.2）。兩者的對象不同（新建的檔 vs 使用者帶來的無樣式檔），到那一批再一起決定。

### 3.6 0.2.18 的紅案

0.2.18 **沒有**選單項目：`/ocs/v2.php/apps/files/api/v1/templates` 的清單裡沒有 `app === "litecore"` 的 creator，Files 的「＋ 新增」裡沒有
`template-new-litecore-*`。這要在**升級之前**對真的 0.2.18 量一次（runner 的 `--control` 模式），不是事後假造。

## 4. 判準

新 runner `wasm_sdk_probe/tools/check_m3_new_document.py`，對 dev 實例（`litecore`）跑，Chrome 與 Firefox 各自一個瀏覽器、每臂重新登入。
使用者設定兩組，用 admin 自己切（`occ user:setting admin core lang／locale`），**量完還原成量測前讀到的值**（擁有者每天用這個實例）：

| 臂 | `core/lang` | `core/locale` | 預期三元組 | 預期檔 |
| --- | --- | --- | --- | --- |
| **TW** | `zh_TW` | （刪掉＝沒設） | en-US／zh-TW／hi-IN，TC，**A4** | `en-US_zh-TW_A4.odt` |
| **EN** | `en` | `en_US` | en-US／zh-TW／hi-IN，TC，**Letter** | `en-US_zh-TW_Letter.odt` |

每臂：Files（`?dir=/`）→「＋ 新增」→ `template-new-litecore-*` → 檔名對話框打 `新文件 測試-<臂>-<瀏覽器>.odt` → 送出 →（core 帶 `openfile` 開啟→
我們的預設動作→編輯器路由）→ 點進第一行 → **真鍵**打 `zqx` → 工具列儲存 → 等 host 的 save settled → 回 Files 再開一次 → 讀狀態。
伺服器那一側全部走 WebDAV／OCS（`probe_m3_lock_semantics.Client`），檔案位元組用 sha256 與解 zip 讀。

| 判準 | 內容 | 形式 | 從來沒做時的結論 |
| --- | --- | --- | --- |
| **N1** 選單有項目 | `GET /ocs/v2.php/apps/files/api/v1/templates` 的 creator 清單裡**恰有一個** `app === "litecore"`，`extension === ".odt"`，`mimetypes` **恰等於** `[odt]`（沒有 ott）；Files 頁面 DOM 有 `[data-cy-upload-picker-menu-entry^="template-new-litecore-"]`。每瀏覽器每臂 | 工具封閉的枚舉（清單由 core 生成） | 0.2.19 不得稱有「新增文件」 |
| **N1 紅案** | 同一支 runner `--control` 在升級前對 0.2.18 跑：清單裡**沒有** `litecore`→紅。證據留 `findings/evidence/new-document/control-0.2.18/` | 先紅一次（真的 0.2.18） | runner 不得用來宣告 N1 |
| **N2** 建出來的是指定的範本 | 送出檔名後，資料夾裡出現**那個名字**的檔（PROPFIND），其位元組 sha256 **等於** `blank/MANIFEST.json` 裡該臂預期檔的 sha256，長度等於該檔長度；`php -r` 呼叫 `BlankDocument::choose(lang, locale)` 回的檔名等於預期檔名（PHP 的規則與本表一致） | 逐實例（每臂） | 預設不得稱「跟著使用者」 |
| **N3** 預設動作開得起來 | 建檔後瀏覽器落在 `/e2-editor.html`、`fileId` 等於 N2 的 fileid；host `fetched.sha256` 等於 N2 的 sha256；頁面 `state === "ready"`、`doc` 等於檔名 | 逐實例 | 新建的檔不得稱可開啟 |
| **N4** 打字、存檔 | 真鍵三下各讓 `revision` ＋1、`generation` 不變；儲存後 host 最後一筆 save `outcome === "saved"`；伺服器上該檔 **長度 > 0、解得開**、`content.xml` 的段落序列（`odt_paragraphs`）含 `zqx` **恰一次** | 逐實例 | 新建的檔不得稱可編輯 |
| **N5** 重開看得到 | 回 Files 點同一列：落在編輯器、`state === "ready"`、host `fetched.sha256` 等於 N4 之後伺服器上的 sha256（引擎拿到的就是含標記的那份）；`#a11y-doc[data-offers]` 記進報告；**若為 "1"**，點進第一行後 `#a11y-para` 含 `zqx` | 逐實例；a11y 那半是**條件式**（出貨 profile 沒提供時登錄 `NOT_OFFERED`，是「沒東西可守」不是「沒人守」） | 不得稱「重開看得到」 |
| **N6** WASM 存回的 styles.xml 寫明預設 | N4 之後伺服器上該檔的 `styles.xml`：`style:default-style[paragraph]/style:text-properties` 的 `fo:language`／`fo:country`、`style:language-asian`／`style:country-asian`、`style:language-complex`／`style:country-complex`、`style:font-name`／`style:font-name-asian`／`style:font-name-complex` **逐一等於**該臂預期三元組與 3.2 的字型；`style:page-layout-properties` 的寬高換算成 mm 後，與 A4（210×297）或 Letter（215.9×279.4）之差 **≤ 1 mm**，判成預期的紙張。**兩臂 × 兩瀏覽器全部**。另記：兩瀏覽器同一臂的 `styles.xml` 是否逐位元組相同（資料，不是判準） | 逐實例（每臂每瀏覽器） | 「範本寫明預設」不得稱成立 |
| **N7** 不會悄悄產生 0 位元組或損壞的檔 | (a) 每個 N2 的檔長度等於範本長度（已含在 N2）；(b) **紅案一次**：runner `--red-corrupt` 把 dev 實例 app 裡的 `blank/MANIFEST.json` 暫時改名，以 OCS 建立空白文件→**必須** 403（`Failed to create file from template`），且資料夾裡**沒有**那個名字的檔；量完還原、`git status` 乾淨。記在 `findings/evidence/new-document/red-corrupt/` | (a) 逐實例；(b) 先紅一次 | 「不會悄悄產生壞檔」不得宣稱 |
| **N8** 沒有寫入權限 | admin 建資料夾、以**唯讀**（permissions 1）分享給第二個使用者 `lcprobe`；lcprobe 以 OCS `templates/create` 在該資料夾建空白文件→**403**；admin PROPFIND 該資料夾**沒有**那個檔。另記 lcprobe 在瀏覽器裡該資料夾的「＋ 新增」按鈕 `disabled`（資料） | 逐實例（API 那半） | 不得稱「照 Nextcloud 的拒絕」 |
| **N9** 其他都沒動 | 宿主 `engine/MANIFEST.json` 的 buildId 與每個檔的雜湊等於 0.2.18 的；HTTP 讀到的 `e2-editor-app.js` 解碎後 sha256 等於 0.2.18 的頁面（`b24d754a…`）；宿主 `git diff 96a87d8..HEAD --name-only` 只含 `appinfo/info.xml`、`lib/AppInfo/Application.php`、`lib/Listener/*`、`lib/Template/*`、`blank/*`、`l10n/*`；study_LiteCore 的 `wasm_sdk_probe/{web,editor-shell*,sdk,src,Makefile}` 在本輪 commit 裡沒有改動 | 逐實例（每個檔） | 0.2.19 不得稱「只改宿主」 |
| **N10** 範本過 ODF 驗證 | `blank/` 裡**每一個** `.odt`：`odfvalidator -e` 的輸出含 `Validation: Yes`、沒有任何 `Error:` 行；`MANIFEST.json` 裡每個檔的 sha256 等於磁碟上的 | 逐實例（產生的集合） | 範本不得稱合規 |
| **N10 紅案** | 同一支檢查對 richdocuments 的 `template.odt` 必須紅（它有 extra field，第 2 節） | 先紅一次 | — |
| **N11** 原生 round trip 範本贏過環境 | 原生 26.8 LOK（`probe-1-native-defaults/tool/lok_defaults_probe.cpp` 的作法）在 `LANG=en_US.UTF-8` 與 `LANG=zh_TW.UTF-8` 下各載入 `en-US_zh-TW_A4`、`en-US_zh-TW_Letter`、`en-US_ja-JP_A4`、`de-DE_zh-TW_Letter` 四個檔並存成 ODT：存出的 `styles.xml` 的三組語言、三個字型名、紙張**等於**範本寫的（八格全對）；對照：richdocuments 的 `template.odt` 在同兩個環境下亞洲語言**不同**（zh-CN vs zh-TW）——證明量得出環境的影響 | 逐實例（每格） | 「範本自己寫明預設」不得稱在引擎裡成立 |
| **N12** 封閉性 | 對 Nextcloud 的每一個語言代碼（`core/l10n/*.json` 的檔名＋`en`）× 地區 {沒設, `en_US`, `zh_Hant_TW`}：`BlankDocument::choose` 回的檔名**都在** `MANIFEST.json` 裡（PHP 表加了一個語言而產生器沒產生那個檔→紅）；反向：MANIFEST 裡每個檔至少被一組輸入選到 | 工具封閉的枚舉 | PHP 的表不得稱「每個值都有檔」 |

**量測前的修訂（2026-10-14，第一次完整 shakedown `shakedown/2026-10-14T032312Z.json` 之後、任何計數之前；原文留著，以下取代對應的句子）**：

1. **臂跑在自己的資料夾 `新文件 測試資料夾`，不在根目錄**。取代上文「Files（`?dir=/`）」。理由（已觀察）：擁有者的根目錄有 `Readme.md`，
   `text` app 把它嵌在清單頂端就地編輯；TW/chrome 那一趟它跳出「檔案已被覆寫。無法自動儲存…」的衝突對話框，把檔名對話框的送出吞掉，
   頁面留在 Files（`landedInstead` 記下了那段文字）。同一輪 TW/firefox、EN 兩臂都沒碰到。這是儀器的隔離問題，不是產品缺陷。
2. **點進第一行的位置依紙張算**：距頁面頂端 23 mm（2 cm 邊界＋半行），換成 `#paper` 高度的比例（A4 0.0774、Letter 0.0823），x 固定 0.3。
   理由（已觀察）：原本固定 y＝0.075 在 Letter 上是 21 mm、落在上邊界裡，引擎正確地拒絕（`EDITOR_CARET_NOT_PLACED：the caret did not reach
   the point that was clicked`），EN 兩臂都中；A4 上是 22.3 mm、在行內，TW 兩臂都成功。
3. **N4 的「失敗」判在點擊、不判在按鍵**：按鍵之後 `#s-latency` 不會更新，它留著的是點擊那一行的字；原本把它拿來判每一下按鍵，EN 兩臂因此
   紅在按鍵上，而按鍵其實三下都 revision ＋1。改成：**點進第一行必須成功**（`latency` 含「定位游標」且不含「失敗」、沒逾時）是 N4 的第一條；
   每一下按鍵只看 revision ＋1、generation 不變。這是加嚴（多一條點擊必須成功）加上歸位，不是放寬。
4. 送出之後 90 秒內沒到編輯器路由就讓那一趟直接死掉並記下頁面上的 modal 與文字，不再空等 400 秒的 `HOST_DONE`。
5. **（第一次計數執行 `runs/2026-10-14T034231Z.json` 之後加的）檔名每一趟不同**：`新文件 測試-<臂>-<瀏覽器>-<HHMMSS>Z.odt`，取代上文固定的檔名。
   理由（已觀察）：那一趟兩個 Chrome 格都死在檔名對話框的「此名稱已使用」——前一趟 shakedown 存出來的同名檔還在，runner 的 `DELETE` 回 **423 Locked**
   （log 裡兩筆），因為前一個 session 的 token 鎖在瀏覽器被 CDP 關掉之後要到 300 秒才失效（Chrome 離頁的 UNLOCK 到不了伺服器，finding 105 的一族；
   Firefox 兩格的舊檔在根目錄、不在新資料夾，`DELETE` 回 404，兩格都過）。那一次計數執行**不算**：它紅在儀器上，留在 `runs/` 當紀錄。
   順帶：`DELETE` 的狀態碼現在記進每一趟（`removeOld`），執行結束把建立的檔刪掉（`cleanup`，鎖還在的回 423、照記）。

**計數語意**：N1–N9 由一次 `--counted` 執行（兩瀏覽器 × 兩臂 × 1 次）判定；N10–N12 是靜態／原生檢查，在宿主 commit 之後、計數之前跑一次。
0.2.19 是**未計數候選**（擁有者 2026-10-12 裁示：五小時計數鏈併到下一個改引擎的批次）；本 spec 的判準是它專屬的驗收，照跑。

**綁定**（計數前寫進 runner）：宿主 0.2.19 的 commit、`blank/MANIFEST.json` 的 sha256、0.2.18 的頁面 sha256 與 buildId（N9 的對照值）。

## 5. 預測（寫在執行之前）

1. N1–N6 兩瀏覽器兩臂全綠；TW 臂 A4、EN 臂 Letter；亞洲語言兩臂都是 zh-TW、字型 `Noto Sans CJK TC`。
2. N6 的「兩瀏覽器同一臂 styles.xml 逐位元組相同」：**預測相同**——styles.xml 不含 rsid（rsid 在 content.xml 的自動樣式裡）。若不同，差異會在 `meta`／`settings`，不在這裡；記下來就好。
3. N5 的 `data-offers` 在出貨 v19 上：**預測 "0"**（caret paragraph text 是 a11y core 的資料）→ N5 的 a11y 半登錄 `NOT_OFFERED`。
4. N11：八格全對；richdocuments 對照 zh-CN／zh-TW 不同（分析 1 的 A 與 B 臂重現）。
5. N7 (b)：403、無檔。N8：403、無檔、按鈕 disabled。
6. 第一次 shakedown 會紅在**儀器**上（對話框選擇器、`openfile` 之後的導向時機、空白文件裡點第一行的座標），不在產品上；修儀器不改判準。

## 6. 裁決（fable 代擁有者，2026-10-14）

每一條都是本輪我替擁有者決定的，白話寫，擁有者看了不同意可以推翻；推翻的話只動對應的檔，判準照第 4 節的形式重寫並附理由。

- **D1 範圍**：只做「新文字文件」（`.odt`），不列 `.ott`、不做試算表。理由：Calc 沒就位；`.ott` 要另外設計第一次開檔的轉換（分析 1 Q4）。
- **D2 語言**：西文跟使用者的 Nextcloud 語言（表在 3.2）；**亞洲語言只有中日韓使用者跟自己，其他人一律 zh-TW**；複合固定 hi-IN。
  理由：這顆引擎只有正體字形，打出來的中文就是正體，標成 zh-CN 是對檔案說謊；買家是台灣機構，英文介面的員工最多。
- **D3 紙張跟「地區」不跟語言，而且只認使用者明確設的地區**：設了 locale（或系統 `default_locale`／`force_locale`）就用它的國家；沒設就看語言代碼有沒有地區段
  （zh_TW→TW、en→沒有）；都沒有→A4。只有 LibreOffice 自己那 14 國是 Letter。**不用 Nextcloud 的 `findLocale()`**，因為它會把 zh_TW 補成 en_US，
  擁有者自己就會拿到 Letter。代價：美國使用者語言 `en` 沒設 locale 會拿到 A4，要到 Nextcloud 個人設定把地區設成 en_US（或管理者設 `default_locale`）。
- **D4 用 30 個靜態檔，不在伺服器端代換**：位元組可以事先驗證、釘雜湊；PHP 只查表＋核對 sha256。代價：多 80 KB 左右的檔、加語言要重新產生。
- **D5 字型**：西文 `Liberation Serif`、亞洲依語言 `Noto Sans CJK TC／HK／SC／JP／KR`、複合 `Liberation Sans`，三者 12pt。名字全部在出貨影像裡（第 2 節量過）。
- **D6 不支援的語言**退回 en-US／zh-TW／紙張照 D3，不記 log、不當錯誤。
- **D7 失敗就刪檔再丟例外**：範本缺、雜湊不符、寫入失敗，都把剛建立的空檔刪掉再丟出去，讓 Nextcloud 顯示它自己的「Failed to create file from template」。
  不留 0 位元組的檔給使用者。
- **D8 選單字樣**：英文 `New document`，zh_TW 譯「新文字文件」（跟 richdocuments 一樣，使用者兩邊看到同一個詞）；只加 zh_TW。
- **D9 範本形式**：ODF 1.3、全部 STORED、時間戳 1980-01-01、`mimetype` 第一且無 extra field；保留 `Standard` 樣式名，其餘讓引擎補。
- **D10 量測用 admin 切語言、量完還原**；無寫入權限那格用第二個使用者 `lcprobe`＋唯讀分享走 API。理由：瀏覽器登入 helper 綁 admin；少一個變因。
- **D11 0.2.18 的紅案在升級前量真的 0.2.18**（`--control`），不事後假造。
- **D12 一併登錄的不一致**（3.5）：下一批 `Language=` 對 `en` 給 Letter、本輪範本對 `en` 沒設地區給 A4——到那一批再一起決定，本輪不處理。

## 7. 結果

（只准 append，更正寫在後面並指名取代什麼。）

### 7.1 判定（2026-10-14）

**計數執行 `findings/evidence/new-document/runs/2026-10-14T035226Z.json`：`NEW-DOCUMENT WORKS`**——兩臂 × 兩瀏覽器四格 N1–N6 全 PASS，
N8／N9／N10／N12 全綠，admin 的語言設定還原成量測前的值（`zh_TW`／沒設 locale）。紅案 29 個全紅、基線綠（`--red-cases` 2026-10-14 ~04:00Z）。
綁定：宿主 **0.2.19** `afbaf3c`（乾淨）、`blank/MANIFEST.json` `e5cdb8e2…`、引擎包 buildId `d6d04880f56e31da`、頁面 `b24d754a…`——後兩者**等於 0.2.18**。
study_LiteCore 這一輪的 commit `503263d2`、`b893e7bf` 沒碰任何產品路徑。runner sha256 `f9a46a05…`。

**0.2.19 是未計數候選**（§4 計數語意；五小時計數鏈併到下一個改引擎的批次）。

| 格 | 瀏覽器 | `navigator.language` | 建出的檔 | 點進第一行 | 三鍵 revision | 存檔 | 伺服器 `styles.xml`（W／A／C、字型、紙張） | 重開 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TW | Chrome 151 | zh-TW | 3,940 B＝`en-US_zh-TW_A4` | 405 ms | 0→1→2→3，世代 1 | saved，7,958 B，`zqx` ×1 | en-US／zh-TW／hi-IN，Serif／**TC**／Sans，**A4** 210.01×297 | ready，拿到存回的位元組 |
| TW | Firefox 157 | **en-US** | 同上 | 407 ms | 同上 | saved，7,957 B | **同上**（`styles.xml` sha `5addf7dc…` 與 Chrome 逐位元組相同） | ready |
| EN | Chrome 151 | zh-TW | 3,939 B＝`en-US_zh-TW_Letter` | 406 ms | 同上 | saved，7,995 B | en-US／zh-TW／hi-IN，Serif／TC／Sans，**Letter** 215.9×279.4 | ready |
| EN | Firefox 157 | en-US | 同上 | 405 ms | 同上 | saved，7,997 B | **同上**（sha `09d2dd95…` 與 Chrome 相同） | ready |

兩個瀏覽器的 UI 語言不同（Chrome zh-TW、Firefox en-US），同一臂的 `styles.xml` 仍逐位元組相同：**瀏覽器語言漏不進新建的文件**（分析 1 的 Q1 在新建文件上已關閉）。

- **N1**：清單恰一個 `litecore` creator，`.odt`，mimetypes 恰 `[odt]`；Files 選單有 `template-new-litecore-1`「新文字文件」（admin 語言 en 時顯示 "New document"）。
  **紅案**：升級前對真的 0.2.18（`96a87d8`）量到清單只有 `text` 的 creator（`control-0.2.18/2026-10-14T031813Z.json`）。
- **N2**：四格建出的位元組都等於 MANIFEST 裡該臂的檔；`BlankDocument::choose` 的答案與臂一致（TW：`country TW, from language`；EN：`country US, from locale`）。
- **N5 的 a11y 半**：四格 `#a11y-doc[data-offers]="0"`→**`NOT_OFFERED`**（出貨 v19 沒有 caret paragraph text；預測 3 成立）。「重開看得到」由位元組那半承載。
- **N7 (b)**：`red-corrupt/2026-10-14T031918Z.json`——藏起 MANIFEST → OCS **403**「無法從範本建立檔案」、資料夾裡沒有檔、MANIFEST 還原、`git status` 乾淨；
  還原後同一請求 200 且位元組等於 `en-US_zh-TW_A4`（3,940 B，`7e6221b6…`）。
- **N8**：`lcprobe` 對唯讀分享（`SGDN`）的資料夾 OCS 建立 → **403** "Failed to create file from template"，admin 看不到檔；（資料）lcprobe 在該資料夾的 Files
  頁面**沒有渲染「＋ 新增」**（`[data-cy-upload-picker]` 不存在），所以使用者根本按不到。
- **N10**：30／30 過 `odfvalidator -e`，MANIFEST 雜湊全對；richdocuments 的 `template.odt` 紅（mimetype extra field）。
- **N11**：原生 8／8（`native-roundtrip/`），對照組亞洲語言 en_US→zh-CN、zh_TW→zh-TW。
- **N12**：58 個語言 × 3 地區＝174 組輸入，30 個檔，兩個方向封閉；紅案（PHP 表多加 `pl`）轉紅。

### 7.2 預測對帳

1. N1–N6 四格全綠、TW A4、EN Letter、亞洲 zh-TW、TC：**成立**。
2. 兩瀏覽器同臂 `styles.xml` 逐位元組相同：**成立**（兩臂都是）。
3. `data-offers` 在 v19 是 "0"：**成立**。
4. N11 八格全對、對照組分裂：**成立**。
5. N7 (b) 403 無檔、N8 403 無檔：**成立**；N8 的「按鈕 disabled」實際是**整個 picker 不渲染**（比預測更強）。
6. 第一次 shakedown 紅在儀器上：**成立，而且不止一次**（§4 修訂 1–5）——三個都是儀器：根目錄的 Readme.md 衝突對話框、Letter 上點進邊界、
   前一趟的檔還被前一個 session 的鎖抓著（`DELETE` 423）。沒有一個是產品缺陷。

### 7.3 順帶量到的（資料，不是判準）

- **擁有者的 Templates 資料夾有 11 個 `.odt`**（Nextcloud 的範例範本：Calendar、Certificate、Invoice…），所以四格都看到範本選擇器（12 格、「空白」預選），
  runner 按「建立」。沒有 `.odt` 範本的使用者會直接建立。
- **關掉瀏覽器之後鎖還在**：counted 執行結束時的 `cleanup`，Chrome 兩格 **423**（session 由 CDP `Browser.close` 收掉，UNLOCK 沒到伺服器）、
  Firefox 兩格 **204**（WebDriver 關 session 時 UNLOCK 有送到）。鎖 300 秒後自己失效。finding 105 的一族，非本輪範圍。
- 開新建文件到 `ready`：Chrome 2.8 s、Firefox 3.1–3.4 s（熱快取的引擎）；重開 1.6–2.7 s。
- `text` app 在根目錄的 `Readme.md` 就地編輯器會跳「檔案已被覆寫。無法自動儲存…」（`shakedown/2026-10-14T032312Z.json` TW/chrome 的 `landedInstead`）；
  那是 Nextcloud `text` app 的行為，與本輪無關，但它會把同頁的對話框送出吞掉——使用者在根目錄建檔時若正好碰到，要先關掉那個對話框。

### 7.4 之後

- 擁有者手測 0.2.19：Files 任一資料夾「＋ 新增 → 新文字文件」、打字、存、重開；用桌面 LibreOffice 開存出的檔看段落樣式的語言與頁面大小（A4）。
- D12（§3.5）進下一批連結的 `Language=` 討論：`en` 的紙張。
- `Language=`（分析 1 的 B）在 v20 之後的連結批次；本輪的範本不受它影響（檔案自己寫明）。
- 測試資料夾 `新文件 測試資料夾` 在 admin 的 Files 裡；runner 每趟結束會刪自己建的檔（鎖還在的那幾個留到鎖失效後再刪）。
