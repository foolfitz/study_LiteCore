# Host 0.2.21: the K3 regression net (task 10-14p)

Task: `handoff/tasks/TASK-2026-10-14p-host-0.2.21-k3-regression-net.md`. Mechanical runs of existing probes, read with existing judges unchanged, on host 0.2.21 (finding 141's page and finding 143's CSS installed). Nothing here changes a probe, judge, check or product file; no `make`, package, `occ upgrade`, host change or `--write`. Facts only: inferences are labelled as inferences, and anything I did not check is marked "unverified". Times are UTC.

## Result in one table

| clause | measured | verdict |
|---|---|---|
| K3a-1 held probe, C-aware judge, `--page 2d6c4580…` | `verdict PASS`, exit 0, 12 of 12 runs (`k3a-held/judge-output.txt`) | **PASS** |
| K3a-2 table probe, same judge | `verdict PASS`, exit 0, 12 of 12 runs (`k3a-table/judge-output.txt`) | **PASS** |
| K3a-3 restore-window is a void C-profile run | refusals 0, generations `['1']`, polls 955 / 958 / 964 (Chrome) and 899 / 898 / 902 (Firefox) at the 20 s deadline, first typed key 20,018–20,023 ms after the Delete keydown, 6 of 6 rounds (`k3a-restore-window/timing.txt`) | **recognised as void, as 10-14m describes it** |
| K3b-1 `burst-1s`, exactly 1 engine delete request | Chrome 1 request / 1 response; Firefox 1 / 1 (18 keydowns, 18 `beforeinput` each) | **PASS** (both) |
| K3b-2 `burst-1s`, 處理中 ends < 2.5 s after the first keydown | Chrome ready at 2,262.1 ms; Firefox 2,256.2 ms | **PASS** (both) |
| K3b-3 `burst-1s`, generation `1`, document unchanged, no toast | generations `['1']`, revision 0 → 0, `toasts []` in both | **PASS** (both) |
| K3b-4 `page-number` (d) text bottom ≤ `#content` bottom | Chrome 965.8 ≤ 972; Firefox 980.5 ≤ 986 | **PASS** (both) |
| K3b-5 `page-number` (e) font ≥ 13 px, contrast ≥ 4.5:1 | 13 px, 15.91:1 (`rgb(34,34,34)` on white) in both | **PASS** (both) |
| K3b-6 `page-number` (f) follows the wheel | 18 steps (17 distinct texts in Firefox, 18 in Chrome; 「第 1–2 頁」 … 「第 16 頁」, back to 「第 1 頁，共 60 頁」), never hidden | **PASS** (both) |
| K3b-7 `page-number` (g) full-width bar at the root's bottom edge, number leftmost | Chrome bar `[8, 940, 1834, 32]`, root bottom 972, text left 20; Firefox `[8, 954, 1834, 32]`, root bottom 986, text left 20 | **PASS** (both) |
| K3c 132-B held-key probe, verdict as on 0.2.18 (`132-B PASS`) | **`132-B FAIL`, judge exit 1.** 12 of 12 holds FAIL clauses (a) and (c); (b), (d), (e) pass; both wash controls pass | **RED** |

`judge_k.py` (K3b) printed `VERDICT PASS`, exit 0, for both browsers. K3c is the only red clause. It is recorded verbatim below; no instrument, judge or product file was changed in response.

## K3c in detail (the red clause)

