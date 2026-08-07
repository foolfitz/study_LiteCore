# 016 — forward delete 已改文件，但 SDK 未建立可歸屬的 completion

| | |
|---|---|
| **狀態** | **已修：closed verified-selection barrier跨Chrome／Firefox與desktop round-trip通過；結構邊界拒絕後需fresh Worker** |
| **Bugzilla** | — |
| **發現日** | 2026-08-04 |
| **嚴重度** | 阻斷 |
| **可重現** | 100%（Chrome、Firefox各1/1正式重現） |
| **是否上游** | **否**（2026-08-05原生對照推翻上游假設，詳見「原生對照」一節）／**不可送單** |

## 現象

對collapsed caret送出封閉的forward delete後，文件內容確實少一個字元，但caret位置不變；當時SDK completion
只接受tile／caret／selection callback，沒有任何一種抵達。Document SDK只能在30秒後回`TIMEOUT`，無法安全宣稱
mutation完成或未開始。後續最小實驗證明另有word-count state自然抵達，但舊SDK沒有分類或歸屬它。

## 重現步驟

1. 建立隔離的`e1-editor-discovery` diagnostic profile，不替換R5 `writer-review`。
2. 開啟`plain-grapheme.odt`，在`E1-PLAIN-START`後插入`ABC`。
3. 將caret移到`A`前，送出closed `delete-forward`；只接受documented callback作completion barrier。
4. 等待request結果，逾時後不retry，直接save ODT並檢查內容。

**預期**：一次request只做一次delete，並以可歸屬的documented completion回傳`revision = before + 1`。

**實際**：Chrome 150與Firefox 153都逾時；save後文字為`E1-PLAIN-STARTBCASCII...`，證明`A`已刪除，
但SDK無法分辨「完成但無callback」與「仍在處理」。後續同一diagnostic Worker拒絕新closed action為`BUSY`，
沒有自動重送mutation。

## 證據

- Machine checkpoint：`findings/evidence/sdk-e1/discovery/summary.json`
- Chrome原始操作、事件、畫面與輸出：
  `findings/evidence/sdk-e1/discovery/browser/chrome/plain-grapheme/attempt-05/`
- Firefox原始操作、事件、畫面與輸出：
  `findings/evidence/sdk-e1/discovery/browser/firefox/plain-grapheme/`
- 隔離artifact：loader `7c734343dce4ebb8b893ada0561accd8647c173001c607333593a86585661dca`；
  WASM `bda069ed34233c2ec5cb13b05be396414864f9e3819e47bd6e5ca4a889a930dc`。
- 基線保護：`findings/evidence/sdk-e1/baseline/preflight-after.json`。
- 補救machine decision：`findings/evidence/016/remediation/summary.json`。
- 補救原始操作、輸出ODT、page log與畫面：
  `findings/evidence/016/remediation/browser/chrome/`（初次結果及`attempt-02`～`attempt-05`均保留）。
- 補救前後基線：`findings/evidence/016/remediation/baseline/preflight-before.json`、
  `preflight-after.json`。
- 最終隔離artifact：loader
  `0752ba1462c89478e08eec92c5693ad2f7f7357b3fde9dfa339104a365e48ca3`；WASM
  `d9057273e5e1d6432e46e5907886e52f163fe9a6b1fca2fc326617b323f132da`。
- Scheduler最小實驗總結：`findings/evidence/016/scheduler-wasm/summary.json`。
- Scheduler隔離artifact與基線：`findings/evidence/016/scheduler-wasm/artifact.json`、`baseline/`。
- 最終Chrome／Firefox結果：`findings/evidence/016/scheduler-wasm/browser/chrome/latest.json`、
  `browser/firefox/latest.json`；第一次立即drain與第二次錯誤分類亦保留於Chrome `result.json`、`attempt-02/`。
- Selection barrier總結：`findings/evidence/016/selection-barrier-wasm/summary.json`。
- Selection barrier Chrome／Firefox原始結果：
  `findings/evidence/016/selection-barrier-wasm/browser/chrome/latest.json`、
  `findings/evidence/016/selection-barrier-wasm/browser/firefox/latest.json`。
