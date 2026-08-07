# DEVLOG 2026-08-06 — E2-A 候選 1：主迴圈跑起來了，freshness 假設卻死在自己的探針下

> 對象：一起看 E2 的同事。接續 [DEVLOG-2026-08-05-wasm-sdk-e2-a2-wasm](DEVLOG-2026-08-05-wasm-sdk-e2-a2-wasm.md)。  
> 相關：[SPEC E2-A](specs/SPEC-E2-A-paragraph-format-discovery.md)（已改 v7）、
> [finding 021](findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)

## 這一輪做了什麼

把 finding 021 的候選 1（跑上游 emscripten 主迴圈）從「屬重構、待評估」做到「已實作、
兩瀏覽器實測」。新隔離 profile `e2-mainloop-attribution`（`OXSDK_MAINLOOP_ENGINE`）：
engine 不再有阻塞的 `for(;;)`＋condition variable 命令迴圈，改為 COOL kit 的產品拓撲——
命令派送發生在 unipoll poll callback 裡，VCL scheduler 由上游主迴圈的 tick 推動。

**結論同樣分兩半，而且第二半否證了我自己前一天的推論：**

- **主迴圈機制成立。** 開檔（0.8 秒）、render、search、click、五個格式派送、逐步存檔、
  close，全流程 Chrome 150 與 Firefox 153 通過。產品層推排程機制從「未定」變成
  「有一個實測可跑的候選」。
- **「有了迴圈狀態就會新鮮」是錯的。** 活迴圈下純 caret 移動，watched payload 會抵達，
  但**落後一個定位點**——每個位置讀到的是前一段的值。昨天歸因實驗三「推排程後狀態
  立刻正確出現」在舊組態成立，但那個 drain 做的事**不只是推一次排程**：它迴圈到靜止，
  而穩定跳動的迴圈追不上。

> **同日覆核修訂。** 本文初版此處寫「core 連狀態重算都沒排進 scheduler（
> `GetMostUrgentTaskPriority()` 回 -1、STATE_CHANGED 零抵達）」。兩個引用都不成立，
> 已在下面「覆核：我把三件事說錯了」一節逐條更正；正確的機制是收斂／順序問題。

A3 仍不啟動，但卡點從「產品 pump 機制未定」精確化為「PEI 與活迴圈的行為差異未歸因」。

## 通往迴圈的三個坑（依踩到的順序）

每個都值一條「已排除」，全部已寫進 finding 021。

**一、`lo_startmain`：所有既往 WASM profile 都帶著一條隱藏執行緒。**
第一版直接呼叫 `runLoop`，open 逾時 180 秒。Playwright console 抓到
`Thread name: "lo_startmain"`——不設 `SAL_LOK_OPTIONS=unipoll` 時，
`lo_initialize` 會自己 spawn 這條執行緒跑一條 soffice_main（`init.cxx:8381`），
我們的 `runLoop` 再跑第二條，兩條相撞。修法照抄 COOL kit：hook 前
`setenv("SAL_LOK_OPTIONS", "unipoll", ...)`（`cool kit/SetupKitEnvironment.hpp`）。
順帶的修正主義發現：昨天寫「我方探針從不呼叫 `Application::Execute()`，所以那個迴圈
不存在」不準確——舊建置裡上游的 lo_startmain 有跑完整 `Desktop::Main` 並裝過主迴圈，
只是它的 tick 從未推動我方 scheduler（為何如此是獨立的未驗證子問題）。

**二、`runLoop` 在本平台不跑迴圈。** unipoll 模式下 hook 已 InitVCL，
`runLoop` 內部的 `soffice_main` 走到 `ImplSVMain` 的 `IsVCLInit()` 早退
（`vcl/source/app/svmain.cxx`），立即返回。`runLoop` 只貢獻 poll／wake callback 註冊與
`SfxLokHelper::registerViewCallbacks`。迴圈本體由 engine 自己呼叫
`Application::Execute()`（out-of-tree 宣告綁定，同 finding 016 對
`IsUseSystemEventLoop` 的技巧）。副作用是好的：`emscripten_set_main_loop_arg` 的
`throw 'unwind'` 只展開 engine 自有的框架，`sofficemain.cxx` 那個 HACK 對付的
「unwind 穿越帶解構子的上游框架」問題整個消失。

**三、`pData` 為 null 會靜默停用 unipoll。** 這個最陰：一切就緒、tick 在跑、
`execute-returned` 沒出現（unwind 成功）、tick-alive 探針每秒準點——但 poll 一次都沒被
呼叫。`SvpSalInstance::ImplYield` 的 unipoll 分支要 `mpPollClosure` 非空才呼叫
poll callback，而我把 `runLoop(kit, poll, wake, nullptr)` 的第四參數傳了 null。
COOL 傳它的 KitSocketPoll 指標，從不為 null。改傳任意穩定非空指標後，
`poll #0` 立刻出現、open 0.8 秒完成、全流程通了。

## 然後 freshness 假設被自己的探針殺掉

> **本節初版有兩個引用是錯的**（見下面「覆核：我把三件事說錯了」）。原文保留在
> 下方並標示，因為錯的推理鏈本身是這一輪的產出之一；正確的結論是「payload 會抵達
> 但落後一格」，不是「什麼都沒送」。

迴圈通了之後，readback 的數字似曾相識：`freshPositions` 只有第一輪 click 的
heading／body-paragraph，`listReadInsideList: false`——**與 finding 021 的原始特徵
一模一樣**。當時我認為三個證據把「迴圈會帶來 freshness」釘死在否證上：

1. ~~search 定位後 settle 4 秒，`stateChangedDelta` = 0——core 什麼都沒送~~
   **（錯：這是過渡 build attempt-03 的讀數。最終 build 有抵達，只是落後一格。）**
2. ~~`poll-pending` 探針在 idle poll 期間全程回 -1——scheduler 裡沒有 ready 任務~~
   **（錯：該取樣點結構上只能印 -1，零資訊。）**
3. click 在前兩個位置的爆量 26／158 筆，與舊 blocking 迴圈 profile 的數字**一字不差**。
   同數字不是巧合：那是 `initializeForRendering` → `doc_iniUnoCommands` 註冊 slot 後的
   **初始 binding flush**，推一次就沒了，跟「逐移重查」無關。所以它出現在「第一次有
   輸入事件」的位置，之後衰減成 2 筆不可辨識。**（這一項成立。）**

第 3 點單獨仍足以否證「迴圈帶來 freshness」（click 的流量不是逐移重查），而落後一格
的正確圖像同樣否證它，只是理由不同：不是「沒送」，是「追不上」。於是昨天的歸因敘述
要修正：`ProcessEventsToIdle` 在舊組態放得出 watched payload，但那不能解讀成「任務
在排程裡等著、只缺人推」——PEI 與活迴圈之間有真實的行為差異，候選解釋有三（舊建置的
lo_startmain 跑完了完整 `Desktop::Main` 初始化而 unipoll 組態沒有；PEI「迴圈到靜止」
與每 tick 一件的語意差；真實輸入路徑與 API 定位路徑的 invalidation 差異），
判別實驗已列在 finding 021。

## 這一輪我自己犯的三個錯

**一、「idle-poll 即清 stale」——一個看起來優雅、實際不健全的不變式。**
第一版的 freshness 設計：poll 以非零 timeout 進來 ⇒ scheduler 到 idle ⇒ core 該算的
都算完了 ⇒ 清 stale。推理鏈的第二步是假的（上面第 2 點證據）。這個版本跑出過一次
漂亮的 5/5 全成立＋存檔相符（Chrome attempt-03）——僥倖：五個派送都落在同一段落，
髒快取剛好是對的值。**如果 A3 的跨段落序列先跑，這就是一次「別段狀態造成的假
no-op」實彈**——finding 021 存在的意義就是擋這個。已回退為「僅 watched payload 抵達
才清」；回退後 sound 語意的矩陣是誠實的：兩瀏覽器 5/5 typed 拒絕、檔案零變動。
attempt-03 保留，但只作迴圈機制示範，文件裡標明它的前置讀值依賴同段序列。

**二、engine pthread 的 stderr 進了黑洞，我對著空 console 猜了兩輪。**
`fprintf(stderr, ...)` 在該 worker 完全到不了 Playwright 能捕捉的 console，而
`Thread name:` 這類 SAL 輸出又到得了，誤導我以為通道沒問題、是程式碼沒跑到。
改用 `MAIN_THREAD_EM_ASM` 的 console.log（與 emitJson 同一條已證實可達的通路）後，
每一階段立刻可見。教訓與上一輪「否定結果需要對照組」同構：**先證明你的量測通道
會響，再解讀它的沉默。**

