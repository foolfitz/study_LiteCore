# SPEC R5-000：Resource and size profiles

> **日期**：2026-08-01  
> **狀態**：完成（GO）  
> **依據**：[R4 結果](../devlog/DEVLOG-2026-08-01-wasm-sdk-r4.md)、
> [SDK 主報告 §6、§10](../research/RESEARCH-2026-08-01-oxoffice-wasm-document-sdk.md)

## 1. 目標

把 R1～R4 刻意延後的體積工作集中在可回歸、可解釋的 profile system：

```text
full-qa baseline
    ├── product link flags ──► writer-review / writer-reader code profiles
    ├── resource classifier ─► base + CJK + fallback-font packs
    └── content hashes ──────► immutable large-artifact cache policy
```

每個減量必須指出移除的是什麼、對應哪個功能邊界，並以相同文件與瀏覽器測試證明結果；不能以
刪檔後「剛好啟動」或只量 raw bytes 作成功標準。

## 2. Baseline

R4 `full-qa` 核心 artifact：

| 產物 | raw bytes | gzip -9 bytes |
|---|---:|---:|
| `probe.js` | 367,855 | 90,960 |
| `probe.wasm` | 169,263,111 | 45,649,122 |
| `soffice.data` | 102,765,226 | 42,969,853 |
| **合計** | **272,396,192** | **88,709,935** |

`soffice.data` 有 1,358 個檔案；`/instdir/share/fonts/truetype` 的 129 個字型共
72,945,990 bytes，是最大可分包來源。現行 link 使用 `-O1`、assertions 與
`--profiling-funcs`，適合作 QA，不應直接當產品 profile。

## 3. Profile matrix

| Profile | 定位 | C ABI／功能 | Link | 資源 |
|---|---|---|---|---|
| `full-qa` | 診斷與回歸基線 | R4 全能力 + legacy harness | R4 assertions／profiling | 完整單包 |
| `writer-review` | Provider／協作產品 | R4 review semantic API | `-Oz`、無 profiling names、assertions off | minimal base + startup CJK；fallback optional |
| `writer-reader` | 閱讀、預覽、搜尋 | open／render／search／save／cancel | 同 product flags、縮窄 C exports | 同分包；CJK 依產品 locale 啟用 |
| `writer-automation` | 未來企業 automation | 尚未定義受控 surface | **本輪不產 binary** | 不適用 |

`writer-automation` 不得以重新暴露 unoembind、任意 `.uno:*` 或 UNO object graph 充數。只有受控
automation operation、權限與相容契約另行定義後，才可從「not shippable」轉為可建置 profile。

## 4. Product link profile

- Product objects 使用 `-Oz`；仍保留 pthread、WASM exceptions、longjmp、1 GiB memory ceiling 與
  strict undefined-symbol 檢查。
- 移除 `--profiling-funcs`、`--bind` 與 assertions。
- `EXPORTED_RUNTIME_METHODS` 只保留 Worker 真正需要的 `ccall`、`FS`、`HEAPU8`。
- Product binary 不包含 R1 legacy `_probe_*` surface。
- `writer-reader` 以 compile-time macro 回報較窄 capability bits，且不定義 edit／comment／redline
  C wrappers；Worker 再依 manifest 做第二層 operation gating。
- C ABI version 維持 1.1；profile 由 capability negotiation 區分，不為相同 ABI 人為升版。

## 5. Resource packs

由完整 Emscripten metadata 與 data blob 可重現地分類：

1. **Base pack**：所有非字型資源，加上 Liberation Sans／Serif／Mono 的 Regular、Bold、Italic、
   BoldItalic 12 個基本字型。
2. **CJK pack**：`NotoSansCJK-Regular.ttc`，提供 zh-TW／中日韓 fallback；R5 中文 corpus 在 engine
   start 前載入。
3. **Fallback-font pack**：其餘字型，預設不首載；遇到阿拉伯文、希伯來文、複雜 script、特定
   fidelity policy 或文件 font inventory 命中時，由產品重啟 engine 並載入。

三包所有檔案的 byte ranges 必須互斥且聯集等於原始 metadata；合併 raw bytes 與 full pack 完全
相同。Pack loader 只接受 `/instdir/share/fonts/truetype/` allowlist path，檢查 size、offset、SHA-256，
拒絕 traversal、重疊、越界與 hash mismatch。

R5 不刪除 Writer UI、registry、filter data 或 configuration。它們先列入 inventory；只有另有
功能 corpus 證據時才可進下一輪減量，避免把尚未觸發的相依誤判為無用。