- 十份瀏覽器輸出以desktop LibreOffice reopen／PDF export的結果：
  `findings/evidence/016/selection-barrier-wasm/roundtrip/summary.json`。

## 分析

### 已觀察

- 同一artifact的backward delete因caret移動而收到`INVALIDATE_VISIBLE_CURSOR`，兩瀏覽器各3/3可完成。
- forward delete刪除caret右方字元時caret幾何不變，兩瀏覽器都沒有當時completion allowlist可接受的callback。
- 兩份save output均通過ODT ZIP CRC與XML parse，且都只刪除一個`A`；不是「mutation根本沒發生」。
- JS沒有raw callback、arbitrary key code、arbitrary UNO或`.uno:*`escape hatch。

### 當時推論（已被2026-08-05 scheduler最小實驗修正）

`postKeyEvent()`為void input surface，現有documented callbacks是畫面／selection狀態通知，不是帶request identity的
mutation acknowledgement。對不改變caret幾何的mutation，它們不足以建立exactly-once completion contract。

### 待驗證

- 上游是否有尚未納入目前LibreOfficeKit header文件的正式command acknowledgement能力。
- 能否新增帶operation identity的上游completion callback，或建立不依賴任意延遲／未承諾payload的semantic readback。
- 若產品縮範圍，是否存在仍具實用性的authoring contract；在此之前不得啟動E1-B假API。

## 文件化fixed-command補救（2026-08-04）

### 方法

- 將四個closed action固定映射為`.uno:Delete`、`.uno:SwBackspace`、`.uno:InsertPara`與
  `.uno:InsertLinebreak`；JS不能傳入command字串，沒有raw UNO／任意`.uno:*`escape hatch。
- 使用`postUnoCommand(..., true)`與文件化`LOK_CALLBACK_UNO_COMMAND_RESULT`作request completion；解析器只讀
  文件化的`commandName`與`success`。
- delete在dispatch前嘗試以文件化`setAccessibilityState()`與`getA11yFocusedParagraph()`取得content、position與
  selection，段落邊界則在零mutation前回`EDITOR_BOUNDARY_UNSUPPORTED`。
- 不用sleep、任意invalidate、未承諾callback欄位或mutation retry；只重連隔離E1 profile，未重建或修改core。

### 已觀察

- 初次補救錯把帶空白的command-result JSON當compact JSON，六次delete皆回`LOK_RESULT_MISMATCH`；原始結果保留於
  Chrome plain fixture根目錄。
- `attempt-02`修正parser後，command result可穩定完成；但同步focused-paragraph snapshot仍是舊值，harness曾將
  delete錯標`changed:false`。保存ODT證明forward delete有落地，不能把該輪`pass:true`視為合格產品契約。
- `attempt-03`加入dispatch前語意檢查後，段落中間與邊界都讀到預設空段落；六次positive delete全被安全拒絕。
- `attempt-04`將a11y啟用延到首次render後，結果不變。
- `attempt-05`再於成功search selection後以文件化API disable／enable重新attach，六次段落中間delete仍全回
  `EDITOR_BOUNDARY_UNSUPPORTED`；六次真正邊界negative則全部正確拒絕且revision不變。
- 同一最終artifact的`insert-paragraph-break`與`insert-line-break`各3/3成功，每次
  `revision = beforeRevision + 1`、`changed:true`、completion為`uno-command-result`。
- Chrome已足以觸發停止條件，因此沒有再消耗Firefox Worker generation或跑完整E1-A矩陣。Final remediation
  summary為`complete:false`、`decision:STOP_OR_RESCOPE`。

### 當時推論（已被後續WASM直接觀察否證）

文件化fixed UNO command解決了「命令完成確認」的一半問題，也證明break可形成closed contract；但目前LOK
`getA11yFocusedParagraph()`是listener cache，不是可在任意caret/search狀態同步查詢的authoritative readback。
因此delete仍無法同時保證「不是段落合併邊界」與「只在安全範圍內準確回報changed」。把command-result一律當成
changed會把邊界no-op或段落合併混在一起，不能升格為SDK承諾。

