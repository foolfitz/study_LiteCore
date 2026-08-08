# SPEC E1-A：Editing interaction discovery

> **日期**：2026-08-04  
> **狀態**：A0～A6完成；`PARTIAL_GO_TO_E1_B`  
> **上層規格**：[SPEC E1-000](./SPEC-E1-000-overview.md)  
> **前置閘門**：[R8 `PARTIAL_GO_LOCAL_DELIVERY`](./SPEC-R8-000-overview.md)

## 1. 目標

在不先承諾新ABI的前提下，找出ODT-first基本編輯器可安全建立的最小closed surface。A只做邊界discovery、
行為矩陣與checkpoint判定；不交付完整編輯器UI。

主要輸出是：

- 文件化LOK輸入／callback到typed editor state的可行映射；
- 可凍結的closed operation、completion barrier、revision與error taxonomy；
- Chrome／Firefox與fixture差異；
- B階段可實作清單、需縮小能力及停止finding。

## 2. 進場API inventory

| 能力 | 現有公開SDK | 已觀察限制 |
|---|---|---|
| caret placement | `click(xTwips,yTwips)` | 只回revision；無caret rectangle／visible state |
| text input | `insertText(text)` | composition commit可用；不是keyboard contract |
| selection | `search()`＋`getSelection()` | search有rectangles，任意selection只有text |
| replace | `replaceSelection(non-empty)` | 空字串被拒絕，不能表示delete |
| history | `undo()` | 無Redo、無history availability state |
| keyboard | 無 | probe內部legacy `key()`不得直接升格或暴露任意key code |
| mouse drag | 無 | LOK有`setTextSelection()`，但位於unstable API區段 |
| editor state | 無 | raw LOK callback不向app暴露，只有粗粒度invalidated event |
| formatting | comments／tracked changes固定operation | 無bold／italic／paragraph／list產品operation |

## 3. Discovery checkpoint順序

### A0：Baseline與來源分類

- 固定core commit、R5 artifact hash、R8 release A與Chrome／Firefox版本。
- 對每個候選LOK method／callback記錄：stable header、unstable header、payload文件、LibreOffice QA測試與目前probe使用。
- 凍結fixture、operation、timeout、repetition與decision matrix；結果後不得放寬門檻。

### A1：Caret與typed callback

- click已知文字位置，擷取`INVALIDATE_VISIBLE_CURSOR`、`CURSOR_VISIBLE`、text-selection start/end/rectangles。
- 只解析`LibreOfficeKitEnums.h`文件化格式；測old rectangle與new JSON兩種documented variant，正規化為同一typed state。
- state至少含document handle、revision、visible、part、caret rectangle、selection rectangles及source sequence；不得含raw payload。
- 驗證zoom 100%／150%、tile rerender、scroll、CJK、emoji、段首／段尾與跨頁位置。

### A2：Closed keyboard action oracle

候選action固定為：

- `move-character-left/right`、`move-line-up/down`、`move-line-home/end`；
- 上述移動的`extend-selection`變體；
- `delete-backward`、`delete-forward`；
- `insert-paragraph-break`、`insert-line-break`。

diagnostic層可把closed action映射到文件化`postKeyEvent()`，但不得接受JS提供charCode／keyCode／modifier數字。
每次action要記before／after revision、callback sequence、selection text／geometry、save後文字與重複次數。

### A3：Mouse selection與geometry

- 以固定twips起點／終點建立forward／backward、同列／跨列／跨段selection。
- 比較`postMouseEvent` drag與`setTextSelection` start／end／reset的可觀察結果、callback順序與跨browser差異。
- 因`setTextSelection`屬unstable API，A需判定：可版本化包裝、僅內部相容層、或E1 v1不承諾drag handles。
- `getSelection()`文字、typed rectangles與ODT內容必須一致；無selection時回明確collapsed state。

### A4：Mutation completion、Undo／Redo與復原

- 研究void key/mouse LOK call如何形成request completion：候選barrier只能使用文件化callback、revision與語意readback，
  不用任意延遲或「收到任何invalidate就算完成」。
- 每個delete／break／format候選至少3次；確認一次request只造成一次mutation。
- stale revision、queue cancel、timeout before start、timeout after dispatch、Worker crash與reload分別驗證零mutation或
  typed outcome unknown；不得自動retry。
