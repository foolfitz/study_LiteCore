# SPEC-M3-v27-finding-176：空行按清單改讀第一段（引擎 `e2-editor-v27`、殼層 generation 81、宿主 0.2.43）

> 狀態：**釘死**（2026-10-30，任何實作與執行之前；原生量測 N-176、N-Q63 是釘死前的量測）。釘死之後只准追加（CLAUDE.md 第 10 節）。
> 草案經一次對抗性審核（opus，2026-10-30），見 §12。
> 依據：finding 176；fable 裁決 2（`findings/evidence/176/RULING-fable-2026-10-30.md`，§3.2 殼層項、§3.3 引擎項 C、§3.4 普查、§3.5 預設）；fable 裁決 3（`findings/evidence/176/RULING-fable-2026-10-30-c.md`，C 的設計，以下引用寫成「裁決 3 Q1.2」）；原生臂 `findings/evidence/176/native/`（`5d11bd4de`，與 Q6.3 的補量）。
> 擁有者：上一個 session「先交接，下個session做1跟2」（1＝殼層項、2＝引擎項 C）；本 session「如果跟ddev無關就發給fable」（C 的設計）、「C 一併交 fable」（083 的路）。裁決 2 §3.2：殼層項跟下一個殼層 generation 一起出，不單獨出版——所以本規格是一個批次。

## 1. 為什麼要有

擁有者在宿主 0.2.42 手測 (a)：有內容的文件空一行按項目符號，符號出現了，同時跳出「動作已送出，但這一格的檢查涵蓋了不只一個段落，無法單獨核對你的段落……」，畫面下方的「上次操作」寫「• 項目符號 失敗」〔實測，擁有者畫面；finding 176〕。

兩件事，兩個修法：

1. **「失敗」是假的**（殼層）。`run()` 在看處置之前就把 `#s-latency` 寫成 `${label} 失敗`（`web/e2-editor-app.js` 約 2133 行），`review` 分支沒有改回來。S2 run-02 的 48 筆紀錄全是 `• 項目符號 失敗`〔實測〕。
2. **提示本身**（引擎）。核對用 `.uno:SelectText` 選游標所在段落；在空段落上它一定多選到下一段，讀回兩段 → `multi-block-readback` → `review`（finding 046）。原生臂量到〔實測，`native/README.md`〕：
   - 裁決 2 提的候選（清單狀態項）在每一格都晚於引擎組回覆的那次 poll（25/25，中位數 300 ms）——拿不到；
   - 讀回的**第一段**（解析器的 `listTag`／`blockTag`，`formatBarrierReadbackSatisfied` 本來就只讀它們）在每一個多段讀回裡都等於派送那一段在存檔裡的狀態（16 格 × 5 輪），連「什麼都沒套上而下一段本來就是項目符號」的陷阱（n2）都分得出來；
   - 依原始碼〔讀碼，裁決 3 §2 核對〕，`.uno:SelectText`＝`FN_SELECT_PARA`：從游標所在段落的開頭選起，只有在已經位於段尾（空段落）時才往**下**跳一個內容節點，絕不往上。

## 2. 範圍

**做**：

1. 殼層項：`review` 時「上次操作」寫 `${label}：待確認`（§4.3）。
2. 引擎項 C：有序引擎的 **collapsed 路徑**，多段讀回改由現有判斷式判第一段，選取前不再做幾何還原（§4.1）。適用動作：**五個段落動作全部**——項目符號、編號、取消清單、標題、內文（裁決 3 Q3；Q6.3 的補量五個都 `IN-SCOPE`，§7.1 N-Q63）。
3. 引擎 profile `e2-editor-v27`（v26 的後繼，**要重新連結**，擁有者跑）、worker、manifest、連結機械。
4. 殼層 generation 81；宿主 0.2.43。

**不做**：

- **083 的路不改**（裁決 3 Q5）：最後一行的空段落、只有一段的空白文件，`.uno:SelectText` 什麼都選不到，沒有任何讀文件的觀測值；按清單之後照舊跳 083 那句（一般樣式），「上次操作」改成「待確認」。候選（`.uno:SelectAll` 等）留給之後的批次，先量原生。
- RangeSingle、RangeCross 兩條路徑不改（裁決 3 Q1.1、Q2.4）。
- undo 不當判決依據（裁決 3 Q4.1）；只記錄（§4.1 第 4 項）。
- 頁面三句提示的文字與樣式不改（v26 U3 的狀態）。
- K、計數鏈（照擁有者 10-12 的併批規則延後，§11 列出累積的未計數改動）。

## 3. 決定紀錄