### 待驗證

- 上游能否提供同步、authoritative的caret／paragraph boundary query，或讓command result帶實際changed／postcondition。
- 若產品縮成只含insert、paragraph break與line break而不含delete，是否仍有足夠價值；這是後續產品方向決策。

## 人工刪除觀察頁（2026-08-04）

- 新增獨立`e1-manual-delete.html`，提供搜尋／collapse caret、Backspace、Delete、paragraph break、line break、
  insert、save與reload按鈕，以及canvas點擊定位。
- 人工delete仍是兩個closed action；host只傳action enum與`manualObservation:true`，不傳key code、UNO command或raw
  callback。Engine固定映射既有Writer command。
- 人工delete結果固定回`changed:null`、`manualVerificationRequired:true`與
  `completion:uno-command-result-manual-observation`；產品revision只作診斷操作排序，不能據此宣稱內容已改。
- 靜態、C++、unit test與HTTP/COOP/COEP資產檢查已通過；本輪環境沒有可連線的內建瀏覽器，互動與語意結果明確標為
  待操作員，不把未執行的人工測試寫成pass。
- 首輪操作員紀錄顯示：沒有active selection時，「游標到選取開頭」其實只左移一字，導致Delete刪掉
  `E1-PLAIN-START`中的`A`；後續可搜尋`E1-PLIN-START`直接支持此判讀。這證明第一版流程有歧義，尚不能據此宣稱
  fixed Delete command本身映射錯誤。
- 第二版改為四個一鍵案例；每次先重載fixture。字元案例固定搜尋`0123456789`、collapse、delete，再同時檢查預期
  字串存在且原字串消失；段落邊界案例清楚標示預期合併方向。自由組合操作移到最後一區。
- 第二版操作員實測時，同一Worker close／open後的第一筆anchor search等候30秒仍沒有result callback而逾時；SDK的
  best-effort cancel因search已列入asynchronous request而不能取消，且`closeDocument()`沒有清除全域
  `gSearchRequestId`，所以下一個fixture的search立即回`BUSY`。原始紀錄保存於
  `findings/evidence/016/manual/operator-2026-08-04-02.log`。
- 第三版不再於案例內close／open同一Worker；每個一鍵案例與「載入原始文件」都以頁面navigation建立全新Worker，
  初始化只open一次再執行案例。若仍收到`TIMEOUT`／`BUSY`，頁面會把Worker標為失效、停用自由操作，只保留可建立
  fresh Worker的按鈕。
- 第三版排除timeout後，操作員回報Delete與Backspace都失敗；Backspace原始回應明確顯示move-right完成時
  `selection.collapsed:false`且整個`0123456789`矩形仍在，後續delete才清空selection，而預期短字串與原字串皆找
  不到。已觀察事實是方向鍵completion沒有證明selection收斂；整個搜尋選取遭刪除是與readback一致的推論。
- 第四版一鍵案例不再用方向鍵collapse。Host解析文件化search result rectangle，以既有public click點擊矩形開頭或
  結尾，接著用`getSelection()`與typed editor state雙重確認selection text為空且`collapsed:true`；任一不成立就回
  `CARET_NOT_COLLAPSED`並在delete dispatch前停止。段落邊界案例沿用相同fail-closed定位。
- 第四版Backspace實測中，public click後`getSelection()`仍回完整`0123456789`且typed state仍
  `collapsed:false`；`CARET_NOT_COLLAPSED`在mutation前正確攔截，沒有再刪除整段。原始紀錄保存於
  `operator-2026-08-05-04.log`。
- 第五版採用已存在的closed diagnostic `selection-reset-unstable`，也就是host只能傳固定method enum與座標，沒有
  raw UNO／raw callback／任意key code。過往E1 Chrome與Firefox plain discovery都曾在相同helper完成後繼續insert與
  backward delete，因此它是最後一種具既有跨瀏覽器成功證據的定位候選；r5仍保留公開selection text及typed
  collapsed雙重前置條件。
