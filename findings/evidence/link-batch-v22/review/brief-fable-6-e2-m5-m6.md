# Ruling request 6 (v22): item 2's first reading — M5 not established by a binding the v22 move missed, Firefox M6 not established by a foreign process

To: fable (external judge). From: the main session (opus), 2026-10-19 ~17:20. **Read-only for you**: read files, `git show`, run `python3 -I` readers over the reports. No browser, no make, no ddev, nothing written.

**Authority.** The owner, in this session, was asked 「第 2 項的 M5（儀器綁定漏搬）與 Firefox M6（外部 CPU 負載）要怎麼處置？」 and chose **「A 送 fable 裁決（建議）」**, whose text read 「附上實測數字與我的傾向，請 fable 代你決定重跑範圍、停止規則、怎麼組合判定；我把白話理由轉述給你」. So: decide for the owner on this question, and **put a short plain-language section in zh-TW for the owner first** (「裁決（白話，給擁有者）」, as rulings 4 and 5 did). Read `CLAUDE.md` 「驗收判準的形式」 §1–§11 before ruling. The spec is `specs/SPEC-M3-link-batch-v22.md` (§11 is ruling 5; §11.2 is E2; §11.7 is the order; §13 the owner's two decisions). The handoff is `handoff/HANDOFF-2026-10-19c-v22-shell-items-evidence-chain-running.md`.

All paths below are under `findings/evidence/link-batch-v22/shakedown/` unless written in full; tools are under `wasm_sdk_probe/tools/`.

## Facts (each checked by the main session today)

**F1 — the reading.** The detached chain (`chain-item2-item1.sh`, started 12:13 at `0da3cc33`) finished item 2: Chrome 12:13–14:04 exit 0, Firefox 14:04–15:58 exit 0 (`chain.log`). Item 1 is still running (Firefox, started 16:46). The unchanged judge, `--expect-page 3b96cb16…`, gives exit 1, `VERDICT NOT PASS` (`item2/first-reading/judge-item2-first.txt`):
- every cell PASS in both browsers except: **M5 NOT_ESTABLISHED in both** (r1, r2, r3: "no probe.wasm GET in the proxy's log"), and **Firefox M6 NOT_ESTABLISHED (2 passed)** (r2: "foreign CPU load");
- no report was refused (identity, page, wasm, population all accepted).

**F2 — M5's cause: a v21 default the v22 binding move did not list.**
- `v21_network.positive_control(entries, mirror_port, profile: str = "e2-editor-v21")` (`v21_network.py:379-386`) looks for a GET ending in `profiles/<profile>/probe.wasm`.
- The runner calls it without `profile` (`run_v21_shakedown_item2.py:1233-1234`).
- The M5 mirror served `e2-editor-v22` (`results.m5.identity.profile`, both reports). Every recorded probe.wasm GET is `/profiles/e2-editor-v22/probe.wasm` (Chrome 149, Firefox 123 in the kept log; v21 GETs: 0).
- So each round's `positiveControl` was recorded `None` and the judge's NE line fires (`judge_v21_shakedown_item2.py:449-451`) before any item of the round is read.
- Spec §11.7 step 3 lists the binding moves by hand (DEFAULT_PROFILE and EXPECTED, the judge's WASM, dist0224, CHROME_ONLY, the long-paragraph pins). This default is not in the list; `f0f9b3fd` moved exactly the listed ones. In CLAUDE.md §1's terms the list was a hand enumeration.
- **Same shape, no effect:** `v21_workers.shipped_worker_text(profile: str = "e2-editor-v21")` (`v21_workers.py:62-63`), called without a profile at `run_v21_shakedown_item2.py:1340`, feeds the instrumented workers of the `bytes` and `trace` pages. `dist/profiles/e2-editor-v21/sdk-worker.js` and `…/e2-editor-v22/sdk-worker.js` are both `0d55bcfa…` (sha256 today), so the instrumented bytes are what v22 would give.
- **Census** (grep of default-argument profile literals and `"e2-editor-v2N"` strings in every local module the two item runners and judges import): only these two. Item 1's `e2-editor-v20` strings are D5w's intended v20 page; `judge_v21_shakedown_item1.py:1210-1211` is self-test data. No item-1 tool imports `v21_network` or `v21_workers`.

**F3 — what the recorded data can and cannot recover.**
- The report keeps only the last 3000 proxy entries (`run_v21_shakedown_item2.py:1263-1264`); both reports hold exactly 3000. The positive control itself is computed live from the full in-memory log (`:1233`), so the cap did not cause the NE, but it means rounds 1 and 2 cannot be re-read: the kept log starts after round 2 began in both browsers.
- Round 3 is covered: re-reading the kept log with `profile="e2-editor-v22"` finds the round's GET (Chrome t=…601.5, Firefox t=…359.5, both 200) (`item2/first-reading/m5-positive-control-diagnostic.txt`).
- **Diagnostic, not a verdict:** with every round's control assumed present, `judge_m5` reads Chrome PASS 114 / Firefox PASS 111 (the 3 fewer are dialog-route items the judge skips on `inputIntact: false`, `:468-469`). Each round's second control (`/m5-control`) is in both the proxy's and the listener's log; 0 runner errors. With the controls present Chrome would also print 11 non-target info requests (`mtalk.google.com:5228` ×9, `android.clients.google.com:443` ×2), recorded and not judged (ruling S3).

**F4 — Firefox M6 r2.**
- `foreignCpu.ok: false`: one process over the 50 % limit, `chrome --type=renderer … --extension-process`, 81.0 %, whose `--crashpad-handler-pid=2745205` is the owner's desktop Chrome (not a runner's). The runner's own Chrome had exited at 14:04.
- The round's own numbers: busy→ready 558.6 ms (bound 10,000), `busyEndState: ready`, one Undo restored (`s2EqualsR.same: true`). r1 577.3 ms, r3 553.6 ms, both PASS. Chrome M6: 659.4 / 378.3 / 357.2 ms, 3/3.
- `desk.log` records 39–40 Chrome processes at the start of every chain step (the owner's desktop Chrome, present throughout). The pre-run checks did not refuse.
- ARMS-item2 M6 already says "Run alone, with the desk checked" (`findings/evidence/link-batch-v21/shakedown/ARMS-item2.md:135`).

**F5 — the written rules.**
- v21 spec (copied verbatim into E2 by v22 §11.2): 「缺報、缺回、NE 一律等於「沒做」，套用該條的預設」 (`specs/SPEC-M3-link-batch-v21.md:343`). M5's and M6's defaults: no entry (ARMS-item2 `:123`, `:134`). v22 §11.2 and §11.8: item 2 not done or red → `PASTE_MARKDOWN_ENTRY_SHIPS = false` before the freeze, pageServed re-recorded.
- v22 §11.7 step 5: 「`judge_v21_shakedown_item2.py --dir … --expect-page <pageServed>` 兩個瀏覽器都 exit 0」.
- Precedents for a re-run, each granted by a ruling with a stop rule:
  - v21 §12.4 (e) 3: D7's reads all in the window and NE only from foreign CPU → one more run, once; (e) 5: instrument invalid → that run void, cause found, re-run once, not counted toward the rule.
  - v21 §12.5 (e) 3 (ii): an external cause recorded in the report → one re-run per browser.
  - v22 §11.3.1 (F3): 「每一格取自它的程序跑對的那一份報告，沒有任何一格因為產品結果而重跑」. F3's tool reports per variant; item 2's judge reads one report per browser.

**F6 — what the default would cost** (inference; read before relying on it). Entry off changes the page bytes, so pageServed moves off `3b96cb16…`. The item-1 reports now being taken are on `3b96cb16…`, so I1-rerun would need a new run on the new page (about 1 h per browser). E0-v22 as written expects the entry shown, so it would need a reading for the entry-off page. The handoff's Next step 4 already flags this branch as needing a ruling before any run.

**F7 — the runner and judge mechanics.**
- `--arms m5` runs M5 alone in its own proxied browser (`run_v21_shakedown_item2.py:1446-1452`). `--arms m6` runs M6 alone in a fresh browser (`:1350-1366`). Both can share one invocation.
- The runner refuses to overwrite `report-<browser>.json` (`:1318-1320`). The judge needs exactly one report per browser per `--dir` (`judge…:797-807`).
- **Synthetic, not evidence** (`item2/first-reading/synthetic-partial-reading.txt`): the unchanged judge on copies that carry only the re-run arms prints those cells (Chrome M5 PASS 114; Firefox M5 PASS 111, M6 PASS 3) and FAIL/NE "missing" for every other cell, `VERDICT NOT PASS`, exit 1.
- Cost on this run: M5 834.7 s (Chrome) and 959.5 s (Firefox); M6 49.0 s (Firefox). A whole item-2 re-run was 1 h 51 m (Chrome) and 1 h 53 m (Firefox).

## The main session's leaning (claims for you to check, not settled)

- **P1. Fix.** Remove the `profile` default from both functions (a required argument). The runner passes the profile of the mirror it actually built: `identity["profile"]` for M5, and the profile under test for the worker. A future profile move then reaches the control through the mirror's identity, per instance (form one), instead of through a list. Witness: the chain's own reports (all six rounds NE) and F3's round-3 lookup (v21 → None, v22 → the GET). A unit test is red on today's code and green after the fix. §34.4: **execution +1** (the positive control). The worker default rides in the same commit at 0, because it changed no byte.
- **P2. Re-run only the cells the fault or the foreign process voided.** Chrome `--arms m5`; Firefox `--arms m6,m5`. N=3, the same page bytes, a fresh `--out` (`item2-rerun/`), S-9 lock, after `CHAIN DONE`.
- **P3. Reading.** E2 per browser = each M cell from the report whose procedure ran right: M5 (both) and Firefox M6 from the re-run's judge lines; every other cell from `judge-item2-first.txt`. The re-run reports must pass the judge's `refuse()` and I2-v22 (`htmlSourceSha256` = `b9c2b975…`, identity = the final candidate). The README quotes both judge outputs. This departs from §11.7 step 5's literal "one call, exit 0", so it needs your word, or a whole re-run.
- **P4. Stop rules, pinned before the re-run.**
  - M5: any FAIL → FAIL, entry off (the default). NE again with a cause in the runner → stop and hand off, no third run.
  - Firefox M6: this one re-run only. NE again only from foreign CPU → one more run, after asking the owner to close the desktop Chrome for those two minutes (§12.4 (e) 3's shape). Any FAIL → the default.
- **P5. Not re-run.** The rest of item 2. Item 1 is not touched by this fault class (F2's census).
- **Alternatives I see:**
  - (C) Re-run item 2 whole in both browsers, ~4 h. The judge is then read literally.
  - (D) Take the default, entry off, with F6's cost.

## Questions

- **Q1.** Is P1's fix right? Is the §34.4 count (+1 / 0) right?
- **Q2.** May M5 (both browsers) and Firefox M6 be re-run alone, and read per cell as in P3? Or must it be (C) or (D)? Is F3's round-3 lookup worth anything as evidence, or is it diagnostic only, as I treat it?
- **Q3.** The stop rules (P4). Should the owner be asked to close the desktop Chrome **before** the re-run instead of only after a second NE?
- **Q4.** Is F2's census complete for both items' tools? Run your own (CLAUDE.md §5). Does the 3000-entry cap need a change before the re-run? Does anything else in the first reading need a line in the README: the `treeHead` mix the handoff notes, or Chrome's background requests as M5 info?
- **Q5.** Anything this brief gets wrong or leaves out.

## Answer format

As rulings 4 and 5:
1. 裁決（白話，給擁有者）, zh-TW, short;
2. answers Q1–Q5 in English, each with its form (§1) and its default (§2);
3. the F-claims you checked;
4. "What the main session must do next, in order", including the spec append (append-only) and when it lands relative to the re-run.
