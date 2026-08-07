# SPEC R7-000：真實輸入、文件相容與可用性 corpus

> **日期**：2026-08-02  
> **狀態**：完成（`PARTIAL_GO_ODT_FIRST`；正式判定見 `findings/evidence/sdk-r7/summary.json`）  
> **依據**：[R6 GO](./SPEC-R6-000-overview.md)、[R6+ roadmap](./SPEC-R6+-roadmap.md)

## 1. 目標

R7 將 R1～R6 的固定 probe fixture 擴成可解釋的產品風險 corpus，回答四個問題：

1. 真實作業系統 IME 經 host UI 進入公開 Document SDK 時，是否不重複、不漏字，cancel 是否零 mutation？
2. 純文字 clipboard 在授權、拒絕與取消情境下，是否維持明確的 user intent 與 typed error？
3. 目標 ODT／DOCX corpus 能否穩定 open、render、search，並以既有 ODT save surface 保存可驗證結果？
4. viewer 的基本鍵盤、頁面定位、超連結與長時間 Worker lifecycle 是否可用且沒有無界記憶體成長？

R7 不以「能開一份文件」代表相容，也不以 synthetic composition event 代表真 IME。每份文件與輸入案例都要有
manifest、預期語意、失敗分類、原始證據與可重跑閘門。

## 2. 已觀察的進場基線

- R6 最終判定 GO；R5 `writer-review` loader／WASM SHA-256 為
  `35d96f…c63566`／`ba257b…dfc6`，core HEAD 為
  `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`。
- 公開 SDK 已有 `click()`、`insertText()`、search／selection、revision-guarded replace／undo、comment／
  tracked changes、ODT save、cancel、close 與 Worker restart。
- `insertText()` 目前以 LibreOfficeKit `paste(text/plain;charset=utf-8)` 為主，失敗時才逐 Unicode code point
  `postKeyEvent`；它不是 composition API，也沒有 preedit／cancel contract。
- `OpenOptions.name` 已存在且 C ABI 會收到 name，但目前 `writeInputFile()` 一律將 bytes 寫成
  `/tmp/oxsdk-input-<request>.odt`。因此 DOCX 是否能靠 content detection 正確開啟尚未驗證，不能先新增
  `open-docx` capability。
- 現有專案 corpus 只有 `t1-plain-zh.odt`、`t2-styled.odt`、`t3-long.odt`；分別涵蓋純文字、樣式／表格／
  圖片／註解與 22 頁長文件。LibreOffice QA tree 另有約 1,101 份 Writer ODT、2,101 份 Writer DOCX，
  只能經 allowlist、來源／授權／hash manifest 挑選，不能整批當成通過宣稱。
- 本機環境為 Wayland，Fcitx5 正在執行，目前 input method 是 Chewing；系統另已安裝 Cangjie、Pinyin 與
  Chinese addons。Chrome 150、Firefox 152、geckodriver、自製 CDP/WebDriver runner、`psutil`、Orca、
  桌面 LibreOffice 26.2.4.2 與 PDF／ZIP 工具均可用；未安裝 Playwright，但 R7 不需要為此新增依賴。
- finding 012 的 `t2-styled.odt` 特定 discovery 操作組合 close timeout 仍開放；R7 長時間測試必須把它
  當已知風險追蹤，不可用 quarantine 隱藏一般 close leak。

以上「已觀察」只形成 discovery 假設；R7-A 必須用固定命令與 evidence 重驗後才能升格為 R7 執行結論。

## 3. 不可退讓的邊界

- 優先沿用 R5 `writer-review` artifact 與 R6 Worker／reader shell；R7-A 不重建 artifact、不修改
  `libreoffice-26-8`。
- 若窄 SDK adapter 變更已足夠，維持在 `wasm_sdk_probe`；需要 core tracked change、raw UNO、unoembind、
  任意 `.uno:*`、macro 或未承諾 callback 才能完成時，停止該路徑並建立 finding。
- IME composition 由 host 擁有 DOM composition buffer；只有確定 commit 的 Unicode 字串可呼叫公開
  `insertText()`。preedit、cancel 與 late event 不得送入文件。
- clipboard v1 只接受 `text/plain`。不允許 generic HTML paste、任意 MIME、`execCommand` 或把 browser
  clipboard 權限當成文件 mutation 權限。
- DOCX v1 只研究 import/open；公開 save surface 仍是 ODT。DOCX → ODT → desktop/PDF 可作 round-trip，
  不把它描述成 DOCX re-export。
