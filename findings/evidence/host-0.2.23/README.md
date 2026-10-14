# Host 0.2.23: the scroll page bubble's host criteria H1-H3, and 132-B and the boundary burst as guards (task 10-15a)

Task: `handoff/tasks/TASK-2026-10-15a-host-0.2.23-bubble-h1-h3-and-132b.md` (commit `934e1ec3`). Criteria: `specs/SPEC-M3-scroll-page-bubble.md` section 5 (H1-H3), pinned before any run; G1 and G2 are the task's guards. Mechanical runs of existing probes, read with existing judges unchanged, on host 0.2.23. Nothing here changes a tool, judge, probe, check or product file; no `make`, package, `occ upgrade`, host change or `--write`; no `git push`. Facts only: inferences are labelled as inferences, and anything I did not check is marked "unverified". Times are UTC (the desk's local time is +0800).

**Headline.** G1, G2 and H3 are green. **H1 and H2 were not run: `probe_bubble.py` cannot drive the host path and `judge_bubble.py` cannot read host reports and has no H2 clause** (what is missing, exactly, is under "H1 and H2: what is missing"). Neither is a red clause and neither is a green one; they are unmeasured. Under the spec's own "if never done" column both read "the host does not ship this version"; that conclusion stands until they are measured, whatever the owner's hand test said.

## Result in one table

| clause | measured on 0.2.23 | previous release (0.2.22, task 10-14r) | verdict |
|---|---|---|---|
| **H1** N1-N5 on the owner's path (Files -> 60-page fixture -> wheel, drag, keys) | **not run**: `probe_bubble.py` has no host mode and `judge_bubble.py` reads only `report-nohost-*.json` (see below) | n/a (the bubble is new in 0.2.23) | **NOT RUN (unverified)** |
| **H2** bubble rect inside desk rect inside `#content` rect; bubble does not intersect `#page-status` rect, both browsers | **not run**: no tool reads the bubble on the host, and `judge_bubble.py` has no clause for desk-in-`#content` or bubble-vs-`#page-status` (see below) | n/a | **NOT RUN (unverified)**; a by-eye look at two existing screenshots is under "Indicative, not a clause" |
| **H3** `git diff afbaf3c..HEAD -- templates/editor.php` contains no `scroll-bubble` | `grep -c scroll-bubble` = **0** (and `grep -ci bubble` = 0); the diff is the 0.2.21 `#page-status` CSS, +21 -1 lines, one commit (`187b36d`); 0.2.23's own commit `2ccf1a9` changes only `appinfo/info.xml` among the files git tracks | n/a | **PASS** |
| **G1** 132-B: `judge_132b.py --page ccb67a52...` reads `132-B PASS` | **`132-B PASS`, judge exit 0**: 12 of 12 holds PASS, both wash controls PASS (Chrome selection fills 5, Firefox 9) | `132-B PASS` | **PASS** |
| **G1 (a)** at most 2 deletes after release in 12/12 holds | **1, 2, 2, 1, 2, 2** (Chrome) and **1, 2, 1, 2, 2, 2** (Firefox): max 2, 12 of 12 within the limit | 2, 2, 2, 2, 1, 2 / 1, 2, 1, 2, 2, 2 | **PASS** |
| **G2** `burst-1s` on the 60-page fixture, both browsers: 1 engine request | Chrome **1** request / 1 response; Firefox **1** / 1 (`verified-boundary-noop`, 18 keydowns, 18 `beforeinput` each) | 1 / 1 | **PASS** (both) |
| **G2** ready < 2.5 s | Chrome ready at **2,265.8 ms**; Firefox **2,256.5 ms** (the label reads 「⌫ 刪除 2266 ms」 / 「⌫ 刪除 2256 ms」) | 2,260.9 / 2,257.1 | **PASS** (both) |

No red clause in the clauses that ran. Extra, not clauses of the brief (the existing judge printed them): `judge_k.py` `VERDICT PASS` (K2 (a)-(c) on `burst-1s`, and the K4 status-bar clauses (d)-(g) on the `page-number` arm both browsers ran with it), and its `--red-check` self-test `K2 red=True K4 red=True -> self-test PASS`.

## Static (every report)