| 題 | 決定 | 出處 |
|---|---|---|
| 殼層項的字 | `${label}：待確認` | 裁決 2 §3.2 的例子；`review`＝「已送出、佇列開著、請你看一下」，同一畫面的提示正在請使用者確認 |
| C 的判法 | collapsed 路徑上 `readback.multiBlock` 不再一律拒絕，交給現有的 `formatBarrierReadbackSatisfied`（只讀第一個結構標記與第一個區塊標記）；**雙向**：符合 → 已驗證，不符合 → `postcondition-not-met`（與有字的段落今天相同，rollback 處置） | 裁決 3 Q1.2；不保留 `review` 給「不符合」，因為那是新機制（CLAUDE.md §4） |
| 選取前的還原 | collapsed 路徑拿掉（G）；選取後的還原與 NONE 確認照舊 | 裁決 3 Q2；原生 G＝F（每格 5/5） |
| 路徑 | 只有 collapsed | 裁決 3 Q1.1 |
| undo | 不參與判決；派送前與回傳時各讀一次 `.uno:Undo`，紀錄帶「有沒有變」與新的頂端說明 | 裁決 3 Q4 |
| r1（空行本來就是項目符號，再按一次） | 變成「已驗證」：後置條件成立；`changed:null` 本來就不宣稱是這次派送做的 | 裁決 3 Q4.1、finding 030 的 setter 語意 |
| 083 的路 | 維持提示 | 裁決 3 Q5 |
| 被綁的 F3 格 | 依設計退役（PASS→FAIL，事先宣告），由衍生檢查接手 | 裁決 2 §3.3、裁決 3 Q6.4 |
| 046 的 B 案 | 在本規格的條件下（collapsed、`FN_SELECT_PARA`、§10 釘的原始碼）被取代；其餘情況照舊否決。寫成 046 的追加 | 裁決 3 Q1.6 |
| profile 名稱 | `e2-editor-v27` | 「版本是身分」；v26 是 manifest 後繼，下一個改引擎的批次叫 v27（v26 規格 §2） |
| define 名稱 | `OXSDK_E2_V27_FIRST_BLOCK`，要求 `OXSDK_E2_V25_FORMAT_PROOF`（沒有就 `#error`） | v25 的寫法 |
| 回歸基準 | v25 引擎／generation 80／0.2.42 | 裁決 3 Q6.7；記憶「回歸基準＝上一個出貨版」 |
| `editorContract.formatBarrier` 葉 | 保留 `verified-format-readback-v2`，不升版 | 葉名的是協定（以讀回驗證、紀錄形狀）；v27 改的是 collapsed 路徑接受哪些讀回，紀錄形狀不變（只多 `undo`，worker 投影）；殼層、worker、SDK 沒有任何地方讀這個葉〔審核 grep〕。升版只會多一個沒人讀的 manifest 差異（審核細項 12，判斷題，主 session 決定） |
| undo 投影到產品 | worker 只投影 `{read, changed, actionsBefore, actionsAfter}`；`top` 只留在引擎紀錄 | undo 說明可帶最多約 20 字的文件文字（`caret_delete_witness.hpp:17`），worker 的投影原則是最小（審核細項 13） |
| 連結前的 WASM 預測 | 要做（§7.2 PL-1）：v26 的引擎紀錄已經帶 v27 判決的每個輸入 | 審核第 1 項；`probe_engine.cpp:1700-1752` 已核對 |

## 4. 設計

### 4.1 引擎（全部在 `#ifdef OXSDK_E2_V27_FIRST_BLOCK` 之下）

1. **`ordered_format.inc` `startOrderedFormatAction`**：`barrier.route == FormatBarrierRoute::Collapsed` 時，`.uno:SelectText` 之前**不呼叫** `restoreOrderedFormatPoint()`；RangeSingle 照舊呼叫。選取後的 `restoreOrderedFormatPoint()` 與 `restoreConfirmed` 不動。`restorePoint` 照舊在派送前擷取（選取後的還原要用）。
2. **`ordered_format.inc` `finishOrderedFormatReadback`**：非 cross 分支裡，`readback.multiBlock` 只在 route **不是** Collapsed 時拒絕（`multi-block-readback`，RangeSingle 照舊）；Collapsed 時往下走：a11y 段落識別（照舊；產品 core 沒有 a11y，`paragraphIdentityChecked` 是 false）、`restoreConfirmed`、`formatBarrierReadbackSatisfied()`。不改解析器、不改判斷式。
3. 成功與失敗的紀錄不加新的判決欄位：`appendFormatBarrierDetails` 本來就序列化 `readback.multiBlock`、`blockCount`、`itemCount`、`listTag`、`blockTag`（`probe_engine.cpp:1737-1743`，裁決 3 §2 核對），worker 本來就轉送 `readbackBlockCount`、`itemCount`——「這個判決是從兩段讀回得出的」在產品回覆裡看得出來。
4. **undo 紀錄**（記錄，不判決）：在 `startOrderedFormatAction` 裡、路由通過之後、`postUnoCommand` 之前讀一次 `.uno:Undo`，最後一次還原與其確認讀取之後再讀一次（都不在三個還原呼叫之間）。讀法用引擎既有的 `readMergeUndoPayload`（`OXSDK_MERGE_KEY_UNDO`，v25 的規則已帶〔Makefile 2256〕，定義在 inc 被 include 之前〔審核：4159 對 6244〕），解析用 `probe::merge::summarizeUndoPayload`（`merge_key_undo.hpp:334`）。紀錄是 **`formatBarrier` 物件裡面**的一個欄位（worker 從 `event.formatBarrier` 讀；`keyUndo` 那種頂層欄位是錯的位置）：`"undo":{"read":true|false,"changed":<兩次原始 payload 不相等>,"actionsBefore":N,"actionsAfter":M,"top":"<回傳時第一個 comment>"}`；任一次讀不到 → `read:false`、其餘省略。成功、`postcondition-not-met`、派送後的其他拒絕都帶；**派送前的拒絕不帶**（沒有嘗試讀，不是讀不到）。回覆組成（`deferOrderedFormatReply`、`finishOrderedFormatReadback`）裡不呼叫任何 LOK（`test_ordered_format_scope.py` 的 `violations()` 守這條）。
5. 前置處理不變（V0-v27）：以 v23、v24、v25 的 define 前置處理 `E2_C_SOURCES` 的每一個單元（含 `unoembind_stub`），輸出與改動前的 HEAD 逐位元組相同。
6. **宣告的 hunk**（封閉清單，v25 §15.4 的寫法）：`editor_api.h` 的 `#error` 守衛（所在的 TU 是 `editor_api.cpp`）；`FormatStateBarrier` 的 undo 欄位；`appendFormatBarrierDetails` 的 `undo` 序列化；inc 裡的兩次 undo 讀取；inc 裡 collapsed 路徑拿掉選取前的還原；inc 裡 `multiBlock` 分支只對非 collapsed 拒絕。v27 區塊**不巢在** v25 區塊裡（`strip_v25` 的非貪婪正規式會因此失效）。

