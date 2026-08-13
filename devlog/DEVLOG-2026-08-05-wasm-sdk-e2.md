# DEVLOG 2026-08-05 — E2 起步：段落層級格式與一次前提翻案

> 對象：一起看 E1／E2 的同事。  
> 相關：[SPEC E2-000](../specs/SPEC-E2-000-overview.md)、[SPEC E2-A](../specs/SPEC-E2-A-paragraph-format-discovery.md)、
> [finding 019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)、
> [finding 020](../findings/020-lok-list-command-result-contradicts-document.md)

## 這一輪做了什麼

產品目標定為「**編輯功能精簡、讀取完整**」的 Writer WASM：工具列只有粗體、斜體、有序／無序清單這類基本
項目，但開文件必須是完整可信的 LibreOffice 讀取結果。

對照 E1 交出的窄版編輯器，落差分成兩條互不相依的線：

- **編輯側**：E1 的八個 action 全是 inline 或字元層級。缺清單、標題、上下方向鍵與拖曳選取。
- **讀取側**：ODT 28 份 corpus 已通過，但 DOCX 明確 unsupported（finding 013）。

本輪只做編輯側，編為 **E2**；讀取完整性另編 **E3**，不混入。兩者沒有技術相依，順序可以對調。

已建立 `SPEC-E2-000` 與 `SPEC-E2-A`，並執行 E2-A 的 A2 先決條件。**A2-wasm 與 A3～A7 尚未執行，
E2-A 目前沒有判定。**

## A2：先跑原生，然後前提就垮了

E2-A v1 的整個設計建立在一句從 E1-A 繼承的話上：「paragraph／list 的 fixed command 會改到文件、但不回
`LOK_CALLBACK_UNO_COMMAND_RESULT`」。於是 v1 的未知數被寫成「拿不到 command result 時怎麼建立 completion」。

依 Finding 016 學到的做法，先用原生 26.8 對照，而不是直接在 WASM 上驗證。理由有兩個：WASM 的否定結果分不出
「core 沒送」與「我方沒收到」；而且 barrier 需要比對 style 字串，那個字串猜錯會讓 barrier 悄悄失效。

探針每派送一個命令就 `saveAs` 一次，後置條件從 ODT `content.xml` 讀 —— **不從被檢驗的 callback 讀**。
格式命令不改文字，所以 Finding 016 用的「文字長度」防呆在這裡完全沒用，存檔就是防呆。

結果：

| 派送 | command result | state | 文件實際結果 |
|---|---|---|---|
| `.uno:DefaultBullet` | `success:true`、**`wasModified:false`** | `DefaultBullet=true` | **有效**，段落進清單 |
| `.uno:DefaultNumbering` | `success:true`、`wasModified:true` | `DefaultNumbering=true` | 有效 |
| `.uno:RemoveBullets` | **`success:false`**、`wasModified:true` | `DefaultNumbering=false` | **有效**，離開清單 |
| `.uno:Heading1ParaStyle` | 無 | 無 | **完全無效** |
| `.uno:StyleApply`＋參數 | `success:true`、`wasModified:true` | `StyleApply=Heading 1` | 有效 |

三件事同時翻案：

**1. 段落樣式的命令名稱根本不存在。** `.uno:Heading1ParaStyle` 在 LibreOffice 全樹只出現在
`WriterCommands.xcu` 的 `UserInterface/Popups`，沒有任何 `.sdi` slot。它是選單別名，`TargetURL` 指向
`.uno:StyleApply?Style:string=Heading 1&FamilyName:string=ParagraphStyles`。派送別名字串等於什麼都沒做。

E1-A 因此把段落樣式歸類成 completion 缺口 —— **歸因是錯的**。不是命令沒回應，是那個字串不是命令。
E1-A 從來沒有真正派送過段落樣式。記為 [finding 019](../findings/019-e1a-paragraph-style-mapped-to-ui-alias.md)，
並已回頭在 `SPEC-E1-A` 第 11.3 節就地標註撤回。

