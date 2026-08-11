# SPEC E2-A：段落層級格式的 completion barrier discovery

> **日期**：2026-08-05（最後修訂 2026-08-11，v12）  
> **狀態**（2026-08-11 v12）：A1（部分）、A2、**A3／A4／A5 已執行且全數通過**
> ——綁定引擎 `25761ff0…`，兩瀏覽器 × 三 fixture（A5 四 fixture）。
> **A6／A7 未執行，E2-A 因此尚無總判定。**
> A3 的前置（第 4 節〈路線 C 未決事項〉）已由使用者選定路線並實作完成。  
> **上層規格**：[SPEC E2-000](./SPEC-E2-000-overview.md)  
> **前置閘門**：[E1](./SPEC-E1-000-overview.md) 已判定 `E1_GO_ODT_EDITOR`  
> **凍結矩陣**：[`e2/discovery-matrix-v1.json`](../wasm_sdk_probe/e2/discovery-matrix-v1.json)

## 1. 目的

> **2026-08-05 v2 修訂**：A2 原生實測推翻了本規格 v1 的進場前提。v1 寫「這些 fixed command 會改到文件、
> 但不回 `LOK_CALLBACK_UNO_COMMAND_RESULT`」。實測是：五個派送形式中四個**有**回 command result；真正的
> 兩個缺陷是**命令映射對到不存在的 UI 別名**（[finding 019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)）
> 與**command result 的成敗欄位與文件矛盾**（[finding 020](../findings/020-lok-list-command-result-contradicts-document.md)）。
> 以下各節已依實測改寫；v1 的錯誤前提保留在本段，不從歷史抹掉。

E1-A 把清單與段落樣式縮限，歸因為 completion 缺口。E2-A 要驗證能否為這類操作建立可歸屬、可重複、
能區分 no-op 與遺失的完成條件，並確認 E1-A 的歸因是否成立。

E2-A 是 discovery，不凍結產品 ABI。它的產出是「哪些能力可以進 E2-B」與「哪些必須維持 unsupported，
以及否證證據」。

## 2. 進場基線

### 2.1 已觀察

- discovery ABI 已有五個段落層級 action 與固定映射（`src/editor_discovery_api.h`、
  `src/probe_engine.cpp:2083-2097`）：`.uno:TextBodyParaStyle`、`.uno:Heading1ParaStyle`、
  `.uno:RemoveBullets`、`.uno:DefaultBullet`、`.uno:DefaultNumbering`。
- E1-A 十份 fixture 實測中，這五個 action 沒有取得可承諾的跨瀏覽器 completion（[SPEC E1-A](./SPEC-E1-A-editing-discovery.md) 第 11.3 節）。
- `src/probe_engine.cpp:457` 已把 `.uno:Bold=<bool>`、`.uno:Italic=<bool>` 的 STATE_CHANGED payload 解析成
  typed state，並在 `:2023` 用它實作 `documented-state-noop`；該路徑在 Chrome／Firefox 皆已由 E1-A／B／C 實測。
- core 的 `GetKitUnoCommandList()`（`sfx2/source/control/unoctitm.cxx:1165`）是封閉列舉表，
  `Bold`、`Italic`、`DefaultBullet`、`DefaultNumbering` 同為 `IsActivePayload`，`StyleApply` 為
  `StyleApplyPayload`（`:969` 以 `Template.StyleName` 組成 payload），五者 `initializeForStatusUpdates` 皆 `true`。

### 2.2 A2 原生實測結果（2026-08-05，已觀察）

證據：[`sdk-e2/discovery/state-readback/native-26-8/`](../findings/evidence/sdk-e2/discovery/state-readback/native-26-8/)。
每個命令派送後立即 `saveAs` 成 ODT，後置條件由存檔內容判定，與被檢驗的 callback 無關。

| 派送 | command result | state callback | 文件實際結果 |
|---|---|---|---|
| `.uno:DefaultBullet` | `success:true`、`wasModified:false` | `DefaultBullet=true` | **有效**，段落進入清單 |
| `.uno:DefaultNumbering` | `success:true`、`wasModified:true` | `DefaultNumbering=true` | 有效 |
| `.uno:RemoveBullets` | **`success:false`**、`wasModified:true` | `DefaultNumbering=false` | **有效**，離開清單 |
| `.uno:Heading1ParaStyle` | 無 | 無 | **完全無效** |
| `.uno:StyleApply`＋參數 | `success:true`、`wasModified:true` | `StyleApply=Heading 1`／`Body Text` | 有效 |

三項關鍵事實：

1. **段落樣式的命令名稱是錯的。** `.uno:Heading1ParaStyle`／`.uno:TextBodyParaStyle` 在 LibreOffice 全樹只
   存在於 `WriterCommands.xcu` 的 `UserInterface/Popups`，沒有 `.sdi` slot；它們是選單別名，`TargetURL`
   指向參數化 `.uno:StyleApply`。E1-A 從未真正派送過段落樣式命令。
2. **command result 可歸屬但不可信。** 它帶 `commandName`，這正是廣播式 state 缺少的東西；但 `success` 與
   `wasModified` 各有一個命令說謊。
3. **一個樣式三種字串**：送出 `Text body`、ODT 存 `Text_20_body`、state 回報 `Body Text`。互相不可代用。

另：command result 在 1～4 ms 抵達，state 在 301～602 ms 後才抵達，兩者不同步。

### 2.3 A2-wasm 實測結果（2026-08-05，已觀察）

證據：[`sdk-e2/discovery/state-readback/wasm/`](../findings/evidence/sdk-e2/discovery/state-readback/wasm/)。
Chrome 150 與 Firefox 153 各 2 次，結果完全一致。每次派送後即存 ODT，postcondition 由檔案判定。

**通過的部分：**

- 三個 payload 在 WASM profile 確實抵達（`listBulletKnown`／`listNumberKnown`／
  `paragraphStyleKnown` 皆 true）。2.1 節末的核心推論就此升格為已觀察。
- 五個派送全部以 `verified-format-state` 完成、`changed:true`、revision 各前進一格，
  且五份存檔 ODT 的結構逐項相符（5/5）。
- 「一個樣式三種字串」在 WASM 完整重現：送 `Text body`、state 回 `Body Text`、
  ODT 存 `Text_20_body`。
- `crosstalkCount` 與 `earlyStateCount` 十次派送皆為 0：result 先於 state 的順序在 WASM 成立。
- [finding 020](../findings/020-lok-list-command-result-contradicts-document.md) 跨平台重現：
  `DefaultBullet` 回 `wasModified:false` 卻改了文件，`RemoveBullets` 回 `success:false` 卻生效。
  這使該單不再只是原生觀察。

**未通過的部分（[finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)）：**

- state **不隨 caret 移動更新**。10 次定位讀取只有 2 次新鮮，其餘回報上一段的快取值；
  caret 實際位於 `<text:list>` 內時，引擎從未回報過「在清單內」。
- 這推翻 2.2 節「純 caret 移動就會更新」的原生觀察在 WASM 的適用性，並使 barrier 的
  **前置條件**（`stateKnown`／`alreadyAtTarget`）可能讀到別段的狀態。後置條件不受影響。

### 2.4 finding 021 的歸因（2026-08-05，已觀察）

決定性實驗已完成，證據在 [`evidence/021/native-caret-tracking/`](../findings/evidence/021/native-caret-tracking/)：

- 同 commit 原生以**四種**移動方法（游標命令、`setTextSelection(RESET)`、滑鼠點擊、
  以及 WASM 逐字序列 `ExecuteSearch`＋`setTextSelection`）在同一份 fixture、同一組定位點跑，
  **全部正常追隨 caret**。「兩次量的是不同東西」的解釋就此否證。
- 在 E2 profile 加上原始 STATE_CHANGED 計數器（只計數、不轉發 payload）後，失敗位置的
  watched command 抵達數為 **0**，排除「core 有送、我方解析失敗」。

- 分層歸因（隔離 profile `e2-scheduler-attribution`，E2 組態＋Finding 016 的 scheduler drain）：
  每次定位後推進一次 `Scheduler::ProcessEventsToIdle()`，**四個位置的狀態全部變新鮮且與原生一致**
  （Chrome 與 Firefox 逐項相同）。先前「零抵達」的位置一旦推排程就有 watched payload。

**結論：core 計算正確，問題在我方 engine 迴圈從不推進 VCL scheduler。** LOK 的 status update 是
idle job；原生由 `soffice_main` 的 VCL 主迴圈推動，我方探針核外連結、自帶命令迴圈，兩個操作之間
沒有任何東西推進 scheduler。派送命令有狀態，是因為那條路徑在命令執行中同步廣播，不需要 idle job。
**finding 021 因此不是上游問題**，先前的上游候選分類已撤回。

修法方向隨之改變：不是繞開不可靠的狀態，而是在讀前置狀態前推進 scheduler 讓它可靠。

進一步實測收斂了做法：`Application::IsUseSystemEventLoop()` 在此建置為 `true`，因此公開的
`Application::Reschedule()` **回傳 false 且什麼都不做**（`vcl/source/app/svapp.cxx:400-406`），
不能當修法；而 callback 是在 pump **返回之後**才 flush，因此「推完就同步讀」也不行。

