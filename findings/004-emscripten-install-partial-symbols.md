# 004 — Emscripten 部分符號建置未產生 soffice `.dwp`，安裝封裝失敗

| | |
|---|---|
| **狀態** | 待驗證（根因修補已建立；待重新連結與封裝） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-07-31 |
| **嚴重度** | 一般（建置最後一步失敗；主要執行產物已產生） |
| **可重現** | 1/1（本次 Qt 6 POC 有完整證據；前次同症狀未保留原始 log） |
| **是否上游** | **未確認**（`origin/master` 仍有相同程式碼，但尚未以無本地修改的 stock 組態重現） |

## 現象

以 `--enable-symbols=Executable_soffice_bin` 建置 Emscripten 版本時，
`Executable/soffice.js` 已連結成功，所有非 instset 模組也已完成；最後安裝封裝卻因找不到
`soffice.wasm.debug.wasm.dwp` 而失敗：

```text
[build ALL] All modules but instset: ...
cp: cannot stat '.../instdir/program/soffice.wasm.debug.wasm.dwp': No such file or directory
make[1]: *** [.../instsetoo_native/CustomTarget_emscripten-install.mk:34: .../emscripten-install.done] Error 1
make: *** [Makefile:312: build] Error 2
```

`soffice.js`、`soffice.wasm`、`soffice.wasm.debug.wasm`、`soffice.data` 與
`qt_soffice.html` 均已存在，只有 `.dwp` 缺少。

## 重現步驟

1. 設定 Emscripten WASM 建置，使用 `--enable-symbols=Executable_soffice_bin`。
2. 確認 `HAVE_EXTERNAL_DWARF=TRUE`。
3. 執行 `make`。

**預期**：soffice 連結後執行 `emdwp` 產生 `.dwp`，安裝封裝完成。

**實際**：soffice 連結完成但沒有執行 `emdwp`；installer 要求複製不存在的 `.dwp`。

## 證據

- [`evidence/004/make-error-qt6-poc.txt`](evidence/004/make-error-qt6-poc.txt) — 本次完整錯誤前後文
- [`evidence/004/make-error-qt6-poc-retry2.txt`](evidence/004/make-error-qt6-poc-retry2.txt) — 第一版修補後確實重新連結，但 `.dwp` 仍缺少
- [`evidence/004/env-qt6-poc.txt`](evidence/004/env-qt6-poc.txt) — 發現當下環境與本地修改
- [`evidence/004/dwp-audit-qt6-poc.txt`](evidence/004/dwp-audit-qt6-poc.txt) — 設定、產物及 gbuild 判定路徑稽核
- [`evidence/004/t-symbols-audit-retry2.txt`](evidence/004/t-symbols-audit-retry2.txt) — gbuild 布林值、retry2 時間戳與第一版條件失效原因

## 分析

### 已觀察並確認的事實

本次 `config_host.mk` 設定為：

```make
export ENABLE_SYMBOLS_FOR=Executable_soffice_bin
export HAVE_EXTERNAL_DWARF=TRUE
```

`LinkTarget.mk` 已用真正的 gbuild target 名稱計算 target-local 變數：

```make
$(call gb_LinkTarget_get_target,$(1)) : T_SYMBOLS := \
    $(if $(call gb_target_symbols_enabled,$(2)),$(true),$(false))
```

對 `soffice_bin` 而言，`$(2)` 是 `Executable_soffice_bin`。gbuild 定義 `true := T`、
`false :=`，因此這裡的實際值是 `T_SYMBOLS=T`。

但 `unxgcc.mk` 的動態連結 recipe 原本重新呼叫：

```make
$(call gb_target_symbols_enabled,$(1))
```

此處 `$(1)` 是實際輸出路徑
`.../instdir/program/soffice.js`，不是 `ENABLE_SYMBOLS_FOR` 清單使用的
`Executable_soffice_bin`。判定因此為 false，後面的 `emdwp` 被跳過。

