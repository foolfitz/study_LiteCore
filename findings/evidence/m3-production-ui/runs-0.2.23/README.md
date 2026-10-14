# The 0.2.23 count chain (host 0.2.23, engine v20): the batched count of 0.2.13–0.2.23

Prepared 2026-10-15 (fable, count-chain preparation task; reviewed and amended the same night by the main session), **not run**. The owner has not agreed a window (P5); the main session asks in the morning and starts it. Everything here is a script that calls existing runners and judges, plus text. One runner was edited for this count (`check_m3_production_ui.py`, the R arms re-expected under C, with its §34.4 witness — below); no judge, test or Makefile.

Files:

| file | what |
|---|---|
| `chain-0.2.23.sh` | the chain: preflight P0–P6, then the 0.2.13 shape minus B3x, plus the new-document runner, the merge count and C2 × 3; `--preflight-only` runs P0–P6 and prints every reading |
| `read-0.2.23.sh [LOGDIR]` | after `DONE`: the red cases, the merge judge (`--profile e2-editor-v20`), the C2 judges per run, the product-path reader; prints and saves, applies no reading table |
| `c2-extension.sh` | C2 r4–r6, only if r1–r3 read "1 PASS + 2 attributable FAILs" (ruling J-b.2 row 3); identity check first; run by hand |
| `preflight-only-2026-10-15.txt`, `-15b.txt`, `-15c.txt` (+ `-p6-unittest.txt`, `-p6-static.txt` for the first and third) | the three `--preflight-only` runs made while preparing (below; the second refused P3 on a false positive, since excluded) |
| `../witness-c-0.2.23/rejudge-under-c.txt` | the production-UI runner's before/after on the witness report (R arms re-expected under C) |
| `../../release-0.2.23/product-path/{judge.py,PREDICTION.md}` | the product-path net's per-release reader copy and predictions, written before any run |

## What the chain runs, in order, with the estimated durations

From the committed chain logs (`runs-0.2.12/chain-2026-10-11b.out`, `runs-0.2.13/chain-2026-10-12.out`, the v19 X7 report timestamps, `136/guard-r2/c2/chain.txt`, `m3-autosave/shakedown/`, `new-document/runs/`, `witness-c-0.2.23/`). **Total about 8.2 h (7.5–9.5 h); started at 23:00 it ends around 07:15.**

| # | step | command (relative to the repo root; `T=wasm_sdk_probe/tools`) | writes | est. |
|---|---|---|---|---|
| 0 | preflight P0–P6 (below); a refusal exits 3 with no `START` | — | stdout only | 2 min |
| 1 | `IDENTITY-START`, `START`, desk line | — | `build/m3-count-<stamp>/chain.txt`, `started` | — |
| 2 | shakedowns, six M3 runners, **the one STOP rule** (`STOP: shakedown X not clean; no counted run started`, exit 1) | `check_m3_{page_honesty,locks,versions,assets,host_entry,same_second}.py --label shakedown --repeats 1` | `build/m3-count-*/shakedown-*.log`; the runners' `shakedown/` dirs | 66 min |
| 3 | shakedown autosave (the 0.2.13 gate: three arms) | `check_m3_autosave.py --label shakedown --arms as2-key,as4a,as5 --repeats 1` | as above | 10 min |
| 4 | shakedown new-document (see "new-document" below) | `check_m3_new_document.py --label shakedown` | `new-document/shakedown/` | 3–14 min |
| 5 | counted production UI, 0.2.13's split **without B3x**: Kdel,Kbs,Rbs,Rdel ×3; Bctl,S,P ×1 (the spec's §13 arms; no arm was added since 0.2.13). B3x is withdrawn from this count (SPEC-M3-link-batch §17.3, below); Rbs/Rdel are scored under C, keyed on the served wasm's bytes | `check_m3_production_ui.py --counted --rounds N --arms … --out runs-0.2.23/counted-*.json` | `runs-0.2.23/counted-{KR-x3,ctl-S-P}.json` | 27 min (15 in 0.2.12 + 12 × the R arms' 60-s reopen wait, which under C ends by timeout) |
| 6 | the six counted | `check_m3_<r>.py --label counted` | the runners' `runs/` dirs; `build/m3-count-*/counted-*.log` | 140 min |
| 7 | counted autosave (AS-*'s first counted run) | `check_m3_autosave.py --label counted` | `m3-autosave/runs/` | ~100 min |
| 8 | counted new-document | `check_m3_new_document.py --label counted` | `new-document/runs/` | 5 min |
| 9 | the product-path net: v8 (candidate, repointed) and **v20** (plain) interleaved, 3 rounds × Chrome/Firefox | `run_e2_c_product_path.py --browser B [--candidate-profile e2-editor-v8] --out release-0.2.23/product-path/e2-editor-{v8,v20}-B-rN.json` | `release-0.2.23/product-path/*.json`, `chain.log` | 78 min |
| 10 | the merge count, v19's X7 modes (`findings/evidence/v19/chain.sh`): per browser `counted`, `counted --control`, `--pair`, `m2-1b`, `m2-4`, `m2-1-red` on v8 | `run_merge_wasm_shakedown.py --mode … --candidate-profile e2-editor-v20 --out release-0.2.23/merge-m2/<name>-B.json` (red: `--candidate-profile e2-editor-v8`) | `release-0.2.23/merge-m2/` (judge_counted_m2.py's `FILES` names) | 50 min |
| 11 | C2 three times, `136/guard-r2/c2/chain-c2.sh`'s shape per run (both browsers; ratio 2 wide gap 80/200; ratio 1.5 recorded; ratio 1 P2 cells) | `probe_typing_latency_view.py` / `probe_typing_latency.py` | `release-0.2.23/c2/r1`, `r2`, `r3` (each with `chain.txt`, `desk-at-start.txt`) | 13 min |
| 12 | `IDENTITY-END`, desk line, Firefox-profile cleanup (as 0.2.13), `DONE` | — | — | — |

