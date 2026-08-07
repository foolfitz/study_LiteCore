# 002 — qt_vcldemo.html 沒有連結 fs image，README.wasm.md 卻要人跑它

| | |
|---|---|
| **狀態** | 可送出（根因完全確定，不依賴精簡組態） |
| **Bugzilla** | tdf#______ |
| **發現日** | 2026-07-31 |
| **嚴重度** | 一般（影響的是官方文件指定的測試路徑） |
| **可重現** | 100% |
| **是否上游** | **是** —— 缺的是連結期的 pre-js，與 configure 旗標無關 |

## 現象

`static/README.wasm.md` 明文要人跑這個當測試：

> You should be able to run either
>
>     $ emrun --hostname 127.0.0.1 --serve_after_close workdir/installation/LibreOffice/emscripten/qt_soffice.html
>     $ emrun --hostname 127.0.0.1 --serve_after_close workdir/LinkTarget/Executable/qt_vcldemo.html

但第二個必定失敗：白畫面，主控台是 `Bootstrap exception Cannot open uno ini file:///instdir/program/unorc`。

## 重現步驟

1. 依 `README.wasm.md` 建置 WASM 版本
2. `emrun --hostname 127.0.0.1 --port 6932 workdir/LinkTarget/Executable/qt_vcldemo.html`
3. 開新分頁載入

**預期**：vcldemo 的繪圖測試畫面
**實際**：白畫面，UNO bootstrap 失敗

## 證據

- `evidence/002/console.txt` — 完整主控台紀錄
- `evidence/002/loader-missing.txt` — 兩個 .js 的比對
- `evidence/002/screenshot-blank.png`

網路請求時序證明 **`soffice.data` 從頭到尾沒有被請求過**：

```
[0.0s] 200      3229B  qt_vcldemo.html
[0.0s] 200      3047B  qtlogo.svg
[0.0s] 200     22298B  qtloader.js
[0.1s] 200    281830B  vcldemo.js
[0.1s] 200 123498234B  vcldemo.wasm
                            ← 沒有 soffice.data，也沒有 soffice.data.js.metadata
[1.0s] LOG  Bootstrap exception Cannot open uno ini file:///instdir/program/unorc
```

直接比對兩個 .js：

```
$ grep -c 'soffice\.data\|loadPackage' vcldemo.js      →  0
$ grep -c 'soffice\.data\|loadPackage' soffice.js      → 11
```

## 分析

`file_packager` 產生的載入器（`soffice.data.js`）是在連結期以 pre-js 的形式併進去的。`soffice.js` 有（`loadPackage`、`REMOTE_PACKAGE_BASE` 都在），**`vcldemo.js` 完全沒有**。

所以 vcldemo 執行時虛擬檔案系統是空的，`/instdir/program/unorc` 不存在，UNO bootstrap 第一步就失敗。

值得注意的是 `solenv/gbuild/platform/unxgcc.mk:191-193` 會把 `soffice.data` 和 `soffice.data.js.metadata` **複製**到每個可執行檔旁邊 —— 檔案確實在 `workdir/LinkTarget/Executable/` 底下躺著，只是沒有任何程式碼去載入它們。複製了卻沒連結載入器，看起來是漏了一半。

修法有兩個方向，**由上游決定哪個才對**：

1. 讓 `vcldemo` 這類 Executable 也連結 `soffice.data.js.link` 這個 pre-js
2. 如果 vcldemo 本來就不該依賴 fs image，那就從 `README.wasm.md` 拿掉那一行，並停止複製 `soffice.data` 過去

## 環境

同 001（見 `./env-snapshot.sh`）。

**已在三種組態上覆驗**（lite / stock / t3），`vcldemo.js` 一律沒有載入器。與 configure 旗標無關。

## 還缺什麼才能送

- [x] 在 `build-stock/` 與 `build-t3/` 上覆驗 → 兩者 `vcldemo.js` 的 `soffice.data`/`loadPackage` 出現次數皆為 **0**，`soffice.js` 為 13。確認與組態無關
- [ ] 搜尋 Bugzilla 是否已有重複
- [ ] 確認 Component

## Bugzilla 欄位

| 欄位 | 值 |
|---|---|
| Product | LibreOffice |
| Component | Build tooling（送出前查證） |
| Version | 26.8.0.1 rc |
| Hardware / OS | x86-64 / Linux (Ubuntu 26.04) |
| Summary | WASM: qt_vcldemo.html is unusable — fs image loader is not linked in, contrary to README.wasm.md |

## 時間軸

- 2026-07-31 為了切開 001 的問題層次而跑 vcldemo，發現它以完全不同的原因失敗
