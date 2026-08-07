# 017 — selection reset後`getTextSelection()`回unsupported UTF-16 flavor，SDK無法表示空selection

| | |
|---|---|
| **狀態** | **已修（SDK側）／瀏覽器實測通過；不再阻斷E1** |
| **Bugzilla** | — |
| **發現日** | 2026-08-05 |
| **嚴重度** | 阻斷 |
| **可重現** | 原始故障1/1 headed實測；修正後實測通過（逐字log 1輪，跨瀏覽器為操作員回報） |
| **是否上游** | 未確認；目前先分類為專案SDK與LibreOfficeKit空selection邊界不相容 |

## 給接手同事的摘要

E1 Finding 016人工頁需要在delete前證明搜尋選取已收成collapsed caret。r5用既有closed diagnostic
`selection-reset-unstable`完成reset後，第一個公開readback `DocumentHandle.getSelection()`沒有回空字串，而是：

```text
LOK_ERROR: Flavor text/plain;charset=utf-16 is not supported
```

Project engine實際要求的是`text/plain;charset=utf-8`，artifact也與source一致；錯誤中的UTF-16不是JS或舊artifact
偷偷改了MIME type，而是LibreOfficeKit `getFromTransferable()`把UTF-8 canonicalize成內部UTF-16 flavor後，該
selection transferable不支援此flavor。當時的`handleGetSelection()`把任何null都升格為`LOK_ERROR`，因此無法把
「沒有文字selection」表達成成功的`text: ""`。

本輪不再用更多人工caret技巧繞過；人工頁r5在delete dispatch前停止，沒有mutation。

**2026-08-05修訂**：修正已實作。`handleGetSelection()`改用`getSelectionTypeAndText()`，`none`／`text`／`complex`
三態明確可分，空selection成為成功結果，**不需要修改LibreOffice core**。另外因為core會把「真的沒選取」與
「flavor意外缺失」都回報成`NONE`（無法在API層區分，詳見「已知限制」），收合caret必須再用callback路徑
（`selection.observed`＋`selection.collapsed`）交叉驗證後才可dispatch mutation。編譯、SDK單元測試與瀏覽器
實測皆已通過，**017不再阻斷**。本段完成當時E1仍停在Finding 016；其後016已由verified-selection barrier解除，
E1-A最終判定為`PARTIAL_GO_TO_E1_B`。

## 最小重現

1. 使用`e1-editor-discovery`隔離artifact開啟`plain-grapheme.odt`。
2. 以公開search選取`0123456789`。
3. 以closed `selection-reset-unstable`及search result rectangle末端座標嘗試收成caret。
4. 立刻呼叫公開`DocumentHandle.getSelection()`，尚未呼叫Delete。

**預期**：若沒有文字selection，readback成功回`text: ""`；若仍有selection，回完整selection text。兩者都不應是
一般`LOK_ERROR`。

**實際**：`get-selection`回`LOK_ERROR`，訊息為
`Flavor text/plain;charset=utf-16 is not supported`，所以r5無法執行第二個typed-state readback，也沒有dispatch
Delete。

## Artifact與證據

- 原始故障操作員log：`findings/evidence/017/operator-2026-08-05.log`
- 修正後驗證log：`findings/evidence/017/operator-2026-08-05-verify.log`
- 修正後machine metadata：`findings/evidence/017/artifact-verify.json`
- 程式碼路徑摘要：`findings/evidence/017/source-trace.txt`
- Machine metadata：`findings/evidence/017/artifact.json`
- Core：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- Profile：`e1-editor-discovery`；SDK `0.6.0-r6-worker+e1-editor-discovery`

重現本故障的artifact（已被修正後版本取代，hash對照見「已完成的驗證」）：

- Loader：`a733b8f89eebaa53685056c447cf76151f5a86f455ff1d9dd0c725ff20f8e87d`
- WASM：`1c8b79fd5c9968dd362a43e4e1e032fe07806f72c34c1f5b041c8af00d6c1e78`
- Worker：`09e34824ba938c76ebd53e908be1885e3f3e6e020d58effcaec7f1c3983ec3ed`
- SDK manifest：`da78c6937d746282ffcf7e57789546df7cd0ee8930d2a92ad572504545e62ca8`

## 分析

### 已觀察

- `handleGetSelection()`傳給LOK的是`text/plain;charset=utf-8`，不是UTF-16。
- Core `getFromTransferable()`收到UTF-8 plain text時會改查`text/plain;charset=utf-16`的`OUString` flavor；flavor不
  支援時，會產生本輪逐字相同的錯誤訊息並回false。