`static-check.txt` in each step directory is the output of a one-off script (`wrappers/static_check.py`, copied here for the record; not a tree tool) over each report's `static` and, where the probe records it, `staticAfter`. It exits 1 on any mismatch of host version, buildId or page. Every `static` (and the 132-B report's `staticAfter`) reads:

- `hostVersion` 0.2.23, `hostCommit` `2ccf1a9`, `hostDirty` `[]`;
- `buildId` `c3c22d9294de068a`;
- `servedPage` = `distPage` = `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e`;
- `servedSession` `f47c80ec955397c44d7638da63ed6837a3dea47125f6e279192298c20ed62ba9`;
- `shellBundle` exit 0, manifest `e2/editor-shell-v2-bundle-v72.json`, sha256 `4dc105075659...` (the v72 freeze), `problems` `[]`.

The 132-B report's `staticAfter` (taken at 16:45) equals its `static` in every field, including `shellBundle` exit 0: the source tree did not move during the 34-minute run (10-14r's did, see its README). The two `probe_10_14o.py` reports record `static` only. Host repo `~/Projects/Nextcloud_Apps/litecore`: HEAD `2ccf1a9`, `appinfo/info.xml` `<version>0.2.23`, `git status --short` empty at H3 (16:10Z) and again after the last step (about 16:50Z). `servedPage` is what `ui.static_facts` reads from the host's `engine/MANIFEST.json` (`files["e2-editor-app.js"].sha256`), not a fetch over HTTP. Unverified by me: that the HTTP bytes decode to that page under gzip and under zstd (the brief states it; `MANIFEST.json` lists `gzSha256` `942fd1f9...` and `zstSha256` `58a597ac...`, which I did not fetch or compare).

## H3 in detail (`h3/`)

`h3/h3-result.txt` and `h3/editor.php.diff`. Command as the brief gives it: `git -C ~/Projects/Nextcloud_Apps/litecore diff afbaf3c..HEAD -- templates/editor.php`. The diff (exit 0) is the 0.2.21 host change: a `#litecore-editor-root #page-status` rule block (Collabora-like status bar, with the finding-143 comment), `#litecore-editor-root #page-status[hidden] { display: none; }`, and the root's inline style `height: calc(100vh - 50px)` -> `height: 100%`. `grep -c 'scroll-bubble'` over it prints 0; the looser `grep -ci 'bubble'` also prints 0. `git log afbaf3c..HEAD -- templates/editor.php` is the one commit `187b36d` (0.2.21). Per the spec the 0.2.21 CSS for `#page-status` is expected there. H3 is a git read and starts no browser; it ran at 16:10:59Z, 19 s before the first health block (the KWallet property read by hand a few minutes earlier, before this step, read `b false`, `pgrep -c chrome` 33, `pgrep -c firefox` 1; that hand read was not written to a file).

## G1 in detail (`g1-132b/`)