已在 discovery profile 驗證的設計：engine 於 caret 移動時標記 state 為 stale，前置條件為 stale
時回 `EDITOR_FORMAT_STATE_UNAVAILABLE`、零 mutation；refresh 由 **host** 驅動（先 pump、等 flush
穩定、再下動作），engine 不做任何 sleep，沿用 E1-B 在 click 之後以 host 有界輪詢的既有慣例。

| 情境 | 五個格式動作 | 存檔 postcondition |
|---|---|---|
| 不做 host refresh | 5/5 `EDITOR_FORMAT_STATE_UNAVAILABLE`、零 mutation | 文件未變 |
| 有 host refresh | 5/5 `verified-format-state`、revision 各 +1 | 5/5 相符 |

兩瀏覽器一致。**但 A3 仍不啟動**：discovery 用的 pump 是 unit-test 掛鉤
（`unit_lok_process_events_to_idle()`），**不得**升格為產品機制；正規推進方式未定，且若進入共用
路徑需先跑完整回歸。

### 2.5 待驗證

- ~~caret 移動後的狀態重算為何在活迴圈下未被排程~~。**已判別（2026-08-06 下半）**：
  差異在 PEI 語意（迴圈到靜止），非 Desktop::Main 初始化、非定位路徑——PEI 在活迴圈
  組態下照常有效且修法矩陣重現（複合 profile，兩瀏覽器）；真游標 dispatch 不觸發重算。
  剩餘工作是上游報告，見
  [finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)
  「判別實驗結果與剩下的路」。
- 主迴圈進入共用路徑前的再進入／teardown 副作用（finding 012 屬相鄰風險）與 R6～E1 全量回歸。
- ~~`Body Text` 等 state 顯示名稱是否隨 UI locale 改變。若會，postcondition 不能比對顯示名稱。~~
  **已答（2026-08-11）：會變，見 [finding 031](../findings/031-styleapply-postcondition-compares-a-localized-ui-name.md)。**
  `SID_STYLE_APPLY` 的狀態放的是 `UIName` 且**不放 ProgName**（`sw/.../docst.cxx:140,145,166`），
  而 UIName 陣列以 UI 語系為 key、由 `SwResId()` 建（`DocumentStylePoolManager.cxx:2665-2676`）；
  ProgName 陣列則是寫死不翻譯的。既有證據已佐證這一點：我方送 `Text body`／`Standard`，
  state 回 `Body Text`／`Default Paragraph Style`——送出與回報不是同一個字串。
  建置樹的 `instdir` 有 `zh_TW/LC_MESSAGES/sw.mo`（`Heading 1`→「標題 1」、
  `Body Text`→「內文」，正是第 4 節比對的那兩串），**但出貨的 WASM 檔案系統映像沒有**：
  `soffice.data` 的 1,358 個檔裡 `.mo` 是 0、`/resource/` 下只有一個字型，
  却有三個 zh-TW registry langpack XCD——**選得到但沒有東西可選**。
  端到端實測**已試且為假陰性**：新增隔離 profile `e2-locale-attribution`
  （engine 走 `documentLoadWithOptions(…, "Language=zh-TW")`，編譯期常數隔離）跑 Chrome 一輪，
  回報字串完全沒變、五個 action 全 `verified-format-state`、postcondition 5/5——
  沒有譯文的 build 上這條路不可能印出不同值，**因此最後一環仍是推論**。
  要真的量到得先把譯文打進 FS 映像（做 zh-TW 產品本來就得做）或執行期寫進 MEMFS。
  清單三個動作不受影響（payload 是布林值）。
- ~~state 是否可能早於 command result 抵達~~。已驗證：`earlyStateCount` 全為 0。
- 清單切換產生的 `<text:list>` 包裝結構是否觸發 [Finding 012](../findings/012-r6-styled-document-close-timeout.md)
  的 `frame.wrapper` 類 teardown 阻塞。本輪 close 正常，但未做 A5 的 `list-teardown` 專項。

### 2.6 finding 021 候選 1 實測（2026-08-06，已觀察）

隔離 profile `e2-mainloop-attribution`（`OXSDK_MAINLOOP_ENGINE`）把 engine 的阻塞命令
迴圈換成上游主迴圈：`SAL_LOK_OPTIONS=unipoll`（hook 前 setenv）→
`libreofficekit_hook_2` → `runLoop`（僅貢獻 poll／wake callback 註冊；其 `soffice_main`
因 `ImplSVMain` 的 `IsVCLInit()` 早退立即返回）→ engine 直呼 `Application::Execute()`
（out-of-tree 宣告綁定）。命令派送搬進 unipoll poll callback。無 unit-test 掛鉤連結。

**結果一（機制，通過）**：unwind 後 engine pthread 存活（emsdk 4.0.10），tick 驅動
poll，開檔／render／search／click／派送／存檔／close 全流程 Chrome 150 與 Firefox 153
通過，poll 計數 ~810／idle ~739。三個一次性陷阱已記錄於 finding 021 的「已排除」表
（`lo_startmain` 隱藏執行緒、`IsVCLInit` 早退、`pData` 判空）。

**結果二（freshness，否證）**：活迴圈下純 caret 移動，watched payload **會抵達但
落後一個定位點**——最終 sound build 的 search readback 裡，`body-paragraph` 讀到
heading 的值、`list-item` 讀到 body 的值、`after-list` 讀到 list-item 的值
（Chrome `after-list` 1 筆 watched、Firefox `list-item` 2 筆／`after-list` 1 筆，
兩者皆被標為 fresh）。所以不是「重算未被排程」，是收斂／順序問題：穩定跳動的迴圈
追不上，PEI 的迴圈到靜止追得上。click 爆量（26／158）與舊 blocking profile 逐字
相同，判為 `initializeForRendering` → `doc_iniUnoCommands` 的初始 binding flush。
過渡 build 曾以「idle-poll 即清 stale」讓五個派送 5/5 成立（Chrome attempt-03，
同段序列下前置讀值僥倖正確），該不變式不健全已回退；sound 語意下兩瀏覽器矩陣為
5/5 `EDITOR_FORMAT_STATE_UNAVAILABLE`、檔案零變動（逐項檢查）。

~~**結果三（覆核追加，未修補）**：回退後的不變式擋不住落後一格的 payload。~~
**（2026-08-06 二次覆核撤回。）** engine 的 `formatStateStale` 在兩瀏覽器全部
search 列都正確為 `true`，且 `updateEditorFormatState` 先清旗標才發事件，不存在
「事件到了旗標仍 stale」的 payload；被誤讀的是 harness 的 `fresh` 欄位
（`formatStateEventsObserved > 0`，計數起點在定位之前）。殘留的真實缺口改為**逐欄位
世代標記**（一個旗標守五個欄位），屬推論、未觀測到實例，見
[finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)。

**A3 仍不啟動**：待本規格依產品路線 C 重新定義前置條件契約後再評。

**（2026-08-06 下半補記）** 判別實驗已完成並收斂：複合 profile
`e2-mainloop-pei-attribution`（活迴圈＋drain）證明 PEI 在新組態下照常有效且修法
完整矩陣重現（兩瀏覽器 5/5 verified ＋ postcondition 5/5）；真游標 dispatch
（`move-character-left` nudge）不觸發對位重算。缺口定為 PEI 語意——每 tick 的
`ImplYield(isActive(), false)` 收斂不到 process-to-idle 的狀態，且與 PEI 差
`bWait`／`bHandleAllCurrentEvents` 兩個參數加一個外層迴圈，三者尚未隔離。

**（2026-08-06 產品決定，v10）** 使用者決定**不送上游**，產品路線定為 **C：不讀前置
狀態**。closed action 一律直接派送，判定只用後置條件（派送後 state ＋ 存檔 ODT，
已驗證 5/5）；`alreadyAtTarget` 一路的 `documented-state-noop` 移除，改為不宣稱
「有沒有變」。此路線消掉 pump 依賴，本規格的 A3 前提隨之改寫。另更正一項既往前提：
`Scheduler::ProcessEventsToIdle()` 是公開 API（`include/vcl/scheduler.hxx:65`）且有
產品呼叫者，「沒有受支援入口」不成立；路線 A（產品自行 pump）**延後而非否決**。

### 2.7 路線 C 的兩個前提實測（2026-08-11，已觀察）

證據：[`sdk-e2/discovery/reissue/native-26-8/`](../findings/evidence/sdk-e2/discovery/reissue/native-26-8/)，
見 [finding 030](../findings/030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)。

路線 C 移除前置條件讀取，等於**允許同一個 action 被連續派送**。這使兩件先前被
`alreadyAtTarget` 短路遮住的事變成必須先答的問題。原生 26.8、同一段落、先置入相反狀態再
連按三次，每次派送後存 ODT，判定一律讀存檔內容。

