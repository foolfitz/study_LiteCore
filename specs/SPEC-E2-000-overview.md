# SPEC E2-000：段落層級格式與精簡編輯器補完

> **日期**：2026-08-05  
> **狀態**：規劃；尚未執行  
> **依據**：[E1 `E1_GO_ODT_EDITOR`](./SPEC-E1-000-overview.md)、
> [R7 ODT-first 部分 GO](./SPEC-R7-000-overview.md)、[R6+ roadmap](./SPEC-R6+-roadmap.md)

## 1. 文件定位

產品目標是一個**編輯功能精簡、讀取完整**的 Writer WASM：使用者看到的工具列只有粗體、斜體、有序清單、
無序清單這類基本項目，但開啟文件時必須是完整、可信的 LibreOffice 讀取結果，不是簡化渲染。

E1 已交付窄版 ODT-first 編輯 contract（八個 closed action、`E1_GO_ODT_EDITOR`），但那八個 action 全部是
**inline 或字元層級**的。段落層級——清單與標題——在 E1-A discovery 被明確縮限，未升格為產品能力。

E2 只處理這個落差的**編輯側**。讀取完整性（DOCX 與其他格式）是另一組獨立未知數，另編 E3，不混入本輪。

## 2. 目標與現況落差

| 目標工具列項目 | E1 現況 | 落差來源 |
|---|---|---|
| 粗體 | `set-bold` 已成立 | — |
| 斜體 | `set-italic` 已成立 | — |
| 無序清單 | unsupported | fixed command 不回 UNO command result |
| 有序清單 | unsupported | 同上 |
| 標題／內文樣式 | unsupported | 同上 |
| 上下方向鍵、Home／End | unsupported | [Finding 018](../findings/018-lok-line-navigation-completion-nondeterministic.md) |
| 滑鼠拖曳選取 | unsupported | `postMouseEvent` drag 形不成可用 selection completion |
| Redo | unsupported | 固定 Redo 回 `LOK_COMMAND_FAILED` |

清單與標題是使用者明確要求的功能；方向鍵與拖曳選取雖然不是格式功能，但缺了它們，「精簡編輯器」在實際
操作上並不成立。兩者的共同阻礙都是 **completion 歸屬**，不是能不能改到文件。

## 3. 本輪唯一的主要未知數

> 一個操作在**沒有可信的成敗回報**時，SDK 能不能為它建立**可歸屬、可重複、能區分 no-op 與遺失**的
> completion barrier？

[Finding 016](../findings/016-lok-forward-delete-completion-gap.md) 的 delete 卡的是同一件事，最後靠自建的
verified-selection barrier 解除。E2 要驗證這個方法能不能一般化到段落層級格式。一個未知數，換回三到五項能力，
符合 roadmap「每輪只解一組主要未知數」。

> **2026-08-05 v2 修訂**：本節 v1 原本問的是「拿不到 `LOK_CALLBACK_UNO_COMMAND_RESULT` 時怎麼辦」。
> A2 原生實測顯示這些命令**多半有**回 command result，只是 `success`／`wasModified` 會說謊
> （[finding 020](../findings/020-lok-list-command-result-contradicts-document.md)），而段落樣式之所以
> 毫無回應是因為 E1-A 映射到了不存在的 UI 別名
> （[finding 019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)）。未知數的形狀因此修正如上：
> 問題不是「沒有回報」，是「回報不可信」。

## 4. 編號決策

本里程碑編為 **E2**，接在 E1 之後。讀取完整性另編 **E3**（DOCX 為其中的低順位選項），Markdown 讀寫另編
**E4**，R9 Automation 與 R10 深層減量編號不變。E2、E3、E4 沒有技術相依，順序依產品優先度決定；本文件
不預先授權 E3 或 E4。

**三者同時是 R10 的前置條件。** R10 要靠「產品確定會用到什麼」來決定裁掉哪些 core 程式碼與資源，而 E2 會
新增清單／段落樣式的相依、E4 可能承諾 markdown 濾鏡、E3 可能承諾整套 DOCX 匯入 filter。先裁切再補能力必然
要重編一次 corpus 與 A/B artifact，因此 R10 不得在三者能力範圍定案前啟動。見
[R6+ roadmap](./SPEC-R6+-roadmap.md) 第 8.1 節與第 10 節。

## 5. 已觀察的進場基線

