# Finding 136 page — the "must not break" set on the final bytes, run 2

Task: `handoff/tasks/TASK-2026-10-13e-136-guard-chain-r2.md`, which is run 2 of `handoff/tasks/TASK-2026-10-13d-136-guard-chain.md` (SPEC-M3-held-key §16; ruling-3 conditions 5–6). Run 1 is in `../guard/` and stays in the tree as "Chrome not measured (environment)": every Chrome half of run 1 died at its first `Page.navigate` because the KDE wallet `kdewallet` was locked after the owner's reboot (`../guard/README.md`, last section; `../guard/chrome-wallet-diagnosis.txt`). Mechanical runs of existing instruments and judges on one page; nothing here changes a check, a judge or an instrument. Facts only; anything not checked is marked unverified. All times UTC.

**Run 2 is the verdict of record for every step** (the task fixed this before the run): each judge reads one report holding both browsers. Run 1's Firefox halves are an extra sample, reported beside run 2's Firefox halves; they do not overrule run 2 (if run 2's Firefox half of a cell is red and run 1's is green, the cell is red).

## Conditions (common)

- Page under test: `wasm_sdk_probe/dist/e2-editor-app.js` sha256 `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678` (= `wasm_sdk_probe/web/e2-editor-app.js`; `sha256sum` of both checked at 2026-10-13T05:38:18Z before G0).
- Host `litecore` 0.2.18 (`appinfo/info.xml`, uncommitted on purpose; host HEAD `f5b34f0`, `git status --short` = ` M appinfo/info.xml`), engine package buildId `d6d04880f56e31da` (`engine/MANIFEST.json`: `source.page` = the page above, `source.profile` e2-editor-v19, `packagedAt` 2026-10-13T02:25:55+00:00). Every probe report's `static` and `staticAfter` carry `servedPage` = the page above, `buildId` `d6d04880f56e31da`, `hostVersion` `0.2.18` (checked per step below).
- Pins (verified with `grep`, no pin commit in this run): `FINAL_PAGE_SHA256` in `wasm_sdk_probe/tools/probe_129_m4_wasm.py` line 70 = `b24d754a…` (run 1 commit `1b5efdbb`); `PAGE` in `findings/evidence/c-prime/c2/judge_c2.py` line 53 and `findings/evidence/typing-latency/judge_p2.py` line 41 = `b24d754a…` (run 1 commit `a0ed713f`).
- Chrome 151.0.7922.169, Firefox 157.0.1, one browser at a time, one job at a time.
- Desk notes (2026-10-13T05:38Z, before G0): `pgrep -c chrome` = 1, which is `/opt/marktext/chrome_crashpad_handler` (the owner's MarkText editor, pid 102013, not a Chrome browser); Chrome browsers by `pgrep -fc '/opt/google/chrome/chrome( |$)'` = 0; `pgrep -c firefox` = 1, the owner's own snap Firefox (pid 101463), left alone for the whole chain. `pgrep -af "probe_|check_m3|run_e2_c"` showed only its own `bash -c` wrapper line. Each step directory records its own desk at start.
- Not done by me, by instruction: no `make`, no edit of `wasm_sdk_probe/web` or `dist`, nothing in `~/Projects/Nextcloud_Apps`, no `--write` mode, no `git push`, no probe/judge/launcher edit.
- `static.shellBundle` in the probe reports is the same "shell generation v65 not frozen for this page" record as in run 1; the probe records it and does not stop on it. Not investigated.

## Precondition and health checks (new in run 2)

`health-checks.txt` holds every check with a UTC time: the wallet (`busctl --user get-property org.freedesktop.secrets /org/freedesktop/secrets/collection/kdewallet org.freedesktop.Secret.Collection Locked`, must print `b false`) and the default-flag Chrome check (`timeout 30 google-chrome --headless=new --user-data-dir="$(mktemp -d)" --dump-dom https://litecore.ddev.site:8443/login`, no `--password-store`; must exit 0 and print a DOM containing `Nextcloud`). Both ran before G0 and again before every browser step; a failure would have stopped the whole chain. (The helper script lives in the session scratchpad, not in the tree; it writes one line per check.)

## G0 — 132-B on the 136 page: PASS (exit 0) — Chrome 6/6 and Firefox 6/6 holds, both wash controls

`132-b/` (own README). 2026-10-13T05:38:49–06:13:11Z. Command: `probe_hand_test_0212.py --out findings/evidence/136/guard-r2/132-b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (exit 0). `judge_132b.py --page b24d754a…` **exit 0**, last line `132-B PASS` (`chrome|firefox hold-high|hold-low round 0|1|2: PASS` ×12, wash-control fills Chrome 5 / Firefox 9, both PASS); `read_hold.py` exit 0. Read: deleted per hold 25 (Chrome) / 26 (Firefox), 1–2 deletes after release (last at 58.4–115.8 ms), caret band fresh 73.0–130.4 ms after release, 0 washes, `persistent.differing` 0. Run 1's Firefox half (same arms): 6/6 holds PASS, wash fills 10, last delete after release 70.6–105.3 ms, band fresh 89.6–123.4 ms — same verdict as run 2's Firefox half. Run 1's Chrome half was not measured.

## G1 — 131-B and 128-B (one probe run, then the host-segment arms once more): 131-B PASS (judge exit 0); 128-B single presses PASS in both browsers; host-segment cell NOT_JUDGED in the first run in both browsers, PASS in both on the one allowed rerun; red control red in both runs

Directory `131b-128b/`. Command: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/136/guard-r2/131b-128b --browsers chrome,firefox --arms high,low,rapid20,hostseg,hostseg-red --rapid-rounds 6` (exit 0, `probe.out` ends `probe exit 0`). Chrome 2026-10-13T06:14:36–06:20:20Z, Firefox 06:20:20–06:26:14Z. Desk at the start (`started-utc.txt`): `pgrep -c chrome` 0 and `pgrep -c firefox` 0 (MarkText and the owner's Firefox were no longer running by now; I did not touch either), load 0.27 0.48 0.52. Health check before it: `health-checks.txt` `[before-G1]` OK. `report.json` → `static` and `staticAfter`: `servedPage` = `distPage` = `b24d754a…`, buildId `d6d04880f56e31da`, host 0.2.18.

| Clause | Read with | Chrome | Firefox | Verdict |
|---|---|---|---|---|
| 131-B: 6 rapid20 bursts, each `deleted 20`, `refused 0`, `other []` | `judge_131b.py report.json --page b24d754a…` → `judge_131b-output.txt`, **exit 0**, last line `131-B PASS []` | 6/6 bursts `deleted 20 refused 0 other []` | 6/6 | PASS |
| 131-B: `persistent.differing == 0` in the four high/low arms | same | high 0, low 0 | high 0, low 0 | PASS |
| 128-B: every single press `staleAfterCaretMs` ≤ 40 ms | `read_128b_cells.py report.json` → `read_128b-output.txt` (exit 0) | high 14.3 16.8 17.9 17.5; low 20.6 18.7 21.0 16.7 | high 24.7 20.8 18.2 21.0; low 21.5 27.0 21.2 26.0 | PASS (max 27.0) |
| 128-B: host-segment cell holds | `runs[].hostseg.judged` | first run `NOT_JUDGED` (`2 PUTs, 1 keys, save saved`); rerun **PASS** | first run `NOT_JUDGED` (same string); rerun **PASS** | not judged in the first run; PASS in the rerun (both browsers) |
| 128-B: host-segment red control (`hostseg-red`) is red | `runs[].hostsegRed.judged` | `FAIL` both runs (band fresh 2748.0 / 2772.1 ms after the key, `heldPaints` 1) | `FAIL` both runs (2753.1 / 2771.4 ms, `heldPaints` 1) | red, as required |

- The rapid keys printed by the reader (Chrome high 23.3 – 81.2 15.6, low 76.0 – 82.6 10.8; Firefox high 78.3 – 78.3 89.7, low 80.0 – 81.1 79.6; `–` = the caret did not move inside that key's own window) are not part of the task's criteria; I did not judge them.
- **First run, host-segment cell `NOT_JUDGED` in both browsers** — the state the 132, 134 and run-1 chains also hit. `runs[].hostseg.put.puts` has two PUTs per browser: the first held and answered normally (Chrome held 317778.5, sent 320778.8, answered 320839.5 ms; Firefox held 322348.8, sent 325349.3, answered 325406.2 ms); a second PUT held 1.13 s after the first was answered (Chrome 321968.0, Firefox 326535.3 ms) and was still outstanding when the arm ended (`out: 1`). Cause unverified.
- **Rerun, as the task's one exception allows** — only the two arms once, instrument and verdict function unchanged: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/136/guard-r2/131b-128b-hostseg-rerun --browsers chrome,firefox --arms hostseg,hostseg-red` (exit 0; Chrome 06:26:39–06:27:07Z, Firefox 06:27:07–06:27:41Z; health check `[before-G1-hostseg-rerun]` OK; served page, buildId, host version as above). One PUT per arm this time (`hostseg.put.puts` has one entry, `out: 0`).

| | Chrome | Firefox |
|---|---|---|
| host-segment cell (`runs[].hostseg.judged`) | **PASS**: PUT held 3034.8 ms, key at 3340.8 ms (inside the hold), caret moved 22.9 ms after the key, caret band fresh 38.6 ms after the key, PUT answered 6103.2 ms, `heldPaints` 0 | **PASS**: held 3199.4, key 3521.1, caret moved 25.8 ms, band fresh 40.1 ms, answered 6265.7 ms, `heldPaints` 0 |
| red control (`runs[].hostsegRed.judged`) | **FAIL**: band fresh 2772.1 ms after the key, `heldPaints` 1 | **FAIL**: 2771.4 ms, `heldPaints` 1 |

`read_128b-output.txt` in the rerun directory is empty (that reader prints the high/low arms only). Each host-segment cell has been sampled twice; the first sample is not a PASS.

Run 1 Firefox half for comparison (`../guard/README.md`, G1): 131-B bursts 6/6, persistent 0/0, single presses max 27.0 ms, host-segment cell NOT_JUDGED then PASS on its rerun (caret band fresh 36.8 ms), red control red (2754.9 / 2805.8 ms) — the same pattern and verdicts as run 2's Firefox half. Chrome had no sample in run 1.

Output files: `131b-128b/` — `probe.out`, `report.json`, four screenshots, `judge_131b-output.txt`, `read_128b-output.txt`, `started-utc.txt`, `ended-utc.txt`; `131b-128b-hostseg-rerun/` — `probe.out`, `report.json`, `read_128b-output.txt` (empty), `started-utc.txt`, `ended-utc.txt`.

## G2 — 121-B (selection, then Backspace / Delete): PASS in all four cells (Chrome and Firefox, both keys)

Files: `../../121/0.2.18-136-r2-binding.txt` (before 2026-10-13T06:28:19Z, after 06:29:40Z; both lines carry the page sha256 `b24d754a…`, all four exits 0), `../../121/0.2.18-136-r2-<browser>-<key>.json` and `.stderr` (all four `.stderr` files are empty). Command per cell: `python3 findings/evidence/121/select_delete_probe.py <browser> <Key>` (standalone page built from `dist/`, `boundaries.odt`, a drag inside "M01 plain alpha", one real key; no host involved), run sequentially from a small wrapper script (session scratchpad, not kept) that wrote the binding file and ran the wallet/Chrome health check before each of the four cells (`health-checks.txt`, `[G2-<browser>-<key>]`, all OK; the wrapper would have stopped the chain on a failure). Desk at the start: `g2-desk-at-start.txt` (`pgrep -c chrome` 0, Chrome browsers 0, `pgrep -c firefox` 0, load 0.43 0.40 0.43). Criterion (SPEC-M3-autosave §9.13): shape `range-single` before the key, after the key 「刪除選取 N ms」, `ready`, generation 1 → 1, revision 0 → 1, no toast, first paragraph `M01 alpha`.

| Cell | shape before | latency after | state | generation | revision | `toasts` | first paragraph | Verdict |
|---|---|---|---|---|---|---|---|---|
| Chrome Backspace | `range-single` | 「刪除選取 15 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Chrome Delete | `range-single` | 「刪除選取 15 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Backspace | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Delete | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |

Compared with `0.2.16-134-*.json`, `0.2.15-132-*.json` and `0.2.13-131fix-*.json`, after masking the `定位游標 N ms` figure of the `before` field (34 / 36 / 38 / 36 ms here): Chrome Backspace, Firefox Backspace and Firefox Delete are byte-identical (as JSON, keys sorted) to all three earlier sets; Firefox Backspace and Delete are also identical to run 1's `0.2.18-136-firefox-*.json`. **One pair differs in a number**: Chrome Delete reads 「刪除選取 15 ms」 here against 14 ms in `0.2.15-132` and `0.2.13-131fix` and 16 ms in `0.2.16-134` (the criterion names no threshold for N; every field it names is as required). The `after.toast` field reads 「已開啟 f.odt」 in all four files, as in the earlier sets; the criterion's "no toast" is the `toasts` list, empty in all four. Run 1's Chrome files `0.2.18-136-chrome-*.json` are empty (not measured), so there is no Chrome comparison with run 1.

## G3 — 129-B (arrow keys after a selection): PASS in both browsers, all clauses

No pin commit in this run (the task: the pin is already `b24d754a…`; `grep` showed `FINAL_PAGE_SHA256 = "b24d754a…"` at `probe_129_m4_wasm.py` line 70 before the run). Round directory `../../129/final/round-20261013T063013Z/`. Driver `tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1` run from `wasm_sdk_probe/` — i.e. `cd wasm_sdk_probe` first (the precedent's docs directory and arguments: round label 4, 1 round; driver exit 0). Chrome 2026-10-13T06:30:13–06:42:59Z, Firefox 06:42:59–06:56:34Z (driver ended 06:56:44Z). Desk at the start (`machine-at-start.txt`): load 0.39 0.41 0.43; `pgrep -c chrome` 0, `pgrep -c firefox` 0 (checked just before the launch). Health check before the step: `[before-G3]` OK (the driver runs Chrome first, then Firefox; the wallet was not re-checked between the two halves, only afterwards by the next step's check). Analysis: `python3 wasm_sdk_probe/tools/analyze_129_m4.py round-20261013T063013Z round-20261012T092119Z` run in `findings/evidence/129/final/`, exit 0, stdout in `round-20261013T063013Z/analysis-stdout.txt` (the analyzer also wrote `analysis.json` and `summary.md` in the round directory). Two extra invocations, not in the task, as in the earlier chains and run before the task's form so the final `analysis.json`/`summary.md` are the task's form: against `round-20261012T235136Z` (the 134 page's round; `analysis-vs-235136Z-stdout.txt`, exit 0) and against `round-20261013T042552Z` (run 1's round, Firefox only; `analysis-vs-042552Z-stdout.txt`, exit 0). The page under test is `dist/`; the red control is 0.2.12's page from `build/archive/host-0.2.12-engine-45cdcedfc0fe7e61/`.

`preflight.final` in both `report-chrome.json` and `report-firefox.json`: `pageUnderTestSha256` `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678` (`pageUnderTestIsFinal: true`), `redControlSha256` `8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401` (`redControlIs0212: true`); neither report has a `fatal`.

| Clause (§9.4 129-B, as in `../../129/final/README.md`) | Chrome | Firefox | Verdict |
|---|---|---|---|
| 42 brief cells land where native `ref` lands | old 12 = native exact 12/12; S1–S5 30/30 by rule, 28/30 exact (`s1/Down` 195 vs native 201, `s1/End` 194 vs 200: the same two cells as in every earlier round); drag cells `s1d`/`m1d` follow native `ref` by rule | same | PASS |
| toolbar shape after the key is `collapsed` | 54 of 54 m4 arms (analyzer: `not fresh: []; selection-mismatch: []; other not counted: []`) | same | PASS |
| 0 toasts | analyzer: `toasts in m4 arms … 0 arms []`; pill `stopped` in none | same | PASS |
| key → move done < 400 ms | max 284.9 ms (47 moving keys 81.5–85.1; the 7 arms whose key does not move the caret 283.0–284.9) | max 289.2 ms (moving 84.2–87.7; the 7 non-moving 285.8–289.2) | PASS |
| Shift+arrow does not move, no toast | `shift` arms: `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret`/`sameSelection` true | same | PASS |
| red control refuses | 3 of 3 `red-*` arms `refused: true` with the `EDITOR_FORMAT_GESTURE_UNSUPPORTED` toast | 3 of 3 | red, as required |
| L-129 cells (recorded, not judged) | `s1d`/`m1d` Down follow native `ref` (`dragDownFollowsRef: ["s1d", "m1d"]`) | same | recorded |

Cross-checks printed by the analyzer: Chrome against Firefox landing index equal in 54/54 cells; each browser against `round-20261012T092119Z` (the d761f1ce round), against `round-20261012T235136Z` (the 134 page's round) and Firefox against `round-20261013T042552Z` (run 1's round): 54 compared, 0 differ, wrap offsets the same.

Run 1's Firefox half (`round-20261013T042552Z`): same verdicts for every clause (key → move max 289.2 ms there as here; moving keys 84.6–87.4); Chrome had no round in run 1 (fatal before the first arm).

Odd, not a criterion: the analyzer's "swap pages during arms" line for the Firefox half reads `pswpinMax: 3060` (one arm, `m4-s1d-End`; `pswpin` 4 in `m4-m1d-Home`; 49 of 54 arms with no swap activity), where the earlier rounds read 0–4 for Firefox. That arm's key → move time is inside the range above; I did not look into the cause (unverified, the machine's other activity at that moment was not recorded).

## G4 — 122-B / C2 typing latency: PASS in both browsers, every cell (`judge_c2.py` exit 0, `judge_p2.py` exit 0) — after one aborted first start (read the next paragraph)

No pin commit in this run: `PAGE` in `judge_c2.py` line 53 and `judge_p2.py` line 41 already read `b24d754a…` (grep before the run; run 1 commit `a0ed713f`).

**The chain was started twice; the second start is the verdict of record.** The first start (2026-10-13T06:57:56Z, `c2-aborted-load-1.58/`, see its `ABORTED.txt`) began 80 seconds after G3's Firefox half had ended, at `/proc/loadavg` 1.58 1.19 0.88 (a trailing average; nothing else was running and there was no Chrome browser). The C2 README asks for a clean desk; I noticed the load after launching and killed the chain after its first two cells (Chrome ratio-2 owner gap 80 and gap 200) had written JSON. I did not judge those two files. For disclosure, from their JSON: the first start's Chrome gap-80 cell read `onScreenMs` median 25.4 / **max 158.3** (the gate is max < 150) and `revisionMs` max 147.9, with keys i = 9 and 10 slow (147.9, 97.0 ms commit; 158.3, 103.1 ms on screen) and the other 18 keys 13.3–43 ms — the stall at key index 9–10 that finding 135 records for this cell; whether the load had anything to do with it is unknown (finding 135 records the stall on a clean desk too). Its Chrome gap-200 cell had completed too (10 rows, completed 06:58:31Z; `onScreenMs` median 32.4 / max 41.2, `revisionMs` max 23.9; `c2-aborted-load-1.58/c2-candidate-chrome-owner-gap200.json`), but `chain.txt` has no line for it because the chain script was killed before it. I then waited until the 1-minute load average was 0.38 and restarted the whole chain from its first cell with the same script. This is the one deviation from "no reruns" in this chain; it was made because the desk precondition was not met, and the restarted chain, not the first start, is the verdict of record whatever it reads. The two cells of the first start are not counted as samples of the restarted chain; they are reported here so that a reader of finding 135 has them.

Chain: `c2/chain-c2.sh`, a copy of run 1's `findings/evidence/136/guard/c2/chain-c2.sh` with exactly one line changed (`diff` shows only `E=` → `findings/evidence/136/guard-r2/c2`; its `PAGE=b24d754a426706bb` line was already changed in run 1 for the reason run 1 gave: the script refuses to run when `dist/e2-editor-app.js` does not hash to its `PAGE`). Structure unchanged (ratio 2 wide `--dpr 2 --window 1400x1000`, owner gap 80 / 20 chars and gap 200 / 10 chars; ratio 1.5 wide recorded only; ratio 1 `probe_typing_latency.py` owner gap 80, owner gap 200, boundaries gap 200; Chrome first, then Firefox, one cell at a time). Started with `nohup` (detached), waited for `DONE`. Health check just before: `[before-G4]` (06:57:55Z, the first start) and `[before-G4-restart]` (07:00:38Z) both OK.

Desk at the start of the restart (`c2/desk-at-start.txt`, 2026-10-13T07:00:39Z): `pgrep -c chrome` 0, Chrome browsers 0, `/proc/loadavg` 0.40 0.88 0.81, no Firefox, nothing of ours running. `chain.txt`: `START tree 845c2c0b dist b24d754a426706bb view 1412e4c863de6fcb probe dbad93c0dcf27fbf`, started 07:00:39Z, `DONE` 07:05:00Z, all 12 cells `exit 0`. Tool hashes equal the ones both judges bind.

Judges, run as the C2 README did with `--dir` at this directory; output in `c2/judge-output.txt` (it also carries my `$ …` command line and `exit N` line per judge):

- `python3 findings/evidence/c-prime/c2/judge_c2.py --dir findings/evidence/136/guard-r2/c2` → last line `PASS: both browsers, every cell`, **exit 0** (ratio 2 wide).
- `python3 findings/evidence/typing-latency/judge_p2.py --dir findings/evidence/136/guard-r2/c2/ratio-1` → last line `PASS: both browsers, every cell`, **exit 0** (ratio 1, P2's cells).

| Cell (judge) | Chrome | Firefox | run 1 Firefox | Verdict |
|---|---|---|---|---|
| ratio 2 wide, owner gap 80: every key committed / on screen | 20 of 20 / 20 of 20 | 20 of 20 / 20 of 20 | 20 / 20 of 20 | PASS |
| ... on-screen median (needs < 70 / < 90) and max (< 150) | 23.7, **max 43.1** | 30.0, max 48.8 | 28.4, max 43.1 | PASS |
| ... (a) every commit < 2 × gap (< 160) | max 36.1 | max 35.0 | max 35.5 | PASS |
| ... (b) median commit < gap (< 80) | 16.8 | 22.8 | 22.3 | PASS |
| ratio 2 wide, owner gap 200: every key committed / on screen | 10 of 10 / 10 of 10 | 10 of 10 / 10 of 10 | 10 / 10 of 10 | PASS |
| ... on-screen median (< 70 / < 90) and max (< 150) | 30.8, max 42.1 | 34.3, max 44.4 | 34.0, max 51.9 | PASS |
| ratio 2 wide (ii), recorded not gated | gap 80 52.3 ms, gap 200 69.8 ms | gap 80 61.2 ms, gap 200 72.6 ms | 60.8, 65.5 | recorded |
| ratio 1 (P2), owner gap 80: committed / on screen | 20 of 20 / 20 of 20 | 20 of 20 / 20 of 20 | 20 / 20 of 20 | PASS |
| ... on-screen median (< 70 / < 90), max (< 150) | 25.6, max 40.9 | 26.6, max 53.5 | 29.3, max 46.2 | PASS |
| ... (a) max commit (< 160); (b) median commit (< 80) | 32.8; 18.3 | 43.7; 20.7 | 38.2; 22.0 | PASS |
| ratio 1 (P2), owner gap 200: committed / on screen | 10 of 10 / 10 of 10 | 10 of 10 / 10 of 10 | 10 / 10 of 10 | PASS |
| ... on-screen median (< 70 / < 90), max (< 150) | 29.4, max 38.0 | 32.0, max 46.3 | 32.1, max 48.1 | PASS |
| ratio 1 (P2), boundaries gap 200: committed / on screen | 10 of 10 / 10 of 10 | 10 of 10 / 10 of 10 | 10 / 10 of 10 | PASS |
| ... commit median (≤ 10) | 4.3 | 3.9 | 3.7 | PASS |
| ratio 1.5 wide, owner gap 80 (recorded only, no judge): commit median / max, on-screen median / max | 19.4 / 36.3, 25.2 / 45.2 | 21.1 / 34.1, 27.6 / 38.8 | 21.4 / 35.6, 27.3 / 45.1 | recorded |

Per-key backlog `b_i` is 0.0 for all 20 keys in the Chrome and Firefox ratio-2 gap-80 cells and in the Chrome and Firefox ratio-1 gap-80 cells. Chrome's ratio-2 gap-80 cell here has no slow stretch (revision max 36.1 ms); on the 134 page that cell read 148.7 ms and finding 135 records it over the gate in 3 of 10 repeats. The restarted chain's single run of it says nothing about the rate (see G6 for two more runs of the same cell).

## G5 — restore-window on the new page (ruling-3 condition 5): PASS in 6 of 6 rounds (Chrome 3, Firefox 3); `scrollTop` never went to 0

Directory `restore-window/`. Command: `python3 findings/evidence/134/restore-window/probe_restore_window.py --out findings/evidence/136/guard-r2/restore-window` (default `--browsers chrome,firefox --rounds 3`; exit 0, `probe.out` ends `probe exit 0`). 2026-10-13T07:05:55Z–07:08:30Z (`started-utc.txt`: `pgrep -c chrome` 0, Chrome browsers 0, `pgrep -c firefox` 0, load 0.50 0.80 0.82; health check `[before-G5]` OK). `report.json` → `static` and `staticAfter`: host 0.2.18, buildId `d6d04880f56e31da`, `servedPage` = `distPage` = `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`. No round has a `fatal`.

Criterion (task G5): every round 1 refusal, generations `['1','2']`, `marks == 1`, mark in paragraph 210, rest unchanged; report the caret-back time and whether `scrollTop` ever went to 0 (expected: it no longer does). The numbers below are read from `report.json` → `runs[].log` and `runs[].summary`/`server` by a one-off script (not kept), the same readings run 1 made.

| browser | round | refusals | generations | keys typed (ms after the gen-2 `ready` log entry) | first state entry after the last key (ms after gen-2 `ready`) | `scrollTop` over the 12 state entries of the round | `marks` / paragraph | rest of document |
|---|---|---|---|---|---|---|---|---|
| chrome | 0 | 1 | `['1','2']` | +17.7, +70.5, +122.4 | +165.8 | 21477 in all (min 21477, max 21477) | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| chrome | 1 | 1 | `['1','2']` | +8.2, +60.4, +112.7 | +148.8 | 21477 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| chrome | 2 | 1 | `['1','2']` | +6.5, +58.9, +111.2 | +150.7 | 21477 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 0 | 1 | `['1','2']` | +18.0, +72.7, +128.3 | +167.4 | 21463 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 1 | 1 | `['1','2']` | +22.4, +77.4, +132.4 | +172.5 | 21463 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 2 | 1 | `['1','2']` | +6.5, +62.2, +118.1 | +157.9 | 21463 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |

- **`scrollTop` never went to 0 in any of the six rounds.** `scroll` is sampled with every state entry; in each round all 12 samples, from before the key through the new generation's `ready` entry and after it, read the value from before the key (Chrome 21477, Firefox 21463). On the 134 page (`../../134/restore-window/README.md`) the view sat at the document start for about 0.7 s and then returned (caret back +765, +741, +754 ms in Chrome and +759, +768, +724 ms in Firefox).
- **Caret-back time:** with no scroll excursion there is no scroll-return to time, so there is no measured caret-back time. The nearest analogue, as in run 1 — the first state entry after the last typed key — is at +148.8 to +165.8 ms (Chrome) and +157.9 to +172.5 ms (Firefox) after the new generation's `ready` entry; its label already reads 「重新載入 N ms」 (`summary.readyInNewGenerationMs`: Chrome 1403.9, 1448.2, 1400.0; Firefox 2239.8, 2164.1, 2187.7). I did not verify that this entry is the moment the caret was placed back (the page's caret-restore step is not logged separately); read it as "first state entry after the keys", not as a measured caret-back time.
- The three letters were typed inside the window (keydowns +6.5 to +132.4 ms after the new generation became `ready`) and all landed at the restored caret in paragraph 210; `marks == 1` and the document with the mark removed equals the original in every round. The prediction in `../../134/restore-window/README.md` (all three letters in the last paragraph, `marks == 1`, rest unchanged, refusals 1, generations `['1','2']`) holds in all six rounds.
- Run 1's Firefox half (3 rounds): same verdicts; `scrollTop` 21463 throughout; first state entry after the last key +171.6, +170.2, +161.1 ms; `readyInNewGenerationMs` 2203.7, 2193.3, 2220.8. Chrome had no round in run 1.
