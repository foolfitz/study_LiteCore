# 交接 2026-08-16d — D5 的人工輪走完了，而它逼出三個沒有自動化找得到的產品缺陷

上一份是 [`HANDOFF-2026-08-16c-queue-shrunk.md`](HANDOFF-2026-08-16c-queue-shrunk.md)。
本日 25 個 commit：`273c317` → `2b55697`。

## 一分鐘版

- **D5 四格全部 PASS**（第六輪，Firefox，397 個真人事件、零合成）。
  每一格的效果都在存檔裡看得到，包含一個**貼進去的字是從文件自己複製出來的**
  剪貼簿往返。
- **三個產品缺陷**在過程中被逼出來並在同日修掉：
  [049](../findings/049-the-product-save-button-writes-fifteen-bytes-of-object-object.md)（存檔寫出 15 位元組的 `[object Object]`）、
  [050](../findings/050-every-ime-commit-after-the-first-is-rejected-as-a-buffer-mismatch.md)（一個 session 只能打一次中文）、
  以及 **Ctrl+C 從來沒有問過引擎要選取**。
  **沒有一個是自動化找得到的**——它們全躺在「harness 走的路」與「使用者走的路」之間。
- **連結的兩個 blocker 都解除了**（外部裁決駁倒我的前提之後，在**凍結的引擎**上量掉），
  `check_relink_queue.py` 現在說 `P1 complete: True`、blocking 是空的。
  **但連結的決定是「先等一等」**（使用者裁定，理由寫在佇列 JSON 與手冊開頭）。
- **殼層 bundle 今天走了四代**：v3 → v4（049）→ v5（050）→ **v6（複製與 trace 接線）**。
  D3 語料輪／D4／D5 機器半邊跑在 v3；D5 的四格人工跑在 v6。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨（`AGENTS.md`／`CLAUDE.md` 仍未追蹤） |
| 出貨 artifact | `e2-editor-v2`（wasm `572035ac…`），**整天逐位元未變** |
| 殼層 bundle | **v6 `9b7e7d2a…`**（v1–v5 全部凍結，各自是某些輪次跑過的紀錄） |
| 靜態 | `test-e2-c-static`／`test-e1-c-static`／`test-e2-b-static` 全部 exit 0 |
| 佇列 | 20 項，15 項如宣告在樹裡，**5 項未做、0 項擋連結** |
| E1-C | 殼層綁定仍斷（048 ＋ 050 兩筆已申報 divergence），收復條件見 §11.8 |

## 今天分成三段

### 一、自主佇列（`273c317` … `78023c9`）

計畫 [`PLAN-2026-08-16c-autonomous-queue.md`](PLAN-2026-08-16c-autonomous-queue.md) 的六項全做完：

- **D4 的 heap 佇列項撤銷**：數字本來就拿得到（出貨引擎每個 stage 就印），
  而且**佇列指名的那個數字是常數**（`-sTOTAL_MEMORY=1GB`，無 growth）——
  做出來會讓門檻對任何 build 永遠成立。會動的是 `sbrk`。
- **046 的 native／WASM 不一致解掉**：`preBlocks`／`postBlocks` 在 collapsed 路徑上
  **從來沒有被寫入**。證明它的是控制格，不是原始碼：**一個成功的 barrier 也回報 0**。
- **佇列變成會跑的東西**：`e2/relink-queue-v3.json` ＋ `tools/check_relink_queue.py`。
- **矩陣凍結時機**從散文變成會拒跑的斷言（D0 的 runner 與判定器各一次）。
- **048 的四十倍**：那段等待**在引擎那一側，佔 99%**——到此為止，不得再往下猜。

### 二、外部裁決與診斷輪（`d769c90` … `32a780a`）

**fable 駁倒了我的主要前提**，而且三個 claim 我逐一核對成立：診斷 profile 是
`shutil.copy2` 打包，**引擎位元不動**，所以 barrier 的原始紀錄在凍結的 v2 上就讀得到。

於是兩個 blocker 當天量掉，**都不是往我預期的方向**：

- **3b 撤銷**：空段落的讀回是 `parsed:true, blockCount:2`——項目符號套用了，
  而讀回把下面那一段也吞進來。沒有任何一格產生「parsed 但零 block」。