- `doc_getTextSelection()`在`getFromTransferable()`失敗時回nullptr（`init.cxx:5941`）；project engine再把nullptr
  映射成SDK `LOK_ERROR`。
- 同一project engine的`handleEditorGetState()`對同樣的null selection pointer採另一種行為：序列化成
  `selectionText:""`，沒有拋錯。兩個readback contract不一致。
- **`doc_getSelectionTypeAndText()`走的是同一條`getFromTransferable()`路徑**（`init.cxx:6019`，同樣送
  `text/plain;charset=utf-8`），一樣會踩到缺失的flavor。差別只在錯誤對應：`!bSuccess`時回
  `LOK_SELTYPE_NONE`而非nullptr。因此換用此API即可解除阻斷，且**不需要修改LibreOffice core**。
- `getFromTransferable()`在`init.cxx:5873`設定last-exception訊息後，`doc_getSelectionTypeAndText()`在回傳
  `NONE`前並未清除它。也就是說函式「成功回NONE」時，`getError()`仍是那句`Flavor ... is not supported`。
- `LOK_CALLBACK_TEXT_SELECTION`的空payload會被`parseEditorSelectionRectangles()`正確處理成「清空矩形列表並回
  true」（`probe_engine.cpp:269`），而非解析錯誤；`selection-reset-unstable`本來就以此callback作完成barrier
  （`probe_engine.cpp:1578`）。**reset完成的那一刻，空的selectionRectangles已經是core主動發出的「沒有選取」
  聲明**，且與transferable／flavor路徑完全獨立。
- r5呼叫順序是selection reset → public getSelection → typed getState → delete；錯誤發生於第二步，所以沒有呼叫
  getState或delete。
- Source、served page與E1 artifact hash均已核對；不是瀏覽器仍載入舊r4 JS，也不是manifest／WASM不匹配。

### 推論

- selection reset很可能已把文字selection收掉，因而新的transferable沒有plain-text flavor；但本輪尚未讀到其後的
  typed state，所以不能把「reset確定成功」寫成已觀察。
- 主要產品缺口在readback語意：empty／none selection是正常狀態，不能與真正的LOK failure共用同一個
  `LOK_ERROR`結果。
- 這不等於LibreOffice core一定有bug；project SDK若先讀selection type並把`LOK_SELTYPE_NONE`正規化為空selection，
  已足以建立清楚契約。此推論在2026-08-05修訂中經原始碼核對成立。

### 已知限制（原「待驗證2」，經核對後改寫）

**原本要求「區分真正沒有selection與transferable存在但文字flavor意外缺失」，在LibreOfficeKit現行C API層無法
達成。** core自己已先做了這個合併：`init.cxx:6019-6026`把三種狀態

1. `pDoc->getSelection()`回null（`init.cxx:6009`）；
2. flavor查不到導致`getFromTransferable()`失敗（`init.cxx:6019`）；
3. 讀取成功但字串為空（`init.cxx:6025`）

全部塌成同一個`LOK_SELTYPE_NONE`，資訊在進入SDK之前就已遺失。已排除的替代路徑：

- `doc_getSelectionType()`：同樣的合併（`init.cxx:5978-5985`）。
- 直接以`text/plain;charset=utf-16`呼叫`getTextSelection()`：命中同一flavor，結果相同。
- `doc_getClipboard()`：雖以`getTransferDataFlavors()`列舉flavor，但讀的是剪貼簿
  （`LOKClipboardFactory::getClipboardForCurView()`，`init.cxx:6073`）而非selection，且需先執行copy造成mutation。

**替代作法（已採用）**：不要求單一API自我區分，改以兩條互相獨立的路徑交叉驗證是否已收成caret——

- transferable路徑回報`selectionType == "none"`；
- callback路徑回報`selection.observed == true`且`selection.collapsed == true`。

兩者一致才可視為selection確實已清空；不一致即為「flavor意外缺失但selection仍在」，應拒絕dispatch mutation。
若要讓core自身區分這三種狀態，屬上游改動，非本輪範圍。

### 待驗證

