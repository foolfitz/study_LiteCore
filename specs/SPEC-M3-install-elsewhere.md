# SPEC M3：從發佈壓縮檔裝進另一台 Nextcloud

2026-09-29 起草。擁有者同日選了「B＋E」（交接 `HANDOFF-2026-09-29-asset-delivery-lands.md` 的選項），實例＝
**`litecoreprobe` 原樣加裝**（不重裝、不建新 ddev 專案）。之後擁有者離座，授權 fable 代為裁決；本檔寫成時沒有
需要裁決的岔路。

## 1. 為什麼要有

路線圖 §5.5 的 M3 完成判準：**在一台乾淨的 Nextcloud 上**，從 Files 點開一份 ODT → 編輯 → 存回 → 版本正確 → 鎖正確，
**且整個流程沒有任何伺服器端文件行程**。

到今天為止（已觀察）：

- M3 的每一個計數執行（骨架、宿主入口、鎖與權限、版本、資產派送）都跑在 `litecore` 這一台開發實例上，而那裡的 app 是
  宿主 repo 的**工作樹**，被 `nc-link` 逐項 symlink 進 `apps-extra/litecore/`。**發佈壓縮檔從來沒有被裝過**——資產派送
  K4 只量了它的大小（60.5 MiB），壓縮檔本身沒有留。
- 「沒有任何伺服器端文件行程」**從來沒有被量過**。它是架構上的推論（app 只有 PHP，而 PHP 只送檔案），不是觀察。
- 宿主入口的計數 runner 在任何會上鎖的宿主上都跑不起來（資產派送 K3）：它不離頁就關瀏覽器，自己拿的 token 鎖留到約
  306 秒後才失效，下一臂重設檔案時吃 423。**一支跑不起來的計數 runner 是回歸網上的洞。**

這一步把三件事一起結掉：B（裝進另一台，並在那一台上重跑 M3 的流程）、§5.5 那半句沒量過的話、E（宿主入口 runner）。

**如果這件事永遠沒做**：M3 完成判準只在開發實例上成立；「app 帶著自己的引擎、換一台照樣裝得起來」只是資產派送 §5
「明確不承諾」裡的一句話；「沒有伺服器端文件行程」停在推論；宿主入口的 H3（衝突後不重載、第二次按也不覆寫）在會上鎖
的宿主上沒有人量。

## 2. 實例，以及它不乾淨的地方（已觀察，2026-09-29）

`litecoreprobe`（`~/Projects/Nextcloud_Apps/litecoreprobe`，`https://litecoreprobe.ddev.site:8443`）：Nextcloud 34.0.2
正式版 tarball、apache-fpm、PHP 8.4、MariaDB 11.4，只有 `admin` 一個使用者（重裝時記進 `install.json` 的 `users`）；`files_lock` 34.0.1、`files_versions`
1.27.0 啟用；可寫的 app 路徑只有一個：`apps_paths[1]`＝`/var/www/html/nextcloud/apps-extra`。

它**不是**全新安裝，差在四處。每一處寫明由什麼擋住它影響判定：

| 差異 | 會怎麼干擾 | 擋住它的 |
| --- | --- | --- |
| 閘門 0 的探針 app `litecoreprobe` 0.1.0 啟用中 | 它在 Files 頁上的三個 listener 能加 COOP／COEP 標頭；（審核後補）它還有一條**不受開關控制**的路由 `/r/{mode}/{path}`（`ProbeController.php:138`），送整個 `dist/`，其中也有一個以 `/e2-editor.html` 結尾的頁面，而 runner 判「落在編輯路由」只看後綴 | 三個 listener 都在 `files_probe` 不是 `on` 時直接 return（`lib/Listener/*.php`）；現值 `off`／`files_isolation` `off`。I1-4 在前後各讀一次。路由那一半由 I2-4 擋：窗內 litecoreprobe 的 access log 沒有任何打到探針 app 路徑的請求 |
| 唯讀 bind mount `/mnt/litecore-dist`（study_LiteCore 的 `dist/`，給探針 app 用） | app 若讀到它，「只讀自己帶的檔」就假過 | 宿主只讀 `dirname(__DIR__, 2) . '/engine'`（`EditorController.php:297`，原始碼論證）；~~資產派送 K1-1 核對送出的 gz 位元組，而 `dist/` 裡沒有 `.gz`~~（**寫錯了**，審核第 2 項：`dist/` 裡有 117 個 `.gz`，其中 30 個與發佈成員逐位元相同，K1-1 分不出來源）；量測上由 I2-3 擋：取樣器每次掃 `/proc/*/fd`，窗內沒有任何行程開著掛載底下的檔 |
| `zz-m3gate0.config.php`：`debug` false、`loglevel` 2 | 與開發實例的 `zz-litecore.config.php` **同值**，不是差異來源 | I1-3：system config 在安裝前後逐鍵相同 |
| `firstrunwizard` 停用 | 同開發實例 | — |

**真正全新的實例**要新建 ddev 專案，會重建共用 router、讓擁有者其他在跑的 ddev 專案（`fgp-nc`、`nc-bridge`）短暫 404；
擁有者這一輪沒有選它。

## 3. 做法

### 3.1 發佈壓縮檔

新工具 `wasm_sdk_probe/tools/build_m3_release.py`：

- 內容＝宿主 commit（`5e53362`）在 `appinfo/ lib/ templates/ js/` 底下的**被追蹤檔案**，取自 git 物件（`git archive`
  的語意，**不是**工作樹）；加上 `engine/MANIFEST.json` 與它列出的每一個 `engine/files/<路徑>.gz`（取自宿主目錄的
  `engine/`，那是資產派送 K0 核對過的那一份，buildId `9076b0b425222c0e`）。頂層目錄 `litecore/`。
- 決定性：成員依名稱排序、mtime 固定、uid／gid 0、權限正規化（目錄 755、檔案 644）、gzip 標頭 mtime 0。
- 寫出發佈紀錄 `findings/evidence/m3-install/release.json`：來源 commit 與主旨、壓縮檔 sha256 與位元組數、每個成員的
  路徑與 sha256。壓縮檔本身（約 60 MB）放 `wasm_sdk_probe/build/release/`，**不進 git**；紀錄綁住它的 sha256。

### 3.2 安裝

新工具 `wasm_sdk_probe/tools/check_m3_install_elsewhere.py install`：把壓縮檔解到 `litecoreprobe` 的
`nextcloud/apps-extra/`（該實例唯一可寫的 app 路徑），然後 `ddev occ app:enable litecore`。這就是管理者從壓縮檔裝一個
非 App Store app 的做法。安裝前後各記一次：`occ app:list`、`occ config:list system`、`occ config:list`（全部 app）、
探針 app 的兩個開關、`occ user:list`、安裝目錄的完整清單（每個檔的 sha256、有沒有 symlink）；安裝後記 `occ app:getpath litecore`。
`apps-extra/litecore` 已存在就拒絕。

（審核後加）**解壓之前先對 web 容器取樣 120 秒**（與 §3.5 同一支取樣器，涵蓋兩次 ddev 健康檢查），那是 I4-1b 的基線：
「PID 1 的子行程在裝 app 之前叫什麼名字」。第一次安裝（2026-09-29 06:3x）沒有這段基線，所以以 `--reinstall` 重裝一次：
先確認安裝目錄與發佈紀錄逐檔相同、`occ app:remove litecore`，再照上面的步驟裝。重裝的位元組與第一次相同。

（審核二第 1 項）**`app:remove` 會留下 app 設定**（`enabled: no`、`installed_version: 0.2.1`），所以那次重裝的 `app:enable`
是「啟用一個已知版本」，不是安裝。`--reinstall` 因此在 `app:remove` 之後逐鍵刪掉 `litecore` 自己的 app 設定
（`occ config:app:delete`；這個 app 沒有 migration、背景工作、repair step——`appinfo/info.xml`——所以 app 設定就是它在
資料庫裡的全部狀態），刪了什麼、刪完讀回什麼都記在 `removedFirst`；I1-1 要求安裝前 `config:list` 裡**沒有** `litecore`。
基線改成「PID 1 的後代，以 (pid, 啟動時間, comm) 識別」（第 3.5 節），所以基線只在**同一個容器生命週期**內有效：安裝與
開窗各記一次 web 容器的 `State.StartedAt`，兩者不同，I4-1b 紅（容器重啟過就要重裝重取基線）。

（審核三第 4 項，**更正上一段的理由**）「那次重裝是啟用已知版本、不是安裝」**不成立**：NC 34 的
`core/Command/App/Enable.php:93` 一律呼叫 `Installer::installApp()`，它的 `installAppLastSteps`（`lib/private/Installer.php:535`
起）一律跑 migration、背景工作、install repair step，再寫 `installed_version` 與 `enabled`。殘留的 `installed_version` 只決定
走哪個**分支**：有舊版本時多跑 pre／post-migration repair step，而且 migration 不是 schema-only（`:538-550`、
`MigrationService::migrate($to, $schemaOnly)`）。這個 app 沒有 migration、沒有 repair step，兩個分支做的事相同。所以刪設定
與 I1-1 的新條件**保留**，理由改成：讓安裝走「從沒裝過這個 app 的實例」會走的那個分支（對之後帶 migration 的版本才有差），
而且安裝前的資料庫狀態等於全新實例的。

### 3.3 四支計數 runner 接受「另一台」

`check_m3_assets.py`、`check_m3_versions.py`、`check_m3_locks.py`、`check_m3_host_entry.py` 都接受 `--ddev-root`
（預設仍是開發實例）。

