# SPEC R7-A：輸入／格式 discovery 與 corpus 基線

> **日期**：2026-08-02  
> **狀態**：完成（PARTIAL GO；automatic＋Chrome／Firefox headed manual 通過，DOCX public open unsupported）  
> **上層規格**：[SPEC R7-000](./SPEC-R7-000-overview.md)

## 1. 目標

在實作輸入 UI 或宣稱 DOCX 相容前，以最小、可丟棄的 probe 凍結 R7 corpus、測試方法與閘門。R7-A 必須
回答：

- 真 OS IME、synthetic composition 與 SDK commit 各自能證明什麼；
- 現有 `insertText()` 是否能保存目標 Unicode，且 cancel 能否在 host 層做到零 SDK request；
- Clipboard API 在 loopback secure context、拒絕與 user gesture 下的可測性；
- `writer-review` 對 ODT／DOCX bytes 的實際 open 行為，以及固定 `.odt` MEMFS 路徑是否造成錯誤分類；
- 什麼 corpus 與 memory baseline 足以讓 R7-B／C／D 的門檻在看結果前凍結。

R7-A 是 discovery checkpoint，不以漂亮 UI 為交付，也不得把 probe-only private state 變成 public SDK。

## 2. 進場 inventory

執行前保存 `findings/evidence/sdk-r7/baseline/`：

- core HEAD／status、R5 artifact／resource manifest 與 SHA-256；
- Chrome／Firefox／geckodriver、Node／Python、desktop LibreOffice、Fcitx5 與 session type；
- Fcitx profile 已啟用的 input methods；只盤點、不自動修改使用者全域 IME 設定；
- 現有 t1／t2／t3 hash、頁數、ZIP/XML 與 feature inventory；
- runner 可用的 CDP／WebDriver method、`psutil`、`/proc` process tree、Orca 與 PDF 工具；
- finding 012 狀態與可重現命令。

目前唯讀盤點已觀察：Wayland＋Fcitx5 正在執行，Chewing 為 current method，Cangjie／Pinyin 元件已安裝；
Chrome／Firefox 與自製 runner 可用；global Python 沒有 Playwright，但不是 R7 必要依賴。

## 3. Discovery probes

### 3.1 Host composition probe

建立獨立 DOM input adapter，不連接正式 reader UI，記錄下列事件序列：

```text
compositionstart
  → compositionupdate* / beforeinput(insertCompositionText)*
  → compositionend(commit text) → exactly one SDK insertText

compositionstart
  → compositionupdate*
  → cancel / empty compositionend / teardown → zero SDK mutation
```

自動測試可注入 synthetic event 驗證 adapter，但 evidence 必須標記 `synthetic=true`。Headed Chrome／Firefox
各以 Fcitx Chewing 做一次真輸入，記錄 `Event.isTrusted`、commit code points、SDK request count、revision 與
save 後 ODT anchor。不得記錄非 fixture clipboard 或使用者私人輸入。

若 browser／IME 的 blur、Escape、candidate selection 事件順序不同，保存完整 trace，先調整 state machine
規格；不得以 timeout 猜 commit。

### 3.2 Unicode insertion probe

以公開 `insertText()` 逐項驗證：

- 繁中 `臺灣文件測試`；
- 全形標點 `「」，。！？；：`；
- astral CJK `𠀀`、emoji `😀`、ZWJ family `👨‍👩‍👧‍👦`；
- combining sequence `e\u0301` 與 NFC `é`，兩者按 code-point expectation 分開保存；
- 換行與連續兩次 commit；
- cancel、空字串與超過輸入上限。

每項記錄 JS UTF-16 length、Unicode scalar sequence、SDK 回報 `paste|postKeyEvent`、revision delta、search
結果、ODT XML code points 與 desktop open 結果。不得只用畫面「看起來一樣」判定 normalization。

### 3.3 Clipboard probe

在 loopback secure context，以實際 button user gesture 探測：

1. `navigator.clipboard.writeText()`／`readText()` 可用性與 permissions query；
2. granted／prompt／denied 時的 browser 錯誤名稱與是否有 SDK request；
3. 真實 Ctrl+C／Ctrl+V 與頁面失焦；
4. 空 clipboard、超過上限、含換行／emoji 的純文字；
5. clipboard 同時含 HTML 時只取 `text/plain`，不把 HTML 傳入 SDK。

