# Ruling 6, addendum 1 (v22): item 1's first reading — four NOT_ESTABLISHED cells from the desk and the chain's procedure, no FAIL; the re-run, the superseded move, the reading, the stop rules, the desk gate

Judge: fable (external, the judge of ruling 6), 2026-10-20 ~01:45. Read-only: the files the brief names, read by path; `python3 -I` over the four named item-1 reports; `git log`/`git show --stat`; the process list; no repo-wide search of any kind, nothing under `item2-rerun/` touched, no browser, no make, no ddev, no runner, no lock, nothing written in the repo. Brief: `findings/evidence/link-batch-v22/review/brief-fable-6-addendum-1-item1.md` (`24e1f64f`). `CLAUDE.md` 「驗收判準的形式」 §1–§11 applies. Shape as ruling 6. This amends nothing in ruling 6; it rules item 1's first reading.

**A disclosure first.** One of the four cells (Firefox D7, press `sec-end-n2` r3) was voided by this judge's own file search for `chain-item2-item1.sh` during ruling 6 (`bfs … -name chain-item2-item1.sh` at 172.5 % CPU, 17:16–17:19). The search was unnecessary — the file's path was derivable from the brief. The rule the brief now imposes on me (no repo-wide search) is right and is applied here; it must also apply to every session and subagent while a timing arm runs (Q3, Q4).

## 1. 裁決（白話，給擁有者）

**出了什麼事。**第 1 項的證據鏈六份報告跑完，判讀器讀出 6 格不是 PASS：兩格 E0 是附錄 1 早就說會紅的（v22 入口打開，那條 v21 規矩必紅），E0-v22 的讀法 379 次讀取全過；另外四格是「沒成立」（NE），**沒有任何一格是 FAIL**——每一格都是環境或我們自己的程序造成的，不是產品：

- **D5w Firefox**：Firefox 一個瀏覽器工作階段連跑 11 支臂，前 43 次載入都好，第 44 次起每一次引擎啟動都失敗（`WORKER_INIT_FAILED`，記憶體配置中止），d5w、x-lc、表格那三支臂全丟。這跟 10-17 v21 的 W2 一模一樣；當時的處方是把 Firefox 的這批臂拆成三個新開的瀏覽器工作階段跑，沒有改工具。**這次鏈的腳本沒有照那個處方拆**，又用一個工作階段跑全部——這是主 session 寫程序時的疏漏，不是工具的錯。
- **D7 Chrome**：192 下按鍵裡 2 下的前置 CPU 取樣抓到你桌面 Chrome 的擴充功能程序（80%、78%，和 M6 那次同一個 Chrome）。v21 的 Chrome D7 第一次也是被同一種程序打掉的（74.5%、75.6%），當時重跑了 d1、舊報告搬到 `superseded/`。
- **D7 Firefox**：8 下被打掉——OxOffice 另一個專案的 `make -j 4` 和它的 `cc1plus`（97–99%）、你的 zen 瀏覽器（81–101%），**還有我自己**：裁決 6 時我做了一次整個 repo 的檔案搜尋（172%），正好落在一下計時按鍵上。這一格有我的責任。
- **D9 Firefox**：12 次讀取裡 1 次被桌面 Chrome 的擴充功能程序（78.4%）打掉。

**我的決定。**

