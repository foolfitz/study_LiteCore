# 交接 — 2026-08-15（第四段）：E2-B 的 relink 做完了，G3 已修並在產品 artifact 上驗過

**接手先讀這一份 ＋ [`PLAN-E2-B-relink-and-freeze.md`](PLAN-E2-B-relink-and-freeze.md)。**
它接在 [`HANDOFF-2026-08-15c-session-state.md`](HANDOFF-2026-08-15c-session-state.md) 之後。

## 一句話

**規格第 5 節十四項全部定案（v11），P1 的 relink 做完了，P2 的核心接線做完並冒煙測過，
而 G3——那個「回報成功但只驗得了一半」的缺陷——已經在產品 artifact 上、兩個瀏覽器上驗證修好。**

## 現在的狀態

| | |
|---|---|
| **產品 v2 artifact** | **`572035ac…`**，profile `dist/profiles/e2-editor-v2/`，**還沒有任何判定綁上去** |
| 四顆凍結 artifact | `835b453d`／`679def61`／`c89f069e`／`940b7723` **全部逐位元未變**，每次連結後都核對 |
| SPEC-E2-B | **v11**，第 5 節十四項全部定案，第 7 節門檻已訂 |
| 上游 | **送出擱置**（使用者裁示），證據與草稿都留著 |
| demo | **重要性已降級**（使用者），不得拿來壓縮 P3 |

## 做完的

**P1（唯一一次 relink）全部十三項。** ABI 升 v2、五個動作、兩個新 C symbol
（`oxsdk_editor_abi_version`、`oxsdk_editor_set_action_gestures`）、B' 的路由本體、
產品建置變體（三個旗標、export 只有五個產品 symbol、掛 relink 守衛）、
逐 block 文字抽取、證據欄位、兩件欠著的 Makefile。

**P2 的核心。** v2 profile builder（會拒絕不合格的 artifact）、worker 的操作表取代字尾比對、
v2 的派送、`formatBarrier` 轉發、manifest 的動作交集、gesture mask 推送、editor ABI 比對、
以及 `editor-shell-v2/` 的 v2 client。

**冒煙測試通過**（`tools/run_e2b_smoke.py`，兩瀏覽器）：五個動作在收合游標上全部派送成功、
revision 每次 +1、`route`／`preBlocks` 一路傳到 client。

**wasm 一致性通過**——裁決最後一個翻案條件。`range-cross` 在兩瀏覽器上
`preBlocks 2`／`postBlocks 2`／identity 與 state 都成立。**G3 關掉了。**

## 還沒做的

| 階段 | 事情 |
|---|---|
| **P2** | `editor-shell-v2` 的 session（**B ＝ rollback 到 checkpoint**，5.13）、v2 的 `.d.ts`、negative matrix 的執行器、validator 的 `--self-test` |
| **P3** | 90 個正向 run ＋ 7.1 補的六格 ＋ negative matrix 十一列 ＋ no-op 方程式 ＋ forbidden-field ＋ A3／A4／A5 重掃 |
| **P4** | 凍結、`demo-structure` 遷移 |

## 動手之前必讀（本段新增的）

1. **`editor-shell/*.js` 是 hash 綁定的。** E1-C 的 bundle 把 `editor-client.js` 與
   `editor-session.js` 列在 `included`，改它們會解除 `E1_GO_ODT_EDITOR`；
   **在那個目錄底下新增檔案也會**（驗證要求未歸類的 module 為空）。
   v2 因此放在 `editor-shell-v2/`。`make test-e2-b-static` 每次都會用
   `tools/check_e1_c_bundle_intact.py` 檢查這件事（唯讀）。
2. **不要把 `validate_e1_c.py` 掛進靜態檢查**——它會把結果寫回
   `findings/evidence/`，等於語法檢查改動了被綁定的證據。我犯過一次，已還原。
3. **profile 內含的是 worker 的複本。** 改 `sdk/sdk-worker.js` 之後**一定要重建 profile**，
   否則跑的是舊的 worker。冒煙測試第一次跑就是死在這裡。
4. **改 Makefile 之後連結目標就算過期**，守衛會擋。現在擋得住的有五個目標
   （四顆凍結的 ＋ v2）。**Makefile 本身可以分次改**，要只做一次的是「跑 make 去連結」。
5. **`em++` 在 `/usr/bin`**，可以只編 object 不連結：
   `tools/`（scratchpad 裡的 `compile_engine.sh`）那條路一開始就抓到
   `probe_engine.cpp` 看不到 ABI 巨集。**改引擎務必先這樣編一次。**

## 本段我犯的錯

| | 抓到的方式 |
|---|---|
| 逐 block 抽取器沿用 parser 的 `index = bracket - 1`，把 `>` 留進文字裡 | **拿真實量到的 markup 當測試 case**，第一次跑十個 case 全紅 |
| 逐 block 狀態檢查只看第一個 tag——**正是 B' 要移除的那個缺陷** | 自己複查時發現，抽取器改成回傳 tag ＋ text |
| `setList` 同步 throw 而 `action()` 是 reject，`.catch()` 接不到 | 測試用呼叫端的用法呼叫，因此抓得到 |
| 把 `validate_e1_c.py` 掛進靜態檢查，跑一次就改動了綁定的證據 | 跑完看 `git status` |
| 冒煙測試用同一個 engine 開第二份文件 | 引擎自己回 `BUSY`（finding 038 的教訓本來就寫著要一臂一個 engine） |

**最值得記的**：`editor-shell/*.js` 的 hash 綁定是**計畫沒抓到的**，
而照原計畫寫「editor-client.js 加五個方法」會**靜默解除一個已出貨的判定**。
是實作到那一步、去查 bundle manifest 才發現的。