Synthetic `ClipboardEvent` 只能測 adapter 分支。真 OS clipboard 由 operator 使用 fixture text 驗收，不用
shell 工具繞過權限；目前環境沒有 `wl-copy`／`xclip`，R7-A 不因而安裝新依賴。

### 3.4 ODT／DOCX open spike

現有 SDK 雖接收 `OpenOptions.name`，WASM 內部實際固定寫成 `.odt`。用全新 Worker、相同 timeout 依序測：

| Case | Bytes | `name` | 目的 |
|---|---|---|---|
| A | t1 ODT | `t1.odt` | 正控制 |
| B | t1 ODT | `t1.docx` | 名稱是否實際影響 filter |
| C | 最小 generated DOCX | `plain.docx` | DOCX content detection |
| D | 同一 DOCX | `plain.odt` | 固定副檔名風險 |
| E | truncation／bad ZIP | 對應格式名 | typed failure／Worker recovery |
| F | 非 Office bytes | `unknown.bin` | unsupported format |

每個 case 記錄 stage、open result、document type／dimensions、first tile、已知 anchor search、close、Worker
health 與 desktop baseline。若 C/D 結果不同，表示 public name 與實際 path 不一致影響 filter；建立 finding，
先提出 allowlisted `format`／safe extension 的窄 SDK 修正，不得直接加入 raw filename/path surface。

若 DOCX 只能在 `full-qa` 成功、`writer-review` 失敗，保存兩個 artifact hash 與 filter差異；R7-C 預設縮為
ODT-first，是否另建 DOCX profile 必須另行決策，不在 discovery 偷換 artifact。

### 3.5 Corpus candidate inventory

R7-A 只從自有生成檔與 LibreOffice QA allowlist 選取。下列是盤點候選，不等於已納入：

| Feature | Candidate | Bytes | SHA-256 |
|---|---|---:|---|
| DOCX comments | `sw/qa/extras/tiledrendering/data/comments-on-load.docx` | 20,338 | `09ae12a5…b6e86` |
| DOCX redline＋comment | `sw/qa/writerfilter/dmapper/data/redline-range-comment.docx` | 17,713 | `27f72a9f…12d98` |
| DOCX image | `sw/qa/extras/ooxmlimport/data/image-lazy-read.docx` | 9,392 | `20344bba…0ba` |
| DOCX embedded font | `sw/qa/writerfilter/dmapper/data/subsetted-embedded-font.docx` | 36,987 | `d980bf64…7877` |
| ODT hyperlink | `sw/qa/extras/tiledrendering/data/hyperlink.odt` | 9,154 | `bb7e0817…f8a5` |
| ODT redline＋comment | `sw/qa/filter/md/data/redlines-and-comments.odt` | 13,408 | `4d27378e…b0e2` |

正式 manifest 必須存完整 hash，不得使用表內縮寫；另加入自有 deterministic plain／table＋image／
comment＋redline ODT/DOCX pairs、derived corrupt cases，以及 100 頁含圖片 fixture。QA candidate 要記錄來源
commit、原始相對路徑與 MPL-2.0 project provenance；不修改或提交來源 tree。

### 3.6 Memory／lifecycle baseline

在尚未加入 R7 UI 前，以 t1／t2／t3 對 Chrome／Firefox 各量：

- browser 主程序與 descendants 的 RSS／PSS（可取得時）、process／Worker count；
- diagnostic WASM heap size／sbrk、tile cache peak、first tile、close latency；
- 10 次 open／first tile／close 與 3 次 crash／restart；
- finding 012 的 operation sequence 與正常 close sequence分開。

R7-A 用此 baseline 預先凍結 R7-D 的 cycle count、block size、絕對／相對 growth ceiling；正式 longevity
結果產生後不得再調門檻。Firefox／Chrome 指標不可混為同一量測方法，process cache 與 WASM heap也不可相減
冒充已釋放記憶體。

在執行 R7-A browser baseline 前先凍結 R7-D 門檻如下；machine-readable 副本由
`validate_r7_a.py` 寫入 `findings/evidence/sdk-r7/discovery/memory/thresholds.json`。這些數值不能在看到
R7-D 正式結果後放寬：

