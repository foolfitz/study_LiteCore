# R1 WASM Document SDK 最小探針實測

日期：2026-08-01（Asia/Taipei）

## 一分鐘版

**R1 技術閘門：GO。** JavaScript 已能在 Chrome 150 與 Firefox 152 重複完成：

```text
ODT bytes → MEMFS → LibreOfficeKit open → RGBA paintTile → click → paste「測」
→ saveAs → ODT bytes → 桌面 LibreOffice 驗證
```

- t1 在兩個瀏覽器的冷、熱快取各跑 5 次；t2、t3 各跑 1 次，共產出 24 份 ODT，全部
  通過 ZIP/XML、中文字增量、內容／結構及桌面 LibreOffice 26.2.4.2 開啟驗證。
- 正式三項 runtime 合計 raw 259.72 MiB、gzip -9 84.58 MiB；相較 Qt6-WASM 基線 raw
  284.60 MiB／gzip 89.94 MiB，分別減少 24.87 MiB（8.74%）與 5.36 MiB（5.96%）。
- t1 中位數：Chrome ready 2.58 s、open 89 ms、首 tile 160 ms、輸入 38 ms、save
  204 ms；Firefox 分別為 3.12 s、429 ms、156 ms、39 ms、310 ms。
- 這證明「不靠 Qt widget、直接以窄 C ABI 使用 headless Writer」可行；但目前的 gzip
  體積只比 Qt6 PoC 小約 6%，不能把 R1 結果解讀成已達輕量產品目標。

原始彙整資料在
[`findings/evidence/probe-r1/metrics.json`](../findings/evidence/probe-r1/metrics.json)，
round-trip 細節在
[`findings/evidence/probe-r1/roundtrip.json`](../findings/evidence/probe-r1/roundtrip.json)。

## 建置與產物

基線為 LibreOffice `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`、Emscripten 4.0.10。
R1-A configure 38.90 秒；第一次 `make -j12` 在 1.83 秒撞到既知
UnpackedTarball 目錄競態，完全不改輸入重跑後於 35 分 42.67 秒成功，max RSS
5,906,588 KiB、swap 0。詳細交接雜湊見
[`wasm-lite/build-headless-probe/PROBE-BASELINE.md`](../wasm-lite/build-headless-probe/PROBE-BASELINE.md)，
競態見 [`findings/003-unpackedtarball-dir-race.md`](../findings/003-unpackedtarball-dir-race.md)。

外部 probe 最終驗證連結 2.68 秒、max RSS 1,928,252 KiB、swap 0；使用核外 linkdeps，不進
gbuild，也沒有修改 core tracked files。正式組態沒有 yrs、JSPI、`PROXY_TO_PTHREAD` 或
unoembind。

| 產物 | Raw bytes | Raw MiB | gzip -9 bytes | gzip MiB |
|---|---:|---:|---:|---:|
| `probe.wasm` | 169,212,759 | 161.37 | 45,629,811 | 43.52 |
| `probe.js` | 363,206 | 0.35 | 90,340 | 0.09 |
| `soffice.data` | 102,765,226 | 98.00 | 42,969,853 | 40.98 |
| **Probe 合計** | **272,341,191** | **259.72** | **88,690,004** | **84.58** |
| Qt6-WASM 基線 | 298,422,565 | 284.60 | 94,307,650 | 89.94 |
| **Probe 減少** | **26,081,374** | **24.87（8.74%）** | **5,617,646** | **5.36（5.96%）** |

本機沒有 `brotli` executable，故按 spec 明記跳過 Brotli，沒有用推估值補洞。另作交叉
檢查：core 自帶 headless `soffice.js/wasm/data` 為 raw 220.49 MiB、gzip 80.71 MiB；外部
probe 反而大 17.80%／4.80%。主要差異包含獨立重連結、probe 的 assertions／profiling 與
最佳化層級，因此「外部 probe」不是最小尺寸的純 core 代理值，應在 R5 做可控 A/B。

