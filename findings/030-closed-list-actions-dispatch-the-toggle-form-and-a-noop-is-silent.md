# 030 — 封閉清單動作派送的是 toggle 形式，而合法的 no-op 不會廣播任何狀態

| | |
|---|---|
| **狀態** | **已確認（原生實測＋原始碼對照）／產品路線 C 需修訂** |
| **Bugzilla** | — |
| **發現日** | 2026-08-11 |
| **嚴重度** | 嚴重（缺陷一使封閉列舉在第二次按下時反轉；缺陷二使 E2-A 判定落入自訂的 STOP 條件） |
| **可重現** | 100%（原生 26.8，一次 run 內 bare 與 param 兩組對照，每組三次連按） |
| **是否上游** | 缺陷一**否**（我方派送形式）；缺陷二**否**（core 的既有語意，我方的判定設計不能建立在它之上） |

## 摘要

2026-08-06 的產品決定把路線定為 **C：不讀前置狀態**——封閉 action 一律直接派送，判定只用後置條件。
這條路線靠一個從未量測的前提：`probe_engine.cpp:2688` 的註解寫「dispatching unconditionally is
idempotent for these commands」。本輪原生實測**否證**了它，並帶出第二個更難處理的問題。

**缺陷一：兩個命令是 toggle，不是 setter。** 不帶參數派送 `.uno:DefaultBullet`／`.uno:DefaultNumbering`
時，core 取的是 `!SelectionHasBullet()`——也就是**現況的相反**。第二次按下 `set-list-unordered`
會把段落踢出清單。SPEC E2-000:140 明寫「以 explicit closed enum 設定，不是 toggle」，
bare 形式做不到這件事。

**缺陷二：值沒變就沒有 STATE_CHANGED。** 已經在目標狀態時再按一次，文件正確、
command result 照常抵達、但**沒有任何被監看的 state payload**。E2-A 的 barrier 以
「命令結果歸屬 ＋ state 後置條件」為完成條件，因此會逾時成 `MUTATION_OUTCOME_UNKNOWN`——
文件其實是對的。這正是 SPEC E2-A 第 8 節列為 STOP 的「no-op 與遺失不可區分」。

兩者都不是路線 C 造成的新行為，而是**路線 C 移除前置條件讀取後才顯露**：舊設計的
`alreadyAtTarget → documented-state-noop` 短路，恰好同時遮住了這兩件事。

## 最小重現

原生 26.8，同一段落（以錨點文字定位），先置入相反狀態，再連按三次同一動作，每次派送後存 ODT：

```text
bare  set-list-unordered   .uno:DefaultBullet（無參數）
      reset  → 不在清單
      issue1 → bullet 清單     state: .uno:DefaultBullet=true
      issue2 → 不在清單        state: .uno:DefaultBullet=false      ← 反轉
      issue3 → bullet 清單     state: .uno:DefaultBullet=true

param set-list-unordered   .uno:DefaultBullet {"On":true}
      reset  → 不在清單
      issue1 → bullet 清單     state: .uno:DefaultBullet=true
      issue2 → bullet 清單     state: （無）                        ← 正確但無聲
      issue3 → bullet 清單     state: （無）
```

重跑：`wasm_sdk_probe/tools/run_e2_a_native_reissue.sh`

## 證據

- `findings/evidence/sdk-e2/discovery/reissue/native-26-8/`——原始 callback 串流、
  九個案例各四份後置條件 ODT、`analysis.json`、`cases.json`、探針與分析器原始碼。
- **判定一律讀存檔 ODT，不讀 callback。** finding 020 已證明 `success`／`wasModified`
  會說謊，被檢驗的東西不能同時當證據。

九個案例的判定（`analysis.json` 的 `verdicts`）：

