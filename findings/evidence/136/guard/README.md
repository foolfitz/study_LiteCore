# Finding 136 page — the "must not break" set on the final bytes

Task: `handoff/tasks/TASK-2026-10-13d-136-guard-chain.md` (SPEC-M3-held-key §16; ruling-3 conditions 5–6). Precedents: `findings/evidence/134/guard/README.md` (task `TASK-2026-10-13-134-guard-chain.md`) and `findings/evidence/132/guard/README.md`. Mechanical runs of existing instruments and judges on one page; nothing here changes a check, a judge or an instrument except the pin edits the task names (G3, G4), each its own commit. Facts only; anything not checked is marked unverified. All times UTC.

## Conditions (common)

- Page under test: `wasm_sdk_probe/dist/e2-editor-app.js` sha256 `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678` (= `wasm_sdk_probe/web/e2-editor-app.js`; `sha256sum` of both checked at 2026-10-13T03:35:51Z before G0).
- Host `litecore` 0.2.18 (`appinfo/info.xml`, uncommitted on purpose; host HEAD `f5b34f0`, `git status --short` = ` M appinfo/info.xml`), engine package buildId `d6d04880f56e31da` (`engine/MANIFEST.json` read before G0: `source.page` = the page above, `source.profile` e2-editor-v19, `packagedAt` 2026-10-13T02:25:55+00:00). Every probe report's `static` and `staticAfter` say `servedPage` = the page above, `buildId` `d6d04880f56e31da`, `hostVersion` `0.2.18`. ddev project `litecore` running.
- What changed from 0.2.16 (`6470dec0…`), per the task: finding 136 (`updateState` notes the last caret the engine pushed with no range selected; the reopen puts the caret back there) and the restore flash (`updateState` does not follow the caret while the page reopens). I did not read the page diff.
- Chrome 151.0.7922.169, Firefox 157.0.1, one browser at a time, one job at a time. Before each browser step `pgrep -af "probe_|check_m3|run_e2_c"` showed nothing of ours (apart from the `bash -c` wrapper matching its own command line) and `pgrep -c chrome` was 0 (after the owner's reboot Codex desktop's crashpad handler, which counted as 1 in the 134 run, is not running). No owner Firefox was open at the start.
- Not done by me, by instruction: no `make`, no edit of `wasm_sdk_probe/web` or `dist`, nothing in `~/Projects/Nextcloud_Apps`, no `--write` mode, no `git push`.
- `static.shellBundle` in the G0/G1 reports is `exit 1` ("manifest is out of date … changed=['web/e2-editor-app.js']", `e2/editor-shell-v2-bundle-v65.json`): the shell generation is not frozen for this page; the probe records it and does not stop on it. Not investigated.

## Chrome headless could not load any http page during this run (environment, read this first)

