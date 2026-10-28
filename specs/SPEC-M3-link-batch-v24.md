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
