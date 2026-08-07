# SPEC R8-D：Production-shaped delivery驗證

> **日期**：2026-08-04  
> **狀態**：已完成；`PARTIAL_GO_LOCAL_DELIVERY`  
> **上層規格**：[SPEC R8-000](./SPEC-R8-000-overview.md)  
> **前置閘門**：[SPEC R8-C](./SPEC-R8-C-offline-update-recovery.md) GO或部分GO

## 1. 目標

以R8-A凍結的topology／threshold與R8-B/C實作，完成跨瀏覽器、跨origin、R6/R7 corpus、效能、離線與復原
正式矩陣，判定R8是完整GO、local delivery部分GO或停止。

R8-D負責整合驗證，不在看到結果後新增capability或重寫cache模型。若D發現架構問題，保存evidence並回到對應
B/C修正單位，不能在validator裡豁免失敗。

## 2. 凍結測試拓樸

### T0 deterministic loopback（required）

- same-origin application/artifact、隔離browser profile、固定release A/B與fault server。
- 用於原子性、Service Worker、cache、offline、fault、recovery與完整功能回歸。
- 可重現但不是internet/CDN效能證據。

### T1 local cross-origin（required）

- application origin與allowlisted artifact origin使用不同port/origin。
- 驗證CORS／CORP／COEP、redirect、credential exclusion、preflight（若有）與pthread isolation。
- 不修改系統DNS／proxy／firewall，不宣稱真TLS或CDN。

### T2 user-approved HTTPS deployment（full GO required）

- 使用者另行提供或核准的HTTPS host/proxy/CDN；記region、server/proxy/CDN、TLS、compression與cache topology。
- 不自行申請帳號、改DNS、上傳遠端或建立憑證。
- 缺T2不阻擋自動完成T0/T1與`PARTIAL_GO_LOCAL_DELIVERY`，但不得宣稱production CDN SLA。

## 3. 正式scenario matrix

### D1 Fresh install

- empty browser profile、release A、mandatory locale pack、engine init、R7 t1 first tile、save/close。
- 驗證release graph、headers、encoded/decoded bytes、cache inventory與cold stage timing。
- Chrome／Firefox × T0/T1各3次；T2各browser至少3次（環境存在時）。

### D2 Warm與offline

- online hot reload、browser restart hot、offline ready release、offline optional pack unavailable、offline cold no release。
- known-good可用時完整open/render/search；不可用時typed拒絕，不碰document mutation。
- Chrome／Firefox × T0各3次；T1代表情境各1次；T2視環境執行。

### D3 Atomic update與多client

- release A client保持開啟；stage B；新client採B；舊client仍A；明確reload後採B。
- candidate下載／verify／activate各stage中斷，restart後state與expected一致。
- manifest／artifact stale cache與server release變更不得造成跨release混版。
- Chrome／Firefox每個happy path 3次、每個barrier negative至少1次。

### D4 Integrity、quota與rollback

- R8 fault taxonomy全部正式跑一次；每次確認runtime未啟動或未mutation，並可恢復A。
- deterministic cache write／quota-like failure必測；真quota依A分類在可用環境執行並另標。
- B health check失敗、B entry損壞、rollback到A、rollback後offline均需成立。
- rollback target也損壞時回typed terminal action，不reload loop或拼湊cache。

### D5 Font policy

- zh-TW mandatory CJK、base-only degraded fixture與explicit fallback fidelity三條路徑。
- pack下載/verify cancel、offline unavailable、restart-required與reload後fidelity。
- 使用R7 font corpus檢查content anchor、page count、tile與desktop PDF差異；沒有font inventory時維持policy-driven。

### D6 R6/R7 product regression

- R6雙client review reference flow：reader、comment/suggestion、lease/CAS、Provider、save/reload與desktop round-trip。
- R7 automatic input/clipboard contract；沿用headed Chewing evidence，不重做人工IME。
- R7 compatibility：28份manifest至少在T0 active release完整跑一次／browser；T1/T2跑凍結代表集。
- R7 longevity：100頁單次、reuse cycles、bounded crash/close、30-minute soak使用R8 cache/Worker。
- Finding 012 known document維持bounded Worker recovery；Finding 014的Firefox generation budget與reload提示可觀察。
- DOCX、Cangjie/Pinyin、document accessibility與hyperlink限制保持typed/unsupported，不因delivery誤升格。

