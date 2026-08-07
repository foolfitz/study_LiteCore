# 交接：finding 023 —— 同一分頁反覆開檔到固定深度後，SDK init 永久卡住

> **【已結案，2026-08-07 下午】** 牆的機制是**探針基礎設施自己的 pipe 阻塞**
> （runner `Popen(serve.py, stderr=PIPE)` 從不讀取，請求 log 塞滿 64 KiB 後
> HTTP handler 卡在 `anon_pipe_write`，之後所有 fetch 永不回應）。已修、已驗證
> （full 45/45＋30/30、minimal 120/120，牆全部消失）、位元組對帳吻合。
> 本檔 §2「為什麼值得修」的產品影響推論**已撤回**；§1 末句「剩下只有引擎那層」
> **已否證**（`minimal` rung 零 LibreOffice 程式碼也撞牆）。完整第二次歸因見
> [finding 023（第二版）](findings/023-sdk-init-wedges-at-fixed-session-depth.md)；
> 過程見 [DEVLOG](DEVLOG-2026-08-06-wasm-sdk-e2-mainloop.md) 最末節。過程中挖出
> 兩個真的 Firefox 側問題（與 pipe 無關），見
> [finding 024](findings/024-firefox-lazy-reclaim-of-navigated-away-engine-workers.md)。
> 以下原文保留為「當時相信什麼」的紀錄。

> **給接手的人**：這份是進入點。全部背景在
> [finding 023](findings/023-sdk-init-wedges-at-fixed-session-depth.md)，
> 過程與踩過的坑在
> [DEVLOG 2026-08-06](DEVLOG-2026-08-06-wasm-sdk-e2-mainloop.md) 最後兩節。
> 本檔的每一句都標了**已觀察／推論／待驗證**，請維持這個習慣。

## 1. 一句話

**在同一個瀏覽器分頁裡反覆載入引擎，到某個固定次數之後，`init` 再也不會完成 ——
worker 起得來、一個 SDK 事件都沒有、120 秒逾時，之後該 session 不會恢復。判別階梯已把
瀏覽器、driver、worker 汰換、共享記憶體全部排除；剩下的只有「載入並初始化 LibreOffice
WASM 模組」這一層，還沒有再切開。**（已觀察；最後一句的「剩下」是推論）

## 2. 為什麼值得修

- **擋住 E1-C。** 產品驗收的四個自動相位跑在單一 session 裡，跑不完 → 拿不到
  `E1_GO_ODT_EDITOR`。現行裁決 `E1_STOP_OR_RESCOPE`。
- **這不是 harness 的毛病。** lifecycle 相位存在的理由，正是要證明「反覆開檔、存檔、
  關檔」有界。真實使用者開著分頁工作一天會踩到同一件事：**開到第二十幾份之後再也開不
  起來，沒有錯誤訊息，只有一個永遠不回來的 init。**（推論，但機制相同）
- 所以**不要**用「每 N 次換一個瀏覽器 session」把它繞掉。那會讓驗收永遠測不到產品真正
  的處境。若最後真的要加這種策略，必須在矩陣裡明寫它掩蓋了什麼。

## 3. 現象（已觀察）

```
SdkTimeoutError: init timed out after 120000 ms
workers: { created: 1, terminated: 0 }
operations: []
```

Chrome 有時更低一層就死：driver 的 `Page.navigate` 等 180 秒等不到
`document.readyState === 'complete'`。

**深度是固定的，而且形狀是懸崖不是斜坡：**

| 執行 | 每格工作量 | Firefox | Chrome |
|---|---|---|---|
| 正式矩陣 2026-08-06 | 重（含 100 頁壓力檔、崩潰情境） | 22 | 30 |
| 正式矩陣 2026-08-07 | 同上 | **22** | **30** |
| 探針 2026-08-07 第一輪 | 輕（重複最便宜的一格） | 26 | 34 |
| 探針 2026-08-07 第二輪 | 同上 | — | **34** |

失敗前**完全沒有劣化**：Firefox 前 25 輪每輪 2.26 秒（±0.01），Chrome 前 33 輪每輪
1.22 秒；行程樹記憶體同樣平坦（Chrome 穩定 1.5～1.6 GB，主機 30 GiB 只用 8 GiB），
`processCount` 全程不變（Firefox 12、Chrome 11）。下一輪直接掉到逾時。

**同一種工作量 → 同一個深度，逐次重現；換工作量 → 深度移動，且比較重的工作比較早撞牆。**
這是確定性的累積預算，不是抖動。

## 4. 已排除，不要重做

判別階梯：同一個 `serve.py`、同樣的 COOP/COEP、同樣的 navigate 迴圈，只抽換頁面內容。