- Undo／Redo測空history、單步、多步、selection replace、Unicode、newline與format；save/reload後history不作持久承諾。

### A5：最低格式能力spike

- 候選closed operation：`set-bold(on|off)`、`set-italic(on|off)`、`set-paragraph-style(body|heading)`、
  `set-list(none|unordered|ordered)`。
- 不提供toggle-only模糊語意；若只能取得toggle而不能讀取／指定目標state，該能力標partial或移出E1 v1。
- 即使內部需固定command，也不能接受command string；需等待command completion並以save ODT XML、desktop PDF／文字與
  Undo／Redo驗證語意。

### A6：整合與checkpoint

- 將成立的caret／selection action與R7 host-owned IME／clipboard adapter組合；synthetic只驗state machine，
  不取代既有headed Chewing evidence。
- Chrome／Firefox跑plain、Unicode、multi-paragraph、styled/list與table-boundary fixture。
- save為ODT，做ZIP CRC／XML parse／anchor／格式／desktop LibreOffice round-trip；回歸R6、R7、Finding 012與R8。
- 產出`GO_TO_E1_B`、`PARTIAL_GO_TO_E1_B`或`STOP_OR_RESCOPE`。

## 4. 凍結fixture與案例維度

| Fixture | 目的 |
|---|---|
| `plain-grapheme` | ASCII、臺灣中文、emoji、combining mark、段首／段尾與空文件邊界 |
| `multi-paragraph` | 上下左右、Home／End、paragraph／line break、跨段selection |
| `styled-list` | bold／italic、body／heading、ordered／unordered list與Undo／Redo |
| `table-boundary` | caret／delete／newline碰到table cell邊界時安全拒絕或可解釋行為 |
| `r7-t2-styled` | Finding 012 close recovery與既有round-trip回歸 |

每個browser至少執行collapsed caret、forward selection、backward selection、stale revision、cancel／timeout與save/reload。
每個`EditorSession`最多3個Worker generation（＝最多2次崩潰／boundary回復），不能用無界restart規避。
> **2026-08-08 更正**：這句描述的「每頁」量**產品從未實作**；實際實作的是
> `EditorSession` 的 `maxWorkerGenerations`（預設 **3**）＝**同一個 session 的崩潰／
> boundary 回復次數**。**產品維持 3；「每頁」承諾撤除。**見
> [finding 026](../findings/026-generation-cap-means-two-different-things.md)
> 與 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)。


> **2026-08-08 前提更新**：本條的唯一依據是
> [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)，
> 而該 finding 的成因已改判為我方 harness
> （[023](../findings/023-sdk-init-wedges-at-fixed-session-depth.md) 的 unread pipe
> 與 [025](../findings/025-webdriver-script-injection-never-ran-on-firefox.md) 的注入腳本
> 從未執行）。實測：**同一頁面連續 50 個 engine generation 全過**
> （50 建 50 拆、active 0、記憶體斜率 +22.4 MB／block，遠低於 67 MB 門檻；證據
> `findings/evidence/sdk-r7/single-page-generations/firefox/s2-fresh/run-1/result.json`），
> 是本條所寫上限的 16 倍以上。**條文本身未改**——放寬它會改變本規格對外承諾的內容
> 與產品的 reload 行為，屬產品決定；此處僅記錄前提已不成立。


## 5. Typed contract候選（非承諾）

```ts
type EditorAction =
  | { kind: "move"; unit: "character" | "line" | "line-boundary"; direction: string; extend: boolean }
  | { kind: "delete"; direction: "backward" | "forward" }
  | { kind: "break"; breakType: "paragraph" | "line" }
  | { kind: "history"; action: "undo" | "redo" }
  | { kind: "inline-format"; format: "bold" | "italic"; enabled: boolean }
  | { kind: "paragraph-format"; style: "body" | "heading" }
  | { kind: "list-format"; style: "none" | "unordered" | "ordered" };
```

候選結果至少包含`beforeRevision`、`revision`、`changed`、`completion`與typed caret／selection snapshot。
實際名稱與shape只在A evidence成立後由B spec凍結。

## 6. Error與結果分類候選

