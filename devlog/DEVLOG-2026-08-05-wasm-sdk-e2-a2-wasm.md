# DEVLOG 2026-08-05（下半）— E2-A A2-wasm：payload 到了，但它不看 caret

> 對象：一起看 E2 的同事。接續 [DEVLOG-2026-08-05-wasm-sdk-e2](DEVLOG-2026-08-05-wasm-sdk-e2.md)。  
> 相關：[SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md)（已改 v5）、
> [finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)、
> [finding 020](../findings/020-lok-list-command-result-contradicts-document.md)

## 這一輪做了什麼

跑完 E2-A 的 A2-wasm：建 `e2-format-discovery` 隔離 profile、建瀏覽器 harness，在 Chrome 150 與
Firefox 153 上確認 `.uno:DefaultBullet`、`.uno:DefaultNumbering`、`.uno:StyleApply` 三個 state
payload 到底會不會抵達。這是把上一輪「barrier 在瀏覽器中仍是推論」升格為已觀察的最小實驗。

**結論分兩半，而且兩半的答案不一樣：**

- **後置條件成立。** 五個格式命令派送後，state 與存檔 ODT 逐項相符（5/5，兩瀏覽器各一輪）。
  barrier 的歸屬機制有效，`crosstalkCount` 與 `earlyStateCount` 十次派送全為 0。
- **前置條件不成立。** state **不隨 caret 移動更新**。10 次定位讀取只有 2 次是新鮮的，其餘
  回報的是上一段留在快取裡的值。caret 實際位在 `<text:list>` 內時，引擎從未回報過「在清單內」。

第二點推翻了 A2-native 的觀察在 WASM 的適用性，記為
[finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)。
**A3 因此暫不啟動。**

## 順帶把 finding 020 從原生觀察變成跨平台事實

barrier 計數器接通後，WASM 完整重現了原生的說謊行為，兩瀏覽器一致：

| 派送 | command result | 文件實際結果 |
|---|---|---|
| `.uno:DefaultBullet` | `success:true`、**`wasModified:false`** | 有效，段落進清單 |
| `.uno:RemoveBullets` | **`success:false`**、`wasModified:true` | 有效，離開清單 |

這對 finding 020 送上游有直接價值：它不是 Emscripten 特有行為。

「一個樣式三種字串」也完整重現：送出 `Text body`、state 回 `Body Text`、ODT 存 `Text_20_body`。
上一輪靠原生量出來、寫死進 barrier 的常數，在瀏覽器裡逐字對上。

## 為什麼「不隨 caret 更新」是嚴重的

barrier 用同一份 typed state 做兩件事：派送前判前置狀態，派送後判後置條件。後者沒問題，前者
會讀到**別的段落**的值。

具體的壞路徑：`alreadyAtTarget` 拿上一段的狀態判定「已經是目標狀態」，回一個
`documented-state-noop`、`changed:false`，而該段落其實從未進入該狀態，且什麼都沒發生。
這是靜默 no-op，與 SPEC E2-000 第 10 節「no-op 與遺失不可區分」的停止條件同類。

本輪五次派送都落在同一段落並依序進行，所以沒有踩到。A3 的三態循環要跨段落，會踩到。

當時的下一步是那個能區分「WASM 特定」與「兩次量的不是同一件事」的實驗：**同 commit 原生、
同一份 fixture、同一組四個定位點**重跑純 caret 移動。A2-native 說過「純 caret 移動就會更新」，
但它用的是另一組移動序列，兩者不可直接相比 —— 這正是上一輪學到的教訓的反向應用。
（跑完之後還需要再一層，見下面兩節。）

## 本輪我自己犯的三個錯

三個都是量測工具的錯，而且前兩個都會把壞結果偽裝成別的東西。

**一、第一次 Chrome run 是假否定。** 我的 harness 只用 `setTextSelection(RESET)` 定位，而且
只把 `source === "format-state"` 的事件記進 metrics。結果拿到「三個狀態全是 null、零事件」，
看起來像「WASM 完全收不到格式狀態」。

但那份證據**無法區分**「狀態沒抵達」與「caret 根本沒移動」—— 因為我把能證明 caret 有沒有移動的
事件全丟掉了。連 `bold`／`italic` 都是 null 這件事救了我：那兩個是 E1-C 驗證過會運作的狀態，
它們也 null，指向工具而不是 core。

