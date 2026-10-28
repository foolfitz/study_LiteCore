# 169：Writer 把純文字貼到多格表格選取時，第二格起把 UTF-16 位元組逐位元組當字元解讀

| | |
|---|---|
| **狀態** | 已確認（原生 26.8 LOK，3/3 穩定）；未修 |
| **Bugzilla** | —（上游送出擱置中） |
| **發現日** | 2026-10-28（從 [168](168-sdk-type-over-a-cross-cell-selection-pastes-into-both-cells-and-adds-a-hash.md) 拆出） |
| **嚴重度** | 一般偏高（使用者貼上的文字在第二格起變成亂碼或整段消失，沒有任何錯誤） |
| **可重現** | 原生 LOK 每個輸入 3/3；WASM 產品 Chrome 2 次、Firefox 1 次（只量過 `x`） |
| **是否上游** | **未確認**——原生 build 出自本地樹 `671c848b`，本地修改只在建置系統／wasm／Qt（`sw/` 無修改，見環境），但**還沒在官方桌面版重現** |

## 現象

表格裡選取兩格以上（例如 A1 文字尾端 Shift+Right，選到 A1、B1），再用 LOK `paste("text/plain;charset=utf-8", …)` 貼上純文字。Writer 在表格選取模式下不刪除既有內容，而是在**每一格**末端插入貼上的文字；**第一格正確，第二格起插入的是那段文字 UTF-16LE 位元組逐位元組解讀的結果**。

## 重現步驟

原生 harness `wasm_sdk_probe/tools/f168_native_table_type_routes.cpp`，fixture 是 S5 的 `run-03/fixture.fodt`（A1 `A1 cell text`、B1 `B1 cell text`、A2、B2 同形）。

1. 開檔，點在 A1 文字尾端。
2. Shift+Right（選取讀回 `A1 cell text\tB1 cell text\n`）。
3. `paste("text/plain;charset=utf-8", 文字)`，回傳 true。
4. 存檔，讀段落。

**預期**：每一格插入的文字相同（或依 Writer 的表格貼上語意處理，但不得改變文字內容）。
**實際**（`f168-native-routes/run-01`，每列 3/3 相同）：

| 貼上的文字 | UTF-16LE 位元組 | A1 | B1 |
|---|---|---|---|
| `x` | `78 00` | `A1 cell textx` | `B1 cell textx#` |
| `xy` | `78 00 79 00` | `A1 cell textxy` | `B1 cell textx#y#` |
| `hello world` | 22 bytes | `A1 cell texthello world` | `B1 cell texthello world`（正確） |
| `é` | `E9 00` | `A1 cell texté` | `B1 cell text`（**什麼都沒插入**） |
| `中` | `2D 4E` | `A1 cell text中` | `B1 cell text-N` |

四格選取（再加 Shift+Down，A1:B2）貼 `x`：A1 `…textx`，B1、A2、B2 **全部** `…textx#`——不是只有第二格，是第一格之後的每一格。

對照：游標在 A1（沒有表格選取、只有一個 PaM）貼 `x` → 只有 A1 `A1 cell textx`，沒有 `#`。

## 證據

- `evidence/link-batch-v23/feature-protocol/f168-native-routes/`：英文 README、build receipt（`build-01/`）、`run-01`（預設語系 zh_TW.UTF-8）、LC_ALL=C 擾動、讀取器輸出。
- `#`、`-N`、整段消失三種結果都正好是「把 UTF-16LE 位元組流用單位元組字元集讀」會給的東西：`78 00` → `x` ＋ NUL（控制字元換成 `#`）；`2D 4E` → `-N`。`hello world` 正確，表示較長的輸入有被偵測成 UTF-16。
- WASM 產品上同一選取打 `x` 存出 B1 `B1 cell textx#`（[168](168-sdk-type-over-a-cross-cell-selection-pastes-into-both-cells-and-adds-a-hash.md)），與原生逐字相同——不是 WASM build 才有的問題。

## 分析

輸入→輸出的對應是量到的；**下面的程式路徑是讀碼，沒有逐步追蹤（未驗證，當成假說）**。core `671c848b`：