- corpus 不能含未授權的使用者文件、secret、macro、外部連結依賴或未設上限的壓縮炸彈。所有來源都需
  hash、大小、media type、預期 feature 與授權／生成方式。
- synthetic browser event、CDP `insertText` 或 WebDriver `sendKeys` 只能驗證 host state machine，不能標成
  真 OS IME 證據；真 IME 與真 clipboard 必須有 headed browser 人工 evidence。
- 版面差異要區分內容遺失、結構變化、字型 fallback 與可接受像素差；不得只用單一 screenshot 肉眼判定。

## 4. 子 spec 與執行順序

| Spec | 內容 | 完成訊號 |
|---|---|---|
| [R7-A](./SPEC-R7-A-discovery-corpus.md) | artifact／API gap、IME／clipboard 可測性、DOCX open spike、corpus manifest 與 memory 基線 | discovery GO／部分 GO／停止，凍結 R7 corpus 與閘門 |
| [R7-B](./SPEC-R7-B-input-clipboard.md) | host composition state machine、真 IME、Unicode 與純文字 clipboard | Chrome／Firefox 自動契約＋headed 人工輸入通過 |
| [R7-C](./SPEC-R7-C-document-compatibility.md) | ODT／DOCX corpus、typed failure、結構／語意／版面與 desktop round-trip | corpus matrix 有逐檔判定，DOCX scope 明確 |
| [R7-D](./SPEC-R7-D-usability-longevity.md) | 鍵盤／accessibility spike、頁面／超連結、100 頁與長時間 memory／Worker lifecycle | usability 限制可解釋，memory 閘門通過 |

執行順序固定為 **R7-A → R7-B → R7-C → R7-D**。A 的 corpus manifest、typed error taxonomy、
memory 閾值與 manual/automatic evidence 分類凍結後，B～D 才可實作；不得在看到結果後回頭放寬門檻。

## 5. R7 v1 範圍

### 5.1 輸入

- Fcitx5 Chewing／Cangjie／Pinyin 的真實 composition commit、cancel 與連續輸入。
- 全形標點、BMP／astral Unicode、emoji、ZWJ sequence、combining mark 與換行。
- host UI 到 SDK 的單次 commit、序列化 mutation、revision 與 ODT 保存驗證。
- Clipboard API 的純文字 copy／paste、權限拒絕、空內容、取消與頁面失焦。

### 5.2 文件相容

- 既有 t1／t2／t3、R7 自有 deterministic ODT／DOCX feature fixtures、少量 LibreOffice QA allowlist。
- 多頁、樣式、表格、圖片、註解、修訂、hyperlink、embedded／missing font。
- 損壞 ZIP、格式與副檔名不符、超過上限、加密／不支援格式的 typed failure。
- open／render／search／list semantic objects／ODT save，以及桌面 LibreOffice open／PDF evidence。

### 5.3 Viewer usability 與 longevity

- host controls 的鍵盤順序、focus、label、status announcement 與基本 accessibility tree。
- 頁面位置、搜尋結果定位與 hyperlink spike；缺少公開 geometry／target 時明確降級。
- 100 頁含圖片 fixture、重複 open／render／close、Worker crash／restart、30 分鐘 soak 與 memory high-water。
- 多文件需求只量化，不把單 Worker 改成同時持有多文件。

## 6. 明確不在 R7

- production auth／storage／CDN／Service Worker／rollback；屬 R8。
- generic rich HTML／圖片 clipboard、拖放、OS 檔案貼上或完整 Writer toolbar。
- DOCX save/re-export、Microsoft Word pixel parity、密碼文件、macro／VBA、OLE 執行。
- 完整 screen-reader 文件內 caret 模型、行動裝置、觸控 IME 與瀏覽器外 virtual keyboard。
- `writer-automation`、任意 command、UNO object graph；屬獨立 R9 候選。
- 為縮體積移除 filter／library／resource；R10 必須使用 R7 corpus，不得在本輪同時裁切。

## 7. Corpus 與 evidence contract

每份 corpus item 至少包含：

```ts
type R7CorpusItem = {
  id: string;
  path: string;
  source: "generated" | "libreoffice-qa" | "derived-negative";
  sourcePath?: string;
  license: string;
  sha256: string;
  bytes: number;
  mediaType: string;
  features: string[];
  expected: {
    open: "pass" | "typed-failure";
    save?: "odt" | "none";
    degradation?: string[];
  };
  anchors: Array<{ text: string; count: number }>;
  limits: { openMs: number; peakBytes?: number };
};
```

