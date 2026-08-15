# 交接 — 2026-08-15（第五段）：E2-B 判了 `GO_TO_E2_C`

**接手先讀這一份**，它取代同日的
[`HANDOFF-2026-08-15d-e2b-relink.md`](HANDOFF-2026-08-15d-e2b-relink.md)
（內容已併入）與
[`PLAN-E2-B-relink-and-freeze.md`](PLAN-E2-B-relink-and-freeze.md)（已執行完）。

## 一句話

**E2-B 從「十四項協定問題全部未解」走到 `GO_TO_E2_C`：產品 v2 artifact 存在、
G3 那個「回報成功卻只驗得了一半」的缺陷已修並在兩個瀏覽器上驗過、
132 個正向 run ＋ 12 列 negative matrix ＋ no-op 方程式全部達標，
判定由工具從證據重推而不是寫下來的。**

## 狀態

| | |
|---|---|
| **E2-B** | **`GO_TO_E2_C`**，artifact **`572035ac…`**（profile `e2-editor-v2`），contract v2／15 動作／跨段 `verify-every-block` |
| 規格 | **SPEC-E2-B v12**，第 5 節十四項全部定案 |
| E2-A | `PARTIAL_GO_TO_E2_B` **不變**，仍綁 `c89f069e`（`summary.json` 重跑逐位元不變） |
| E1-C | `E1_GO_ODT_EDITOR` **不變**，shell bundle `f9b1a52f` 完好 |
| 四顆凍結 artifact | 全程逐位元未變，每次連結後核對 |
| 上游 | **擱置**（使用者裁示） |
| demo | **已降級**，不得拿來壓縮量測；`demo-structure` 已遷到 v2，舊的改名保留 |

## 證據在哪

- `findings/evidence/sdk-e2/e2-b-summary.json` — 判定，由 `tools/validate_e2_b.py` 產生
- `.../discovery/e2b-matrix/` — 132 個正向 run ＋ 預測 ＋ README
- `.../discovery/e2b-negative/` — 12 列 negative matrix
- `.../discovery/e2b-crossparagraph/` — 原生五輪 ＋ wasm 一致性 ＋ 六份預測
- `.../discovery/e2b-gate/`、`e2b-gate-round2/` — 第 3 節閘門兩輪

## 下一步（沒有一項在擋路）

1. **這個 GO 明確不含四件事**（規格 9.11）：`set-list-ordered` 打在「兩段都已
   編號」的跨段範圍、H2–H6、實體指標拖曳、**標題的大綱參與**
   （`.uno:StyleApply` 套的是樣式，匯出仍是 `<text:p>` 沒有 `outline-level`）。
   要收哪一格就各自開一輪。
2. **E2-C**：規格還沒寫。
3. 上游的 040／043 等使用者解除擱置。

## 動手之前必讀

1. **版本是身分。** 別做「能用旗標從 v1 變 v2」的東西——builder、檔案、
   版本號都一樣。這條在本段被違反三次的代價都是同一個：沒有人說得清楚
   那個東西是哪一版。
2. **`editor-shell/*.js` 是 hash 綁定的**，改它或**在它旁邊加檔案**都會解除
   `E1_GO_ODT_EDITOR`。v2 因此在 `editor-shell-v2/`。
   `make test-e2-b-static` 每次都會查（唯讀）。
3. **靜態檢查不得改動被綁定的證據。** 我把 `validate_e1_c.py` 掛進 static
   跑一次就改寫了兩個證據檔，已還原並換成唯讀的 `check_e1_c_bundle_intact.py`。
4. **profile 內含 worker 的複本**：改 `sdk/sdk-worker.js` 之後一定要重建 profile。
5. **`em++` 在 `/usr/bin`，可以只編 object 不連結**——改引擎務必先那樣編一次。
6. **改 Makefile 之後連結目標就算過期**，五個目標有守衛（四顆凍結的 ＋ v2）。
   Makefile 可以分次改，要只做一次的是「跑 make 去連結」。

## 本段我犯的錯

| | 怎麼抓到的 |
|---|---|
| 逐 block 抽取器把 `>` 留進文字裡 | **拿真實量到的 markup 當 test case**，十個 case 全紅 |
| 逐 block 狀態檢查只看第一個 tag——**正是 B' 要移除的缺陷** | 自己複查 |
| `setList` 同步 throw 而 `action()` 是 reject | 測試用**呼叫端的用法**呼叫 |
| 把 `validate_e1_c.py` 掛進靜態檢查，改動了綁定證據 | 跑完看 `git status` |
| 判定器用 ODF 元素名猜 heading | **E2-A 10.2 三個月前就量過並更正過同一個猜測**——我沒讀自己的樹 |
| 在每一臂內部掃描錨點，掃的是那一臂要量的文件 | 跨行那臂只讀回第一條視覺行；閘門早就寫過不能這樣 |
| 綁定跑啟動時 harness 還沒把 `selfRed` 傳給判定器 | Chrome 跑完才發現，**那半丟掉重跑** |
| demo 少複製一個模組，頁面停在「啟動中」而且沒有錯誤 | **實際載入跑過**，不是只做語法檢查 |
| `pkill -f` 的樣式打到自己的 shell | 指令回 144 |

> **最值得記的**：那個 heading 判準。E2-A 的 10.2 節寫著「期望值錯，不是產品錯」，
> 而我在三個月後對同一件事做了同一個猜測。**新開一輪之前先讀自己的樹**
> ——這是 memory 裡已經有的那條，它今天又救了一次，只是慢了一步。
