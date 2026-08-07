# SPEC R7-C：ODT／DOCX 文件相容性 corpus

> **日期**：2026-08-02  
> **狀態**：完成（`PARTIAL_GO_ODT_FIRST`；28份corpus跨瀏覽器與desktop fidelity通過，DOCX unsupported）  
> **上層規格**：[SPEC R7-000](./SPEC-R7-000-overview.md)  
> **前置閘門**：[SPEC R7-A](./SPEC-R7-A-discovery-corpus.md) GO 或 ODT-first 部分 GO；
> [SPEC R7-B](./SPEC-R7-B-input-clipboard.md) 已完成並留下 GO／部分 GO／停止判定

## 1. 目標

以凍結 manifest 的逐檔 corpus，驗證 `writer-review` 對真實 ODT／目標 DOCX 的 open、render、search、
semantic inspection、ODT save 與 desktop round-trip。結果要能回答「哪些文件可安全使用、哪些會明確降級、
哪些必須 typed reject」，而不是只有總通過率。

DOCX v1 的 round-trip 定義為 **DOCX import → 公開 SDK 操作 → ODT save → desktop open/PDF**；本規格不承諾
DOCX re-export。

## 2. Corpus 分層

### L0：既有 regression

- `t1-plain-zh.odt`：中英／繁中、搜尋、輸入與主要 save。
- `t2-styled.odt`：標題樣式、表格、圖片、註解、三頁；同時追蹤 finding 012。
- `t3-long.odt`：22 頁、長 viewport、重複 anchor與 memory基線。

### L1：R7 自有 deterministic pairs

由 desktop LibreOffice固定腳本產生 ODT與DOCX source pairs，至少包含：

- plain CJK／Latin／Unicode；
- heading／paragraph styles、分頁與頁首頁尾；
- merged／nested table；
- inline／anchored PNG；
- comment thread與 tracked changes；
- hyperlink／bookmark；
- declared missing font與可用 CJK fallback；
- 100 頁含圖片 stress文件（只供 R7-D，不納入每次完整 C matrix）。

生成器需固定 source text／image、LibreOffice版本、filter name與預期 anchors；ODT／DOCX bytes不要求 bit-identical，
但 manifest每次接受新 hash都要有原因。

### L2：LibreOffice QA allowlist

從 R7-A 候選選少量已知 feature文件，保留來源 commit、相對路徑、MPL-2.0 provenance、完整 hash與上游測試
意圖。不得把 3,000+份 QA文件全部計入分母，也不得只挑最後成功者。

初始 feature目標為 comments、redline、image、embedded font、hyperlink各至少一份ODT與可用時一份DOCX。

### L3：deterministic negative

- ODT／DOCX truncation、bad central directory、缺必要 XML、格式與宣告不符；
- random/non-Office bytes、超過 size ceiling、entry count／uncompressed ratio超限；
- encrypted／macro-enabled／外部依賴文件若未支援，使用最小可合法分享fixture並預期 typed unsupported；
- derived case必須記 parent SHA與生成recipe，不手工破壞後只留結果。

### L4：stress

100頁含圖片、目標上限附近檔案與重複物件文件，由 R7-D使用；C先驗證其結構、desktop baseline與單次
open/render/search/save，避免把壞生成器帶進longevity。

## 3. Format discovery 與 capability

- R7-A 先證明 DOCX content detection在固定 `.odt` MEMFS路徑下的實際行為。
- 未通過前，manifest與SDK capability仍只有 `open-odt`；UI對DOCX顯示 experimental／unsupported，不能
  依副檔名假裝成功。
- 若只需讓 allowlisted format產生安全副檔名，提案應是 `format: "odt" | "docx"`或等價closed taxonomy，
  並驗證 path traversal／NUL／超長name；不得公開任意 MEMFS path。
- 若需窄SDK ABI minor bump，先以既有artifact做A/B evidence、更新manifest／compatibility tests並取得執行
  決策；不修改 LibreOffice core。
- 若 `full-qa` 可開而 `writer-review` 不可開，記為profile/filter reachability輸入，R7-C可部分GO ODT-first；
  不直接把 full-qa當產品artifact，也不在R7裁切／重連結core。

