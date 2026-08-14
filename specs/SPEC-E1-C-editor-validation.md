# SPEC E1-C：窄版 ODT Editor 整合與產品驗證

> **日期**：2026-08-05（最後修訂 2026-08-14，v9）  
> **狀態**：現行裁決 **`E1_GO_ODT_EDITOR`**（**2026-08-14 重綁**，矩陣 v2、
> `automaticPass: true`、`complete: true`、`failedProperties: []`、50 格全綁）。
>
> > **這一次的涵蓋是四個雜湊，不是三個**：loader `1fe83aed…`／wasm `835b453d…`／
> > worker `e4f37ffe…`，**加上殼層 bundle `f9b1a52f…`**。08-14 上午那個
> > 「不涵蓋 08-13 之後的殼層」的具名界定**已由這個新綁定取代**，不再需要隨引用附帶。
> > 證據樹：[`editor-validation-v2/`](../findings/evidence/sdk-e1/editor-validation-v2/)。
> > 前一輪（2026-08-07、三個雜湊）的證據樹**原封保留**在 `editor-validation/`，未被覆寫。
>
> 曾三度判定 GO（2026-08-05、2026-08-06、2026-08-07）。中間因 E1-D 範圍選取與底線／刪除線兩次重連結
> 一度降為 `E1_STOP_OR_RESCOPE`，重跑期間又撞上 finding 023；兩者皆已結案。
> 沿革見 §11.4／§11.5，收復經過見 §11.6。  
> **前置閘門**：[E1-B](./SPEC-E1-B-narrow-editor-contract.md) 已完成並判定`GO_TO_E1_C`  
> **凍結矩陣**：[`validation-matrix-v2.json`](../wasm_sdk_probe/e1/validation-matrix-v2.json)（現行）／
> [`validation-matrix-v1.json`](../wasm_sdk_probe/e1/validation-matrix-v1.json)（2026-08-07 那一輪，保留）
> **最終證據**：[`editor-validation-v2/summary.json`](../findings/evidence/sdk-e1/editor-validation-v2/summary.json)

## 1. 目的

E1-C不再擴充Editor ABI；它要證明E1-B的窄版產品contract在真實host輸入、代表性ODT、故障復原與較長操作序列中
仍維持exactly-once、可保存且可解釋。完成後才對整個E1里程碑作GO／部分GO／停止判定。

本階段重用R7的`HostInputAdapter`、plain-text clipboard、Chewing人工證據、ODT corpus與bounded Worker recovery，
但只重驗E1新增的caret／selection／editor action交互；不重做R7已通過且與Editor Contract無關的完整矩陣。

## 2. 進場基線

### 2.1 已觀察

- E1-B `e1-editor-v1`只開放八個closed action與typed state；Chrome 150／Firefox 153各27筆shell操作、ODT
  round-trip及R6～R8／E1-A回歸均通過。
- E1-B artifact hash為loader
  `45c31f321fa4bcf2e5065c1942e0358b03ab94148732496160ae822541b9511e`、WASM
  `94b38437cce120de4bffb6275d084f1257abb7d6a310cb3cf20594ae72eab6ef`、Worker
  `9696c9ce580b431644cd4f56ea7356647dfd9ab143da6370e521bc2474a35fd7`。
- R7的Chrome／Firefox Fcitx5 Chewing真實composition、cancel、trusted paste與Clipboard API已各有一份
  `pass:true`人工證據；Cangjie／Pinyin未驗證且不在E1 v1承諾。
- R7 28份相容性corpus已通過ODT-first驗證；E1-C只取五份代表性positive ODT，避免把DOCX與negative format
  classification混入editor驗收。
- Finding 012已有bounded Worker recycle。E1-C的每個`EditorSession`最多使用三個Worker generation
  （＝最多兩次崩潰／boundary回復），達上限時明確reload整個頁面。
> **2026-08-08 更正**：此處把 finding 014 的限制列為「已觀察」，但該 finding 的成因已改判為我方 harness，**同頁 50 個 generation 實測全過**（上限所寫的 16 倍以上）。見 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)〈每頁 Worker generation 上限為 3〉一節。條文未改，僅記錄前提不成立。
>
> **2026-08-08 第二次更正（這一條數錯了東西）**：上面說的「每頁 Worker generation」是
> **每頁引擎實例化次數**，而**產品從來沒有實作過它**。產品唯一實作的是
> `editor-shell/editor-session.js` 的 `maxWorkerGenerations`（預設 **3**），數的是
> **同一個 `EditorSession` 的崩潰／boundary 回復次數**：首次 `open()` 算第 1 代，
> 之後每次 `restart()` ＋1；`close()` 之後不能再開，下一份文件是新的 session、計數器歸零。
> 兩者只有在「一頁只有一個 session」時才碰巧一致。見
> [finding 026](../findings/026-generation-cap-means-two-different-things.md)。
>
> **決定（2026-08-08）：產品維持 3。**理由是崩潰回復深度本來就該有界，
> 與 finding 014 無關、也不因 014 撤回而需要改動；
> **「每頁」這個承諾撤除**——它沒有任何產品側實作，且 014 撤回後也沒有任何已量測的理由
> （單頁 100 代通過，記憶體是回收延遲不是殘留，見 finding 014〈待驗證 10 結案〉）。
> 佐證：出貨 artifact `835b453d…` 在回復軸上 Chrome／Firefox 各 **16/16**，
> 第 17 次仍以 `WORKER_GENERATION_LIMIT`＋`requiresPageReload` 擋下，fail-closed 未被移除。

- Finding 016要求結構邊界拒絕後fresh Worker；Finding 018使line navigation維持unsupported。

### 2.2 推論