1. **重跑，不走預設。**預設「v22 不可出貨」是為「產品紅」或「沒做」寫的；這四格沒有一格是產品的結果，每一格的原因都記在報告裡，而且前例都在：v21 的 Chrome D7（同一種桌面 Chrome 程序）就是重跑 d1；外部 CPU 准再跑一次（v21 §12.4 (e) 3）；W2 用三個新工作階段重跑。
2. **重跑的範圍就是那四份報告的臂**，約 1.5 小時：Chrome `d1`（29 分）、Firefox `d1`（33 分）、Firefox `d9,d10,d14`（8 分）、Firefox 剩下的臂照 v21 的分法拆成三個新工作階段 A／B／C（約 15–20 分）。不能只跑壞掉的那幾下：判讀器一個（瀏覽器、臂）只收一份報告，報告檔不能拆，舊報告整份搬到 `item1/superseded/`（不刪，v21 的作法），然後判讀器照原樣跑整個目錄。
3. **一條先寫好的讀法**：有些格只是因為跟壞掉的格同一份檔案才被迫重跑（例如 Firefox 的 D10、D14、D2p…D12）。它們第一次是乾淨的 PASS；若重跑時又被桌面打成 NE，**第一次的讀數算**（裁決 6 的原則：每一格取自程序跑對的那份報告），兩段判讀器輸出都原文引用；但**任何一次 FAIL 就是 FAIL**，這條規則不救 FAIL，也不救那四格本身。
4. **停止規則**：任何 FAIL → 第 1 項紅，v22 不可出貨，停手交接。那四格若又因外部 CPU 而 NE（在鏈已經檢查過桌面安靜的情況下）→ 記下是哪個程序，停手交接。A／B／C 裡又出現 W2 → 停手交接（v21 的拆法從沒失手過，這會是新東西）。
5. **桌面要先查、髒就不跑。**這次鏈的每一步開始時 `desk.log` 都記到 39–40 個 Chrome 程序，但只記錄、沒擋。新的鏈腳本每一步之前先查（沒有 Chrome／zen／make／cc1plus、1 分鐘負載 < 1.5、2 秒外部 CPU 取樣乾淨、KWallet 沒鎖），髒就記 `DESK DIRTY` 停下來，等乾淨再啟動。**而且在計時臂跑的時候，主 session 和任何 subagent 都不做吃 CPU 的事**：不搜尋整個 repo、不跑測試、不讀大報告，只看 log 尾巴。
6. **帳**：沒有改任何工具，因執行而修 0、因審核而修 0。「因 harness 損失而重跑」+1（W2，第二次了：處方存在但沒被帶進腳本）；另列一行「因桌面而重跑」+3（Chrome D7、Firefox D7、Firefox D9），其中一下是我的搜尋。

**要請你做的事（A／B）**：接下來約 1.5 小時桌面要安靜——桌面 Chrome 關著、zen 關著、不開別的建置。
- **A** 現在就可以（你 01:19 說其他 session 都關了；第 2 項的 Firefox 重跑約 01:35 結束，之後就啟動）。
- **B** 你指定一個時段。

## 2. Answers (English)

Forms per CLAUDE.md §1; defaults per §2. "Spec append" = v22 spec §11.4.2, append-only, **before any item-1 re-run** (§9 condition 1).

### Q1. Re-run (P1), not the default (b)

1. **Re-run.** I1-rerun's default 「沒做或紅 → v22 不可出貨」 is written for a product red or an un-run criterion. Here: no FAIL in any of the 26 criterion cells; the two E0 FAILs are the construction addendum 1 predicted and E0-v22 PASSes (379 reads, 0 red, 0 blind); each of the four NEs carries its cause inside the report — the W2 state (`open.settled.state: recoverable-error`, outcome `step-error`, on every one of the 17 loads from load 44 on) and the foreign-CPU blocks naming the process (`own: false`, pid, cmd, pct). Precedents, each already spent on the same shape: v21's Chrome D7 NE from the owner's desktop Chrome `--extension-process` renderer (74.5 / 75.6 %) → Chrome d1 re-run, the first report to `evidence/superseded/item1/` (v21 README `:160`, `:222`); v21 §12.4 (e) 3 (NE only from foreign CPU → one more run, once); W2 (procedural re-run in three fresh Firefox sessions, the lost report kept as a witness). Taking (b) would discard a candidate whose only non-PASS cells came from our desk and our chain script — one of them from this judge.
2. **Form / default.** Form one (per cell, per report). If the re-run is never done: I1-rerun not done → v22 not shippable, 0.2.26 nominal (§11.4). If the spec append does not land before the re-run: the re-run does not count for I1-rerun.

### Q2. Scope (P2) and the move-and-read (P3)