| 組 | 案例 | 派送 | 判定 |
|---|---|---|---|
| bare | `set-list-unordered` | `.uno:DefaultBullet` | **toggle** |
| bare | `set-list-ordered` | `.uno:DefaultNumbering` | **toggle** |
| bare | `set-list-none` | `.uno:RemoveBullets` | setter |
| bare | `set-paragraph-heading` | `.uno:StyleApply`＋`Heading 1` | setter |
| bare | `set-paragraph-body` | `.uno:StyleApply`＋`Text body` | setter |
| param | `set-list-unordered` | `.uno:DefaultBullet`＋`On=true` | setter |
| param | `set-list-ordered` | `.uno:DefaultNumbering`＋`On=true` | setter |
| param | `set-list-unordered-from-ordered` | 同上（起點為有序清單） | setter |
| param | `set-list-none-from-ordered` | `.uno:RemoveBullets`（起點為有序清單） | setter |

**參數化形式連跨種類轉換都成立**（有序清單→無序清單，且停在那裡），所以
`set-list(none｜unordered｜ordered)` 這個三態封閉列舉**做得到**——用對派送形式就做得到。

`silentRepeats`：九個案例的 `issue2`／`issue3` 全部零 watched payload，**無一例外**。
command result 則九個案例每次派送都有，且帶正確的 `commandName`。

## 分析

### 缺陷一：參數存在，我方沒送

`svx/sdi/svx.sdi:2251`（`DefaultBullet` → `FN_NUM_BULLET_ON`）與 `:4985`
（`DefaultNumbering` → `FN_NUM_NUMBERING_ON`）都宣告了一個 `SfxBoolItem On FN_PARAM_1`。
`sw/source/uibase/shells/txtnum.cxx:81-108` 的處理是：

```cpp
const SfxBoolItem* pItem = rReq.GetArg<SfxBoolItem>(FN_PARAM_1);
bool bMode = !GetShell().SelectionHasBullet();   // #i29560#
if ( pItem )
    bMode = pItem->GetValue();
```

有參數就是 explicit mode，沒有就是 toggle。**這是既有且有文件的 core 行為，不是上游缺陷**。

我方 `src/probe_engine.cpp:2569` 的 `startFormatBarrierActionResolved()` 只設
`barrier.command = ".uno:DefaultBullet"`，`barrier.arguments` 留空，派送的就是 toggle 形式。

**這與 finding 019 是同一個形狀**：那次是把段落樣式對到沒有 slot 的 UI 別名，這次是送了有 slot
但缺參數的形式。兩次的修法也相同——送有文件的參數化命令。

**目前是潛伏而非正在發生**（此判斷為推論，理由如下）：現行 discovery profile 仍是路線 B 的
fail-closed，只有在「狀態已知且不等於目標」時才派送，而那正好是 toggle 會做對事的情況。
唯一的現行活路是 finding 021 v10 記錄的**逐欄位世代標記**缺口（一個旗標守五個欄位，
屬推論、未觀測到實例）。**路線 C 一旦落地，遮罩就消失。**

### 缺陷二：值沒變就沒有廣播

core 的 status 廣播只在值改變時送出，這是 SfxBindings 的既有語意，不是缺陷。
問題出在**我方的判定設計**：E2-A 第 4 節把 completion 定義為

> (a) command result 的 commandName 等於本次派送的命令；**且**
> (b) 對應命令的 state payload 值等於期望值。

(b) 在合法 no-op 時永遠不會到。路線 B 靠 `alreadyAtTarget` 在派送**之前**就攔下來，所以
這條路走不到；路線 C 移除了那個攔截，於是每一次「按第二下」都會逾時成
`MUTATION_OUTCOME_UNKNOWN`。

值得說清楚的是**這不是誤報，是低報**：文件是對的，我方宣稱不知道。fail-closed 的方向正確，
但代價是使用者每次重複按下都拿到一個「結果未知」，而 SPEC E2-A 第 8 節把
「no-op 與遺失不可區分」列為 `STOP_OR_RESCOPE`。**只修缺陷一不會讓 A3 可判定**。

### 出路（未決，需產品決定）

1. **接受低報**：維持 fail-closed，重複按下回 `MUTATION_OUTCOME_UNKNOWN`。誠實、零新機制，
   但把「不知道」變成常態讀數，等於讓判定訊號變鈍。
