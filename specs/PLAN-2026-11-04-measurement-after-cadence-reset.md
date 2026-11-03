# 量測規劃（2026-11-04 重擬）：只為手測時段發布

擁有者 2026-11-04 採用 fable 的建議（A，一到六條），規則本體在 `CLAUDE.md`〈節奏：只為擁有者的手測時段發布〉。
這份是**照新規則重排的量測計畫**：哪些量測留著、哪些停掉、這一輪（宿主 0.2.56）怎麼走、下一輪起怎麼走。

## 1. 量測分三類，只有第一類按功能計

| 類別 | 什麼時候跑 | 例 | 留／停 |
| --- | --- | --- | --- |
| **功能量測**：新功能的第一次量測＋一個紅案 | 每個新功能一次，在 dev profile 上 | W 與 `W_RED`（v32／v4 上 0/26 開）；H8 與「在 0.2.55 上先紅」 | **留**。這一類一週內抓到 finding 180–184 和 ODT 寫進 .docx 那個缺陷 |
| **發布回歸**：沒改到的東西有沒有壞 | 每個**手測時段**一次，不是每個 generation | Writer 網（P5、P4、S1、Z、P1、F4、F3）、Calc 網（C、CU、cell、range、autosave、P2）、Files 52/52 | **留，但次數降**。一週只抓到一個真缺陷（Z10） |
| **儀式**：重讀已 commit 的證據、衍生工具、驗證的驗證 | 不跑 | V0′ 第三段以後、每版衍生七支發布腳本、凍結重讀（cohort `instrumentSources`、K live-bound set） | **停** |

計數鏈 K 不變：仍照擁有者 10-12／10-19 的裁示併批、排夜間；名義出貨版本停在 0.2.45。

## 2. 這一輪：宿主 0.2.56（開微軟文件）就是下一個手測時段的版本

v33／ods-editor-v5／第 89 代昨晚已凍結，所以這一輪照原路出貨，但用新工具、不衍生。

| # | 步驟 | 狀態（2026-11-04 03:20） |
| --- | --- | --- |
| 1 | KWallet 守衛退休（`f8865e28b`） | **完成**。見證：11-03 23:11 F3 的 Chrome 臂在沒有 secrets 服務時 46/46 |
| 2 | Writer 網重跑（`ms-formats/gen-89/rerun-01.sh`，P5、P4、S1、Z、P1、F4 兩瀏覽器） | **完成**（00:01–01:10）：五個 `*_HOLDS`、F4 24/24（`e1217cebb`） |
| 3 | 發布工具參數化：`wasm_sdk_probe/tools/host_release.py`＋`host-0.2.56/release-inputs.json`（`bab2e0857`） | **完成**。在 0.2.55 的封存上重現已 commit 的 `DELTA_HOLDS` |
| 4 | 宿主版本號 0.2.56（宿主 repo `6def1da`，只在候選 clone 裡改，線上工作副本維持 `main`） | **完成** |
| 5 | H8 在線上 0.2.55 先紅（`host_batch8.py --out host-0.2.56/h8-red-on-0255`） | **完成**：`action-docx`／`-xlsx`、`read-only-*` 紅，ODF 對照組過 |
| 6 | `host_release.py gate／package／delta／offline／install` | **完成**：閘門 28/28、引擎 `1b8dda1e`、`DELTA_HOLDS`、`PACKAGE_HOLDS`、`CANDIDATE_INSTALLED`（01:37） |
| 7 | 裝好之後：H8（新功能那一臂）、Files 52/52、`capture` | **完成**：H8 兩瀏覽器 18/18（Firefox 要改成人的打字速度，見 §5）、Files 52/52；`capture` 只紅在鎖表（見 §5） |
| 8 | 擁有者手測（十條，見交接） | 等擁有者 |

**這一輪不跑的**（0.2.55 跑過、新規則下不再跑）：`host_batch.py`、`host_layout.py`、`host_calc_theme.py`（T6）、
`host_batch6.py`，以及閘門裡前幾批的紅案（S1 在 v29 上紅、P1／P4／P5 的紅案、Z 突變、Z10、T6／layout 紅、G1–G3）。
那些是各自功能第一次量測的紅案，已 commit、不會變，再讀一次只證明 git 會動。
**如果這件事永遠沒做**：宿主版面若被這一輪的頁面改動弄壞，由擁有者手測第 1–6 條看到；這一輪頁面只多了儲存格式與另存新檔對話框，宿主模板沒動。〔推論〕

