# 交接 2026-08-16c — 佇列變短了一項、解開了一項，而且它自己現在會跑

上一份是 [`HANDOFF-2026-08-16b-d3-d4-d5-done.md`](HANDOFF-2026-08-16b-d3-d4-d5-done.md)。
本輪的計畫是 [`PLAN-2026-08-16c-autonomous-queue.md`](PLAN-2026-08-16c-autonomous-queue.md)。

## 一分鐘版

- **一個佇列項撤銷了**：引擎不需要「回報 WASM heap」——數字本來就拿得到，
  而且**佇列指名的那個數字是常數**，做出來會讓門檻對任何 build 永遠成立。
- **3b 卡住的那個 native／WASM 不一致解掉了**：瀏覽器那個 `0` **從來不是讀回**，
  是一個在該路徑上沒有被寫入的欄位。3b 的問題因此換成一個投影決定。
- **佇列不再是散文**：`e2/relink-queue-v3.json` ＋ `check_relink_queue.py`，
  fail closed、雙向、掛進靜態目標。它已經抓到我自己寫錯的一個檔名。
- **矩陣的凍結時機從散文變成會拒跑的斷言**（D0 的 runner 與判定器各一次）。
- **048 的四十倍量到一半**：那段等待**在引擎那一側，佔 99%**——而且到此為止，
  不得再往下猜是哪一層。
- 全部在**凍結的 `e2-editor-v2`** 上量的，**沒有連結、沒有重建**。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨（`AGENTS.md`／`CLAUDE.md` 仍未追蹤，與本輪無關） |
| 出貨 profile | `e2-editor-v2`（wasm `572035ac…`），**逐輪核對未變** |
| 靜態 | `test-e2-c-static`／`test-e2-b-static` 都 exit 0 |
| 佇列 | **16 項，12 項如宣告地在樹裡，4 項未做，其中 2 項仍擋 relink**（`p1-3b`、barrier 段落順序） |
| E2-C 判定 | 仍是第一輪的 `E2_STOP_OR_RESCOPE`；本輪不改變它 |

跑一次就知道佇列狀態：

```
cd wasm_sdk_probe && python3 tools/check_relink_queue.py
```

## 六件做完的事

### 1. D4 的 heap 缺口：**佇列項撤銷**（`06254ea`）

佇列說「產品沒有任何路徑報得出 WASM heap」。**兩半都不成立**：

- 出貨引擎每個 stage 就印 `emscripten_get_heap_size()` 與 `sbrk`
  （`probe_engine.cpp:1665`，**沒有編譯守衛**），出貨 worker 在 `debug` 開著時
  轉成 diagnostic 事件，而 `createDocumentEngine` 本來就收 `debug`。
  **十二輪、兩瀏覽器、384 個 stage 事件，一個檔案都沒改。**
- 而且**那個數字不會動**：所有 profile 都是 `-sTOTAL_MEMORY=1GB` 且沒有
  `ALLOW_MEMORY_GROWTH`，所以 `heapBytes` 恆為 `1073741824`。
  **那一欄若做出來，`d4-memory` 的斜率門檻會對任何 build 永遠成立，包含在漏的。**
  會動的是同一行的 `sbrk`（一顆引擎跑八份文件：290.8 → 338.7 MB，第三輪起打平）。

P-H5（`debug` 開關不改變 PSS 斜率）**照登記判 FAILED**，而補跑的三輪對照說明了為什麼：
同一條件內的散布 ~20 MB／session，而門檻寫 2 MB——**門檻低於它要比較的量自己的雜訊**。
記成 `NOT_SEPARATED`，不是事後放寬。

**沒人預測到的一件**：同一顆引擎上**第二次 `search` 不會回來**，之後每次都 `BUSY`；
兩瀏覽器一樣，而**不做 search 的同一迴圈 8／8 全過**（控制變數已經量了）。
產品今天不走這條路（每個 session 新開引擎），所以是 SDK 層觀察與佇列候補。