補上三件事後重跑才有意義：public `click()` 作為第二種定位方式、記錄**全部** editor-state 事件
來源、以及 set-bold 正向對照（一個已知會動的東西，用來證明管線本身活著）。

**二、`trackedCaret` 判準太鬆，把壞結果判成 `pass:true`。** 第一版寫的是「值在各位置之間有差異
就算有追隨 caret」。但 null→已知的轉變就滿足它。於是一份「狀態從不追隨 caret」的資料，
第一次判定是**通過**。

這跟上一輪 run script 標題印錯是同一類：**摘要判準本身沒有被驗證**。改成以 fixture 結構為真值的
逐位置檢查 —— 清單內的段落要讀成在清單內、清單外要讀成在清單外、heading 與 body 的樣式要不同 ——
而且每個讀數都要有該位置的新鮮事件支持，否則標記為 stale 不採用。改完之後，同一份資料判定為
不通過。

**三、我又猜了一個常數。** `heading-on` 的 postcondition 我寫成「輸出 ODT 應該出現 `<text:h>`」。
實測是 `.uno:StyleApply` 對既有 `<text:p>` 套用 `Heading_20_1` 段落樣式，元素型別不變。
期望值錯，不是產品錯。

第一次跑出 4/5 的時候，那個「未達成」看起來像產品問題。要不是順手去看了存檔的實際結構，
它會被寫成一張假的 finding。**先量，再寫死** —— 上一輪的結論，這一輪又踩了一次，換了個位置。

## 保護凍結 artifact：這次是刻意的，不是僥倖

上一輪的教訓是 `make test-*-static` 不保證不會建置。這次先 `make -n` 看相依再動手：

- `e2-format-discovery-profile` 的建置計畫只寫 `build/e2/` 與 `dist/profiles/e2-format-discovery`，
  不碰任何凍結 artifact。建完驗 hash，三個全未變。
- `test-e1-c-static` 確認**會**重建 `e1-editor-v1`。我沒有跳過它，而是先機械證明我的
  `probe_engine.cpp` 改動（一段註解）在 E1-B 的前處理輸出裡完全不存在，然後刻意跑，
  跑完驗 hash：`45c31f32…`／`94b38437…`／`9696c9ce…` 三個逐位元回到 E1-C 記錄值。

第二點順帶再次證明這條建置鏈是決定性的。知情地跑並驗證，跟不知情地跑，是兩件事。

### 共用 worker 沒有被改

E2 需要三處 Worker 差異（discovery scope 閘門、錯誤訊息、把 barrier 計數器轉發出來）。直接改
`sdk/sdk-worker.js` 會讓每個 profile 複製到的 bytes 都變，`e1-editor-v1` 與 `e1-editor-discovery`
就再也重建不出 E1-C 記錄的 hash。

所以改的是**本 profile 的副本**：由 `tools/build_e2_discovery_profile.py` 做三次精確字串替換，
每一處都要求剛好命中一次，否則建置直接失敗。這是 `OXSDK_E2_FORMAT_BARRIER` 在 JS 側的對應做法。
`sdk/sdk-worker.js` 的 hash 仍是 `9696c9ce…`。

替換必須失敗即停這點是刻意的：靜默 no-op 會產生一個 Worker 會拒絕 E2 待測操作的 profile，
而那個失敗看起來會像「能力不存在」，不像建置錯誤。`tests/test_e2_profile.py` 有一則測試
專門驗證這個失敗路徑。

## 接著跑完了 finding 021 的歸因：先指向 WASM，再指回我們自己

原生 harness 的原始碼一打開就看到問題：A2-native 是用 `.uno:GoToStartOfDoc`／`.uno:GoDown`
**派送 UNO 命令**移動 caret 的，而 A2-wasm 用的是 `setTextSelection(RESET)` 與滑鼠點擊。
兩次量的確實不是同一件事 —— 這正是 finding 021「待驗證」列的第一項。

（先排除了一個更簡單的解釋：WASM 的 `search()` 內部也是 `postUnoCommand(".uno:ExecuteSearch")`，
所以「有沒有派送 UNO」不是差異點。差異在移動命令**本身是不是游標命令**。）