**（一）不帶參數的清單命令是 toggle。** `.uno:DefaultBullet`／`.uno:DefaultNumbering`
在沒有 `On` 參數時取 `!SelectionHasBullet()`，也就是現況的相反（`svx/sdi/svx.sdi:2251`、
`:4985` 宣告 `SfxBoolItem On FN_PARAM_1`；`sw/source/uibase/shells/txtnum.cxx:81-108`
有參數才是 explicit mode）。實測第二次按下 `set-list-unordered` 會把段落踢出清單。
**帶 `On=true` 則四個案例全部是 setter**，包含有序清單→無序清單的跨種類轉換——
所以第 4 節的三態封閉列舉做得到，前提是送對形式。engine 已改派參數化形式
（`src/probe_engine.cpp`，`tests/test_e2_profile.py` 有測試釘住，突變控制通過）。

修法後以 `--mode scheduler-attribution` 兩瀏覽器各重跑一輪（新 profile `38d15ed4…`），
五個 action 全為 `verified-format-state`、`documentPostconditions` 5/5，與最後一版
sound build 逐項相同。**但那輪只證明「沒弄壞」**：該 harness 的五個派送都是跨狀態轉換，
toggle 與 setter 在跨狀態轉換上結果相同，所以就算 `On` 在序列化中被丟掉也會照樣全過。
「參數在 WASM 路徑上生效」要靠**重複派送**才驗得到，而那正是路線 B 的 `alreadyAtTarget`
擋住的事——留給 A4。

**（二）值沒變就沒有 STATE_CHANGED。** 已在目標狀態時再按一次，文件正確、command result
照常抵達且帶正確 `commandName`，但**九個案例的第二、三次全部零 watched payload**。
第 4 節的 completion 需要 (a) 歸屬與 (b) state 後置條件同時成立，(b) 在合法 no-op 時
永遠不會到，因此會逾時成 `MUTATION_OUTCOME_UNKNOWN`——而文件其實是對的。

**這是低報，不是誤報**，但第 8 節把「no-op 與遺失不可區分」列為 `STOP_OR_RESCOPE`，
所以只修（一）不會讓 A3 可判定。四條出路（接受低報／路線 A／新增文件 readback／
只用 command result）記在 finding 030，**待產品決定**。

## 3. 不可退讓的邊界

沿用 [SPEC E2-000](./SPEC-E2-000-overview.md) 第 6 節全部條款。E2-A 另加：

- 只使用隔離的 `e2-format-discovery` artifact。不重建、不覆寫 R5 `writer-review` 與 E1-B `e1-editor-v1`。
- 只接受 discovery 期間**實際量到並記錄在 evidence 裡**的固定 payload 字串集合；不做前綴比對、
  子字串比對或正規表示式猜測。
- barrier 只接受該 action 對應命令的 payload。「dispatch 之後抵達的任何 state」不構成 completion。

## 4. 要驗證的 barrier 設計

A2 的結果決定了設計：**兩個來源各自只提供一半，缺一不可。**

- command result 帶 `commandName`，是唯一能把結果綁到這個 request 的東西 —— 解決 attribution。
- state callback 是唯一如實反映文件的東西 —— 解決真值。反過來用會錯：用 `success` 判定會讓
  `set-list-none` 每次都回報失敗。

> **2026-08-11 v11 修訂（路線 C 的前置條件契約）**：下方流程圖的**前兩行已作廢**。
> 產品路線 C 不讀前置狀態，`EDITOR_FORMAT_STATE_UNAVAILABLE` 的前置檢查與
> `documented-state-noop` 一併移除；派送是無條件的。作廢的原文保留在本段，
> 不從歷史抹掉：
>
> ```text
> dispatch 前   ── 對應 typed state 未知 ──▶ EDITOR_FORMAT_STATE_UNAVAILABLE（零 mutation，fail closed）
>               └─ 已等於目標值 ──────────▶ documented-state-noop（changed:false，revision 不變）
> ```
>
> 移除的代價已於 2.7 節實測：合法 no-op 不再有任何 state payload 可等，
> 因此下方的「barrier 逾時」會成為**重複按下的常態讀數**。這是本規格目前的
> 未決點，見本節末的〈路線 C 未決事項〉。

```text
dispatch      ── 無條件派送（不讀前置狀態）。記錄 beforeRevision / beforeSequence，
                 開啟 barrier，期間其他 editor action 回 BUSY
barrier 命中  ── 需同時成立：
                 (a) command result 的 commandName 等於本次派送的命令；
                 (b) 對應命令的 state payload 值等於期望值。
              ──▶ revision +1，completion = "verified-format-state"
barrier 逾時  ──▶ MUTATION_OUTCOME_UNKNOWN，不 retry，不猜
```

固定對照（closed map，命令與參數都不可由 JS 指定）：

| action | 派送 | 後置條件（state） |
|---|---|---|
| `set-list-unordered` | `.uno:DefaultBullet` ＋ `On=true` | `.uno:DefaultBullet=true` |
| `set-list-ordered` | `.uno:DefaultNumbering` ＋ `On=true` | `.uno:DefaultNumbering=true` |
| `set-list-none` | `.uno:RemoveBullets` | `DefaultBullet=false` **且** `DefaultNumbering=false` |
| `set-paragraph-heading` | `.uno:StyleApply` ＋ `Style=Heading 1`、`FamilyName=ParagraphStyles` | `.uno:StyleApply=Heading 1` |
| `set-paragraph-body` | `.uno:StyleApply` ＋ `Style=Text body`、`FamilyName=ParagraphStyles` | `.uno:StyleApply=Body Text` |

> **2026-08-11 v11 修訂（派送形式）**：前兩列原本寫不帶參數的命令名。實測那是 toggle，
> 在無條件派送下第二次按會反轉（2.7 節、[finding 030](../findings/030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)）。
> `On` 是 core 有文件的 explicit mode 參數，**不是我方發明的旗標**。
> `set-list-none` 維持不帶參數：`FN_NUM_BULLET_OFF` 本身就轉呼 `On=false` 再
> `DelNumRules`，實測三次連按皆停在「不在清單」，從 bullet 與 numbered 兩種起點都一樣。

`success` 與 `wasModified` 只記錄進 evidence，**不參與判定**。

**次要危害仍是 attribution。** state callback 是廣播的，caret 移動也會送出。command result 已大幅降低這個
風險，但兩個保護仍保留並各自計數：`crosstalkCount`（watched 命令但值不對）與 `earlyStateCount`（值對但早於
command result 抵達）。第 5 節的 `state-crosstalk` 案例驗證這兩個計數確實有效。

### 路線 C 的 no-op 缺口：已選定出路 3（2026-08-11）

2.7 節（二）的實測讓上面的 completion 定義在一種情況下永遠無法成立：文件已經在目標狀態時，
core 不廣播 state，於是 (b) 不會到，barrier 逾時。

**使用者 2026-08-11 決定走出路 3：後置條件改讀文件，不讀廣播。**
可行性已先實測（見 2.8 節），因此 A3 的這一項前置**已解除**；
未解除的是實作本身與它帶來的兩項縮限（同見 2.8 節）。

以下四條出路原樣保留，說明選擇是在什麼之間做的：

1. **接受低報**：維持現有定義，重複按下回 `MUTATION_OUTCOME_UNKNOWN`。零新機制，
   但把「不知道」變成常態讀數，判定訊號變鈍。
2. **路線 A（產品自行推進 scheduler）**：狀態可信之後，前置條件與 no-op 再次可分。
   代價是進入共用路徑需跑完整回歸（finding 012 相鄰風險）。
3. **後置條件改讀文件**：派送後直接讀該段落實際格式，不靠廣播。最誠實，
   但需要一個目前不存在的 readback 能力，得自成一輪 discovery。
4. **只用 command result 當完成條件**：歸屬有了，真值沒有。這正是本節開頭明確拒絕的做法
   （finding 020），列出只為說明它被考慮過。**不建議。**

無論選哪一條，**派送形式的修正（2.7 節（一））都是必要的**，因此已先行實作。

### 2.8 出路 3 的可行性實測（2026-08-11，已觀察）

證據：[`sdk-e2/discovery/format-readback/native-26-8/`](../findings/evidence/sdk-e2/discovery/format-readback/native-26-8/)。

先排除再量測：`getCommandValues` 的實作（`sw/source/uibase/uno/loktxdoc.cxx`）只服務 form
field、bookmark、section 與 `ExtractDocumentStructures`（chart／content control／doc prop／
track changes），**沒有游標所在段落的樣式或清單狀態**。剩下的候選是 selection transferable
（`doc_getTextSelection`，`desktop/source/lib/init.cxx:5912`）。

| 情境 | `text/html` 讀到 |
|---|---|
| heading | `<h1 class="western">…</h1>` |
| body 段落 | `<p style="line-height: 100%; …">…</p>` |
| 無序清單 | `<ul><li><p …>…</p></li></ul>` |
| 有序清單 | `<ol><li><p …>…</p></li></ol>` |
| 離開清單後 | `<p …>…</p>` |

**五個 closed action 全部可分、讀數跟著 mutation 走、且與語系無關**——分辨用的是 HTML 結構
而非 UI 名稱，所以 2.5 節的 finding 031 曝險在段落樣式那兩個動作上一併解掉。

**三項代價／限制，量出來的：**