- `EDITOR_ACTION_UNSUPPORTED`
- `EDITOR_STATE_UNAVAILABLE`
- `SELECTION_GEOMETRY_UNAVAILABLE`
- `STALE_REVISION`
- `NO_HISTORY_ENTRY`
- `MUTATION_NOT_STARTED`
- `MUTATION_OUTCOME_UNKNOWN`
- `WORKER_GENERATION_BUDGET_EXHAUSTED`
- 既有`TIMEOUT`、`ABORTED`、`WORKER_CRASHED`、`STALE_DOCUMENT`

錯誤不得附raw callback、任意command、使用者文件內容或clipboard資料。

## 7. 凍結門檻

- 自動browser：Chrome與Firefox；每個必要positive至少3次，每個negative至少1次。
- action callback barrier：10,000 ms；一般action request：30,000 ms；open／save：180,000 ms。
- 每個`EditorSession`最多3個Worker generation；R7 headed IME原則上重用，不新增人工輪次。
> **2026-08-08 更正**：這句描述的「每頁」量**產品從未實作**；實際實作的是
> `EditorSession` 的 `maxWorkerGenerations`（預設 **3**）＝**同一個 session 的崩潰／
> boundary 回復次數**。**產品維持 3；「每頁」承諾撤除。**見
> [finding 026](../findings/026-generation-cap-means-two-different-things.md)
> 與 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)。

- 每個成功mutation必須`revision = beforeRevision + 1`，除非A證據促成更嚴格、另有版本的batch定義；不得一個
  host action增加兩次產品revision。
- save output通過ZIP CRC、全部XML parse、預期anchor／格式與desktop LibreOffice reopen。
- timeout／abort／stale／unsupported不得silent mutation；outcome unknown不得自動retry。

機器版門檻見`wasm_sdk_probe/e1/discovery-matrix-v1.json`。

## 8. GO／部分GO／停止條件

**GO_TO_E1_B**：caret／selection geometry、closed keyboard actions、delete／break、Undo／Redo皆在兩browser形成
typed、exactly-once contract；至少bold／italic與一種paragraph/list能力安全成立；ODT round-trip通過。

**PARTIAL_GO_TO_E1_B**：核心文字編輯、selection與history成立，但drag handles、某格式或table-boundary需明確
unsupported；E1-B只實作成立capability。

**STOP_OR_RESCOPE**：必要caret／delete／break只能靠禁止surface；completion無法分辨重複／遺失；文件化callback
仍不足且必須解析內部payload；兩browser語意無法收斂；ODT輸出損壞；或recovery違反unsaved mutation邊界。

## 9. 預期evidence

```text
findings/evidence/sdk-e1/
  baseline/
  discovery/inventory.json
  discovery/browser/<browser>/<fixture>/<case>/result.json
  discovery/callback-contract/
  discovery/mutation-barrier/
  discovery/roundtrip/
  discovery/regression/
  discovery/summary.json
```

若A觸發停止，只保存diagnostic artifact、原始callback／操作序列與finding；不建立E1-B假API。

## 10. 執行授權邊界

本節保留E1-A規劃當時的授權邊界：執行前需另列精確新增／修改檔案、是否建立隔離diagnostic profile、link/build
命令、browser runner、fixture來源、validator與預期artifact；取得確認後才可修改或build。E1-A實際執行已依此
另行取得確認，結果記於第11節；本段不是目前仍停在規劃階段的聲明。

## 11. 執行結果（2026-08-04）

### 11.1 已完成範圍

- A0 corpus、matrix與baseline均通過；core HEAD、六筆既有dirty現場及R5 `writer-review`兩個hash在after
  preflight完全一致。
- 建立隔離`e1-editor-discovery` diagnostic profile；manifest明列
  `productionArtifactReplaced:false`、`rawCallbackExposed:false`、`arbitraryKeyCodeAccepted:false`及
  `arbitraryUnoCommandAccepted:false`。
- closed character move與Shift selection在Chrome／Firefox各3次完成；backward delete以documented
  visible-cursor callback在兩瀏覽器各3次完成，revision每次只加1。
- Chrome另取得break、Undo／Redo、bold／italic、table-boundary與R7 styled回歸資料；所有失敗嘗試以attempt目錄保留。
- 4項Python decision／corpus／profile測試、14項Document SDK／discovery client測試、ABI header與Emscripten C++
  編譯均通過；R6 release仍為GO，R7／R8靜態回歸通過。

### 11.2 停止證據

