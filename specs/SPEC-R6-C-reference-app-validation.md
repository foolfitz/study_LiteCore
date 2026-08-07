# SPEC R6-C：Reference app 整合與驗收

> **日期**：2026-08-02  
> **狀態**：執行完成（GO）  
> **上層規格**：[SPEC R6-000](./SPEC-R6-000-overview.md)  
> **依賴**：[R6-A Reader shell](./SPEC-R6-A-reader-shell.md)、
> [R6-B Collaboration contract](./SPEC-R6-B-collaboration-contract.md)

## 1. 目標

把 reader shell、Document／Provider SDK 與 collaboration reference service 組成一個可由兩個獨立
browser context 操作的 reference application，並用成功、衝突、斷線與復原情境證明：

- sidecar 審閱不需要多個 client 同時修改 Writer model；
- 少量修改可由短效 lease 與 compare-and-swap 安全提交；
- 遠端更新採明確 reload，不以不可靠的 binary merge 假裝即時共編；
- Provider 只能提出受控 operation，不能繞過 validator 或版本邊界。

## 2. Reference app 構成

```text
Browser context A / Alice                   Browser context B / Bob
├ Reader shell                              ├ Reader shell
├ Collaboration client                      ├ Collaboration client
├ Provider host + Provider Worker           ├ Provider host + Provider Worker
└ Document Worker / writer-review            └ Document Worker / writer-review
                 │                                      │
                 └──── loopback HTTP + event stream ────┘
                               │
                    Collaboration reference service
                    ├ immutable ODT versions
                    ├ sidecar comments/suggestions
                    ├ presence + lease
                    └ ordered event log
```

兩個 context 必須有不同 session、不同 Document Worker 與不同 JS object graph。只開兩個 iframe、但共享
同一個 parent state，不算通過。

## 3. UI 最小資訊架構

### Reader 區

- 文件 canvas／viewport、zoom、scroll、搜尋。
- document ID、version／ETag、本機 SDK revision 與 ready／stale／conflict 狀態。
- reload、下載當前權威版本、下載本機未提交 bytes。

### Review 區

- presence 列表與使用者所看 version；明示位置只是 hint。
- sidecar comment thread：新增、回覆、resolve。
- suggestion 列表：quote、context、replacement、作者、base version、狀態與 conflict reason。
- 建立人工 suggestion，以及透過 R4 Provider 建立 suggestion。

### Edit 區

- lease 狀態、持有者、到期倒數、acquire／renew／release。
- accept suggestion、save、cancel／undo。
- 衝突時顯示權威 version 與本機 base version，禁止把「儲存失敗」簡化成無資訊 toast。

測試身份 Alice／Bob 必須顯示「fixture identity；非正式登入」。

## 4. Provider 到 sidecar suggestion

R4 Provider 原本回傳 validated `replaceSelection` operation。R6 使用相同 contract，但改變 host 的產品
動作：

1. Bob 在 v1 搜尋並取得 immutable selection snapshot。
2. Provider Worker 只收到允許的文字、SDK revision 與 descriptor input。
3. Provider 回傳 replacement operation；既有 validator 驗證 type、endpoint、文字與 expected revision。
4. R6 host **不直接修改 Bob 的文件**，而把通過驗證的結果轉成 sidecar suggestion：
   `baseVersion=v1`、quote、context fixture、replacement、provider descriptor／invocation audit ID。
5. invalid、generic UNO、stale revision 或取消後 late result 均不得建立 suggestion。

轉為 sidecar 後，Alice 接受時仍需重新驗證 document version、anchor 與當下 SDK revision。Provider 的舊
validation 不是永久授權。

## 5. Accept suggestion transaction

R6-C 的接受流程固定如下：

1. 確認 suggestion 是 `open`，且其 `baseVersion` 等於目前權威 version。
2. Alice 取得綁定該 base version 的 lease。
3. Alice 的 Document Worker 已開啟同一 blob／ETag；不一致則 reload。
4. 以 `search(quote)` 確認唯一候選，再用 `getSelection()` 驗證 exact text。
5. 呼叫 `replaceSelection(replacement, { expectedRevision })`。
6. `save()` 得到 ODT bytes；client 計算／驗證必要 metadata並保留本機副本。
7. 以 `If-Match: <v1-etag>`、lease token、idempotency key、blob hash 與 suggestion ID 提交。
8. service 在單一 domain commit 中建立 v2、將 suggestion 標為 accepted、釋放 lease並發出
   `suggestion-decided`／`document-updated`。
9. Alice 以 server response 校對 v2 hash；Bob 收到事件後進入 `stale`。
10. Bob 明確 reload：關閉舊 handle，抓 v2 bytes，以新 Worker handle 開啟並搜尋 replacement。