### 2. 046 的不一致：**解掉了**（`9ac62d7`）

同一份 `empty-paragraph.odt`、同一個空段落：原生說「上一段、一個 block」，
出貨 build 說「零個 block」。**它們從來不可比。**

`preBlockCount` 全樹只有一處指派（在「選取矩形不為空」的分支＝range 路徑），
`postBlockCount` 只有一處（cross 路徑）。這場爭論的每一格兩邊都是 `collapsed`。

**不是靠讀原始碼定案的，是靠控制格**：一個**成功**的 barrier 打在有文字的段落上，
也回報 `preBlocks: 0`；而 range-single 那一格回報 `1`。兩瀏覽器、兩輪、完全一樣。

順帶量到：**兩個手勢現在一致了**（D2 記到的 click／selectRange 差別是「點擊沒落地」
的性質，048 修好之後兩者都是 `multi-block-readback`）；**文件最後一段的空段落不一樣**
（連讀回都沒走到，`stage-deadline:awaiting-selection`）。

### 3. 佇列變成可以跑的東西（`06254ea`）

`e2/relink-queue-v3.json` ＋ `tools/check_relink_queue.py`：

- **fail closed**：查不出來的算不通過；
- **雙向**：宣告 `absent` 的項目悄悄出現在樹裡也算漂移（3b 意外落地和 3b 沒落地一樣糟）；
- `line-equals` 整行比對，`if (false && …)` 騙不過；
- **`p1Complete` 不會因為「做完的都做完了」就說完成**——還在擋 relink 的項目會讓它是 False；
- 十個突變釘住，而且**它上線第一件事就是抓到我自己寫錯的規格檔名**。

### 4. 矩陣凍結時機的斷言（`2919fc7`）

`tools/e2_c_matrix_entry.py`，D0 的 runner 在**開瀏覽器之前**呼叫、判定器在**寫判定之前**
再呼叫一次。三種拒絕：`status` 不是 `frozen-before-D0`、baseline 還有佔位雜湊或形狀不對、
**baseline 與現場 `dist/` 的位元組對不上**。第三種才讓它是斷言——一份凍結了但描述別顆
build 的矩陣比沒凍結更糟。承重的自我測試：**只把 status 翻成 frozen、雜湊還是佔位字串，
仍然被拒**。

### 5. 引擎與投影：不要把沒被寫入的預設值當觀測值（`ea0e91d`，**只編 object**）

`preBlocksObserved`／`postBlocksObserved` 進引擎與投影；投影另補
`readbackParsed`／`readbackBlockCount`／`containment{checked,held}`——前兩個是 3b 的判準
需要的「什麼都沒讀到 vs 只讀到清單項」，第三個回答「這個判定到底是不是關於呼叫端那一段」。

**「barrier 驗自己動過的那一段」這一項的前提由我自己更正**：檢查存在而且會失敗
（`selection-does-not-contain-restore-point`，從 finding 034 就在），錯的是**順序**
——排在 `multiBlock` 後面，所以在催生這一項的案例裡準確的診斷被蓋掉。
**本輪刻意不重排**，因為瀏覽器現在還看不到讀回內容，沒辦法檢查哪個形狀才對。
記成決定，不是遺漏。

### 6. 048：那段等待在引擎那一側（`50c4eac`）

出貨 worker 無條件轉發 LOK 回呼 id 0／1，所以一次點擊在頁面上有兩個可觀測時刻；
再加一個校準（`getState` 的來回＝傳輸地板）就切得開：

| | Chrome | Firefox |
|---|---|---|
| 傳輸地板 | 1.02 ms | 0.88 ms |
| 點擊自己的來回 | **0.34 ms** | **0.45 ms** |
| 引擎那一側 | **35.1 ms** | **35.0 ms** |
| 引擎側佔比 | **99.0 %** | **98.8 %** |

