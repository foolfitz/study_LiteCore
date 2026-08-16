# 自主執行佇列 2026-08-16

接在 [`HANDOFF-2026-08-16-e2c-d3-done-048-fixed.md`](HANDOFF-2026-08-16-e2c-d3-done-048-fixed.md)
後面。**這份是排序與自主邊界，不是規格**——每一項的內容仍以
`SPEC-E2-C`、`PLAN-E2-C-relink-v3.md` 與對應的 finding 為準。

每一項都標了三件事：**我能自己跑完到哪裡**、**在哪裡必須停下來等使用者**、
以及**跑之前就寫得出來的失敗長什麼樣**。沒有第三項的任務不排進來。

## 一眼看完

| # | 任務 | 自主程度 | 擋在誰前面 | 狀態 |
|---|---|---|---|---|
| T1 | finding 048 的引擎側機制（原生量測） | **全自主** | 決定 048 是不是上游的事 | **✅ 做完（2026-08-16）** |
| T2 | D3 結構輪：七份語料 × 兩瀏覽器 | **全自主** | relink（佇列完整性 #8） | **✅ 做完（2026-08-16）** |
| T3 | D4：生命週期＋回歸 | **全自主** | relink | **✅ 做完＝`PARTIAL`（2026-08-16）** |
| T4 | relink 佇列補完（**寫，不連結**） | 全自主到「連結」為止 | relink | 稽核＋4a／4e／4d 已做；**4b 量完但判準仍不能定案**；佇列新增兩項 |
| T5 | D5 harness 的機器那一半 | 寫得完，**人工四格要 operator** | relink、E2-C 第二輪判定 | **✅ 機器半邊做完（2026-08-16）**；四格 `NOT_ESTABLISHED` |
| T6 | E1-C 收復：做，還是明確延後 | 判斷題 | `E1_GO_ODT_EDITOR` 的引用 | **✅ 已裁決＝延後（SPEC E1-C §11.8）** |

建議順序：**T1 → T2 → T3 → T4**，T5 在 T3 之後隨時可插。

**2026-08-16 收尾：六項的自主部分全部做完**，接續狀態見
[`HANDOFF-2026-08-16b-d3-d4-d5-done.md`](HANDOFF-2026-08-16b-d3-d4-d5-done.md)。
剩下的都不是自主項：relink 本身、operator 時段（D5 四格 ＋ E1-C 收復，同一個時段）、
以及兩個新的量測（048 剩下的四十倍、native／WASM 對空段落讀回的不一致）。

---

## 本輪已完成的三件（2026-08-16）

**T1 做完了**：原生點擊 → 游標矩形 **0.6 ms**（三輪、N2 各 5／5），瀏覽器是
22–28 ms，**四十倍**。048 並列的兩個假說**都出局**：游標回呼與同一次點擊的其他
回呼同時到（P-N2 三輪皆成立），而 core 承認一次點擊只要 0.6 ms。
**但這只排除了 core 的點擊處理，沒有指認肇因**——040 的前例是原生乾淨、WASM 壞、
仍然是上游。剩下的四十倍還沒被分成「我們的 transport」與「Emscripten 主迴圈整合」。
證據 `findings/evidence/048/native/`，自我測試 9／9。順帶量到兩件：產品那條
400 ms 安靜規則現在有依據（同點點擊 15 次重複零回呼），以及 `.uno:GoDown` 在
`list-contexts.odt` 上一個游標矩形都不發（`styled-list.odt` 上發 23 個）。

**T6 已裁決＝延後**（外部裁決，SPEC E1-C §11.8）。解除條件具名：`e1-editor-v1`
的 relink 決定之後的第一個 operator 時段（可與 D5 併一個時段），另設「有人要引用
殼層那一半就即刻收復」的引信。**我原本寫的理由 1 有事實錯誤並已更正**：045 是
**引擎**缺陷不是殼層缺陷，修法在 relink 佇列 P1-1、一個殼層位元組都不動；誠實的
計數是 047 與 048（同一個家族、兩天內同一個函數修兩次），加上 D5 會去量的拖曳選取。
承重理由其實是我沒放進 T6 的那一條：**`e1-editor-v1` 自己的 relink 決定已經排定**，
若它是 relink，現在收復的兩輪人工百分之百作廢。

