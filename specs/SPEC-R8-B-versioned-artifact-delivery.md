# SPEC R8-B：Versioned artifact delivery與防混版載入

> **日期**：2026-08-04  
> **狀態**：已完成，PARTIAL GO；可進R8-C  
> **上層規格**：[SPEC R8-000](./SPEC-R8-000-overview.md)  
> **前置閘門**：[SPEC R8-A](./SPEC-R8-A-delivery-discovery.md) GO或部分GO且schema／threshold已凍結

## 1. 目標

建立不依賴Service Worker也能驗證的versioned direct-delivery基線：bootstrap只接受一份已驗證release manifest，
SDK Worker、WASM、base data與font pack必須全部屬於同一release ID。任何HTTP、media type、encoding、size或hash
錯誤都在engine啟動前typed拒絕，且可安全重試或回到既有release。

先把release identity與HTTP delivery做對，再由R8-C加入Service Worker；避免同時除錯manifest、cache lifecycle
與LibreOffice runtime。

## 2. Versioned bundle

每個release bundle至少包含：

```text
releases/<release-id>/
  release-manifest.json       # update-checkable，非immutable
  app.<hash>.js
  sdk-worker.<hash>.js
  document-sdk.<hash>.js
  probe.<hash>.wasm
  base.<hash>.data
  base.<hash>.metadata
  cjk.<hash>.data             # policy要求時mandatory
  cjk.<hash>.metadata
  fallback-fonts.<hash>.*     # optional
```

實際角色與檔名由R8-A凍結inventory決定；上圖不是授權複製或重建artifact。bundle generator只讀現有artifact，
產出canonical manifest、預壓縮副本與inventory，不修改來源bytes。

要求：

- release ID不得只用可碰撞的短版本字串；需包含manifest content identity或由CI提供不可重用ID。
- 同一role只能有一個logical artifact；多encoding是同bytes的transport representation，不是不同release內容。
- manifest先過schema、URL/origin、duplicate role、size與capability驗證，再開始fetch。
- mandatory graph全部ready後才可建立Document Worker；optional pack未要求時不阻擋。
- browser log、DOM status與Worker handshake都顯示同一release ID，但不把完整內部path暴露給provider。

## 3. Verified loader

載入流程固定為：

```text
fetch manifest (no-cache)
  → schema / release / URL / capability validation
  → fetch mandatory artifacts
  → HTTP / media type / encoding / length validation
  → SHA-256 identity validation
  → mount verified packs
  → start Worker generation pinned to release
  → negotiate SDK capability
  → open document
```

- 驗證失敗不得fallback到同logical path的瀏覽器舊cache response。
- hash計算邊界依R8-A凍結規則；若hash為decoded bytes，`Content-Encoding`錯誤仍要獨立拒絕。
- WebAssembly compile／instantiate只能使用已驗證bytes或具等價identity保證的response，不能一邊streaming執行
  一邊事後補hash。
- Emscripten`locateFile()`只能從verified release mapping解析；未知logical file回typed error。
- Worker handshake回報實際SDK/profile/core/release，不只相信host manifest宣稱。
- cancel在fetch／verify／mount／engine init各stage都要有界；late response不得啟動已取消generation。

## 4. HTTP與compression contract

### 4.1 Headers

- HTML/bootstrap/manifest：更新可見，採R8-A凍結的`no-cache`或更嚴格策略。
- content-hashed artifact：`public, max-age=31536000, immutable`，不得使用相同URL覆蓋bytes。
- Service Worker script在B僅保留路徑／header規則，不啟用C的cache lifecycle。
- `X-Content-Type-Options: nosniff`；各artifact使用凍結media type。
- document與API response不因artifact policy自動變成public cache。
- COOP／COEP／CORP／CORS必須使T0/T1的`crossOriginIsolated`及pthread Worker成立。

### 4.2 Precompression

- build/release步驟產出identity及可用時gzip／Brotli；記錄工具版本、參數與encoded bytes。
- server依`Accept-Encoding`選已存在variant，送正確`Content-Encoding`與`Vary: Accept-Encoding`。
- 不在正式measurement request中即時壓縮大型WASM/data。
- identity、gzip、Brotli解碼後content identity一致；encoded hash如保存只能作transport evidence。
- 缺Brotli工具可形成部分GO delivery，但不得偽造`.br`或改裝新依賴而未取得確認。

## 5. Font pack載入

- manifest把base/CJK/fallback的data與metadata視為不可拆散pair。
- locale policy在fetch前決定mandatory packs；hash/offset/overlap沿用R5 pack integrity validator。
- optional fidelity pack下載中可cancel；失敗時不啟動宣稱full-fidelity的engine。
- 目前release已啟動後才要求pack，回`FONT_PACK_RESTART_REQUIRED`並提供save/reload；不得直接改MEMFS後假設
  LibreOffice重讀字型。
- R7 font corpus比較source/output content、desktop page count/PDF與degradation reason。

## 6. Negative與安全矩陣

每個案例在Chrome／Firefox至少1次，之後重新載入known-good release證明可恢復：

- manifest JSON／schema／release ID錯誤；duplicate/unknown role；path traversal／credential／未知scheme。
- JS／Worker／WASM／data／metadata缺檔、404、500、redirect到非allowlist origin。
- bytes、hash、raw size、media type、encoding或metadata/data pair錯誤。
- response部分中斷、late response、timeout、cancel與重試。
- host manifest release與Worker handshake release/profile/capability不一致。
- CORS／CORP／COEP錯誤造成isolation失敗。
- optional pack失敗、取消與restart-required。
- cached stale response與server candidate不一致；不得啟動stale mixed graph。

