# SPEC M3：連結批次 v24——打字走 `.uno:InsertText`（finding 168）

狀態：**判準釘死（2026-10-28，本檔第一個 commit）。**任何 v24 的執行——引擎碼、worker、SDK、`make -n` 的 v24 目標、連結、瀏覽器——都在這個 commit 之後（CLAUDE.md「驗收判準的形式」§9.1「先於滿足」）。之後只准追加更正（同 §10）。

依據：

- **fable 裁決 1**（`findings/evidence/link-batch-v23/feature-protocol/s5-type-route-ruling/RULING.md`；簡報 `BRIEF.md`）：路線 A（縮小版）、T1–T5、紅案 (i)–(v)、重驗清單、M0–M2。下文「裁決 1 §N」指它的第 N 節。
- **fable 裁決 2**（同目錄 `RULING-2-abi.md`；簡報 `BRIEF-2-abi.md`）：**編輯器 ABI 留 6**，新 export 用 contract 宣告葉；撤回裁決 1 的「ABI 6→7」；init 時的宣告 export 存在檢查；紅案 (a)–(e)。同檔的**追問**（同日）：「沒宣告就拒絕打字」撤回，改由 v24 頁面把關，附修正 A1–A3 與收緊的 T2。ABI、宣告與路線欄位以裁決 2（含追問）為準，其餘以裁決 1 為準。
- **擁有者 2026-10-28 的兩個決定**：ABI 這一題交 fable（選 C）；**v24 只帶打字路徑**（選 A，不搭別的引擎改動）。
- 原生證據：`feature-protocol/f168-native-routes/`（`420c0301`，15 臂 × 3 回）、M0（`m0-input-path-census.json`）、M1（`m1-reader-01.json`），都在 `ded5cfe5`。
- finding 168（產品把打字做成 paste）、169（多格貼上第二格起逐位元組解碼，core）、166（原生 harness 的鍵序，與產品無關）。
- 形狀照 `specs/SPEC-M3-link-batch-v22.md`；有序指令的定義照 `specs/SPEC-M3-ordered-commands.md` §5.2、§16.4。

證據標記：**已觀察**＝量過或在產物上讀到；**讀原始碼**＝沒量；**推論**＝從前兩者推出；**未量**＝沒有人量過，後面寫怎麼量。

## 1. 為什麼要有

- **finding 168（已觀察）**：計數的 S5-02 在 Chrome `shift-Right@cell-end/type` 停下（前面 401 格 PASS）。從 A1 文字末端 Shift+Right 選到 B1、打 `x`：產品存成 A1 `A1 cell textx`／B1 `B1 cell textx#`；綁定的原生鍵盤參考（run-03）是 A1 空、B1 `x`。
- **成因是產品的路線，不是 WASM build（已觀察）**：`probe_engine.cpp` 的 `handleInsertText` 先用 LOK `paste(text/plain;charset=utf-8)`，失敗才逐字送鍵；回覆寫著 `method: "paste"`。原生 LOK 26.8 上，`paste` 給出與產品一模一樣的結果；鍵盤、`.uno:InsertText`、ext-text-input 都給 A1 空／B1 `x`。在游標處與純文字選取上，paste 與鍵盤相同——所以另外 401 格會過；只有表格選取模式不同（`swdtflvr.cxx` 的 `PasteData` 在表格模式跳過刪除選取，讀原始碼）。
- **修法要動引擎**：路線在引擎裡，只能重新連結；連結是擁有者的步驟。

## 2. 範圍

**改的**（全部在後繼身分 `e2-editor-v24` 之下）：

1. **引擎**：新的**附加** export `oxsdk_document_insert_typed_text`，在新 define `OXSDK_E2_V24_TYPED_INSERT` 之下編譯；舊的 `oxsdk_document_insert_text` 一個位元組的行為都不變（§4.1）。
2. **worker**：新檔 `sdk/v24-feature-worker.js`，由 v23 的 `sdk/v23-feature-worker.js`（`3fd3e1e6…`）衍生；v23 那份**不改**（它被 generation 76 綁著，也被複製進 v23 的 profile）。
3. **SDK**：`sdk/document-sdk.js` 的 `insertText` 依 `options.metadata.source` 決定路線（§4.3）。
4. **頁面**：`web/e2-editor-app.js` 切到 v24（worker URL、wasm 釘選）並要求 manifest 宣告新路線（§4.4）。
5. **身分**：新 profile `e2-editor-v24`；**編輯器 ABI 仍是 6**（裁決 2）；manifest 多一個宣告葉 `editorContract.typedInsert`；匯出表多一行。新殼層 generation（77）。

**不改的**：

- `editor-shell/editor-session.js`、`input/input-adapter.js`（E1-C 的 bundle `e1/editor-shell-bundle-v2.json` 綁著）：它們已經把 `source` 帶到 `document.insertText(text, options)`（`editor-session.js:93`、`:511`，讀原始碼，裁決 1 與主 session 都核對過）。
- 真的貼上（`clipboard-event`／`clipboard-api`）、沒有 metadata 的公開 `insertText`、`replaceSelection`、`pasteMarkdown`：照舊走 LOK paste，逐位元組相同。
- 帶 U+000A／U+000D 的打字：照舊走 paste（Enter 是另一族，要改得另裁，裁決 1 §SUMMARY）。
- `kMaxInternalEditorAction`、gesture 表、任何動作 id（不是編輯器動作，裁決 1 §1）。
- finding 169 的修法（core 的缺陷；修要 core patch＋擁有者建置，上游擱置）；它在本批是**正向對照與具名限制**（裁決 1 §2）。
- 166（原生 harness 的鍵序；產品的鍵序由產品自己保證）、core、Calc（`spreadsheet-shell/calc-document-sdk.js` 有自己的 engine 類別，只從共用 SDK 匯入 `DocumentSdkError`，讀原始碼）。
- 連結旗標：v23 的那一行照抄（`link_product_stack_1m`，1 MiB pthread stack）。

## 3. 決定紀錄

| 項 | 決定 | 出處 |
|---|---|---|
| 路線 | 打字（`beforeinput`／`composition`）走 `.uno:InsertText`；真的貼上與沒有來源的 `insertText` 照舊走 paste | 裁決 1 §SUMMARY |
| B（所有單行 `insertText` 都改 InsertText） | 不採：會把單行 Ctrl+V 改成取代選取、單行與多行貼上分家、169 只藏一半 | 裁決 1 |
| C（逐字送鍵） | 不採：`postKeyEvent` 沒有完成回呼（沒有有序證明）、走 166 那條路、vcl 鍵碼 16 位元（非 BMP）、IME 會變成 N 個鍵事件 | 裁決 1 |
| ext-text-input | 不採：`postExtTextEventAsync` 沒有結果回呼 | 裁決 1 |
| 形狀 | 新的附加 export；舊 export 保持 paste 語意 | 裁決 1 |
| 編輯器 ABI | **留 6**；不升 7（ABI 是動作 allowlist 的版本，新 export 不是動作；前例 page-rectangles、paste-markdown） | 裁決 2 §SUMMARY |
| 宣告 | `editorContract.typedInsert: "document-sdk-insert-typed-text"` | 裁決 2 §3 |
| 舊 wasm 配新 manifest | v24 worker 在 init 檢查每個宣告的 export 都在 binary 裡，缺就以具名錯誤拒絕 init（ABI 7 原本會擋的那一條） | 裁決 2 §SUMMARY |
| worker 的 profile 條件 | `featureExtendPermitted` 寫死 `e2-editor-v23`，v24 worker 必須改成自己的名字，否則延伸在 v24 上靜默關掉 | 裁決 2 §SUMMARY |
| 完成證明 | `UNO_COMMAND_RESULT` **出現**就是證明；不看 `success`（M1：每回都是 `false`）、不看 `wasModified`（M1：文字變了仍是 `false`） | 裁決 1 §1、M1 |
| 順序 | 產品是 unipoll，`.uno:InsertText` 在 `postUnoCommand` 裡同步派送，沒有新的排序風險 | 裁決 1、主 session 讀 `init.cxx` 核對 |
| 沒宣告的 profile | SDK 完全不看 metadata，請求逐位元組同今天，不加新錯誤；`INSERT_ORIGIN_UNKNOWN` 只在有宣告時生效 | 裁決 2 追問 A1 |
| 「v24 上不得靜默貼上」由誰守 | v24 頁面開檔時要求宣告（`PAGE_BUILD_MISMATCH`）；worker 的宣告閘門另守一層 | 裁決 2 追問 A2 |
| 路線的兩個陳述 | 請求的 `route` 是 SDK 的決定，回覆的 `method` 是引擎做了什麼；逐請求都記、要一致 | 裁決 2 追問 A3 |
| 169 | 不修；當正向對照（T5）與具名限制（§10） | 裁決 1 §2 |
| 批次組成 | 只有打字路徑 | 擁有者 2026-10-28 |

