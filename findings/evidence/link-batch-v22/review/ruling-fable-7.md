# Ruling 7 (v22): the ddev window for host 0.2.27 — tonight is named by delegation, not by the owner's words; the install order, the HTTP-check binding, what stops the session, and what a red arm does to the install while the owner sleeps

Judge: fable (external, the judge of ruling 6 and its addendum), 2026-10-20 ~03:30. Read-only: the files the brief and its addition name, read by path; `git log`/`git show --stat` on the study repo and read-only `git log`/`status`/`ls-files` on the host repo; the process list and load; no ddev command, no browser, no make, no lock, nothing written. Brief: `findings/evidence/link-batch-v22/review/brief-fable-7-ddev-window.md` (`44f30990`) plus the coordinator's G6 addition. `CLAUDE.md` 「驗收判準的形式」 §1–§11 applies. Shape as ruling 6.

## 1. 裁決（白話，給擁有者）

**問題。**規格 §13 是你 10-19 選的 A：碰 ddev 的步驟（裝 0.2.27、跑四支宿主臂）要集中在**你指定的時段**，沒有時段就做到凍結 v75 為止交接。鏡像那邊今晚全部過了、v75 也凍了，就停在這裡。你 01:40 說「全部都跑，我先去睡，有疑義的發給 fable，我授權給他代我決定」——這句話**沒有指定時段**，主 session 也沒把「時段」這個問題用那幾個字問過你。所以它把這題當疑義交給我。

**我的決定：今晚算時段，由我代你指定，範圍有界。**理由不是「你那句話已經指定了」（它沒有），而是兩件事加起來：(1) 你明說把疑義交給我決定；(2) 你選 A 的理由是「量測佔用 ddev 會讓我其他專案都不能進行」，而今晚那件事不會發生——03:12 `ddev list` 只有 `litecore` 在跑，其他專案全停著，你在睡，整套宿主步驟約 1.5–2 小時、05:30 前結束。沒有任何一天的白天時段會比今晚更符合你定這條規則的用意。**這只算這一次**：§13 的規則不變，之後的時段還是你指定。

**要先跟你說的一件事。**`ddev occ upgrade` 這個指令在 0.2.25 被權限系統擋過（最後是你自己打的），0.2.26 是你打了指令由 session 代跑。今晚很可能又被擋。被擋就照裁決 5 第 17 項第 (6) 條：**停手、還原、交接**——不排錯、不繞。還原在這個分支不需要任何 ddev 指令（版本登記根本沒改到）：把 0.2.26 的引擎檔案從封存複製回去、把版本號那一個 commit revert 掉。早上你會看到交接第一行寫「ddev 還是 0.2.26；0.2.27 的封包已封存；要裝就是這三行」。

**順序。**(1) 先把還原方法寫進 `host-0.2.27/README.md`，並核對現在裝著的 `engine/` 跟 0.2.25 封存逐檔相同（這就是還原來源）；(2) HTTP 檢查工具要複製一份、只改 v21→v22 兩條路徑和檔名——先在**還沒動過的 0.2.26** 上跑它的紅案（v22 的路徑在 0.2.26 的 manifest 裡找不到，必須紅），再用；(3) 打包、封存、升版號 commit；(4) `ddev occ upgrade`；(5) HTTP 綠案；(6) `HOST_EXPECT["v22"]`；(7) 四支宿主臂，每一支之前先過桌面閘門，Chrome 再 Firefox，各三輪。

**臂紅了怎麼辦（你在睡）。**分兩種：
- H-154c、D2-v22、M11-autosave 任何一支 **FAIL**（產品真的不對：對話框蓋住編輯器、Ctrl+Home 後 Backspace 吃字、貼上後不自動存檔）→ **把檔案還原成 0.2.26**（引擎檔案從封存複製回去、revert 版本號），再跑一次 `occ upgrade`。要先講清楚：Nextcloud 不會降版，`app:list` 之後**還是會寫 0.2.27**，但送出去的位元組是 0.2.26 的；這個「標籤 0.2.27、內容 0.2.26」的狀態寫在交接第一行，由你早上處理。
- 只是 **NE**（量不到：桌面髒、工具錯、沒讀到）而沒有 FAIL → **0.2.27 留著不動**，交接寫明哪一支沒成立、原因是什麼、怎麼還原；早上你決定。理由：還原是一個從來沒在這台 ddev 上真正執行過的程序，而且會留下標籤不符的狀態；為了一個「沒量到」去跑它，風險比留著一個鏡像判準全過的候選還大。
- 四支全過 → 0.2.27 留著當你日常用的未計數候選（10-12 你的裁示）。

