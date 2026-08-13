# DEVLOG 2026-08-04：WASM SDK E1

## 里程碑定位

- E1命名為ODT-first Editor主線，不改動既有R9 Automation與R10深層減量編號。
- 本日只完成規劃與唯讀inventory；沒有build、browser run、ABI修改或LibreOffice core修改。
- 規格入口：`specs/SPEC-E1-000-overview.md`；discovery checkpoint：
  `specs/SPEC-E1-A-editing-discovery.md`。

## 已觀察

- 現有SDK可click、insert text、search／selection text、replace non-empty selection、Undo與save ODT；沒有公開
  caret geometry、任意selection geometry、keyboard、delete、newline、Redo與format operation。
- C ABI v1.1的capability bits也沒有上述能力；`replaceSelection()`拒絕空字串，不能當成delete。
- probe engine內部已有legacy raw key入口，但Document SDK未暴露。E1不會把它直接升格；候選只能是closed action
  到固定LOK key event的內部映射。
- LibreOfficeKit文件化visible-cursor與text-selection callback payload，並提供postKeyEvent／postMouseEvent；
  `setTextSelection()`位於unstable API區段，需由A做風險分類。
- 目前sdk-worker收到raw LOK event後，只把tile／visible-cursor粗略轉成`document-invalidated`；應用沒有raw payload，
  也沒有typed editor state。
- R7 input decision為`PARTIAL_GO`且Chrome／Firefox Chewing pass；R8為`PARTIAL_GO_LOCAL_DELIVERY`。E1應沿用
  這些evidence，不要求操作員重做既有IME矩陣。