1. **游標塌陷時讀不到**（selection type 0、0 bytes）。barrier 必須先
   `.uno:GoToStartOfPara` → `.uno:EndOfParaSel` 選起整段才讀得到，讀完要還原選取，
   **且還原本身要被驗證**。這是新增的可觀察副作用，A5 需要為它加案例。
2. **`Text body` 與預設樣式都是 `<p>`**。這個讀法分得出「是不是 heading」，
   分不出「是 Text body 還是 Standard」。`set-paragraph-body` 的後置條件因此
   **比現行的 `.uno:StyleApply=Body Text` 弱**；SPEC E2-000 承諾的是
   `set-paragraph-style(body｜heading)` 兩態，「不是 heading」剛好夠用，
   但這是縮限，第 8 節判定要明列。
3. **這串 HTML 是序列化器輸出，不是有文件的契約。** 整串比對等於把序列化器釘成 ABI，
   跨版本可能變。**未驗證**，是 A7 回歸該涵蓋的事。

### 2.9 readback barrier 已實作並實測（2026-08-11，已觀察）

engine 的 `OXSDK_E2_FORMAT_BARRIER` 已改為路線 C ＋ 文件後置條件：

```text
dispatch      ── 無條件派送（不讀前置狀態）
command result ─ commandName 相符 ⇒ 歸屬成立；接著排一個 step（不在 callback 內做事，
                 與 selection barrier 同一條非再進入規則）
step          ── .uno:GoToStartOfPara → .uno:EndOfParaSel，等 TEXT_SELECTION
step          ── getTextSelection("text/html")，解析 body 內的開標籤序列
              ── listTag（ul／ol／none）與 blockTag（h1／p）**分開判定**
              ── 還原游標，等塌陷確認
              ──▶ completion = "verified-format-readback"
不符          ──▶ EDITOR_FORMAT_POSTCONDITION_FAILED（帶實際讀到的標籤與原始 HTML）
還原不成      ──▶ EDITOR_SELECTION_NOT_RESTORED（文件已改，但選取沒還原，照實報）
```

`completion` 的字串**跟著證據來源改名**：舊名 `verified-format-state` 下的證據是另一種檢查產生的。

**兩個標籤分開判定不是設計潔癖**：實測 `heading-on-repeat` 讀到
`listTag="ul"` 且 `blockTag="h1"`——清單裡的 heading。只取第一個標籤會讀成 `ul`，
段落樣式的後置條件在清單裡就永遠不可能成立。

實測（`e2-format-discovery` WASM `7665308a…`，9 個派送含 4 次重複）：

| | Chrome 150.0.7871.128 | Firefox 153.0.1 |
|---|---|---|
| `verified-format-readback` | 9/9 | 9/9 |
| `restoreConfirmed` | 9/9 | 9/9 |
| 存檔 ODT postcondition | 9/9 | 9/9 |

**兩瀏覽器逐項相同。** 正控制來自同一個 profile 的前後對照：加 fail-closed 之後
它對五個動作一律回 `EDITOR_FORMAT_STATE_UNAVAILABLE`、文件零變動（10.3 節），
現在同一個 profile 是 9/9 完成、文件如實改變——**讀數變了**。

**四次重複派送同時答完兩題**：
（一）**冪等**——`bullet-on-repeat-2`／`heading-on-repeat-2` 都停在目標狀態，
所以 `On` 參數確實原封不動通過我方 worker／engine 路徑。
這正是 2.7 節那輪 scheduler-attribution 重跑**答不出來**的問題（全是跨狀態轉換），現在有答案。
（二）**無聲 no-op**——重複派送不再逾時，barrier 照常完成。第 4 節的缺口關閉。

#### `changed` 不再宣稱（同日稍後更正）

第一版實作照舊送 `"changed":true`。**那是一個沒有任何檢查支持的宣稱**：
readback 回答的是「文件現在是不是目標狀態」，不是「是不是這次派送把它變成這樣」——
重複按下時文件本來就對，讀回來一模一樣，`changed:true` 就是假的。

v10 其實早就決定「不宣稱有沒有變」（`documented-state-noop` 被移除正是因為那個宣稱撐不住），
只是程式還在宣稱。已改為 `"changed":null`。重跑兩瀏覽器：9/9 完成、`changed` 全為 null、
`restoreConfirmed` 9/9、postcondition 9/9（WASM `80b48abf…`）。

#### 凍結矩陣已就地修訂並保留被取代的值

`e2/discovery-matrix-v1.json` 與實作在兩處已不一致（派送參數、completion 規則）。
矩陣是凍結契約，**不能默默改**，因此加了 `revisions` 區塊：逐項記錄改了什麼、為什麼、
以及**完整保留被取代的舊值**（`superseded`）。兩項都是**依實測修正，不是放寬門檻**——
`thresholds` 一個字沒動，且 A3 尚未產生正式結果，沒有已判定的東西受影響。

另移除 `requiredProperties` 的 `fail-closed-unknown-precondition`：路線 C 不讀前置條件，
該性質**變成恆真而非被滿足**，留著會讓一個空洞的性質被算成通過的性質。
改列兩項 readback 設計真正產生的義務：`postcondition-read-from-the-document`、
`selection-restored-and-confirmed`。`tests/test_e2_profile.py` 有五個測試把矩陣與 engine 釘在一起。

## 5. 凍結矩陣

數量與項目以 [`e2/discovery-matrix-v1.json`](../wasm_sdk_probe/e2/discovery-matrix-v1.json) 為準，
正式結果產生後不得放寬。

### A1：進場與 surface inventory

保存 core HEAD／dirty baseline、E1-B 與 R5 artifact hash、瀏覽器與桌面版本；確認 discovery profile 沒有
匯出產品 ABI，也沒有 raw callback 逃生口。

### A2：狀態回讀存在性（**先決條件**）

在**不接 barrier、不宣稱 completion** 的前提下，觀測 `.uno:DefaultBullet`、`.uno:DefaultNumbering`、
`.uno:StyleApply` 三個 payload 是否抵達、格式為何、caret 在清單內外移動時是否隨之變化，並記錄實際字串。
每次派送後存檔，後置條件由 ODT 內容判定。

**先跑原生再跑瀏覽器。** 理由與 Finding 016 相同：WASM 的否定結果無法區分「core 沒送」與「我方沒收到」。
原生也是唯一能安全取得 style 字串的地方 —— 猜錯會讓 barrier 悄悄失效。

A2 不通過就直接停止：沒有可靠的後置狀態，barrier 無從建立，第 8 節判定為 `STOP_OR_RESCOPE`。

- **A2-native**：已完成（2026-08-05）。結果見 2.2 節；通過，但推翻 v1 前提並產生 finding 019／020。
- **A2-wasm**：已完成（2026-08-05）。結果見 2.3 節。三個 payload 抵達且派送後可信，但
  caret 追隨性不成立（finding 021），因此 A2 **部分通過**：後置條件成立，前置條件不成立。
- **A2-reissue（原生）**：已完成（2026-08-11）。結果見 2.7 節。路線 C 的兩個前提各得一個答案：
  派送形式要帶參數才是 setter（已修）；合法 no-op 沒有後置條件可等（未決）。
  此項是路線 C 定案後才成立的問題，v1～v10 沒有對應的先決條件。

### A3：正向 barrier

Chrome／Firefox 各 3 次，每個 fixture：

- `set-list-unordered` → `set-list-ordered` → `set-list-none` 三態循環；
- `set-paragraph-heading` → `set-paragraph-body` 兩態往返；
- 每次驗證 completion source、`changed`、revision 只前進一格與 typed 後置狀態。

> **2026-08-11 v11 補充**：三態循環的每一步都是**跨狀態轉換**，所以它驗不到重複派送。
> 那正是路線 C 新增的風險面，因此 A4 改寫如下。

### A4：重複派送（原「no-op 與 fail-closed」）

> **2026-08-11 v11 改寫。** 原文兩條都建立在讀前置狀態上，路線 C 之後兩條都不再適用，
> 作廢原文保留於此：
>
> - ~~已是目標狀態時重下同一 action，必須回 `documented-state-noop`、`changed:false`、revision 不變。~~
> - ~~在狀態尚未已知時下 action，必須回 `EDITOR_FORMAT_STATE_UNAVAILABLE` 且零 mutation。~~

無條件派送之下，要驗的是**冪等**與**無聲 no-op**：

- **冪等**：已是目標狀態時連下同一 action 三次，每次派送後存檔，
  五個 action 的文件狀態都必須停在目標，**不得反轉**。2.7 節已在原生驗過參數化形式成立；
  A4 要驗的是 WASM 路徑上 `On` 參數確實原封不動送達（原生成立不代表我方 worker／engine
  的序列化沒動它）。
- **無聲 no-op**：同上重複派送時記錄 completion 的實際結果。
  依第 4 節〈路線 C 未決事項〉選定的出路判定；**在未決之前，A4 不算通過，A3 不啟動**。
- **零 mutation 的 fail-closed 仍要有一條**：`stale-revision` 移到 A5 一併驗（原本就在那裡）。

### A5：負向與邊界

