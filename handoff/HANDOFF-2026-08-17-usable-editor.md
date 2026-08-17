# 交接 — 2026-08-17：短期目標轉向「能用的編輯器」，以及它掉出來的四個缺陷

> 進場點。讀完這一頁就能接手，不需要翻前面的交接。
> 前一份是 `HANDOFF-2026-08-16g-block-identity-and-high-paths.md`。

## 0. 目前綁定

| | |
|---|---|
| artifact | `d538ce0b91478426…`（**未動**，本階段沒有連結） |
| 殼層 | **v16 `e48685976e8626c5…`**（本階段 v12 → v16，四代，全部不需連結） |
| manifest | `a7d2b6ba09a06e68…` |
| 矩陣 | `e2/validation-matrix-v2.json`，**D0 仍未跑** |
| 產品路徑 | **13 格：11 PASS ＋ 1 NOT_ESTABLISHED ＋ 1 KNOWN_RED** |
| 佇列 | `P1 complete: **False**` —— 059 擋著下一次連結，**這是對的** |

本階段七個提交：`4f82ae9`、`eda1417`、`79b975b`、`787b25f`、`ab28942`、`1bba4e1`、`efbc5dd`。

## 1. 目標變了（使用者裁示，2026-08-17）

> **a11y／block identity 移到長期目標；短期目標是「一個可以讀檔、擁有基本編輯功能的編輯器」。**

**不要再拿 a11y 當推力，也不要為它提議重編 core。**

## 2. 驗收清單是這條線的入口

**`wasm_sdk_probe/e2/usable-editor-checklist.json`**，由 `tools/check_usable_editor.py` 執行
（自測 8 格）。說明頁 `specs/SPEC-P-usable-editor.md`。

每一格必須指到**真的存在**的 `check`（runner 的檢查 id）／`queue`／`finding`，指不到就紅。
狀態字彙**只由 JSON 的 `statuses` 供應**（曾經 JSON 與 Python 各寫一份，十分鐘就漂移）。

```
done        7  開檔、存檔、中文輸入、複製貼上、看得到游標、鍵盤改錯字、復原
partial     2  剪下（移除未證）、快捷鍵（Ctrl+B/I/U/S 待 059）
unverified  3  點擊定位、段落格式、錯誤復原
missing     1  真實長度文件
blocked     3  格式開關（059）、redo、上下鍵 —— 都要連結
```

**「做完」＝清單綠 ＋ 每個 `done` 的檢查綠 ＋ 沒有 `blocked`。** 今天三件都不成立。

## 3. 本階段查清楚的四件事

### 056／057 —— a11y 是建置組態，而且改組態也修不好

`--with-wasm-module=writer` → `ENABLE_WASM_STRIP_ACCESSIBILITY` → `sw/source/core/access`
少編 26 個物件（**實測 2 對 28**）→ `SwEditWin::CreateAccessible()` 回 `{}` →
`SetLOKAccessibilityState()` 靜靜返回。**出貨的二進位自己作證**：`SwAccessible*` 命中 0、
`LOKDocumentFocusListener` 命中 45。

**057**：同一個開關兩半接到不同輸入，而 `enable_wasm_strip` 對 Emscripten 是
`configure.ac:1280` **無條件 yes**。⇒ **26.8 的 Emscripten 上沒有任何旗標組合能開**。
要動就得改 `configure.ac` ＋ 重編 core。

守衛：`tools/check_core_build_provides.py`（問 core 的 build 有沒有提供產品宣稱的能力，
比 `check_product_build_reaches.py` 低一層）。**它現在是紅的，而且應該是。**

### 046 殘留 —— 修的是**處置**，不是判決

空白行按項目符號不再叫使用者回檔。`recovery` 新增第四個值 **`review`**
（SPEC E2-C **2.6b**，與殼層世代同一次出貨）。

**實作要點**：基底類別是看**錯誤碼**擋佇列的（`editor-shell/editor-session.js:20` 的
`RECOVERY_ERRORS` 含 `MUTATION_OUTCOME_UNKNOWN`），而那個檔**綁 E1-C 雜湊不能動**。
做法是讓操作以 sentinel **resolve**（基底的 catch 只在 reject 時跑），drain 外再丟原始錯誤。
**而且它會自我撤銷**：sentinel 沒帶 `state`，drain 會向引擎要一次 `getState`，引擎卡住就
TIMEOUT，而 TIMEOUT 在 `RECOVERY_ERRORS` 裡。

**明確不涵蓋文件最後一行的空段落**——它到不了 readback（`stage-deadline:awaiting-selection`）。
**不要說「空白行按項目符號不會再叫你回檔」。**

### 058 —— 使用者看不到游標（已修）

九格回歸網全綠，而畫面上沒有游標、沒有反白。資料一直有送，頁面只是沒有畫。
已修（`paint()`）。判準是**同一條帶狀區域的深色像素差**（2763→2739）。

**判準第一版取直行，沒抓到**——游標吸附到文字位置，x 不是點擊的 x（差約 43 px）。

### 059 —— **擋下一次連結**，機制已定

驗收清單第一次驅動 `set-bold` 就掉出來：**四個 inline 格式在出貨的 artifact 上全部
`LOK_COMMAND_FAILED`**，每按一次還把 session 打進 `recoverable-error`。

原生對照（`findings/evidence/059/native/`）**推翻了本篇原本的假設**：

