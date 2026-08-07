# SPEC E1-B：窄版 Editor Contract 與 Host Shell

> **日期**：2026-08-05  
> **狀態**：完成；`GO_TO_E1_C`  
> **前置條件**：[E1-A](./SPEC-E1-A-editing-discovery.md) 已完成並判定
> `PARTIAL_GO_TO_E1_B`

## 1. 目的

E1-B 將 E1-A 已跨 Chrome／Firefox成立的操作縮成一份可版本化的產品 contract，並建立最小 host editor
shell。這不是把 diagnostic API 改名：產品 profile 必須只匯出白名單 ABI，Worker 只接受 typed operation，JS 不得
接觸任意 key code、UNO command、WASM pointer或raw LibreOfficeKit callback。

E1-B 完成後只代表窄版編輯 contract 與 shell 可以進入 E1-C；完整 IME、clipboard、recovery、ODT corpus與人工
可用性驗收仍屬 E1-C。

## 2. 已凍結的 v1 capability

| capability | 公開語意 | mutation |
|---|---|---|
| `move-character-left` | 向左移動一個 Writer character unit；可明確要求延伸 selection | 否 |
| `move-character-right` | 向右移動一個 Writer character unit；可明確要求延伸 selection | 否 |
| `delete-backward` | verified-selection barrier 後刪除前一個安全文字 unit | 是 |
| `delete-forward` | verified-selection barrier 後刪除下一個安全文字 unit | 是 |
| `insert-paragraph-break` | 插入 Writer paragraph break | 是 |
| `insert-line-break` | 插入 Writer line break | 是 |
| `set-bold` | 以 explicit boolean 設定 inline bold | 視狀態而定 |
| `set-italic` | 以 explicit boolean 設定 inline italic | 視狀態而定 |

`click`、Unicode committed text、selection文字readback、Undo、save與close沿用Document SDK既有公開方法，不在
Editor ABI重複定義。R7 `HostInputAdapter`仍是composition／clipboard commit唯一host邊界。

以下固定為unsupported：line up/down/home/end、Redo、mouse drag／handles、paragraph／list style、structural
boundary delete、generic key event、generic UNO command及空字串`replaceSelection()`刪除替代。

## 3. C ABI v1

- 版本：`OXSDK_EDITOR_ABI_VERSION == 1`。
- 匯出：`oxsdk_editor_action()`、`oxsdk_editor_get_state()`。
- action只接受本spec第2節八個enum；未知值、錯誤boolean、無效request／document handle必須同步回
  `OXSDK_STATUS_INVALID_ARGUMENT`。
- mutation帶`expected_revision`；stale revision必須零mutation。
- 產品profile不匯出`oxsdk_editor_discovery_*`，也不宣告diagnostic capability。
- 實作可重用E1-A已驗證的內部engine mapping，但產品header不得include或暴露diagnostic enum。

## 4. Worker protocol

產品profile只開放：

- `editorActionV1`：`{documentHandle, expectedRevision, action, extendSelection, enabled}`。
- `editorGetStateV1`：`{documentHandle}`。

Worker以manifest capability `narrow-editor-v1`及`editorContract.version == 1`雙重gating。action字串先經固定map轉換；
payload不得帶`keyCode`、`unoCommand`或任意command string。Diagnostic operation在產品profile必須回
`UNSUPPORTED_OPERATION`。

## 5. Typed result與state

action result至少包含：

- `action`、`beforeRevision`、`revision`、`changed`
- `completion`
- `state`

state只公開：

- `revision`、`sourceSequence`、`documentChangeSequence`
- `visible`與nullable caret rectangle
- selection的`observed`、`collapsed`、nullable start／end與rectangle陣列
- `selectionType`、`selectionTextMissing`、`selectionText`
- `format.bold`、`format.italic`，未知值為`null`

不把a11y diagnostic counters、scheduler probe或raw callback payload升格為產品state。

## 6. Exactly-once與錯誤邊界

- Host shell以單一FIFO mutation queue串行化文字commit與editor mutation。
- timeout、abort、Worker crash、`MUTATION_OUTCOME_UNKNOWN`均不自動retry。
- delete只接受`completion == "verified-selection-delete"`且`revision == beforeRevision + 1`。
- `EDITOR_BOUNDARY_UNSUPPORTED`若附帶fresh-worker要求，session進入`restart-required`，封鎖後續mutation；只有以
  authority／last saved bytes重開新Worker才能恢復。
- format no-op可回`changed:false`且revision不變；實際format mutation必須`changed:true`且revision加一。
- navigation不得改revision，且必須由文件化caret／selection callback完成。

## 7. Host editor shell

Shell只提供：開啟ODT、tile顯示、click定位、文字輸入sink、字元移動／selection、雙向delete、兩種break、Undo、
bold／italic、save及reload。未成立功能不得顯示成可用按鈕。

Session至少有`idle`、`loading`、`ready`、`busy`、`restart-required`、`recoverable-error`與`closed`狀態；stale
handle、crash及boundary rejection必須停用input。E1-B自動shell使用合成commit驗證；真實Chewing IME不在本階段
重做。

## 8. 執行順序

1. **B0 contract freeze**：header、manifest與JS typed surface一致，negative test fail closed。
2. **B1 ABI/profile**：隔離`e1-editor-v1`可build；不取代R5／R6／R8 artifact。
3. **B2 client/session**：FIFO、revision、restart-required與no-retry單元測試通過。
4. **B3 shell smoke**：Chrome／Firefox各完成同一窄版操作序列並保存ODT evidence。
5. **B4 checkpoint**：靜態、既有release regression與workspace preflight全部完成。