| 案例 | 期望 |
|---|---|
| `state-crosstalk` | dispatch 前後刻意移動 caret 觸發無關 state；barrier 不得誤判為 completion |
| `stale-revision` | 零 mutation |
| `timeout-after-dispatch` | `MUTATION_OUTCOME_UNKNOWN`，無 retry，後續回 `BUSY` |
| `table-boundary` | **實測改寫，見下** — typed 結果，且文件必須同意 |
| `unsupported-action` | typed 拒絕 |
| `list-teardown` | 清單切換後 open→close 不得重現 Finding 012 類阻塞 |

> **2026-08-11 v12 修訂：`table-boundary` 的凍結期望被實測否證。**
>
> 原文寫「typed 拒絕，之後 fresh Worker」。那是**寫矩陣時的預期**，不是量到的行為：
> 表格儲存格內的段落在 26.8 上**接受** `set-list-unordered`，barrier 完成，
> 而且存回的文件同意——readback 是
> `<ul><li><h1>E1-CELL-A1</h1></li></ul>`，文字自己標明讀的是儲存格內那一段。
>
> 期望改為：**typed 結果，且文件必須同意**。也就是不預設是接受或拒絕，
> 但無論哪一個，都必須是分類過的結果，且不得出現「回報成功而文件不支持」。
> 這比原文弱，**但原文弱的是它的真假而不是它的嚴格度**——一條要求拒絕而系統會接受的
> 期望，只會讓每一輪 A5 都判失敗，而失敗的是規格。
>
> 範圍限制（**不得**外推）：Chrome 150.0.7871.128 與 Firefox 153.0.1、
> 引擎 `25761ff0…`、`table-boundary` fixture 的**單一儲存格** `E1-CELL-A1`、
> 派送時 caret 是**收合**的。跨儲存格選取、巢狀表格、表格邊界上的段落合併都**沒有量過**。
>
> 證據：`findings/evidence/sdk-e2/discovery/negative/{chrome,firefox}/table-boundary/`。

### A6：次要能力重評（不列入判定）

line navigation（Finding 018）與 mouse drag selection 各跑一輪，只收集證據。允許結論為「維持 unsupported」；
**不得**因為它們失敗而降低 A3～A5 的判定。

### A7：round-trip 與回歸

每個瀏覽器至少 3 份輸出 ODT 通過 ZIP CRC、XML、anchor 與 `<text:list>`／樣式結構檢查，再由 desktop
LibreOffice reopen 與 PDF export。回歸 R6～R8、E1-A／B／C 與 before／after workspace preflight。

### 門檻

| 項目 | 值 |
|---|---|
| 正向重複次數／瀏覽器 | 3 |
| 負向重複次數／瀏覽器 | 1 |
| barrier 上限 | 10,000 ms |
| operation timeout | 30,000 ms |
| open／save timeout | 180,000 ms |
| 每個 `EditorSession` 的 Worker generation 上限（＝最多 2 次崩潰／boundary 回復） | 3 |
> **2026-08-08 更正**：這句描述的「每頁」量**產品從未實作**；實際實作的是
> `EditorSession` 的 `maxWorkerGenerations`（預設 **3**）＝**同一個 session 的崩潰／
> boundary 回復次數**。**產品維持 3；「每頁」承諾撤除。**見
> [finding 026](../findings/026-generation-cap-means-two-different-things.md)
> 與 [finding 014](../findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)。

| 人工 IME 輪數 | 0 |

## 6. Evidence contract

```text
findings/evidence/sdk-e2/
  baseline/preflight-before.json
  baseline/preflight-after.json
  inventory/profile.json
  discovery/state-readback/<browser>.json      ← A2
  discovery/reissue/native-26-8/               ← A2-reissue（2.7 節）
  discovery/browser/<browser>/<fixture>/<attempt>/
  discovery/secondary/<browser>.json           ← A6
  roundtrip/summary.json
  regression/summary.json
  summary.json
```

- 每次失敗 attempt 獨立保存不覆寫；A2 的原始 payload 字串必須逐字保存。
- 每筆結果標 `observed`、`inferred` 或 `notValidated`；`pass:true` 不得掩蓋縮限。
- 可重現且影響 SDK／browser／core 邊界的新問題建立編號 finding；單純 runner／fixture 錯誤留 DEVLOG。

## 7. 執行順序與停止點

順序固定為 **A1 → A2 → A3 → A4 → A5 → A6 → A7**。

- A1 若 surface 不符先停止，不跑 mutation。
- **A2 不通過即停止**，不進 A3；這是本輪最主要推論的驗證點。
- **（2026-08-11 v11 新增）A3 另有一個前置條件**：第 4 節〈路線 C 未決事項〉必須先有決定。
  在那之前跑 A3 只會得到一批「跨狀態轉換都過、重複派送都 UNKNOWN」的資料，
  而那個 UNKNOWN 是設計未定，不是量測結果——**跑了也不能判定**。
- A3／A4 出現 silent mutation、completion 不可歸屬或 no-op 與遺失不可區分時，立即停止並建立 finding。
- A5 的 `state-crosstalk` 失敗等同 completion 不可歸屬，屬停止條件，不得以「實務上很少發生」略過。
- A6 失敗不停止。
- 不需新 core 修改時一路自動執行；若需要修改 LibreOffice core、擴大檔案範圍或新增外部依賴，另行取得確認。

## 8. 判定

**`GO_TO_E2_B`**：A2 三個狀態全部可靠抵達；A3 清單三態與樣式兩態在兩瀏覽器達門檻；A4、A5 全部通過；
A7 round-trip 與回歸通過。

**`PARTIAL_GO_TO_E2_B`**：清單或段落樣式其中一組成立、另一組必須縮限；或 heading 只能承諾單一層級；
或 `StyleApply` 字串因 locale 不穩定而只能承諾清單。縮限項目必須明列。

**`STOP_OR_RESCOPE`**：A2 狀態不抵達或不穩定；completion 不可歸屬（含 `state-crosstalk` 失敗）；
no-op 與遺失不可區分；清單切換造成結構 silent loss 或 teardown 阻塞；或補齊需要禁止 surface。

> **2026-08-11 v11 註**：`STOP_OR_RESCOPE` 的「no-op 與遺失不可區分」現在**已經有一個已知實例**
> （2.7 節（二））。這不表示 E2-A 現在就是 STOP——判定要有完整的 A3～A7 才成立，而 A3 尚未啟動。
> 它表示的是：若第 4 節〈路線 C 未決事項〉選了出路 1（接受低報），
> **選擇本身就落在這條 STOP 條款上**，那時要嘛改寫這條條款、要嘛接受 STOP。
> 兩者都可以，但不能當作沒看到。

## 9. 實作檔案

已新增（A2-native）：

- `wasm_sdk_probe/tools/e2_a_native_state_readback.cpp`
- `wasm_sdk_probe/tools/run_e2_a_native.sh`

已新增（A2-reissue，2026-08-11）：

- `wasm_sdk_probe/tools/e2_a_native_reissue.cpp`
- `wasm_sdk_probe/tools/run_e2_a_native_reissue.sh`
- `wasm_sdk_probe/tools/analyze_e2_a_native_reissue.py`（判定放在分析器，不放在 shell 摘要行，
  理由與 `run_e2_a_native.sh` 的前綴比對錯誤相同）

已修改（barrier 實作）：

- `wasm_sdk_probe/src/probe_engine.cpp`：新增 `.uno:DefaultBullet`／`.uno:DefaultNumbering`／
  `.uno:StyleApply` 的 typed state 解析、verified-format-state barrier，並依 finding 019 把段落樣式改派
  參數化 `.uno:StyleApply`。以 `OXSDK_E2_FORMAT_BARRIER` 隔離，E1 discovery 與 E1-B 產品組態不受影響
  （兩種組態均已重新編譯通過）。

預計新增（A2-wasm 之後）：

- `wasm_sdk_probe/e2/discovery-matrix-v1.json`
- `wasm_sdk_probe/e2/format-discovery-client.js`
- `wasm_sdk_probe/web/e2-format-discovery.html`
- `wasm_sdk_probe/web/e2-format-discovery-app.js`
- `wasm_sdk_probe/tools/build_e2_discovery_profile.py`
- `wasm_sdk_probe/tools/run_e2_discovery.py`
- `wasm_sdk_probe/tools/validate_e2_a.py`
- `wasm_sdk_probe/tests/test_e2_a.py`

預計修改：

- `wasm_sdk_probe/src/probe_engine.cpp`（狀態解析與 verified-format-state barrier）
- `wasm_sdk_probe/src/editor_discovery_api.h`（如需新增 typed 結果欄位）
- `wasm_sdk_probe/sdk/sdk-worker.js`（轉發 typed 格式狀態）
- `wasm_sdk_probe/Makefile`
- `wasm_sdk_probe/README.md`

LibreOffice core 不修改。

## 10. 執行結果

### 10.1 已完成：A1（部分）與 A2-native

- A2 原生 state-readback 通過。三個 state payload 全部抵達，並在無 mutation 的純 caret 移動時就會更新。
- 同一次 run 推翻 v1 前提，產生兩張編號 finding：
  [019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)（我方命令映射對到 UI 別名）與
  [020](../findings/020-lok-list-command-result-contradicts-document.md)（command result 與文件矛盾，上游候選）。