**三、背景 shell 的 cwd 沒了，`make` 打了空氣，我拿舊 wasm 又跑了一輪探針。**
背景執行的重建在錯誤目錄下 `make: No rule to make target`，而我只看了任務完成通知
沒看輸出，接著用未更新的 dist 跑探針、得到「修了沒效」的假結果。之後每輪 rebuild
都改成驗 `BUILD_EXIT`＋比對 dist 的 `wasmSha256`＋`strings` 找新字串三重確認。
與 E1-C 的教訓同款：**「跑過了」不等於「跑的是你以為的那個」。**

## 保護凍結 artifact

- 所有 engine 改動都在 `#ifdef OXSDK_MAINLOOP_ENGINE` 內。機械證明：以 E1-B 組態
  （`-DOXSDK_EDITOR_DISCOVERY -DOXSDK_FINDING_016_SELECTION_BARRIER`）重編改動後的
  `probe_engine.cpp`，與既有 `build/e1/editor-v1/probe_engine.o` **逐位元相同**。
- worker 仍走 builder 的精確替換（gate 加第三個 scope），`sdk/sdk-worker.js` 本體未動。
- `make -n` 先驗建置計畫：只寫 `build/e2/mainloop-attribution` 與
  `dist/profiles/e2-mainloop-attribution`（外加兩個決定性的 exports.txt 中間檔）。
- `tests/test_e2_profile.py` 17 項全過（新增 4 項：scope／engineLoop 標記、
  **無 drain 能力**——「無 unit hook 可連」是排除法的一部分，用測試釘住——
  與既有 profile 不被取代）；凍結 hash 測試通過。

## 現在的狀態

**已完成**

- `e2-mainloop-attribution` 隔離 profile：Makefile 區塊、builder（`engineLoop` 診斷
  欄位、三 scope 共用 worker patch）、client scope、harness `mainloop-attribution` mode
  （refresh 是有界等待，不派送任何 pump）、runner mode、靜態測試。
- 候選 1 機制鏈實測通過（兩瀏覽器）；三個坑歸因並記錄。
- freshness 假設否證（三重證據）；不健全的 stale 清除回退；sound 語意矩陣兩瀏覽器落地。
- finding 021 大改（新已觀察章、已排除表 +4、卡點重定義、判別實驗）、SPEC E2-A v7、
  記憶檔更新。

**未完成**

- PEI vs 活迴圈的差異歸因（判別實驗一：帶 drain 的 mainloop profile——先合併兩個
  `class Application` 宣告，目前有 `#error` 擋著；判別實驗二：游標命令 placement）。
- A3～A7 未執行，E2-A 仍無判定。
- finding 018 重評、finding 020 送上游，順位不變。

## 下一步（同日已執行，見下章）

1. 判別實驗一：`OXSDK_MAINLOOP_ENGINE`＋scheduler drain 的複合 profile，在活迴圈組態下
   直接測 PEI。放得出 payload ⇒ 差異在 PEI 語意（往「受支援的 flush 原語」談）；
   放不出 ⇒ 差異在 `Desktop::Main` 初始化（往「unipoll 組態缺了哪段 init」查）。
2. 判別實驗二：用游標命令動作（完整 SfxDispatch 路徑）作 placement 重跑 readback。
3. 兩個判別結果落地後，重寫 finding 021 的上游溝通草稿——現在能精確描述缺口了。

## 同日下半：兩個判別實驗都出了裁決

**實驗一：PEI 在活迴圈下有效——假設「差異在 Desktop::Main 初始化」否證。**
複合 profile `e2-mainloop-pei-attribution`（合併兩個 `class Application` 宣告時用
016 區塊內的巢狀 `#ifdef`，既有組態的前處理輸出不變；poll callback 加了重入護欄，
因為 drain 命令會在 poll 內巢狀跑 `ImplYield`，命令派送絕不能跟著巢狀）。結果兩瀏覽器
逐項相同：search 四點 `freshAfterDrain` 全 true、值全對（list-item false→**true**、
after-list true→**false**），五個派送 `verified-format-state`、postcondition
**5/5 相符**——修法完整矩陣第一次在產品級迴圈組態下重現。

**實驗二：真 dispatch 也叫不醒重算——假設「差異在定位路徑」否證。**
每次 API 定位後加派一個 `move-character-left`（完整 SfxDispatch；單向一步，雙向來回
會讓第二步重標 stale 而值未變不再廣播，把訊號自己蓋掉——設計時差點踩這個）。nudge
全部派送成功，list-item 依然讀不到「在清單內」，五個派送全拒。

**裁決：缺口在 PEI 語意本身。** 每 tick 的 `ImplYield(isActive(), false)` 收斂不到
`InnerYield(false, true)` 迴圈到靜止所到達的狀態，對位的 payload 因而落後一格；
需要的工作一直都在，PEI 的執行方式把它跑完，穩定跳動的迴圈跑不完。哪個因素是關鍵
（`bWait`、`bHandleAllCurrentEvents`、外層迴圈——**三個都不同**）留給後續窄歸因；
覆核提供的機制線索（`DispatchUserEvents` 後提早 return 跳過 `CheckTimeout()`）讓
「改傳 `true`」成為最有根據的一個，但仍需隔離確認。

上游報告的一句話版本：**unipoll＋system-loop（emscripten）組態下，svp `loop()` 的
每 tick `ImplYield(isActive(), false)` 收斂不到 `Scheduler::ProcessEventsToIdle()`
所到達的狀態，caret 移動後 watched command 的 STATE_CHANGED 要嘛不抵達、要嘛落後
一個定位點，使 LOK host 讀到的段落格式狀態屬於前一段**；可提的修法：`loop()` 改傳
`bHandleAllCurrentEvents=true`／迴圈到靜止，或把 process-to-idle 升格為受支援入口。
最小重現就是 `e2-mainloop-attribution`（壞）與 `e2-mainloop-pei-attribution`（好）
的對照。

## 覆核：我把三件事說錯了

本文與 finding 021 的 2026-08-06 章節寫完之後，外部覆核挑出三處，查證全部屬實，
已在兩份文件原地修訂。記在這裡，因為錯的形態比錯本身有價值。

**一、「重算根本沒被排進 scheduler」對最終 build 的證據為假。**
我引用的 `stateChangedDelta=0` 來自 Chrome attempt-03——**過渡 build**（`681b8a1d`，
就是那個被我判為不健全、只能當機制示範的版本）。最終 sound build（`a696f0d6`）的
同一批讀數是：Chrome `list-item` 15 筆（全不可辨識）、`after-list` 5 筆含 **1 筆
watched**；Firefox `list-item` 52 筆含 **2 筆 watched**、`after-list` 同樣 1 筆。
而且值乾淨地落後一格：`body-paragraph` 讀到 heading 的 `F/T`、`list-item` 讀到 body
的 `F/F`、`after-list` 讀到 list-item 的 `T`。

諷刺的是，這一輪我自己寫過「hash 要對得上該輪 evidence，不以最終 hash 回溯代表早期
結果」——然後反向踩了同一個坑：拿早期讀數代表最終結論。**紀律寫進文件不等於套用到
自己身上。**

**二、`GetMostUrgentTaskPriority() == -1` 是零資訊量測。**
探針只在 `timeoutUs != 0` 取樣，而該條件蘊含 `CheckTimeout()` 回 false（sal 計時器
未到期）；`GetMostUrgentTaskPriority()` 在 `nTime < mnTimerStart + mnTimerPeriod - 1`
就直接回 -1。兩個條件是同一件事，那行只可能印 -1，不論有沒有任務被排。我拿它當
「連 ready 任務都沒有」的證據，引用了四處。

這比第一項更難堪：上一段我才寫「先證明你的量測通道會響，再解讀它的沉默」，然後
造了一個**結構上不可能響**的探針，並解讀它的沉默。加一條可操作的判準：**新探針
上線前，先問「什麼輸入會讓它印出不同的值」——答不出來就不是探針，是常數。**

**三、`loop()` 與 PEI 差兩個參數，我只點名一個。**
`loop()` 是 `ImplYield(comphelper::LibreOfficeKit::isActive(), false)`（LOK 下
`bWait=true`），PEI 是 `ImplYield(false, true)`。`bWait` 與 `bHandleAllCurrentEvents`
都不同，外加 PEI 的外層 `while` 迴圈——三個候選因素未隔離。要向上游提「改傳 `true`」
而不先隔離，就是猜。

覆核附帶一條我沒看到的線索，直接把提議升級：`ImplYield` 開頭
`if (!bHandleAllCurrentEvents && bWasEvent) return true;` 會在派掉 user event 後
提早返回，跳過下一行的 `CheckTimeout()`——而那行的上游註解自己寫著
`CheckTimeout() invokes the sal timer, which invokes the scheduler`。**每個有 user
event 的 tick，scheduler 完全不會被叫到**，與「落後一格」完全吻合。