## 4. 每份文件的測試流程

### 4.1 Preflight

1. 驗證 manifest schema、bytes、SHA-256、media type、ZIP limits、XML與禁止內容。
2. Desktop LibreOffice以隔離profile開啟原始文件，記錄成功／錯誤、頁數、PDF與semantic baseline。
3. 若desktop baseline本身失敗，分類為fixture invalid；不能拿來判WASM regression。

### 4.2 WASM open／render／inspect

1. 每份文件用全新 Document Worker與明確timeout開啟。
2. 驗證document dimensions／parts、first tile、首／中／末viewport與至少兩個zoom。
3. 對manifest anchors做found／count／selection text；不解析未承諾search rectangles。
4. 能力適用時執行`listComments()`／`listTrackedChanges()`；記錄數量與安全欄位，不解析raw internal IDs。
5. image／table／style以結構validator與指定render region雙重檢查；pixel image不是唯一真相。
6. close並確認無late callback／canvas mutation；finding 012 sequence另列，不能污染正常流程統計。

### 4.3 Mutation／ODT save

- 只對manifest標記`mutationAllowed=true`文件執行窄semantic operation：固定selection replace或append fixture
  text；使用revision guard、save ODT、保留source與output。
- DOCX source保存結果永遠命名／標示ODT；UI不得下載成`.docx`。
- Save後驗證ZIP CRC、所有XML、anchor counts、media entries、styles、comment／redline expectation與禁止字串。
- Desktop LibreOffice以隔離profile開啟output ODT並轉PDF；任何filter repair dialog／stderr／timeout都保存。

## 5. Fidelity 分類

每份文件分開判四層：

| 層 | 必要證據 | 判定示例 |
|---|---|---|
| content | anchors、Unicode code points、段落／table cell文字 | loss／duplicate為fail |
| structure | ZIP/XML、styles、media、comments、redlines、relationships | 必要object遺失為fail |
| layout | page count、landmark region、desktop PDF與WASM tile | 可解釋reflow或fail |
| font | manifest要求、resource packs、fallback與glyph evidence | exact／degraded-known／silent-unknown |

- screenshot／PDF diff使用固定viewport、scale、fonts與容許遮罩；threshold由R7-A以control fixtures凍結。
- 不要求不同browser像素完全相同；同一文件的content／structure expectation必須相同。
- missing font若沒有公開font inventory，只能標`degraded-known`或`not-observable`並輸入R8；不可標full fidelity。
- DOCX兼容差異要判斷是desktop import本身、WASM resource pack、filter不在profile或save-to-ODT造成，不把
  所有差異歸成「瀏覽器問題」。

## 6. Typed error taxonomy

R7 application至少能表達：

| Code | 意義 | Mutation |
|---|---|---|
| `UNSUPPORTED_FORMAT` | allowlist外格式／macro／encryption | 0 |
| `CORRUPT_DOCUMENT` | preflight已確認ZIP／必要part損壞 | 0 |
| `DOCUMENT_TOO_LARGE` | compressed／expanded／entry／pixel上限超標 | 0 |
| `DOCUMENT_OPEN_FAILED` | engine拒絕但無法安全細分類 | 0 |
| `DOCUMENT_OPEN_TIMEOUT` | 到達預註冊timeout | 0；terminate Worker |
| `DOCUMENT_DEGRADED` | 可開但有manifest已知fidelity限制 | 依policy保持read-only或明確同意 |
| `SAVE_VALIDATION_FAILED` | output結構／anchor／hash gate失敗 | 不發布；保留bytes |

Preflight可以分類的錯誤不得全部包成`LOK_ERROR`；engine未知錯誤也不能捏造為corrupt。錯誤details不得含
host path、stack、raw callback或文件內容。

## 7. Browser／corpus matrix

- L0：Chrome／Firefox各3次，完整open/render/search/mutation/save/close。
- L1代表集（plain、table+image、comment+redline各格式）：Chrome／Firefox各3次。
- 其餘L1／L2 allowlist：兩browser各至少1次；任何flaky item追加到3次並保留所有失敗。
- L3每個negative case：兩browser各1次deterministic run，之後同Worker建立新engine開t1以證明可恢復。
- L4：兩browser各1次單次功能流程，再交R7-D長時間測試。
- 每份成功source／output都做desktop round-trip；DOCX source與ODT output的baseline分開。