- 在plain fixture插入`ABC`後，closed forward delete於Chrome 150與Firefox 153都在30秒後`TIMEOUT`；沒有
  documented tile、caret或selection callback可歸屬該request。
- 兩份逾時後save output都含`E1-PLAIN-STARTBCASCII`且不含`E1-PLAIN-STARTABCASCII`，並通過ODT ZIP CRC／XML
  parse；因此mutation已發生，但SDK無法安全知道結果。
- harness沒有retry；同Worker後續closed action回`BUSY`。這符合`MUTATION_OUTCOME_UNKNOWN`安全語意，卻直接命中
  第8節「completion無法分辨重複／遺失」停止條件。
- Machine summary為`complete:true`、`stoppedEarly:true`、`decision:STOP_OR_RESCOPE`。依第9節不再執行Firefox
  其餘4個fixture、完整round-trip與E1-B；這是規格要求的提早停止，不是遺漏。

### 11.3 附帶觀察

- Chrome cumulative line-up在到達文件邊界後同樣沒有callback；不能把no-op假報成功。
- `postMouseEvent` drag首輪沒有形成可用selection completion；`setTextSelection`仍只能視為unstable內部候選。
- paragraph／list部分fixed command沒有回UNO command result；不能以toolbar外觀或dispatch return宣稱成功。
  **（2026-08-05 E2-A撤回本項歸因）** 原生實測顯示`.uno:DefaultBullet`／`.uno:DefaultNumbering`／
  `.uno:RemoveBullets`都有回command result；段落樣式之所以毫無回應，是因為E1-A映射到的
  `.uno:Heading1ParaStyle`／`.uno:TextBodyParaStyle`是UI別名、沒有可派送slot，見
  [finding 019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)。command result本身另有可信度
  問題，見[finding 020](../findings/020-lok-list-command-result-contradicts-document.md)。原觀察「不能以
  dispatch return宣稱成功」仍然成立，但成因與本文件當時的判斷不同。

### 11.4 判定與下一步（歷史checkpoint；已由11.8解除）

**判定：`STOP_OR_RESCOPE`。** 主要阻礙記為[Finding 016](../findings/016-lok-forward-delete-completion-gap.md)。
E1-B／E1-C不啟動。原始checkpoint只能證明WASM profile沒有收到可歸屬completion；2026-08-05原生對照已推翻
「上游缺少acknowledgement」的歸因；後續scheduler最小實驗又否證「我方缺主迴圈」，證實word-count state會在
顯式drain前自然抵達。現改判為SDK callback分類／completion歸屬缺口。下一步只評估可承諾的closed typed barrier，
不導入`unipoll`／`runLoop`控制反轉。禁止以sleep、任意state／invalidate、raw UNO或自動retry繞過。

Machine evidence：`findings/evidence/sdk-e1/discovery/summary.json`；基線：
`findings/evidence/sdk-e1/baseline/preflight-after.json`。本階段不需要人工驗收。

### 11.5 Finding 016早期補救結果（歷史checkpoint）

- 使用closed action到四個固定Writer command的內部映射，並以文件化
  `LOK_CALLBACK_UNO_COMMAND_RESULT`作completion；沒有JS command字串、raw UNO、任意key code或新core patch。
- paragraph break與line break在Chrome最終artifact各3/3成功，revision每次只增加1。
- delete dispatch前使用文件化focused-paragraph snapshot區分段落中間與邊界；經過JSON parser、render時序與
  search後a11y reattach共五輪漸進實驗，snapshot仍維持預設空段落。六次段落中間delete皆被安全拒絕，六次真正
  boundary negative亦被同一typed error拒絕，無法形成positive delete contract。
- 補救validator輸出`findings/evidence/016/remediation/summary.json`：
  `complete:false`、`decision:STOP_OR_RESCOPE`。Chrome已命中本spec停止條件，因此不再跑Firefox或完整A6矩陣。
- core HEAD、既有dirty現場與R5 `writer-review` hash在補救前後完全一致；本輪不需人工驗收。

**結論不變：`STOP_OR_RESCOPE`。** Fixed command足以保留為break候選研究成果，但不足以讓必要delete通過第8節；
E1-B／C仍不得啟動。

### 11.6 2026-08-05原生對照後的中間改判（已由11.7修正）

