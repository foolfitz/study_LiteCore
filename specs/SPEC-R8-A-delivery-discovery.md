# SPEC R8-A：Delivery discovery與契約凍結

> **日期**：2026-08-04  
> **狀態**：已完成，PARTIAL GO  
> **上層規格**：[SPEC R8-000](./SPEC-R8-000-overview.md)

## 1. 目標

在撰寫Service Worker或改變artifact delivery前，以最小probe回答：

- R5/R7實際release graph有哪些entry、Worker、WASM、data、metadata與font pack；哪些為啟動必需？
- Chrome／Firefox在T0 loopback與T1 local cross-origin下，對Service Worker、CacheStorage、COOP／COEP／
  CORP／CORS、預壓縮與large response有哪些可重現差異？
- 現有manifest能否無歧義擴充為closed versioned release schema，還是需要新schema major？
- optional font pack是否能在engine start前可靠選擇／驗證；沒有font inventory時產品policy要縮到哪裡？
- fault與效能要如何deterministic注入、採樣和分類，才能在B～D看到失敗時定位stage？

R8-A是discovery checkpoint，不以完成UI或Service Worker為目標。輸出是凍結契約、閾值、fixture與GO／部分GO／
停止判定；沒有通過A不得先寫production cache流程。

## 2. 唯讀進場盤點

進場先保存並比對：

- core HEAD／dirty status與R5 writer-review loader／WASM hash；
- R5 profile manifest、resource inventory、cache evidence及hashed filename規則；
- R6 reader/reference asset graph、R7 reference/compatibility/longevity asset graph；
- 現有`web/serve.py` header行為與Chrome CDP／Firefox WebDriver runner capability；
- R7 summary、compatibility corpus、font fixtures、memory thresholds與findings 012～014；
- 本機compression工具、browser版本、secure-context／Service Worker可用性與可用port，不安裝新依賴。

若基線hash或core狀態與規格不符，先停止並判斷是使用者新現場或artifact漂移，不自行覆蓋。

## 3. Discovery probes

### 3.1 Release graph inventory

由現有dist/profile manifest與HTML／Worker靜態相依建立machine-readable inventory，至少記：

- logical role、relative path、sha256、raw bytes、media type、是否mandatory；
- 由哪個entry／Worker引用，是否由Emscripten`locateFile()`解析；
- cache policy與是否允許cross-origin；
- base／CJK／fallback pack的metadata/data pair與mount順序；
- 不可content-address或runtime動態生成的路徑，逐一說明原因。

禁止以regex掃到「看似URL」就自動加入release graph；每一role需closed allowlist與fixture驗證。

### 3.2 Browser、origin與header matrix

T0與T1各在Chrome／Firefox探測：

- Service Worker register/install/activate/controller與scope；
- `isSecureContext`、`crossOriginIsolated`、`SharedArrayBuffer`與pthread Worker init；
- CacheStorage put/match/delete、large response、opaque response拒絕與storage estimate可觀測性；
- JS、Worker、WASM、JSON、data、metadata的content type與`nosniff`；
- same-origin及allowlisted resource origin下的COOP／COEP／CORP／CORS組合；
- gzip、Brotli與identity response的`Content-Encoding`、encoded／decoded bytes及hash計算邊界；
- navigation reload、hard reload、new tab/client與browser restart後的controller/cache狀態。

synthetic故障只能證明state machine；browser實際SW／CacheStorage結果須由真browser API觀察，不能用pure unit test代替。

### 3.3 Manifest schema spike

候選schema至少包含：

```ts
type ReleaseManifestV1 = {
  schemaVersion: 1;
  releaseId: string;
  createdAt: string;
  sdkVersion: string;
  profile: "writer-review";
  coreCommit: string;
  entry: string;
  artifacts: Array<{
    role: string;
    url: string;
    sha256: string;
    rawBytes: number;
    encodedBytes?: number;
    mediaType: string;
    contentEncoding?: "identity" | "gzip" | "br";
    required: boolean;
    cachePolicy: "entry" | "immutable" | "optional-pack";
  }>;
  capabilities: string[];
};
```

A要驗證而非預設：hash針對decoded artifact或wire representation、同一logical artifact是否允許多encoding、
optional pack如何表達、entry與Service Worker如何取得candidate release，以及舊schema如何typed reject。

URL必須為相對同origin或明確allowlisted origin；拒絕absolute file path、`data:`、`blob:`、credential、fragment、
path traversal、scheme-relative URL與未知scheme。

### 3.4 Fault injection feasibility

建立不需root的test-only delivery fixture設計，逐一證明可穩定重現：

- fixed latency與chunk barrier；
- response中途close、declared length不符、404／500；
- bytes/hash/media type/content encoding錯誤；
- manifest缺entry、重複role、循環／未知dependency、跨release URL；
- CacheStorage write reject／quota-like failure與entry缺損；
- install／activate／client reload前後的明確barrier。

真storage quota若browser automation無安全、可重現的控制面，A要將它分成「real quota manual／environment」與
「deterministic write-failure contract」，不得以mock pass宣稱真quota通過。

