# 交接 — 2026-08-12（035 已關、037 已擋、038 開著、E1-C 已具名收窄）

接手前先讀這一份。上一份是 [`260811-handoff.md`](HANDOFF-2026-08-11-session-state.md)。
**這一份在同一天內被完整改寫過一次**：早上那版只涵蓋到 035／037，下面是一整天的狀態。

## 現在的狀態

| | |
|---|---|
| 分支 | `main`，工作樹乾淨 |
| **E2 出貨引擎** | **`c89f069e7c43e78e630e4f7d62ba5d016c7aaf434d9f4abf5a0e009e931f9d0f`** |
| A3／A4／A5 | **全部 PASS 且綁在 `c89f069e`**（44 輪重掃，`tools/sweep_e2_a.py`） |
| **E1 出貨編輯器** | **`835b453d…`**，`E1_GO_ODT_EDITOR`，48 綁定 0 superseded（**未動**） |
| 測試 | `wasm_sdk_probe` 下 `python3 -m unittest tests.test_e2_profile` → 55 過 |
| 語料閘門 | `python3 tools/validate_e1_corpus.py` → pass（**現在真的會跑**，見下） |

存檔的 artifact（`wasm_sdk_probe/build/archive/`，gitignore）：
`bd102b4a` → `38168306` → `ee185b3d` → **`c89f069e`（現行）**。

## 動手之前必讀

1. **凍結的連結現在會拒絕重連結。** 三個（E2 出貨、`e1-editor-discovery`、`e1-editor-v1`）
   共用 `refuse_unasked_relink`，要重編得明寫 `make ALLOW_FROZEN_RELINK=1 <target>`，
   而且拒絕訊息會講清楚那個 artifact 承載什麼。**這是這一輪加的，因為我自己改 Makefile
   時把三個都變成過期而只擋了一個。**
2. **要診斷不一定要重編。** 引擎本來就把每一個 LOK callback 在處理前送出，只是出貨 worker
   丟掉——重新打包同一份 wasm＋worker 副本多兩行就拿到完整現場（`e2-wedge-trace`、
   `e2-preguard-diagnostic`）。**重編是最後手段。**
3. **fixture 的共用區塊會炸掉既有證據。** `create_e1_corpus.py` 的 `NAMESPACES`／`STYLES_XML`／
   `MANIFEST_XML` 是**所有 fixture 共用**，新 fixture 必須自帶；改完一定要
   `git show HEAD:<path> | sha256sum` 逐份對，**別信工具自己報的數字**。
   語料現在有 13 份（新增 `image-variants`、`frame-no-image`、`frame-paragraph-anchored`、
   `frame-char-anchored`、`frame-contexts`、`endnote-frame`）。

## 這一天做完的事

**035（中日韓段落 fail closed）已修並關閉**——結構深度 parser，一次 build，44 輪重掃。

**037 已定位到單一呼叫並擋下（我方）**：卡的是 `getTextSelection(…, "text/html", …)`，
擋法＝讀取前先取 selection type，非 `TEXT` 就 `selection-type-not-readable` 具名拒絕。
同一列由 **20001 ms 卡死變成 37 ms 拒絕、事後 handle 可用**。殺傷範圍是量的：
`c89f069e` 上 428 次 barrier，426 次 TEXT，被擋的 2 次都是圖片那列。

**037／012／038 是同一個內容特徵的三個入口**，觸發條件收窄到 **`as-char` 錨定的 `draw:frame`**：

| finding | 入口 | 狀態 |
|---|---|---|
| 037 | `getTextSelection("text/html")` 不返回 | 我方已擋，core 端未修 |
| 012 | `destroy()` 不返回 | SDK 有界 close recovery，root cause 未修 |
| **038** | **選取涵蓋註腳引用記號時卡死** | **開著，037 的擋法搆不到** |

012 這一天收窄兩刀：**image 不是必要條件（frame 才是）**、**`as-char` 是必要的**
（`frame-no-image` close 10829 ms 要 recovery；只差一個 `text:anchor-type` 的
`frame-paragraph-anchored` close 11 ms、零 recovery）。

**038 的觸發是兩個條件缺一不可**：選取**涵蓋註腳／尾註的引用記號** ＋ 該註腳本文**有 as-char frame**。
四格全部實測，而且**在出貨 artifact `835b453d` 上逐格複製過**（走出貨路徑 `editorSelectRangeV1`）。
**選取本身就殺死引擎**——選完靜置 8 秒不下任何命令，引擎已經死了。

**E1-C 判定經外部覆核（fable）裁定「重新界定而非撤銷」**，SPEC-E1-C 新增 **9.1 具名收窄**。
理由：C3 五份語料有 as-char frame（`l0-t2` 1 個、`l4-stress-100` 100 個）但**沒有任何 `text:note`**，
所以該組合不可能出現、沒有記錄過的 PASS 變錯——依 034／035／037 前例。48 個綁定未動。

