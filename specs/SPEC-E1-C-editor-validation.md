# SPEC E1-C：窄版 ODT Editor 整合與產品驗證

> **日期**：2026-08-05  
> **狀態**：現行裁決 **`E1_GO_ODT_EDITOR`**（2026-08-07 23:48，對出貨 artifact `835b453d…`／10 actions）——
> 曾三度判定 GO（2026-08-05、2026-08-06、2026-08-07）。中間因 E1-D 範圍選取與底線／刪除線兩次重連結
> 一度降為 `E1_STOP_OR_RESCOPE`，重跑期間又撞上 finding 023；兩者皆已結案。
> 沿革見 §11.4／§11.5，收復經過見 §11.6。  
> **前置閘門**：[E1-B](./SPEC-E1-B-narrow-editor-contract.md) 已完成並判定`GO_TO_E1_C`  
> **凍結矩陣**：[`validation-matrix-v1.json`](../wasm_sdk_probe/e1/validation-matrix-v1.json)
> **最終證據**：[`summary.json`](../findings/evidence/sdk-e1/editor-validation/summary.json)

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
- Finding 012已有bounded Worker recycle；Finding 014限制Firefox同頁面大量建立大型WASM Worker。E1-C必須每頁
  最多使用三個Worker generation，達上限前明確reload整個頁面。
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
- Crash前未保存內容不恢復；crash前已保存authority可重開；pending composition與queued input不重播。

### 4.2 明確不承諾

- Cangjie／Pinyin、行動／觸控IME、rich clipboard、圖片貼上與拖放。
- Line up/down/home/end、Redo、滑鼠拖曳selection handles、段落／heading／list格式。
- 表格結構、圖片、shape、註解或修訂內容的結構編輯；corpus內這些物件只驗證旁側安全文字編輯不破壞原內容。
- DOCX open／save、多人同步、autosave、完整document-content accessibility與完整Writer toolbar。

## 5. 自動測試矩陣

數量與項目以`validation-matrix-v1.json`為準，正式結果產生後不得放寬。

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
- fresh Worker只重開authority bytes，boundary action與queue不重播；
- composing、queued mutation、unsaved local edit、saved authority四個crash barrier；
- unsaved內容明確不可恢復，saved authority可恢復，舊handle／舊generation結果不可污染新session；
- 每頁Worker generation上限為3，達上限前要求完整page reload，不以無界restart規避Finding 014。

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
