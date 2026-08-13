# DEVLOG 2026-08-05：WASM SDK E1

## Finding 016人工觀察頁r4

### 已觀察

- 操作員判定r3的Delete與Backspace兩個一鍵案例都失敗；保存的Backspace log中，move-right雖以
  `documented-callback-visible-cursor`完成，但回應仍是`selection.collapsed:false`，selection rectangle完整涵蓋
  `0123456789`。
- Backspace完成後selection才變成collapsed；預期`012345678`與原始`0123456789`皆搜尋不到。原始紀錄保存於
  `findings/evidence/016/manual/operator-2026-08-05-03.log`，未將失敗覆寫。
- r4移除一鍵案例的方向鍵collapse：改由search result rectangle計算開頭／結尾座標，使用既有public click定位。
- r4在delete dispatch前依序呼叫公開`getSelection()`與typed editor `getState()`；只有selection text為空且
  `selection.collapsed:true`才允許mutation，否則回`CARET_NOT_COLLAPSED`並停止。
- 字元與段落邊界四個案例皆套用相同前置條件；沒有raw UNO、raw callback、任意key code、sleep或mutation retry。
- Python 6/6、Node 15/15、JS syntax、C++ header syntax與Python compile全通過；source、dist與HTTP served資產hash
  一致。沒有重建WASM或LibreOffice core，core基線未變。

### 推論

- r3失敗不是Delete／Backspace固定command方向已證明錯誤，而是用方向鍵callback當成selection collapse barrier的
  前提不成立；後續mutation很可能正確地刪除了當時仍存在的整段選取。
- r4的雙重readback先保證「不是整段selection」再測delete方向，可將caret定位失敗與delete command行為分離；但
  click精確落在字元邊界的實際結果仍需headed人工觀察。

### 待驗證

- Chrome headed環境中，矩形開頭／結尾click是否分別穩定落在`0`之前與`9`之後。
- pre-mutation readback是否得到空selection與`collapsed:true`；若否，r4應安全停止而非刪除內容。
- Delete是否得到`123456789`、Backspace是否得到`012345678`，以及段首／段尾是否只合併預期段落。

### 判定

- r4靜態實作完成，互動狀態為`pending-operator-r4`；E1 Finding 016仍維持`STOP_OR_RESCOPE`，不得把人工頁結果當成
  SDK產品契約。

## Finding 016人工觀察頁r5

### 已觀察

- r4 Backspace在search rectangle末端執行public click後，公開`getSelection()`仍回完整`0123456789`，typed state
  也仍為`collapsed:false`；`CARET_NOT_COLLAPSED`在mutation前正確停止。原始log保存於
  `findings/evidence/016/manual/operator-2026-08-05-04.log`。
- 過往E1 Chrome／Firefox plain discovery中，`placeCaretAtRectangleEnd()`以closed
  `selection-reset-unstable`完成後，流程能繼續insert與backward delete；因此r5改採該既有方法，而非再發明未驗證
  的click／key組合。
- r5仍以`getSelection()`及typed `getState()`雙重驗證空selection與collapsed state，不成立就不dispatch delete。
- Python 6/6、Node 15/15、JS syntax、C++ header syntax與Python compile通過；HTTP served與source／dist hash一致，
  沒有重建WASM或LibreOffice core。

### 推論

- public click在目前LOK Writer view中不等同「清除search selection」，不能當作caret placement契約。
- selection reset雖有過往成功證據，但位於unstable diagnostic surface；即使r5人工行為通過，也只能回答診斷問題，
  不能直接升格為產品SDK承諾。

### 待驗證與停止界線

- 操作員只需再驗證r5 Delete與Backspace。若reset timeout或readback仍非collapsed，本人工迭代停止，記錄為目前
  selection control不足；不再用更多人工技巧繞過。

## Finding 017交接與人工流程停止

### 已觀察

- r5 selection reset後，public `getSelection()`回
  `LOK_ERROR: Flavor text/plain;charset=utf-16 is not supported`；失敗發生在Delete dispatch前，revision仍為0。