2. **路線 A（自行推進 scheduler）**：v10 已更正「沒有受支援入口」不成立——
   `Scheduler::ProcessEventsToIdle()` 是公開 API（`include/vcl/scheduler.hxx:65`）且有產品呼叫者。
   狀態可信之後，前置條件與 no-op 都能再次區分。代價是進入共用路徑需跑完整回歸（finding 012 相鄰風險）。
3. **後置條件改讀文件而非讀廣播**：不靠 callback，派送後直接讀該段落的實際格式。
   最誠實，但需要一個目前不存在的 readback 能力，得自成一輪 discovery。
   **← 使用者 2026-08-11 選定；可行性已實測，見本節末。**
4. **只用 command result 當完成條件**：歸屬有了（實測九案例每次都到），但真值沒有——
   這正是 E2-A 第 4 節當初明確拒絕的做法（finding 020）。**不建議**，列出是為了說明它被考慮過。

**本輪不替使用者決定**。可以先做的是與路線無關的部分：把派送改成參數化形式（缺陷一），
那在四條出路裡都是必要的。

### 出路 3 已選定，且可行性已實測（2026-08-11）

使用者選了出路 3：**後置條件改讀文件**。動手前先量它存不存在——這是 A2 的同一條紀律，
不然就是把 barrier 蓋在猜測上。證據：
[`sdk-e2/discovery/format-readback/native-26-8/`](evidence/sdk-e2/discovery/format-readback/native-26-8/)。

`getCommandValues` 先以讀原始碼排除（見上）。剩下的候選是 selection transferable：
`doc_getTextSelection`（`desktop/source/lib/init.cxx:5912`）把選取交給剪貼簿機制，
所以 `text/html` 應該會帶出結構。實測結果：

| 情境 | `text/html` 讀到 |
|---|---|
| heading | `<h1 class="western">…</h1>` |
| body 段落 | `<p style="line-height: 100%; …">…</p>` |
| 無序清單 | `<ul><li><p …>…</p></li></ul>` |
| 有序清單 | `<ol><li><p …>…</p></li></ol>` |
| 離開清單後 | `<p …>…</p>` |

**五個 closed action 全部可分，而且讀數跟著 mutation 走**（五次派送後的讀數都與派送內容相符，
存檔 ODT 一致）。**而且它與語系無關**——分辨用的是 HTML 結構（`h1`／`ul`／`ol`／`li`），
不是 UI 名稱，所以段落樣式那兩個動作的 [finding 031](031-styleapply-postcondition-compares-a-localized-ui-name.md)
曝險也一併解掉。

**兩個代價是量出來的，不是猜的：**

1. **游標塌陷時讀不到任何東西**（selection type 0、0 bytes）。barrier 必須先選起整段
   （`.uno:GoToStartOfPara` → `.uno:EndOfParaSel`）才讀得到。那會動到使用者的選取，
   讀完要還原，而**還原本身也要被驗證**——不能只是「做了就假設成功」。
2. **`Text body` 與預設樣式都序列化成 `<p>`**。這個讀法分得出「是不是 heading」，
   分不出「是 Text body 還是 Standard」。也就是說用它做 `set-paragraph-body` 的後置條件，
   **宣稱會比現在的 `.uno:StyleApply=Body Text` 弱**。SPEC E2-000 的承諾是
   `set-paragraph-style(body｜heading)` 兩態，「不是 heading」剛好夠用——
   但這是縮限，要寫進判定，不能當作沒發生。

另有一項要先想清楚再實作：這串 HTML 是**序列化器的輸出，不是有文件的契約**。
整串比對等於把序列化器釘成 ABI，跨 LibreOffice 版本可能變。這一項**尚未驗證**。

### 一條線索（**推論，未實測**）

「值沒變就不廣播」在上游本身就被當成要繞開的東西：`txtnum.cxx:100-106` 在
`bNewResult != bMode` 時，會用 `rBindings.SetState()` **先送反值再送真值**，
硬把 payload 逼出來給 toolbar 更新。也就是說 core 有強制重播的手段
（`SfxBindings::InvalidateAll(bool bWithMsg)`、`SfxLokHelper::sendUnoStatus()`）。