## 8. Metrics 與 machine summary

逐檔至少記錄：

- corpus ID／source／hash／bytes／features、artifact/resource hashes、browser／desktop版本；
- preflight、open、first tile、各viewport、search、semantic list、save、close時間；
- page/dimensions、tile count／cache peak、Worker error／restart；
- content／structure／layout／font各層結果與degradation reason；
- source/output ODT／DOCX／PDF hash與validator結果；
- typed error、timeout stage、recovery與是否建立finding。

證據路徑：

```text
findings/evidence/sdk-r7/corpus/
findings/evidence/sdk-r7/browser/compatibility/<browser>/
findings/evidence/sdk-r7/roundtrip/odt/
findings/evidence/sdk-r7/roundtrip/docx-import/
findings/evidence/sdk-r7/negative/
findings/evidence/sdk-r7/compatibility-summary.json
```

## 9. 驗收與判定

**GO**：manifest所有required ODT／DOCX在Chrome／Firefox通過逐檔content／structure gates；layout/font差異皆
在預先允許範圍且可解釋；成功output可desktop open/PDF；negative全部typed、零mutation且Worker可恢復；
沒有silent repair或未記錄degradation。

**部分 GO（ODT-first）**：ODT required corpus完整通過，但DOCX因固定副檔名、filter reachability或不可接受
fidelity無法形成產品承諾。UI／manifest明確拒絕或標experimental，保留DOCX evidence供後續profile決策，
不阻擋R7-B與ODT viewer主線。

**停止回報**：required ODT內容／結構silent loss、錯文件format卻成功另存、negative造成不可恢復crash／hang、
同bytes跨run非決定性套用錯內容、或修正需要raw UNO／unoembind／core tracked change。保存source、失敗output、
tiles、event/stage與desktop比較，立即建立finding。

## 10. 交付物

- 凍結corpus與manifest validator、deterministic generator／negative recipes。
- Chrome／Firefox逐檔evidence、ODT／DOCX-import round-trip與typed-error summary。
- fidelity分類報告與R8 font/delivery、R10 filter/reachability輸入。
- DOCX capability決策：GO、experimental／部分GO或unsupported。

## 11. 執行結果

- 2026-08-03 已建立並凍結28份L0～L4 corpus、typed ZIP/format preflight、Chrome／Firefox browser runner、
  desktop baseline/fidelity validator與ODT-first Reference App；corpus validator 28/28及靜態測試全通過。
- L4 100頁fixture、L3 negative與DOCX finding 013 typed unsupported均已納入machine manifest。
- Finding 012 bounded Worker recovery完成後已執行正式matrix。Chrome repeat 3/3＋full 1/1、Firefox repeat
  3/3＋full 1/1全部通過；Firefox以每個邏輯group單一browser process、每頁Worker budget 3分批，完整case覆蓋
  仍由aggregate exact-ID gate驗證。
- 原始`Del 16`是tracked-deleted文字，不適合作public selection anchor，改用唯一可見`Lorem ipsum`；L3 ratio
  fixture也由1 MiB修正為8 MiB，使實際ZIP ratio約337並確實越過預註冊200門檻。失敗嘗試均保留。
- corpus 28/28、兩瀏覽器、desktop source baseline、fidelity matrix與DOCX typed unsupported六項gate全通過。
- **判定：`PARTIAL_GO_ODT_FIRST`**。ODT內容／結構／round-trip成立；DOCX仍依finding 013明確unsupported，
  不宣稱DOCX import能力。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。定義分層ODT／DOCX corpus、DOCX→ODT round-trip、fidelity分類與typed negative gates。 |
| 2026-08-03 | v2。記錄corpus／runner完成，但因B manual pending與R7-D normal close停止而未跑正式matrix。 |
| 2026-08-04 | v3。remediation後完成Chrome／Firefox正式matrix與desktop fidelity；判定ODT-first部分GO。 |