- Project `handleGetSelection()`明確要求`text/plain;charset=utf-8`；LibreOfficeKit `getFromTransferable()`會將該
  MIME canonicalize成內部`text/plain;charset=utf-16` OUString flavor，unsupported時產生逐字相同錯誤。
- 現行public getSelection將LOK null一律映射為`LOK_ERROR`；同一engine的typed editor getState則把null
  selection pointer序列化成空`selectionText`，兩者契約不一致。
- LibreOfficeKit header已有`getSelectionType()`及since 7.4的`getSelectionTypeAndText()`；這是接手者可先驗證的
  文件化候選，不需先修改core。
- 建立`findings/017-lok-collapsed-selection-readback.md`、原始log、source trace與machine metadata。沒有修改程式、
  沒有build，Core與原有dirty現場保持不變。

### 推論

- Reset很可能已成功清除文字selection，但因public readback不能表示none而失敗；本輪未執行其後typed getState，故
  不把reset成功寫成事實。
- 最小修正應先讓SDK明確區分none／text／complex selection，不能簡單吞掉所有LOK error或把unsupported flavor一律
  假裝成空字串。

### 判定

- Finding 016人工r1～r5正式停止；不再要求操作員重測。
- E1維持`STOP_OR_RESCOPE`。Finding 017修正、unit／Emscripten／headed跨瀏覽器驗證完成前，不恢復Delete／Backspace
  驗收。

## 後續更新：Finding 017已修、Finding 016根因改判

本文件以上段落是人工r4／r5與Finding 017建立當下的逐步紀錄；其「待修／待驗證」狀態已由同日後續工作取代。
完整交接以[DEVLOG-2026-08-05-lok-readback-and-completion.md](./DEVLOG-2026-08-05-lok-readback-and-completion.md)
為準，原始失敗歷程保留不覆寫。

### 已觀察

- Finding 017已在SDK側改用selection type aware readback，並以transferable與
  `selection.observed && selection.collapsed` callback兩條獨立路徑交叉驗證caret；artifact重建、16項SDK測試、
  E1靜態回歸及headed瀏覽器驗證通過，017不再阻斷。
- 原生26.8對照在forward delete確實改變文件後收到185筆延遲型`STATE_CHANGED`，其中
  `.uno:StateWordCount`由94變93字元；callback約在UNO command result後600 ms抵達。
- 我方WASM引擎沒有`runLoop`、unipoll或其他LO scheduler驅動，整場亦未收到原生明確存在的format state串流。
- 因此Finding 016的「是否上游」已改為否、不可送Bugzilla；先前a11y同步boundary路線亦已否證。

### 推論與下一步

- 最合理解釋是WASM Worker的執行模型沒有讓LOK延遲型callback被flush；此解釋尚未由WASM scheduler實跑直接證實。
- E1維持`STOP_OR_RESCOPE`，E1-B／C不啟動。下一個最小測試是在隔離WASM diagnostic內讓LO scheduler實際執行
  一次，觀察`STATE_CHANGED`是否恢復；通過前不直接導入不返回的`runLoop`控制反轉。

## Finding 016 scheduler最小實驗完成

以上「WASM未flush延遲callback」是實驗前推論；本節為最新結果。

### 已觀察

- 獨立`finding-016-scheduler` profile使用Core既有`unit_lok_process_events_to_idle()`，沒有修改／重編Core，也沒有
  替換R5 `writer-review`。
- Chrome 150／Firefox 153都在delete後等待1000 ms、drain前自然收到`StateWordCount`的93字元狀態；兩邊drain
  增量均為0，精確刪除一字元並輸出合法ODT。
- `findings/evidence/016/scheduler-wasm/summary.json`為`pass:true`；decision均為
  `WORD_COUNT_CALLBACK_DELIVERED_WITHOUT_DRAIN`，`schedulerHypothesisSupported:false`。
- Chrome前兩次失敗分類與最後成功run均保留，沒有mutation retry或覆寫失敗證據；Core dirty基線前後一致。

### 推論與判定

- 主迴圈缺口假說已否證；舊probe未把已到達的document state納入typed completion，才是目前最窄解釋。
- 特定payload能否成為穩定產品契約仍待驗證，所以Finding 016與E1 `STOP_OR_RESCOPE`尚未解除；下一步是closed typed
  completion barrier評估，不是`runLoop`重構，也不需人工驗收。