於是寫了新的原生探針，同一份 fixture、同一組定位點，四種移動方法各跑一遍。座標不用猜：
phase 0 先用游標命令走一遍文件，把每一站的 visible-cursor 矩形量下來，後面的 phase 重用。

| 移動方法 | 新鮮讀數 | 進出清單兩個轉換都讀對 |
|---|---|---|
| 游標命令（A2-native 原用） | 4/5 | 是 |
| `setTextSelection(RESET)` | 4/4 | 是 |
| 滑鼠點擊 | 4/4 | 是 |
| `ExecuteSearch`＋`setTextSelection`（WASM 逐字序列） | 4/4 | 是 |

**原生四種全部正常**，包括 WASM 失敗的那兩種。移動方法假設否證。（唯一非新鮮的一步是清單項
之間移動 —— 值沒變，core 正確地不廣播。）

還剩一個歸因缺口：「core 沒送」與「我們收到但沒解析」在現有證據裡分不開。於是在 E2 profile 加了
兩個計數器 —— 抵達的 STATE_CHANGED 總數，以及其中無法辨識的數量。**只計數，不轉發 payload**，
所以不擴大 callback surface。Chrome 與 Firefox 逐數字相同：

| 位置 | 定位方式 | 抵達 | 無法辨識 |
|---|---|---|---|
| `list-item` | search | **0** | 0 |
| `after-list` | search | **0** | 0 |
| `list-item` | click | 2 | **2** |
| `body-paragraph` | click | 158 | 154 |

失敗位置「無法辨識 ＝ 抵達總數」，代表 watched command 的 payload 一筆都沒到。**排除我方解析失敗。**

已排除 core 版本（同 commit）、移動方法、fixture、我方解析 —— 剩下的唯一變數是 WASM build。
當下判為 WASM 特定、上游候選。**但再分一層之後這個分類就撤回了。**

## 再分一層：不是上游，是我們自己沒推排程

`unit_lok_process_events_to_idle()` 是 `Scheduler::ProcessEventsToIdle()` 的 LOK 掛鉤，Finding 016
當時的 scheduler 探針已經接好了。於是建一個隔離 profile `e2-scheduler-attribution`
（E2 組態＋`OXSDK_FINDING_016_SCHEDULER_PROBE`），每次定位後多做一步推排程，再讀一次狀態。

兩瀏覽器逐項相同：

| 位置 | drain 前 | drain 後 | 原生 |
|---|---|---|---|
| `heading` | stale | `inList=true` | `inList=true` |
| `body-paragraph` | stale | `inList=false` | `inList=false` |
| `list-item` | stale | **`inList=true`** | `inList=true` |
| `after-list` | stale | `inList=false` | `inList=false` |

`search` 定位的四個位置 drain 前**全部**不新鮮、drain 後**全部**新鮮，值與原生完全一致。四次 drain
分別釋放 25、157、6、5 筆 STATE_CHANGED，其中 2、4、2、1 筆是 watched payload —— 先前「零抵達」的
位置，一推排程就有了。

**所以 core 算得完全正確，只是負責廣播的 idle job 在我們的建置裡從來沒跑。** LOK 的 status update
是 idle job；原生由 `soffice_main` 的 VCL 主迴圈推動，而我們的探針是核外連結、自帶命令迴圈，兩個
操作之間沒有任何東西推進 scheduler。派送命令之所以有狀態，是因為那條路徑在命令執行中**同步**廣播，
不需要 idle job。

finding 021 因此改判為**我方問題，不是上游**。上游候選的分類撤回了。

這跟 Finding 016 的 scheduler 實驗不矛盾：那一輪問的是 delete 的 completion callback，drain 沒有幫助，
於是否證了主迴圈缺口**對那個問題**的解釋。本輪問的是 idle 驅動的 status update，drain 直接解決。
同一個機制、不同的相依 —— 一次否證只否證它測到的那條路。

順帶記一個量測細節：Finding 016 的 drain 自身回報 `delta.stateChangedCount = 0`，看起來像什麼都沒
釋放。那是舊探針的侷限 —— 它在 drain 呼叫內同步取樣，而 callback 在 drain 返回後才送達。本輪新增的
`stateChangedTotal` 才量得到真實增量。如果只看舊計數器，這個實驗會得到完全相反的結論。