### 4.2 worker（`sdk/v27-first-block-worker.js`）

由封存的 v26 worker（`build/archive/e2-editor-v26-44cb15ea-worker-95d6e7ae/sdk-worker.js`）衍生，差異是封閉清單：

1. `featureExtendPermitted` 的 `"e2-editor-v26"` → `"e2-editor-v27"`（v26 規格 §4.2：不改，行延伸靜默失效）。
2. `productFormatBarrier` 加 `undo`：`value.undo` 是物件時投影 `{read, changed, actionsBefore, actionsAfter}`（布林與整數之外的值 → 該欄 `null`；**不投影 `top`**，§3），否則 `null`。
3. 檔頭註解說明衍生來源與本節。

### 4.3 頁面與殼層

`web/e2-editor-app.js`：

1. `run()`：先讀 `const recovery = error?.recovery;`，再寫 `el.s.latency.textContent = recovery === "review" ? \`${label}：待確認\` : \`${label} 失敗\`;`。唯讀（`：唯讀`）、成功（`N ms`）、rollback／restart／無處置（`失敗`）、三句提示與樣式、`console.warn` 都不變。
2. `workerUrl` → `./profiles/e2-editor-v27/sdk-worker.js`；`PINNED_WASM_SHA256` → v27 實際 wasm 的前 16 位（連結後才知道）。
3. 「`review` is NOT a failure」那段註解加一句指向本規格。

client、session 不改。

### 4.4 manifest 與身分

profile `e2-editor-v27`；`editorContract` 每一個葉（含 `select-all` 的三個 gesture 與 `limits`、`typedInsert`）等於 v26；只換 `profile`、`sdkVersion`、`wasmSha256`、`loaderSha256`、`workerSha256`；匯出表等於 v26 封存的 `exports.txt`（沒有新增）。

## 5. 身分與連結的機械（比照 v25 §5，只換名字）

- Makefile 的 v27 區塊接在 v26 之後：`E2_V27_BUILD := build/e2/editor-v27`、`E2_V27_DIST := dist/profiles/e2-editor-v27`；編譯規則逐字照抄 v25，defines 多 `-DOXSDK_E2_V27_FIRST_BLOCK`；依賴加 `src/ordered_format.inc`（v25 已有）；匯出表取 v26 封存的；worker `cp sdk/v27-first-block-worker.js`，前置檢查驗衍生來源是封存的 v26 worker（`95d6e7ae…`）；連結受守衛（`refuse_unasked_relink`），用 `link_product_stack_1m`。
- 新檔：`tools/build_e2_v27_first_block_profile.py`（v25 的建構，再把 `select-all` 換成 v26 的葉）、`tools/check_v27_first_block_contract.py`、`tools/link_v27_first_block_owner.sh`、只跑測試的 `test-v27-first-block-static`。v25、v26 的工具位元組不動。
- `test-e2-c-static` 的 M1-1 載體行加 `--carrier E2_V27=probe_engine,sdk_api,editor_api`，先紅（證人）再綠。
- `tools/what_the_link_ships.py` 加 variant `link-batch-v27`，`--since 9d7fb9e7c`（v25 的連結原始碼：那之後 `wasm_sdk_probe/src` 沒有 commit，連結前再以 `git diff 9d7fb9e7c -- wasm_sdk_probe/src` 只剩 v27 的改動確認）；它看不到 `.inc`（v25 規格 §15 的盲點），所以另由 hunk 讀取器 `check_v27_ships_confined.py`（`check_v25_ships_confined.py` 的衍生，基準同上）證明 v27 的改動全在 v27 區塊內、恰好是 §4.1 第 6 項的清單。
- 改了 inc，v23D、v23D_R2、v23、v24、v25 的物件依 Makefile 都會變舊（1875、1967、2059、2149、2251 行依賴 `src/ordered_format.inc`）；擁有者的那一行指令只建 v27 的 manifest，所以連結前記錄那一行指令的 `make -n`：只有 `build/e2/editor-v27` 的編譯行加一次受守衛的連結。
- 連結前：驗 v26 封存的 `SHA256SUMS`；凍結集合 `findings/evidence/v27-176/pre-link/frozen-set-before.sha256`；確認 `build/e2/editor-v27`、`dist/profiles/e2-editor-v27`、連結 log 都不存在。
- **連結是擁有者的**：`bash tools/link_v27_first_block_owner.sh`（會編譯；agent 只跑 `bash -n`）。

## 6. 普查（裁決 2 §3.4；釘死前做完，2026-10-30）

一次性量測（CLAUDE.md §1 的形式三：成員住在別處），指令與輸出存成證據：`findings/evidence/v27-176/census/census.sh`、`census.txt`。對 `wasm_sdk_probe/tools/`、`web/`、`editor-shell-v2/`、`sdk/` 搜 `s-latency`、提示字串、兩個會移動的檢查 id、`recoveryPairing`、`multi-block-readback`，以及 `findings/evidence/` 裡讀這兩個 id 的 `.py` 與 `DISPOSITIONS.md`。