**什麼會讓 session 停下來。**任何錯誤或權限拒絕；`ddev list` 出現別的專案在跑；桌面閘門髒（等最多 10 分鐘，還髒就停）；你醒來打任何一個字；或到 07:00 還沒跑完——都只跑完手上那一支臂就停，交接。

## 2. Answers (English)

### Q1. Does the owner's 「全部都跑」 name tonight as the window?

1. **No — and tonight is still the window, named by the delegate.** The owner's words name no time, and the question 「時段」 was never put to him; P1's "he knew the host steps were next" is weaker than the brief admits (the list came after his words). What his words do is **delegate every doubtful question of this round** (「有疑義的發給 fable，我授權給他代我決定」; memory `away-owner-delegates-decisions-to-fable`, eleventh instance, where the main session correctly logged this very question as a 疑義 for fable). So the question is mine to decide, and I decide it on §13's **reason**, not its letter: choice A exists because host measurements occupying ddev stall the owner's other projects and his own `ddev start/stop` breaks a measurement (memory `ddev-is-shared-do-not-occupy`). Tonight neither can happen: `ddev list` at 03:12 shows only `litecore` running, every other project stopped or paused; the owner sleeps; the host steps take ~1.5–2 h and end before ~05:30. No daytime window the owner could name serves the rule's purpose better.
2. **Bounds of the naming:** this window only; §13's rule (「時段由擁有者指定」) is unchanged for every later window, K included. Append §13.1 recording the naming, its grounds, its bounds (item 9) and the stop conditions (item 10), before any ddev step.
3. **(b) and (c) rejected.** (b) spends nothing but gains nothing: nothing measured depends on waiting, and the rule's reason is not engaged. (c) rewrites the live app's `engine/` with no measurement — a ddev-side change that buys only the state item 17 (7) forbids.
4. **Form / default.** A one-time scheduling decision (form three, registered — not a criterion). Default if never named: §13's stop point — hand off after §11.7 step 7, which is exactly where the tree stands now (`1d8c9e5f`).

### Q2. Conditions, order, and what stops the session (P2, G6, the coordinator's order question)

