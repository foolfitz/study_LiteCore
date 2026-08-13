# SPEC E1-000：ODT-first 基本編輯器

> **日期**：2026-08-04  
> **狀態**：現行裁決 **`E1_GO_ODT_EDITOR`**（2026-08-07 重取，對出貨 artifact `835b453d…`／10 actions）。
> 期間因兩次重連結一度降為`E1_STOP_OR_RESCOPE`，證據已全數重取（見
> [E1-C spec §11.4／§11.6](./SPEC-E1-C-editor-validation.md)）  
> **依據**：[R8 local-delivery 部分 GO](./SPEC-R8-000-overview.md)、
> [R7 ODT-first 部分 GO](./SPEC-R7-000-overview.md)、[R6+ roadmap](./SPEC-R6+-roadmap.md)

## 1. 文件定位

E1 是 R8 後的 ODT-first 基本編輯器主線。它不追求重做 LibreOffice Online，也不以 canvas 上畫一個假 caret
宣稱已可編輯；目標是確認既有 LibreOfficeKit／Document SDK 邊界能否形成小而完整的 authoring contract。

E1 先回答六個問題：

1. host 能否從文件化的 LibreOfficeKit cursor／selection callback 得到可正規化的 caret 與 selection geometry？
2. 方向鍵、Home／End、Backspace／Delete、段落／換行能否成為封閉 typed operation，而不是任意 key code？
3. 每個 mutation 能否有 revision guard、可解釋 completion barrier 與 exactly-once 結果？
4. Undo／Redo、stale handle、Worker crash／restart與未儲存內容能否維持 R6～R8 的安全邊界？
5. 粗體、斜體、heading與list能否用固定語意 operation 實作並以 ODT round-trip 驗證，而不開放任意 `.uno:*`？
6. R7 的 IME／clipboard state machine能否在 caret移動、selection取代與composition cancel後仍不重複、不漏字？

## 2. 編號決策

本里程碑使用 **E1（Editor 1）**，不占用 roadmap 既有的 R9 Automation 與 R10深層減量。E1是產品主線，
R9仍是需求驅動的平行候選；R10必須等待E1 corpus／reachability凍結。

## 3. 已觀察的進場基線

- R8 machine decision為`PARTIAL_GO_LOCAL_DELIVERY`，13項local safety checks全為true；E1可沿用verified release、
  Service Worker、offline與rollback，不重做delivery架構。
- R7已驗證Chrome／Firefox Chewing composition、cancel零mutation、純文字clipboard與ODT-first corpus。
- 現有Document SDK公開`click()`、`insertText()`、`search()`、`getSelection()`、`replaceSelection()`、`undo()`、
  `save()`；selection只有文字，沒有公開caret／selection geometry。
- C ABI v1.1沒有keyboard、delete、newline、Redo、selection handle或format operation；`replaceSelection()`拒絕
  空字串，因此不能拿它假裝Delete。
- `insertText()`優先走LibreOfficeKit `paste(text/plain;charset=utf-8)`，失敗才逐Unicode code point
  `postKeyEvent`；它不是一般鍵盤事件contract。
- LibreOfficeKit有文件化的`postKeyEvent()`、`postMouseEvent()`、`setTextSelection()`、
  `LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR`與text-selection callbacks。`setTextSelection`列在unstable API區段，
  必須在A階段做相容與維護風險判定，不能先升格為SDK承諾。
- 目前probe把所有LOK callback先包成raw `lok`事件；sdk-worker只將tile／visible-cursor invalidation折疊成
  `document-invalidated`，沒有把raw payload暴露給應用，但也沒有typed editor state。
- Finding 012要求styled ODT close維持bounded Worker recovery；Finding 014要求Firefox generation有界並在預算
  耗盡前提示整個browser工作階段reload。