- E1 最終判定 `E1_GO_ODT_EDITOR`；`e1-editor-v1` profile 凍結八個 action，loader
  `45c31f32…1b9511e`、WASM `94b38437…4ea7b6ef`、Worker `9696c9ce…474a35fd7`。
- E1-A discovery ABI 已含 `OXSDK_EDITOR_SET_PARAGRAPH_BODY`、`SET_PARAGRAPH_HEADING`、`SET_LIST_NONE`、
  `SET_LIST_UNORDERED`、`SET_LIST_ORDERED`（`src/editor_discovery_api.h`），並映射到
  `.uno:TextBodyParaStyle`、`.uno:Heading1ParaStyle`、`.uno:RemoveBullets`、`.uno:DefaultBullet`、
  `.uno:DefaultNumbering`（`src/probe_engine.cpp:2083-2097`）。**能力缺的是 completion，不是 ABI。**
- E1-A 已觀察：「paragraph／list 部分 fixed command 沒有回 UNO command result；不能以 toolbar 外觀或
  dispatch return 宣稱成功」（[SPEC E1-A](./SPEC-E1-A-editing-discovery.md) 第 11.3 節）。
- `set-bold`／`set-italic` 之所以成立，是因為它們**同時**有 UNO command result 與 STATE_CHANGED 狀態回讀；
  `src/probe_engine.cpp:457` 已把 `.uno:Bold=true`／`.uno:Italic=true` 解析成 typed state，
  `:2023` 已用該狀態實作 `documented-state-noop`。
- LibreOfficeKit 在 core 有一份**封閉列舉**的 command→state payload 對照表
  `GetKitUnoCommandList()`（`sfx2/source/control/unoctitm.cxx:1165`）。其中
  `DefaultBullet`、`DefaultNumbering` 為 `IsActivePayload`，`StyleApply` 為 `StyleApplyPayload`，
  三者 `initializeForStatusUpdates` 皆為 `true`，並由 `doc_iniUnoCommands()`
  （`desktop/source/lib/init.cxx:3947-3963`）在 view 建立時初始化 slot。
- Bold／Italic 與 DefaultBullet／DefaultNumbering／StyleApply 出自**同一張表、同一個機制**；SDK 現有的
  Bold 狀態解析已證明這條路徑在本專案的 WASM profile 上會實際送達。
- [Finding 012](../findings/012-r6-styled-document-close-timeout.md) 的候選軸是 `frame.wrapper`；清單切換會在
  ODT 產生 `<text:list>` 包裝結構，屬相鄰風險。
- [Finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md) 要求 Firefox 每頁 Worker
  generation 有界。

> **2026-08-08 補標**：此處把 finding 014 的限制列為「已觀察」，但該 finding 的成因已改判為我方 harness，**同頁 50 個 generation 實測全過**（上限所寫的 16 倍以上）。見 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)〈每頁 Worker generation 上限為 3〉一節。條文未改，僅記錄前提不成立。（本處先前漏列於 finding 014 的〈下游影響〉，2026-08-08 第三次複核才補上。）

以上只是進場基線。第 5 節後三點形成本輪的核心**推論**，必須由 E2-A 用實測升格，不得直接當結論。

**2026-08-05 更新**：A2 原生實測已將該推論升格為**已觀察** —— 三個 state payload 都會抵達。同一次實測
另外推翻了兩件本節原本視為已知的事：段落樣式的命令映射是錯的（finding 019），而 command result 的成敗
欄位不可信（finding 020）。詳見 [SPEC E2-A](./SPEC-E2-A-paragraph-format-discovery.md) 第 2.2 節。

## 6. 不可退讓的邊界

- 不新增 raw UNO、unoembind、任意 `.uno:*`、任意 key code、WASM pointer 或未分類 LOK callback payload。
  新增能力一律是 closed enum，內部映射固定，JS 端拿不到 command string。
- 只解析 core `GetKitUnoCommandList()` 已列舉的 payload 形態。不解析未列舉欄位、不做正規表示式猜測、
  不因為某個 payload「看起來像」就採用。
- completion 必須可歸屬到單一 request。**不得**以「下一個抵達的 state callback 就是我的」作 correlation，
  也不得以 sleep、固定 delay、tile invalidation 或 UI 外觀補成 completion。
- 「已經是目標狀態」必須是 typed no-op（`changed:false`），不得與「callback 沒到」混為一談；前置狀態未知時
  一律 fail closed，回 typed error，不猜。