任一步在 server commit 前失敗，權威版本與 suggestion 狀態都不變。若 response 在 commit 後中斷，client
以同一 idempotency key 查回既有結果，不再建立 v3。

## 6. 必跑整合情境

### S1：Presence 與 sidecar comment

- Alice、Bob 開啟 v1，彼此 presence 出現。
- Bob 建 comment，Alice reply 並 resolve。
- 驗證 sidecar event 與畫面一致；ODT hash、version 與 SDK revision 都不變。
- 關閉 Bob 或推進 fixture clock，Alice 看到 Bob presence 到期。

### S2：Provider suggestion 成功接受

- Bob 對固定 Latin selection 執行 R4 `text.translate` fixture。
- operation 通過 validator 後只建立 suggestion，不修改 Bob 的 local document。
- Alice 依 §5 接受並產生 v2。
- Bob 看到 stale，reload 後找到 replacement；v1 仍可下載且內容不變。

### S3：競爭提交／lost-update 防護

- Alice、Bob 都從 v1 開始；Alice 先取得 lease。
- Bob acquire 得 `LEASE_HELD`。測試再用 fault fixture 讓 Bob 持有一個已過期或錯誤 token。
- Alice 成功提交 v2；Bob 以 v1 ETag 提交不同 bytes。
- Bob 得 typed conflict，reference service 仍只有 v1、v2，current hash 等於 Alice 的結果，Bob bytes
  可由 UI 下載但未成為權威版本。

### S4：Anchor failure

- 一筆 quote 不存在、一筆 quote 在文件中重複。
- 接受時分別得到 `ANCHOR_NOT_FOUND`、`ANCHOR_AMBIGUOUS`。
- suggestion 留在 open 或轉 conflict；文件 SDK revision、blob hash、current version 不變。

### S5：事件斷線與 gap

- Bob 暫停 event transport；Alice 建 comment 並提交新 version。
- Bob 重連時先測完整 replay，再測已淘汰 gap 的 snapshot fallback。
- 兩條路最後都收斂到相同 sidecar snapshot／current version；不得把 v1 canvas 標示成 v2。

### S6：Provider 邊界回歸

- generic `.uno:*`、未知 operation、錯誤 endpoint、過長 replacement 被 validator 擋下。
- Provider cancel 後 late result 不建 suggestion。
- Provider Worker crash 不影響 Document Worker；重新啟動後可執行新的 invocation。

### S7：Worker crash 與未提交資料

- Alice 完成本機 replace、尚未 PUT 前注入 Document Worker crash。
- UI 保留已 `save()` 的 bytes 時提供下載；若尚未 save，明示本機修改不可恢復。
- 不因 Worker restart 自動重送 mutation；權威 version 不變。

## 7. Browser matrix

| 組合 | 必跑 |
|---|---|
| Chrome：Alice + Bob 兩個獨立 context | S1～S7 |
| Firefox：Alice + Bob 兩個獨立 context | S1～S7 |
| Chrome Alice + Firefox Bob | 至少 S1、S2、S3、S5 |

每個完整成功流程至少重跑 3 次；conflict／fault scenario 至少各 1 次 deterministic run。測試不得依賴人工
競速，race 由 service barrier／fixture clock 精確控制。

## 8. 文件 corpus 與 round-trip

R6 v1 使用：

- `t1-plain-zh.odt`：Provider suggestion、繁中搜尋、CAS 與主要 round-trip。
- 一份含樣式或多頁的既有 R1 corpus：viewport scroll／zoom 與 version reload。
- 一份刻意含重複 quote 的 fixture：anchor ambiguous 負向驗證。

每份成功提交的 ODT 檢查：

1. ZIP 結構、CRC 與 XML well-formed。
2. 原始必要文字／樣式仍存在，replacement 只出現在預期位置。
3. stale、invalid Provider 與 conflict fixture 的禁止文字不存在。
4. 桌面 LibreOffice 開啟並轉 PDF；記錄實際桌面版本與 exit status。
5. v1 blob hash 與 bytes 不因 sidecar 或 v2 建立而改變。

## 9. Metrics 與 machine summary

每次 run 至少記錄：

- browser／版本、client role、run ID、artifact hashes；
- engine ready、document open、first visible tile、stale-to-reload-ready；
- event reconnect／snapshot recovery 時間與 event sequence；
- lease wait、save、PUT commit 時間；
- version／ETag transition、SDK revision transition；
- tile request、cancel、cache hit／miss 與 peak cache bytes；
- 最終 server version count、sidecar counts、current blob hash；
- typed errors、是否預期、是否造成 mutation；
- `pass` 與各驗收布林值。

不得把 loopback latency 外推為 production SLA。R6 數字主要用來找 regression、事件順序與不合理等待。