Command (the 10-14r and 10-14p command, from the repo root): `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/host-0.2.23/g1-132b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (16:11:19-16:45:09, exit 0). Judge: `python3 findings/evidence/132/judge_132b.py --page ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e findings/evidence/host-0.2.23/g1-132b/report.json` (exit 0). Reader: `python3 findings/evidence/132/read_hold.py .../report.json` (exit 0). `judge-output.txt` (its first line is the `$ ...` command line and the trailing `exit 0` was appended by my wrapper; the judge's own last line is `132-B PASS`):

```
chrome hold-high round 0|1|2: PASS     chrome hold-low round 0|1|2: PASS
firefox hold-high round 0|1|2: PASS    firefox hold-low round 0|1|2: PASS
chrome wash-control: selection fills [5]  PASS
firefox wash-control: selection fills [9]  PASS
132-B PASS
```

(The file lists the twelve holds as twelve lines `<browser> hold-<arm> round <n>: PASS`; the block above is a compaction.) Per-hold numbers (`hold-table.txt`, an inline one-off parse over the repo reader's `read_hold-output.txt`, not kept as a file), beside 0.2.22's (`../host-0.2.22/h1/README.md`):

| | 0.2.23 Chrome (6 holds) | 0.2.23 Firefox (6 holds) | 0.2.22 Chrome / Firefox |
|---|---|---|---|
| keydowns / flagged repeats | 52 / 51 | 52 / 51 | 52 / 51 |
| deleted per hold | 25 x6 | 26 x6 | 25, 25, 25, 25, 25, 26 / 26 x6 |
| `beforeinput` events | = deleted (25 x6), `otherLatency` `[]` | = deleted (26 x6), `[]` | = deleted |
| (a) deletes after release (limit <= 2) | **1, 2, 2, 1, 2, 2** | **1, 2, 1, 2, 2, 2** | 2, 2, 2, 2, 1, 2 / 1, 2, 1, 2, 2, 2 |
| last delete after release (ms) | 61.5-95.1 | 61.6-81.9 | 65.3-115.5 / 59.5-89.5 |
| (b) shown / done at release (needs shown >= done - 2) | 22/24, 22/23, 22/23, 22/24, 22/23, 22/23 -> pass | 23/25, 23/24, 23/25, 23/24 x3 -> pass | 22/23-22/24 / 23/24-23/25 |
| caret band fresh after release (ms) | 73.3-108.8 | 78.2-109.3 | 83.2-136.9 / 75.4-111.6 |
| (d) washes in hold | 0 x6 | 0 x6 | 0 / 0 |
| (e) `persistent.differing` | 0 x6 | 0 x6 | 0 / 0 |
| characters left in the paragraph after the hold (`leftAfterHold`) | 27 x6 | 26 x6 | 27 x5, 26 x1 / 26 x6 |
| median gap between deletes (ms) | 65.7-66.2 | 66.5-67.4 | 65.7-66.4 / 66.5-67.1 |
| single presses: lag (ms), 24 presses per browser | 43.9-47.7 | 45.7-51.1 | 44.3-47.3 / 45.6-53.0 |
| oldest press's wait, `lag` first -> max (ms) | 45.6-47.1 -> 137.1-153.2 | 47.3-50.1 -> 131.1-136.6 | 44.2-45.8 -> 138.5-143.4 / 47.1-48.9 -> 131.2-136.3 |

Reading (facts): (a) is inside the limit in all twelve holds, the key came up and the editor kept deleting for at most 95.1 ms (Chrome) and 81.9 ms (Firefox), 1-2 more characters; (c), `beforeinputs == deleted`, holds in all twelve (0.2.21's counted 102 against 52, per 10-14r). The numbers sit in the same ranges as 0.2.22's. The probe ran unchanged: `report.json` carries `deskRepeat` `{delay 500, repeat-interval 30, repeat true}` and `options` `holdMs 2000, holdDelayMs 500, holdIntervalMs 30, holdRounds 3`, the same defaults as the earlier runs; `probe.out` ends `probe exit 0`. Chrome/151.0.7922.169 and Firefox 157.0.1. (a) sits at the limit of 2 in 8 of the 12 holds (as 0.2.18 and 0.2.22 did); I did not rerun on a quiet desk, so whether a slower desk could push a hold over is unverified. The 1-minute load was 2.16 before the run and 1.76 after it, and the owner's browsers were running.

## G2 in detail (`g2-burst1s/`)

Command: `python3 findings/evidence/host-0.2.21/probe_10_14o.py --out findings/evidence/host-0.2.23/g2-burst1s --browser <firefox|chrome> --doc long60 --arms burst-1s,page-number --mode host`, Firefox 16:46:11-16:47:25, Chrome 16:47:26-16:48:20, both exit 0 (`probe-firefox.out`, `probe-chrome.out` end `probe exit 0`). The brief names `burst-1s`; I ran 10-14r's arm pair (`burst-1s` then `page-number`, one process per browser, each arm a fresh open of the 60-page fixture `probe-10-14n-long60.odt`, 5,149 bytes, in a folder the probe creates and deletes: `probe-10-14n-20261014T164611` and `...T164726`, MKCOL 201, PUT 201, `deletedFolder` 204 in both reports). The `page-number` arm is extra to the brief; it is the same probe's default second arm and it guards the 0.2.21 status bar. Judge: `python3 -I findings/evidence/host-0.2.21/judge_k.py --k2 .../g2-burst1s --k4 .../g2-burst1s` (exit 0, `VERDICT PASS`), self-test `judge_k.py --red-check` (`self-test PASS`).

Burst at the document start (`burst-1s`: 1 press, then from 500 ms a keyup+keydown every 30 ms to 980 ms, keyup at 995 ms, every keydown `repeat: false`, after a real click on the first line and Home):

| | Firefox 157.0.1 | Chrome 151.0.7922.169 |
|---|---|---|
| keydowns / `beforeinput` | 18 / 18 | 18 / 18 |
| engine requests (`editorActionV2`) / responses | 1 / 1 | 1 / 1 |
| the response | `delete-backward`, `verified-boundary-noop`, `changed false`, `waitedMs 2253`, revision 0 -> 0 | same, `waitedMs 2260` |
| ready again (`readyAgainMs`) | 2,256.5 ms | 2,265.8 ms |
| generations / revision / toasts / `limit` | `['1']` / 0 -> 0 / `[]` / null | same |
| verdict | PASS | PASS |

(0.2.22: 1 request, 2,257.1 / 2,260.9 ms; 0.2.21: 2,256.2 / 2,262.1 ms.)

`page-number` (extra; the 18 real wheel steps, 14 x 700 px, 3 x 3,000 px, then -40,000), the status-bar clauses of `judge_k.py`: (d) text bottom <= `#content` bottom: Chrome 965.8 <= 972, Firefox 980.5 <= 986, PASS; (e) 13 px, `rgb(34, 34, 34)` on white, contrast 15.91, PASS; (f) 18 steps, never hidden, 18 distinct texts in Chrome and 17 in Firefox, PASS; (g) bar rect `[8, 940, 1834, 32]` in Chrome (root bottom 972) and `[8, 954, 1834, 32]` in Firefox (986), `#content` `[8, 50, 1834, 922 / 936]`, text left 20, PASS. These equal the 0.2.22 numbers to the pixel. In both browsers the scroll log holds 21 `paint` requests and 0 other page-issued requests (rq id < 900000) over the 18 steps; the probe's own `pageRectangles` asks answer `parts 60` at open and after the scroll. None of the probe's fields reads the bubble (`#scroll-bubble`), so this arm says nothing about H1 or H2 by itself.

