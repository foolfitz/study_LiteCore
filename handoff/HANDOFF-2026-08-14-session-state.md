# 交接 — 2026-08-14（E2-A 已發判定、E1-C 已重綁、037 併進 012、根因在上游）

接手前先讀這一份。上一份是 [`260813 的 E2-A 判定包`](HANDOFF-2026-08-13-e2a-verdict.md)
（已結案，只當提問紀錄看，**不要拿它當判定引用**）。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨 |
| **E1 出貨編輯器** | `835b453d…`＋**殼層 bundle `f9b1a52f…`**；**`E1_GO_ODT_EDITOR`（08-14 重綁）**、50 格全綁、八屬性全真 |
| **E2 出貨引擎** | `c89f069e…`；**E2-A 總判定＝`PARTIAL_GO_TO_E2_B`**，縮限七項 |
| E1-C 證據樹 | **`findings/evidence/sdk-e1/editor-validation-v2/`**（08-07 那棵 `editor-validation/` 原封保留） |
| E1-C 矩陣 | **`e1/validation-matrix-v2.json`**（`v1` 位元組保留、未修改） |
| 上游缺陷 | **finding 040**：`Scheduler::IdlesLockGuard` 在 Emscripten 上永遠等不到條件。草稿 `findings/drafts/040-bugzilla.txt`，**未送** |

**今天有兩個判定在動，兩個都不是我自己拍的**——`regression` 那一格和 §4.1 的矛盾都交給
外部裁決，理由寫在下面〈我今天站在錯的位置上兩次〉。

## 動手之前必讀（今天新增的）

1. **殼層現在綁進證據了。** `e1/editor-shell-bundle-v1.json` 逐檔記下驗證頁**實際 import**
   的五個模組＋一個彙總雜湊，進 preflight 與 per-case 綁定。改 `editor-shell/` 或 `input/`
   任一位元組，**三個檢查會紅**（其中一個指名檔案與 source／dist 哪一側）。
   **但沒有重算工具**——要手改三個地方（manifest、matrix v2 baseline、`tests/test_e1_c.py`
   裡釘死的字面值）。**最省事的路是「把檢查放寬」，請不要走那條**（任務 #43）。
2. **`test-e1-c-static` 不再相依 assets。** 它以前經由 `Makefile:486`（`Makefile` 自己是每個
   `.o` 的相依）耦合到 build 樹的 mtime，於是**凍結期間唯一可達值是 false，
   而唯一變綠的路是重連結凍結 artifact**。取而代之的是 **`test-e1-c-frozen-guard`**：
   `make --always-make -n build/e1/editor-v1/probe.js` 必須印出
   `refusing to relink a frozen profile`。它與 mtime 無關，**拿掉防護就紅**。
3. **「靜態測試」目標可能會建置。** `test-r8-c/d-static` 以前經 `.PHONY` 資產鏈
   **鑄 release id**（finding 041），而 E1-C 的 `regression` 定義裡就含它——
   `--run-regression` 每跑一次鑄一次。已修。**判斷一個測試目標會不會動到東西，
   讀配方不夠，要 `make -n` 讀整條相依鏈。**
4. **`pkill -f` 會比對到自己的指令列。** 這條備忘記過，我今天又踩了一次（exit 144）。
5. **`serve.py` 服務的是 `dist/`。** 改 `web/` 或 `editor-shell/` 之後要 `make <asset target>`，
   否則跑的是舊的。今天四個檔全是舊的。

## 今天做完的事

### E2-A：總判定 `PARTIAL_GO_TO_E2_B`（規格 10.14 節，commit `78dec50`）

決定它的那句條文**不在 E2-A 裡**：§8 的 STOP 款寫「teardown 阻塞」，而它是母規格
`SPEC-E2-000-overview.md:168`「觸發 **Finding 012 類** teardown 阻塞」的縮寫——抄寫時掉了
四個字。012 是**關檔路徑**，其操作化是 A5 的 `list-teardown` 且通過，所以 finding 039
不屬該款。**這是條文說的，不是讀法。**

**規格 §10.10 的表引用了它沒量過的 build**（A3 寫 21/105、A5 寫 11/58，那是 `25761ff0`
時代的數字，重綁兩次都沒改）。對 `c89f069e` 重算是 **A3 25/125、A4 18/270、A5 8/42**。
已補 `tools/check_e2_a_summary_numbers.py`，帶 `--self-test`。

縮限七項，其中第七項在寫的時候變得更嚴重：**「395 次全部從收合游標派送」是從 harness
形狀推論的，不是量到的**——run 與 step **沒有欄位記錄選取型態**。那一格連事後判讀都不行。
**E2-B 補掃要補的是欄位，不只是覆蓋。**

**E2-B 進場條件**：先修 finding 039，relink 後重掃 A3／A4／A5 通過，才可凍結 B 的 ABI。

### 任務 032／012／037：根因找到了，而且在上游（`478e724`、`aa68d85`）

**finding 040**：`Scheduler::IdlesLockGuard` 的建構子在非主執行緒等
`ImplSVData::m_inExecuteCondtion`，而全樹唯一的 `set()` 在 `Application::Execute()` 裡
`if (!DoExecute(...))` 的 body——Emscripten 的 `DoExecute` 標 `O3TL_UNREACHABLE`，
**永遠不返回**，那個 body 結構上進不去。

**037 併進 012**：專為此建的 `e2-preguard-profiling`（`e05fd156…`）在 037 卡死當下取到
27 格具名堆疊，第 21 格是 `doc_getTextSelection`、第 17 格是 `SwTransferable::~SwTransferable`。
`getTextSelection` 把 `pDoc->getSelection()` 取到**區域** reference，返回時解構，
銷毀它自己那份剪貼簿 `SwDoc`——同一條 `DelLayoutFormat` → guard。