**T4c 佇列稽核做完了**（第二方 codex ＋ 我自行覆核關鍵項），三項與佇列文件不符，
已就地更正進 `PLAN-E2-C-relink-v3.md`：3c 的**引擎那半已經在樹裡**（只剩 worker
投影）、**`routeFormatBarrier()` 的 `selectionObserved` 沒修**（審查說「一併修」，
實際只修了新閘門——這一項我自己讀過 `src/probe_engine.cpp:3300` 確認）、以及
`inlineFormatEnabledIsHonoured` 是樹裡有而文件沒有的 manifest 改動。

---

## T1 — finding 048 的引擎側機制：原生量測

**狀態**：[048](../findings/048-place-caret-confirms-before-the-click-takes-effect.md)
的「還缺什麼」剩下兩項未打勾，這是其中之一。產品已經不受害（修法已進），
但「為什麼要 22–28 ms」沒有答案，而**那個答案決定它是不是上游的事**。

**為什麼排第一**：它是佇列裡最便宜的一項——一個 `g++` 探針掛在既有的
`build-native-26-8/instdir` 上，**不動任何 artifact、不動殼層、不需要瀏覽器**，
所以它既不會擴大 T6 的成本，也不會與其他任何一項搶狀態。而且它是唯一一項
「答案可能通往上游」的工作。

**要分開的兩個假說**（048 已經寫下，未量）：

| 假說 | 產品對策 | 可否證的訊號 |
|---|---|---|
| A：mouse event 排在主迴圈後面 | 等引擎 | 回呼與**狀態讀回**同時變新；兩者都晚 |
| B：`LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR` 比游標本身晚到 | 等回呼 | 狀態讀回已經是新位置，回呼還沒來 |

**做法**：`tools/f048_native_click_latency.cpp` ＋ `tools/run_f048_native.sh` ＋
`tools/analyze_f048_native.py`，形式沿用 `f045`／`f049` 那一套（預測先寫進
`findings/evidence/048/native/PREDICTION.md`，判定離線）。每一臂記
`t(postMouseEvent)` → `t(第一個游標回呼)` 與 `t(postMouseEvent)` →
`t(狀態讀回顯示新段落)`，兩個時間戳分開記，**不要只記一個總和**。

**驗收（先寫）**：

- 三次執行的中位數彼此在同一個數量級，否則這一輪不下結論；
- 原生也落在 20 ms 以上 → **上游候選**，開 finding 的上游段並補重現包；
- 原生在 2 ms 以下 → 是**我們這一側**（worker 排程／transport），
  留在自己的樹裡，並回頭記進 048；
- 兩者之間（2–20 ms）→ 不硬選，記成「機制未分離」並寫下下一個要量的變數。

**自主邊界**：全自主。只編一個獨立的 `-o` 執行檔，不進任何 profile 的 build 目錄。

### 結果（2026-08-16）：**兩個假說都出局，但答案只完成一半**

上面那張驗收表**照原樣計分**，包括第三行——它需要更正，而更正是在**任何 arm 資料
存在之前**做的（記在 `PREDICTION.md` 的 A2，由外部裁決提出）：
「原生 ≤ 2 ms → 是我們這一側」**寫得太滿**。040 的前例是原生乾淨、WASM 壞、
**仍然是上游**（Emscripten build 的排程整合）。所以那一支只能結論
「**不在 core 的點擊處理裡**」，不得指認肇因。

| | 原生（三輪中位數） | 瀏覽器 |
|---|---|---|
| 點擊 → 游標矩形 | **0.6 ms** | 22–28 ms（Chrome）、23–33 ms（Firefox） |

五條預測：P-N1／P-N2／P-N3 三輪皆成立，P-N5 兩輪成立一輪差 0.1 ms 記為不成立
（量級是雜訊，但**預測照寫下來的樣子計分**），P-N4 **NOT_MEASURED**——
`.uno:GoDown` 在這份語料上一個游標回呼都不發。

**判定器修了兩處，都在看到第一輪資料之後，都已記在 A3**：中線對中線的比較
（原本拿矩形上緣比行中目標，每個正確落點都剛好卡在容差邊界），以及
**把 `NOT_MEASURED` 從 `FAILED` 裡拆出來**——「沒量到」不是「預測被推翻」。
兩處都不會把 FAILED 變成 HELD。自我測試 9／9。