### D7 Cache retention與長時間update

- 多次A→B→C候選／rollback，確認failed/staging與retiring cache依policy回收。
- 至少30分鐘online/offline/update soak；記CacheStorage bytes、browser process PSS、Worker generation與open handles。
- 不要求Firefox無限fresh Worker；以凍結budget測試產品reload策略。
- storage與memory門檻沿用A預註冊值，不在測後調整。

## 4. Performance與network evidence

每個cold/warm/offline/update至少分段：

1. navigation/bootstrap；
2. manifest discovery/validation；
3. mandatory network encoded bytes；
4. cache read/write；
5. artifact hash validation；
6. resource mount；
7. WASM compile/instantiate與engine ready；
8. document open與first tile。

報告median、p90（樣本足夠時）、min/max與失敗，不只挑最快一次。T0/T1/T2分開，Chrome／Firefox分開，cold／
warm/offline分開。range request只有在A/B另有已核准A/B設計、且實際減少ready/first-tile成本時才可列入；否則
保持整檔content-addressed delivery。

效能未達budget但正確性成立可形成部分GO；不可為改善數字降低hash、isolation、rollback或R7資料完整性。

## 5. 安全與隱私驗證

- artifact origin不接收document bytes、clipboard、collaboration token或不必要credential。
- manifest/URL拒絕credential、unknown origin/scheme、path traversal與release escape。
- Service Worker scope不攔截不屬於app的path；user document/API response不進public CacheStorage。
- log/evidence對query token、Authorization、cookie與非fixture document metadata做redaction。
- offline頁面不顯示前一位使用者文件內容；R8不新增persistent document cache。
- hostile manifest／response只觸發typed error，不進raw command／UNO／macro surface。

## 6. 人工驗收最小化

- T0/T1全部由runner執行，不要求人工開DevTools、切offline、清cache、關頁競速或反覆輸入。
- R8不重跑R7已通過的Chrome／Firefox Chewing人工矩陣。
- 若有T2，人工只需一次提供已授權URL／部署方式或完成外部登入；後續header、browser與network matrix自動跑。
- 若沒有T2，直接判`PARTIAL_GO_LOCAL_DELIVERY`，不為了完整GO要求使用者臨時建立雲端帳號。
- 最終人工smoke最多一輪：開頁、確認update提示、offline known-good與下載ODT；若自動evidence已充分可省略。

## 7. Evidence與machine summary

```text
findings/evidence/sdk-r8/
  baseline/
  delivery/
  service-worker/
  browser/<topology>/<browser>/
  network/
  performance/
  fonts/
  compatibility/
  longevity/
  roundtrip/
  regression/
  deployment/
  summary.json
```

Top-level summary至少包含：

- decision、topologies與formal gaps；
- core/profile/release/artifact/browser/server識別；
- fresh/warm/offline/update/rollback/font/security/performance/regression checks；
- cache high-water、memory/generation policy與typed failures；
- T2存在時的實際拓樸，不存在時的`not-executed-no-authorized-environment`；
- findings與next action。

`pass: true`可代表規格允許的部分GO，但`decision`與formal gaps必須明確，不能讓缺T2看起來是完整GO。

## 8. GO／部分GO／停止條件

**GO**：T0/T1跨瀏覽器全部正確；T2授權環境的headers、compression、isolation、cold/warm/update通過；原子
更新、offline、rollback、font與有界cache成立；R6/R7 product regression與round-trip通過；無混版、silent
degradation或unsaved mutation replay。

**部分GO（`PARTIAL_GO_LOCAL_DELIVERY`）**：T0/T1與所有正確性／回歸／復原gate通過，但沒有T2授權環境，或
某瀏覽器需顯式reload／某真quota只能部署後驗證。可交付self-host checklist與last-known-good策略，不宣稱
production CDN performance或無縫update。

**停止回報**：任何混版、hash mismatch後執行、known-good遺失、offline partial runtime、user document進public
artifact cache、更新造成mutation重送／遺失、cache/memory無界、主要瀏覽器隔離失敗，或R6/R7 ODT內容／
round-trip回歸。保存所有stage evidence、建立finding並停止R8，不以手動重試洗掉失敗。