## 4. 設計

### 4.1 引擎

- **`oxsdk_document_insert_typed_text(requestId, documentHandle, utf8, utf8Length)`**：與 `oxsdk_document_insert_text` 同樣的參數形狀與邊界檢查（`sdk_api.cpp:163-173` 那一段的樣子），呼叫 `probe::insertTypedText`，送出新的指令種類 `CommandType::InsertTypedText`。全部在 `#ifdef OXSDK_E2_V24_TYPED_INSERT` 之下；這個 define 要求 `OXSDK_E2_V23_FEATURE_ABI6`（沒有就 `#error`，比照 `editor_api.h` 的寫法）。
- **`handleInsertTypedText`**（在引擎執行緒）：
  1. `requireDocument(command, "insert")`。
  2. 內容檢查，**不派送**就拒絕：不是合法 UTF-8 → `INVALID_UTF8`；含 U+0000、U+000A、U+000D → `INVALID_ARGUMENT`（SDK 不會送這些，見 §4.3；這是邊界，不是路由）。兩者回覆都帶 `dispatched: false`。
  3. `expectOrderedUno(".uno:InsertText")`，登記回覆，`postUnoCommand(".uno:InsertText", {"Text":{"type":"string","value":<jsonEscape(text)>}}, true)`。
  4. 回覆在派送後的第一次 poll 組（`SPEC-M3-ordered-commands` §5.2、§16.4）：`orderedUnoResult(".uno:InsertText", payload)` 為假 → `emitOrderedMissingProof(command, "insert", "UNO_COMMAND_RESULT")`，即 `failureShape: "proof-absent-at-poll:UNO_COMMAND_RESULT"`、`code: "MUTATION_OUTCOME_UNKNOWN"`（照舊是錯誤，不是成功）。為真 → `advanceRevision()`，送 `{"type":"inserted","method":"uno-insert-text","completion":"uno-command-result","resultPayload":<原始 payload>, schemaVersion, requestId, documentHandle, revision}`。
  5. **不看 `success`、不看 `wasModified`**：M1 的 16 對 × 3 回、每一回 payload 都是 `{"success":false,"result":{"type":"void"},"wasModified":false,…}`（已觀察，原生）；讀原始碼的成因是 FN_INSERT_STRING 那一支沒有 `rReq.Done()`（`textsh.cxx:153-156`）而 `bSuccess = aItem.is()`（`unoctitm.cxx:771`）。
- **`handleInsertText` 一行不改**；v23 的物件與 v24 的物件從同一份原始碼編，舊路徑在兩邊的前置處理輸出相同（S3-v24 驗）。
- `jsonEscape` 的引數用 `command.text`（已排除 NUL，所以 `c_str()` 不會截斷）。

### 4.2 worker（`sdk/v24-feature-worker.js`）

由 v23 的 worker 衍生，**與它的差異是封閉清單**（W1，§6.1）：

1. **`insertText` 的路由**：payload 的 `route` 為 `"uno-insert-text"` → 呼叫 `oxsdk_document_insert_typed_text`；為 `"paste"` 或沒有 `route` → 呼叫 `oxsdk_document_insert_text`（今天的那一行）；其他任何值 → `INVALID_ARGUMENT`、`dispatched: false`，不碰 WASM。
2. **宣告表**：`DOCUMENT_EXPORT_OPERATIONS` 加 `typedInsert`（`field: "typedInsert"`、`declaration: "document-sdk-insert-typed-text"`）；`route: "uno-insert-text"` 只在宣告存在時才送進 WASM，否則 `UNSUPPORTED_OPERATION`、`dispatched: false`。
3. **init 的存在檢查**（裁決 2）：manifest 宣告的每一個文件層 export（`DOCUMENT_EXPORT_OPERATIONS` 的每一列，`typedInsert` 在內），其 WASM 符號都必須存在；缺任何一個就拒絕 init，錯誤碼 `DECLARED_EXPORT_MISSING`，訊息帶缺的符號名。位置在既有的編輯器 ABI 精確比對旁邊（`v23-feature-worker.js:1264-1280` 那一段）。
4. **profile 條件**：`featureExtendPermitted` 的 `profile === "e2-editor-v23"` 改成 `"e2-editor-v24"`；ABI 條件照舊是 6。
5. 檔頭註解說明衍生來源與本節。

### 4.3 SDK（`sdk/document-sdk.js`）

- 匯出一張表 `INSERT_ROUTE_BY_SOURCE`：`beforeinput → "uno-insert-text"`、`composition → "uno-insert-text"`、`clipboard-event → "paste"`、`clipboard-api → "paste"`。
- `insertText(text, options)`：
  1. manifest **沒有**宣告（`editorContract.typedInsert !== "document-sdk-insert-typed-text"`）→ **完全不看 metadata**：payload 與今天逐位元組相同（`{documentHandle, text}`，沒有 `route`），也**沒有新的錯誤**。那是該 profile 出貨時、被量過的路線（裁決 2 追問 A1）。
  2. manifest 有宣告 → `source = options.metadata?.source`：有值（不是 `undefined`、`null` 或空字串）而且不是表裡的鍵 → 丟 `INSERT_ORIGIN_UNKNOWN`、`details.dispatched: false`，不送請求（裁決 1：未知來源是錯誤，絕不靜默貼上）。否則**每一個** `insertText` 都帶 `route`：表給 `"uno-insert-text"` 而且文字不含 U+0000／U+000A／U+000D → `"uno-insert-text"`；其餘（真的貼上、沒有 metadata、含換行或 NUL 的打字）→ `"paste"`。所以 v24 上沒有 `route` 的請求只可能來自別的 SDK，而且看得出來。
- **為什麼不是「沒宣告就拒絕打字」**（裁決 2 §2 的原句，已由它自己撤回）：共用 SDK 的頁面不只 v24 的產品頁——`web/` 底下 28 個頁面 import 它，其中 `web/e1-editor-app.js`、`web/demo-editor-app.js` 與 E1／E2 的 harness 頁都經同一個 adapter 進 `DocumentSdk.insertText`（讀原始碼，fable 也核對過），它們的 profile 永遠不會有這個宣告；照字面做，下一次從樹組裝時它們全都打不了字。而且沒有人普查過 adapter 以外帶 `metadata.source` 的呼叫者，所以連新錯誤也不加在沒宣告的 profile 上。「v24 上不得靜默貼上」改由 v24 頁面在開檔時把關（§4.4），worker 另有自己的一層（§4.2 第 2 項）。

### 4.4 頁面與殼層