The desk line (`DESK <label> load … chrome … chrome-browsers … firefox … swap-used-MB … kwallet-locked [..] ours N host-login [rc= bytes= grep=]`) is written at `START`, before every step and at `END`; **recorded, never gated** (J-a.1). Once `START` is written nothing stops the chain but steps 2–4's STOP rule; counted steps write their exit code and go on (J-a.1 "Once START is written").

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

A detached session (`setsid nohup … &`: the precedent for long overnight runs here, handoff 10-08b "background jobs started by a session die with it"):

```bash
cd /home/jiajun/LibreOffice/study_LiteCore
# the window is the P5 argument; it is echoed into chain.txt
setsid nohup bash findings/evidence/m3-production-ui/runs-0.2.23/chain-0.2.23.sh \
     --owner-window "2026-10-15 23:00 – 2026-10-16 09:00 Asia/Taipei, agreed by the owner at HH:MM (the owner does not open litecore.ddev.site)" \
     > /dev/null 2>&1 &
# the log directory is named at run time: wasm_sdk_probe/build/m3-count-<UTC stamp>/chain.txt
```

Preflight only: `bash findings/evidence/m3-production-ui/runs-0.2.23/chain-0.2.23.sh --preflight-only`.

After `DONE`: `bash findings/evidence/m3-production-ui/runs-0.2.23/read-0.2.23.sh` (optionally the log directory). Then by hand: J-b.2's reading table on the three C2 verdict lines; the product-path reader made red once on scratch copies before its `SUMMARY` line is read (§34.7); the descriptive v20-vs-0.2.12-v19 comparison (PREDICTION.md); RESULT in the shape of `../RESULT-0.2.12.md`. The reading table for every chain outcome is **ruling J-a.2** (`handoff/RULING-2026-10-15-pre-binding.md`).

A re-run (no `DONE`, or `IDENTITY-END` ≠ `IDENTITY-START`, or a STOP) is a **new file**: the old `build/m3-count-*` directory stays; move `release-0.2.23/merge-m2/` and `release-0.2.23/c2/r1–r3` aside (P0 refuses otherwise); the production-UI and product-path reports are overwritten in place as 0.2.13's shape does, so copy them aside too if the partial run is wanted as evidence.

### The owner's file (decide before launch)

