# 034 — barrier 的段落選取在游標 offset 0 時會跑到別段，而測試從沒用過那個 offset

| | |
|---|---|
| **狀態** | **已確認並已修（2026-08-11 實測關閉，引擎 `38168306…`）——見〈修法已實作並實測關閉〉** |
| **Bugzilla** | —（upstream 部分見末節，低優先） |
| **發現日** | 2026-08-11 |
| **嚴重度** | 嚴重（可對錯誤段落回報成功，且無訊號；觸發手勢是「在行首點一下再按格式鈕」） |
| **可重現** | 100%（原生 26.8，`paragraph-selection-edges/native-26-8/`） |
| **是否上游** | **否**（我方 barrier 的命令選擇）；upstream 只有一個次要註記 |

## 摘要

路線 C 的 readback barrier 用 `.uno:GoToStartOfPara` ＋ `.uno:EndOfParaSel`
選起「游標所在段落」再讀 `text/html`。

**`.uno:GoToStartOfPara` 不冪等。** 游標**已經在 offset 0** 時它會跳到**上一段**。
core 自己在 `sw/source/core/crsr/pam.cxx:1238` `GoCurrPara()` 的註解寫明：

```cpp
const sal_Int32 nNew = &aPosPara == &fnMoveForward ? 0 : pNd->Len();
// if already at beginning/end then to the next/previous
if( nOld != nNew ) { rPos.SetContent( nNew ); return true; }
```

鏡像對（`GoToEndOfPara` ＋ `StartOfParaSel`）在 offset `Len()` 對稱地壞。
**「移到一端再選到另一端」這個形狀本身就有兩個死角。**

## 為什麼 375 次已判定派送一次也沒碰到

`caretAtAnchor()` 把游標放在錨點文字的 `rectangle.x + width`＝**offset `Len()`**。
原生 search 也把游標留在命中處**之後**，同樣是 `Len()`。
兩邊一致——**所有既有證據都只覆蓋那一個「現行序列剛好正確」的 offset。**

這不是運氣不好，是**覆蓋軸從來沒有被寫進矩陣**。

## 實測矩陣（原生 26.8）

證據：`findings/evidence/sdk-e2/discovery/paragraph-selection-edges/native-26-8/`。
每一列的游標都確認落在目標段落（`caretY` 欄）；放不到位的案例輸出 `skipped`
而不是拿上一個案例殘留的游標硬測。

| 游標位置 | 現行 pair | `.uno:SelectText` |
|---|---|---|
| 文字段落 **offset 0** | **跨選兩段** ✗ | 正確 ✓ |
| 文字段落 offset 中間 | 正確 ✓ | 正確 ✓ |
| 文字段落 **offset `Len()`**（＝既有全部證據） | 正確 ✓ | **正確 ✓（無退步）** |
| 空段落 · 文件中段 | 讀到**上一段** ✗ | **跨選兩段** ✗ |
| 空段落 · 文件末段 | 讀到**上一段** ✗ | **完全沒有 selection**（selType 0） ✗ |

## 後果已量到：今天低報，而假成功只差一個 fixture

WASM 現行 build `25761ff0`（`barrier-deadline/chrome/empty-paragraph/`）：
barrier 回報 `EDITOR_FORMAT_POSTCONDITION_FAILED`，而**存檔 ODT 顯示 mutation 成功**——

```xml
<text:list><text:list-item><text:p text:style-name="P1"/></text:list-item></text:list>
```

所以今天是**低報**：動作成功了，呼叫端被告知失敗。而且這個低報**正在邀請重放**，
清單命令是 toggle 形式時重放會反轉狀態。

把被誤讀的鄰段換成一個**本來就在目標狀態**的段落，同一機制就會回報**成功**，
而實際改的是另一段——[033](033-readback-barrier-read-wherever-the-caret-went.md) 的失效模式，
**不需要任何併發**。

## 為什麼獨立編號而不併進 033

033 是**呼叫端併發**把游標移走；本單是**確定性的原語邊界語意**——單執行緒、必然發生、
觸發條件是**輸入**（offset 0）而不是時序。033 的殘留靠 BUSY 閘縮小可達性，本單靠不了。

