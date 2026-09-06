# 091：出貨的殼層自 087／088 修法之後就沒有被任何 generation 宣告，而 revert 正好落在那裡

**發現於 2026-09-06 的 revert 演練第二半**（W-5），
證據在 `findings/evidence/queue-v12-cutover-revert-rehearsal/`。

## 現象

樹完全還原、`git status` 乾淨的狀態下，對出貨頁面跑一輪產品路徑網：

- runner 給 **38 PASS / 2 NE、`ok: true`**；
- `check_usable_editor.py --report` 給 **`ok: false`**。

```
servedShell.bundle                     e2/editor-shell-v2-bundle-v43.json
servedShell.declaredSha256             7e99d3a3b8ba789b…
servedShell.servedSha256               f89d7bb9d1438ef2…
servedShell.differingPaths             ["web/e2-editor-app.js"]
servedShell.differsOnlyInTheEntrypoint true
```

## 成因，量出來的

`e2/editor-shell-v2-bundle-v43.json` 凍結於 2026-08-27（finding 084 的修法），
它宣告 `web/e2-editor-app.js` 是 `28e03e5bc9fcb8c4…`。

樹今天服務的是 `5aeae0e1dbfe492d…`。那顆頁面在 finding 087 的修法（`681a22b0`）、
finding 088 的修法（`3d3d0323`）落地時各動了一次，`make dist/e2-editor-app.js`
（finding 090）又同步了一次——**而這中間沒有凍過任何一個新的 generation**。

工具自己說得很清楚（`v43-vs-the-tree-after-restore.json`，樹還原後量的）：

```
manifest is out of date: added=[] removed=[] changed=['web/e2-editor-app.js']
refusing to rewrite … A changed shell needs a NEW generation …
```

bundle 裡其他 12 個檔案全部還對得上，只有 entrypoint 一個不對。

## 為什麼一路沒有東西抓到

**已押的每一筆 soak 都是候選（candidate）run**，而 served-shell 檢查對候選 run
有一個**刻意而且很窄的豁免**：候選 run 帶著 `candidateCutover`，它的 entrypoint
雜湊被要求等於 cutover 將要寫入的那顆頁面。十筆 soak、三輪 4a、三筆游標 diagnostic、
一次 ODT 來回，全部走那個豁免或走它們自己的探針。

**這次演練的第二半，是 087／088 修法落地之後第一次跑純出貨頁面的網**，第一次跑就紅。

已押的證據不受影響：那些 run 本來就是照那個豁免判的，而豁免仍然成立。

## 影響：revert 的目的地不是一個被宣告的狀態

這才是它擋門的地方。cutover 的第 3 步會凍一個新 generation（演練裡是 v44，
`78c23684…`，post-cutover 那一輪 `differingPaths: []`、判讀工具 `ok: true`——
**第 3 步是有效的**）。但 revert 把 `MANIFEST` 退回 v43、把頁面退回 `5aeae0e1`，
而那個組合**沒有任何 frozen generation 描述它**。

換句話說：**cutover 之後的狀態是宣告過的，cutover 之前的狀態不是。** revert 從一個
合法狀態退回一個不合法狀態。

## 沒有做的事，以及為什麼

最自然的處方是**現在就替目前的殼層凍一個 generation**，讓 revert 有地方可落。
我沒有做，兩個理由：

1. 那會在**閘門正在對這棵樹計數的時候**改動樹的宣告身分。已押十筆 soak，而
   `servedShell` 是每一筆報告都記下的欄位。改 `MANIFEST` 是換儀器。
2. 「凍了之後才發現還要改」是這棵樹已經付過學費的事（2026-08-22 一天凍三次，
   其中一次凍得太早）。cutover 本身還沒發生，殼層還可能再動。

登錄，不修。處置交給使用者／裁決。

## 順帶：這正是「演練一次」買到的東西

