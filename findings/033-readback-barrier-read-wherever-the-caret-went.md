# 033 — readback barrier 讀的是「游標現在在哪」，不是「命令改了哪一段」

| | |
|---|---|
| **狀態** | **已確認並已修（2026-08-11 實測關閉）——關掉它的是 BUSY 閘，不是歸屬；見〈修法已實作〉。未結的期限缺口亦已於同日補上** |
| **Bugzilla** | — |
| **發現日** | 2026-08-11 |
| **嚴重度** | 嚴重（可能對錯誤的段落回報成功，且不會有任何錯誤訊號） |
| **可重現** | 100%（A5 `state-crosstalk`，兩次實測） |
| **是否上游** | **否**（我方 barrier 設計） |

## 摘要

路線 C 的 readback barrier 派送後會選起「游標所在段落」再讀 `text/html` 判定後置條件。
**但游標可能在派送與讀取之間被移走**——barrier 於是讀了另一段。

A5 的 `state-crosstalk` 案例（派送後立刻把游標移到別段）實測讀到
`EDITOR_FORMAT_POSTCONDITION_FAILED`：**fail-closed，方向是對的**。

**但那是運氣。** 那一段剛好不是目標狀態才會不符。若游標移到一段**本來就已經是目標狀態**
的段落，barrier 會讀到相符、回報 `verified-format-readback`——
而實際被改的是另一段。**沒有任何訊號會顯示這件事**。

這是 A5 存在的理由：正向矩陣（A3／A4 共 555 次派送）全部通過，這條路一次也沒被碰到。

## 修法

在**選段落來讀之前**，先把游標移回派送當時記錄的位置（`restorePoint`，
在派送**之前**就擷取，因為派送本身也可能移動游標）。

修後同一個案例：`state-crosstalk` 由 `EDITOR_FORMAT_POSTCONDITION_FAILED`
變成 `verified-format-readback`，且存檔 ODT 顯示 **heading 落在被派送的那一段**
（`E1-STYLED-END` → `Heading_20_1`），不是游標移去的那一段。

## 2026-08-11 更正：修法不完整，真正的洞不是座標

上面的修法**沒有關掉這個缺陷**，而我當時的成因判斷也錯了。

恢復 error payload 的 readback 轉發後（引擎本來就送，是 `sdk-worker.js` 把整包
`formatBarrier` 丟掉——矩陣的 `postconditionFailure` 明寫要帶原始 markup，是管線毀約），
重跑 table-boundary 的 crosstalk 案例，失敗當下讀到的 markup 是：

```html
<p style="margin-bottom: 0.08in; line-height: 100%">E1-TABLE-BEFORE</p>
```

**那是 crosstalk 段落本身**（`parsed:true`、`unknownTag:false`、`restoreConfirmed:true`）。
不是座標落錯、不是表格 API——**是 barrier 消費了一個它無法歸屬的 `TEXT_SELECTION` 回呼**：
`AwaitingSelection` 階段見到任何非空選取就前進，而 crosstalk 的 `search` 正好產生一個。

barrier in-flight 期間，`search`／`placeCaret`／`select` **目前不被 `BUSY` 擋**，
所以 caller 可以替 barrier「按下一步」。其他 fixture 通過只是時序沒對上，不是修好了。

**座標殘留仍是真的**（見下節），但它與本節是兩件事，本案例否證的是座標成因。

### 而且「其他 fixture 通過」也是假的

我原本寫「其他 fixture 修好後會通過，只有 table-boundary 仍失敗」。**那是錨點選得不健全造成的**：
`A5_CROSSTALK_ANCHORS["styled-list"]` 原本指向 `E1-STYLED-HEADING`，而那一段**本來就是
`Heading_20_1`**，案例派送的又是 `set-paragraph-heading`——**讀對段與讀錯段都會得到 `h1`**，
案例兩種情況都通過。我把本單警告的那個陷阱直接蓋進了它自己的測試裡。

改成非 heading 的 `E1-LIST-ONE` 後重跑：**styled-list 的 crosstalk 一樣失敗**，
`blockTag='p'`——讀到的正是 crosstalk 段落。

所以：**這個缺陷不分 fixture，本單原本的修法（讀前先還原游標）在任何 fixture 都沒有關掉它。**
劫持穩定地贏過還原。