| 欄位 | Chrome | Firefox |
|---|---:|---:|
| `sampleIntervalMs` | 1,000 | 1,000 |
| `warmupCycles` | 10 | 10 |
| `blockSize` | 10 | 10 |
| `cycleCount` | 50 | 50 |
| `maxPostCloseGrowthBytes` | 536,870,912 | 536,870,912 |
| `maxPostCloseGrowthRatio` | 0.35 | 0.35 |
| `maxBlockMedianSlopeBytes` | 67,108,864 | 67,108,864 |
| `maxWasmHeapStepBytes` | 268,435,456 | 268,435,456 |
| `maxWorkersAfterClose` | 0 | 0 |
| `openTimeoutMs` | 180,000 | 180,000 |
| `closeTimeoutMs` | 180,000 | 180,000 |

R7-A 自身只跑 10 次 open／close 與 3 次 crash discovery，不能拿這個短 baseline 取代 R7-D 的 50-cycle、
20-crash 與 30 分鐘正式 gate。若某欄在 browser 無法取得，標 `unavailable`，不能將門檻改成零或事後換量測方法。

## 4. Corpus manifest validator

預定 `wasm_sdk_probe/test-docs/r7/manifest.json` 與 validator 至少檢查：

- schema、unique ID/path、來源與 license；
- file exists、exact bytes／SHA-256／media type、size ceiling；
- ZIP CRC、entry count、uncompressed size／compression ratio ceiling、XML parse；
- ODF mimetype／OOXML content types 與禁止 macro／external dependency policy；
- expected feature anchors、page class、mutation policy與 typed negative result；
- derived-negative 的 parent hash 與 deterministic derivation recipe。

不允許 validator 自動接受新 hash 或在結果後覆寫 expected baseline。

## 5. 預定工具與證據

執行階段預定新增下列工具；本規格盤點階段尚未建立：

```text
wasm_sdk_probe/tools/create_r7_corpus.py
wasm_sdk_probe/tools/validate_r7_corpus.py
wasm_sdk_probe/tools/run_r7_discovery.py
wasm_sdk_probe/tools/validate_r7_preflight.py
```

預定命令：

```bash
python3 tools/validate_r7_preflight.py --phase before
python3 tools/validate_r7_corpus.py
python3 tools/run_r7_discovery.py --browser chrome
python3 tools/run_r7_discovery.py --browser firefox
```

證據放入：

```text
findings/evidence/sdk-r7/baseline/
findings/evidence/sdk-r7/discovery/input/
findings/evidence/sdk-r7/discovery/clipboard/
findings/evidence/sdk-r7/discovery/formats/
findings/evidence/sdk-r7/discovery/memory/
findings/evidence/sdk-r7/corpus/manifest-validation.json
findings/evidence/sdk-r7/discovery/summary.json
```

## 6. Discovery 判定

**GO**：ODT baseline、host composition state machine、headed Chewing、clipboard user-gesture、DOCX open
classification 與 memory sampling 都產生可重跑 evidence；corpus manifest 與 R7-D thresholds 在正式結果前
凍結；無 core change／未承諾 surface。

**部分 GO**：

- synthetic composition contract 可自動化，但其中一個 browser 的 headed 真 IME evidence 暫時無法取得；
  B 必須保留 manual gate 並標明未驗 browser／method；或
- DOCX 無法在 `writer-review` 可靠 open，但 ODT、輸入與 typed unsupported 成立；C 改成 ODT-first，DOCX
  留明確 unsupported／finding；或
- font／hyperlink／Firefox process metric 只能以安全降級量測，不影響內容完整性主線。

**停止回報**：composition commit/cancel 無法區分而造成重複／漏字；clipboard denied 後仍 mutation；正常
ODT 在新 probe 回歸；DOCX 錯誤辨識後產生可保存的靜默錯內容；Worker crash／open hang 不可恢復；memory
sampling 必須解析 raw callback 或修改 core。保存完整 event trace／bytes／process tree，建立 finding 後才決定
是否改 spec。

R7-A 未 GO／部分 GO 前不得開始 R7-B～D 實作。

## 7. 交付物

- 凍結的 corpus manifest、來源／license／hash inventory 與 negative derivation recipes。
- input／clipboard／format／memory discovery raw evidence 與 machine summary。
- 真 IME manual checklist 與 synthetic evidence 的明確分類。
- R7-D 預註冊 memory thresholds。
- 任何 architecture／SDK／browser 相容性 finding，以及 R7 GO／部分 GO／停止建議。

## 8. 執行結果（2026-08-02～2026-08-03）

### 8.1 已觀察

- Preflight before／after 均 `pass:true`；core HEAD、6 筆既有 dirty baseline、R5 `writer-review`
  loader／WASM／resources hash 未變，沒有 rebuild 或 core 修改。
