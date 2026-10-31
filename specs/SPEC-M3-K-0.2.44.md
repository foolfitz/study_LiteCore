# SPEC-M3-K-0.2.44：宿主 0.2.44 的計數鏈（K）

> 狀態：**釘死**（2026-10-31，任何計數執行之前；之後只准追加，CLAUDE.md 第 10 節）。
> 依據：K 協定 fable 裁決「A 修改版」＋修正一（`findings/evidence/host-0.2.39/k-protocol-ruling/RULING.md`，規格 `SPEC-M3-link-batch-v24` §23）；格 7、9 的裁決（`findings/evidence/host-0.2.39/k-nine-cells/RULING-v25-fixes.md` Q3、Q4）；`DISPOSITIONS.md`；規格 v27 §8 第 6 項。
> 擁有者 2026-10-31：選 B（排計數鏈），接著「請執行A／然後可以跑B／但我不在座位，請自主執行／授權讓你跑編譯和連結」。

## 1. 要回答什麼

0.2.26 之後累積的引擎改動（v22–v28）與殼層改動（generation 75–82）、宿主改動（0.2.27–0.2.44），有沒有弄壞沒改到的東西。**成立**：名義出貨版從 0.2.26 前移到 0.2.44。**不成立**：名義出貨版留在 0.2.26，0.2.44 照舊是日常未計數候選，紅的格開 finding。

候選身分：宿主 `a97724f`（0.2.44）、engine package `dacdfa20fd4ff1ea`（`build/archive/host-0.2.44-engine-dacdfa20fd4ff1ea`）、引擎 `e2-editor-v28`（wasm `13f674e4…`）、殼層 generation 82（`a02673fa…`）、頁面 `3b0a2ebb…`。

## 2. 協定對到 0.2.44（裁決的 8 項）

v24 的裁決寫的是 v24、第 77 代、頁面 `b15a6d8e`。v24 沒有跑過 K，所以這裡是**同一份協定換值**，不是新協定。下表是全部差異；沒列到的照裁決原文。

| 裁決項 | v24 | 0.2.44 |
|---|---|---|
| 1 merge 負向臂 | 0.2.26 已提交的 v8 red 報告，以讀取綁定；runner `aaee0cda…`；v8 wasm `4a2710bb…` | 不變。`sha256(run_merge_wasm_shakedown.py) != aaee0cda…` 的預設：merge red NOT ESTABLISHED、K 不成立 |
| 2 舊缺行為訊號 | `judge_counted_m2.py --uncounted`，預期 exit 4、`red PASS`、`oneRunner true` | 不變，`--profile e2-editor-v28`，K 目錄放 v28 報告＋0.2.26 red 報告與 docs 的副本 |
| 3 計數身分讀取 | 新檔，自己的紅案 | `tools/read_k_0244_merge.py`：非 red 報告 `counted true`、`binding == proposedMergeBinding`（`findings/evidence/k-0.2.44/k-binding-inventory.json`）、`bound == binding` 九個鍵、runner `aaee0cda…`、stderr 空；red 報告 `binding == originalMergeBinding`、非 profile 鍵相等、wasm `4a2710bb…`。紅案：不帶覆寫的 run 是 `counted false`；翻一個雜湊 |
| 4 綁定覆寫 | 行程內 | `tools/run_k_0244_merge.py`：匯入前把 `build_e2_c_shell_bundle.MANIFEST` 換成 v82，再把 `run_merge_wasm_shakedown.BINDING` 換成 proposed binding，記錄 `{default, used, applied}`。`:176` 的 `BINDING` 不改；`judge_counted_m2.py` 不改 |
| 5 product-path | v24 plain 臂，v77 重綁 | `tools/run_v82_f3_clipboard.py`（v82 重綁＋finding 175 的剪貼簿讀取，spec v26 追加二的處方；只有這三處與 F3-82 同一支），3 輪 × 2 瀏覽器。讀取器 `tools/read_k_0244_product_path.py`。母體＝`v28-083/f3-82/run-01/{chrome,firefox}/report.json` 的 46 個 id，依序；被綁 runner `7ba30235…`。P1：每份報告恰好那些 id、依序，否則 STOP。P2：entrypoint `3b0a2ebb…`、沒有 `candidateCutover`、override `used` ＝ v82、檔案 sha `da4e595d…`。P3：錨點＝`release-0.2.26/product-path/e2-editor-v21-{chrome,firefox}-r{1,2,3}.json`，舊 `verdict()` 不改。v8 列只進 P4（描述） |
| 6 頁面把關負向臂 | K 目錄重跑 `probe-legacy-v8-gate.py` | `findings/evidence/k-0.2.44/probe-legacy-v8-gate.py`（host-0.2.39 那支的衍生，鎖名與路徑）：control PASS、legacy-v8 `EXPECTED_REFUSAL`、`insertRequests 0`、頁面 `3b0a2ebb…`、v8 wasm `4a2710bb…`。鏡像、不用 DDEV，放在鏈的 preflight 之前 |
| 7 釘選 | 23 個 `frozenBy: []` 一支 repin 一次 commit | `findings/evidence/k-0.2.44/repin_0244.py`：清單工具列的 22 個字串釘選（第 23 列是 autosave self-test 的 `PAGE_SHA256 = None`，不是釘選）＋ AST 清單抓不到的 `judge_c2.py`、`judge_p2.py` 的 `PAGE`（0.2.26 的 repin 有列）。舊值留在註解。P4 期望 `3b0a2ebb…`：dist、web、0.2.44 封存、宿主送出 |
| 8 計數語意 | 第一次乾淨的 K 之後不加判準 | 不變。第 2–6 節任一沒做＝K NOT RUN，名義版留 0.2.26。沒紅過的讀取器不算證據 |