`check_m3_production_ui.py` uploads over **`m3-109 測試.odt` (fileId 7340, admin's root)** at every arm — the same file the owner opened in the 10-14 hand test. Tonight's witness overwrote it (now 567,408 B, mtime 2026-10-15 03:01:34 local, read from `oc_filecache`); the pre-witness version is in Nextcloud versions as `files_versions/m3-109 測試.odt.v1791975573` (fileId 18622, 2026-10-14 18:59:33, **567,309 B** — the size 10-14n recorded), among 22 versions (2026-10-06 … 2026-10-15). The count will overwrite the file many times (each arm: upload, edit, save). The owner decides before launch whether to keep a copy of that version (a read-only check: `SELECT fileid, path, size, FROM_UNIXTIME(mtime) FROM oc_filecache WHERE path = 'files_versions/m3-109 測試.odt.v1791975573'`).

## Every pin and binding the chain relies on, and where it was set

| what | value | set in |
|---|---|---|
| page (dist = web = packaged) | `ccb67a52a3fe4b73…` | the cutover source already pointed at v20; host 0.2.23 `2ccf1a9`, shell v72 `19c19543` |
| host | `2ccf1a9`, `0.2.23`, buildId `c3c22d9294de068a`; archive `build/archive/host-0.2.23-engine-c3c22d9294de068a/` | handoff 10-14b Addendum |
| six M3 runners' pins (`PAGE_SHA256`, `BUILD_ID`, `HOST_COMMIT`, `HOST_VERSION`, `SESSION_SHA256 f47c80ec…`, `SHELL_BUNDLE_SHA256 4dc10507…`) | 0.2.23 / v72 | part P4 (page pins, eight commits `773aa6de`…), `4421df62` (the other 13 lines; SPEC-M3-link-batch §17.1) |
| production UI / autosave pins | as above | `d5075093`, `90fed007` (page), `4421df62` (rest) |
| **production UI runner, the R arms' expectation under C** | keyed at run time on the bytes of the wasm the host serves (`engine/files/profiles/<p>/probe.wasm.gz`, decoded, sha256 = the manifest's): `static.boundaryNoop.declared` True → Rbs/Rdel expect the no-op; False → the refusal as before; unreadable → the run refuses | this preparation (commit named in the §34.4 line below; SPEC-M3-link-batch §17.3; witness `../witness-c-0.2.23/`) |
| new-document bindings (`HOST_COMMIT 2ccf1a9`, `HOST_VERSION 0.2.23`, `MANIFEST_SHA256 e5cdb8e2…`, `ENGINE_BUILD_ID c3c22d92…`, `PAGE_SHA256 ccb67a52…`) | 0.2.23 | part P3 `004fcdd3` |
| merge runner `BINDING` (nine `BOUND_KEYS`: wasm `313b08d5…`, worker `478d0da1…`, session `f47c80ec…`, shell `e7c4eefe…`, html `b1185aaa…`, page/pageSource `ccb67a52…`, eshape `c3f9bbed…`, native `2940a841…`) | v20 | `22e8c900` (SPEC-M3-link-batch §17.2; runner `365ceef6…`, **frozen** under §34.1 until the verdict is read) |
| merge judge `--profile` | `e2-editor-v20` is passed by `read-0.2.23.sh` (the default is `e2-editor-v19`; without it the identity clause reads NOT DONE, fail-closed) | part P1 `c8d53f39` (the judge learned C); V19Witness `00903e29` |
| product-path reader copy (`--candidate v20`, `--candidate-page ccb67a52…`, `V8_REPOINTED 49d1fd5f…`) | `release-0.2.23/product-path/judge.py` | `aed97819`; the v8 repoint recomputed with the runner's own `repointed_page()` (0.2.13's `fac708d0…` and 0.2.12's `0660beaf…` reproduced with the same call) |
| product-path runner | `9d1f44c6…` (0.2.12's `bd6fc0ca…` + one mutation anchor, `8565d973`) | recorded in `product-path/chain.log` |
| C2 judges' `PAGE` | `ccb67a52…` | part P4 `af0ddacc` (judge_c2), `034d9a8c` (judge_p2) |
| C2 judges' `RUNNER` | `probe_typing_latency_view.py 1412e4c863de6fcb`, `probe_typing_latency.py dbad93c0dcf27fbf` | unchanged; the tree's probes hash exactly these (checked 2026-10-15; `c2-extension.sh` re-checks) |
| C2 reading | three runs r1–r3; table in ruling **J-b.2**; one extension r4–r6 by `c2-extension.sh` only on row 3 | `RULING-2026-10-15-pre-binding.md` |
| Firefox profile scratch | `wasm_sdk_probe/build/scratch-m3-production-ui/ff-*` removed at the end (195 there on 2026-10-15) | 0.2.13's chain |

## New-document: in the count, and why

`check_m3_new_document.py --label counted` **is in the chain** (step 8), with a `--label shakedown` first (step 4, under the STOP rule like every other runner the chain counts). Basis: `specs/SPEC-M3-new-document.md` §4 「計數語意」 — N1–N9 are decided by one `--counted` run (two browsers × two arms), and 0.2.19 was an uncounted candidate because "the five-hour count chain is batched into the next engine-changing batch", which is this one; §7.5 「計數語意」 — from 0.2.20 on the count binds the **candidate engine** (`ENGINE_BUILD_ID`, `PAGE_SHA256`), both `None` until the binding step writes them, so that "the count refuses rather than inheriting 0.2.19's engine clause". Part P3 (`004fcdd3`) wrote exactly those five bindings for 0.2.23 and the report's `--red-cases` give 39 RED / 0 MISS, i.e. the runner was bound **for this count** and would otherwise be a binding with no run. The rule set it runs on is DISPOSITION Q3's (`findings/evidence/new-document/review/DISPOSITION.md`); 0.2.19's acceptance-only clauses stay off the count by construction (`DELTA_HOST_VERSION = "0.2.19"`). Its report goes to `findings/evidence/new-document/runs/`; the reader runs its `--red-cases` on it. Not strictly in the §9.4 list of "the six M3 runners, production UI, autosave, the product-path net", so it is listed here as the one addition to that list, with this reason.

## Resolved before launch: the production-UI arms Rbs, Rdel and B3x expected a refusal that v20 no longer makes

Found while preparing (from source: `check_m3_production_ui.py` had only pin commits since `3a6603de`), witnessed by the main session (`../witness-c-0.2.23/`, `f3b543c9`: non-counted, runner `bd3a15fb…` unedited, host 0.2.23, both browsers), decided the same night; the full registration is **SPEC-M3-link-batch §17.3**. In short:

- On v20 the engine carries **C** (SPEC-M3-link-batch §4.4, §10.5): Backspace at the document start and Delete at its end are `verified-boundary-noop` (busy→ready in 2,257–2,261 ms on the witness, revision unchanged), no refusal, no reopen, generation stays 1. On this document v19's only refusals were its two ends (SPEC-M3-production-ui §13.1); on v20 there is none left.
- **Rbs/Rdel re-expected under C** (A1-2′ R, §10.7's new expectation): 0 refusals (generation stays `'1'`), the document unchanged (exactly one marker on the server, the marker-removed text = `ORIGINAL_SEQ`), no sample outside ready/busy (A1-3′ inverted). Keyed on the **bytes of the wasm the host serves** — the merge runner's precedent `boundary_noop_declared` (`7e6c9acd`), the emitted fragment `,"completion":"verified-boundary-noop"`, imported from it, decoded from `engine/files/profiles/<p>/probe.wasm.gz` with the sha256 checked against the manifest; recorded in the report as `static.boundaryNoop`; **fail-closed**: unreadable → the run refuses (exit 2), a recorded-but-`None` key → the R arms read red. A pre-key report is re-judged with `--score … --engine <archived package>` (its buildId must be the report's). Shown: the 34 committed production-UI reports score byte-identically under the old and new runner (30 identical; the 4 `no-scope/*.json` differ only in a traceback's line numbers — they have no `runs` and were never runner reports); 0.2.12's pooled `--red-cases` still `40/40`; the witness: Rbs/Rdel 0/1 × 4 before → 1/1 × 4 after under `--engine build/archive/host-0.2.23-engine-c3c22d9294de068a`; the C-branch red cases 6/6 (`../witness-c-0.2.23/rejudge-under-c.txt`). `wait_reopened` (60 s) is kept — it ends by timeout and changes nothing scored; it costs about 60 s per R arm per round. **§34.4: repaired because of execution +1** (witness `f3b543c9`).
- **B3x withdrawn from this count** (AGENTS.md §4): its premise (spec §13.2) is false under C, nothing can induce it; its scoring is not edited; the chain does not run it and the reader does not pool it. Registered (AGENTS.md §3): A1-5 (the Worker generation ceiling's rescue, notice and reload) and A1-2′ R's rescue across a refusal **still exist as behaviour on v20** (refusals remain, e.g. Delete at a table cell's end, finding 136) but no counted arm induces them — unguarded on v20+ until an arm on a fixture with a real refusal exists (a work item, new mechanism, not built). The owner confirms the B3x part in the morning.
- **Named limit, from the main session's review (SPEC-M3-link-batch §17.4; no code, §34.4: no witness):** the C branch (`score_noop`) has no positive control. A boundary key the page swallowed before it reached the engine would leave generation 1, one marker, the original text and no blocked sample — all green. The evidence that the key ran is in the timeline: one busy span of about 2.26 s with `rev` unchanged (the witness: 2,257–2,261 ms on all four R runs; every other busy span ≤ 905 ms). **When RESULT is written, the reader confirms this by hand for every counted Rbs/Rdel run** (a span ≥ 2,000 ms, `rev` equal at its start and end) and writes the per-run spans into RESULT; a run without it is NOT_ESTABLISHED for that arm, not PASS.
- Reading consequence: the pooled production-UI `--red-cases` now reads `red cases: 27/27` with 13 `no passing B3x run` notes and **exit 1** by the runner's every-mutation rule; `read-0.2.23.sh` prints the expectation beside it.

## The three `--preflight-only` runs made while preparing (2026-10-15)

First run (`preflight-only-2026-10-15.txt`, 38 s), before the amendments:

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
PREFLIGHT-ONLY done: 2 refusal(s)
```

The 10 lock rows (a read-only `SELECT user_id, type, owner, file_id, creation, ttl, scope`): all `admin`, type 2, ttl 300 s, created 00:47–02:32 local on 2026-10-15 — the browser probes of the concurrent `host-0.2.23-hold` measurement, minutes before this preflight; the witness run that followed (`../witness-c-0.2.23/`) cleared them by the runner's own `clear_locks` and left 0. At a real start, with nothing else of ours running, the read should print 0, and if it does not, the refusal is correct: the runners clear the whole table and would clobber whoever holds those locks. The desk at the time: load 1.3–1.9, 35 chrome processes (31 browser processes: the owner's desktop Chrome), 1 firefox, swap used 5.2 GB of 64 GB.

Second run (`preflight-only-2026-10-15b.txt`, 37 s), after the amendments (B3x removed from the chain, the runner re-expected): P0, P1, P2 (same numbers), P4 ok; **P5 `oc_files_lock` rows: 0: ok** (the witness run's `clear_locks` had emptied the table); P5 agreement refused (no window yet); P6 134 + 108 OK. **P3 REFUSED on a false positive**: the one `pgrep -af` line was the harness's own wrapping `bash -c … eval '…'` command, which quoted `check_m3_production_ui.py` because the same command ran `py_compile` on the runner — no runner was running. The raw line is kept in the file. The reading's exclusion was widened from "this script's command line" to "this script and the shells it was launched from" (the ancestor PIDs of the chain; the ruling's "excluding pgrep itself", one step further): a launching shell's command line can quote a runner's name without running one; a runner, probe or judge is never an ancestor of the chain. Run b's P6 outputs were not kept (the copy failed on the same echoed line).

Third run (`preflight-only-2026-10-15c.txt`, 38 s, with the exclusion in place and a launching command line that again named `check_m3_production_ui.py` on purpose): P0 ok; P1 `b false`; P2 rc=0 bytes=738274 grep=167; **P3 0 lines: ok**; P4 all `ccb67a52a3fe4b73`, host `2ccf1a9` 0.2.23 clean; P5 agreement refused (by design, no window yet), `oc_files_lock` rows 0: ok; P6 unittest `Ran 134 tests … OK`, `make test-e2-c-static` `Ran 108 tests … OK`, both exit 0 (`-p6-unittest.txt`, `-p6-static.txt`); `PREFLIGHT-ONLY done: 1 refusal(s)`.

## §34.4 for this preparation

Repaired because of execution **1**: `check_m3_production_ui.py`, the R arms' expectation under C, witness `f3b543c9` (`../witness-c-0.2.23/`; before/after in `rejudge-under-c.txt`). Repaired because of review **0**. No judge, test or Makefile edited; B3x's scoring untouched. Other edits outside this directory and `release-0.2.23/product-path/`: the release-text draft §5 (two revision-log rows) and SPEC-M3-link-batch §17.3 (append-only).