| 讀的人 | 讀什麼 | 殼層項 | 引擎項 C |
|---|---|---|---|
| 被綁的 F3 runner `run_e2_c_product_path.py`（與 `run_e2_c_product_path_clipboard.py`）格 `bulleting-a-blank-line-does-not-demand-a-rollback`（約 5721 行） | 提示含 `無法單獨核對`／`取不到任何內容` 且含 `不是你要的就按「復原」` | 不動（不讀 latency） | **PASS→FAIL，依設計**（§8） |
| 同 runner `notice-action-recovers-the-session`（約 5776 行） | `recipe_ran = "項目符號" in latency`；053 的誘發手段 | 不動（新字串仍含「項目符號」） | 誘發手段到不了 `review`，`attempts` 紀錄改變；2026-08-16 的子句（「或它派送的格式動作完成了」）讓它維持 NE 而不是紅（§8） |
| 同 runner 的定位游標、B2 邊界（4213、4302、5341、6317、9091 行） | `"失敗" in latency` | 不動（游標與打字的路） | 不動 |
| 同 runner 的 `recoveryPairing`（3939-3964、9918-9946 行） | `recovery_pairing_holds(bulleting, notice)`；不成立時整份報告 `ok:false` | 不動 | **`held` true→false、報告 `ok:false`，依設計**（§8 第 3 項） |
| 同 runner 的 `MUTATIONS["review-disposition"]`（1648-1664 行）、`caret-off-by-one-line` 的 `alsoRed`（1709 行起） | 前者的主體是 046 那格的 `review` 處置；後者把 046 那格列為連帶紅 | 不動 | 前者失去主體（v27 上那一格不再 `review`），後者的連帶清單不再準；兩者都記錄、不判（§8 第 4 項） |
| 同 runner 的 047 誘發手段（存檔、點、按清單的競賽） | `attempts[0]` | 不動 | G 改了呼叫序列，`attempts[0]` 可能變；記錄、不判 |
| `read_v25_f3.py`（v26 §5.6 的讀法一）、`host-0.2.39/k-nine-cells/DISPOSITIONS.md` 第 1–2 列、0.2.42 的 `prepare-release.py`（要求讀法一＝`F3_RED` 且問題恰好是宣告的那些） | P 群取自 DISPOSITIONS；`recoveryPairing.held is True` | 不動 | **讀法一依構造紅**；DISPOSITIONS 第 1–2 列依設計退役（§8 第 5、6 項） |
| `check_soak_bank.py` | v13 的 soak bank（39 PASS／2 NE，NE 含 notice 那格） | 本批不跑（預設 profile `e2-editor-v13`，歷史） | 同左 |
| 殼層 client `paragraph-editor-client.js:330` | `failureShape === "multi-block-readback"` → 已送出、未核對 | 不動 | 程式碼不變；v27 上只剩 RangeSingle 會走到這個 shape |
| B1 `check_v79_blank_bullet.py`（被 B1-79 綁）、S2 `check_v80_blank_bullet.py` | 等 `項目符號` in latency；判準讀 083 句與 `on_173_path` | 不動（等待仍成立；判準不讀 latency） | 不動（083 的路不改） |
| `run_e2_c_page_smoke.py`、宿主 `check_m3_host_entry.smoke_ok`（`check_m3_page_honesty` 的 K-held／U1） | 修訂號 +1 **且** latency 不含 `失敗`；預設動作 `set-paragraph-heading` | 不放水：`review` 不推進修訂號〔讀碼：`failFormatBarrier` 不呼叫 `advanceRevision`；實測：S2 run-02 按完 `revision` 仍為 "0"〕 | 不動（有字的段落） |
| `check_m3_page_honesty.py` V4 | `^定位游標 \d+ ms$`、`^下移一行 \d+ ms$` | 不動 | 不動 |
| `check_v25_clear_format_noop.py`（F2）、`check_v26_select_all.py`、`run_calc_editor_host.py` | 只等 `定位游標` | 不動 | 不動 |
| `diag_format.py`（v25 的 F1） | 空行按清單的錯誤紀錄 `dispatched:true` | 不動 | 那一格在 v27 上成功、沒有錯誤紀錄可讀；F1 不在本批重跑，由 S3 接手（§7.3） |
| 殼層單元 `page-review-sentence.test.mjs`、`page-review-presentation.test.mjs` | 直接造錯誤物件，判提示 | 不動 | 不動 |
| 歷史探針（`probe_079_selection_shape.py`、`probe_093_fix_shape_oracle.py`、`probe_129_m4_wasm.py`、`probe_autosave_m1.py`、`probe_hand_test_0212.py`、`probe_paste_latency.py`、`v21_item1_observer.py`） | 讀 `#s-latency` | 本批不跑，不是閘門 | 同左 |

## 7. 判準

證據目錄 `findings/evidence/v27-176/`。每條都有「沒做的話」的預設。

### 7.1 釘死前（已做；原生，agent 自己跑）

- **N-176**（`findings/evidence/176/native/`，`5d11bd4de`）：`WITNESS-FAILS`（照預先登錄）；記錄的第一段與 undo 如 §1。
- **N-Q63**（裁決 3 Q6.3，PREDICTION 追加二在執行前登錄停止規則，`3f9c130ef`）：10 格 × 5 輪全乾淨；G 之下每一格的第一段都等於存檔 → 項目符號、編號、取消清單、標題、內文五個動作 `IN-SCOPE`（`read_q63.py`，紅案 6/6）。另記錄：內文套到空標題（b1）在 F 與 G 之下都讀兩段、第一段是派送那一段，最後一次還原後游標在那個空段落——裁決 3 Q2.1 的假說（F 會選到下一段）沒有出現；兩個空段落相連（a6）讀兩段、第一段是派送那一段。登錄的標題對照 b0 自己套了 Heading 1、證明不了 fixture 的初始狀態，另以「載入後不做任何事直接存檔」確認是 `text:h`（`out-q63-fixture-check/`）。「先登錄後執行」靠的是時間：追加二寫著約 12:12，runner log 的第一筆是 04:12Z（同一分鐘），兩者在同一個 commit 裡——commit 本身不是先後的證據（審核細項 11）。

### 7.2 連結前（原始碼與單元測試，agent 自己跑）