`k3c-132b/judge-output.txt` (the first line is the `$ …` command line and the trailing `exit 1` was appended by my wrapper; the judge's own last line is `132-B FAIL`):

```
chrome hold-high round 0: FAIL a c
    (a) deletesAfterRelease 28
    (c) beforeinputs 102 != deleted 52
...                                     (12 holds, all "FAIL a c")
chrome wash-control: selection fills [5]  PASS
firefox wash-control: selection fills [9]  PASS
132-B FAIL
```

The per-hold numbers (`k3c-132b/hold-table.txt`, read from `report.json`; `read_hold-output.txt` is the repo reader's output), beside 0.2.18's (`findings/evidence/136/guard-r2/132-b/README.md`, the verdict of record for that page, `132-B PASS`):

| | 0.2.21 Chrome (6 holds) | 0.2.21 Firefox (6 holds) | 0.2.18 Chrome | 0.2.18 Firefox |
|---|---|---|---|---|
| keydowns / flagged repeats | 52 / 51 | 52 / 51 | (not tabulated there) | |
| deleted per hold | **52** ×6 | **52** ×6 | 25 ×6 | 26 ×6 |
| `beforeinput` events | **102** ×6 | **102** ×6 | = deleted | = deleted |
| (a) deletes after release (limit ≤ 2) | **28, 29, 29, 29, 29, 29** | **28, 27, 27, 27, 27, 28** | 1–2 | 1–2 |
| last delete after release (ms) | 1,834.7–1,846.8 | 1,781.1–1,824.6 | 58.4–115.8 | 60.9–101.3 |
| (b) shown / done at release (needs shown ≥ done − 2) | 22/24, 22/23 ×5 → pass | 23/24, 23/25, 24/25, 23/25, 23/25, 23/24 → pass | 22/23–22/24 | 23/24–23/25 |
| caret band fresh after release (ms) | 1,844.5–1,855.1 | 1,799.2–1,835.9 | 73.0–130.4 | 76.7–116.4 |
| (d) washes in hold / on single presses | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| (e) `persistent.differing` | 0 | 0 | 0 | 0 |
| median gap between deletes (ms) | 65.6–65.7 | 66.4–67.0 | 66.7–67.1 | 67.2–67.9 |
| single presses: lag (ms) | 44.0–48.0 | 45.8–51.3 | 44.2–49.2 | 45.6–50.8 |
| oldest press's wait, `lag` first → max (ms) | 44.4–46.8 → 2,303–2,312 | 46.0–49.1 → 2,297–2,341 | | |
| wash-control: range fills | 5 | 9 | 5 | 9 |

(a) is the physical symptom: the key came up and the editor kept deleting for about 1.8 s, 27–29 more characters. (c) fires because `beforeinputs` (102) is not `deleted` (52): the instrument counts both the 52 keydown-originated `beforeinput` events and the 50 that the page re-dispatches on the sink when it releases a held press (the 10-14o README names the same counting in its K2: "34 beforeinput: the 18 presses plus the 16 held presses re-delivered through the sink"). Inference: (c) is red partly because of what the instrument counts, (a) is red on a behaviour. I did not change either.

**Reading of the cause (inference, from reading `wasm_sdk_probe/web/e2-editor-app.js` lines 2515–2630 and 2832–2842; not tested by any run, no file touched).** H2's cut is `dropsHeldRepeat`: a flagged repeat keydown is dropped when `deletesInFlight >= HELD_DELETE_DEPTH (2)`. Since finding 141 a `beforeinput` of a key whose delete is unanswered is held and counted in `heldDeletes`, and only the sent delete is counted in `deletesInFlight`. So during a hold `deletesInFlight` stays at 1 (one delete out, the others held), the keydown cut at depth 2 is not reached, every one of the 52 keydowns becomes a held-then-released delete (`deleted` 52, against 25–26 when H2 cut them), and at release about 28 held presses are still to be released one per engine answer (about 65 ms each, which is where the 1.8 s comes from). The 10-14o README says "SPEC-M3-held-key §3.2's 「放開之後最多再刪 2 字」 is unaffected inside text"; this measurement contradicts that sentence for a held key (flagged repeats) inside text, in both browsers. The 10-14o K1 table lists T2 (18 unflagged presses in text) and T4 ("flagged repeats obey H2 at the keydown"); it does not list a flagged hold of a key whose first press is still unanswered. I did not read the tests.

Instrument ran unchanged on 0.2.21: no refusal of the instrument, no moved pin or anchor (the judge's `--page` check on `static` and `staticAfter` passed; `probe.out` ends `probe exit 0`). `report.json` carries `deskRepeat` `{delay 500, repeat-interval 30, repeat true}`; the hold length is the probe's default (`--hold-ms` 2,000; 52 keydowns = the first press plus 51 repeats from 500 ms at 30 ms), the same as the 0.2.18 command, which did not pass `--hold-ms` either.

## Static (every report)

`static-check.txt` in each step directory is the output of a one-off script (session scratchpad, not kept) over each report's `static` and, where the probe records it, `staticAfter`. All read identically, and the queue would have stopped on any mismatch (none occurred):

- `hostVersion` 0.2.21, `hostCommit` `187b36d`, `hostDirty` `[]`;
- `buildId` `9bcdb50969ba53e5`;
- `servedPage` = `distPage` = `2d6c4580e8beaac7ddda4cbda0f346ffb91eff671247225659223307e91a61de`;
- `servedSession` `f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9`;
- `shellBundle` exit 0, manifest `e2/editor-shell-v2-bundle-v70.json`, sha256 `18b12c51…`, `problems` `[]`.

`staticAfter` exists in the held, table, restore-window and 132-B reports (equal to `static`); the `probe_10_14n.py` reports (K3b) record `static` only ("staticAfter absent" in `k3b/static-check.txt`). The judges' engine keying resolved `buildId` to the archive `wasm_sdk_probe/build/archive/host-0.2.21-engine-9bcdb50969ba53e5` (profile `e2-editor-v20`, wasm sha256 `313b08d5cb085897…`, "declares C: True"). Host repo at the end: `187b36d`, `git status --short` empty. Not checked: whether `servedPage` matches under gzip and zstd (the task states it; the probes read the served page once per report).

## Desk

`health-checks.txt` holds a block before each step and one after the last: KWallet `Locked` (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`), a default-flag headless Chrome check (`timeout 30 google-chrome --headless=new --user-data-dir="$(mktemp -d)" --dump-dom https://litecore.ddev.site:8443/login`, rc 0 and `Nextcloud` ×328 every time), the process counts, the load, and "ours running". The queue wrapper (`queue-log.txt` is its stdout) would have stopped on `b true`, a failed Chrome check or anything of ours running; none occurred. The wrapper and helper scripts are in the session scratchpad, not in the tree.

| time (UTC) | before step | KWallet | `pgrep -c chrome` | Chrome browser processes | `pgrep -c firefox` | load (1/5/15) | ours running |
|---|---|---|---|---|---|---|---|
| 12:44:10 | H0 | b false | 33 | 29 | 1 | 1.86 1.67 1.65 | 0 |
| 12:44:13 | H1 (held) | b false | 33 | 29 | 1 | 1.86 1.67 1.65 | 0 |
| 12:54:08 | H2 (table) | b false | 35 | 31 | 1 | 2.09 2.39 2.12 | 0 |
| 13:03:01 | H3 (restore-window) | b false | 35 | 31 | 1 | 1.76 2.50 2.32 | 0 |
| 13:07:35 | B1 (K3b Firefox) | b false | 37 | 33 | 1 | 2.41 2.50 2.36 | 0 |
| 13:08:47 | B2 (K3b Chrome) | b false | 32 | 28 | 1 | 1.94 2.36 2.33 | 0 |
| 13:09:46 | C1 (132-B) | b false | 32 | 28 | 1 | 1.85 2.26 2.29 | 0 |
| 13:34:09 | after C1 | b false | 35 | 31 | 1 | 0.70 1.02 1.58 | 0 |

- **The desk was not clean.** The owner's Chrome (with the claude-in-chrome extension host) and snap Firefox were running throughout; I did not start, stop or touch either. The owner's `手測-126-60頁.odt` has a last-modified time of 12:39:43Z, before my first step, and the same time in the listing taken at 13:33Z (so no change to that file during the run); whether the owner used the instance otherwise is unverified.
- The load was 1.7–2.5 for the first hour and fell to 0.7 at the end. I did not find its source and did not rerun on a quieter desk, so whether a quieter desk would change any number is unverified. K3c's red is not a latency threshold on a noisy number: it is 27–29 extra deletes against a limit of 2, in 12 of 12 holds in both browsers.
- `ours running` is the count of `pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20'` lines excluding `pgrep` and the wrapper itself, read after the Chrome check.
- No `.git/index.lock` before the commit.

## Commands and exits

One job at a time, in this order, from the repo root, each with its probe's default arguments except where listed. `probe.out` of each step ends with a `probe exit N` line written by my wrapper; `started-utc-<step>.txt` / `ended-utc-<step>.txt` are the wrapper's.

| step | command | window | exit |
|---|---|---|---|
| H1 | `python3 findings/evidence/132/held-into-refusal/probe_held_into_refusal.py --out findings/evidence/host-0.2.21/k3/k3a-held` | 12:44:16–12:54:07 | 0 |
| H1 judge | `python3 findings/evidence/132/held-into-refusal/judge_held_into_refusal.py …/k3a-held/report.json --page 2d6c4580e8beaac7ddda4cbda0f346ffb91eff671247225659223307e91a61de` | | **0**, `verdict PASS` |
| H2 | `python3 findings/evidence/134/table/probe_table_refusal.py --out …/k3a-table` | 12:54:11–13:03:01 | 0 |
| H2 judge | same judge, `…/k3a-table/report.json`, same `--page` | | **0**, `verdict PASS` |
| H3 | `python3 findings/evidence/134/restore-window/probe_restore_window.py --out …/k3a-restore-window` | 13:03:04–13:07:35 | 0 |
| B1 | `python3 findings/evidence/host-0.2.20-hand-test/probe_10_14n.py --out …/k3b --browser firefox --doc long60 --arms burst-1s,page-number --mode host` | 13:07:38–13:08:47 | 0 |
| B2 | same, `--browser chrome` | 13:08:52–13:09:46 | 0 |
| B judge | `python3 -I findings/evidence/host-0.2.21/judge_k.py --k2 …/k3b --k4 …/k3b` | | **0**, `VERDICT PASS` |
| B judge self-test | `python3 -I findings/evidence/host-0.2.21/judge_k.py --red-check` | | 0, `RED-CHECK verdict: K2 red=True K4 red=True -> self-test PASS` (`k3b/judge-k-red-check-output.txt`) |
| C1 | `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out …/k3c-132b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (the guard-r2 command) | 13:09:49–13:34:09 | 0 |
| C1 judge | `python3 findings/evidence/132/judge_132b.py --page 2d6c4580e8beaac7ddda4cbda0f346ffb91eff671247225659223307e91a61de …/k3c-132b/report.json` | | **1**, `132-B FAIL` |
| C1 reader | `python3 findings/evidence/132/read_hold.py …/k3c-132b/report.json` | | 0 |

Rounds: held = 6 per browser (`start-press` 1, `start-hold` 2, `end-hold` 2, `end-press-type` 1); table = 6 per browser (four 1-round arms plus `cell-start-hold` 2); restore-window 3 per browser; 132-B 3 holds per hold arm per browser plus the wash control. Hold arms in the held and table probes hold the key 8 s (`holdMs` 8000, delay 500, interval 30; `deskRepeat` read back `{delay 500, repeat-interval 30, repeat true}`).

K3b used `probe_10_14n.py` (the file the task names), not `probe_10_14o.py` (10-14o's copy with one added control arm and a wider "ours running" exclusion). The two arms ran in one process per browser, `burst-1s` first, each with its own fresh open of the 60-page fixture (`probe-10-14n-long60.odt`, 5,149 bytes, built in memory). The probe created and deleted its folder (`probe-10-14n-20261014T130739`, `…T130852`; `deletedFolder` 204 in both reports).

## K3a in detail

### Held (`k3a-held/`, judge reads C; facts in `facts.txt`)

The judge printed `expectation C (RULES_C on […])`; the per-run lines are all `PASS`. Chrome and Firefox read the same unless a cell gives both.

| arm (runs per browser) | refusals | generations | document read back | marker | toasts | `scrollTop` | judge |
|---|---|---|---|---|---|---|---|
| `start-press` (1) | 0 | `['1']` | `sameAsOriginal` true, `charDelta` 0, 211/211 paragraphs | `wvy` in paragraph 0 only, at its start | none | 0 throughout | PASS ×2 |
| `start-hold` (2) | 0 ×4 | `['1']` | same; `kjkjk` fully gone | `wvy` in paragraph 0 at its start | none | 0 | PASS ×4 |
| `end-hold` (2) | 0 ×4 | `['1']` | same | `zqx` + `wvy` contiguous in paragraph 210, `wvy` at the paragraph end | none | Chrome 21,517 before the key, then 21,633 later in the log; Firefox 21,503 → 21,619 (the same +116 px step 10-14l recorded; never below the pre-key value) | PASS ×4 |
| `end-press-type` (1) | 0 | `['1']` | same | `kj` + `zqx` contiguous in paragraph 210 | none | 21,517 / 21,503 constant | PASS ×2 |

Caret (property 4 of §10.7) is, as in 10-14l, not measured by an independent read: "caret after" is inferred from the marker's place. Unverified beyond that.

### Table (`k3a-table/`)

`cell-start-hold` (the one arm under C, 2 per browser): refusals 0 ×4, generations `['1']`, `refusalStage` `{"stage": null, "stages": []}`, `paragraph1StartsWithAfter` true and `paragraph1IsAfterThenOriginal` true, document `sameAsOriginal` true, `charDelta` 0 — PASS ×4. The four other arms keep the refusal expectation (they still refuse on v20): `before-table-press-type` and `before-table-hold` refuse at stage `key-posted`, `cell-press-type` and `cell-hold` at `anchor-mismatch`, each with refusals 1 and generations `['1','2']` in both browsers (refusal at 2,297.6 / 2,103.0 / 255.4 / 45.9 ms in Chrome and 2,283.4 / 2,098.4 / 238.9 / 41.3 ms in Firefox), the reload toasts as in 10-14l, document `sameAsOriginal` true, `charDelta` 0 — PASS ×8.

### Restore-window (`k3a-restore-window/`; no judge reads this probe)

Read as 10-14m's README §3 says to recognise it: `summary.refusals` 0, `generations` `['1']`, `polls` at the deadline. `timing.txt` (first typed key's keydown minus the Delete keydown on the page clock, from `runs[].log`):

| browser | round | refusals | generations | polls | first typed key after the Delete keydown (ms) | `scrollTop` values | marks / paragraph | document |
|---|---|---|---|---|---|---|---|---|
| chrome | 0 / 1 / 2 | 0 / 0 / 0 | `['1']` ×3 | 955 / 958 / 964 | 20,019.6 / 20,022.5 / 20,019.2 | 21,517 | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 0 / 1 / 2 | 0 / 0 / 0 | `['1']` ×3 | 899 / 898 / 902 | 20,022.8 / 20,019.5 / 20,018.4 | 21,503 | 1 / 210 | same |

(10-14l, 0.2.20: polls 965 / 965 / 966 Chrome, 898 / 901 / 902 Firefox; first key about 20.0 s after the Delete.) The report is void as a window measurement and is not read against G5's v19 criterion.

### Observation on the held tail (not a K3 clause)

Time from the last repeat keydown to the first `ready` state entry, same readings as 10-14m's "3.0–4.3 s busy tail" (`facts.txt`, `tailMs`): `start-hold` Chrome 1,851 / 1,847 ms, Firefox 1,487 / 1,483; `end-hold` Chrome 1,094 / 1,096, Firefox 771 / 802; table `cell-start-hold` Chrome 1,776 / 1,776, Firefox 1,483 / 1,471; the four table hold arms that still refuse (`before-table-hold`, `cell-hold`) 4,207 / 4,239 (Chrome) and 4,272 / 4,295 (Firefox). In the held probe's hold arms the page logged `beforeinputs` 258–259 (`start-hold`, `cell-start-hold`) and 255 (`end-hold`) per run against 13 / 8 on 0.2.20 (10-14l): the keydowns the old H2 cut now produce a `beforeinput` that the page holds and counts. The judged properties do not depend on this.

## K3b in detail (`k3b/`; facts in `k3b-facts.txt`, judge in `judge-k-output.txt`)

Burst at the document start (`burst-1s`: 1 press, then from 500 ms a keyup+keydown every 30 ms to 980 ms, keyup at 995 ms, every keydown `repeat: false`), after a real click on the first line and Home:

| | Firefox 157.0.1 | Chrome 151.0.7922.169 |
|---|---|---|
| keydowns / `beforeinput` | 18 / 18 | 18 / 18 |
| engine requests (`editorActionV2`) / responses | 1 / 1 | 1 / 1 |
| the response | `verified-boundary-noop`, `changed false`, `waitedMs 2252`, revision 0 → 0 | same, `waitedMs 2259` |
| 處理中 ends (`readyAgainMs`) | 2,256.2 ms (label 「⌫ 刪除 2256 ms」) | 2,262.1 ms (「⌫ 刪除 2262 ms」) |
| generations / revision / toasts | `['1']` / 0 → 0 / `[]` | `['1']` / 0 → 0 / `[]` |
| `limit` | null | null |
| verdict | PASS | PASS |

(10-14n, no fix: 18 requests and 40,589–40,617 ms; 10-14o no-host with the fix: 1 request, 2,260.1 / 2,259.4 ms.)

Page number (`page-number`, 18 real wheel steps: 14 × 700 px, 3 × 3,000 px, then −40,000):

| | Firefox (viewport 1850×994) | Chrome (1850×980) |
|---|---|---|
| text rect (left, top, w, h) / bottom | `[20, 960.5, 98.3, 20]` / 980.5 | `[20, 946.8, 98.3, 19]` / 965.8 |
| `#content` rect / bottom | `[8, 50, 1834, 936]` / 986 | `[8, 50, 1834, 922]` / 972 |
| (d) bottom ≤ bottom | PASS | PASS |
| (e) font, colour on background, contrast | 13 px, `rgb(34,34,34)` on `rgb(255,255,255)`, 15.91:1 | same |
| (f) steps | 18, never hidden, first 「第 1–2 頁，共 60 頁」, last 「第 1 頁，共 60 頁」; 17 distinct texts (the judge asks for at least 10) | same; 18 distinct |
| (g) bar rect / root bottom / text left | `[8, 954, 1834, 32]` = `#content`'s x and width; 986; 20 | `[8, 940, 1834, 32]`; 972; 20 |
| `elementAtCentre` / `display` | `page-status` / `flex` | same |
| page-issued engine requests during the wheel steps (`scrollLog`, `rq` < 900000) | 21 `paint`, 0 `pageRectangles`; the probe's own asks before and after answer `parts 60` | same: 21 `paint`, 0 `pageRectangles` |

The (d)–(g) numbers per browser equal 10-14o's K4 run on the template-only host (`../k4-host-css/`), now with 0.2.21 installed. Screenshots: `k3b/*-page-number-0-mid.png` (scrollTop 4,900) and `*-end.png`, `*-burst-1s-0-end.png`.

**Odd, not a clause:** in the Chrome `page-number` arm the host's file lock was refused (`host.lock` `{"state": "refused", "status": 423, "holder": {"owner": "admin", "type": "2"}}`) and the host notice bar 「你在另一個視窗或裝置開著這個檔案：這裡的存檔會另存副本。」 was shown, because that arm opened the same file right after the `burst-1s` arm's session closed (same pattern as the 10-14n multi-arm Chrome run; 10-14o's single-arm K4 run read lock `held`). The Firefox arms both read lock `held`. None of (d)–(g) reads the lock, and Chrome's geometry equals 10-14o's single-arm numbers. I did not rerun the arm alone.

## Cleanup

The held, table and restore-window probes upload `probe-held-refusal.odt`, and the 132-B probe `probe-hand-0212.odt`, to the admin root and delete neither. After the last step I deleted exactly those two (`cleanup.txt`: both `DELETE` → 204), through the probes' own `Instance` helper. Nothing else on the instance was touched: `probe-autosave-m1.odt`, `probe-autosave-m3.odt` and the owner's files (`手測-126-60頁.odt`, `m3-109 測試.odt`, `PMPC…`, `測試新增文件.odt`, `新增測試文件-chrome.odt`, …) are as listed before the run. The K3b probe folders were deleted by the probe itself.

## What was not checked, and what was not done

- The 132-B red is not diagnosed by any run: the reading of the cause above is from the page source only. I did not run 132-B on 0.2.20, on a no-host mirror, or with the 141 page swapped out, and I did not run any mutation of the judge.
- Whether the 132-B (a) red also shows on a real keyboard path (the probe's `repeat` flags come from the driver: CDP `autoRepeat`, WebDriver key repeat; the owner's KDE/Wayland/fcitx5 path was never measured, per 10-14n). The owner's hand test passed on 0.2.21; whether it included a held key inside text is unverified.
- The caret by any independent read; a rerun on a quiet desk; Orca or any screen-reader path; the host-segment arms of 128-B, 131-B, 121-B, 129-B, C2/P2 (only 132-B was in the task).
- No `make`, link, freeze, `--write`, package, `occ upgrade`, host change; no edit of any tool, judge, probe, check, `web/`, `editor-shell*/`, `sdk/` or `src/`. No `git push`.
- Files here: `k3a-held/`, `k3a-table/`, `k3a-restore-window/`, `k3b/`, `k3c-132b/` (each: `report.json`, `probe.out`, `started/ended-utc-*.txt`, `static-check.txt`; plus `judge-output.txt`, `facts.txt`, `timing.txt`, `hold-table.txt`, `read_hold-output.txt` where named above), `health-checks.txt`, `queue-log.txt`, `cleanup.txt`. `facts.txt`, `timing.txt`, `hold-table.txt`, `k3b-facts.txt` and `static-check.txt` are output of one-off reader scripts over the reports (session scratchpad, not kept), not of any tool in the tree.