所有negative在Document mutation前失敗，revision與協作authority不變。

## 7. Browser與round-trip矩陣

- Chrome／Firefox：identity、gzip及環境可用時Brotli各至少3次cold與3次warm。
- T0 same-origin、T1 allowlisted resource origin各跑mandatory graph與negative representative。
- 每個成功release至少跑R6 reader/reference smoke、R7 t1／t2與一份font fixture的open/render/search/save/close。
- 成功輸出做ZIP/XML與desktop LibreOffice open/PDF；delivery不能改變ODT語意。
- Finding 012 known-close走bounded recovery；Finding 014要求Firefox優先reuse並記generation budget。
- 記錄manifest、release、artifact hash、response headers、cache source、encoded/decoded bytes、各stage timing與
  Worker handshake。

## 8. Evidence

```text
findings/evidence/sdk-r8/delivery/
  bundles/
  manifests/
  headers/
  compression/
  browser/<browser>/
  negative/
  fonts/
  roundtrip/
  summary.json
```

release evidence可保存manifest與小型metadata；大型既有artifact以path、bytes與SHA-256識別，除非失敗bytes是
必要最小重現，否則不重複複製進evidence。

## 9. GO／部分GO／停止條件

**GO**：兩browser在T0/T1對identity及可用precompression通過cold/warm；完整mandatory graph只由同release
啟動；所有negative在engine前typed拒絕且known-good可恢復；font policy與R6/R7 round-trip通過。

**部分GO**：versioned identity、headers與防混版成立，但Brotli或某cross-origin拓樸受環境限制；保留明確
部署要求後可進C，不宣稱缺項已驗證。

**停止回報**：任一錯誤artifact仍可執行；manifest無法約束Emscripten動態路徑；browser cache可繞過hash；
same release ID可得到不同bytes；或cross-origin isolation只能靠降低安全header完成。保存response/manifest/
Worker log並建立finding，未解決不得進C。

## 10. 交付物

- release bundle／manifest generator與schema validator。
- verified loader、font restart狀態與host UI最小狀態顯示。
- deterministic header/compression/fault server擴充。
- unit、Chrome／Firefox、negative、font與desktop round-trip evidence。
- R8 DEVLOG、machine summary與必要finding。
- C的精確檔案、命令與預期產物，另行取得確認。

## 11. 執行結果（2026-08-04）

- 建立standard `writer-review-5fa3ca0d38f2b46d`（manifest SHA-256
  `244276f2f12f176fac5d189a19500b6d1d49e19b4e0deb022e6efff5ec089cc4`）與full-fidelity
  `writer-review-687bd4d891114d62`（manifest SHA-256
  `1cf633a9024da1f3b331c32c0d89a86a6ef9ac46fa38162965bb24a1dc89cfec`）兩個canonical bundle；同release目錄
  不得以不同tree覆寫。
- Chrome 150／Firefox 153各完成T0 44＋T1 39 case。每一browser／topology對identity、gzip皆完成3 cold＋
  3 warm，release／profile／SDK／core／capability／resource pack handshake一致。
- 88個跨browser negative均在engine前typed拒絕，Worker與document mutation為0；handshake mismatch只啟動
  1個待拒Worker，沒有open document；每個topology最後known-good recovery成功。
- R6/R7/font共8份正式輸出通過ODT ZIP/XML、全文等價與desktop PDF page count；full-fidelity fallback pack在
  engine start前載入，熱切換回`FONT_PACK_RESTART_REQUIRED`。
- Finding 015由完整graph實證：Firefox partial response即使resolve，decoded size/SHA-256仍拒絕；產品不依賴
  transport rejection。
- 結案audit發現第一輪bundle的`locateFile()`對未知logical file仍有原始path fallback；該輪證據完整保留為
  pre-final attempt。最終bundle改為未知名稱回`R8_UNKNOWN_LOGICAL_ARTIFACT`，worker source shape漂移時build
  fail closed；修正後完整166 browser cases與8份roundtrip重新通過。
- `libreoffice-26-8` HEAD、既有dirty與R5 loader/WASM hash在before/after相同；R5、R6-C、R7-D及Finding 012
  remediation回歸通過。

**判定：PARTIAL_GO。** 所有安全gate為true，未觸發停止條件，可進R8-C。未宣稱完成的兩項為：

1. 環境沒有Brotli CLI；只有identity與deterministic gzip evidence。
2. full-fidelity required graph為218,473,422 bytes，超過R8-A凍結的200,000,000-byte limit；兩browser雖實際
   啟動及roundtrip通過，仍保留產品預算缺口，不放寬threshold。

Machine summary：`findings/evidence/sdk-r8/delivery/summary.json`。R8-C不得重新解釋B的direct-delivery成功為
Service Worker atomic update、offline或rollback已完成。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。定義versioned direct delivery、verified loader、precompression、headers與防混版gate。 |
| 2026-08-04 | 完成Chrome／Firefox T0/T1、negative與roundtrip；判定PARTIAL GO，可進R8-C。 |
| 2026-08-04 | 結案audit封閉`locateFile()`未知logical path，重跑完整矩陣後維持PARTIAL GO。 |