五條預測全部成立。**結論到此為止**：不是我們的 transport、不是我們的 worker 排程。
是哪一層不知道——core 自己的點擊處理原生 0.6 ms，減下來剩三十幾毫秒，
而**餘數不是歸因**（040 的前例）。兩個量測限制寫進證據（id 0 與 1 被合併；
35 ms 與 D3 的 22–28 ms 是不同區間）。

## relink 佇列的現況（權威在 JSON，這裡是敘述）

| 項 | 狀態 |
|---|---|
| P1 的 1／2／3／3c／4／5／6／7／8b／9b | **在樹裡**，`check_relink_queue.py` 每次靜態檢查都驗 |
| **3b `empty-readback`** | **仍擋 relink**——不一致解掉了，但判準變成一個投影決定，要在 v3 上量 |
| **barrier 驗自己動過的那一段** | **仍擋 relink**——檢查在、順序錯；重排等第二輪的資料 |
| preBlocks／postBlocks 不得謊報 | **已進樹**（只編 object，未連結） |
| 引擎報 WASM heap | **撤銷**（量過） |
| 一顆引擎上第二次 search 不回來 | 新候補，未定性；產品今天不走這條路 |
| 矩陣 v2 | 草稿，等 v3 的五個雜湊；**凍結時機現在有守衛** |

## 下一步（沒有排序）

1. **relink 本身**——你的決定。**擋著的只剩兩項**，而兩項都需要第二輪的投影才量得清楚，
   所以「先連結、再用 v3 量它們」現在是一個合理的順序（本輪之前不是）。
2. **operator 時段**：D5 的四格 ＋ E1-C 的收復，設置完全一樣（SPEC E1-C §11.8）。
3. **048 的下一刀**：引擎側時間戳，需要一顆診斷 build。
4. **`d4-memory` 的判準改讀 `sbrk`**，並加一條「先量這一頁自己的雜訊底」——
   本輪量到 PSS 斜率的單輪散布是 ~20 MB／session。

## 外部裁決（2026-08-16，fable，subagent）：**「現在連結」被駁倒**

裁決要求三題，回來的判斷是 **Q1 反對／Q2 資料不足但缺的量測免費／Q3 同意**。
三個可驗證的 claim **我逐一核對過**：

| fable 的 claim | 核對 |
|---|---|
| 診斷 profile **不編譯任何東西**——`build_e2_discovery_profile.py` 是 `shutil.copy2(wasm, …)`，`--wasm` 是輸入 | **成立**（`:171-173`）。餵它凍結的 `572035ac`，profile 的引擎就是出貨那顆，逐位元相同 |
| 出貨引擎**早就把兩個 blocker 需要的欄位全部序列化了** | **成立**：凍結的 wasm 裡 `"readback":{"parsed":`、`"blockCount":`、`"itemCount":`、`"html":"`、`"containment":{"checked":` 各 1 筆；`"preBlocksObserved":` 0 筆（正確——那是今天未連結的改動） |
| 六個 worker patch 錨點在**凍結的** dist worker 上各匹配一次 | **成立**（六個都是 frozen=1、live=1） |

**所以我錯在哪**：我寫「沒有 build 就觀察不到」，而診斷 profile 是一個 **Python 打包
步驟**，引擎位元一個都不動。`findings/evidence/046/browser-vs-native/PREDICTION.md`
的 decision rule 帶著同一個錯誤假設（「那顆 profile 的引擎會含著佇列裡的修法」）——
那只在**選擇重編一顆新 wasm 時**才成立，而沒有任何東西要求那麼做。

**Q2**：fable 給了一個我沒寫出來的可證界——`multi-block-readback`（`:3583`）與
`selection-does-not-contain-restore-point`（`:3591`）**兩個分支都是
`kFormatMutationOutcomeUnknown`**（已核對），所以重排**不可能**把任何格從失敗翻成
成功，唯一可觀測差異是 shape 字串與訊息。缺的只剩「爭議格重排後落在哪」這一個量測，
而它不需要 relink。量完之後**預設進這次連結**。