> **2026-08-08 補標**：此處把 finding 014 的限制列為「已觀察」，但該 finding 的成因已改判為我方 harness，**同頁 50 個 generation 實測全過**（上限所寫的 16 倍以上）。見 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)〈每頁 Worker generation 上限為 3〉一節。條文未改，僅記錄前提不成立。（本處先前漏列於 finding 014 的〈下游影響〉，2026-08-08 第三次複核才補上。）

以上分成已觀察基線，不代表E1能力已成立。

## 4. 不可退讓的邊界

- 不向JS暴露raw UNO、unoembind、任意`.uno:*`、任意key code、WASM pointer或未分類的LOK callback payload。
- 固定格式操作即使內部映射到已知LibreOfficeKit command，也只能接受closed enum，並以語意postcondition驗證；
  不提供command string escape hatch。
- 不解析未文件化callback欄位；若文件化payload在目標browser／fixture不穩定，標unsupported或建立finding。
- DOM input sink負責IME preedit與clipboard user gesture；document canvas不得偽裝成contenteditable或原生文字模型。
- mutation在timeout、abort、stale revision或Worker crash後不得自動重送；不確定是否落地時回typed
  `MUTATION_OUTCOME_UNKNOWN`或更窄分類，要求reload／save recovery。
- E1只承諾ODT。DOCX public open、generic rich clipboard、圖片貼上、拖放、表格結構編輯、任意樣式與macro不在v1。
- discovery優先沿用R5 `writer-review`與R8 release；若需新ABI，只建立隔離的editor-discovery artifact，
  不覆蓋既有artifact、不無理由修改LibreOffice core。
- core HEAD與既有dirty工作現場必須保留；不執行root、破壞性clean/reset或外部寫入。

## 5. 子階段與固定順序

| 階段 | 目的 | 完成訊號 |
|---|---|---|
| [E1-A](./SPEC-E1-A-editing-discovery.md) | caret／selection／keyboard／delete／newline／Redo／format邊界 discovery | 凍結可實作的closed operation與停止缺口 |
| [E1-B](./SPEC-E1-B-narrow-editor-contract.md) | narrow editor ABI、typed state與host editor shell | 不暴露generic escape hatch且exactly-once成立 |
| [E1-C](./SPEC-E1-C-editor-validation.md) | Chrome／Firefox、IME、ODT corpus、round-trip、recovery與可用性驗收 | 形成E1 GO／部分GO／停止判定 |

順序固定為 **E1-A → E1-B → E1-C**。A未完成前不凍結新ABI；A若證明某能力只能靠禁止surface，B必須
縮小產品範圍，不能用UI假象補洞。

## 6. E1 v1候選能力

### 6.1 Caret與selection

- click定位caret、可見性與document twips rectangle。
- 方向鍵、Home／End與Shift延伸selection；跨行、跨段、CJK、emoji／grapheme與文件邊界。
- 滑鼠drag或selection handles建立／調整selection；取得文字、rectangles、start／end與revision。
- zoom／scroll／tile rerender後geometry仍可解釋；不要求建立DOM文字鏡像。

### 6.2 文字mutation

- host提交已完成composition的Unicode文字；preedit仍留在DOM。
- backward／forward delete、paragraph break與line break為不同closed operation。
- selection存在時的insert／delete語意固定；空selection與文件邊界為安全no-op或明確結果。
- 每個mutation回傳before／after revision、changed、completion source與必要的editor state snapshot。

### 6.3 History與復原

- Undo與Redo為對稱closed operation；沒有history時為typed no-op，不猜測成功。
- stale revision零mutation；timeout／abort區分未開始、已完成與outcome unknown。
- crash後舊handle拒絕，unsaved mutation不自動重送；Finding 012／014策略保持。

### 6.4 最低格式

- inline：bold、italic。
- paragraph：body／heading候選與單一unordered／ordered list toggle候選。
- discovery需確認collapsed caret與selection兩種套用語意、Undo／Redo、save/reload與desktop round-trip。
- 若無安全state query，可將toggle降為一次性fixed action或從E1 v1移除，不以按鈕外觀推測文件狀態。

## 7. 非範圍

