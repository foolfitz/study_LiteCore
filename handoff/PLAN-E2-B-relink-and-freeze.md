# E2-B 執行計畫：一次 relink，然後凍結

2026-08-15 訂。規格 v9，第 5 節十四項全部定案、第 7 節門檻已訂。
**這份是執行順序與風險，不是規格**——每一步的內容都在 `SPEC-E2-B` 裡。

## 為什麼順序這麼重要

三條約束疊在一起：

1. **finding 042**：`Makefile` 是每個 `.o` 的前置依賴，改它就重編重連。
2. **finding 036**：hash 不是原始碼的函數，一次 relink 就換一顆 artifact。
3. **finding 027**：判定綁 artifact hash，換了 artifact，綁在舊 hash 上的證據全部失效。

**所以：能在 relink 前決定的都要先決定，能在量測前定稿的都要先定稿，
量測開始之後到凍結之間不得再編。**

## P0 — 動手前（零風險，先做）

- `build/archive/` 存一份現行 profile（memory 的規矩：改引擎前先 archive）。
- 核對三顆凍結 artifact 的 hash 未變：`835b453d`／`679def61`／`c89f069e`。
- 記下 `e2-combination` = `940b7723` 的 hash——本輪所有既有證據綁在它上面。

## P1 — 引擎與 Makefile：**唯一一次 relink**

| # | 檔案 | 內容 | 規格 |
|---|---|---|---|
| 1 | `src/editor_api.h` | v1 enum **一個字不動**；另開 `oxsdk_editor_v2_action` 只含 11–15；ABI 版本常數 → 2（flat） | 5.11、5.4 |
| 2 | `src/editor_api.cpp` | 11–15 → engine internal 15–19；五個段落動作兩個旗標必須為 0 | 5.11 |
| 3 | `src/editor_api.{h,cpp}` | **新 C symbol `oxsdk_editor_abi_version()`** | 5.4 |
| 4 | `src/probe_engine.cpp` | **B'**：派送前 `blocks` 路由；`blocks == 1` 走現行 barrier 不動；`blocks >= 2` 走派送後驗證，身分閘門＝逐 block html 文字相等，狀態檢查逐 block | 9.9 |
| 5 | `src/probe_engine.cpp` | 所有派送後失敗一律 B；不前進 revision | 5.13 |
| 6 | `Makefile` | 產品 v2 建置變體：三個旗標、export list 四個產品 symbol、掛 `refuse_unasked_relink` | 5.12 |
| 7 | `Makefile` | **兩件欠著的**：`f049_native_select_after_format.cpp` 與 `e2b_native_crossparagraph.cpp` 進語法檢查；E2-B harness 與 `dist/e2b-fixtures/` 的 target | 5.12 |
| 8 | `tests/editor_abi_header_test.cpp` | 斷言 11–15 與新的 ABI 常數（`-fsyntax-only`，不影響 artifact） | 5.9 |

**P1 完成才能 relink。漏一項就是第二次 relink。**

## P2 — JS／Python：不重連結，但必須在量測前定稿

| # | 檔案 | 內容 | 規格 |
|---|---|---|---|
| 1 | `sdk/sdk-worker.js` | 明確的操作表取代 `endsWith("V1")`；v2 操作族；產品 state 投影改看集合不是字串相等；轉發 `formatBarrier` | 5.5 |
| 2 | `sdk/sdk-worker.js` | manifest `actions` 的**交集**執行（只能收窄） | 5.7 |
| 3 | `editor-shell/editor-client.js` ＋ `.d.ts` | v2 allowlist、五個方法、路線 C 結果**逐動作**放寬 | 5.6、5.9 |
| 4 | `editor-shell/editor-session.js` | v2 client、五個 session 方法、**B ＝ rollback 到 checkpoint** | 5.13、5.9 |
| 5 | `tools/build_e2_b_profile.py` | 新 builder，寫 manifest 前 fail closed（export inventory） | 5.8 |
| 6 | validator | negative matrix 十列 ＋ `--self-test` | 5.10、7.1 |

## P3 — 量測（產品 profile 上，開始之後不得再編）

- **90 個正向 run**：5 動作 × 3 手勢 × 2 瀏覽器 × 3 次
- `wrapped-paragraph.odt` 變體：`set-list-unordered`，每瀏覽器 ≥ 1
- **negative matrix 十列**，各 1 次／瀏覽器
- **no-op 方程式臂**（新的，從沒測過重複派送）
- **forbidden-field inventory**，一次送一個
- **A3／A4／A5 重掃**（finding 027／036）
- validator `--self-test` 的輸出

## P4 — 凍結與遷移

- 凍結；`demo-structure` 改接 v2，舊的改名保留為歷史實驗檯（第 9 節）
- 格式按鈕必須跟在選取手勢之後（5.13 的 checkpoint 前提）

## 我看到的三個風險

**一、B' 的 wasm 一致性目前是前提不是結論。** 身分閘門在原生量了五輪，
但跨段的 html 讀回**在 wasm 上沒量過**——而要量它就得先有 B'，
也就是先 relink。fable 的翻案條件第 3 條就是這個。
**若 P3 發現 wasm 行為不同，退回 A 需要第二次 relink。**

**二、90 個 run 的規模。** E2-A 的門檻是每瀏覽器 3 次，我照抄。
但 E2-A 是 discovery，E2-B 是凍結前的驗收——同樣的數字是不是同樣的意思，
我沒有把握。

**三、demo 與凍結可能不是同一件事。** demo 的擋路項原本是「選一段再按按鈕」，
那個（#49）**已經修好也驗過**。E2-B 凍結是產品目標。
**這兩件事可能可以分開排。**
