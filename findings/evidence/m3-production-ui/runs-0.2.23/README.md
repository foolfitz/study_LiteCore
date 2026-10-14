# The 0.2.23 count chain (host 0.2.23, engine v20): the batched count of 0.2.13–0.2.23

Prepared 2026-10-15 (fable, count-chain preparation task), **not run**. The owner has not agreed a window (P5); the main session asks in the morning and starts it. Everything here is a script that calls existing runners and judges, plus text; no runner, judge, test or Makefile was edited.

Files:

| file | what |
|---|---|
| `chain-0.2.23.sh` | the chain: preflight P0–P6, then the 0.2.13 shape plus the new-document runner, the merge count and C2 × 3; `--preflight-only` runs P1–P6 and prints every reading |
| `read-0.2.23.sh [LOGDIR]` | after `DONE`: the red cases, the merge judge (`--profile e2-editor-v20`), the C2 judges per run, the product-path reader; prints and saves, applies no reading table |
| `c2-extension.sh` | C2 r4–r6, only if r1–r3 read "1 PASS + 2 attributable FAILs" (ruling J-b.2 row 3); identity check first; run by hand |
| `preflight-only-2026-10-15.txt` (+ `-p6-unittest.txt`, `-p6-static.txt`) | the one `--preflight-only` run made while preparing (below) |
| `../../release-0.2.23/product-path/{judge.py,PREDICTION.md}` | the product-path net's per-release reader copy and predictions, written before any run |

## What the chain runs, in order, with the estimated durations

From the committed chain logs (`runs-0.2.12/chain-2026-10-11b.out`, `runs-0.2.13/chain-2026-10-12.out`, the v19 X7 report timestamps, `136/guard-r2/c2/chain.txt`, `m3-autosave/shakedown/`, `new-document/runs/`). **Total about 8.5 h (7.5–9.5 h).**

| # | step | command (relative to the repo root; `T=wasm_sdk_probe/tools`) | writes | est. |
|---|---|---|---|---|
| 0 | preflight P0–P6 (below); a refusal exits 3 with no `START` | — | stdout only | 2 min |
| 1 | `IDENTITY-START`, `START`, desk line | — | `build/m3-count-<stamp>/chain.txt`, `started` | — |
| 2 | shakedowns, six M3 runners, **the one STOP rule** (`STOP: shakedown X not clean; no counted run started`, exit 1) | `check_m3_{page_honesty,locks,versions,assets,host_entry,same_second}.py --label shakedown --repeats 1` | `build/m3-count-*/shakedown-*.log`; the runners' `shakedown/` dirs | 66 min |
| 3 | shakedown autosave (the 0.2.13 gate: three arms) | `check_m3_autosave.py --label shakedown --arms as2-key,as4a,as5 --repeats 1` | as above | 10 min |
| 4 | shakedown new-document (added; see "new-document" below) | `check_m3_new_document.py --label shakedown` | `new-document/shakedown/` | 3–14 min |
| 5 | counted production UI, 0.2.13's split: Kdel,Kbs,Rbs,Rdel ×3; Bctl,S,P ×1; B3x ×2 (the spec's §13 list; the runner's default; **no arm was added since 0.2.13** — `git log` of the runner since `3a6603de` is pin moves only) | `check_m3_production_ui.py --counted --rounds N --arms … --out runs-0.2.23/counted-*.json` | `runs-0.2.23/counted-{KR-x3,ctl-S-P,B3x-x2}.json` | 40 min (19 in 0.2.12 + the R/B3x waits, below) |
| 6 | the six counted | `check_m3_<r>.py --label counted` | the runners' `runs/` dirs; `build/m3-count-*/counted-*.log` | 140 min |
| 7 | counted autosave (AS-*'s first counted run) | `check_m3_autosave.py --label counted` | `m3-autosave/runs/` | ~100 min |
| 8 | counted new-document | `check_m3_new_document.py --label counted` | `new-document/runs/` | 5 min |
| 9 | the product-path net: v8 (candidate, repointed) and **v20** (plain) interleaved, 3 rounds × Chrome/Firefox | `run_e2_c_product_path.py --browser B [--candidate-profile e2-editor-v8] --out release-0.2.23/product-path/e2-editor-{v8,v20}-B-rN.json` | `release-0.2.23/product-path/*.json`, `chain.log` | 78 min |
| 10 | the merge count, v19's X7 modes (`findings/evidence/v19/chain.sh`): per browser `counted`, `counted --control`, `--pair`, `m2-1b`, `m2-4`, `m2-1-red` on v8 | `run_merge_wasm_shakedown.py --mode … --candidate-profile e2-editor-v20 --out release-0.2.23/merge-m2/<name>-B.json` (red: `--candidate-profile e2-editor-v8`) | `release-0.2.23/merge-m2/` (judge_counted_m2.py's `FILES` names) | 50 min |
| 11 | C2 three times, `136/guard-r2/c2/chain-c2.sh`'s shape per run (both browsers; ratio 2 wide gap 80/200; ratio 1.5 recorded; ratio 1 P2 cells) | `probe_typing_latency_view.py` / `probe_typing_latency.py` | `release-0.2.23/c2/r1`, `r2`, `r3` (each with `chain.txt`, `desk-at-start.txt`) | 13 min |
| 12 | `IDENTITY-END`, desk line, Firefox-profile cleanup (as 0.2.13), `DONE` | — | — | — |

