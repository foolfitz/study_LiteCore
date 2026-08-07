# SPEC R8-000：正式載入、更新、離線與復原

> **日期**：2026-08-04  
> **狀態**：R8 已完成；`PARTIAL_GO_LOCAL_DELIVERY`  
> **依據**：[R7 ODT-first 部分 GO](./SPEC-R7-000-overview.md)、
> [R6+ roadmap](./SPEC-R6+-roadmap.md)、[R5 profile GO](./SPEC-R5-000-overview.md)

## 1. 目標

R8 將 R5 的 loopback cache contract 與 R7 的 ODT-first reference application，提升成可部署、可更新、
可離線復原且不會混用版本的 delivery contract。R8 回答五個問題：

1. bootstrap、SDK Worker、JS、WASM、base data 與 optional font pack 能否由同一 immutable release manifest
   綁定，任何缺檔或 hash mismatch 都不啟動混版 runtime？
2. gzip／Brotli、content type、COOP／COEP／CORP／CORS 與 cache headers 能否在 Chrome／Firefox 維持
   pthread WASM 所需隔離與可解釋的 cache 行為？
3. Service Worker 的 install、activate、更新、舊版保留、cache eviction、離線與 rollback 是否為原子流程，
   且既有 client 不會在執行中換版？
4. locale／fidelity 驅動的字型 pack 是否在 engine start 前完成驗證；需要重啟時是否有明確、可取消狀態，
   不造成靜默版面降級？
5. 慢網、斷線、部分回應、錯誤 content type、hash mismatch、storage quota 與更新中途關頁後，是否能回到
   last-known-good release，或以 typed error 要求使用者採取明確動作？

R8 不把「localhost 能載入」稱為 production-ready。功能原子性可在 deterministic local origin 自動驗證；
CDN／真實 HTTPS 拓樸的延遲與 header 結論必須標示實際環境，沒有外部環境時只能形成部分 GO。

## 2. 已觀察的進場基線

- R5 `writer-review` loader／WASM SHA-256 為
  `35d96f5fdcb9ed0cdb19f28a743245e0dbd255cbf90a2c14d680f0b1b9c63566`／
  `ba257beb038b6a2df751156d90e5b299840eced2ed68ec5800bff731bf26dfc6`；content-hashed artifact 與
  loopback immutable/no-cache header contract 已 GO。
- R5 已將資源分成 base、CJK 與 fallback-font packs；fallback pack 的產品載入時機仍未由正式 delivery
  policy 驗證。
- R7 machine summary 為 `PARTIAL_GO_ODT_FIRST`。ODT corpus、host input、review flow、bounded Worker
  recovery 與桌面 round-trip 可作 R8 回歸基線。
- R7 正式限制為：DOCX public open unsupported（finding 013）、Cangjie／Pinyin未驗證、document-content
  accessibility與安全 hyperlink activation unsupported，以及 Firefox大量重建大型WASM Worker的generation
  exhaustion（finding 014）。R8 不得把 delivery 成功誤寫成這些功能已解決。
- 現有 `web/serve.py` 只提供固定 COOP／COEP、content-hash cache header 與 `no-cache` entry；沒有預壓縮、
  release slot、Service Worker、故障注入、rollback或真實跨origin矩陣。
- 現有 Chrome CDP、Firefox WebDriver runner、R7 corpus／memory工具與desktop LibreOffice validator可重用；
  不需因R8規劃預先安裝Playwright或修改全域瀏覽器設定。
- `libreoffice-26-8` HEAD基線為`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`，既有五筆tracked dirty與
  一筆untracked研究文件屬使用者現場。

上述是進場觀察，不等同R8結論。R8-A要以固定manifest、header dump、browser capability與fault probe重驗。

## 3. 不可退讓的邊界

- 優先沿用R5 `writer-review` artifact與R7 host／Worker；R8-A不重建LibreOffice core，也不修改
  `libreoffice-26-8`。
- release manifest只列closed schema與content-addressed相依；不得執行manifest中的任意script、command、
  path或callback。
- authenticity由受信任HTTPS origin與部署權限負責；R8的SHA-256驗證只證明content identity，不把hash誤稱
  數位簽章。
- manifest、bootstrap與Service Worker更新檢查不得使用immutable長快取；content-hashed JS／WASM／data／
  metadata／font pack才可immutable。
