# SPEC R6-B：Collaboration contract 與 reference service

> **日期**：2026-08-02  
> **狀態**：執行完成（GO）  
> **上層規格**：[SPEC R6-000](./SPEC-R6-000-overview.md)

## 1. 目標

定義並實作一個最小、可決定性測試的協作 domain contract，證明 sidecar 審閱與 Office blob 單一權威
版本可以阻止 lost update。契約必須獨立於 Document SDK、傳輸 library 與正式儲存產品，讓 reference
service、瀏覽器 client 與純測試 adapter 使用同一份 fixture。

R6-B 驗證的是語意，不宣稱 reference service 已具 production security、durability 或 scalability。

## 2. Contract version 與 envelope

R6 application contract 版本為 `1.0`。所有 JSON response／event 使用共同 envelope：

```ts
type ContractEnvelope<T> = {
  contractVersion: "1.0";
  requestId?: string;
  documentId: string;
  snapshotVersion: number;
  eventSequence: number;
  data: T;
};
```

- major 不同直接拒絕；不得靜默以「看起來相容」繼續。
- 較新的 minor 只有在未知欄位可忽略、未知 mutation／event 可明確拒絕時才相容。
- ID 都是 opaque string。client 不從 ID 推算排序、作者或時間。
- mutation 要有 `requestId`／idempotency key；相同 key + 相同內容重試只能得到同一結果，相同 key +
  不同內容必須拒絕。
- server timestamp 只作顯示與稽核，事件順序以 `eventSequence` 為準。

## 3. Domain model

### 3.1 文件與版本

```ts
type DocumentVersion = {
  documentId: string;
  version: string;
  etag: string;
  blobSha256: string;
  bytes: number;
  mediaType: "application/vnd.oasis.opendocument.text";
  createdAt: string;
  createdBy: string;
  parentVersion: string | null;
};
```

- 每次成功 save 都建立新 immutable version；舊 blob、metadata 與 hash 不變。
- `etag` 必須是 strong validator，並與該 version 的 bytes 一對一對應。
- v1 可用單一 parent 線性歷史；不建立 branch merge。
- 權威 current version 只能由通過 lease + compare-and-swap 的一次 mutation 前進。

### 3.2 Presence

```ts
type Presence = {
  sessionId: string;
  actorId: string;
  displayName: string;
  viewedVersion: string;
  locationHint?: { part?: string | number; page?: number };
  lastSeenAt: string;
  expiresAt: string;
};
```

- presence 是 ephemeral hint，不進文件版本歷史，也不是編輯授權。
- client 以 heartbeat 延長 TTL；連線消失後由 TTL 收斂，不要求精準即時 offline。
- location 只供顯示，不得當 suggestion anchor 或權限判斷。

### 3.3 Sidecar comment

```ts
type SidecarComment = {
  id: string;
  documentId: string;
  baseVersion: string;
  parentId: string | null;
  body: string;
  authorId: string;
  status: "open" | "resolved";
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
};
```

- reply 是帶 `parentId` 的新 immutable entry。
- resolve 是狀態事件，不改寫原 comment body。
- comment mutation 不改變 Office blob version／ETag／hash。

### 3.4 Suggestion 與 anchor

```ts
type Suggestion = {
  id: string;
  documentId: string;
  baseVersion: string;
  anchor: {
    quote: string;
    prefix: string;
    suffix: string;
    locationHint?: { part?: string | number; rectangles?: string };
  };
  replacement: string;
  authorId: string;
  status: "open" | "accepted" | "rejected" | "conflict";
  createdAt: string;
  decidedAt?: string;
  decidedBy?: string;
  acceptedInVersion?: string;
};
```

- `quote` 與 replacement 不可為空；長度設測試上限，避免把整份文件塞入 sidecar operation。
- prefix／suffix 是保存的人類可讀 context。R6 v1 不假設現有 SDK 能讀取任意 range 周邊文字。
- 自動套用前以 SDK `search(quote)` 計算候選；必須恰有一個 selection，且 `getSelection().text` 與 quote
  完全相同。零個是 `ANCHOR_NOT_FOUND`，多個是 `ANCHOR_AMBIGUOUS`。
- `locationHint` 不能打破歧義；它只能協助 UI 導覽。
- suggestion 的 `baseVersion` 不是 current version 時，R6 v1 不自動 rebase。即使 quote 看似唯一，也先
  回報 `VERSION_CONFLICT`；未來要放寬必須另有 context API 與 corpus 證據。