- E1-C的主要未知數不是單一action能否運作，而是composition、selection replacement、save authority與Worker
  generation交錯時，session是否仍不重複、不漏字、不重播未儲存mutation。
- 真IME的`isTrusted`不能由自動化取代；但人工只需覆蓋E1相對R7新增的interaction delta，不需重跑三輸入法大全。

## 3. 不可退讓的邊界

- 不新增raw UNO、unoembind、任意`.uno:*`、任意key code、WASM pointer或raw／未分類LOK callback。
- 不為通過驗收擴回line navigation、Redo、drag／handles、paragraph／list、structural boundary editing或DOCX。
- DOM擁有IME preedit；只有確定commit的Unicode文字可進FIFO mutation queue。Cancel、blur、stale、crash與restart
  不得把preedit或未確定文字送入文件。
- Clipboard只接受`text/plain`且必須有user intent；HTML、圖片、任意MIME與permission denied皆不得mutation。
- Timeout、abort、stale revision、boundary rejection、Worker crash與outcome unknown皆不得自動retry或replay。
- Browser結果必須再經ODT ZIP／XML／anchor與desktop LibreOffice reopen／PDF驗證；canvas畫面不能取代內容證據。
- 優先沿用E1-B artifact；沒有可重現的ABI／Core缺口不得修改LibreOffice Core或重建不同core。

## 4. 凍結產品範圍

### 4.1 必須成立

- Click定位後typed collapsed caret；字元左右移動與Shift延伸selection。
- 真／合成composition在collapsed caret提交一次；selection存在時以一次commit取代selection。
- Backspace／Delete verified-selection barrier、paragraph／line break、Undo、explicit bold／italic與save。
- Plain-text copy／paste、permission denied／empty／unsupported MIME零mutation。
- Boundary rejection後`restart-required`、fresh Worker、舊handle失效且queued mutation不重播。
- ~~Crash前未保存內容不恢復；crash前已保存authority可重開；pending composition與queued input不重播。~~
  **（2026-08-14 修訂，v8；重綁已於同日完成，現已生效）** Crash後只能重開引擎自己save出的bytes：
  authority與selection手勢前checkpoint兩者取content stamp較新者；自checkpoint重開時session
  必須標dirty且typed state揭露`hasCheckpoint`。不在這兩份bytes內的內容（含pending composition
  與queued input）不恢復、不重播。checkpoint永不寫入authority；authority只由顯式save更新，
  顯式save後checkpoint作廢。checkpoint save失敗不得使手勢失敗，但必須以typed state揭露
  （`checkpointError`），不得只留在session內部欄位。（原文與修訂理由見修訂紀錄v8。）
  > **這一項不是擴 surface，跟被否決的那條路不同。** `checkpointError` 是**殼層 session
  > snapshot** 的欄位，不是 Editor ABI——§3 守的是 raw UNO／任意 `.uno:*`／key code／
  > WASM pointer／未分類 callback 那一類**引擎面**擴充，一個唯讀的狀態欄位不在其中。
  > 被否決的 (B) 之所以算擴 surface，是因為它需要 `restart({source})`：一個讓呼叫端
  > **選擇復原來源**的新入口。**多告訴 host 一件已經發生的事，和多給 host 一個新的控制項，
  > 不是同一件事。**

### 4.2 明確不承諾

- Cangjie／Pinyin、行動／觸控IME、rich clipboard、圖片貼上與拖放。
- Line up/down/home/end、Redo、滑鼠拖曳selection handles、段落／heading／list格式。
- 表格結構、圖片、shape、註解或修訂內容的結構編輯；corpus內這些物件只驗證旁側安全文字編輯不破壞原內容。
- DOCX open／save、多人同步、autosave、完整document-content accessibility與完整Writer toolbar。

## 5. 自動測試矩陣

數量與項目以`validation-matrix-v2.json`為準（2026-08-14 起；`v1` 是 2026-08-07 那一輪的，
**位元組保留、未修改**），正式結果產生後不得放寬。

### C0：進場與surface inventory

- 保存Core HEAD／dirty baseline、E1-B manifest／export／artifact hashes與browser／desktop版本。
- 驗證產品profile只有核准action；diagnostic operation、未知action、`keyCode`、`unoCommand`與command string均
  fail closed且零mutation。

### C1：整合 input／clipboard／editor sequence

Chrome／Firefox各三次完整sequence：

1. click並等待typed collapsed caret；真實mutation前不得重送click；
2. 合成composition於caret commit一次，移動caret後再commit一次；
3. Shift-character建立selection，以單次Unicode commit取代selection，驗證舊文字消失、新文字恰好一次；
4. composition cancel、duplicate end、late beforeinput與blocked state全部零mutation；
5. plain-text paste取代selection；HTML+plain只採plain，denied／empty／oversized零mutation；
6. 雙向delete、兩種break、bold／italic、Undo與save；每個action驗證revision及typed postcondition。

### C2：Recovery與no-replay

兩瀏覽器各自驗證：

- stale editor revision與stale document handle零mutation；
- structure boundary回`EDITOR_BOUNDARY_UNSUPPORTED`，session進`restart-required`並拒絕已排隊操作；
- ~~fresh Worker只重開authority bytes，boundary action與queue不重播；~~
  **（2026-08-14 修訂，v8）** fresh Worker只重開引擎save出的bytes（authority或checkpoint，
  取content stamp較新者），boundary action與queue不重播；
- ~~composing、queued mutation、unsaved local edit、saved authority四個crash barrier；~~
  **（2026-08-14 修訂，v8）** composing、queued mutation、unsaved local edit、checkpointed edit、
  saved authority**五**個crash barrier；