The desk line (`DESK <label> load … chrome … chrome-browsers … firefox … swap-used-MB … kwallet-locked [..] ours N host-login [rc= bytes= grep=]`) is written at `START`, before every step and at `END`; **recorded, never gated** (J-a.1). Once `START` is written nothing stops the chain but step 2–4's STOP rule; counted steps write their exit code and go on (J-a.1 "Once START is written").

### Preflight (ruling J-a.1 P1–P5 exactly; P0 and P6 added here)

| # | condition | how it is read | refusal |
|---|---|---|---|
| P0 (chain-local, not J-a) | `release-0.2.23/merge-m2/*.json` and `c2/r1–r3/*.json` absent | `ls` | the merge runner makes `<report>.docs/` with `exist_ok=False` and dies on a second run; a re-run is a new file (J-a.1), so an earlier run's evidence is moved aside first |
| P1 | KWallet unlocked | `busctl --user get-property … kdewallet … Locked` = `b false` | the owner unlocks on the VNC desktop |
| P2 | a default-flag headless Chrome reaches the host | `timeout 30 google-chrome --headless=new --user-data-dir=$(mktemp -d) --dump-dom https://litecore.ddev.site:8443/login`: rc 0 and `grep -c Nextcloud` > 0 | printed rc / bytes / grep |
| P3 | nothing of ours is running | `pgrep -af 'probe_\|judge_\|check_m3\|run_e2_c\|run_merge\|run_v20'` (this script's own line excluded) prints 0 lines | the lines are printed |
| P4 | identity | `dist/e2-editor-app.js`, `web/e2-editor-app.js` and the archived package's `files/e2-editor-app.js.gz` **decoded** (`build/archive/host-0.2.23-engine-c3c22d9294de068a/`) hash the same `ccb67a52…`; `git -C ~/Projects/Nextcloud_Apps/litecore status --porcelain` empty. The installed host's own `engine/files/e2-editor-app.js.gz` is decoded and printed too (recorded, not gated) | all four values printed |
| P5 | the owner's agreement, and an empty lock table | `--owner-window "<window>, agreed by the owner at <time>"` (or `OWNER_WINDOW=`) must be given — it is echoed into the log; `ddev mysql -e "SELECT COUNT(*) FROM oc_files_lock;"` in the ddev root (the runners' `Instance.root`, read-only; they themselves `DELETE FROM oc_files_lock`, `check_m3_locks.py:278`) must print 0 | either missing refuses |
| P6 (not J-a; `link-batch/binding-v20/README.md` "these two test files are in no Makefile target") | `python3 -m unittest tests.test_merge_wasm_clauses tests.test_judge_counted_m2` and `make test-e2-c-static`, both in `wasm_sdk_probe/`, both exit 0 | outputs kept as `build/m3-count-*/preflight-p6-*.txt` |

