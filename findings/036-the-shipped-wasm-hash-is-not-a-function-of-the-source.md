# 036 — 出貨 wasm 的 hash 不是原始碼的函數，所以「舊 build」不能重建，只能保存

| | |
|---|---|
| **狀態** | **已確認（同源同旗標四次編譯得到四個不同目的檔）／已因此毀掉一份被引用的 artifact** |
| **Bugzilla** | —（emscripten／LLVM 最佳化階段，未定位、未回報） |
| **發現日** | 2026-08-11 |
| **嚴重度** | 一般偏高（不影響產品；但讓「回到舊 build 重測」這個動作變成不可能，而本專案的證據紀律預設它可行） |
| **可重現** | 100%（重編就會擲一次） |
| **是否上游** | **未確認** |

## 摘要

[032](032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md) 已經確認
**同源同旗標重編會得到不同的目的檔**（當時：8 次得到兩種，各 4 次）。

本單記錄它的第二個後果，032 沒有寫、而本專案的作業方式一直預設相反：

**連結出來的 `probe.wasm` 的 sha256 因此也不是原始碼的函數。**
同一個 commit、同一套工具鏈、同一台機器，重跑 `make` 會得到**另一個 hash**。

所以「回到舊 build 重測一次」**做不到**。舊 artifact 只能**保存**，不能重建。

## 怎麼撞到的

2026-08-11，我要在改引擎**之前**先於舊 build 跑鑑別器基線。
我先跑了一次 `make e2-format-discovery-assets`（目的只是複製 JS 資產），
而 `src/probe_engine.cpp` 的 mtime 剛好比目的檔新（內容與 HEAD 完全相同，`git diff` 為空），
於是 make 重編了它。

結果：`dist/profiles/e2-format-discovery/probe.wasm` 由 **`25761ff0…`** 變成 **`bd102b4a…`**，
而 `25761ff0` 正是 A3／A4／A5 三個判定綁定的那一份。**沒有備份，無法重建。**

`probe.js` 與 `sdk-worker.js` 的 hash **完全沒變**（`023d1a23…`／`750a670d…`，
與 `repeat/firefox/styled-list/attempt-12/result.json` 記錄的一致）——
只有 wasm 變了，這也是最初誤以為「原始碼一定有差」的原因。

## 量測

先確認「同一輪之內」是可重現的：連續兩次完整 build，wasm 逐位元相同（都是 `bd102b4a`）。
所以不是每次都擲。

再直接測編譯步驟，用 Makefile `$(E2_BUILD)` 那一組旗標，同一份未修改的 `probe_engine.cpp`，
**四次編譯 → 四個不同的目的檔**：

```text
1fc91dc211d0d934…  559bb119b05893f6…  6b99505045d793a8…  f16266614fe20ac1…
```

（032 當時是 8 次得到兩種；本輪多了 `-DOXSDK_E2_FORMAT_BARRIER`，狀態數看起來更多。
本輪四次是並行跑的，032 是循序跑的——**並行不是成因**，032 循序也擲，
但本輪的數字不該被引用為「狀態數是四」。）

## 這推翻／修正了什麼

- **「一個 build、一次重掃」仍然成立**，而且更重要：sweep 與判定之間**絕不能重編**，
  因為重編就換 artifact，即使一行原始碼都沒動。
- **「舊 build 的基線」必須在改動前先跑，或先把 artifact 複製走。** 兩者擇一，不能都不做。
  我這次兩者都沒做。
- **A3／A4／A5 的 `25761ff0` 判定沒有失效**——它們是關於「那一份 artifact 產生的證據」的陳述，
  證據本身完整保留。失去的是**再對那一份 artifact 提問**的能力。
- finding 027 的 artifact 綁定**不受影響**，反而更被需要：既然 hash 不是原始碼的函數，
  「這批證據出自哪一份 artifact」就只能靠記錄，推導不出來。

## 已改的作業方式

改引擎之前，先把現行 profile 複製到 `wasm_sdk_probe/build/archive/<name>/`
（`probe.wasm`／`probe.js`／`sdk-worker.js`／`sdk-manifest.json` 四件）。
本輪之後存在的兩份：

| 目錄 | wasm | 內容 |
|---|---|---|
| `build/archive/e2-format-discovery-prechange/` | `bd102b4a…` | 034 修法前，原始碼＝commit 3bd6108 |
| `build/archive/e2-format-discovery-new/` | `38168306…` | 034 修法後 |

鑑別器因此可以在**同一份案例清單**下對兩個引擎各跑一次，靠交換 `dist/` 內容切換
（`caret-offset-discriminator/analysis.json` 的七列對照就是這樣得到的）。

## 沒有量的

- **哪一個最佳化 pass 造成的**——032 也沒定位，本輪沒有再查。
- **`-Oz` 以外的最佳化等級是否一樣擲**。
- **是否可以用旗標關掉**（`-frandom-seed`、單執行緒 LTO 之類）。若可以，
  「可重建的 artifact」會比「保存 artifact」乾淨得多，值得評估，但不是本輪的事。

## 相關

- [032](032-object-file-comparison-is-a-coin-flip-not-an-isolation-check.md)——同一個不確定性，第一個後果（逐位元比對不是隔離檢查）。隔離檢查改用前處理 TU 比對，本輪照做且通過。
- [027](027-r8d-verdict-silently-outlived-its-release.md)——判定必須綁定產生它的 artifact。
