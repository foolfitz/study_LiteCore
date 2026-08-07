# R5 WASM Document SDK：Resource and size profiles

日期：2026-08-01（Asia/Taipei）

## 一分鐘版

**R5 技術閘門：GO。** R1～R4 的單一 QA binary 已整理成可重現的 profile system：

```text
full-qa ── product link ──► writer-review / writer-reader
        └ resource split ─► base + startup CJK + optional fallback fonts
                          └ content hash + immutable cache
```

- `writer-review`／`writer-reader` 都使用 `-Oz`、assertions off，移除 `--profiling-funcs`、`--bind`
  與 R1 `_probe_*` exports；strict undefined-symbol link 通過。
- `writer-reader` C ABI 與 manifest 只保留 open、tile、search、save、cancel，capability bits 為 59；
  replace／comment 等呼叫在 Worker 邊界得到 typed `UNSUPPORTED_OPERATION`。
- 1,358 個 resource 已拆成 base 1,241 檔／34,178,400 bytes、CJK 1 檔／19,484,784 bytes、
  fallback fonts 116 檔／49,102,042 bytes；三者互斥、聯集完整、byte totals 等於原始 data。
- `writer-review` WASM raw 比 full-qa 少 53,997,961 bytes，gzip -9 少 4,728,906 bytes；首載
  data 另少 49,102,042 bytes。
- 同一輪 deterministic gzip 計算下，review 首載的 loader + WASM + data 從 88,506,049 降為
  63,713,911 bytes（-28.0%）；raw 從 272,396,199 降為 169,071,606 bytes（-37.9%）。
- Chrome 150／Firefox 152：review 6/6、reader cold 6/6、reader warm-cache 6/6 通過。
- reader 12 份與 review 6 份 ODT 全部通過 ZIP/XML、內容條件與桌面 LibreOffice 26.2.4.2
  PDF export；R1～R4 回歸亦通過。
- `writer-automation` 保持 `not-shippable`，本輪沒有重新暴露 unoembind、raw UNO 或任意
  `.uno:*` surface。

機器可讀摘要見
[`findings/evidence/sdk-r5/summary.json`](./findings/evidence/sdk-r5/summary.json)。

## 實作內容

### Product link profiles

[`Makefile`](./wasm_sdk_probe/Makefile) 新增 `r5`／`r5-profiles` target，直接鎖定專案內
Emscripten 4.0.10。這也修掉先前容易誤用系統 Emscripten 3.1.69、導致 libc++ filesystem ABI
不相容的建置陷阱。

兩個 product profile 都不連 R1 `probe_api.cpp`，保留 pthread、WASM exceptions、longjmp、1 GiB
memory ceiling、filesystem 與 strict undefined-symbol check。`writer-reader` 另以
`OXSDK_READER_PROFILE` 在編譯期移除 edit、selection、undo、comment 與 redline wrappers。

實際產物 export 檢查：

- `writer-review`：20 個 `_oxsdk_*` C exports，無 `_probe_*`。
- `writer-reader`：11 個 `_oxsdk_*` C exports，無 click／insert／selection／replace／undo／comment／
  redline，也無 `_probe_*`。
- engine ready event 改為直接呼叫 `oxsdk_capabilities()`，manifest、C ABI 與 event 不再各自維護
  capability 常數。第一輪 browser test 正是由一致性閘門發現舊 event 仍回報 2047，修正後 reader
  runtime 與 manifest 都穩定回報 59。

### Resource packs 與 integrity

[`build_r5_profiles.py`](./wasm_sdk_probe/tools/build_r5_profiles.py) 直接解析完整 Emscripten metadata，
依實際 `/instdir/share/fonts/truetype/` 路徑分類：

| Pack | 檔案 | raw bytes | gzip -9 bytes | 首載 |
|---|---:|---:|---:|---|
| base | 1,241 | 34,178,400 | 7,312,172 | 是 |
| CJK | 1 | 19,484,784 | 15,503,708 | zh-TW corpus 是 |
| fallback fonts | 116 | 49,102,042 | 20,002,976 | 否 |
| **聯集** | **1,358** | **102,765,226** | — | — |

Base 含所有非字型資源及 Liberation Sans／Serif／Mono 的 12 個基本字型；CJK pack 只含
`NotoSansCJK-Regular.ttc`；其餘字型進 optional pack。分類器驗證 source ranges 連續、路徑不重複、
三組互斥、檔案聯集完整與 byte totals 相等，再為每個新 blob 重建連續 offsets 與 SHA-256 metadata。

Worker 在 engine start 前載入 startup pack，拒絕 traversal、非
`/instdir/share/fonts/truetype/` 路徑、重複 path、range gap／overlap／越界、size mismatch 與
SHA-256 mismatch。Browser request evidence 顯示 base unpack 後會抓取並驗證 CJK data／metadata，
才呼叫 `oxsdk_engine_start`；fallback pack 未首載。

R5 沒有刪 Writer UI、registry、filter、configuration 或其他非字型資源。這些仍留在 base，避免在
沒有功能 corpus 證據前把未觸發相依誤判成無用。

### Content hash 與 cache contract

每個 profile manifest 透過 `artifactFiles` 將 `probe.js`、`probe.wasm`、`soffice.data` 與 metadata
logical name 映射到 16 hex content-hashed filename；optional packs 也使用相同命名。Builder 會安全
移除 profile 目錄內舊版 hashed 大型產物，避免每次重建累積重複 binary。

[`serve.py`](./wasm_sdk_probe/web/serve.py) 只對符合 hash pattern 的 JS／WASM／data／metadata 發：

```text
Cache-Control: public, max-age=31536000, immutable
```