## 10. 回歸與工作區保護

- 重跑 R5 review／reader browser flow、Provider conformance、resource classifier 與 profile hash contract。
- 至少跑 R3 semantic round-trip、R2 lifecycle／crash smoke 與 R1 legacy smoke。
- 比對 `libreoffice-26-8` HEAD 與進場前 status；不得把既有 dirty files 誤算為 R6 變更。
- R6 不重新連結 core 時，R5 large artifact 必須 byte-for-byte 相同；若 builder 因必要原因重跑，依 R5
  規則更新 hash 並完整重跑產品 corpus，不以 hash 漂移本身宣稱功能變更。

## 11. 驗收與判定

**Go**：三種 browser 組合完成指定 scenario；成功路徑建立唯一 v2，所有負向路徑零權威 mutation；
event replay／snapshot 收斂；Provider 與 Document Worker 隔離；桌面 round-trip 與 R1～R5 回歸通過。

**部分 Go**：Chrome／Firefox 各自雙 context 通過，但 mixed-browser event transport 不穩；保留協作 domain
與同瀏覽器 reference app 結果，將跨瀏覽器限制寫入 DEVLOG／finding。

**停止回報**：出現 lost update、silent anchor misapply、錯誤版本標示、未經 validator 的 document
mutation、或只有人工競速才能重現成功。保存所有失敗 bytes／event trace，再決定修正或縮小 R6。

## 12. 交付物

- 可由固定指令啟動的 reference service 與 reference app。
- Alice／Bob fixtures、scenario runner、fault controls。
- Chrome／Firefox／mixed-browser evidence、ODT／PDF round-trip 與 machine summary。
- R6 DEVLOG、限制、Go／No-Go 判定與必要 findings。
- 簡短人工驗收步驟；人工成功不能取代自動證據。

## 13. 執行結果（2026-08-02）

- Chrome+Chrome 3/3 與 Firefox+Firefox 3/3 完成 S1～S7；Chrome Alice+Firefox Bob 完成必要的
  S1／S2／S3／S5。race 全由 fixture clock／event retention／明確命令控制。
- Provider operation 經 R4 validator 後只建立 sidecar；Alice 接受時重新驗證 version、唯一 anchor、exact
  selection 與 SDK revision，再 save、hash、lease/CAS commit。Bob v1 競爭 bytes 得
  `VERSION_CONFLICT` 且仍可下載。
- event retained gap 走 replay；淘汰 gap 走 snapshot。Bob 在 reload 前保持 canvas=v1、authority=v2，
  沒有錯誤版本標示；明確 reload 後搜尋到 v2 replacement。
- generic `.uno:*`、未知 operation、錯 endpoint、超長 replacement、cancel late result 與 Provider crash
  都不建立 suggestion；Provider Worker crash 不影響 Document Worker。
- 人工驗收發現 accept 後「本機 edit + save」仍固定使用舊 quote；修正為以目前搜尋欄作明確 edit intent，
  accept／local replace 後同步 replacement，且真正不存在的 quote 仍回 typed `ANCHOR_NOT_FOUND`。新增
  Chrome／Firefox 兩端 accept→edit→undo 自動回歸，各 1/1 通過。
- 修正後再以 Alice／Bob 兩個獨立 browser context 引導驗收：presence、comment/reply/resolve、Provider
  suggestion accept、Bob stale 後明確 reload、lease `LEASE_HELD` 與交接、Document Worker crash/reload、
  本機 edit/save/undo，以及權威／未提交 ODT 分開下載皆符合預期。最終 service 僅 v1／v2、
  `lease=null`，人工驗收判定 **GO**。
- 7 份 v2 ODT 與 PDF 全通過，R1～R5 回歸與工作區保護通過。判定 **GO**。
- 證據：[`../findings/evidence/sdk-r6/browser/r6-c/`](../findings/evidence/sdk-r6/browser/r6-c/)、
  [`../findings/evidence/sdk-r6/roundtrip/`](../findings/evidence/sdk-r6/roundtrip/) 與
  [`../findings/evidence/sdk-r6/regression/`](../findings/evidence/sdk-r6/regression/)。人工驗收摘要見
  [`../findings/evidence/sdk-r6/manual/manual-acceptance-2026-08-02.json`](../findings/evidence/sdk-r6/manual/manual-acceptance-2026-08-02.json)。

## 14. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。定義雙 client reference app、Provider suggestion、lease/CAS、衝突與復原情境。 |
| 2026-08-02 | 執行完成：三種 browser 組合、round-trip 與回歸通過，判定 GO。 |
| 2026-08-02 | 修正 accept 後 edit 舊 quote，新增雙瀏覽器回歸；引導式人工驗收通過，維持 GO。 |