**接下來的那一半**（已寫進 048 的「還缺什麼」）：0.6 ms 與 22 ms 之間的四十倍
還沒被分成「我們的 transport／worker 排程」與「Emscripten 主迴圈整合」。
下一個可控變數：在 WASM 上替 `postMouseEvent` 送出與 worker 收到游標回呼各打
一個時間戳，看那 22 ms 落在 worker 邊界的哪一側。

---

## T2 — D3 結構輪：七份語料 × 兩瀏覽器

### 結果（2026-08-16）：**八格兩瀏覽器全過，一條預測不成立，掉出一個語料缺陷**

詳見 SPEC E2-C 9.5.10 與
`findings/evidence/sdk-e2/e2-c-validation/d3-corpus/README.md`。三件值得記在這裡：

1. **矩陣把 `list-contexts`／`list-split` 寫成「carrying」L 格**，所以那兩份不必
   重跑瀏覽器——結構判準離線施加在 L 輪已存好的文件上。省下的是兩份語料的重跑，
   買到的是「同一份文件不會有兩個互相矛盾的紀錄」。
2. **`l4-stress-100` 的 100 個圖存出來變零，而那不是產品的錯**：兩個 LibreOffice
   build 在完全沒有編輯的情況下都會丟掉它們。**下結論之前先做對照**是這一格唯一
   做對的事——不做，它就會被寫成 D3 停止條款觸發。
3. **第一輪三格被我自己的容差常數擋掉**，兩瀏覽器逐格相同才讓歸因成立。
   常數是清單語料的行距算出來的，對標題行不成立；修法是改用量到的行框重疊。


**狀態**：清單那八格跑完了，**結構那七格一格都沒跑**。矩陣 v1 的
`d3-l0-t1`／`l0-t2`／`l0-t3`／`l1-review`／`l4-stress-100`／`list-contexts`／
`list-split` 七格的 oracle **已經凍結**（「open、在指名錨點編輯、save；
必要錨點在、ZIP CRC 與 XML 有效、禁止內容不出現、桌面重開與 PDF 匯出成功」），
所以這一步**不是重訂判準，是把凍結的判準落成可執行的格**。

**為什麼排在 T1 之後、T3 之前**：codex 對抗性審查的第 8 項——「D2～D5 沒寫，
是連結前的佇列完整性問題」——目前只剩 D3 結構輪、D4、D5 三塊，而 D3 是三塊裡
唯一會**碰內容**的（D4 量的是生命週期，D5 是人工）。內容格最可能再長出佇列項。

**產出**：

- `web/e2-c-d3-corpus.html`／`-app.js`（**不是**改 `e2-c-d3-app.js`——那份是清單
  八格實際跑過的頁面，它的位元組是 `run-3`／`run-4-fixed-shell` 的身分的一部分）；
- runner 相位（沿用 `tools/run_e2_c_d0.py` 已經參數化的 `--page`／`--namespace`）；
- `tools/analyze_e2_c_d3_corpus.py`，離線判定，**帶突變自我測試**
  （每個突變必須**改變**判定，不是必須讓它變紅——D1 分析器已經學過這一課）；
- Makefile：七份語料要進 `dist/`（`dist/r7-compat-fixtures/` 的目標已存在於
  `r7-compatibility-assets`，`e2-c-assets` 需要掛上它與 `list-split`）；
- 證據 `findings/evidence/sdk-e2/e2-c-validation/d3-corpus/`，自帶 README 說明
  哪一輪是哪一輪。

**設計上先寫下來、再寫 harness 的三件**：

1. **每份語料的錨點與動作**。錨點取 `test-docs/r7-compat/manifest.json` 的
   `anchors`（`l0-t3` 有首／末兩個、`l4-stress-100` 有 001／050／100 三個，
   規格說「首／中／末」與「固定頁面文字錨點」）；動作用**一個**段落格式動作，
   一份一格，**不混合序列**（D1 已經學過：混合序列存一次檔，結果歸屬不到單一動作）。
2. **游標一律用產品手勢**（click ＋ 048 的確認輪詢，`web/e2-c-caret.js`），
   不用零寬 `selectRange`。9.5.6 量過手勢會改變答案。
3. **`l1-review` 的額外判準**：comments 與 tracked changes 必須存活——
   矩陣的 oracle 明寫了，判定器要真的去數，不是只驗錨點。

**兩個要誠實記進證據 README 的事**：