- `web/e2-editor-app.js`：`workerUrl` 改成 `./profiles/e2-editor-v24/sdk-worker.js`；`PINNED_WASM_SHA256` 改成 v24 實際 wasm 的前 16 位（連結後才知道）；開檔後那一處既有的釘選檢查（約 `:3851`）旁再要求 `editorContract.typedInsert === "document-sdk-insert-typed-text"`，不成立就走同一條 `PAGE_BUILD_MISMATCH`／`showExpired` 路——沒有宣告就一個字都送不出去。
- 頁面的十處 `abiVersion === 6` **一個都不動**（裁決 2）。
- **殼層 generation 77**：`sdk/document-sdk.js` 與 `web/e2-editor-app.js` 都在 generation 76 的綁定集合裡（`e2/editor-shell-v2-bundle-v76.json`），所以要凍新的 generation；`sdk/v24-feature-worker.js` 照 v23 worker 的前例列為 excluded（由 profile 的 `workerSha256` 另外綁）。**要等本批的殼層改動全部做完才凍**（CLAUDE.md「工作結論」）。v76 原樣保留。E1-C `intact: true`。

### 4.5 manifest 與身分

- profile 名 `e2-editor-v24`、`sdkVersion` 跟著換名；`editorContract.abiVersion` 6；動作、gestures、limits、`pageRectangles`、`pasteMarkdown`、`redo` 等每一個既有的葉都等於 v23；新葉 `editorContract.typedInsert`；`wasmSha256`、`loaderSha256`、`workerSha256` 換成 v24 的。
- 匯出表：v23 的 36 行原樣，後面加一行 `_oxsdk_document_insert_typed_text`。

## 5. 身分與連結的機械

### 5.1 Makefile 的 v24 區塊

接在 v23 的區塊之後（`Makefile:2038` 起那一段的形狀）：

- `E2_V24_BUILD := build/e2/editor-v24`、`E2_V24_DIST := dist/profiles/e2-editor-v24`、物件取自 `$(E2_C_SOURCES)`。
- **編譯規則**：v23 的規則逐字照抄，只換 v24 的路徑，defines 多一個 `-DOXSDK_E2_V24_TYPED_INSERT`。
- **匯出表**：`build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/exports.txt` 加一行 `_oxsdk_document_insert_typed_text`。
- **worker**：`cp sdk/v24-feature-worker.js`；前置檢查驗衍生來源是封存的 v23 worker（`3fd3e1e6…`）。
- **連結**：從第一次連結就受守衛（`refuse_unasked_relink`），呼叫 `link_product_stack_1m`（與 v23 同一個 macro，不新增 macro）。
- **manifest**：新的產生器 `tools/build_e2_v24_feature_profile.py` 與契約檢查 `tools/check_v24_feature_contract.py`——**新檔**；v23 的兩支寫死 profile 名與 ABI，而且它們的位元組被 v23 的完成讀取綁著（裁決 2 §1 第 4 點），不改。
- 只跑測試的 `test-v24-feature-static`（比照 `test-v23-feature-static`）。

### 5.2 連結前的其他改動

- `test-e2-c-static` 的 M1-1 載體行加 `--carrier E2_V24=probe_engine,sdk_api,editor_api`。**先紅**：區塊加進去、載體照舊時 M1-1 必須紅並點名 `E2_V24`（證人 commit），加了之後綠。這是新規則的綁定（前例：v21、v22），不是修理。
- `tools/what_the_link_ships.py` 加 variant `link-batch-v24`（資料：v23 的 defines＋`OXSDK_E2_V24_TYPED_INSERT`、`E2_V24_OBJECTS`、md4c 的 `-I`）。
- 擁有者的連結輔助腳本 `tools/link_v24_feature_owner.sh`（比照 `link_v23_feature_owner.sh`：拒絕既存的 build 目錄／profile／log，`make -j1 ALLOW_FROZEN_RELINK=1 dist/profiles/e2-editor-v24/sdk-manifest.json`，`pipefail` 存完整 log 到 `build/link-v24-feature-01.log`，跑完印五個 artifact 的雜湊）。

### 5.3 v23 的封存直接沿用

`build/archive/e2-editor-v23-fe1f99cd-worker-3fd3e1e6/`：2026-10-28 `sha256sum -c SHA256SUMS` 5/5 OK，四個檔與 `dist/profiles/e2-editor-v23/` `cmp` 相同，`exports.txt` 與 `build/e2/editor-v23/exports.txt` 相同，`sdk/v23-feature-worker.js` 的雜湊等於封存的 worker（已觀察）。再複製一份會逐位元相同，所以不做；連結前在手冊 §0 再驗一次。

### 5.4 v23 的儀器不動

v23 的 runner、判讀工具、原生 harness 與其建置腳本（含 `build_v23_native_s5_owner.py`、`build_v23_native_s5_type_owner.py`）的位元組被 `counted-r1-s5-01/cohort.json` 的 `instrumentSources` 與原生 run-03 的 `identity.json` 綁著（AGENTS.md）。v24 的儀器一律是**新檔**（包裝或衍生），不編輯 v23 的。V0（§6.1）證明這件事。

### 5.5 連結前的凍結集合

`findings/evidence/link-batch-v24/pre-link/frozen-set-before.sha256`：`wasm_sdk_probe/dist/profiles/` 與 `wasm_sdk_probe/build/archive/` 底下每一個一般檔，在本檔釘死之後、連結之前寫。

## 6. 判準總表

形式照 CLAUDE.md「驗收判準的形式」§1；每條附「若沒做或紅」的預設（§2）。

**通則**：

- **缺報、缺回、NE 一律等於「沒做」**，套用該條的預設。
- **證據的身分**：連結後每份瀏覽器報告都帶受測的 wasm、loader、worker、manifest、頁面雜湊與殼層 generation；與 `dist/profiles/e2-editor-v24/` 或 generation 77 不符就作廢，等於沒做。
- **v23 的紀錄不轉移**：R1 144/144（`e5cf298e`）、四臂 24/24（`431bce12`）、S1–S4 234/234、counted-02 的停止、certificate 05 都留在 v23；v24 從零開始（裁決 1 §4）。