- 第五版reset完成後，第一個公開`getSelection()`回
  `LOK_ERROR: Flavor text/plain;charset=utf-16 is not supported`；程式碼對照確認project要求UTF-8，而LOK內部改查
  UTF-16 transferable flavor。此時尚未執行typed state readback或delete，沒有mutation。空selection readback契約
  另立Finding 017，人工r1～r5到此停止。
- 操作引導與靜態證據：`findings/evidence/016/manual/README.md`、`static-smoke.json`。

## 原生對照與根因改判（2026-08-05）

**這一節推翻了本文件先前「LibreOfficeKit公開能力缺口」的定位。** 前面各節的觀察本身沒有錯，錯的是歸因。

### 為什麼要做原生對照

在此之前所有證據都來自headless `--disable-gui` WASM profile。`findings/README.md`送單檢查第一條要求「在上游預設
組態上重現過」，否則自訂旗標造成的問題送出去只會浪費triager時間。因此建置原生26.8作對照。

建置刻意停用qt5／qt6（`ENABLE_QT5 0`、`ENABLE_QT6 0`已核對），確保worktree裡`vcl/qt5/QtFrame.cxx`的既存本地修改
不會被編入；其餘三個本地修改都是emscripten專屬目標，`unxgcc.mk`的hunk整段包在
`$(if $(filter EMSCRIPTEN,$(OS)),...)`內，原生建置不生效。**對照組沒有帶任何我方patch。** 未使用`--disable-gui`，
改在執行期以`SAL_USE_VCLPLUGIN=svp`跑，貼近Collabora Online實際跑法；否則負面結果會卡在「是否為`--disable-gui`
限制」而無法定論。

### 已觀察

探針先`.uno:SelectAll`讀全文長度、刪除後再讀一次比對，確認mutation確實落地（120→119字元，`valid:true`）；
caret移動產生`INVALIDATE_VISIBLE_CURSOR`與`TEXT_SELECTION`，證明callback通道在受測步驟前是活的。**若delete沒有
執行，「沒有callback」會是假陽性**，探針會標記`DISCARD`；本輪非此情形。

- 原生發出**185個**`LOK_CALLBACK_STATE_CHANGED`，其中含內容衍生訊號：

  ```text
  .uno:StateWordCount=20 words, 94 characters    ← delete 前
  .uno:StateWordCount=20 words, 93 characters    ← delete 後
  ```

- `.uno:ModifiedStatus`在delete當下由`false`轉`true`；隨後`.uno:Undo=enabled`、`.uno:DocumentRepair=true`。
- **延遲抵達**：delete於2268ms送出，`UNO_COMMAND_RESULT`於2269ms返回，而大量`STATE_CHANGED`直到**2870ms**才到，
  比命令返回晚約600ms。這些是idle／scheduler驅動的回呼。
- 對照我方舊WASM typed state：整場session `format`都是`{bold:null, italic:null}`。原生明確發出`.uno:Bold=false`；
  當時把這解讀成整條延遲串流未抵達，後續最小實驗證明此負面訊號不足以支持該結論。
- `probe_engine.cpp`中`runLoop`、`unipoll`、`Yield`、`Scheduler`、`ProcessEventsToIdle`、`emscripten_sleep`
  **一個都沒有**。這只能證明probe沒有直接驅動它們，不能證明Core內部執行緒不會自然處理scheduler；後續實驗
  正是用直接觀察修正此歸因。
- COOL參考實作（唯讀checkout `cool-26-04`，`distro/collabora/co-26.04`）：
  - `kit/SetupKitEnvironment.hpp:66` 設定 `options = "unipoll"`
  - `kit/Kit.cpp:3561` 呼叫 `loKit->runLoop(pollCallback, wakeCallback, mainKit.get())`
  - `Kit.hpp`註解直述設計：「Handle the poll from the unipoll callback」
  - 名稱差異：COOL設`SAL_KIT_OPTIONS`，但26.8 core讀的是`SAL_LOK_OPTIONS`（`desktop/source/lib/init.cxx:8083`）；
    實作時以core讀取的名字為準。

### 推論