1. ~~在`handleGetSelection()`改用有版本檢查的`getSelectionTypeAndText()`~~ — 已實作，見下節。
2. ~~區分真正沒有selection與flavor意外缺失~~ — LOK API層不可達，改以callback交叉驗證；見上方「已知限制」。
3. 對search selection、selection reset、一般click、collapsed caret與複雜selection各建測試。
   SDK層5項已完成（`wasm_sdk_probe/sdk/tests/document-sdk.test.mjs`）；**瀏覽器層只跑了collapsed caret一項**，
   `delete-forward`、`complex` selection與段落邊界仍未跑。
4. ~~用同一新artifact在Chrome／Firefox驗證~~ — 已重建並實測；不沿用r5舊WASM。
5. 若readback修好，再回到Finding 016測Delete／Backspace；mutation不得自動retry。

## 修正範圍（已實作，已重建並實測通過）

- `wasm_sdk_probe/src/probe_engine.cpp`
  - 新增共用`readSelection()`與`selectionTypeName()`，以有版本檢查（`LIBREOFFICEKIT_DOCUMENT_HAS`）的
    `getSelectionTypeAndText()`為主、`getSelectionType()`為fallback。
  - `handleGetSelection()`改為selection type aware：`none`成功回`text:""`；`text`缺文字才是typed failure；
    `complex`明確回報，不假裝空字串。**回NONE時不再呼叫`kitError()`**，避免讀到陳舊的flavor訊息。
  - `handleEditorGetState()`改用同一`readSelection()`，兩個readback contract語意對齊；額外輸出
    `selectionType`與`selectionTextMissing`。
  - `EditorState`新增`selectionObserved`，`appendEditorState()`輸出`selection.observed`。空的
    selectionRectangles在首個`LOK_CALLBACK_TEXT_SELECTION`到達前只代表「未知」而非「已收合」；此旗標讓交叉
    驗證不會把初始狀態誤判成caret。
- `wasm_sdk_probe/sdk/sdk-worker.js`：轉發`selectionType`與`selectionTextMissing`。欄位缺失時預設
  **`"unknown"`而非`"none"`**——舊engine不送此欄位，若預設成`none`會讓caret前置條件在selection仍存在時通過，
  正是最危險的方向。
- `wasm_sdk_probe/web/e1-manual-delete-app.js`：前置條件改用新契約。原判準`selection.text === ""`不足
  （`complex` selection的text同樣是空字串），改為`selectionType === "none"`；並加入`selection.observed`，
  因為在首個callback到達前`collapsed`只代表「未知」。三項全部成立才允許dispatch delete。
- `wasm_sdk_probe/sdk/document-sdk.d.ts`：新增`SelectionType`，`SelectionResult`加上`selectionType`。
- `wasm_sdk_probe/sdk/tests/document-sdk.test.mjs`：新增4項selection契約測試。
- 不需要raw UNO、任意`.uno:*`、unoembind、未承諾callback欄位或LibreOffice core修改。

## 已完成的驗證

- Emscripten編譯（`-Oz -pthread -fwasm-exceptions`，core `671c848b`標頭）：
  - 定義`OXSDK_EDITOR_DISCOVERY`：通過。
  - 未定義`OXSDK_EDITOR_DISCOVERY`：通過（共用helper在ifdef之外，兩種組態都須成立）。
- SDK單元測試：16項全數通過（既有11項未回歸，新增5項）。
- `make test-e1-a-static`全套通過：Python 6項、Node 20項、全部`node --check`、ABI標頭`-fsyntax-only`、
  Python `py_compile`。
- **E1 artifact已重建**（2026-08-05，耗時2m03s）。重建前hash與本文件原記載四項逐一相符，確認基線正是產生本錯誤
  的r5 artifact；重建後：

  | 檔案 | 重建前（r5） | 重建後 |
  |---|---|---|
  | `probe.js` | `a733b8f8…f20f8e87d` | `53919e64…85548c3213` |
  | `probe.wasm` | `1c8b79fd…f00d6c1e78` | `d341b5ef…d8eca2cd83` |
  | `sdk-worker.js` | `09e34824…c1f3983ec3ed` | `4c2a3ea7…6323e5dd452` |
  | `sdk-manifest.json` | `da78c693…545e62ca8` | `d3c79bbc…6e86676cdc` |

- 新程式碼確認存在於WASM二進位中（非僅hash改變）：typed failure訊息字串、`"observed":`狀態欄位、
  `selectionTextMissing`均可在`probe.wasm`中找到。
- Manifest自記`productionArtifactReplaced: false`；`writer-review`、`writer-review-r6`、`writer-reader`、
  `full-qa`四個生產profile的dist檔案時間戳均早於本輪修改，未被取代。