- Frozen minimal corpus 共 5 項；manifest validator 與 unit tests 通過，generator 重跑只接受既有 exact hash，
  不自動更新 baseline。
- Chrome 150／Firefox 152 的 synthetic composition exactly-once、cancel 零 request、Unicode／astral／emoji／
  ZWJ／combining/NFC／newline、UTF-8 上限與 plain-text clipboard adapter 均通過。兩份輸出 ODT 的
  `content.xml` 含全部預期 code points，desktop LibreOffice 26.2.4.2 均可轉為 1-page PDF。
- 兩 browser 各 10/10 open/render/close、3/3 crash/restart 通過；crash state、restart 後 stale handle 與
  recovery 分別得到 `WORKER_CRASHED`、`STALE_DOCUMENT` 與成功 control open。Chrome 保存 171 筆、Firefox
  保存 62 筆 process-tree RSS/PSS samples；Firefox browser memory API 明確標 `unavailable`。
- Firefox synthetic `ClipboardEvent` 不暴露程式放入的 payload；保存此差異後以 synthetic adapter fixture
  驗證分支。真 clipboard 不由此結果取代；headed user gesture 另由兩 browser manual evidence 通過。
- DOCX 結果在兩 browser 一致：合法 DOCX 配 `.docx` 名稱於 C ABI 前得 `INVALID_ARGUMENT`，配不實
  `.odt` 名稱則可 open/render/search/close。已建立 finding 013；不以 workaround 宣稱 `open-docx`。
- R5 unit/ABI/profile、R6-C contract/reference static 與 R6 release gate 全通過；R6 判定仍為 GO。

### 8.2 推論與限制

- 自動判定為 **PARTIAL GO**：ODT、host input、typed negative、lifecycle／recovery 成立；DOCX public
  surface 保留 unsupported，必須另決定窄 `format` 修正或 R7-C ODT-first。
- Firefox 10-cycle warmup 的 process-tree PSS 從約 503 MB 到 850 MB；因 R7-D 已將前 10 cycles 定義為
  warmup，不能以本短跑判定無界成長，也不能事後放寬預註冊門檻。R7-D 必須優先跑正式 50-cycle blocks。
- synthetic event 的 `isTrusted=false`，不能證明 Fcitx Chewing 或實際 clipboard。

### 8.3 待驗

- R7-A 無待驗 gate；Chrome／Firefox 已各完成一次 Fcitx5 Chewing commit/cancel 與 user-gesture
  plain-text clipboard write/read。
- 後續 R7-B 仍須依其規格執行三種 IME 與重複 browser contract；R7-A 的單次 headed discovery 不取代 B。

### 8.4 Headed manual 與最終判定

- Chrome 150 clean run：兩筆 Chewing composition、cancel 零 mutation、trusted native paste、Clipboard API
  write/read、全部 searchable anchors 與 21,786-byte ODT save 通過。Chrome 的 `compositionend.isTrusted`
  為 `false`，但同一 composition 的 start/update/beforeinput 均 trusted，保留為 browser-specific observation。
- Firefox 152 clean run：相同 composition/cancel/native paste 與 22,438-byte ODT save 通過。Firefox
  `readText()` 需 operator 在暫時性 Paste 選單逐次確認；第一次未確認得到 `NotAllowedError` 且 mutation delta
  為 0，失敗與 clean pass evidence 均保留，未修改 browser 安全偏好。
- `finalDecision=PARTIAL_GO`：manual gate 全通過且未觸發停止條件；部分 GO 唯一主因仍是 finding 013 的
  DOCX public name／C ABI 邊界。R7-C 必須維持 ODT-first 或另行核准窄 format 修正，不得用 `.odt` 偽名宣稱
  DOCX 支援。

Machine summary：`findings/evidence/sdk-r7/discovery/summary.json`；所有失敗嘗試另保留於
`discovery/attempt-1/`～`attempt-3/` 與 R7 DEVLOG。

## 9. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。定義 R7 第一個 discovery checkpoint、corpus manifest、DOCX extension 風險與 memory threshold 凍結。 |
| 2026-08-03 | v2。回填跨瀏覽器 automatic PARTIAL GO、finding 013、memory baseline 與 pending manual gate。 |
| 2026-08-03 | v3。回填 Chrome／Firefox headed manual 通過與 R7-A 最終 PARTIAL GO。 |
