# SPEC R8-C：Service Worker離線、更新與rollback復原

> **日期**：2026-08-04  
> **狀態**：已完成；`PARTIAL_GO`，允許進入R8-D  
> **上層規格**：[SPEC R8-000](./SPEC-R8-000-overview.md)  
> **前置閘門**：[SPEC R8-B](./SPEC-R8-B-versioned-artifact-delivery.md) GO或部分GO

## 1. 目標

在R8-B已證明direct delivery不混版後，加入Service Worker與versioned CacheStorage，使下列流程可預測：

- 全新安裝與第一次啟動；
- hot cache與offline重開；
- candidate背景staging、使用者同意切版與新舊client並存；
- install／activate中斷、browser關頁、cache entry損壞與storage write failure；
- candidate健康檢查失敗後回到last-known-good；
- 有界保留舊release並安全evict。

R8-C不追求「永遠無提示熱更新」。文件引擎與Worker必須pin release；安全reload優先於執行中換版。

## 2. Ownership與狀態模型

### 2.1 Release slot

```text
absent
  └─ staging
       ├─ failed ─────────────► delete candidate-only cache
       └─ ready
            ├─ activate for new client
            ├─ pinned by old client
            └─ health failure ─► rollback to last-known-good

active ─► retiring ─► evict only after no client pin + retention rule
```

每個cache name含schema與完整release ID；不得把不同release放進共用「current」cache。bootstrap維護的current／
candidate／last-known-good metadata本身需小型、原子且可重建；metadata失敗時由cache inventory保守恢復，不猜測
最新版本。

### 2.2 Client pin

- navigation取得一個release ID後，該page、Document Worker與所有mandatory artifacts固定同release。
- candidate ready不影響已開啟文件；host顯示update available，由明確reload/new session採用。
- `controllerchange`不得直接替換正在使用的Worker或重送mutation。
- 多tab各自回報pin；舊release只有在無client pin且超過凍結retention條件後才可evict。
- crash recovery預設重用同release；若finding 014 generation budget耗盡，要求整個browser session reload，
  不能暗中切candidate。

## 3. Install與activate contract

### 3.1 Install/staging

- 先fetch／validate candidate manifest，再建立candidate專用cache。
- mandatory graph逐項套R8-B HTTP/media/encoding/size/hash驗證後才寫cache。
- 任一mandatory失敗，candidate標failed並清除candidate-only entry；last-known-good不變。
- optional font packs不必阻擋base install，但已選為locale mandatory的pack必須完整stage。
- concurrent install由release ID與single-flight lock序列化；late舊candidate不得覆蓋新metadata。

### 3.2 Activate

- candidate ready後才可成為新client預設；activation metadata更新要有recoverable journal／等價原子策略。
- 不無條件`skipWaiting`搶走既有client；採用策略由R8-A凍結browser evidence決定。
- activation後先跑manifest／cache inventory與最小runtime health check，再升格last-known-good。
- health check不能修改使用者文件；使用自有fixture或engine init/open/read/close bounded probe。
- health failure恢復上一release並留下typed狀態，不反覆reload loop。

## 4. Fetch與offline contract

- app artifact request只從client-pinned release cache或該release的verified network fetch取得。
- navigation/bootstrap使用network/update policy，但offline時只打開已完整ready的known-good shell。
- offline cold且沒有完整release回`OFFLINE_RELEASE_UNAVAILABLE`，不得拼湊部分browser HTTP cache。
- cache entry缺失或hash不符時，online可repair同release；offline則拒絕啟動並保留其他完整release。
- user document/API/collaboration request採network與其自身storage contract，不進application artifact cache。
- test fixture只有明確allowlist才可cache；URL query不作文件identity。

## 5. Rollback與eviction

- 至少保留active與一份last-known-good，另可保留仍被client pin的release。
- candidate永遠不能因「版本號較新」取代known-good；需完整install與health evidence。
- rollback可由automatic health failure或明確使用者action觸發；記from/to release與原因。
- rollback後新client採known-good，舊client維持原pin直到安全reload；不跨release熱換Worker。
- eviction先列plan、確認client pins、刪release cache，再更新inventory；中途失敗可重跑。
- quota壓力優先刪failed/staging、過期retiring，再考慮optional packs；不得先刪唯一known-good mandatory graph。

## 6. Fault與recovery矩陣

每個scenario有固定ID、barrier與expected cache/release/client state：

| 類別 | 最低案例 |
|---|---|
| Fresh | 空profile online install、install後restart、空profile offline |
| Warm/offline | hot online、ready release offline、offline entry缺損 |
| Update | old client＋candidate、new client採candidate、old client仍pin old |
| Interrupt | manifest後關頁、artifact中斷、cache write後metadata前中斷、activate前後關頁 |
| Integrity | wrong bytes/hash/type/encoding/size、cache entry被替換、跨release URL |
| Storage | deterministic write reject、quota-like failure、eviction中斷、metadata損壞 |
| Health | candidate engine init/open/close失敗、Finding 012 bounded close、Firefox generation budget |
| Rollback | candidate failed、activation health failed、rollback target缺失、rollback後offline |