當時依原生／WASM表面差異，推論是我方執行模型缺少LOK預期的主迴圈，導致延遲型callback未被flush。後續
scheduler最小實驗直接在同一WASM profile觀察到延遲型`STATE_CHANGED`自然抵達，因此此推論**不成立**；保留本段
是為了呈現歸因如何被可區分實驗推翻。

`.uno:StateWordCount`帶字元數，隨文件內容逐次變動，是本finding一直在找的「文件是否真的改變」權威判準候選。

### 待驗證

1. 在WASM引擎中讓LO scheduler實際執行一次，觀察`STATE_CHANGED`是否出現。此項已由下節完成，結果是否證。
2. 若成立，評估採用unipoll／`runLoop`控制反轉模型的規模：`runLoop`不會返回，會接管Worker執行緒，命令處理需
   移入`pollCallback`。影響request序列化、`BUSY`語意與close／teardown路徑。COOL `kit/Kit.cpp`是同一monorepo內
   可參照的實作。
3. 確認`.uno:StateWordCount`是否足以承擔per-operation的changed判定，或需搭配其他訊號。

### 未解問題（不用於支持上述結論）

原生在drain 1500ms後**同樣**完全沒有發出`INVALIDATE_TILES`。COOL顯然依賴它重繪，因此這裡仍有未理解之處。本輪
結論不建立在tile invalidation上，而是建立在STATE_CHANGED串流的有無對比。

### 證據

- `findings/evidence/016/native-26-8/callbacks.jsonl`（完整callback串流，含時間戳）
- `findings/evidence/016/native-26-8/sal.log`
- `findings/evidence/016/native-26-8/finding_016_native_lok.cpp`（探針原始碼，含DISCARD防呆）
- `findings/evidence/016/native-26-8/artifact.json`（建置組態、對照乾淨度核對、hash）
- 重跑：`wasm_sdk_probe/tools/run_finding_016_native.sh`

### 對送單的影響

**不可送Bugzilla。** 先前若依「LibreOfficeKit公開能力缺口」送出，會是一張站不住腳的單。原生對照的成本
（一次隔夜建置）遠低於送錯單對後續回報可信度的損害。

## Scheduler最小實驗與第二次根因改判（2026-08-05）

### 實驗邊界

- 使用Core已存在且由LOK單元測試使用的`unit_lok_process_events_to_idle()`；符號已在現有WASM `libvcllo.a`與
  `soffice.js.linkdeps`中，不修改、不重建Core。
- 新增獨立`finding-016-scheduler` diagnostic profile；正常E1與R5 `writer-review`沒有
  `finding-016-scheduler-probe` capability。
- 只將`LOK_CALLBACK_STATE_CHANGED`收斂成typed計數，並在隔離實驗內辨識固定
  `.uno:StateWordCount=N words, M characters`；raw payload不進JS，也不把此parser升格為產品completion契約。
- 同一Worker只做一次forward delete，沒有retry；先保存immediate state，等待1000 ms，再呼叫一次drain，因而能區分
  「自然抵達」與「只有drain後抵達」。

### 已觀察

- Chrome `150.0.7871.128`與Firefox `153.0.1`結果一致：delete後immediate
  `wordCountUpdateCount=0`；等待1000 ms後、**進入drain前**已變成`1`，內容為`20 words / 93 characters`。
- 兩邊drain的`stateChangedCount`與`wordCountUpdateCount`增量都是`0`。顯式drain沒有恢復任何callback，因為目標
  callback早已由既有執行模型自然送達。
- 兩邊都精確由`0123456789`變為`123456789`，save ODT通過ZIP CRC；沒有raw callback、任意UNO、任意keycode或
  mutation retry。
- Chrome第一次失敗嘗試在timer到期前立即drain，只見非word-count state；第二次已看見自然抵達的93字元，卻因
  classifier只比較drain前後而誤判失敗。兩次原始結果均保留，最終分類沒有覆寫失敗歷程。
- 實驗summary為`pass:true`，兩瀏覽器decision皆為
  `WORD_COUNT_CALLBACK_DELIVERED_WITHOUT_DRAIN`，`schedulerHypothesisSupported:false`。
