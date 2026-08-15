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
| **9** | `src/editor_api.{h,cpp}` | **新 C symbol `oxsdk_editor_set_action_gestures(action, mask)`**＋路由的拒絕分支 | 5.7 v10 |
| **10** | `src/probe_engine.cpp` | **路由讀取要先檢查型態再讀 html**（037 的新呼叫點） | 2.3 v10 |
| **11** | `src/probe_engine.cpp` | 五個新 shape 名稱**照 2.3 v10 的字串**寫死 | 2.3 v10 |
| **12** | `src/probe_engine.cpp` | 把 `preBlocks`、走了哪條路由、逐 block 判讀**發成 state 欄位** | 7.1 歸屬 |
| **13** | `src/probe_engine.cpp` | `editorActionMutates()`／`requireRevision()` 要涵蓋 11–15（`:3591`） | — |

**export list 因此是五個 symbol，不是四個。**

**P1 完成才能 relink。漏一項就是第二次 relink。**

## P1 完成（2026-08-15）

**產品 v2 artifact：`572035ac…`**，profile 在 `dist/profiles/e2-editor-v2/`。

> 第一次連結是 `64b94569…`。改了 Makefile（profile target 與 static target）
> 之後守衛判定它過期——**那正是 finding 042 的情形，守衛做對了**。
> 因為當時**還沒有任何證據綁上去**，重連結是免費的，就重連結了。
> **P3 開始之後同樣的情形要付的代價完全不同。**

連結當下核對：**四顆凍結 artifact 全部逐位元未變**
（`835b453d`／`679def61`／`c89f069e`／`940b7723`）；
五個產品 symbol 都在 loader 裡；**discovery symbol 零個**。

> 這一顆是**還沒有任何判定綁上去**的 artifact。P2 改完 JS 之後若發現
> 引擎還要動，現在還來得及重連結——**P3 開始之後就不行了**。

**整條路已經冒煙測過**（`tools/run_e2b_smoke.py`，Chrome）：
engine 起得來、manifest 讀得到 gestures 與 limits、
**五個段落動作全部派送成功**、revision 每次剛好 +1（0→5）、
`changed: null` ＋ `verified-format-readback` 被放寬後的驗證接受、
而且 `route: collapsed`／`preBlocks: 0` 一路從引擎經 worker 傳到 client
——路由的證據欄位是通的。

> 冒煙測試第一次跑就抓到一件事：**profile 內含的是 worker 的複本**，
> 我改了 `sdk/sdk-worker.js` 但 profile 還是舊的，所以 `editorActionV2`
> 是未知操作。這種接線錯誤本來就該死在這裡，而不是死在 90 個 run 的第一格。

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

## 三個風險，覆核之後的結論

**一、B' 的 wasm 一致性——風險消失了，而且不是靠賭。**

原本的問題：跨段 html 讀回在 wasm 上沒量過，要量就得先有 B'，
若 P3 發現不同，退回 A 要第二次 relink。

**解法是 P1 第 9 項本身**：A 的拒絕 ＝ manifest 宣告
`gestures: [collapsed, single-range]`，由 engine 的 mask 執行；
B' ＝ manifest 宣告三個都收。**同一個機制。**
而那個機制**本來就非進 relink 不可**（否則部分 GO 不可執行）。

所以：**A 與 B' 的選擇變成 manifest 的選擇，在不重連結的那一層做，
而且是在 P3 量到 wasm 真實行為之後才做。**

> 我原本擔心「兩條路只有一條被走到」。不成立：
> **兩條在 P3 都會被走** —— B' 走 90 格正向矩陣，拒絕走 N11。
> 也擔心「這樣的 artifact 不算產品」。不成立：
> artifact ＋ manifest 三件組**才是**產品，而「只能收窄」本來就是 5.7 的語意。
>
> **代價是紀律不是相容性**：兩條處置**各要自己的預先登記預測**，
> 而且要在 P3 開始**之前** commit。3.7 原本就要求拒絕那條要有自己的一輪
> ——現在它從假設變成跑得起來的東西。

**二、90 個 run：尺寸對，形狀缺六格。** 三次重複是合理的——本專案每一臂
在輪與輪之間都是逐格相同，判別力來自**格**不是**次數**。缺的是格，
已補進 7.1（反向、清單轉換、清單中段離開、混合狀態、no-op 兩族、rollback 驗收）
再加 9.9 的自我紅臂。

**三、demo 與凍結分開排，而且這是可檢查的不是方便的答案。**

可否證的問法：**同事 demo 需要 P1–P4 的任何一個產物嗎？** 不需要。
擋路的是 #49，已修已驗；`demo-structure` 今天就跑在釘死的 `c89f069e` 上，
五個動作與復原鈕都在。第 9 節的遷移條款觸發條件是「**產品 build 出現之後**」
——它是**凍結的交付項**，不是 demo 的前置。

> **但 demo 腳本有一件事要先決定**：在現在這顆 build 上做**跨段拖曳**，
> 會重現 G3 的過寬成功宣稱——文件結果是對的，宣稱只涵蓋一段。
> 要嘛腳本的選取都留在單一段落內，要嘛發生時明說。
> **在 demo 之前決定，不要在 demo 當下決定。**