**四（覆核連帶發現）：fail-closed 的實作有個沒補的洞。**
現行不變式是「只有 watched payload 抵達才清 stale」。落後一格的 payload 一樣會清掉
它——`after-list` 就被標成 `fresh=true` 而手上是 `list-item` 的值。我以為回退掉的
靜默 no-op 路徑，換了個門又開著；本輪五個派送全拒是因為等待窗內沒等到 payload，
不是因為不變式擋住了。修補方向是把 payload 綁到 caret／position 序號（engine 已有
`sourceSequence`）。**這一項優先於取得 pump**——pump 到手也擋不住它。

## 交接備註

本輪到此告一段落。後續交接給下一個 session，順序已改：
**① 補 fail-closed 的序號綁定（上面第四點）② 窄歸因隔離三個候選因素
③ 寫上游報告（照抄落後一格的數字，不要寫「永不抵達」）④ A3。**
接手入口：finding 021 的「卡在哪裡（給接手的人）」（開頭有覆核警語）與
「判別實驗結果與剩下的路」，以及記憶檔 `litecore-wasm-sdk-status`。送上游前的紀律
不變：先搜重複單、在完全未修改的上游 build 重現；finding 020 的送出順位仍在本單之前。

## 方法上值得帶走的一點

**探針要先於解釋。** 這一輪三次關鍵轉折——lo_startmain、`runLoop-returned`、
`poll-pending -1`——沒有一次是讀碼推出來的，全是儀器先看到、再回頭讀碼對上機制。
反例也在同一輪裡：我對著讀碼建立的「idle ⇒ 已重算」推理鏈寫了實作，被自己的
計數器否證。與昨天「先量，再寫死」是同一個原則，但這次它救的不是常數，是不變式。

還有一件：**僥倖通過比失敗更危險。** attempt-03 的 5/5 若不是後續 readback 數字
似曾相識引起懷疑，它就會以「修法驗證通過」進文件——而它實際驗證的是「五個派送
恰好同段」。判準要問的不是「結果對不對」，是「結果對的理由是不是你宣稱的那個」。

---

## 二次覆核（同日稍後）：撤回一個我自己加上去的安全洞

第一輪覆核的三條指正全部成立，已原地修訂。但**第一輪據此加寫的第四件事是錯的**，
在動手實作前先去驗前提時發現，已撤回。

錯的宣稱是：「落後一格的 payload 會清掉 stale 旗標，fail-closed 被繞過，未修補且
阻擋 A3。」撤回依據三項，全部來自原始碼與**同一批既有 evidence**，沒有新實驗：

1. 上表的 `fresh` 是 harness 的欄位，定義為 `entry.formatStateEventsObserved > 0`
   （`web/e2-format-discovery-app.js:268`），而計數起點在**定位動作之前**（同檔 :242），
   所以它把定位本身引發的廣播也算進來。
2. engine 的 `formatStateStale` 才是權威訊號，而它在兩瀏覽器**全部 search 列都是
   `true`**——保留下來的舊值被正確地標成不新鮮。
3. 機制上也不可能：`updateEditorFormatState` 先 `formatStateStale = false` 才
   `emitEditorStateEvent("format-state")`，不存在「事件到了但旗標還 stale」的 payload。

殘留的真實缺口比原本寫的窄：**一個旗標守著五個欄位**，任何一筆 watched payload
（例如 `.uno:Bold`）都會清掉它，之後讀清單前置條件時該欄位可能從未為這一段廣播過。
標為推論、未觀測到實例。

這一條的教訓與同日上半場完全相同，只是換了個對象：**先確認量測通道量的是什麼，
再解讀它。** 上半場我造了一個結構上不可能響的探針（`GetMostUrgentTaskPriority`），
下半場我把 harness 的欄位當成 engine 的判準。兩次都是拿一個沒問清楚定義的數字當證據。

## 產品決定：路線 C，上游暫緩

使用者決定**不現在送上游**，素材另行整理為
`UPSTREAM-REPORT-DRAFT-lok-status-update-under-emscripten-loop.md`（草稿，第 7 節列了
送出前必須完成的四件事，目前 0/4）。

同時更正一個一直沒被質疑的前提：**「沒有受支援的刷新入口，只能等上游」是錯的。**
`Scheduler::ProcessEventsToIdle()` 是 `include/vcl/scheduler.hxx:65` 的公開 API
（`class VCL_DLLPUBLIC Scheduler final`），且有產品呼叫者
（`sw/source/uibase/dbui/dbmgr.cxx:1375`、`sw/source/ui/dbui/mmresultdialogs.cxx:712`、
`vcl/source/app/svmain.cxx:438`）；被標成 unit-test 的只有 C 包裝
`unit_lok_process_events_to_idle`（`svapp.cxx:485-491`），內容三行。真正的限制是該
header 自己的 busy-lock 警告，那是我方要設界限的事。

產品路線定為 **C：不讀前置狀態**——closed action 一律直接派送，判定只用後置條件
（派送後 state ＋ 存檔 ODT，已驗證 5/5），移除 `documented-state-noop`。理由是
barrier 壞的是前置那一半，後置那一半完全可信；而 `documented-state-noop` 本來就是
finding 021 明文不得當成已驗證能力的東西。路線 A（產品自行 pump）延後而非否決。

## 然後就撞到 finding 022：021 在產品面已經成真

改文件時注意到 `set-bold`／`set-italic` 的 `documented-state-noop` 捷徑**不在**
`#ifdef OXSDK_E2_FORMAT_BARRIER` 之內，而 `e1-editor-v1` 走的
`updateEditorFormatState`（`#else` 分支）**沒有 `formatStateStale`**。推論：已出貨的
release 可能已經在產生假 no-op。

在**未重建**的凍結 profile 上驗證（新 harness `web/e1-bold-noop-check.html` ＋
`tools/run_e1_bold_noop.py`；`make -n e1-bold-noop-assets` 確認只複製兩個檔案，
不相依 `e1-editor-profile`）。三個 case 只差快取如何被填：

| case | 前置 | 快取 `bold` | 派送 | 存檔 ODT |
|---|---|---|---|---|
| control | 無 | `null` | `uno-command-result` | 已變粗體 |
| exposure（search） | search 選粗體字 | `null` | `uno-command-result` | 已變粗體 |
| exposure-click | **click** 進粗體字 | **`true`** | **`documented-state-noop`** | **未變** |

Chrome 150 與 Firefox 153 逐欄相同。已立
[finding 022](findings/022-e1-release-set-bold-false-noop.md)。

第一版用 search 定位沒踩到，一度以為 release 是安全的——查下去才發現原因是快取
**根本沒被填過**（`bold` 全程 `null`）。**那不是防護，是巧合**：同一個缺陷讓那條
路徑意外安全。這正是同日兩次覆核的教訓第三次出現：沒踩到不等於擋住了，要問的是
「沒發生的理由是不是你以為的那個」。

修法傾向與路線 C 一致：移除捷徑，`set-bold`／`set-italic` 一律派送、只用後置條件判定。

## 本輪回歸

`make test-e2-a-static` 17 項全過；`e2/discovery-matrix-v1.json` 通過 JSON 驗證；
`dist/profiles/e1-editor-v1` 的 `probe.wasm`／`probe.js`／`sdk-worker.js` 三個 SHA-256
跑前跑後逐一比對相同（`94b38437…`／`45c31f32…`／`9696c9ce…`）。

## 補測與修法（finding 022）

**補測：三種操作全中。** harness 擴為六個 case（三組配對，每組只差前置的 click）：
套用粗體、套用斜體、**取消粗體**。三組的 exposure 全部回 `documented-state-noop`
且存檔零變動，三組的 control 全部正常生效，Chrome 150 與 Firefox 153 逐欄相同。

取消粗體那一組值得單獨記：快取被 click 填成 `bold=false`，目標卻是真的粗體字，
`set-bold(false)` 因此被短路掉、粗體留著。**方向無關**——不是「該套用的沒套用」，
是任何一次快取與實際不符都會靜默失效。

判準上多加了一個欄位：`notReached`。第一輪用 search 定位沒踩到，差點被讀成「安全」，
實際上是快取根本沒填成功、根本沒測到捷徑。把「沒踩到」和「沒測到」分開記，是為了讓
同一個誤讀不會再發生一次。

**修法：移除捷徑，兩端一起。**

- `src/probe_engine.cpp` 的 `handleEditorAction`：`set-bold`／`set-italic` 不再讀前置
  快取、一律派送。原處留了註解說明為什麼移除，免得日後被當成效能優化加回來。
- `editor-shell/editor-client.js`：同步移除對 `documented-state-noop` 的接受。engine
  不再產生它、client 也不再接受它——只改一端的話，同一個靜默 no-op 回來時沒人會發現。