| rung | 每次導覽做的事 | 結果 | 因此排除 |
|---|---|---|---|
| `inert` | 只設 driver 在等的兩個 global | 兩瀏覽器 **60/60** | 瀏覽器與 WebDriver 的分頁汰換 |
| `worker` | 建一個 module worker、答一句、終止 | **60/60** | worker 建立／終止的汰換 |
| `buffer` | 同上 ＋ 256 MiB `SharedArrayBuffer` | **60/60** | 隔離共享記憶體的配置／釋放 |
| `pool` | **8 個 worker 共用 1 GiB SAB，每個都寫入** | **60/60** | 「worker 太多」「共享記憶體太大」 |
| `full` | 真正的 E1-C 頁面 | **26／34 死** | —— |

60 遠超過四道牆（22／26／30／34）。cross-origin isolation 在五個 rung 都成立。

`pool` 那格的參數不是隨便挑的：引擎連結參數是
`-sPTHREAD_POOL_SIZE=7 -sTOTAL_MEMORY=1GB`（`wasm_sdk_probe/Makefile:463-465`），
所以一次導覽實際是 **1 個 SDK worker ＋ 7 個 pthread pool worker 共用 1 GiB**。
控制組必須長成這樣才有意義。

**另外，主機負載已被排除**：探針跑的時候主機是閒的，而且每輪跑的是完全相同的一格。

## 5. 已撤回的說法（別再引用）

- ~~「heavy host load from concurrent WASM linking」~~ —— 矩陣 `rerunAfterRefreeze.flakes`
  的原文保留為「當時相信什麼」的紀錄，旁邊有 `flakesAttributionWithdrawn`。
- ~~「單獨重跑 lifecycle 相位就全過，所以沒事」~~ —— 重跑確實會過，**但那是繞過去**：
  lifecycle 單跑是 10 warmup ＋ 10 cycle ＝ **20 次導覽**，低於每一道牆，從未靠近限制。
  這句話是症狀，不是佐證。
- ~~「不是固定次數」~~ —— 我第一輪這樣寫，是因為預測 22／30 而實測 26／34。重跑 Chrome
  又是 34，正確說法是**同一種工作量下固定**。

## 6. 相關程式路徑

init 的呼叫鏈（`wasm_sdk_probe/sdk/sdk-worker.js`）：

```
handleInit()                       :685
  → loadManifest()
  → ensureModule()                 :342   importScripts(probe.js)
                                          → createProbeModule({...})   ← wasm 實例化 ＋ pthread pool
  → loadStartupResourcePacks()
  → ccall("oxsdk_abi_version")
  → callStatus("oxsdk_engine_start", ...)                              ← engine 執行緒啟動
```

失敗時 `operations: []` 且沒有任何回應，所以**卡點在 `ensureModule()` 或
`oxsdk_engine_start` 之間**，還沒有切開。（推論）

其他：

- 連結參數：`wasm_sdk_probe/Makefile:460-475`（`define link_r5_product`）
- engine 側：`wasm_sdk_probe/src/probe_engine.cpp`
- 出貨 profile：`wasm_sdk_probe/dist/profiles/e1-editor-v1/`
  （wasm `835b453d…`、loader `1fe83aed…`、worker `e4f37ffe…`）

## 7. 下一步（按成本排序，都未執行）

1. **切開「載入大 wasm」與「LibreOffice 初始化」** ——（最重要）用一個**不連結 core**的
   最小 wasm 模組，用同一組連結參數（`-pthread -sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7`）
   建出來，跑同一個階梯。若它也在 26／34 卡住 → 問題在 emscripten 執行期或分頁的
   wasm 配額，跟 LibreOffice 無關；若它撐過 60 → 問題在 LibreOffice 初始化本身。
   成本：一個新的小 profile ＋ 一個新 rung。**這是我原本要做而停下來的那一步。**
2. **看卡在哪裡** —— 失敗那輪 worker 活著但零事件。需要在 worker 內側取診斷。
   ⚠️ 已知陷阱：**engine pthread 的 stderr 到不了可捕捉的 console**，診斷要走
   `MAIN_THREAD_EM_ASM`（finding 021 已經踩過這個坑）。`sdk-worker.js` 的
   `print`／`printErr` 只有在 `debug: true` 時才轉成 `diagnostic` 事件。
3. **量分頁內的執行緒與記憶體映射** —— `processCount` 全程不變，所以沒有行程洩漏；
   要看的是分頁內的 thread 數與 wasm 記憶體映射，不是行程數。
4. **確認是否只發生在「同一分頁反覆導覽」** —— 若改成每次開新分頁（同一瀏覽器 session）
   就不會卡，那指向分頁層級的資源不釋放。這一格很便宜，可以先做。

## 8. 這個 repo 的規矩（會影響你怎麼做實驗）

- **`libreoffice-26-8` worktree 不可 reset**，裡面有六個既存修改（`git status` 應該恰好是
  那六筆，`validate_e1_c.py` 的 `CORE_BASELINE_STATUS` 會檢查）。patch 快照在
  `wasm-lite/patches/INVENTORY.md`。