## 修法的前置量測已完成（2026-08-11，已觀察）

覆核判定：**`sourceSequence` 時序過濾不是歸屬**——它在回呼**送達時**遞增，而所有危險來自
**未來才送達**的外來回呼，它們全都拿到更大的序號、全都通過檢查。
那會產生「已加歸屬」的紀錄而實際上什麼都沒歸屬，**比不加更糟**。此方案作廢。

最小充分機制是 **commandName 歸屬**：`EndOfParaSel` 改以 `notify=true` 派送，
`AwaitingSelection` 的推進條件改為「收到 `commandName == ".uno:EndOfParaSel"` 的
`UNO_COMMAND_RESULT` **且** 選取非空」。基礎設施已存在（`commandResultMatches`）。

**前置量測**（這類「命令不回 result」的說法在 2026-08-05 被原生實測推翻過一次，不用猜的）：

證據 `findings/evidence/sdk-e2/discovery/endofparasel-result/native-26-8/`。原生 26.8，
以 `notify=true` 派送，逐一計數 `LOK_CALLBACK_UNO_COMMAND_RESULT` 的 `commandName`：

| commandName | 次數 |
|---|---|
| `.uno:EndOfParaSel` | **8**（＝派送次數） |
| `.uno:GoToStartOfPara` | 8 |
| `.uno:StyleApply` | 2 |
| `.uno:DefaultBullet`／`.uno:DefaultNumbering`／`.uno:RemoveBullets` | 各 1 |

**`EndOfParaSel` 會回 result，每次都回。** 機制可行，退路（文字回聲檢查）不必動用。

一併記下：**`GoToStartOfPara` 也會回 result**，所以推進條件必須比對 `commandName` 本身，
不能寫成「收到任何 result」——`commandResultMatches` 正是做這件事。

## 修法已實作並實測關閉（2026-08-11，**已觀察**）

引擎 `25761ff0…`（前一版 `902379ba…`、修法前 `68590548…`）。

兩層都做了：

1. **歸屬**——`EndOfParaSel` 以 `notify=true` 派送，`AwaitingSelection` 的推進條件改為
   「收到 `commandName == ".uno:EndOfParaSel"` 的 result **且** 選取非空」。
2. **BUSY 閘**——`search`／`editor-select` 在 `formatBarrierActive()` 期間一律回 `BUSY`。
   `search` 也在內，因為 `.uno:ExecuteSearch` **會選起命中處**，它是 caret mover，
   而且正是 crosstalk 案例實際走的那條路。

A5 `state-crosstalk`，Chrome 150.0.7871.128：

| fixture | 結果 | readback | `caretMoveAccepted` |
|---|---|---|---|
| styled-list | `verified-format-readback` | `listTag=ul`、`blockTag=h1`、`restoreConfirmed=true` | `false` |
| table-boundary | `verified-format-readback` | `<ul><li><h1>E1-CELL-A1</h1></li></ul>` | `false` |

markup 自己帶著段落文字（`E1-CELL-A1`），所以「讀到哪一段」是**直接看得見**的，
不必靠「那一段剛好不是目標狀態」這種會兩邊都通過的判準——本單前面正是栽在這裡。

### 關掉它的是 BUSY，歸屬沒有被獨立證實

`caretMoveAccepted=false`：crosstalk 的 `search` 被 `BUSY` 擋掉，游標根本沒移動。
而 `selectionBeforeResultCount` 在**每一次** barrier 都是 `0`——
意思是在自己的 `EndOfParaSel` result 到達之前，沒有任何非空選取抵達。

**所以歸屬那一層在這批證據裡沒有攔到任何東西。** 它是縱深防禦，不是這次的修復者。
本單不宣稱它修好了什麼；`selectionBeforeResultCount` 之所以不叫
`unattributedSelectionCount`，就是為了不把判讀寫進名字裡。

### 附帶量到的事：`notify` 是兩條派送路徑，混用不保序

第一版只把 `EndOfParaSel` 改成 `notify=true`，`GoToStartOfPara` 維持 `false`
（當時的理由是「少一個 result 比較乾淨」）。結果在 A5 styled-list attempt-04：

