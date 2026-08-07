# SPEC R6-A：Reader shell 與 viewport rendering

> **日期**：2026-08-02  
> **狀態**：執行完成（GO）  
> **上層規格**：[SPEC R6-000](./SPEC-R6-000-overview.md)

## 1. 目標

把 R5 單張 canvas 驗證頁提升為可承接協作狀態的最小閱讀 shell。使用者必須能辨認正在看的文件版本、
瀏覽超過一個 viewport、搜尋內容、看見載入或過期狀態，且任何 Worker／網路錯誤都不會只停在 console。

R6-A 不追求產品視覺完成度；成功標準是狀態可解釋、操作可重複、可由自動測試觀察。

## 2. 可使用的既有 SDK 能力

R5 `writer-review` 已提供：

- `open(ArrayBuffer)` 與 ownership transfer；
- `parts`、`widthTwips`、`heightTwips`、`tileMode`；
- `render(RenderRegion)` 回傳 RGBA tile；
- `search()`、`getSelection()`；
- revision-guarded replace／undo／comment／tracked changes；
- `save()`、`close()`、cancel、timeout、Worker restart 與事件監聽。

R6-A 優先只組合這些公開能力。若缺少 viewport 所需資訊，先以小型 SDK capability 提案與 finding
說明缺口，不可直接讓 UI 讀取 LOK callback raw payload 或 Emscripten memory。

## 3. 第一個 discovery checkpoint

正式寫 reader shell 前，用既有 R5 文件確認：

1. `widthTwips`／`heightTwips` 是否代表目前 Writer part 的完整可渲染區域。
2. 相鄰與部分超出邊界的 `RenderRegion` 是否有一致結果。
3. search result 的 `rectangles` 能否穩定轉為 viewport highlight；格式若不屬公開契約，只能顯示命中數
   與選取文字，不可暗中解析未承諾格式。
4. 文件 mutation 後，既有 event 是否足以讓 cache 失效；若不足，安全預設是清除該版本全部 tile。
5. 連續 render request 的實際執行順序與 abort 行為。

結果記入 R6 DEVLOG。發現不一致時先存 browser log、輸入 region 與 artifact hash，再決定縮小功能或
提出窄 SDK 變更。

## 4. Shell 狀態模型

同一時間只能有一個主要狀態：

```text
idle → loading-core → loading-document → ready
                                      ├→ saving → ready
                                      ├→ stale → reloading → ready
                                      ├→ conflict
                                      ├→ recoverable-error → reloading
                                      └→ fatal-error → closed
ready／stale／conflict → closed
```

畫面必須同時顯示：

- document ID、權威 version／ETag 與本機 SDK revision；
- profile、core commit 與 SDK／Provider contract version；
- 目前狀態與可執行的下一個動作；
- 是否存在尚未提交的本機 bytes；
- 錯誤的 typed code，不以模糊的「載入失敗」取代衝突或 Worker crash。

遠端新版本到達時進入 `stale`，而不是假裝目前 canvas 已同步。若本機有未提交結果，reload 前必須提供
下載或明確捨棄選項；自動驗收使用下載路徑，不執行靜默丟棄。

## 5. Viewport 與 tile scheduler

### 5.1 座標與 cache key

- UI 使用 CSS pixel；所有送入 SDK 的區域在單一 adapter 轉為 twips。
- cache key 至少包含 `documentVersion`、SDK `revision`、part、scale、x／y／width／height。
- 不同版本或 revision 的 tile 絕不可共用；mutation 後若 invalidation 資訊不完整，清除該 revision cache。
- tile 像素必須驗證 `width * height * 4`，並在繪製後釋放不再需要的 buffer reference。

### 5.2 排程規則

1. 先排可見 viewport，再排一圈固定上限的鄰近區域。
2. scroll／zoom 產生新的 generation；舊 generation 尚未開始的 request 取消，完成後也不得覆蓋新畫面。
3. 同一 Worker 的 in-flight 數設有小且明確的上限；不得以大量 request 塞滿序列 queue。
4. zoom 改變 cache key；可先顯示舊 scale 預覽，但狀態需標示正在更新。
5. canvas 數量與 cache bytes 設上限；淘汰策略與命中／miss 計數寫入 metrics。
6. render error 只影響對應 tile 時可重試一次；Worker crash 則整份文件進 recovery，不做無限重試。

具體 tile 尺寸、prefetch 距離與 cache 上限先作 fixture 參數，不在 v1 凍結成公開 SDK 契約。

## 6. 最小操作