- **需要 sudo 的指令交給使用者跑**，不要用 `!` 前綴（那個 shell 沒有 TTY 會直接失敗）。
- **不得放寬 fail-closed**；**不得把 unit-test pump 掛鉤帶進任何產品 profile**
  （`unit_lok_process_events_to_idle` 是 unit-test 掛鉤；但它包的
  `Scheduler::ProcessEventsToIdle()` 本身是公開 API —— 見 finding 021）。
- **猜出來的常數會把自己的錯誤偽裝成上游的 bug。**
- **文件用 zh-TW 全形標點**（程式碼區塊維持半形）；**原地修訂＋補修訂紀錄**，不要新開
  檔案覆蓋舊結論。
- **每個前提標成已觀察／推論／待驗證。**

## 9. 探針紀律（這次踩到兩次，寫下來）

- **能印出不同值才算探針。** `run_e1_c_session_depth.py` 每輪印 elapsed 秒數與行程樹
  位元組，就是為了能看出「斜坡」還是「懸崖」——只回 pass/fail 的話這個 finding 到現在
  還會是「偶發」。
- **無法證明自己做了那件事的對照組，不是對照組。** `buffer` rung 原本只記 operations 的
  **數量**，看不出 `SharedArrayBuffer` 到底配置了沒；若參數沒傳對它會靜靜退化成 `worker`
  而我會拿它當證據。補了 `lastOperation` 實測 `bufferBytes: 268435456` 才算數。
- **探針不做判定。** `result.json` 刻意沒有 `pass` 欄位，只有 `observation`。跑乾淨與
  死在第 26 輪都是有用的量測結果，不是「探針失敗」。
- **不留下量測序列就死掉的探針，等於毀掉它存在的理由。** 第一版 Chrome 那輪因為 navigate
  例外直接往上拋，`result.json` 根本沒寫成；已修成把 driver 層失敗也記成一筆證據。

## 10. 檔案與指令

```bash
cd wasm_sdk_probe
make e1-c-session-depth-control-assets      # 刻意不相依任何 profile

# 重現卡死（Firefox 約 26、Chrome 約 34）
python3 tools/run_e1_c_session_depth.py --browser firefox --rung full --iterations 40

# 對照組（都應該 60/60）
python3 tools/run_e1_c_session_depth.py --browser firefox --rung inert  --iterations 60
python3 tools/run_e1_c_session_depth.py --browser firefox --rung worker --iterations 60
python3 tools/run_e1_c_session_depth.py --browser firefox --rung buffer --iterations 60
python3 tools/run_e1_c_session_depth.py --browser firefox --rung pool --buffer-mib 1024 --iterations 60
```

| 檔案 | 作用 |
|---|---|
| `wasm_sdk_probe/tools/run_e1_c_session_depth.py` | 探針；`RUNGS` 是階梯定義，加新 rung 從這裡 |
| `wasm_sdk_probe/web/e1-c-session-depth-control.html` | 對照頁；`?mode=inert\|worker\|buffer\|pool` |
| `wasm_sdk_probe/web/e1-c-session-depth-control-app.js` | 對照頁邏輯 |
| `wasm_sdk_probe/web/e1-c-session-depth-worker.js` | 對照 worker |
| `findings/evidence/sdk-e1/editor-validation/session-depth/<rung>/<browser>/result.json` | 每輪的 elapsed 秒數與行程樹位元組 |
| `wasm_sdk_probe/tools/run_e1_c.py` | 正式矩陣執行器（`session_class("cold")` 只建一次，`:405`；四個相位共用它） |
| `wasm_sdk_probe/tools/validate_e1_c.py` | 裁決；`artifact_binding()` 是 2026-08-07 新增的綁定閘門 |
| `wasm_sdk_probe/e1/validation-matrix-v1.json` | 凍結矩陣；`execution` 區塊是歷次執行紀錄 |

## 11. 一件跟 023 無關但你會撞到的事

E1-C 的證據**同時**還有另一個問題：2026-08-07 的兩次重連結（E1-D 範圍選取、底線／刪除線）
讓全部 48 個瀏覽器 case 與人工輪都綁在舊 artifact 上。`validate_e1_c.py` 現在會查
（`artifactBinding`），所以就算 023 修好，還是要**重跑全部相位＋雙瀏覽器各一輪人工
Chewing**，全部對 `835b453d…`。人工輪需要 `ssh -L 8765:127.0.0.1:8765`（頁面 gate 在
`crossOriginIsolated` 且用真的 `navigator.clipboard`，改 bind 到 LAN 位址會讓案例直接死掉）。

詳見 [SPEC E1-C §11.4／§11.5](specs/SPEC-E1-C-editor-validation.md)。
