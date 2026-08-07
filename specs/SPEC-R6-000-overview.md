# SPEC R6-000：協作 Reference Application

> **日期**：2026-08-02  
> **狀態**：執行完成（GO）  
> **依據**：[R5 結果](../DEVLOG-2026-08-01-wasm-sdk-r5.md)、
> [Document SDK 主報告 §9～§11](../RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)、
> [協作編輯器研究 §6～§7](../RESEARCH-2026-08-01-wasm-collaboration-editor.md)

## 1. 目標

用 R1～R5 已驗證的 Document SDK、Provider SDK 與 `writer-review` profile，做出第一個可重複驗收的
review-first 協作應用。R6 驗證的是產品工作流與責任邊界，不把 Office 文件本體改造成 CRDT，也不追求
完整 Web 版 LibreOffice。

最小成功流程：

```text
Alice、Bob 開啟同一份 v1
  → 看見彼此 presence
  → Bob 建立以 quote + context 錨定的 sidecar 建議
  → Alice 取得短效 edit lease
  → Alice 在本機 Document Worker 接受建議並存出新 blob
  → 伺服器以 If-Match／baseVersion compare-and-swap 接受為 v2
  → Bob 收到 document-updated，明確重新載入 v2
  → 舊 v1 的競爭提交被拒絕，不能覆蓋 v2
  → v2 可由桌面 LibreOffice 開啟
```

R6 通過後，才能主張 R1～R5 的 SDK 不只是一組 probe，而能支撐「閱讀為主、審閱協作、少量修改」的
完整參考工作流。

## 2. 基線與不可退讓的邊界

- 文件引擎使用 R5 `writer-review` profile；SDK C ABI 維持 1.1，Provider contract 維持 1.0。
- 每個瀏覽器 client 各自持有 Document Worker；協作服務不得取得 raw WASM pointer、UNO object graph、
  Emscripten `FS` 或任意 `.uno:*` 能力。
- Office blob 是不可變版本；服務端以新 blob 建立新版本，不就地覆寫已發布版本。
- sidecar 留言／建議與 ODT 內嵌 comment 是不同資料層，R6 不把兩者暗中混用。
- 同一時間只允許一個有效 edit lease；儲存必須同時驗證 lease 與 base version／ETag。
- 遠端文件更新不直接注入正在執行的 Writer model；client 提示後明確 close／reopen 新版本。
- selection token、tile 座標與頁碼不是跨版本永久 ID。建議以原文 quote、前後文與 base version 為主要
  anchor；座標只能作 UI hint。
- quote/context 無法唯一重新定位時必須回報衝突，禁止猜測後靜默套用。
- 不修改 `libreoffice-26-8` tracked 檔案；若 R6 需要 core 修改才能成立，停止該路徑並記錄 finding。

## 3. 子 spec 與執行順序

| Spec | 內容 | 依賴 | 完成訊號 |
|---|---|---|---|
| [R6-A](./SPEC-R6-A-reader-shell.md) | 可操作的閱讀 shell、viewport tile、搜尋與狀態模型 | R5 artifacts | 單 client 閱讀流程可自動重跑 |
| [R6-B](./SPEC-R6-B-collaboration-contract.md) | 文件版本、sidecar、presence、lease、CAS 與事件契約 | 無；可與 A 先平行設計 | 純 domain／HTTP conformance 通過 |
| [R6-C](./SPEC-R6-C-reference-app-validation.md) | 整合雙 client 工作流與跨瀏覽器驗收 | A + B | 完整流程、衝突防護與 round-trip 通過 |

執行時先凍結 B 的 domain fixture 與錯誤語意，再讓 A、B 各自完成；C 只負責整合，不在整合階段臨時
發明新的協作規則。

## 4. R6 v1 範圍

### 4.1 Reader shell

- 開啟本機測試服務提供的版本化 ODT。
- 顯示載入、ready、stale、saving、conflict、fatal 與 closed 狀態。
- 依 viewport 排程 tile，支援基本縮放、捲動、搜尋與選取文字顯示。
- 文件更新後清楚提示目前畫面仍是舊版本，並提供明確 reload 動作。
- 保留下載當前版本與下載本機未提交結果的逃生路徑。

### 4.2 Sidecar collaboration

- 兩個 fixture identity；僅供測試，不宣稱 production authentication。
- presence：使用者、目前文件版本、可選頁面／位置 hint、最後活動時間與 TTL。
- sidecar comment：建立、回覆、resolve；不寫入 ODT。
- suggestion：`baseVersion`、quote、prefix／suffix context、replacement、作者、時間與狀態。
- 建議接受必須先重新定位並取得 lease；歧義、遺失或 stale 都產生 typed conflict。