### 6.1 連結前（原始碼與單元測試）

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| T3 | **工具封閉**：測試抽出 `input/*.js` 裡每一個 `source: "<字面量>"`，斷言集合**等於** `INSERT_ROUTE_BY_SOURCE` 的鍵集合（多一個或少一個都紅）；非空洞性：讀到的檔數 ≥ 2、字面量 ≥ 4，否則紅（目錄改名時要紅，不是回報「零」）。執行期（對**有宣告**的 manifest，裁決 2 追問 A1）：未知的非空 `source` → `INSERT_ORIGIN_UNKNOWN`、`dispatched: false`、沒有送出請求。**紅案 (iv)**：在 scratch 複本的 adapter 加 `source: "fake"` → 測試紅 | 形式二＋逐實例 | 連結不交給擁有者 |
| U1 | SDK 對應的單元測試，逐列：有宣告時，四個已知來源、沒有 metadata、含 LF／CR／NUL 的 `beforeinput` 文字各自的 `route`（含換行或 NUL → `paste`），而且每一個請求都帶 `route`；**沒宣告時**，同一組輸入加上一個未知來源，payload 的鍵集合恰好是 `{documentHandle, text}`、沒有任何一列丟錯 | 逐實例（表的每一列） | 連結不交給擁有者 |
| W1 | `sdk/v24-feature-worker.js` 對封存的 v23 worker 做 diff，**只有** §4.2 的五項（封閉清單，現在寫下）；其他任何一處不同：紅 | 逐實例（這一對） | 連結不交給擁有者 |
| W2 | worker 的 node 測試：`route` 三種值（`uno-insert-text`、`paste`、缺）各呼叫對的符號、第四種值 `INVALID_ARGUMENT` 且沒有呼叫任何符號。**紅案 (d′)**（裁決 2 追問 A2）：沒有 `typedInsert` 的 scratch manifest 上 `route: "uno-insert-text"` → 既有的 `documentExportDeclared` 閘門回 `UNSUPPORTED_OPERATION`，沒有呼叫任何符號。**紅案 (viii)＝裁決 2 (e)**：v23 的 manifest 給 v24 worker 的 `featureExtendPermitted` → false，v24 的 → true | 逐實例 | 連結不交給擁有者 |
| E1 | 引擎的原始碼測試（不連結）：`handleInsertTypedText` 對 LF、CR、NUL、壞 UTF-8 回 `dispatched: false` 的錯誤而且在那之前沒有 `postUnoCommand`；回覆組裝只用 `orderedUnoResult` 的存在、不讀 `success`／`wasModified`；`handleInsertText` 的位元組在 v24 區塊落地前後相同 | 逐實例 | 連結不交給擁有者 |
| S3-v24 | 在 `wasm_sdk_probe/`、`build/e2/editor-v24/` 還不存在時，`make -n dist/profiles/e2-editor-v24/sdk-manifest.json` 存成 `findings/evidence/link-batch-v24/pre-link/make-n-v24.txt`；把 `editor-v24`／`e2-editor-v24`／`E2_V24` 換回 v23 的名字之後，對 v23 的同一個目標的 `make -n`（同一天取、同一棵樹）做以空白分詞的 word diff，不同的地方**恰好**是（封閉清單）：① 編譯行多一個 token `-DOXSDK_E2_V24_TYPED_INSERT`；② 匯出表的配方（v23：`cp` v22 的封存；v24：v23 的封存＋一行）；③ worker 的來源（`v23-feature-worker.js` → `v24-feature-worker.js`）與它的前置檢查；④ manifest 產生器與契約檢查的檔名；⑤ 守衛那一行的說明文字。其他任何 token 不同：紅 | 逐實例（這一對） | 連結不交給擁有者 |
| V0 | **v23 的綁定還是綠的**：實作全部落地之後，`counted-r1-s5-01/read-completion.py`（新的輸出檔名）exit 0；原生 run-03 的身分重讀（`read_v23_native_s5_type.py`）通過；`check_e1_c_bundle_intact.py` `intact: true` | 逐實例 | 停手：某個被綁的位元組動了，先找出來還原 |
| M1-1 | §5.2 的先紅再綠 | 逐實例 | 連結不交給擁有者 |
| J-red | v24 判讀工具（T2 的那一支）在任何 v24 執行之前的紅案：**(ii)** 一份 `method: "uno-insert-text"` 但沒有 `UNO_COMMAND_RESULT`（`proof-absent-at-poll`）的合成回覆 → 該格 FAIL，絕不 PASS；**(iii)** v23 counted-02 `shift-Right@cell-end/type` 的保留頁面餵給 v24 的判讀工具 → FAIL，理由點名路線（`method: "paste"`）；**(v)** 把 T2 的路線條款、T3 的集合相等條款各拿掉一次，對應的紅案必須轉綠＝守衛有在作用（拿掉後紅案仍紅，代表紅另有原因，該守衛沒被測到） | 逐實例 | 該判讀工具不得用來判 v24 |

### 6.2 連結之後（靜態，連結當天）

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| L1 | 連結 log：v24 的物件全部重新編譯、一次連結、`-DOXSDK_E2_V24_TYPED_INSERT` 出現在每一條 v24 的編譯行；loader 匯出 `_oxsdk_document_insert_typed_text`（loader 對實際 wasm 的公開函式比對，v23 runbook 的作法） | 逐實例 | v24 不綁定 |
| I1-v24 | X1（`tools/check_profile_identity.py --candidate dist/profiles/e2-editor-v24 --reference dist/profiles/e2-editor-v23 …`）印 `VERDICT PASS`，差異**恰好**是（裁決 2 §3）：`profile`／`sdkVersion` 換名；wasm 不同；loader 雜湊；`--declared-worker <v24 worker sha>`；`--declared-new-leaf .editorContract.typedInsert="document-sdk-insert-typed-text"`；`--declared-export _oxsdk_document_insert_typed_text`。**沒有** `--declared-changed-leaf`：`abiVersion` 仍是 6。**紅案 (a)**：v24 manifest 的複本改 `abiVersion: 7` → X1 的 manifest 條款紅；**(b)** 宣告了葉但 manifest 沒有、宣告了 export 但匯出表沒變 → 各自的宣告條款紅。**凍結集合**：`frozen-set-before.sha256` 每一個檔雜湊相同，`dist/profiles/`、`build/archive/` 底下除了 `dist/profiles/e2-editor-v24/` 沒有新檔（封存 v24 之前量）。`ScDocShell` 0 次。E1-C `intact: true` | 逐實例 | v24 不綁定 |
| A1 | **立刻封存** v24 到 `build/archive/e2-editor-v24-<wasm sha8>-worker-<worker sha8>/`（五個檔＋`SHA256SUMS`＋`ATTRIBUTION.md`） | 逐實例 | 不得做任何瀏覽器執行 |

### 6.3 連結之後（瀏覽器，任何計數之前）

| # | 判準 | 形式 | 若沒做或紅 |
|---|---|---|---|
| (vi) | **裁決 2 (c)**：v24 的 manifest＋封存的 v23 `probe.wasm` → worker init 以 `DECLARED_EXPORT_MISSING` 拒絕，**不是**第一個字才出現的 `WORKER_EXCEPTION` | 逐實例 | 舊 wasm 的風險在 v24 上**沒關**，v24 不綁定 |
| (vii) | **裁決 2 (d)，依追問 A2 改成真的頁面執行**：v24 的 manifest 拿掉 `typedInsert` → 頁面開檔時走 `PAGE_BUILD_MISMATCH` 拒絕，該窗內**零個** `insertText` 請求。**正向對照**（同一天、同一頁面）：宣告在 → 開檔成功，第一個打的字的請求帶 `route: "uno-insert-text"`。正向對照不成立＝這一臂沒量到東西，NE | 逐實例 | v24 不綁定 |
| M2 | **裁決 1 §5 M2**：S5 的 84 個 type 格 × 兩個瀏覽器的準備執行（不計數）：`.uno:InsertText` 的 `proof-absent-at-poll` 為 0；每一個 type 格的回覆 `method: "uno-insert-text"`；回覆之後的存檔含那個字；table2 等於 run-03 | 逐實例（格 × 瀏覽器） | 不做計數的 S5 |
| T5 | **裁決 1 T5**：兩個瀏覽器、各 3/3，用**真的鍵**（CDP 逐字送鍵，不是 `commitText`）：table2 打 `x` → A1 空／B1 `x`；table2 Ctrl+V `x` → `A1 cell textx`／`B1 cell textx#`（169 的對照：證明貼上路線沒變、修法不是 B） | 逐實例（6＋6） | NE → 不做計數的 S5 |
| (i) | **裁決 1 (i)**：scratch SDK 把 `beforeinput` 對到舊 export → T2 紅（判讀工具看得到路線） | 逐實例 | T2 不得用來判 v24 |
| T4 | **裁決 1 T4**（形式二）：產品路徑 runner 在 v24 上，母體由工具從報告生成——每一個發出 `insertText` 的請求：帶 `route`，而且 `route` 與回覆的 `method` 一致（`uno-insert-text`↔`uno-insert-text`、`paste`↔`paste`）；路線為 paste 的檢查（真的貼上、`replaceSelection`、`pasteMarkdown`、插入欄位按鈕）期望值一個字不改而且 PASS。若某支檢查比對**請求 payload** 的位元組，v24 多出的 `route: "paste"` 是宣告過的差異、不是退步；結果（存檔、回覆）仍要逐位元組相同（裁決 2 追問） | 逐實例＋形式二 | NE；v24 不得宣稱「貼上沒變」 |

### 6.4 計數