- [Finding 017](../findings/017-lok-collapsed-selection-readback.md)已完成SDK側修正、artifact重建、16項SDK單元測試、
  E1靜態回歸及headed瀏覽器驗證。空selection現在以`selectionType:"none"`表達，並與
  `selection.observed && selection.collapsed`的callback路徑交叉驗證；017不再阻斷。
- Finding 016的a11y候選已否證：listener未掛上與真空段落在公開readback無法區分，不能作權威boundary gate。
- 乾淨的原生26.8對照確認delete確實改字元，且約600 ms後收到185筆`STATE_CHANGED`，含
  `.uno:StateWordCount`由94變93字元。當時因我方probe沒有直接呼叫`runLoop`／unipoll／scheduler，推論延遲型
  callback未被flush；此推論使Finding 016的「是否上游」先改為**否**，不可送Bugzilla。
- 上述WASM主迴圈解釋在當時仍只是原生／WASM表面對照支持的**推論**，所以先要求隔離最小實驗，而未直接改架構。
- 完整證據與方法交接見
  [DEVLOG-2026-08-05-lok-readback-and-completion.md](../DEVLOG-2026-08-05-lok-readback-and-completion.md)。

### 11.7 Finding 016 scheduler最小實驗

- 建立隔離`finding-016-scheduler` profile，只在該profile暴露一次性
  `unit_lok_process_events_to_idle()` diagnostic operation；未修改或重建Core，也未替換R5 artifact。
- Chrome 150與Firefox 153都在delete後等待1000 ms、**呼叫drain之前**收到
  `.uno:StateWordCount`的93字元狀態；兩邊drain的state／word-count增量皆為0。
- 兩邊都精確刪除一字元、輸出合法ODT、無raw callback／任意UNO／retry。Machine summary：
  `findings/evidence/016/scheduler-wasm/summary.json`為`pass:true`，decision均為
  `WORD_COUNT_CALLBACK_DELIVERED_WITHOUT_DRAIN`，`schedulerHypothesisSupported:false`。
- 因此11.6的「WASM缺主迴圈」是已否證推論。Finding 016改判為SDK未分類／歸屬已到達的document state；
  `StateWordCount`特定payload尚未證明可作產品承諾，故E1仍維持`STOP_OR_RESCOPE`，但不需進行`runLoop`重構。

### 11.8 Finding 016 verified-selection barrier與恢復執行

#### 已觀察

- 隔離`finding-016-selection-barrier` profile先用closed action選取待刪除unit，等文件化typed selection callback，
  再於engine command loop以public selection readback確認單一有效文字unit；驗證後才送固定Delete／Backspace。
- 成功completion需同一transaction serial、成功command result、新collapsed typed selection與public none readback；
  revision只增加1。250 ms deadline只能拒絕，不能宣稱mutation成功。
- Chrome 150與Firefox 153的ASCII、中文、emoji、combining grapheme前後向刪除，各自24/24通過；精確mutation、
  selection文字、revision與public Undo還原全數符合。
- 每個browser四個段落／table cell邊界案例都回`EDITOR_BOUNDARY_UNSUPPORTED`，revision delta 0、內容不變；
  邊界拒絕後因晚到callback風險明定使用fresh Worker。
- 兩瀏覽器各五份ODT通過ZIP CRC、XML與anchor檢查，總計十份再由desktop LibreOffice 26.2.4.2 reopen並
  export PDF，10/10通過。總結為
  `findings/evidence/016/selection-barrier-wasm/summary.json`與`roundtrip/summary.json`。
- 沒有raw callback、任意key code、任意UNO、`StateWordCount` completion或automatic retry；未修改／重建Core，
  未替換R5 `writer-review`。

#### 推論與判定

- Verified-selection barrier建立可歸屬、exactly-once且fail-closed的必要delete contract，Finding 016不再命中第8節
  「completion無法分辨重複／遺失」停止條件。
- **目前判定為「解除停止並恢復E1-A」，不是E1-A GO。** 原始停止依第9節省略Firefox其餘fixtures與完整A6；
  format／list、全套round-trip與recovery仍需補完，才能判斷`GO_TO_E1_B`或`PARTIAL_GO_TO_E1_B`。
- 結構邊界與fresh Worker要求必須成為capability／UI可見限制，不得將拒絕當成成功或自動重送mutation。

### 11.9 A6最終整合與checkpoint

#### 已觀察