Every Chrome run in this chain failed the same way, before any measurement: `report.json` → `runs[chrome].fatal` is a traceback ending `TimeoutError: timed out in 180.0s` in `login()` → `navigate(…/login)` → `Page.navigate`. G0 Chrome fatal at 03:36–03:39Z, G1 Chrome fatal 03:57–04:00Z, G1 hostseg rerun Chrome fatal 04:13–04:16Z; Firefox ran normally each time. The earlier 134-chain run on the same machine (before the owner's reboot) had Chrome working.

A diagnostic outside the chain (Chrome 151.0.7922.169, headless, a fresh temporary profile each time; `CDP Page.navigate` through `run_browser_probe.ChromeSession`, and `google-chrome --headless=new --dump-dom <url>` with a 12–40 s limit) showed: `Page.navigate` to `about:blank` returns at once and `Runtime.evaluate` works; `--dump-dom data:text/html,<p>hello</p>` prints the DOM; but `Page.navigate` / `--dump-dom` to **any** `http(s)` URL never returns — `http://127.0.0.1:<chrome's own debugging port>/json/version`, `https://litecore.ddev.site:8443/login`, a refused local port (`http://127.0.0.1:8123/`), `http://localhost:8123/`, and a `python3 -m http.server` on `127.0.0.1:8124`. `curl https://litecore.ddev.site:8443/login` answers 200 in 0.06 s from the same shell. None of `--no-sandbox`, `--disable-features=NetworkServiceSandbox`, `--disable-features=NetworkServiceInProcess2`, `--enable-features=NetworkServiceInProcess`, `--no-proxy-server`, `--disable-background-networking`, `--headless=old` changed it (each hung to the time limit). `--enable-logging=stderr --v=0` printed only two lines (`No machine level policy manager exists.`, `InitializeSandbox() called with multiple threads in process gpu-process.`). No proxy environment variable is set; `gsettings` proxy mode is `none`. Cause unverified: this looks like Chrome's network service not answering at all on this boot, independent of the page, the host and the probe. I changed nothing to fix it (not in scope). Consequence for this chain: every cell that needs Chrome is **not measured**, which is different from a measured FAIL.

## G0 — 132-B on the 136 page: FAIL (exit 1) — Chrome not run (environment), Firefox 6/6 holds PASS

`132-b/` (own README). 2026-10-13T03:36:01–03:56:10Z. Command: `probe_hand_test_0212.py --out findings/evidence/136/guard/132-b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (exit 0). `judge_132b.py --page b24d754a…` **exit 1**, last line `132-B FAIL`; its lines: `chrome: fatal in the run  FAIL`, `chrome hold-high: 0 holds < 3  FAIL`, `chrome hold-low: 0 holds < 3  FAIL`, `chrome wash-control: not run  NOT_ESTABLISHED`, `firefox hold-high|hold-low round 0|1|2: PASS` ×6, `firefox wash-control: selection fills [10]  PASS`. Firefox read: deleted per hold 26, 1–2 deletes after release (last at 70.6–105.3 ms), caret band fresh 89.6–123.4 ms after release, 0 washes, `persistent.differing` 0. Commit `b2b4dda2`. Not rerun (task: record, go on).

## G1 — 131-B and 128-B (one probe run, then the host-segment arms once more): 131-B FAIL (Chrome not run; Firefox clauses hold); 128-B Firefox single presses PASS; Firefox host-segment cell NOT_JUDGED in the first run, PASS in the one rerun; red control red in both; Chrome none

Directory `131b-128b/`. Command: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/136/guard/131b-128b --browsers chrome,firefox --arms high,low,rapid20,hostseg,hostseg-red --rapid-rounds 6` (exit 0, `probe.out` ends `probe exit 0`). Chrome fatal 03:57:05–04:00:11Z, Firefox 04:00:11–04:06:05Z. At the start `pgrep -c chrome` = 0, load 0.78 0.45 0.37 (`started-utc.txt`).

| Clause | Read with | Chrome | Firefox | Verdict |
|---|---|---|---|---|
| 131-B: 6 rapid20 bursts, each `deleted 20`, `refused 0`, `other []` | `judge_131b.py report.json --page b24d754a…` → `judge_131b-output.txt`, **exit 1**, last line begins `131-B FAIL ['chrome: fatal …', 'chrome: 0 bursts, wanted 6', 'chrome high persistent None', 'chrome low persistent None']` | not run (fatal) | 6/6 bursts `deleted 20 refused 0 other []` | Chrome NOT MEASURED; Firefox holds |
| 131-B: `persistent.differing == 0` in the four high/low arms | same | not run | high 0, low 0 | Chrome NOT MEASURED; Firefox holds |
| 128-B: every single press `staleAfterCaretMs` ≤ 40 ms | `read_128b_cells.py report.json` → `read_128b-output.txt` (exit 0) | not run (no line printed) | high 27.0 20.6 20.7 21.0; low 23.6 24.8 22.0 21.1 | Firefox PASS (max 27.0); Chrome NOT MEASURED |
| 128-B: host-segment cell holds | `runs[].hostseg.judged`, first run | not run | `NOT_JUDGED`, why `2 PUTs, 1 keys, save saved` | not judged in the first run; Firefox PASS in the rerun (below) |
| 128-B: host-segment red control (`hostseg-red`) is red | `runs[].hostsegRed.judged` | not run | `FAIL` (band fresh 2754.9 ms after the key, `heldPaints` 1) | Firefox red, as required |

- The rapid keys printed by the reader (Firefox high 79.5 – 78.6 90.3, low 81.6 – 80.9 78.5; `–` = the caret did not move inside that key's own window) are not part of the task's criteria; I did not judge them.
- **First run, Firefox host-segment cell `NOT_JUDGED`** — the state the 132 and 134 chains also hit. `runs[].hostseg.put.puts` has two PUTs: the first held 322203.7, sent 325204, answered 325262.5 ms; a second PUT held at 326388.5 ms and still outstanding when the arm ended (`out: 1`). Cause unverified.
- **Rerun, as the task's disposition says** — only the two arms once, instrument and verdict function unchanged: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/136/guard/131b-128b-hostseg-rerun --browsers chrome,firefox --arms hostseg,hostseg-red` (exit 0; Chrome fatal 04:13:19–04:16:25Z, Firefox 04:16:25–04:17:01Z; served page, buildId and host version as above).

| | Chrome | Firefox |
|---|---|---|
| host-segment cell (`runs[].hostseg.judged`) | not run (fatal, same traceback) | **PASS**: PUT held 3333.7 ms, key at 3646.4 ms (inside the hold), caret moved 21.4 ms after the key, caret band fresh 36.8 ms after the key, PUT answered 6397.2 ms (one PUT, `out: 0`), `heldPaints` 0 |
| red control (`runs[].hostsegRed.judged`) | not run | **FAIL**: band fresh 2805.8 ms after the key, `heldPaints` 1 |

`read_128b-output.txt` in the rerun directory is empty (that reader prints the high/low arms only). The Firefox host-segment cell has been sampled twice; the first sample is not a PASS. Chrome has no sample of any G1 clause on this page.

Output files: `131b-128b/` — `probe.out`, `report.json`, `judge_131b-output.txt`, `read_128b-output.txt`, `started-utc.txt`, `ended-utc.txt`; `131b-128b-hostseg-rerun/` — `probe.out`, `report.json`, `read_128b-output.txt` (empty), `started-utc.txt`, `ended-utc.txt`. (No screenshots were written: the probe writes them from the Chrome half.)

## G2 — 121-B (selection, then Backspace / Delete): Firefox PASS in both cells; Chrome not measured (both cells exit 1, empty JSON)

Files: `../../121/0.2.18-136-binding.txt` (before 2026-10-13T04:18:10Z, after 04:25:08Z; both lines carry the page sha256 `b24d754a…`), `../../121/0.2.18-136-<browser>-<key>.json` and `.stderr`. Command per cell: `python3 findings/evidence/121/select_delete_probe.py <browser> <Key>` (standalone page built from `dist/`, `boundaries.odt`, a drag inside "M01 plain alpha", one real key; no host involved), run sequentially from a small wrapper script that also wrote the binding file (the exact lines of the 134 chain). Criterion (SPEC-M3-autosave §9.13): shape `range-single` before the key, after the key 「刪除選取 N ms」, `ready`, generation 1 → 1, revision 0 → 1, no toast, first paragraph `M01 alpha`.

Exit codes in the binding file: `chrome Backspace exit 1`, `chrome Delete exit 1`, `firefox Backspace exit 0`, `firefox Delete exit 0`.

| Cell | shape before | latency after | state | generation | revision | `toasts` | first paragraph | Verdict |
|---|---|---|---|---|---|---|---|---|
| Chrome Backspace | — (JSON empty, 0 bytes) | — | — | — | — | — | — | NOT MEASURED: `.stderr` ends `TimeoutError: timed out in 180.0s` (a CDP call, the same Chrome network hang as in the section above) |
| Chrome Delete | — (JSON empty) | — | — | — | — | — | — | NOT MEASURED (same) |
| Firefox Backspace | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Delete | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |

Compared with `0.2.16-134-firefox-*.json`, `0.2.15-132-firefox-*.json` and `0.2.13-131fix-firefox-*.json`: after masking the `定位游標 N ms` figure of the `before` field (35 and 38 ms here), both Firefox files are byte-identical (as JSON, keys sorted) to all three earlier sets. The `after.toast` field reads 「已開啟 f.odt」 in both files, as in the earlier sets; the criterion's "no toast" is the `toasts` list, empty in both. Chrome: nothing to compare.

## G3 — 129-B (arrow keys after a selection): Firefox PASS (all clauses); Chrome not measured (fatal before the first arm)

Pin commit (its own, before the run): `1b5efdbb` — `FINAL_PAGE_SHA256` in `wasm_sdk_probe/tools/probe_129_m4_wasm.py` from `6470dec0…` to `b24d754a…`, the old value kept in the comment above it; nothing else in the file changed (`git diff` was 3 insertions, 1 deletion). Round directory `../../129/final/round-20261013T042552Z/`. Driver `tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1` run from `wasm_sdk_probe/` (the precedent's docs directory and arguments: round label 4, 1 round; driver exit 0 — the driver exits 0 although the Chrome half is fatal). Chrome fatal 04:25:52–04:28:58Z, Firefox 04:28:58–04:43:13Z, load 0.22 0.37 0.56 at the start (`machine-at-start.txt`), `pgrep -c chrome` = 0. Analysis: `python3 wasm_sdk_probe/tools/analyze_129_m4.py round-20261013T042552Z round-20261012T092119Z` run in `findings/evidence/129/final/`, exit 0, stdout in `analysis-stdout.txt` (the analyzer also wrote `analysis.json` and `summary.md` in the round directory). One extra invocation, not in the task, as in the 134 chain: the same analyzer against `round-20261012T235136Z` (the previous page's round), stdout in `analysis-vs-235136Z-stdout.txt`, run first and the task's form rerun last so the final `analysis.json`/`summary.md` are the task's form. The page under test is `dist/`; the red control is 0.2.12's page from `build/archive/host-0.2.12-engine-45cdcedfc0fe7e61/`.

`preflight.final` in both `report-chrome.json` and `report-firefox.json`: `pageUnderTestSha256` `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678` (`pageUnderTestIsFinal: true`), `redControlSha256` `8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401` (`redControlIs0212: true`).

Chrome: `report-chrome.json` → `fatal` ends `TimeoutError: timed out in 180.0s` (the first `Page.navigate` to the standalone mirror page); no `arms-chrome.jsonl`, no `calibration-chrome.json`. The analyzer prints a Firefox section only.

| Clause (§9.4 129-B, as in `../../129/final/README.md`) | Chrome | Firefox | Verdict |
|---|---|---|---|
| 42 brief cells land where native `ref` lands | not run | old 12 = native exact 12/12; S1–S5 30/30 by rule, 28/30 exact (`s1/Down` 195 vs native 201, `s1/End` 194 vs 200: the same two cells as in every earlier round); the drag cells `s1d`/`m1d` also follow native `ref` by rule | Firefox PASS |
| toolbar shape after the key is `collapsed` | not run | 54 of 54 m4 arms `afterKey.toolbar.shape` = `collapsed` | Firefox PASS |
| 0 toasts | not run | analyzer: `toasts in m4 arms … 0 arms []`; pill `stopped` in none | Firefox PASS |
| key → move done < 400 ms | not run | max 289.2 ms (47 moving keys 84.6–87.4; the 7 arms whose key does not move the caret 286.5–289.2) | Firefox PASS |
| Shift+arrow does not move, no toast | not run | `shift` arms: `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret` true | Firefox PASS |
| red control refuses | not run | 3 of 3 `red-*` arms `refused: true` with the `EDITOR_FORMAT_GESTURE_UNSUPPORTED` toast | Firefox red, as required |
| L-129 cells (recorded, not judged) | not run | `s1d`/`m1d` Down follow native `ref` (`dragDownFollowsRef: ["s1d", "m1d"]`) | recorded |

Cross-check printed by the analyzer: Firefox against `round-20261012T092119Z` (the d761f1ce round): 54 compared, 0 differ, wrap offsets the same; against `round-20261012T235136Z` (the 134 page's round): 54 compared, 0 differ, wrap offsets the same. Chrome has no cross-check from this round.

## G4 — 122-B / C2 typing latency: Firefox every cell PASS; Chrome not measured; judge exits 2 (`judge_c2.py`) and 1 (`judge_p2.py`) because of the Chrome cells

Pin commit (its own, before the run): `a0ed713f` — in `findings/evidence/c-prime/c2/judge_c2.py` and `findings/evidence/typing-latency/judge_p2.py` only the `PAGE = "…"` line changed, from `6470dec0…` (kept in a comment above) to `b24d754a…` (`git diff --stat`: 6 insertions, 2 deletions, all comment lines and the two `PAGE` lines). A consequence, not checked further: the reports in `findings/evidence/134/guard/c2/` (page `6470dec0…`) are now REFUSED by the default pin of those two judges.

Chain: `c2/chain-c2.sh`, a copy of `findings/evidence/134/guard/c2/chain-c2.sh` with two lines changed (`diff` shows exactly these): `E=` (output directory) → `findings/evidence/136/guard/c2`, and `PAGE=` → `b24d754a426706bb`. The second one is not an output directory; I changed it for the reason the 134 chain gave: the script's first check refuses to run when `dist/e2-editor-app.js` does not hash to its `PAGE`, and the task did not name that line. The header comment of the copy is unchanged. Structure unchanged (ratio 2 wide `--dpr 2 --window 1400x1000`, owner gap 80 / 20 chars and gap 200 / 10 chars; ratio 1.5 wide recorded only; ratio 1 `probe_typing_latency.py` owner gap 80, owner gap 200, boundaries gap 200; Chrome first, then Firefox, one cell at a time). Started with `nohup` (detached), waited for `DONE`.

Desk at the start (`c2/desk-at-start.txt`, 2026-10-13T04:44:37Z): `pgrep -c chrome` = 0; `pgrep -fc '/chrome/chrome( |$)'` = 0; `/proc/loadavg` 0.18 0.58 0.61; no Firefox process. `chain.txt`: `START tree a0ed713f dist b24d754a426706bb view 1412e4c863de6fcb probe dbad93c0dcf27fbf`, started 04:44:40Z, `DONE` 05:05:49Z. All 12 cells print `exit 0` in `chain.txt` (the script records the `timeout` wrapper's exit and the last output line; for the six Chrome cells that line is `TimeoutError: timed out in 180.0s`, for the Firefox cells the summary JSON). Tool hashes equal the ones both judges bind.

Judges, run as the C2 README did with `--dir` at this directory, output in `c2/judge-output.txt` (it also carries my `$ …` command line and `exit N` line for each judge):

- `python3 findings/evidence/c-prime/c2/judge_c2.py --dir findings/evidence/136/guard/c2` → **exit 2**, last line `REFUSED: chrome owner-gap80, chrome owner-gap200; also FAIL: chrome owner-gap80 every key committed, chrome owner-gap80 every key on screen, chrome owner-gap200 every key committed, chrome owner-gap200 every key on scree…` (the two Chrome files carry only the probe's header — `probe`, `browser`, `document`, `gap`, `chars`, `page`, `runner`, `startedAt`, `version`, `completedAt` — no `rows`, so the judge's binding check refuses them).
- `python3 findings/evidence/typing-latency/judge_p2.py --dir findings/evidence/136/guard/c2/ratio-1` → **exit 1**, last line `FAIL: chrome owner-gap80 every key committed, chrome owner-gap80 every key on screen, chrome owner-gap80 (ii) every band current after the last key, chrome owner-gap200 every key committed, chrome owner-gap200 every key …` (Chrome: 0 of 20 / 0 of 10 keys, no rows).

| Cell (judge) | Chrome | Firefox | Verdict |
|---|---|---|---|
| ratio 2 wide, owner gap 80: every key committed / on screen | 0 of 20 / 0 of 20 (REFUSED, no rows) | 20 of 20 / 20 of 20 | Firefox PASS; Chrome NOT MEASURED |
| ... on-screen median (needs < 70 / < 90) and max (< 150) | — | 28.4, max 43.1 | Firefox PASS |
| ... (a) every commit < 2 × gap (< 160) | — | max 35.5 | Firefox PASS |
| ... (b) median commit < gap (< 80) | — | 22.3 | Firefox PASS |
| ratio 2 wide, owner gap 200: every key committed / on screen | 0 of 10 / 0 of 10 (REFUSED) | 10 of 10 / 10 of 10 | Firefox PASS; Chrome NOT MEASURED |
| ... on-screen median (< 70 / < 90) and max (< 150) | — | 34.0, max 51.9 | Firefox PASS |
| ratio 2 wide (ii), recorded not gated | — | gap 80 60.8 ms, gap 200 65.5 ms | recorded |
| ratio 1 (P2), owner gap 80: committed / on screen | 0 of 20 / 0 of 20 | 20 of 20 / 20 of 20 | Firefox PASS; Chrome NOT MEASURED |
| ... on-screen median (< 70 / < 90), max (< 150) | — | 29.3, max 46.2 | Firefox PASS |
| ... (a) max commit (< 160); (b) median commit (< 80) | — | 38.2; 22.0 | Firefox PASS |
| ratio 1 (P2), owner gap 200: committed / on screen | 0 of 10 / 0 of 10 | 10 of 10 / 10 of 10 | Firefox PASS; Chrome NOT MEASURED |
| ... on-screen median (< 70 / < 90), max (< 150) | — | 32.1, max 48.1 | Firefox PASS |
| ratio 1 (P2), boundaries gap 200: committed / on screen | 0 of 10 / 0 of 10 | 10 of 10 / 10 of 10 | Firefox PASS; Chrome NOT MEASURED |
| ... commit median (≤ 10) | — | 3.7 | Firefox PASS |
| ratio 1.5 wide, owner gap 80 (recorded only, no judge): commit median / max, on-screen median / max | no rows | 21.4 / 35.6, 27.3 / 45.1 | recorded |

Per-key backlog `b_i` is 0.0 for all 20 keys in the Firefox ratio-2 gap-80 cell and in the Firefox ratio-1 gap-80 cell. The Chrome ratio-2 gap-80 cell that was a near-miss on the 134 page (finding 135) has **no** measurement on this page from G4; G6 below is the same cell, Chrome only.