## 6. Cache 與首載

- WASM、base data 與 optional packs 使用至少 12 hex 的 content-hashed filename。
- 測試 server 僅對符合 hash 命名的 `.wasm`、`.data` 與 metadata 發
  `Cache-Control: public, max-age=31536000, immutable`；HTML、JS entry 與 manifest 維持
  `no-cache`，使版本切換不會黏住舊路徑。
- Worker 先讀 profile manifest，以 `locateFile()` 將 Emscripten 固定 logical name 映射到 hash
  artifact；resource packs 在 `oxsdk_engine_start` 前驗證並寫入 MEMFS。
- 冷啟動報告分列 mandatory base、locale pack、optional fidelity pack，不以三包總和冒充首載。
- 不把 gzip raw sum 當網路 SLA；R5 同時記錄 raw、gzip -9、cold browser ready 與 warm-cache
  ready，樣本只作 profile regression，不宣稱 production CDN 數字。

## 7. Browser harness

### `writer-review`

使用 R4 Provider flow，必須維持：

- Provider Worker／Document Worker isolation；
- progress、cancel、invalid operation block；
- concurrent edit stale rejection；
- comment／tracked-change 能力仍可由 R3 regression 使用；
- CJK output render/save 與 desktop round-trip。

### `writer-reader`

新增 reader flow：

```text
init + verified CJK pack → open → search CJK/Latin → render → save → close
                         → replace/comment request rejected as unsupported
```

Reader manifest capabilities 與 runtime capability bits 必須相同；公開 TypeScript class 可以保留方法
以維持套件型別穩定，但不在 profile 的方法必須得到 typed `UNSUPPORTED_OPERATION`，不能落到缺 symbol
或 runtime crash。

## 8. 驗收

1. Resource classifier 證明三包互斥、聯集完整、offset／hash 正確，並產出每類 inventory。
2. `writer-review` product link 比 `full-qa` 的 raw 與 gzip WASM 都小；strict link 通過。
3. `writer-reader` exports／capability bits 不含 insert、selection、replace、undo、comment、redline。
4. Chrome／Firefox 各至少 3 次 `writer-review` R4 flow 與各至少 3 次 `writer-reader` flow。
5. 兩個 product profile 的 CJK pack 均在 engine start 前完成驗證；中文搜尋、tile 與 save 成立。
6. Review／reader 輸出 ODT 通過 ZIP/XML、預期內容與桌面 LibreOffice 開啟。
7. Chrome／Firefox warm-cache 各至少 3 次 reader 初始化；所有 hash artifact 回應 immutable cache
   header，entry／manifest 回應 no-cache。
8. R4 conformance、R3 semantic flow、R2 conformance 與 R1 legacy/full-qa smoke 仍通過。
9. `libreoffice-26-8` tracked 狀態與進場前完全相同。
10. 交付 profile manifest、resource inventory、cache/header evidence、R5 DEVLOG 與 machine summary。

## 9. Go／No-Go

**Go**：review／reader product links 與分包資源在兩個瀏覽器通過各自 corpus，首載 raw／gzip 有可量測
下降，capability／cache／pack integrity contract 成立，R1～R4 無回歸。

**部分 Go**：link optimization 成立，但 optional CJK 動態載入無法在 engine start 前穩定完成；保留
product binary，產品首版仍以 base+CJK 合併包發佈，fallback pack 保持可選。

**停止回報**：減量只能靠修改 LibreOffice core、移除必要 filter／registry 後造成壞檔、pack integrity
無法在 Worker 邊界驗證，或 product link 在主要瀏覽器產生功能回歸。

## 10. 執行結果

R5 於 2026-08-01 完成並判定 **GO**：`writer-review`／`writer-reader` strict product link、三類資源
pack、content hash 與 cache contract 全部成立。Chrome 150／Firefox 152 的 review 6/6、reader cold
6/6、reader warm-cache 6/6 通過；reader／review 共 18 份輸出 ODT 均通過 ZIP/XML、內容條件與桌面
LibreOffice 26.2.4.2 開啟驗證。R1～R4 回歸、Provider conformance、reader capability／exports、pack
integrity 與 core 工作區狀態也全部通過。

完整數據見 [R5 DEVLOG](../devlog/DEVLOG-2026-08-01-wasm-sdk-r5.md)與
[machine summary](../findings/evidence/sdk-r5/summary.json)。