順帶又抓到自己一個猜測：analyzer 第一版斷言 heading 的 `inList` 應為 false，實測原生與 WASM
都回報 true，而原生同時回報 `style='Heading 1'` —— 與 outline numbering 一致。改成只判定 fixture
保證會變的兩個轉換，不對 heading 的清單狀態做斷言。**第三次了**，同一輪裡第三個猜出來的常數。

## 然後把修法做出來並驗證

歸因指向「我們沒推排程」之後，直覺的修法是「呼叫 `Application::Reschedule()`」。**那是個陷阱。**

上游在 `__EMSCRIPTEN__` 下由 `SvpSalInstance` 建構子無條件把 `m_bUseSystemLoop` 設成 true
（`vcl/headless/svpinst.cxx:103`），而在該模式下 `Application::Reschedule()` 直接回 false、
什麼都不做（`svapp.cxx:400-406`），`Application::Yield()` 甚至會 `abort()`。
`Scheduler::ProcessEventsToIdle()` 之所以有效，是因為它直接呼叫 `InnerYield` 繞過那個閘門。

這件事我沒有只靠讀碼下結論，因為猜錯的代價很具體：寫一個永遠 no-op 的修法，然後在錯誤的地方
找為什麼沒效。實測（Chrome，四個位置皆同）：

| 量測 | 值 |
|---|---|
| `IsUseSystemEventLoop()` | `true` |
| `Reschedule(true)` 回傳 | `false` |
| drain 呼叫**內**的 STATE_CHANGED 增量 | 0 |
| drain 返回**後**的增量 | 25／157／6／5 |

最後兩行同樣重要：callback 是在 pump 返回之後才 flush 的，所以「推完就同步讀」也讀不到。

### 第一版實作是錯的

我先寫了 engine 端非同步等待：pump 之後等 watched payload 抵達再繼續。跑出來 `bullet-on` 逾時、
`list-off` 逾時、`body-on` BUSY。

原因是 **core 只在值改變時廣播**。值沒變就永遠等不到那個 payload —— 我在前置條件這一層，
又造了一次「no-op 與遺失不可區分」。而且逾時之後 `pending` 沒有清掉，把後面每個動作都 BUSY 掉了。

### 第二版：engine 只負責拒絕，host 負責刷新

改成沿用 E1-B 的既有慣例（click 之後由 host 做有界 typed-state 輪詢）：

- **engine**：caret 一動就把格式狀態標記為 stale；前置條件是 stale 時回
  `EDITOR_FORMAT_STATE_UNAVAILABLE`、零 mutation。engine 不做任何 sleep。
- **host**：下格式動作前先 pump，等 flush 穩定，再下動作。

pump 到 idle 之後，core 已經重算過，所以「沒有新 payload」代表值沒變、快取正確 —— 歧義消失了。

驗證結果（Chrome 150 與 Firefox 153 一致）：

| 情境 | 五個格式動作 | 存檔 postcondition |
|---|---|---|
| 不做 host refresh | 5/5 `EDITOR_FORMAT_STATE_UNAVAILABLE`，零 mutation | 文件未變 |
| 有 host refresh | 5/5 `verified-format-state`、revision 各 +1 | **5/5 相符** |

兩行都要看：下面那行證明修法有效，上面那行證明拒絕真的會發生 —— 只驗證成功路徑的話，
fail-closed 有沒有接上根本看不出來。

**但這不能進產品。** discovery 用的 pump 是 `unit_lok_process_events_to_idle()`，上游註解明寫是
unit-test 掛鉤。已知不可行的替代是 `Application::Reschedule()`（實測 no-op）。剩下的候選只有
兩個：照上游設計實際跑 `Application::Execute()` 的 emscripten 主迴圈（但它會拋 JS 例外展開堆疊
且不返回，與本 SDK 由 Worker 送命令的架構衝突，屬重構）；或向上游要一個受支援的狀態刷新原語
（`doc_iniUnoCommands()` 只註冊 slot，沒有強制重新廣播的入口）。

## 現在的狀態

**已完成**

- `e2-format-discovery` 隔離 profile（WASM `45f2372b…`）、Makefile 規則、profile builder、
  瀏覽器 harness、runner、11 項靜態測試與 `make test-e2-a-static`（該目標不觸發任何建置）
