# 166：native LOK 連送 Shift+方向鍵與字元 x，Writer 先處理 x（56/56）

| | |
|---|---|
| **狀態** | 已確認（量測）／發生在哪一層**未定** |
| **Bugzilla** | — |
| **發現日** | 2026-10-27 |
| **嚴重度** | 一般（對本樹：害 native 參考答錯題；對產品：無直接影響） |
| **可重現** | 100%（run-01 的 56/56 type 格） |
| **是否上游** | **未確認**——讀碼有候選，沒有量測區分 |

## 現象

native S5 參考 harness（`wasm_sdk_probe/tools/v23_native_s5.cpp`，build 01）在同一顆文件上**連續**呼叫 `postKeyEvent`：Shift+方向鍵的 KEYINPUT／KEYUP，接著字元 x（character 120、key 0）的 KEYINPUT／KEYUP，四次呼叫在 0.015 ms 內依序返回，中間沒有任何讀取或等待。Writer 實際的處理順序卻是 **x 先、Shift 後**：

- 以 `shift-Right@caret-mid/type` 為例：游標在 `P2 ALPHA BE|TA`。宣告的序列是「Shift+Right 選到 T，再打 x 蓋掉」，應得 `P2 ALPHA BExA`；native 存檔是 `P2 ALPHA BExTA`，而且存檔後 `T` 仍是選取狀態（Shift 延伸是在 x 之後才套上去的）。產品頁同一格得到的是 `P2 ALPHA BExA`。
- run-01 全部 56 個 native-capable type 格都是這個形狀。

## 證據

- 原始紀錄：`evidence/link-batch-v23/feature-protocol/s5-native/run-01/native.jsonl`（每格的 `posts` 與 `after`）、`run-01/saves/*_type-after.odt`。
- 普查：`evidence/166/census.json`，工具 `wasm_sdk_probe/tools/census_f166_native_type_order.py run-01 run-02`。run-01：56 格中 52 格的偏移可由 setup 名稱推導，**52/52** 的存檔文字等於「把 x 打在按 Shift 之前的游標／選取上」；14 個形狀**每個**的四個 Shift 鍵（Left／Right／Home／End）都給出同一段文字（剩下 4 格是 wrap-line-end，只能用這一條判）。這重現了 fable 裁決 3 的普查。
- 對照：run-02／run-03（`s5-native/run-02/`、`run-03/`，同一套 setup，只在 Shift 與 x 之間加上既有的 800 ms quiet settle 並讀一次選取；run-03 只多了 15 位數時間戳）。可推導的 52 格中只剩 **7** 格等於「x 打在 Shift 之前」——正好是 Shift 本來就不動的靜默格；14 個形狀中**沒有一個**四鍵同文。run-03 的 56 格，settle 後讀到的選取全部等於 Writer 三輪的 Shift 選取。也就是說：**讓 Shift 先處理完，Writer 就照宣告的順序做**。
- 裁決：`evidence/link-batch-v23/feature-protocol/s5-type-oracle-ruling/RULING.md`。

刪除類（Backspace／Delete）**沒有**這個現象：裁決 3 的普查判它們不受影響，`s5-prep-02` 的五個刪除格與 native 存檔一致。

## 分析（讀碼，**未量測**）

兩個 KEYINPUT 走同一條路進同一個佇列：`SwXTextDocument::postKeyEvent` → `SfxLokHelper::postKeyEventAsync` → `postEventAsync` → `Application::PostUserEvent`（`libreoffice-26-8/sw/source/uibase/uno/unotxdoc.cxx:4012`、`sfx2/source/view/lokhelper.cxx:1273-1311`），處理時依序呼叫 `KeyInput`（同檔 `:1215-1221`）。所以**重排不在 LOK 的投遞層**——至少從這段程式碼看不出來。

候選（假說，沒有任何量測區分）：`SwEditWin::KeyInput` 對 Shift+方向鍵預設「forward to View」（`sw/source/uibase/docvw/edtwin.cxx:1735`），若它在 view 端經 `AcceleratorExecute` 的非同步派送（`svtools/source/misc/acceleratorexecute.cxx:225`，`AsyncAccelExec` 另外 post 一個 user event）執行，而字元在 `KeyInput` 裡同步插入，就會得到 x 先。旁證：同一函式在 `vcl::lok::isUnipoll()` 時改成同步 `dispatch`，註解是「tdf#130382 - all synchronous really」（同檔 `:213-221`）——上游知道非 unipoll 的加速鍵是非同步的；run-01 跑的正是預設的非 unipoll native 模式（`SAL_LOK_OPTIONS` 已移除）。這個假說也要能解釋刪除鍵為什麼保序——若 Backspace／Delete 同樣走非同步派送就說得通，但沒有查證。

可否證的下一步：同一 harness 在 unipoll 模式下（加速鍵同步）重跑一個 type 格，若 back-to-back 也得到 Shift 先，候選就成立一半；仍得 x 先，候選出局。

裁決 3 明定「harness 的 `typeChar` 路徑還是 LOK 非同步投遞，哪一層重排是工作項，此處不決定」。上面的讀碼把「LOK 投遞層」這一支削弱了，沒有決定任何事。

## 影響

- **對本樹**：run-01 的 56 個 type 存檔不是宣告序列的 oracle，已撤（裁決 3）；run-02 以逐格順序見證取代。產品不受影響——產品的 x 走 `insertText` wire 請求、Shift 走 `editorActionV2`，序列順序由產品自己保證（`s5-prep-02` 的 overlap 見證）。
- **對上游（未確認）**：若候選成立，任何 LOK 客戶端（例如 Collabora Online）在 Writer 處理前就把 Shift+方向鍵與一個字元都送進佇列，使用者就會看到字元插在選取之前、而不是蓋掉選取。是否真的會在 COOL 的時序下發生，沒有量過。

## 還缺什麼才能送

- [ ] 區分層級：同一 harness 把 x 換成 `postWindowExtTextInputEvent`、或把 Shift+方向鍵換成 `.uno:CharRightSel` 的 `postUnoCommand`，看順序是否改變
- [ ] 用上游預設組態（非 svp、桌面 LibreOffice 的 LOK 測試）重現
- [ ] 搜尋 Bugzilla 有無重複
- [ ] 上游送出目前擱置（2026-08-15 起），重啟時先重查

## 時間軸

- 2026-10-27 04:27：`s5-prep-02` 的 `shift-Right@caret-mid/type` 紅，產品 `BExA` 對 native `BExTA`。
- 2026-10-27：fable 裁決 3（`4a06317e`）撤 run-01 的 type 存檔、定 run-02 處方。
- 2026-10-27 06:49：run-02（build `v23-s5-type-owner-01`）執行；時間戳只印 6 位有效數字，46 格無法見證順序，由 run-03 取代。
- 2026-10-27 06:57：run-03（build `v23-s5-type-owner-02`）56/56 有見證，綁進 S5 計畫。
