# Host 0.2.22: H1, 132-B and the K3 regression net again (task 10-14r)

Task: `handoff/tasks/TASK-2026-10-14r-host-0.2.22-h1.md`, which repeats `handoff/tasks/TASK-2026-10-14p-host-0.2.21-k3-regression-net.md` on the new bytes; criteria are H1 of `handoff/tasks/TASK-2026-10-14q-fix-144-held-depth-counts-held-presses.md`. Mechanical runs of existing probes, read with existing judges unchanged, on host 0.2.22 (finding 144's page installed). The probes, judges and readers are the ones 10-14p ran: `git diff 121df038 HEAD` (10-14p's commit) over `findings/evidence/132/held-into-refusal`, `findings/evidence/134`, `findings/evidence/132/judge_132b.py`, `findings/evidence/132/read_hold.py`, `findings/evidence/host-0.2.20-hand-test`, `findings/evidence/host-0.2.21/judge_k.py` and `wasm_sdk_probe/tools` is empty except for one file, `wasm_sdk_probe/tools/build_e2_c_shell_bundle.py` (the v71 freeze commit `8df98ec6`: `MANIFEST` v70 → v71 and a comment; it is the tool behind each report's `static.shellBundle`, not a probe or a judge). Nothing here changes a probe, judge, check or product file; no `make`, package, `occ upgrade`, host change or `--write`. Facts only: inferences are labelled as inferences, and anything I did not check is marked "unverified". Times are UTC.

## Result in one table

| clause | measured on 0.2.22 | 0.2.21 (10-14p) | 0.2.18 (guard-r2) | verdict |
|---|---|---|---|---|
| K3a-1 held probe, C-aware judge, `--page aa50cd20…` | `verdict PASS`, exit 0, 12 of 12 runs (`k3a-held/judge-output.txt`) | PASS, 12 of 12 | n/a | **PASS** |
| K3a-2 table probe, same judge | `verdict PASS`, exit 0, 12 of 12 runs (`k3a-table/judge-output.txt`) | PASS, 12 of 12 | n/a | **PASS** |
| K3a-3 restore-window is a void C-profile run | refusals 0, generations `['1']`, polls 954 / 954 / 959 (Chrome) and 903 / 905 / 901 (Firefox) at the 20 s deadline, first typed key 20,004.8–20,017.0 ms (Chrome) and 20,009.2–20,016.4 ms (Firefox) after the Delete keydown, 6 of 6 rounds (`k3a-restore-window/timing.txt`) | polls 955–964 / 898–902, first key 20,018–20,023 ms | n/a | **recognised as void, as 10-14m describes it** |
| K3b-1 `burst-1s`, exactly 1 engine delete request | Chrome 1 request / 1 response; Firefox 1 / 1 (18 keydowns, 18 `beforeinput` each) | 1 / 1 both | n/a | **PASS** (both) |
| K3b-2 `burst-1s`, 處理中 ends < 2.5 s after the first keydown | Chrome ready at 2,260.9 ms; Firefox 2,257.1 ms | 2,262.1 / 2,256.2 | n/a | **PASS** (both) |
| K3b-3 `burst-1s`, generation `1`, document unchanged, no toast | generations `['1']`, revision 0 → 0, `toasts []` in both | same | n/a | **PASS** (both) |
| K3b-4 `page-number` (d) text bottom ≤ `#content` bottom | Chrome 965.8 ≤ 972; Firefox 980.5 ≤ 986 | same numbers | n/a | **PASS** (both) |
| K3b-5 `page-number` (e) font ≥ 13 px, contrast ≥ 4.5:1 | 13 px, 15.91:1 (`rgb(34,34,34)` on white) in both | same | n/a | **PASS** (both) |
| K3b-6 `page-number` (f) follows the wheel | 18 steps (17 distinct texts in Firefox, 18 in Chrome), never hidden, first 「第 1–2 頁，共 60 頁」, last 「第 1 頁，共 60 頁」 | same | n/a | **PASS** (both) |
| K3b-7 `page-number` (g) full-width bar at the root's bottom edge, number leftmost | Chrome bar `[8, 940, 1834, 32]`, root bottom 972, text left 20; Firefox `[8, 954, 1834, 32]`, root bottom 986, text left 20 | same | n/a | **PASS** (both) |
| **K3c / H1 132-B held-key probe, `132-B PASS`** | **`132-B PASS`, judge exit 0.** 12 of 12 holds PASS, both wash controls PASS | **`132-B FAIL`**, exit 1, 12 of 12 holds FAIL (a) and (c) | `132-B PASS` | **PASS** |
| **H1 (a): ≤ 2 deletes after release in 12/12 holds** | **2, 2, 2, 2, 1, 2** (Chrome) and **1, 2, 1, 2, 2, 2** (Firefox): max 2, 12 of 12 within the limit | 28, 29, 29, 29, 29, 29 / 28, 27, 27, 27, 27, 28 | 1–2 | **PASS** |

`judge_k.py` (K3b) printed `VERDICT PASS`, exit 0; its `--red-check` self-test printed `RED-CHECK verdict: K2 red=True K4 red=True -> self-test PASS` (`k3b/judge-k-red-check-output.txt`). No red clause in this run. One anomaly that is not a clause is recorded under "A change in the source tree during the 132-B run" below.

## K3c / H1 in detail

`k3c-132b/judge-output.txt` (the first line is the `$ …` command line and the trailing `exit 0` was appended by my wrapper; the judge's own last line is `132-B PASS`):

```
chrome hold-high round 0|1|2: PASS      chrome hold-low round 0|1|2: PASS
firefox hold-high round 0|1|2: PASS     firefox hold-low round 0|1|2: PASS
chrome wash-control: selection fills [5]  PASS
firefox wash-control: selection fills [9]  PASS
132-B PASS
```

(The file lists the twelve holds as twelve lines `<browser> hold-<arm> round <n>: PASS`; the block above is a compaction.) Per-hold numbers (`k3c-132b/hold-table.txt`, a one-off reader over the repo reader's `read_hold-output.txt`), beside 0.2.21's (`../../host-0.2.21/k3/k3c-132b/`) and 0.2.18's (`../../136/guard-r2/132-b/README.md`, the verdict of record for that page):

| | 0.2.22 Chrome (6 holds) | 0.2.22 Firefox (6 holds) | 0.2.21 Chrome / Firefox | 0.2.18 Chrome / Firefox |
|---|---|---|---|---|
| keydowns / flagged repeats | 52 / 51 | 52 / 51 | 52 / 51 | (not tabulated there) |
| deleted per hold | 25, 25, 25, 25, 25, 26 | 26 ×6 | 52 ×12 | 25 ×6 / 26 ×6 |
| `beforeinput` events | = deleted (25, 25, 25, 25, 25, 26) | = deleted (26 ×6) | **102** ×12 | = deleted |
| (a) deletes after release (limit ≤ 2) | **2, 2, 2, 2, 1, 2** | **1, 2, 1, 2, 2, 2** | 28–29 / 27–28 | 1–2 |
| last delete after release (ms) | 65.3–115.5 | 59.5–89.5 | 1,834.7–1,846.8 / 1,781.1–1,824.6 | 58.4–115.8 / 60.9–101.3 |
| (b) shown / done at release (needs shown ≥ done − 2) | 22/23 ×4, 22/24, 23/24 → pass | 23/25, 23/24, 23/25, 23/24 ×3 → pass | 22/23–22/24 / 23/24–24/25 | 22/23–22/24 / 23/24–23/25 |
| caret band fresh after release (ms) | 83.2–136.9 | 75.4–111.6 | 1,844.5–1,855.1 / 1,799.2–1,835.9 | 73.0–130.4 / 76.7–116.4 |
| (d) washes in hold / on single presses | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| (e) `persistent.differing` | 0 ×6 | 0 ×6 | 0 | 0 |
| characters left in the paragraph after the hold (`leftAfterHold`, `read_hold.py`) | 27 ×5, 26 ×1 | 26 ×6 | **0** ×12 | 27 ×6 / 26 ×6 |
| median gap between deletes (ms) | 65.7–66.4 | 66.5–67.1 | 65.6–65.7 / 66.4–67.0 | 66.7–67.1 / 67.2–67.9 |
| single presses: keydown → done (ms) | 44.3–47.3 | 45.6–53.0 | 44.0–48.0 / 45.8–51.3 | 44.2–49.2 / 45.6–50.8 |
| oldest press's wait, `lag` first → max (ms) | 44.2–45.8 → 138.5–143.4 | 47.1–48.9 → 131.2–136.3 | 44.4–46.8 → 2,303–2,312 / 46.0–49.1 → 2,297–2,341 | (not tabulated) |
| wash-control: range fills | 5 | 9 | 5 / 9 | 5 / 9 |

Reading (facts, then one inference):

- (a) is back inside the limit in all twelve holds: the key came up and the editor kept deleting for at most 115.5 ms (Chrome) and 89.5 ms (Firefox), 1–2 more characters. (c), `beforeinputs == deleted`, passes: 25–26 of each, where 0.2.21 counted 102 against 52.
- Deleted per hold went from 52 (every one of the 52 keydowns became a delete) to 25–26 (0.2.18: 25 in Chrome, 26 in Firefox; here one Chrome hold deleted 26, see the next point); `leftAfterHold` from 0 to 26–27 (0.2.18: 27 in Chrome, 26 in Firefox; here one Chrome hold left 26).
- Chrome `hold-low` round 2 deleted 26 where the other five Chrome holds deleted 25, with its last delete 115.5 ms after release; 0.2.18's Chrome had one value of 115.8 ms. Both are inside the judge's limits (the judge printed PASS for the hold); I compared against no threshold other than the judge's.
- Inference, not a run: the change task 10-14q describes (the depth counts held presses; a held press is released by a direct call, not a synthetic event) is what the numbers look like; I did not read the page source in this task and ran no mutation.

Instrument ran unchanged: no refusal of the instrument, no moved pin or anchor (the judge's `--page` check on `static` and `staticAfter` passed; `probe.out` ends `probe exit 0`). `report.json` carries `deskRepeat` `{delay 500, repeat-interval 30, repeat true}` and `options` `holdMs 2000, holdDelayMs 500, holdIntervalMs 30, holdRounds 3`, the same defaults as the 0.2.18 and 0.2.21 commands. Chrome/151.0.7922.169 14:28:25–14:45:11, Firefox 157.0.1 14:45:11–15:02:14.

## Static (every report)

`static-check.txt` in each step directory is the output of a one-off script (session scratchpad, not kept; the 10-14p script with the three constants changed) over each report's `static` and, where the probe records it, `staticAfter`. It stops the queue on any mismatch of host version, buildId or page. Every `static` reads:

- `hostVersion` 0.2.22, `hostCommit` `ba0125e`, `hostDirty` `[]`;
- `buildId` `0c2af1b33aff9ef9`;
- `servedPage` = `distPage` = `aa50cd20e975954adef23534a5bb73b7105d1206c6d67fc7c5f18cfc9cbbad7a`;
- `servedSession` `f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9` (the same as on 0.2.21);
- `shellBundle` exit 0, manifest `e2/editor-shell-v2-bundle-v71.json`, sha256 `4291cc4bcc12ac3b78b99903adc7ba1d22559362c7a52001bb2d8c6a74f69d93`, `problems` `[]`.

`staticAfter` exists in the held, table, restore-window and 132-B reports and equals `static` in every field except one: the 132-B report's `staticAfter.shellBundle` is **exit 1**; see the next section. The `probe_10_14n.py` reports (K3b) record `static` only. The judges' engine keying resolved `buildId` to the archive `wasm_sdk_probe/build/archive/host-0.2.22-engine-0c2af1b33aff9ef9` (profile `e2-editor-v20`, wasm sha256 `313b08d…`, as for 0.2.21). Host repo `~/Projects/Nextcloud_Apps/litecore`: HEAD `ba0125e`, `appinfo/info.xml` `<version>0.2.22`, `git status --short` empty (read before the first step; not re-read after the last, unverified). Not checked: whether `servedPage` matches under gzip and zstd (the task states it; the probes read the served page once per report).

## A change in the source tree during the 132-B run (not a clause; recorded verbatim)

The 132-B report's `staticAfter` (taken at its end, 15:02:14) reads, in `shellBundle`:

```
"exit": 1, "manifest": "e2/editor-shell-v2-bundle-v71.json", "sha256": "4dc10507565992d51527c12c8a738b7f857ff3e67fc2bc98db00c0e4e2252731",
"problems": ["dist copy differs from source: web/e2-editor-app.js (run `make e2-c-assets`)",
 "manifest is out of date: added=[] removed=[] changed=['web/e2-editor-app.js']",
 "refusing to rewrite e2/editor-shell-v2-bundle-v71.json -- it exists with digest 4291cc4bcc12ac3b... and the tree now hashes 4dc10507565992d5.... A changed shell needs a NEW generation: bump MANIFEST and add this one to FROZEN_MANIFESTS. --force only if you mean to discard the record of what a round actually ran on."]
```

Cause (fact from `ls` and `git log`, not from the probe): `wasm_sdk_probe/web/e2-editor-app.js` was modified in the study_LiteCore tree at 14:33:21Z (22:33:21 +0800) and committed at 14:35:39Z as `bb30b99f` ("SPEC-M3-scroll-page-bubble 的單元半…", by the main session, not by me; `web/e2-editor-app.js` is now `ccb67a52…`, `dist/e2-editor-app.js` is still `aa50cd20…`, and that commit's message says `dist/` and the browser were not touched). That is inside the 132-B window (14:28:24–15:02:14). The earlier steps' `staticAfter` (held, table, restore-window; all taken before 14:27) read `shellBundle` exit 0, and the 132-B `static` (14:28) read exit 0.

What this does and does not touch (facts): `staticAfter.servedPage` and `.distPage` in the 132-B report both still read `aa50cd20e975954a…`, and the judge's `--page` check on `static` and `staticAfter` passed; the page the browsers loaded is the one the host serves (the installed copy), not the tree's `web/`. The shell-bundle check compares the study_LiteCore source tree with its frozen manifest, so it went red because the tree moved, not because the installed host moved. The queue's static-check script requires version, buildId and page only (as in 10-14p) and so printed `-> OK` for that line; it did not stop the queue and I did not rerun. Unverified: whether anything the main session ran at the same time (the commit message names node tests and a mutation census) shared CPU with the 132-B probe; the desk load after the step was 3.43 / 2.80 / 2.19, against 0.9–1.8 (1-minute value) before every step; (a) sits at the limit of 2 in 9 of the 12 holds (as 0.2.18 did, 1–2), so a slower desk could in principle push a hold over, and I did not rerun on a quiet desk. The 132-B result as recorded stands on the page it ran on (`aa50cd20…`), and a reader who wants the shell-bundle check green at the end of that step should read it as red for the reason above.

## Desk

`health-checks.txt` holds a block before each step and one after the last: KWallet `Locked` (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`), a default-flag headless Chrome check (`timeout 30 google-chrome --headless=new --user-data-dir=<tmp> --dump-dom https://litecore.ddev.site:8443/login`, rc 0 and `Nextcloud` ×328 every time), the process counts, the load, and "ours running". The queue wrapper (`queue-log.txt` is its stdout) would have stopped on `b true`, a failed Chrome check or anything of ours running; none occurred. The wrapper is the 10-14p wrapper with the constants changed (session scratchpad, not in the tree).

| time (UTC) | before step | KWallet | `pgrep -c chrome` | Chrome browser processes | `pgrep -c firefox` | load (1/5/15) | ours running |
|---|---|---|---|---|---|---|---|
| 14:03:13 | H0 | b false | 35 | 31 | 1 | 1.72 1.05 0.87 | 0 |
| 14:03:16 | H1 (held) | b false | 35 | 31 | 1 | 1.66 1.05 0.87 | 0 |
| 14:12:57 | H2 (table) | b false | 35 | 31 | 1 | 1.78 1.33 1.06 | 0 |
| 14:21:40 | H3 (restore-window) | b false | 35 | 31 | 1 | 0.93 1.18 1.09 | 0 |
| 14:26:11 | B1 (K3b Firefox) | b false | 33 | 29 | 1 | 0.98 1.05 1.05 | 0 |
| 14:27:23 | B2 (K3b Chrome) | b false | 37 | 33 | 1 | 1.39 1.16 1.09 | 0 |
| 14:28:21 | C1 (132-B) | b false | 34 | 30 | 1 | 1.52 1.27 1.13 | 0 |
| 15:02:14 | after C1 | b false | 37 | 33 | 1 | 3.43 2.80 2.19 | 0 |

- **The desk was not clean.** The owner's Chrome (with the claude-in-chrome extension host) and snap Firefox were running throughout; I did not start, stop or touch either. The owner's `手測-126-60頁.odt` has the same last-modified time (12:39:43Z) in the admin-root listing taken at 15:09Z as in 10-14p's, and `m3-109 測試.odt` is 10:59:33Z; whether the owner used the instance otherwise is unverified.
- The Chrome browser-process count moved between 29 and 33 across steps with nothing of ours running at any step start; I did not find the source of the changes (the owner's browser, unverified).
- `ours running` is the count of `pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20'` lines excluding `pgrep` and the wrapper itself, read after the Chrome check.
- No `.git/index.lock` before the commit.

## Commands and exits

One job at a time, in this order, from the repo root, each with its probe's default arguments except where listed. `probe.out` of each step ends with a `probe exit N` line written by my wrapper; `started-utc-<step>.txt` / `ended-utc-<step>.txt` are the wrapper's. `$PAGE` is `aa50cd20e975954adef23534a5bb73b7105d1206c6d67fc7c5f18cfc9cbbad7a` and `$K` is `findings/evidence/host-0.2.22/h1`.

| step | command | window | exit |
|---|---|---|---|
| H1 | `python3 findings/evidence/132/held-into-refusal/probe_held_into_refusal.py --out $K/k3a-held` | 14:03:19–14:12:57 | 0 |
| H1 judge | `python3 findings/evidence/132/held-into-refusal/judge_held_into_refusal.py $K/k3a-held/report.json --page $PAGE` | | **0**, `verdict PASS` |
| H2 | `python3 findings/evidence/134/table/probe_table_refusal.py --out $K/k3a-table` | 14:13:00–14:21:39 | 0 |
| H2 judge | same judge, `$K/k3a-table/report.json`, same `--page` | | **0**, `verdict PASS` |
| H3 | `python3 findings/evidence/134/restore-window/probe_restore_window.py --out $K/k3a-restore-window` | 14:21:43–14:26:11 | 0 |
| B1 | `python3 findings/evidence/host-0.2.20-hand-test/probe_10_14n.py --out $K/k3b --browser firefox --doc long60 --arms burst-1s,page-number --mode host` | 14:26:14–14:27:23 | 0 |
| B2 | same, `--browser chrome` | 14:27:28–14:28:21 | 0 |
| B judge | `python3 -I findings/evidence/host-0.2.21/judge_k.py --k2 $K/k3b --k4 $K/k3b` | | **0**, `VERDICT PASS` |
| B judge self-test | `python3 -I findings/evidence/host-0.2.21/judge_k.py --red-check` | | 0, `RED-CHECK verdict: K2 red=True K4 red=True -> self-test PASS` |
| C1 | `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out $K/k3c-132b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (the guard-r2 and 10-14p command) | 14:28:24–15:02:14 | 0 |
| C1 judge | `python3 findings/evidence/132/judge_132b.py --page $PAGE $K/k3c-132b/report.json` | | **0**, `132-B PASS` |
| C1 reader | `python3 findings/evidence/132/read_hold.py $K/k3c-132b/report.json` | | 0 |

Rounds: held = 6 per browser (`start-press` 1, `start-hold` 2, `end-hold` 2, `end-press-type` 1); table = 6 per browser (four 1-round arms plus `cell-start-hold` 2); restore-window 3 per browser; 132-B 3 holds per hold arm per browser plus the wash control. Hold arms in the held and table probes hold the key 8 s (`holdMs` 8000, delay 500, interval 30; `deskRepeat` read back `{delay 500, repeat-interval 30, repeat true}`).

K3b used `probe_10_14n.py` (the file the task names), not `probe_10_14o.py` or `probe_10_14q.py`. The two arms ran in one process per browser, `burst-1s` first, each with its own fresh open of the 60-page fixture (`probe-10-14n-long60.odt`, 5,149 bytes). The probe created and deleted its folder (`probe-10-14n-20261014T142615`, `…T142728`; `deletedFolder` 204 in both reports).

## K3a in detail

### Held (`k3a-held/`, judge reads C; facts in `facts.txt`)

The judge printed `expectation C (RULES_C on [...])`; the twelve per-run lines are all `PASS`. Every run: refusals 0, generations `['1']`, document read back `sameAsOriginal` true, `charDelta` 0, 211/211 paragraphs, no `limit`, scroll within the 10-14l pattern.

| arm (runs per browser) | marker | `scrollTop` | judge |
|---|---|---|---|
| `start-press` (1) | `wvy` in paragraph 0 only, at its start | 0 | PASS ×2 |
| `start-hold` (2) | `wvy` in paragraph 0 at its start | 0 | PASS ×4 |
| `end-hold` (2) | `zqx` + `wvy` contiguous in paragraph 210, `wvy` at the paragraph end | Chrome 21,517 → 21,633; Firefox 21,503 → 21,619 (the same +116 px step as 10-14l and 0.2.21; never below the pre-key value) | PASS ×4 |
| `end-press-type` (1) | `kj` + `zqx` contiguous in paragraph 210 | 21,517 / 21,503 constant | PASS ×2 |

Caret (property 4 of §10.7) is, as in 10-14l, not measured by an independent read: "caret after" is inferred from the marker's place. Unverified beyond that.

### Table (`k3a-table/`)

`cell-start-hold` (the one arm under C, 2 per browser): refusals 0 ×4, generations `['1']`, `refusalStage` `{"stage": null, "stages": []}`, `paragraph1StartsWithAfter` true and `paragraph1IsAfterThenOriginal` true, document `sameAsOriginal` true, `charDelta` 0, 6/6 paragraphs: PASS ×4. The four other arms keep the refusal expectation (they still refuse on v20): `before-table-press-type` and `before-table-hold` refuse at stage `key-posted`, `cell-press-type` and `cell-hold` at `anchor-mismatch`, each with refusals 1 and generations `['1','2']` in both browsers (refusal at 2,305.5 / 2,104.9 / 237.6 / 46.6 ms in Chrome and 2,262.1 / 2,095.4 / 208.2 / 40.3 ms in Firefox; 0.2.21: 2,297.6 / 2,103.0 / 255.4 / 45.9 and 2,283.4 / 2,098.4 / 238.9 / 41.3), document `sameAsOriginal` true, `charDelta` 0: PASS ×8.

### Restore-window (`k3a-restore-window/`; no judge reads this probe)

Read as 10-14m's README §3 says to recognise it: `summary.refusals` 0, `generations` `['1']`, `polls` at the deadline. `timing.txt` (first typed key's keydown minus the Delete keydown on the page clock, from `runs[].log`):

| browser | round | refusals | generations | polls | first typed key after the Delete keydown (ms) | `scrollTop` | document |
|---|---|---|---|---|---|---|---|
| chrome | 0 / 1 / 2 | 0 / 0 / 0 | `['1']` ×3 | 954 / 954 / 959 | 20,010.4 / 20,004.8 / 20,017.0 | 21,517 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 0 / 1 / 2 | 0 / 0 / 0 | `['1']` ×3 | 903 / 905 / 901 | 20,016.4 / 20,009.2 / 20,010.4 | 21,503 | same |

(0.2.21: polls 955 / 958 / 964 Chrome, 899 / 898 / 902 Firefox; first key 20,018–20,023 ms.) The report is void as a window measurement and is not read against G5's v19 criterion.

### Observation on the held tail (not a K3 clause)

Time from the last repeat keydown to the first `ready` state entry (`facts.txt`, `tailMs`), beside 0.2.21's from its README: `start-hold` Chrome 1,843 / 1,837 ms (0.2.21: 1,851 / 1,847), Firefox 1,441 / 1,509 (1,487 / 1,483); `end-hold` Chrome 1,091 / 1,107 (1,094 / 1,096), Firefox 759 / 809 (771 / 802); table `cell-start-hold` Chrome 1,776 / 1,776 (1,776 / 1,776), Firefox 1,476 / 1,445 (1,483 / 1,471); the table hold arms that still refuse (`before-table-hold`, `cell-hold`) 4,216 / 4,245 (Chrome) and 4,273 / 4,309 (Firefox) (4,207 / 4,239 and 4,272 / 4,295). These holds start at a document or cell boundary and are unchanged by finding 144's fix (10-14q names the boundary hold as a residual of 141). What did change in these probes: `beforeinputs` per hold run is **16** (`start-hold`, `cell-start-hold`) and **11** (`end-hold`), against 258–259 / 255 on 0.2.21 (the re-dispatched events) and 13 / 8 on 0.2.20 as 0.2.21's README quotes 10-14l (I did not re-read 10-14l). The judged properties do not depend on this.

## K3b in detail (`k3b/`; facts in `k3b-facts.txt`, judge in `judge-k-output.txt`)

Burst at the document start (`burst-1s`: 1 press, then from 500 ms a keyup+keydown every 30 ms to 980 ms, keyup at 995 ms, every keydown `repeat: false`), after a real click on the first line and Home:

| | Firefox 157.0.1 | Chrome 151.0.7922.169 |
|---|---|---|
| keydowns / `beforeinput` | 18 / 18 | 18 / 18 |
| engine requests (`editorActionV2`) / responses | 1 / 1 | 1 / 1 |
| the response | `verified-boundary-noop`, `changed false`, `waitedMs 2253`, revision 0 → 0 | same, `waitedMs 2258` |
| 處理中 ends (`readyAgainMs`) | 2,257.1 ms (label 「⌫ 刪除 2257 ms」) | 2,260.9 ms (「⌫ 刪除 2261 ms」) |
| generations / revision / toasts | `['1']` / 0 → 0 / `[]` | `['1']` / 0 → 0 / `[]` |
| `limit` | null | null |
| verdict | PASS | PASS |

(0.2.21: 1 request, 2,256.2 / 2,262.1 ms; 10-14n, no fix: 18 requests and 40,589–40,617 ms.)

Page number (`page-number`, 18 real wheel steps: 14 × 700 px, 3 × 3,000 px, then −40,000):

| | Firefox (viewport 1850×994) | Chrome (1850×980) |
|---|---|---|
| text rect (left, top, w, h) / bottom | `[20, 960.5, 98.3, 20]` / 980.5 | `[20, 946.8, 98.3, 19]` / 965.8 |
| `#content` rect / bottom | `[8, 50, 1834, 936]` / 986 | `[8, 50, 1834, 922]` / 972 |
| (d) bottom ≤ bottom | PASS | PASS |
| (e) font, colour on background, contrast | 13 px, `rgb(34,34,34)` on `rgb(255,255,255)`, 15.91:1 | same |
| (f) steps | 18, never hidden, 17 distinct texts (the judge asks for at least 10) | 18, never hidden, 18 distinct |
| (g) bar rect / root bottom / text left | `[8, 954, 1834, 32]` = `#content`'s x and width; 986; 20 | `[8, 940, 1834, 32]`; 972; 20 |
| `elementAtCentre` / `display` | `page-status` / `flex` | same |
| page-issued engine requests during the wheel steps (`scrollLog`, `rq` < 900000) | 21 `paint`, 0 `pageRectangles`; the probe's own asks at open and after the scroll answer `parts 60` | same |

The (d)–(g) numbers equal the 0.2.21 K3b run's, to the pixel.

**Odd, not a clause (the same as on 0.2.21):** in the Chrome `page-number` arm the host's file lock was refused (`host.lock` `{"state": "refused", "status": 423, "holder": {"owner": "admin", "type": "2"}}`) and the host notice bar 「你在另一個視窗或裝置開著這個檔案：這裡的存檔會另存副本。」 was shown, because that arm opened the same file right after the `burst-1s` arm's session closed. The Firefox arms both read lock `held`. None of (d)–(g) reads the lock. I did not rerun the arm alone.

## Cleanup

The held, table and restore-window probes upload `probe-held-refusal.odt`, and the 132-B probe `probe-hand-0212.odt`, to the admin root and delete neither. After the last step I listed the admin root (`PROPFIND` depth 1) and deleted exactly those two, through the probes' own `Instance` helper (`cleanup.txt` holds the listing before and after: `probe-held-refusal.odt` last modified 14:26:00Z and `probe-hand-0212.odt` 15:01:58Z, both from this run; both `DELETE` → 204). The listing after is the listing before minus those two lines (and the root's own timestamp). Nothing else on the instance was touched: `probe-autosave-m1.odt`, `probe-autosave-m3.odt` and the owner's files (`手測-126-60頁.odt`, `m3-109 測試.odt`, `PMPC…`, `測試新增文件.odt`, `新增測試文件-chrome.odt`, …) keep the modification times they had. The K3b probe folders were deleted by the probe itself (204).

## What was not checked, and what was not done

- The cause of the fix is not diagnosed here: I did not read `wasm_sdk_probe/web/e2-editor-app.js` or the tests, and ran no mutation of the judge or the page. The 132-B PASS is a measurement of the installed page's behaviour; the sentence in the 132-B section that connects it to 10-14q's change is an inference.
- Whether the 132-B (a) result also holds on a real keyboard path (the probe's `repeat` flags come from the driver: CDP `autoRepeat`, WebDriver key repeat; the owner's KDE/Wayland/fcitx5 path was never measured, per 10-14n).
- The caret by any independent read; a rerun on a quiet desk; Orca or any screen-reader path; the host-segment arms of 128-B, 131-B, 121-B, 129-B, C2/P2 (only 132-B was in the task).
- Whether the main session's concurrent work (the commit `bb30b99f` window above) affected any timing; whether `servedPage` matches under gzip and zstd.
- No `make`, link, freeze, `--write`, package, `occ upgrade`, host change; no edit of any tool, judge, probe, check, `web/`, `editor-shell*/`, `sdk/` or `src/` by me. No `git push`.
- Files here: `k3a-held/`, `k3a-table/`, `k3a-restore-window/`, `k3b/`, `k3c-132b/` (each: `report.json`, `probe.out` (K3b: `probe-firefox.out`, `probe-chrome.out`), `started/ended-utc-*.txt`, `static-check.txt`; plus `judge-output.txt`, `facts.txt`, `timing.txt`, `hold-table.txt`, `read_hold-output.txt`, `k3b-facts.txt`, `judge-k-output.txt`, `judge-k-red-check-output.txt` where named above), `health-checks.txt`, `queue-log.txt`, `cleanup.txt`. `facts.txt`, `timing.txt`, `hold-table.txt`, `k3b-facts.txt` and `static-check.txt` are output of one-off reader scripts over the reports (session scratchpad, not kept; the 10-14p scripts, with `timing.txt`, `hold-table.txt` and `k3b-facts.txt` rewritten because the 10-14p copies were not kept; I checked the rewrites by running them on the 0.2.21 reports and comparing with the 10-14p outputs for the same fields), not of any tool in the tree.