## 3. product-path 的特別讀法

**格的登錄**（`DISPOSITIONS.md` 的列；K 讀取器逐列寫死，不從 dispositions 檔解析）：

| 列 | 瀏覽器 | 格 | K 的讀法 |
|---|---|---|---|
| 1、2 | chrome、firefox | `bulleting-a-blank-line-does-not-demand-a-rollback` | **退役，不以 P3 判**（規格 v27 §8 第 1、6 項）。該格斷言 046 的提示存在，v27 起那個提示依設計不見了。K 讀取器只驗 FAIL 的形狀是 v27 的：`observed.state == "ready"`、`observed.toast == ""`、`unverifiedSentence is None`，每輪。接手的是 S3、S4（已成立，不重跑），不是這一格 |
| 3–6 | | inline 格式四格 | P3 照舊（v21 PASS 3/3 ⇒ PASS 3/3）。v25 修好，F3-82 都 PASS |
| 7 | chrome | `a-boundary-arrow-press-does-not-cost-the-work` | I-worker-inducer-single-shot（Q3）：B1–B3 每輪 true **且**誘發器紀錄恰好是單發形狀（`fired:false`、那句 `why`、`attachedTypes:[]`）→ 格 PASS；其他 FAIL ＝ 產品紅。三輪都要符合 |
| 8 | chrome | `the-enter-key-reaches-the-document` | I-enter-raw-substring（v24 §17.3）：Enter 臂 PASS、Shift 臂 `together true`、`lineBreaksBetween false`（＝原始子字串看不到斷行的形狀）**且** `check_v24_shift_enter.py` 在 v28 上 `V24_ENTER_HOLDS`（鏡像、3 次，§5）。其他 FAIL ＝ 產品紅 |
| 9 | chrome、firefox | `editing-a-long-document-stays-responsive` | Q4：N ＝ K 的三輪。三臂 `seconds <= 1.0` 且 `revisionAdvanced` ⇒ PASS；恰一臂 `seconds < 0.08` 且 `revisionAdvanced false`、另兩臂過 ⇒ I-ink-trigger-race，每瀏覽器最多一次；其他 FAIL 或兩次 ⇒ 產品紅；缺格 ⇒ STOP |

`v23-product-*` 四格在 0.2.26 沒有列：要 PASS 3/3。`recovery-returns-what-the-product-promised` 帶 row 1′（窗口從 git 追蹤的 v8 報告算，同舊 `verdict()`）。

**`recoveryPairing` 不判**（規格 v27 §8 第 3 項：哨兵跟 bulleting 一起退役）；K 讀取器要求它是 `held false`、`ok false`、verdict 以 `the recovery pair disagrees` 開頭，與 F3-81／F3-82 相同。

**紅案（K 之前）**：翻一格 v21 3/3 的 ⇒ RED；新 id 不是 3/3 ⇒ RED；0.2.26 目錄餵進來當 K ⇒ STOP（42 ≠ 46）；row 7、8、9 的反例（別的 FAIL 形狀）⇒ RED；row 9 的兩個紅案（`seconds 0.5`＋`revisionAdvanced false`；兩次簽名）；row 1、2 的 FAIL 換成 rollback 形狀 ⇒ RED。

## 4. 鏈

`findings/evidence/m3-production-ui/runs-0.2.44/chain-0.2.44.sh`，由 `chain-0.2.26.sh` 衍生，差異是封閉清單：

