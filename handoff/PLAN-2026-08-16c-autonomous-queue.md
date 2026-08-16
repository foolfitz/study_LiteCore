# 後續任務計畫 2026-08-16c — 讓 relink 的內容先變小、再變確定

上一份計畫 [`PLAN-2026-08-16-autonomous-queue.md`](PLAN-2026-08-16-autonomous-queue.md)
的六項全部做完；本份接在交接
[`HANDOFF-2026-08-16b-d3-d4-d5-done.md`](HANDOFF-2026-08-16b-d3-d4-d5-done.md) 之後。

**排序的依據只有一句**：`P1 完成才能 relink，漏一項就是第二次 relink`——所以
**先做能改變佇列內容的事**（拿掉一項、或把一項的形狀定下來），再做把佇列釘死的守衛，
最後才是與 relink 無關的量測。

---

## 開工前先講一件會改變佇列的事（推論，還沒量）

佇列上寫著「**引擎要在 typed state 裡報自己的 WASM heap**，因為**產品沒有任何路徑
報得出這個數字**」。**這個前提現在看起來是錯的**，而它是 D4 掉出來、也是第二輪
`d4-memory` 能不能脫離 PARTIAL 的唯一理由。

讀原始碼與對出貨位元組比對得到的四件事（**都還沒有在瀏覽器上跑過**）：

| 觀察 | 位置 |
|---|---|
| `emitStage()` **沒有任何編譯守衛**，而且它印的就是 `emscripten_get_heap_size()` | `src/probe_engine.cpp:1665-1674` |
| 一次開檔會走過 **7 個 stage**（`open.begin` … `open.query-metadata`），關檔另有 2 個 | `:2217-2281`、`:1823-1827` |
| **出貨的 `e2-editor-v2` 位元組裡就有** `heapBytes` 與 `"type":"stage"` | `dist/profiles/e2-editor-v2/probe.wasm`（byte grep） |
| 出貨的 worker 會把它轉成 `diagnostic` 事件，**閘門是 init 時的 `debug`**，而 `createDocumentEngine({debug:true})` **本來就收這個選項** | `dist/…/sdk-worker.js:776-778`、`sdk/document-sdk.js:96,111` |

也就是說：**一顆位元組都不用改、一個 hash 綁定的檔案都不用動**，頁面就可能拿得到
每一次開檔的 heap 數字——而 D4 的循環正好是一次循環開一次檔。

**先不要改任何文件的判定**：這是讀出來的，不是量出來的。T1 就是去量它。

---

## T1 — 把 D4 的 heap 缺口重新量一次（**可能拿掉一個佇列項**）

**為什麼排第一**：它是唯一一個可能讓 relink 的佇列**變短**的任務，而佇列變短比佇列
做完便宜。反過來如果量不到，佇列項就從「聽起來合理」升級成「量過而且知道為什麼」。

**做什麼**

1. 先寫 `PREDICTION.md`（**在跑之前**），登記四條：P-H1 開一次檔會收到 ≥1 個帶
   `heapBytes` 的 stage 事件；P-H2 每個 D4 循環各拿得到一個值；P-H3 值隨循環單調
   不減（`emscripten_get_heap_size()` 是配置量，不是使用量——**這一句要寫進預測，
   不是事後解釋**）；P-H4 `debug:true` 與 `debug:false` 兩輪的 PSS 斜率沒有差別。
2. 在**出貨的 `e2-editor-v2`** 上跑 D4 的記憶體格，`debug:true`，把 heap 值填進
   R7-D sampler 早就在讀的 `wasmHeapBytes` 欄位（欄位已存在，一直是 `null`）。
3. **P-H4 是這一項的自我防衛**：`debug:true` 會多送事件，多送事件本身會用記憶體。
   不做這個對照，就是拿一個被觀測改變過的東西去判它有沒有漏。

**驗收（先寫死）**

- 拿得到值 → `d4-memory` 用**現有出貨 artifact** 重判，佇列項改寫成它真正剩下的
  形狀（可能是「不靠 `debug` 也要看得到」，也可能是**整項刪除**），並在
  `PLAN-E2-C-relink-v3.md` 與 D4 的證據裡各記一次**為什麼原本寫錯**。
- 拿不到值 → 記下**卡在哪一層**（事件沒送出／worker 沒轉／頁面沒收到），佇列項保留，
  而且從此帶著一個可否證的理由。
- 兩種結果都不得把 `emscripten_get_heap_size()` 講成「產品用掉的記憶體」。

**不做**：不改 `sdk/document-sdk.js`、不改 `sdk/sdk-worker.js`、不改任何殼層 bundle
綁定的模組。這一項的價值正是**它不需要動它們**；一旦要動，它就不再是「今天就能量」。

---

## T2 — 3b 卡住的那個不一致（**一個量測，不是一個決定**）

**現況**：同一個空段落，core 說「選取跑到**上一段**、blockCount 1」，出貨 build 說
「零個 block」。**解釋清楚之前不得把 `empty-readback` 這個名字寫進引擎**——這是
046 已經定案的紀律。

**做什麼**

1. 先登記預測與**三個候選解釋**：(a) 兩邊的選取對不是同一組 UNO 動作；
   (b) 兩邊讀的不是同一個段落（native 的 `.uno:GoToStartOfPara` ＋
   `.uno:EndOfParaSel` 已量到會往上走一段）；(c) 讀回字串相同、只是 parser 走了
   不同分支。**三個各自要有能把它殺掉的觀測**。