- 接受／拒絕只允許由 `open` 終態轉移一次。拒絕可直接完成；接受只有在新 blob CAS commit 同時成功
  時才完成，不能先把 suggestion 標成 accepted；重試相同 idempotency key 回同一結果。

此保守規則刻意避免把目前不存在的「跨版本穩定 range ID」假裝成既有能力。

### 3.5 Edit lease

```ts
type EditLease = {
  leaseId: string;
  token: string;
  documentId: string;
  actorId: string;
  baseVersion: string;
  issuedAt: string;
  expiresAt: string;
};
```

- 每份文件最多一個未過期 lease；server time 是唯一到期判準。
- token 只在 acquire／renew response 回給持有者，event 與一般 snapshot 不得包含 token。
- renew 不改 base version；若 current version 已前進，續租失敗並要求重新載入。
- release 可冪等；lease 到期後提交得到 `LEASE_EXPIRED`。
- service restart 是否保留 lease 不在 v1 durability 保證；測試 reset 必須明確清空。

## 4. HTTP 與事件表面

路徑名稱可在實作前作小幅調整，但語意與 conformance fixture 不可省略：

| Method／path | 語意 | 重要條件 |
|---|---|---|
| `GET /api/documents/:id` | 取得 current metadata | 回 strong ETag |
| `GET /api/documents/:id/versions/:version/blob` | 取得 immutable ODT | hash／bytes 與 metadata 相符 |
| `GET /api/documents/:id/collaboration` | sidecar + presence snapshot | 帶 snapshot version／event sequence |
| `POST /api/documents/:id/presence` | heartbeat／位置 hint | session + actor fixture |
| `POST /api/documents/:id/comments` | comment／reply | idempotency key |
| `POST /api/documents/:id/comments/:commentId/resolve` | resolve | idempotency key |
| `POST /api/documents/:id/suggestions` | 建立 suggestion | anchor schema validator |
| `POST /api/documents/:id/suggestions/:suggestionId/decision` | reject／mark-conflict 終態 | accept 不走此端點 |
| `POST /api/documents/:id/lease` | acquire | 單一有效持有者 |
| `POST /api/documents/:id/lease/:leaseId/renew` | renew | token + base version |
| `DELETE /api/documents/:id/lease/:leaseId` | release | token；冪等 |
| `PUT /api/documents/:id/blob` | 建立新版本，可同時接受 suggestion | `If-Match` + lease token + SHA-256 + idempotency key |
| `GET /api/documents/:id/events` | event stream／重連 | last event sequence |

`PUT blob` 的 decision metadata 必須與 blob commit 在 domain 層原子完成：不能出現 ODT 已成 v2，但
suggestion 仍永久顯示 open 的半套狀態。Reference service 可用單程序 lock 模擬 atomic section，不代表
已選定 production transaction 技術。

## 5. 事件契約

最小 event taxonomy：

- `presence-upserted`、`presence-expired`；
- `comment-created`、`comment-resolved`；
- `suggestion-created`、`suggestion-decided`；
- `lease-acquired`、`lease-released`、`lease-expired`，不含 secret token；
- `document-updated`，含 previous／new version 與 ETag；
- `snapshot-required`，通知 client 不可再靠增量事件收斂。

每份文件的 `eventSequence` 嚴格單調遞增。client 重連帶最後已處理 sequence：

- service 尚保有完整 gap 時依序 replay；
- gap 已淘汰時回 `snapshot-required`；
- client 收到重複 sequence 必須去重；
- 收到跳號不得自行假設中間事件無關，必須抓 snapshot。

R6 可選 Server-Sent Events 或 WebSocket；conformance 只依賴上述事件語意，不把 transport-specific frame
暴露到 application state。

## 6. Typed error

至少覆蓋：

- `CONTRACT_VERSION_MISMATCH`
- `INVALID_ARGUMENT`
- `NOT_FOUND`
- `IDEMPOTENCY_CONFLICT`
- `VERSION_CONFLICT`
- `LEASE_HELD`
- `LEASE_EXPIRED`
- `INVALID_LEASE`
- `ANCHOR_NOT_FOUND`
- `ANCHOR_AMBIGUOUS`
- `EVENT_GAP`
- `HASH_MISMATCH`