## Finding 016 verified-selection barrier完成

### 已觀察

- 新增隔離`finding-016-selection-barrier` profile。host只傳closed `delete-forward`／`delete-backward`；SDK先形成一個
  unit selection，等typed selection callback，在engine command loop用public selection readback確認單一文字unit，
  才送固定Delete／Backspace。
- Completion要求同一document／request／transaction serial的成功command result、新collapsed selection與public none；
  revision只增加1。250 ms deadline只能回安全拒絕，不能宣稱mutation成功。
- Chrome 150與Firefox 153的ASCII、中文、emoji、combining grapheme前後向刪除，各自24/24通過；selection文字、
  exact mutation、revision +1與public Undo還原均符合，兩瀏覽器合計48/48。
- 每個browser四個段首／段尾／table cell邊界案例均回`EDITOR_BOUNDARY_UNSUPPORTED`、revision delta 0、內容不變；
  合計8/8。邊界拒絕後因晚到callback可能污染同Worker，contract明定fresh Worker。
- 兩瀏覽器各五份輸出ODT均通過ZIP CRC、XML與anchor檢查；desktop LibreOffice 26.2.4.2 reopen／PDF export
  10/10通過。總結：`findings/evidence/016/selection-barrier-wasm/summary.json`；desktop：`roundtrip/summary.json`。
- Artifact diagnostic hash：loader `43a26f0520a7da5a31de219977cf9c64a8bc97581cd4e6619bc0673930f4240b`、
  WASM `a55343b441d27f424f49d39647785a482e881b86bd3b2765487c167db907fe80`、Worker
  `289e4d0036ae7a21d951b1152bcfcd7549ae58f18ef36e00acdde7f9ef88c544`。
- 沒有raw callback、任意key code、任意UNO、`StateWordCount` completion或automatic retry；Core HEAD與dirty
  baseline不變，R5 `writer-review`未替換。

### 失敗嘗試（保留，未覆寫）

- 第一版在callback內直接read selection／dispatch，Chrome命中callback reentrancy並使Worker crash；之後所有
  callback只記typed signal並排入engine-loop internal command。
- Smoke第一輪selection barrier本身成功，但測試以舊discovery Undo判讀LO void `success:false`而失敗；改用public
  `documentHandle.undo()`後通過。
- Chrome attempt-02的24個正向案例全過，但document-start沒有callback，action timeout，後續search回`BUSY`。
- attempt-03加入立即fallback後反而跑在callback之前，將第一個正向案例誤判boundary；該結果與smoke失敗均保留。
- attempt-04正向案例全過，document-start安全拒絕；paragraph-end雖在mutation前停止，卻因同步reset selection與
  晚到callback交錯而升格成`EDITOR_STATE_UNAVAILABLE`。最終改成每個boundary案例全新Worker，不在同Worker重置。
- C++曾將`transactionSerial`誤放進`EditorPendingOperation`造成六個compile error；移回
  `SelectionBarrierTransaction`後通過。靜態測試也曾因fixture capability與過寬retry assertion失敗，均修正並留在
  本日操作輸出，而非刪除成功前的歷程。

### 推論

- Finding 016不是上游缺ack、WASM缺scheduler，也不需要解析語系相依`StateWordCount`。最窄根因是SDK未把已驗證的
  selection事實與固定mutation acknowledgement綁成單一transaction。
- Selection barrier足以解除Finding 016停止條件，但目前是隔離diagnostic contract。E1-A因早停而省略的Firefox
  fixtures、format／list、完整round-trip與recovery仍需補齊，因此不能直接寫成E1-A GO。

### 判定與下一步

- Finding 016：**已解除阻斷**；machine decision
  `SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART`。結構邊界拒絕後需fresh Worker。
- E1-A：由`STOP_OR_RESCOPE`恢復執行剩餘A6矩陣；完成後才判定`GO_TO_E1_B`或`PARTIAL_GO_TO_E1_B`。
- 不需新增人工GUI驗收；後續優先使用自動browser與desktop machine evidence。

### 協作執行備忘

