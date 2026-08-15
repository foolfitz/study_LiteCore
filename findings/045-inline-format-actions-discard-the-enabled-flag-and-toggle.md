# 045 — 四個 inline 格式動作把 `enabled` 丟掉，派送的是 toggle

| | |
|---|---|
| **狀態** | **已確認（兩瀏覽器實測 ＋ 原始碼對照）／擋住 E2-C D1** |
| **Bugzilla** | —（**不是上游缺陷**） |
| **發現日** | 2026-08-15 |
| **嚴重度** | 嚴重（出貨契約收一個明確的布林值，引擎完全不用它；`enabled: false` 關不掉格式） |
| **可重現** | 100%（Chrome／Firefox 各一輪，全新文件、純文字游標） |
| **是否上游** | **否——我方的派送形式**，與 [030](030-closed-list-actions-dispatch-the-toggle-form-and-a-noop-is-silent.md) 缺陷一同型 |

## 摘要

`set-bold`／`set-italic`／`set-underline`／`set-strikethrough` 的 ABI 收一個
**明確的 `enabled` 布林值**，客戶端強制要求它（`editor-client.js`：
「the inline format actions require an explicit enabled boolean」），
worker 一路帶到引擎——**然後引擎把它存進一個只拿來回報的變數，
派送的是不帶參數的 `.uno:Bold`**。

core 的 slot 宣告是 `Toggle = TRUE`。不帶參數派送 ⇒ **切換現況**，不是設定成目標值。

**後果**：`enabled: false` 不會關掉格式。在**全新文件、純文字游標**上派送
`set-bold(enabled: false)`，之後打的字**是粗體**。

**這正是 finding 030 缺陷一的同一個形狀**，030 修好了兩個清單命令
（`kListOnArguments`，`probe_engine.cpp:3091`），**四個 inline 格式沒有跟著修**。

## 最小重現

出貨 profile `e2-editor-v2`（wasm `572035ac…`），語料 `test-docs/e2/d1-anchors.odt`，
**全新文件**（每一格自己的引擎與文件，前面沒有任何派送）：

```text
把收合游標放在一段純文字上（E2-D1-BOLD-ON plain）
派送 set-bold(enabled: false)   → changed: true、revision +1、uno-command-result
在同一個游標提交 "OFFONLY"
存檔
```

**Chrome 與 Firefox 逐字相同**：

```xml
<text:p text:style-name="P1">E2-D1<text:span text:style-name="T1">OFFONLY</text:span>-BOLD-ON plain</text:p>
<style:style style:name="T1" …><style:text-properties fo:font-weight="bold" …/></style:style>
```

**要求關閉，得到開啟。**

## 機制（原始碼層級，逐行）

| 位置 | 做什麼 |
|---|---|
| `wasm_sdk_probe/src/probe_engine.cpp:3897` | `case OXSDK_EDITOR_SET_BOLD: startEditorUnoAction(command, name, ".uno:Bold")` |
| `…:3034` | `gEditorUnoOption = command.values[2] != 0;` ← `enabled` 進到這裡 |
| `…:3036` | `startUnoMutation(command, "editor-action-completed", unoCommand, {});` ← **參數是空的** |
| `…:2073` | `gEditorUnoOption` 的第一個用途：只用來認出 delete 的 manual-observation 分支 |
| `…:2083` | 第二個用途：原樣回報成 `"option"` 欄位 |
| `libreoffice-26-8/svx/sdi/svx.sdi:832,838` | `SvxWeightItem Bold SID_ATTR_CHAR_WEIGHT` ＋ **`Toggle = TRUE`** |

**`enabled` 在引擎裡沒有第三個用途。** 它從來沒有離開過我方的程式碼。

### 順帶：這幾個動作的 `changed` 是常數

`probe_engine.cpp:2085` 把 `changed` 寫死成 `"true"`（delete 的手動觀察分支除外）。
所以 inline 格式回的 `changed: true` **不是對文件的觀察**，是一個字面值。

同一輪另外量到：在收合游標上派送這四個動作，**`<office:body>` 逐位元不變**
（效果在之後打的字上）。兩件事合起來的意思是：
**`changed: true` 在這裡既不代表文件變了，也沒有任何東西去看過文件。**

## 已排除／未排除

| 假說 | 結果 |
|---|---|
| 客戶端沒把 `enabled` 送出去 | **排除**——D0 的請求信封逐欄比對過，`enabled: false` 確實在 payload 裡 |
| worker 沒轉發 | **排除**——`sdk-worker.js` 把 `payload.enabled ? 1 : 0` 放進呼叫 |
| 瀏覽器差異 | **排除**——兩瀏覽器逐字相同 |
| 前一次派送的打字屬性殘留 | **排除**——重現用的是全新引擎、全新文件，前面沒有任何派送 |
| ~~「連按兩次會關掉」（toggle 的正常行為）~~ | **已量（原生，2026-08-15），而且推翻了我的預測**：兩個**不相鄰**位置各 bare 派送一次，**兩個標記都被套上格式**。所以 bare 是**相對於游標處狀態**的切換，不是殼層層級的翻轉——在兩個純文字位置上，兩次都是「關 → 開」。詳見 `evidence/045/native/`。 |