- `e1-editor-discovery`已整合Finding 016 verified-selection barrier；manifest明列
  `verified-selection-delete`、`automaticRetry:false`、`stateWordCountUsedForCompletion:false`與
  `boundaryRejectionRequiresFreshWorker:true`。沒有修改或重建LibreOffice core，也沒有替換R5 `writer-review`。
- Chrome 150與Firefox 153的五個fixture皆完成，最新結果10/10為`pass:true`；兩瀏覽器的character left/right、
  Shift selection、backward／forward delete、paragraph／line break及public Undo各達3次門檻。Delete completion均為
  `verified-selection-delete`，每次revision只增加1。
- styled fixture在兩瀏覽器各完成bold及italic的三輪明確`off → on`；共12次format mutation／browser，全部
  `changed:true`、revision +1，最後回到原格式。paragraph／list未取得可承諾的跨瀏覽器completion，未升格。
- line Up／Down／Home／End曾在Chrome一次全部3/3通過，但相同artifact的下一輪於第一個End逾時；成功與失敗皆保留，
  記為[Finding 018](../findings/018-lok-line-navigation-completion-nondeterministic.md)。最終capability不包含line
  navigation。
- diagnostic fixed Redo回`LOK_COMMAND_FAILED`，未以dispatch return或UI狀態假報成功；E1 v1只保留已成立的public
  Undo，Redo明確unsupported。drag handles、paragraph/list與結構邊界編輯亦保持縮限。
- 10份Chrome／Firefox輸出ODT全部通過ZIP CRC、XML、anchor與結構檢查，再由desktop LibreOffice reopen／export
  PDF，10/10通過。Machine summary：`findings/evidence/sdk-e1/discovery/summary.json`；round-trip：
  `findings/evidence/sdk-e1/discovery/roundtrip/summary.json`。
- R6 release仍為GO；R7、Finding 012、R8與Finding 016靜態／既有decision回歸均通過。after preflight確認core
  `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`、六筆既有dirty現場及R5 artifact hash完全保留。

#### 推論與判定

- 必要ODT文字編輯、character caret／selection、delete、兩種break、Undo及bold／italic已形成兩瀏覽器closed typed
  contract，且round-trip安全成立；Finding 016原停止條件沒有復發。
- 完整GO仍不成立：line navigation沒有確定completion，Redo未成立，mouse drag／handles與paragraph/list沒有安全
  跨瀏覽器契約，structural boundary仍需拒絕後fresh Worker。
- **最終判定：`PARTIAL_GO_TO_E1_B`。** E1-B只能實作上述已成立capability；縮限項目必須在manifest與UI明示，
  不得以raw UNO、任意key code、sleep、callback猜測或automatic retry補齊。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。凍結A0～A6 discovery順序、closed action候選、門檻、evidence與checkpoint。 |
| 2026-08-04 | v2。完成隔離discovery；Finding 016跨瀏覽器確認mutation outcome unknown，判定STOP_OR_RESCOPE並停止E1-B。 |
| 2026-08-04 | v3。完成Finding 016 fixed-command補救；break成立但delete缺可靠boundary readback，停止判定維持。 |
| 2026-08-05 | v4。Finding 017修復；原生對照推翻上游缺口歸因，Finding 016改判為我方WASM缺LOK主迴圈，維持停止判定。 |
| 2026-08-05 | v5。隔離scheduler實驗跨Chrome／Firefox否證主迴圈缺口；改判為SDK callback分類／歸屬缺口，停止判定維持。 |
| 2026-08-05 | v6。Verified-selection barrier跨Chrome／Firefox與desktop round-trip通過；Finding 016解除停止，恢復剩餘A6矩陣。 |
| 2026-08-05 | v7。完成A6雙瀏覽器10 fixture、10份desktop round-trip與回歸；判定PARTIAL_GO_TO_E1_B，line navigation／Redo／drag／paragraph-list縮限。 |
| 2026-08-08 | 更正。更正 Worker generation 上限的**語意**：規格原本寫「每頁」，但產品唯一實作的是每個 `EditorSession` 的崩潰／boundary 回復次數（`maxWorkerGenerations`，預設 3）。**產品維持 3，「每頁」承諾撤除**（無實作，且 finding 014 撤回後無已量測理由）。條文與註記已就地修訂；未動任何閘門，判定不變。見 finding 026。 |