這正是路線 C 在最小範圍的落實：**不讀前置狀態，只用後置條件判定。** 這兩個命令本來
就是冪等的，多派送一次沒有代價；失去的只有 `changed` 的「本來就是這個狀態」語意，
而那個語意 finding 021 早就寫明不得當成已驗證能力。

**驗證：隔離 profile，不動凍結 artifact。** 新增 `e1-editor-v1-noopfix`
（`E1_FIX_BUILD`／`E1_FIX_DIST`），編譯旗標與 `e1-editor-v1` **完全相同**，只有輸出
路徑不同；`make -n e1-noopfix-assets` 確認整條規則鏈不觸及
`dist/profiles/e1-editor-v1/`。兩瀏覽器跑同一組六個 case：`exposed` 為空、
`notReached` 也為空、六個 case 全部生效並由存檔 ODT 確認。

`notReached` 為空是這次驗證的關鍵：它代表快取仍然被填、情境仍然到達，修法不是靠
「剛好沒走到那條路」通過的。這一輪反覆吃過這個虧，所以判準先把它寫進去。

**還沒做、需要明確決定的一步**：凍結的 `e1-editor-v1` 仍帶缺陷。原始碼修好不等於
出貨物修好——依 SPEC E2-A 第 3 節不得擅自重建或覆寫該 artifact，要讓修法進到出貨物
必須重建它並重跑 E1-C 驗收與 R6～R8 回歸。目前原始碼與凍結 artifact 之間有一個
已知且已記錄的落差。

回歸：`make test-e2-a-static` 17 項全過；`dist/profiles/e1-editor-v1` 三個 SHA-256
在整輪建置與六次瀏覽器跑測前後逐一比對相同。

## 重新凍結 e1-editor-v1（使用者授權）

**暴露面先釐清（靜態，便宜）。** `editorActionV1` 在 `sdk/sdk-worker.js:37,94` 以
`narrow-editor-v1` 能力開閘。dist 內十四個 profile，只有 `e1-editor-v1`（與其驗證
變體）宣告該能力；`writer-review`、`writer-review-r6`、`writer-reader`、`full-qa`
都沒有。所以雖然共用同一份 `handleEditorAction`，R5～R8 的呼叫端到不了那條捷徑。
**暴露面就是 e1-editor-v1 一個。**

**重建。** 舊 artifact 先備份再覆寫。新 hash：WASM `94b38437…` → `97e605ee…`、
loader `45c31f32…` → `b9a29749…`；`sdk-worker.js` 未變（修法在 engine 端）。

**驗證的是出貨物本體，不是驗證 profile。** 重建後直接對 `e1-editor-v1` 跑同一組六個
case：Chrome 與 Firefox 皆 `exposed` 為空、`notReached` 為空、六個 case 全部生效。

這一步是有必要的，因為隔離驗證 profile 的 WASM hash（`e424eec4…`）與重建後的出貨物
（`97e605ee…`）**不同**。兩者大小完全相同、僅 30 個位元組相異，且差異落在 code
section 的 local index，屬連結器在不同輸出路徑下的暫存器配置非決定性。但那是推論
——與其論證「差異無害」，不如直接對真正會出貨的那份重跑一次。

**釘住舊 hash 的三處已更新，每處都留了為什麼改的紀錄**：`tests/test_e2_profile.py`
的 `FROZEN`、`e1/validation-matrix-v1.json` 的 `baseline`（加 `refrozen` 區塊）、
`e2/discovery-matrix-v1.json` 的 `baseline`（加 `e1EditorV1RefrozenNote`，載明所有
E2-A 量測都早於這次重凍、且 E2-A 從未跑在 e1-editor-v1 上，因此沒有任何 E2-A 結果
被作廢）。

**測試契約也跟著改，而且加了一道反向護欄。**
`editor-shell/tests/editor-client.test.mjs` 原本有一項「接受 typed no-op」的斷言，
改為斷言必然變更；另外**新增一項回歸測試：engine 若再送 `documented-state-noop`，
client 必須拒絕**。這個 bug 已經出過一次，而且是靜默的——只把它修掉、不留下會叫的
護欄，等於等它再回來一次。

**全回歸通過**：`test-e1-{a,b,c}-static`、`test-e2-a-static`、
`test-r6-{a,b,c,roundtrip,release}`、`test-r7-{a,b,c,d}-static`、
`test-r8-{a,b,c,d}-static`、`test-finding-016-scheduler-static`。

finding 022 就此關閉。

## E1-C 瀏覽器驗收（重新凍結後重跑）

**先更正一個帳面錯誤**：`e1/validation-matrix-v1.json` 的 `status` 一直寫
`planned-not-executed`，但 E1-C 其實 **2026-08-05 就跑過並判定 `E1_GO_ODT_EDITOR`**
（證據樹與 `summary.json` 都在）。那個欄位是過時的紀錄，不是未執行。已更正並補上執行史。

不過重跑仍然必要：那份裁決是對**修正前**的 artifact 做的，重新凍結後它就不再描述
出貨物了。

**自動部分：兩瀏覽器全過。** integration（3 輪）、recovery（6 案）、corpus（5 份）、
lifecycle（10 warmup ＋ 10 cycle）在 Chrome 150 與 Firefox 153 全部通過；
roundtrip、regression、preflight 亦通過。`automaticPass: true`。

**兩次偶發，各一次，重跑後消失。** Chrome 的 `cycle-06` 與 Firefox 的 `warmup-08` 各出現
一次 `init timed out after 120000 ms`。兩者都發生在我同時在做 115 MB WASM 連結的時候，
單獨重跑 lifecycle 階段後兩瀏覽器每一輪都過。判為主機負載造成，非產品缺陷——但**失敗的
attempt 保留在證據樹裡**，沒有覆蓋掉，因為「重跑就好了」不該由結論來背書。

**人工輪擋下來了，而且是驗證器自己擋的。** 裁決是 `E1_PARTIAL_GO_ODT_EDITOR`，
`automaticPass: true` 但 `manual.pass: false`，兩瀏覽器都卡在 `artifact` 這一項。原因是
`validate_e1_c.py` 把人工證據綁在 `artifact.editorContract.{loader,wasm,worker}Sha256`
上，而現存的 Chewing 紀錄仍帶著修正前的 `94b38437…`，對不上重新凍結後的 `97e605ee…`。

**這正是應該發生的事。** 人工輪需要真人以 Fcitx5 Chewing 做可信輸入與原生複製貼上，
我做不到；如果驗證器當初沒把人工證據綁上 hash，這次就會靜靜地拿舊 build 的人工結果
替新 build 背書。這個設計值得記下來——**它擋下的正是我這一輪自己差點犯的那類錯**
（我一度以為人工 JSON 沒記 hash，是我看錯欄位）。

要補完 `E1_GO_ODT_EDITOR`，需要操作者各跑一輪：

```bash
cd wasm_sdk_probe
python3 tools/run_e1_c.py --manual-server        # 然後在 Chrome 與 Firefox 各做一輪
python3 tools/validate_e1_c.py                   # 重新裁決
```

## 人工輪 attempt-02：遠端執行成立，但四段固定字串打錯而未通過

操作者從 192.168.2.232 之外遠端接入。**已觀察**：`--manual-server` 硬綁
`127.0.0.1:8765`，而人工頁的 pass 閘門要求 `crossOriginIsolated`、人工模式又用真的
`navigator.clipboard`，兩者都需要 secure context。把 port 綁到 `0.0.0.0` 再從
`http://192.168.2.232:8765` 連，不是繞過限制而是直接讓驗收失敗。採 SSH port forward
（`ssh -L 8765:127.0.0.1:8765`），origin 維持 `127.0.0.1`，secure context 成立。

事前檢查：`dist/editor-shell/editor-client.js`、`editor-session.js`、`state-machine.js`、
`sdk/document-sdk.js`、`e1-editor-validation{.html,-app.js}` 與修正後原始碼 `cmp` 相同，
人工輪跑的確實是含 finding 022 修正的 client。

**結果：兩輪都沒過，`manual.pass: false`。** 遠端管道本身沒問題——`crossOriginIsolated:
true`、artifact hash 對上 `97e605ee…`、`operatorConfirmedChewing`、`trustedComposition`、
`nativeCopy.isTrusted`、`cancelProbe`、Clipboard API 讀寫、取消字串零出現，全部通過。
壞掉的是**打進文件的字串本身**：