## 影響範圍

- **出貨的 E1 契約也有這個問題。** 這四個動作從 E1-B 起就是這樣派送的；
  `e1-editor-v1`（`835b453d…`）與 `e2-editor-v2`（`572035ac…`）走同一段程式碼。
- **E1-C 為什麼沒抓到**：它驗的是 revision 與 typed 後置條件，
  **沒有任何一格去存檔看那段文字到底變成什麼**。demo 手動驗過的是「開啟」那一側。
- **違反上位規格**：[SPEC E2-000](../specs/SPEC-E2-000-overview.md) 第 8.1 節寫
  「以 explicit closed enum **設定**，不是 toggle」。那句話是為清單寫的，
  但同樣的理由適用於這四個。
- **擋住 [SPEC E2-C](../specs/SPEC-E2-C-paragraph-format-validation.md) 的 D1**：
  凍結矩陣裡 `d1-set-*-false` 四格的判準是「之後打的字**不帶**那個屬性」，
  在現行 artifact 上**不可能通過**。

## 還缺什麼才能處置

- [x] **已由外部裁決（fable，2026-08-15）決定處置**，見下面的〈處置〉。
- [x] **原生實測預測的參數形狀**——**成立**（2026-08-15，`evidence/045/native/`）。
      下一步是進 WASM，而那需要 relink。
- [ ] **D1 序列二分**，把 `d1-body-collapsed` 的機制查出來——
      **它與本 finding 是同級的 STOP，而且可能也是引擎側的**。
      漏掉它就是第二次 relink。
- [x] 乾淨的 toggle 對照——**已做，而且推翻了預測**（bare 是相對於游標處狀態的切換）。
- [ ] 決定 E1 側要不要一併發修訂（同一段程式碼，同一個缺陷）。

## ~~兩條路都要 relink~~ **更正（2026-08-15，外部裁決查出來的）**

**「縮限也要重連結」是錯的。** `tools/build_e2_b_profile.py:111-165` 是**打包器不是
連結器**——它 `shutil.copy2` 已經建好的 loader／wasm／worker，manifest 由 Python
dict 寫出。拿同一批位元組重跑它，`probe.wasm` 逐位元相同、`wasmSha256` 還是
`572035ac…`。而且**沒有任何東西釘住 manifest 自己的位元組**：

- `e2/validation-matrix-v1.json` 的 baseline 只釘四個雜湊（wasm／loader／worker／
  殼層 bundle），**沒有 manifest 雜湊**；
- `validate_e2_b.py:116-130` 重算三個 artifact 雜湊，只檢查 manifest **描述**它們；
- `check_e2_b_inventory.py:43-47` 只比對動作**名稱→id**，`limits` 對它是隱形的。

**所以在 manifest 加一行 `limits` 不需要重連結，而且現行每一道檢查都會放行。**

**但它仍然不該單獨做**，理由是它值的比我以為的少：

1. 它**關不掉這一輪的紅**——那四格判在存出來的文件上，而矩陣**跑完之後不能改**；
2. **謊言不在 `limits` 那裡，在線上形狀**：兩個出貨客戶端都**硬性要求**那個布林值
   （`editor-shell/editor-client.js:108-118`、
   `editor-shell-v2/narrow-editor-v2-client.js:167-177`），加一行註記之後，
   呼叫端還是得繼續送一個不生效的參數。**誠實的縮限要改 `sdk-worker.js`，
   而 `workerSha256` 正是 E2-B 綁的三個雜湊之一**——那就一樣會斷綁。
3. **就地改一顆已出貨 profile 的宣告，形狀就是 finding 027**：那 132 個 run 是在
   `limits: []` 下量的，改宣告而判定還是綠的，意思是**檢查沒看見**，那是缺口不是許可。
4. 連**驗證**那個改動都會污染：`validate_e2_b.py` 每跑一次就重寫
   `e2-b-summary.json`（判定證據），而那正是 E2-C 第 3 節禁止跑它的原因。

## 預測：正確的派送形式（**原始碼推導 → 已原生實測，2026-08-15**）

> **結果：P1 成立，修法確認。** 七個預測六個成立，破的那一個（P4）正是預先標為
> 「中信心、045 自己欠的那格」。完整結果與判讀在 `evidence/045/native/README.md`。
>
> | 量到的 | |
> |---|---|
> | 帶參數 `value:false` 在純文字游標上 | 之後打的字 `fo:font-weight="normal"`——**要求關閉，得到關閉** |
> | 帶參數 `value:true` | 打的字是粗體 |
> | **帶參數 `false` 打在已套用的選取上** | **屬性被移除**——**出貨產品今天完全做不到這件事** |
> | 不帶參數，兩個**不相鄰**位置各一次 | **兩個都被套上**（P4 破，模型更正見上表） |
>
> 四個命令行為一致，28 個 arm 各自在重新載入的文件裡跑。

外部裁決把「參數形狀還沒查」也推翻了——它是從原始碼推得出來的：