| 編號 | 判準 | 紅案（先紅） |
|---|---|---|
| E1 | 新單元測試 `tests/ordered_format_v27_test.cpp`（`test_ordered_format_v27.py` 驅動，前例 v25）：(a) collapsed＋多段＋符合 → 成功，送出的紀錄 `readback.multiBlock == true`；(b) collapsed＋多段＋不符合 → `EDITOR_FORMAT_POSTCONDITION_FAILED`、shape `postcondition-not-met`；(d) collapsed：派送與 `.uno:SelectText` 之間沒有 `reset`／`start`，讀完之後恰好一組 Q 序列，且剩下的那次還原用的是派送前擷取的座標（裁決 3 Q2.2：重釘「兩個還原點都用擷取的座標」那條標籤） | 「v25 的行為」＝把 inc 裡的 v27 區塊剝掉、**帶著** v27 define 編（欄位在 v27 define 之下，不帶就編不過，那是編譯錯不是紅）：必須編得過，且 (a)(b)(d) 印 FAIL |
| E2 | 守住的（今天綠、之後也要綠）：(c) RangeSingle＋多段 → `MUTATION_OUTCOME_UNKNOWN`／`multi-block-readback`（假路由要加 RangeSingle 開關）；RangeSingle 照舊有選取前的 Q 序列；還原失敗照舊拒絕；(f) 成功與兩種失敗都帶 undo 紀錄 | 突變：Collapsed 判斷寫成「所有路徑」→ (c) 紅；G 也套到 RangeSingle → 「RangeSingle 照舊有選取前的 Q 序列」紅；undo 紀錄只在成功時寫 → (f) 紅 |
| E3 | 改過的 inc 上，三支既有的 inc 文字測試照舊綠：`tests/test_ordered_format.py`（它的突變錨點各恰好出現一次）、`tests/test_ordered_format_scope.py`（`legacy-RESET-only-restore` 突變的錨點 `'    restoreOrderedFormatPoint();'` 仍要改得到原始碼；`violations()` 守「回覆與序列化裡沒有 `pClass`」）、`tests/test_ordered_format_v25.py`（D1 不帶 v27 define，仍是 v25 的紀錄）。這三支都不在任何 Makefile 目標裡，所以逐支跑、各留收據。`tests/ordered_format_test.cpp` 的「兩個還原點都用擷取的座標」照舊（它不帶 v27 define）——v27 的呼叫序列由 E1 (d) 釘 | — |
| E4 | 正式解析器跑錄下的 HTML（裁決 3 Q6.2；前例 `format_readback_text_test.cpp`，從 `probe_engine.cpp` 以正規式抽出 `FormatReadback`、`parseFormatReadback` 與它的三個輔助函式、`formatBarrierReadbackSatisfied`，不另寫一份）：a1、a2、n2、n3、r1、r3、r4、r5、r6 與它們的 G 版 g-a1、g-a2、g-n2、g-n3（`native/out/<cell>/r1.jsonl`），以及 g-r3、g-r4、g-r5、a6g、b1g（`native/out-q63/<cell>/r1.jsonl`）的 `format.html`——產品跑的是 G，期望 `(listTag, blockTag, blockCount, itemCount, multiBlock)` 與每個目標的判斷式結果。關鍵列：n2 → `listTag ""` → 對 ul 不符合；r6 → ul、`itemCount 2`、符合；r5 → `blockTag h1` | 改一個期望值要紅（落地前先做） |
| W1 | worker 對封存 v26 worker 的差異恰好是 §4.2 三項 | 多一行要紅 |
| W2 | worker 的 `undo` 投影：物件 → `{read, changed, actionsBefore, actionsAfter}`；缺 → `null`；型別不對的欄 → `null`；引擎紀錄裡的 `top` **不出現**在投影裡 | 四個反例：缺、型別錯、`top` 被投影出來、頂層 `undo`（不在 `formatBarrier` 裡）被讀成投影 |
| V0-v27 | v23、v24、v25 define 下 `E2_C_SOURCES` 的每一個單元（含 `unoembind_stub`）前置處理輸出與改動前 HEAD 逐位元組相同（`v0_preprocess.py` 的衍生） | 正向對照：共用段落改一個字，恰好那幾列不同 |
| S | em++ `-fsyntax-only`（v27 define）乾淨，`taskset -c 0`；正向對照：v27 才有的錯在帶 define 時被抓到、不帶時看不到；v27 define 不帶 v25 撞到 `#error`——對照要打在**帶著守衛的那個 TU**（`editor_api.cpp`，v25 §13.1 的教訓：打錯 TU 會假綠） | 正向對照本身 |
| M1-1 | 載體行先紅後綠 | 證人 |
| L | `what_the_link_ships --variant link-batch-v27`；hunk 讀取器 `check_v27_ships_confined.py`：v27 的改動全在 v27 區塊內、恰好是 §4.1 第 6 項 | hunk 讀取器的紅案（區塊外多一行；少一個宣告的 hunk） |
| PL-1 | **連結前的 WASM 預測**（審核第 1 項；鏡像、v26 profile、不連結、不用 DDEV）：在 worker 裡包 `JSON.parse` 讀引擎原始紀錄（v25 F1 `diag_format.py` 的觀察器），跑 S3 的配方與 F3 list-contexts 那一格（點 (0.92, 0.28)、斷行、按清單），每個配方兩瀏覽器 × N＝3。讀取工具 `read_v27_pl1.py` 對每一筆 `multi-block-readback` 紀錄套 v27 的判法：`route == collapsed`、`readback.parsed`、三個旗標皆 false、`restoreConfirmed`、判斷式（`listTag`／`blockTag` 對目標）→ 「會驗證」。**N/N 都要「會驗證」**，且每一筆的 `failureShape` 是 `multi-block-readback`（＝量到的是 046 那格） | `--self-test`：`restoreConfirmed:false`、`listTag:""`、`route:range-single`、少一筆，各自要紅 |
| PIN | §10 的原始碼釘選、凍結集合 `frozen-set-before.sha256`、v26 封存的 `SHA256SUMS` 驗證、擁有者指令的 `make -n`（§5） | 釘選工具：改一個位元組要紅 |
| U1 | 殼層單元 `editor-shell-v2/tests/page-review-latency.test.mjs`（切出 `run()`，比照 v26 U3）：三種 `review` → strip＝`• 項目符號：待確認`、不含「失敗」；rollback／restart／無處置 → `• 項目符號 失敗`；唯讀 → `：唯讀`；成功 → `N ms` | 未修改的頁面上三種 `review` 紅；見證 `u1/red-before.txt` |