| # | 判準 | 若沒做或紅 |
|---|---|---|
| S5-v24 | 新目錄、兩個瀏覽器、完整母體，counted-01／02 與所有準備執行**零**分（裁決 1 §4）。**T1**（逐實例，對產生器的 type 母體）：每一個參考解析成 native 的 type 格，v24 存檔後的段落文字等於 run-03 的存檔後；比較器不變（裁決 3）；參考是 settled-WASM 的格照既有協定、用 v24 自己新產的參考。**T2**（工具封閉，逐請求，依裁決 2 追問收緊）：每一個計數的 type 格，其 `insertText` 請求帶 `route: "uno-insert-text"`，**而且**回覆 `method == "uno-insert-text"`、`completion == "uno-command-result"`；type 格的請求沒有 `route`、或出現任何 `method: "paste"`、或 proof-absent → 該格 **FAIL**，不是 NE | T1 NE（v24 沒有 S5 的立足點）；T2 預設 FAIL |
| R1-v24 | R1 144 在 v24 上 | v24 不得宣稱 R1 |
| S14-v24 | S1–S4 234 在 v24 上 | 同 |
| A4-v24 | 四支產品臂在 v24 上 | 同 |
| K | 計數鏈在最終位元組上成立，照 `release-count-batched`（**這就是批次一直在等的引擎改動**）：殼層凍結、宿主新版本、`BINDING` 之後，在擁有者指定的 ddev 時段、脫離 session、先問。累積的未計數改動以 `research/2026-10-25-count-batching-and-next-work.md` 的帳為底，加上之後的；清單在 K 準備時由工具從 git 與宿主版本生成，列在交接 | v24 是未計數候選；名義出貨版本不變 |

**計數語意（§9）**：v24 沒有任何乾淨的母體，所以沒有東西歸零；T1–T5 與紅案都在任何 v24 執行之前寫下（本檔）。截止＝每個瀏覽器第一個完整、乾淨的 S5 母體落地；之後的顧慮變成 finding 或事後工作。

## 7. 連結（擁有者的步驟）

`handoff/RUNBOOK-relink-v24.md`，照 `RUNBOOK-v23-feature-link.md` 的形狀。交給擁有者的是**一行短指令**：

```bash
cd /home/jiajun/LibreOffice/study_LiteCore/wasm_sdk_probe && bash tools/link_v24_feature_owner.sh
```

`ALLOW_FROZEN_RELINK=1` 只給 v24 這一個目標；v8、v15、v18–v23 永遠不給。前提：§6.1 全綠、證人都已 commit、frozen set 已寫。預估 3–10 分鐘（v23 的同型連結）。

## 8. 順序

1. 釘死本檔（commit）。
2. 引擎碼、worker、SDK、頁面的宣告檢查（§4.1–§4.4 中不需要實際雜湊的部分）、單元測試與紅案；Makefile 區塊、M1-1、`what_the_link_ships`、產生器與契約檢查；S3-v24；V0；frozen set；手冊與輔助腳本。
3. **擁有者連結**。
4. §6.2：L1、I1-v24 與紅案 (a)(b)、封存。
5. 頁面切到 v24（wasm 釘選）、殼層其餘改動做完、**凍 generation 77**。
6. §6.3：(vi)、(vii)、M2、T5、(i)、T4。
7. §6.4：S5-v24（計數）、R1、S1–S4、四臂。
8. 宿主新版本、`BINDING`、K。

## 9. 在 v24 上重驗 vs 留在 v23（裁決 1 §4）

- **重跑**：完整 S5（新目錄）、R1 144、S1–S4 234、四支產品臂、計數鏈。
- **留給 v23 當它的紀錄**：`e5cf298e` 的 R1、counted-02 的停止、`431bce12` 的四臂、certificate 05。
- **不綁產品、原樣沿用**：run-03 原生 type 參考（雜湊綁在計畫上）、Astra A 的刪除分割、f168 原生路線。裁決 3 與 Astra A 都不動，不申請任何縮小。

## 10. 具名限制與發佈說明

出 v24 的每一版發佈說明都要寫（v23 從未出貨，所以沒有要拿掉的句子）：

- **L-typed-no-autocorrect**：打字不再經過自動校正（M1：鍵盤在文件末端把 ` teh ` 改成 ` The `，`.uno:InsertText` 不改）。v23 的 paste 本來也沒有，所以不是對 v23 的退步，是與桌面 Writer 的差異。S5 只打 `x`，不在 S5 範圍內。
- **L-169-multicell-paste**：把純文字貼到跨多格的表格選取時，第二格起的內容會被逐位元組解碼（`x`→`x#`、`中`→`-N`、`é` 消失）；這是 Writer 本身的缺陷，桌面版**未確認**。
- **L-168-paste-routes**：真的貼上、插入欄位按鈕、`replaceSelection` 在跨格的表格選取上仍是 Writer 的貼上語意（加在後面、不取代選取，再加上 169）。
- **L-typed-line-break**：打字內容含換行時照舊走貼上路線。
- **M1 收尾的異常（不是限制，是待辦）**：M1 的原生程序在最後一筆紀錄之後以 exit 1 結束，`native.stderr` 有一行 `Unspecified Application Error`；所有紀錄與存檔都驗過。**工作項（不是閘門）**：在引擎依賴 notify 模式的結果之前重跑 M1 一次；再出現就登錄成 finding。產品不會這樣拆掉 LOK，所以不擋 v24。

page honesty（`check_m3_page_honesty.py`）在 v24 的頁面上照 K 鏈的前提跑，本批沒有新增或拿掉控制項。

## 11. §34.4

本批連結前的工具改動都是**新增**：v24 worker、SDK 的對應表、引擎的新 handler、T3／U1／W2／E1 的測試、v24 的產生器與契約檢查、`what_the_link_ships` 的 variant（資料）、M1-1 的載體行、輔助腳本與 v24 判讀工具。因執行而修 0、因審核而修 0。

## 12. 修訂紀錄

- 2026-10-28：釘死（裁決 1、裁決 2 與它的追問、擁有者的兩個決定）。草稿期間 §4.3 曾寫「未知來源在所有 profile 上都丟錯」，釘死前依裁決 2 追問 A1 改成只在有宣告時；沒有任何執行讀過那一版。

## 13. 紅案對照表

| 紅案 | 出處 | 本檔 |
|---|---|---|
| (i) scratch SDK 把 `beforeinput` 對到舊 export → T2 紅 | 裁決 1 | §6.3 |
| (ii) 有 `uno-insert-text` 沒有結果 → FAIL | 裁決 1 | §6.1 J-red |
| (iii) v23 counted-02 的那一格 → v24 判讀工具 FAIL | 裁決 1 | §6.1 J-red |
| (iv) `source: "fake"` → T3 紅（執行期臂用有宣告的 manifest） | 裁決 1、追問 A1 | §6.1 T3 |
| (v) 拿掉 T2／T3 的守衛 → 對應紅案轉綠 | 裁決 1 | §6.1 J-red |
| (a) `abiVersion: 7` → X1 紅 | 裁決 2 | §6.2 I1-v24 |
| (b) 宣告了卻沒有 → X1 紅 | 裁決 2 | §6.2 I1-v24 |
| (vi)＝(c) v24 manifest＋v23 wasm → `DECLARED_EXPORT_MISSING` | 裁決 2 | §6.3 |
| (vii)＝(d) 拿掉宣告 → 頁面拒絕開檔＋正向對照 | 裁決 2、追問 A2 | §6.3 |
| (d′) 沒宣告的 manifest 上 `uno-insert-text` → worker `UNSUPPORTED_OPERATION` | 追問 A2 | §6.1 W2 |
| (viii)＝(e) `featureExtendPermitted` 的 profile 條件 | 裁決 2 | §6.1 W2 |

## 14. 實作逼出的更正（2026-10-28，只追加；任何 v24 的連結與瀏覽器執行之前）

四件事都是實作時讀到或量到的具名事實逼出來的，原文不動、以本節為準（CLAUDE.md §9、§10）。證據 `findings/evidence/link-batch-v24/pre-link/README.md`。