- `sfx2/source/appl/appuno.cxx:206-219`（`TransformParameters`）：property slot 的
  **單一參數、名稱等於 slot 的 UNO 名**，會走 `pItem->PutValue(value, 0)`。
- MemberId 0 對這四個 item 都是布林存取子：`MID_BOLD=0`、`MID_ITALIC=0`、
  `MID_TEXTLINED=0`、`MID_CROSSED_OUT=0`（`include/editeng/memberids.h:108-124`），
  每個 `PutValue` 的 case 0 都是 `SetBoolValue(Any2Bool(rVal))`
  （`editeng/source/items/textitem.cxx:612-620, 471-479, 1170-1179, 1412-1419`）。
- **參數集非空時**，`unoctitm.cxx:713-717` 直接帶 item 執行；
  **參數集為空才走 bindings**，而那條路的註解逐字是
  「execute using bindings, **enables support for toggle**/enum etc.」（`:733-737`）。
  **我們現在走的就是那條。**（本專案已核對：`memberids.h` 四個 MID 全是 0，
  `unoctitm.cxx` 的兩條分支逐字如上。）

預測的四個參數字串，形狀與 `kListOnArguments` 相同：

```text
.uno:Bold        {"Bold":{"type":"boolean","value":false}}
.uno:Italic      {"Italic":{"type":"boolean","value":false}}
.uno:Underline   {"Underline":{"type":"boolean","value":false}}
.uno:Strikeout   {"Strikeout":{"type":"boolean","value":false}}
```

引擎側的改動是 `probe_engine.cpp:3897-3912` 每個 case 一個參數字串，
與 `:3091` 的 `kListOnArguments` 同一個作法。

~~**原生測試還要回答**：收合游標上帶明確 item 時，打字屬性是否與 toggle 路徑同樣建立；
以及本 finding 自己欠的那個乾淨 toggle 對照（兩個**不相鄰**的位置）。~~
**兩件都已回答（2026-08-15）**：帶明確 item 時打字屬性照樣建立（P1／P2）；
不相鄰的 toggle 對照做了，而且**推翻了預測**（P4）。

## 處置（外部裁決，2026-08-15）

**先判 STOP，再量兩件事，然後一次 relink 把整個佇列帶進去。**

1. **現在**：E2-C 第一輪依 8.0 判 `E2_STOP_OR_RESCOPE`——這不是選擇，是預先登記的
   結果；看到紅之後改判別的就是 029／044 那種罪。同時**把 `E1_GO_ODT_EDITOR` 的
   涵蓋範圍就地標註**（這四個動作只驗過「開啟」方向，沒有任何一格開過存出來的 ODT）
   ——是標註，不是撤銷。
2. **relink 之前先量兩件**：上面那個原生探針；以及 `d1-body-collapsed` 的序列二分。
3. **一次有計畫的 relink**，照 E2-B 的 P-plan 形式，帶**完整**佇列：四個參數字串、
   `d1-body-collapsed` 若是引擎側所需的修法、規格已經記為「下次 relink 必帶」的
   manifest 債（4.2 的註腳 `limits`、2.5 的十個繼承動作 gesture mask 執行），
   以及對 `changed` 的處置——**建議是記錄而不是改**：9.5.2 已經把這四個動作的
   `changed: true` 定義成「引擎接受且狀態前進」，那讓 `:2085` 的字面值變成
   有文件的語意而不是謊言。新契約版本（v3）、新的 builder 與 profile 目錄，
   照「版本是身分」。
4. **`e1-editor-v1` 可分割**，等 v2 的參數化形式在產品上驗過再單獨決定。

**為什麼不現在就 relink**：`d1-body-collapsed` 是同級的 STOP 而機制未明，
可能也要動引擎。`handoff/PLAN-E2-B-relink-and-freeze.md` 自己寫過規矩——
**「P1 完成才能 relink。漏一項就是第二次 relink」**。

## 時間軸

| 日期 | 事件 |
|---|---|
| 2026-08-11 | finding 030：兩個清單命令是 toggle，**已修**（送 `On` 參數） |
| 2026-08-15 | E2-C D1 第一輪 smoke 的四個 `-false` 格全紅 → 追到同一個形狀，四個 inline 格式從來沒被修過 |
| 2026-08-15 | 全新文件對照 ＋ 原始碼逐行對照，兩瀏覽器一致；本 finding 建立 |
| 2026-08-15 | **原生探針**：七個預測六個成立。**P1 成立＝修法確認**（帶參數就是 setter，兩個方向都是）；**P7 成立**＝帶參數 `false` 可以把已套用選取的格式**移除**，而出貨產品今天做不到；**P4 破**＝bare 是相對於游標處狀態的切換，不是殼層翻轉 |
| 2026-08-15 | **外部裁決（fable）**：推翻「縮限也要 relink」，推翻「參數形狀不明」，並指出 `d1-body-collapsed` 是同級 STOP、relink 時機該由它決定。處置定為「先判 STOP → 量兩件 → 一次 relink」 |

## 證據

`findings/evidence/045/`（英文 README），兩瀏覽器各一輪，含存出來的 ODT。