- ~~unsaved內容明確不可恢復，saved authority可恢復，舊handle／舊generation結果不可污染新session；~~
  **（2026-08-14 修訂，v8）** 既未進authority亦未進checkpoint的內容明確不可恢復；saved authority
  可恢復；checkpoint較authority新時restart重開checkpoint並標dirty（`crash-after-checkpoint`格釘住）；
  顯式save後checkpoint作廢、不得復活（`crash-saved`格的新assertion釘住）；
  舊handle／舊generation結果不可污染新session；
- **每個`EditorSession`**最多3個Worker generation（首次open為第1代，其後每次崩潰／boundary
  `restart()`＋1），達上限時以typed `WORKER_GENERATION_LIMIT`＋`requiresPageReload`要求完整page
  reload，不以無界restart規避。
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


### C3：ODT editor corpus

固定五份positive ODT：

| ID | 目的 | 允許編輯位置 |
|---|---|---|
| `l0-t1` | 純文字、CJK與grapheme | 指定普通段落anchor |
| `l0-t2` | style／table／image／comment保存 | 非結構普通段落，不進table/image |
| `l0-t3` | 22頁長文件 | 首／中／末指定文字anchor |
| `l1-review-odt` | comment／tracked-change保存 | 未修訂普通段落anchor |
| `l4-stress-100` | 100頁含圖片 | 固定頁面文字anchor |

每份在每個browser至少一次open→定位→文字／delete／format最小序列→Undo→save。輸出需驗證原始required anchors、
新增／刪除postcondition、ZIP CRC、XML、禁止內容未出現、desktop reopen與PDF export。E1-C不重生成或改寫R7
corpus source bytes。

**2026-08-13 新增第六份 `list-contexts`（下一次重綁起生效）**，理由與界線見 9.2：

| ID | 目的 | 允許編輯位置 |
|---|---|---|
| `list-contexts` | 清單內容軸（無序＋有序）與**孤立的清單動作錨點** | `E1-LC-ISOLATED`（前為標題、後為普通段落，**兩側都不是清單**） |

**它放在 `test-docs/e1/` 而不是 `test-docs/r7-compat/`**，因為本節明訂 E1-C 不重生成或改寫
R7 corpus source bytes；新增一份 E1 自有語料不碰那條規則。**`styled-list` 不能代替**：
[SPEC E2-A](./SPEC-E2-A-paragraph-format-discovery.md) 第 11 節記過它的錨點緊鄰既有清單，
套用清單會與鄰居合併，後置條件分不出「動作成功」與「併進隔壁那串」。
`E1-LC-BETWEEN`（兩側都是清單的普通段落）刻意留著，讓合併行為有地方可量。

**目前的 `E1_GO_ODT_EDITOR` 是在五份上量的，不涵蓋這一份**——它是下一次重綁的目標，
不是對既有判定的追認。盤點檔因此有兩個套件：`E1-C-C3`（判定實際跑過的五份，
`list` 釘成 absent）與 `E1-C-C3-next`（六份，`list` 釘成 present）。
**既有判定跑過什麼是歷史事實，不因為後來補了語料就改寫**（前例：[027](../findings/027-r8d-verdict-silently-outlived-its-release.md)）。

### C4：Bounded lifecycle與回歸

- 每個browser跑10個獨立edit→save→reopen session、4種crash barrier與2種boundary restart；每頁不超過三個
  Worker generation，runner自行reload新頁而非要求人工。
- 每次結束Worker／handle歸零；記錄browser process tree、PSS／RSS可取得值、WASM heap、latency與forced
  termination。E1-C只要求無連續成長與無zombie，不重做R7的30分鐘viewer soak。
- 回歸R6 release、R7-B／C／D、R8-D、E1-A與E1-B；before／after workspace preflight必須通過。

## 6. 人工驗收最小化

人工只在C0～C4全部通過後開始，Chrome與Firefox各**一個集中run**，只用既有Fcitx5 Chewing：

1. 在collapsed caret輸入固定繁中phrase；
2. 用產品Shift-character按鈕建立selection，再以真IME取代；
3. 移動caret後開始composition並Escape cancel，確認revision與save後ODT皆無取消字串；
4. 真Ctrl+C／Ctrl+V與一次Clipboard API user-gesture讀寫；
5. save後由machine validator檢查exact anchor count與desktop reopen。

兩個browser可在同一次operator時段完成；不要求Cangjie、Pinyin、Orca或重複三輪。若已有同browser／同artifact的
trusted evidence且自動delta沒有改到相關互動，可由validator明確標`reused`；但不能拿synthetic事件冒充真IME。
人工無法取得時可判部分GO，不為湊GO反覆要求operator操作。

## 7. Evidence contract

```text
findings/evidence/sdk-e1/editor-validation/
  baseline/preflight-before.json
  baseline/preflight-after.json
  inventory/profile.json
  browser/<browser>/<attempt>/
  recovery/<browser>/
  corpus/<browser>/<fixture>/
  lifecycle/<browser>/
  manual/<browser>-chewing.json
  roundtrip/summary.json
  regression/summary.json
  summary.json
```

- 每次失敗attempt獨立保存，不覆寫；browser／desktop啟動前的sandbox拒絕也要保存。
- 每筆結果標示`observed`、`inferred`、`reused`或`notValidated`；summary不得用`pass:true`隱藏縮限。
- 人工evidence只記fixture字串、code points、事件metadata與hash，不保存任意clipboard或私人輸入。
- 可重現且影響SDK／browser／Core邊界的新問題建立編號finding；單純runner／fixture錯誤留DEVLOG與attempt。

## 8. 執行順序與停止點

順序固定為 **C0 inventory → C1 integration → C2 recovery → C3 corpus → C4 lifecycle/regression → C5 headed**。