- r7-compat manifest 裡四份的 `mutationPolicy` 是 `read-only`。那是 **R7 相位對
  磁碟位元組的政策**，不是禁止在瀏覽器內的複本上編輯——E1-C 的 C3 已經這樣跑過
  （`findings/evidence/sdk-e1/editor-validation-v2/corpus/*/output.odt`）。
  **不寫下來的話，後人讀到的是「政策被違反了」。**〔已觀察〕
- `l0-t3`（22 頁）與 `l4-stress-100`（100 頁）會慢。先單份量一次再定 timeout，
  **不得為了省時間砍格或降 repeat**（規格第 5 節：正式結果產生後不得放寬）。

**驗收（先寫）**：兩瀏覽器逐份相同；七份全過，或任一份出現無聲內容／結構損失
就**停**並開編號 finding（規格第 7 節的停止點）；分析器自我測試每個突變都改變判定。

**自主邊界**：全自主。桌面重開與 PDF 走 `r7_support.desktop_pdf_roundtrip`
（`/usr/bin/soffice` 在）。

---

## T3 — D4：生命週期與回歸

### 結果（2026-08-16）：**`PARTIAL`，卡在一個產品量不到的數字**

`d4-sessions`／`d4-residuals` 兩格兩瀏覽器全過（10／10、generation 各 1、
worker 與 handle 每次取樣都是 0）；`d4-regression` 11 個目標全綠、artifact 未變。
**`d4-memory` 是 PARTIAL**：產品沒有任何路徑報得出 WASM heap，
`measureUserAgentSpecificMemory` 的 breakdown 沒有 WASM 歸屬，Firefox 連 API 都沒有。
**這是 D4 掉出來的 relink 佇列項**（引擎在 typed state 裡報 heap）。

另記：Firefox 的 PSS 斜率 7.52／8 過，但絕對成長 +35.1 MB，**我自己登記的
P-D4-3 第二子句因此不成立**——格子照矩陣過、預測照原樣記為不成立。


**狀態**：沒開始。矩陣 v1 的四格（`d4-sessions`／`d4-residuals`／`d4-memory`／
`d4-regression`）門檻**已凍結**且是數值的，不是「無連續成長」那種不可否證的說法。

**產出**：

- 10 輪 × 2 瀏覽器的相位（每輪一個獨立的 edit → save → reopen session，
  每頁不超過三個 generation，runner 自行 reload）；
- `tools/analyze_e2_c_d4.py`：worker／handle 歸零、WASM heap 十輪線性回歸斜率
  ≤ 2 MB／session 且第 10 輪 ≤ 首輪＋20 MB、PSS／RSS 斜率 ≤ 8 MB／session；
  取樣在 `close()` 之後等到沒有 in-flight 請求，**同一輪固定 3 秒後再取一次，
  取較小值**；
- **Firefox 拿不到 PSS 時記 `notValidated` 並判 PARTIAL**，不得因為量不到就當通過
  （矩陣的 `onUnavailable` 欄位就是為了讓這件事是規則而不是一句話）；
- 回歸：`test-r6-release`、`test-r7-b/c/d-static`、`test-r8-d-static`、
  `test-e1-a-static`、`test-e1-b-static`、`test-e2-a-static`、`test-e2-b-static`
  ＋ workspace preflight 前後各一次。**不得跑 `test-e1-c-static`**，改跑
  `check_e1_c_bundle_intact.py` 與 `test-e1-c-frozen-guard`（矩陣 v1 的
  `d4-regression` 把這件事凍結成判準，所以照做）。

**但排除它的理由要改寫，不能照抄**〔已觀察，2026-08-16〕。原文寫「它會重建凍結的
`e1-editor-v1`」——**自 SPEC E1-C v9（08-14）起不成立**：那個目標刻意無前置，
配方是純檢查。真正的現況是另一回事，而且更值得寫：**`test-e1-c-static` 今天是
紅的**——`tests/test_e1_c.py` 的兩條（目標就停在這裡）加上最後一行
`regenerate_shell_bundle.py`，三處都不認 divergence 檔。一個在申報期恆紅的靜態目標，正是 intact 守衛註解裡警告的
「會被關掉的守衛」形狀。處方二選一（記在 SPEC E1-C §11.8）：教 check 模式讀
divergence 檔，或維持排除但把理由寫對。

