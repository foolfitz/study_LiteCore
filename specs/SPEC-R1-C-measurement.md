# SPEC R1-C：量測、驗收與報告

> **日期**：2026-08-01/**狀態**：可執行 spec（v1）/**上層**：[SPEC-R1-000](./SPEC-R1-000-overview.md)
> **依賴**：R1-A 與 R1-B 完成（探針 `Run All` 可重現）

## 1. 測試文件（`wasm_sdk_probe/test-docs/`）

三份 ODT，由桌面版 LibreOffice 製作（記錄製作用版本）：

| 檔名 | 內容 |
|---|---|
| `t1-plain-zh.odt` | 1 頁，純文字，中英混排（含全形標點、常用中文約 200 字） |
| `t2-styled.odt` | 2–3 頁，含標題樣式、一個 3×3 表格、一張嵌入圖片、一則註解 |
| `t3-long.odt` | 20 頁以上，重複中文文字流（測開檔與記憶體） |

## 2. 量測矩陣

### 2.1 產物體積（一次性）

對 `dist/probe.js`、`dist/probe.wasm`、`dist/soffice.data`：
raw（`stat`）、`gzip -9 | wc -c`、`brotli -q 11 | wc -c`（brotli 不在則註明跳過）。

對照組（直接引用，不必重量）：

- core 自身產物：R1-A 的 `PROBE-BASELINE.md`；
- 完整 Qt6-WASM：協作報告 §3.2（raw 284.60 MiB/gzip 89.94 MiB）。

**必答問題**：探針產物（≈拿掉 Qt UI + embind 的 core）與完整 Qt6-WASM 的差距是多少?
這是研究線第一個「拿掉 Qt 省多少」的實測數字。

### 2.2 時間（每一項：t1 文件、Chromium 與 Firefox、冷/熱快取各 5 次，報 p50/p95）

| 指標 | 定義（以 `__probe_metrics` 打點） |
|---|---|
| `t_ready` | 頁面載入開始 → `ready` 事件 |
| `t_open` | `probe_open` → `opened` |
| `t_first_tile` | `probe_paint_tile` → 首個 `tile` 事件 |
| `t_insert` | `probe_insert_text` → 首個 invalidate callback |
| `t_save` | `probe_save` → `saved` |

冷快取：DevTools「Disable cache」+ 硬重載；熱快取：一般重載。記錄瀏覽器版本。
t2、t3 至少各跑 1 輪 `t_open`/`t_first_tile`/`t_save`（觀察規模效應，不必 5 次）。

### 2.3 記憶體（盡力而為，方法要記錄）

- `performance.measureUserAgentSpecificMemory()`（COI 環境可用）於 open 前、open 後、
  paint 後、save 後各取一次；
- 瀏覽器工作管理員的分頁記憶體讀值（手動，截圖存證）；
- 註明 `TOTAL_MEMORY=1GB` 為固定預留，上述為實際占用近似值；精確 heap 統計留待 R2。

### 2.4 round-trip（每份文件）

1. 探針開啟 → 插入「測」→ save → 下載 `out.odt`；
2. 桌面版 LibreOffice 開啟：無修復對話框、內容完整、「測」在點擊位置；
3. `zipinfo out.odt` 正常、`content.xml` 可解析（`python3 -c "import zipfile,xml.dom.minidom; xml.dom.minidom.parseString(zipfile.ZipFile('out.odt').read('content.xml'))"`）；
4. t2 額外檢查：表格、圖片、註解、樣式仍在；
5. 記錄桌面版版本與結果（通過/異常描述）。

## 3. `metrics.json` 格式

存 `findings/evidence/probe-r1/metrics.json`：

```json
{
  "date": "2026-08-0X",
  "core_commit": "671c848b...",
  "emcc": "4.0.10",
  "artifacts": {"probe.wasm": {"raw": 0, "gzip": 0, "brotli": 0}, "probe.js": {}, "soffice.data": {}},
  "runs": [
    {"browser": "chromium-XXX", "doc": "t1-plain-zh.odt", "cache": "cold",
     "t_ready_ms": [], "t_open_ms": [], "t_first_tile_ms": [], "t_insert_ms": [], "t_save_ms": []}
  ],
  "memory": [{"phase": "after-open", "browser": "", "bytes": 0, "method": ""}],
  "roundtrip": [{"doc": "t1", "desktop_version": "", "pass": true, "notes": ""}]
}
```

## 4. Go/No-Go 判定（對應 SDK 報告 R1 閘門）

**Go（全部成立）**：

1. 五步驟（open/paint/click+insert/save）在 Chromium 與 Firefox 都可由 `Run All` 重現；
2. 三份文件 round-trip 通過（t2 容許記錄「已知樣式劣化」但不能壞檔）；
3. 插入的中文字在重畫與存檔後都存在；
4. 產物體積與時間已量測入 `metrics.json`（數字本身不設門檻，只要求誠實記錄）。

**No-Go 訊號（任一成立即回報，不要自行擴大修改）**：

- LOK init 或 documentLoad 在 headless WASM 反覆失敗且需改 core 才能繞過；
- 單份 t1 等級文件在預設組態下記憶體不足或穩定崩潰；
- save 產物桌面版持續無法開啟。

No-Go 不代表研究線失敗：轉向選項（server-native LOK）已在研究報告定義，由使用者決策。

## 5. 交付報告

寫 `DEVLOG-<日期>-wasm-sdk-probe.md`（工作區慣例格式），含：

1. 一分鐘版（結果先行：Go/No-Go、關鍵數字）；
2. 與 Qt6-WASM 基線的體積對照表；
3. 各步驟實測行為（paste vs postKeyEvent 哪條路通、callback 順序、顏色格式實況）；
4. 異常與 findings 連結；
5. 明確的「下一步建議」（進 R2，或轉向討論）。

同步更新：SDK 報告 §10 R1 段落加一行結果註記與 DEVLOG 連結（原地修訂 + 修訂紀錄，
遵守工作區文件慣例）；`findings/evidence/probe-r1/` 放 metrics.json、console log、
截圖與 out.odt 樣本。