5. **Item 17's eight conditions verbatim** (spec §11.5), with these precisions:
   - **(4) 「一字不改」 means the procedure and the tools are reused, not re-invented; a tool's profile binding moves with a witness.** G6 is such a binding: `host-0.2.25/http_served_page.py` pins `PATHS` to `profiles/e2-editor-v21/…` (`:20`) and `NAME` to `host-0225-http-check.odt` (`:21`); on 0.2.27's manifest (`profiles/e2-editor-v22/…`) the unchanged tool reads 「not in the manifest」 for a reason that is not the host's. Precedent: 0.2.25 wrote its own copy "in the shape of" 0.2.24's checker. **Ruling:** copy it to `host-0.2.27/http_served_page.py` and change only `PATHS` (v21 → v22) and `NAME`; a binding, **0/0**, with two witnesses: (a) the diff against the 0.2.25 tool is exactly those two lines; (b) **the red case runs first, on the untouched 0.2.26 host, before packaging** — the copy against the installed `engine/MANIFEST.json` (0.2.26's, a v21 manifest) must be red on the v22 paths (「not in the manifest」, and whatever status the host returns for a path it does not have). That red case needs no package in place and no change to the host, so it also satisfies CLAUDE.md §6 before the tool passes anything. The 0.2.25-shape red (the new serving against 0.2.26's archived manifest) may be added **after** `occ upgrade`; it is not needed before.
   - **Same class, check before use:** `check_engine_decoded.py` (run on the packaged copy before install on 0.2.25) is read for v21 literals before it is run; a profile pin there is handled exactly as G6 (copy, the pin only, red first).
   - **(5) is a check, not only a sentence:** before packaging, verify the restore source — `diff -rq` of the installed `~/Projects/Nextcloud_Apps/litecore/engine/` against `build/archive/host-0.2.25-engine-f5f0df762e1855f2/` equal except `ATTRIBUTION.md` (as 0.2.26's `package-unchanged.txt` recorded), and the archive's `MANIFEST.json` `buildId` `f5f0df762e1855f2`. Unequal → stop before packaging; the restore source is not what is installed.
   - **(6) the two restore shapes, written now:** a refusal or error **before `occ upgrade` has run** (the likely branch, G6's two facts) → copy the archive back into `engine/` (`diff -rq` equal), `git revert` the bump commit if it was made; **no ddev command is needed**, the registered version never changed. A refusal or error **after** `occ upgrade` succeeded → item 13.
   - **(7) holds literally:** nothing measured on the host between the package landing and `occ upgrade` done — the HTTP red case is before packaging, the green check after `occ upgrade`.
   - The host repo commit (`info.xml` 0.2.26 → 0.2.27, one line) carries `Co-Authored-By`, no `Claude-Session`, no push; restores are `git revert`, never a reset.
   - **Registered, not built (CLAUDE.md §1, §4):** the HTTP tool's `PATHS` is a hand-enumerated binding a profile move invalidates (the same class as ruling 6's `positive_control`); the next tool round derives the worker and wasm paths from the manifest (the page's `workerUrl`), with tonight's red case as its witness.
6. **Order (answering the coordinator): the red case first, then package, then bump, then `occ upgrade`, then the green check** — not "package, red case, bump, upgrade". In full:
   1. desk gate clean (`shakedown/desk_gate.py`); read-only `ddev list`: `litecore` OK, nothing else OK;
   2. `host-0.2.27/README.md` with the restore of item 5 (both shapes) and the restore-source check, committed before anything touches the app dir;
   3. G6: the tool copy, its diff witness, its red case on the untouched 0.2.26 host; `check_engine_decoded.py` read for pins; commit;
   4. `package_m3_engine.py --app ~/Projects/Nextcloud_Apps/litecore` → buildId; `check_engine_decoded.py` on the packaged copy; archive to `build/archive/host-0.2.27-engine-<buildId>/` with `ATTRIBUTION.md` (0.2.25's shape, naming v22's profile, v75's bundle, the page `3b96cb16…`, HTML `b9c2b975…`);
   5. `info.xml` 0.2.26 → 0.2.27, commit (local);
   6. `ddev occ upgrade`; `app:list` 0.2.27, maintenance false. **Refused → item 5's first restore shape, hand off** (item 14's first line);
   7. the green HTTP check against the new manifest (page `3b96cb16…`, worker `0d55bcfa…`, wasm `f7a40bcc…` under gzip and zstd; address starts with the new buildId); optionally the 0.2.25-shape red;
   8. `HOST_EXPECT["v22"]` in `run_v21_d2.py` (version 0.2.27, servedPage `3b96cb16…`, hostShellDigest `e35923a0…`, hostWasm `f7a40bcc…`; `--page` choices gain `v22`); `--identity-only --page v22` → `[]`; `--page v21` red on exactly version, page, wasm; `--self-test` 19/19. A binding, 0/0;
   9. the arms, each preceded by the desk gate and a read-only `ddev list`: H-154c/H-154o (`diag_markdown_dialog_on_host.py --h154 … --expect-version 0.2.27 --expect-build-id <id>`), D2-v22 (`run_v21_d2.py --mode host --page v22`), M11-autosave (`m11_autosave.py … --expect-version 0.2.27 --expect-build-id <id>`); Chrome then Firefox, N=3; their offline red cases (10/10, 8/8, 19/19) are already on file and are not re-run.
7. **What stops the session** (after the arm in progress, never mid-arm): any error or permission refusal (item 17 (6)); `ddev list` showing another project OK; the desk gate dirty after a bounded wait (`--wait 600`); any Chrome, zen or build process appearing (the gate's own clauses); the owner typing anything in the session; **07:00** — the window closes when the owner's morning begins, whichever comes first. The session itself stays idle during each arm (ruling 6 addendum 1 item 9): `tail` only.
8. **Form / default.** Per step and per arm (form one). Default when a condition fails: stop, restore per the shape that applies, hand off with the exact line.

### Q3. A red host arm, or an error, while the owner sleeps

9. **Distinguish FAIL from NE; the handoff's "ask the owner" is deferred to the morning, not replaced by a blind rollback.**
   - **FAIL on H-154c, D2-v22 or M11-autosave** (each default bars the candidate: 0.2.27 不可出貨 / v22 不可出貨 / 頁面沒有入口; each is a daily-use hazard — a dialog over the editor, a Backspace that eats a character after Ctrl+Home, no autosave after a paste) → **restore the files**: `engine/` from the 0.2.25/0.2.26 archive (`diff -rq` equal), `git revert` the bump; then `ddev occ upgrade` once, its output recorded, not troubleshot. **Expected state, written in advance:** Nextcloud does not downgrade an app, so `app:list` will still read **0.2.27** while every served byte is 0.2.26's — the handoff's first line says so and how the owner clears the label (his call; nothing further is done tonight). H-154o's FAIL cases (focus not in the textarea, box outside the viewport) are not in this list: its default is 「位置未量，照實寫」, a record, and a top-left box is a finding for the next host version (ruling 5 item 19), not a bar.
   - **NE only, no FAIL** (foreign CPU, a tool error, a blind read) → **leave 0.2.27 installed**; hand off with the arm, its recorded cause and the restore lines; the owner decides in the morning. Grounds: the rollback after a successful upgrade has never been executed on this ddev and leaves a label mismatch; running it at 05:00 for a cell that was not measured is a larger risk to the owner's daily use than keeping a candidate every mirror criterion passed. "0.2.27 stays only if all pass" (handoff Next 8) is read as "stays **for daily use** only if all pass": with an NE it stays installed **as not established**, which the first line says.
   - **All PASS** → 0.2.27 stays, the uncounted candidate for daily use (owner's 10-12 ruling; §13 K deferred).
   - **Error or refusal mid-install** → item 5's restore shapes: before `occ upgrade` ran, files + revert and no ddev command; after it ran, as the FAIL branch.
10. **Form / default.** Per arm outcome (form one). Default if no arm runs: 0.2.27 not established; whatever state ddev is in is the handoff's first line.

### Q4. What the brief gets wrong or leaves out

11. **P1's basis.** The owner's words do not name a window; the grounds are delegation plus the rule's reason not being engaged (item 1). Write it that way in §13.1, or the next session will read 「全部都跑」 as a standing window.
12. **The rollback is not a clean switch** (item 9): untested on this ddev, and label-breaking after a successful upgrade; before `occ upgrade` it needs no ddev command at all. P3's "roll back on any red" becomes FAIL → restore, NE → leave and hand off.
13. **G6 and its class** (item 5): the HTTP tool's pin, the order of its red case, and `check_engine_decoded.py` read for pins before use.
14. **The handoff's first line has four possible shapes**, each written now: (a) 0.2.27 installed, all four arms PASS — daily use; (b) 0.2.27 installed, arm X NE for cause Y — not established, restore lines; (c) files restored to 0.2.26 after FAIL on X, label still 0.2.27 — how to clear it; (d) nothing registered changed (refused/error at step N), 0.2.27 package archived at `build/archive/host-0.2.27-engine-<buildId>/` — the three lines to install (copy, bump, `occ upgrade`).
15. **The window's end** (07:00 or the owner awake) and the bounded desk-gate wait are missing from P2.
16. **§34.4 tonight:** execution 0, review 0; two bindings 0/0 (the HTTP tool copy, `HOST_EXPECT["v22"]`); one registered work item (item 5, last bullet).
17. **Nothing else wrong.** G1–G5 reproduce (section 3); the owner's 「需要建置的話也請代替我建置」 is not needed tonight (no compile in steps 8–9).

## 3. G-claims checked

- **G1:** `git log`: `1d8c9e5f` (freeze v75, cutover; `web/e2-editor-app.js` 2 lines, `expected-gesture-offers.json` profile, relink queue re-anchor, bundle v75); `98508912` (I1-rerun PASS); `63362c9d` (E2 PASS); `freeze-v75/README.md`: bundle `5b14038e…`, `make test-e2-c-static` 0, E1-C intact, shell digest `e35923a0…` over `dist/` and the tree, "What is still ahead: host 0.2.27 … K".
- **G2:** spec §13 second bullet verbatim as quoted (`:449-460`): the window is the owner's, named after the mirror chain; no window → hand off after step 7; 「裁決 5 第 17 項管的是「能不能」，這一條管的是「什麼時候」」. Memory `ddev-is-shared-do-not-occupy`: the owner's reason (「這樣我其他專案都不能進行了」), the shared router, choice A. Memory `away-owner-delegates-decisions-to-fable`, eleventh instance (2026-10-20 01:40): the main session logged the ddev-window question as a 疑義 for fable 「不自己認定」 — consistent with the brief.
- **G3:** not re-run (no ddev command allowed to me); the host repo read-only: HEAD `3c01876` (0.2.26), tree clean, `appinfo/info.xml` `<version>0.2.26</version>`, `engine/` git-ignored (`.gitignore:4`). Process read at 03:14: load 0.54, no chrome/firefox/zen/make/runner. The restore archive exists: `build/archive/host-0.2.25-engine-f5f0df762e1855f2/{ATTRIBUTION.md,MANIFEST.json,files}`, `buildId f5f0df762e1855f2`, files under `profiles/e2-editor-v21/…`; 0.2.26's README: the package byte-equal to that archive (`package-unchanged.txt`), rollback written, never executed.
- **G4:** the eight conditions as spec §11.5 and ruling 5 item 17 state them; the handoff's Next 7–8 as quoted; `package_m3_engine.py` docstring: "Reads dist/, never writes it. Replaces `<app>/engine/` whole: builds `engine.new/` beside it, then swaps"; buildId = sha256 of the decoded files' canonical JSON. Offline red cases: 154 10/10, M11 8/8 (brief; on file per the handoff).
- **G5:** nothing measured so far depends on tonight — agreed; the mirror criteria are closed and committed.
- **G6 (addition):** `host-0.2.25/http_served_page.py:20-21` as quoted; the tool compares served bytes with a manifest's `files[path].sha256` and the address with the manifest's `buildId`; 0.2.25's red case (`http-served-red-against-0224-manifest.txt`) ran with the new package in place against the old manifest — the shape item 6 moves to after `occ upgrade`. 0.2.25's README: `occ upgrade` refused to the session by the auto-mode classifier, run by the owner; 0.2.26's: run by the session on the owner's typed command. So the refusal branch is the expected one, as the coordinator says.

## 4. What the main session must do next, in order

1. **Append spec §13.1** (append-only, before any ddev step): tonight's window named by delegation (items 1–2), its bounds and the stop conditions (item 7), the install order (item 6), the §11.5 (4) precision and G6's binding with its witnesses (item 5), the FAIL/NE rule for the install (item 9), the four first-line shapes (item 14), the registered work item. Commit.
2. **Steps 1–3 of item 6** (desk gate, `ddev list`, the README with the restore and the restore-source check, the HTTP tool copy with its diff and its red case on the untouched 0.2.26, `check_engine_decoded.py` read for pins). Commit.
3. **Steps 4–6** (package, decoded check, archive with `ATTRIBUTION.md`, bump and commit, `ddev occ upgrade`). **Refused or error → restore shape one (files + revert, no ddev command), write first-line shape (d), hand off.** Do not retry, do not rephrase the command, do not troubleshoot.
4. **Steps 7–8** (the green HTTP check, `HOST_EXPECT["v22"]` with its three witnesses). Commit the evidence under `findings/evidence/host-0.2.27/`.
5. **Step 9**, one arm at a time, desk gate and `ddev list` before each, the session idle during each; stop on any trigger of item 7, finishing the arm in progress.
6. **Read each arm with its own judge** as ruling 5 items 18–20 and §11.5 pin them; apply item 9 at the end: all PASS → leave; any FAIL on H-154c / D2-v22 / M11-autosave → restore shape two, record `app:list`'s label; NE only → leave, not established.
7. **Hand off** with the first line in the shape that applies (item 14), the §34.4 line (item 16), the owner's hand tests on 0.2.27 (F3-hand; Ctrl/Cmd+Home/End; the dialog's look, with H-154o's position reading in plain words), the release-text consequences, and the registered work items. Push nothing.

**Defaults restated:** §13.1 not appended before the first ddev step → the window is not named → §13's stop point (hand off now). Restore source not byte-equal to the installed engine → stop before packaging. `occ upgrade` refused → files restored, nothing registered changed, hand off. A FAIL on a barring arm → files restored, label 0.2.27 recorded. An NE → 0.2.27 stays, not established, the owner decides. 07:00 or the owner awake → stop after the current arm.

---

## The main session's check before adopting (opus, 2026-10-20 ~03:40)

The text above is fable's, committed verbatim (extracted from the subagent's transcript). Checked before acting on it:

- **G6's line numbers.** `PATHS` and `NAME` are at `host-0.2.25/http_served_page.py:23-24`, not `:20-21`; lines 20–21 are imports. The content is as quoted, so the binding is the same.
- **`check_engine_decoded.py` (item 5).** The tool is `findings/evidence/release-0.2.13/check_engine_decoded.py`, not a file under `wasm_sdk_probe/tools/`. It reads `engine/MANIFEST.json` and every packaged file, and compares the decoded `e2-editor-app.js` with `dist/` and `web/`. It holds no profile literal (grep `e2-editor-v[0-9]`: none), so it is used unchanged.
- **The host repo (G3).** `.gitignore:4` is `/engine/`, so `engine/` is untracked and a restore of it is a file copy, not a git operation. As stated.
- **The ruling's other G-claims** (spec §13's text, the two memories, the 0.2.25 and 0.2.26 records of `occ upgrade`) match what the main session read for the brief.

Adopted as written.