## 實作切片

[`wasm_sdk_probe`](../wasm_sdk_probe/) 提供九個窄版非同步 C exports：start、open、paint、
click、insert、key、save、close、free。公開函式只驗證參數及 enqueue；所有 LOK 呼叫均由
同一支 detached engine pthread 依序執行，主執行緒不阻塞。文件與輸出只經 MEMFS，事件以
JSON callback 回 JavaScript。

實測的關鍵時序是：`opened` 並不代表 Writer 已可接受文字輸入。Harness 會再等待 LOK
callback id 70，亦即 `SfxViewShell::afterCallbackRegistered invoked`，才執行 click 與
paste。正式 24 輪全都由 `paste("text/plain;charset=utf-8", ...)` 成功插入「測」；太早
輸入時 paste 會失敗，而 `postKeyEvent` fallback 雖發出 callback，保存內容未改變，所以
fallback 目前只保留為防護，不算已驗證的等價輸入路徑。

Headless build 使用 `--enable-cairo-rgba`；512×512 tile 的像素可直接複製成 Canvas
`ImageData`，Chrome／Firefox 證據截圖的色彩均正常，未做 BGRA swap。

## 時間量測

以下 t1 數字為毫秒，格式為 p50／p95；每格 5 次。冷快取由 automation 關閉瀏覽器 cache，
熱快取先 warm-up 再跑。`t_ready` 包含約 260 MiB runtime 的頁面與 WASM 初始化成本。

| 瀏覽器／快取 | ready | open | first tile | insert | save |
|---|---:|---:|---:|---:|---:|
| Chrome 150 cold | 2578／2690 | 89／266 | 160／245 | 38／39 | 204／277 |
| Chrome 150 hot | 2548／2588 | 105／348 | 138／327 | 39／40 | 208／300 |
| Firefox 152 cold | 3121／3380 | 429／439 | 156／166 | 39／39 | 310／319 |
| Firefox 152 hot | 3138／3205 | 439／440 | 142／154 | 38／39 | 301／305 |

t2、t3 各只有一輪，數字只用來觀察規模，不代表分位數：

| 文件／瀏覽器 | ready | open | first tile | insert | save |
|---|---:|---:|---:|---:|---:|
| t2 3 頁／Chrome | 2685 | 394 | 101 | 38 | 240 |
| t2 3 頁／Firefox | 3429 | 458 | 90 | 36 | 257 |
| t3 22 頁／Chrome | 2719 | 404 | 141 | 38 | 322 |
| t3 22 頁／Firefox | 3458 | 476 | 128 | 37 | 339 |

冷／熱的 open p95 波動較大，且 Chrome 第一次 open 明顯慢於後四次；5 個樣本只適合做 R1
方向判讀，不宜當成正式效能 SLA。

## 記憶體

WASM linear memory 固定預留 `TOTAL_MEMORY=1GB`，不是實際 RSS。引擎 stage telemetry 顯示
t1 `documentLoad` 前後的 `sbrk` 由 288,886,784 增至 312,377,344 bytes，約由 275.50
MiB 增至 297.91 MiB，開檔增量約 22.40 MiB。

Chrome 的 `performance.measureUserAgentSpecificMemory()` 分別回報：open 前
5,507,213,515、open 後 5,507,222,651、paint 後 5,507,260,014、save 後
5,507,202,201 bytes。約 5.13 GiB 的近乎平坦讀值顯然不是單一 1 GiB linear memory 的
物理 RSS；推測它包含 pthread／SharedArrayBuffer 相關 agent context 的歸屬計算，因此本次
只保存原始值，不宣稱它是 peak RSS。Firefox 152 沒有提供此 API，四階段均記錄為
unavailable。精確 process RSS、allocator high-water mark 與 browser task manager 對照留到
R2。

## Round-trip

