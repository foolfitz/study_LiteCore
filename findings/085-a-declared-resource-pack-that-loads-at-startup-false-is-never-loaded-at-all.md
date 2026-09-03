# 085 — 宣告了 `loadAtStartup: false` 的 resource pack 從來不會被載入，而三份文件把它讀成「延後載入」

| | |
|---|---|
| **狀態** | 已確認 |
| **Bugzilla** | —（我方程式碼，不送上游） |
| **發現日** | 2026-08-29 |
| **嚴重度** | 一般（無使用者可見故障；影響的是**文件與決策**） |
| **可重現** | 100%（靜態普查） |
| **是否上游** | 否——我方 SDK 的行為與措辭 |

## 現象

`sdk-manifest.json` 的 `resourcePacks[]` 有一個 `loadAtStartup` 欄位。值為
`false` 讀起來像「延後到需要時再載入」，實際語意是**永遠不載入**——SDK 裡沒有
任何按需載入路徑，而且從來沒有過。

具體後果：`e2-editor-v8` 宣告的 `fallback-fonts-r5`（46.8 MiB，複雜文字與
fidelity fallback 字型）**從來沒有被編輯器抓取過**。v8 的使用者從未收到那批字型。

這件事沒有造成任何當機或錯誤訊息，所以它是靠**查一個判準的前提**才被發現的，
不是靠任何檢查轉紅。

## 重現步驟

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
python3 findings/evidence/queue-v11-split-probe/probe_no_on_demand_pack_path.py
```

**預期**（若按需載入存在）：某處存在 `loadResourcePack` 的第三個出現位置，
或 worker 之外有呼叫者。
**實際**：26 支 worker（現役 ＋ 全部 archive）每一支都剛好兩次出現；worker
之外 100 個檔案裡 0 個呼叫者。`verdict: CONFIRMED`。

## 證據

- `evidence/queue-v11-split-probe/probe_no_on_demand_pack_path.py`（普查，會 assert）
- `evidence/queue-v11-split-probe/no-on-demand-pack-path.json`
- `evidence/queue-v11-split-probe/RESULT-no-on-demand-pack-path.md`

```
workers scanned                     26
workers with other than 2 hits       0
the single call is the guarded one   yes
callers outside the worker           0   (100 files searched)
```

普查自己檢查非空洞性：目錄改名時它會紅，而不是搜了零個檔案然後回報「零」。

## 分析

`loadResourcePack()`（`sdk/sdk-worker.js:557`）只有一個呼叫者：
`loadStartupResourcePacks()`（`:617–620`），它只在 `pack.loadAtStartup === true`
時載入，而它自己只被 `handleInit`（`:1085`）呼叫一次。

`web/e2-editor-app.js`、`sdk/document-sdk.js` 與兩棵 editor-shell 裡
`resourcePack` 出現 **0 次**。樹上另外兩處引用都是**讀 manifest**、不是載入器：
`web/r5-reader-app.js:129`（斷言 cjk 包宣告為 startup）與
`web/r8-delivery-app.js:209`（把欄位抄進報告）。

封存的 worker 一路回溯到 `e2-editor-v2`，包含 `e2-editor-v8` 自己那支
（`build/archive/e2-editor-v8-4a2710bb-…/sdk-worker.js:539,602`），全部相同。

**語意缺陷**：`loadAtStartup: false` 是**宣告了行為而沒有東西實作它**——一筆
死組態，它的 false 值與「這個包沒有被宣告」在行為上無法區分。

### 它驅動出來的假句子

| 出處 | 句子 | 錯在哪 |
|---|---|---|
| `PLAN-2026-08-28` 尺寸表 | `fallback-fonts-r5` … 46.8 MB **on demand** | 沒有 demand |
| `HANDOFF-2026-08-28` §5 | v11 沒有 resource pack，所以 **v8 有的 lazy loading** 沒了 | 預設了一條從未存在的 lazy 路徑 |
| `PLAN-2026-08-28` addendum part 1 §A-3 | fallback 字型包 **no longer deferred** | 同上，且是本輪自己寫的 |
| D-4 外包工單的前提 | v8 "defers … to on demand" | 從 plan 照抄未查 |

順帶：v8 的 "total bytes 208.3 MB" 這一欄包含 46.8 MiB **沒有任何 client 下載過**
的位元組。下次引用該欄時要說明它的意思。

**未量**：兩個 profile 碰到需要 fallback 字型的文件會怎樣（靜默替換／缺字框／
其他）**沒有量過**。本 finding 宣稱的是檔案系統的事實，不是渲染結果。該量測
登錄為 B-2 判準 3′-iii。

## 處置

裁定為**佇列中的產品工作，不擋 cutover**。三條路（改欄位名／讓 manifest 說實話／
真的做出載入器）擇一，**本裁定不指定**，而且明確**沒有**指示去造新機制。

三份文件的更正依 D-3 的 append-only 機制落地並引用本編號。

## 還缺什麼

- [ ] 3′-iii：拿一份只有 fallback 包才有的字型的 fixture，在 v8／切分 v11／
      未切分 v11 上各開一次，記錄各自畫出什麼
- [ ] 決定三條路走哪一條（不擋 cutover）
