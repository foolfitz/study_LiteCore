# fable ruling — finding 133 (a save in flight across a page freeze is declared dead), 2026-10-12

Brief: `findings/evidence/133/ruling/brief.md`. Judge: fable (subagent, read-only). Everything below was re-derived from the committed files named in the last section; the main session's readings were treated as claims.

## 0. Ruling in one screen

| Q | Ruling |
|---|---|
| **Q1** | **A′ — 修了再計數。** Fix in `sdk/document-sdk.js` only; new shell generation **v63**; host **0.2.14**; the number 0.2.13 is retired (never shipped). Not B (K8 is right to be red; re-ruling its premise would be building machinery to keep a check green), not C (removes the trigger, keeps the cause, and gives up the one save COOL's own research called the last reliable moment). |
| **Q2** | Where: the SDK's deadline timer (`_request`, `document-sdk.js:186-190`). Why not the session subclass or the page: §2. Criteria **133-U** (unit, deterministic) and **133-B** (browser, per-instance with a positive control and a guard-burn count), both in §9.20 below, written before any run. Red cases: the committed probe runs 1 and 3 + shakedown `113020Z` (browser), and the new unit test run against the pre-fix SDK (must be shown red and committed). Re-open: the whole count chain (nothing counted exists); 131-B/121-B/129-B/130-U/128-B and the owner's §9.18 hand test **stand** on v62 with the stated reason, conditional on the v63 manifest differing from v62 in `sdk/document-sdk.js` only. |
| **Q3** | **K8 unchanged.** It did not misjudge — the page really died and no PUT landed — so §34.4 gives no licence to touch `check_m3_locks.py`; ledger stays 因執行而修 11 / 因審核而修 6. K8 keeps its premise (page truly stopped, lock expired, the save after thaw lands) and, on 0.2.13+, additionally carries a save across the freeze; that is the product's behaviour under the same scenario, not drift of the check. The 133-specific measurement lives in the probe (a diagnostic, not a counted check) and the unit test. |
| **Q4** | Five corrections, none changing the disposition: §4. |

## 1. Q1 — 處置與理由（給擁有者）

**裁決：A′。先修，修在 SDK，重新打包成 v63／0.2.14，再跑計數鏈。0.2.13 這個號碼作廢，不出貨。**

- **這是 127 帶進來的退步，而且剛好打在自動儲存要保護的那一刻。** 0.2.13 之前 27 次 K8 全部 `ready`（§6 表），0.2.13 的頁面 5 次紅 3 次。成因量到了：切到背景那一刻送出的存檔（`e2-editor-app.js:2629-2633` → `:2605-2618`），逾時計時器用的是 `setTimeout`（`document-sdk.js:186-190`），頁面停住 330 秒後它過期了約 150 秒；解凍時它和 Worker 的回覆賽跑；它贏，session 就把 `TIMEOUT` 當成「引擎死了」（`editor-session.js:16`、`:321-325`），頁面寫「自上次儲存以來的內容不會回來」（`e2-editor-app.js:753`）。引擎沒死（探針第 2 次回覆在解凍後 271 ms 到，存檔照常落地）。
- **不選 B（照出貨、K8 記紅）**：K8 判得對，不是檢查的錯。把 K8 的前提改掉來讓它綠，正是 CLAUDE.md §4 禁止的「造機械維持宣稱」。而且 §9.4「計數」要六支 M3 runner 全過，K8 紅＝鎖的閘門不成立，計數本來就不能算。
- **不選 C（拿掉切背景就存）**：它拿掉的是觸發，不是成因。任何在途請求跨過凍結都會走同一條路（手動存檔、閒置存檔、甚至一次打字的 `editorAction`——讀碼成立、未量）。而「切到背景立刻存」是 §8.1 Q3 採用的理由：分頁被丟棄之前最後可靠的時機。為了讓一格綠而拿掉產品最有價值的一次存檔，是倒過來的交換。
- **真實世界多常碰到：未量，我不替它估。**但要碰到它的條件（切走分頁或闔上筆電、接著系統睡眠、睡超過剩下的期限）是每個筆電使用者每天做的事；不能用「沒量過」當成「不會發生」。
- **代價**：修法是 SDK 一處、十行以內；一輪單元測試＋一輪 6 次的探針（約 1 小時）＋打包與重綁（約 1 小時）；計數鏈本來就一次也還沒算，重跑不是額外成本。擁有者在 §9.18 測的是頁面 `d761f1ce…`，這份位元組**不動**；v63 只多 SDK 的修法，發佈說明要寫明這一點。出貨中的 0.2.12 不動（它只在手動存檔跨過凍結時曝露，讀碼成立、未量；修法隨 0.2.14 出）。

## 2. Q2 — 修在哪裡、判準、紅案、重開範圍

**位置：`sdk/document-sdk.js` `_request` 的逾時回呼。** 不在 E1-C（`e1/editor-shell-bundle-v2.json` 的 `included` 只有 editor-shell 三檔＋input 兩檔），在 E2 殼層 bundle（`build_e2_c_shell_bundle.py:674` SCOPE 含 `sdk`）→ v63。

**行為（不是程式碼）**：上鏈時記 `dueAt = now + timeoutMs`（`now` 用 `performance.now()`，單調時鐘，NTP 校時不能假造「遲到」）。計時器到期時，算 `late = now − dueAt`：
- `late ≤ L`（**L = 2000 ms**）：照舊 `failAndCancel(SdkTimeoutError)`——準時到期仍然是逾時，`cancel` 照送（`:170-181`）。
- `late > L`：頁面曾經停住；**不判失敗、不送 cancel**，`dueAt = now + G`（**G = 10 000 ms**），重新 `setTimeout(G)`，把新的 timer 寫回 `entry.timer`（讓 `_cleanupPending :214` 與回覆路徑照舊清掉）。再到期時再看一次 `late`。最終的 `SdkTimeoutError.details` 要帶 `extendedMs`（累計延長）與 `extensions`（次數）——錯誤訊息帶酬載（CLAUDE.md §7）。
- 一律適用所有請求（save 180 s、getState 30 s、render 60 s、open 120 s）；`signal` 中止不變。L、G、`now` 可由 `createDocumentEngine` 的 options 注入（預設如上），只為了讓單元測試不用等 10 秒。

**為什麼不是另外兩處**：
- **v2 session 子類別**：只攔得到它自己包的操作。`save()` 的 TIMEOUT 在基底類別的 drain `catch` 裡就封佇列（`editor-session.js:321-325`），子類別要搶在前面得重抄 `save()` 連同 `finalize`（`:558-583`），而且只救 save——getState／editorAction 跨凍結照死。修在這裡＝修一個症狀。
- **頁面**（Page Lifecycle `freeze`／`resume`）：只有 Chrome 發這兩個事件，系統睡眠不發；頁面也拿不到 SDK 的 pending 表，只能用 `signal` 中止自己的存檔再於 `resume` 補存——多一次存檔、多一個機制，仍然只救 save。
- 這一題的本質是「期限把頁面停住的時間算進去了」，期限住在 SDK，就修在 SDK。它**不改**「逾時＝引擎死了」這條規則（那條在 E1-C），而是讓「逾時」重新只在頁面在跑的時間裡成立。

**判準**：見 §9.20 的 133-U、133-B（寫在任何執行之前）。**N 的理由**：修法前的失敗率是 5 次 3 次，但它由解凍後被節流的計時器喚醒相位決定（三次探針：+182、+188、+795 ms，§4 第 2 點），所以「連續 N 次綠」本身不是證據——計時器輸的那幾次在沒修的頁面上也是綠的。133-B 因此要求：每一次都有「存檔真的跨過凍結」的正向對照，**而且**至少一次探針看到守衛燒過（計時器先到、被重新上鏈、回覆接著到、存檔落地）。燒過的每一次是一筆逐實例的證明；沒燒的只是對照。6 次之內看不到守衛燒過的機率，照 3/5 算是 0.4⁶≈1%，照 27% 的喚醒假說算是 15%，所以規則寫成「6 次；守衛 0 次就再 6 次，最多 12」。

**重開範圍**：
- **全部重跑**：計數鏈（六支 M3 runner、production UI、autosave、產品路徑網）——它就是計數，而且一格都還沒算。K8 的期望照 §9.4「計數」不變。
- **可以站在 v62 的量測上**（寫明理由）：131-B、121-B、129-B、130-U、128-B、§9.18 擁有者手測。理由：頁面 `d761f1ce…` 位元組不變；修法在它們的路徑上只多「上鏈時記一個時間戳、到期時比一次」，新分支只在某個期限遲到超過 2 秒時才進得去，而那些量測裡沒有任何期限到期過（報告全部以 `ready` 結束；有 TIMEOUT 就會是 `recoverable-error`）。**條件**：v63 manifest 與 v62 的差異必須只有 `sdk/document-sdk.js`、digest、`frozenDate`；多一個檔，這一段就不成立，那幾格重跑。
- **E1-C**：不受影響（SDK 不在 bundle 裡）；凍結後 `check_e1_c_bundle_intact.py` 仍須 intact。
- **產品路徑判讀副本**：兩個常數不變（頁面同、`repointed_page()` 只看頁面與 v8 manifest）；用同一個呼叫重算一次確認。

## 3. Q3 — K8

- K8（`SPEC-M3-locks-and-permissions.md:86`；`check_m3_locks.py:606-622`，評分 `:958-982`）照舊。它的前提三句都還成立；0.2.13 起它多載一次跨凍結的存檔，是產品在同一情境下的新行為，不是檢查漂移。§9.4「計數」已經預見 auto 紀錄（`:965-970` 的註解，證人 `075616Z`），只是沒預見賽跑。
- 不加 133 專屬臂到 `check_m3_locks.py`：§34.4 沒有證人（檢查沒判錯），§34.6 不長判準文字。133 的量測放在探針與單元測試。
- `probe_k8_frozen_recovery.py` 是診斷工具不是計數檢查：修它的 `score_arm` `KeyError: 'original'`（探針的 record 少了 runner 會記的 `original`）與加一個 `rearm` logpoint，**不記進 §34.4 的帳**，交接裡另列一行「探針改了什麼」。
- 具名限制（已存在）：K8 只有 Chrome（Firefox 沒有凍結手段）；K8 單格綠不能證明 133 修好（計時器輸的那一邊本來就綠）。

## 4. Q4 — 主 session 讀錯或講過頭的

1. **commit 認錯**：K8 期望的改動是 `65e90f62`（`check_m3_locks.py` +22 行），不是 brief 寫的 `ce758882`（那筆只是證人重判的原始輸出）。
2. **「計時器 vs 回覆的賽跑」少講了一半**：三次探針裡，過期 300 秒的 30 秒閒置自動儲存計時器與 180 秒存檔期限在同一個瞬間一起到期（run 1：333985／333987；run 3：334014／334016；run 2：334659，在回覆 334135 之後）。也就是說解凍後過期的計時器是**成批在一次喚醒**時放出來的，相位 +182、+188、+795 ms；回覆固定在 +271 ms 左右。賽跑的變數是喚醒相位（讀碼假說：Chrome 對 hidden 分頁的計時器對齊），不是回覆快慢。這決定了 133-B 不能只數綠燈（§2）。
3. **「引擎其實沒死」只有跨 run 的證據**：runs 1／3 看不到遲來的 `resp save 18`，是因為 `resp` logpoint 放在 `document-sdk.js:236`，在 `:234 if (!entry) return;` 之後——被取消的請求的回覆**照構造就不會被記到**。finding 133 把它寫成事實；應寫成「由 run 2 推得」。修探針時把 logpoint 移到 `:233` 之前（或加一個）就能在同一次裡看到。
4. **「1–2 ms 之後」**：run 3 是 5 ms（freezeAt 3416 → `autosaveNow` 3421）。小事，照 §11 登錄。
5. **宿主版本**：brief 把修法的代價寫成「v63、重綁、重跑」，漏了宿主要換號。引擎包的 buildId 由內容算（`check_m3_assets.py:99`），SDK 一改 buildId 就變；同一個 0.2.13 名下有兩份不同的引擎包，是「版本是身分」那一課的形狀。所以是 **0.2.14**（`info.xml` 一行），不是 0.2.13 重裝。

其餘核對無誤：27 次 K8 全 `ready`（15 筆 counted＋12 筆 shakedown，`2026-09-28T112341Z`…`2026-10-12T075616Z`）；chain 在 12:09:51Z 停在 locks 21/22；探針 2/3；`TIMEOUT` ∈ `RECOVERY_ERRORS`（`editor-session.js:15-22`）；save 的 180 000 ms 在 `editor-session.js:558-562`。

## 5. COOL（co-26.04）的先例——借得到什麼、借不到什麼

- **COOL 的用戶端沒有任何「每個請求一個期限」。** `browser/src/app/Socket.ts` 的計時器只有 access-token 到期（`:342-362`）、slurp（`:849-878`）與重連（`:523`、`:536`、`:613`）。「伺服器死了」唯一的訊號是 WebSocket 的 `onclose`（`:482`），之後**透明重連**（`_scheduleReconnect :664-669`，busy 顯示 Reconnecting…），重連時 `load` 帶 `_reconnecting`（`:429-433`）；使用者看到的是 snackbar「The connection to the document has been lost.」（`:650-658`），透明重連失敗才是「Well, this is embarrassing…」（`:592-601`）。**沒有任何一句說未存的內容不會回來**——因為文件與未存狀態住在伺服器。
- **存檔的期限在伺服器那一側**，用伺服器自己的 `steady_clock` 量（`wsd/DocumentBroker.hpp:984-987`、`:1252-1255`），值是載入時間的 4 倍＋0.5 秒、最少 5 秒（`wsd/DocumentBroker.cpp:3889-3892`）。逾時只把那次存檔記成失敗、結束 save activity（`:679-683`），**不殺文件**；「kit 斷線」是另一個獨立的判定（`:671-676`）。「慢」與「死」是兩個述詞——這是我們該借的那一條。
- **能見度**：COOL 完全沒有 `visibilitychange`（整個 `browser/src` 只有 Debug.ts 提到；`browser/js/global.js` 沒有）。它用 window `blur`／`focus`（`Map.js:1437`、`_onLostFocus :1471-1476`、`_onGotFocus :1485-1494`）：失焦後起 `out_of_focus_timeout_secs`（預設 300 秒，`coolwsd.xml.in:94`；`Control.IdleHandler.ts:140-142`）才 `_dim()` → 送 `userinactive`（`:226-232`），蒙版寫「Idle document - please click to reload and resume editing」（`:45`）；不活躍時外送訊息直接丟掉（`Socket.ts:200-209`）；回來時 `useractive`（`:68-81`）。**切到背景不存**；離頁是 `beforeunload` 關 socket（`browser/src/main.js:145-150`），由伺服器在最後一個 session 走掉時 `autoSaveAndStop("dead")`（`DocumentBroker.cpp:579-594`）、閒置 30 秒／每 5 分鐘自己存（`coolwsd.xml.in:69-70`、`DocumentBroker.cpp:4138-4146`）。
- **COWASM 與我們同形，但沒有「死」的訊號**：同一套用戶端對著頁內的 coolwsd 講話，socket 是 `FakeWebSocket`（`browser/js/global.js:1406-1426`：`readyState` 永遠 1、`close()` 空的、`send` → `postMobileMessage`），回覆由另一條執行緒經 `MAIN_THREAD_EM_ASM` 推回（`wasm/wasmapp.cpp:36-57`、`:75-79`）。所以瀏覽器版那個 `onclose` 在 COWASM 根本不會發生；而頁內 coolwsd 的存檔期限用 `steady_clock`（Emscripten 的單調時鐘），**和我們的 `setTimeout` 一樣會把凍結的時間算進去**。樹裡沒有任何 COWASM 在頁面凍結下的量測，我不替它宣稱有沒有同一個缺陷。
- **類比的邊界**：COOL 的引擎在伺服器，時鐘與用戶端的永遠分開跑，所以「用戶端等太久」從來不是活性判定；我們的引擎在同一頁的 Worker 裡，跟頁面一起被凍、一起解凍，而 `TIMEOUT` 是我們唯一被當成活性訊號的東西（真正的死訊是 `WORKER_CRASHED`）。借來的只有一句：**期限只量引擎有機會跑的時間，而且逾時不等於死**——這正是 §2 的修法做的事。COOL 把期限綁到載入時間（4×）的做法記在 §9.20 工作項，不在這一輪做。

## 6. 給 `SPEC-M3-autosave.md` 追加的 §9.20（zh-TW，只追加，原樣貼上）

### 9.20 finding 133 的裁決：修在 SDK、v63／0.2.14、判準 133-U／133-B（fable，2026-10-12，只追加；`findings/evidence/133/ruling/fable-ruling.md`）

**裁決：A′——修了再計數。**0.2.13 的計數鏈停在 locks shakedown K8 `frozen` Chrome 0/1（`m3-locks/shakedown/2026-10-12T113020+0000.json`），沒有任何計數執行開始。修法在 `sdk/document-sdk.js`；殼層 generation **v63**；宿主 **0.2.14**；0.2.13 這個號碼作廢、不出貨。擁有者 §9.18 測的頁面 `d761f1ce…` 位元組不變。

**量到的機制**（`m3-locks/k8-recoverable-2026-10-12/probe-2026-10-12T121440+0000.json`，三次）：CDP 凍結前頁面先 `hidden`，§9.2「切到背景」在 2–5 ms 內送出 `save`（請求 18，期限 180 000 ms）；凍結約 330 秒；解凍時過期的計時器成批在一次喚醒放出（相位 +182／+188／+795 ms），Worker 的回覆約 +271 ms；計時器先到就 `TIMEOUT` → `RECOVERY_ERRORS` → `recoverable-error`（2/3），回覆先到就兩次存檔都落地（1/3）。0.2.13 之前 27 次 K8 全 `ready`。

**修法（行為）**：請求上鏈時記 `dueAt = performance.now() + timeoutMs`。計時器到期時算 `late = performance.now() − dueAt`：`late ≤ 2000 ms` 照舊逾時（`failAndCancel`，cancel 照送）；`late > 2000 ms` 視為頁面曾停住——不判失敗、不送 cancel，以 10 000 ms 重新上鏈、再看一次。所有請求一律適用；`signal` 中止不變。最終的 `SdkTimeoutError.details` 帶 `extendedMs` 與 `extensions`。L、G、`now` 可由 options 注入（只給測試）。不動 `editor-shell/editor-session.js`（E1-C）；不動頁面；不動 Worker。

**判準 133-U（逐實例；單元，`sdk/tests/document-sdk.test.mjs`）**：
- U1：期限遲到 > L 到期、寬限內回覆 → 請求 resolve，0 個 cancel。
- U2：期限遲到 > L 到期、寬限內沒有回覆 → 以 `TIMEOUT` reject，恰 1 個 cancel，`details.extensions == 1`。
- U3（既有 `:249`「timeout rejects and emits a best-effort cancel」）：準時到期 → 行為不變。
- **紅案**：U1 在修法前的 SDK 上必須 FAIL，輸出 commit 到 `findings/evidence/133/unit/`；U3 在修法後仍 PASS。*若永遠沒做：133 不算修好，v63 不凍。*

**判準 133-B（逐實例＋正向對照；瀏覽器，Chrome）**：儀器 `probe_k8_frozen_recovery.py --repeats 6`，0.2.14 的宿主、頁面 `d761f1ce…`、新 buildId。每一次都要：
- (a) 正向對照：`diag` 裡 `autosaveNow hidden` 與 `req save` 的時間 < `freezeAt + 1000`（真的有一次存檔跨過凍結）；
- (b) `save1State.state == "ready"`；`host.saves[-1].trigger == "manual"` 且最後一次 attempt 204；`serverAfter.sha256 == host.saves[-1].sha256`；`copiesAfter == []`；之前每筆 `trigger == "auto"`；
- (c) `diag` 裡沒有 `blockQueue`、沒有 `fail save`；
- (d) 若有 `rearm`（新 logpoint，修法的重新上鏈那一行），其後 10 000 ms 內要有 `resp save` → 這一次算「守衛燒過」。
- 6 次全過 (a)–(c)，且守衛燒過 ≥ 1 → 成立。守衛 0 次 → 再 6 次（最多 12）；12 次仍 0 → 瀏覽器這一格 NOT_ESTABLISHED（登錄「12 次賽跑都是回覆先到」），由 133-U 承載修法，計數照跑。
- **紅案**：已 commit 的探針 run 1、run 3 與 shakedown `113020Z`（沒修的包上 (b)(c) 都紅），不重跑。*若永遠沒做：133 不算修好，0.2.14 不計數。*

**預測（寫在執行之前）**：守衛燒過 2–5 次／6；燒過的每次恰 1 次 `rearm`，`resp` 在解凍後 400 ms 內；auto 紀錄 412（帶 token）→ 204（不帶），`lock.lostBy == "save"`；manual 204；計數鏈的 K8 1/1；鏈上其他格與 0.2.13 的期望逐格相同。

**重開範圍**：計數鏈全部重跑（本來一格都沒算）。131-B、121-B、129-B、130-U、128-B、§9.18 站在 v62 的量測上，理由：頁面不變，新分支只在期限遲到 > 2 秒時可達，那些量測沒有任何期限到期過；**條件**是 v63 manifest 與 v62 只差 `sdk/document-sdk.js`、digest、`frozenDate`。E1-C 不受影響，凍結後 intact 照查。產品路徑判讀副本常數不變（重算一次確認）。

**具名限制**：
- **L-133-band**：凍結或睡眠若在期限前不到一次回覆時間、或期限後不到 2 秒內結束，計時器仍可能先到；寬度約 L。
- **L-133-suspend**：系統睡眠後 `setTimeout` 會不會過期看平台時鐘，任何平台都沒量；修法在它過期時生效，不過期時本來就沒事。
- **L-133-hidden-verdict**：分頁長時間在背景被節流時，真的死掉的引擎可能要等分頁回到前景才被判死（每次遲到都重新上鏈）。未量。
- **L-133-firefox**：K8／133-B 只有 Chrome。

**K8 與 §34**：K8 不改；`check_m3_locks.py` 不動；帳不變（因執行而修 11／因審核而修 6）。探針的 `score_arm` `KeyError: 'original'` 與新 logpoint是診斷工具的修改，不記帳、交接列一行。

**宿主**：0.2.14 只是 `appinfo/info.xml` 版本＋新引擎包（buildId 由內容算）；宿主程式碼不動。

**工作項（不是判準）**：COOL 把存檔期限綁到載入時間（`wsd/DocumentBroker.cpp:3889-3892`，4×＋0.5 秒、最少 5 秒）；我們的 180 秒常數沒有量測依據，下一輪可量。探針的 `resp` logpoint 移到 `document-sdk.js:233` 之前，讓被取消請求的遲到回覆也看得到。

## 7. Steps, in order (each commits before the next)

1. Append §9.20 verbatim to `specs/SPEC-M3-autosave.md`; add a status line to `findings/133-…md` (處置 A′、v63／0.2.14、判準在 §9.20); commit.
2. Write U1/U2 in `sdk/tests/document-sdk.test.mjs` (U3 exists at `:249`). Run against the **pre-fix** SDK → U1 FAIL; save the output under `findings/evidence/133/unit/red-on-<tree sha>.txt`; commit tests + red output.
3. Implement the SDK change (§2 behaviour; options `lateDeadlineMs`, `lateDeadlineGraceMs`, `now`). `node --test wasm_sdk_probe/sdk/tests/*.test.mjs` green (U1–U3), `make test-e2-c-static` exit 0, `check_e1_c_bundle_intact.py` intact; commit.
4. One adversarial review (opus; codex only if its MCP connects — it did not this session) of the SDK diff and U1/U2 **only** (product change; no check is reviewed, §34.3). Dispositions in `findings/evidence/133/review/`; any BLOCKING dispositioned before step 5; commit.
5. Probe: fix `score_arm`'s missing `original`, add the `rearm` logpoint + its `EXPECT` line, move/add the `resp` logpoint before `:234`; commit (tool change, not a check; say so in the handoff).
6. `make e2-c-assets`; freeze **v63** (`build_e2_c_shell_bundle.py`, comment block names 133); verify the manifest diff vs v62 is `sdk/document-sdk.js` + digest + `frozenDate` only; static exit 0; commit.
7. `package_m3_engine.py` → new buildId; archive `build/archive/host-0.2.14-engine-<buildId>/`; `check_engine_decoded.py`; host `info.xml` → 0.2.14; install/upgrade on ddev as §9.11 did; host commit.
8. Re-pin the seven runners (buildId, version, host commit, shell digest; page sha unchanged) and confirm the product-path judge copy's two constants; static exit 0; commit (binding; K8's expectation untouched).
9. Run 133-B (`--repeats 6`, extend per §9.20); write the per-run table (freezeAt, thawAt, rearm?, resp at, end state, saves) in `findings/evidence/133/133-b/README.md`; commit.
10. Count chain for 0.2.14 (same shape and STOP rule as `chain-2026-10-12.sh`, identity lines updated), red cases, `RESULT-0.2.14.md` with findings 127–133 by their own criteria; commit.
11. Release text: 0.2.13 never shipped; v63 = v62 + `sdk/document-sdk.js`; the owner's §9.18 hand test stands for the page; named limits L-133-*.