- barrier 實作已依實測改寫並三組態編譯通過；尚未在瀏覽器執行，因此仍屬**推論**。
- 回歸 R6～R8 與 E1-A／B／C 全過（退出碼 0）。R5 `writer-review`、E1-A `e1-editor-discovery`、
  E1-B `e1-editor-v1` 三個凍結 artifact hash 均與原記錄一致。
- 執行期間曾因 `make test-e1-b-static` 的相依鏈重建 `e1-editor-v1`，且新增狀態欄位未完全隔離，導致該產品
  profile 的 WASM 與行為被改動。已將全部新增項移入 `OXSDK_E2_FORMAT_BARRIER` 並逐字還原原函式，重建後
  hash 回到 E1-C 記錄值 `94b38437…`。詳見 [DEVLOG](../DEVLOG-2026-08-05-wasm-sdk-e2.md)。

### 10.2 已完成：A2-wasm（2026-08-05）

結果見 2.3 節，證據在 `findings/evidence/sdk-e2/discovery/state-readback/wasm/`。摘要：

- 主要問題答案是「會抵達」。barrier 的後置條件、歸屬計數器與 ODT postcondition 全部成立，
  且 finding 020 跨平台重現。上一輪標為「推論」的 barrier 行為，其後置條件部分升格為已觀察。
- 但 state 不追隨 caret（[finding 021](../findings/021-wasm-format-state-not-refreshed-by-caret-movement.md)），
  barrier 的前置條件因此可能讀到別段的值，`documented-state-noop` 有靜默誤判的路徑。

新增的隔離 artifact：`e2-format-discovery` profile。A2 的結果量自 WASM
`45f2372beb961907…`（Chrome attempt-02～06、Firefox attempt-02）；其後為 finding 021 歸因加入原始
STATE_CHANGED 計數器，同一 profile 重建為 `9b6e9c587e1224ed…`（Chrome attempt-07、Firefox
attempt-03）。兩個 hash 涵蓋的證據如上，不混用。R5 `writer-review`、E1-A `e1-editor-discovery`、
E1-B `e1-editor-v1` 三個凍結 artifact 的 hash 全程未變。

共用 `sdk/sdk-worker.js` **未修改**（hash 仍為 `9696c9ce…`）：E2 需要的三處 Worker 差異由
`tools/build_e2_discovery_profile.py` 對本 profile 的副本做精確替換，替換不中即建置失敗。
這是 `OXSDK_E2_FORMAT_BARRIER` 在 JS 側的對應做法——讓其他 profile 仍能從現有原始碼重建出
E1-C 記錄的 hash。

#### 本輪修正的兩個自身量測缺陷

1. **第一版 harness 只用 `setTextSelection(RESET)` 定位、且只記錄 format-state 事件。** 於是
   「狀態沒抵達」與「caret 根本沒移動」無法區分，首次 Chrome run 得到全 null 的假否定。
   已補上 public `click()` 定位、全事件記錄與 set-bold 正向對照。
2. **`trackedCaret` 判準太鬆。** 原本只要求「值在各位置間有差異」，而 null→已知的轉變就能滿足它，
   於是一份「狀態從不追隨 caret」的資料被判成 `pass:true`。已改為以 fixture 結構為真值的
   逐位置檢查，並要求該位置有新鮮事件支持。

另修正一個猜出來的常數：`heading-on` 的 postcondition 原本期望產生 `<text:h>` 元素，實測是
`.uno:StyleApply` 對既有 `<text:p>` 套用 `Heading_20_1` 段落樣式。期望值錯，不是產品錯；
已依實測改正，不是放寬。

### 10.3 已完成：finding 021 歸因（2026-08-05）

三步歸因見 2.4 節：四種移動方法的原生對照 → 原始 callback 計數 → scheduler 推進實驗。
**結論：我方 engine 迴圈未推進 VCL scheduler，非上游問題。**

新增隔離 artifact：`e2-scheduler-attribution` profile（E2 組態＋`OXSDK_FINDING_016_SCHEDULER_PROBE`）。
歸因與修法期間兩個 E2 profile 都隨程式碼演進重建過數次，最終為 `e2-format-discovery`
`044975a73cc3c5a3…`、`e2-scheduler-attribution` `7c5b8e5c595edec6…`；每份 evidence 的
`manifest.diagnostic.wasmSha256` 記錄了它實際跑在哪個 build 上，不以最終 hash 回溯代表早期結果。

**注意：`e2-format-discovery` 的派送語意已改變。** 加入 fail-closed 之後，該 profile 沒有 refresh
能力，所以五個格式動作都會回 `EDITOR_FORMAT_STATE_UNAVAILABLE`。10.2 節記錄的 5/5 成立結果是
修法前（`45f2372b…`）量的；修法後的成立結果在 `e2-scheduler-attribution`。三個凍結 release
artifact 全程未受影響。

新增檔案：`tools/e2_a_native_caret_tracking.cpp`、`tools/run_e2_a_native_caret.sh`、
`tools/analyze_e2_a_native_caret.py`。判定邏輯放在 analyzer 而不是 shell 摘要行，理由與
上一輪 `run_e2_a_native.sh` 的前綴比對錯誤相同：摘要行本身會錯，且錯得不易發現。

本輪 analyzer 也修正了自身的一個猜測：第一版斷言 heading 的 `inList` 應為 false，實測原生與
WASM 都回報 true（且原生同時回報 `style='Heading 1'`，與 outline numbering 一致）。改為只判定
fixture 保證會變的兩個轉換（進清單、出清單），不對 heading 的清單狀態做斷言。

### 10.7 已完成：A3 正向矩陣（2026-08-11）

判定：**`A3_PASS`**。摘要 `findings/evidence/sdk-e2/summary.json`，
證據樹 `findings/evidence/sdk-e2/discovery/browser/<browser>/<fixture>/<attempt>/`。

| | 每格要求 | 實得 |
|---|---|---|
| chrome × styled-list／multi-paragraph／plain-grapheme | 3 | 3／3／3 全通過 |
| firefox × 同上 | 3 | 3／3／3 全通過 |

**18 次 run × 5 個派送＝90 次**，每次都要同時滿足四項才算通過：
completion 為 `verified-format-readback`、**`changed` 未被宣稱**（null）、
`restoreConfirmed` 為 true、**存檔 ODT 的後置條件相符**。
每一步各自判定，不是只看循環結尾——中途走錯再被改回來不算通過。

`table-boundary` 未列入 A3，它是 A5 的負向案例；摘要以 `fixturesDeferredToA5`
明寫，不是省略。

**validator 以矩陣展開必要格，不是列舉找得到的 run**：沒跑過的 fixture 會被標成
`missing` 而不是靜靜消失，`A3_NOT_RUN`／`A3_PARTIAL_COVERAGE`／`A3_PASS` 三態分開。
突變控制：把 `cycle-list-ordered` 的期望改成 bullet，18 次 run 全數轉為失敗並逐格指名。

**清單種類要逐層讀。** `styled-list` 的 `L1` 是**混合定義**（level 1 為 bullet、
level 2／3 為 number），第一版 validator 問「這個樣式含不含 numbered level」，
於是把一份正確的 bullet 清單讀成 number。改為讀段落所在層級的定義。
同一個順序錯誤在 `analyze_e2_a_native_reissue.py` 也存在，一併修掉並以修好的判讀
重跑原生已存證據——**九個案例判定完全不變**。

**styled-list 的錨點緊鄰既有清單，套用清單會與鄰居合併**；另外兩份 fixture 沒有清單，
量的是同一個動作但沒有這個混淆。三份都通過。

### 10.8 已完成：A4 重複派送（2026-08-11）

判定：**`A4_PASS`**。證據樹 `findings/evidence/sdk-e2/discovery/repeat/<browser>/<fixture>/<attempt>/`，
摘要在 `summary.json` 的 `a4` 區塊。

每個 action 先驅動到目標一次，再在**已經在目標狀態的段落上**連按兩次。
2 瀏覽器 × 3 fixture × 3 次 × 15 個派送＝**270 次**，全部通過同一組四項條件
（completion、`changed` 未宣稱、還原經確認、存檔 ODT 相符）。

這一輪同時答兩題，而且答案互相獨立：

- **冪等**：重複派送後文件停在目標。toggle 會在這裡反轉——2.7 節實測不帶參數的
  `.uno:DefaultBullet` 正是如此。
- **無聲 no-op**：core 在值沒變時不廣播，barrier 仍然完成而非逾時。
  第 4 節〈路線 C 未決事項〉的缺口到此關閉，且是用矩陣證據關閉的。

突變控制：把 `list-unordered-repeat-1` 的期望改成「已離開清單」（也就是 toggle 的行為），
19 次 run 全數轉為失敗。

### 10.9 已完成：A5 負向與邊界（2026-08-11）

判定：**`A5_PASS`**。證據樹 `findings/evidence/sdk-e2/discovery/negative/<browser>/<fixture>/`，
摘要在 `summary.json` 的 `a5` 區塊。2 瀏覽器 × **4** fixture（含 `table-boundary`）
× 6 個案例，綁定引擎 `25761ff0…`。

