# SPEC-M3-K-0.2.45：宿主 0.2.45 的計數鏈（K）

> 狀態：**釘死**（2026-11-02，任何計數執行之前；之後只准追加，CLAUDE.md 第 10 節）。
> 依據：`SPEC-M3-K-0.2.44`（協定與追加 1–3，本規格照抄，下面只列差異）；`SPEC-M3-v29-tick-pacing` §7、追加 7、追加 8；`SPEC-M3-own-stack`；finding 178。
> 擁有者 2026-11-02：C2 門檻選 A。

## 1. 要回答什麼

0.2.26 之後累積的引擎改動（v22–v29）、殼層改動（generation 75–83）、宿主改動（0.2.27–0.2.45）有沒有弄壞沒改到的東西。**成立**：名義出貨版從 0.2.26 前移到 0.2.45。**不成立**：名義出貨版留在 0.2.26，紅的格開 finding。

候選身分：宿主 `eeac22c`（0.2.45）、engine package `623f51d295ff6030`（`build/archive/host-0.2.45-engine-623f51d295ff6030`）、引擎 `e2-editor-v29`（wasm `e61e5890…`）、殼層 generation 83（`607b280d…`）、頁面 `022d0cd0…`、HTML `ca58f40f…`。

K 0.2.44 沒有跑過，所以這不是 K 的第二次，而是**同一份協定第一次真的跑**。

## 2. 對 `SPEC-M3-K-0.2.44` 的差異（封閉清單）

沒列到的照原文，包含裁決 8 項、§3 的格登錄、§4.1、§4.2、§6 的計數語意、追加 1 的 H1–H4、追加 2 的 merge 表與 K5。

| 項 | K 0.2.44 | K 0.2.45 | 為什麼 |
|---|---|---|---|
| 身分 | `3b0a2ebb`、v28、第 82 代、`dacdfa20`、`a97724f` | §1 的值 | 換值 |
| 釘選 | `repin_0244.py` 24 處 | `k-0.2.45/repin_0245.py`：同一套，**另加**兩個 `SHELL_MANIFEST` 與 `BOUNDARIES_COMMIT_MEDIAN` | 見 §3 |
| 工具名 | `run_k_0244_merge.py`、`judge_k_0244_merge.py`、`read_k_0244_merge.py`、`read_k_0244_product_path.py`、`check_v82_shift_enter.py` | 對應的 `0245`、`v83` 版，由 `k-0.2.45/derive_k_tools.py` 封閉清單衍生 | 舊檔屬於舊規格，不改 |
| keying | `k_0244_merge_keying.py` | **同一支，不改** | 裡面沒有身分 |
| P6 的具名紅 | `k-0.2.44/p6-named-reds.txt` | **同一份**；repin 後重讀，多一個少一個都停 | `k_static_target.py` 不動 |
| product-path | `run_v82_f3_clipboard.py` | `tools/run_k_0245_path.py`：`run_v83_f3_clipboard.py` 加兩個記憶體內替換（§4） | finding 178 |
| 母體 | F3-82 的 46 個 id | **不變** | F3-83 沒有移動任何格 |
| K6 門檻 | `boundaries` commit ≤ 10 ms | **≤ 16 ms**，上螢幕門檻不動 | 擁有者裁定（v29 追加 8） |
| 宿主 | ddev | 自有 stack，`host-stack/bin` 放 PATH 最前面 | `SPEC-M3-own-stack` ST1–ST4 成立 |
| 窗口 P5 | ddev 共用，不開站台、不起別的專案 | 只剩不開 **litecore** 站台：runner 會清整張鎖表。別的專案不受影響 | ST4 |
| C2 | 桌面只記錄 | 每輪前跑 `desk_gate.py --wait 300`，髒就**該輪不跑** | §5 |

## 3. 釘選（普查逼出來的）

`k-0.2.45/census_old_identity.py` 工具封閉地走過鏈與讀取腳本的 import closure（50 個檔），列出舊身分字面值與 `ddev` 呼叫形狀。

**抓到一個計數才走的路徑**：`check_m3_production_ui.py:97`、`check_m3_host_entry.py:89` 的 `SHELL_MANIFEST` 還是 v82，不在 K 0.2.44 的 repin 清單裡（那是追加 1 的 H3 加的，AST 清單只看名單上的符號）。不改的話 production UI 第一個計數步驟就拒跑（`shell.exit` 1），host_entry 也拒跑。shakedown 走不到，ST2 也沒抓到。