- C0若profile surface不符先停止，不跑內容mutation。
- C1／C2觸發silent mutation、重播或outcome不明時立即停止C3～C5並建立finding。
- C3 required ODT有silent內容／結構損失時停止；單一非核心fixture若能安全縮限才可考慮部分GO。
- C4未通過不得要求人工驗收；人工不能推翻machine stop。
- 不需新ABI／Core時一路自動執行；若需要擴大檔案範圍、重建Core或新增外部依賴，另行取得確認。

## 9. 判定

**E1_GO_ODT_EDITOR**：C0～C4全部通過；Chrome／Firefox各一份trusted Chewing delta通過或有同artifact可接受的
明確reuse；五份ODT皆desktop round-trip；recovery、no-replay、generation上限、回歸與workspace保護成立。

**E1_PARTIAL_GO_ODT_EDITOR**：核心文字／selection／delete／break／Undo／save及安全recovery成立，但單一browser
人工IME、bold／italic、非必要corpus或host accessibility只能縮限；限制以capability／UI明示且不影響內容安全。

**E1_STOP_OR_RESCOPE**：文字重複／漏失、selection replacement錯誤、cancel／denied／stale後mutation、boundary
或crash後自動重播、舊generation污染新文件、required ODT silent loss／損壞、Worker無界增長，或完成流程需要禁止
surface。保存失敗bytes／trace並建立finding，不以last-write-wins、sleep或retry掩蓋。

### 9.1 判定不涵蓋的內容軸（2026-08-12 具名收窄，[finding 038](../findings/038-a-frame-inside-a-footnote-wedges-the-engine-on-selection.md)）

**`E1_GO_ODT_EDITOR` 不涵蓋「選取涵蓋某個註腳／尾註的引用記號，而那個註腳本文裡有
`text:anchor-type="as-char"` 的 `draw:frame`」這個組合。在該組合上，出貨的範圍選取會讓
引擎執行緒停止回應，之後只有重啟 worker 能復原，未存檔內容遺失。**

> **2026-08-13 機制更正（不改變本節收窄的範圍）**：停止回應的不是選取，是**選取之後
> 出貨客戶端自動做的那次選取讀回**（`getState`／`getSelection` → `readSelection()`）。
> 選取之後引擎仍正常回應 `search`／`render`／`insertText`／**`save`（141 ms）**；
> 那次讀回逾時之後才永久停止回應。使用者可見的結果不變（出貨的 `selectRange` 自己會做讀回），
> **但「未存檔內容遺失」是產品的處置造成的，不是缺陷本身強迫的**——見
> [finding 038](../findings/038-a-frame-inside-a-footnote-wedges-the-engine-on-selection.md)
> 〈更正：殺死引擎的不是選取，是選取之後的讀取〉。

**這是覆蓋範圍之外，不是被證偽的結果。** C3 語料五份 ODT 的內容軸實際盤點：
`l0-t2-styled.odt` 有 1 個 as-char `draw:frame`、`l4-stress-100.odt` 有 100 個，
但**五份沒有任何一份含 `text:note`**——所以這個組合在語料裡不可能出現，
沒有任何一格記錄過的 PASS 因此變成錯的。判定依 034／035／037 的前例**重新界定而非撤銷**
（對照：022 是記錄結果被證偽→重建重跑；027 是綁定斷裂→STOP）。

> **2026-08-13 更正上面那個「101 個」**：那是**屬性**的數量，不是**行為**的數量。
> `l4-stress-100` 那 100 個 `draw:frame` **直接掛在 `office:text` 底下、不在任何段落裡**，
> 而 as-char 是「文字流裡的一個位置」，在那裡等於沒有意義。實測佐證：
> **`l4-stress-100` close 4 ms、`l0-t2-styled`（唯一一個在 `text:p` 裡的）close 10777 ms
> 走 recovery**（[finding 012](../findings/012-r6-styled-document-close-timeout.md) 的形狀）。
> **所以本語料對 012／037／038 那個構造的覆蓋是 1 個樣本，不是 101 個。**
> 這不改變 9.1 的收窄理由（那建立在「五份都沒有 `text:note`」上），
> 但它改變「語料對 as-char frame 覆蓋得不錯」這個印象——**沒有**。
> 兩個數字現在都釘在 `e1/content-axis-suites.json` 與
> `tests/test_content_axis_inventory.py` 裡，改動要是刻意的。

**已在出貨 artifact 上量到，不是跨 artifact 的推論**（`findings/evidence/sdk-e1/note-frame-select/`，
`835b453d…`，走出貨路徑 `editorSelectRangeV1`／`narrow-editor-v1`）：

| case | 形狀 | 結果 |
|---|---|---|
| `plain-full` | 沒有 frame 的段落 | `selectRange` 7 ms，事後可用 |
| `note-partial` | 註腳段落，選取**不**涵蓋引用記號 | `selectRange` 6 ms，事後可用 |
| `footnote-no-frame-full` | 註腳**沒有** frame，選取涵蓋引用記號 | `selectRange` 8 ms，事後可用 |
| **`note-full`** | **註腳有 frame，選取涵蓋引用記號** | **`selectRange` TIMEOUT 15004 ms，事後不可用** |

出貨的鍵盤選取（`extendSelection`，限 `move-character-left/right`）在同一個段落上
最終同樣不可用（2/2），但形狀不同：擴選全部成功、死在之後的讀取；該輪的純段落對照
**因為擴選越出段落進到表格而不乾淨**，已記在 finding 038 裡。

**因此本判定的效力範圍是：C3 語料涵蓋的內容軸。** 任何含註腳／尾註且註腳本文帶
as-char frame 的文件不在其內，在該缺陷修好之前也不會被納入。