但這條線索**不構成第五條出路**：強制重播出來的 payload 一樣要靠 scheduler 才 flush 得出去，
繞回路線 A 的同一個代價。列在這裡是為了讓「no-op 沒有後置條件」不被誤讀成 core 的疏漏——
它是既有語意，而且上游自己也要為它寫繞法。

另外掃過 `getCommandValues` 的實作（`sw/source/uibase/uno/loktxdoc.cxx`）：
支援的是 form field／bookmark／section／`ExtractDocumentStructures`（content control、
chart、doc property、redline）等，**沒有**游標所在段落的清單／樣式狀態。
出路 3 需要的 readback 確實不存在於現有 LOK 介面——這一項是查過原始碼的，不是推測。

## 修法後的重跑（2026-08-11）

engine 改派參數化形式後重建兩個 E2 profile：`e2-format-discovery` `abf3598f…`、
`e2-scheduler-attribution` `38d15ed4…`。以 `--mode scheduler-attribution`
兩瀏覽器各跑一輪（Chrome 150.0.7871.128、Firefox 153.0.1）：

| | Chrome | Firefox |
|---|---|---|
| 五個 action 的 completion | 全為 `verified-format-state`、`changed:true` | 同 |
| `documentPostconditions` | 5/5 `allMet:true` | 5/5 `allMet:true` |

與最後一版 sound build（`7c5b8e5c…`，Chrome attempt-04／Firefox attempt-02）**逐項相同**。
新證據在 `state-readback/scheduler-attribution/chrome/attempt-05` 與 `firefox/attempt-03`。

**這輪重跑證明的是「沒弄壞」，不是「參數生效」。** 該 harness 的五個派送每一個都是
**跨狀態轉換**，而在跨狀態轉換上 toggle 與 setter 的結果完全相同——就算 `On` 在我方
worker／engine 的序列化中被丟掉，這五項也會照樣全過。要證明參數在 WASM 路徑上生效，
必須**重複派送**，而路線 B 的 `alreadyAtTarget` 正好擋住重複派送。
這件事留給 A4（第 4 節未決事項定案之後），與 finding 028 的
「瀏覽器重跑不能當成 body 路徑的證明」是同一種侷限。

engine 改動的隔離也逐位元驗過：關掉 `OXSDK_E2_FORMAT_BARRIER` 重編 E1-B 組態的
`probe_engine.o`，與既有 `build/e1/editor-v1/probe_engine.o` **完全相同**；
`e1-editor-v1` 仍為 `835b453d…`。

## 未驗證

- WASM profile 下 Chrome／Firefox 是否重現這兩件事（本輪只有原生）。
- `On` 參數是否原封不動通過我方 `postUnoCommand` 路徑——**修法後的重跑不能回答這題**，
  理由見上一節。
- `.uno:RemoveBullets` 有沒有參數化形式；本輪兩組都用 bare 派送，因為它本來就測到是 setter。
- 表格內或清單邊界的段落是否相同；本 fixture 兩者皆無。

## 本輪的量測限制

九個案例在同一 session、同一段落、依序執行，因此每個案例的起點是前一個案例留下的狀態。
各案例的 reset 步驟才是讓該案例讀數成立的東西；段落樣式在案例之間確實有殘留，讀數裡看得到。

第一輪只跑了 bare 組，而且分析器拿**自動樣式的生成名稱**（P1/L1 對 P2/L2）做比對，於是宣稱
沒被碰過的清單項變了——其實沒變。已改為把自動樣式解析到它的具名 parent。
**沒有為此重跑量測，只重跑了對同一批資料的判讀。**

## 相關

- [019](019-e1a-paragraph-style-mapped-to-ui-alias.md)——同一形狀：派送形式錯，不是能力不存在。
- [020](020-lok-list-command-result-contradicts-document.md)——為什麼判定不能讀 callback。
- [021](021-wasm-format-state-not-refreshed-by-caret-movement.md)——路線 C 的由來，以及路線 A 的代價。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 第 2.6 節（產品決定 v10）、第 4 節（barrier 契約）、第 8 節（判定）。
