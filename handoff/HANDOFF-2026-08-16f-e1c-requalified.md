# 交接 2026-08-16f — E1-C 收復完成，D5 四格改在同一代殼層上重跑

上一份是 [`HANDOFF-2026-08-16e-product-path.md`](HANDOFF-2026-08-16e-product-path.md)。
本段三個 commit：`d808ebb` → `40db201`。

## 一分鐘版

- **`E1_GO_ODT_EDITOR` 回來了**，而且這次綁在**現行殼層**上：`failedProperties: []`、
  八個 property 全 true、**50 格全部綁到預期 artifact、0 格 superseded**。
- **E1-C 的殼層綁定是「重新綁定」修好的，不是繼續申報**：
  新的 `e1/editor-shell-bundle-v2.json` = `187706b2…`，**v1 一個位元組沒動**。
- **D5 第七輪：四格全部 PASS，411 個真人事件、零合成**，
  跑在**殼層 v8**、用**強化後的判準**判——比 round 6 那次 PASS 更強。
- **產品路徑覆蓋率變成一份會紅的清單**：28 條路徑、**只有 7 條被自動輪走過**，
  三條標 HIGH（`undo`、`insert-text`、**回到檢查點**）。
- **relink 仍照你的決定等著**；佇列 23 項、6 項未做、**0 項擋連結**。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨 |
| E1 artifact | `835b453d…`（未動）；E1 殼層 **v2 `187706b2…`**，`intact: true` |
| E2 artifact | `572035ac…`（未動）；E2 殼層 **v8 `4daad6b4…`** |
| E1-C | **`E1_GO_ODT_EDITOR`**（2026-08-16 收復輪） |
| E2-C D5 | 四格 PASS，round-two 判準，殼層 v8 |
| 靜態 | 三個目標全部 exit 0 |

## 收復是怎麼做的（三個決定值得記住）

### 一、重新綁定，不是繼續申報

`e1/editor-shell-bundle-v2.json` 是新的一代；**v1 保持原樣**，它是 08-07 那份裁決
跑過的紀錄。divergence 檔保留並標記 `resolved`，四筆（048／050／051／052）從此
不再是「差異」，而是 v2 登記的內容。

**`resolved` 之後放寬歸零**——一個解除之後還在放行的申報就是永久豁免。這一條有
兩格突變測試：「已解除的申報什麼都不放行」（改動仍要紅）＋「已解除的申報在乾淨的
樹上仍然是綠的」（證明前一格是為改動而紅，不是為 `resolved` 這個字）。

矩陣 `e1/validation-matrix-v2.json` 啟用了——**它本來就寫著 `effectiveAt:
next-rebinding`**，這一輪就是那個 rebinding。啟用檢查也從固定答案改成**狀態一致性**：
半個轉換（寫了 `activatedOn` 卻還指著 v1，或反過來）會紅。

### 二、守衛擋下了第一次嘗試，而且擋對了

第一次跑自動相位，`integration-01` 當場失敗：
`served shell bundle does not match ./e1/editor-shell-bundle-v1.json`。
**驗證頁拒絕對一份沒申報的殼層產出證據**，並逼出正確順序（先綁定再取證）。
那次失敗原樣保留在 `attempt-01`。

### 三、第一次判定是 STOP，而兩個失敗都不是產品的

`regression` 與 `workspaceBaseline` 是**流程產物**——開了新的證據命名空間卻沒補上。
補跑之後 `failedProperties: []`。

**`preflight-before` 是事後寫的，它憑什麼成立要寫下來**：用工具本來就有的
`preserved-entry-baseline` 模式，而前提逐項核對過——core 的 HEAD 與
`git status --short` 六行**與前一輪記錄的完全相同**。真正更強的證據不在快照裡而在
每一格身上：**50 格全部綁定、0 格 superseded**，加上驗證頁在每一格開始前自己驗過
所服務的殼層雜湊（見上一點）。

## D5 第七輪：兩件事一起收掉

| | round 6 | round 7 |
|---|---|---|
| 殼層 | v6 | **v8**（`session-attestation-2.json` 從頁面外面證言前後未變） |
| 判準 | round one | **round two（強化後）** |
| 事件 | 397，零合成 | **411，零合成** |

強化判準實際咬到的東西：拖曳兩格的 `<text:list>` **打開文件數**（2 → 3 → 4）、
IME **兩次 commit 修訂號正好前進兩次**且兩串字都在文件裡、剪貼簿 **copy 與 paste
兩個都要有**。**round 6 的證據與判定原樣保留。**

**這也是第一輪跑在 051／052 都修好的 build 上的人工輪。** 前六輪的 operator 是在
「點在行下半、點在文字外都放不了游標，每次還要等 30 秒」的產品上操作的——
round 1 那句「游標沒辦法被放置」**是字面上為真的**。

## 產品路徑覆蓋率：下一個 049 在哪裡

規則的形狀和殼層 bundle 一樣：**頁面的路徑 − 已驅動 − 已豁免 必須為空**
（`e2/product-path-coverage.json` ＋ `tools/audit_product_path_coverage.py`，
已進 `test-e2-c-static`，self-test 六格）。

**28 條路徑，7 條被走過。** 三條 HIGH：

| 路徑 | 為什麼危險 |
|---|---|
| `action:undo` | 產品呼叫 `session.undo()` 的那一行從沒被執行過。D1 驗的是**殼層**的 undo，而那個差別正是 049 能活那麼久的原因 |
| `action:insert-text` | 自動的 commit 全走 adapter 或殼層，沒走過這顆鈕 |
| `listener:click#notice-action` | **產品的復原路徑**（`session.rollback()`）。規格規定 dispatched failure 的處方是 rollback，而沒有任何一輪按過它 |

它也明說自己**檢查不到**的事：它讀頁面不讀 harness，「被指名的驅動者是否真的驅動
那條路」看不出來。

## 下一步

1. **relink** —— 你的決定，目前「等一等」。門檻達成、blocking 是空的。
   手冊 [`RUNBOOK-relink-v3.md`](RUNBOOK-relink-v3.md)。
   **搭同一班車最值得的引擎工作是 block identity**（見下）。
2. **block identity 的設計 ＋ 事前預測** —— 三個模糊（046 選過頭、052 殘留、
   同一行不同 x）的共同處方。**趁 relink 還沒發生把預測寫下來，它才有事前性。**
   佇列項 `queue-verify-caret-by-block-identity`。
3. **那三條 HIGH 的產品路徑** —— 寫進產品路徑 harness 並做突變驗證。
   需要瀏覽器，等機器空著的時候跑。
4. **六個未做的佇列項**，全部非阻擋。

## 今天第二段的教訓

- **守衛擋下你自己的第一步，是它值錢的時候。** 驗證頁拒絕對沒申報的殼層取證，
  把「先綁定再取證」的順序逼了出來——那個順序如果由我自己記，今天就會記錯。
- **判定失敗要先分清楚「產品壞了」還是「流程沒做完」。** 第一次的
  `E1_STOP_OR_RESCOPE` 全部是後者，而報告只寫 `failedProperties` 不會告訴你這件事。
- **事後補的證據要說出它憑什麼成立。** `preflight-before` 不是重建，是因為
  core 那六行一字未改；而真正承重的是每一格自己記的 artifact 綁定。