**Q3**：同意撤銷，並且**反向駁倒了我自己登記的弱點**——`emitStage()` 在引擎裡
**無條件**印 `heapBytes` 與 `sbrk`（已核對），`debug` 閘門在 **worker 側**，
所以那個旗標擾動不了 `sbrk`。`NOT_SEPARATED` 只毒到 **PSS 通道**的比較，
而 PSS 是外部量的、可以 debug 關著量。處方：兩個通道分開跑，零 relink。

**它指出的第一個風險是我今天才裝上的守衛**：`run_e2_c_d0.py` 的 `require_entry()`
會拒絕診斷 profile（worker 被 patch 過，`workerSha256` 對不上 baseline）。
**這是正確行為**，需要的是一個**具名的旁路**（證據標成 diagnostic、永不混進矩陣證據），
不是把守衛放寬。

## 裁決之後：診斷輪跑完了，**兩個 blocker 都解除**

裁決說「這些問題不需要 relink 就量得到」。照做了，而且**兩個 blocker 都不是往我
預期的方向解決的**。證據：`findings/evidence/046/diagnostic-readback/`
（**evidence class: diagnostic**，runner 帶 `--diagnostic-round <理由>`，
理由蓋在每一份 `result.json` 裡，永遠不會被誤認成矩陣證據）。

**引擎是出貨那顆**：`dist/profiles/e2-readback-diagnostic/probe.wasm` 與
`dist/profiles/e2-editor-v2/probe.wasm` **逐位元相同**。方法的自我控制先成立
（P-046D-5）：同一頁、同一批 arm、兩個 profile 的**結果完全相同**。

**讀出來的東西**：空段落那一格是 `parsed:true, blockCount:2, itemCount:1`，
原始 markup 是 `<ul><li><p></p></li></ul><p>E1-EMPTY-AFTER</p>`——
**項目符號套用了，而讀回把下面那一段也吞進來了**。

| blocker | 處置 | 依據 |
|---|---|---|
| **3b `empty-readback`** | **撤銷** | 沒有任何一格產生「parsed 但零 block」的讀回；它賴以成立的「零個 block」是那個從未被寫入的 `postBlocks` |
| **containment 重排** | **不進這次連結** | 爭議格的 containment 是 `held: true`，重排**不會改變任何一格**（裁決事前指名的撤退條件） |

**真正的缺陷現在精確了**（新項，**不擋連結**）：空段落上 `.uno:SelectText`
**會選過頭**，把下一段也選進來——動作成功、驗證多讀一段、回報
`MUTATION_OUTCOME_UNKNOWN`。而 containment 依構造抓不到它：它問「選取有沒有涵蓋
游標」，不是「有沒有只涵蓋游標那一段」——**單向的檢查**，只抓得到選少了。

**原生那一輪也更正了**：它把 `.uno:GoToStartOfPara` ＋ `.uno:EndOfParaSel` 說成
「barrier 自己的選取對」，但引擎送的是單一 `.uno:SelectText`——那個「對」正是因為
**會逃到鄰段**（finding 034）才被取代的。原生輪重量了一個已被取代的手勢。

### 所以佇列現在說什麼

```
17 items, 12 declared present, 5 still open, 0 drifted
P1 complete: True
  blocking:  (none)
```

**連結的門檻依佇列自己的判準達成了。** 五個未做項全部具名、全部非阻擋，理由都寫在
JSON 裡。操作手冊在 [`RUNBOOK-relink-v3.md`](RUNBOOK-relink-v3.md)。

## 這一輪的三個教訓

- **在為一個佇列項付錢之前，先量它的前提。** 一次 relink 會鑄出新身分、作廢舊判定；
  這一項的前提兩半都是錯的，而查證只花了一輪量測。
- **零有兩種意思，而證據不會自己說是哪一種。** `preBlocks: 0` 被當成量測讀了兩輪，
  它其實是「沒有人寫過這個欄位」。分辨它的是**控制格**——一個成功的動作也回報 0。
- **門檻要先量雜訊底。** 登記 2 MB 去比較一個單輪散布 20 MB 的量，
  失敗的不是產品，是那個比較。