## 9. 判定

**GO_TO_E1_C**：八個Editor action、既有text／Undo、typed state、session queue及雙browser shell smoke全部通過；
產品profile沒有generic escape hatch，preflight與回歸通過。

**PARTIAL_GO_TO_E1_C**：安全contract與必要文字編輯成立，但非必要format或單一browser shell整合須明確縮限；不影響
exactly-once、ODT保存或recovery邊界。

**STOP_OR_RESCOPE**：產品profile仍能呼叫未核准action；mutation completion無法歸屬；boundary rejection後可繼續
寫入；timeout／crash會自動重送；typed state必須解析未承諾payload；或輸出ODT損壞。

## 10. Evidence

機器證據寫入`findings/evidence/sdk-e1/editor-contract/`，至少包含before／after preflight、profile inventory、
Chrome／Firefox結果、regression與`summary.json`。每次browser失敗保留獨立attempt，不覆寫先前結果。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。依E1-A `PARTIAL_GO_TO_E1_B`凍結八個產品action、typed state、boundary restart及B0～B4門檻。 |
| 2026-08-05 | v2。完成產品ABI、Worker、client/session、雙browser shell、ODT round-trip與回歸；判定`GO_TO_E1_C`。 |

## 12. 執行結果

### 12.1 已觀察

- 隔離profile `e1-editor-v1`只匯出`oxsdk_editor_action()`與`oxsdk_editor_get_state()`；manifest以
  `narrow-editor-v1`及`editorContract.version == 1`雙重gating，八個action與本spec第2節完全一致，沒有
  discovery symbol、diagnostic capability、任意key code或UNO command入口。
- JS client、FIFO session與host shell已完成。Boundary rejection會進入`restart-required`並封鎖後續mutation；
  restart只以authority／已保存bytes建立fresh Worker，不重送先前操作。Timeout、crash與outcome unknown同樣
  不自動retry。
- Chrome 150與Firefox 153各完成27筆窄版操作，包含click／typed state、字元移動與selection、Unicode文字、
  backward／forward delete、paragraph／line break、Undo、bold／italic、save與安全boundary rejection；兩份最終
  result均為`pass:true`。
- Chrome輸出ODT為10,918 bytes、SHA-256
  `cf4c297cad94c42178cfe8a284d8fe83c13b31e723e34c27eb8acf4d38f69912`；Firefox為10,912 bytes、
  `37c23c2705e2b53a90f25990996ef324101a167851854c91f94e566494154a23`。兩份均通過ZIP CRC、XML、原始與新增
  anchor檢查，並由desktop LibreOffice 26.2.4.2 reopen／輸出PDF成功。
- R6 release、R7-D、R8-D、E1-A與E1-B static regression全部通過。Before／after preflight均為`pass:true`；
  Core HEAD、六筆既有dirty檔案與R5 `writer-review` artifact未變。
- 最終machine evidence在
  `findings/evidence/sdk-e1/editor-contract/summary.json`，`complete:true`且decision為`GO_TO_E1_C`。

### 12.2 失敗嘗試與修正

- 第一版C++直接include discovery header，因既有typedef `oxsdk_editor_action`與產品export函式同名而編譯失敗；
  最終改用產品私有numeric mapping，避免產品header依賴或暴露diagnostic enum。
- 受控環境第一次browser runner在建立本機socket前即被sandbox拒絕，保留於
  `browser/launch-sandbox-denied.json`；以同一條無root命令取得允許後完成，不改用外部服務。
- 第一輪Chrome runner因頁面只提供新的E1-B metrics名稱而逾時；加入相容的read-only metrics alias後續跑。其後
  attempt-01至04依序保留boundary後不可續用、重新搜尋仍落在結構邊界、click後立即讀到舊selection，以及過窄
  forward-delete文字期待等結果。最終session在單次public click後只輪詢typed state，沒有重送click；測試也改以
  mutation postcondition判定，attempt-05通過。
- Desktop validator在sandbox內曾因dconf runtime目錄唯讀而無法啟動；該次ZIP／XML檢查已通過，但暫判STOP。
  同一validator以無root授權重跑後兩份desktop round-trip皆通過，最終summary才改為GO。

### 12.3 推論

- E1-A的verified-selection barrier可以安全升格為窄版產品contract；應用不需也不能接觸raw callback、任意按鍵或
  arbitrary command string。
- `click()`的回覆只表示事件已派送，不代表typed caret state已同步；產品session必須以bounded typed-state poll
  等待collapsed selection。這是host completion規則，不需要增加ABI或解析未承諾callback。
- 八個action加既有Document SDK文字commit、Undo與save，已足以支撐E1-C驗證的最小ODT-first editor；未成立的
  line navigation、Redo、drag／handles、paragraph/list與結構邊界編輯維持不可用。

### 12.4 待驗證

- E1-C重用R7 headed真實Chewing IME／clipboard流程，確認caret移動、selection取代與composition cancel仍維持
  exactly-once；只在自動證據不足時集中一次人工驗收。
- E1-C補齊crash、stale handle、restart、ODT corpus與較長操作序列；boundary後fresh Worker規則不得放寬。

### 12.5 判定

八個Editor action、既有文字／Undo、typed state、FIFO session、雙browser shell、ODT round-trip、回歸與workspace
保護全部通過，且產品profile沒有generic escape hatch。E1-B判定 **`GO_TO_E1_C`**；未觸發停止條件，也不需新增
編號finding。