- 若受控環境反覆對本機browser／desktop啟動顯示資安警告，不循環要求提權。Agent先完成程式、靜態測試與證據
  讀取，再交給操作員執行**一條明確、可重現、無root的本機命令**；操作員只回報完成或短錯誤，Agent讀取
  machine evidence收尾。本輪Firefox與desktop round-trip已用此模式完成。

## E1-A剩餘A6矩陣完成

### 已觀察

- 將已驗證的Finding 016 selection barrier編入`e1-editor-discovery`，但仍維持isolated diagnostic profile；manifest
  新增`verified-selection-delete`及完整fail-closed限制。SDK loader hash為
  `43a26f0520a7da5a31de219977cf9c64a8bc97581cd4e6619bc0673930f4240b`，WASM為
  `679def61e7848a6d678b6bcc2b4fad7acb37904cdcd0e615afb3405fb5afb634`，Worker為
  `289e4d0036ae7a21d951b1152bcfcd7549ae58f18ef36e00acdde7f9ef88c544`。
- Chrome 150與Firefox 153各五個fixture全部通過。Plain fixture的backward／forward delete各3/3皆回
  `verified-selection-delete`、精確選取待刪unit、revision +1；原先的forward delete timeout沒有復發。
- Multi-paragraph的paragraph／line break各3/3通過；public `DocumentHandle.undo()`各3/3通過。Diagnostic fixed
  Redo持續回`LOK_COMMAND_FAILED`，因此明確不升格。
- Styled fixture最初採format→public Undo反覆驗證；第二、三輪因typed format state未同步而被判成no-op，雖然頁面
  pass且save後原bold／italic仍在，不能拿來滿足「每輪mutation」門檻。該結果保留於Chrome `attempt-02`。
- 修正後改成在同一selection上做三輪明確`off → on`；Chrome與Firefox的bold／italic各6個action全部
  `changed:true`、revision +1，最後ODT保留原格式。
- Line navigation第一次改成每輪search＋reset，但第三次相同reset本身無callback而timeout（Chrome multi
  `attempt-02`）；改成交替Up／Down、Home／End後一次全數3/3通過（`attempt-03`），下一輪卻在第一個End timeout
  並使後續editor action回`BUSY`（`attempt-04`）。因此建立Finding 018並把line navigation移出E1 v1。
- Table fixture不在同Worker重複boundary mutation；直接引用Finding 016已完成的跨瀏覽器四類boundary evidence，
  A6只做table caret與未改內容的save／round-trip。這遵守「boundary拒絕後fresh Worker」，沒有洗掉晚到callback。
- 受控執行環境第一次啟動browser runner時在`free_port()`建socket即被拒；第一次desktop round-trip與after
  preflight也因本機process stream權限回`Operation not permitted`。三次都發生在測試／mutation之前，之後以同一條
  無root命令取得明確授權再跑成功；失敗分別保存在`browser/launch-sandbox-denied.json`、
  `roundtrip/attempt-sandbox-denied.json`與`baseline/preflight-after-sandbox-denied.json`，沒有只留最後pass。
- 10份最終ODT全部通過ZIP CRC、XML、fixture anchor與結構檢查；headless desktop LibreOffice reopen／PDF export
  10/10通過。兩瀏覽器相同fixture的PDF byte size一致。
- `make test-r6-release test-r7-d-static test-r8-d-static test-finding-012-static
  test-finding-016-selection-barrier-static test-e1-a-static`通過；regression machine evidence在
  `findings/evidence/sdk-e1/discovery/regression/summary.json`。
- After preflight為`pass:true`：Core HEAD與六筆既有dirty狀態未變，R5 `writer-review` loader／WASM hash未變。

### 推論

- Character navigation／selection、text commit、雙向delete、兩種break、Undo及bold／italic足以支撐窄版ODT editor
  ABI；selection barrier已可從Finding diagnostic整合到E1 discovery，而不擴大JS輸入surface。
- Full editor contract仍不足：line navigation completion不確定、Redo沒有成功結果、drag／handles與paragraph/list
  無跨瀏覽器barrier。把這些能力留在UI外比依偶發callback或toolbar外觀猜成功更安全。

### 待驗證