- 實例（網址、admin 密碼、`ddev occ`／`ddev mysql`、access log）一律從 `--ddev-root` 來。
- **宿主綁定**（報告的 `hostRepo`／`hostDirty`／`hostFiles`，與宿主入口的 `instance.app`）：在開發實例上照舊讀 git；
  在其他實例上讀**安裝目錄**，逐檔對發佈紀錄——兩邊的檔案集合相同、每個 sha256 相同、沒有 symlink，`hostRepo` 才是
  發佈紀錄的來源 commit，否則 `hostRepo` 是空字串、`hostDirty` 列出每一處不符。~~評分函式一行都不改~~（**不成立**，審核二
  第 11 項：§3.4 第 4 點改了宿主入口的 `score`——H3 釘分支。資產派送、版本、鎖三支的評分函式沒改。所以宿主入口那幾列
  等價性是有意義的比較，而且過了：舊報告沒有 `intruder.mode`，評分不變。）計數時「dirty 就拒絕」「`hostRepo` 以
  `5e53362` 開頭」照舊成立。
  （審核二第 17 項）「逐檔相同」另外把**空目錄**與**非一般檔**（socket、FIFO、裝置檔）列為不符——`tree_listing` 原本只看
  一般檔與 symlink，這兩種放在安裝目錄裡它看不見（`check_m3_skeleton_open.tree_oddities`）。
  （審核二第 10 項）三支 runner 記錄宿主綁定改成呼叫同一個函式 `binding_fields`，資產派送的 K0 記錄改成呼叫
  `package_for`——runner 與等價性檢查呼叫的是同一個東西，不是一份抄本。
- 資產派送 K0 的兩條 git 條款（K0-4 的「被追蹤」那半、K0-6）讀的是**來源 repo**；K0-4 的目錄列表那半、K0-1～3、K0-5
  讀安裝目錄。
- **等價性**：改完之後，用改過的 runner 重新評分每一份既有的計數報告，判定逐份與改動前相同~~（改動沒有改到開發實例那條路）~~。
  （審核第 6 項：評分函式本來就沒改，重新評分**不可能**不同，它證明不了括號裡那句。）所以另外在開發實例上把「記錄」那條路
  舊新各跑一次、逐欄比對：宿主綁定三欄（舊的是內嵌的 git 指令，新的是 `host_binding`）、資產派送 K0 的 `package_record`、
  `Instance.describe()` 的 `app`。並記下 `tools/` 裡每個被載入模組的 sha256——`host_binding` 住在
  `check_m3_skeleton_open.py`，它不在任何 runner 的 sha 裡。
  （審核二第 10 項）「舊的」那一側原本是一份手抄的 git 指令，跟 `host_binding` 開發實例那支逐字相同，所以比對它證明不了
  runner 以前真的這樣記；「新的」那一側寫死 `package_record(DEFAULT_DDEV)`，不是 runner 實際走的條件分支。改成：舊側
  是三個運算式（`hostRepo`、`hostDirty`、`hostFiles`，加上資產派送的 `package_record(DEFAULT_DDEV)`），工具先在
  `git show 9748b714:` 的三支 runner 原始碼裡逐一找到它們（空白正規化後逐字；`hostDirty` 在資產派送與版本是
  `dirty = …` 加 `"hostDirty": dirty` 兩處），找到的**同一段文字**再拿去求值；新側呼叫 runner 自己呼叫的
  `binding_fields`、`package_for`、`Instance.describe`。找得到與否記在 `equivalence.json` 的 `transcription`，I3-8 判。
  （審核二第 5 項）每一列另外記舊新兩支 runner 的 `--red-cases` exit，舊新要相同（列的比較本來就是整個 dict 相等）。
  （審核二第 12 項，依 §3.5 的裁決 Q3）`module_shas` 只量**編排器自己**這個 process 載入的模組；runner 是 subprocess，它們
  延遲載入的模組（`build_e2_c_shell_bundle`、`validate_e1_c`）與 `make test-e2-c-static` 讀的一切（node 測試、`web/*.js`、
  Makefile）沒有東西綁。所以在等價性檢查、開窗、收窗三個時點各記一次：`git rev-parse HEAD:wasm_sdk_probe`（tree 物件）、
  最後一個碰 `wasm_sdk_probe` 的 commit、`git status --porcelain --untracked-files=all -- wasm_sdk_probe`（**必須是空的**），
  以及 `sys.version`、`node --version`、`make --version` 第一行。三個時點的 tree、最後 commit、三個版本要相同；開窗時工作樹
  不乾淨就**拒絕**計數執行（不只是判紅）。`module_shas` 照留。**具名極限**：gitignore 掉的路徑（`dist/`、`build/`、
  `__pycache__`）不在範圍；`dist/` 由各 runner 自己核對的頁面與引擎 sha 綁住。
- （2026-10-02，在 0.2.5 上重跑之前）**等價性的錨從 PRE 換成開發基線。**上面那套比的是「`9748b714` 的工具」對「現在的工具」。
  它要證的事——`--ddev-root` 的改動對開發實例中性——在 0.2.1 的計數窗口證過了；之後評分函式**刻意**改過（頁面與宿主 pin、
  資產派送 K2 的 A′ 儀器、鎖的 K9′／K10′），每一項都在新綁定上重新計數，所以在 0.2.5 上照原文重跑，6 列只有 1 列相同
  （`findings/evidence/m3-install/equivalence.json`，2026-10-02T14:21:12Z）。照原文要綠只能把舊報告釘回舊綁定——那是造機械
  維持舊宣稱（CLAUDE.md「驗收判準的形式」第 4 節）。所以 PRE 的列與「記錄路徑 PRE 對現在」撤回（I3-8），它守的那個問題
  ——**判 litecoreprobe 的工具，是不是產生開發實例那些判定的同一套**——改用 2026-09-29 在開發實例上、宿主 0.2.5 跑出來的
  四份計數報告當基線來守（I3-9～I3-11）：報告由工具依原始欄位選（不手列）；它們記下的記錄欄位要等於現在的記錄路徑**完全**
  相同；它們的 runner sha 要等於現在的 runner 檔；而它們跑過之後，`wasm_sdk_probe/` 底下除了編排器本身之外**沒有任何檔案**
  被 commit 改過。最後這條比對抗性審核建議的「runner 的 import 閉包＋Makefile＋`editor-shell-v2/tests/`＋`web/`」嚴：
  `make test-e2-c-static` 實際讀的遠不只那幾處（`tools/check_e1_c_bundle_intact.py`、`tools/inventory_corpus_axes.py`、
  `test-docs/`、`tests/*.py`、`editor-shell/`、`e2/`），手列就是第 1 節不可當硬判準的那種；反過來只放行一個檔，任何別的漂移
  都會紅。放行的那一個要自證不在 runner 的路上：不在四支 runner 的 import 閉包裡（工具用 `ast` 走 import，含函式內的延遲
  import——`modulefinder` 在本機 Python 3.14 上崩）、Makefile 沒有提到它。PRE 對現在的記錄路徑比較照跑，改成登錄、不判；
  `transcription` 照判。tree 綁定另記 `ssl.OPENSSL_VERSION`（審核第 12 項）。
  **具名極限**：開發報告跑的時候工作樹乾不乾淨，沒有任何地方記錄；libssl3 在 2026-10-02 09:24 升級，晚於開發報告，`openssl`
  只綁得到等價性檢查到收窗；記錄路徑的四個可呼叫物件（`binding_fields`、`package_for`、`release_record`、`Instance.describe`）
  是手列的——I3-11 讓開發報告之後沒有任何 commit 改得到它們，但工具若改從別的函式記錄，這個清單不會自己變。瀏覽器：見 I3 的
  「登錄、不判」與修訂紀錄（擁有者裁示 B）。
  （同日，第二次對抗性審核之後，`findings/evidence/m3-install/review-2026-10-02-opus-i3-9-12.md`）三處更正：
  (1) 「任何別的漂移都會紅」**不成立**（審核第 6 項）：gitignore 掉的輸入（測試文件在 `dist/`）、系統函式庫、樹外的輸入都不在
  I3-11 裡——測試文件改由 I3-13 比，系統函式庫只綁等價性檢查到收窗。(2) 「放行的那一個要自證不在 runner 的路上」只證了一個方向
  （審核第 1 項）：runner 不 import 它，可是**它啟動 runner、也評 runner**——窗裡跑了什麼（臂、次數、測試文件）由它決定，宿主
  入口自己的評分又不釘臂（少了 H3 的 `conflict` 臂照樣 `LANDS`）。綁住它啟動了什麼的是 I3-13，不是 I3-11。Makefile 之外，
  改成 `wasm_sdk_probe/` 底下任何地方都不准提到它（`git grep`）。(3) libssl3 在開發報告之後升級了**兩次**（2026-10-01 11:31:46
  3.5→3.6、2026-10-02 09:24:33 3.6→3.7，`/var/log/apt/history.log`），不是一次；而 `ssl.OPENSSL_VERSION` 三版都讀成
  `OpenSSL 3.5.5 27 Jan 2026`，看不見這種升級（審核第 3 項）。tree 綁定另記 `dpkg-query` 的 `libssl3t64` 版本。
  另外：`transcription` 照判，但它守的是**登錄的那份 PRE 比較的來源**（舊側確實是 `9748b714` 的運算式），不是交接文件寫的
  「記錄路徑仍是 runner 用的那條」——後者沒有任何東西在看現在的 runner（審核第 10 項）。
- （審核後加）**綁定的自我測試**：`host_binding` 是 I1-2、I3-5 與每一次「dirty 就拒絕」背後唯一的儀器。每次開窗前在一個
  暫存實例上解出發佈壓縮檔，量乾淨、改一個位元組、多一個檔、少一個檔、多一個 symlink、整個安裝目錄換成 symlink 六種；
  乾淨那一種要讀成乾淨，其餘五種都要在 `hostDirty` 點名。「安裝目錄本身是 symlink」原本看不見（`rglob` 會跟進去），已補。
  （審核二第 17 項）再加兩種：多一個 FIFO、多一個空目錄——共八種，乾淨一種、漂移七種。