| 案例 | Chrome 存下的 | Firefox 存下的 | 應為 |
| --- | --- | --- | --- |
| caret IME | `e1cbbp人工第一筆中文輸入` | ``E`1C人工第一筆中文輸入`` | `E1C人工第一筆中文輸入` |
| selection 取代 | `e1c人工選取替換` | `E1C人工選取替代` | `E1C人工選取替換` |
| 原生貼上 | 完全不存在 | 正確 | `E1C人工原生貼上臺灣😀` |
| Clipboard API | 正確 | 正確 | `E1C人工剪貼簿臺灣😀` |

Chrome 的 `E1C` 前綴變成小寫且多出 `bbp`，Firefox 多出一個 `` ` ``——都是注音模式下輸入
ASCII 前綴時鍵位外漏。Firefox 的「替**代**」是選錯候選字。`searchText()` 的比較是
`selection.text === text` 嚴格相等，而 LOK `search()` 大小寫不敏感，所以 Chrome 第二列
出現 `found:false` 卻帶著 selection rectangle——搜尋確實命中了 `e1c…`，是嚴格比較擋下來的。
**這是閘門正確運作，不是產品缺陷。**

**待驗證**：Chrome 的 `trustedPaste: false` 且原生貼上字串完全不存在，但同一 build 的
Firefox 這一步是通過的，`nativeCopy.isTrusted` 在 Chrome 也是 true（複製有發生）。最可能
是 Ctrl+V 時焦點不在 SDK sink，但沒有證據排除 Chrome 特有問題。若重跑時操作者確認有在
sink 內按下 Ctrl+V 而 `trustedPaste` 仍為 false，就升級為 finding 候選。

失敗的兩份證據由 `preserve_previous()` 保留為 `*-attempt-01` 之後的世代，未覆蓋。
裁決維持 `E1_PARTIAL_GO_ODT_EDITOR`。

## 人工輪 attempt-03：兩瀏覽器通過，E1 回到 `E1_GO_ODT_EDITOR`

同一個 SSH port forward 管道，操作者重打 caret 與 selection 兩段固定字串並補上 Chrome 的
Ctrl+V。Chrome 150 與 Firefox 152 的九項檢查全過——`operatorConfirmedChewing`、
`trustedComposition`、`trustedNativeCopy`、`trustedPaste`、`cancel`、`clipboardWrite`、
`clipboardRead`、`artifact`、`output`——四段必要字串各出現一次，取消字串零出現，兩份 ODT
的 artifact hash 都是 `97e605ee…`。

`validate_e1_c.py` 最終裁決：`automaticPass: true`、`complete: true`、
**`decision: E1_GO_ODT_EDITOR`**。E1 這個閘門對**修正後的出貨物**重新完整成立。

**前一輪的待驗證項結案。** attempt-02 裡 Chrome 的 `trustedPaste: false` 沒有重現；
在同一個 build、同一台機器、同一條遠端管道上重跑就通過了，所以那是按 Ctrl+V 時焦點不在
SDK sink 的操作落差，不是 Chrome 特有缺陷。**不開 finding。**

三代人工證據都在：`*-attempt-01`（2026-08-05，舊 artifact `94b38437…`）、
`*-attempt-02`（打錯字串的失敗輪）、以及現行這一輪。沒有任何一代被覆蓋。

**遠端執行的結論值得記著**：`--manual-server` 綁 `127.0.0.1` 不是需要放寬的限制，而是
人工輪能成立的前提——secure context 沒了，`crossOriginIsolated` 與 `navigator.clipboard`
會一起消失，而那正是六個人工案例裡的兩個。要遠端就用 port forward 把 origin 留在
`127.0.0.1`，不要改 bind 位址。

## 便宜實驗包（一）：finding 018 歸因完成，答案不是原本猜的那個

零重建。`e1-editor-discovery`（無活迴圈）、`e2-scheduler-attribution`（無活迴圈，
但有 format barrier 與相同 worker patch）、`e2-mainloop-attribution`（活迴圈）三者都已
建好，且都宣告 `editor-discovery-closed-actions`——判別實驗只要寫 harness，不用連結。

**結果推翻了本來的假設。** 原本要問的是「018 是不是和 021 同一個成因」。答案比那更
specific：

- 無活迴圈的三格，逾時**全部落在第一個 End**，18 輪中 14 輪；Home 每次都完成。
- `e2-scheduler-attribution` 與控制組同分——所以差異不是 barrier 也不是 worker patch，
  只剩迴圈。
- **但加上 Shift 之後，連無迴圈的控制組都 36／36 零逾時**，且後置條件逐輪一致
  （shift-Home 選 10 字、shift-End 收回 0）。

所以 line navigation 的移動**本身沒有壞**；壞的是引擎在 collapsed 情形等的那個
`EditorCaretOrSelectionCallback`（visible cursor）在沒有活迴圈時不會送達，而
`LOK_CALLBACK_TEXT_SELECTION` 會。這和 021 是同一個成因家族（要過 VCL scheduler 的
東西不會發生），但修法方向完全不同：**不必等上游、也不必在產品裡跑主迴圈，只要
completion 不依賴 visible-cursor callback**——和 022 之後採用的路線 C 同一個原則。

Home 會完成、End 不會，這個不對稱說明「無迴圈時 callback 一律不到」是錯的。成因沒有
再往下追，留為待驗證，連同「非 Shift 的 End 是否真的移動了游標」（逾時後 worker 被
`gEditorPending` 卡住，同輪內補測不到）。Chrome 未跑。

證據 `findings/evidence/finding-018-line-nav-attribution/`；harness
`web/f018-line-nav-check.html` ＋ `f018-line-nav-app.js`，`make f018-line-nav-assets`
刻意不相依任何 profile。

## Demo 前端編輯器（給 2026-08-07 的同事 demo）

純前端，跑在重新凍結的 `e1-editor-v1` 上，**零重建**——`demo-editor-assets` 刻意不相依
`e1-editor-profile`，因為重建出貨物會作廢當晚才補完的人工 Chewing 證據。

新檔：`web/demo-editor.html`、`web/demo-editor-app.js`、Makefile 的
`demo-editor-assets` 與 `serve-demo`。底下用的是既有且已驗收的 `EditorSession` /
`NarrowEditorClient`，沒有新增任何引擎能力。執行說明另立
`DEMO-2026-08-07-litecore-writer.md`。

**兩個設計決定直接來自 findings。** 粗體／斜體按鈕**不讀引擎前置狀態**——按鈕只反映
「自游標上次移動以來我們自己要求過什麼」，游標一動就回到未知並在 tooltip 說明；這是
路線 C 在 UI 上的樣子，也是 022 不會從這條路回來的原因。不支援的操作（上下行移動、
Home／End、Redo）按下去會**出聲拒絕**而不是靜靜不動。

驗證由存檔 ODT 判定，兩瀏覽器：Chromium 打字 revision 0→7、Shift+→ 選 5 字素後套粗體，
存檔 `content.xml` 出現 `T1` 帶 `fo:font-weight="bold"` 套在 `臺灣😀E1`（**emoji 算一個
字素**）；Firefox 153.0.1 同樣的 `T1` 套在 `E1-PL`。取消粗體、復原、三種不支援鍵提示、
zip／CRC 完整性、Worker 世代維持 1 全數確認。真 IME 組字未在這頁測過，留為待驗證。

## Demo 加上游標與選取（2026-08-07）

**不需要重建**（使用者已表示可以重建，但用不到）。出貨的 `e1-editor-v1` 的
`editorGetStateV1` 本來就回 `caret`（x／y／width／height，twips）與
`selection.{observed,collapsed,start,end,rectangles[]}`；`appendEditorState` 雖然在
`#ifdef OXSDK_EDITOR_DISCOVERY` 附近，但窄版 state 路徑一樣吐這些欄位。實測確認。

**一個要記著的量測陷阱。** 第一次探測用 SDK 原生 `doc.click()`，讀回來的狀態完全沒動
（`sourceSequence` 停在 5、caret 沒變、selection 還是搜尋留下的字串），我差點寫成
「click 之後幾何是 stale 的」。改用 demo 實際走的 `EditorSession.placeCaret` 就正常
（seq 5→6、collapsed 轉 true）。**兩者不是同一條路，探測要用產品實際呼叫的那條。**

逐項新鮮度（`sourceSequence`）：placeCaret 6、move-left 7／8（caret x 2331→2211）、
shift-right 12／16（選取 `"b"`→`"bc"`）、delete 12、段落換行 13、undo 14、set-bold 15
——**唯獨 `commitText` 當下不動**（停在 6）。追加輪詢後 51 ms 時前進到 7、x 2437→2784。
所以打字的 caret callback 只是晚幾十毫秒，不是不來。

實作：疊層 div 畫在 canvas 之上（游標閃爍不該讓引擎重繪），`px = twips / 15 × 縮放`。
每次操作後**有界等待 `sourceSequence` 前進**（上限 400 ms）——等的是可觀察訊號不是盲目
sleep；等不到就保留舊幾何並畫成虛線空心、狀態列寫「位置未確認」。打字不經過 `run()`
（輸入轉接器直接呼叫 `commitText`），所以另外掛在 `document-invalidated` 上做 debounce
補抓。