最鋒利的表述：對 offset-0 這類輸入，現行檢查**對「讀對段」與「讀錯段」會給出同一結果**
——本 repo 紀律裡最核心的那句話的實物展示。

## 修法（已實作，見下一節的實測）

1. **選取動作換成單一派送 `.uno:SelectText`（`FN_SELECT_PARA`）。**
   clamp 在 stock core 的 dispatch handler 裡（26.8 baseline
   `sw/source/uibase/shells/textsh1.cxx:1975`）：

   ```cpp
   if ( !rWrtSh.IsSttOfPara() ) rWrtSh.SttPara();
   else                         rWrtSh.EnterStdMode();
   rWrtSh.EndPara( true );
   ```

   單一派送**順帶整類消滅** [033](033-readback-barrier-read-wherever-the-caret-went.md)
   記錄的雙命令重排 bug（不再有兩條 dispatch 路徑可以亂序）。
2. **多段 readback 防護**：`parseFormatReadback` 見到第二個 block tag 或第二個 `li`
   → `multiBlock:true` → fail closed。封掉空段落中段跨選的假成功。
3. **containment 檢查**：selection 的縱向範圍必須包含 restore point，否則 typed 失敗。
   這條對現行 build 的 offset-0 案例**會真的 fire**，突變對照是現成的。
4. **引擎側 deadline**（見 033）：**採用 `SelectText` 會製造出可達的 stall**
   ——文件末段空段落沒有任何 selection，`AwaitingSelection` 永不推進。
   deadline 因此由「防禦一個量不到的問題」變成**本修法的必要配件**。
5. **失敗碼**：deadline／containment 失敗／`multiBlock` 一律 `MUTATION_OUTCOME_UNKNOWN`
   （呼叫端只看碼，而「勿重放」對三者都成立），診斷差異放 `failureShape`。
   `EDITOR_FORMAT_POSTCONDITION_FAILED` 保留給「乾淨讀到單一段落、但不在目標狀態」。

**空段落是規格層收窄，不是實作缺陷**：它沒有可選取的內容，任何以游標移動為基礎的選取
都定址不到它。路線 C 的 readback 驗證定義在非空段落上；空段落的 mutation 一律回報
typed 的不可驗證，**永不回報成功**。開放項（記錄、不實作）：引擎已有
`getA11yFocusedParagraph` 管線，未來可評估作為空段落的第二讀取路徑。

## A3／A4／A5 不降級

375 次派送量了什麼就主張什麼，沒有任何一筆被否證。要做的是**書面收窄＋補覆蓋**：
矩陣加 `caretOffsetCoverage` 軸（非空 × {0, 中間, Len} ＋ 空段落 × {中段, 末段}），
走既有 revision 機制記錄「既有證據僅覆蓋 offset `Len()`」。

## 修法已實作並實測關閉（2026-08-11，**已觀察**）

引擎 `38168306b20891e9…`（修法前同源的 `bd102b4a…`，見 [036](036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)）。
四個改動全部進同一個 build：`.uno:SelectText` 單一派送、多段防護、containment、
三個 awaiting stage 的 5000 ms 期限。

### 先量了一件沒人量過、而整個修法都靠它的事

`AwaitingSelection` 的推進條件要求「收到 `commandName == kFormatBarrierSelectCommand`
的 result」。**`.uno:SelectText` 會不會回 result，從來沒有人量過**——若不會，
每一次派送都會卡到期限，修法等於把功能改死。

原生 26.8 實測：**10 次派送 / 10 次 result**。順帶量到 result 一律早於非空選取
（每一列都早 3 個回呼事件），以及五個封閉動作透過 `SelectText` 讀回的 markup
形狀完全不變。證據 `findings/evidence/sdk-e2/discovery/selecttext-result/native-26-8/`。

控制組：`.uno:GoDown`／`.uno:GoToStartOfDoc` 以 `notify=false` 派送，計數為 0
——計數器能印出不同的值。

### 鑑別器：同一份案例清單，修法前後各跑一次

`findings/evidence/sdk-e2/discovery/caret-offset-discriminator/`，Chrome 150。
判準是**讀回 markup 裡是哪一段的文字**，不是「讀回是否符合目標狀態」
——後者在鄰段剛好符合時兩邊都會過，033 就是栽在那裡。