1. **§4.2 的 worker 改動是六項，不是五項；W1 的封閉清單跟著改。**第 6 項：`inserted` 回覆的投影是白名單，v23 只轉 `{ method, revision }`（`sdk/v23-feature-worker.js:887-890`，已觀察），照原清單做，新路線的 `completion` 與 `resultPayload` 到不了頁面，T2 永遠讀不到證明。v24 worker 只在引擎送了這兩個欄位時才轉，所以 paste 的回覆仍是 v23 的形狀。W1 的實作是 `tests/v24-worker-delta.json`（13 個帶項次標籤的 hunk）＋`tests/test_v24_feature_worker_delta.py`：套到封存的 v23 worker 上要逐位元組等於 v24 worker。這條更正與 W1 的證據同一個 commit 落地；沒有任何 W1 結果是在五項的文字下登錄的。
2. **V0 的前提錯了，改成 V0′。**v23 的 `config()`／`identity()`（`tools/v23_feature_selection_cases.py:484-500`）要求活的樹裡 generation 76 的每一個殼層檔都等於綁定的位元組，所以只要有殼層改動進樹（本批的 `sdk/document-sdk.js`），在活的樹上重讀 v23 就**依構造**是紅的（已觀察：`final shell source/dist differs: sdk/document-sdk.js`）。V0 要證的是「除了宣告的殼層檔，沒有碰到任何 v23 綁住的位元組」，所以 V0′ 是：(a) **只**把宣告的殼層檔換回 generation 76 的位元組時，`read-completion.py` exit 0（換完立刻還原並核對雜湊）；(b) 原生 run-03 的重讀與已 commit 的 `reader-03.json` 相同；(c) E1-C `intact: true`。宣告的殼層檔現在是 `sdk/document-sdk.js`；切換（§8 第 5 步）之後加上 `web/e2-editor-app.js`，V0′ 照樣兩個一起換回。三件 2026-10-28 都成立。
3. **S3-v24 兩邊都用 `make -n -B`。**v23 的 build 與 profile 目錄已存在，不加 `-B` 只有 v24 會印出兩行 `mkdir -p`；加了兩邊都印（各兩行）。比較前只把 `editor-v24` 換成 `editor-v23`（`E2_V24` 不換，否則 define 本身也被換掉）。結果的十二行差異恰好落在 §6.1 S3-v24 的五類裡。
4. **§8 第 2 步不改頁面。**§4.4 的頁面改動（worker URL、wasm 釘選、`typedInsert` 的要求）全部在連結之後的切換一次做：頁面現在釘著 v23，先加 `typedInsert` 的要求會讓活的頁面拒絕開 v23。

另記：E1 的基準是釘死本檔的 commit `ceaa2770`（四個檔的 blob 雜湊寫在 `tests/test_v24_typed_insert_engine.py`）。J-red（v24 判讀工具的紅案）排在連結之後、M2 之前；它在 §6.1 的預設是「該判讀工具不得用來判 v24」，不是連結的閘門。

§34.4：因執行而修 0、因審核而修 0（第 1、2 項改的是判準的文字，不是已 commit 的檢查；E1 的紅案第一次沒紅是測試在 commit 前的錯，記在證據 README）。

## 15. 切換與 generation 77 的凍結時機（2026-10-28，只追加；任何 v24 的瀏覽器執行之前）

- **切換已做**（證據 `findings/evidence/link-batch-v24/cutover/README.md`）：頁面加上 `typedInsert` 的要求，再用 `build_cutover_page.py --profile e2-editor-v24 --write --expect-sha256 b15a6d8e…` 改 worker URL 與 wasm 釘選；頁面 `c25b11c4…` → `b15a6d8e…`，`dist/` 已複製。切換後的 V0′（兩個宣告的殼層檔一起換回）成立。
- **generation 77 晚一點凍，取代 §8 第 5 步的「凍 generation 77」**：裁決 1 §3 的順序是「紅案 → 兩個瀏覽器的準備 → 凍綁定 → 新目錄」，而這棵樹的教訓是殼層改完才凍（同一天凍 v28／v29／v30 那次）。§8 第 5 步把凍結排在 §6.3 之前，兩者衝突，以裁決為準：77 在 §6.3 的 (vi)、(vii)、J-red、M2、T5、(i)、T4 都過、而且沒有待做的殼層改動之後才凍，在任何 §6.4 的計數之前。
- 因此 §6 通則「與 generation 77 不符就作廢」在 §6.3 讀成「與報告記下的頁面雜湊＋候選殼層摘要不符就作廢」（今天的候選摘要 `56ce44c7…`）；凍出來的 77 若摘要不同，§6.3 的準備在新位元組上重做。§6.4 照原文。
- 凍 77 時排除清單要**明列** 7 項（v76 的 6 項＋`sdk/v24-feature-worker.js`）：工具的已凍結清單沒有 v76，不明列就從 v75 繼承 3 項。

## 16. fable 裁決 1（v24 計數前）帶來的更正（2026-10-28，只追加；T4 run 01 之後、run 02 之前）

依據：`findings/evidence/link-batch-v24/pre-count/rulings/RULING-1.md`（簡報 `BRIEF-1.md`；擁有者選 A 交 fable）。原文不動，以本節為準。

1. **§5.4 更正**：v24 的儀器一律是新檔，**例外是 `findings/evidence/link-batch-v24/pre-count/bound-tool-edits.json` 宣告的修改**。目前授權的封閉清單只有兩項：**E1**（`tools/run_e2_c_product_path.py` 的 Shift+Enter 判準與其酬載，別的不動）、**E2**（`tools/build_e2_c_shell_bundle.py` 的 `MANIFEST` 指到 v77、`FROZEN_MANIFESTS` 加 v76，與寫出 v77 同一個 commit）。每一項都要在修改之前先進清單、附逼出它的事實與證人。`build_v23_native_s5_owner.py`、`build_v23_native_s5_type_owner.py` 永遠不改（AGENTS.md）。之後再有被綁檔案要改，比照辦理，不必再裁決。
2. **§6.1 V0 列 → V0″**：V0′（§14.2）推廣到工具。宣告的殼層檔與宣告的工具檔都換回凍結的位元組（工具取自 `frozen-sources.tar.gz` 的 `instrument/<path>`）後，`counted-r1-s5-01/read-completion.py` exit 0 而且階段結論等於 `completion-read-01.json`；只換殼層時要以「恰好一個宣告的工具路徑」為酬載失敗；原生 run-03 重讀等於 `reader-03.json`；E1-C `intact: true`；換回之後每個宣告檔的雜湊等於清單的 `liveSha256` 且**不等於**凍結值。細節照裁決 §3.4（七步）與紅案 V-1…V-3（§3.5）。**每次宣告的修改之後跑一次，而且每一次 §6.4 計數與 K 之前各跑一次。**預設照 V0：沒跑就停手，任何 §6.4 計數都不得開始。
3. **§6.3 T4 列**：規則 2 拆成 2a／2b 加固定的易變欄位清單，見 `t4/README.md` 的 Correction 1；規則是在 run 01 之後改的，所以 **T4 的判決看 run 02**，並與 run 01 逐檢查比對（除了 Chrome 的 Enter 檢查之外都要相同）。
4. **§10 新增 D-typed-rsid-spans**（D 是「宣告過的差異」，不是限制）：v24 打的字存檔時帶 `officeooo:rsid` 的字元 span，與原生鍵盤打字相同；v23 的 paste 路線不寫。證據：`t4/shift-enter-diagnostic-02/` 與一支讀 `m1-run-01/saves/` 的小工具（每個 shape×text×回合比較 key 與 uno-insert-text 兩臂的 rsid 樣式數與 span 數）。**那支工具沒寫出來之前，「與桌面 Writer 打字相同」只是推論，不得寫進發佈說明。**
5. **§13 新增紅案**：R-a…R-f（T4 讀取工具，裁決 §1.4）、Enter 判準的正負對照（§2.4）、V-1…V-3（V0″，§3.5）。
6. **generation 77**：照裁決 §4 的順序——更正 → 讀取工具紅案 → E1＋對照＋V0″ run 1 → T4 run 02 → 凍 77（E2＋v77 寫出且摘要等於 `56ce44c7…`＋`make test-e2-c-reachability` 綠＋V0″ run 2）→ §6.4。