- manifest 凍結後任何 bytes／expected result 變更都需新 hash 與修訂理由。
- 原始 browser log、screenshots、輸出 ODT／PDF、process memory samples 與人工 checklist 放入
  `findings/evidence/sdk-r7/`；`summary.json` 只彙整，不取代 raw evidence。
- 每項結果標示 `observed`、`inferred`、`manual-only` 或 `not-validated`。人工輸入成功不能取代 SDK／
  round-trip machine assertion；synthetic event 成功也不能取代人工真 IME。

## 8. Browser、desktop 與重跑矩陣

- Chrome／Firefox：R7-A discovery 各至少 1 次；B 的自動 input contract 各 3 次；C 的代表 corpus 各 3 次、
  全 corpus 各至少 1 次；D 的 lifecycle／soak 各至少 1 次。
- Headed 人工：Chrome／Firefox 各自執行 Chewing、Cangjie、Pinyin 與真 clipboard checklist；記錄 OS session、
  Fcitx input method、browser/version、artifact hash 與最終 ODT hash。
- Desktop LibreOffice 對所有成功保存的 ODT 做 ZIP/XML、semantic anchors、open 與 PDF；DOCX 原始輸入也由
  desktop baseline 開啟，避免把壞 fixture 誤判為 WASM filter 問題。
- fault／negative scenario 使用 deterministic input、timeout、process barrier 或權限 fixture，不依賴人工競速。

## 9. 回歸與工作區保護

- 每個子階段至少跑受影響單元與 browser slice；R7 最終跑 R1～R6 release regression。
- 進場與結束保存 core HEAD／status、R5 artifact/resource hashes、browser／desktop／IME 環境。
- 既有五筆 core tracked dirty 與一筆 untracked 文件都屬使用者現場；不得納入 R7 變更或 commit。
- 若外層仍非 Git repository，記錄無法切 commit；若未來出現可用 repo，依單一 spec／validator 的內聚單位
  分 commit，不提交 core 既有 dirty files。

## 10. Go／部分 Go／停止條件

**GO**：R7-A checkpoint 未觸發停止條件；Chrome／Firefox 的 host input contract 與三種真 IME 不重複／漏字，
clipboard 權限語意明確；目標 ODT／DOCX corpus 無 silent content loss，成功輸出可 desktop round-trip；基本
viewer 操作可用，長時間測試沒有無界成長；R1～R6 與 artifact/core 保護全通過。

**部分 GO**：安全 ODT-first 與輸入工作流成立，但 DOCX import、某一 IME／瀏覽器、hyperlink geometry、
font fidelity 或完整 accessibility 缺少可靠公開能力。保留逐項 evidence 與 typed unsupported/degraded 狀態，
不得將未通過項目列為產品能力。

**停止回報**：出現 silent text duplication/loss、composition cancel 仍 mutation、clipboard 拒絕後 mutation、
損壞文件造成 Worker／browser 不可復原、DOCX 錯誤 filter 後靜默另存、memory 持續無界成長、或需 raw UNO／
unoembind／任意 callback／core tracked change 才能達成。立即保存輸入 bytes、event trace、輸出文件與 process
metrics，建立 finding 後決定縮為 ODT-first、manual-only 或停止該能力。

## 11. 交付物

- 本 overview 與 R7-A／B／C／D 子 spec。
- 執行期的 `DEVLOG-<日期>-wasm-sdk-r7.md`。
- `wasm_sdk_probe/test-docs/r7/` corpus、manifest、生成／驗證工具與來源說明。
- `findings/evidence/sdk-r7/summary.json`、browser／manual／compatibility／roundtrip／memory／regression evidence。
- 必要編號 finding，以及 R8 font/delivery 與 R10 filter/reachability 的量測輸入。

## 12. 規格盤點／執行結果（2026-08-02）

- 本輪只完成唯讀盤點與規格化，沒有建立 corpus、修改 SDK/core、重建 artifact 或執行 R7 browser matrix。
- 已確認 R7 的第一個高風險 checkpoint 是「host composition 與真 IME 證據分離」以及「DOCX bytes 被固定
  `.odt` 路徑開啟」；兩者均在 R7-A 先驗證，不先承諾產品能力。

## 13. 最終執行結果（2026-08-04）