- **containment 重排不進這次連結**：爭議格的 containment 是 `held: true`，重排
  不會改變任何一格（裁決在資料出現之前就指名的撤退條件）。
- **真正的缺陷**：空段落上 `.uno:SelectText` **選過頭**。範圍量過了：
  **只有空段落**——把游標放在有文字段落的最後一個字之後，讀回一個 block、成功。
  日常手勢是好的。

### 三、人工輪六輪（`0a1538a` … `2b55697`）

| 輪 | 瀏覽器 | 結果 | 它教了我們什麼 |
|---|---|---|---|
| 1 | Chrome | 0/4 | 四格全掛在**我漏寫的一條指示**（沒叫 operator 存檔）；量到 Chrome 的 `compositionend` 是 `isTrusted:false` |
| 2 | Chrome | 0/4 | 帶回一個 15 位元組的下載檔 → **finding 049** |
| 3 | Firefox | 0/4 | **Firefox 的 `compositionend` 是可信的**——Chrome 那個是平台限制，判準不放寬 |
| 4 | Firefox | **2/4** | 頭兩格成立；判定器只檢查「有沒有攔到存檔」不看內容——**判定器比矩陣弱**（第一次） |
| 5 | Firefox | — | 三次 commit 只進去一次 → **finding 050**；而判定器判它 PASS——**判定器比矩陣弱**（第二次） |
| 6 | Firefox | **4/4** | 全部成立，強化判準也過 |

**harness 這一路也修了四件**：一個檔案的匯出（原本要人從 console 撈變數）、
即時讀數五行（每一行對應一條判準）、指標軌跡疊圖、**存檔改由 harness 自己按**
（那一步三輪三敗）。

## 兩次「判定器比它自己的 oracle 弱」

這是今天最該被記住的方法論問題，兩次都**沒有偷偷修掉**：

1. **round 4**：凍結的 oracle 說「而且存出來的 ODT 看得到」，判定器只檢查「有沒有
   攔到檔」。內容由我手動讀（`text:list` 2 → 3 → 4）。
2. **round 5**：oracle 說「一次收合游標的 commit，**以及一次取代選取的**」，判定器
   只問「修訂號有沒有動過」——於是它對一個**默默丟掉使用者三分之二輸入**的 build
   回報成功。

兩次的處置一樣：**不追溯改判定器**（它 judged 過前面每一輪），把落差寫進證據，
強化判準寫進矩陣 v2 草稿。

## 下一步

1. **relink** —— 你的決定，目前是「等一等」。門檻達成、blocking 是空的，
   刻意留著讓 `.uno:SelectText` 選過頭那一項有機會搭同一班車。
   操作手冊：[`RUNBOOK-relink-v3.md`](RUNBOOK-relink-v3.md)（**指令交給你跑**）。
2. **E1-C 的收復** —— 仍等 `e1-editor-v1` 的 relink 決定（§11.8 條件 1）。
   今天多了一筆申報 divergence（050），**併入同一次收復，不是新成本**。
3. **五個未做的佇列項**，全部非阻擋：3b（判準已可寫，等第二輪投影）、
   containment 重排、引擎報 heap（撤銷後的殘留條目）、一顆引擎上第二次 search
   不回來、`.uno:SelectText` 選過頭。
4. **第二輪的一份殼層**：D5 的四格跑在 v6，其餘相位跑在 v3。相位判定要一份殼層
   蓋住全部——那正是 relink 之後第二輪的事。

## 今天的三個教訓

- **harness 走的路和使用者走的路不同時，只有使用者那條是沒被量過的。**
  三個缺陷都在那道縫裡：存檔按鈕、IME 的第二次、Ctrl+C。自動化不是不夠努力，
  是**結構上看不到**——每個 harness 都自己呼叫 `session.save()`／`commitText()`。
- **判定器會比它的判準弱，而且弱在你最需要它的地方。** 兩次都是「檢查了形式、
  沒檢查實質」。處方不是事後改判定器，是把落差寫下來、把強化寫進下一輪的判準。
- **推論要能被自己的量測推翻。** 今天我推翻了自己三個推論：
  「取代做不到」（量到會取代）、「沒有 build 就觀察不到」（裁決指出打包不是編譯）、
  「preBlocks 是讀回」（成功的 barrier 也回報 0）。三次都是**先量再說**才沒有寫錯。
