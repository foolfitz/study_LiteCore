# Collabora Calc 的輸入、雙擊、格式與本樹自動儲存差異

## 結論

Collabora 的「選格後直接打字」和「雙擊編輯」是兩種不同狀態。**直接打字是輸入新內容；雙擊是修改既有內容。**不只空白格能直接輸入；一般非空白格直接打字也會取代原內容。雙擊／第一次 F2 會先保留原內容，進入格內文字編輯。

B／I／U 也有兩個作用範圍：**只選 cell 時套整格／所選範圍；格內編輯並選取文字時，套選取的文字。**按鈕送的命令相同，核心依目前編輯 context 分派到不同 handler。

我們目前已支援只選 cell 後套整格 B／I／U；雙擊 textarea 的文字選取**尚未接成部分文字格式**，此時仍是整格格式。直接選格打字也尚未接線。目前 Calc **只有手動儲存，尚未對齊 Writer 的自動儲存**。以下把原始碼事實與實測分開記錄。

## 參考版本與方法

本機唯讀來源：`/home/jiajun/LibreOffice/study_LiteCore/cool-26-04`，HEAD **c64a7343a5c6295623619c80aa7857c4e00e1ddd**；既有研究記載此 worktree 來源為 `distro/collabora/co-26.04`。另有 `/home/jiajun/LibreOffice/collabora_online`。本報告針對這份本機 snapshot，沒有宣稱它就是使用者當前部署或最新 upstream。

只讀程式與既有上游測試；沒有啟動 Collabora 的實例。下列 Collabora 操作語意是**原始碼推論**；我們的全白問題另有實際 Chrome／Firefox 證據。只借鑑機制，沒有移植 Collabora 程式碼。

## 選格後打字為何與雙擊不同

| 操作 | 核心路徑／狀態 | 一般文字 cell 的語意 |
| --- | --- | --- |
| 單擊、方向鍵移到某格 | 選格；尚未開啟格內 EditView | 可對整格套格式、開始新的輸入 |
| 選格後直接打字 | `ScInputHandler::KeyInput` 或延伸文字的 `InputCommand` → `DataChanging` → `StartTable`；新輸入後成為 `SC_INPUT_TYPE` | 第一個字觸發新的輸入，既有文字被清掉，隨後插入新字；空白格看不出覆寫的差別 |
| 雙擊 | mouse 帶 `clickCount=2` → `ScGridWindow` → `SetInputMode(SC_INPUT_TABLE)` | 以現有內容建立 EditEngine，將文字游標放到雙擊位置，讓使用者修改／選取文字 |
| 第一次 F2 | `StartOrToggleEditMode` → `SC_INPUT_TABLE` | 進入編輯；再次 F2 可在 TABLE／TYPE 間切換，不能把「每次 F2」都簡化為雙擊 |
| 上方輸入列 | `SC_INPUT_TOP`，與 table EditEngine／selection 同步 | 顯示原始文字／公式，保留編輯草稿 |

直接的依據：