- 以滾輪／scrollbar 瀏覽文件高度；至少跨越初始 viewport。
- `fit width`、100% 與一個放大倍率；切換後重畫可見區域。
- 輸入關鍵字、下一筆搜尋、顯示命中／未命中與目前 selection text。
- 若 search rectangles 可依公開契約解析，顯示 highlight；否則只顯示結果與 selection，不以猜測座標充數。
- 顯示目前權威版本，提供 reload、下載與關閉。
- 鍵盤可操作主要控制項並有可讀 label；完整 screen-reader／caret accessibility 延後，但 R6-A 不建立
  完全無語意的 canvas-only 控制介面。

## 7. 與協作層的介面

Reader shell 只依賴下列 application-level input：

```ts
type DocumentSnapshot = {
  documentId: string;
  version: string;
  etag: string;
  bytes: ArrayBuffer;
};

type RemoteDocumentUpdate = {
  documentId: string;
  previousVersion: string;
  version: string;
  eventSequence: number;
};
```

R6-A 不直接知道資料庫、WebSocket implementation 或 lease 儲存方式。它輸出 user intent（reload、下載、
要求編輯），由 R6-C orchestration 呼叫 R6-B client。

## 8. 自動測試

### 8.1 純前端／scheduler

- viewport → twips 換算與邊界 clamp。
- 相同 key 去重、generation 淘汰、cache LRU／byte ceiling。
- stale tile 完成後不覆蓋新 generation。
- mutation／version change 清 cache。
- timeout、abort、單 tile error、Worker crash 的狀態轉移。
- `stale` 且有本機 bytes 時禁止無提示 reload。

### 8.2 Browser

Chrome／Firefox 各至少驗證：

1. 冷啟動並顯示版本與第一個 viewport。
2. scroll 到初始 viewport 外，畫面不是重複第一張 tile。
3. 切換兩個 zoom level，舊 request 不覆蓋新 scale。
4. 搜尋 Latin 與繁中 fixture，命中 selection text 正確。
5. 注入遠端 version event 後進入 `stale`，reload 取得新 ETag 並關閉舊 handle。
6. 注入 Worker crash 後顯示 typed error，重啟不沿用舊 handle／tile。
7. 關閉後沒有 late canvas mutation。

Browser evidence 記錄 viewport、scale、cache hit/miss、request／generation、首張與 scroll 後首張 tile 時間，
以及最終狀態。

## 9. 驗收與閘門

**Go**：兩個主要瀏覽器均能穩定完成開啟、跨 viewport 瀏覽、縮放、搜尋、stale reload 與 crash recovery；
所有畫面都有正確 version／revision，且 UI 只使用公開 SDK surface。

**部分 Go**：基本閱讀與狀態模型成立，但 search highlight 或增量 invalidation 缺少穩定公開資料；保留
selection text／全 cache invalidation 的安全退化路徑，將缺口記為 finding，不阻擋 R6-B。

**停止回報**：跨 viewport rendering 需要解析未穩定 raw callback、tile cache 無法可靠區分 revision，
或正常 scroll 即造成不可控記憶體成長。此時不進 R6-C 的「可日常閱讀」宣稱。

## 10. 交付物

- reader shell 與明確的 UI state model。
- viewport／tile scheduler 及其單元測試。
- Chrome／Firefox R6-A evidence 與 metrics。
- discovery checkpoint 結果、限制與必要 findings。

## 11. 執行結果（2026-08-02）

- Discovery：Chrome 150／Firefox 152 的 t1、t3 均證明完整 width／height、相鄰與部分越界 tile、
  bounded queue/cancel、semantic invalidation 與 unique／not-found／ambiguous anchor 分類。
- 安全退化：不解析 opaque rectangles；revision mutation 清除整份 tile cache；selection signature 只在同一
  open version/revision 內比較。
- Scheduler／state machine 單元測試 11/11；Chrome／Firefox browser 各 3/3。所有樣本都跨初始 viewport、
  跑重疊 zoom generation、Latin/CJK 搜尋、v1→v2 reload、Worker crash recovery 與 close 後無 late draw。
- 每個 recovery generation 完成 20 張 tile、取消 4 個舊 request，max in-flight=2。判定 **GO**。
- 原始證據：[`../findings/evidence/sdk-r6/discovery/`](../findings/evidence/sdk-r6/discovery/) 與
  [`../findings/evidence/sdk-r6/browser/r6-a/`](../findings/evidence/sdk-r6/browser/r6-a/)。

## 12. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-02 | v1。以 R5 公開 SDK 能力規劃 viewport reader 與協作狀態承接點。 |
| 2026-08-02 | 執行完成：discovery 與 Chrome／Firefox reader shell 判定 GO。 |