- timeout、abort、stale revision、boundary rejection、Worker crash 與 outcome unknown 皆不自動 retry／replay。
- 不修改 LibreOffice core。不重建或覆寫 R5 `writer-review` 與 E1-B `e1-editor-v1` artifact；E2 discovery 只用
  隔離 artifact。
- core HEAD 與既有 dirty 工作現場必須完整保留；不執行 root、破壞性 clean／reset 或外部寫入。
- 產品若最終只能縮限，UI 與 manifest 必須明示 unsupported，不以按鈕外觀暗示已支援。

## 7. 子階段與順序

| 階段 | 目的 | 完成訊號 |
|---|---|---|
| [E2-A](./SPEC-E2-A-paragraph-format-discovery.md) | verified-format-state barrier discovery：清單、標題，附帶重評 line navigation 與 drag selection | 凍結可實作的 closed operation 與縮限項目 |
| E2-B | 將成立能力併入 `e1-editor-v1` 的後續版本 ABI、typed state 與 host shell | 不擴大 escape hatch 且 exactly-once 成立 |
| E2-C | 雙瀏覽器、ODT corpus、round-trip、recovery 與產品驗收 | 形成 E2 GO／部分 GO／停止判定 |

順序固定為 **E2-A → E2-B → E2-C**。A 未完成前不凍結新 ABI；A 若證明某能力只能靠禁止 surface，B 必須縮小
產品範圍。B 與 C 的規格待 A 有結果後另寫，本文件不預先授權。

## 8. E2 v1 候選能力

### 8.1 主要（有源碼層級候選機制）

- `set-list(none | unordered | ordered)`：以 explicit closed enum 設定，不是 toggle。
- `set-paragraph-style(body | heading)`：同上；heading 先只承諾單一層級，不做 H1～H6 全套。
- 每個操作回傳 before／after revision、`changed`、completion source 與 typed 後置狀態。

### 8.2 次要（本輪只做證據，允許維持 unsupported）

- line navigation（up／down／home／end）：Finding 018 的重評。
- mouse drag selection：是否有可承諾的 selection completion。

次要項目**不得**成為 E2-A 的判定條件。它們的價值在於留下可重複的否證證據，避免下一輪重跑同樣的死路。

## 9. 非範圍

- H1～H6 全層級、清單縮排／階層、自訂樣式、字型／字級／顏色、對齊與行距。
- Redo、structural boundary editing、表格／圖片／shape 編輯。
- DOCX 與其他格式的讀取或輸出（屬 E3）。
- markdown 語法輸入或輸出。產品的「精簡」指工具列範圍，不指檔案格式。
- 完整 document-content accessibility。

## 10. 驗收與停止條件

**GO**：清單三態與段落樣式兩態在 Chrome／Firefox 各達門檻次數，completion 可歸屬、no-op 與遺失可區分、
revision 每次只前進一格、ODT round-trip 與 desktop reopen 通過，且不需要任何禁止 surface。

**部分 GO**：清單或段落樣式其中一組成立、另一組必須安全縮限；或 heading 只能承諾單一層級。限制以 capability
與 UI 明示。

**停止／縮範圍**：completion 無法歸屬到單一 request；no-op 與遺失不可區分；state payload 在目標瀏覽器不穩定
或需要解析未列舉欄位；清單切換造成 ODT 結構 silent loss 或觸發 Finding 012 類 teardown 阻塞；或補齊需要
raw UNO／任意 command string／sleep／自動 retry。保存失敗 bytes 與 trace 並建立編號 finding。

## 11. Evidence 與人工

- machine evidence 放 `findings/evidence/sdk-e2/`，分 `baseline`、`discovery`、`browser`、`roundtrip`、
  `regression` 與 `summary.json`。
- 每個失敗 attempt 獨立保存不覆寫；每筆結果標 `observed`、`inferred` 或 `notValidated`。
- E2-A **不需要**人工驗收：本輪沒有改變 IME／clipboard 互動。若 E2-B／C 改到 caret 或 selection 行為，
  才依 E1-C 的方式做最小化 headed 確認。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。建立 E2 編號與段落層級補完主線；定義單一未知數、A／B／C 路由與 GO／部分 GO／停止條件。 |
| 2026-08-05 | v2。A2-native 完成；未知數由「沒有回報」修正為「回報不可信」，並建立 finding 019／020。E2-A 尚無判定。 |