- 同一Document Worker generation只能使用一個release ID。更新不得熱替換既有Worker的JS、WASM、data或
  pack；需要新release時建立新generation或明確reload。
- Service Worker不得cache未明確allowlist的使用者文件、clipboard內容、協作token、presence或sidecar資料；
  R8只管理應用程式artifact與自有test fixture。
- storage quota、網路或更新失敗不得刪除唯一last-known-good release；cache eviction必須有版本保留規則與
  可重跑的client ownership判定。
- Worker crash／close timeout後不自動重送unsaved mutation；沿用Finding 012 bounded recovery語意。
- 不以raw UNO、unoembind、任意`.uno:*`、macro、未承諾callback或last-write-wins完成delivery功能。
- 不執行`sudo`／`su`／`doas`、不修改系統proxy／firewall／traffic control。慢網與故障由範圍內測試server
  或browser automation deterministic注入。
- 外部hosting、DNS、CDN、憑證、帳號或遠端寫入不在既有授權內；若完整GO需要這些環境，先停下列出精確
  動作，沒有環境時以部分GO如實結案。

## 4. 子spec與執行順序

| Spec | 內容 | 完成訊號 |
|---|---|---|
| [R8-A](./SPEC-R8-A-delivery-discovery.md) | release graph、browser／origin、SW／CacheStorage、font與fault discovery | **完成，PARTIAL GO**；schema、topology、fault與門檻已凍結 |
| [R8-B](./SPEC-R8-B-versioned-artifact-delivery.md) | versioned bundle、預壓縮、headers、verified loader與防混版 | **完成，PARTIAL GO**；166 browser cases與8 roundtrip通過 |
| [R8-C](./SPEC-R8-C-offline-update-recovery.md) | Service Worker原子install／activate、offline、rollback、quota與中斷復原 | **完成，PARTIAL GO**；跨瀏覽器T0/T1原子更新與復原成立 |
| [R8-D](./SPEC-R8-D-production-validation.md) | R6／R7 corpus回歸、跨origin、performance與production-shaped驗收 | **完成，PARTIAL_GO_LOCAL_DELIVERY**；全部safety gate通過 |

執行順序固定為 **R8-A → R8-B → R8-C → R8-D**。A的release schema、fault taxonomy、cache保留政策、
performance採樣方式與topology分類凍結後才能實作B；不得在看到結果後放寬門檻。每一子階段仍須先列出
精確檔案與命令並取得執行確認。

## 5. R8 v1範圍

### 5.1 Release identity與artifact graph

- release ID、schema version、SDK/profile/core識別、entry、Worker、WASM、mandatory packs與optional packs。
- 每個artifact的相對URL、SHA-256、encoded／decoded bytes、media type、content encoding與cache policy。
- closed dependency graph、同origin／allowlisted resource origin與minimum runtime capability。
- current、candidate、last-known-good與retiring release的狀態及保留上限。

### 5.2 HTTP delivery

- gzip／Brotli預壓縮與identity fallback；不在request時重壓大型artifact造成不可比較結果。
- JS／WASM／JSON／data／metadata的正確content type與`nosniff`。
- COOP／COEP／CORP／CORS matrix，驗證`crossOriginIsolated`與pthread Worker可啟動。
- entry／manifest／Service Worker更新策略與content-hashed immutable artifact策略分離。
- response length、ETag／Last-Modified如採用時的角色；不能以弱validator取代release hash。

### 5.3 Service Worker與復原

- staging、ready、active、retiring與failed狀態；install只有完整mandatory graph驗證後才能ready。
- 既有client pin舊release，新client只採用完整candidate；不允許逐檔漂移。
- offline cold/warm、更新中斷、browser關頁、quota、cache損壞與rollback。
- 明確的更新提示、retry／cancel／reload與typed recovery action。
- cache inventory與eviction evidence；最後一份known-good不得被未驗證candidate取代。

### 5.4 Font pack與engine restart

- locale與產品fidelity policy先決定mandatory pack；沒有公開document font inventory時不得猜測完整字型需求。
- optional pack下載、bytes/hash/offset驗證都在engine start前完成。
- 已啟動engine若需要新pack，UI必須說明save／reload需求；取消時保留目前release與document狀態。
- 使用R7 embedded／missing font corpus比較內容、page count與desktop PDF，不只檢查pack下載成功。

