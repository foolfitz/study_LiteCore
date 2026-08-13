# 021 — WASM 段落格式 state 不隨 caret 移動更新，使 barrier 的前置條件讀到別段的值

| | |
|---|---|
| **狀態** | **已歸因到底：缺口在 PEI 語意（判別實驗一、二完成，兩瀏覽器）**；產品級主迴圈可跑、修法矩陣已在該組態重現（pump 仍為 unit-test 掛鉤）。（2026-08-06 曾記為「fail-closed 有未修補的安全洞」，二次覆核後**撤回**，見已觀察第三點之附；殘留的是逐欄位世代標記，屬推論。）產品路線已定為 **C：不讀前置狀態**（見「影響與目前決策」），不送上游 |
| **Bugzilla** | — |
| **發現日** | 2026-08-05 |
| **嚴重度** | 嚴重 |
| **可重現** | 100%（Chrome 150 與 Firefox 153 各 4 次逐數字相同；原生 4 種移動方法各 4/4 正常） |
| **是否上游** | **否**（我方 WASM harness／engine 迴圈；core 計算正確） |

## 現象

E2-A 的 verified-format-state barrier 用同一份 typed state 做兩件事：**派送前**判斷前置狀態
（`stateKnown` 決定是否 fail closed、`alreadyAtTarget` 決定是否回 `documented-state-noop`），
**派送後**判斷後置條件。

A2-wasm 實測顯示這兩個用途在 WASM 下的可靠度**完全不同**：

- **派送後可靠。** 五個格式命令派送後，state 的變化與存檔 ODT 內容逐項相符（5/5）。
- **派送前不可靠。** 純 caret 移動時 state 多半不更新。10 次定位讀取只有 2 次是新鮮的，
  其餘 8 次回報的是**上一個段落**留在快取裡的值。

具體後果：caret 實際位在 `<text:list>` 內的段落時，引擎從未回報過「在清單內」
（`listReadInsideList: false`），而是沿用前一段的 `listBullet:false, listNumber:false`。