**預設**：任一條沒做或紅案沒先紅，不交連結。PL-1 不是「會驗證」N/N 也不交連結：那表示 v27 在 WASM 上會把今天的 `review` 換成 rollback（佇列擋住），比今天更糟。

### 7.3 連結之後（靜態，連結當天；瀏覽器，鏡像，不用 DDEV）

- **P-v27**：五個 artifact 的雜湊、`check_v27_first_block_contract.py`（葉等於 v26、只換三個雜湊與兩個名字）、匯出表等於 v26、封存 `build/archive/e2-editor-v27-<wasm8>-worker-<worker8>`；凍結集合對 `frozen-set-before.sha256`：既有的檔一個都沒變，新增的恰好是 v27 的四個 profile 檔（v25 §14 的作法）。
- **切頁**：頁面改指 v27；殼層 generation 81 等本批殼層改動全部做完才凍：與 80 只差頁面一個檔（工具算出的差異＝封閉清單）；排除清單＝v80 的＋`sdk/v27-first-block-worker.js`（v25 §15.2 是執行之後才找到這一條）；Makefile bundle 行改指 81（改前紅、改後綠、指回 80 紅）；`make -n e2-c-assets` 只印一行 `cp`。
- **S3（新，046 那一格，使用者那條路）**：`tools/check_v81_blank_line_bullet.py`。程序：開一份兩段的文件（`Plain first`／`E1-EMPTY-AFTER`；由 `native/fixtures/two-plain.fodt` 經原生 core 一次 `saveAs` 成 ODT，收據與 sha 釘在工具裡），真的點第一行行尾之後，真的按 Enter，真的點工具列的項目符號，真的打一個標記字，按產品的存檔，讀存檔 ODT。產品 before＝generation 80（v26），after＝generation 81 候選（v27）；兩瀏覽器 × N＝3。
  - after PASS（每一次）：按完 `state == ready`；`#toast` 空；按鍵期間主控台沒有 `[review]`；strip 符合 `^• 項目符號 \d+ ms$`；**worker 回覆列**（B1 的觀察器已記錄）：回覆 ok、`completion == "verified-format-readback"`、`formatBarrier.route == "collapsed"`、`formatBarrier.readbackBlockCount == 2`（同時端到端證明 §4.1 第 3 項「看得出是兩段讀回判的」）；`formatBarrier.undo` 記錄、不判；存檔裡標記所在段落在 `<text:list>` 裡、該清單樣式是項目符號；兩個鄰段的文字與種類不變。之後按 **兩次** Ctrl+Z（第一次撤回打字、第二次撤回 `Number On/Off`），再存一次檔：仍是三段、中間那段空且不在清單裡、兩個鄰段不變（以兩個鄰段定位中間那段）。
  - before 為 176 而紅：提示含「不只一個段落」、strip 不符合上面的樣式、存檔照樣在清單裡（＝清單有套上，只是沒被核對）。
  - **突變普查**（裁決 3 Q6.5）：`--mutation press-list-none`（按「取消清單」代替項目符號）after 必須紅（存檔沒有清單）；`--mutation hide-review-toast`（頁面變體把 `review` 的提示藏起來＝B 案的形狀，用在 before 上）必須紅；`--mutation cosmetic-review`（頁面變體在 before 上同時藏提示、不印 `[review]`、strip 寫 `N ms`＝外觀上完全像 v27）**必須紅**——只有 worker 回覆列抓得到（裁決 3 Q6.5 說「因為讀 ODT」，但 before 的 ODT 本來就在清單裡，ODT 分不出來；審核第 4 項）。
  - **與裁決 3 Q6.4 的差異**（明寫）：Q6.4 以兩個鄰段定位那個空段落；S3 在裡面打了一個標記字，用標記定位，Ctrl+Z 之後才以鄰段定位。S3 用的是 a3 的 fixture 形狀（兩段的文件），不是 F3 的 list-contexts——同形狀、不同 fixture；list-contexts 那一格本身由 F3-81 的結果與 PL-1 涵蓋。
  - `--self-test REPORT`：每個子句一個突變，全紅。
- **S2′（083 的路與殼層項，擁有者的路）**：`tools/check_v81_blank_bullet.py`，由 `check_v80_blank_bullet.py` 衍生（後者不改）：B1 的程序與四條、S2 的三條照舊；after 再加 `press.latency == typed.latency == "• 項目符號：待確認"`（打字不經 `run()`，strip 留到下一個動作；S2 run-02 的 `typed.latency` 與 `press.latency` 相同〔實測〕）。before＝generation 80 為 176 的殼層項而紅＝B1 與 S2 的條件成立而 `press.latency == "• 項目符號 失敗"`。兩瀏覽器 × 兩臂 × N＝3。
- **F3-81**：重新衍生 `run_e2_c_product_path_clipboard.py`（綁 v81 manifest，W-f3 的作法；衍生前後各跑一次舊值掃描）。讀法：`read_v80_f3_equal.py` 的衍生對 F3-80，**事先宣告的移動恰好是**：兩瀏覽器的 `bulleting-a-blank-line-does-not-demand-a-rollback` PASS→FAIL，**而且 FAIL 的理由釘死**：`observed.state == "ready"`、`observed.toast` 為空、`unverifiedSentence` 為 null（rollback 也會讓這一格 FAIL，但那時 `state` 不是 ready）；`notice-action-recovers-the-session` 維持 NE（`attempts` 的 053 那筆不再到 `review`）；`recoveryPairing.held` true→false、報告 `ok:false`、verdict 是「the recovery pair disagrees」（§8 第 3 項）。其餘格子與 F3-80 相同。讀法一（`read_v25_f3.py`）預期 `F3_RED`，問題恰好是：兩瀏覽器的 bulleting P 格，加兩瀏覽器的 `held False`（§8 第 5 項）。有不在清單上的移動就停下查清。
- **F4-81**：v80 四臂工具的衍生，兩瀏覽器 24/24。
- **E1-C**：`check_e1_c_bundle_intact.py` `intact: true`。
- **V0′-81**：照 v80 的作法，換回宣告的檔重讀 B1、F3-80 的讀取器，逐位元組相同。
- **預設**：任一條沒跑、NE、或有未宣告的移動，0.2.43 不送裝。