08-28 那一輪的結論是「**不是 flip 會失敗，而是還有別的東西得跟著 flip**」——那次
找到的是第 3 步。這一輪找到的是第 4 件：**flip 回去的目的地也得是一個被宣告的
狀態**。兩次都不是靠讀計畫發現的，是靠真的做一次。

---

## 更正（2026-09-06，裁決 E-6 指出，我覆核後確認）

### 一、「為什麼一路沒有東西抓到」是錯的——有東西守著，只是沒有人跑它

上面那一節說「這次演練的第二半，是第一次跑純出貨頁面的網，第一次跑就紅」。**紅的
不只那一輪。** 樹自己就有守衛：

```
$ python3 -m unittest tests.test_e2_c_shell_bundle
tests/test_e2_c_shell_bundle.py::test_the_real_manifest_matches_the_real_tree
FAILED --  manifest is out of date: added=[] removed=[] changed=['web/e2-editor-app.js']
Ran 12 tests … FAILED (failures=1)
```

它跑在 `make test-e2-c-static`（Makefile:2804）底下，而
`make test-e2-c-reachability`（Makefile:2894）會另外唯讀跑一次凍結器，今天也是
exit 1；兩個目標都在 Makefile:240–244 的總目標裡。

**這是 `AGENTS.md` §3 的第一種登錄（有東西守著），我把它寫成了第三種（沒有東西
可守）。** 這正是我在 2026-08-29 犯過一次、並且寫進規矩裡的那個錯：把「有洞」和
「沒洞」寫成同一句話。

差別是實質的：真正的缺陷不是「沒有守衛」，是**守衛紅了而沒有人跑它**——而處方也
因此不同（把跑守衛納入驗收，裁決 E-3 已經這麼做了），不是去發明一個新的守衛。

### 二、「頁面動了三次」不精確，而且日期歸錯了

分開講才對：

| | 動了幾次 | 何時 |
| --- | --- | --- |
| **原始碼** `web/e2-editor-app.js` | **兩次** | `681a22b0`（087，09-05 00:29 CST，`28e03e5b` → `74c89ba0`）、`3d3d0323`（088，00:55 CST，→ `5aeae0e1`） |
| **服務的那份** `dist/e2-editor-app.js` | **一次** | finding 090 的 `make`（約 01:3x CST，soak run 1 之前） |

所以：

- **靜態守衛**（比 `web/` 對 manifest）**從 087 的修法起就紅**；
- **`servedShell`**（比瀏覽器實際服務的位元組對 manifest）**從 090 的 `make` 起才
  不符**——在那之前 `dist/` 還是 `28e03e5b`，對得上 v43，**而那正是 2026-09-03 那
  次演練的 revert 能夠 reconcile 的原因**。

本 finding 的**標題（「自 087／088 修法之後」）對原始碼是對的，對產品早了一步**。
標題不改（檔名是引用點），更正記在這裡。

### 三、2026-09-03 已經有一份 step-3 演練，我不知道

`findings/evidence/queue-v12-cutover-revert/RESULT-2026-09-03-step-3-rehearsed.md`
在 09-03 就對 `e2-editor-v12` 做過完整的 cutover／revert，含步驟 3，而且**revert
之後那一輪 reconcile 是 `true`**（頁面回到 `28e03e5b`）。同一個目錄裡還有一份
09-03 的 v12 ODT 來回。

我 09-06 的演練仍然有價值——它是在**移動之後那顆頁面**（`20f09cc9`）上做的，而
09-03 那份是在 `3dfdcfef` 上——但我把它寫成「W-5 從未被演練過」（照抄計畫裡那句
早已過時的文字），而且引的前一次是 2026-08-28 的 v11 版，不是 09-03 的 v12 版。

**教訓是我已經寫下來過的那一條**：開新的量測之前先重讀自己的樹。這一次的代價只是
重做了一次已經做過的事——但**同一個疏漏也讓我把「沒有東西抓到」寫進了 finding**。