**同族**：[037](../findings/037-a-paragraph-with-an-inline-image-wedges-the-handle.md)（後置條件讀取不返回，我方已擋）、
[012](../findings/012-r6-styled-document-close-timeout.md)（`destroy()` 不返回，SDK 以有界 close recovery 處理）。
三者的觸發都是 as-char 錨定的 frame。

### 9.2 發 GO 的必要輸入：語料內容軸盤點（2026-08-13 新增）

**任何 GO／PARTIAL GO 判定前，必須跑
[`tools/inventory_corpus_axes.py --check`](../wasm_sdk_probe/tools/inventory_corpus_axes.py)，
並把該次語料的內容軸盤點與盲區清單一併寫進判定。**

理由不是流程潔癖。034、035、037、038 是同一種失敗，而且**都不是「矩陣有一格沒跑」，
是「矩陣沒有這條軸，而且沒有人看得出它不在」**。9.1 這段收窄本身就是證據：
C3 五份語料帶著 101 個 as-char frame 與 0 個 `text:note`，所以 038 的組合
再跑一百次也不會出現。**這件事從測試清單上看不出來，從位元組上看得出來。**

工具做的事：把每份 fixture 的**容器 ×內容**共現格算出來（註腳／尾註／表格儲存格／
文字方塊／頁首頁尾／區段／清單項／註解／修訂 × 依錨定型別分開的 frame／圖片／標題／
清單／表格／…），加上文字腳本軸；`e1/content-axis-suites.json` 宣告每個驗證套件實際
跑過哪幾份文件，並把規格裡用文字寫的宣稱改寫成會失敗的斷言。**數字一律從位元組算，
不從文件抄。**

首次執行即發現一個**本規格先前沒有記載**的盲區：**C3 五份語料完全沒有 `text:list`／
`text:list-item`**（`text:h` 有 125 個）。目前出貨契約沒有清單動作所以無害；
**清單動作要進出貨契約之前，必須先補語料或依 9.1 的形式具名排除。**
**已補**：新 fixture `list-contexts`（第 5 節 C3），從下一次重綁起是 C3 的第六份。

**第二次修正來自另一個量測，而且修的是這個工具本身**（2026-08-13）：初版只數
**屬性**，於是把 `l4-stress-100` 那 100 個掛在 `office:text` 底下的
`draw:frame` 也算成 as-char——**它們的 close 是 4 ms，不是 10.8 秒**。
工具現在把 `frame-as-char-in-paragraph` 與 `frame-as-char-body-level` 分開算，
9.1 的數字已就地更正。**教訓寫在這裡而不是只寫在工具註解裡**：
一個從位元組算出來的數字仍然可能量錯東西——`draw:frame` 上有 `as-char`
不等於它是 as-char 錨定的。**盤點軸的定義本身也要有反例測試。**

## 10. 實作檔案

本輪新增：

- `wasm_sdk_probe/web/e1-editor-validation.html`
- `wasm_sdk_probe/web/e1-editor-validation-app.js`
- `wasm_sdk_probe/editor-shell/tests/editor-validation.test.mjs`
- `wasm_sdk_probe/tools/run_e1_c.py`
- `wasm_sdk_probe/tools/validate_e1_c.py`
- `wasm_sdk_probe/tests/test_e1_c.py`

本輪修改：

- `wasm_sdk_probe/editor-shell/editor-session.js`
- `wasm_sdk_probe/editor-shell/tests/editor-session.test.mjs`
- `wasm_sdk_probe/web/e1-editor.html`
- `wasm_sdk_probe/web/e1-editor-app.js`
- `wasm_sdk_probe/Makefile`
- `wasm_sdk_probe/README.md`
- `specs/SPEC-E1-000-overview.md`
- `specs/SPEC-E1-C-editor-validation.md`
- `DEVLOG-2026-08-05-wasm-sdk-e1.md`

LibreOffice Core未修改；machine evidence依第7節產生，不視為產品source。

## 11. 執行結果

### 11.1 已觀察

- C0～C4全部通過。Chrome 150／Firefox 153共48個browser cases：integration 6、recovery 12、corpus 10、
  lifecycle 20；所有輸出都通過ODT ZIP CRC／XML／anchor，16份required輸出再通過desktop LibreOffice reopen與
  PDF export。
- 每個browser完成10個bounded lifecycle session。Chrome process-tree記憶體成長29,467,648 bytes（1.80%），
  Firefox成長53,212,160 bytes（7.83%），均低於512 MiB及35%雙門檻。
- Chrome與Firefox各完成一次集中Fcitx5 Chewing人工run；trusted composition、selection replacement、cancel零
  mutation、trusted Ctrl+C／Ctrl+V及Clipboard API皆通過。兩份輸出ODT都包含四段required文字且取消字串為零。
- R6～R8、E1-A／B回歸與before／after workspace preflight全部通過；Core HEAD、既有dirty狀態及R5
  `writer-review` artifact未變。

### 11.2 推論與限制

- E1已形成可交付的**窄版ODT-first編輯器contract**：character caret／selection、Unicode文字、雙向delete、兩種
  break、public Undo、explicit bold／italic、plain-text clipboard、save及bounded recovery成立。
- 這不是完整Writer。Line navigation、Redo、drag／handles、paragraph／list、structural editing、DOCX、rich
  clipboard、Cangjie／Pinyin及完整content accessibility仍維持unsupported，不得由UI暗示已支援。
- 執行期間修正session舊generation drain競態與人工頁不可觀察性；兩者均以既有closed contract解決，未新增ABI、
  Core修改或編號finding。

### 11.3 判定

- Final summary：`automaticPass:true`、`complete:true`、`decision:E1_GO_ODT_EDITOR`。
- 未觸發停止或部分GO條件；E1完成。後續若擴增能力，需另立里程碑，不改寫本次凍結矩陣與證據。