## 8. Numbers relied on, with sources

| Number | Source |
|---|---|
| chain: page_honesty exit 0 (11:30:19Z); locks exit 1, STOP (12:09:51Z) | `findings/evidence/m3-production-ui/runs-0.2.13/chain-2026-10-12.out` |
| K8 chain cell: freezeAt 3534, thawAt 333880, `recoverable-error` | `m3-locks/shakedown/2026-10-12T113020+0000.json` |
| 27 earlier K8 records all `ready`: 15 in `m3-locks/runs/`, 12 in `m3-locks/shakedown/` (`2026-09-28T112341Z` … `2026-10-12T075616Z`) | python3 -I walk of every `arm == "frozen"` record |
| Probe run 1: freezeAt 3425; `autosaveNow hidden` 3427, `req save 18` 3428; thawAt 333805; idle-autosave 333985; `fail save 18 TIMEOUT` 333987 (+182); `blockQueue recoverable-error editor-recovery`; `host.saves == []` | `probe-2026-10-12T121440+0000.json` runs[0].diag/host |
| Probe run 2: freezeAt 3496; hidden 3498, req 3500; thawAt 333864; `resp save 18 ok` 334135 (+271); busy→ready 334142; idle-autosave 334659 (+795); auto save 412(token)→204(no token), `outcome saved`; manual `save 22` 335752→204 | runs[1] |
| Probe run 3: freezeAt 3416; hidden 3421 (+5 ms), req 3422; thawAt 333828; idle-autosave 334014; `fail` 334016 (+188) | runs[2] |
| `resp` logpoint at `document-sdk.js:236`, after `:234 if (!entry) return;` | probe `LOGPOINTS`/`EXPECT` (`probe_k8_frozen_recovery.py:46-79`) |
| Timer: `_request :159` timeoutMs, `:170-181` failAndCancel (+cancel), `:186-190` setTimeout; `_cleanupPending :214`; `_handleMessage :221` | `wasm_sdk_probe/sdk/document-sdk.js` |
| `RECOVERY_ERRORS` incl. `TIMEOUT` `:15-22`; drain catch `:321-325`; `_blockQueue :342`; `save()` 180 000 ms `:558-562` | `wasm_sdk_probe/editor-shell/editor-session.js` |
| `autosaveNow :2605`; `visibilitychange` → `autosaveNow("hidden")` `:2629-2633`; notice text `:753` | `wasm_sdk_probe/web/e2-editor-app.js` |
| E1-C bundle included = 5 files, no SDK; E2 SCOPE includes `sdk` | `e1/editor-shell-bundle-v2.json`; `tools/build_e2_c_shell_bundle.py:674` |
| K8 arm `:606-622`, scorer `:958-982`, red cases `:1127-1133`, `("K8", ("chrome",), 1)` `:74` | `wasm_sdk_probe/tools/check_m3_locks.py` |
| K8 expectation change = `65e90f62` (+22 lines in `check_m3_locks.py`); `ce758882` = witness re-score outputs | `git show --stat` |
| Pins: assets `:77,:99`; locks `:57`; page_honesty `:63-69`; versions `:59`; same_second `:64`; production_ui `:79-83`; autosave `:83-86` | the seven runners |
| COOL: Socket.ts `:200-209, :342-362, :429-433, :482, :523, :536, :592-601, :613, :650-658, :664-669`; IdleHandler.ts `:45, :68-81, :140-142, :226-232`; Map.js `:1437, :1471-1476, :1485-1494`; main.js `:145-150`; global.js `:1406-1426`; wasmapp.cpp `:36-57, :75-79`; DocumentBroker.hpp `:984-987, :1252-1255`; DocumentBroker.cpp `:573-594, :671-683, :3889-3892, :4138-4146`; coolwsd.xml.in `:68-70, :94-95` | `cool-26-04/` (read-only) |