- 完整Writer toolbar、任意字型／字級／顏色、複雜表格、圖片與shape編輯。
- DOCX編輯／輸出、多文件同Worker、同步多人共同編輯、任意automation。
- 拼字建議、尋找取代UI、頁首頁尾、註腳、欄位、目錄與版面設定。
- 完整document-content accessibility tree；E1只要求host controls與editor state提示可存取，內容語意另立研究。
- 以COOL／Collabora協定直接替代Document SDK。它們可作行為參考，但不能偷偷引入未版本化私有contract。

## 8. 驗收與停止條件

**GO**：A證明caret／selection與縮限後必要mutation可由文件化LOK surface形成closed、可版本化contract；B／C的
兩browser自動矩陣、headed IME、ODT save／desktop round-trip、public Undo與bounded recovery全部成立；被A判定
無可靠completion的Redo／line navigation等能力必須明列unsupported。

**部分GO**：文字、delete、newline、selection與history成立，但格式、drag geometry、特定browser或
document-content accessibility須安全縮小；限制以capability與UI明示。

**停止／縮範圍**：需要raw UNO／unoembind／任意`.uno:*`、任意key code、未文件化callback parser、DOM假caret；
mutation completion無法區分重複／遺失、stale或timeout會silent mutation、selection geometry無法對應文件、
ODT round-trip破壞內容，或recovery自動重送unsaved mutation。

## 9. Evidence與人工最小化

- machine evidence放`findings/evidence/sdk-e1/`，分baseline、discovery、browser、roundtrip、regression與summary。
- 已有R7 Chrome／Firefox Chewing pass不重做；只有E1改變caret／selection後的IME交互且自動evidence不足時，
  集中做最多一輪headed人工確認。
- 每個失敗嘗試保留；可重現且影響SDK／browser／core邊界者建立編號finding。
- 明確分開已觀察、推論、待驗證；`pass:true`不得掩蓋partial decision或unsupported capability。

## 10. E1-A／B／C結果

E1-A原始key路徑的forward delete曾在Chrome／Firefox都出現「文件已刪除、沒有可歸屬completion callback、request
逾時」，並依規格停止。Finding 017其後修正空selection readback；原生與WASM scheduler實驗再否證上游缺少
callback及WASM缺主迴圈兩個假說。

2026-08-05完成的隔離verified-selection barrier不解析`StateWordCount`：SDK先以closed action形成一個文字unit
selection，用文件化typed callback與public readback驗證，再送固定Delete／Backspace；completion需同一transaction的
command result、新collapsed selection與public none。Chrome 150／Firefox 153各24/24正向案例與4/4邊界拒絕通過，
十份輸出ODT再通過desktop LibreOffice reopen／PDF export。Machine decision為
`SELECTION_BARRIER_SUPPORTED_WITH_BOUNDARY_RESTART`。

[Finding 016](../findings/016-lok-forward-delete-completion-gap.md)因此解除停止條件；結構邊界拒絕後必須fresh Worker，
不得自動retry。其後A6已完成Chrome／Firefox各五個fixture、bold／italic、public Undo、完整ODT round-trip與
R6～R8回歸，machine decision為`PARTIAL_GO_TO_E1_B`。

E1-B依此縮限凍結八個產品action，完成隔離`e1-editor-v1` ABI／profile、typed Worker protocol、JS client、FIFO
session與host editor shell。Chrome 150／Firefox 153各完成27筆相同操作，兩份輸出ODT均通過ZIP／XML／anchor與
desktop LibreOffice reopen／PDF export；R6～R8與E1-A回歸、workspace before／after preflight也全部通過。
Machine summary為`complete:true`、decision `GO_TO_E1_C`。

產品surface沒有generic key／UNO escape hatch；delete仍要求verified-selection completion，boundary rejection後
必須fresh Worker，timeout／crash不自動retry。Line navigation因
[Finding 018](../findings/018-lok-line-navigation-completion-nondeterministic.md)不具確定completion；Redo、mouse
drag／handles、paragraph/list及structural boundary editing同樣保持unsupported。