installer 另外以全域 `ENABLE_SYMBOLS_FOR` 是否非空決定要不要複製
`soffice.wasm.debug.wasm` 與 `.dwp`。在本次組態中 soffice 本來就被明確選中，所以它期待
`.dwp` 是合理的；真正造成檔案缺少的是前述 linker recipe 誤判。

### 本地修補

`solenv/gbuild/platform/unxgcc.mk` 改用已正確計算的 target-local `T_SYMBOLS`：

```make
$(if $(T_SYMBOLS),... emdwp ...)
```

第一版修補曾寫成 `$(filter TRUE,$(T_SYMBOLS))`。retry2 的 `main.c`、`soffice.js` 與
`soffice.wasm` 時間戳均更新，證明 target clean 與重新連結確實執行；但 `T_SYMBOLS` 的
真值是 `T` 而非 `TRUE`，該 filter 仍為空，所以 `emdwp` 再次被跳過。第二版改為直接測試
非空值，與 gbuild 其他 `T_SYMBOLS` 使用方式一致。

這只改變 Emscripten、外部 DWARF 已啟用且目前 link target 確實開啟 symbols 時的
`.dwp` 產生條件。

### 尚未證明的獨立問題

installer 使用全域 `ENABLE_SYMBOLS_FOR`，理論上在「只替其他 target 開 symbols、未替
soffice 開啟」時仍會錯誤要求 soffice debug 檔。這不是本次組態的直接原因，也尚未另行
重現；若確認，應拆成另一筆 finding。

## 影響

主要瀏覽器執行產物已生成，但 `make` 尚未成功完成，且
`workdir/installation/LibreOffice/emscripten/` 只得到部分複製結果。完整性仍以修補後的
重新連結與封裝結果為準。

## 環境

```text
LibreOffice   26.8.0.1.0+ @ 671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb
Emscripten    4.0.10 (b7dc6e5747465580df5984e723b9d1f10d8e804b)
Qt            6.10.2（WASM，thread／WASM exceptions／JSPI）
Configure     --enable-symbols=Executable_soffice_bin
Build dir     wasm-lite/build-qt6-poc
Host          Ubuntu 26.04 LTS / x86_64
```

本次是在帶有 Qt 6.10 相容性修補與 fs-image 本地修改的 worktree 上觀察，因此尚未標記
「上游＝是」。這些修改與 `.dwp` 判定路徑沒有直接關係，但 stock reproduction 仍不可省略。
完整快照及工具限制見 [`evidence/004/env-qt6-poc.txt`](evidence/004/env-qt6-poc.txt)。

## 還缺什麼才能送

- [ ] 對 `Executable_soffice_bin` 做 target clean 後重新執行 `make`
- [ ] 確認重新連結實際產生 `soffice.wasm.debug.wasm.dwp`
- [ ] 確認 `emscripten-install.done` 與整體 `make` 成功
- [ ] 以無本地修改、接近上游預設的組態重現
- [ ] 搜尋 Bugzilla／Gerrit 是否已有重複或修補
- [ ] 確認 Component

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | Build tooling（送出前確認） |
| Version | 26.8.0.1 rc |
| Hardware / OS | All / All |
| Summary | Emscripten: partial `--enable-symbols` skips `emdwp` and breaks installation |

## 時間軸

- 2026-07-31 使用部分符號建置時首次遇到安裝階段缺少 `.dwp`。
- 2026-08-01 Qt 6.10.2 POC 再次重現；`soffice.js` 已成功連結，僅 `.dwp` 缺少。
- 2026-08-01 確認 linker recipe 傳錯符號目標識別值；建立改用 `T_SYMBOLS` 的第一版修補。
- 2026-08-01 retry2 確實重新連結但仍缺 `.dwp`；確認第一版錯把 gbuild 真值 `T` 當成 `TRUE`。
- 2026-08-01 第二版改為直接測試 `$(T_SYMBOLS)` 是否非空，待手動重新連結與封裝驗證。