### 3.4 宿主入口 runner（E）

三處改動，判準 H1–H3、H5 **一個字都不改**：

1. **離頁再關瀏覽器**：每一臂結束時先導回 Files（同資產派送 K2 的「回 Files」），再以 admin 輪詢伺服器的 `nc:lock` 最多
   10 秒，記下鎖與 PROPFIND 的狀態碼（審核第 19 項：失敗的 PROPFIND 讀起來會像「已釋放」）。
2. **重設時碰到殘留的鎖**：臂開始時若伺服器上有鎖，記下它（`lockAtReset`），以資料庫清掉（同鎖與權限 runner 的
   `clear_locks`）再重設。記下而不擋，因為離頁釋放鎖是資產派送 K2-5 與鎖與權限的判準，不是宿主入口的。
3. **衝突臂的入侵者改帶 token**：頁面持有 token 鎖之後，不帶 token 的 PUT 是 423（`49cc4ab` 起；宿主入口上一次計數
   執行在 `0dcb745`，那時還沒有鎖），衝突根本造不出來，H3 無從量起。入侵者改成以 PROPFIND 讀 `lockdiscovery` 拿到
   token、以 `If: (<token>)` 送 PUT。~~——那是鎖擋不住的寫入路徑（finding 102）~~（**錯引**，見下方裁決：入侵者是 admin，
   跟頁面**同一個使用者**；持鎖者帶自己的 token 從另一個用戶端寫入，是 WebDAV 本來就允許的寫入（RFC 4918 §6.4），
   finding 102 講的是**另一個**使用者拿別人的 token，修不修都不影響這條路。）H3 量的是**頁面與宿主對「檔案在開著時被改了」
   的反應**（412、另存副本、不重載、第二次按也不覆寫）。
   宿主的 PUT 同時帶 `If-Match` 與 `If: (<token>)`（`js/litecore-editor.js` 的 `put()`）；帶 token 的 412 之後宿主會問
   伺服器 token 還在不在，在就不重送、直接另存副本（`saveOnce()`）。兩個 shakedown（開發實例
   `findings/evidence/m3-host-entry/shakedown/2026-09-28T223038Z.json`、litecoreprobe `…223518Z.json`）的衝突臂都是
   入侵者 204、兩次存檔 `(412, tokenOnServer true)`。~~鎖與權限 K6（token 已失效、`tokenOnServer` false）走不到它~~
   （**不完整**：K6 走不到，但鎖與權限 K12 `unlock-refused` 與版本第 6 步都走得到 `tokenOnServer true`；**只有 H3 有的是
   「再按一次」**。）
4. （裁決條件 3，2026-09-29 加）**H3 的評分釘住它宣稱走的分支**：報告帶 `intruder.mode = "lock-token"` 時，每一輪衝突臂
   都要入侵者 2xx 而且拿得到 token、每次存檔恰好一個 PUT `(412, 帶 token)`、`tokenOnServer` 是 true；否則那一輪 H3 紅，
   訊息點名是入侵者被拒還是鎖死了（不會落到看起來像產品問題的「伺服器位元組不對」）。舊報告沒有 `mode`，評分不變（§3.3
   的等價性因此仍成立）；有 `lockAtEnd`（新 runner）卻沒有 `mode` 的報告直接紅。新紅案 `H3-intruder-refused`、
   `H3-lock-died`。

#### 裁決（fable，2026-09-29，擁有者授權代為決定）

問題：`SPEC-M3-locks-and-permissions.md:94` 已經寫了「宿主入口的 H3 **被 K6 取代**」，保留 H3 等於推翻一個已登錄的處置。
主 session 的傾向是照處置退役（A，弱）；**裁決是保留（B）**，理由改正。白話理由（原文）：

> :94 那句「H3 被 K6 取代」是 2026-09-28 18:21 寫的（`6c0a3b66`），而 H3 的「再按一次」條款在 25 分鐘前（17:56，
> `1c0975a6`）就已經進了宿主入口規格；:94 只講了「入侵者怎麼寫進來」那件事，完全沒有提到第二次按。查下來，K6、K12 和
> 版本那一步的第 6 步都只按一次存檔，所以「衝突之後再按一次仍然被拒、不會把別人的內容蓋掉」這件事目前只有 H3 在守——
> 而且它守的是一個真實的洞：伺服器回 412 時會附帶一個 ETag（shakedown 裡的 `responseEtag` 就是），宿主現在只在成功時
> 更新版本，但只要有人日後「順手」拿 412 的 ETag 來用，第二次按就會變成默默覆寫。選 A 的主要理由（「B 靠的是上游缺陷
> 102，上游修了就會紅」）查下來不成立：runner 的入侵者和頁面是同一個使用者 admin，持鎖的人自己帶 token 從別的用戶端
> 寫入本來就是 WebDAV 允許的，102 修不修都不影響。至於「之後再把第二次按補進 K6 或 K12」，那是動一個已經落地的計數
> 閘門，要重跑鎖與權限，比留在已經寫好、已經有紅案、已經在兩個實例上各過一輪的 H3 裡貴得多。

主 session 自己核對過：兩個 commit 的時間、`responseEtag`（`litecore-editor.js:394`）只記不用、`etag` 只在成功時更新
（`:381`）。裁決附帶的條件：:94 不改，在鎖與權限規格的修訂紀錄 append 一列（「:94 對鎖的閘門仍成立；對宿主入口 runner
被本規格 §3.4 取代」）；本節的理由改正（上面的刪除線）；H3 評分釘分支（第 4 點）與兩個紅案；runner 開頭註解與
`findings/evidence/m3-host-entry/README.md` 寫明入侵者是同一個使用者；開發實例上的計數執行在這些之後；交接文件
更正選項 E 的說法——「宿主入口唯一沒被別處涵蓋的是 H5」**不成立**，另外還有 H3 的「再按一次」與 H2 的「伺服器上的檔案
真的有標題」（鎖與版本的 runner 裡都沒有 `Heading` 或 `text:h` 的檢查）。

宿主入口改完之後，在**開發實例**上也跑一次計數執行（它上一次在任何會上鎖的宿主上都沒跑成），不在 §4 I3 的時間窗內跑。

### 3.5 伺服器端行程的量法

~~`check_m3_install_elsewhere.py run` 在四支 runner 跑的整段時間裡，每 0.5 秒以一次 `docker exec ddev-litecoreprobe-web`
取樣 web 容器：`ps -eo pid,ppid,comm,args`，加上 `find /proc/[0-9]*/fd -lname '*litecore-dist*'`（誰開著掛載底下的檔）。
每個樣本記下 `docker exec` 花了多久（`d`）。~~（**已被下一段取代**，審核二第 16 項：舊文沒劃掉，讀起來像現行做法。）
docker exec 的身分是 uid 1000，跟 php-fpm worker 相同，看得到它們的 fd（2026-09-29 實測）。

**（第二次 shakedown 之後改儀器，判準不動）**取樣改成**整個時間窗只用一個常駐的 `docker exec`**：容器裡的 shell 迴圈每 0.5 秒
印出容器時鐘、`ps`、以及每個開著掛載底下檔案的 fd 連同它的 ppid 與 cmdline（`/proc/<pid>/stat`、`/proc/<pid>/cmdline`）。
逼出它的兩個量測（`findings/evidence/m3-install/shakedown/2026-09-28T230921+0000.json`）：每個樣本一次 `docker exec` 時，
有一次被正向對照自己同時在跑的 `docker exec` 拖到 1.6 秒（I4-2 因此紅）；對照的 `sleep` 在 `ps` 跑完、`find` 跑之前才被 fork，
沒有 ps 列可以歸屬（I2-3 因此紅）。兩者都是儀器錯，不是產品。實測新迴圈的間隔 ~~0.509–0.515 秒~~（沒有證據檔，審核二第
16 項）窗內最大 0.515 秒（`findings/evidence/m3-install/shakedown/2026-09-28T231953+0000.json`）。

**（審核二之後再改儀器，判準見下）**迴圈內的順序與格式：

- **先 `find` 再 `ps`**（第 6a 項）：一個在兩者之間被 fork 的開檔者，只要到 `ps` 時還活著就有 ps 列；已經死了的，保有 `find`
  當下讀到的 ppid 與 cmdline。原本的順序只補得了「少一層」。
- `ppid` 取 `/proc/<pid>/stat` 最後一個 `") "` 之後的第二欄（第 15 項：`comm` 可以含空白，`cut -f4` 會讀錯；實測一個叫
  `lc sp` 的開檔者與它的子行程都讀對）。
- `ps -ww -eo pid=,ppid=,comm=,lstart=,args=`（第 15 項：沒有終端時 `args` 被截在 80 欄；`lstart` 給每個行程 pid 以外的
  身分，第 2 項）。`comm` 以「下一段是 `lstart` 形狀」切開，所以含空白也讀得對。
- 取樣器的 stderr 由一條執行緒持續讀掉，最後 50 行記進報告（第 15 項：沒人讀的 pipe 滿了會卡住迴圈）。

~~Nextcloud 在這個容器裡以 php-fpm 執行，app 的每一行 PHP 都在某個 `php-fpm` 行程裡；**app 若啟動任何行程（文件伺服器、
轉檔器、`exec()` 出去的 shell），它會是某個 `php-fpm` 的後代，而且 `comm` 不是 `php-fpm`**。判準就寫成這個，不列舉「哪些
程式算文件伺服器」。~~（**錯**，審核第 1 項：從 PHP 背景化出去的行程（`exec('soffice … &')`）在 shell 結束後被收養到
PID 1，不再是 php-fpm 的後代；而 `ddev occ` 以 `php occ` 執行時會載入每個啟用中的 app，那也不在 php-fpm 底下。）

所以判準分兩條，都不列舉「哪些程式算文件伺服器」：

