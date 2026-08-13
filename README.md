# study_LiteCore

**LibreOffice → WebAssembly 可行性研究的紀錄。**

> **In English** — This repository is the *written record* of a feasibility study on
> running the LibreOffice document core (LibreOfficeKit) in the browser via
> WebAssembly, against a LibreOffice 26.8 baseline. It contains specifications,
> numbered findings with their supporting evidence, and development logs — all in
> Traditional Chinese.
>
> **It is not a buildable project.** The study spans roughly 69 GB on disk: five
> upstream checkouts, a 4.2 GB toolchain, ~43 GB of build trees, and 1.7 GB of
> frozen build artifacts. **None of that is in git**, by design — what you get on
> clone is ~27 MB of documents and measurement evidence. Cloning this repository
> will not let you reproduce a build; it lets you read what was measured, what was
> concluded, and — importantly — what was later retracted.
>
> Findings that appear to be upstream defects are recorded in [`findings/`](findings/)
> and have **not** been filed upstream yet.

---

## repo 裡有什麼、沒有什麼

這是這份 README 最重要的一段。`.gitignore` 是刻意寫成 allowlist 的：預設忽略一切，
再逐項放行自己寫的東西。所以 **clone 下來只有 27 MB**，而磁碟上的研究環境大約 69 GB。

**收在版控裡的**（9,658 個檔案）：

| 目錄 | 內容 |
|---|---|
| [`specs/`](specs/) | 33 份規格（R 系列＝reader／SDK，E 系列＝editor） |
| [`findings/`](findings/) | 38 份編號問題紀錄，附 9,157 個證據檔 |
| [`devlog/`](devlog/) | 開發日誌，2026-07-31 起 |
| [`research/`](research/) | 前置研究與外部方案調查 |
| [`handoff/`](handoff/) | session 之間的交接紀錄 |
| [`docs/`](docs/) | 運維文件（部署清單、已知限制、artifact 備份） |
| [`wasm_sdk_probe/`](wasm_sdk_probe/) | 探針與 SDK 的**原始碼**（不含建置產物） |
| [`wasm-lite/`](wasm-lite/) | 建置說明與 8 份 patch 快照 |
| [`Skills/`](Skills/) | 這個專案沉澱出來的可重用工作方法 |

**刻意不在版控裡的**：

- 五個上游 checkout／worktree（`libreoffice-25-2`、`libreoffice-26-2`、`libreoffice-26-8`、`collabora-25.04`、`cool-26-04`）
- 約 43 GB 的建置樹與 4.2 GB 的 Qt／Emscripten 工具鏈
- `wasm_sdk_probe/dist/profiles/` — 1.7 GB 的**凍結 artifact**，是證據綁定的錨點，
  且至少 R5 profile 已無法從原始碼重建。它們走另外的 checksum 備份，見
  [`docs/ARTIFACT-BACKUP.md`](docs/ARTIFACT-BACKUP.md)。

## 從哪裡開始讀

想知道**這個研究做出了什麼**：

1. [`litecore-analysis.md`](litecore-analysis.md) — 最初的整體分析
2. [`specs/SPEC-E1-000-overview.md`](specs/SPEC-E1-000-overview.md) — 編輯器線的規格總覽
3. [`findings/README.md`](findings/README.md) — 38 份問題紀錄的索引表，附狀態與嚴重度

想知道**這個研究怎麼做的**：

- [`QA-GUIDE.md`](QA-GUIDE.md) — 怎麼參與 QA
- [`Skills/`](Skills/) — 從這個專案長出來的方法論，例如「每次建置要好幾小時時，怎麼二分出是哪個建置選項造成差異」
- [`devlog/`](devlog/) — 逐日的實作與量測過程

## 關於證據

這份紀錄的組織方式，是為了讓**結論可以被推翻**。

每一份 finding 都綁著 `findings/evidence/` 底下的量測資料，而量測資料綁著特定的
建置 artifact——因為[這個專案量到 wasm 產物的 hash 並不是原始碼的函數](findings/036-the-shipped-wasm-hash-is-not-a-function-of-the-source.md)，
所以「哪一版引擎」不能靠原始碼版本推定，只能靠 artifact 本身認定。

因此這裡有若干 finding 是**已撤回或已改判**的，而且撤回紀錄原地保留、不刪除。
最完整的例子是 [finding 014](findings/014-firefox-long-lived-wasm-worker-init-exhaustion.md)：
原本歸因為 Firefox 的缺陷，後來查明是量測工具自己的 pipe 阻塞
（[finding 023](findings/023-sdk-init-wedges-at-fixed-session-depth.md)），三組觀察全部撤回。
撤回的過程與代價都留在文件裡，因為那本身就是這個研究的一部分。

## 授權

Copyright (c) 2026 foolfitz

- 文件、規格、findings 與證據資料：[CC BY 4.0](LICENSE)
- [`wasm-lite/patches/`](wasm-lite/patches/) 底下的 patch **不適用上述授權**——
  它們是 LibreOffice 與 qtbase 原始碼的衍生作品，各自沿用上游條款
  （MPL-2.0／GPL-3.0-only／LGPL-3.0-only，逐檔不同）。
  詳見 [`wasm-lite/patches/NOTICE`](wasm-lite/patches/NOTICE)。