- `sw/source/uibase/dochdl/swdtflvr.cxx` `PasteFileContent`：把 `OUString` 的 UTF-16 記憶體直接包成 `SvMemoryStream`，只在進 `SwReader` 之前設一次 `aAOpt.SetCharSet(RTL_TEXTENCODING_UCS2)`。
- `sw/source/filter/basflt/shellio.cxx` `SwReader::Read`：對 PaM ring 的每一個 PaM 各呼叫一次 `po->Read(...)`，重用同一個 stream。
- `sw/source/filter/ascii/parasc.cxx` `AsciiReader::Read`：每次讀完 `m_aOption.ResetASCIIOpts()`，charset 回到 `osl_getThreadTextEncoding()`。
- 第二個 PaM 起，`ReadChars` 看到選項等於預設，改走 `SwIoSystem::IsDetectableText` → `SvStream::DetectEncoding`（ICU 字元集偵測）。兩個位元組的 `78 00` 偵測不出 UTF-16，就以單位元組字元集讀，NUL 換成 `#`；`E9 00` 偵測回 DONTKNOW 時，裸 NUL 讓 `IsDetectableText` 回 false，那一格整段放棄。

語系擾動：LC_ALL=C／LANG=C 重跑（`run-03-lc-all-c`），**15 臂結果與 zh_TW.UTF-8 完全相同**——fallback 字元集沒有參與，與「後續 PaM 由 ICU 偵測決定」一致，但仍不是追蹤。

修法方向（未實作、未驗證）：`SwReader::Read` 在 PaM 迴圈裡每次重設 reader 的 ASCII 選項，或 `AsciiReader::Read` 在多 PaM 插入時不要在每次讀完就 reset。

## 和 168 的關係

[168](168-sdk-type-over-a-cross-cell-selection-pastes-into-both-cells-and-adds-a-hash.md) 是「產品把打字做成 paste」——路線選錯，量到的是語意差異（鍵盤清空選取、paste 在每格附加）。本單是 paste 本身在多格選取時把文字解碼錯。**修好 168（打字不走 paste）不會修好本單**：使用者真的按 Ctrl+V 貼到多格選取時仍然走 LOK paste，仍然會壞。

## 環境

`evidence/link-batch-v23/feature-protocol/f168-native-routes/env-snapshot.txt`（2026-10-28 發現當下）。core `671c848b`（libreoffice-26-8，2026-07-30）；本地修改：`RepositoryModule_host.mk`、`bridges/CustomTarget_gcc3_wasm.mk`、`configure.ac`、`dbaccess/Module_dbaccess.mk`、`desktop/CustomTarget_soffice_bin-emscripten-exports.mk`、`solenv/gbuild/platform/{EMSCRIPTEN_INTEL_GCC,unxgcc}.mk`、`static/CustomTarget_emscripten_fs_image.mk`、`vcl/qt5/QtFrame.cxx`——`sw/`、`tools/`、`desktop/source/lib/` 都沒有。原生執行：`SAL_USE_VCLPLUGIN=svp`，`native-lok-26-8/build/instdir/program`。

## 還缺什麼才能送

- [ ] 在官方桌面版 Writer 重現：選兩格、從剪貼簿貼一個字（或 Paste Special → Unformatted text）。LOK 的 `paste` 走 `.uno:Paste`，桌面應該是同一條路，但沒量過。
- [ ] 確認 master 是否已改（`git log` 看 `shellio.cxx`／`parasc.cxx`／`swdtflvr.cxx` 26.8 之後的變更）。
- [ ] 搜尋 Bugzilla 有沒有重複（關鍵字：table cells paste unformatted text `#`／garbage／multiple cells）。
- [ ] 程式路徑目前是讀碼；要送 patch 的話先在原生 build 加一個 SAL_INFO 或斷點確認第二個 PaM 選到的 charset。
- [ ] Component：Writer（送出前查證）。

## 時間軸

- 2026-10-27：S5-02 計數在 `shift-Right@cell-end/type` 停下（WASM，B1 `B1 cell textx#`），登錄為 168。
- 2026-10-28：原生 route harness 15 臂 × 3 輪；原生 paste 逐字重現 `x#`，長度與非 ASCII 對照定出逐位元組解讀的形狀；LC_ALL=C 重跑結果不變；從 168 拆出本單。