## 3. 下一輪起：兩個手測時段之間怎麼工作

1. **改動留在 dev profile**（`build/e2/editor-vNN/profile`、`build/ods/editor-vN/profile`），不凍 `dist/profiles/`、不切頁面指標、不打宿主包。
2. **每個功能**：第一次量測＋一個紅案，在 dev profile 上跑；判讀工具的 bug 由執行修，記一行，只重跑那一臂。
3. **時段到了**（擁有者指名）：一次凍結、一個 generation、一次發布回歸、一個宿主版本。
4. 要連結時照舊交給擁有者（全域規則不變）；連結攢成一次。

### 3.1 下一次凍結前要先做的工具瘦身（現在不做）

這三件只有在下一次凍結時才會被用到，所以**排在下一個時段之前**，不搶在現在：

| 項 | 做法 | 如果永遠沒做 |
| --- | --- | --- |
| 身分工具參數化 | 一支 `four_arms_identity.py` 讀 `generation-NN.json`，取代 `v8x_four_arms_identity.py` 每代一份 | 下一次凍結就要再衍生一份；違反〈節奏〉第 2 條，必須先做 |
| V0′ 只讀兩段 | 上一個 generation＋最後一次計數的 K，取代第 89 代的十二段 | 同上，必須先做 |
| worker 只衍生到 `build/` | 不再 commit `sdk/v*-worker.js` 副本（ms-formats 已經這樣做） | 下一個 profile 會多 1,900 行副本進 git |

## 4. 已退休的守衛與規矩

- **量測前要求 KWallet 解鎖**：`pre_run_checks()` 等四支工具只記錄、不拒絕；Chrome 全部帶 `--password-store=basic`（單元測試守著兩個啟動器）。
- **凍結重讀轉紅＝不能改工具**：改成「報告記下工具 sha＋argv；工具改了要重現一次已 commit 的判定」。`v21_shakedown_common.py`
  改動後，v23／v24 cohort 與 K 的 live-bound set 重讀會報它 moved，這是預期的。
- **§34.4**：交接只報「因審核而改的檢查數」。
- **交接**：一個 session 一份。

## 5. 這一輪發現、要記著的事

- **線上的 app 目錄就是宿主 repo 的工作副本**（host stack 把 `STACK_ROOT` 掛成 `/var/www/html`）。11-03 晚上工作副本被留在
  `host-0.2.56` 分支，線上因此跑了 0.2.56 的 PHP／JS 配 0.2.55 的引擎、版本號仍是 0.2.55。〔已觀察：容器內
  `EditorController.php` 有 `openxmlformats`〕00:20 切回 `main`。**工作副本不可以停在候選分支**；候選一律用
  `host_release.py candidate` 的 clone。
- **H8 在 Firefox 紅的那一格是 finding 130**（輸入佇列深 8），不是另存新檔：真的按鍵、兩個瀏覽器，8 鍵連發完整、10 鍵掉 2、14 鍵只留 8、每鍵 150 ms 完整（`host-0.2.56/diag-burst-01/`）。H8 的 Firefox 打字改成每鍵 150 ms。130 的佇列上限要不要調、按住一個鍵（約 33 ms／鍵）會不會掉，是下一個功能時段的候選，**現在不做**。〔已觀察〕
- `capture` 的鎖表多了 5 列已過期的 admin 鎖，時間都落在我的診斷工具執行期間，H8 五輪與 Files 實流程沒有留下任何一列；成因（工具在存檔途中離頁，或頁面某條路徑沒放鎖）未查。**如果永遠沒查**：鎖 ttl 300 秒，最壞是另一位使用者 5 分鐘內打不開那個檔。〔推論〕
- `tests/test_v21_shakedown_common.py` 的 `test_the_real_mirror_reproduces_the_round_identity` 在 HEAD 上本來就紅（釘的是舊一輪頁面身分），不是這輪造成的；沒修。

## 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-11-04 | 初版 |
| 2026-11-04 | 03:20 更新：§2 各步驟完成；§5 補 finding 130 與鎖表兩項 |