- `stale-revision` 的 readback 是 `<p>D-END</p>`，而那一段的文字是 `E1-STYLED-END`
  ——**選取錨點落在字中間**，也就是 `EndOfParaSel` 比 `GoToStartOfPara` 先生效。
- `list-teardown` 直接 **30 秒逾時**：游標本來就停在段尾，`EndOfParaSel` 選到空，
  非空選取的回呼永遠不會來。

兩個都不是 flake，是同一個原因。兩個命令改成同樣 `notify=true` 後，五個案例全數回復
（`stale-revision` 重新回到 `STALE_REVISION` 這個該有的分類拒絕）。
原生那支確立本 readback 可行的探針，用的就是兩個都 `notify=true`。

**代價是多一個 command result**——而這正是推進條件必須比對 `commandName` 的原因：
`GoToStartOfPara` 也會回 result（原生 8/8，見上表）。那條當時看起來像註腳的量測，
現在是承重的。

**2026-08-11 補記：這一對命令已經不存在了。**
[034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md) 把選取步驟
換成單一的 `.uno:SelectText`，於是「兩條派送路徑可以亂序」這一整類問題連同本節記錄的
症狀一起消失——不是修好，是沒有兩條路徑可以亂。`commandName` 歸屬**保留**且仍然必要
（動作自己的命令也會回 result），而 `SelectText` 同樣每次都回 result（原生 10/10）。
本節保留原樣，因為它記錄的是「`notify` 是兩條派送路徑」這件仍然為真的事。

### 順帶暴露的缺口：barrier 卡住會讓引擎永久 BUSY（**已觀察**，2026-08-11 已修）

`list-teardown` 逾時的是 client（30 秒），引擎那側的 barrier **仍然是 active**，
於是下一個案例的 `search` 收到 `BUSY`——整個 document handle 就此卡死。

引擎目前沒有 format barrier 的自有期限。矩陣有 `boundaryReadbackDeadlineMs: 250` 與
`deadlineCanDeclareMutationSuccess: false`，方向是清楚的（期限只能判失敗，不能判成功），
但 format barrier 沒接上。這條**在正常路徑上碰不到**（上述順序修好後五案例全通），
但它是「一次逾時就毀掉整個 session」的形狀，列為未結項。

**2026-08-11 已修（引擎 `38168306…`）。** 三個 awaiting stage 各有自己的期限，
進入每個 stage 時重新起算，期限只能判失敗。

兩件與上面這段不同的事，記下來因為它們改變了這條的性質：

1. **期限值是 5000 ms，不是這裡寫的 250。** 250 是為了另一個問題量的
   （selection barrier 的結構邊界探測需要多久），因為就在旁邊而沿用它，
   就是把一次量測變成習慣。目前所有健康的 barrier 都在 40 ms 內完成。
2. **它不再是「碰不到的防禦」。** [034](034-paragraph-selection-escapes-at-the-offset-the-test-never-used.md)
   的修法改用 `.uno:SelectText`，而該命令在**文件末段的空段落上完全不產生選取**
   （原生實測 selType 0，result 照回）——`AwaitingSelection` 於是有了一條
   **確定會發生**的卡死路徑。期限從此是那個修法的必要配件，不是預防性設計。
   實測：`MUTATION_OUTCOME_UNKNOWN`／`stage-deadline:awaiting-selection`，
   5010 ms，document handle 事後仍可用。

## 未消除的殘留（**推論，未實測**）

還原用的是**文件座標**，而派送本身可能改變該段的高度或縮排（套用 heading 會變高、
進清單會改縮排）。極端重排下，那個座標仍可能落到別段。

這條路**沒有被量測過**，也沒有被關閉。要真正關掉需要一個「段落身分」而非座標的定位方式，
那是目前 LOK 介面沒有提供的東西（`getCommandValues` 的實作已查過，見 finding 030）。

BUSY 閘縮小了它的可達性——barrier in-flight 期間 caller 已經動不了游標——
但**沒有消除**它：還原點是派送**前**擷取的座標，而派送本身就會改變幾何。
上面 attempt-04 的 `<p>D-END</p>` 剛好也示範了「錨點落在段落中間」這件事會長什麼樣子，
只是那次的成因是命令順序而不是重排。

## 相關

- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)——readback barrier 的由來。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 2.8／2.9 節。