| 臂 | 存檔樣式 | 粗體？ | 命令結果 |
|---|---|---|---|
| `.uno:Bold` ＋ 參數 `true` | `T1` `bold` | **是，成功了** | **`success:false`** |
| `.uno:Bold` 不帶參數 | `T4` normal | 否 | `success:true` |
| `.uno:DefaultBullet` ＋ `{"On":…}`（對照） | — | — | `success:false` |

**核心照做了，然後回報失敗。** 缺陷在我們這邊：`commandResultSucceeded()`
（`probe_engine.cpp:1696`）要 `success:true`，`:2286` 把其他變成 `LOK_COMMAND_FAILED`；
**barrier 那條路不這樣判**，所以清單動作照常運作。

⇒ **不要撤回 `inlineFormatArgument`，045 的修法是對的。** 要改的是判準
（`wasModified` 或 barrier 的 readback，**兩個都還沒量**）。

**一格明確沒量而且重要**：WASM 上是不是也「照做了但回報失敗」。產品一按就進
`recoverable-error`、佇列被擋，打不了字也存不了檔，**在產品路徑上量不到**。
若也是照做了，今天的產品是**在一個成功的動作上叫使用者回滾**。

## 4. 接手就能做的（都不需要連結）

1. **把 `unverified` 三格接進回歸網。** 十四個動作在 `e2/product-path-coverage.json` 裡
   是 uncovered——「按鈕在、沒人按過」。**這棵樹被這形狀咬過五次**（049／050／Ctrl+C／
   058／059）。
2. **真實長度文件的量測**（`queue-viewport-wall-never-measured`）。頁面把整份文件畫成
   一張 canvas、每次編輯整張重畫；瀏覽器上限約 32767px，A4 大約十幾頁**靜默**撞牆。
   先量，不要先修；`TileScheduler` 已經被 `editor-session.js` 匯入。
3. **recovery 路徑的新誘發手段**（`queue-recovery-path-lost-its-inducer`）。v14 之後
   046 那一格不再進 `recoverable-error`，而它是回歸網唯一的入口。候選：註腳形狀
   （`endnote-frame.odt` 存在，而且產品現在能開任意檔案）。

## 5. 下一次連結要帶的（`P1 complete` 為 False 的原因）

- **059 的判準**（`queue-inline-format-argument-is-rejected-by-core`，`blocksRelink: true`）
  —— **先做原生量測**再決定用 `wasModified` 還是 readback。
- `queue-quantifier-check-for-multi-block-readback`（046 的驗證，全部或全部沒有；
  **「驗 block[0]」已被否決不是延後**，有反例）。
- `queue-redo-and-line-movement-need-wire-ids`（**契約**層，不是引擎沒做）。
- `queue-engine-must-report-core-lacks-accessibility`（引擎別再謊報 `enabled: true`）。

## 6. 給接手的人：這一階段真正的教訓

**所有自動化都從 DOM 和存出來的 ODT 判讀，而那些全部可以在一個什麼都不畫、按鈕全壞的
頁面上通過。**

| | 沒被量到的是 |
|---|---|
| 049／050／Ctrl+C | 按鈕沒人**按**過 |
| 056 第一次連結 | 機制沒人確認**編進去**沒 |
| 貼上（本階段） | 假設「殼層有、沒人呼叫」，**沒量就寫** → 貼兩份 |
| 058 | 畫面**沒人看**過 |
| 059 | 修法出貨之後**沒人按過那顆按鈕** |

具體的操作紀律，本階段各犯過一次：

- **動手加 handler 之前，先確認沒有別人在處理同一個事件。** 貼上那次沒確認，突變輪量到
  `markOccurrences: 2`。打字路徑那次先確認了。
- **新檢查放在**所有用**位置索引**取存檔的檢查**之後**，否則會把它們的索引推移
  （踩到兩次）。
- **檢查要指對檔案。** `queue-no-cut` 和打字路徑那項原本指著 `input-adapter.js`——
  **不管做了什麼都不可能變綠**。
- **`--write` 不再默默重寫既有殼層世代**（我把 v14 原地重寫成不同 digest，已從 git
  逐位元還原）。守衛第一版**擋下了寫入卻不說話**——我 rebind 了 list 而 report 抓的是
  舊的，正是它要防的形狀。
- **`KNOWN_RED`**：runner 可以宣告某格為了某個 finding 紅著（不 confound 突變輪），
  **而且它一旦變綠，runner 主動說宣告過期**。

## 7. 外部裁決

- **fable subagent `a049290c1399c57f2`**（可用 SendMessage 續談）。本階段兩輪：046 的
  修法（否決了我兩個候選，第三條路是它提的）、盤點審查（找出 058、指出「產品介面從來
  沒有被設計過」、糾正我對 redo／move-line 的層級判斷）。
- **codex**：057 是它找到、而我原本判錯的。

## 8. 不要重犯

- **不要把 a11y 當推力**（長期目標）。
- **不要撤回 `inlineFormatArgument`**（045 是對的，見 059）。
- **不要說 046 修好了「空白行按項目符號」**——文件最後一行不涵蓋。
- **不要在 059 修好之前把 Ctrl+B/I/U/S 接上鍵盤**——那是把缺陷複製到第二條路徑。
- **D0 一跑，殼層再動就得換矩陣**，不能再原地重凍。