**Odd, not a clause (the same as on 0.2.21 and 0.2.22):** in the Chrome `page-number` arm the host's file lock was refused (`host.lock` `{"state": "refused", "status": 423, "holder": {"owner": "admin", "type": "2"}}`) and the host notice bar 「你在另一個視窗或裝置開著這個檔案：這裡的存檔會另存副本。」 was shown, because that arm reopened the same file right after the `burst-1s` arm's session closed. The Firefox arms and Chrome's `burst-1s` read lock `held`. None of the clauses reads the lock. I did not rerun the arm alone.

## H1 and H2: what is missing

The brief: use `findings/evidence/scroll-page-bubble/probe_bubble.py` if it can drive the host path; if it cannot, record exactly what is missing, do not edit it, and for a probe change stop and report. Read from the sources (commit `82ee51fc`, unchanged since; `git status` shows no modification under `findings/evidence/scroll-page-bubble/`):

1. **`probe_bubble.py` has no host path.** `main()` has no `--mode` option. Every run goes through `run_arm`, which opens a document only by the no-host route: `pp.build_mirror(DIST, ...)` plus `web/serve.py` on 127.0.0.1, `smoke_navigate(nohost["url"])`, then `pp.OPEN_FILE` with `./fixture.odt` (lines 322-331, 408-419). It has no `login(...)`, no `open_from_files(...)`, and no MKCOL/PUT/DELETE of a probe folder; those are in `probe_10_14o.py`'s `run_arm` host branch and `main()`, which `probe_bubble.py` imports as `base` but does not call. Its report is hard-coded `"mode": "nohost"` and `report-nohost-{browser}-{doc}.json` (lines 323, 402, 405), and the page pin lives under `report["nohost"]` (`servedPage` from the mirror at the start, `servedPageAtEnd` at the end; lines 416-419, 433). The arms themselves (`arm_wheel`, `arm_reduce`, `arm_drag`, `arm_keys`, `arm_short`) act on an open `session` and do not use the mirror, so a host mode is a small change, but it is a change to the probe, which the brief reserves for a stop-and-report.
2. **`judge_bubble.py` cannot read host reports.** `judge_dir` globs `report-nohost-*.json` (lines 294, 368) and `judge_report` reads the page pin from `report["nohost"]["servedPage"]` / `["servedPageAtEnd"]` (lines 265-267). Pointed at a directory of host reports (`probe_10_14o.py --mode host` writes `report-host-<browser>-<doc>.json`, with the pin in `static.servedPage`), it prints `no report -> FAIL`, `RED`, exit 1: `h1-h2/judge-on-host-report-dir.txt` (a measurement of the glob only; it is not a verdict on any host run).
3. **`judge_bubble.py` has no H2 clause.** Its criteria are `N1, N2, N3, N4, N5, N6-plain, N6-reduce, D1, K1, Z1` (`CRITERIA`, line 38). The only geometry it checks is N2's `inside(bubble, desk)` (bubble rect inside the desk rect, line 83) and the bubble's distance from the desk's right edge. Nothing reads `#content`'s rect or `#page-status`'s rect, and nothing tests that the bubble and `#page-status` do not intersect; `grep -n 'content\|H2\|page-status\|intersect'` over the judge finds nothing. The probe's fields that a future H2 clause could read: per wheel step `deskBox` and `bubble.rect` (one decimal), and at open `content.rect` and the status bar's `rect` (rounded to integers, read before the bubble element exists, since it is created on the first scroll).
4. The self-test the brief asks for was run (below) on the existing no-host report directories, because no host report directory for this judge exists.