- R7-A discovery維持部分GO：ODT與host input邊界成立，DOCX依finding 013 unsupported。
- R7-B automatic Chrome／Firefox各3/3，既有雙瀏覽器Chewing真實IME／clipboard通過；Cangjie／Pinyin未驗證，
  判定部分GO且不再增加人工負擔。
- R7-C 28份corpus、兩瀏覽器正式repeat/full、desktop baseline與fidelity全部通過；DOCX typed unsupported，
  判定`PARTIAL_GO_ODT_FIRST`。
- Finding 012以bounded Worker recycle完成SDK remediation；不改core／R5 artifact，S5 normal／known跨瀏覽器通過。
- R7-D Chrome完整50-cycle／20-crash／30-minute矩陣通過；Firefox一般、reuse、30-minute與S5通過，但fresh
  35/50及crash recovery 19/20後出現init timeout，建立finding 014。
  **（2026-08-08 更新：那兩筆 init timeout 是 [finding 023](../findings/023-sdk-init-wedges-at-fixed-session-depth.md)
  的 unread `serve.py` pipe，不是 Firefox。以修好的 harness 重跑正式九輪，Firefox
  `summary.pass: true` 全數通過——見 [R7-D §10.3](./SPEC-R7-D-usability-longevity.md)。
  R7-D 判定仍為部分 GO，但理由只剩 accessibility。）**
- **R7總判定：部分 GO（ODT-first）**。可交付安全ODT閱讀／輸入／review基線；不承諾DOCX、Cangjie／Pinyin、
  完整document accessibility／link activation~~或Firefox無限Worker generation~~。未使用raw UNO、unoembind、
  任意`.uno:*`、last-write-wins或未承諾callback。
  **（2026-08-08：刪節號那項撤回——Firefox 的 Worker generation 上限不存在，見上一條。
  R7 總判定不因此改變，其餘保留項未動。）**
- 環境具備啟動 R7-A 的本機工具，不需 root 或新增依賴；任何 Fcitx profile 變更與 headed 人工操作仍需在
  執行期明確記錄。
- 2026-08-03 R7-A automatic matrix 已跨 Chrome／Firefox 通過 input、ODT XML／desktop PDF、typed negative、
  10-cycle lifecycle、3-crash recovery 與 R1～R6 regression；automatic decision 為 **PARTIAL GO**。
- DOCX public name/C ABI 邊界已由 runtime 證實並建立 finding 013；現階段不宣稱 `open-docx`，也不修改
  SDK/core。
- Chrome 150／Firefox 152 headed manual 均以 Fcitx5 Chewing 完成 composition commit/cancel、trusted native
  paste 與 user-gesture Clipboard API write/read；拒絕路徑零 mutation。R7-A 最終判定 **PARTIAL GO**，可依
  固定順序進入 R7-B，但 R7-B 實作仍須另列動作並取得確認。
- 2026-08-03 R7-B automatic Chrome／Firefox各3/3通過；集中三輸入法headed gate因後續停止而未執行。
- R7-C 28份L0～L4 corpus、preflight、runner與validator已完成static gate，但未啟動正式browser matrix。
- R7-D diagnostic在required t2 styled ODT證實只做`open → close`也會於Chrome／Firefox各自完整180秒
  timeout；依D規格的normal close停止條件，R7整體判定 **STOP**，finding 012升級為阻礙。
- 因deterministic stop已無法由人工IME／keyboard／Orca改變，沒有要求額外人工驗收，也沒有把pending項目
  計成pass。Machine summary為`findings/evidence/sdk-r7/summary.json`。

## 14. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。依 R6 GO 建立 R7 輸入、相容性、可用性與 longevity 規格基線；尚未授權執行。 |
| 2026-08-03 | v2。記錄 R7-A automatic PARTIAL GO、finding 013 與 pending headed manual gate。 |
| 2026-08-03 | v3。記錄 R7-A headed manual 完成與最終 PARTIAL GO。 |
| 2026-08-03 | v4。記錄B automatic、C implementation與finding 012跨瀏覽器normal close造成R7 STOP。 |
| 2026-08-04 | v5。Finding 012 bounded Worker remediation後完成正式矩陣；R7最終判定為ODT-first部分GO。 |
| 2026-08-08 | v6。finding 014撤回（成因是finding 023的unread pipe）：Firefox R7-D正式九輪重跑全過，總判定保留項刪去「Firefox無限Worker generation」。R7總判定與其餘保留項不變。 |
