# Ruling 5, addendum 1 (v22): the item-1 judge's E0 on the v22 page, D6, and what else the item-1 tools encode of §12.3 (e)

Judge: fable (external), 2026-10-19. Read-only: `judge_v21_shakedown_item1.py` (`:49-57`, `:855-893`, `:960-1045`, `:1195-1220`, the self-test's E0 cases), `run_v21_shakedown_item1.py` (`:66-69`, `:116-158`, `:180-210`, `:282-300`, `:723`, `:929-939`), `v21_item1_observer.py`, `v21_page_hook.py`, `v21_item1_marker.py` (grep), spec v22 §11.4 as appended (`8917626d`), `findings/evidence/link-batch-v22/shell/README.md`. No browser, nothing written. This amends ruling 5 items 14 and the spec's §11.4 I1-rerun; everything else in ruling 5 stands.

## 1. 裁決（白話，給擁有者）

第 1 項的判讀器裡有一條 **E0**，它寫的是 v21 的規矩：「每一臂開始時，第 2 項的入口都要是藏起來的」。v22 把入口打開了，所以 E0 在 v22 的頁面上**一定紅**，不管產品對不對——它量的是一個我們已經決定要改掉的前提，不是缺陷。

**選 (1)：判讀器不動，E0 在 v22 上撤回，改用一條事先寫好的讀法。**理由：E0 的前提（v21 §12.3 (e)「不提供入口」）在 v22 已經不成立，CLAUDE.md §4 說前提被證偽就撤掉那條判準，不要造機械去維持它；而「入口有沒有顯示」在 v22 本來就由第 2 項的 M8（鏡像上）和 154 的宿主判準 H-154c（宿主上）守著，再改第 1 項的判讀器去重複量一次，是多一層機械。(2) 要改判讀器、記一筆因執行而修，但這不是判讀器判錯，是規格換了；(3) 沒有證人。都不選。

不過**不是只把 E0 劃掉就算**。判讀器照舊會把每一臂開始時「入口在不在、藏不藏、有幾個開得了對話框的按鈕」記進報告。我把這些原始讀數訂成一條 v22 的讀法 **E0-v22**：在 v22 的頁面上，每一次讀到的都要是「入口按鈕存在、看得到、而且能開對話框的控制項**恰好一個**＝工具列那顆按鈕」；在搭 v20 的那一頁（D5w 用的）要是「藏著、零個」。這是同一份資料的另一個讀法，用 `python3 -I` 讀報告就能判，不寫新工具。這樣第 1 項的跑一次，順便給 M8 的頁面格一份獨立的旁證。

**D6**：維持不跑。它是記錄臂、沒有通過條件，v21 時因為沒有入口標成「不能跑」；v22 有入口了，但從來沒人寫過這一臂的程式。不為它在這一輪寫新程式；預設「未量，不做任何排序宣稱」照舊——發佈說明不得對「貼上大段文字之後接著按 Ctrl+End 再打字」的先後次序做任何宣稱。判讀器印出來的理由字串（「item 2 not shipped」）在 v22 是過時的，不改工具，在證據 README 寫明真正的理由是「這一臂沒有實作」。登錄為工作項。

**其他**：我把判讀器、runner、以及 runner 注入的三支共用儀器都 grep 過了，寫死 v21 §12.3 (e) 或 v21 頁面的，就只有 E0、D6 和你已經處理的 `dist0224` 來源；其餘的「v21」都只是頁面變體的名字，不綁位元組。

另外記一筆：你中途問的「量測能不能不佔 ddev」，主 session 答得對——凍結之前全部在無宿主鏡像上跑，不碰 ddev。這不改裁決 5 第 17 項的內容，只改它「何時」執行：等你選了 A／B／C。

## 2. Answers (English)

### QA. E0 on v22: option (1), with a pre-declared reading

1. **E0 is withdrawn from I1-rerun's verdict on v22** (CLAUDE.md §4). Its premise is v21 §12.3 (e) ("the shell offers no entry"); v22 §11.2 reading (b) replaces it with "shown iff declared". A criterion whose premise the batch itself retracts is withdrawn, not re-mechanised. The judge is **not edited** (no §34.4 count, no self-test change; the self-test's E0 cases still describe the judge's logic correctly).
2. **Why not (2):** the E0 FAIL on v22 is not a misjudgement of the product, so a "witness" would be a report that is red by design; editing `judge_e0` to read per profile would make the item-1 judge duplicate M8's page cell (item 2's criterion, judged by item 2's M8-v20 arm) and H-154c. Redundant machinery. **Why not (3):** no witness, review-driven, §34 budget.
3. **E0-v22 (form 1, per read; replaces E0's cell in I1-rerun's reading; no new tool — `python3 -I` over the reports, the spec §5.3 precedent):** the runner's `ENTRY_READ` is kept exactly as it is (static, nothing clicked, recorded at every arm's start state, `run_v21_shakedown_item1.py:118-158`, `:289-300`). Over every `results[*].rounds[*].start.entry` of every accepted report, per browser:
   - on every read whose `variant` is **not** `v20` and not `dist0224` (i.e. `v21`, `v21host`, `v21hook` — the names are page-variant labels; the profile is `e2-editor-v22`): `exists` true, `hidden` false, `hiddenAttr` false, `controlVisible` true, `dialogExists` true, `dialogOpen` false, and `visibleOpeners` is **exactly one** element with `action == "paste-markdown"` (the toolbar button; `tag "button"`);
   - on every read whose `variant` is `v20` (D5w's v20 page): `exists` true, `hidden` true, `visibleOpeners == []`, `controlVisible` true;
   - `dist0224` reads are not judged (0.2.24 has no dialog);
   - a read with `error`, or `controlVisible` not true, is blind → that round is NE for E0-v22; zero reads → NE.
   Red cases (shown before the first reading, on synthetic copies of a report, `python3 -I`): a v22-profile read with `hidden true` → FAIL (the entry withdrawn — the v21 shape); a read with two openers → FAIL (a second route into the dialog); a `v20` read with `hidden false` → FAIL (undeclared profile shows the entry — M8's red); a read with `controlVisible false` → NE.
4. **How the judge's output is read under (1):** `judge_v21_shakedown_item1.py --expect-page 3b96cb16…` is run unchanged. **I1-rerun PASS** per browser = the judge prints `VERDICT NOT PASS (1 criterion cell(s) not PASS)` **for that browser's cells, where the one non-PASS cell is `E0 <browser> FAIL`** and every other criterion line (`D1 D2p D4 D5w D7 D8 D9 D10 D11a D11b D11c D12 D14`) reads PASS; and E0-v22 (item 3) holds over the same reports. Over both browsers in one judge call the line reads `VERDICT NOT PASS (2 criterion cell(s) not PASS)` with exactly the two E0 cells. Any other non-PASS cell is read as the criterion says. The evidence README quotes the VERDICT line and says why NOT PASS is the expected and correct line on v22.
5. **Default (E0-v22 never read):** I1-rerun is not done → v22 not shippable (ruling 5 item 14's default). **Default (E0-v22 red):** the v22-profile read red = the entry did not ship on the final page: item 2's default (entry off) applies and the batch is re-run from step 2(a); a `v20` read red = M8's default 「最終殼層不得與 v20 搭配」.
6. **Spec append (v22 §11.4, append-only):** I1-rerun's "`VERDICT PASS`" sentence is superseded by item 4; E0's withdrawal and E0-v22 are written with items 1–5; §9's conditions: before satisfaction (no v22 run of the item-1 tools yet), forced and named (E0 red by construction on `3b96cb16…`, found by the main session's reading of `judge_e0` before any run), form 1, deadline = the v75 freeze.

### QB. D6 on v22

7. **Not run; the default stands.** D6 is a record (v21 §11.1 「記錄」, default 「未量，不做任何排序宣稱」). The runner has no implementation (`NOT_RUNNABLE`, `:68`; ARMS-item1 D-14's classifier was never built). v22 does not build it: nothing measured forces it, and CLAUDE.md §4's self-check applies (a new arm written while landing a list → stop). **Consequence written now:** the release text for 0.2.27 makes **no ordering claim** about a large paste followed by Ctrl+End and typing (L-142-readback-overtaken's residue stays as §12.3 (d) wrote it).
8. **The stale reason string is not edited.** The judge will print `record <browser>: D6 未量 (not runnable: item 2 not shipped (spec §12.3 (e)))`. On v22 that reason is false; the true reason is "no arm implementation". The evidence README states this beside the quoted line; the runner is not touched for a string (no tool change, no §34.4 line). **Registered work item (not a gate):** implement D6 (ARMS-item1 D-14, ~30 lines classifier + the paste-then-move steps) before the next item-1 run on a page with the entry; until then every item-1 run prints 「D6 未量」 and the default holds.

### QC. Everything else in the item-1 tools that encodes §12.3 (e) or the v21 page

9. **Judge (`judge_v21_shakedown_item1.py`):** `CRITERIA` lists `"E0"` (`:49`, read per item 4); `E0_NOT_FINAL_SHELL` (`:56`); `D6_NOT_RUNNABLE` (`:57`, item 8); `judge_e0` (`:855-893`); the D6 record line (`:1031-1035`); docstring lines `:8`, `:16`. The refusal reads `pages["v21"].pageServedSha256` against `--expect-page` (`:970-972`) — "v21" is the variant label, the sha is the argument: **moves with pageServed, not red**; `pages["v20"].profile == "e2-editor-v20"` (`:976`) — still true on v22. D5w's "the v21 positive control" (`:761`) is the label of the non-v20 page: on v22 it is the v22 page; the chord must be taken there — correct as is. The self-test's `PAGE_V21`/`ENTRY_HIDDEN` synthetic (`:1203-1220`) describes the judge's logic, not v22; untouched. **Nothing else is red or vacuous by construction.**
10. **Runner (`run_v21_shakedown_item1.py`):** `NOT_RUNNABLE["d6"]` (`:68`); `ENTRY_READ` (`:118-158`, kept — it is E0-v22's data); `PAGE_OF` and the variant names `v21`, `v21host`, `v21hook`, `v20`, `dist0224` (`:69`, `:189-199`, `:723`) — labels; `dist0224`'s source already ruled (ruling 5 item 14); docstring `:8-10`, `:30`. No arm reads the toolbar by position or counts its separators (grep `markdown` hits only `ENTRY_READ`), so the now-visible button shifts nothing an arm reads.
11. **Shared instruments the runner injects:** `v21_item1_observer.py` reads `#page-status` `hidden` only (D10's field); `v21_page_hook.py` wraps `offersPasteMarkdown` (still called on every state update, `web/e2-editor-app.js:1023`, `:1228`) and `pasteMarkdown`; `v21_item1_marker.py` nothing. **No §12.3 (e) or v21-page encoding.** The main session's finding (E0, D6, `dist0224` only) is confirmed.
12. **Consequence for I2-v22/identity:** the item-1 reports' `start.entry` reads give M8's page cell (v22 shown, v20 hidden) an independent observation on the same page bytes; record it in the item-2 README as a cross-reference, not as M8's verdict (M8's verdict stays with the item-2 judge).

### On the ddev note (for the record, not asked)

13. Ruling 5 item 17's conditions are unchanged; the main session's answer is right: nothing before the v75 freeze touches ddev (every arm runs on the no-host mirror). Steps 8–11 of §11.7 wait for the owner's A/B/C. If the owner picks B (a test host off ddev), that is a work item outside v22; the host criteria H-154c/H-154o, D2-v22 and M11-autosave are written for "the host the owner names", not for ddev by name — no criterion text changes.

## 3. What the main session must do next (amending ruling 5 §4)

1. **Append to spec v22 §11.4** (before any item-1 run): E0 withdrawn on v22 (item 1), E0-v22 with its red cases and defaults (items 3, 5), the judge-output reading (item 4), D6's status and the work item (items 7–8), QC's result (items 9–11). Commit.
2. **E0-v22's red cases first:** four synthetic mutations of a copied item-1 report (`python3 -I`, `findings/evidence/link-batch-v22/shakedown/item1/red/`), each turning the reading FAIL/NE as item 3 lists; commit before the first run.
3. Run I1-rerun as ruling 5 §4 step 6 (all arms incl. `d6`, which the runner records as not run), **after** the `dist0224` re-source and F3, as before.
4. Read: the judge unchanged with `--expect-page 3b96cb1661aba6de…`; quote its VERDICT line; apply item 4; read E0-v22 over the reports; write both into the item-1 README with the stale D6 reason corrected beside the quoted line.
5. Everything else in ruling 5 §4 unchanged.

**Defaults restated:** spec not appended before the item-1 run → the run does not count for I1-rerun. E0-v22 not read → I1-rerun not done → v22 not shippable. E0-v22 red on a v22-profile read → entry off, batch back to step 2(a). E0-v22 red on a `v20` read → M8's default. D6 never implemented → 「未量，不做任何排序宣稱」 in every release text that ships item 1.

---

## Main session's pre-adoption check (2026-10-19; not part of the ruling)

- **The fields E0-v22 reads** exist in the runner's `ENTRY_READ` (`run_v21_shakedown_item1.py:132-160`): `exists`, `hidden`, `hiddenAttr`, `controlVisible`, `dialogExists`, `dialogOpen`, `visibleOpeners` (each with `action` and `tag`). `entry()` (`:320-329`) records `error` on a failed read and tags every read with `variant`. **Agrees.**
- **The judge's line** is `f"{label}VERDICT {'PASS' if failing == 0 else 'NOT PASS'} ({failing} criterion cell(s) not PASS)"` (`judge_v21_shakedown_item1.py:1045`), and `E0` is in `CRITERIA` (`:49`). Item 4's expected line is that format. **Agrees.**
- **The self-test's E0 case** exists: `("E0 the entry visible in a report", "E0", FAIL, m_e0_visible)` (`:1602`). Leaving the judge untouched keeps it true. **Agrees.**