### 7.4 宿主 0.2.43

- 由 `findings/evidence/host-0.2.42/` 衍生（不改那些檔）：父＝`host-0.2.42` 的 `93b1ebc`；前身 archive `host-0.2.42-engine-01e6c3fb62626d16`。
- 套件判準：對 0.2.42 恰好改 1 筆（頁面）、新增 4 筆（`profiles/e2-editor-v27/`）、移除 4 筆（`profiles/e2-editor-v26/`，工具先確認套件裡沒有別的頁面用 v26）。紅案：多一筆、少一筆、v27 的 wasm 等於 v26 的（＝沒換引擎）。
- 安裝要擁有者的時段（DDEV 共用），`slot.json` 有明確的「不開站」回答。
- 裝完：Files 實流程、`capture-after.py`（具名限制照舊）、請擁有者手測：(a) 有內容的文件空一行（後面還有段落）按項目符號 → 沒有提示、「上次操作」顯示時間；(b) 新的空白文件按項目符號 → 083 那句（一般樣式），「上次操作」寫「待確認」；(c) (a) 之後 Ctrl+Z → 清單撤回。
- **預設**：沒有時段就不裝；0.2.42 仍是日常未計數候選。

## 8. 被綁的格子與讀取器：事先宣告的移動

1. `run_e2_c_product_path.py`（被綁，不改）的 `bulleting-a-blank-line-does-not-demand-a-rollback`：**依設計退役**。它斷言 046 那格的提示存在；v27 上那格沒有提示，PASS→FAIL 是預期（理由釘在 §7.3 F3-81）。接手的是 S3 的 after 判準（同形狀、不同 fixture：點行尾、斷行、對空段落按清單，加上 worker 回覆列與讀存檔）。之後的規格不得再把這一格的 PASS 引為任何事的證據。
2. 同 runner 的 `notice-action-recovers-the-session`：它的誘發手段之一（053）是 046 那格；v27 上那一步不再進 `review`、也不進 `recoverable-error`。這一格今天就是 NE（誘發手段 2026-08-17 起就欠），之後照樣 NE；2026-08-16 的子句「或它派送的格式動作完成了」（`recipe_ran`）讓它不變紅。
3. **`recoveryPairing.held` 依設計 true→false**（審核第 2 項；`run_e2_c_product_path.py:3939-3964`、`9918-9946`）：哨兵的前提是「bulleting FAIL ⇒ 佇列擋住」；v27 上 bulleting FAIL 是因為提示不見了而佇列開著，`recovery_pairing_holds("FAIL", "NOT_ESTABLISHED")` 回 false，整份 F3 報告 `ok:false`。哨兵跟著 bulleting 那格一起退役；v27 之後的任何讀法不得要求 `held:true`。
4. 同 runner 的 `MUTATIONS["review-disposition"]` 失去主體、`caret-off-by-one-line` 的 `alsoRed` 不再準：記錄、不判。
5. **讀法一 `read_v25_f3.py`**（v26 §5.6）：P 群取自 DISPOSITIONS、要求 `held is True`，v27 上依構造紅。F3-81 的讀法一預期結果恰好是 `F3_RED`＋第 7.3 節列的四個問題；0.2.43 的 `prepare-release.py` 要求的就是這個恰好的結果（0.2.42 的前例：要求讀法一恰好是宣告的紅），其他結果拒絕。
6. **K 的 `DISPOSITIONS.md` 第 1–2 列**（兩瀏覽器的 bulleting 格）：對 K 依設計退役，接手的是 S3。下一次 K 的協定要寫明這兩列不再以 P 群判。
7. F3 的相等讀取器（v80 的衍生）：預期的移動恰好是第 1、3 項（兩瀏覽器）。

## 9. 具名限制與量測範圍外（裁決 3 Q1.7）

- **量測範圍外**（不是靜默略過）：表格、frame、附註裡的段落；隱藏的追蹤刪除（合併段落，`IsSttPara` 的檢視位置分支）；不同種類的巢狀清單（單段路徑本來就有的問題，不是 C 引入的）；下一個內容節點不相鄰（那時選不到東西＝NONE，走 083 的路）。
- **L-083-stays-a-toast**：最後一行的空段落、只有一段的空白文件，按清單照舊跳 083 那句；「上次操作」寫「待確認」。
- **L-first-block-rests-on-select-para**：C 的正確性靠 `FN_SELECT_PARA` 的語意（§10 釘的原始碼）；core 升級就要重開這一題。
- **L-noop-verified**：空行本來就是項目符號再按一次，v27 判「已驗證」（後置條件成立），不宣稱是這次派送做的（`changed:null`）。
- **L-no-a11y-identity**：產品 core 沒有 a11y，段落識別照舊判「未檢查」；C 不依賴它。

## 10. 原始碼釘選（裁決 3 Q1.5）