- **I4-1a**：php-fpm 的後代而自己不是 php-fpm——抓 app 在請求裡直接起的子行程。（審核二第 13 項）另外：名字是 php-fpm、
  但祖先裡有**兩個以上** php-fpm 的行程——worker 以 `pcntl_fork` 生出的子行程保留 `php-fpm` 這個名字，原規則把它當成
  worker 放過；只有 master 的子行程才是 worker。
- **I4-1b**：~~**PID 1 的直接子行程**，名字不在「裝 app 之前 PID 1 的子行程」的名字集合裡~~（審核二第 2 項：以名字比，
  一個跟基線同名的孤兒連同它整棵子樹都漏掉；只看直接子行程，孤兒的子孫也漏掉）**PID 1 的每一個後代，以 (pid, `lstart`,
  `comm`) 識別，都要是「裝 app 之前 PID 1 的後代」之一**——抓被收養的孤兒，不管它原本是誰生的（背景化的文件伺服器、
  `occ` 載入 app 時起出來又留下的東西）。基線在解壓之前量（§3.2），只在同一個容器生命週期內有效。**實測**（2026-09-29，
  shakedown 的樣本）：服務行程樹不接在 PID 1 底下——PID 1 是 `bash /pre-start.sh`，supervisord、php-fpm、apache 的根是
  另一個 ppid 0 的 `bash -c …start.sh`（PID 9）。~~所以規則寫成「PID 1 的直接子行程」，不是審核者提議的「接到 PID 1 的血統」
  （那樣會把整棵服務樹算進基線以外）。~~（**寫錯了**，審核二第 2 項：那是我從 PID 9 的發現推論出來的，而同一批樣本顯示
  PID 1 的後代只有 pid 8 `cat`（加上對照）——服務樹正是**不在** PID 1 底下，所以血統規則不會把它算進去。）
  ~~孤兒一定被收養到 PID 1（容器裡沒有 subreaper）。~~（審核二第 14 項：推論，不是量測；處置見下方裁決。）
  依裁決改成量到的那句（條件 8）：**在兩條實際走過的路上（docker exec 根：對照 1；php-fpm worker：對照 4），背景化的子行程
  在對照期間內是 PID 1 的直接子行程——每個窗都量一次。**不寫「容器裡沒有 subreaper」這種全稱句。一次性量測
  （`findings/evidence/m3-install/fpm-path-measurement-2026-09-29.md`）另外登錄：孤兒會**繼承** worker 開著的檔（PHP 的
  `fopen` 不設 `O_CLOEXEC`），而且只有 I4-1b 抓得到它——`exec('… &')` 的 `sh -c` 幾毫秒就結束，I4-1a 看不到。

**正向對照**（否則「沒看到」與「儀器沒接上」長得一樣），窗一開就跑，~~三個~~四個（對照 4 是下方裁決加的），外加窗尾一個：

1. 把 `/bin/bash` 複製成 `/tmp/litecore-ctl/php-fpm`（`comm` 因此是 `php-fpm`），讓它背景起 `/tmp/litecore-ctl/lcorphan 6`
   （`sleep` 的複本）、前景 `sleep 2` 後結束。I4-1a 必須在對照期間看到那個 `sleep`；它結束之後 `lcorphan` 被 PID 1 收養，
   I4-1b 必須看到 `lcorphan`。（審核二第 6b 項）`lcorphan` 的 stdio 導到 `/dev/null`：它原本握著 docker exec 的 pipe，讓那支
   exec 多撐約 4 秒、拖慢同時的另一支 exec。
2. 把 `/bin/bash` 複製成 `/tmp/litecore-ctl/lcfd`，讓它 `exec 3</mnt/litecore-dist/e2-editor.html` 再睡 3 秒。I2-3 必須看到
   `lcfd` 開著掛載底下的檔（實測：`find` 找得到 `/proc/<pid>/fd/3`）。
3. `docker create` 一個名為 `litecore-ctl-events` 的容器再 `docker rm`。I4-3 的事件串流必須看到它的 `create`。
   （審核二第 9 項）映像改用 `ddev/ddev-utilities:latest`：用 web 容器的映像建出來的容器帶著 litecoreprobe 的 compose 標籤，
   中斷在 create 與 rm 之間時，會留下一個 ddev 會當成 litecoreprobe web 容器的停止容器。（審核二第 3 項）**窗尾再做一次**
   （`litecore-ctl-events-end`，在 `window.end` 之前），也必須被串流到——事件串流只在 +13 秒左右證明過活著，中途死掉會讀成
   「沒有事件」；停止串流前另外記它還在不在跑（`lifecycleAlive`）。
4. （裁決加）**走真實 php-fpm 的對照**：以容器裡的 PHP CLI 跑一支 25 行的 FastCGI 用戶端，連 pool 的 socket
   （`/run/php/php-fpm.sock`，0666），請 pool 在一個普通的 `php-fpm: pool www` worker 裡執行 `/tmp/litecore-ctl/fpm.php`——
   沒有 HTTP 請求、docroot 裡沒有檔案、任何 access log 都沒有一列（所以 I2-1、I2-4 不受影響）。腳本依序：背景起
   `/tmp/litecore-ctl/lcorphan4 8`（stdio 導到 `/dev/null`）、前景跑 `/tmp/litecore-ctl/lcfg 2`、開 `/mnt/litecore-dist/e2-editor.html`
   睡 3 秒再關、印出 `worker=<pid> orphan=<pid>`。先起子行程再開檔，因為 `fopen` 不設 `O_CLOEXEC`，之後起的子行程會繼承 fd。
   I4-1a 必須看到 `lcfg`，**而且它的 php-fpm 是腳本回報的那個 worker、那個 worker 的父行程是 ppid 不為 0 的 php-fpm**（真的
   master；對照 1 的假 php-fpm 是 docker exec 起的，ppid 0）；I4-1b 必須看到 `lcorphan4`；I2-3 必須看到**那個 worker 自己**開著
   **那個檔**。名字刻意跟對照 1、2 不同，每個對照各有自己「一定要看到」的集合，誰也不能替誰滿足。

對照的歸屬看行程或它的祖先的 `args` 有沒有 `/tmp/litecore-ctl`，而且樣本時間在該對照起訖 ±1 秒內（審核第 17 項：樣本的
時間戳記在 docker exec 之前，會早約 45 ms）。對照 4 的 worker 自己的 `args` 是 pool 的，不含那個路徑：它的 fd 以「腳本回報的
pid、腳本開的那個檔、對照 4 的時間窗」三者同時成立來歸屬（取樣迴圈記下每個 fd 指向的檔，I2-3 的問題列因此帶著檔名）。
**具名極限**：~~對照 4 的那約 5 秒（±1）裡~~（**寫錯了**，審核三第 5 項：程式碼豁免的是 start 到 start＋9 秒再 ±1，約 11 秒，
而 FastCGI 請求約 5.3 秒就返回，之後那個 worker 是普通的 pool worker）從對照 4 開始前 1 秒到它的 FastCGI 請求返回後 1 秒
（`controls.fpm.returned`；實測請求 5.1 秒）裡，那一個 worker 讀那一個檔不會被判紅；讀掛載底下別的檔會。腳本沒回報 pid 時，
「對照 4 沒看到」直接紅，不會 SKIP。

#### 裁決（fable，2026-09-29，擁有者授權代為決定）：對照 4、subreaper、工具的綁定

審核二把三件事留給「下一個 session 決定」：第 4 項（I2-3 有沒有走 php-fpm 的對照）、第 14 項（「沒有 subreaper」是推論）、
第 12 項（`module_shas` 漏掉延遲載入的模組與 `make test-e2-c-static` 讀的一切）。主 session 先量（上面的一次性量測），再以
選項 A／B／C 附傾向送 fable；fable 唯讀，裁決 **Q1 C、Q2 C、Q3 C（加強）**，十三條條件逐條落地，對照表在
`findings/evidence/m3-install/ruling-2026-09-29-fable-controls.md`。白話理由（原文）：