1. 身分：`PAGE`、`ARCHIVE`、`R` ＝ `findings/evidence/release-0.2.44`、`E` ＝ `runs-0.2.44`、候選 `e2-editor-v28`。
2. product-path：只有 plain 臂（沒有 v8 臂，裁決第 5 項），三輪兩瀏覽器，走 `run_v82_f3_clipboard.py`。
3. merge：走 `run_k_0244_merge.py`；**沒有 `red-*` 步**（裁決第 1 項：讀 0.2.26 的 red，不重跑）；鏈結束後由 read 腳本把 red 報告複製進 K 目錄。
4. P0 另查 `$PP`；P6 改成 `make -i test-e2-c-static`，紅的集合要**恰好等於**具名的既有紅（§4.1），多一個或少一個都拒絕。P6 的兩個 unittest 照舊。
5. `OURS` 加 `run_v8|run_k_|read_k_`（只會多拒絕）。
6. 其他步驟、STOP 規則、desk 行不變；shakedown 不乾淨就 STOP，不進計數。

### 4.1 P6 的具名既有紅（2026-10-31 重讀）

`make -i test-e2-c-static` 的紅項自 v27／v28 起都已具名，鏈前重跑一次、把實際集合寫進 `findings/evidence/k-0.2.44/p6-named-reds.txt`；它們都是「工具預設綁舊 generation」或文字漂移，不是產品：

- `U2 wiring: the handler takes Ctrl+A …`（L-select-all-u2-pins-v26-profile）
- `test_the_real_manifest_matches_the_real_tree`、`test_every_mutation_matches_its_target_exactly_once`、`test_the_inducing_arms_hold_the_guard_off`（v27 pre-link 具名的三個）
- `tools/check_relink_queue.py` 與 `--self-test`（L-relink-queue-drift-v26-v27）

### 4.2 V0″

v24 §17 第 1 項要求 K 前 V0″ `V0PP_HOLDS`。它還原的是 v24 計數的殼層，put-back 比對 v24 切頁的位元組。V0′-82（`v28-083/v0/`，`V0_PRIME_HOLDS`）已在第 82 代上重讀 v24 的 selection cohort 與 A4，以及 79–81 的讀法，涵蓋它要守的事（活的綁定集合沒被動到）。**K 前再跑一次 V0′-82 的等價檢查**：`git diff` 確認活的綁定集合 40 路徑自 v24 計數以來沒有位元組改動（工具算，`findings/evidence/k-0.2.44/live-bound-set.json`）；repin 不得碰到任何一個（`frozenBy` 不是空的那一個是 `BINDING`，不改）。

## 5. 鏈前在鏡像上跑的

1. `probe-legacy-v8-gate.py`（§2 第 6 項）。
2. `check_v24_shift_enter.py`（§3 第 8 列），3 次。
3. 讀取器的紅案（§2 第 3 項、§3）。

## 6. 判定

K 成立＝以下全部：

- K1：鏈有 `DONE`，`IDENTITY-START` 與 `IDENTITY-END` 相同，P0–P6 ok。
- K2：production UI 計數兩份 exit 0；紅案 `28/28`、13 個 `no passing B3x run`（B3x 照舊撤回）。
- K3：六支 runner 計數都著陸；各自的 `--red-cases` exit 0。
- K4：autosave、new-document 計數著陸；紅案 exit 0。
- K5：`read_k_0244_merge.py` 成立；`judge_counted_m2.py --uncounted --profile e2-editor-v28` exit 4、`red PASS`、`oneRunner true`。
- K6：C2 三輪照 J-b.2 的表（「只有 chrome owner-gap80 on-screen max 紅且 < 200 ms」歸 135）。
- K7：`read_k_0244_product_path.py` `K_PATH_HOLDS`。
- K8：頁面把關負向臂、Enter 重播成立。

任一不成立：**不改判準、不重跑到綠**。shakedown 的紅停在進計數之前，查清是產品還是儀器；儀器紅（runner 綁舊頁面的斷言）照 §34 先做紅案與證人再修。計數中的紅就是結果：開 finding、K 不成立。

## 7. 擁有者的窗口（P5）

擁有者不在座位、授權跑 B。`--owner-window` 引述原話；窗口從鏈 START 到 DONE（約 8–10 小時）。litecore 由 agent `ddev start`（重開機後是 paused）。鎖表要是空的（P5）。**鏈不佔別的專案，但 ddev 共用**：這段時間不開 litecore 站台、不 `ddev start` 別的專案。

## 8. 沒做的預設

K NOT RUN，名義出貨版留 0.2.26。

## 9. §34.4

本規格是既有協定換值，沒有新裁決，也沒有審核輪。修正登錄在交接。

## 10. 修訂紀錄

| 日期 | 修改 |
|---|---|
| 2026-10-31 | 初版、釘死。 |