**整份回歸清單已經先掃過一遍**〔已觀察，2026-08-16〕：其餘十項**全綠**
（`test-r6-release`、`test-r7-b/c/d-static`、`test-r8-d-static`、
`test-e1-a-static`、`test-e1-b-static`、`test-e2-a-static`、`test-e2-b-static`、
`test-e1-c-frozen-guard`、`check_e1_c_bundle_intact.py`），掃描前後每一顆
`probe.wasm` 逐顆雜湊未變。**這件事值得先做而不是等 D4 才發現**——
`test-e2-a-static` 從 08-15 起就紅著，沒有人跑過它。

**那個交互作用也量掉了**〔已觀察〕：`check_e1_c_bundle_intact.py` 在殼層綁定
已斷但已申報的狀態下 **exit 0**、`intact: false`、`divergedAsDeclared` 三筆、
`problems: []`。D4 直接引用這個結果，不再是待驗證項。

**驗收（先寫）**：四格各自的門檻是數字，過不過由 `analyze_e2_c_d4.py` 判；
任何一格紅就是 STOP（`d4-memory` 在量不到時是 PARTIAL），**不在跑完之後調門檻**。

**自主邊界**：全自主。

---

## T4 — relink 佇列補完：**寫，但不連結**

### 4b 的結果（2026-08-16）：**量完了，判準仍不能定案，而問題換了一個**

原生量到：空段落上，barrier 的選取對會把游標**往上帶一段**、讀回描述**上一段**
（blockCount 1），兩個手勢完全相同，動作前後也一樣——**而動作是成功的**
（存檔證明空段落確實變成 `text:list-item`）。所以不是「bullet 沒生效」，
是「檢查看了別的地方」。

出貨 build 對同一個手勢回報「零個 block」，**與 core 不一致**。在那個不一致被
解釋清楚之前，`empty-readback` 這個名字會取在一個機制未明的症狀上，所以 3b
**不撤回也還不能寫**。同時掉出一個更根本的佇列項：**barrier 驗的是動作沒碰到的
那一段**，與 048 同一個家族。


**連結是使用者的決定，而且不可逆。** 這一項做到「所有東西都寫好、只編 object
驗證得過、佇列稽核表是綠的」為止，然後停。

| 子項 | 內容 | 自主 |
|---|---|---|
| 4a | **3c**：`itemCount` 補進產品投影。**稽核後縮小**：引擎那半已在樹裡（`probe_engine.cpp:1241`），只剩 `sdk/sdk-worker.js:172–190` | 全自主 |
| 4b | **3b**：046 的 `empty-readback` 判準——**先量再寫** | 全自主 |
| 4c | 佇列完整性稽核 | **✅ 做完（codex ＋ 自行覆核）** |
| **4e** | **稽核新掉出來的兩項**：`routeFormatBarrier()` 的 `selectionObserved` fail-closed（審查說「一併修」，實際沒修）；`inlineFormatEnabledIsHonoured` 進佇列與規格（它會改 v3 的 manifest，而 manifest 是第五個綁定身分） | 全自主 |
| 4d | `e2/validation-matrix-v2.json` 草稿，**外加一個進場斷言**：矩陣 baseline 五個雜湊齊全且與現場一致，由 D0 的 runner／判定器檢查——否則「連結之後、D0 之前才凍結」這個窗口沒有守衛 | 全自主 |
| — | **跑 `make` 去連結** | **使用者** |

**4b 的順序不能反過來**。3b 的判準壓在「零個 block 是什麼都沒讀到，還是只讀到
清單項」這個區別上，而產品投影今天看不到 `itemCount`。可以**不等 relink** 就把
判準變成量出來的：用原生探針去問 core，同一個空段落的 readback 到底回什麼
（`blockCount`／`itemCount`／html 逐欄記下來），判準壓在量到的值上，**然後**才寫進
`probe_engine.cpp`。這樣 3b 進佇列時是量出來的，不是猜的。

**4a 的動手規矩（P0 那條教訓）**：只編 object 的檢查要編到 **scratch 目錄**，
不得編進任何 profile 的 build 目錄——上一輪把 v2 的 object 換成新原始碼編出來的，
artifact 沒事，但那個 build 目錄現在是混的。

**4d 要進矩陣 v2 的四件**（規格 11.4）＋**這一輪新掉出來的一件**：

- baseline 換成 v3 的**五個**雜湊（含 manifest 自己的 sha256）；
- 游標一律照產品的方式形成；
- 一格釘住 9.5.6 量到的 `selectRange` 差別；
- 帶文件判準的範圍格（單段與**真的跨段**）；
- **新增：相鄰同型清單的合併規則**。D3 的 L2 與 L8 都併入了相鄰的同型清單、
  L5 因為轉成不同型所以分裂。這是一條連貫的規則，但**沒有人在跑之前寫下來**，
  所以第一輪照原樣記成「預測不成立」。第二輪要把它寫成預期行為，
  **就得先寫進矩陣再跑**，不得事後追認。

