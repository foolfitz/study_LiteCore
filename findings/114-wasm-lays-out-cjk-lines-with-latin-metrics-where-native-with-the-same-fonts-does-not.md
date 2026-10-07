# 114 — 同一組字型檔與 fontconfig，原生用 CJK 行高、WASM 用拉丁行高：擁有者文件在 WASM 上每一行約 0.79 倍高

| | |
|---|---|
| **狀態** | **已確認、未診斷**（2026-10-07）：差異在 WASM 引擎那一側，不在字型集；成因未讀 |
| **所在** | WASM 建置的字型解析／替代（推論，未讀原始碼）。字型包、頁面、殼層都已排除（見下） |
| **發現日** | 2026-10-07（merge WASM shakedown 第 3 次：擁有者文件 11 格全部 `placement-mismatch`） |
| **嚴重度** | 一般：沒有東西消失，但擁有者這類台灣字型名的文件在 WASM 上整份比桌面版矮約兩成、分頁不同（WASM 文件總高 257,114 twips，原生在 275,530 還有內容） |
| **可重現** | 100%（決定性：原生兩種字型設定 11 格逐 twip 相同；WASM 兩次執行相同） |
| **是否上游** | 未定（要先讀 WASM 的字型替代路徑才知道是上游的 WASM 移植還是我方的組態） |

## 現象

擁有者的 `PMPC指南.odt` 在 WASM（v16）上，原生 R0c 記下的游標放不回去：同一個位置的行高原生 348／521 twips，WASM 276／414。
這組數字跟度量值的算術對得上：276＝12 pt × Liberation Sans 的行距 1.149，348＝12 pt × Noto Sans CJK 的 1.448；414／521 是 18 pt 的同一對
（**推算**，不是從引擎讀出來的）。也就是 WASM 用拉丁字型的行高排這些中文行，字形照常畫出（glyph fallback）。

這是 finding 113 末段留下的開放項目（「台灣字型名在 v8 就已經拿到拉丁行高，未診斷、未量成保真缺口」）第一次在擁有者的文件上有數字。

## 排除了什麼（判別實驗，預測先 commit：`findings/evidence/merge-native/r0c-wasmfonts/PREDICTION.md`）

- **不是字型集**：把 v16 profile 的 13 個字型檔與它自己的 fontconfig 抽出來（`tools/extract_wasm_fontset.py`），用 `FONTCONFIG_FILE` 讓原生只看得到它們，
  重跑原生 R0c——11 個游標與用系統字型那一輪**逐 twip 相同**（W2 沒中）。
- **設定確實生效**（正向對照）：同一個探針在 `strace` 下，帶設定只開了 7 個字型檔、全部屬於抽出來的那組；不帶設定開了 363 個系統字型檔。
- **不是合併**：同一輪的合併判讀 11 格都是 `merge`、0 KILL（W1 命中）；WASM 上這 11 格根本沒按到鍵。
- 這份文件的字型名在兩種 fontconfig 設定下用 `fc-match` 解析的結果，只有 `Microsoft JhengHei`、`PMingLiU` 不同（這台機器裝了真的微軟正黑體、
  新細明體）；其餘（含主要的「思源黑體」）都解析成 Noto Sans CJK TC——而原生換了設定版面不變，所以那兩個名字不是這份文件版面的來源。

## 重現步驟

1. merge WASM runner 對擁有者文件（`run_merge_wasm_shakedown.py --cases E01`，需要 `build/` 底下的文件）：`place.engineCaret` 的高度對 `nativeCaret` 的高度。
2. 原生：`FONTCONFIG_FILE=…/build/wasm-fontset-v16/fonts.conf MERGE_ESHAPE=1 MERGE_FOLLOW_TEXT=Z tools/run_merge_native.sh <out> 1 <PMPC> test-docs/merge/r0-pmpc.cases.tsv 1`，
   看 `arms.jsonl` 的 `placed.cursor`。

**預期**：同一組字型、同一個 core，行高相同。**實際**：原生 348、WASM 276（E01 等七格）；521 對 414（E02）。

## 影響

- M2-1 在擁有者文件上無法用原生座標放置（規格 §25：退回 A）。
- 保真：凡是段落字型名不是剛好五個 Noto Sans CJK 家族名之一的中文文件，WASM 的版面都可能比桌面版矮（113 的機制在 v16 的五家族之外仍然存在）。
  量成語料層級的保真缺口，要等 20.3／21.2 的語料版面比對（那是 v16 對完整 TTC，不是對原生）或另立一個對原生的比較。

## 未做

- 讀 WASM 建置的字型替代路徑（為什麼同一組 fontconfig，原生把「思源黑體」解析成 Noto Sans CJK TC、WASM 卻用 Liberation 的行高）。
- v8 上同一份文件的行高（113 說 v8 也如此，這次沒量）。