### 5.5 可觀測性與效能

- network、manifest、Service Worker、pack mount、engine init、document open與first tile分段計時。
- 記錄encoded／decoded bytes、cache source、release ID、Worker generation與typed failure stage。
- cold、warm、offline、update、rollback分開報告；不把loopback時間或gzip raw sum當CDN SLA。
- Firefox generation budget採finding 014安全策略，接近上限時要求重新載入session，不等待120秒timeout。

## 6. 明確不在R8

- 任意游標、拖曳選取、backspace/delete、Redo、rich formatting或完整Writer toolbar；屬延後的ODT-first
  基本編輯器里程碑。
- DOCX import修正或DOCX re-export；finding 013維持typed unsupported。
- production auth、協作storage backend、tenant policy、billing、telemetry SaaS或使用者文件同步。
- 申請／修改外部CDN、DNS、TLS憑證或雲端帳號；R8-D可使用另行授權的環境，但不自行建立。
- generic rich clipboard、圖片貼上、拖放、macro／VBA／OLE執行。
- `writer-automation`與任意command；R9仍是需求驅動的獨立候選線。
- filter／library／resource深層裁切、LTO／PGO／wasm-split；屬R10，且不得先於編輯功能corpus凍結。

## 7. Release與錯誤contract

最低狀態模型：

```text
unknown
  └─ discover manifest
       ├─ rejected ───────────────► typed terminal/retryable error
       └─ staging
            ├─ failed ────────────► preserve last-known-good
            └─ ready
                 ├─ activate new clients
                 └─ retain old clients ─► retiring ─► bounded eviction
```

最低typed error taxonomy：

- `RELEASE_MANIFEST_INVALID`
- `RELEASE_UNSUPPORTED`
- `ARTIFACT_HTTP_ERROR`
- `ARTIFACT_MEDIA_TYPE_MISMATCH`
- `ARTIFACT_ENCODING_MISMATCH`
- `ARTIFACT_SIZE_MISMATCH`
- `ARTIFACT_HASH_MISMATCH`
- `CROSS_ORIGIN_ISOLATION_REQUIRED`
- `SERVICE_WORKER_UNAVAILABLE`
- `CACHE_WRITE_FAILED`
- `STORAGE_QUOTA_EXCEEDED`
- `OFFLINE_RELEASE_UNAVAILABLE`
- `UPDATE_INCOMPLETE`
- `ROLLBACK_UNAVAILABLE`
- `FONT_PACK_RESTART_REQUIRED`
- `WORKER_GENERATION_BUDGET_EXHAUSTED`

每個error要標stage、release ID、retryable、safe next action與mutation狀態；不得將URL query、token、文件bytes
或clipboard內容寫入一般log。

## 8. 測試拓樸與fault matrix

| 層級 | 用途 | 正式宣稱 |
|---|---|---|
| T0 deterministic loopback | 版本原子性、SW、offline、fault與browser回歸 | 必須通過；不宣稱CDN效能 |
| T1 local cross-origin | CORS／CORP／COEP與resource origin policy | 必須通過；不宣稱internet拓樸 |
| T2 user-approved HTTPS deployment | proxy/CDN headers、實際壓縮、latency與更新 | 完整GO需要；缺少時可部分GO |

fault至少包含404／500、延遲、分段中斷、錯誤bytes、錯誤hash、錯誤content type／encoding、manifest指向缺檔、
candidate安裝中關頁、offline cold/warm、quota write failure、cache entry缺損及rollback目標缺失。每個fixture用固定
scenario ID，不依人工切網路時機。

## 9. 自動與人工驗收

- Chrome／Firefox的T0／T1功能矩陣全部自動化，保存browser/network/Service Worker/cache raw evidence。
- 沿用R7 headed Chewing證據；R8不重跑IME人工矩陣，除非delivery改變input origin或安全上下文。
- R8不要求人工競速關頁、拔網路或清cache；由runner建立隔離profile與deterministic barrier。
- 只有T2外部HTTPS環境、瀏覽器原生權限對話框或自動化無法取得的真實拓樸才要求人工；一輪集中完成。
- 所有人工結果記operator action、browser/version、release/hash、時間與可機器重驗的後置狀態。

## 10. 驗收、部分GO與停止條件