## 9. 完成後的路由

- R8 GO／部分GO後，下一個產品主線是延後的ODT-first基本編輯器里程碑；先做caret／selection／keyboard／
  delete／newline／Redo與最低格式能力的discovery，再決定是否需要窄SDK ABI。
- R9 Automation只在有具體企業需求時獨立啟動，不阻擋主線。
- R10深層減量必須等待R8 corpus與基本編輯器corpus凍結，避免裁掉未來authoring依賴。
- Finding 014可平行做最小browser/runtime歸因，但不是R8 delivery完整性通過的前提；產品generation budget必須先在。

## 10. 交付物

- T0/T1完整自動matrix與可選T2部署evidence。
- performance/network/cache/font/security/regression/round-trip/longevity machine summaries。
- 部署與rollback checklist、operator runbook及known limitations。
- R8 final DEVLOG、top-level summary、spec執行結果與GO／部分GO／停止判定。
- 必要finding與下一里程碑的唯讀盤點輸入。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。定義T0/T1/T2、正式scenario、效能、安全、R6/R7回歸與最少人工驗收。 |
| 2026-08-04 | 完成T0/T1、active-release corpus、30分鐘longevity與回歸；缺T2且保留Firefox Finding 014缺口，判定部分GO。 |

## 12. 執行結果（2026-08-04）

### 已觀察

- Chrome以同一active cached release A完成28/28份R7 corpus；分6個頁面批次、共12個Worker generations，
  每頁最高3個。Finding 012文件與table/image文件各發生一次bounded replacement，仍維持release identity。
- Chrome正式longevity為30.038分鐘、30/30 cycles通過；同一A Worker完成長壽render cycles，依序觀察
  `active-a`、`active-b`、`offline-a-runtime`、`rollback-a`，最後在server-down狀態以新Worker完成離線
  open／render／search。總generation為4、每頁最高3個。
- Firefox在R8-C完整矩陣後以兩種策略啟動R8-D active-cache corpus，皆在第一批文件開始前等待900秒而沒有
  頁面結果。兩份attempt保留為`pass:false`，Firefox compatibility／longevity summary也保持`pass:false`。
- Firefox部分GO組合證據同時要求：R7 Firefox 28份完整corpus、R7 Firefox 30分鐘soak、R8-C Firefox
  active-release update/offline/rollback與Finding 014。Top-level validator明列接受此組合，不宣稱單一combined run。
- 8組R6／R7／Finding 012／R8-C回歸命令全部通過；Python R8-D 5項、Node release/loader 18項測試通過。
- performance、network、font、security、round-trip與operator docs摘要均產出；after-preflight確認core HEAD、
  既有dirty及R5 loader／WASM hash不變。

### 失敗嘗試與修正

- Chrome corpus先後暴露search-before-render、跨文件engine reuse、Finding 012 generation權重與三一般Worker實際
  超過頁面預算；正式runner改為R7順序、每案verified Worker及保守6頁分批。所有attempt均保留。
- Longevity曾遇到既有A client啟用B的`CLIENT_ALREADY_PINNED`、短測沒有實際dwell、第二次engine reuse search
  timeout；正式設計以獨立B client、wall-clock cycles、render-only reuse及最後新Worker health解決。
- 第一次final aggregate因預期negative case的`verified:null`觸發統計器`AttributeError`；修正為只統計非null
  timing並補單元測試後，正式aggregate通過。沒有改寫或刪除browser失敗證據。

### 推論、待驗證與判定

- **推論**：R8 local delivery的closed graph、原子更新、offline known-good、rollback與回歸邊界成立；Chrome長壽
  路徑在凍結generation budget內。Firefox仍須產品級bounded reuse與整個browser工作階段reload提示。
- **待驗證**：使用者授權的T2 HTTPS/CDN、真browser quota、candidate無須顯式reload的替代產品體驗，以及
  Finding 014根因。這些未被T0/T1或deterministic quota-like failure冒充。
- **判定：`PARTIAL_GO_LOCAL_DELIVERY`。** 所有13項safety checks為true，未觸發停止條件；缺T2及上述明列
  缺口，所以不宣稱production CDN SLA或Firefox單一combined campaign已通過。Machine summary：
  `findings/evidence/sdk-r8/production/summary.json`。