§34.4（本節）：因執行而修 2（`read_v24_t4.py` 的規則 2、`run_e2_c_product_path.py` 的 Enter 判準）、因審核而修 0。

## 17. fable 裁決 1 追加 1：被綁的共用工具一律不改（2026-10-28，只追加；T4 run 02 之前）

依據：`RULING-1.md` 的 Addendum 1。起因：E1 落地後 V0″ run 01 第 1 步紅——`s5-native/settled-reference-reader-05.json` 逐檔綁 1,772 個輸入（`run_e2_c_product_path.py`、`build_e2_c_shell_bundle.py` 都在內），而 v24 自己的 S5／R1 計畫也會經 v23 的 `s5()` 驗它；E1 生效時 v24 連計畫都建不出來。E1 已還原（`aaea5336`）。

1. **取代 §16 第 1、2 項**：**活的綁定集合**（`counted-r1-s5-01` 的 30 支 ∪ reader-05 綁在 `wasm_sdk_probe/` 底下的 30 個 ∪ 原生 run-03 identity 的 12 個）裡的檔案，只要還有計畫匯入 v23 的 `s5()`，就**一律不改**。`bound-tool-edits.json` 關閉，E1 一筆留作紀錄。真有產品理由非改不可時，走「重發 settled 證書」（選項 B），要新裁決。V0″ 保留，以空的宣告清單當每次 §6.4 計數與 K 的前置檢查，必須 `V0PP_HOLDS`。
2. **取代 §16 第 3 項的 run 02 期望**：見 `t4/README.md` Correction 2——Enter 檢查在 Chrome 照凍結判準 FAIL（與 run 01 相同）、Firefox NE；46 支結果全部與 run 01 相同；另由新工具 `tools/check_v24_shift_enter.py` 以讀穿 span 的判準重播 3/3。
3. **§10 新增 I-enter-raw-substring**（儀器的具名限制，不是產品限制）：v24 起打的字帶 rsid span，凍結 runner 的 Enter 檢查 Shift 臂用原始 XML 子字串比對，在 Chrome 必定 FAIL；斷行其實在。每一份 v24 的產品路徑報告都會帶這個 FAIL。
4. **generation 77 用 `--manifest` 凍，工具一個位元組都不改**：`python3 tools/build_e2_c_shell_bundle.py --manifest e2/editor-shell-v2-bundle-v77.json --write --frozen-date …` 加明列的 7 項 `--exclude`；摘要必須等於 `56ce44c7…`。`Makefile:4843` 改成傳 `--manifest …v77.json`（Makefile 不在任何綁定裡）。**交接 10-28d 與工具自己的提示「改 MANIFEST、把 v76 加進 FROZEN_MANIFESTS」在這棵樹作廢**：工具的預設刻意留在 v76。`v24_feature_selection_cases.identity()` 在凍結後釘 v77 檔的雜湊並以紅案驗證。
5. **A4-v24**：新包裝器 `tools/run_v24_four_arms.py` 在匯入 runner 前於行程內把 `build_e2_c_shell_bundle.MANIFEST` 換成 v77 並記錄；v24 的四臂判讀包裝器要求身分指名凍結的 77。不帶包裝器直接跑 runner，在 v24 上四臂一律 NE（綁 v76）。
6. **順序**：本節 → `check_v24_shift_enter.py`＋紅案＋3 次重播 → T4 run 02 → 凍 77（＋Makefile、identity 釘選、V0″）→ A4 包裝器 → §6.4。

§34.4（取代 §16 的數字）：因執行而修 1（`read_v24_t4.py` 的規則 2）、因審核而修 0；E1 落地又還原，runner 與 run 01 逐位元組相同。

## 18. §6.4 計數工具的落地方式（2026-10-28，只追加；任何計數之前）

接續交接 `HANDOFF-2026-10-28e-v24-pre-count-done-77-frozen.md`。generation 77 已凍結；本節沒有重開 §6.3 或搬移既有計數。

1. **保留前置量測的讀取身分**：既有 v24 preparation runner、reader、cases 也不改。新的 `v24_counted_selection_cases.py` 呼叫既有 `config()`，只換成由新 runner／reader／launcher／完成讀取器的靜態 import 圖生成的 instrument closure。避免新工具讓 M2 的 live-config 比較失效。舊有 40 個活的綁定成員不改。
2. **判讀沿用原碼**：R1、S1–S4 及 aggregate 用 v23 的 code object，在新的 namespace 只接 v24 的 Evidence／readiness／S5（含 T2）；S5 的 T1 比較器與 T2 沿用既有 v24 reader。紅案先於任何計數：v23 頁面不可過、缺 route／proof 必須 FAIL、空母體／少一格／重複頁面不可 PASS、preparation 報告不可取得 counted 身分。
3. **封存與執行**：新 cohort 先封存 config 與實際 instrument／served sources，列出每一 stage 的工具生成 caseIds、兩瀏覽器與命令。順序 S5（588 × 2＝1,176）、R1（72 × 2＝144）、selection（117 × 2＝234）。每 stage 前 V0″ 必須 `V0PP_HOLDS`；launcher 核對封存、來源與前置證據；第一個非 PASS／漂移就停，既有 status 或輸出一律拒絕重跑。完成讀取器重讀原始產物，不採信 runner 的結論。尚未完整跑完的 stage 預設 NE。
4. **A4 包裝器**：依 §17 與裁決追加 1，匯入 runner 前把 bundle 模組的 MANIFEST 綁到 77，輸出記錄原預設、實用 manifest 與 file hash。新 A4 reader 在原本的完整判讀之外，逐實例要求 v24 profile、ABI 6、v24 artifacts、凍結 77。`--preflight-only` 不開瀏覽器，供無 override／不存在 v78 的拒絕紅案；舊 run-01 的 v76 產物必須 NE。仍需新的兩瀏覽器四臂實跑才可宣稱 A4。
5. **執行時段**：工具與紅案做好後才詢問擁有者 A（脫離 session 執行，建議）或 B（擁有者自行執行）。本節不授權直接開始數小時的計數、不取得 DDEV 時段；K、宿主與 BINDING 仍依 §6.4。

截止與歸零語意維持 §6.4。工具的紅案與離線重讀不給任何 counted cell；若正式執行一直沒做，S5／R1／S14／A4 全數仍為未成立。

### 18.1 R1 marker 的傳輸身分（同日，只追加；計數前讀原始碼逼出）

§18 第 2 項「只接 Evidence／readiness／S5」補正：`judge_v23_feature_selection.r1_marker_witness` 也用完整 payload 相等檢查 `#`，而 R1 的 marker 同 readiness 一樣走真實打字，v24 會多 `route: "uno-insert-text"`。新 reader 的 marker witness 只在這一行加入 route；其餘文字逐行相同，`r1_arm` 用原 code object 接到這個新 witness。紅案必須使正確 v24 wire shape 通過、缺 route 的 marker 不可 PASS；合成改寫的歷史頁面只測儀器，不給 v24 計數。若不補正，R1 預設 NE，不能沿用 v23 144/144。

### 18.2 前置報告的身分界限（同日，只追加）

§18 第 1 項「避免 M2 的 live-config 比較失效」收窄為「避免再新增工具位元組的差異」：M2 原報告寫 `candidate-77-not-frozen`，凍結後 live config 已寫 77；因此原 main 的完整 live-config 比較已有差異。裁決追加 1 §4 明定相同殼層摘要下 §6.3 仍成立。原 config 的逐格重讀與當時 reader 結論可保留；不可宣稱現在完整 live-config 相等，也不可把這份準備報告搬成 counted。

## 19. S5 已完成、R1 零格負載拒絕後的剩餘計數（2026-10-29，只追加；新執行之前）