- [inputhdl.cxx:2675](../cool-26-04/engine/sc/source/ui/app/inputhdl.cxx#L2675) 在按鍵路徑明確以 `cTyped != 0` 區分 overtyping 與 editing。`StartTable` 取回原 cell 後，`KeyInput` 在新啟動且舊模式為 NONE 時清空 EditEngine，再送鍵（[同檔 :4008](../cool-26-04/engine/sc/source/ui/app/inputhdl.cxx#L4008)）；不是「只有空白格特殊允許打字」。百分比等數值格式另有分支，表格只概括一般文字 cell。
- 延伸文字／IME 的 [InputCommand :4238](../cool-26-04/engine/sc/source/ui/app/inputhdl.cxx#L4238) 則走 `DataChanging(0,true)`，同樣在新建立且舊模式為 NONE 時清空 table／top EditEngine，再轉交 Command；瀏覽器的 `textinput` 不能一律說成 KeyInput。
- [DataChanging／DataChanged :2794](../cool-26-04/engine/sc/source/ui/app/inputhdl.cxx#L2794) 與 [SetMode／StartOrToggleEditMode :3050](../cool-26-04/engine/sc/source/ui/app/inputhdl.cxx#L3050) 建立 TYPE／TABLE／TOP 的區分。格內編輯時方向鍵能交給文字 EditEngine；公式參照模式另有選格規則，不能只用「有沒有游標」分類。
- [gridwin.cxx:2659](../cool-26-04/engine/sc/source/ui/view/gridwin.cxx#L2659) 的雙擊分支及 [:2720](../cool-26-04/engine/sc/source/ui/view/gridwin.cxx#L2720) 的 SetInputMode／MouseButtonDown，表明它是在修改既有內容並定位文字游標。
- 瀏覽器端 [MouseControl.ts:102](../cool-26-04/browser/src/canvas/sections/MouseControl.ts#L102) 帶出 click count；[TextInput.js:1220](../cool-26-04/browser/src/layer/marker/TextInput.js#L1220) 將文字送為 `textinput`，[ChildSession.cpp:2068](../cool-26-04/kit/ChildSession.cpp#L2068) 送進核心的延伸文字輸入；不是由瀏覽器把空白 cell 改成 HTML input。

## 同一顆格式按鈕，兩種核心 context

[Control.NotebookbarCalc.js:566](../cool-26-04/browser/src/control/Control.NotebookbarCalc.js#L566) 與 [Control.TopToolbar.js:162](../cool-26-04/browser/src/control/Control.TopToolbar.js#L162) 都送 `.uno:Bold`、`.uno:Italic`、`.uno:Underline`。

一般選格時，[ScFormatShell::ExecuteTextAttr](../cool-26-04/engine/sc/source/ui/view/formatsh.cxx#L651) 從 selection pattern 讀目前格式，再用 `ApplyUserItemSet` 套到所選 cell／range。這條路**不需要先雙擊**。上游現有 [mobile/calc/apply_font_spec.js:9](../cool-26-04/cypress_test/integration_tests/mobile/calc/apply_font_spec.js#L9) 也先 clickOnFirstCell，再按三個格式鈕，透過複製出的 HTML 驗證格式；本輪只讀該測試，沒有執行它。

格內編輯時，[SetEditShell](../cool-26-04/engine/sc/source/ui/view/tabvwsh4.cxx#L872) 裝上 `ScEditShell`；其 [粗體／斜體分支](../cool-26-04/engine/sc/source/ui/view/editsh.cxx#L1100) 建立 EditEngine 屬性，最後 [SetAttribs](../cool-26-04/engine/sc/source/ui/view/editsh.cxx#L1264) 套到目前文字選取／插入點。粗體／斜體同時處理 Latin／Asian／Complex 字族。

這說明了部分文字樣式不能只把 cell 的 `CharWeight` 改掉。我們 v1 的 textarea 有文字 selection，但 SDK 寫的是整個 XCell 的格式，沒有傳 selection range、文字 runs 或 EditView context；選取 textarea 文字不會自動改變 SDK 的作用範圍。若要對齊，需要另立格內 rich-text 契約，並驗證選取／字族／存檔的文字 runs；不應只改按鈕名稱或假裝目前已支援。

## Calc 與 Writer 的自動儲存核對

此處查的是本樹連到 Nextcloud host 時的 Writer／Calc，不是 Collabora 的伺服器儲存策略。Writer 的離線鏡像下載頁沒有啟動這套 host autosave。

| 項目 | Writer | Calc v1 |
| --- | --- | --- |
| 明確按儲存／Ctrl＋S | 有 | 有，存 ODS |
| 無操作後排程 | 30 秒 | **沒有** |
| 持續編輯的上限處理 | 未存滿 5 分鐘後改用 3 秒靜止間隔 | **沒有** |
| 切到背景 | visibilitychange 時嘗試安全儲存 | **沒有**；pagehide 只關 session |
| 組字／忙碌／佇列／拖曳／在途存檔保護 | autosaveAllowed 明確判斷；暫時不能存則 3 秒後重查 | 手動存檔的序列化與 IME guard 有，但沒有 autosaveAllowed／排程 |
| 版本／鎖／衝突副本 | 共用 Nextcloud host | 同一 host；MIME／副檔名為 ODS |
| 未存離開保護 | 有 | 有；**提醒未存不等於自動存回** |

來源為 [Writer 常數 :103](../wasm_sdk_probe/web/e2-editor-app.js#L103)、[排程 :3401](../wasm_sdk_probe/web/e2-editor-app.js#L3401) 與 [實際 host save :2452](../wasm_sdk_probe/web/e2-editor-app.js#L2452)；Calc 的 [save](../wasm_sdk_probe/web/ods-editor-app.js#L140)、[按鈕／鍵盤／離開](../wasm_sdk_probe/web/ods-editor-app.js#L157) 顯示只由手動入口觸發，並硬傳 `trigger:"manual"`。宿主本身沒有定時器幫任意頁面儲存，因此不能因為重用同一 host 就說已對齊。

若下一輪對齊，建議沿用 Writer 的時序和保護語意；另處理 Calc 還停在文字框、尚未 Enter 的草稿。需要先提交草稿才能匯出，且組字中不可提交；無法存回或副本也失敗時仍要保護未存內容。以此範圍新增定向驗收，沿用既有鎖／ETag／衝突處理，不重做 Writer 已成立的判準。

## 全白回歸的實測

[證人與修法](../findings/evidence/165-calc-format-blank/README.md) 保留原始紅案：第一次格式的 DOM 舊 tile 與引擎直接 render 不同；後續五個操作 DOM tile 數為 0，而模型和格式正確。原因是 session 先以新 revision 通知畫面，再讓 scheduler 清快取／取消工作。修正是先 invalidate，再同步發布狀態；不改引擎、格式作用範圍或輸入語意。

## 宿主實際核對結果

全白修法已裝 **0.2.35／b007f950b2e18cd2**，不需重連結。鏡像兩瀏覽器各三輪 90／90，實際 Files 兩瀏覽器 24／24，畫面與引擎 render 一致；詳見 [0.2.35 證據](../findings/evidence/host-0.2.35/README.md)。

兩個瀏覽器各在已提交的修改後靜置 **35,021 ms**，host saves 皆為零、仍 dirty；隨後手動儲存成功並從伺服器 XML 讀回修改。這是特定閒置時段的觀察；「目前沒有 autosave 排程」仍以原始碼核對為依據。本輪先完成差異確認與 165 修正，沒有把新 autosave 行為併入。litecore 保留原本 running，現有 24674 鎖及其他專案狀態不變。