## 下一步（按覆核定的順序，1、2 已完成）

3. **(d) 復原 ＋ (c′) 重新界定後的閘門，同一次 worker 改動。**
   **關鍵事實：這兩個都在 worker JS，不動 wasm**——E2-A 那 44 輪不受影響。
   我原本的成本表把它們寫成「要重編、會解綁 E2-A」，**那是錯的，也是自利的**，覆核直接點名。
   代價是 E1-C 要重新綁定（worker 改動會換編輯器 bundle 身分）。
   **(c′) 必須擋掉所有會造成選取的動作**，不只範圍選取——鍵盤 shift-extend 屬於**原本八個動作的契約**。
4. **上游單**：草稿 `findings/drafts/037-bugzilla.txt` ＋ 重現包 `findings/repro/037-as-char-frame-hang/`
   （含一屬性對照的兩份 fixture 與可編可跑的最小 LOK 探針）。**要補上 038 與 as-char 那一刀再送。**
5. **語料內容軸清單**（覆核點名、我原本四個選項裡完全沒有）：每份 fixture 含哪些 ODF 構造，
   對上出貨手勢碰得到的構造，**列為日後發 GO 的必要輸入**。034／035／037／038 都是
   「軸不在矩陣裡而且沒人看得出它不在」——這是唯一治本的一項。

## 還沒有答案的

- **那條執行緒在等什麼。** 已知它**停等不是空轉**（同一輪卡死前後各 profile 一次，兩欄一模一樣）。
  **`-sPTHREADS_DEBUG=1` 不能回答**——它只印執行緒生命週期，不印 futex／proxy（我挑錯工具，
  花了一次編譯）。那次編譯的收穫是 name section：`wasm-function[36295]` ＝ `__pthread_cond_timedwait`。
  剩下的路：在 core 裡加 log（大編譯），或從主執行緒讀 pthread 結構（未試）。
- **038 卡在哪個呼叫**：選取的 callback 與 result 都出來了才靜默。
- **為什麼表格儲存格裡的 frame 走 037 的擋法，而註腳裡的不走。**
- **完整 `EditorSession` 狀態機會不會自己升級成 `restart-required`**（直接影響 (d) 是要蓋還是只要標型別）。

## 方法論：這一天被抓到的錯

**沒有一個是「跑完才發現」的——全部是控制組、驗證器或外部覆核抓的。**

- **一個欄位有值 ≠ 那件事成功。** `closeMs: 10906` 被我讀成「文件關掉了」，實際是 close 逾時 10 秒後
  **重啟 worker**。同型的還有 runner 的 exit code（a3/a4/a5 跑得好好的也 exit 1）。
- **沒有控制組的 profile 差點送出假結論。** 第一輪讀起來是「三條執行緒在 `wasm-function[36295]` 空轉」，
  控制組一跑，那三條在卡死**之前**也是 100%。同一輪還把 V8 的 `(idle)` 偽框當樣本計，
  於是每條停等執行緒都被判成 spinning——**一個兩種答案都會通過的判準**。
- **一個沒做到事情的探針，看起來和「做了但沒事」一模一樣。** 部分選取設成 513 twips，
  兩列都回 `selectionType=none`＝拖曳太短根本沒選到；只看「有沒有卡」會讀成「部分選取安全」。
- **對照組會被污染而不自知。** 鍵盤那一輪的純段落對照擴選越出段落進到表格，
  它沒卡，但它證不了純段落安全。
- **我的成本表是自利的**（覆核點名）：把預防寫成「要重編、解綁 E2-A」，讓「少做」顯得被逼。
- **推論被寫成事實**（覆核點名）：「範圍選取正是觸發 038 的手勢」在補量之前是跨 artifact 推論。
  補量之後成立——**而且同一次補量推翻了我另一個說法**：「產品死前最後訊息是 completed」
  對診斷路徑成立、對出貨路徑不成立（出貨的 `selectRange` 回報 `TIMEOUT`）。
- **別在會改變狀態的指令後面加 `2>/dev/null`**；**別用會匹配到自己命令列的 `pkill -f`**
  （這一天犯兩次，把自己的背景工作殺掉）。

## 外包

- **codex**：機械性、驗收條件可機器檢查的步驟可以丟。**它的結論要自己跑變異控制覆核。**
- **fable**：判斷題。這一天它抓到我兩個錯（自利的成本表、推論當事實），
  並補上一個我四個選項裡都沒有的東西（語料內容軸清單）。**裁決全文在對話紀錄裡，
  重點已落進 SPEC-E1-C 9.1 與本檔「下一步」。**