2. 在出貨 build 上跑同一份語料同一個手勢，**把 barrier 的原始讀回字串整段留下來**
   （不是只留分類結果），連同本輪剛補上的 `itemCount`。
3. 與 `findings/evidence/046/native/` 的原生輸出**逐欄並排**。
   `tools/test_format_readback_parser.py` 已經能把出貨的 C++ scanner 切出來單獨編，
   所以「同一個字串餵給同一支 parser」是可以直接做的對照——**先做這個**，
   它能一次殺掉候選 (c)。

**驗收**

- 不一致有了成立的解釋 → 3b 的判準可以寫，**而且要寫成矩陣 v2 的格**（草稿裡
  「空段落兩手勢並排」那一格就是為它留的）。
- 沒有解釋 → 3b 繼續不寫，但**卡住的問題要再換一次**，並記下下一個可控變數。
  **不得因為 relink 快到了就把它降級成「先照 native 寫」。**

---

## T3 — 讓佇列自己可以被跑：`tools/check_relink_queue.py`

**為什麼**：這張佇列表**騙過我們兩次**（3b 記成已寫而 `grep` 零筆；第 8 項寫成
「一併修」而實際只修一處）。兩次都是靠**人工稽核**抓到的，而人工稽核不會在連結那天
自動再跑一次。這正是本輪那條教訓的形狀：**沒有人跑的檢查會爛掉**。

**做什麼**：P1 每一項各給一個機器可判的檢查（引擎符號／shape 字串／manifest 欄位／
測試存在且會紅），彙總成一個 exit code。**fail closed**：查不出來的項目算不通過，
不算通過。接進 `test-e2-c-static`。

**驗收**：六個突變各自要能把它變紅——把 3b 的 shape 拿掉、把
`selectionObserved` 閘門註解掉、把 `inlineFormatEnabledIsHonoured` 從 builder 拿掉、
把 ABI 常數改回 2、把 v3 的 Makefile target 刪掉、把 `itemCount` 從 worker 投影拿掉。
**突變不通過的檢查等於沒有檢查。**

---

## T4 — 矩陣 v2 的凍結時機守衛（草稿裡是散文，要變成程式碼）

`validation-matrix-v2-draft.json` 的 `freezeProcedure.entryAssertion` 現在**只是一段
文字**：「D0 必須在任何 baseline 雜湊還是 `TO-BE-FILLED-AT-RELINK`、或 `status` 不是
`frozen-before-D0` 的時候拒跑」。外部裁決指名這個窗口是第一輪的錯唯一能重演的地方。

**做什麼**：把它寫進 `run_e2_c_d0.py` 與 `analyze_e2_c_d0.py` 的**進場斷言**，
並加測試。

**驗收**：**今天就測得到**——草稿的五個雜湊現在全是佔位字串，所以斷言現在必須拒跑；
把 `status` 改成 `frozen-before-D0` 但雜湊仍是佔位字串，也必須拒跑（否則這個守衛
只擋得住忘記改 status 的人）。

---

## T5 — 引擎側的兩項修改（**只編 object，不連結**）

順序在 T1／T2 之後，因為**這兩項的內容取決於它們**：

| 項 | 取決於 |
|---|---|
| barrier 驗自己動過的那一段 | T2——如果不一致的成因是選取對本身走錯段，這一項的修法就會變 |
| 引擎在 typed state 報 heap | T1——可能整項不需要 |

**紀律照舊，而且加一條**：只編 object 的檢查要編到 **scratch 目錄**，不得編進任何
profile 的 build 目錄（P0 的那條違規紀錄）。archive → 只編 object → 停。
**這一輪不連結。**

---

## T6 — 048 剩下的四十倍（與 relink 無關，可平行）

048 自己已經寫好下一個可控變數：**在 WASM 上把 `postMouseEvent` 送出的時刻與 worker
收到游標回呼的時刻各打一個時間戳，看那 22 ms 落在 worker 邊界的哪一側。**

第一刀**全部在 JS 裡**（頁面 → worker → 進 wasm 的呼叫前後 → 回呼抵達），
出貨 artifact 就能跑；只有在四個時間戳仍分不開時，才需要引擎側的時間戳，
而那要另一顆診斷 profile。

**驗收**：22 ms 落在哪一側要有數字。**兩邊都不得在量到之前被寫成結論**——
040 的前例（一個 Emscripten build 永遠不會設的條件）就是這樣被誤判過一次的。

---

## 不是自主項的三件（**要你決定**）

1. **relink 本身**。門檻（D2～D5 寫好並跑過）已達成，但佇列還有三項未完成，
   而 T1 可能把它變成兩項。
2. **一個 operator 時段**：D5 的四格 ＋ E1-C 的收復。**設置完全一樣**
   （Fcitx5 新酷音、真剪貼簿、可信指標事件），SPEC E1-C §11.8 指名的解除條件就是它。
3. **需要 sudo 的步驟**（若 T6 第二刀真的要重編診斷 profile 的相依）——指令給你跑。

## 建議的執行順序

**T1 → T2 →（T3、T4 可與前兩項平行）→ T5 → T6**

T1 排最前面只有一個理由：**它可能讓後面少做一件事**。