`ddev` 呼叫形狀：`mysql`、`occ`、`describe`、`exec`，全在介面卡範圍內。

## 4. product-path 的兩個替換

`tools/run_k_0245_path.py`，薄包裝，`run_e2_c_product_path.py`（`7ba30235…`）不改：

1. **單按**（finding 178）：拿掉 `format_arm` 的第一按。不拿掉 K7 在 v29 上會無故紅。紅案就是同一批位元組上的原工具（Firefox 4/4）。
2. **等 toast**（finding 178 的另一個競態）：兩個等「清除格式」標籤的地方改等 toast「已清除…」，標籤在四個步驟的第一步就滿足。v29 上自然發生率 2/120（Firefox）。

這兩個在各自的診斷裡分開跑過，**合在一起沒有跑過**，所以 §5 要先在鏡像跑一輪，46 格要等於 F3-82。

## 5. C2 的桌面閘門

K 0.2.44 的鏈只記錄桌面。但 C2 是計時格，紅了不能重跑（§6「不重跑到綠」），桌面髒時等於拿擁有者的桌面去賭 K6。所以每輪前跑 `desk_gate.py --wait 300`：乾淨才跑；髒就寫 `c2 rK REFUSED dirty desk`、該輪不跑，其餘步驟照走。依 J-b.2，少於三輪是 `NOT_ESTABLISHED`，不是紅；之後在乾淨桌面補跑沒跑過的輪，不算重跑。

`desk_gate` 只擋 C2，鏈的其他步驟不看它（`timing-runs-need-quiet-desk-and-idle-session`：閘門只用在計時格）。

## 6. 鏈前（agent 跑，鏡像或離線）

| 項 | 判準 | 證據 |
|---|---|---|
| 普查 | §3 列的項目全部處理完，重跑普查，程式碼行不再有舊身分 | `k-0.2.45/census.json` |
| 釘選 | `repin_0245.py` 每處恰好一次 | `k-0.2.45/repin-0.2.45.json` |
| 活的綁定集合 | 自 v24 計數以來沒有位元組改動，`--flip` 會紅 | `k-0.2.45/live-bound-set.json` |
| P6 | 紅集合等於具名集合 | 鏈的 preflight |
| 計數才走的路徑 | `check_counted_paths.py` 換值後全過，含 H1–H4 的紅案 | `k-0.2.45/counted-paths/` |
| T1 重判 | 新門檻下 `judge_p2` 三輪 PASS；把門檻改回 10 仍是原本的兩次 FAIL（紅案） | `k-0.2.45/t1-under-gate-16/` |
| 頁面把關負向臂 | `LEGACY_V8_CONTROL_REFUSED`，頁面 `022d0cd0` | `k-0.2.45/legacy-v8-gate/` |
| Enter 重播 | `V24_ENTER_HOLDS`，3 次 | `k-0.2.45/enter-replay/` |
| merge smoke | 逐格讀 `pass`，26/26 | `k-0.2.45/merge-smoke/` |
| K 路徑一輪 | 兩瀏覽器，46 格等於 F3-82 | `k-0.2.45/path-smoke/` |
| 讀取器紅案 | `read_k_0245_merge.py`、`read_k_0245_product_path.py` 的 self-test | `k-0.2.45/readers/` |
| 鏈 preflight | `--preflight-only` 只剩 P5（要擁有者的話） | `k-0.2.45/preflight-only.txt` |

## 7. 判定

K 成立＝`SPEC-M3-K-0.2.44` §6 的 K1–K8 全部，工具名換成 §2，K6 的 `boundaries` commit 讀 ≤ 16 ms。

任一不成立：**不改判準、不重跑到綠**。shakedown 的紅停在進計數之前；計數中的紅就是結果，開 finding、K 不成立。例外只有 §5：沒跑的輪不是紅。

## 8. 擁有者的窗口（P5）

約 8–10 小時。期間**不開 litecore 站台**：每支 M3 runner 會清整張鎖表，開著的工作階段會被弄壞。別的專案不受影響（ST4）。要擁有者的話才開跑；C2 要乾淨桌面，鏈開始前請關掉桌面 Chrome 與 zen，否則 C2 會被擋下、之後補跑。

手測與鏈不能同時：手測要先做完，手測發現問題就不開鏈。

## 9. 沒做的預設

K NOT RUN，名義出貨版留 0.2.26。

## 10. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-11-02 | 初版、釘死。 |