**2. command result 會說謊。** `RemoveBullets` 回 `success:false` 卻確實生效；`DefaultBullet` 回
`wasModified:false` 卻確實修改了文件。記為
[finding 020](../findings/020-lok-list-command-result-contradicts-document.md)，是本專案目前唯一的上游候選單。

**3. 一個樣式三種字串。** 送出用 `Text body`、ODT 存成 `Text_20_body`、state 回報 `Body Text`。
任何一個拿來當另一個用都會失敗。這正是「先量再寫」救回來的東西。

## barrier 因此重新設計

翻案後的設計比原本更乾淨，因為兩個來源**各自只提供一半**：

- **command result 帶 `commandName`** —— 這是唯一能把結果綁到這個 request 的東西。廣播式 state callback
  沒有這個資訊。→ 負責**歸屬**。
- **state callback 如實反映文件** —— 與存檔一致。→ 負責**真值**。

反過來用會錯得很具體：用 `success` 判定會讓 `set-list-none` 每次都回報失敗。

所以完成條件是兩者皆備。`success` 與 `wasModified` 只記進 evidence，**不參與判定**。前置狀態未知時
fail closed；已在目標狀態時回 typed `documented-state-noop`，不與「callback 沒到」混為一談 —— 這是從
Finding 016 帶過來的同一個原則。

另外保留兩個計數器，讓「沒發生」能自己證明自己：`crosstalkCount`（watched 命令但值不對）與
`earlyStateCount`（值對但早於 command result 抵達）。原生量到的順序是 result 先、state 晚 300～600 ms；
如果 WASM 下順序反過來，`earlyStateCount` 會直接講出來，而不是讓 barrier 默默接受一個沒有歸屬的 state。

## 本輪我自己犯的三個錯

**一、我的 run script 標題是錯的。** 第一次跑完，腳本印「UNO_COMMAND_RESULT count: 0 — 與 E1-A 觀察一致」。
實際是 5。原因是 grep 找 `"name":"UNO_COMMAND_RESULT"`，但串流裡是 `LOK_CALLBACK_UNO_COMMAND_RESULT`。
差一個前綴，就把一個推翻前提的結果印成了「確認前提」。

這跟上一輪 `run_finding_016_native.sh` 的錯誤是同一類：**摘要行本身沒有被驗證**。已修腳本並在註解寫明成因。
真正救回來的是後來把整條 callback 串流拉出來重看 —— 摘要可以錯，原始串流不會。

**二、我把繼承來的觀察當成前提直接寫進規格。** E2-A v1 的第 1 節、第 3 節、第 4 節全部建立在「沒有 command
result」上，而那句話我沒有測就寫了。規格已改為 v2，v1 的錯誤前提保留在文件裡沒有抹掉。

**三、我把 E1-C 驗證過的產品 artifact 換掉了。**（已修復）

跑回歸時用了 `make test-e1-a-static ... test-e1-b-static ...`。這些目標名字看起來是靜態檢查，但相依鏈會經過
`$(E1_B_BUILD)/%.o: src/%.cpp`，而我改過 `probe_engine.cpp`，於是 make **重建了 `e1-editor-v1` 產品 profile**。
E1-C 在 16:00 驗證的 WASM 是 `94b38437…`，被換成 `9d54dc2a…`。

更糟的是這不只是 hash 變動：我新增的 `listBullet`／`listNumber`／`paragraphStyle` 狀態欄位與 payload 解析
**沒有全部關在 `OXSDK_E2_FORMAT_BARRIER` 旗標裡**，所以 E1-B 的 `editor-state` 會多吐三個欄位、
會開始解析三個原本不解析的 payload。那是對凍結產品的行為變更。

修法是讓非 E2 組態的前處理輸出**完全還原**：把 `#include <algorithm>`、狀態欄位、`appendEditorState` 的新欄位、
`FormatStatePayload` 與擴充版 `updateEditorFormatState` 全部移進旗標，並在 `#else` 逐字還原原始函式。
重建後三個 hash 全部回到 E1-C 記錄值：