錯誤 response 帶 stable code、可讀 message、request ID 與目前可公開的 version metadata；不得把 stack、
filesystem path 或 lease token 回給 client。

## 7. Reference service 約束

- 僅綁 loopback，預設不對區網公開。
- 無外部資料庫與雲端依賴；測試 fixture 可一次指令重置。
- fixture clock／TTL 可注入，避免測試依靠長時間 `sleep`。
- blob、metadata、sidecar、idempotency result 與 event append 必須在單一 domain mutation 中一致更新。
- 每次測試使用獨立 state directory 或記憶體 instance；不可讀到前一輪的 lease／presence。
- 記錄 structured audit event，但 redact token 與文件 bytes。
- 限制 JSON body、ODT bytes、comment、context 與 replacement 大小；拒絕 traversal 與未知 document ID。
- 測試身份只允許固定 Alice／Bob fixture，並在 UI 明示「非正式認證」。

## 8. Conformance scenarios

1. 建立 v1 後 metadata、ETag、SHA-256 與 blob bytes 一致。
2. Alice／Bob heartbeat 出現在 snapshot；clock 前進超過 TTL 後產生 expiry。
3. comment、reply、resolve 事件順序正確，且 v1 blob hash 不變。
4. suggestion schema 拒絕空 quote、空 replacement、過長 payload 與未知欄位 mutation。
5. Alice 取得 lease；Bob 同時 acquire 得 `LEASE_HELD`，且看不到 token。
6. Alice 使用正確 ETag／token 提交 v2；parent、hash、event、suggestion decision 原子成立。
7. Bob 以 v1 ETag 提交被拒；current 仍是 v2，版本數與 blob 均未增加。
8. 錯誤 token、過期 token、token 跨文件使用全部拒絕。
9. 相同 idempotency key + 相同 request 安全重試；不同 request 得 `IDEMPOTENCY_CONFLICT`。
10. event duplicate 去重、gap replay 與 snapshot fallback 都收斂到同一狀態。
11. service fault injection 在 commit 前失敗時不產生半個 version；commit 後 response 中斷可用
    idempotency key 查回既有成功結果。
12. contract major mismatch 與未知 mutation kind 被明確拒絕。

所有 conformance 以純 domain adapter 與真 HTTP adapter 各跑一次，預期結果除 transport metadata 外一致。

## 9. Go／No-Go

**Go**：12 項 scenario 在 domain／HTTP adapter 均通過；任何競爭、重試、expiry 或 fault injection 都不
造成 lost update、secret 洩漏或半套 state；兩個 adapter 使用同一 fixture。

**部分 Go**：版本／lease／CAS 已成立，但 event replay transport 尚不穩；可讓 R6-C 使用 snapshot polling
繼續整合，但不得宣稱即時更新／重連已完成。

**停止回報**：只能用 last-write-wins、mutation 無法原子更新 version 與 suggestion、或測試必須依賴
外部服務與不可控時間。先記 finding，再縮小 contract 或替換 reference adapter。

## 10. 交付物

- versioned collaboration contract types／schema 與 canonical fixture。
- 純 domain reference implementation、loopback HTTP／event adapter。
- deterministic clock、fault injection 與 reset harness。
- domain／HTTP conformance 結果與 machine-readable summary。
- R6 DEVLOG 段落及任何重大 findings。

## 11. 執行結果（2026-08-02）

- 實作 versioned runtime validator、TypeScript types、canonical fixture、deterministic clock、pure domain、
  loopback HTTP／event adapter、browser client、fault/reset harness。
- 12 項 conformance 以同一 fixture 在 domain／HTTP adapter 各 12/12；adapter 結果一致。
- wrong／expired／cross-document lease、stale ETag、idempotency conflict、event replay／snapshot fallback 與
  contract major mismatch 均為 typed rejection。
- commit-before fault 零 version；commit-after response interruption 由相同 idempotency key 取回既有 v2，
  不產生 v3。audit 掃描不含 token／文件 bytes。
- 判定 **GO**；證據：[`../findings/evidence/sdk-r6/contract/`](../findings/evidence/sdk-r6/contract/)。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。定義 sidecar、單一權威版本、lease、CAS、事件與保守 anchor 規則。 |
| 2026-08-02 | 執行完成：domain／HTTP 24/24 conformance，判定 GO。 |