已觀察：`counted-selection-01` 的 S5 1,176/1,176 PASS，runner 28,039.1 秒；隨後 R1 啟動前取樣有外部 Zen 程序使用單核 105.8%（門檻 50%），R1 零格拒絕，selection 未執行。`completion-read-01.json` 逐格重讀與 aggregate 相同：S5 完整 PASS、R1 NE，整批 NE。這是已凍結的停止，不修改其 status、宣告、工具或門檻。

1. **依母體保留結果**：§6.4 與截止原本逐母體定義。S5 已成立，不因下一母體開始前的負載拒絕歸零；另開新目錄只執行 R1（144）與 selection（234），不重跑 S5、不把舊目錄改成可續跑。若剩餘部分沒做，R1／S14 仍 NE，整體也 NE。
2. **所有原檔保持凍結**：新 remaining entry points 只替換 cohort verifier。原 verifier 的 code object 在新 namespace 把 `KINDS` 改為 `(r1, selection)`，`stage_spec` 改指新 collector／judge entry point；collector、逐格 judge、launcher 與完成讀取的原 code object 不改。collector 和 judge 新入口在匯入／呼叫原工具前安裝這個具名替換。原 config 與 38 個 instrumentSources 逐位元組相同；新增的 orchestration 靜態 import closure 另封存並逐檔比對，不冒稱舊 config 已包含新入口。
3. **來源與合併判讀**：新宣告釘住原 cohort、status、S5 report／judge、完整 completion read 的 hash；來源 S5 必須完整 1,176 PASS。新完成讀取器重新讀原 S5 原始產物，再用原完成讀取的 code object（只替換 verifier）讀新兩階段；兩者全部成立才給 `V24_SELECTION_COUNTS_HOLD`。只餵一份自述 PASS、少一格或缺 status 均不得成立。
4. **先讓新介面紅**：來源 S5 receipt 改錯／移除、remaining 少案例或瀏覽器、orchestration 來源或封存改變、空 status、重複啟動都必須拒絕或 NE；未改的凍結輸入必須可 dry-run，verifier／launcher／collector／judge／完成讀取的沿用關係需可檢查。紅案在新計數前完成。
5. **授權與負載**：擁有者本日明確要求離座後由代理代跑必要建置、測量及後續工作，取代前一日 B 的自行執行安排。新兩階段及 A4 由代理執行，仍逐階段 V0″、CPU 門檻不變、首個非 PASS 停止、新目錄不重試。若再次負載拒絕，保留零格結果並另作判讀；不關閉擁有者的瀏覽器、不偷偷等待到紅項消失而重用原目錄。

原始 S5 以逐格 gzip 無損封存，receipt 仍以解壓後位元組計；這只改儲存，不改任何既有判準或結果。

## 20. 功能計數成立，K 尚未執行（2026-10-29，只追加）

代理依擁有者離座授權執行 `remaining-counted-01`，02:01:12 啟動、06:06:18 結束，job 結論 `SELECTION_AND_A4_PASS`。全部來源與原始產物可由既有讀取器重讀，不由本段敘述代替判讀。

- **S5-v24**：原 `counted-selection-01` 1,176/1,176 PASS，無重跑；原始產物重讀與當時 inspection／aggregate 相同。
- **R1-v24**：新 `remaining-counted-01` 144/144 PASS，兩瀏覽器、literal 與 layout-relative 各 36 格／瀏覽器、六格 wrong-old-click 對照全過。
- **S14-v24**：新 234/234 PASS；S1 168、S2 216、S3 20、S4 18 全過（membership 重疊，不相加當母體）。合併完成讀取 `V24_SELECTION_COUNTS_HOLD`，共 1,554 個實測格。
- **A4-v24**：`four-arms-counted-01`，四臂 × 三格 × 兩瀏覽器＝24/24 PASS，零 aggregate problems；前後儀器雜湊全同，逐次 V0″ 全過。代理執行原始產物 reader 的新檔重讀，結果與初次 aggregate 逐位元組相同。
- **界限不撤回**：完整 product-path runner 仍含既有／宣告的 FAIL、NE；兩次 `runnerExit: 1` 與 A4 wrapper 的成功分開留存。不宣稱全部 46 項 PASS。I-enter-raw-substring 與 S5 對 no-op extension 後 delete 單位的既有限制維持。
- **K**：宿主新封包、BINDING、完整計數鏈仍待執行；功能計數不代替 K，也不前移名義出貨版本。本次測量已結束，目前無佔用 DDEV 時段。

## 21. 宿主 0.2.39 與 K 前置（2026-10-29，只追加；封包與新診斷之前）

擁有者指示執行下一步。實際宿主為乾淨 `0.2.38 / fff18e48`，包含後加的 Calc 深色主題修法，不再以 0.2.37 當前版。新候選 0.2.39 從這個實際 parent 建隔離 worktree，只更新宿主版本並封裝目前已驗證的 Writer v24／殼層 77；viewer v3、Calc v2 與深色主題 HTML 保留。依現有 package 工具從三頁實際 import／worker manifest 推導母體，驗 raw／gzip／zstd、封存精確 engine、新舊差異、來源身分與回退封包。K0/Z0/H5-1 的既有離線讀取與紅案在安裝前完成；若未完成，不安裝候選。

讀原碼發現舊 K 的前提衝突：`chain-0.2.26.sh` 的 product-path 對照與 merge red 都把目前頁面 repoint 到 v8；`repointed_page()` 只換 worker URL／wasm pin，保留 v24 的 `typedInsert` 必要宣告檢查，而 v8 manifest 不帶該葉。這是既有紅案 (vii) 的把關，不能藉「更新 pins」移除。先用獨立、本機 Chrome 的 v24 正向對照與實際 repointed-v8 觀察確認：v24 可開啟並 typed insert；v8 預期 PAGE_BUILD_MISMATCH／無 insertText。這份診斷不計入 K，亦不修改產品或任一已凍結工具。若符合預期，舊鏈不能直接重綁執行；對照／red 的新計數處方須先定案，不能造假的 manifest 或放鬆產品把關來維持舊前提。

本次只先做離線封包與上述有限診斷。實際 `litecore` 暫停、另有 fgp-nc／nc-bridge 執行中，未取得共用 DDEV 時段；J-a P5 的具名窗口／期間不開站約定仍不得由代理代填。原始文件／鎖列保持不變，安裝前另讀現況與完整明細。完成可檢視候選及 K 的實際差異／前提紀錄後，再協調時段；不重新要求已完成的 F3-hand／H7／V3-SEE。

## 22. 宿主 0.2.39 安裝（2026-10-29，只追加；安裝之後寫）

擁有者在這一輪回答了時段問題：「現在開始，我不開」litecore.ddev.site，並在同一則訊息授權關掉其他 DDEV 專案。時段依實際回覆記在 `findings/evidence/host-0.2.39/slot.json`（09:21:11–10:06:11 +0800），不從交接推斷。fgp-nc／nc-bridge 先停，litecore 由 paused 啟動；結束後兩者照原樣啟回，litecore 留在 running（DDEV 1.25.3 沒有 pause，進場時的 paused 是重開機造成的）。

結果：guarded installer 預檢與安裝都通過（CANDIDATE_INSTALLED）。受保護文件與完整鎖列前後相同（鎖列為零筆），三條未登入路由都是 401。既有 `run_calc_editor_host.py` 以兩個瀏覽器做擁有檔的 Files 實際流程，**52/52 PASS**，清理完整。安裝後讀取 `capture-after.py` 成立，紅案兩個都會轉紅；其中一個第一次沒轉紅，是讀取工具漏算 buildId 欄位，已在登錄前修好（因執行而修 1，因審核而修 0）。

限制照寫：Writer 臂走頁面的插入欄位（`commitText`），不是對 sink 送按鍵；v24 的真實鍵入由 mirror 上的 S5／R1／A4 成立，沒有在這台宿主重量。0.2.39 現在是**日常使用的未計數候選**，取代 0.2.38；名義出貨版仍是 **0.2.26**。K 沒跑，控制協定交由 fable 裁決（擁有者選 A），未採用前不開計數。