**`judge_bubble.py --self-test`** (`h1-h2/judge-self-test.txt`), the documented invocation with the three no-host report directories and the pinned page: `python3 -I judge_bubble.py --self-test --page ccb67a52 --dir n-nohost-v20/firefox --dir n-nohost-v20/chrome --dir n-nohost-v20/firefox-css-bar` (run from `findings/evidence/scroll-page-bubble/`), exit 0, `selfTest: ok (red where it must be)`: K4's bubble-less reports N1/N2/N4 FAIL in both browsers; every mutated copy red on its named clause (Chrome rect +40 FAIL, Firefox rect +40 INSTRUMENT_RED because that main run has no readable thumb, over-the-rail FAIL, whole-text FAIL, never-hides FAIL, a11y-spoke FAIL, keys-no-scroll FAIL, Z1-shown FAIL, the still drag NOT_ESTABLISHED), no `NOT RED WHERE IT MUST BE` line. I did not run `judge_bubble.py` on any real verdict path this task (there is no host report to give it).

**What a follow-up task would need (a proposal, not done):** `probe_bubble.py --mode host` reusing `probe_10_14o.py`'s host branch (login, `open_from_files`, the folder lifecycle, the `static` block), an end-of-run re-read of the served page, per-step `#content` and `#page-status` rects at full precision in `step_read`, and a report name and page-pin location the judge reads; `judge_bubble.py` accepting host reports and gaining H2 clauses with their own red cases (spec H2's red: bubble rect bottom beyond `#content`'s bottom) in its self-test. The Z1 arm uses `dist/blank.odt`, which a host mode would have to replace or leave out (H1 asks for N1-N5 only).

## Indicative, not a clause: the bubble in two existing host screenshots