- E1-B立spec時凍結capability與typed result shape，特別是verified-selection delete、public Undo及boundary restart。
- Finding 018若未來有產品需求，再做獨立line-position postcondition實驗；不阻擋目前窄版E1-B。
- E1-B完成後，E1-C才重用R7 headed IME／clipboard與crash recovery驗證；本輪沒有新增人工驗收。

### 判定

- E1-A machine summary：`complete:true`、`stoppedEarly:false`、`decision:PARTIAL_GO_TO_E1_B`。
- E1-B可以開始規劃，但只可包含已成立能力；E1-C尚未啟動。

## E1-B窄版Editor Contract完成

### 已觀察

- 新增隔離`e1-editor-v1`產品profile；C ABI只匯出`oxsdk_editor_action()`與
  `oxsdk_editor_get_state()`，Worker以`narrow-editor-v1`及contract version 1雙重gating。八個action固定為字元
  左右移動、雙向delete、paragraph／line break、explicit bold／italic；產品profile沒有discovery symbol、raw
  callback、任意key code或UNO command入口。
- JS editor client驗證action、flags、typed result與revision；FIFO session將文字與mutation串行化。Boundary
  rejection、timeout、crash與outcome unknown不會自動retry；`restart-required`只允許以authority／last saved
  bytes重開fresh Worker，不重播先前mutation。
- Host shell沿用Document SDK的click、文字commit、Undo與save，以及R7 `HostInputAdapter`與E1-A
  `TileScheduler`。單次public click後以bounded typed-state poll等待collapsed selection，不以重送click催促完成。
- 產品artifact hash：loader `45c31f321fa4bcf2e5065c1942e0358b03ab94148732496160ae822541b9511e`、
  WASM `94b38437cce120de4bffb6275d084f1257abb7d6a310cb3cf20594ae72eab6ef`、Worker
  `9696c9ce580b431644cd4f56ea7356647dfd9ab143da6370e521bc2474a35fd7`。
- Chrome 150與Firefox 153各完成27筆操作，結果皆`pass:true`。Chrome輸出ODT為10,918 bytes、SHA-256
  `cf4c297cad94c42178cfe8a284d8fe83c13b31e723e34c27eb8acf4d38f69912`；Firefox為10,912 bytes、
  `37c23c2705e2b53a90f25990996ef324101a167851854c91f94e566494154a23`。
- 兩份ODT均通過ZIP CRC、XML、fixture／新增anchor及desktop LibreOffice 26.2.4.2 reopen／PDF export。
  Chrome PDF為33,804 bytes、SHA-256
  `6be335eb8461951f4c455323ed39107e62075769e28bb7de4bbb1ff16d4b8b43`；Firefox同為33,804 bytes、
  `936f138b7d0a685d81e1459192aab4a575347d42c211983074530f8e381ab2dd`。
- R6 release、R7-D、R8-D、E1-A與E1-B static regression通過。Before／after preflight皆`pass:true`；Core
  HEAD、六筆既有dirty檔案及R5 `writer-review` artifact未變。最終summary在
  `findings/evidence/sdk-e1/editor-contract/summary.json`。

### 失敗嘗試（保留，未覆寫）

- C++第一版include discovery header時，typedef `oxsdk_editor_action`與產品export函式同名而編譯失敗；改以產品
  私有numeric mapping，避免ABI header依賴diagnostic enum。
- 第一次browser runner在受控環境建立本機socket前即被sandbox拒絕，證據保留於
  `browser/launch-sandbox-denied.json`；後續只以同一條無root命令取得執行允許。
- Chrome第一輪因runner仍尋找舊metrics名稱而timeout，加入read-only相容alias後續跑。Attempt-01至04依序暴露：
  boundary後同Worker不可續用、重搜仍可能落在結構邊界、click response只是dispatch而立即read會看到舊
  selection、以及測試對forward-delete設了比contract更窄的exact-text期待。每輪結果均分開保留；最終
  attempt-05通過。
- Desktop validator在sandbox內因dconf runtime目錄唯讀而無法啟動；當次ZIP／XML已通過但暫判STOP。同一validator
  以無root允許重跑後desktop round-trip完成，才產生最終GO summary。