這推翻 A2-native 的觀察「三個 state payload 在無 mutation 的純 caret 移動時就會更新」
（[SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 第 10.1 節）。

## 重現步驟

全部在 `wasm_sdk_probe/` 下執行。fixture 為 `test-docs/e1/styled-list.odt`，四個定位點分別落在
heading、一般段落、`<text:list>` 內的項目、清單後的段落。

### 原始症狀（狀態不追隨 caret）

```bash
make e2-format-discovery-assets
python3 tools/run_e2_discovery.py --browser chrome    # Firefox 同
```

看 `a2.tracking`：`freshPositions` 只有 `heading`、`body-paragraph`，`listReadInsideList` 為
`false` —— caret 實際在清單項內時，引擎從未回報「在清單內」。

**注意**：同一份 run 的五個派送現在會全部回 `EDITOR_FORMAT_STATE_UNAVAILABLE`，這是預期的。
本 profile 沒有 refresh 能力，加入 fail-closed 之後它只能示範問題，不能示範修法。
（修法前的 `45f2372b…` build 曾在此顯示 5/5 成立，見 SPEC E2-A 第 10.2 節。）

### 修法（fail-closed ＋ host 刷新）

```bash
make e2-scheduler-attribution-assets
python3 tools/run_e2_discovery.py --browser chrome --mode scheduler-attribution
```

五個派送全部 `verified-format-state`，`documentPostconditions.allMet` 為 true，
每個定位點的 `freshAfterDrain` 為 true。

### 原生對照

```bash
bash tools/run_e2_a_native_caret.sh
```

四種移動方法各自的 `tracksListMembership` 全部為 true。

### 候選 1（上游主迴圈，2026-08-06 起）

```bash
make e2-mainloop-attribution-assets
python3 tools/run_e2_discovery.py --browser chrome --mode mainloop-attribution   # Firefox 同
```

預期（sound 語意 build）：全命令流程可跑、`mainloopAttribution.lastPollCount` 數百起跳、
readback 對 caret 移動仍 stale、五個派送 5/5 `EDITOR_FORMAT_STATE_UNAVAILABLE`、檔案零變動。
瀏覽器 console 有 `oxsdk-mainloop:` 前綴的階段診斷（poll／dispatch／tick-alive／poll-pending）。

## 證據

- `evidence/sdk-e2/discovery/state-readback/wasm/chrome/attempt-05/result.json`（判準修正後）
- `evidence/sdk-e2/discovery/state-readback/wasm/chrome/attempt-06/result.json`（含 barrier 計數器）
- `evidence/sdk-e2/discovery/state-readback/wasm/firefox/attempt-02/result.json`
- `evidence/sdk-e2/discovery/state-readback/wasm/{chrome/attempt-07,firefox/attempt-03}/`（原始
  STATE_CHANGED 計數器）
- `evidence/021/native-caret-tracking/`（同 commit 原生四種移動方法）
- `evidence/021/scheduler-attribution/`（推排程前後對照、可用推進 API 量測、修法驗證，兩瀏覽器）
- `evidence/sdk-e2/discovery/state-readback/mainloop-attribution/`（候選 1：Chrome
  attempt-03 為迴圈機制示範〔過渡 build〕，chrome/attempt-04 與 firefox/ 為 sound 語意
  最終 build 的兩瀏覽器矩陣；含每步 `stateChangedDelta`、poll 計數器與 freshness 等待記錄）
- `evidence/sdk-e2/discovery/state-readback/mainloop-pei-attribution/`（判別實驗一，
  Chrome＋Firefox：活迴圈下 PEI 有效、修法矩陣重現）
- `evidence/sdk-e2/discovery/state-readback/mainloop-move-attribution/`（判別實驗二，
  Chrome：真 dispatch nudge 不觸發重算）
- 逐步存檔 `after-*.odt`（每次派送後即存，postcondition 由檔案判定）

兩瀏覽器的 `freshPositions` 與 `stalePositions` 完全相同：

```text
fresh : heading, body-paragraph          （只在第一輪 click 定位時）
stale : heading, body-paragraph, list-item, after-list  ×  其餘各輪
listReadInsideList : false
styleTracked       : false
```

定位方式對照（同一輪、同一份文件）：

| 定位方式 | caret／selection 事件 | format state 事件 |
|---|---|---|
| `setTextSelection(RESET)`（E1-A discovery 路徑） | 5～6 | **0**（四個位置皆是） |
| public `click()`（E1-B 產品路徑） | 5～9 | 前兩個位置 2／4，後兩個位置 **0** |

caret 確實移動了（每個位置都有 5 筆以上 caret／selection callback），但格式 state 沒有跟上。

## 分析

### 已觀察

- 三個 payload 在 WASM profile **確實會抵達**：`listBulletKnown`、`listNumberKnown`、
  `paragraphStyleKnown` 在兩瀏覽器皆為 true。A2-wasm 的主問題（濾鏡／callback 在不在）答案是「在」。
- 派送後的 state 與存檔 ODT 逐項相符，含「一個樣式三種字串」：送出 `Text body`、state 回
  `Body Text`、ODT 存 `Text_20_body`；heading 對應 `Heading 1`／`Heading_20_1`。
- `crosstalkCount` 與 `earlyStateCount` 在全部十次派送都是 0，即 result 先於 state 的順序在
  WASM 下也成立。
- 純 caret 移動時，`setTextSelection(RESET)` 在四個位置都沒有觸發任何 format state；
  `click()` 只在前兩個位置觸發。
- [Finding 020](020-lok-list-command-result-contradicts-document.md) 在 WASM 完整重現：
  `.uno:DefaultBullet` 回 `wasModified:false` 卻改了文件，`.uno:RemoveBullets` 回
  `success:false` 卻生效。兩瀏覽器一致。

### 已觀察（2026-08-05 追加的兩個歸因實驗）

**一、同 commit 原生對照：原生四種移動方法全部正常。**
證據：`evidence/021/native-caret-tracking/`（探針原始碼、完整 callback 串流、分析、SHA-256）。

| 移動方法 | 新鮮讀數 | 進出清單的兩個轉換是否都讀對 |
|---|---|---|
| `.uno:GoDown` 等游標命令（A2-native 原用） | 4/5 | 是 |
| `setTextSelection(RESET)` | 4/4 | 是 |
| `postMouseEvent` 點擊 | 4/4 | 是 |
| `.uno:ExecuteSearch` ＋ `setTextSelection`（WASM 逐字序列） | 4/4 | 是 |

原生在 `list-item` 位置每次都送出 1 筆 watched command 的 STATE_CHANGED 並正確回報「在清單內」。
唯一非新鮮的一步是清單項之間移動（值沒變，core 正確地不廣播）。**移動方法假設就此否證**：
WASM 失敗的那兩種方法在原生都成立。

**二、原始 callback 計數：core 在該位置根本沒送。**
在 E2 profile 加上兩個計數器（只計數，不轉發 payload）後，Chrome 與 Firefox 逐數字相同：

| 位置 | 定位方式 | 抵達的 STATE_CHANGED | 其中無法辨識 | 結果 |
|---|---|---|---|---|
| `list-item` | search | **0** | 0 | 沒有任何狀態抵達 |
| `after-list` | search | **0** | 0 | 同上 |
| `list-item` | click | 2 | **2** | 抵達的都是別的 slot |
| `after-list` | click | 2 | **2** | 同上 |
| `heading` | click | 26 | 24 | 有 2 筆 watched |
| `body-paragraph` | click | 158 | 154 | 有 4 筆 watched |

「無法辨識」等於「抵達總數」代表**沒有任何 watched command 的 payload 抵達**，因此排除
「core 有送、我方解析失敗」。

**三、分層歸因：推進 scheduler 後狀態立刻正確出現。**
證據：`evidence/021/scheduler-attribution/`（Chrome 與 Firefox）。

在隔離的 `e2-scheduler-attribution` profile（E2 組態＋Finding 016 的 scheduler drain）中，
每次定位後多做一步 `Scheduler::ProcessEventsToIdle()`（LOK 的 `unit_lok_process_events_to_idle`），
再讀一次狀態。兩瀏覽器逐項相同：

| 位置 | drain 前 | drain 後 | 原生對照 |
|---|---|---|---|
| `heading` | stale（前一段的值） | `inList=true` | `inList=true` |
| `body-paragraph` | stale | `inList=false` | `inList=false` |
| `list-item` | stale | **`inList=true`** | `inList=true` |
| `after-list` | stale | `inList=false` | `inList=false` |

`search` 定位的四個位置在 drain 前**全部**不新鮮、drain 後**全部**新鮮，且值與原生完全一致。
四次 drain 分別釋放 25、157、6、5 筆 STATE_CHANGED，其中 2、4、2、1 筆是 watched payload ——
先前「零抵達」的位置，一旦推排程就有 payload。

（Finding 016 的 drain 自身 `delta.stateChangedCount` 回報 0，是該舊探針的侷限：它在 drain 呼叫內
同步取樣，而 callback 在 drain 返回後才送達。本輪新增的 `stateChangedTotal` 才量得到真實增量。）

**四、哪個推進 API 可用（2026-08-05 實測）。**
上游在 `__EMSCRIPTEN__` 下由 `SvpSalInstance` 建構子**無條件**設定 `m_bUseSystemLoop = true`
（`vcl/headless/svpinst.cxx:103`），唯一的推進來源是 `Application::Execute()` 經
`SvpSalInstance::DoExecute` 安裝的 `emscripten_set_main_loop_arg`（同檔 :315，100 fps）。
我方探針從不呼叫 `Application::Execute()`，所以那個迴圈不存在。

在該模式下 `Application::Reschedule()` 會**直接回傳 false 且什麼都不做**
（`vcl/source/app/svapp.cxx:400-406`），`Application::Yield()` 會 `abort()`。
`Scheduler::ProcessEventsToIdle()` 之所以有效，是因為它直接呼叫 `InnerYield`、**繞過**該閘門。

在 profile 內實測（Chrome，四個位置皆同）：

| 量測 | 值 |
|---|---|
| `Application::IsUseSystemEventLoop()` | `true` |
| `Application::Reschedule(true)` 回傳 | `false`（零事件） |
| drain 呼叫內的 STATE_CHANGED 增量 | 0 |
| drain 返回後的 STATE_CHANGED 增量 | 25／157／6／5 |

兩個直接後果：**公開的 `Application::Reschedule` 不能當修法**（它在此組態是保證的 no-op，
會靜默失效）；而且**「推完就同步讀」也不行** —— callback 是在 pump 返回後才 flush 的。

**五、修法在 discovery profile 驗證通過。**
engine 端改為：caret 移動即標記 `formatStateStale`，watched payload 抵達或完成一次 pump 才清除；
前置條件為 stale 時回 `EDITOR_FORMAT_STATE_UNAVAILABLE`、零 mutation。refresh 由 **host** 驅動
（先 pump、再等 flush 穩定，才下動作），engine 不做任何 sleep —— 沿用 E1-B 在 click 之後以
host 有界輪詢等待 typed state 的既有慣例。

| 情境 | 五個格式動作 | 存檔 postcondition |
|---|---|---|
| 不做 host refresh | 5/5 `EDITOR_FORMAT_STATE_UNAVAILABLE`，零 mutation | 文件未變 |
| 有 host refresh | 5/5 `verified-format-state`、revision 各 +1 | **5/5 相符** |

Chrome 150 與 Firefox 153 一致。靜默 no-op 的路徑因此關閉：狀態不新鮮時是 typed 拒絕，
不是拿別段的值回答。

### 已觀察（2026-08-06 候選 1 實作與實測）

候選 1（跑上游的 emscripten 主迴圈）已在隔離 profile `e2-mainloop-attribution`
（`OXSDK_MAINLOOP_ENGINE`）實作並在兩瀏覽器實測。結論分兩半：**主迴圈機制成立，
但它不自動帶來 caret 移動後的狀態新鮮度**——後者的成因比「沒推排程」更深。

**一、可行的機制鏈（全部已實測）：**

1. `SAL_LOK_OPTIONS=unipoll`（engine 於 hook 前 setenv；COOL kit 同做法，
   `cool kit/SetupKitEnvironment.hpp`）。不設的話 `lo_initialize` 會自己 spawn
   `lo_startmain` 執行緒跑一條 soffice_main（`desktop/source/lib/init.cxx:8381`），
   之後任何 host 側的主迴圈嘗試都會與它相撞——**所有既往 WASM profile 其實都帶著
   這條隱藏執行緒**，見下面第三點。
2. `runLoop`（LOK 公開 API）在本平台只貢獻 poll/wake callback 註冊與
   `SfxLokHelper::registerViewCallbacks`：它內部的 `soffice_main` 因
   `ImplSVMain` 的 `IsVCLInit()` 早退（`vcl/source/app/svmain.cxx`）而立即返回
   ——unipoll 模式下 InitVCL 已在 hook 內做過（`init.cxx:8386`）。實測
   `runLoop-returned` 即刻出現。
3. 迴圈本體由 engine 直呼 `Application::Execute()` 進入（out-of-tree 以宣告
   綁定符號，同 finding 016 的技巧）：`DoExecute` 裝上
   `emscripten_set_main_loop_arg(loop, .., 100, 1)`（`vcl/headless/svpinst.cxx:315`），
   `throw 'unwind'` 只展開 engine 自有的框架（無上游解構子/catch 風險），
   emsdk 4.0.10 的 pthread 進入點捕捉 'unwind' 後讓 worker 存活
   （`runtime_pthread.js`），tick 與 engine 註冊的 `emscripten_set_interval`
   探針（tick-alive）全程並行。
4. 命令派送搬進 unipoll poll callback；`submit()` 通知的 cv 改由 poll 內
   有界等待。**陷阱：`runLoop` 的 `pData` 不得為 null**——
   `SvpSalInstance::ImplYield` 只在 `mpPollClosure` 非空時才呼叫 poll callback，
   null 會靜默停用整個 unipoll（這吃掉了一輪歸因）。

在此機制下，開檔（0.8 秒）、render、search、click、set-bold 對照、五個格式派送、
逐步存檔、close，全流程在 Chrome 150 與 Firefox 153 都正常；poll/idle-poll 計數
（~810/~739，兩瀏覽器幾乎相同）證明迴圈全程在跑。**產品層推排程機制的候選從
「未定」變成「有一個已實測可跑的形態」。**

**二、但「迴圈會讓 caret 移動後的狀態及時且對位地變新鮮」被否證。**

> **2026-08-06 覆核修訂。** 本節初版寫「狀態重算根本沒有被排進 scheduler」，
> 引用的是 Chrome attempt-03（過渡 build `681b8a1d`）的 `stateChangedDelta=0`。
> **對最終 sound build（`a696f0d6`）的證據為假**，已改寫如下。這是本輪自己
> 訂下的紀律（「hash 要對得上該輪 evidence」）沒有套用到自己身上。

最終 sound build 的 search readback（`stateChangedDelta`／其中無法辨識）：

| 位置 | Chrome attempt-04 | Firefox | 讀到的值 |
|---|---|---|---|
| `heading` | 1／1（0 筆 watched） | 1／1 | 未知 |
| `body-paragraph` | 2／2（0 筆） | 2／2 | `bullet=F, number=T` ← **heading 的值** |
| `list-item` | 15／15（0 筆） | 52／50（**2 筆 watched**，fresh） | `F, F` ← **body 的值** |
| `after-list` | 5／4（**1 筆 watched**，fresh） | 5／4（1 筆，fresh） | `bullet=T` ← **list-item 的值** |

即：watched payload 在活迴圈下**會抵達，但落後一格**——每個位置讀到的是前一個
位置的值，且抵達時間晚到本位置的 settle 視窗才被算進來。所以這不是「重算從未
被排程」，是**收斂／順序問題**：穩定跳動的迴圈永遠追不上，而 PEI 的「迴圈到
靜止」會。（Chrome attempt-04 的 `list-item` 15 筆全不可辨識、Firefox 同位置
52 筆中有 2 筆 watched，兩瀏覽器在這一格不同——屬時序不確定性，未進一步歸因。）

click 首兩個位置的爆量（26／158）與舊 blocking profile 數字一字不差，判為
`initializeForRendering` → `doc_iniUnoCommands` 註冊後的初始 binding flush，
而非逐移重查——只在前兩次 click 出現、之後衰減成 2 筆不可辨識。

**這推翻本 finding 先前機制敘述的一半**：「推排程後狀態立刻正確出現」在舊組態
成立，但**舊組態的 `ProcessEventsToIdle` 所做的不只是推一次排程**。差異的候選
（當時未驗證，已由判別實驗一、二裁決，見下節）。

**二之附：`GetMostUrgentTaskPriority=-1` 這個量測無效，已撤回。** 探針只在
`timeoutUs != 0` 取樣，而該條件蘊含 `ImplYield` 裡 `CheckTimeout()` 回 false
（sal 計時器未到期）；`Scheduler::GetMostUrgentTaskPriority()` 在
`nTime < mnTimerStart + mnTimerPeriod - 1` 就直接回 -1（`vcl/source/app/scheduler.cxx`
的第二道 guard），計時器未啟動時則由第一道 guard 回 -1。兩個條件是同一件事，
**該取樣點只可能印 -1，與有沒有任務被排無關**。本 finding 先前四處引用它作為
「連 ready 任務都沒有」的證據，全部撤回。探針本身若要再用，取樣點必須移到
`ImplYield` 之外（例如命令派送前後），否則它永遠只會印同一個數字。

**三、修法第一版的「idle-poll 即清 stale」不健全，已回退。** 該版以「到達
idle poll ⇒ core 已重算」清除 stale 旗標；第二點證明前提為假（到達 idle 時對位的
payload 可能還在路上），清除會讓前置條件拿**別段**的快取作答——正是本 finding
禁止的靜默 no-op 路徑。當輪（Chrome attempt-03）五個派送 5/5 成立且存檔相符，
但那依賴「五個派送都落在同一段落」，只能當**迴圈機制的示範**，不能當修法驗證。
回退後（sound 語意，只有 watched payload 抵達才清 stale）兩瀏覽器的矩陣為：

| 情境 | 五個格式動作 | 存檔 |
|---|---|---|
| mainloop profile，host 有界等待新鮮（5 秒逾時） | 5/5 `EDITOR_FORMAT_STATE_UNAVAILABLE`，零 mutation | 逐項檢查未變 |

**三之附（2026-08-06 二次覆核後改寫，原文為誤）。** 本節先前宣稱「落後一格的
payload 會清掉 stale 旗標，fail-closed 被繞過，未解且阻擋 A3」。**該宣稱不成立，
已撤回。** 撤回依據（兩者皆為原始碼與同一批 evidence，非新實驗）：

1. 上表的 `fresh` 是 **harness 的欄位**，定義為
   `entry.formatStateEventsObserved > 0`（`web/e2-format-discovery-app.js:268`），
   而計數起點在**定位動作之前**（同檔 :242）。所以它把定位本身（`.uno:ExecuteSearch`）
   引發的廣播也算進來，之後 caret callback 再把旗標重設為 stale。它量的是
   「這一步之內有沒有發生過事件」，不是「快取是否描述當前段落」。
2. engine 端的 `formatStateStale` 才是權威訊號，而它在**兩瀏覽器全部 search 列
   都是 `true`**（Chrome attempt-04 與 Firefox 的 `format.formatStale`）。也就是說
   保留下來的舊值**被正確地標成不新鮮**，不變式沒有被繞過。
3. 機制上也不可能：`updateEditorFormatState` 是先 `formatStateStale = false`
   才 `emitEditorStateEvent("format-state")`。真正的 watched payload 一定同時
   清旗標並產生事件，不存在「事件到了但旗標還是 stale」的 payload；觀測到的
   `fresh=true` 與 `engineStale=true` 併存，來源是第 1 點的計數窗，不是落後的 payload。

**真正殘留的缺口是另一個，而且比原本寫的窄**：`formatStateStale` 是**一個旗標守著
五個欄位**。任何一筆 watched payload（例如 `.uno:Bold`）都會清掉它，之後
`set-list-unordered` 讀 `listBullet` 時，該欄位可能從未為這一段重新廣播過。正確
形態是**逐欄位的世代標記**，而非單一旗標。此缺口目前是**推論，未觀測到實例**，
不得當成已發生的事故；驗證方式是在同一定位點只讓 bold 廣播、再讀清單前置條件。

（原文的錯誤來源：把 harness 的 `fresh` 當成 engine 的新鮮度判準。這正是本 finding
反覆強調的同一類錯——先確認量測通道量的是什麼，再解讀它。）

**四、對既往敘述的修正。** 「我方探針從不呼叫 `Application::Execute()`，所以
那個迴圈不存在」不準確：非 unipoll 建置裡上游的 `lo_startmain` 有跑
`soffice_main` → `Desktop::Main` → `Execute`（hook_2 的 `WaitForReady` 就是在等
它），主迴圈曾被安裝過；它的 tick 為何從未推動我方 scheduler（unwind 穿越上游
框架後 tick 死亡?）是獨立的未驗證子問題。成立不變的是：**在我方 engine 迴圈
的執行緒上**，兩個操作之間確實沒有任何東西推進 scheduler。

### 已觀察（2026-08-06 判別實驗一與二）

「目前的卡點與下一步實驗」列的兩個判別實驗已跑完（實驗一 Chrome＋Firefox 逐項相同，
實驗二 Chrome），裁決乾淨：

**實驗一：PEI 在活迴圈組態下有效——差異在 PEI 語意，不在 `Desktop::Main` 初始化。**
複合 profile `e2-mainloop-pei-attribution`（`OXSDK_MAINLOOP_ENGINE`＋scheduler drain；
兩個 `class Application` 宣告已合併，016 區塊內用巢狀 `#ifdef` 保持既有組態的前處理
輸出不變；poll callback 加重入護欄，巢狀 `ImplYield` 不會巢狀派送命令）：

| 位置（search 定位） | drain 前 bullet | drain 後 bullet | freshAfterDrain |
|---|---|---|---|
| `heading` | 未知 | false | true |
| `body-paragraph` | false | false（style 補齊） | true |
| `list-item` | false（別段快取） | **true** | true |
| `after-list` | true（別段快取） | **false** | true |

五個派送全部 `verified-format-state`、存檔 postcondition **5/5 相符**（兩瀏覽器）——
修法完整矩陣（fail-closed ＋ host 每次定位後 pump）在主迴圈 profile 重現。也就是說：
需要的工作一直都在，活迴圈的每 tick 收斂不到 PEI 的「迴圈到靜止」所到達的狀態，
使對位的 payload 一直落後一格（見上一節第二點）。

**兩者確切差了兩個參數，不是一個。** `loop()` 呼叫的是
`ImplYield(comphelper::LibreOfficeKit::isActive(), false)`（`vcl/headless/svpinst.cxx:303-305`，
LOK 下 `bWait=true`），PEI 呼叫的是 `InnerYield(false, true)` →
`ImplYield(bWait=false, bHandleAllCurrentEvents=true)`（`vcl/source/app/svapp.cxx:441-455`）。
**`bWait` 與 `bHandleAllCurrentEvents` 都不同**，加上 PEI 外層的 `while` 迴圈到靜止，
共三個候選因素未隔離。

**有機制的解釋（讀碼，未實驗）**：`ImplYield` 開頭是
`bWasEvent = DispatchUserEvents(bHandleAllCurrentEvents); if (!bHandleAllCurrentEvents && bWasEvent) return true;`，
而下一行的上游註解自己寫著 `CheckTimeout() invokes the sal timer, which invokes the
scheduler`。也就是說在 `bHandleAllCurrentEvents=false` 下，**每一個派掉了 user event
的 tick 都會在 scheduler 被叫到之前返回**——狀態重算要等到某個「沒有 user event」
的 tick 才輪得到，落後一格與此一致。這讓「`loop()` 改傳 `true`」從經驗性提議變成
有機制解釋的提議，但仍需實驗確認（改哪一個參數才是必要條件）。

**實驗二：真 dispatch 的 caret 移動也不足以讓狀態對位——invalidation 缺口不是
API 定位路徑特有。** 在 `e2-mainloop-attribution` 上，每次 API 定位後加派一個真游標
命令（`move-character-left`，完整 SfxDispatch 路徑，engine 現有 closed action）：
nudge 全部派送成功，`stateChangedTotal` 每個位置 +2 而 unrecognised 同樣 +2（**有
廣播，但沒有一筆是 watched**），`list-item` 依然讀不到「在清單內」，五個派送全數
typed 拒絕、檔案零變動。

**綜合裁決**：freshness 需要的是「caret 移動後把 scheduler 跑到靜止的一次脈衝」；
穩定跳動的主迴圈與任何單發 dispatch 都不能替代它。產品缺口收斂成一句可向上游提的話：
**unipoll＋system-loop（emscripten）組態下，svp `loop()` 的每 tick
`ImplYield(isActive(), false)` 收斂不到 `Scheduler::ProcessEventsToIdle()` 所到達的
狀態，caret 移動後 watched command 的 STATE_CHANGED 要嘛不抵達、要嘛落後一個定位點，
使 LOK host 讀到的段落格式狀態屬於前一段；LOK host 需要一個受支援的等價物**
（例如 `loop()` 改傳 `bHandleAllCurrentEvents=true`、或把 process-to-idle 升格為
受支援入口）。

### 推論

- **core 計算是正確的；問題在我方 engine 迴圈從不推進 VCL scheduler。** LOK 的 status update 是
  idle job，要靠 scheduler 跑到 idle 才會重算並廣播。原生 LOK 由 `soffice_main` 的 VCL 主迴圈推動；
  我方探針是核外連結、自帶 `main()` 與命令迴圈，兩個操作之間沒有任何東西推進 scheduler。
  派送命令之所以有狀態，是因為那條路徑在命令執行中同步廣播，不需要 idle job。
- 因此**不是上游問題**，也不是 Emscripten 特定的 core 缺陷。先前列為上游候選是基於「原生／WASM
  行為不同」，但那個差異的原因在我方這一層，不在 core。
- 這與 [016](016-lok-forward-delete-completion-gap.md) 的 scheduler 實驗不矛盾：那一輪問的是
  delete 的 completion callback，drain 沒有幫助，因而否證了主迴圈缺口**對該問題**的解釋。
  本輪問的是 idle 驅動的 status update，drain 直接解決。同一個機制、不同的相依。
- 因此 `alreadyAtTarget` 有機會用**別的段落**的狀態判定「已經是目標狀態」，回一個
  `documented-state-noop`、`changed:false`，而該段落其實從未進入該狀態，且什麼都沒發生。
  這是靜默 no-op，與 SPEC E2-000 第 10 節「no-op 與遺失不可區分」的停止條件同類。
- 本輪五次派送都落在同一段落並依序進行，所以沒有踩到；A3 的三態循環要跨段落，會踩到。
- `click` 在前兩個位置有大量狀態流量（26／158 筆）而後兩個位置幾乎沒有，與「status update 在
  初始化時被推動過一次，之後負責重算的 idle 週期沒有在跑」一致。

### 待驗證

- **產品層面該用什麼推排程的機制，仍未決定。** discovery 用的是
  `unit_lok_process_events_to_idle()`，上游註解明寫「used by unit tests that test only via the
  LOK API」，**不得**升格為產品機制。已知**不可行**的替代是 `Application::Reschedule()`（實測在此
  組態回 false）。剩下的候選：
  1. 依上游設計實際跑 `Application::Execute()` 的 emscripten 主迴圈。但
     `emscripten_set_main_loop_arg(..., simulateInfiniteLoop=1)` 會拋 JS 例外展開堆疊且不返回
     （`O3TL_UNREACHABLE`），與本 SDK 由 Worker 送命令、engine 自帶命令迴圈的架構衝突，屬重構。
  2. 向上游要一個受支援的「請求狀態刷新」原語。目前 `doc_iniUnoCommands()` 只註冊 slot，
     core 仍是值改變才廣播，沒有強制重新廣播的公開入口。
- 在操作邊界推進是否有再進入或 teardown 副作用未驗證
  （[finding 012](012-r6-styled-document-close-timeout.md) 的 document destroy 阻塞屬相鄰風險）。
- 推進若進入共用路徑會改變所有既有 release 的行為，R6～E1 全部要回歸；目前只在隔離的
  attribution profile 內，未影響任何 release。
- heading 位置讀到 `listNumber:true`（原生與 WASM 皆是）。原生同時回報 `style='Heading 1'`，
  與 outline numbering 一致，但未專門驗證，不得當作已知行為。
- 此機制是否也能解釋 [018](018-lok-line-navigation-completion-nondeterministic.md) 的 line
  navigation completion 不確定性。未驗證，但值得在 E2-A 收尾時一併重評。

## 影響與目前決策

- **修法方向已驗證可行，但只在 discovery profile 內**：engine fail-closed ＋ host 驅動刷新。
  沒有刷新時是 typed 拒絕與零 mutation，有刷新時五個動作全部成立且存檔證實。這關閉了靜默 no-op。
- **產品級迴圈機制已有實測可跑的候選**（2026-08-06）：unipoll ＋ `runLoop` 註冊 ＋
  `Application::Execute()`，命令派送搬進 poll callback，全流程兩瀏覽器通過。但它**不能取代
  refresh**：活迴圈下對位的 watched payload 落後一個定位點（見 2026-08-06 已觀察第二點），
  freshness 仍只有 PEI 做得到，而那是 unit-test 掛鉤，所以修法整體仍不可進產品。
- ~~**fail-closed 目前的實作不完備**：落後一格的 payload 會清掉 stale 旗標~~
  **（2026-08-06 二次覆核撤回，見已觀察第三點之附。）** engine 的 `formatStateStale`
  在全部 search 列都正確為 `true`；被誤讀的是 harness 的 `fresh` 欄位。殘留的是
  **逐欄位世代標記**（一個旗標守五個欄位），屬推論、未觀測到實例。
- A2-wasm 的**主要問題通過**（三個 payload 抵達、派送後 state 可信、postcondition 由檔案獨立
  證實）；但本 finding 使 barrier 的**前置條件**部分不可直接進 A3。
- barrier 的後置條件設計不受影響，`crosstalk`／`early` 計數器有效。
- 歸因完成後，修法方向從「繞開不可靠的狀態」變成「**讓狀態可靠**」：在讀前置狀態之前推進一次
  scheduler，使 `stateKnown`／`alreadyAtTarget` 讀到的是這一段的值。這比原先設想的兩個候選都乾淨，
  因為它修的是成因而不是症狀。
- **產品路線已定：C（不讀前置狀態）**，2026-08-06 決定，使用者已確認不送上游。理由：
  五個 closed action 本來就是明確動作而非 toggle，前置狀態只服務 fail-closed 與
  `documented-state-noop`，而後者本 finding 明文不得當成已驗證能力；barrier 壞的是
  前置那一半，**後置那一半（派送後 state 與存檔 ODT 相符 5/5）完全可信**，C 保留可信的
  一半。A（產品自行呼叫 pump）**延後而非否決**——若日後需要工具列即時狀態指示再回來，
  屆時先量 pump 實際耗時。
- **A3 仍不啟動**：待 E2-A 依 C 重新定義前置條件契約後再評。在此之前不得放寬 fail-closed。
- 不因為「本輪沒踩到」就把 `documented-state-noop` 當成已驗證能力。
- 這條線同時是既有 release 的潛在共通議題：任何依賴 idle 驅動 LOK 廣播的能力，在目前的 engine
  迴圈下都拿不到。E2-A 收尾時應一併重評
  [018](018-lok-line-navigation-completion-nondeterministic.md)。

## 卡在哪裡（給接手的人）

一句話：**技術面已經沒有未知數了——缺口是每 tick 的 `ImplYield(isActive(), false)`
收斂不到 `ProcessEventsToIdle()` 所到達的狀態；修法（pump 一次再讀）兩瀏覽器 5/5
驗證過。剩下的是產品決定，而決定已經下了：走 C——產品不讀前置狀態，因此不需要
pump，本 finding 對產品線就此關閉。** 未結的只有 discovery 側與一個待驗證的暴露面
（見「還缺什麼才能關閉」）。

**這裡不需要上游。**（2026-08-06 修正）先前寫「沒有受支援的刷新入口，只能等上游」
是錯的：`Scheduler::ProcessEventsToIdle()` 是 `include/vcl/scheduler.hxx:65` 的公開
API，類別為 `class VCL_DLLPUBLIC Scheduler final`，且有產品呼叫者
（`sw/source/uibase/dbui/dbmgr.cxx:1375`、`sw/source/ui/dbui/mmresultdialogs.cxx:712`、
`vcl/source/app/svmain.cxx:438`）。被標成 unit-test 的只有 `svapp.cxx:485-491` 那個
C 包裝（內容三行：取 SolarMutex ＋ 呼叫它）。「不得用 unit-test 掛鉤」這條規矩
仍然有效，但滿足它只要直接呼叫公開 API。真正的限制是 header 自己的警告
`This can busy-lock, if some task or system event always generates new events`——
那是我方要設界限的事，不是要等別人。

> ⚠️ 另一個要記住的風險：該 API 的 doc comment 寫「Internally it just calls
> `Application::Reschedule(true)`」是**過時的**，實作實際走 `InnerYield(false, true)`，
> 正因為繞過 `Reschedule` 的閘門才有效。若日後啟用 A，依賴的是實作而非文件承諾。

接手順序建議：先讀本節與「已觀察（2026-08-06 判別實驗一與二）」，再讀
[DEVLOG 2026-08-06](../devlog/DEVLOG-2026-08-06-wasm-sdk-e2-mainloop.md)。

> **接手前必讀（2026-08-06 兩次覆核）。** 本 finding 的 2026-08-06 章節初版有三處
> 錯誤，已在原地修訂並標示：(1) 「重算根本沒被排進 scheduler」對最終 build 的證據
> 為假——raw STATE_CHANGED 實測 15／52／5 筆，正確描述是收斂／順序問題；(2)
> `GetMostUrgentTaskPriority=-1` 的量測在該取樣點是結構性必然、零資訊，已撤回；
> (3) `loop()` 與 PEI 差兩個參數而非一個。第一輪覆核據此加寫的「落後一格的 payload
> 會清掉 stale 旗標」**在第二輪覆核被撤回**（已觀察第三點之附）——那是把 harness 的
> `fresh` 欄位誤當 engine 判準。若你讀到本檔任何其他地方仍寫著「零抵達／從未排程／
> 永不抵達」或「fail-closed 有安全洞」，以本段為準。

### 已排除，不要再試

| 做法 | 為什麼不行 | 依據 |
|---|---|---|
| `Application::Reschedule(true)` | 此組態下**保證 no-op**，直接回 false。用它修等於靜默失效 | `vcl/source/app/svapp.cxx:400-406`；已實測回 false |
| `Application::Yield()` | 同組態下直接 `abort()` | `vcl/source/app/svapp.cxx:494-503` |
| `unit_lok_process_events_to_idle()` | 有效，但上游註解明寫是 unit-test 掛鉤，不得作為產品機制。**但這不等於沒有入口**——它包的 `Scheduler::ProcessEventsToIdle()` 本身是公開 API（見「卡在哪裡」） | `vcl/source/app/svapp.cxx:485-492` |
| pump 之後同步讀狀態 | callback 在 pump **返回後**才 flush，同步讀仍是舊值 | 本 finding「已觀察」第四點 |
| engine 端等 watched payload 才繼續 | core 只在**值改變**時廣播，值沒變就永遠等不到；第一版實作因此逾時 | 本 finding 時間軸 2026-08-05 第三條 |
| 期望 `runLoop` 在本平台自己跑迴圈 | 其內部 `soffice_main` 因 `IsVCLInit()` 早退**立即返回**；迴圈要另呼 `Application::Execute()` | `vcl/source/app/svmain.cxx`；已實測 `runLoop-returned` |
| `runLoop` 的 `pData` 傳 null | `ImplYield` 只在 `mpPollClosure` 非空時呼叫 poll callback，null 靜默停用 unipoll | `vcl/headless/svpinst.cxx` unipoll 分支；已實測 |
| 「idle-poll 即清 stale」 | 到達 idle 不代表對位的 payload 已到——實測落後一格，清了會拿別段快取作答 | 2026-08-06 已觀察第二、三點 |
| ~~只憑「watched payload 有沒有到」清 stale~~ | **本列已撤回**（2026-08-06 二次覆核）。engine 端旗標在全部 search 列都正確為 stale；被誤讀的是 harness 的 `fresh` 欄位 | 已觀察第三點之附 |
| 用 harness 的 `fresh`（`formatStateEventsObserved > 0`）判斷快取是否描述當前段落 | 計數起點在定位動作**之前**，會把定位本身引發的廣播算進來；權威訊號是 engine 的 `formatStateStale` | `web/e2-format-discovery-app.js:242,268` |
| 在 `ImplYield` 的 poll callback 內取樣 `GetMostUrgentTaskPriority()` | 取樣條件與該函式的 early-return 條件等價，只可能回 -1，零資訊 | 2026-08-06 已觀察第二點之附 |
| engine pthread 的 stderr 當診斷通道 | 該 worker 的 stderr 到不了可捕捉的 console；診斷要走 `MAIN_THREAD_EM_ASM` | 2026-08-06 實測 |

根因（pump 面）是 `vcl/headless/svpinst.cxx:103`：`__EMSCRIPTEN__` 下無條件
`m_bUseSystemLoop = true`，唯一推進來源是 `Application::Execute()` 裝上的
`emscripten_set_main_loop_arg`（同檔 :315）。**這一面已解**：候選 1 的機制鏈
（`SAL_LOK_OPTIONS=unipoll` → hook → `runLoop` 註冊 → `Application::Execute()`）
在兩瀏覽器實測可跑，見 2026-08-06 已觀察。

### 判別實驗結果與剩下的路（2026-08-06 更新）

原列的三個判別方向已全部執行（結果詳見「已觀察（2026-08-06 判別實驗一與二）」）：

1. ~~Desktop::Main 初始化差異~~——**否**。複合 profile 在活迴圈組態下 PEI 照常放出
   watched payload 且值正確，兩瀏覽器一致。
2. **PEI「迴圈到靜止」vs 每 tick 一件的語意差——是，這就是缺口。**
3. ~~真實輸入路徑 vs API 定位路徑~~——**否**。真游標 dispatch（nudge）不觸發重算。

剩下的路（2026-08-06 依產品路線 C 重排。**上游報告已從路線上移出，改為暫緩**：
使用者決定先不送，素材另行整理為獨立草稿，待整組實驗結束後評估）：

1. ~~**驗證 E1 release 的暴露面**~~ —— **已做，已踩到，另立
   [finding 022](022-e1-release-set-bold-false-noop.md)**（Chrome＋Firefox 重現，
   凍結 artifact 未重建）。下面保留原始推論，因為它就是命中的那條路：
   `probe_engine.cpp` 的 `set-bold`／`set-italic` 讀 `gEditorState.bold`／`italic` 並在
   相符時直接回 `documented-state-noop`，而**該分支不在 `OXSDK_E2_FORMAT_BARRIER` 之內**
   ——也就是在 e1-editor-v1 的路徑上，而那個 profile 的 `updateEditorFormatState`
   （`#else` 分支）**根本沒有 `formatStateStale`**。若快取跨段落未更新，使用者按粗體會
   得到「成功、未變更」而文件沒動。**目前是推論，未實測。** 驗法：兩段 fixture
   （粗體段 → 非粗體段），click 進第二段後按粗體，由存檔 ODT 判定。踩到就開新 finding。
2. **依 C 重新定義 E2-A 的前置條件契約**：closed action 一律直接派送，判定只用
   後置條件（派送後 state ＋ 存檔 ODT，已驗證 5/5）；移除 `alreadyAtTarget` 一路的
   `documented-state-noop`，改為不宣稱「有沒有變」。這同時消掉 pump 依賴。
3. （可選，非阻擋）逐欄位世代標記——一個 `formatStateStale` 守五個欄位，任一筆
   watched payload 都會清掉它。屬推論、未觀測到實例；C 之下前置條件不再被讀，
   優先度隨之下降，但若日後啟用 A 就必須先補。
4. （可選）窄歸因：`loop()` 與 PEI 差**兩個**參數（`bWait`、`bHandleAllCurrentEvents`）
   加一個外層迴圈，三者未隔離。只有在日後要走 A 或要對外說明時才需要。

另一條線不變：`doc_iniUnoCommands()` 只在 `initializeForRendering` 時註冊 slot 並推
一次初始狀態（click 爆量 26/158 即此），之後 core 仍是值改變才廣播，沒有公開的
強制重查入口——這是「為什麼 host 自己補不了狀態、只能靠 pump 或不讀它」的論據。

### 決定之前不得做的事

- 不得放寬 fail-closed（狀態不新鮮時必須是 typed 拒絕，不是拿別段的值回答）。
- 不得因為「目前的測試序列沒踩到」就把 `documented-state-noop` 當成已驗證能力。
- 不得把 discovery 用的 unit-test 掛鉤帶進任何產品 profile。
- 推進若進入共用路徑，R6～R8 與 E1 全部要回歸，並確認不觸發
  [finding 012](012-r6-styled-document-close-timeout.md) 類的 teardown 阻塞。

### 相關檔案

- 實作：`wasm_sdk_probe/src/probe_engine.cpp`，搜 `OXSDK_E2_FORMAT_BARRIER` 與 `formatStateStale`；
  候選 1 迴圈搜 `OXSDK_MAINLOOP_ENGINE`（poll／wake／anyInput callback、`mainLoopTrace` 診斷）
- 建置：`wasm_sdk_probe/Makefile` 的 `E2_BUILD`／`E2_SCHED_BUILD`／`E2_MAINLOOP_BUILD` 區塊
- harness：`wasm_sdk_probe/web/e2-format-discovery-app.js`（`mode` 參數；`mainloop-attribution`
  的 refresh 是有界等待而非 pump）
- 規格：[SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 第 2.4、10.3 節（v6）
- 經過：[DEVLOG 2026-08-05 下半](../devlog/DEVLOG-2026-08-05-wasm-sdk-e2-a2-wasm.md)
- 機器可讀：`wasm_sdk_probe/e2/discovery-matrix-v1.json` 的 `finding021Attribution`／
  `finding021Remediation`

## 環境

- Core commit：`671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`
- Profiles（全部隔離，未取代任何 release artifact）：
  - `e2-format-discovery` WASM `45f2372beb961907…`（首次觀察）
  - 同 profile 加入原始 STATE_CHANGED 計數器後重建為 `9b6e9c587e1224ed…`（計數器歸因）
  - `e2-scheduler-attribution` WASM `1b6a3dd2a5cbeb3c…`（排程歸因）
  - `e2-mainloop-attribution`（候選 1；歸因期間隨程式碼演進重建多次，sound 語意
    build 為 `a696f0d61347e6da…`，nudge 實驗輪重建為 `1b64d70b64f0455f…`；各 attempt
    實跑的 build 以其 evidence 的 `manifest.diagnostic.wasmSha256` 為準，Chrome
    attempt-03 的 5/5 示範跑在 idle-poll 清 stale 的過渡 build 上）
  - `e2-mainloop-pei-attribution` WASM `3d87eb36829e53d3…`（判別實驗一：活迴圈＋drain）
- Emscripten（候選 1 輪確認）：專案釘的 emsdk `4.0.10`（`wasm-lite/tools/emsdk`），
  非系統版 3.1.69；pthread 'unwind' 存活行為兩版皆有
- Chrome：`150.0.7871.128`；Firefox：`153.0.1`
- 詳見 `evidence/021/env.txt`

## 還缺什麼才能關閉

- [x] 同 commit 原生以相同 caret 序列對照，確認是否 WASM 特定。**是。**
- [x] 排除「core 有送、我方沒解析」。**已排除**（watched payload 抵達數為 0）。
- [x] 判斷是上游或我方。**我方**：推進 scheduler 後狀態正確出現，core 計算無誤。
- [x] 證明修法方向可行。**已驗證**：fail-closed ＋ host 刷新，兩瀏覽器 5/5 且存檔獨立證實。
- [x] ~~決定產品層面正規的推排程機制（不得用 unit-test 掛鉤）與推進時機~~。**機制已實測可跑**
  （unipoll ＋ `runLoop` 註冊 ＋ `Application::Execute()`，2026-08-06），但見下一項。
- [x] ~~歸因「PEI（舊組態）放得出 payload、活迴圈（新組態）連任務都沒排」的差異~~。
  **已歸因：差異在 PEI 語意（迴圈到靜止），非 Desktop::Main 初始化、非定位路徑**
  （判別實驗一與二，2026-08-06）。
- [x] ~~補 fail-closed 的序號綁定~~。**該項所依據的宣稱已於二次覆核撤回**（已觀察
  第三點之附）：engine 旗標未被繞過。留下的是逐欄位世代標記，屬推論，列為可選。
- [ ] 向上游報告——**暫緩，非取消**。使用者 2026-08-06 決定先不送，素材另行整理成獨立
  草稿（`UPSTREAM-REPORT-DRAFT-…`），待整組實驗結束後再評估是否送出。注意「沒有受支援
  入口」的前提本身有誤，草稿不得沿用（`Scheduler::ProcessEventsToIdle()` 是公開 API，
  見「卡在哪裡」）。
- [x] **驗證 E1 release 的 `set-bold` 是否已在產品路徑上產生假 no-op。已重現，兩瀏覽器**
  ——見 [finding 022](022-e1-release-set-bold-false-noop.md)。本 finding 因此不只是
  E2-A 的閘門問題：同一成因**已在已出貨的 `e1-editor-v1` 上造成靜默 no-op**。
- [ ] 依路線 C 重新定義 E2-A 的前置條件契約，並讓 E2-A 取得判定。
- [ ] 若日後啟用 A（產品自行 pump）：先量 pump 實際耗時、補逐欄位世代標記、回歸
  R6～R8 與 E1 全部 release，並確認不觸發 finding 012 類 teardown。
- [x] ~~若判定為上游：搜重複單~~。不適用，非上游問題。

## 時間軸

- 2026-08-05：A2-wasm 首次在 Chrome 觀察到零 format state；查出是自身 harness 只用
  `setTextSelection(RESET)` 定位且只記錄 format-state 事件所致，補上 `click()` 定位、全事件
  記錄與 set-bold 正向對照後重跑。
- 2026-08-05：判準修正（原 `trackedCaret` 只要求「值有差異」，會被 null→已知的轉變滿足）後，
  Chrome 與 Firefox 各 2 次得到完全相同的 fresh／stale 分布，確認跨瀏覽器成立。
- 2026-08-05：同 commit 原生以四種移動方法對照，全部正常，否證「移動方法不同」的解釋。
  另加原始 STATE_CHANGED 計數器，證明失敗位置的 watched payload 抵達數為 0，排除我方解析失敗。
  當時判為 WASM 特定、上游候選。
- 2026-08-05：分層歸因推翻上述分類。在隔離的 `e2-scheduler-attribution` profile 中於每次定位後
  推進 VCL scheduler，四個位置的狀態全部變新鮮且與原生一致。**改判為我方 engine 迴圈未推進
  scheduler，非上游問題。**
- 2026-08-05：量出 `useSystemEventLoop=true` 與 `Application::Reschedule()` 在此組態為 no-op，
  排除「用公開 Reschedule 修」這條路；並量出 callback 在 pump 返回後才 flush，排除「推完就同步讀」。
- 2026-08-05：依此在 discovery profile 實作 fail-closed ＋ host 驅動刷新並驗證通過。第一版曾用
  engine 端非同步等待 payload，因 core 只在值改變時廣播而在值未變時逾時，並且逾時未清除 pending
  導致後續動作 BUSY；已改為現行設計。
- 2026-08-06：實作候選 1（`e2-mainloop-attribution`）。途中依序排除：未設 unipoll 時
  `lo_startmain` 隱藏執行緒與第二條 soffice_main 相撞（open 逾時）；`runLoop` 因
  `IsVCLInit` 早退不進迴圈（補呼 `Application::Execute()`）；`pData=null` 靜默停用
  unipoll（`mpPollClosure` 判空）。修好後全命令流程兩瀏覽器可跑。
- 2026-08-06：同輪否證「迴圈帶來 freshness」：caret 移後 idle 時零 STATE_CHANGED、
  `GetMostUrgentTaskPriority=-1`；click 爆量與舊 profile 數字一字不差，判為初始
  binding flush 而非逐移重查。第一版「idle-poll 即清 stale」因此不健全，回退為
  「僅 watched payload 抵達才清」；回退後兩瀏覽器 5/5 typed 拒絕、檔案零變動
  （Chrome attempt-03 的 5/5 成立保留為迴圈機制示範，其前置條件讀值依賴同段序列，
  不作修法驗證）。卡點重定義為 PEI 與活迴圈的行為差異，判別實驗已列。
- 2026-08-06（下半）：兩個判別實驗執行完畢。實驗一（複合 profile
  `e2-mainloop-pei-attribution`）：PEI 在活迴圈組態下有效、修法完整矩陣重現
  （兩瀏覽器 5/5 verified ＋ postcondition 5/5）——排除 Desktop::Main 初始化假設；
  實驗二（`move-character-left` nudge）：真 dispatch 移動不觸發重算——排除定位路徑
  假設。裁決：缺口在 PEI 語意本身，產品出路收斂為上游報告（每 tick ImplYield vs
  process-to-idle）。本 finding 的下一步移交上游溝通線。
- 2026-08-06（覆核）：外部覆核指出本日章節三處錯誤，全部查證屬實並原地修訂：
  「重算從未被排程」引用的是過渡 build 的讀數，最終 build 顯示 payload 會抵達但
  落後一格（改寫為收斂／順序問題，並修正原擬送上游的「永不抵達」句）；
  `GetMostUrgentTaskPriority=-1` 因取樣點與該函式 early-return 條件等價而零資訊
  （四處引用撤回）；`loop()` 與 PEI 差 `bWait` 與 `bHandleAllCurrentEvents` 兩個參數
  （原僅列一個），並補上 `DispatchUserEvents` 提早 return 跳過 `CheckTimeout()` 的
  機制解釋。連帶宣稱「落後一格的 payload 會清掉 stale 旗標，fail-closed 實作不完備」，
  列為最優先待修——**該宣稱於同日二次覆核撤回，見下條**。
- 2026-08-06（二次覆核）：上一條末尾的安全洞宣稱**不成立，已撤回**。查證：harness 的
  `fresh` 是 `formatStateEventsObserved > 0` 且計數起點在定位之前
  （`web/e2-format-discovery-app.js:242,268`），會把定位本身引發的廣播算進來；engine 的
  `formatStateStale` 在兩瀏覽器**全部 search 列都正確為 true**；且
  `updateEditorFormatState` 是先清旗標才發事件，不存在「事件到了旗標還 stale」的
  payload。誤因是把 harness 欄位當成 engine 判準。殘留的真實缺口改寫為**逐欄位世代
  標記**（一個旗標守五個欄位），標為推論、未觀測到實例。
- 2026-08-06（產品決定）：使用者決定**不送上游**。同時查證「沒有受支援的刷新入口」
  這個前提有誤——`Scheduler::ProcessEventsToIdle()` 是 `include/vcl/scheduler.hxx:65`
  的公開 API（`class VCL_DLLPUBLIC Scheduler final`），且有產品呼叫者；被標為
  unit-test 的只有 `svapp.cxx:485-491` 的 C 包裝。產品路線定為 **C：不讀前置狀態**，
  A（產品自行 pump）延後而非否決。「剩下的路」與「還缺什麼」依此重排，
  最高優先改為驗證 E1 release 的 `set-bold`／`set-italic` 暴露面。