3. **Scope as P2, whole-report replacement, no cheaper reading.** The judge keeps one result per (browser, arm) and prints FAIL 「two reports for one (browser, arm)」 on a duplicate (`judge_v21_shakedown_item1.py:991-994`); a report is one file per invocation (`run_v21_shakedown_item1.py:1009`); and W2's witness README states the rule: 「The good rounds of d2p–d12 here are re-measured, not reused: the judge reads one report per (browser, arm), and evidence files are not split.」 A hand-split report is one 「任何已 commit 的 runner 都產生不出來的報告」 (§34.2) and is never read as evidence. So alternative (a) is out, and:
   - Chrome `--arms d1 --rounds 3` (D1, D4, D7);
   - Firefox `--arms d1 --rounds 3`;
   - Firefox `--arms d9,d10,d14 --rounds 3` (d9's report carries d10 and d14);
   - Firefox's rest as W2's split, three fresh sessions, the same lists as v21: A `d2p,d8,d8red,d11b`; B `d11a,d11c,d12`; C `d5w,xlc,table,d6` (d6 stays `NOT_RUNNABLE`, recorded).
   Chrome's `d9,d10,d14` and Chrome's rest are untouched. `--rounds 3` explicitly (the runner's default is 1).
4. **The move.** `git mv` the four replaced reports — `report-chrome-d1-20261019T155807.json`, `report-firefox-d1-20261019T164633.json`, `report-firefox-d9-d10-d14-20261019T171939.json`, `report-firefox-d2p-…-d6-20261019T172740.json` — with their `docs/<browser>-<stamp>/` folders and step logs into `item1/superseded/`, with a README line per report naming its cause (W2 / desktop Chrome / build + zen + the judge's search / desktop Chrome). The judge's `load()` globs `report-*.json` in `--dir` only (`:954`), so `superseded/` is invisible to it; `e0_v22.py` takes explicit paths (`:128-134`) — pass `item1/report-*.json` only. The move may precede the re-run (the new reports carry new stamps; no overwrite) but must be done **between steps, never during a timing step**, and before the judge is run. The first-reading output stays in `item1/first-reading/`.
5. **Reading.** The judge runs unchanged over `item1/` (eight reports: Chrome d1 new, Chrome d9-d10-d14 old, Chrome rest old, Firefox d1 new, Firefox d9-d10-d14 new, Firefox A, B, C). I1-rerun PASS = `VERDICT NOT PASS (2 criterion cell(s) not PASS)` with exactly `E0 chrome FAIL` and `E0 firefox FAIL` (addendum 1 item 4), every other line PASS, **and** E0-v22 PASS over the same eight reports (its red cases unchanged). The D6 line prints the stale reason as before; the README says so beside it.
6. **Companion-cell rule (pinned now; this is where P3's "no composition needed" is incomplete).** Companion cells = cells re-run only because they share a report with a voided cell: Chrome d1's D1, D4; Firefox d1's D1, D4; Firefox d9-d10-d14's D10, D14; A/B's D2p, D8, D11a, D11b, D11c, D12. Their re-run reading is the reading — **except** when a companion reads NE on the re-run for a cause recorded in the report (a foreign-CPU block, the W2 state, a `runnerError`) while its first reading was PASS with its procedure run right: then the first reading stands for that cell (ruling 6's principle, 「每一格取自它的程序跑對的那一份報告」), the README composes with both judge outputs quoted verbatim, and the superseded report is the committed evidence for it. **A FAIL in either run is FAIL.** The rule never rescues a FAIL and never applies to the four voided cells themselves (D5w Firefox, D7 Chrome, D7 Firefox, D9 Firefox), which have no clean first reading.
7. **Form / default.** Form one. Default if the move is never made: two reports per (browser, arm) → the judge prints FAIL by its duplicate rule → that FAIL is a tool refusal, not a product result; I1-rerun is then not read → not done → v22 not shippable.

### Q3. Stop rules (P4) and the desk condition

8. **Stop rules, pinned before the re-run:**
   - any FAIL, in a voided cell or a companion, in either run → I1-rerun red → v22 not shippable; stop, hand off; a product finding;
   - a voided cell NE again from foreign CPU on a desk the chain checked quiet (item 9) → record the process (pid, cmd, pct), stop, hand off; the default stands unless a new ruling grants more; no third run in this session;
   - W2 inside A, B or C → new (v21's split held); stop, hand off; the failed report becomes a second W2 witness; the next remedy would be a runner-level session split, a tool change with two witnesses — not built in this batch;
   - any other NE on a voided cell (`runnerError`, no reply, missing press) → stop, hand off;
   - a companion NE with a recorded cause → item 6; a companion NE without one → stop, hand off;
   - the E0 lines must be exactly the two expected FAILs; any other E0 shape → read as addendum 1 item 5.
9. **The desk is checked before each step and a dirty one is refused — both, not either.** The guard's per-press NE is honest but spends the single re-run; the first reading shows the cost (`desk.log`: 39–40 Chrome processes at every step's start, recorded and not acted on; the runner's `pre_run_checks` refuses only on KWallet). The chain script (procedure, an addition 0/0) runs before each step: KWallet unlocked; `pgrep -c chrome` = 0 and no `zen`, `make`, `cc1plus`, `ninja`; 1-min load < 1.5 (v21 §12.4's desk condition); `python3 -B tools/v21_shakedown_common.py` printing `foreignCpu.ok: true` (the existing 2 s sample, `:394-395`, starts no browser); the S-9 lock free (the runner waits anyway). Dirty → log `DESK DIRTY <reason>` and **stop the chain** (later steps would only add reports to supersede); the session re-launches it when the desk is clean. **And a rule for the session itself:** while a timing step runs (`d1`, `d9,d10,d14`, `d14` in C is not timing-bound but C is cheap), the main session and every subagent do nothing CPU-heavy — no repo-wide search, no unit tests, no node, no `python3` over the reports, no `git` beyond `status`/`log`; only `tail` on `chain.log`/`desk.log`. The judge briefs carry the same rule (applied here).
10. **Form / default.** Form one (per step, per read). Default if the desk gate is never written: the guard alone; a foreign-CPU NE then falls under item 8's second line.

### Q4. The §34.4 tally; what the missed split and the judge's search need

11. **Tally:** tools modified because of execution **0**, because of review **0** (no tool edited; the chain script and its desk gate are additions). **Runs lost to the harness and re-run: +1** (W2 — the second time; v21's remedy existed and was not carried into the v22 chain script). **Runs lost to the desk and re-run: +3** (Chrome d1, Firefox d1, Firefox d9-d10-d14), a separate line because the desk is not the harness; one Firefox D7 press of the three was the judge's own search. Stretch stays **+3 / 0**, running **32 / 18**.
12. **Beyond README lines, procedure only, no tool:** (a) the next chain script is written from a checklist line in the handoff, not from memory: Firefox's rest is three sessions; `--rounds 3`; the desk gate before each step; `DESK DIRTY` stops the chain; (b) the handoff's Hazards get the session-idle rule of item 9 and the judge-brief rule; (c) the README records the recurring foreign load by name: the owner's desktop Chrome `--extension-process` renderer has now voided timing cells four times (v21 Chrome D7 74.5 / 75.6 %; v22 Firefox M6 81 %; v22 Chrome D7 80 / 78 %; v22 Firefox D9 78.4 %) — so 「桌面 Chrome 關閉」 is a standing desk condition of every timing step, not a per-run request; (d) no finding: a procedure fault and a desk fact, not a product or tool defect. Form: the tally is a count over committed reports; the checklist is procedure.

### Q5. What the addendum gets wrong or leaves out

13. **P3 is incomplete** — the companion-cell rule (item 6) must be pinned before the run, or a desk NE on a forced re-run of a clean cell has no reading.
14. **The spec append's content and timing:** §11.4.2 (append-only), landing before any item-1 re-run: the four NEs and their recorded causes; the re-run scope (item 3); the move (item 4); the reading (item 5); the companion rule (item 6); the stop rules (item 8); the desk gate and the session-idle rule (item 9); the tally (item 11); the registered procedure items (item 12); §9's four conditions — before satisfaction (no re-run yet), forced and named (`f56ccddc`'s six reports and `judge-item1-first.txt`), form one, deadline = the re-run's reports landing; the defaults.
15. **Timing against the item-2 re-run:** the chain starts only after `item2-rerun/`'s Firefox run has exited and its report is judged per ruling 6 (the S-9 lock serializes browsers, but the desk gate's `pgrep firefox` would also see the runner's Firefox). Do not let the two overlap.
16. **A precedent the brief did not cite:** v21's Chrome D7 — the same desktop-Chrome extension renderer, re-run as `d1`, the first report moved to `evidence/superseded/item1/` (v21 README `:160`, `:222`). It is the exact shape of today's Chrome D7 and belongs in the README.
17. **F2's load count:** my record-order scan of the Firefox rest report gives 43 good loads (d2p 9, d8 15, d8red 3, d11a 3, d11b 6, d11c 3, d12 3, d5w r1 `v20`), the first failure at load 44 (d5w r1 `v21`), 17 failing loads (d5w 5, xlc 9, table 3), every one `step-error` with `open.settled.state: recoverable-error`; v21's W2 failed from load 45. Same shape; write 43/44, not "44 good loads", for v22.
18. **The D4 deviation lines** (`DEVIATION-D4-op … counted, for the main session`, 18 per browser, PASS) are the recorded v21 deviation, not new; carry them in the README as v21 did.
19. **Nothing else wrong.** F1, F3, F4, F5, F6 reproduce (section 3).

## 3. F-claims checked

- **F1:** reproduced from `item1/first-reading/judge-item1-first.txt` (tree `1b393f8f`, exit 1): `VERDICT NOT PASS (6 criterion cell(s) not PASS)` — `E0 chrome FAIL`, `E0 firefox FAIL`, `D5w firefox NOT_ESTABLISHED`, `D7 chrome NOT_ESTABLISHED`, `D7 firefox NOT_ESTABLISHED`, `D9 firefox NOT_ESTABLISHED`; every other line PASS; no FAIL elsewhere. `e0-v22-first.txt`: 120 + 57 + 21 + 120 + 40 + 21 = 379 reads, 0 red, 0 blind, `E0-v22 PASS`. `chain.log`: `CHAIN DONE` after `item1-firefox-rest` 17:27:40–18:22:25, every step exit 0.
- **F2:** reproduced over `report-firefox-d2p-…-d6-20261019T172740.json` (one session 17:27:40–18:22:25): d2p 9/9 done, d8 15/15, d8red 3/3, d11a 3/3, d11b 6/6, d11c 3/3, d12 3/3; d5w 1 done + 5 `step-error`; xlc 9 `step-error` (1466.5 s); table 3 `step-error` (488.6 s); d6 `notRun`. Loads 1–43 good, 44–60 failing, all 17 with `open.settled.state: recoverable-error` (the toast text as the brief quotes it; my scan read the settled state). Pages: `v21`/`v21host`/`v21hook` profile `e2-editor-v22`, page `3b96cb16…`, wasm `f7a40bcc…`, HTML `b9c2b975…`; `v20` on `e2-editor-v20`; `dist0224` page `901dd6a6…`. The chain script runs Firefox's rest as one invocation (`chain-item2-item1.sh`, read during ruling 6).
- **F3:** reproduced. Chrome d1 (120/120 done): foreign over limit on `t-home-A1-n1` r2 (pid 3136562, 80.0 %) and `t-end-B2-n1` r3 (pid 3145842, 78.0 %), both `chrome --type=renderer … --extension-process`, `--crashpad-handler-pid=2745205`, `own: false`. Firefox d1 (120/120 done): 8 records over limit — `make -j 4 … Makefile.gbuild` (`Library_merged` 96.8 % r2; `CppunitTest_ossii_extension_documentcontext` 98.3 / 99.3 % r3), `cc1plus` 99.0 % (r2), zen `Isolated Web Co` pid 2780809 (101.3, 81.5, 93.5 %, r2), and `bfs -S dfs … -name chain-item2-item1.sh` pid 3205598 at 172.5 % on `sec-end-n2` r3 (this judge's search). The judge's D7 lines carry only 「foreign CPU over the limit」 reasons — no window FAIL, no missing press — 2 Chrome lines, 15 Firefox lines (multi-press arms repeat). `judge_d7` (`:244-275`): a foreign press is NE; fewer than N clean rounds is NE.
- **F4:** reproduced. Firefox d9-d10-d14: D9 `Ctrl+End flagged r2` foreign (pid 3212733, 78.4 %, the same crashpad parent); the other 11 reads as v21's (flagged 1 move / 0 ms; unflagged 4 moves / 235–239 ms); D10 3/3 and D14 6/6 done and PASS. `preRun` at that step's start: load `3.47 2.25 1.64`, 40 Chrome processes.
- **F5:** verbatim as quoted. The duplicate rule at `judge_v21_shakedown_item1.py:991-994`; `load()` non-recursive (`:954`); v21's `evidence/superseded/item1/` holds Chrome d1 `054335` and Firefox d1 `071208`, `092410` with their logs and docs; W2's witness README (`evidence/witness/firefox-rest-worker-init-failed/`) states the remedy and the no-split rule.
- **F6:** step times from `chain.log`: Chrome d1 29.4 min, Firefox d1 33.1, Firefox d9-d10-d14 8.0, Chrome rest 11.8. Desk at 01:27: load 1.20, the only runner process `run_v21_shakedown_item2.py --browser firefox --arms m6,m5` (pid 3599695); no chrome, zen, make or cc1plus in my process read. Commits since `0da3cc33`: `1b393f8f` is the only tool commit, item-2 files only (outside item 1's closure, ruling 6 item 15); the reports' `treeHead`s (`09855075`, `4d78b111`, `22bc3df4`, `7475d52d`, `1b393f8f`) are the commits that landed during the chain.
- **The brief's leaning:** P1 right; P2 right; P3 right but incomplete (item 6); P4 adopted with the desk gate before each step (item 9); P5 right, with the desk re-runs on their own line (item 11).

## 4. What the main session must do next, in order

1. **Wait for the item-2 Firefox re-run** in `item2-rerun/` to exit; judge it per ruling 6 (§11.2.1) and record its cells. Nothing item-1 starts before that.
2. **Append spec v22 §11.4.2** (item 14). Commit.
3. **Move the four replaced reports** with their docs and step logs to `item1/superseded/` by `git mv`, with the README lines of item 4. Commit. Between steps only.
4. **Write the re-run chain script** (an addition): the desk gate of item 9 before each step, `DESK DIRTY` stops the chain; steps in order — Chrome `d1`; Firefox `d1`; Firefox `d9,d10,d14`; Firefox A `d2p,d8,d8red,d11b`; B `d11a,d11c,d12`; C `d5w,xlc,table,d6` — each `--rounds 3 --out …/shakedown/item1 --wait-lock 1800`, logged to `chain.log`/`desk.log` as before. Commit it.
5. **Ask the owner (A/B)** for the quiet 1.5 h; on A, start the chain detached (`setsid nohup`) once step 1 is done and the desk gate passes. **The session then idles**: `tail` only, no search, no tests, no reports read, until `CHAIN DONE` or `DESK DIRTY`.
6. **Read:** the judge unchanged with `--expect-page 3b96cb16…` over `item1/`; expect `VERDICT NOT PASS (2 criterion cell(s) not PASS)` with exactly the two E0 cells; `e0_v22.py item1/report-*.json` → `E0-v22 PASS`; apply items 6 and 8; quote the first-reading output beside the new one wherever item 6 composes.
7. **Write `item1/README.md`**: the four causes with the process names, the v21 Chrome D7 precedent, the W2 count (43/44), the D4 deviation lines, the stale D6 reason, the companion-cell composition if any, the tally of item 11, the desk fact of item 12 (c). Commit with the re-run reports and logs.
8. **Then §11.7 step 7 onward as the handoff lists** (freeze v75, the ddev window). The handoff's Hazards gain item 9's session-idle rule and item 12's checklist line.

**Defaults restated:** spec not appended before the re-run → the re-run does not count. Re-run never done → I1-rerun not done → v22 not shippable, 0.2.26 nominal. Any FAIL → v22 not shippable, stop. A voided cell NE again on a quiet desk, or W2 inside A/B/C → stop, hand off; the default stands unless a new ruling. Reports not moved → the judge's duplicate FAIL is a refusal, not a verdict; I1-rerun not read.

---

## The main session's check before adopting (opus, 2026-10-20 ~01:35)

The text above is fable's, committed verbatim (extracted from the subagent's transcript). Checked before acting on it:

- **The v21 Chrome D7 precedent (item 1, item 16).** `findings/evidence/link-batch-v21/shakedown/README.md:160` lists `superseded/item1/` as "Chrome's first d1 run (D7 NE from foreign CPU)". `:221` records it: sec-home-n2 r1 at 74.5 % and sec-end-n1 r3 at 75.6 %, from the owner's desktop Chrome's `--extension-process` renderer. `:222`: the re-run counts. `evidence/superseded/item1/` holds `report-chrome-d1-20261017T054335.json` and two Firefox d1 reports with their logs. As stated.
- **The duplicate rule (item 3).** `judge_v21_shakedown_item1.py:992-994`: `result == "DUPLICATE"` → `(FAIL, ["two reports for one (browser, arm)"])`. As stated.
- **The desk gate's sample (item 9).** `python3 -B tools/v21_shakedown_common.py`, as `__main__` (`:394-400`), prints `preRun` and a 2 s `foreignCpu` sample and tries the S-9 lock. It starts no browser. As stated. It takes the lock for an instant, so the gate runs it only when no runner is up.
- **`--rounds` (item 3).** `run_v21_shakedown_item1.py:994`: the default is 1, so every step passes `--rounds 3`.
- **The load count (item 17).** I wrote "about 44" to the owner; 43 good and the first failure at 44 is the ruling's scan, and the README uses it.

Adopted as written. The owner is asked item 5's A/B after the item-2 re-run is judged.