**A5 在此之前沒有任何判定**——案例跑完是人工看的。一個沒人判的負向套件，
形狀和「不會失敗的檢查」一樣，所以它現在走與 A3／A4 相同的機制。

`state-crosstalk` 的判準改成讀 **readback markup 自己的文字**：序列化器會寫出段落內容，
所以「barrier 讀到哪一段」是直接看得見的，不必靠結構標籤——本規格的舊判準正是敗在
兩種答案都會通過（[finding 033](../findings/033-readback-barrier-read-wherever-the-caret-went.md)）。

鑑別控制不是合成的，是既有證據自己給的：同一條判準在**現行 build 11/11 通過、
在它之前的三個 build 0/9**。

修法本身見 finding 033。一句話：**關掉 crosstalk 的是 BUSY 閘，不是 commandName 歸屬**
——`selectionBeforeResultCount` 每次都是 0，歸屬那一層沒有攔到任何東西，
它是縱深防禦，本規格不宣稱它修好了什麼。

### 10.10 目前總結（2026-08-11）

| 相位 | 判定 | 綁定證據 |
|---|---|---|
| A3 | **A3_PASS** | 21 runs／105 次派送 |
| A4 | **A4_PASS** | 18 runs／270 次派送 |
| A5 | **A5_PASS** | 11 runs／58 個案例 |
| A6 | 未執行 | — |
| A7 | 未執行 | — |

**E2-A 仍無總判定**：第 8 節要求 A6／A7 也有結果。

兩個未結的引擎缺口（都已記在 finding 033，都不擋 A3～A5 的判定）：

1. ~~**format barrier 沒有引擎側期限。**~~ **2026-08-11 已修**，見下方 10.11。
2. **座標殘留仍在。** 還原點是派送**前**擷取的文件座標，而派送本身改變幾何。
   BUSY 閘縮小可達性，沒有消除它。**containment 檢查（10.11）縮小了它的後果**
   ——選取縱向範圍不含還原點時改為 typed 失敗——但沒有消除成因。

### 10.11 barrier 選取步驟改版與兩條覆蓋軸（2026-08-11，引擎 `38168306…`）

上表三個 PASS 原本綁定 `25761ff0…`。引擎改動後**全部重跑重綁**，見 10.12。

**改了什麼（四項，同一個 build）：**

1. 選取步驟由 `.uno:GoToStartOfPara` ＋ `.uno:EndOfParaSel` 改為單一 `.uno:SelectText`。
2. `parseFormatReadback` 加多段防護：第二個 block tag 或第二個 `li` → `multiBlock` → fail closed。
3. containment 檢查：選取的縱向範圍必須包含還原點。
4. 三個 awaiting stage 各有 5000 ms 期限，進入時重新起算，**永不判成功**。

失敗碼：期限／containment／`multiBlock` 一律 `MUTATION_OUTCOME_UNKNOWN`
（呼叫端的決定在三者都相同：不要重放）；診斷差異放 `formatBarrier.failureShape`。
`EDITOR_FORMAT_POSTCONDITION_FAILED` 收窄為「乾淨讀到單一段落、但不在目標狀態」。

**為什麼（finding 034）：** `.uno:GoToStartOfPara` 不冪等，游標已在 offset 0 時會跳到上一段。
既有 375 次判定派送**全部落在 offset `Len()`**——現行序列唯一正確的位置。
`caretAtAnchor` 放在 `rectangle.x + width`，search 把游標留在命中處之後，兩邊一致。

**兩條本來不存在的覆蓋軸（矩陣第 3 筆 revision）：**

- `caretOffsetCoverage`——非空段落 × {0, 中間, `Len`} ＋ 空段落 × {文件中段, 文件末段}。
- `paragraphContentCoverage`——{純 ASCII 無 run, 行內字元格式, 中日韓文字}。

第二條是修法逼出來的：改對之後 barrier 開始讀對的段落，而那一段帶 `<b>`／`<i>`，
於是撞上 [finding 035](../findings/035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)
——readback 的封閉標籤集只收 `ul/ol/li/h1/p`，**任何有字元格式或含中文的段落都 fail closed**
（序列化器把中日韓 run 包在 `<font><span>` 裡）。既有缺陷，兩個 build 行為相同，
**本次未修**：它是下一個 build 加下一次重掃，混進同一個 artifact 會讓兩個改動都無法
對應到自己的證據（finding 027）。

因此 `paragraphContentCoverage` 的後兩欄**沒有通過的格子**，不得當作已覆蓋報告。

**空段落是規格層收窄，不是實作缺陷。** 空段落沒有可選取的內容，任何以游標移動為基礎的
選取都定址不到它。路線 C 的 readback 驗證定義在非空段落上；空段落的 mutation 一律回報
typed 的不可驗證，**永不回報成功**。

### 10.4 尚未執行

~~A3～A7 尚未執行。~~ ~~**A3（10.7 節）與 A4（10.8 節）已完成，皆 PASS；A5～A7 尚未執行。**~~ **2026-08-11 再更新：A5（10.9 節）亦已完成且 PASS；A6／A7 尚未執行，見 10.10 節。**
以下 08-06 的原文保留：A3～A7 尚未執行。**A3 仍不啟動**：finding 021 已歸因且產品級主迴圈候選已實測可跑
（2.6 節），但 caret 移動後的 freshness 來源未定（PEI 與活迴圈的行為差異未歸因），
且推進點若進入共用路徑需先跑完整回歸。E2-A 目前**沒有**判定；第 8 節的三個結果都還不成立。

> **2026-08-11 v11 更新：擋住 A3 的理由換了一個。** 產品路線 C 定案後，上面那個
> freshness 問題**不再是 A3 的前置**——路線 C 根本不讀前置狀態。取而代之的是 2.7 節
> 實測出來的新前置：合法 no-op 沒有後置條件可等（第 4 節〈路線 C 未決事項〉）。
>
> 已完成、與出路選擇無關的部分：派送形式改為參數化 explicit mode（2.7 節（一）），
> `e2-format-discovery` 已重建為 `abf3598f…`，三個凍結 artifact 未受影響。
>
> **2026-08-11 更正（[finding 032](../findings/032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md)）**：
> 本段原本寫「`OXSDK_E2_FORMAT_BARRIER` 關閉時 E1-B 組態的 `probe_engine.o` 逐位元不變」。
> **那個檢查不可靠**——同源同旗標連編 8 次會得到兩種目的檔（各 4 次、固定差 37 bytes），
> 通過與否有一半是運氣。隔離改以**前置處理後的翻譯單元**比對驗證，
> 這才是直接證明「該組態看到的原始碼一模一樣」的東西，且不受 codegen 不確定性影響：
> 與 `HEAD` 版本在 E1-B 組態下 **4,355,327 bytes 逐位元相同**。結論不變，理由換掉。`tests/test_e2_profile.py` 新增三項釘住派送形式，
> 突變（拿掉 `On` 參數）證明會失敗。

### 10.5 順帶記錄（與 E2 無因果關係）

`src/probe_engine.cpp` 的 `struct SelectionReadback` 定義在 `#ifdef OXSDK_EDITOR_DISCOVERY` 區塊內，但
`readSelection()` 與 `handleGetSelection()` 在區塊外。因此不帶 `-DOXSDK_EDITOR_DISCOVERY` 編譯（即 R5
`writer-review`／`writer-reader` 的組態）會失敗於 `unknown type name 'SelectionReadback'`。這是上一輪
finding 017 修復留下的既有狀況，不是本輪造成；與
[finding 017](../findings/017-lok-collapsed-selection-readback.md) 已記錄的 boost include 問題並列，
同樣使 R5 profile 目前無法從現有 source 重建。凍結的 R5 artifact 未受影響。

### 10.6 已完成：finding 021 候選 1 主迴圈實測（2026-08-06）

結果見 2.6 節。新增隔離 artifact：`e2-mainloop-attribution` profile（E2 組態＋
`OXSDK_MAINLOOP_ENGINE`，無 scheduler drain 能力——「無 unit hook 可用」是排除法的
一部分，`tests/test_e2_profile.py` 有測試釘住）。歸因期間隨程式碼演進重建多次，最終
sound 語意 build 為 `a696f0d61347e6da…`；每份 evidence 的 `manifest.diagnostic.wasmSha256`
記錄實跑 build，不以最終 hash 回溯代表早期結果（Chrome attempt-03 跑在 idle-poll 清
stale 的過渡 build 上，僅作迴圈機制示範）。

工具面：`run_e2_discovery.py` 與 harness 新增 `mainloop-attribution` mode（refresh 步驟
是有界等待 typed staleness，不派送任何 pump）；`build_e2_discovery_profile.py` 對三個 E2
scope 共用同一份 worker patch，manifest 新增 `engineLoop` 診斷欄位。engine 的
`OXSDK_MAINLOOP_ENGINE` 區塊以旗標關閉時 E1-B 組態目的檔逐位元不變驗證
（重編對比既有 `build/e1/editor-v1/probe_engine.o`），凍結 artifact 未受影響。
> **2026-08-11 註（[finding 032](../findings/032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md)）**：
> 這句用的是目的檔逐位元比對，**該方法後來被證明有一半機率通過**。
> 本次結論未被推翻，但它的證據力要照這個折扣讀；要重新確認請改比對前置處理後的翻譯單元。
瀏覽器 console 的 `oxsdk-mainloop:` 診斷（poll／dispatch／tick-alive／poll-pending）
是本輪歸因的主要儀器；engine pthread 的 stderr 到不了可捕捉的 console，診斷一律走
`MAIN_THREAD_EM_ASM`。