### 推論

- E1-A verified-selection barrier已能安全升格為產品ABI；不需向host開放raw LOK、任意按鍵或command string。
- `click()`回覆是dispatch acknowledgement，不是caret同步barrier；bounded typed-state poll是必要的host端
  completion規則，且不會重複mutation。
- 八個action加既有文字commit、Undo與save已足以進入E1-C。Line navigation、Redo、drag／handles、
  paragraph/list與structural boundary editing繼續縮限，不用UI外觀假裝成立。

### 待驗證

- E1-C重用R7 headed真實Chewing／clipboard，驗證caret／selection互動、composition cancel與exactly-once；自動
  evidence不足時才集中最多一輪人工驗收。
- E1-C補齊crash／restart、stale handle、ODT corpus與長序列；boundary後fresh Worker規則保持。

### 判定

- E1-B machine decision：`complete:true`、`decision:GO_TO_E1_C`。
- 未觸發停止條件、未新增finding；E1-C可開始規劃，但尚未啟動。

## E1-C規劃凍結

### 已觀察

- E1-B產品profile、雙browser shell、ODT round-trip、session no-retry與workspace preflight皆已成立，因此E1-C不需
  先新增ABI或修改Core。
- R7已有Chrome／Firefox Fcitx5 Chewing真composition／cancel／clipboard人工pass；R7 ODT compatibility corpus
  與bounded Worker recovery可直接重用。Cangjie／Pinyin仍未驗證，E1 v1不擴大承諾。
- Finding 014限制Firefox同頁大量Worker generation；Finding 016要求boundary後fresh Worker。兩者已寫入E1-C
  lifecycle與recovery gate，不以反覆restart或retry掩蓋。

### 推論

- E1-C的新增風險集中在「IME／clipboard × caret／selection × save／restart」交錯，而不是重跑每個單一action。
  因此自動矩陣先驗證selection replacement、cancel、stale、crash與no-replay，再跑corpus與人工。
- 五份ODT足以涵蓋plain CJK、style/table/image/comment保存、長文件、review物件與100頁壓力；structural object只
  驗證不被旁側文字編輯破壞，不擴成結構編輯。

### 待驗證

- Chrome／Firefox各三次整合sequence、五份ODT各一次、10個bounded edit/save/reopen session、四種crash barrier
  與兩種boundary restart。
- 自動閘門全過後，Chrome／Firefox各最多一個集中Chewing／clipboard headed run；若取不到trusted evidence，
  明確部分GO，不反覆增加人工操作。

### 規劃產物與狀態

- 建立`specs/SPEC-E1-C-editor-validation.md`與`wasm_sdk_probe/e1/validation-matrix-v1.json`。
- Evidence預定寫入`findings/evidence/sdk-e1/editor-validation/`；本規劃階段尚未建立或宣稱結果。
- 狀態：**規劃完成、尚未授權實作**。實作前另列確切source、build／test命令與產物；任何ABI／Core擴張需另行
  確認。

## E1-C人工輸入頁視覺回饋修正（執行中）

### 已觀察

- 自動C0～C4通過後啟動集中人工驗收；operator回報不論是否啟用輸入法，input sink看起來都無法輸入。當次尚未
  POST任何正式manual evidence，因此沒有成功證據遭覆蓋。
- `HostInputAdapter`對一般文字及composition期間的`beforeinput`刻意`preventDefault()`，讓ODT mutation保持唯一
  文字authority；原人工頁卻沒有顯示commit狀態，也沒有在commit完成後重畫tile。結果是textarea維持空白、左側
  文件仍顯示舊畫面，即使事件已送入adapter，人工觀察仍會判斷成「沒有輸入」。
- 修正只落在host validation UI：新增聚焦外框與input feedback，顯示組字中／提交中／已提交revision／錯誤；
  `commit-end`後清空host sink並串行重畫文件。沒有改動SDK mutation、IME exactly-once規則、產品ABI或Core。
- `make test-e1-c-static`通過：Python 6 tests、Node 57 tests及JS／JSON／Python static checks皆成功；更新後頁面資產已
  複製到`wasm_sdk_probe/dist/`。

### 推論