### 11.4 後續失效（2026-08-06 起）

上面兩條敘述的是**當時**對**當時的 artifact** 成立的判定，保留原狀。此後 artifact 被重建三次，
每次都讓證據與出貨物脫鉤：

| 日期 | 重建原因 | 出貨 wasm | 裁決 |
|---|---|---|---|
| 2026-08-06 | finding 022：`set-bold` 可從陳舊快取回 `documented-state-noop` | `97e605ee…` | 全部相位＋人工輪重跑，回到`E1_GO_ODT_EDITOR` |
| 2026-08-07 | SPEC E1-D 範圍選取，新增匯出 | `69d4333d…`（完整摘要已佚失，見矩陣 `hashesCorrected`） | 未取證即被下一次重建取代 |
| 2026-08-07 | 底線／刪除線，contract 8→10 actions | `835b453d…` | 當時 **`E1_STOP_OR_RESCOPE`**；已於 §11.6 重跑收復為 `E1_GO_ODT_EDITOR` |

**2026-08-07 補上的閘門**：在此之前只有人工閘門會比對「證據自己記錄的 artifact hash」與
`dist/profiles/e1-editor-v1/` 的現況；四個自動相位不比對。後果是重連結會依構造作廢人工輪，
卻讓 48 個瀏覽器 case 靜靜存活，於是驗證器能報出 `E1_PARTIAL_GO_ODT_EDITOR` —— 而那個裁決的
語意正是「機器相位描述的就是出貨物，只缺 trusted input」，當時並不成立。

`validate_e1_c.artifact_binding()` 把每個自動 case 綁到現場 profile，並作為 `decide()` 的第七個
自動要件；沒有記錄 artifact 的證據同樣不綁定。加上之後首次執行：48 個 case 全部 superseded、
0 綁定，其餘六項屬性仍通過，裁決 `E1_PARTIAL_GO_ODT_EDITOR` → `E1_STOP_OR_RESCOPE`。

**這不是新發現的編輯器缺陷**，是同一筆重建成本被完整計入。回到 GO 需要：雙瀏覽器四個自動相位
（`python3 tools/run_e1_c.py --browser <name>`）＋各一輪人工 Chewing，全部對 `835b453d…`。

### 11.5 重跑自動相位時撞上 finding 023（2026-08-07）

依 §11.4 重跑，**兩個瀏覽器都在 lifecycle 相位死掉**：Chrome 於 `cycle-06`、Firefox 於
`warmup-08`，皆為 `init timed out after 120000 ms` —— 與 2026-08-06 那次**同樣兩格**。

綁定結果：`boundCases 33`、`supersededCases 14`、`unattributableCases 1`
（Chrome `cycle-06` 因 init 從未完成而沒有 artifact 可記，正是「無從歸屬」那一類）。

歸因實驗完成，見 [finding 023](../findings/023-sdk-init-wedges-at-fixed-session-depth.md)：
同一個瀏覽器 session 反覆導覽到固定深度後，SDK init 永久卡住。**同一種工作量深度固定、
逐次重現**（Firefox 22／26、Chrome 30／34），且失敗前完全沒有劣化。判別階梯以三個對照
rung 各 60/60 通過，排除主機負載、瀏覽器／driver、worker 汰換與 `SharedArrayBuffer`。

矩陣原本把它記成「主機負載偶發」並以「單獨重跑 lifecycle 就全過」佐證 —— 該歸因已撤回。
lifecycle 單跑只有 20 次導覽，低於觀察到的每一道牆，那次重跑**從未靠近過限制**。

**對 E1-C 的後果**：在 finding 023 解決之前，四個自動相位無法在單一 session 內跑完，
`E1_GO_ODT_EDITOR` 拿不到。若要改成「每 N 個 case 換一個瀏覽器 session」，必須在矩陣裡
明寫它掩蓋了什麼 —— lifecycle 相位存在的理由正是證明反覆開檔有界，而這正是卡住的東西。

### 11.6 收復：對 `835b453d…` 重跑完畢，裁決回到 `E1_GO_ODT_EDITOR`（2026-08-07）

[finding 023](../findings/023-sdk-init-wedges-at-fixed-session-depth.md) 修復（harness 的三條無人讀取的
pipe）之後，§11.4 要求的重跑全數完成，全部對出貨 artifact `835b453d…`（contract 8→10 actions，
新增 `set-underline`、`set-strikethrough`）：

| | 結果 |
|---|---|
| 四個自動相位 | `automaticPass: true`、`complete: true` |
| artifact 綁定 | **`boundCases: 48`、`supersededCases: 0`、`unattributableCases: 0`** |
| 人工 Chewing | Chrome 23:41、Firefox 23:48，**兩份各九項檢查全過** |
| 裁決 | **`E1_GO_ODT_EDITOR`**、`failedProperties: []` |

人工輪兩份證據自記的 `wasmSha256` 都是 `835b453d…`／10 actions；四段 required 文字各命中一次、
取消字串零出現（`cancelledCount: 0`）；`operatorConfirmedChewing`、`trustedComposition`、
`trustedNativeCopy`、`trustedPaste`、`cancel`、`clipboardWrite`、`clipboardRead`、`artifact`、
`output` 九項皆 `true`。回歸 `make test-e1-c-static` 62 pass／0 fail。

兩點附帶結論：

- **attempt-02 的 Chrome `trustedPaste: false` 未再現**（本輪 `true`）。當時記的待驗證
  「若操作者確認在 sink 內按 Ctrl+V 仍為 false 就升格 finding 候選」**不成立，該候選關閉**——
  是焦點不在 SDK sink，不是 Chrome 特有問題。