`--preflight-only` runs all of P0–P6, prints every reading, writes nothing (the P6 outputs go to a temp dir it names) and exits with the number of refusals.

## Start command (the main session, after the owner agrees the window)

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
# the window is the P5 argument; it is echoed into chain.txt
nohup bash findings/evidence/m3-production-ui/runs-0.2.23/chain-0.2.23.sh \
     --owner-window "2026-10-15 23:00 – 2026-10-16 09:00 Asia/Taipei, agreed by the owner at HH:MM (the owner does not open litecore.ddev.site)" \
     > /dev/null 2>&1 &
# the log directory is named at run time: wasm_sdk_probe/build/m3-count-<UTC stamp>/chain.txt
```

Preflight only: `bash findings/evidence/m3-production-ui/runs-0.2.23/chain-0.2.23.sh --preflight-only`.

After `DONE`: `bash findings/evidence/m3-production-ui/runs-0.2.23/read-0.2.23.sh` (optionally the log directory). Then by hand: J-b.2's reading table on the three C2 verdict lines; the product-path reader made red once on scratch copies before its `SUMMARY` line is read (§34.7); the descriptive v20-vs-0.2.12-v19 comparison (PREDICTION.md); RESULT in the shape of `../RESULT-0.2.12.md`. The reading table for every chain outcome is **ruling J-a.2** (`handoff/RULING-2026-10-15-pre-binding.md`).

A re-run (no `DONE`, or `IDENTITY-END` ≠ `IDENTITY-START`, or a STOP) is a **new file**: the old `build/m3-count-*` directory stays; move `release-0.2.23/merge-m2/` and `release-0.2.23/c2/r1–r3` aside (P0 refuses otherwise); the production-UI and product-path reports are overwritten in place as 0.2.13's shape does, so copy them aside too if the partial run is wanted as evidence.

## Every pin and binding the chain relies on, and where it was set

| what | value | set in |
|---|---|---|
| page (dist = web = packaged) | `ccb67a52a3fe4b73…` | the cutover source already pointed at v20; host 0.2.23 `2ccf1a9`, shell v72 `19c19543` |
| host | `2ccf1a9`, `0.2.23`, buildId `c3c22d9294de068a`; archive `build/archive/host-0.2.23-engine-c3c22d9294de068a/` | handoff 10-14b Addendum |
| six M3 runners' pins (`PAGE_SHA256`, `BUILD_ID`, `HOST_COMMIT`, `HOST_VERSION`, `SESSION_SHA256 f47c80ec…`, `SHELL_BUNDLE_SHA256 4dc10507…`) | 0.2.23 / v72 | part P4 (page pins, eight commits `773aa6de`…), `4421df62` (the other 13 lines; SPEC-M3-link-batch §17.1) |
| production UI / autosave pins | as above | `d5075093`, `90fed007` (page), `4421df62` (rest) |
| new-document bindings (`HOST_COMMIT 2ccf1a9`, `HOST_VERSION 0.2.23`, `MANIFEST_SHA256 e5cdb8e2…`, `ENGINE_BUILD_ID c3c22d92…`, `PAGE_SHA256 ccb67a52…`) | 0.2.23 | part P3 `004fcdd3` |
| merge runner `BINDING` (nine `BOUND_KEYS`: wasm `313b08d5…`, worker `478d0da1…`, session `f47c80ec…`, shell `e7c4eefe…`, html `b1185aaa…`, page/pageSource `ccb67a52…`, eshape `c3f9bbed…`, native `2940a841…`) | v20 | `22e8c900` (SPEC-M3-link-batch §17.2; runner `365ceef6…`, **frozen** under §34.1 until the verdict is read) |
| merge judge `--profile` | `e2-editor-v20` is passed by `read-0.2.23.sh` (the default is `e2-editor-v19`; without it the identity clause reads NOT DONE, fail-closed) | part P1 `c8d53f39` (the judge learned C); V19Witness `00903e29` |
| product-path reader copy (`--candidate v20`, `--candidate-page ccb67a52…`, `V8_REPOINTED 49d1fd5f…`) | `release-0.2.23/product-path/judge.py` | this preparation; the v8 repoint recomputed with the runner's own `repointed_page()` (0.2.13's `fac708d0…` and 0.2.12's `0660beaf…` reproduced with the same call) |
| product-path runner | `9d1f44c6…` (0.2.12's `bd6fc0ca…` + one mutation anchor, `8565d973`) | recorded in `product-path/chain.log` |
| C2 judges' `PAGE` | `ccb67a52…` | part P4 `af0ddacc` (judge_c2), `034d9a8c` (judge_p2) |
| C2 judges' `RUNNER` | `probe_typing_latency_view.py 1412e4c863de6fcb`, `probe_typing_latency.py dbad93c0dcf27fbf` | unchanged; the tree's probes hash exactly these (checked 2026-10-15; `c2-extension.sh` re-checks) |
| C2 reading | three runs r1–r3; table in ruling **J-b.2**; one extension r4–r6 by `c2-extension.sh` only on row 3 | `RULING-2026-10-15-pre-binding.md` |
| Firefox profile scratch | `wasm_sdk_probe/build/scratch-m3-production-ui/ff-*` removed at the end (195 there on 2026-10-15) | 0.2.13's chain |

## New-document: in the count, and why

`check_m3_new_document.py --label counted` **is in the chain** (step 8), with a `--label shakedown` first (step 4, under the STOP rule like every other runner the chain counts). Basis: `specs/SPEC-M3-new-document.md` §4 「計數語意」 — N1–N9 are decided by one `--counted` run (two browsers × two arms), and 0.2.19 was an uncounted candidate because "the five-hour count chain is batched into the next engine-changing batch", which is this one; §7.5 「計數語意」 — from 0.2.20 on the count binds the **candidate engine** (`ENGINE_BUILD_ID`, `PAGE_SHA256`), both `None` until the binding step writes them, so that "the count refuses rather than inheriting 0.2.19's engine clause". Part P3 (`004fcdd3`) wrote exactly those five bindings for 0.2.23 and the report's `--red-cases` give 39 RED / 0 MISS, i.e. the runner was bound **for this count** and would otherwise be a binding with no run. The rule set it runs on is DISPOSITION Q3's (`findings/evidence/new-document/review/DISPOSITION.md`); 0.2.19's acceptance-only clauses stay off the count by construction (`DELTA_HOST_VERSION = "0.2.19"`). Its report goes to `findings/evidence/new-document/runs/`; the reader runs its `--red-cases` on it. Not strictly in the §9.4 list of "the six M3 runners, production UI, autosave, the product-path net", so it is listed here as the one addition to that list, with this reason.

## READ BEFORE STARTING: the production-UI arms Rbs, Rdel and B3x expect a refusal that v20 no longer makes

Found while preparing; not repaired (a runner edit is outside this task; it is also the owner's call how to count it). `wasm_sdk_probe/tools/check_m3_production_ui.py` scores:

- the R arms (A1-2′ R, spec §13.3) as **refusal + reopen**: `score_run` `:639–640` — `if run.get("genOpened") != "1" or run.get("genAfter") != "2": bad.append("… no refusal-and-reopen happened")`; `run_refusal` `:431–456` waits for a generation change (`wait_reopened` `:398–405`, 60 s);
- B3x (A1-5, spec §9.3) as **three refusals reaching the Worker-generation ceiling**: `score_three_refusals` `:771–772` — `if generations != [("1","2"),("2","3"),("3","3")]`, then `restart-required`, the `saved` notice, the reload (`:773–799`); `run_three_refusals` `:458–500` waits 60 s per press for the reopen.

On v20 the engine carries **C** (SPEC-M3-link-batch §4.4, §10.5; `boundary_noop_declared` True for `dist/profiles/e2-editor-v20/probe.wasm`): Backspace at the document start and Delete at its end are `verified-boundary-noop`, no refusal, no reopen, generation stays 1 — the owner's 0.2.20 hand test saw exactly this at the start (finding 141). On this document v19's only refusals were its two ends (spec §13.1); on v20 there is **none left**, so A1-2′ R and A1-5 have **no inducer** on this host. By construction, the counted production-UI run will read **Rbs 0/3, Rdel 0/3 (both browsers) and B3x 0/2** red, and the chain will spend about 20 extra minutes in those arms' 60-s waits (the estimate above includes it). The Kdel, Kbs, Bctl, S and P arms are untouched by C.

SPEC-M3-link-batch **§10.7 (S-9)** foresaw this class: "before any count, list every arm whose expectation names `nothing-selected`, a refusal count or a generation list, and its new expectation under C: 0 refusals, generations `['1']`, document and caret unchanged, the typed marker where the caret was … v20's first shakedown of those arms is the §34.4 witness for changing their judges, counted as 'repaired because of execution'". Its list was drawn from the held-into-refusal probe (`start-press`, `start-hold`, …, done in `269cbc6d`); the production-UI runner's three arms were not on it.

What the chain as written does: runs them as the spec's §13 list says, records everything (`genOpened`/`genAfter`, the server's paragraph sequence, the marker count, the timeline), and the reading follows ruling J-a.2's row "DONE; a counted step red": attribute first against the uncounted list — this is **v20 itself (C)**; no re-run on the spot; the counted report is the committed witness §34.1(b) / §10.7 asks for, so the runner's expectation for these arms is changed afterwards with that report as its red case and the report re-judged, no re-run. (For A1-5 the ceiling, the `saved` notice and the reload have no inducer at all on v20; whether that criterion is re-expected or withdrawn per AGENTS.md §4 is the owner's decision, not the chain's.) The main session may instead prefer to settle this before launch; the options are in the task report, not here.

## The one `--preflight-only` run made while preparing (2026-10-15, `preflight-only-2026-10-15.txt`)

```
P0 output directories empty: ok
P1 kdewallet Locked = [b false]: ok
P2 headless Chrome --dump-dom https://litecore.ddev.site:8443/login: rc=0 bytes=738274 grep=167: ok
P3 pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20': 0 lines: ok
P4 pages: dist ccb67a52a3fe4b73 web ccb67a52a3fe4b73 archive ccb67a52a3fe4b73 (installed host serves ccb67a52a3fe4b73, recorded);
   want ccb67a52a3fe4b73; host HEAD 2ccf1a9 version 0.2.23 dirty[]  -> P4 identity: ok