- A2-wasm 在 Chrome 150 與 Firefox 153 各 2 輪，六次 Chrome attempt 全部保留不覆寫
- finding 021 建檔；finding 020 升格為跨平台；SPEC E2-A 原地改為 v3；凍結矩陣補 `a2WasmResult`
- 回歸：E1-A／B／C 與 R6～R8 靜態全過；三個凍結 artifact hash 未變；core worktree HEAD 與
  六筆 dirty 檔案未變

- finding 021 三步歸因完成：原生四種移動方法對照 → 原始 callback 計數 → scheduler 推進實驗。
  **結論是我方 engine 迴圈未推進 VCL scheduler，非上游。** 新增
  `tools/e2_a_native_caret_tracking.cpp`、`run_e2_a_native_caret.sh`、`analyze_e2_a_native_caret.py`
  與隔離 profile `e2-scheduler-attribution`；證據在 `findings/evidence/021/`

**未完成**

- finding 021 修法已在 discovery profile 驗證（fail-closed ＋ host 刷新，兩瀏覽器 5/5 且存檔證實）
- A3～A7 未執行。**A3 仍不啟動**：產品層的推排程機制未定，discovery 用的是 unit-test 掛鉤。
- E2-A 仍無判定。

## 下一步

1. 決定正規的推排程機制。已排除 `Application::Reschedule()`（實測 no-op）與
   `unit_lok_process_events_to_idle()`（unit-test 掛鉤）。剩兩個候選：跑上游的 emscripten 主迴圈
   （重構），或向上游要一個受支援的狀態刷新原語。並確認在操作邊界推進有沒有再進入或 teardown
   副作用（finding 012 的 document destroy 阻塞屬相鄰風險）。
2. 決定推進時機：每次操作前都推，或只在需要前置狀態時推。前者會改變所有既有 release 的行為，
   R6～E1 全部要回歸；後者範圍小。**在產品機制確定前不得放寬 fail-closed**，也不得因為
   「本輪沒踩到」就把 `documented-state-noop` 當成已驗證能力。
3. 一併重評 finding 018 的 line navigation completion —— 同樣是 idle 驅動的東西，可能是同一個成因。
4. finding 020 送上游前仍需搜重複單，並在完全未修改的上游 build 重現。現在它有原生＋兩個瀏覽器
   的證據，是本專案最接近可送出的一張。

## 方法上值得帶走的一點

這一輪真正救回結果的，是**一個已知會動的對照組**。

set-bold 的狀態回讀是 E1-C 驗證過的能力。把它放進同一份 harness、同一個 profile、同一輪執行，
就得到一個判準：如果連它都不吭聲，那是我的工具壞了；如果它會動而三個 E2 payload 不動，
差異才可以歸因到那三個命令。

沒有這個對照組，第一次那份「全 null」的資料有兩種讀法，而我很可能會挑錯的那種 —— 寫成一張
「WASM 收不到格式狀態」的 finding，然後在錯誤的方向上做接下來三天的工作。

**否定結果需要對照組才有方向。** 這跟上一輪「先跑原生再跑 WASM」是同一個原則的另一個面向：
原生對照解決的是跨層歸因，正向對照解決的是「工具壞了還是被測物壞了」。

還有一件：**「已排除所有其他變數」不等於「找到成因」。** 原生對照跑完，我手上是「同 commit、
同 fixture、同方法、同位置，只剩 WASM build 這一個變數」—— 邏輯上無懈可擊，而結論
（上游候選）是錯的。因為「WASM build」不是一個變數，是一整層，裡面還有我們自己寫的 engine 迴圈。
消去法只能把範圍縮到某一層，接下來要找的是那一層裡**能被開關的機制**。scheduler drain 就是那個
開關：按下去，行為就變成原生的樣子。

歸因那一段還多學到一件事：**比較兩個結果之前，要先確認兩邊量的是同一件事。** A2-native 與
A2-wasm 的結論看起來直接矛盾，實際上兩者連 caret 怎麼移動都不一樣。如果沒有回頭讀原生探針的
原始碼，這個矛盾會被寫成「WASM 壞了」然後結案 —— 方向對了，但理由是錯的，而錯的理由會讓下一個人
去修錯的東西。真正把它釘死的是把差異變成受控變數：同一份 fixture、同一組座標、四種方法各跑一遍。