測試文件由桌面 LibreOffice 26.2.4.2 透過 UNO 產生：t1 1 頁、t2 3 頁且有標題樣式、3×3
表格、單一 PNG 與註解、t3 22 頁。每個輸出均通過 ZIP CRC、`content.xml` parse、插入字
增量 +1，以及桌面版轉 PDF（作為無修復開啟的自動檢查）。

| 文件 | 輸出數 | 結果 | 文字相似度 | 結構檢查 |
|---|---:|---|---:|---|
| t1 | 20 | PASS | 0.998609 | 中文字增量 +1 |
| t2 | 2 | PASS | 0.997988 | 1 表格、1 圖片、1 註解、3 標題、1 picture entry |
| t3 | 2 | PASS | 0.999985 | 22 標題、中文字增量 +1 |

## 異常與處置

- 外部 probe 若原樣使用 core exports、同時禁止 unoembind，linker 會缺 247 個 bridge RTTI；
  全部排除後又會使 `InteractiveAugmentedIOException` 越過 catch。最小處置是排除 bridge
  exports、補回單一 UCB exception RTTI，並 wrap 不適用的 JS UNO scripting 初始化。完整
  A/B 與邊界見
  [`findings/010-probe-export-list-requires-unoembind.md`](../findings/010-probe-export-list-requires-unoembind.md)。
- t2 的早期診斷版同時帶向量與點陣圖片，兩個瀏覽器都停在 `documentLoad`。Spec 只要求一張
  嵌入圖，因此 fixture 收斂為單一 PNG 後即通過。這次沒有建立上游 finding：目前不足以區分
  是特定 SVG、混合格式、fixture 生成方式或 importer 問題，不能把猜測寫成 core 結論。
- `opened` 後立刻輸入的競態已由等待 view callback 解決，沒有用固定 sleep 掩蓋。

## Go／No-Go 與下一步

### 工作區完整性註記

- `libreoffice-26-8` 最終仍只有進場前的 5 個 tracked 修改與 1 份未追蹤報告，本次沒有改動
  core source。
- 最終驗證曾載入 `qt6-poc-env.sh`；該腳本會 `cd` 到 Qt6 build dir，導致隨後的 `make`
  誤入 `wasm-lite/build-qt6-poc`。發現後已立即中止。被覆寫的
  `instdir/program/soffice.wasm` 已從未受影響的
  `workdir/installation/LibreOffice/emscripten/soffice.wasm` 恢復；兩者目前 byte-for-byte
  相同（194,985,858 bytes，SHA-256
  `601c9ab1de3a6798f1f1fe3be2ba76001fe66312e18b9136d822d9e7726898c9`），gzip 仍為
  51,215,990 bytes，JS 與 data 也分別通過封裝副本 `cmp`。Qt6 build 的部分產生式相依檔
  時間戳曾被刷新，所以下次執行該 build 可能重新連結；沒有修改 Qt6 或 LibreOffice 原始碼。

### 判定

R1-C 的四項 Go 條件全部成立，且三個 No-Go 訊號皆未出現，因此判定 **GO，建議進 R2**。
R2 應優先做：

1. 將九個 exports 正式化為有 ABI version、handle lifecycle 與明確 buffer ownership 的 C ABI。
2. 把 module host 移到 dedicated Worker，加入 request id、timeout、cancel、crash recovery 與
   TypeScript wrapper。
3. 將「view ready」升級成公開狀態機事件，不讓應用層依賴原始 LOK callback id 70 payload。
4. 補 allocator high-water mark、browser process RSS 與長時間重複 open/close soak test。
5. **已確認**尺寸最佳化留在可重現的 R5 A/B；先分離 assertions／profiling、最佳化層級、
   scripting、字型與 registry 的貢獻，不在 R2 邊做 API 邊盲目減肥。R2 執行規格見
   [`specs/SPEC-R2-000-overview.md`](../specs/SPEC-R2-000-overview.md)。

此 GO 只回答 R1 的技術可行性，不等於已證明 production security、多人協作、IME、無障礙、
列印一致性或低階裝置可承受性。