### 4.3 Versioned editing

- 短效、單一持有者 edit lease；取得、續租、釋放與逾時語意可測。
- save 使用 base version／ETag compare-and-swap；成功建立不可變新版本。
- stale submit、錯誤 lease、過期 lease、重複提交均不得改變權威版本。
- 成功提交後廣播單調遞增的 `document-updated` event；其他 client 明確重新載入。
- 使用 R3 semantic operation 或 R4 經 validator 的 Provider operation 套用建議，不能加入 generic command
  passthrough。

### 4.4 Reference service

- 本機、可重置、可決定性重跑的最小服務與固定 fixture。
- 提供真實 HTTP 條件式請求與事件通道；不可只在同一個頁面的共享 JavaScript object 模擬成功。
- 記憶體儲存或測試目錄皆可，但每輪必須隔離，且輸出可供 round-trip 驗證。
- 測試可注入 event delay、lease expiry、stale ETag 與斷線／重連，不依賴外部 SaaS。

## 5. 明確不在 R6

- ODT／DOCX 本體 CRDT、OT 或真正 multi-writer 合併。
- 將遠端鍵盤事件、binary diff 或任意 UNO command 注入另一個 client。
- 正式帳號、ACL、OAuth、secret broker、稽核法規或 hostile multi-tenant sandbox。
- 正式資料庫、object storage、WebDAV、Nextcloud、CDN 或高可用部署。
- 離線修改後自動 merge、P2P／WebRTC 與 Service Worker background sync。
- 完整編輯 toolbar、複雜排版、圖片／表格編輯、Calc／Impress。
- DOCX、真 IME、完整 accessibility、行動裝置與 100 頁壓力 corpus；列入後續里程碑。
- `writer-automation`。受控 Automation contract 仍是獨立研究線，不以 R6 UI 需求順便擴大 SDK。
- 更深的 WASM／resource 裁切。R6 只監測 R5 artifact 是否漂移，不同時改 link graph。

## 6. 協作狀態與錯誤語意

R6 的 application-level contract 使用獨立版本，不與 Document SDK protocol 或 C ABI 共用版本號。至少
要能表達下列穩定錯誤碼：

| 錯誤 | 含意 | client 行為 |
|---|---|---|
| `VERSION_CONFLICT` | base version／ETag 已過期 | 保留本機 bytes，提示 reload，不自動重送 |
| `LEASE_HELD` | 另一使用者持有有效 lease | 維持唯讀並顯示持有者／到期時間 |
| `LEASE_EXPIRED` | 提交時 lease 已失效 | 不提交；要求重新取得並重新驗證 anchor |
| `INVALID_LEASE` | token 與文件／使用者不符 | 視為操作失敗，不洩漏有效 token |
| `ANCHOR_NOT_FOUND` | quote/context 無法定位 | 建議維持未套用，交由人工處理 |
| `ANCHOR_AMBIGUOUS` | 有多個同等候選位置 | 禁止任選其一套用 |
| `EVENT_GAP` | client 偵測事件序號缺口 | 重新取得 snapshot，不猜測缺失事件 |

所有 mutation response 必須帶回權威版本、事件序號或可用來重新同步的 snapshot version。

## 7. 實驗與證據紀律

R6 是實驗，不把「最後成功」當成唯一紀錄。執行時必須：

1. 建立 `DEVLOG-<日期>-wasm-sdk-r6.md`，記錄假設、嘗試、否證、取捨、限制與最後判定。
2. 原始與機器可讀證據放在 `findings/evidence/sdk-r6/`；至少包含 contract、browser、conflict、
   round-trip 與 regression summary。
3. 每個失敗嘗試記錄輸入、環境、預期、實際、是否可重現與後續決定；不得只留下最後一次成功輸出。
4. 可重現且會影響架構、SDK 邊界、瀏覽器相容性或上游的發現，依 `findings/TEMPLATE.md` 建立編號
   finding；不要等到 R6 結束才回憶補寫。
5. 文件中明確標示「已觀察」、「推論」與「待驗證」。猜測不得升格為結論。
6. 遇到同一阻礙反覆嘗試兩次仍無新證據時，先停下整理 finding 與替代路徑，再決定是否繼續。

## 8. 驗收