## 11. 修訂紀錄

| 日期 | 內容 |
|---|---|
| 2026-08-05 | v1。建立 verified-format-state barrier discovery 規格、凍結矩陣、A2 先決條件與停止點。 |
| 2026-08-05 | v2。A2-native 完成並推翻 v1 前提；barrier 改為 command result（歸屬）＋state（真值）雙條件，段落樣式改派參數化 `.uno:StyleApply`；建立 finding 019／020。 |
| 2026-08-05 | v3。A2-wasm 完成：三個 payload 抵達、後置條件與歸屬計數器成立、finding 020 跨平台重現；但 state 不追隨 caret，建立 finding 021，A2 判為部分通過、A3 暫不啟動。記錄本輪兩個自身量測缺陷與一個猜錯的 postcondition 常數。 |
| 2026-08-05 | v4。finding 021 歸因完成：原生四種移動方法全部正常、失敗位置的 watched payload 抵達數為 0，一度判為 WASM 特定、上游候選。A3 仍不啟動。 |
| 2026-08-05 | v5。scheduler 推進實驗撤回上游分類：推排程後四個位置狀態全部正確且與原生一致，成因是我方 engine 迴圈未推進 VCL scheduler。修法改為讓狀態可靠而非繞開它；產品機制未定，A3 仍不啟動。 |
| 2026-08-05 | v6。量出 `Application::Reschedule` 在此組態為 no-op、callback 在 pump 返回後才 flush；據此在 discovery profile 實作 fail-closed ＋ host 驅動刷新並驗證（無刷新 5/5 typed 拒絕、有刷新 5/5 成立且存檔證實，兩瀏覽器）。產品推進機制仍未定，A3 不啟動。 |
| 2026-08-06 | v7。finding 021 候選 1 實測：unipoll ＋ `runLoop` 註冊 ＋ `Application::Execute()` 的產品級主迴圈在兩瀏覽器可跑（新隔離 profile `e2-mainloop-attribution`），命令派送搬進 poll callback；但同輪否證「迴圈帶來 freshness」——caret 移後重算根本未被排程，「idle-poll 即清 stale」不健全已回退，sound 語意下 5/5 typed 拒絕、檔案零變動。卡點重定義為 PEI 與活迴圈的行為差異，A3 仍不啟動。 |
| 2026-08-06 | v8。判別實驗一（複合 profile `e2-mainloop-pei-attribution`）：PEI 在活迴圈下有效、修法完整矩陣重現（兩瀏覽器 5/5 verified ＋ postcondition 5/5），排除 Desktop::Main 初始化假設；判別實驗二（真游標 dispatch nudge）：不觸發重算，排除定位路徑假設。缺口定為 PEI 語意（每 tick ImplYield vs 迴圈到靜止），產品出路收斂為上游報告。A3 在有受支援 pump 前不啟動。 |
| 2026-08-06 | v9（覆核修訂）。2.6 節結果二改寫：watched payload 在活迴圈下**會抵達但落後一個定位點**（原寫「零抵達／未被排程」對最終 build 的證據為假，該讀數屬過渡 build），缺口正確描述為收斂／順序問題；撤回 `GetMostUrgentTaskPriority=-1` 作為證據（取樣點使該值恆為 -1）；補記 `loop()` 與 PEI 差兩個參數。新增結果三：回退後的 fail-closed 仍擋不住落後一格的 payload，**未修補**，A3 的前提因此多一項。 |
| 2026-08-06 | v10（二次覆核＋產品決定）。撤回 v9 追加的「結果三：落後一格的 payload 會清掉 stale 旗標」——engine 旗標在兩瀏覽器全部 search 列都正確為 stale，且 `updateEditorFormatState` 先清旗標才發事件，誤因是把 harness 的 `fresh`（計數起點在定位之前）當成 engine 判準；殘留缺口改寫為逐欄位世代標記（推論，未觀測到實例）。更正「沒有受支援的刷新入口」：`Scheduler::ProcessEventsToIdle()` 是公開 API 且有產品呼叫者，只有 C 包裝 `unit_lok_process_events_to_idle` 是 unit-test 掛鉤。使用者決定不送上游，產品路線定為 **C：不讀前置狀態**（closed action 直接派送，只用後置條件判定，移除 `documented-state-noop`），路線 A（產品自行 pump）延後而非否決。 |
| 2026-08-08 | 更正。更正 Worker generation 上限的**語意**：規格原本寫「每頁」，但產品唯一實作的是每個 `EditorSession` 的崩潰／boundary 回復次數（`maxWorkerGenerations`，預設 3）。**產品維持 3，「每頁」承諾撤除**（無實作，且 finding 014 撤回後無已量測理由）。條文與註記已就地修訂；未動任何閘門，判定不變。見 finding 026。 |
| 2026-08-11 | v11（路線 C 的前置條件契約）。把 v10 的產品決定落成條文：第 4 節作廢前置狀態讀取與 `documented-state-noop`（原文保留於引用區），A4 由「no-op 與 fail-closed」改寫為「重複派送」。新增 2.7 節，記錄路線 C 兩個前提的原生實測（[finding 030](../findings/030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)）：（一）不帶參數的 `.uno:DefaultBullet`／`.uno:DefaultNumbering` **是 toggle**，第二次按下會反轉，帶 `On=true` 則四案例全為 setter（含跨種類轉換）——已修，engine 改派參數化形式，測試釘住並通過突變控制，E1-B 目的檔逐位元不變；（二）**值沒變就沒有 STATE_CHANGED**，合法 no-op 因此沒有後置條件可等，barrier 逾時成 `MUTATION_OUTCOME_UNKNOWN`。（二）尚未有解，第 4 節新增〈路線 C 未決事項〉列四條出路並註明本規格不預設；第 7 節因此給 A3 加上「未決事項先有決定」的前置，第 8 節註明出路 1 本身就落在 STOP 條款上。**擋住 A3 的理由由 freshness 換成 no-op 的可判定性**，10.4 節已就地更新。 |
| 2026-08-11 | v12（crosstalk 關閉＋`table-boundary` 期望改寫）。[finding 033](../findings/033-readback-barrier-read-wherever-the-caret-went.md) 的修法實作並實測關閉：barrier in-flight 期間 `search`／`editor-select` 一律 `BUSY`（`.uno:ExecuteSearch` **會選起命中處**，它是 caret mover，也是 crosstalk 案例實際走的路），`EndOfParaSel` 以 `notify=true` 派送且推進條件比對 `commandName`。**關掉它的是 BUSY 閘**——`selectionBeforeResultCount` 全為 0，歸屬那一層在這批證據裡沒有攔到東西，本規格不宣稱它修好了什麼。附帶量到：`notify` 是兩條派送路徑，只改一個命令會使 `EndOfParaSel` 先於 `GoToStartOfPara` 生效（readback 讀到 `<p>D-END</p>`，段落實為 `E1-STYLED-END`），游標在段尾時選取為空、barrier 永久等待。A5 表格的 `table-boundary` 期望由「typed 拒絕，之後 fresh Worker」改為「typed 結果，且文件必須同意」——儲存格內的段落在 26.8 **接受** `set-list-unordered`，原期望是寫矩陣時的預期而非量到的行為；修訂已附範圍限制。A5 首次覆蓋兩瀏覽器 × 四 fixture，**Firefox 負向輪由零變成有**。 |
| 2026-08-11 | v12 續（A5 判定與 artifact 重綁）。A5 首次有判定（10.9 節）：`validate_e2_a.py` 之前只判 A3／A4，A5 跑完是人工看的。`state-crosstalk` 改以 readback markup 自己的文字判定，鑑別控制取自既有證據——現行 build 11/11、之前三個 build 0/9。引擎改動使 A3／A4 既有證據變成別的 artifact 的證據（finding 027 規則），兩瀏覽器 × 三 fixture 全數重跑：**A3_PASS（105 次派送）、A4_PASS（270 次派送）、A5_PASS（兩瀏覽器 × 四 fixture）**，全部綁定 `25761ff0…`。新增 10.10 節總結，並列出兩個未結的引擎缺口（barrier 無引擎側期限、座標殘留）。矩陣 `status` 由 `A2-complete-A3-ready-…` 改為 `A3-A4-A5-pass-…-A6-A7-not-run`，附 `statusProvenance`。另修 summary 的 `boundToCurrentBuild` 欄位名——它印 false 卻與 `A3_PASS` 並排，同一份報告的兩個欄位互相矛盾；它問的一直是「樹裡每一次 run 都是現行 build 嗎」，改名為 `allEvidenceIsCurrentBuild` 並補上 `verdictCountsOnlyCurrentBuild`。 |