REFUSED P5 owner agreement not given                       (expected: no window has been agreed yet)
REFUSED P5 oc_files_lock rows: [10] (want 0)               (see below)
P6 unittest tests.test_merge_wasm_clauses tests.test_judge_counted_m2: exit 0 :: Ran 134 tests in 17.502s OK
P6 make test-e2-c-static: exit 0 :: Ran 108 tests in 0.805s OK
PREFLIGHT-ONLY done: 2 refusal(s)                           (38 s wall clock)
```

The 10 lock rows (a second read-only `SELECT user_id, type, owner, file_id, creation, ttl, scope`): all `admin`, type 2, ttl 300 s, created 00:47–02:32 local on 2026-10-15 — the browser probes of the concurrent `host-0.2.23-hold` measurement (its untracked run directories were in the tree at the time), minutes before this preflight. They lapse by their 300-s ttl; at a real start, with nothing else of ours running, the read should print 0, and if it does not, the refusal is correct: the runners clear the whole table and would clobber whoever holds those locks. The desk at the time: load 1.3–1.9, 35 chrome processes (31 browser processes: the owner's desktop Chrome), 1 firefox, swap used 5.2 GB of 64 GB.

## §34.4 for this preparation

Repaired because of execution **0**, because of review **0**. No tool, test, spec or finding was edited; the only edit outside this directory and `release-0.2.23/product-path/` is the release-text draft's §5 sentence (v19 → v20; new-document added), with a revision-log row.