> Q1：B 最差——I2-4 的整句意思就是「窗內沒有任何 /apps/litecoreprobe/ 請求」，B 要在那裡開豁免；而且照探針 app 的程式碼，
> `.wasm` 根本是 redirect 到 Apache 靜態檔去，不經 php-fpm，PHP 那條路也只在 `file_get_contents` 那幾毫秒持有 fd，所以 B
> 既不 php-fpm-faithful 也不改機率。A 只有一次性量測，容器換 image、換 php-fpm 設定就沒人看著。C 是逐實例性質（每個窗都要
> 看到），成本一支 docker exec 約 5 秒，跑在 runner 之前所以不跟 runner 搶 worker。但要講清楚：C **不改 I2-3 的射程**，它
> 證明的是「儀器看得到真 php-fpm worker 的 fd」與「I4-1a／1b 在真的 php-fpm 血統上會亮」——現有對照 1 是 bash 改名的假
> php-fpm，掛在 docker exec 底下。射程句照 A 改寫，不論 C 落不落地。
>
> Q2：既然 C 每個窗都有一個真 worker 背景化的孤兒，「沒有 subreaper」就從推論變成每窗量到的事實。但要寫成量到的那句——
> 「兩條路（docker exec 根：對照 1；php-fpm worker：對照 4）背景化的子行程在對照期間內是 PID 1 的直接子行程」——不是
> 「容器裡沒有 subreaper」這種全稱句。fd 繼承那件事留在一次性量測檔裡登錄。
>
> Q3：A 只綁 runner 自己 process 載入的模組，`make test-e2-c-static` 那串（node 測試、Makefile、web/*.js）還是沒人綁，而且
> 要改四支 runner 的記錄路徑、碰 I3-8。B 是手工枚舉（第 1 節不可當硬判準那種）：多一個輸入目錄它不會紅。C 是工具封閉的
> 枚舉，成員由 git 生成。但主 session 寫的 `--untracked-files=no` 有洞：一個沒進版控的 `tools/foo.py` 或 `tests/*.test.mjs`
> （Makefile 用 glob）它看不到；改成 `all` 要空，今天這棵樹本來就沒有這種檔，不多花任何東西。另外現況比 F4 說的還少：
> `module_shas` 量的是編排器自己的 process，runner 是 subprocess。

主 session 核對過 fable 引用的數字：第三次 shakedown 的引擎請求 471 次／窗長 383.5 秒、`check_m3_host_entry.py:104` 的延遲
import、`EditorController.php:226` 的 `StreamResponse`、當時工作樹有五個改過的工具檔。fable 更正了主 session 的一個事實：
探針 app 的路由對 `.wasm` 是 redirect 到 Apache 靜態檔（`ProbeController.php:151-153`），不經 php-fpm。

**容器**（審核第 4 項）：`docker ps -a` 的集合只看得到「多了一個容器」，看不到**啟動**一個本來就在的容器（這台機器上有
`oxool-dev`，一個 OxOOL 文件伺服器，狀態 Exited）。所以窗內另外即時串流 `docker events` 的容器生命週期事件（create、
start、restart、unpause、die、kill、stop、pause、destroy）。**不能事後查**：Docker 只在記憶體裡留有限的事件，而取樣器自己
每秒就產生約六筆 exec 事件。

## 4. 驗收判準（先於任何工具與任何執行寫下；審核之後、任何計數執行之前修訂）

評分由 `check_m3_install_elsewhere.py --score` 做，只讀報告裡的原始欄位；四支 runner 的報告由它們各自的評分函式重新評分
（計數時 strict），紅案也在評分當下重跑。

### I0 壓縮檔（離線）

1. 成員集合＝來源 commit 在 `appinfo/ lib/ templates/ js/` 底下的被追蹤檔案（工具當場從 `git ls-tree` 推出）∪
   `engine/MANIFEST.json` ∪ MANIFEST 列出的每一個 `engine/files/<路徑>.gz`，不多不少（全部在 `litecore/` 底下）。
   `appinfo/ lib/ templates/ js/` 這四個是手選的；來源 commit 頂層其餘的項目（`src/`、`package*.json`、`.ddev` …）記在
   `archive.excludedTopLevel`，**登錄、不判**（少了執行期需要的檔，I3 會紅）。
2. 被追蹤成員的位元組＝該 commit 的 git blob；engine 成員＝宿主目錄 `engine/` 的位元組；MANIFEST 的 `buildId` 與紀錄
   相同；發佈紀錄的成員清單＝壓縮檔的成員清單。
3. 同一個來源建三次（建檔時兩次、開窗時一次），壓縮檔 sha256 相同。範圍只到「同一台機器、同一個 zlib」，不是跨環境可重現。
4. 沒有 symlink、沒有硬連結、沒有任何成員路徑含 `..` 或以 `/` 開頭。

### I1 安裝

1. `occ app:enable litecore` exit 0；之後 `occ app:list` 的 `enabled` 裡有 `litecore`，版本＝壓縮檔裡 `info.xml` 的
   `<version>`。（審核二第 1 項）而且那是**安裝**不是重新啟用：安裝前的 `occ config:list` 裡沒有 `litecore` 這個 app。
2. 安裝目錄是實體目錄，底下沒有任何 symlink；它的檔案集合與每一個 sha256＝發佈紀錄的成員（兩個方向都比）——安裝當下量一次，
   **開窗時再量一次**（`host_binding`，含「目錄本身不是 symlink」）；`occ app:getpath litecore` 在安裝後與開窗時都是
   `/var/www/html/nextcloud/apps-extra/litecore`（Nextcloud 依版本在 `apps_paths` 之間挑，別處的一份會被優先服務，審核第 5 項）；
   §3.3 的綁定自我測試~~六種~~八種全對。（審核二第 17 項）安裝目錄底下也沒有空目錄與非一般檔（`tree.others` 是空的）。
3. `occ config:list system` 安裝前後逐鍵相同（`--private` 不開，值以 `***REMOVED SENSITIVE VALUE***` 比對）。其他 app 設定的
   差異**記下、不判**（第一次安裝實測只有 `litecore` 自己的三個鍵）。
4. 探針 app 的 `files_probe` 與 `files_isolation` 在安裝前、時間窗開始、時間窗結束三次都讀到 `off`。

### I2 與開發實例、與掛載、與探針 app 無關（逐實例性質）

1. 時間窗內，**開發實例** `litecore` 的 web 容器 access log 新增的列裡，沒有任何一列的來源位址不是 `127.0.0.1`（那是 ddev
   每 60 秒的 `/phpstatus` 健康檢查；經 router 進來的請求來源是 router 的位址，實測 `172.24.0.5`）。儀器非空洞：讀到的
   `GET /phpstatus` 列數 ≥ ⌊窗長／60⌋ − 1（審核第 12 項：原本只要「有任何一列」）。
   **前置條件**（shakedown 之後加）：開發實例最後一列非 loopback 請求已過 ≥ 60 秒才開窗，等了多久記下來（`window.devQuiet`）。
   逼出它的量測：`findings/evidence/m3-install/shakedown/2026-09-28T223255+0000.json` 在窗內讀到兩列
   `172.24.0.5 … "-" 408 0`，時間 06:33:13，恰好是開發實例上一個 shakedown 最後一個請求（06:32:33–34）之後 40 秒——
   Apache `mod_reqtimeout`（`header=20-40`）關掉 router 先開好、沒用上的後端連線。那是**窗外活動的殘渣落進窗內**；判準照
   字面判紅是對的，所以改的是開窗時機，不是判準（408 空請求**不**豁免）。對稱地，**窗結束後等 60 秒才讀**開發實例的 log
   （審核第 14 項：窗內造成的 408 會晚 40 秒才落地）。
2. 四支 runner 報告裡的 `baseUrl`／`instance.baseUrl` 都是 `https://litecoreprobe.ddev.site:8443`。
3. （審核後加）窗內每個樣本：沒有任何行程開著 `/mnt/litecore-dist` 底下的檔，正向對照 2 除外而且一定要看到。
   ~~限度：讀得比 0.5 秒快的小檔可能漏掉；引擎的大檔（gz 最大 41 MB）串流遠比 0.5 秒久。~~（**被自己的量測推翻**，審核二
   第 4 項：41 MB 的 gz 在 0.096 秒內送完，`findings/evidence/m3-assets/runs/2026-09-28T172628+0000.json`
   `wire.files["profiles/e2-editor-v8/probe.wasm"].gzip`——那是開發實例經宿主的 `StreamResponse` 送的，不是掛載。）
   **射程**（裁決條件 1）：一次持續 d 秒（d < 0.5）的讀取被抓到的機率約 d／0.5；最大的引擎檔也只要 0.096 秒。所以 I2-3 是
   **整個窗的統計性質**（第三次 shakedown 的窗 383.5 秒裡有 471 次引擎請求），**不是逐次讀取的保證**。**如果窗內從來沒看到
   任何人讀掛載**，結論只是「窗內沒有被抓到的掛載讀取」，可能有一次短讀取沒被抓到，判準不多宣稱什麼。
   （裁決加）正向對照 4 的 worker 開著它自己那個檔，除外而且一定要看到——這證明儀器看得到**真的 php-fpm worker** 的 fd，
   不改上面的射程。
4. （審核後加）窗內 litecoreprobe 的 access log 沒有任何請求路徑落在 `/apps/litecoreprobe/` 或 `/apps-extra/litecoreprobe/`
   底下（探針 app 那條不受開關控制的路由，第 2 節）。儀器非空洞：同一段 log 裡有引擎路由 `/apps/litecore/r/` 的請求。

### I3 M3 的流程在另一台上

在 `litecoreprobe` 上、`--ddev-root` 指向它、計數模式：

1. 資產派送 `ASSETS DELIVERED`（K0–K2，Chrome 3／Firefox 3）。
2. 版本 `VERSIONS CORRECT`（R1，Chrome 3／Firefox 3）。
3. 鎖與權限 `LOCKS LAND`（全部 22 格）。
4. 宿主入口 `LANDS`（H1–H3 兩瀏覽器各 3/3、H5 Chrome 1/1；§3.4 的 runner，H3 釘分支）。
5. 四份報告的宿主綁定都＝發佈紀錄：`hostDirty` 空、`hostRepo`（或宿主入口的 `instance.app.commit`）以發佈紀錄的來源
   commit 開頭；（審核後加）每份報告的 `startedAt`／`completedAt` 都落在窗內。
6. 四支的紅案對各自這一份報告全紅：執行時記下的 exit 0，**而且評分當下重跑一次**也全紅；報告檔的 sha256 等於執行結束時
   記下的（審核第 8 項：原本只綁路徑）。

另外（不在時間窗內）：

7. 宿主入口（§3.4 的 runner）在**開發實例**上計數執行 `LANDS`，紅案全紅（同樣在評分當下重跑），而且在開窗**之前**結束。
   （裁決條件 12）而且在等價性檢查**之後**開始——它延遲載入的模組只有 §3.3 的 tree 綁定綁得住。
8. §3.3 的等價性：~~改過的四支 runner 對既有計數報告重新評分，判定逐份與改動前相同；開發實例上的記錄路徑舊新逐欄相同；~~
   計數時，runner 的 sha256 與 `tools/` 被載入模組的 sha256 在等價性檢查、開窗、收窗三個時點相同。（審核二）~~每一列的紅案
   exit 舊新相同；~~舊的記錄運算式在 `9748b714` 的三支 runner 原始碼裡都找得到（`transcription`）；（裁決 Q3）計數時
   `wasm_sdk_probe` 的 tree、最後 commit、三個直譯器版本在三個時點相同，三個時點的工作樹都沒有未提交的東西。
   （2026-10-02）劃線的三段**撤回**（理由在 §3.3 末段與修訂紀錄），由下面 9～11 取代；tree 綁定另記 `ssl.OPENSSL_VERSION`，
   三個時點也要相同。

（2026-10-02 新增，任何 0.2.5 的窗口與等價性檢查的重跑之前；理由見 §3.3 末段與修訂紀錄。）

9. **記錄路徑對開發基線**：等價性檢查當下，開發實例的記錄路徑——`binding_fields(host_binding)` 的四欄（`hostRepo`、
   `hostDirty`、`hostFiles`、`hostBinding`）、`package_for`、`release_record`、`Instance.describe()` 整份——與第 10 條每一份
   **被判**的開發基線報告記下的**完全相等**。比的是報告裡有的那幾欄（頂層同名的鍵；`describe()` 對 `instance`），每份至少
   比到一欄。dict 遞迴；list、純量與型別改變是葉子，比相等；任一邊缺鍵就紅——只在現在才有的欄位**沒有豁免**（審核第 4 項：
   Z0-1、Z0-2 讀的正是只在現在才有的 `zst*` 欄位）。記錄路徑出錯就紅。
10. **開發基線**：工具選、不手列。四支 runner 各自 `findings/evidence/<runner>/runs/` 裡的每一份報告，若 `label` 是 counted、
    base URL 是開發實例（版本與鎖讀頂層 `baseUrl`，資產派送與宿主入口讀 `instance.baseUrl`）、綁定的宿主 commit
    （`hostRepo`；宿主入口是 `instance.app.commit`）以 `release.json` 的 `commit` 開頭、`startedAt` 早於等價性檢查，就被選進來；
    評分當下照同一條規則重選，要等於 `equivalence.json` 記下的集合，而每一份被選的報告本身也要照這四項重驗。被選的報告裡，
    記下的 runner sha256 等於等價性檢查當下 runner 檔的那幾份**被判**：每支 runner 至少一份；**全部**達到該 runner 的計數判定
    （`ASSETS DELIVERED`、`VERSIONS CORRECT`、`LOCKS LAND`、宿主入口 `LANDS`，評分當下由 runner 自己的 `score` 重算）；
    紅案在等價性檢查時 exit 0，評分當下重跑也全紅（審核第 3 項：不准挑）。sha 不同的列出、不判。每一份被選的報告，在等價性
    檢查時是已 commit 的 blob（`HEAD:<路徑>` 的 blob 等於工作樹那份的 blob），評分當下的 sha256 等於檢查時記下的（審核第 9 項）；
    `release.json` 的 commit 在等價性檢查與開窗時相同。
11. **開發基線之後 `wasm_sdk_probe/` 只動過編排器**：每一份被判的開發報告，取它 `startedAt` 當下或之前最後一個碰
    `wasm_sdk_probe/` 的 commit；從它到等價性檢查的 HEAD，`wasm_sdk_probe/` 底下改過的檔案**只准**是
    `tools/check_m3_install_elsewhere.py`。這個例外要自證：它不在四支 runner 的 import 閉包裡（工具以 `ast` 從四支 runner 走
    import，含函式內的延遲 import；閉包裡要有四支 runner 本身），`Makefile` 也沒有提到它。
12. **判準組相同**：`litecoreprobe` 上每一份 runner 報告的 `criteria` 等於同一支 runner 被判的開發基線報告的 `criteria`
    （審核第 10 項：資產派送的 `criteria` 決定 Z0–Z2 評不評）。

**登錄、不判**（擁有者裁示 B，修訂紀錄 2026-10-02）：每一份開發基線報告與每一份 `litecoreprobe` 報告逐次 run 的瀏覽器
`version` 集合（`runs[i].version`；宿主入口是 `browsers/<b>/<arm>[i].version`），記在 `equivalence.json` 與評分結果的
`registered.browserVersions`——0.2.5 的 RESULT 開頭那一行瀏覽器限定引用的就是這兩處；PRE 的記錄路徑對現在的差異
（`recording.preDifferences`）；四支 runner 的 import 閉包。

（2026-10-02 第二次新增：第二次對抗性審核之後、任何 0.2.5 的計數窗口之前；這一輪的等價性檢查、I3-7 與 shakedown 都要照新工具
重跑。理由見修訂紀錄同日第三列。）

13. **跑的東西相同**：`litecoreprobe` 上每一份 runner 報告，以及 I3-7 的那一份開發實例宿主入口報告，與同一支 runner 每一份被判的
    開發基線報告比：(a) **執行形狀**——資產派送、版本、鎖是逐次 run 的 (瀏覽器, 臂) 計數；宿主入口是每個瀏覽器每個臂的 run 數加上
    `repeats`——相同，只在計數時判（shakedown 本來就跑得少）；(b) **測試文件**——開發基線報告有 `original` 的，`original.sha256`
    相同（測試文件在 gitignore 掉的 `dist/`，原本只跟自己比）。
14. **等價性檢查與開窗之間沒有別的開發計數執行**：四支 runner 的 `runs/` 裡，`label` 是 counted、base URL 是開發實例、綁定的宿主
    commit 以 `release.json` 的 `commit` 開頭、`startedAt` 在等價性檢查開始之後（含）且不晚於開窗的報告，集合**恰好等於**以
    `--dev-host-entry` 傳入的那一份。它與第 10 條的選取互補：開窗之前的每一份開發計數報告，不是被判的基線，就是 I3-7——I3-7
    不能重跑到綠為止（審核第 2 項）。

另外，第 8、10、11 條各補一處（同一輪）：第 8 條——等價性檢查要在它所搭配的安裝**之後**開始（`install.completedAt` ≤
等價性檢查的 `startedAt`；加上 I4-1b 的容器生命週期，安裝、檢查、窗口就在同一個生命週期裡），tree 綁定的三時點另比
`libssl`；第 10 條——每一份被選的開發報告，在它**第一次被 commit 的那個 commit** 裡的 blob 也要等於 `HEAD` 的（commit 之後
沒再改過，審核第 7 項）；版本與鎖讀頂層 `baseUrl`、資產派送與宿主入口讀 `instance.baseUrl`，照條文逐支讀（審核第 9 項）；
第 11 條——`devCommit`、改過的檔案清單、import 閉包與提到編排器的行，評分時從等價性檢查的 HEAD 用 git 重算，要等於記下的；
閉包要包含等價性檢查自己載入的每一個模組（編排器除外，正向對照，審核第 5 項）。

### I4 沒有伺服器端文件行程

1. 時間窗內每一個樣本：**a** 沒有任何行程是某個 `comm`＝`php-fpm` 行程的後代而自己的 `comm` 不是 `php-fpm`；~~**b** PID 1 的
   每一個直接子行程，名字都在安裝前基線裡 PID 1 子行程的名字集合裡。~~（被下方審核二後的 **b** 取代；審核三第 9 項：原本
   只劃掉了下面的複本。）基線至少 120 個好樣本、集合非空。正向對照 1 的違規
   只准出現在它的起訖（±1 秒）之內，而且那段之內**一定**要出現：a 看到它的 `sleep`、b 看到 `lcorphan`。
   （審核二與裁決之後，任何計數執行之前）**a** 另外：沒有任何 `php-fpm` 的祖先裡有兩個以上 `php-fpm`（第 13 項）。
   ~~**b** PID 1 的每一個直接子行程，名字都在安裝前基線裡 PID 1 子行程的名字集合裡~~ **b** PID 1 的每一個**後代**，
   (pid, 啟動時間, comm) 都在安裝前基線裡 PID 1 後代的集合裡（第 2 項）；安裝與開窗時 web 容器的 `State.StartedAt` 相同。
   正向對照 4 的違規也只准出現在它的起訖（±1 秒）之內，而且那段之內一定要出現：a 看到**真的 worker 底下**的 `lcfg`、
   b 看到 `lcorphan4`。
   （審核三之後，任何計數執行之前）**b 的「啟動時間」改成 `/proc/<pid>/stat` 第 22 欄**（開機後的 clock tick），不用
   `lstart`：`lstart` 是 `btime`＋tick／HZ，而 `btime` 隨每一次時鐘校正移動——實測 `btime` 1790117002、「現在 − uptime」
   1790117002.80，小數 0.80，所以往前 0.2 秒的 NTP 校正就讓每個 `lstart` 多一秒，pid 8 `cat` 不再等於基線，整個窗每個樣本
   都誤紅（這台機器 NTP 開著，這次開機休眠過 3 次）。tick 不隨時鐘移動。**基線本身**另加一條（第 2 項）：基線裡每一個 PID 1
   的後代都要在 PID 1 啟動後 10 秒內啟動（以 tick 比，不經時鐘）——`--reinstall` 在 `app:remove` 之後重取基線，一個之前的
   安裝或窗留在 PID 1 底下的孤兒原本會被它收進白名單。對照 1、4 的孤兒要是 **PID 1 的直接子行程**才算看到，對照 4 的還要是
   腳本回報的那個 pid（裁決條件 8 的字面，第 10 項）。對照 4 的 worker 在請求期間 fork 出來、還沒 exec 的那一瞬間
   （`comm` 仍是 `php-fpm`、父行程是那個 worker）歸給對照 4（第 12 項）。
2. 取樣器非空洞：時間窗內好樣本數 ≥ 窗長秒數，**相鄰兩個好樣本（含窗的兩端）相距不超過 1.0 秒**（審核第 3 項：原本只算總數，
   窗長一半的空白也過得了；shakedown 實測最大間隔 0.501 秒），每個樣本都至少有一個 `php-fpm` 行程。
   （審核三第 6 項，登錄）計數模式比 shakedown 多出的負載只有兩樣：重複次數與 `make test-e2-c-static`。後者實測 2.5 秒，
   期間取樣最大間隔 0.51 秒。重複次數帶來的是**窗長**（約 7,000 個樣本對 shakedown 的約 780 個），它的尾端只有計數執行本身
   量得到——若 I4-2 在計數執行裡紅，那是判準照字面在做事，不是放寬的理由。
3. `docker ps -a` 的容器集合（名稱、映像、建立時間、狀態）在時間窗開始與結束相同；窗內即時串流的容器生命週期事件，除了
   正向對照 3 的容器之外**一筆都沒有**，而正向對照 3 的 `create` 一定要被串流到。
   （審核二第 3、9 項）窗尾的第二個對照容器的 `create` 也一定要被串流到；停止串流時它還在跑。事件串流看的是**整台主機**的
   容器，不只 ddev 專案：**窗內主機上任何容器的生命週期活動都會讓 I4-3 紅**——長跑期間別在這台機器上起停任何容器。

**登錄、不判**：安裝目錄的 PHP（去掉註解之後）裡有沒有 PHP 手冊「程式執行」那一章的函式（`exec`、`shell_exec`、`system`、
`passthru`、`proc_open`、`popen`、`pcntl_exec`、反引號）——手工枚舉，記在 `archive.execFamilyScan`。（審核二第 13 項）
加上 `pcntl_fork`（在手冊的「行程控制」那一章，不是「程式執行」；加它是因為 I4-1a 的新分支就是為它寫的）。
（審核二第 8 項）另外登錄每個窗內樣本裡 ppid 0 的根（PID 1 以外）——docker exec 起的東西：健康檢查、`php occ`、
`runc init`、服務樹的 `bash -c …start.sh`——記在評分結果的 `registered.execRoots`，以出現的樣本數計。

### 紅案與計數

`--red-cases` 對 I0–I4 每一條至少一個突變，每個突變都要**多出**一個以該條款開頭的問題（相對於報告本來就有的問題）。
（審核第 9 項）只在計數模式才判的分支，在 shakedown 報告上用 `--red-cases --strict` 讓它紅：報告本身不乾淨沒關係，看的是
每個突變有沒有多出它那一條的問題。**先讓評分紅一次再跑計數**——在一份 shakedown 報告上，`--strict` 零 SKIP、零 GREEN。
（審核二第 7 項）每個突變另外指定「多出的問題必須含有的一段字」，把它釘在它要測的那個分支上：同一條款的另一個分支替它
變紅不算數（I0-2 的 git blob、I4-1b 的對照原本都只是被順帶抓到）；審核列出的每一個沒有突變的分支各補一個。
計數執行照 `findings/evidence/m3-locks/README.md` 的「Counted run: rules fixed before it started」四條。長跑期間不啟動、
不重啟任何其他 ddev 專案；開發實例上的宿主入口計數執行在開窗之前結束，窗內不對開發實例做任何事。

I0–I4 全過＝**`INSTALLS ELSEWHERE`**：M3 的完成判準（§5.5）在一台從發佈壓縮檔安裝的實例上成立，**限定**：那台實例不是全新的
（第 2 節）；「沒有伺服器端文件行程」量的是 web 容器裡的行程與容器的生命週期，不含經網路連到一個窗外就已經在跑的服務
（第 5 節）。兩個限定要跟著判定一起寫。

## 5. 明確不承諾

- `litecoreprobe` 不是全新安裝（第 2 節）。全新實例要新建 ddev 專案，擁有者這一輪沒選。
- nginx、Safari、Nextcloud 33（`info.xml` 宣稱 `min-version="33"`）沒量。
- 從 0.2.1 升級到下一版沒量；App Store 的簽章與完整性檢查（`occ integrity:check-app`）沒量——壓縮檔沒有簽章。
- 取樣間隔 0.5 秒：活不到 0.5 秒的行程可能漏掉。~~長壽的文件伺服器漏不掉~~（**原句不成立**，審核第 1 項）長壽的文件伺服器
  由 I4-1a／b 兩條一起擋，它們合起來仍漏掉：`occ` 行程底下活不到 0.5 秒、也沒有被留成孤兒的子行程（`occ` 是我們的儀器自己
  呼叫的，不在 php-fpm 底下）。一次性的 `exec()` 由「登錄、不判」的原始碼掃描補一部分。
- **在 php-fpm 行程裡面**解析 ODT（例如某條路由讀了檔案內容再處理）看不到——那不是另一個行程。唯一的證據是宿主原始碼：
  `EditorController` 只送 `engine/` 底下的預壓縮檔。
- 只取樣 web 容器。資料庫容器、router 不在範圍。I4-3 保證窗內沒有容器被建立或啟動；**一個窗外就已經在跑、經網路被呼叫的
  服務**不在 I4 的範圍（開窗時的 `docker ps -a` 狀態記在報告裡）。
- 入侵者與頁面是同一個使用者（admin）；另一個使用者帶 token 寫入是 finding 102 的量測，這一步沒有重做。
- （審核二第 8 項）**docker exec 起的行程樹不在 I4-1 裡**：它們的根 ppid 是 0，不在 php-fpm 底下、也不在 PID 1 底下。窗內有人
  以 `docker exec -d` 起一個文件伺服器，I4-1 看不到（exec 事件也被 I4-3 的濾器濾掉）。這些根登錄在 `registered.execRoots`，
  不判。app 自己沒有辦法走這條路（它只能在 php-fpm 裡跑）；會走這條路的是操作者與我們自己的儀器。
- I2-3 的射程是統計性的（§4 I2-3）；對照 4 的那一個 worker 在它的請求期間（±1 秒）讀它那一個檔不判紅（§3.5 具名極限）。
- （審核三第 13 項）**服務樹裡新長出來的子行程**（supervisord、apache2、mailpit 底下，例如一個 CGI）既不在 I4-1a／b 裡，也不在
  `execRoots` 裡；§5 前面只講了它們的孤兒。app 的程式碼跑在 php-fpm 裡，走不到那裡；列在這裡是因為它是量測沒涵蓋的地方。
- （審核三第 15 項）I2-3 只看 `/proc/*/fd`，不看 `cwd`、`maps`、`exe`；不可 dump 的行程讀不到 fd，會被靜默略過
  （`2>/dev/null`）。容器裡的行程都是 uid 1000，今天沒有這種行程。
- 「沒有 subreaper」只在兩條實際走過的路上量過（docker exec 根、php-fpm worker）；服務樹裡其他行程（supervisord、apache）
  背景化出去的子行程會落在哪裡沒有量。
- 工具的綁定不含 gitignore 掉的路徑（§3.3）。
- 重裝時 opcache 不會重新載入：mtime 固定（`build_m3_release.py` 的 `MTIME`），而 PHP 的 opcache 以 mtime 判斷檔案有沒有變。
  這一步的重裝用的是**逐位元相同**的檔案，所以快取的 bytecode 也相同；換成不同位元組的建置之後要重新載入 php-fpm。

## 6. 修訂紀錄

| 日期 | 內容 |
| --- | --- |
| 2026-09-29 | 起草，先於任何工具與執行。 |
| 2026-09-29 | shakedown 之後、任何計數執行之前：§3.4 補宿主衝突分支的觀察（`tokenOnServer` true）；§3.4 更正「版本與鎖都沒有 H3 的條款」——「等 5 秒不重載」鎖與權限 K6 有，沒有的是「再按一次」；I2-1 加開窗前置條件（開發實例安靜 ≥ 60 秒），理由是 shakedown 量到的 408 殘渣。判準本身沒有放寬。 |
| 2026-09-29 | **對抗性審核（opus，唯讀，19 項）與裁決（fable，H3）之後、任何計數執行之前。**審核全文與逐項處置在 `findings/evidence/m3-install/review-2026-09-29-opus.md`。改正三件寫錯的事實：`dist/` 沒有 `.gz`（有 117 個、30 個與發佈成員相同）；「app 起的行程一定是 php-fpm 的後代」（背景化的行程被 PID 1 收養）；「長壽的文件伺服器漏不掉」。加的判準：I1-2 開窗時重量、`app:getpath`、綁定自我測試；I2-1 健康檢查列數與窗後等 60 秒；I2-3 掛載開檔；I2-4 探針 app 路由；I3-5 報告時間在窗內；I3-6 紅案評分時重跑、報告 sha256；I3-8 記錄路徑舊新比對與模組 sha；I4-1b 孤兒與安裝前基線（因此重裝一次）；I4-2 相鄰間隔 ≤ 1.0 秒；I4-3 容器生命週期事件串流；三個正向對照。§3.4 依 fable 裁決保留 H3、改正理由（同一個使用者，不是 102）、H3 評分釘分支。判準沒有一條被放寬；全部先於任何計數執行。 |
| 2026-09-29 | 第二次 shakedown 之後、任何計數執行之前：取樣器改成一個常駐的 `docker exec` 迴圈，開檔持有者連 ppid 與 cmdline 一起記（§3.5）。理由是兩個儀器錯：一次 1.6 秒的取樣間隔（對照自己的 exec 拖慢）、一個 ps 沒看到的對照子行程。判準不動（間隔上限仍是 1.0 秒）。 |
| 2026-09-29 | **第二次對抗性審核（opus，唯讀，17 項，`findings/evidence/m3-install/review-2026-09-29-opus-2.md`）與裁決（fable，對照 4／subreaper／工具綁定，`ruling-2026-09-29-fable-controls.md`）之後、任何計數執行之前。**改正四件寫錯的事：拒絕「接到 PID 1 的血統」的理由（服務樹不在 PID 1 底下，血統規則不會把它算進去）；「評分函式一行都不改」（宿主入口的改了）；I2-3 的射程句（41 MB 0.096 秒送完）；§3.5 沒劃掉的舊取樣法與沒有證據檔的 0.509–0.515。收緊的判準：I1-1 要真的安裝（安裝前沒有 app 設定，重裝因此會刪掉殘留設定）；I1-2 空目錄與非一般檔、自我測試加兩種；I3-7 在等價性檢查之後開始；I3-8 紅案 exit、舊運算式逐字核對、tree 綁定；I4-1a 抓 worker 底下的 php-fpm；I4-1b 改成 PID 1 的後代以 (pid, 啟動時間, comm) 識別、基線與窗同一個容器生命週期；I4-3 窗尾第二個對照與串流存活；新增正向對照 4（真的 php-fpm worker，經 FastCGI）。改儀器：先 `find` 再 `ps -ww`、`lstart`、stat 的 ppid 解析、fd 記目標檔、stderr 排乾、對照 1 的 stdio、對照容器換映像。紅案每個釘在自己的分支上，從 45 個到 90 個。**判準沒有一條被放寬**；全部先於任何計數執行。 |
| 2026-09-29 | **第三次對抗性審核（opus，唯讀，15 項，`findings/evidence/m3-install/review-2026-09-29-opus-3.md`）之後、任何計數執行之前。**改正兩件寫錯的事：重裝「不是安裝」的理由（`Enable.php` 一律安裝，殘留設定只換分支）；對照 4 的豁免時長（程式碼是約 11 秒，改成到請求返回為止）。修掉一個會讓計數窗整窗誤紅的儀器錯：I4-1b 的身分改用開機後 tick，不用隨時鐘移動的 `lstart`。收緊的判準：基線的 PID 1 後代要在容器啟動 10 秒內；對照的孤兒要是 PID 1 的直接子行程、對照 4 的要是回報的 pid；等價性每列必須帶紅案 exit。改儀器：`LC_ALL=C`；對照移進 `try`。紅案 90 → 111：補上審核列出的每個沒被釘住的分支。**判準沒有一條被放寬。** |
| 2026-10-02 | **在 0.2.5 上重跑（交接的 J；`SPEC-M3-zstd.md` §6），任何 0.2.5 的執行之前寫下。**發佈＝`litecore` `7420418`（0.2.5）、壓縮檔 `602fe6bb…`（111,711,969 位元組、52 個成員，建置工具連建兩次逐位元相同），`release.json` 改寫成它（0.2.1 的紀錄另存 `release-0.2.1.json`）。自 0.2.1 的計數窗口以來，**判準條文不動**，變的是兩件機制，都在 `SPEC-M3-zstd` 的審核裡定案：(1) I0 的預期成員改由 `package_m3_engine.engine_members()` 從 MANIFEST 推出（每個路徑的 `.gz` 與 `.zst`），原本寫死只有 `.gz`——照舊的話 0.2.5 的發佈會漏掉 `.zst`、裝起來引擎全部 404；(2) I3 裡資產 runner 的報告帶 `criteria`（含 `SPEC-M3-zstd`），所以在 litecoreprobe 上也評 Z0–Z2、Z4-1，並多一臂 `firefox-nozstd`（3 次）。順序照上一次：`install --reinstall`（機器重開過，舊基線本來就失效）→ `equivalence` → 開發實例的宿主入口計數執行 → shakedown 窗口與 `--strict --red-cases` → 計數窗口。期間不得有任何容器生命週期事件（I4-3）。 |
| 2026-10-02 | **I3-8 的 PRE 列撤回、新增 I3-9～I3-12；工具改動、等價性檢查的重跑與任何 0.2.5 的窗口之前。**更正同日前一列的「判準條文不動」（那一列不刪，這一列取代它那一句）：那一列寫在等價性檢查跑之前；檢查跑出來 6 列只有 1 列相同（`equivalence.json`，2026-10-02T14:21:12Z），差異全部來自 0.2.1 窗口之後**刻意**改過、且已在新綁定上重新計數的評分（頁面與宿主 pin、資產派送 K2 的 A′ 儀器、鎖的 K9′／K10′）。照原文要綠只能把舊報告釘回舊綁定，那是造機械維持舊宣稱（「驗收判準的形式」第 4 節）。所以這是**撤回加新增**，不是「判準沒有一條被放寬」：撤回的是「現在的評分函式對 PRE 時代的計數報告評得與 PRE 時相同（含紅案 exit）」與「記錄路徑 PRE 對現在逐欄相同」——**前者之後沒有東西再檢查**；後者照跑、改成登錄。它們守的問題改由 I3-9～I3-11 以 2026-09-29 的四份開發計數報告為基線來守。保留照判：`transcription` 與 I3-8 的三時點綁定（加 `openssl`）。提案 I3-8′（`findings/evidence/m3-install/proposal-2026-10-02-i3-8-prime.md`）送 opus 對抗性審核（`review-2026-10-02-opus-i3-8-prime.md`，1 BLOCKING、6 HEAVY、5 LIGHT），**沒有照提案採用**。審核逐項處置：1 依擁有者裁示 B（下述）；2 採審核的選項 B 但更嚴（I3-11 只放行編排器一個檔，理由在 §3.3 末段）；3、4、8、9、10、12 照建議（I3-10、I3-9、I3-12、tree 綁定的 `openssl`）；5 因列撤回不再需要——任何地方都不保留列的歸因；6 即本列的更正；7 照建議（撤掉釘在 PRE 列與記錄路徑舊新比對上的紅案，每條新判準補釘分支的紅案，工具 commit → 重跑等價性檢查 → I3-7）；11 寫在 `findings/evidence/m3-install/RESULT.md` 的更正（0.2.1 的 Re-check 要用當時的工具跑）。**瀏覽器（擁有者裁示 B，2026-10-02）**：審核的 BLOCKING 是 Firefox 已被 snap 自動更新（156.0 → 157.0，2026-10-01 10:42 CST），建議 A（在 157 上重跑四支開發計數，並加瀏覽器版本相等的判準）。擁有者原話：「我不想因為firefox升級的關係重新量測」。裁示：J 在當下裝的 Firefox 上跑；開發基線用 09-29 的報告（Firefox 156.0）；不為瀏覽器重跑開發計數；**不設瀏覽器判準**，逐次 run 的 `version` 登錄；0.2.5 的 RESULT **開頭**寫明「開發實例的判定在 Firefox 156.0、litecoreprobe 的窗在 Firefox 157.0（Chrome 兩邊都是 151.0.7922.169）；窗裡任何一格紅，瀏覽器差異都是沒有排除的解釋」。既有的計數判定**不因升級重跑**，照它們量到的成立（Firefox 156）；之後的計數執行用當下裝的版本。I3-7 照舊——開發實例上宿主入口計數一次，在重跑的等價性檢查之後、開窗之前；它會跑在 157 上，那是原有協定，不是為瀏覽器重量。**順序**：工具 commit（`wasm_sdk_probe/` 乾淨）→ 重跑等價性檢查 → I3-7 → shakedown 窗口與 `--strict --red-cases`（零 SKIP、零 GREEN）→ 計數窗口。**web 容器在計數窗口結束前任何時候重啟**（I4-1b 的基線因此失效），就 `install --reinstall`（不帶 `--was`，`release.json` 已是裝著的版本），然後從等價性檢查重來：基線、等價性檢查、開發執行與兩個窗口要在同一個容器生命週期裡。**截止與計數**：I3-9～I3-12 適用 0.2.5 的窗口及之後，直到修訂紀錄另寫；這個閘門的判準**新增**在 0.2.5 的計數窗口落地時封閉，之後的顧慮變成 finding 或事後工作。0.2.5 還沒有任何窗口，沒有計數要歸零。0.2.1 的判定照舊，綁 0.2.1 與當天的工具。**如果這些永遠沒做**：0.2.5 沒有 `INSTALLS ELSEWHERE`。 |
| 2026-10-02 | **第二次對抗性審核（opus，唯讀，`findings/evidence/m3-install/review-2026-10-02-opus-i3-9-12.md`，0 BLOCKING、2 HEAVY、9 LIGHT）之後；新增 I3-13、I3-14，補第 8、10、11 條；任何 0.2.5 的計數窗口之前。**審核的結論是「計數窗口可以照現狀開」——沒有一個洞在今天的狀態裡被走到，第 1、2、4 項也能事後從計數報告的原始欄位查。主 session 仍選擇在計數之前把它們寫成判準（第 9 節只准在滿足之前新增）：第 1 項，編排器不在 runner 的 import 閉包裡，可是**它啟動並評分 runner**，而宿主入口自己的評分不釘臂——少了 H3 的 `conflict` 臂照樣 `LANDS`，I3-8～I3-12 全綠（審核實測）→ I3-13；第 2 項，等價性檢查之後的開發計數執行除了傳入的那一份之外沒有人看——I3-7 可以重跑到綠為止，這正是「間歇缺陷：一次綠不算數」那條教訓的反面 → I3-14。形式：I3-13 是逐實例性質（形式一）；I3-14 是工具封閉的枚舉（形式二，成員由 `runs/` 的原始欄位選出，與 I3-10 互補）；第 11 條的 git 重算把「編排器自己記的」換成「誰重跑都一樣的」。**被逼出來且指名**：審核第 1～11 項逐項處置寫在審核檔的開頭。**計數語意**：沒有任何 0.2.5 的計數窗口，沒有計數要歸零；本輪先前的等價性檢查（`e565d422` 的 `equivalence.json`）、I3-7（`m3-host-entry/runs/2026-10-02T154130Z.json`）與 shakedown（`shakedown/2026-10-02T154722+0000.json`）是用舊工具跑的，都要照新工具重跑——那份 I3-7 因此變成開發基線的一份（它開始於新的等價性檢查之前，照第 10 條被選進來，要照第 9～11 條被判），新的 I3-7 再跑一次。截止照同日第二列（新增在 0.2.5 的計數窗口落地時封閉）。**如果這些永遠沒做**：同日第二列——0.2.5 沒有 `INSTALLS ELSEWHERE`。 |
