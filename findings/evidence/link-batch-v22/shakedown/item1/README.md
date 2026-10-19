# Item 1 (Ctrl/Cmd+Home/End) on v22: I1-rerun

The criteria:
- SPEC-M3-link-batch-v22 §11.4 (I1-rerun: item 1's D1–D14 on the final page bytes, both browsers, N=3);
- §11.4.1 (fable ruling 5 addendum 1: E0 withdrawn on v22, E0-v22 read instead, the verdict line's reading);
- §11.4.2 (fable ruling 6 addendum 1: the first reading's four NOT_ESTABLISHED cells, the re-run, the superseded move, the desk gate).

## Verdict: I1-rerun PASS in both browsers

The unchanged judge over this directory (`second-reading/judge-item1-second.txt`, tree `5624b770`) prints:

```
VERDICT NOT PASS (2 criterion cell(s) not PASS)
```

The two cells are exactly `E0 chrome FAIL` and `E0 firefox FAIL`. Every other criterion line is PASS in both browsers: D1, D2p, D4, D5w, D7, D8, D9, D10, D11a, D11b, D11c, D12 and D14.

**Why NOT PASS is the expected, correct line on v22.** `judge_e0` requires item 2's entry to be hidden at every arm's start. That is v21 §12.3 (e)'s reading. v22 ships the entry (§11.1), so E0 is red by construction on page `3b96cb16…`. §11.4.1 withdrew it and reads E0-v22 instead. The judge was not edited.

**E0-v22: PASS** (`second-reading/e0-v22-second.txt`):
- 396 reads over the same eight reports, 0 red, 0 blind.
- Every v22-profile read shows the entry with exactly one visible opener, the toolbar button. Every `v20` read shows it hidden.

**D6** prints `D6 未量 (not runnable: item 2 not shipped (spec §12.3 (e)))`. That reason is stale on v22, where item 2 does ship. The true reason is that the arm has no implementation (addendum 1 item 8). The default stands: 「未量，不做任何排序宣稱」. The release text makes no ordering claim about a large paste followed by Ctrl+End and typing. Implementing D6 is a registered work item.

**The D4 deviation lines** (`DEVIATION-D4-op … counted, for the main session`, 18 per browser, 36 in all) are v21's recorded deviation (smoke ruling S1): on an open range the place-caret request goes out as `click`. They are not new. D4 is PASS.

**No companion cell needed the composition rule** of §11.4.2. Every re-run cell read PASS on its own.

## The first reading, and why four reports were replaced

The chain of 2026-10-19 (`../chain-item2-item1.sh`, 15:58–18:22) gave `VERDICT NOT PASS (6 criterion cell(s) not PASS)` (`first-reading/judge-item1-first.txt`, witness `f56ccddc`):
- the two E0 FAILs;
- four NOT_ESTABLISHED cells;
- no FAIL.

E0-v22 was PASS there too: 379 reads (`first-reading/e0-v22-first.txt`).

| cell | cause, as the report records it |
|---|---|
| D5w Firefox | **The v21 W2 shape.** One Firefox session ran all 11 arms. Loads 1–43 were good. From load 44 on (d5w `v21` r1), every engine init aborted in `instantiateArrayBuffer` (`WORKER_INIT_FAILED`), so d5w r1–r3, R-xlc and R-table were lost. v21 had already prescribed three fresh Firefox sessions for these arms (`link-batch-v21/shakedown/evidence/witness/firefox-rest-worker-init-failed/`). The chain script did not carry that split, which is a procedure fault. |
| D7 Chrome | `t-home-A1-n1` r2 and `t-end-B2-n1` r3 were over the foreign-CPU limit. The process was the owner's desktop Chrome `--extension-process` renderer, at 80.0 % and 78.0 %. v21's Chrome D7 was voided by the same process family (74.5 %, 75.6 %) and re-run as d1 (`link-batch-v21/shakedown/README.md:221-222`). |
| D7 Firefox | Eight presses were over the limit. The processes were: <br>• an OxOffice `make -j 4` and its `cc1plus` at 96.8–99.3 %; <br>• the owner's zen at 81.5–101.3 %; <br>• ruling 6's own repo-wide file search, at 172.5 % on `sec-end-n2` r3. |
| D9 Firefox | `Ctrl+End flagged` r2 was over the limit, from the desktop Chrome renderer at 78.4 %. |

The four reports, with their docs and step logs, are in `superseded/` (its README has one line per report). They were moved by `git mv` before the re-run (`ac479d5d`), because the judge refuses two reports for one (browser, arm).

## The re-run (2026-10-20 01:42–03:07)

- `../chain-item1-rerun.sh` (`5624b770`), detached.
- Steps, each `--rounds 3`, each exit 0 (`../chain.log`):
  - Chrome `d1`, 28.9 min;
  - Firefox `d1`, 33.0 min;
  - Firefox `d9,d10,d14`, 8.0 min;
  - Firefox's rest as W2's three fresh sessions: A `d2p,d8,d8red,d11b` (6.8 min), B `d11a,d11c,d12` (1.8 min), C `d5w,xlc,table,d6` (5.4 min).
- **The desk gate** (`../desk_gate.py`, self-check `../desk-gate-self-check.txt`) read clean before all six steps: no Chrome process, no zen/make/cc1plus/ninja, 1-minute load 0.12–1.13, foreign-CPU sample ok (`../desk.log`).
- In the reports: no round is not done, and no foreign-CPU sample is over the limit.
- R-xlc and R-table are recorded in both browsers, all `done`.
- W2 did not recur in A, B or C.
- The session ran nothing CPU-heavy while the steps ran: it waited on `chain.log` only.

The reports judged: Chrome `d9,d10,d14` and Chrome's rest from the first chain (untouched), plus the six re-run reports. The page is `3b96cb16…` and the wasm `f7a40bcc…` throughout (the judge refuses others).

## §34.4 and the desk

- **Tools:** modified because of execution 0, because of review 0. The re-run chain and its desk gate are additions (0/0).
- **Runs lost to the harness and re-run:** +1 (W2, the second time).
- **Runs lost to the desk and re-run:** +3 (Chrome d1, Firefox d1, Firefox d9-d10-d14). One Firefox D7 press of these was the judge's own search.
- **Running total since 10-14b:** 32 / 18, unchanged by this item.
- **A standing desk fact.** The owner's desktop Chrome `--extension-process` renderer has now voided timing cells four times:
  - v21 Chrome D7;
  - v22 Firefox M6;
  - v22 Chrome D7;
  - v22 Firefox D9.

  "Desktop Chrome closed" is a standing condition of every timing step, enforced by the desk gate.
- **Registered procedure items** (ruling 6 addendum 1 item 12):
  - the next chain script is written from the handoff's checklist: Firefox's rest in three sessions, `--rounds 3`, the desk gate before each step;
  - no session or subagent does CPU-heavy work while a timing step runs.