- core HEAD仍為`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，五筆tracked dirty與一筆untracked研究文件保持原狀。

## 推論

- caret／selection visual state可能可由文件化LOK callback正規化，但callback沒有SDK request ID；如何建立action
  completion barrier是E1-A最重要未知數。
- 方向鍵與delete底層已有LOK輸入surface，不代表能直接形成exactly-once產品API；必須先證明callback／revision／
  semantic readback可以收斂。
- 最低格式可沿用R3固定Undo／comment類似的closed operation模式，但若只能toggle且無法查目標state，產品契約
  可能必須縮小，不能由toolbar外觀猜測。

## 待驗證

- visible cursor old rectangle與new JSON payload在目前Chrome／Firefox artifact的實際variant與順序。
- `setTextSelection()` unstable surface在WASM、縮放、跨行／跨段與兩browser是否足以包成版本化相容層。
- key／mouse void call是否有可靠completion barrier，尤其delete、newline、Home／End與Shift selection。
- Undo／Redo空history、timeout after dispatch、Worker crash outcome與ODT save／desktop round-trip。
- bold／italic／heading／list是否有可設定而非模糊toggle的closed語意與postcondition。

## 規劃產物

- `specs/SPEC-E1-000-overview.md`
- `specs/SPEC-E1-A-editing-discovery.md`
- `wasm_sdk_probe/e1/discovery-matrix-v1.json`
- roadmap與probe README入口更新

## E1-A執行（同日）

### 已觀察

- 建立5份deterministic ODT fixture、closed action diagnostic ABI、typed editor state、Worker／client adapter、
  browser runner及decision validator；只連結隔離的`e1-editor-discovery`，沒有修改LibreOffice core或R5 artifact。
- 第一次Chrome smoke顯示void `postKeyEvent()`回傳不能當completion；改成等待特定documented caret／selection callback。
- 搜尋選到字串末端後再向右是合法no-op，沒有callback；這輪timeout完整保留，之後改由closed selection reset定位，
  沒有加sleep。
- backward delete改變caret，因此Chrome／Firefox各3/3收到visible-cursor callback且revision只加1。
- forward delete不改caret：Chrome／Firefox都先實際刪除`A`，但30秒內無tile／caret／selection callback；保存ODT
  皆為`E1-PLAIN-STARTBCASCII...`，ZIP CRC與XML parse正常。
- timeout後不retry；同diagnostic Worker拒絕後續action為`BUSY`。Machine validator將此分類為
  `FORWARD_DELETE_MUTATION_OUTCOME_UNKNOWN`。
- Chrome附帶觀察：累積line-up到邊界會無callback；mouse drag沒有selection completion；部分paragraph／list command
  沒有UNO command result。這些不是主要停止原因，也沒有用dispatch return假報成功。

### 失敗嘗試保留

- `chrome/plain-grapheme`根目錄與`attempt-02`～`attempt-05`分別保留paint／selection／stale artifact／mutation
  barrier演進；runner修正後不再覆寫既有attempt。
- `attempt-04`在長時間link尚未真正結束時啟動，manifest記錄舊WASM hash；`attempt-05`才是正式新artifact結果。
- Chrome multi／styled的boundary與selection／format timeout、Firefox plain正式重現、所有page log／PNG／ODT均保留在
  `findings/evidence/sdk-e1/discovery/browser/`。

### 推論

- LibreOfficeKit的documented caret／selection callback是狀態通知，不是帶request identity的mutation ack；對caret
  幾何不變的mutation，現有public surface不足以建立exactly-once completion barrier。
- 單靠save後readback只能事後證明mutation發生，不能讓原request安全區分完成、延遲或重複；因此不適合升格產品ABI。

### 待驗證

- 上游是否能提供帶operation identity的completion callback，或是否存在已文件化但未納入目前inventory的ack surface。
- 若不做上游能力，是否要另立大幅縮小且仍具實用價值的authoring scope。這是產品方向決策，不在本輪自動假設。

### 判定

- `findings/evidence/sdk-e1/discovery/summary.json`：`complete:true`、`stoppedEarly:true`、
  `decision:STOP_OR_RESCOPE`；Chrome／Firefox stop evidence皆pass。
- 建立Finding 016；依spec不跑Firefox其餘4 fixture、不做完整round-trip、不啟動E1-B／C。
- 4項E1 Python測試、14項JS測試、ABI／Emscripten編譯、R6 release、R7／R8靜態回歸全通過。
- after preflight確認core HEAD／dirty現場與R5 hashes完全不變。本階段不需人工驗收。

## Finding 016補救研究（同日）

### 已觀察

- 唯讀inventory確認本地26.8與上游候選API仍沒有`postKeyEvent()` request identity；Writer另有四個固定command，
  `postUnoCommand(..., true)`可要求文件化`LOK_CALLBACK_UNO_COMMAND_RESULT`。
- 建立只供E1隔離profile使用的fixed-command路徑與validator；JS仍只能傳closed action enum，SDK Worker未新增raw
  callback或command escape hatch。
- 初輪parser未容忍command-result JSON空白，誤回`LOK_RESULT_MISMATCH`；修正後command result可穩定歸屬request。
- 第二輪證明同步a11y snapshot會落後mutation；雖然頁面一度`pass:true`，ODT與`changed:false`互相矛盾，因此保留
  證據但不採信為成功。
- 第三輪把focused-paragraph snapshot移到delete dispatch前並加入typed boundary拒絕；段落中間與真正邊界都讀到
  預設空段落。
- 第四輪把a11y enable延到首次render後，結果不變。
- 第五輪在成功search selection後用文件化API disable／enable重新attach，六次positive delete仍全回
  `EDITOR_BOUNDARY_UNSUPPORTED`；六次boundary negative全數安全拒絕且零revision。
- 同一最終artifact的paragraph break與line break各3/3通過，completion為`uno-command-result`，revision每次加1。
- `test-e1-a-static`通過6項Python與14項Node測試，Emscripten物件編譯及隔離profile link成功；補救前後preflight
  均pass，core與R5 artifact未變。

### 推論

- Fixed UNO command result可解決command completion，但不能單獨證明delete實際changed或區分段落邊界。
- `getA11yFocusedParagraph()`讀的是listener cache；目前公開surface無法保證在search／caret操作後提供同步、
  authoritative的段落內容與位置。用它當delete前置條件會安全地多拒絕，卻無法交付基本delete。
- 這不是用更多browser repetition可區分的現象；Chrome已在最後兩種attach時序得到相同結果，繼續跑Firefox只會消耗
  Finding 014的Worker generation預算。

### 待驗證

- 上游是否願意提供帶actual changed／postcondition的command acknowledgement，或同步caret／paragraph boundary query。
- 是否另立不含delete、只含insert與break的更窄產品scope；這需要產品方向拍板，不能由discovery自行宣稱GO。

### 判定

- `findings/evidence/016/remediation/summary.json`為`STOP_OR_RESCOPE`；Finding 016補救未成立。
- 依E1-A停止條件，不跑Firefox補救矩陣、不跑完整E1-A、不啟動E1-B／C，也不以sleep、任意invalidate、raw UNO或
  一律`changed:true`繞過。
- 最終隔離loader hash為`0752ba1462c89478e08eec92c5693ad2f7f7357b3fde9dfa339104a365e48ca3`，WASM hash為
  `d9057273e5e1d6432e46e5907886e52f163fe9a6b1fca2fc326617b323f132da`。

## Finding 016人工觀察頁（同日）

### 已觀察

- 建立獨立人工頁，按鈕涵蓋Backspace、Delete、paragraph／line break、insert、save與reload；搜尋後可將caret
  collapse到選取開頭／結尾，也可直接點canvas定位。
- 人工delete沒有新增action ID或Worker operation，沿用兩個closed delete action與嚴格布林
  `manualObservation`；client拒絕把此旗標套到非delete action或非布林值。
- Engine只在人工旗標成立時略過不可靠的focused-paragraph boundary precondition，仍等待固定command的文件化result；
  回應為`changed:null`與`manualVerificationRequired:true`，不宣稱mutation語意成立。
- Python 6/6、Node 15/15、Emscripten C++、JS syntax與HTTP資產檢查通過；HTML、app與manifest均為HTTP 200且帶
  COOP／COEP header。
- 內建瀏覽器連線清單為空，因此沒有偽造click smoke pass；interactive狀態保留為`pending-operator`。
- 首輪操作員先點canvas，再在沒有selection時按「游標到選取開頭」；該closed move只左移一字，後續Delete刪掉
  `E1-PLAIN-START`的`A`。成功搜尋`E1-PLIN-START`證實實際mutation；此輪分類為manual flow defect，而非直接判定
  fixed command mapping錯誤。
- 人工頁r2把字元delete/backspace改成一鍵自動重載、搜尋`0123456789`、collapse、dispatch與雙重search postcheck；
  只有「預期字串存在且原字串消失」才顯示綠色通過。段首／段尾也改為一鍵案例，自由測試移到最後。
- r2操作員實測發現，一鍵案例在同一Worker close／open後，第一筆search沒有收到result callback，30秒後回
  `TIMEOUT`；下一次案例雖再載入新document handle，search仍因上一筆全域request狀態未清而回`BUSY`。原始log
  保存為`findings/evidence/016/manual/operator-2026-08-04-02.log`，沒有只保留修正後結果。
- 唯讀程式碼對照確認：search request只會在`LOK_CALLBACK_SEARCH_RESULT_SELECTION`／`SEARCH_NOT_FOUND`時清除；
  timeout送出的best-effort cancel不能取消已列入asynchronous set的search，而`closeDocument()`也不清
  `gSearchRequestId`。這解釋後續`BUSY`；至於同Worker重開為何漏掉第一個search callback，仍標為待驗證，未臆測為
  已定位的core root cause。
- 人工頁r3將每個一鍵案例與reload改為頁面navigation，確保全新Worker；新頁初始化只open一次再自動跑指定案例，
  不再走同Worker close／open。收到`TIMEOUT`／`BUSY`時標記recovery required並停用會沿用該Worker的自由操作。
- r3靜態回歸Python 6/6、Node 15/15、JS syntax、C++ header syntax與Python compile全通過；HTTP HTML／app／manifest
  均為200，COOP／COEP header正確，served檔案與source／dist hash一致。沒有重建WASM或LibreOffice core。

### 推論

- 此頁可回答「人眼看到的delete、段落合併與Unicode行為是否合理」，但不能補足SDK自動判斷changed／boundary的能力。
- 若人工行為穩定，可用來準備上游最小重現或評估暫時縮小產品scope；不能單獨把E1轉為GO。
- r2的timeout與同Worker document lifecycle高度相關，fresh Worker隔離是人工診斷頁的保守修復；在尚未有第二份可
  重現證據前，不把它另立新finding或宣稱已找到LibreOffice core根因。

### 產物

- URL：`http://127.0.0.1:8765/e1-manual-delete.html`
- Evidence：`findings/evidence/016/manual/`
- r3人工互動仍待操作員；目前只宣稱流程與靜態資產完成，不把未執行的Delete／Backspace語意寫成pass。
- 人工頁隔離artifact：loader
  `a733b8f89eebaa53685056c447cf76151f5a86f455ff1d9dd0c725ff20f8e87d`；WASM
  `1c8b79fd5c9968dd362a43e4e1e032fe07806f72c34c1f5b041c8af00d6c1e78`。