**驗收（先寫）**：4c 的稽核表每一項都指得出檔案與行號（或指得出「不在樹裡」）
——**已達成**；4a／4e 的 object 編得過（編到 scratch 目錄）且
`tests/editor_abi_header_test.cpp` 斷言 ABI = 3；4b 的判準有一份原生證據撐著。

---

## T5 — D5 harness 的機器那一半

**狀態**：沒開始。四格（`d5-pointer-drag-single`／`-cross`／`d5-ime-commit`／
`d5-clipboard`）的 oracle 已凍結，`onFailure` 都是 PARTIAL。

**能自主的**：頁面、runner、以及 save 之後由 machine validator 檢查錨點數與
桌面重開的那一段。

**不能自主的**：真實指標拖曳（自動化拿不到 `isTrusted`）、Fcitx5 Chewing、
真 Ctrl+C／Ctrl+V。**這四格要 operator，而規格明寫「人工無法取得時可判部分 GO，
不為湊 GO 反覆要求 operator 操作」。**

**排序**：規格第 7 節說 D5 只在 D0～D4 全過之後開始，所以 harness 可以先寫，
**執行要等 T2、T3 全綠**。

---

## T6 — E1-C 收復：**已裁決＝延後**（2026-08-16）

裁決與完整理由寫在 **SPEC E1-C §11.8**（原地修訂＋修訂紀錄）。摘要：

- **延後**，解除條件具名：`e1-editor-v1` 的 relink 決定之後的第一個 operator
  時段（可與 E2-C D5 的四格人工併一個時段），另設**引信**——任何具名事件要引用
  `E1_GO_ODT_EDITOR` 的殼層那一半，即刻收復。
- 承重理由是**已排定的 `e1-editor-v1` relink 決定點**（PLAN P3），不是「殼層還在
  動」：若那個決定是 relink，四個雜湊全換，現在收復的兩輪人工百分之百作廢。
- 歷史查證過：08-06 那次立即收復（含兩輪人工）**24 小時內被下兩次重建作廢**；
  人工輪成本**每事件固定、不隨改動量成長**，所以「愈晚愈貴」方向是反的。
- 我原本寫的理由 1 有事實錯誤：**045 是引擎缺陷不是殼層缺陷**，已更正。

## 發包 codex 的三件（都有客觀判準）

| # | 內容 | 為什麼是 codex |
|---|---|---|
| C1 | **T4c 佇列完整性稽核**：P1 的九項逐項查在不在原始碼樹裡，輸出檔案與行號 | 對錯有客觀判準，而且**上一輪正是這裡出錯**（3b 被記成「已寫」，`grep` 零筆）。用工具查、由第二方查 |
| C2 | **T2 的 harness 與判準對抗性審查**，在跑之前 | 前例：relink 計畫的 codex 審查 11 項、6 個 blocker，全部接受。D3 第一輪的空轉（在沒有清單的段落上驗清單動作）也是對抗性審查抓到的 |
| C3 | **T3 的門檻數學與 `notValidated` 路徑覆核** | 斜率、絕對值、取樣時機都是可驗算的；`notValidated` 那條路徑最容易寫成「量不到就當過」 |

---

## 需要使用者的三件事（其餘我自己跑）

1. **T6 的裁示**：E1-C 現在收復，還是明確延後？（建議先問 fable）
2. **T4 的連結**：佇列補完之後，`make` 連結 v3 是使用者的決定。
3. **T5 的人工輪**：要 operator 的時段，且只在 D0～D4 全綠之後才該開口。

## 不做的事

- **不連結、不重編任何既有 profile。** T1 與 4b 的原生探針編到自己的輸出目錄。
- **不改凍結的證據與 manifest。** 第一輪的證據原封保留；第二輪寫進自己的命名空間。
- **不回頭改 `ad82aa1`／`0a1a531` 的順序。** 那個瑕疵已經寫在交接文件裡，
  改寫歷史買不到任何量得到的東西。
- **不推進上游送出**（2026-08-15 的決定仍然有效）。T1 就算指向上游，
  也是先把 finding 寫完整，不送。