**自己的 bug，值得記。** 補抓一開始也有降級權，於是每個操作完成後 400 ms，那個已經
新鮮的游標會被補抓的「等不到第二次前進」判成未確認。修法是只有跟在真實操作後面的那次
呼叫能降級（`downgrade` 參數）。

驗證兩瀏覽器逐格相同：開檔 94.5px、點擊 259.4px、＋700 ms 仍 confirmed（確認補抓不再
降級）、Shift+→ ×3 出現 259.4px 起 24px 寬的選取塊且游標到 283.4px、打字覆蓋選取後選取
消失且游標落在替換後位置。Chromium 另測連打 A B C，游標 270.9→281.6→292.3px。

## SPEC E1-D 設計階段完成（2026-08-07）：閘門換掉了實作方法

使用者要求 demo 加上滑鼠拖曳反白。引擎已有範圍選取，但掛在
`editorDiscoverySelect` 之下、由 `editor-discovery-closed-actions` 把關，出貨的
`e1-editor-v1` 不宣告該能力——所以這是契約擴充，要重建。依規矩先跑最便宜的閘門，
在**已建好**的 `e1-editor-discovery` 上比較兩個候選方法，全程零重建。

**閘門擋下了原本要做的那條。** `mouse-drag`（合成 MOUSEDOWN→MOVE→UP）在全新 worker 的
第一次拖曳回報 `completed`＋`documented-callback-text-selection`，**選取讀回卻是
`none`**；輪詢一秒 40 次始終為空，不是落後。這就是 finding 022 的缺陷類別——回報成功而
什麼都沒發生。差別只在 022 來自快取，這裡是完成訊號打在 mouse-down 清除舊選取的
callback 上。**若照原計畫升格，等於把剛拔掉的缺陷原樣裝回去。**

`text-handles-unstable`（`setTextSelection(RESET)` ＋ `(END)`）在同一支 harness 全過：
全新 worker 第一次呼叫即正確，**8／8 獨立重複**、文字每次相同、2～3 ms；零長度與空白區
乾淨完成且不卡住 `gEditorPending`。所以要升格的是 API 路徑，不是合成滑鼠事件——前端本來
就握有起訖點，不需要引擎合成滑鼠事件再猜回來。

**契約形狀補測（Chrome 150 ＋ Firefox 153，仍零重建）**：跨三段的範圍成立（48 字元）；
`set-bold` 後存檔 `content.xml` 出現 `fo:font-weight="bold"` 套在正好那 12 個選取字元；
`replaceSelection` 後原字串消失、替換字串就位。**`delete-backward` 被 typed 拒絕**
（`EDITOR_STATE_UNAVAILABLE`，文件無損）——`startSelectionBarrierDelete` 要求 collapsed
caret，那是 finding 016 修法的前提，範圍刪除是另一種交易形狀。因此本規格只做選取，
範圍刪除另立里程碑。

規格 `specs/SPEC-E1-D-range-selection.md`，證據
`findings/evidence/e1-drag-select-gate/`。harness `make e1-drag-select-gate-assets`，
不相依任何 profile。**出貨物仍是 `97e605ee…`，尚未重建。**

一個自我更正記在這裡：我一度認為選到的字數與請求範圍不符，那是我用「行寬 ÷ 字數」估錯
（錨點矩形寬度不等於可見字形寬度），不是引擎的問題。

## SPEC E1-D 實作完成（2026-08-07）：第一版建置帶著閘門漏掉的缺陷

ABI 是 `oxsdk_editor_select_range`，方法在邊界寫死成 `setTextSelection` 路徑——
`mouse-drag` 傳不進來。worker 的 `editorSelectRangeV1` 由 `narrow-editor-v1` 把關並拒收
`method` 欄位。client 的 `selectRange()` 以選取讀回當後置條件。

**第一版建置有一個會卡死編輯器的缺陷。** 在空白處拉範圍、而游標本來就是收合的：什麼都
沒變 → 沒有 `LOK_CALLBACK_TEXT_SELECTION` → **逾時 60 秒**、session 進 recovery。對照
確認成因：從文字選取出發 9 ms 完成，從收合游標出發逾時。

**這是我自己的閘門漏掉的。** 規格 §2.3 的 `handles-empty-area` 就是測這個的那一格，它在
那次執行以 `search timed out` 夭折，我誠實記了「兩次 harness 失敗，保留不掩蓋」——然後
沒有重跑就往下走。我在 harness 註解裡親手寫過「安全那半比 happy path 更重要」，卻把唯一
測它的格子當雜訊放過。**記錄失敗不等於處理失敗。**

**修法是有界的選取讀回**（`EditorSelectReadbackDeadlineMs = 250`）：期限內沒有 callback
就在引擎迴圈醒來、讀回選取、以 `verified-selection-readback` 完成，回報實際存在的東西。
期限不宣告成功，它只是去看。只有產品的 range-select arm 這個期限，診斷 profile 維持純
callback 語意，findings 的量測基準不受影響。

修後：正常範圍 19 ms、零長度 2 ms、空白區 252 ms 回報「沒選到」不卡死、其後一切正常。
demo 拖曳實測單行一塊、跨三段四塊、空白區安全。

**artifact 換成 wasm `69d4333d…`、loader `ff9c9b43…`、worker `053adcf1…`。**
三處釘住的 hash 已更新（歷史紀錄欄位保留舊值不動）。靜態回歸 11 項全過，
`editor-client.test.mjs` 新增四個 selectRange 契約測試（讀回優先於回傳、選不到不是錯誤、
自相矛盾的讀回要拒絕、非法 twips 派送前就擋）。

**E1-C 人工 Chewing 證據隨重建失效**，裁決回到 `E1_PARTIAL_GO_ODT_EDITOR`，
matrix 的 `status` 已改成 `executed-manual-round-invalidated-by-e1-d-rebuild`。

## 真人測一輪，抓到兩個合成事件永遠看不到的缺陷（2026-08-07）

使用者指出我搞混了兩件事：要驗的是**今天做的滑鼠選取**，而我卻遞上 E1-C 人工輪的指引
——E1-C 凍結的六個案例是 IME、剪貼簿、存檔，**裡面根本沒有滑鼠選取**，重跑它一項也測不到
拖曳。那份只是重建造成的帳面工作。指正正確。

真人跑一輪後回報「整頁不能打字也不能 Backspace」，另附截圖顯示文件內容溢出紙張之外。
兩個都重現了，兩個都是我的自動測試在結構上不可能發現的：

**一、焦點被瀏覽器搶走。** 真的點一下畫布後 `document.activeElement` 是 `BODY`，按鍵
完全沒反應。原因是 `pointerdown` 沒有 `preventDefault()`，瀏覽器的預設焦點處理在我
`sink.focus()` **之後**執行，而 canvas 不可聚焦，焦點就落到 body。我的測試一直是直接對
sink 派送 `beforeinput`，**整段跳過焦點**，所以永遠是綠的。修法是 `preventDefault()`；
修後真鍵盤 X 與 Backspace 都生效（revision 0→1→2、`activeElement` 是 `sink`）。

**二、紙張被拉成視窗高度。** `.desk` 是 flex 容器、`align-items` 預設 `stretch`，所以
`.paper` 高度＝視窗而非內容。`r7-t2-styled` 是 1134×3443，畫布整個溢出白紙外，`inset:0`
的疊層也跟著只剩視窗高度、長文件下半的游標與反白會被裁掉。修法 `align-items: flex-start`
＋ `flex: none`（後者防止窄視窗把頁面壓扁而**悄悄改變疊層的 twips→px 比例**）。

順帶修了拖曳的健壯性：改用 pointer events ＋ `setPointerCapture`，並在 `pointermove`
檢查 `buttons`。在視窗外放開時 `mouseup` 收不到，舊寫法會讓 `drag.active` 永遠為真、
之後每次滑過畫布都送一次選取請求——那本身就足以讓鍵盤看起來像死了。

**一個我試了又拆掉的東西。** 截圖右側那塊灰是引擎畫的工作區：`r7-t2-styled` 回報寬
17004 twips，頁面只到約 12158（灰色實測為 `192,192,192`）。我一度加了「開檔時量一次白色
延伸到哪」的啟發式來裁切，但在應用內量到的 `lastWhite` 與獨立探針不一致（399 vs 285），
也就是同一份文件在**已先全尺寸繪製過**之後的小圖結果不同。與其為裝飾去追引擎的繪製語意，
我把啟發式整個拆掉，並移除自己畫的白紙底色——引擎本來就會把頁面畫白、周圍畫灰，
和桌面版 LibreOffice 一致。**那塊灰不是繪製故障，是文件回報區域比頁面寬。**
預設 fixture `plain-grapheme` 不會出現。

教訓延續前一節：合成事件測不出焦點、原生選字、pointer capture 這一類問題。**要驗輸入，
就得有一次真的手。**

