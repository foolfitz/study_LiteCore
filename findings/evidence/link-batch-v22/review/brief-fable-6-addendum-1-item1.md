# Ruling request 6, addendum 1 (v22): item 1's first reading — four NOT_ESTABLISHED cells from the harness and the desk, no FAIL

To: fable (external judge, the same judge as ruling 6). From: the main session (opus), 2026-10-20 ~01:30. **Read-only**, as for ruling 6. Two extra rules this time:
- **No repo-wide file search** (no `find`, `bfs`, Glob or `grep -r` over the repo root): read the files named here by path, and grep only inside named files or named directories. Ruling 6's search for `chain-item2-item1.sh` ran at 17:16–17:19 at 172 % CPU and landed inside a Firefox D7 timing press (F3 below). An item-2 re-run is running now (`item2-rerun/`, Firefox M5, no timing clause). Item 1's re-runs will have timing clauses.
- Do not touch `item2-rerun/`.

**Authority.** The owner, in this session, was asked 「item 1 有四格是環境造成的 NE（D5w Firefox 是 W2 重演；D7、D9 是外部 CPU），沒有任何 FAIL。規格字面是「停手交接、v22 不可出貨」。要怎麼處置？」 and chose **「A 交 fable 當裁決 6 附錄（建議）」**. So: decide for the owner on this question, and put a short zh-TW plain-language section for the owner first. CLAUDE.md 「驗收判準的形式」 §1–§11 applies as before.

All paths are under `findings/evidence/link-batch-v22/shakedown/` unless written in full.

## Facts (checked by the main session)

**F1 — the reading.**
- The chain ended at 18:22 with `CHAIN DONE`; every step exited 0 (`chain.log`).
- The unchanged item-1 judge with `--expect-page 3b96cb16…` gives `VERDICT NOT PASS (6 criterion cell(s) not PASS)` (`item1/first-reading/judge-item1-first.txt`, commit `f56ccddc`):
  - `E0 chrome FAIL`, `E0 firefox FAIL`: expected by addendum 1 (spec §11.4.1);
  - `D5w firefox NOT_ESTABLISHED`;
  - `D7 chrome NOT_ESTABLISHED`;
  - `D7 firefox NOT_ESTABLISHED`;
  - `D9 firefox NOT_ESTABLISHED`;
  - every other criterion line PASS in both browsers: D1, D2p, D4, D5w Chrome, D8, D9 Chrome, D10, D11a, D11b, D11c, D12, D14. No FAIL anywhere.
- E0-v22 PASS: 379 reads over the six reports, 0 red, 0 blind (`item1/first-reading/e0-v22-first.txt`).
- D6 prints the stale 「未量」 reason, as addendum 1 item 8 expects.

**F2 — D5w Firefox: the v21 W2 shape, again.**
- `item1/report-firefox-d2p-…-d6-20261019T172740.json`, one Firefox session, 17:27:40–18:22:25.
- d2p, d8, d8red, d11a, d11b, d11c and d12 are all `done`, and their Firefox cells read PASS. d5w `v20` round 1 is `done`.
- From d5w `v21` round 1 on, every load is `state: stopped` and `open.settled.state: recoverable-error`, with the toast `WORKER_INIT_FAILED：abort@…/profiles/e2-editor-v22/probe.js:7:20337 / instantiateArrayBuffer@…:7:21105`. The start state then reads `not-observed: no selection reported within 10.0 s`.
- That loses d5w rounds 1 (v21) to 3, all of R-xlc (9) and all of R-table (3). The 10 s waits are why this step took 55 min, against Chrome's 12 min for the same arms.
- This is v21's W2 (`findings/evidence/link-batch-v21/shakedown/README.md:237`; witness `…/evidence/witness/firefox-rest-worker-init-failed/README.md`): after 44 good loads in one Firefox session, every init aborted at the same two frames. Finding 024's shape [inferred there].
  - v21's remedy was procedural: no tool edited, the arms re-run in **three fresh Firefox sessions** (A `d2p,d8,d8red,d11b`; B `d11a,d11c,d12`; C `d5w,xlc,table,d6`), and the failed report moved out of `item1/` as a witness.
  - Tally there: "runs lost to the harness and re-run +1".
- **The v22 chain script did not apply that remedy.** `chain-item2-item1.sh` (`0da3cc33`) runs Firefox's rest as one invocation, the same list as Chrome's. This is a fault in the session's procedure, not in a tool.