### 瀏覽器實測（2026-08-05）

**已觀察**（操作員headed實測，原始log見`evidence/017/operator-2026-08-05-verify.log`）：

```text
"selectionType":"none","selectionText":"","stateObserved":true,"stateCollapsed":true
"selection":{"observed":true,"collapsed":true,...,"rectangles":[]}
"verification":{"expectedFound":true,"originalStillFound":false,"pass":true}
```

r5命中`LOK_ERROR`的那一步現在成功回傳空selection，且callback路徑（`observed:true`、`collapsed:true`、
`rectangles:[]`）獨立同意。兩條路徑一致後前置條件放行，Backspace精確刪除一個字元（`revision 0→1`）。

- 環境：同Finding 016機器，Chrome `150.0.7871.128`、Firefox `153.0.1`（操作員提供）。
- 證據等級：**只有一輪逐字log**，且該段excerpt未標示由哪個瀏覽器產生；「Chrome與Firefox皆通過」為操作員回報，
  非逐一保存的輸出。跨瀏覽器主張的強度以此為限。
- 已跑情境：`delete-backward`於anchor結尾、fixture `plain-grapheme`。
- **未跑**：`delete-forward`、`complex` selection分支、段落邊界案例。

**同一份log再次證實Finding 016未解**：`callbackSequenceBefore:7`／`callbackSequenceAfter:7`、`changed:null`、
`documentChangeSequence:0`。文件確實改了，但沒有任何callback sequence前進，completion是靠事後讀文件字串建立，
不是可歸屬的callback。017修好的是「刪除前能否安全確認caret」，不是「刪除後能否知道它完成」。

### 順帶記錄（與本finding無因果關係）

`src/probe_engine.cpp:21`無條件include `boost/property_tree`，但Makefile的基礎`CPPFLAGS`未含boost include路徑，
只有`E1_CPPFLAGS`有。以基礎`CPPFLAGS`編譯非E1 profile會失敗於找不到`json_parser.hpp`。此為既有狀況，不是本輪
修改造成，也未在本輪處理。

## 判定

- Finding 016人工r1～r5到此停止，不再消耗操作員時間嘗試其他caret workaround。
- **Finding 017判定為`REMEDIATION_VERIFIED`，不再阻斷。** 修正已完成artifact重建、編譯、16項SDK單元測試、
  E1靜態回歸與headed瀏覽器驗證；空selection readback及獨立callback交叉驗證均成立。
- 這只證明selection readback契約已修復，不等於Delete／Backspace的產品completion契約成立。此判定當時E1仍因
  [Finding 016](./016-lok-forward-delete-completion-gap.md)維持`STOP_OR_RESCOPE`；其後016已另行修復並完成跨瀏覽器
  coverage，不能倒推成本finding單獨證明delete contract。

## 時間軸

- 2026-08-05：r5在selection reset後命中public getSelection空selection／flavor邊界，建立本finding，人工流程停止。
- 2026-08-05：核對LibreOffice原始碼確認三件事——`getSelectionTypeAndText()`走同一`getFromTransferable()`路徑但
  把失敗折成`LOK_SELTYPE_NONE`（故換API即可解阻斷，不需改core）；`init.cxx:6019-6026`已把三種狀態合併，原
  「待驗證2」在API層不可達，改寫為已知限制並改採callback交叉驗證；`getFromTransferable()`留下的last-exception
  訊息在回傳NONE時未清除，實作必須以回傳值而非`getError()`判斷成敗。
- 2026-08-05：實作selection type aware readback、對齊兩個readback contract、新增`selection.observed`旗標與
  SDK契約測試；兩種編譯組態與單元測試通過。
- 2026-08-05：操作員headed實測通過（Chrome 150.0.7871.128／Firefox 153.0.1，同機器）。空selection readback成功，
  callback交叉驗證一致，Backspace精確刪一字元。017不再阻斷；同一份log再次證實016的completion缺口仍在。
- 2026-08-05：重建E1 artifact。重建前hash與本文件原記載相符（基線確認）；重建後四項hash全部更新，並在WASM
  二進位中確認新程式碼存在。同時發現並修正兩處自身缺陷——worker欄位缺失時的預設值原為`none`（fail-open，
  改為`unknown`），人工頁前置條件原以`text === ""`判斷（對`complex` selection誤判，改為判斷`selectionType`
  並加入`observed`）。`make test-e1-a-static`全套通過。**等待操作員在Chrome／Firefox實測**。