E1-C已完成。Chrome 150／Firefox 153共48個integration／recovery／corpus／lifecycle cases全過，48份ODT通過
ZIP／XML／anchor，16份required輸出通過desktop reopen／PDF。兩browser各一次集中Fcitx5 Chewing人工run也通過
trusted composition、selection replacement、cancel零mutation、原生貼上及Clipboard API。Before／after preflight
與R6～R8、E1-A／B回歸皆通過，最終判定`E1_GO_ODT_EDITOR`。

**該判定綁在當時的 artifact 上，2026-08-07 曾一度失效並已收復。** 兩次重連結（E1-D 範圍選取、
底線／刪除線）換掉了出貨的 wasm／loader／worker，48 個瀏覽器 case 與雙瀏覽器人工輪一度都變成
描述舊二進位（`E1_STOP_OR_RESCOPE`）。同日已對 `835b453d…` 重取全部證據——48/48 綁定、
0 superseded、雙瀏覽器人工輪各九項全過——**裁決回到 `E1_GO_ODT_EDITOR`**。能力邊界不變，
contract 由 8 增為 10 actions（新增底線、刪除線）。見
[E1-C spec §11.4／§11.6](./SPEC-E1-C-editor-validation.md)。

此GO只涵蓋縮限的ODT-first editor v1；Cangjie／Pinyin、Line navigation、Redo、drag／handles、paragraph／list、
structural editing、DOCX與rich clipboard仍不承諾。完整交接見
[E1-B spec](./SPEC-E1-B-narrow-editor-contract.md)、
[E1-C spec](./SPEC-E1-C-editor-validation.md)、
[E1-C machine summary](../findings/evidence/sdk-e1/editor-validation/summary.json)與
[2026-08-05 WASM SDK E1 DEVLOG](../devlog/DEVLOG-2026-08-05-wasm-sdk-e1.md)。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。建立E1編號、ODT-first基本編輯器邊界、A→B→C路由與GO／部分GO／停止條件。 |
| 2026-08-04 | v2。E1-A跨瀏覽器觸發Finding 016停止條件；E1主線暫停於STOP_OR_RESCOPE。 |
| 2026-08-04 | v3。Finding 016 fixed-command補救只證明break成立；delete缺可靠semantic boundary readback，維持停止判定。 |
| 2026-08-05 | v4。Finding 017 SDK readback已修；原生對照將Finding 016改判為我方缺LOK主迴圈，下一步改為最小scheduler驗證。 |
| 2026-08-05 | v5。Scheduler最小實驗跨瀏覽器否證主迴圈缺口；Finding 016改判為SDK callback分類／歸屬缺口。 |
| 2026-08-05 | v6。Verified-selection barrier跨兩瀏覽器與desktop round-trip通過；Finding 016解除阻斷，E1-A恢復剩餘A6矩陣。 |
| 2026-08-05 | v7。E1-A A6完成並判定PARTIAL_GO_TO_E1_B；凍結成立能力與line／Redo／drag／paragraph-list縮限。 |
| 2026-08-05 | v8。E1-B產品contract、雙browser shell與desktop round-trip完成並判定GO_TO_E1_C。 |
| 2026-08-05 | v9。建立E1-C整合／產品驗證spec與凍結矩陣；尚未授權實作。 |
| 2026-08-05 | v10。E1-C自動、desktop與雙browser headed gate全過，E1判定`E1_GO_ODT_EDITOR`。 |
| 2026-08-07 | v11。E1-D與底線／刪除線兩次重連結使全部E1-C證據脫離出貨artifact；自動相位補上artifact綁定閘門後裁決降為`E1_STOP_OR_RESCOPE`。能力邊界不變，待重取證據。 |
| 2026-08-07 | v12。finding 023修復後對`835b453d…`重取全部證據（48/48綁定、雙瀏覽器人工輪各九項全過），裁決回到`E1_GO_ODT_EDITOR`；contract 8→10 actions。 |