**F3 — D7, both browsers: foreign CPU only.** The judge's D7 lines (`judge-item1-first.txt`) give foreign-CPU NEs only, with no read outside the window and no FAIL: Chrome 2 lines, Firefox 15 lines.
- **Chrome** (`item1/report-chrome-d1-20261019T155807.json`): `t-home-A1-n1` r2 and `t-end-B2-n1` r3, a `chrome --type=renderer … --extension-process` at 80.0 % and 78.0 %, under `--crashpad-handler-pid=2745205`. That is the owner's desktop Chrome, the same process family as ruling 6's M6 NE.
- **Firefox** (`item1/report-firefox-d1-20261019T164633.json`), 16:46–17:19:
  - `make -j 4 … /home/jiajun/OSSII/study_OxOffice_AI/OxOffice/Makefile.gbuild` (`Library_merged`, `CppunitTest_ossii_extension_documentcontext`) at 96.8–99.3 %, plus its `cc1plus` at 99.0 %. Another project's build, not ours;
  - `zen` (`Isolated Web Co`) at 81.5–101.3 %, the owner's browser;
  - `bfs -S dfs … -name chain-item2-item1.sh` at 172.5 % (comm `2.1.303`), on `sec-end-n2` r3. [inferred: ruling 6's own search, from its command line and the time; ruling 6 ran 17:16–17:30.]
- `desk.log` shows 39–40 Chrome processes at every chain step's start, and the pre-run checks did not refuse. The judge's D7 clause (`judge_v21_shakedown_item1.py:257-259`) makes a foreign-CPU press NE, and a cell with fewer than N clean rounds NE (`:270-271`).

**F4 — D9 Firefox: foreign CPU only.**
- `item1/report-firefox-d9-d10-d14-20261019T171939.json`: `Ctrl+End flagged` r2 is NE from the desktop Chrome renderer at 78.4 % (pid 3212733, the same crashpad parent).
- Every other D9 Firefox read prints as in v21: flagged 1 move, ready 0 ms; unflagged 4 moves, ready 235–239 ms. D9 Chrome is PASS.

**F5 — the rules.**
- v22 §11.4: I1-rerun 「沒做或紅 → v22 不可出貨」. Addendum 1's reading of the verdict line (§11.4.1).
- v21 `:343`: NE = not done.
- The handoff's Next 4: 「Item 1: any non-E0 cell not PASS … → stop and hand off」.
- The precedents:
  - W2, a procedural re-run in fresh sessions with the failed report as witness;
  - v21 §12.4 (e) 3: foreign CPU only → one more run, once;
  - ruling 6: re-run only the voided cells, read per cell, with stop rules pinned first. Its grant covers item 2's three cells only (its item 8).
- **The item-1 judge refuses two reports for one (browser, arm)**: `judge_v21_shakedown_item1.py:993`, "two reports for one (browser, arm)" → FAIL. So a re-run's report cannot sit beside the one it replaces. v21 moved the replaced reports to `superseded/item1/` and to the witness directory.

**F6 — cost and desk now.**
- Step times in this chain:
  - Chrome d1: 29.4 min;
  - Firefox d1: 33.1 min;
  - Firefox d9-d10-d14: 8.0 min;
  - Chrome rest (one session, no W2): 11.8 min.
- 01:19 today: no Chrome, Firefox, zen or make process; one `claude` (this session); load 0.3. The owner: 「其他session都關掉了」.
- The item-2 Firefox re-run started at 01:19 (M6 done 3/3 with `foreignCpu.ok` true; M5 running, about 16 min).
- The tree is now `f56ccddc`. Since `0da3cc33`, the only tool commit is `1b393f8f` (item-2 tools only; ruling 6 item 15 found them outside item 1's import closure).

## The main session's leaning (claims to check)

- **P1. Re-run, do not take the default.** Every non-E0 non-PASS is NE from the harness (W2) or the desk; none is a product result, and E0-v22 PASS.
- **P2. Scope.** Each re-run is a fresh invocation, on a quiet desk (no desktop Chrome, no zen, no builds, no subagent searches). About 1.5 h.
  - Chrome `d1`, for D7;
  - Firefox `d1`, for D7;
  - Firefox `d9,d10,d14`, for D9. It cannot be `d9` alone: F5's one-report rule means the old report must leave `item1/`, and it carries d10 and d14;
  - Firefox's rest as W2's three fresh sessions A/B/C. Not C alone: the failed report carries d2p–d12, and it must leave `item1/` for C's d5w to be read.
- **P3. Moving and reading.** The replaced reports move to `item1/superseded/` (`git mv`, after this brief's witness commit `f56ccddc`). The judge then runs unchanged over `item1/`, which holds Chrome's two untouched reports, Chrome d1's re-run and Firefox's five re-run reports. The verdict line is read as addendum 1 item 4 says (exactly the two E0 cells), and E0-v22 is re-read over the same set. No composition of judge lines is needed, unlike ruling 6, because the directory again holds one report per (browser, arm).
- **P4. Stop rules.**
  - Any FAIL → I1-rerun red → v22 not shippable (stop, hand off).
  - NE again from foreign CPU on a desk the session checked as quiet → record the process, stop, hand off.
  - W2 again inside one of A/B/C → stop, hand off. That would be new: v21's split held.
  - Any other NE → stop, hand off.
- **P5. §34.4.** Runs lost to the harness and re-run: +1 (W2, as v21 counted it), plus the desk re-runs. No tool edited, so execution +0 and review +0. The chain script's missing split is a procedure fault, registered in the README. Should it be a line in the next chain script's checklist?
- **Alternatives:**
  - (a) re-run only Firefox C, plus D7/D9 as above, keeping the failed session's good d2p–d12 rounds. That needs the judge to read a split report, against F5;
  - (b) the default, I1-rerun not done → v22 not shippable. 0.2.26 stays nominal, and the item-2 re-run's result would not matter for shipping.

## Questions

- **Q1.** P1 vs (b): may item 1's four NE cells be re-run?
- **Q2.** The scope (P2) and the move-and-read (P3). Is whole-report replacement right, or is there a cheaper reading you would accept?
- **Q3.** The stop rules (P4), and the desk condition: must the session check the desk before each step and refuse a dirty one, or is the guard's NE enough?
- **Q4.** The §34.4 tally, and whether the missed W2 split or ruling 6's search inside a timing press needs anything beyond a README line.
- **Q5.** Anything this addendum gets wrong or leaves out, including the spec append's content and its timing.

## Answer format

As ruling 6. The main session commits your text verbatim as `review/ruling-fable-6-addendum-1.md`.