### 3.5 Font policy discovery

- 以zh-TW locale與R7 missing／embedded font fixture量base、base+CJK及fallback pack的content/page/PDF差異。
- 盤點公開SDK是否有已承諾font inventory；沒有就記`not-observable`，不解析raw callback或ODF私有內部狀態。
- 凍結v1策略：locale mandatory pack＋使用者明確fidelity選項；文件自動判定只在有安全公開資料時啟用。
- 驗證pack必須在engine init前mount；已啟動後請求新pack只能要求save/reload，不能熱塞入既有engine。

## 4. 凍結輸出

R8-A結束時必須凍結：

1. release manifest schema與canonical JSON/hash規則；
2. artifact role／URL／origin allowlist與media type表；
3. mandatory／optional graph與release/cache命名；
4. Service Worker client pin與last-known-good保留模型；
5. typed error taxonomy、retryability與safe next action；
6. T0／T1／T2拓樸定義及可宣稱範圍；
7. fault scenario IDs、barrier與expected state；
8. cold／warm／offline／update分段timing與bytes採樣方法；
9. font pack v1 policy與degradation分類；
10. Chrome／Firefox repetition count、timeout、cache／Worker generation budget及停止條件。

門檻必須在B～D正式結果前寫入evidence，不得事後以觀察值放寬。

## 5. 自動化與人工界線

- artifact inventory、manifest/schema、header、origin、SW、CacheStorage與fault probes全部自動化。
- browser UI的「offline」不由人工DevTools切換；runner控制test server或browser network state並保存barrier。
- 不修改全域browser profile、Fcitx、proxy、firewall或DNS。
- 真T2 HTTPS/CDN與不可程式化quota若缺環境，A只記需求與部分GO路徑，不要求使用者現在建立帳號。
- 人工操作預設0次。

## 6. Evidence

```text
findings/evidence/sdk-r8/discovery/
  baseline/
  release-graph/
  browser/<browser>/
  headers/
  compression/
  cache-storage/
  fault-feasibility/
  fonts/
  thresholds.json
  summary.json
```

每份browser evidence至少含版本、origin/topology、release/hash、response headers、SW state、cache keys、timing、
typed result與raw log。log需移除credential、query token與非fixture文件資訊。

## 7. GO／部分GO／停止條件

**GO**：兩browser的T0／T1 capability可觀察，release graph完整且closed schema無歧義；所有fault scenario可
deterministic注入或被誠實分類為T2/manual；font v1 policy可在engine start前成立；threshold與後續B～D gate凍結。

**部分GO**：核心release／SW／cache契約可測，但某browser的真quota、Brotli細節或T2環境不可自動取得；保留
明確替代測試與完整GO缺項，不阻擋B的versioned direct delivery。

**停止回報**：現有artifact graph無法在不執行任意manifest內容下closed列舉；browser無法同時維持SW與
cross-origin-isolated pthread runtime；hash只能在artifact執行後得知；或font pack切換必須改core／未承諾callback。
保存最小probe並建立finding，未決前不得進B。

## 8. 交付物

- inventory／schema／header／font／fault discovery工具與unit/browser tests。
- 凍結threshold、topology、typed error與machine summary。
- R8 DEVLOG的已觀察／推論／待驗證紀錄。
- 必要finding；不把browser policy差異直接猜成上游bug。
- B的精確預定檔案、命令與預期artifact清單，另行取得確認。

## 9. 執行結果（2026-08-04）

- 凍結closed schema v1，共17個role；release ID為`writer-review-82cfce600c80ed6e`，15個required artifact
  合計169,353,155 raw bytes，2個optional artifact合計49,117,707 raw bytes。
- Chrome 150與Firefox 153的T0／T1 capability、headers、fault、Service Worker、CacheStorage、115 MB WASM
  跨browser restart驗證與清除全部通過；測試使用隔離temporary profile，未改日常browser profile。
- gzip decoded identity通過。本機沒有Brotli CLI，真quota缺安全自動控制面，document font inventory在public SDK
  不可觀察，T2 HTTPS不屬A必要環境；依第7節判定`PARTIAL_GO`，不阻擋R8-B。
- Finding 015確認Firefox不一定因`Content-Length`不符reject fetch；後續契約凍結為逐artifact驗證decoded
  bytes與SHA-256，不依賴transport rejection。
- 第一次Firefox session因Snap看不到host `/tmp` profile而失敗；runner改用專案`dist/r8/`下的可清除temporary
  profile後通過。第一次after前aggregate為STOP只是缺少尚未產生的after快照，正式after基線通過。
- R5、R6-C、R7-D static與Finding 012 remediation回歸通過；core HEAD、原有dirty清單及R5 loader／WASM
  hashes在前後一致。
- 正式machine summary：`findings/evidence/sdk-r8/discovery/summary.json`。

## 10. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。定義release graph、browser/origin、manifest、fault、font與threshold discovery checkpoint。 |
| 2026-08-04 | 完成R8-A discovery；兩browser T0/T1通過，因Brotli／真quota／font inventory／T2缺項判定PARTIAL GO。 |