兩棵樹裡下列檔案的 sha256 寫進 `findings/evidence/v27-176/pre-link/source-pin.json`（工具算、連結前）：連結用的 core（Makefile 的 `LOSRC`＝`../libreoffice-26-8`）與原生證據用的 core（`native-lok-26-8/src`，`native/README.md`）。兩棵一致才算裁決 3 Q1.6(a) 的「第二棵 core build」在這幾個檔上是同一份原始碼；不一致就記下差異、交裁決。限制：這釘的是原始碼，不是編出來的 core。行號照裁決 3 §2：`sw/sdi/swriter.sdi`（5649）、`sw/source/uibase/shells/textsh1.cxx`（1975-1982）、`sw/source/uibase/wrtsh/move.cxx`（76-90、396-406）、`sw/source/core/crsr/pam.cxx`（410-423、1238-1263）、`sw/source/core/crsr/paminit.cxx`（46-47）、`sw/source/core/crsr/crsrsh.cxx`（1438-1454）。連結用的樹由工具從 Makefile 的 `LOSRC` 讀出，不手寫。core 換了，C 的前提要重開。

## 11. 順序

1. N-Q63 跑完、讀完（釘死前；§7.1）。
2. 本規格釘死（commit）。
3. 046、176 的追加（裁決 3 Q1.6、Q6.9）。
4. U1 先紅（見證）→ 殼層項 → U1 綠、殼層測試全綠。
5. 引擎：E1 先紅（見證）→ 改動 → E1、E2、E3、E4、V0-v27、S 全綠。
6. worker → W1、W2；Makefile／工具／連結腳本 → `test-v27-first-block-static` 綠；M1-1；L；PIN（§10 的釘選、凍結集合、v26 `SHA256SUMS`、`make -n`）。
6′. PL-1（鏡像、v26、兩瀏覽器；可以和第 4–6 步平行，但交連結之前要成立）。
7. 交擁有者連結（一行指令＋手冊 `handoff/RUNBOOK-relink-v27.md`）。
8. P-v27 → 切頁 → S3、S2′ → 凍 generation 81 → F3-81、F4-81、V0′-81、E1-C。
9. 宿主 0.2.43 套件 → 擁有者時段 → 安裝 → Files 實流程 → 事後讀取 → 擁有者手測。

**累積的未計數改動**（計數鏈併批，擁有者 10-12）：0.2.26 之後的 v22–v26 與本批 v27。K 照舊另排。

## 12. §34.4

本規格釘死之前：因執行而修 **2**（原生判讀工具的時鐘對齊檢查用錯了時間點，smoke 後改用索引；Q6.3 的標題對照設計錯，補直接檢查）；因審核而修 **9＋細項**（opus 對抗性審核，2026-10-30；主 session 讀碼確認第 1、2、3 項後採用：PL-1、`held` 與讀法一、DISPOSITIONS、S3 的回覆列與 `cosmetic-review` 突變、兩次 Ctrl+Z、E1 紅案的編法、E3 的三支 inc 測試、兩棵樹的原始碼釘選、undo 紀錄的位置與形狀、細項 1–11、13；細項 12 判斷後不升版，§3）。fable 裁決：本輪 1 次（裁決 3；裁決 2 是上一輪的）。

## 13. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-10-30 | 草案。 |
| 2026-10-30 | 草案第二版：Q6.3 的結果（五個動作 IN-SCOPE）；併入對抗性審核（§12）；普查存成證據。 |
| 2026-10-30 | 釘死。 |
| 2026-10-30 | 追加一：§1 的「上次操作」歸屬更正（宿主自 0.2.6 藏起狀態列）；§7.4 手測的兩條「上次操作」條文撤回。 |

## 追加一（2026-10-30，擁有者在 0.2.43 手測之後；更正 §1、§2 第 1 項的歸屬與 §7.4 的手測條文，原文保留）

擁有者手測 0.2.43：「a. 如預期。但我在頁面上沒看到「上次操作」／b. 顯示"動作以送出…"，跟之前一樣。也是沒看到「上次操作」／c. 如預期」（截圖 `findings/evidence/host-0.2.43/owner-hand-test-b-toast-20261030-1646.png`）。

1. **§1 的「畫面下方的『上次操作』寫『• 項目符號 失敗』〔實測，擁有者畫面〕」歸屬錯誤**。宿主自 0.2.6（`96a13b9`，2026-10-06）起就把整條 `.statusbar` 藏起來（`templates/editor.php:51`），0.2.42、0.2.43 都一樣。擁有者在宿主上從來看不到「上次操作」。那個「失敗」是鏡像上的量測：S2 run-02、F3（finding 176 的表裡是〔實測〕鏡像），不是擁有者畫面。擁有者畫面上實測到的只有提示句。起草本規格時把兩件事寫成同一個〔實測，擁有者畫面〕，沒有回頭讀宿主模板。
2. **殼層項（§2 第 1 項、§4.3）照舊有效，但只在鏡像與獨立頁面上看得到**。U1、S2′ 是它唯一的量測，宿主使用者看不到它。不撤回改動：它在顯示狀態列的頁面上是真的；也不為了讓宿主看得到而加新東西（CLAUDE.md §4）。要不要讓宿主顯示這一條，是另一個產品決定，屬於擁有者。
3. **§7.4 手測 (a) 的「『上次操作』顯示時間」、(b) 的「『上次操作』寫『待確認』」在宿主上無法觀察，撤回**，不算過、也不算不過。手測依提示判：(a) 沒有提示，擁有者「如預期」；(b) 083 那句，依設計（§2「083 的路不改」、L-083-stays-a-toast），擁有者「跟之前一樣」；(c) 清單撤回，擁有者「如預期」。
4. 「如果這件事永遠沒做」的預設：宿主上「上次操作」維持隱藏，殼層項只由鏡像量測承載。
