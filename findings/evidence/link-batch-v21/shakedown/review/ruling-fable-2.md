# Ruling 2 (v21 shakedown, D7 Firefox), fable, 2026-10-17

Request: `brief-fable-2-d7.md` (commit `269e1f9b`). The owner chose to send D7 to fable (2026-10-17, 「D7 發給 fable」). Fable worked read-only. Verbatim below, as returned to the main session.

Main-session check before adoption (2026-10-17): recomputed from the three D1 reports the per-index lateness rates (run 1: 12/114, 11/54, 4/24; run 2: 14/114, 10/54, 2/24), the sequence gaps between reply and ask (3 or 5, i.e. two or four intervening entries), the identical `snippetSha256` (`00d2d295…`, `52c08695…`) in the Chrome and both Firefox reports, and D10/D11a's read delays (Chrome 500.2–500.6, Firefox 500.2–501.0); confirmed the runner's 50 ms drain loop inside the window (`run_v21_shakedown_item1.py:373-377`) and the id drift (ARMS-item1 `:64` says `0x7F000000`, the observer uses `0x7E000000`). One small difference: the ask round trip after a post later than +520 ms reads 0.9–1.7 ms by the main session's split (fable: 0.8–1.5); the conclusion (identical to on-time, 0.7–1.9) holds.

---

**Ruling 2 (v21 shakedown, D7 Firefox), fable, 2026-10-17, read-only.**

Basis. Read in full: the brief (`review/brief-fable-2-d7.md`), CLAUDE.md 「驗收判準的形式」 §1–§11, spec §11.0/§11.1/§12.3 and the revision log, `SPEC-M3-link-batch.md` §10.2 S2, v21 §9.7, codex review 2 S4, `git show 523871fa`, the observer `v21_item1_observer.py` (whole file), the runner's `ctrl()`/`wait_rs()`/`drain()`/`ev_quiet()` (`run_v21_shakedown_item1.py:225-380`), the judge's `ASK7_WINDOW`/`judge_press`/`judge_d7`/`judge_d10`/`judge_d11a` and its D7 self-test mutations (`:1300-1322`, `:1393-1416`), ARMS-item1 §2.2, D7, D-15, D-18, `v21_shakedown_common.py:295-315`, the handoff 「D7 re-run」, both judge outputs, README §5.5. Ran read-only Python (`python3 -I`) over the three D1 reports and the Chrome/Firefox D10, D11a and the Chrome rest report; re-ran nothing in a browser; edited nothing in the repo.

---

## Q1. Which option, the constant, and whether A0 comes first

**RULING.** **A0 first, then A.** A0 is cut down to what A's premise needs: the real `+500` ask unchanged, plus three *silent sentinel timers* at +440, +455, +470 registered in the same listener, and the paint-reply page times buffered and emitted with the ask entry. **No 5 ms heartbeat.** The constant is then chosen by a rule written here, before A0 runs: **470** if every +470 sentinel in A0 posted at ≤ +540 ms after the reply; otherwise **455** if every +455 sentinel posted at ≤ +540; otherwise **no constant** (the default already in force stands, no evidence re-run). If A0 reproduces no lateness (fewer than 3 presses with the +500 read later than +520), it is uninformative and the constant is 455, recorded as 「premise unmeasured, maximum slack chosen」. The judge, the window and D7's wording do not change. Widening or one-siding the window, choosing reads across reports, and re-running unchanged stay refused, for the brief's reasons.

**WHY（給擁有者）.** D7 量的是「回覆裡的游標 500 毫秒後還是對的」，這件事在 Firefox 兩輪 384 次讀取裡一次都沒錯過；錯的是儀器的鬧鐘在 Firefox 偶爾晚響 5 到 60 毫秒，所以該改的是鬧鐘設幾點，不是判準。但主 session 自己承認「把鬧鐘提早 30 毫秒就會準時」是沒量過的假設：如果主執行緒忙碌那段是從 +470 之前就開始，提早也一樣會被拖到同一個終點。這個假設用三個不會送任何請求的哨兵計時器就能在十到十五分鐘內直接量到，所以先量再改。至於 5 毫秒的心跳我不要，因為它會讓主執行緒永遠不閒，而 Firefox 的垃圾回收正是挑閒的時候做——心跳可能把現象本身藏起來。常數要選哪個，規則現在就寫死，不留到看完數據再決定。