- Firefox 第一次提交未送達伺服器（磁碟檔未變、`preserve_previous()` 也沒產生新世代，
  故可判定 POST 從未進來，而非內容被擋）；操作者重做後落地。屬操作插曲，不改判定。

§11.2 的限制清單是 2026-08-05 當時的凍結敘述，保留原狀；**現行 contract 為 10 actions**，
底線與刪除線已出貨並在本輪綁定範圍內。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。凍結E1-B×R7整合、五份ODT、recovery／lifecycle、最小headed gate及E1最終判定。 |
| 2026-08-05 | v2。回填48個browser cases、16份desktop round-trip、雙browser headed pass與`E1_GO_ODT_EDITOR`。 |
| 2026-08-06 | v3（補記）。finding 022 迫使重建，全部相位與人工輪對`97e605ee…`重跑，仍為`E1_GO_ODT_EDITOR`。 |
| 2026-08-07 | v4。新增§11.4。E1-D與底線／刪除線兩次重連結；補上自動相位的artifact綁定閘門，裁決降為`E1_STOP_OR_RESCOPE`。 |
| 2026-08-07 | v5。新增§11.5。重跑自動相位撞上finding 023（session深度固定後SDK init卡死）；撤回「主機負載偶發」歸因。 |
| 2026-08-07 | v6。新增§11.6。finding 023修復後全部相位＋雙瀏覽器人工輪對`835b453d…`重跑完畢，48/48綁定、0 superseded，裁決回到`E1_GO_ODT_EDITOR`；關閉Chrome `trustedPaste`的finding候選。 |
| 2026-08-08 | v7。更正 Worker generation 上限的**語意**：規格原本寫「每頁」，但產品唯一實作的是每個 `EditorSession` 的崩潰／boundary 回復次數（`maxWorkerGenerations`，預設 3）。**產品維持 3，「每頁」承諾撤除**（無實作，且 finding 014 撤回後無已量測理由）。條文與註記已就地修訂；未動任何閘門，判定不變。見 finding 026。 |
| 2026-08-12 | 9.1 具名收窄（[finding 038](../findings/038-a-frame-inside-a-footnote-wedges-the-engine-on-selection.md)）。判定**不涵蓋**「選取涵蓋註腳／尾註引用記號，且該註腳本文含 as-char `draw:frame`」；在該組合上出貨的範圍選取會讓引擎停止回應，只有重啟 worker 能復原。**覆蓋範圍之外而非被證偽**——C3 五份語料盤點：`l0-t2` 1 個 as-char frame、`l4-stress-100` 100 個，但**五份都沒有 `text:note`**，所以該組合不可能出現，沒有任何記錄過的 PASS 因此變錯；依 034／035／037 前例重新界定而非撤銷。**已在出貨 artifact `835b453d…` 上實測**（走 `editorSelectRangeV1`／`narrow-editor-v1`，四格：無 frame 段落 7 ms、不涵蓋引用記號 6 ms、註腳無 frame 8 ms 皆事後可用；**涵蓋引用記號且註腳有 frame → TIMEOUT 15004 ms、事後不可用**），在此之前是跨 artifact 推論，由外部覆核指出並要求在動修法之前補量。48 個綁定不重跑：這是補充覆蓋，不是重新驗證。 |
| 2026-08-13 | 新增 9.2：**發 GO 前必跑語料內容軸盤點**（`tools/inventory_corpus_axes.py --check`），盲區清單須寫進判定。工具首跑即補到一個本規格先前沒記載的盲區：**C3 五份語料沒有任何 `text:list`／`text:list-item`**。9.1 手寫的兩項語料事實（0 個 `text:note`、101 個 as-char frame）改由 `tests/test_content_axis_inventory.py` 每次檢查。未動任何閘門，判定不變。 |
| 2026-08-13 | C3 新增第六份 `list-contexts`（第 5 節），**下一次重綁起生效，不追認既有判定**：盤點檔分成 `E1-C-C3`（判定實際跑過的五份，`list` 釘 absent）與 `E1-C-C3-next`（六份，`list` 釘 present）。fixture 放在 `test-docs/e1/`，不碰 R7 corpus source bytes；`styled-list` 不能代替（錨點緊鄰既有清單會合併，SPEC-E2-A 第 11 節）。已驗：既有 14 份 fixture 對 git HEAD 逐份位元組相同、原生 LOK 開得起來且 `E1-LC-ISOLATED` 讀得回、desktop round-trip 後兩種清單樣式都還在。 |
| 2026-08-13 | 9.1 的「101 個 as-char frame」**就地更正為「屬性 101、有效 1」**：`l4-stress-100` 那 100 個掛在 `office:text` 底下不在段落裡，實測 close 4 ms，而 `l0-t2-styled` 唯一一個在 `text:p` 裡的 close 10777 ms 走 recovery。收窄理由不變（建立在「五份都沒有 `text:note`」上），改變的是「語料對這個構造覆蓋得不錯」的印象。盤點工具同時修正（新增 `frame-as-char-in-paragraph`／`-body-level` 兩軸與反例測試）。未動任何閘門，判定不變。 |
| 2026-08-14 | **v8。§4.1／C2 的 crash 恢復性質就地修訂（外部裁決代使用者決策，使用者授權）。** 起因：任務 #33（`68227e1`）出貨「選取手勢前 checkpoint ＋ `restart()` 可自 checkpoint 重開」，與原文「Crash前未保存內容不恢復」**正面矛盾**；且 `crash-unsaved` 那一格現在靠**腳本形狀**變綠——它沒有做選取手勢所以 checkpoint 不 arm——**不管 resurrect 語意怎麼改它都會綠**，是一個打不開的檢查。矛盾與這一格的性質是外部覆核在 `shell-change-recheck` 那一輪挑出來的。**採 (A)：修訂條文＋新增會變紅的格**；否決 (B)「判 resurrect 違反凍結範圍、要求顯式徵詢」——`restart({source})` 這類選源 API 會擴 closed contract（§3 底線），而在這個形狀下的徵詢是**答案恆為是的對話框**，不是同意；(B) 是 (A) 的規格工作全集再加產品工作與更多要凍的格，買到的事前同意在揭露充分之下沒有安全增量。**新性質**＝只能重開引擎 save 出的 bytes（authority／checkpoint 取 content stamp 較新者）、自 checkpoint 重開必標 dirty 且揭露 `hasCheckpoint`、checkpoint 永不寫入 authority、顯式 save 後 checkpoint 作廢、checkpoint 失敗須進 typed state。**否決 (B) 的承重事實已逐條在程式碼核對**（不是轉述）：`_authorityBytes` 全檔只有 `open()`（`editor-session.js:87`）與 `save()` finalize（`:440`）兩個賦值點；restart 選源為 `dirty: useCheckpoint`；save finalize 已會作廢 checkpoint；`_checkpointError` 確實從不進 state。**矩陣 v2**：新增 `crash-after-checkpoint`（每瀏覽器 recovery 6→7 格，48→50），`crash-saved` 加「arm checkpoint」步驟與「save 後 `hasCheckpoint === false`」assertion，`crash-unsaved` **原格與腳本逐字保留**、效力具名限縮為「未 arm 選取手勢的順序」（刪掉它才是放寬——它仍是「無 checkpoint 時未保存內容不得回來」的唯一瀏覽器級證據）。**兩條強制附款**：(一) checkpoint 失敗必須進 typed state（`checkpointError`），否則 `recovery-notice.js` 會把「沒東西可救」與「試過保存但失敗」混為一談、對保存失敗的使用者沉默；(二) **殼層 bundle hash 納入 per-case 綁定與 preflight**——這次矛盾能出貨整整一天而所有自動閘門綠著，唯一原因是殼層對三個 artifact hash 隱形。**零新增人工項目**（checkpoint 語意與 `isTrusted` 無涉，合成事件即可）。**無任何既有格被削弱、改寫或刪除，矩陣只增不減**，§5 不得放寬那一關正面通過。#39 的成本數據支持不動 5000 ms 期限：穩態 71–128 ms、不隨頁數成長，最差 first-save 661 ms 有 7.5 倍餘裕。全部**生效於下一次重綁**。**本列有一處超出裁定逐字範圍並在此標明**：裁定只引了 §4.1 與 C2 的三行，而同段「fresh Worker 只重開 authority bytes」是同一個矛盾的第四行，我依同一原則一併修訂。 |
| 2026-08-14 | **v9。重綁完成，判定重發 `E1_GO_ODT_EDITOR`，涵蓋由三個雜湊擴為四個**（新增殼層 bundle `f9b1a52f…`）。證據樹 `editor-validation-v2/`：50/50、`boundCases 50`／`superseded 0`／`unattributable 0`、八個屬性全真、`automaticPass: true`。人工輪兩瀏覽器同一 operator 時段完成，錨點數恰好 1／1／1／1，取消字串 0 次。**v8 上午那個「不涵蓋 08-13 之後殼層」的具名界定由新綁定取代。** 前一輪（08-07、三個雜湊）的證據樹與 `validation-matrix-v1.json` **原封保留，未覆寫**。<br>**`regression` 屬性修復（外部裁決，含 `-o Makefile` 對照實驗）**：原實作經 `test-e1-c-static → e1-editor-validation-assets` 相依 build 樹 mtime 自洽，而 `Makefile:486` 把 `Makefile` 自己列為每個目的檔的相依——**凍結期間唯一可達值為 false，且唯一變綠路徑是重連結凍結 artifact，也就是這個屬性存在就是為了防止的那件事**。它已被 08-12 那次重編不可恢復地釘死，與此後誰碰不碰 Makefile 無關。08-07 的 `regression: true` 之所以成立，是因為整棵 build 樹幾小時前剛全部重建、mtime 恰好自洽。**修法四項，缺一不成立**：(一) `test-e1-c-static` 去除資產相依、**配方本體逐位元組保留**；(二) **新增 `test-e1-c-frozen-guard`**——`make --always-make -n build/e1/editor-v1/probe.js` 必須印出 `refusing to relink a frozen profile`，與 mtime 拓撲完全無關，**實測拿掉防護即紅、還原即綠**，這把舊相依那個「反向訊號」換成正向斷言，是淨收緊；(三) `test-r8-c-static` 去除 `.PHONY` 資產鏈副作用（[finding 041](../findings/041-static-test-targets-build-and-mint-through-a-phony-asset-chain.md)：`--run-regression` 每跑一次鑄一個 release id，實測修後 `release-manifest.json` 雜湊不變）；(四) `manual_gate` 兩項收緊——錨點判準由 `>= 1` 改 **`== 1`**（§6 項目 5 寫的是 exact，兩瀏覽器實測全為 1），並**補上人工輸出的 desktop reopen**（§6 項目 5 字面既有落差，**前每一次 GO 都沒執行過**；實測兩份各 38999 bytes PDF，pass）。**沒有任何檢查被刪除或削弱。** 另記一條程序 deviation：人工輪是在 `regression` 紅著時先跑的（§8 說 C4 未過不得要求人工驗收）；該條保護的是 operator 時間與「人工不得推翻 machine stop」，此處兩者皆未發生，證據完整且綁定，**記錄在案、不重跑人工**——為治癒一條順序註記而再叫 operator 才違反節制條款。 |