1. Reader shell 在 Chrome／Firefox 均可開啟、顯示、搜尋、捲動／縮放並下載版本化 ODT。
2. 兩個獨立 browser context 連入同一文件時，雙方 presence 在 TTL 內出現；關閉／逾時後消失。
3. sidecar comment 的建立、回覆、resolve 不改變 ODT blob hash。
4. suggestion fixture 完整保留 base version、quote/context、replacement 與作者狀態。
5. 唯一 anchor 可套用；零個或多個候選均得到 typed conflict 且不修改文件。
6. 有效 lease + 正確 ETag 的提交只建立一個新版本；舊版本仍可讀且 byte-for-byte 不變。
7. 競爭提交、過期 lease、錯誤 token與重複提交全部不能造成 lost update 或額外版本。
8. `document-updated` 事件讓另一 client 進入 stale 狀態；reload 後看到新版本，舊 Worker 已關閉。
9. 強制 event gap／斷線重連後以 snapshot 收斂到權威狀態，不重播未知 mutation。
10. 至少一條建議由 R4 Provider 產生並經既有 validator 套用；invalid operation 仍不得進 document sink。
11. 最終 ODT 通過 ZIP／XML、預期內容與桌面 LibreOffice 開啟／轉 PDF round-trip。
12. R1～R5 自動回歸、R5 profile／resource integrity 與 core 工作區完整性全部通過。
13. 產出 R6 DEVLOG、machine summary、protocol fixtures、browser evidence 與所有重要 finding。

## 9. Go／部分 Go／停止回報

**Go**：Chrome／Firefox 的雙 client 流程成立；sidecar、lease、CAS、stale reload 與 Provider validator
邊界都有自動證據；衝突不遺失資料；輸出可桌面 round-trip；R1～R5 無回歸。

**部分 Go**：版本／lease／sidecar contract 與單瀏覽器雙 context 成立，但其中一個主要瀏覽器的事件
重連或 viewport shell 不穩定。保留 domain contract 與通過的 browser evidence，不宣稱 reference app
已跨瀏覽器完成。

**停止回報**：可靠儲存必須放寬為 last-write-wins、建議套用必須依賴不穩定內部 object ID、需要暴露
raw UNO／Emscripten surface、或為完成協作而必須修改 LibreOffice core。此時整理 finding，評估轉為
server-native LOK 或縮小應用範圍。

## 10. 交付物

- `wasm_sdk_probe/` 內的 reader shell、collaboration client、reference service 與測試 fixture。
- `findings/evidence/sdk-r6/summary.json` 與分項原始證據。
- `DEVLOG-<日期>-wasm-sdk-r6.md`。
- 必要的新編號 findings 與對應 evidence。
- R6 結果回填本 spec；未通過項目不得只留在 console 或對話紀錄。

## 11. 執行結果（2026-08-02）

- R6-A discovery 與 reader shell 為 GO：Chrome／Firefox 各 3/3，公開 SDK 完成 viewport、zoom、搜尋、
  stale reload、Worker crash recovery 與成功 close；search rectangles 維持 opaque，不宣稱 highlight。
- R6-B 為 GO：contract `1.0` 的 12 項 scenario 在 pure domain／真 HTTP adapter 各 12/12，包含
  lease、CAS、idempotency、expiry、event gap 與 commit 前後 fault injection，無 lost update／token 洩漏。
- R6-C 為 GO：Chrome+Chrome 與 Firefox+Firefox 各 3 次 S1～S7，Chrome+Firefox 跑 S1／S2／S3／S5；
  兩端為獨立 browser context、Document Worker 與 object graph。
- 7 份 v2 ODT 均通過 ZIP CRC、所有 XML、內容／樣式／禁止文字檢查，並由桌面 LibreOffice 26.2.4.2
  成功轉 PDF。R1～R5 回歸與最終 preflight 全數通過。
- `writer-review` loader／WASM SHA-256 仍為 `35d96f…c63566`／`ba257b…dfc6`，core HEAD 與進場前
  dirty state 未改變；本輪沒有重建或修改 LibreOffice core。
- 已知限制：finding 012 的 `t2-styled.odt` 特定 discovery 操作組合 close timeout 尚待最小化；規格必要
  t1／t3 corpus 均正常，不影響 R6 GO。

Machine summary：[`../findings/evidence/sdk-r6/summary.json`](../findings/evidence/sdk-r6/summary.json)。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。依 R5 GO 結果建立協作 reference application、實驗證據與停止條件。 |
| 2026-08-02 | 執行完成：R6-A／B／C、browser matrix、round-trip 與回歸全數 GO。 |