HTML、SDK／Worker entry 與 manifest 都是 `Cache-Control: no-cache`。Machine validator 對所有目前
manifest 引用的 hashed artifacts 與四個 entry paths 做 HEAD 驗證，全部符合契約。

### Reader harness 與 Worker gating

[`r5-reader.html`](./wasm_sdk_probe/web/r5-reader.html) 執行：

```text
verified CJK pack → init → open → Latin/CJK search → reject replace/comment
                  → render → save → close
```

Worker 先依 manifest capability 擋下不支援操作，才可能呼叫 `ccall`；因此 reader 不會因缺少 C
symbol 而 crash。TypeScript public class 可維持跨 profile 的穩定型別，實際能力由 init manifest
negotiation 決定。

## 體積結果

以下 gzip 均由 R5 builder 在同一環境以 level 9 串流計算，適合 profile 間比較；不宣稱是 CDN
傳輸 SLA。

| Profile | loader raw / gzip | WASM raw / gzip | startup data raw / gzip |
|---|---:|---:|---:|
| full-qa | 367,855 / 91,028 | 169,263,118 / 45,590,784 | 102,765,226 / 42,824,237 |
| writer-review | 143,265 / 36,153 | 115,265,157 / 40,861,878 | 53,663,184 / 22,815,880 |
| writer-reader | 142,245 / 35,981 | 115,263,591 / 40,863,353 | 53,663,184 / 22,815,880 |

Review 的首載總量（不含很小的 metadata／entry）raw 減少 103,324,593 bytes（37.9%），gzip 減少
24,792,138 bytes（28.0%）。Reader 的 export/capability surface 明顯較窄，但 LibreOffice core 佔
絕大多數，因此 binary 只比 review 再小約 1.6 KiB；這個結果也說明後續若要大幅縮 code，必須有
可證明的 core feature slicing，而不是只刪幾個 wrapper。

## 瀏覽器與桌面驗證

### Product browser flows

每格 3 次且全數 PASS；時間為中位數，單位毫秒。

| Profile／cache | 瀏覽器 | ready | open | first tile | save |
|---|---|---:|---:|---:|---:|
| review cold | Chrome 150 | 838 | 111 | 137 | 226 |
| review cold | Firefox 152 | 1,563 | 411 | 133 | 281 |
| reader cold | Chrome 150 | 824 | 311 | 150 | 197 |
| reader warm | Chrome 150 | 848 | 115 | 183 | 218 |
| reader cold | Firefox 152 | 1,589 | 396 | 133 | 284 |
| reader warm | Firefox 152 | 1,498 | 394 | 135 | 288 |

本機 loopback 與瀏覽器編譯 cache 使 warm 數值不一定比 cold 低；R5 在此驗證的是 warm 路徑可重跑
及 HTTP cache contract，不把這組數字外推為正式 CDN 效能。

Review 6/6 另確認 Provider discovery、三段 progress、concurrent edit stale rejection、undo、
validated replace、Worker 隔離與 final revision 3。Chrome／Firefox Provider conformance 都確認
invalid operation 不進 sink、cancel 不造成 late mutation、無 generic UNO／raw document surface。

Reader cold/warm 共 12/12 確認 capability bits 59、CJK startup pack、`LibreOfficeKit`／
`臺灣軟體工程` 搜尋、tile、save，以及 replace／comment typed rejection。

### ODT round-trip 與回歸

- reader 12/12：ZIP CRC、`content.xml`、中英文字、原文完全不變、blocked replacement 不存在，
  桌面 LibreOffice 26.2.4.2 可轉 PDF。
- review 6/6：預期 Provider 文字存在，concurrent edit／`.uno:Paste` 不存在，桌面可轉 PDF。
- R2 conformance：lifecycle、ABI mismatch、ownership、cancel／timeout、invalid／stale handle、10 次
  open-render-close soak 與真實 Worker crash recovery 全部通過。
- R3 ABI conformance 與 semantic review flow 通過，輸出 comment／tracked-change round-trip 通過。
- R1 legacy full-qa open／render／insert／save 通過，輸出 ZIP/XML、文字保留與桌面開啟通過。
- `make test-r5`：Document SDK 9/9、Provider SDK 11/11、C++ ABI header、Worker syntax 與 resource
  classifier tests 全部通過。

## 工作區完整性與限制

- `libreoffice-26-8` HEAD 仍是 `671c848b1bb81e5b1a90d97675db9a0f3ae2a9cb`；tracked／untracked
  狀態與 R5 進場前完全相同。R5 沒有修改 core。
- Workspace 根目錄不是 Git repository，因此本輪外層 spec、SDK、tooling 與 evidence 無法依單位
  切 commit；以 profile manifests、content hashes 與 machine summary 追溯。
- Optional fallback pack 的產品觸發政策目前只定義語意，尚未做文件 font inventory 自動重啟；首版
  可依 locale／fidelity policy 明確載入。
- 測試 server 不做 gzip／Brotli on-the-fly，gzip 數字為離線比較；正式 CDN、Service Worker、range
  request 與長期 cache eviction 不在本輪範圍。
- 相同 source 重新編譯 product WASM 時曾出現 hash 漂移，但 exports、大小與行為不變；R5 不宣稱
  LibreOffice/Emscripten link 已達 bit-reproducible。Builder 會依實際 bytes 更新 hash、manifest 並
  清除舊檔，最後交付 hash 已重新跑完 18 個產品 browser samples。
- `writer-reader` 與 `writer-review` 的 code 差異小，下一輪若追求更低 WASM 體積，需要針對 filter、
  UI/config 或 core library 建立額外功能 corpus 與 link reachability 證據。

R5 已把「體積最佳化」從不可追蹤的刪檔，轉成可驗證的 code profile、resource profile 與 cache
contract；符合規格的 Go 條件，可進入下一個里程碑。