| fixture ／ 案例 | 修法前 `bd102b4a` | 修法後 `38168306` |
|---|---|---|
| styled-list ／ `offset-len-control` | 成功，讀對段 | **相同（無退步）** |
| multi-paragraph ／ `offset-len-control` | 成功，讀對段 | **相同（無退步）** |
| styled-list ／ `offset-zero-verifies-wrong-paragraph` | **回報成功，而 markup 是 `E1-LIST-ONE`**（派送的是 `E1-LIST-TWO`） | 成功，**讀對段** |
| multi-paragraph ／ `offset-zero-escapes-to-previous` | 讀**上一段** | **讀對段** |
| empty-paragraph ／ `empty-mid-document` | 讀上一段，`POSTCONDITION_FAILED` | `MUTATION_OUTCOME_UNKNOWN`／`multi-block-readback`，39 ms |
| empty-paragraph ／ `empty-document-end` | 讀上一段，`POSTCONDITION_FAILED` | `MUTATION_OUTCOME_UNKNOWN`／`stage-deadline:awaiting-selection`，**5010 ms**，handle 仍可用 |

第三列是本單最尖銳的形式：**修法前一次按鍵（Home）就能讓 barrier 回報
`verified-format-readback`，而它驗證的是另一段**——033 需要呼叫端併發才能到達的失效，
這裡不需要任何併發。

（那一列不主張「文件變錯了」：`E1-LIST-TWO` 本來就是清單項，結果碰巧是對的。
假的是**「已驗證」這個宣稱**。要讓結果也錯，還需要一次失敗的派送，那是另一個條件。）

### 期限是這次修法**製造**出來的需求，不是預防性設計

`empty-document-end` 那一列：`SelectText` 回了 result，**選取回呼永遠不來**（原生 selType 0）。
沒有期限的話 `AwaitingSelection` 不會結束，而 BUSY 閘會讓整個 document handle 卡死。
5010 ms 就是 5000 ms 的期限加來回；handle 事後仍可用。

期限**永不判成功**，而且這條有實物：文件末段空段落上 `getTextSelection` 在
**完全沒有選取**時仍回 490 bytes、單一 `<p>`——期限若「就地讀一下」會讓
`set-paragraph-body` 的後置條件被無中生有地滿足。

### 修法逼出了另一個更廣的缺陷

第一次跑鑑別器時，`offset-zero` 案例在新 build 仍然失敗，我一度以為是退步。
用 offset `Len()`（不可能逃逸）重跑同一段：**兩個 build 都失敗、`unknownTag` 都是 true**。

那是 [035](035-the-postcondition-read-fails-closed-on-any-formatted-or-cjk-paragraph.md)：
readback 的封閉標籤集不含 `<b>`／`<i>`／`<font>`／`<span>`，所以**任何有字元格式或
含中文的段落都 fail closed**。既有缺陷，非本次造成，**未併入本 build**。

## upstream 註記（低優先，尚未回報）

dispatch handler（`FN_SELECT_PARA`）有 clamp，但 `SwWrtShell::SelPara`
（`sw/source/uibase/wrtsh/select.cxx`，四擊選段路徑）**沒有**——upstream 自己只修了一半。
未查重、未回報。

## 我在本單過程中的三個自傷

都是「與自己名字不符的那一列」抓出來的，記下來因為形狀會重複：

1. WASM 第一版的 `caretIsBetweenAnchors` 驗的是**我要求的座標**，不是游標實際去了哪
   ——它在一次 readback 明確顯示游標在上一段的 run 上通過。已改名。
2. 原生探針把游標放在錨點矩形**左緣**卻把該情形叫作「caret at end」；
   而 search 其實把游標留在 offset `Len()`。名字與量到的東西相反。
3. `positionAtAnchor` 在 search 沒產生游標回呼時**靜默跳過定位**，案例於是從上一個案例
   殘留的游標開始量——有一列叫 `offset-zero` 卻回報兩段之外的 `caretY`。
   現在放不到位就輸出 `skipped`。

## 相關

- [033](033-readback-barrier-read-wherever-the-caret-went.md)——同樣是「barrier 讀錯段落」，但機制是併發而非邊界語意；deadline 的規格在那裡。
- [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md)——readback barrier 的由來。
- [SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md) 2.8／10.10 節。