**FACT CHECK.**
- F1 verified verbatim at `SPEC-M3-link-batch-v21.md:359`. F2 verified: §11.0 (N=3, N/N, 「缺報、缺回、NE 一律等於「沒做」」) and the revision-log row that pins from `523871fa`.
- F3 verified: `SPEC-M3-link-batch.md:159` 「完成後至少 500 ms」 (one-sided); v21 `:220` 「≥500 ms 之後」 (one-sided); codex S4 (`review-2-codex.md:152`) objected only to re-reading until equal and asked for 「單次採樣時點與容許時間窗」; `523871fa` adds the row with 「500±50 ms 的單次」 and nothing else in the spec mentions 單次/採樣/時間窗 (grep: only `:359`). The ±50 has no stated derivation. Note the same commit also tightened the silent-press bound from 1000 ms (§9.7) to < 500 ms (§11.1); not at issue.
- F5 verified in the observer source: `put()` stamps `e.t = now()` before `setTimeout(…, 500)` is called, and the callback stamps `t: now()` into the requests map, which becomes `ask7.tPosted`. So `tPosted − rs.t ≥ 500` by construction (≥ 499.9 after the 0.1 ms rounding); the lower edge of the window is never at risk at 470 or 455. Listener order verified: the observer's listener is added inside the `Worker` wrapper before the instance is returned to the page.
- F7 verified: `ASK7_WINDOW = (450.0, 550.0)` inclusive; outside → NE; `< rounds` non-NE and no FAIL → NE; D7 = worst over the population.
- F9–F11 recomputed (my script, the judge's inclusive rule): Chrome 192 reads 500.1–500.9, 0 outside. Firefox run 1 (`071208`): 165 in [500,505), 15 > 520, max 553.5, **2 outside** (550.1, 553.5); family >505: t 16/72, tl 5/18, sec 4/36, a3 2/21, others 0. Firefox run 2 (`092410`): 166 in [500,505), 13 > 520, max 560.3, **6 outside** (554.7–560.3, all `t-*`, all `ch1`/`ce1`); family >505: t 16/72, a3 4/21, r 2/18 (546.2), tl 2/18, sec 1/36, tf 1/18. The 550.0 read (t-end-B2-n1 r1) sits on the inclusive edge and the judge kept it in. Foreign-CPU void sec-home-n1 r2 (chrome renderer 79 %) verified in the judge output.
- F12 verified: all 8 outside reads caret-equal in four fields; **no caret inequality in any of the 576 reads** across the three D1 reports.
- F13: the quoted 250.6–251.2 are §12.3's diagnostic numbers; in the D1 reports the silent presses' request-to-reply is 250.5–251.5 (Chrome), 250.9–254.0 (Firefox run 1), 250.9–252.5 (run 2). Same conclusion.
- **F6 is wrong as written.** Nothing of ours touches the document between reply and read, but the runner polls the page every ~50 ms inside the window (`ctrl()` loop, runner `:375` `self.log.drain()`), and each poll is one to three script evaluations on the page's main thread through Marionette (Firefox) or CDP (Chrome): `READ_LEN`, then `READ_SLICE` returning the whole JSON log, then `CUT`. The observer's own `flush` (`JSON.stringify(log)`) also runs as a 0 ms timer after every `put`. Chrome shows no lateness under the same polling, so this is not shown to be the cause, but it is main-thread work of ours inside the window, and A0 must run with the same runner so the diagnostic sees the same load.
- **What the reports say about when the busy stretch begins: nothing directly.** The round record keeps page times only for `response.t`, `response.tRq`, the keydowns (`kd`/`kdp`), `ask7.tPosted` and `ask7.t`. Between `response.s` and `ask7.s` there are always four intervening observer entries in the late presses (53/53 across both runs) and in 324 of 331 on-time presses (the rest have two), so there is no extra trace/DOM activity in late presses, and those entries' `t` are not in the report. What *is* observable: (i) the stretch ends at `tPosted`: the ask round trip after a late post is 0.8–1.5 ms, identical to on-time (0.7–1.9), so main thread and worker were both free the moment the timer fired; (ii) the lateness is bimodal and tight, run 2: 9 reads at +10–15, 10 at +45–60, 3 between; run 1: clusters at +15–20 and +40–55; hard ceiling 60.3 ms over 384 reads, none above; (iii) it repeats on the same cells: `t-home-B2-n1 ch1` late in 3/3 rounds of run 1 (542.9, 548.2, 544.5) and 2/3 of run 2 (554.7, 539.0); `t-end-B2-n1 ce1` 550.1 / 550.0 / 560.3; `t-home-B2-n3 ch1` 543.4, 524.1 / 556.1, 557.7. A randomly placed long stretch would spread the lateness uniformly; these tight, cell-specific clusters say a fixed-duration task with a fixed phase after that particular move. That is consistent with the brief's repaint reading, and equally with a 120 ms task starting at +440: the data fix the *end* (+555–560 in run 2, +543–553 in run 1, a ~7–10 ms drift between runs) and leave the *start* unknown. That is exactly the question A0's sentinels answer per press.
- 「The late reads are mostly an arm's first press」 holds for the >550 tail (8/8 across both runs are `ch1`/`ce1`) but not for lateness in general: >505 by press index, run 1: idx0 12/114 (10.5 %), idx1 11/54 (20 %), idx2 4/24 (17 %); run 2: 14/114, 10/54, 2/24.

**CONDITIONS.**
1. Before any browser starts: commit this ruling as `review/ruling-fable-2.md`; append spec §12.4 (append-only, §10) with the pre-committed rules below (constant choice, stop rule, outcome slot); add README §5.5 row J3 naming the witnesses (`superseded/item1/report-firefox-d1-20261017T071208.json`, `item1/report-firefox-d1-20261017T092410.json`, `judge-item1.txt`, `judge-item1-after-d7-rerun.txt`).
2. A0 is a diagnostic, not evidence: a *copy* of `SNIPPET` (the committed observer is not edited for A0), driven by the unchanged runner on the unchanged mirror, Firefox only, arms `t-*` only, N=3 (72 presses), under the browser lock, desktop Chrome closed, 1-minute load < 1.5 at start, no foreign process > 50 % (D-18 A). Output under `review/diag-d7-timer/` (or a `diag-*` folder) with the patched snippet's sha256 and the label 「diagnostic, not evidence」.
3. A0's snippet changes, exactly: on the same successful `move-document-*` reply, also `setTimeout` three silent sentinels at 440, 455, 470 that only record `now()` into a local object; record `t` of every `paint`/`pageRectangles` *response* since that reply into a local array; emit both in the real `ask7` entry (`sentinels: {440, 455, 470}`, `paints: [...]`). No extra `put` and no extra worker request inside the window. The real ask stays at 500.
4. A0 informative iff ≥ 3 presses have the +500 read later than +520. Then: constant **470** iff `max(sentinel470 − rs.t) ≤ 540` over all presses; else **455** iff `max(sentinel455 − rs.t) ≤ 540`; else no constant: the default stands, no evidence re-run, go to Q3 condition 4. If uninformative: constant 455, recorded as such.
5. A: edit the one constant in `v21_item1_observer.py` (`}, 500);` → the chosen value) and nothing else; commit it with A0's output as the record; the new `snippetSha256[1]` is written into README §5 next to the old one.

---

## Q2. Can Chrome's D7 PASS stand; D10 and D11a

**RULING.** **Yes, all stand; no Chrome D1 re-run, no D10 or D11a re-run.** D7's claim is per browser and names the window, not the aim: Chrome's 192 reads at 500.1–500.9 are single scheduled reads inside the pinned window, as are D10's (Chrome 500.2–500.5, Firefox 500.3–501.0) and D11a's (Chrome 500.2–500.6, Firefox 500.2–500.4). The constant is instrument calibration, visible in `snippetSha256`, and §11.0's identity rule binds the product (wasm, worker, page, shell, inputs, reference), not the harness snippet. Uniformity would cost 35 min and buy nothing the window does not already give.

**WHY（給擁有者）.** 判準寫的是「回覆後 500±50 毫秒的單次讀取」，Chrome 那 192 次讀取全部落在 500.1 到 500.9，完全符合判準字面，鬧鐘設幾點不是判準的一部分。D10 跟 D11a 兩個瀏覽器也都落在 500 多一點，一樣符合。報告裡的 `snippetSha256` 會忠實記下 Firefox 用的是不同常數，所以之後的人看得出來，不是藏起來。重跑 Chrome 只是為了兩邊用同一個常數好看，不會改變任何判準的真假，35 分鐘不值得。

**FACT CHECK.**
- F4 verified with a nuance: `judge_d10` calls `judge_press("cursor", press)`, so D10 **does** apply `ASK7_WINDOW` and would read NE on a late Firefox read; `judge_d11a` reads `ask7.caret` for 「moved」 only and applies no window. Both PASS in both browsers in the re-judge output.
- F8 verified: `pages.v21.snippetSha256` is a two-element list (v20's OBSERVER, item-1 SNIPPET: `00d2d295…`, `52c08695…`), identical in the Chrome `064131` and Firefox `092410` reports; `htmlServedSha256` `9d2e18da…` identical; `shellDigest` `e35923a0…`; `runnerSha256` `4fba3d19…` identical across all reports. The handoff's sentence 「its runner version differs only in the … timer constant」 names the wrong locus: the runner hash will not change; `snippetSha256[1]` will.

**CONDITIONS.**
1. README §5 states, in one appended paragraph, that D7's criterion is the window; lists per report the `snippetSha256[1]` and the constant it encodes (Chrome D1, D10, D11a, rest at 500; Firefox D1 at the chosen constant; Firefox D10/D11a/rest at 500); and cites this ruling.
2. No judge change and no re-judge of the Chrome, D10, D11a reports; their verdict lines are carried unchanged.
3. The §34.4 tally does not move for Chrome/D10/D11a (nothing was misjudged there).

---

## Q3. Pre-commit the outcome and the stop rule

**RULING.** The default (「第 1 項不出貨」) is **already in force** (D7 Firefox NE twice); A0+A is the **one** permitted rescue. **Exactly one** Firefox D1 evidence re-run at the chosen constant. The unchanged judge's D7 Firefox line on that report is the verdict:
- **PASS** → D7 Firefox PASS; item 1 proceeds to the other gates.
- **NE from any window miss** (any of the 192 reads outside [450, 550]) → D7 Firefox NE; the default applies to v21: item 1 is not shipped, no second calibration, no third D1 run, the shell follows §11.0 (page stops binding Ctrl+Home/End, **L-142-sdk-callable** named) and v74 freezes that way. The instrument limit is written up as a finding; a §12 append *for v22*, written before any v22 evidence run, re-specifies D7's sampling clause (CLAUDE.md §4: withdraw/re-specify a clause whose premise failed, do not build machinery), and item 1 rides the v22 relink if D7 passes there.
- **NE solely from foreign CPU (D-18)** with zero window misses → one more re-run is allowed, once (a desk fault, not an instrument fault); the same rules then apply with no further allowance.
- **FAIL anywhere** (reply caret ≠ read caret, wrong completion class, silent press ≥ 500 ms) → FAIL; a product finding; item 1 not shipped; no re-run.
- **Instrument void**: if the re-run's in-window reads do not sit at the new constant (median of `tPosted − rs.t` outside [c, c+1.0] or min < c − 0.1), the edit did not reach the served page; the run is void and is repeated once after the cause is found; it does not count against the stop rule.

**WHY（給擁有者）.** 規則現在寫死：改一次常數、跑一次，結果由沒改過的 judge 說。過了就過；若還有任何一次讀取掉出窗外，就照原本的預設，第 1 項這次不出貨，不再第二次調常數、不再第三次重跑——否則就變成「一直重讀到剛好符合」，正是 codex 當初要堵的事。外來 CPU 害的那種 NE 是桌面問題不是儀器問題，所以准再跑一次，但也只有一次。真的沒出貨，也不是丟掉：第 1 項跟著 v22 重連結那一批走，D7 的取樣條款在那之前重新寫清楚。

**FACT CHECK.**
- ARMS-item1 D7 「Prediction」 pre-registered this exact failure mode: 「The risk is not the engine but the ±50 ms window on a busy page (timer jitter while painting); a miss reads NOT_ESTABLISHED and is re-run.」 It names re-run, not a count. One unchanged re-run has been spent (handoff 「D7 re-run」); the brief rightly stops re-running unchanged (2 then 6 of 192).
- §11.0 verified: NE equals 「沒做」 and takes the row's default; the row's default is 「第 1 項不出貨」; the shell consequence is spelled out in §11.0 (「頁面不綁 Ctrl+Home／End…具名 L-142-sdk-callable」).
- README §5.4 item 2 already records that 「the brief allows a re-run only for NE caused by foreign CPU」 and that the instrument question was 「the main session's call」; this ruling is that call.

**CONDITIONS.**
1. §12.4 carries the five-branch rule above *before* A0 runs, with the sentence 「若這件事永遠沒做：第 1 項不出貨（§11.0 預設）」.
2. The re-run: Firefox D1 only, N=3, 38 arms, under the lock, desktop Chrome closed, 1-minute load < 1.5 at start, no foreign process > 50 %, KWallet unlocked; the `092410` report and its docs move to `superseded/item1/` (not deleted), as before.
3. The judge is run unchanged; its output is committed as `judge-item1-after-d7-rerun-2.txt`, the previous two kept.
4. The outcome is appended under the rule in §12.4 and in README §5's D7 row (append, do not rewrite the earlier text).
5. If the branch is 「default applies」: the finding on the instrument limit is opened the same day and cites the lateness numbers above; the v22 §12 append for D7's sampling clause is written before any v22 evidence run.

---

## Q4. §34

**RULING.** The observer constant change is **「modified because of execution」, +1** (J3). Witnesses: the two committed Firefox D1 reports and their two judge outputs (in the tree before the change). 「Because of review」 stays 0: no reviewer found this; the run did. A0 is a diagnostic with a copy and changes no check: 0. The judge does not change, so **no red-first on the judge**; its existing cases already pin the arithmetic (`m_d7_late` +600 → NE; `m_d7_slow` → the +500 PASS shape; `m_d7_caret` → FAIL on a caret mismatch, independent of the constant). Do not add a +470 self-test case just to have one (CLAUDE.md §4 self-check: no new machinery). The instrument gets **two controls**, both already named: A0's differential print (at least one press where the +500 read is late and the +470 sentinel is not; a probe that cannot print different values is not a probe) and the 「edit took effect」 check in the re-run (reads at c.x, not 500.x). A stale-reply FAIL control at the new constant is not needed: that path is judge-side and constant-independent.

**WHY（給擁有者）.** 這是執行時被報告逼出來的修改，所以記在「因執行而修」那一欄加一，證人就是已經 commit 的那兩份 Firefox 報告。judge 一行都沒改，不需要先弄紅再弄綠。但儀器自己要有兩個對照：A0 要真的看到「+500 晚了、+470 沒晚」這種不一樣的值，重跑的報告裡準時的讀取要落在新常數附近而不是 500 附近，否則就是改了沒生效。「過時的回覆要判 FAIL」那條是 judge 的事，跟常數無關，已經有紅案。

**FACT CHECK.**
- README §5.5 verified: the tally for this round is 「execution 2 (J1, J2), review 0, lost-and-re-run 1 (W2)」; the §34 rule (memory, 2026-10-08) is 「checks only guard against accidents; each judging tool audited once; a check change needs a witness report; each handoff lists the two numbers」.
- Judge self-test verified at `:1300-1322`: `m_d7_slow` moves `tPosted` with the reply (+500.0), `m_d7_late` sets +600.0 → NE, `m_d7_caret` → FAIL; D10's `m_d10_fresh` mutates `ask7.caret`.
- The committed observer has the constant in one place (`}, 500);` after the `post.call`), so the edit is one token.

**CONDITIONS.**
1. README §5.5 J3 row: what (Firefox timer lateness, instrument aim), witnesses (the four files above, their commits `a46b9267`/`fd2f854a`), change (the commit of the one constant, A0's record). Tally line appended: execution **3**, review 0, lost-and-re-run 1 (+1 if a foreign-CPU re-run is spent).
2. The constant commit message names the two witness reports and this ruling.
3. The 「edit took effect」 check is written into README §5 as a number from the re-run report (median and min of `tPosted − rs.t` over the in-window reads).
4. No change to `judge_v21_shakedown_item1.py` or its tests for this ruling.

---

## Q5. What the brief did not see, and premises that are wrong

**RULING / FINDINGS.**
1. **F6 is false as stated** (see Q1 FACT CHECK): our polling runs on the page's main thread inside the window, every ~50 ms, plus the observer's per-`put` `flush`. Record it in the instrument description. A0 must keep it (same runner), so the measurement is of the real harness.
2. **A's premise is open, and the data lean neither way on the start, but do fix the end and the shape.** Lateness ceiling 60.3 ms over 384 reads, bimodal (≈10–15 and ≈45–60), cell-repeatable (B2 first presses), end drifting ~7–10 ms between runs. A fixed-phase task is the simplest reading; its start is unknown; A0 measures it. The brief's 「most likely the repaint」 is a hypothesis; the paint-reply stamps in A0 test it (a paint response landing at ≈ +495 would say repaint; none would say otherwise).
3. **「Mostly first press」 describes the tail, not the phenomenon** (rates above). Do not let the README say first presses are the cause.
4. **The handoff's locus is wrong**: the runner's hash does not change with the constant; `snippetSha256[1]` does. README must point there.
5. **Doc drift**: ARMS-item1 §2.2 (c) says ask ids ≥ `0x7F000000`; the observer uses `0x7E000000`. Harmless to the judge (it matches on `k == "ask7"` and `forRq`), fix by append in ARMS/README.
6. **F13's numbers are the diagnostic's**, the D1 reports show 250.5–254.0; cite the reports.
7. **The inclusive edge mattered once**: 550.0 (t-end-B2-n1 r1, run 2) counted in. At the new constant no read should sit within 10 ms of either edge; if one does, record it, but the inclusive rule stands as written.
8. **Chrome's first D1 run was also superseded** (D7 NE from foreign CPU, `superseded/item1/report-chrome-d1-20261017T054335.json`), so the owner's desktop Chrome has already voided three D7 cells across the day; the 「desktop Chrome closed」 condition is not optional.

**WHY（給擁有者）.** 主 session 寫「回覆跟讀取之間沒有我們的動作」不對：runner 每 50 毫秒就戳一次頁面主執行緒去撈 log，Chrome 下沒事不代表它無辜，所以診斷時要用同一支 runner 跑。數據能證明的是忙碌那段的「結尾」在 +555 到 +560 左右、而且同幾個格子每輪都中，「開頭」在哪報告裡沒有任何時間戳可以回答。「大多是第一下」只對最晚的那幾次成立，中等程度的晚響第二下反而比例更高。幾處文件寫錯的地方（runner hash、ask id 範圍、數字出處）一併用追加的方式更正。

**FACT CHECK.** All of the above are from the files and my recomputation named in 「Basis」; none rests on the brief's summaries. The brief's F-claims other than F6 (false) and F13 (provenance) hold; F4 and F8 hold with the nuances stated.

**CONDITIONS.**
1. Append to README §5 (instrument description): the polling inside the window and the per-`put` flush; the lateness shape numbers above; the correction to the handoff's locus; the ARMS id drift.
2. A0's record includes the paint-reply stamps per press, so the 「repaint」 reading becomes a measurement or is dropped.

---

**Next, in order, up to the v74 freeze:** commit `review/ruling-fable-2.md` → append spec §12.4 (pre-committed constant rule + stop rule) and README §5.5 J3, commit, before any browser starts → A0 (Firefox, `t-*`, N=3, sentinels +440/+455/+470 and paint stamps, no heartbeat, desktop Chrome closed) → pick the constant by the §12.4 rule, edit the one token in `v21_item1_observer.py`, commit with A0's record → the single Firefox D1 evidence re-run under the lock, move `092410` to `superseded/`, unchanged judge → append the outcome to §12.4 and README §5 (D7 row, snippet hashes per report, tally 3/0) → then the v74 freeze with or without the item-1 binding as the outcome says, host 0.2.25, the host arms, binding, the count.
