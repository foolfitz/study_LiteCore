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