## 組字框：看得見、跟著內容長、釘在游標上（2026-08-07）

**看不到注音與選字**：IME 的預編輯與候選字視窗是畫在 sink 那個 textarea 裡的，而它
`opacity: 0`。改成組字期間才現形（`.composing`），平時仍隱形。

**`compositionend data and host input buffer disagree`**：`HostInputAdapter` 在組字結束時
比對 `_target.value`，非空且不等於提交字就拒絕——那是 fail-closed 守衛，而**清空是宿主的
責任**（轉接器刻意不碰那個元素）。demo 從來沒清；中文提交後殘留，Backspace 又被
`preventDefault()` 而不會刪到 textarea 自身內容，於是下一次組字必定不一致。修法：
`compositionend` 與非組字的 `input` 之後各清一次，用 `queueMicrotask` 讓轉接器先讀到值
再清（我方監聽器註冊得比轉接器早，靠 microtask 保證順序）。

**尺寸**：textarea 的 `width: auto` 會退回 `cols` 寬度、`rows` 決定高度，所以框固定寬又多
半格空白，長預編輯被裁掉。改成 `rows=1 cols=1` ＋ 由**離屏鏡像元素**量文字寬度
（`scrollWidth` 量不到 textarea 的內容寬）。

第一版讓它換行，結果更糟：縮得太貼身，而**組字中的預編輯不一定會反映到
`textarea.value`**，量到空字串就退回最小寬度，`overflow: hidden` 再把注音裁成只剩第一個
符號——打 `ㄏㄠˇ` 只看得到 `ㄏ`。兩處修正：量的文字改取 `compositionupdate` 事件的
`data`；以及**使用者指出的正解——fcitx 的預編輯本來就是橫的一條，不要換行**。單行之後
高度問題自然消失。實測空框與 `ㄏㄠˇ` 都是 84×22、19 字 278×22、結束回到 2×19，
高度恆為一行。

**位置**：改成從**引擎回報的 caret 幾何**定位，而非最後一次 pointerdown。兩者剛點完時一致，
但游標用鍵盤移動後就分家——使用者回報過一次「框跑到畫面中間」無法重現，這個改動移除了
該成因。

真 IME 行為我無法自測（合成 CompositionEvent 只能驗版面計算），需要操作者確認。

## 補上驗證器的不對稱：重連結作廢的是全部證據，不只人工輪（2026-08-07）

使用者問「E1-C 人工證據再次失效」是什麼意思。解釋的過程裡查出一件更難看的事。

**機制。** `validate_e1_c.py` 的人工閘門一直有這項比對：證據檔裡**頁面自己記下的**
artifact hash，對上 `dist/profiles/e1-editor-v1/` 的現況。三項全不同就 `manual.pass = false`。
證據檔本身的 `pass` 仍是 `true`，存出的 ODT 也還是好的——斷的是綁定關係，不是內容。

| | 現場 profile | 人工證據記的 |
| --- | --- | --- |
| loader | `1fe83aed…` | `b9a29749…` |
| wasm | `835b453d…` | `97e605ee…` |
| worker | `e4f37ffe…` | `9696c9ce…` |

**不對稱。** `collect_cases()` 只看 `result.pass`，**從不**把自動相位的 hash 拿來比。實測 48 個
case 的證據全部記著 `97e605ee`、契約還是八個 action——和人工輪同一個舊 artifact。於是重連結
會依構造作廢人工輪，卻讓 48 個瀏覽器 case 靜靜存活，驗證器報出 `E1_PARTIAL_GO_ODT_EDITOR`。
而那個裁決的語意正是「機器相位描述的就是出貨物，只缺 trusted input」——當時並不成立。

先問了使用者要不要補，並事先講明代價：補完裁決會掉到 `E1_STOP_OR_RESCOPE`，自動相位也得重跑。
使用者同意。

**修法。** 新增 `artifact_binding()`：把每個自動 case 綁到現場 profile，作為 `decide()` 的第七個
自動要件；**沒有記錄 artifact 的證據同樣不綁定**（無從歸屬的通過不是比較弱的證明，是沒有證明）。
`manual_gate()` 改用同一個 hash 抽取 helper，讓「哪三個 hash 具約束力」只有一份定義。輸出寫到
`inventory/artifact-binding.json`，命令列摘要多印 `failedProperties` 與綁定計數——原本只印裁決，
看不出為什麼。

首次執行：`boundCases 0 / supersededCases 48 / unattributableCases 0`，
`failedProperties: ["evidenceArtifactBinding", "trustedManualDelta"]`，
裁決 `E1_PARTIAL_GO_ODT_EDITOR` → **`E1_STOP_OR_RESCOPE`**。
其餘六項屬性照舊通過，所以這不是新的編輯器缺陷，是同一筆重建成本被完整計入。

單元測試加了五項：綁定相符、任一 hash 過期即失敗、沒記 artifact 不算綁定、零個 case 不算通過，
以及 `decide()` 在綁定失敗時**必須是 STOP 而不是 PARTIAL**（PARTIAL 的語意會說謊）。
`tests/test_e1_c.py` 11 項全過。

**順帶修一筆帳。** `rebuiltForE1D` 與 `rebuiltForUnderlineStrikethrough` 兩格記著同一個 wasm hash
`835b453d`——兩次不同的連結不可能產生相同輸出。是我在為第二次重建掃「釘住的 hash」時把 E1-D 那格
一併覆蓋了。完整摘要已隨 artifact 消失，但本篇上一節記過 8 碼前綴（`69d4333d`／`ff9c9b43`／
`053adcf1`），寫回矩陣的 `artifactPrefixes`，完整欄位留 null 而不是留錯的值。

**回到 GO 要做什麼**：雙瀏覽器四個自動相位（`python3 tools/run_e1_c.py --browser <name>`）＋
各一輪人工 Chewing，全部對 `835b453d…`。

## 重跑自動相位撞到牆：finding 023，以及一句被我讀成「修好了」的紀錄（2026-08-07）

補完綁定閘門後重跑四個自動相位，**兩個瀏覽器都死在 lifecycle**：Chrome `cycle-06`、
Firefox `warmup-08`，`init timed out after 120000 ms`。**和 2026-08-06 同樣兩格。**

矩陣裡那次記的是「heavy host load from concurrent WASM linking」，並附了一句
「a clean re-run of the lifecycle phase passed every cycle」。這次主機是閒的。

### 探針：把 case 內容從變因裡拿掉

`tools/run_e1_c_session_depth.py` —— 同一個 session 裡**反覆導覽完全相同的一格**，
每輪印 elapsed 秒數與行程樹位元組。設計上刻意不做判定：`result.json` 沒有 `pass`，
只有 `observation`；跑乾淨與死在第 26 輪都是結果，不是「探針失敗」。

```
Firefox  1..25 每輪 2.26 秒（±0.01）  → 第 26 輪 120.33 秒逾時
Chrome   1..33 每輪 1.22 秒           → 第 34 輪 driver 層 180 秒沒等到 readyState
```

**平坦，然後懸崖。** 沒有任何漸進劣化，記憶體也平的（Chrome 穩定 1.5～1.6 GB，
主機 30 GiB 用了 8 GiB）。失敗那輪 `workers: created 1, terminated 0`、`operations: []`
—— worker 起得來，一個 SDK 事件都沒有。

我先預測「固定牆 22／30」，結果是 26／34，**預測錯了**。但重跑 Chrome 又是 34。
正確的說法是：**同一種工作量下深度固定且逐次重現，換工作量才會移動**，而且比較重的
工作比較早撞牆（正式矩陣每格含 100 頁壓力檔與崩潰情境，22／30；探針只跑最便宜那格，
26／34）。四次執行、兩種工作量，各自完全可重現 —— 這是確定性的累積預算，不是抖動。

### 判別階梯

同一個 `serve.py`、同樣 COOP/COEP、同樣的 navigate 迴圈，只抽換頁面內容：

| rung | 每次導覽做的事 | Firefox | Chrome |
| --- | --- | --- | --- |
| `inert` | 只設 driver 在等的兩個 global | 60/60 | 60/60 |
| `worker` | 建一個 module worker、答一句、終止 | 60/60 | 60/60 |
| `buffer` | 同上 ＋ 256 MiB `SharedArrayBuffer` | 60/60 | 60/60 |
| `full` | 真正的 E1-C 頁面 | **26 死** | **34 死** |

排除主機負載、瀏覽器與 driver 的分頁汰換、worker 汰換、隔離記憶體配置。**只有載入引擎
那層會卡。** cross-origin isolation 四個 rung 都成立，不是變因。

`buffer` 那格我差點交出一個假對照：探針原本只記 `operations` 的**數量**，看不出
`SharedArrayBuffer` 到底配置了沒。如果 `bufferMib` 沒傳對，這個 rung 會靜靜退化成
`worker`，而我會拿它當證據。補記 `lastOperation` 之後實測 `bufferBytes: 268435456`，
再重跑一次 60 輪才算數。**一個無法證明自己做了那件事的對照組，不是對照組。**