The `page-number` arm's `*-page-number-0-mid.png` screenshots were taken 0.6 s after a wheel step whose status bar reads 「第 4–5 頁，共 60 頁」, on 0.2.23. I looked at them with the image reader. By eye, with no measurement and no judge: both browsers show a dark bubble reading 「第 4–5 頁」 to the right of the document column and left of the scrollbar thumb, vertically level with the thumb, between the toolbar and the status bar, not touching the status bar's text at the bottom-left (Chrome: bubble about x 1748-1821, y 253-280 of 1850 x 980, thumb at y 258-274, status bar from y 940; Firefox: about x 1751-1825, y 222-250 of 1850 x 994, status bar from y 954; every number is a by-eye reading, +-several px). This shows the bubble is present on the host and where it sits; it does not establish H1 (N1-N5 over 18 steps, the drag, the keys) or H2 (rects) and must not be read as doing so. Unverified: everything the judge would count (text on every step, hide timing, live regions, requests during the bubble's own scrolls).

## Desk

`health-checks.txt` holds a block before each step and one after the last of each browser run: KWallet `Locked` (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`), a default-flag headless Chrome check (`timeout 30 google-chrome --headless=new --user-data-dir=<tmp> --dump-dom https://litecore.ddev.site:8443/login`, `Nextcloud` x328 every time), the process counts, the load, and "ours running" (`wrappers/health.sh`, which would have stopped the queue on `b true`, a failed Chrome check or anything of ours running; none occurred).

| time (UTC) | before step | KWallet | `pgrep -c chrome` | Chrome browser processes | `pgrep -c firefox` | load (1/5/15) | ours running |
|---|---|---|---|---|---|---|---|
| 16:11:18 | G1 (132-B) | b false | 35 | 31 | 1 | 2.16 1.72 1.39 | 0 |
| 16:45:09 | after G1 | b false | 35 | 31 | 1 | 1.76 1.69 1.66 | 0 |
| 16:46:10 | G2 Firefox | b false | 35 | 31 | 1 | 1.73 1.68 1.65 | 0 |
| 16:47:25 | G2 Chrome | b false | 37 | 33 | 1 | 4.10 2.44 1.92 | 0 |
| 16:48:20 | after G2 | b false | 33 | 29 | 1 | 4.17 2.78 2.07 | 0 |
| 16:48:40 | H1/H2 judge-readability read | b false | 35 | 31 | 1 | 4.41 2.92 2.13 | 0 |

- **The desk was not clean.** The owner's Chrome (with the claude-in-chrome extension host) and snap Firefox were running throughout; I started, stopped and touched neither. Our headless sessions are `--headless=new` Chrome and a WebDriver Firefox. The Chrome browser-process count moved between 29 and 33 across steps with nothing of ours running at any step start; I did not find the source of the changes (the owner's browser, unverified).
- `ours running` is the count of `pgrep -af 'probe_|judge_|check_m3|run_e2_c|run_merge|run_v20'` lines excluding `pgrep`, the wrapper itself and the queue scripts, read after the Chrome check. One browser job ran at a time. The `judge_bubble.py` self-test ran at 16:45:47, between G1's end and G2's first health block, while no probe was running; the G2 probe's per-arm preflight recorded `oursRunning` `[]` in every run.
- The owner's `手測-126-60頁.odt` was last modified 16:04:30Z in `admin-root-before.txt` (taken before my first step) and has the same time in the listing taken after cleanup, so I did not touch it and it did not change during my runs; whether the owner used the instance otherwise is unverified. The H1/H2 judge-readability row is a Chrome check and counts, not a browser job of ours (no probe ran).

## Commands and exits

One job at a time, in this order, from the repo root; `$K` is `findings/evidence/host-0.2.23`, `$PAGE` is `ccb67a52a3fe4b73139467c67a28522b9a87040921cb1da36448e5ad8dfdb43e`. The wrapper scripts are in `wrappers/` (scratchpad copies kept for the record; they are one-off glue, not tools of the tree: `health.sh`, `static_check.py`, `admin_root.py`, `queue_g1.sh`, `queue_g2.sh`, `g2_facts.py`; `hold-table.txt` was produced by an inline parse not kept as a file).

| step | command | window | exit |
|---|---|---|---|
| H3 | `git -C ~/Projects/Nextcloud_Apps/litecore diff afbaf3c..HEAD -- templates/editor.php` and `grep -c scroll-bubble` over it | 16:10:59 | 0 (diff), `0` matches |
| G1 | `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out $K/g1-132b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` | 16:11:19-16:45:09 | 0 |
| G1 judge | `python3 findings/evidence/132/judge_132b.py --page $PAGE $K/g1-132b/report.json` | | **0**, `132-B PASS` |
| G1 reader | `python3 findings/evidence/132/read_hold.py $K/g1-132b/report.json` | | 0 |
| G2 Firefox | `python3 findings/evidence/host-0.2.21/probe_10_14o.py --out $K/g2-burst1s --browser firefox --doc long60 --arms burst-1s,page-number --mode host` | 16:46:11-16:47:25 | 0 |
| G2 Chrome | same with `--browser chrome` | 16:47:26-16:48:20 | 0 |
| G2 judge | `python3 -I findings/evidence/host-0.2.21/judge_k.py --k2 $K/g2-burst1s --k4 $K/g2-burst1s` | | **0**, `VERDICT PASS` |
| G2 judge self-test | `python3 -I findings/evidence/host-0.2.21/judge_k.py --red-check` | | 0, `K2 red=True K4 red=True -> self-test PASS` |
| H1/H2 judge self-test | `python3 -I judge_bubble.py --self-test --page ccb67a52 --dir n-nohost-v20/firefox --dir n-nohost-v20/chrome --dir n-nohost-v20/firefox-css-bar` (cwd `findings/evidence/scroll-page-bubble/`) | 16:45:47 (no probe running) | 0, `selfTest: ok (red where it must be)` |
| H1/H2 judge on a host-report directory | `python3 -I judge_bubble.py --page ccb67a52 --dir ../host-0.2.23/g2-burst1s` | 16:48:41 (after the health block above) | 1, `no report -> FAIL` (the glob, see above) |
| H1, H2 | not run | | n/a |

## Cleanup

The 132-B probe uploads `probe-hand-0212.odt` to the admin root and deletes it never; the G2 probe deletes its own folders (`deletedFolder` 204 in both reports). `admin-root-before.txt` is a `PROPFIND` depth-1 listing taken before the first step (`wrappers/admin_root.py`, through the probes' own `Instance` helper); after G2 the listing differed from it by exactly one line, `probe-hand-0212.odt` (16:44:53Z, inside my G1 window), which I deleted (`DELETE` -> 204). `cleanup.txt` holds the listing before and after that delete; the listing after equals `admin-root-before.txt` except the root's own timestamp. `probe-autosave-m1.odt` and `probe-autosave-m3.odt` predate this task (12 Oct) and were not touched; nothing else on the instance was touched, and the owner's files keep their modification times.

## What was not checked, and what was not done

- **H1 and H2 were not run** (above). The bubble itself was not read by any instrument on the host path: no state, rect, timing or `aria-*` value of `#scroll-bubble` on 0.2.23 is measured here. The by-eye screenshot reading is not a measurement.
- N1-N6, D1, K1 and Z1 on the host, including whether the host's bar (CSS `scrollbar-color`) keeps the thumb readable for the pixel reader on the owner's desktop: unverified here (the no-host run established them on the `dist/` mirror, page `ccb67a52...`, `findings/evidence/scroll-page-bubble/n-nohost-v20/`).
- 132-B on a real keyboard path (the probe's `repeat` flags come from the driver: CDP `autoRepeat`, WebDriver key repeat; the owner's desktop path was never measured, per 10-14n); the caret by any independent read; a rerun on a quiet desk; Orca or any screen-reader path; the host-segment arms of 128-B, 131-B, 121-B, 129-B, C2/P2, and the K3a held/table/restore-window probes (not in this brief).
- That `servedPage` matches under gzip and zstd over HTTP; that no host file differs from `engine/MANIFEST.json` (I read the manifest, not every file).
- No `make`, link, freeze, `--write`, package, `occ upgrade`, host change; no edit of any tool, judge, probe, check, `web/`, `editor-shell*/`, `sdk/` or `src/`. No `git push`. The file `test-e2-c-static-after-freeze-v72.txt` in this directory is not mine.
- Files here: `h3/` (`h3-result.txt`, `editor.php.diff`), `g1-132b/` (`report.json`, `probe.out`, `queue-log.txt`, `judge-output.txt`, `read_hold-output.txt`, `hold-table.txt`, `static-check.txt`, `started/ended-utc-G1.txt`, two settled screenshots), `g2-burst1s/` (two reports, `probe-<browser>.out`, `queue-log.txt`, `facts.txt`, `judge-k-output.txt`, `judge-k-red-check-output.txt`, `static-check.txt`, `started/ended-utc-G2-<browser>.txt`, six screenshots), `h1-h2/` (`judge-self-test.txt`, `judge-on-host-report-dir.txt`), `health-checks.txt`, `admin-root-before.txt`, `cleanup.txt`, `wrappers/`. `facts.txt`, `hold-table.txt` and `static-check.txt` are output of one-off readers over the reports, not of any tool in the tree.