不得以人工快速關頁製造競速；runner在Service Worker／server barrier確認stage後終止page或browser，保存前後cache
inventory。真browser quota另依A分類，不用mock結果取代。

## 7. UI與typed recovery

Host最少顯示：

- current/candidate release、online/offline、downloading/verifying/ready/failed；
- update大小與mandatory/optional pack分類；
- retry、cancel download、reload to update、continue current與rollback（可用時）；
- restart-required與unsaved document提示；
- typed error、retryability與下一步，不顯示stack trace給一般使用者。

若文件有unsaved mutation，update/reload action不得自動執行；先讓使用者save/download或取消。Recovery不自動
replay Document SDK mutation。

## 8. Browser矩陣

- Chrome／Firefox各以隔離profile執行fresh、warm、offline、update、interrupt、integrity、storage與rollback。
- fresh/warm/offline/update/rollback happy path各至少3次；deterministic negative各至少1次並驗證後續known-good。
- 同時開至少2個client驗證pin與retiring；不依DOM文字推測，直接查SW registration、controller與cache inventory。
- 每次成功runtime跑R6 reader smoke及R7 t1 open/search/render/close；candidate health另使用bounded自有fixture。
- Firefox runner遵守R8-A凍結generation budget，避免把finding 014已知耗盡誤判SW功能失敗。
- browser profile只存於測試temporary directory；結束後由runner可回收，不改使用者日常profile。

## 9. Evidence

```text
findings/evidence/sdk-r8/service-worker/
  browser/<browser>/<scenario>/run-N/
    result.json
    browser.log.txt
    network.json
    service-worker.json
    cache-before.json
    cache-after.json
  interruption/
  quota/
  rollback/
  summary.json
```

每個result至少記release graph hash、client pins、SW version/state、cache keys/bytes、barrier、typed error、recovery
action、runtime smoke與active Worker/handle。不可保存真使用者document或credential。

## 10. GO／部分GO／停止條件

**GO**：兩browser的fresh、warm、offline、update、多client pin、中斷、integrity、storage與rollback矩陣通過；
沒有任何混版或唯一known-good遺失；cache保留有界；R6/R7 smoke與unsaved mutation安全邊界成立。

**部分GO**：原子release與offline/rollback成立，但某browser必須顯式reload才能activate，或真quota只能留待T2
環境；產品policy明確採安全降級後可進D。

**停止回報**：新舊client取得混版graph、失敗candidate成為active、唯一known-good被刪、offline啟動部分release、
controllerchange熱換既有engine、update造成unsaved mutation重送／遺失，或cache eviction無法形成有界策略。
保存中斷點前後inventory與log，建立finding並停止進D。

## 11. 交付物

- release-aware Service Worker、client pin/update UI與cache inventory API。
- deterministic interrupt/storage/rollback runner與unit/browser tests。
- Chrome／Firefox原始evidence與machine summary。
- R8 DEVLOG與必要finding。
- D的精確檔案、命令、T2需求與預期產物，另行取得確認。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-04 | v1。定義release slot、client pin、Service Worker install/activate、offline、rollback與eviction。 |
| 2026-08-04 | 完成實作與Chrome／Firefox T0/T1正式矩陣；判定`PARTIAL_GO`。 |

## 13. 執行結果（2026-08-04）

### 已觀察

- release A／B／C使用不同immutable ID；mandatory graph完整驗證後才進ready／active。
- Chrome與Firefox的T0／T1 full suite全部通過：fresh、warm、offline、atomic repair、A→B→C、rollback、
  client pin、manifest／artifact／metadata／activation barrier、deterministic write failure、metadata backup、
  health failure、cache corruption與bounded eviction皆維持同一release graph。
- Firefox的同頁iframe多client probe曾在old-client ready等待900秒；完整失敗結果與截圖已保存。改用同一
  Firefox profile的三個WebDriver tab後，6秒內觀察到A與B兩個client pin同時存在，正式full suite也通過。
- expected typed error頁最初未保存錯誤後的SW state，導致7個negative gate缺少current／known-good證明；補上
  唯讀status snapshot後重跑通過。這些失敗嘗試均保存在`service-worker/attempts/`。
- after-preflight確認core HEAD、既有dirty狀態、R5 loader／WASM hash與三版release set未漂移。

### 推論

- iframe在Firefox headless/WebDriver下不適合作為正式client ownership同步點；獨立tab更接近實際多文件client，
  且能直接由SW `message` source client ID量測pin。
- local deterministic write reject足以證明known-good保留與cleanup流程，但不能等同真browser quota exhaustion。
- update必須由reload／新session採用；不熱換既有Document Worker是安全產品契約，不是功能失敗。

### 待驗證／正式缺口

- 真quota exhaustion留待可控部署環境；沒有安全、跨browser且不污染使用者profile的本機控制。
- T2 HTTPS／CDN與實際production latency由R8-D在另行授權環境執行；本輪沒有此環境。

### 判定

`PARTIAL_GO`。所有R8-C safety checks為true，允許進入R8-D；部分GO只來自真quota與顯式reload限制。
機器摘要：`findings/evidence/sdk-r8/service-worker/summary.json`。