### 那句話是繞過去，不是修好

「單獨重跑 lifecycle 相位就全過」是真的 —— 但 lifecycle 單跑是 10 warmup ＋ 10 cycle
＝ **20 次導覽**，比觀察到的每一道牆（22／26／30／34）都低。**它從來沒有靠近過限制。**
我 2026-08-06 把這句讀成了佐證，實際上它是症狀。

### 這不只是 harness 的事

lifecycle 相位存在的理由，正是證明「反覆開檔存檔關檔」有界。使用者開著分頁工作一天，
會踩到同一件事：開到第二十幾份之後再也開不起來，沒有錯誤訊息，只有一個永遠不回來的
init。所以不能用「每 N 次換 session」了事 —— 那會讓驗收永遠測不到產品真正的處境。

寫成 [finding 023](findings/023-sdk-init-wedges-at-fixed-session-depth.md)，下一步在那裡：
先用不載入 core 的最小 wasm 模組跑同一階梯，切開「載入大 wasm」與「LibreOffice 初始化」。

### 補上階梯缺的一格，然後交接（2026-08-07）

寫交接文件前又查了一次連結參數，發現我的階梯有洞：`-sPTHREAD_POOL_SIZE=7`
＋ `-sTOTAL_MEMORY=1GB`（`Makefile:463-465`），所以真正一次導覽是
**1 個 SDK worker ＋ 7 個 pthread pool worker 共用 1 GiB 共享記憶體**。
我的對照組只有 **1 個 worker、256 MiB** —— 「worker 太多」與「共享記憶體太大」
根本還沒被排除，而我已經寫下「只有引擎那層會卡」。

補了 `pool` rung（8 個 worker 共用 1 GiB，每個都寫入，實測 `workers: 8`、
`bufferBytes: 1073741824`、`touched: 8`）：**兩瀏覽器 60/60 通過**。結論站得住了，
但這次是差一點就把一個沒做完的排除當成做完的。

交接文件 `HANDOFF-2026-08-07-finding-023.md`：卡點、已排除清單、已撤回的三句話、
init 呼叫鏈與行號、按成本排序的四個下一步、這個 repo 的規矩、四條探針紀律。

## finding 023 破案：牆不在瀏覽器也不在引擎，在我們自己的 pipe（2026-08-07，接手）

接手交接文件後把階梯往下切。過程照成本排序，每一步都把上一步的結論再砍掉一半：

1. **`wasmmem` rung**（worker 內配 1 GiB shared `WebAssembly.Memory`，對照已過的
   `pool`/SAB）：兩瀏覽器 60/60。wasm 記憶體記帳排除。
2. **`compile` rung**（fetch＋compile 真的 115 MB probe.wasm）：60/60。編譯空間排除。
3. **`minimal` rung**（交接的步驟 1：40 KB 模組、引擎同款連結參數）：Chrome 首輪
   60/60「通過」——**第二輪 120 迭代死在 62**。Firefox 55。零 LibreOffice 程式碼也
   撞牆，引擎排除。「60/60」原來只證明牆＞60。
4. **`realinstant`**（真模組實例化、不 engine_start）54、**`enginestart`**（真 init 鏈、
   不開文件）45 過——牆的位置跟頁面「每導覽幾個請求」成反比，跟做了什麼運算無關。
5. 這時才想起 runner 是 `Popen(serve.py, stderr=PIPE)` **而且從來沒人讀那條 pipe**。
   趁 full/chrome 正卡在第 34 輪時看 `/proc`：**`serve.py` handler 執行緒
   `wchan=anon_pipe_write`，chrome 全樹零阻塞**。幾分鐘後下一個 runner 的 server
   也被抓到同姿勢。`send_response()` 先 `log_request()` 再送狀態列——pipe 一滿，
   請求連狀態列都拿不到。存檔 `session-depth/pipe-forensics/`。
6. 修法：server 輸出改導 evidence 的 `serve.log`。**驗證輪：full/chrome 45/45、
   full/firefox 30/30、minimal/chrome 120/120，牆全部消失。**對帳：chrome 每導覽
   1902 B → 65536 穿過點第 35 次（原牆 34）；firefox 2431 B → 第 28 次（原牆 26）。

深度為什麼固定？請求序列固定 → log 位元組固定 → 累積穿過 64 KiB 的導覽序號固定。
重工作請求多 → 先撞（22/30 vs 26/34）。兩瀏覽器請求模式不同 → 牆不同。四次「逐次
重現」全是同一條 pipe 在數位元組。

**代價最大的教訓：對照組與實驗組共用的基礎設施本身是一個 rung。**判別階梯五個
rung 共用同一個帶 bug 的 server，而 rung 之間的差異恰好改變請求數——變因躲在
「中性」的共用層裡，把 harness bug 化裝成了「引擎那一層的問題」。

過程中順帶挖出兩個**真的**瀏覽器側問題（Firefox；與 pipe 無關、修復後仍在），
獨立成 [finding 024](findings/024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md)：
惰性回收已導覽離開頁面的引擎 worker（記憶體階梯 +0.9 GB/導覽、第 8 次實例化
abort）；worker 名額惰性釋放（`dom.workers.maxPerDomain=64` 時牆從 55 移到 9，
超額 `new Worker()` 靜默排隊）。產品的對策是 pagehide 時明確 `dispose()`。

E1-C 解封：023 修復後，四個自動相位可以重跑（正好與 §11.4 的 artifact 綁定重跑
同一趟）。probe 基礎設施同型 `Popen(PIPE)` 還有 8 個 runner 未掃，r7 longevity 的
歷史「偶發」值得重看，清單在 finding 023 的「善後」。

## finding 023 善後三件事全部收工；024 已在 Nightly 修復（2026-08-07 傍晚）

1. **E1-C 解封驗證**：修復後的 harness 重跑四個自動相位，chrome＋firefox 皆
   `pass: true`——lifecycle 首次在單一 session 內完整跑完。`validate_e1_c.py`：
   `automaticPass: true`、48 case 全綁 `835b453d…`（0 superseded）、裁決
   **`E1_PARTIAL_GO_ODT_EDITOR`**，唯一缺口是人工 Chewing 輪（需操作者）。
   矩陣 `execution.rerunAfterFinding023Fix` 已記；113 個測試全過。
2. **pipe 同型清掃**：全 tools 掃遍，共修 20 個 runner——16 個 serve.py 未讀
   pipe → DEVNULL；4 個 r8 runner（含 r8_discovery）改 `spawn_captured()`／
   `drain_captured()` 保留「輸出收進證據」語意。良性未改：`subprocess.run`、
   `communicate(timeout)` 即排空者、soffice（輸出遠低於 64 KiB）。
   **r7 longevity 歷史無需作廢**：它每 run 只導覽一兩次，pipe 牆碰不到；其
   firefox `s2-fresh` 敗在記憶體閘門（+34 MB/block）——形狀與 024 一致，列為
   旁證。
3. **finding 024 上游準備**：自包含重現 `findings/repro/024-firefox-worker-reclaim/`
   （40 KB pthread 模組＋自我重導覽頁＋stdlib-only `check.py`）。stock 153 實測
   worker 名額牆 **65**、pref=64 牆 **9**（driver 與無 driver 模式數字一致——
   後者以 serve.log 的 `?n=K` 序列判讀，先用 stock 驗證過才拿去測 nightly）。
   查重無現成票（最近緣 1052398／1286895／1592227／1576829）。
   **Nightly 155.0a1 已修**：default 1343、pref64 624、touch 286 全部無牆，
   每輪 pool 完整起動（證據 `session-depth/finding-024-nightly/`）。M2 記憶體
   路徑的極小化兩次嘗試皆負（SAB commit 與 JS-heap 壓艙物 FF 都回收得掉），
   @8 abort 需大模組編譯碼＋綁定的 1 GiB——誠實記錄，Mozilla 要重現得用真的
   大型 pthread 模組。送不送（uplift 請求）留給使用者。

  過程另拾兩個環境陷阱：snap 版 firefox 讀不到 /tmp 下的 profile（頁面靜默
  不載入——第一輪 stock driverless 因此全滅，profile 改放 $HOME 才對照成功）；
  geckodriver 0.37 拒認 Nightly 155 的 binary（「binary is not a Firefox
  executable」），Nightly 只能無 driver 驅動。

  **E1 下一步只剩一件：人工 Chewing 輪**（兩瀏覽器各一輪，對 `835b453d…`，
  `ssh -L 8765:127.0.0.1:8765`，SPEC E1-C §11.5）→ 裁決可望回 `E1_GO_ODT_EDITOR`。