- Core HEAD仍為`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，前後dirty清單一致。

### 推論

- 「WASM缺LOK scheduler／main-loop驅動」已被直接證據否證，不應導入`runLoop`控制反轉來修這個finding。
- 舊probe只把Bold／Italic轉成typed editor state，且既有completion只等tile／caret／selection；因此
  `StateWordCount`即使抵達也不會完成delete request。舊log的`sourceSequence`不變，不能再解讀為底層callback未抵達。
- 目前最窄的問題是：SDK尚未把延遲型document state與單一、序列化的mutation request安全關聯；這是我方
  callback分類／completion contract缺口，不是Core沒有發訊號。

### 待驗證

1. `.uno:StateWordCount`的特定payload與語言格式是否是足以承諾的穩定公開契約；在確認前只能作diagnostic evidence，
   不得用它假裝產品completion。
2. 若可採用，建立closed、單mutation-in-flight的typed completion barrier，驗證delete／backspace、no-op、段落邊界、
   stale、timeout與Worker recovery，且不能靠任意state callback或sleep宣稱成功。
3. 若payload不具承諾，改找文件化同步postcondition或縮小delete capability；E1-B／C在此之前仍不啟動。

## Verified-selection barrier收斂（2026-08-05）

### 方法

- 建立隔離`finding-016-selection-barrier` profile；host仍只送closed `delete-forward`／`delete-backward`，不接受
  key code、UNO command或callback payload。
- SDK先用固定方向形成一個unit selection，等文件化typed selection callback後，在engine command loop以public
  selection readback確認單一、有效UTF-8且非結構字元的內容；只有驗證成功才送固定內部Delete／Backspace。
- 成功completion必須同時具備同一transaction serial、成功command result、新的collapsed typed selection與public
  none readback；revision只增加1。250 ms deadline只能拒絕，不能宣稱mutation成功。
- 段首、段尾與table cell邊界若沒有可驗證文字unit，回`EDITOR_BOUNDARY_UNSUPPORTED`且不dispatch mutation。
  因晚到selection callback可能污染同一Worker的下一筆狀態，邊界拒絕後明定由host建立fresh Worker。

### 已觀察

- Chrome 150與Firefox 153的ASCII、中文、emoji與combining grapheme前後向刪除，各自24/24通過；每次都精確選中
  預期文字、只改一次revision，public Undo再增加1並完整還原。兩瀏覽器合計48/48。
- 每個browser四個邊界案例皆安全拒絕、revision delta為0且文件內容不變；合計8/8。
- 每個browser保存五份ODT，全部通過ZIP CRC、XML與anchor檢查；十份再由desktop LibreOffice 26.2.4.2
  reopen並export PDF，10/10通過。
- Machine decision為`SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART`；沒有raw callback、任意UNO、任意key、
  `StateWordCount` completion或automatic retry。
- Core HEAD仍為`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`；只重連隔離probe，未修改或重建Core，R5
  `writer-review`未被替換。

### 推論

- 原始Finding 016是SDK沒有把「待刪除unit的selection事實」與後續command acknowledgement組成單一transaction；
  不需要解析`StateWordCount`，也不需要LOK scheduler控制反轉。
- 這個barrier足以解除Finding 016對E1-A的停止條件，但目前仍是隔離diagnostic contract；E1-A其餘Firefox
  fixtures、format／list、完整round-trip與recovery矩陣尚未補齊，不能因此直接宣告E1-A GO。

### 待驗證

- E1-A恢復A6矩陣後，將成立的selection barrier縮成產品capability，並在UI明示結構邊界unsupported及fresh Worker
  recovery；不得把邊界拒絕偽裝成成功。
- 補完先前因停止條件省略的Firefox fixtures與全套E1 round-trip，才依spec判定`GO_TO_E1_B`或
  `PARTIAL_GO_TO_E1_B`。

## 影響與判定

原始`postKeyEvent()`與前五輪fixed-command／a11y嘗試仍是有效失敗證據；scheduler缺口也已排除。最終
verified-selection barrier在兩瀏覽器建立可歸屬、exactly-once且fail-closed的delete completion，因此Finding 016
**解除阻斷**。結構邊界仍是明列限制：拒絕後必須fresh Worker。E1-A恢復剩餘矩陣，但在完成A6前不提前宣告GO。
仍禁止sleep、任意state／invalidate、把command result一律當changed、raw UNO或自動retry補洞。

## 環境

- Core：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- Chrome：`150.0.7871.128`
- Firefox：`153.0.1`；geckodriver `0.37.0`
- Emscripten：專案固定4.0.10
- Desktop round-trip工具：LibreOffice `26.2.4.2`

## 時間軸

- 2026-08-04：Chrome重現，保存mutation已落地但request timeout證據。
- 2026-08-04：Firefox以同artifact重現；E1-A依規格提早停止並建立本finding。
- 2026-08-04：完成文件化fixed-command補救；break 3/3成立，delete在五輪漸進實驗後仍缺可靠同步boundary
  readback，machine decision維持`STOP_OR_RESCOPE`。
- 2026-08-04：加入Finding 016人工刪除觀察頁；自動靜態檢查通過，互動結果等待操作員留痕，不改變停止判定。
- 2026-08-04：首輪人工流程因caret定位歧義刪錯`PLAIN`中的`A`；保存原始log並改成自動重載／定位／驗證的一鍵案例。
- 2026-08-04：第二輪一鍵案例命中同Worker重開後search timeout，下一輪因殘留search回`BUSY`；保存原始log，第三版
  改成每個案例使用全新頁面／Worker，等待操作員重驗。
- 2026-08-05：第三輪證明方向鍵callback completion不等於selection已collapsed；保存整段選取被刪的原始log，第四版
  改用search rectangle click加mutation前雙重selection readback，等待操作員重驗。
- 2026-08-05：第四輪證明public click不會解除search selection，但fail-closed前置條件成功阻止mutation；第五版改用
  既有closed diagnostic selection reset作最後定位候選，若仍失敗即停止人工流程迭代。
- 2026-08-05：第五輪在selection reset後命中public getSelection空selection／flavor邊界；建立Finding 017與同事交接
  紀錄，人工流程正式停止，先修SDK readback才可重驗。
- 2026-08-05：Finding 017修正完成並經Chrome／Firefox實測，空selection readback不再阻斷；同一份log再次證實本
  finding的completion缺口仍在（`sourceSequence`跨mutation不變）。
- 2026-08-05：a11y閘門探針否定。`LOK_CALLBACK_A11Y_FOCUS_CHANGED`完全未抵達（`observed:false`、`changeCount:0`、
  `unparsedCount:0`）。同時查明`SetLOKAccessibilityState()`有兩處靜默early return
  （`sfx2/source/view/viewsh.cxx:3486`的`!pWindow`與`:3492`的`!xAccessible.is()`），且
  `getA11yFocusedParagraph()`只序列化快取成員——**「listener沒掛上」與「段落真的是空的」在輸出上不可分**，
  這正是attempt-03～05徒勞的原因。
- 2026-08-05：建置原生26.8作上游對照（對照組不含任何我方patch）。原生發出185個`STATE_CHANGED`，含
  `.uno:StateWordCount` 94→93字元，且延遲於命令返回後約600ms抵達；我方WASM引擎從不讓出給scheduler。
  比對COOL參考實作後，當時將根因改判為我方執行模型缺LOK主迴圈；此歸因再由下一筆直接實驗修正。
- 2026-08-05：隔離WASM scheduler最小實驗在Chrome／Firefox皆觀察到word-count callback於drain前自然抵達，
  drain增量為0，否證主迴圈缺口。根因再改判為SDK callback分類／completion歸屬缺口；Finding仍阻斷E1，但不需
  `runLoop`重構且仍不可送上游。
- 2026-08-05：verified-selection barrier在Chrome／Firefox各24/24正向案例及4/4邊界案例通過，十份ODT再通過
  desktop LibreOffice reopen／PDF export；Finding 016解除阻斷，邊界拒絕後需fresh Worker。