**GO**：R8-A未觸發停止；B／C的T0與T1跨Chrome／Firefox全部通過；新裝、熱快取、更新、舊client、離線、
中斷、quota與rollback無混版，last-known-good可恢復；font policy無靜默降級；R6/R7 ODT-first corpus與
Finding 012/014產品策略回歸通過；另在明確記錄的T2 HTTPS拓樸驗證headers、壓縮與效能。

**部分GO（local delivery contract）**：T0／T1原子性、復原、font與回歸全部成立，但沒有經另行授權的T2
真實HTTPS/CDN環境，或某瀏覽器只能安全採用顯式reload更新。可交付delivery contract與部署checklist，
不得宣稱production CDN SLA或無縫背景更新。

**停止回報**：任何情境啟動混版JS／WASM／data、hash mismatch後仍執行、candidate失敗會刪除唯一known-good、
offline回退到未驗證release、cache使用無界成長、更新／復原自動重送unsaved mutation、主要瀏覽器無法維持
cross-origin isolation，或完成必須修改core／暴露raw UNO／降低R7安全邊界。立即保存manifest、response headers、
cache inventory、SW lifecycle與browser log，建立finding後決定縮小scope或停止。

## 11. 交付物與留痕

- 本overview與R8-A／B／C／D子spec。
- 執行期`DEVLOG-<日期>-wasm-sdk-r8.md`，保留失敗嘗試與決策歷程。
- `findings/evidence/sdk-r8/summary.json`與release、network、SW、cache、font、performance、round-trip、regression
  原始證據。
- release manifest schema、deterministic delivery/fault server、Service Worker、browser runner與validator。
- 部署checklist、known limitations與T2拓樸識別。
- R1～R7回歸、R5 artifact hash與`libreoffice-26-8`工作區完整性證據。
- 可重現且影響架構、瀏覽器相容、cache安全或SDK邊界的編號finding。

## 12. 階段判定（2026-08-04）

- R8-A已在不修改LibreOffice core、不重建R5 artifact的前提下完成，machine decision為`PARTIAL_GO`。
- Closed release graph、T0／T1 header與origin契約、Service Worker／CacheStorage、115 MB跨重啟cache、gzip與
  deterministic fault都在Chrome／Firefox通過；R8-B可依凍結契約實作verified direct delivery。
- 完整GO缺項為Brotli實際預壓縮、真quota、public document font inventory及T2 HTTPS環境；A的替代測試與
  宣稱邊界已明記，未觸發停止條件。
- Finding 015凍結安全邊界：完整性以decoded bytes＋SHA-256判定，不假設`fetch()`對長度不符必然reject。
- R8-B已完成並判定`PARTIAL_GO`：兩browser T0/T1 direct delivery、防混版、identity/gzip、88 negative與8份
  desktop roundtrip均通過；Brotli缺席及full-fidelity graph超過凍結200 MB門檻保留為明確缺口，可進R8-C。
- R8-C已完成並判定`PARTIAL_GO`：Chrome／Firefox T0/T1的atomic stage／activate、client pin、offline、repair、
  rollback、interrupt與deterministic storage failure均通過；真quota及顯式reload仍是缺口。
- R8-D已完成並判定`PARTIAL_GO_LOCAL_DELIVERY`：13項safety checks全為true；Chrome active-release 28份corpus
  與30.038分鐘soak通過，Firefox依Finding 014保留combined-run缺口並採明列的組合證據。未提供T2，所以不宣稱
  production CDN SLA；R8主線可結案並進入ODT-first基本編輯器規格盤點。
- 延後的基本編輯器不是R8範圍，但已列為R10深層裁切前的產品能力閘門。

## 13. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。依R5 cache與R7 ODT-first證據建立R8 delivery、update、offline、rollback與production-shaped規格。 |
| 2026-08-04 | R8-A完成並判定PARTIAL GO；Finding 015與bytes/hash完整性契約納入R8-B前置。 |
| 2026-08-04 | R8-B完成並判定PARTIAL GO；direct delivery安全gate全通過，下一步R8-C atomic offline/update/recovery。 |
| 2026-08-04 | R8-C完成並判定PARTIAL GO；原子更新、offline、rollback與last-known-good跨瀏覽器成立。 |
| 2026-08-04 | R8-D完成；所有local safety gate通過，缺T2及Firefox Finding 014 combined-run缺口，R8判定PARTIAL_GO_LOCAL_DELIVERY。 |