```text
probe.wasm    94b38437cce120de4bffb6275d084f1257abb7d6a310cb3cf20594ae72eab6ef  ✓
probe.js      45c31f321fa4bcf2e5065c1942e0358b03ab94148732496160ae822541b9511e  ✓
sdk-worker.js 9696c9ce580b431644cd4f56ea7356647dfd9ab143da6370e521bc2474a35fd7  ✓
```

順帶證明了這條建置鏈是決定性的 —— 相同前處理輸入會產生位元相同的 WASM。

兩個要帶走的教訓：**「static」測試目標不保證不會建置**，跑之前要先看相依；以及**隔離旗標要涵蓋所有共用
結構**，只把新函式關進去、卻讓新欄位留在共用 struct 裡，等於沒有隔離。

E1-A `e1-editor-discovery`（`679def61…`）與 R5 `writer-review`（`ba257beb…`）全程未被觸及。修復後回歸重跑，
退出碼 0、172 項通過。

## 順帶發現：R5 profile 目前無法從現有 source 重建

`probe_engine.cpp` 的 `struct SelectionReadback` 定義在 `#ifdef OXSDK_EDITOR_DISCOVERY` 區塊內（126–313），
但 `readSelection()` 與 `handleGetSelection()` 在區塊外。不帶該旗標編譯 —— 也就是 R5 `writer-review`／
`writer-reader` 的組態 —— 會失敗於 `unknown type name 'SelectionReadback'`。

這是上一輪 finding 017 修復留下的，不是本輪造成（三個錯誤全在我沒動過的行上）。與 017 已記錄的 boost
include 問題並列，兩個原因都會讓 R5 無法重建。**凍結的 R5 artifact 沒有受影響**，回歸驗的是 hash 不是重建，
所以目前不阻斷任何事。沒有順手修 —— discovery 階段動產品路徑的程式碼，風險大於收益。

## 現在的狀態

**已完成**

- `SPEC-E2-000`、`SPEC-E2-A`（v2，含翻案紀錄）
- A2-native 通過，證據在 `findings/evidence/sdk-e2/discovery/state-readback/native-26-8/`
  （callback 串流、sal.log、探針原始碼、六份逐步存檔 ODT、artifact.json，全部附 SHA-256）
- finding 019、020；`SPEC-E1-A` 就地標註撤回；roadmap 與 findings README 已回填
- barrier 實作完成，依實測改寫（段落樣式改派參數化 `.uno:StyleApply`），E2、E1／E1-B、scheduler 三種
  組態均編譯通過
- 回歸 R6～R8 與 E1-A／B／C 全過（退出碼 0、172 項）；R5 `writer-review`、E1-A `e1-editor-discovery`、
  E1-B `e1-editor-v1` 三個凍結 artifact 的 hash 均與原記錄一致

**未完成**

- A2-wasm、A3～A7 全部未跑。E2-A 沒有判定。
- `e2-format-discovery` profile 的建置規則、瀏覽器 harness 與 validator 尚未建立。
- 上述 barrier 行為在瀏覽器中仍是**推論**，不是已觀察。

## 下一步

1. 建 `e2-format-discovery` profile（隔離 artifact，不動 R5 與 E1-B），跑 A2-wasm 確認三個 state payload 在
   Chrome／Firefox 同樣抵達。這是把本輪推論升格為已觀察的最小實驗。
2. 通過後才跑 A3～A5，其中 `state-crosstalk` 比任何正向案例重要：正向只能證明會動，crosstalk 才能證明沒誤判。
3. finding 020 送上游前要先搜重複單，並在完全未修改的上游 build 重現 —— 本專案 worktree 有既有 patch。

## 方法上值得帶走的一點

這一輪的翻案不是靠更用力測 WASM，是靠**一份會存檔的原生對照**。跟上一輪 Finding 016 一模一樣。

差別在於，這次連「要比對什麼字串」都是量出來的。如果照直覺把 heading 的後置條件寫成 `Heading 1`、body 寫成
`Text body`，barrier 會在 body 上永遠逾時，而且逾時看起來會像「core 不送 state」—— 又是一個假的上游問題。

**先量，再寫死。** 猜出來的常數會把自己的錯誤偽裝成別人的 bug。