**兩者是同一個缺陷的兩個入口**（誰的 SwDoc 而已），而且**文字已經取出來了，卡的是收尾**。
所以任何**複製**含 frame 選取的路徑都中招，不只那一個讀取 API。
我方擋法之所以有效，是**它在讀取前就拒絕、那份會卡的副本從沒被造出來**——不是修好了什麼。

**工具上的關鍵發現**：`Debugger.pause` 對停在 `memory.atomic.wait32` 的 worker **有效**。
上一輪判定「profile 對停等執行緒取不到樣本」之後就停手了，但 V8 的 inspector 中斷得了那個
等待——**堆疊一直都拿得到，只是沒去拿**。

### E1-C：條文修訂 ＋ 重綁 ＋ 判定重發（`4bfe431`～`ceb2596`）

- **§4.1／C2 修訂 v8**：#33 出貨的「手勢前 checkpoint」與舊條文「未保存內容不恢復」正面矛盾。
  裁決走 (A)＝修條文＋加一個**會變紅**的格；否決 (B)（要求顯式徵詢）——
  **在這個形狀下徵詢是答案恆為是的對話框，不是同意**，而 `restart({source})` 會擴開
  §3 守著的 closed contract。
- **矩陣 v2 ＋ `crash-after-checkpoint`**：實測**把 #33 關掉它就紅**在該紅的地方
  （`hasCheckpoint: false`）。這是 `crash-unsaved` 永遠給不出的紅。
- **附款一**：`CHECKPOINT_FAILED` 以前只進私有欄位，於是「沒東西可救」與「試過保存但失敗」
  是同一個可觀察狀態。現在進 typed state ＋ `recoveryNotice.checkpointFailed`。
- **附款二**：殼層 hash 納入綁定（見上）。
- **重綁**：50/50 兩瀏覽器、人工輪兩瀏覽器同一時段、八屬性全真，判定重發。

## 我今天站在錯的位置上兩次，兩次都交出去了

1. **§4.1 的矛盾**是我自己的產品改動造成的，要不要修條文由我決定就是球員兼裁判。
2. **`regression` 那一格**更明顯：我發現它量的其實是 Makefile 的 mtime、而且唯一變綠的路
   是違規重連結——但「我把檢查重新詮釋了一下，於是我的判定就過了」正是這條線一直在記錄的
   失效模式。**送出去之前先把我的利益衝突寫在問題裡。**

裁決回來的四個條件裡，**我自己想不到的是第二個**：新增 `test-e1-c-frozen-guard` 這個
正向斷言。沒有它，去掉舊相依就只是放寬——舊相依雖然是反向的，畢竟「有人重連結了凍結
artifact」會讓它變綠，那也是一種訊號。

## 覆核糾正了我，這些是我原本會留在文件裡的錯

| 我寫的 | 實際 |
|---|---|
| 「在 bundle builder 動手前停掉」 | 它**已經跑完**了，我停的是下一步（`index.json` mtime 為證） |
| 「沒有損害」 | 綁定面為零是**量到的**；`dist/r8/release-manifest.json` 的前狀態**不可知**（`dist/` 無基線） |
| 「三筆搜尋全中」 | **五筆**（第五筆是取消字串在輸出位元組上為 0 次） |
| 037「卡在後置條件讀取本身」 | 卡在**讀完之後**銷毀剪貼簿 SwDoc 的清理路徑 |
| 「至少八次 Makefile 編輯」 | **15 次**（`git log 41d27fa..HEAD -- wasm_sdk_probe/Makefile`，從 GO 那個 commit 起算）。覆核給的是 13，我沒核它的計法，所以這裡寫我自己能重算的那個 |

還有一項是我**該查而沒查**的：人工輪裡 `hasCheckpoint` 有沒有真的武裝。
實況是兩瀏覽器各 **37 個 state 為 true**、首見於 `checkpointRevision: 4`。
**如果 operator 的順序碰巧讓文件不 dirty，整輪就沒見證到新手勢形狀，而九項照樣全綠。**

## 還開著的

| # | 事情 | 卡在誰 |
|---|---|---|
| **43** | 殼層 manifest 沒有重算工具，一次合法改動要手改三處 | 可做，要設計成「先印 diff、明確旗標才寫」 |
| — | **finding 040 上游未送**（草稿在 `findings/drafts/040-bugzilla.txt`，重複單查過七組、沒有） | 使用者決定要不要送 |
| — | 038 是不是第三個入口（`doc_getSelectionType` 呼叫同一個 `getSelection()`） | **推論，未取得堆疊** |
| — | **E2-B 規格未寫**。E2-000 說 A 有結果後才寫，現在有了；但進場條件是先修 039 | 使用者 |
| — | finding 039 未修（判準 `selectionTypeBeforeReset` 已在資料裡） | 修了要 relink＋重掃 A3/A4/A5 |

## 這一輪的 artifact 帳

出貨的三個**全程未動**：`835b453d…`／`679def61…`／`c89f069e…`（每次重編前後都核對過）。
新增一個診斷用的：**`e2-preguard-profiling`＝`e05fd156…`**（037 擋法以
`OXSDK_037_GUARD_OFF` 編掉＋`--profiling-funcs`，**只有這個 profile 定義那個 macro**，
其他所有 profile 編出來的程式碼逐字不變）。**永不出貨、不綁任何判定。**