- 此問題是人工驗收頁的可觀察性缺陷，不是Chewing專屬失敗，也沒有證據顯示`insertText`或composition contract
  失效。以明確commit回饋與重畫補足觀察面，比允許textarea保存一份第二authority安全。

### 待驗證

- operator重新整理同一URL後，先以一般ASCII確認可看到「已提交到ODT（revision …）」及文件重畫，再執行一次
  Chrome與一次Firefox的集中Chewing／clipboard驗收。

## E1-C完成

### 已觀察

- C0 profile／surface inventory通過；沿用同一`e1-editor-v1` artifact：loader
  `45c31f321fa4bcf2e5065c1942e0358b03ab94148732496160ae822541b9511e`、WASM
  `94b38437cce120de4bffb6275d084f1257abb7d6a310cb3cf20594ae72eab6ef`、Worker
  `9696c9ce580b431644cd4f56ea7356647dfd9ab143da6370e521bc2474a35fd7`。
- Chrome 150／Firefox 153的integration 6、recovery 12、corpus 10、lifecycle 20，共48個cases全部通過。48份
  browser輸出皆通過ZIP CRC／XML／anchor；16份required輸出再通過desktop LibreOffice reopen與PDF export。
- Lifecycle各以10個warmup後獨立session量測：Chrome成長29,467,648 bytes（1.80%），Firefox成長53,212,160
  bytes（7.83%），均低於512 MiB及35%門檻，且每頁Worker generation不超過3。
- Chrome／Firefox各完成一個集中Fcitx5 Chewing人工run。兩者的trusted composition、selection replacement、
  Escape cancel零mutation、trusted Ctrl+C／Ctrl+V及Clipboard API皆通過；輸出ODT各含四段required文字一次，取消
  字串為零。
- `python3 tools/validate_e1_c.py --run-regression`最終輸出`automaticPass:true`、`complete:true`、
  `decision:E1_GO_ODT_EDITOR`。R6～R8、E1-A／B回歸與before／after preflight均通過；Core HEAD、六筆既有dirty及
  R5 `writer-review` artifact未變。

### 失敗嘗試與修正（均保留）

- `crash-queued`早期會等待到case timeout：舊generation drain在restart後仍持有processing ownership，阻塞新queue。
  Session改用generation-scoped drain token，且每個await後重驗token／runtime；舊save結果也不能替換新authority。
  遲到成功、遲到失敗、新generation queue與stale save測試全部通過。
- 相同Emscripten 4.0.10輸入的probe object／WASM曾出現非deterministic hash；`-frandom-seed`亦未直接消除。保存各次
  嘗試後，以重現既有object hash的產物恢復凍結artifact。此現象未改變SDK／runtime行為，暫不建立編號finding；若
  未來要求reproducible build再獨立研究。
- Chrome lifecycle第一次未做warmup，功能10/10通過但記憶體基線失真而未過gate；依R7凍結方法加入10次顯式warmup
  後重跑，失敗證據未覆寫。
- 人工頁第一版因input sink刻意`preventDefault()`且commit後未重畫tile，看起來像完全不能輸入。新增明確組字／
  commit／revision回饋與串行重畫後，Chrome／Firefox各一次正式run通過；沒有改成DOM第二文字authority。

### 推論

- E1-B的closed Editor Contract與R7 host input state machine整合後，能在caret／selection、save／restart及故障交錯
  下維持exactly-once與no-replay；不需raw UNO、任意key code、未承諾callback parser或LibreOffice Core修改。
- 執行中兩個產品程式修正都可在既有contract內完成；沒有出現需新增編號finding的可重現SDK／browser／Core邊界
  缺口。

### 剩餘限制

- `E1_GO_ODT_EDITOR`是窄版ODT-first GO，不是完整Writer：line navigation、Redo、drag／handles、paragraph／list、
  structural editing、DOCX、rich clipboard、Cangjie／Pinyin及完整content accessibility仍維持unsupported。

### 判定

- E1-C：**`E1_GO_ODT_EDITOR`**。未觸發部分GO或停止條件，E1里程碑完成。
- 最終machine evidence：`findings/evidence/sdk-e1/editor-validation/summary.json`。
