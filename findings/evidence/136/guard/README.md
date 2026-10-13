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
| Chrome Backspace | — (JSON empty, 0 bytes) | — | — | — | — | — | — | NOT MEASURED: `.stderr` ends `TimeoutError: timed out in 180.0s` (the first `Page.navigate`, the same Chrome network hang as in the section above) |
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

## G5 — restore-window on the new page (ruling-3 condition 5): Firefox 3 of 3 rounds meet the criterion; Chrome not measured (3 of 3 rounds fatal)

Directory `restore-window/`. Command: `python3 findings/evidence/134/restore-window/probe_restore_window.py --out findings/evidence/136/guard/restore-window` (default `--browsers chrome,firefox --rounds 3`; exit 0, `probe.out` ends `probe exit 0`). 2026-10-13T05:06:26Z–05:17:15Z (`started-utc.txt`: `pgrep -c chrome` 0, load 0.57 0.61 0.52). `report.json` → `static` and `staticAfter`: host 0.2.18, buildId `d6d04880f56e31da`, `servedPage` = `distPage` = `b24d754a426706bb5c93dbacb3f7ffadc655e738ee9a0fdd7168069f0f701678`. Chrome rounds 0, 1, 2: `fatal` (the same `Page.navigate` timeout, 05:06:27, 05:09:33, 05:12:39Z). Firefox rounds 0, 1, 2 ran (05:15:44–05:17:15Z).

Criterion (task G5): every round 1 refusal, generations `['1','2']`, `marks == 1`, mark in paragraph 210, rest unchanged; report the caret-back time and whether `scrollTop` ever went to 0.

| browser | round | refusals | generations | keys typed (ms after the gen-2 `ready` log entry) | first state entry after the last key (ms after gen-2 `ready`) | `scrollTop` over the 12 state entries of the round | `marks` / paragraph | rest of document |
|---|---|---|---|---|---|---|---|---|
| chrome | 0, 1, 2 | — | — | — | — | — | — | NOT MEASURED (fatal) |
| firefox | 0 | 1 | `['1','2']` | +17.9, +72.8, +127.6 | +171.6 | 21463 in all (min 21463, max 21463) | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 1 | 1 | `['1','2']` | +15.8, +71.0, +126.3 | +170.2 | 21463 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |
| firefox | 2 | 1 | `['1','2']` | +20.9, +75.7, +131.4 | +161.1 | 21463 in all | 1 / 210 | `sameAsOriginal` true, `charDelta` 0 |

- **`scrollTop` never went to 0 in any Firefox round.** `scroll` is sampled with every state entry and every scroll event; here all samples, from before the key through the new generation's `ready` entry and after it, read 21463 (the value before the key). On the 134 page (`../../134/restore-window/run-1/report.json`, Firefox round 0) the entry at the new generation's `ready` read `scroll: 0` and the value 21463 came back 759 ms later (the README of that run: caret back +759, +768, +724 ms in the three Firefox rounds).
- **Caret-back time:** with no scroll excursion there is no scroll-return to time. The nearest analogue — the first state entry after the last typed key, which on the 134 page is the one that carried the return of `scroll` (+759 ms there) — is at +171.6, +170.2, +161.1 ms after the new generation's `ready` entry here; its label already reads 「重新載入 N ms」 (round 0: 2119 ms; `summary.readyInNewGenerationMs` of the three rounds 2203.7, 2193.3, 2220.8). I did not verify that this entry is the moment the caret was placed back (the page's caret-restore step is not logged separately); read it as "first state entry after the keys", not as a measured caret-back time.
- The three letters were typed inside the window (keydowns at +16 to +131 ms after the new generation became `ready`) and all landed at the restored caret in paragraph 210; `marks == 1` and the document with the mark removed equals the original in every Firefox round (`server.sameAsOriginal` true, `charDelta` 0). The prediction in `../../134/restore-window/README.md` (all three letters in the last paragraph, `marks == 1`, rest unchanged, refusals 1, generations `['1','2']`) holds in the three Firefox rounds. Chrome has no round.

## G6 — the C2 cell twice more (ruling-3 condition 6): Chrome not measured (both runs fatal); report-only

Directory `c2-extra/`. `repeat.sh` there is a copy of `findings/evidence/134/c2-cell-repeat/repeat.sh` with three changes (`diff` shows exactly these): `E=` → `findings/evidence/136/guard/c2-extra`, `PAGE=` → `b24d754a426706bb`, and the loop 10 → 2 (`seq -w 01 02`, so the files are `run-01.json`, `run-02.json`); the probe command line is unchanged (`probe_typing_latency_view.py --dpr 2 --window 1400x1000 --browser chrome --document owner --gap 80 --chars 20`). Run detached with `nohup`. Desk at the start (`desk-at-start.txt`, 2026-10-13T05:19:25Z): `pgrep -c chrome` 0, load 0.43 0.61 0.53, no Firefox process. `chain.txt`: run 01 05:19:25–05:22:30Z, run 02 05:22:30–05:25:36Z, `DONE`; both `exit 0` of the `timeout` wrapper. A first start of the script (with `seq -w 1 2`, which would have written `run-1.json`) was killed within seconds of launching, before any result, together with its headless Chrome; its `chain.txt`/`run-1.*` were removed and the loop corrected; this is recorded in `desk-at-start.txt`.

Read with `python3 findings/evidence/134/c2-cell-repeat/read_repeat.py findings/evidence/136/guard/c2-extra` (exit 0; output in `read_repeat-output.txt`):

```
run-01.json page b24d754a rows 0 screen median None max None commit median None max None slow>=100 []
run-02.json page b24d754a rows 0 screen median None max None commit median None max None slow>=100 []
```

Both `run-0N.stdout.txt` end in `TimeoutError: timed out in 180.0s`. So **there are no counts for finding 135 from this chain**: the Chrome ratio-2 gap-80 cell on `b24d754a…` has been measured 0 times here (G4's judged run of the same cell is also a Chrome fatal). Not measured is not the same as "0 of 2 over the gate".

## Anything odd, and what was not checked

- **Chrome (headless, driven by CDP) loaded no http page at all during this whole chain** — see the section near the top. Every Chrome half of G0–G6 is a fatal before the first measurement, not a measured FAIL: G0, G1 (twice), G2 (2 cells), G3, G4 (6 cells), G5 (3 rounds), G6 (2 runs). The cause is unverified; the diagnostic outside the chain (fresh temporary profiles, a handful of flags) did not fix it. A health check (`headless Chrome --dump-dom` of a refused local port, 12 s limit; a scratch script, not kept) printed `HUNG` at about 04:07Z (after G1's first run), before G1's rerun, before G4 (04:44Z), before G6 (05:18Z) and after G6 (05:26Z); I did not run it right before G2, G3 or G5, but those Chrome halves failed the same way. I did not rerun any Chrome half, by the task's rule against reruns; the Chrome halves need a re-run once Chrome's network works again.
- Because of that, **no step has a complete (both-browser) verdict on this page.** Firefox halves: G0 6/6 holds PASS, G1 131-B bursts 6/6 and 128-B single presses PASS (host-segment cell NOT_JUDGED then PASS on the one allowed rerun, red control red), G2 both cells PASS, G3 all clauses PASS, G4 every cell PASS, G5 3/3 rounds meet the criterion.
- The judges' exit codes are therefore: `judge_132b.py` 1, `judge_131b.py` 1, `judge_c2.py` 2, `judge_p2.py` 1; `read_hold.py`, `read_128b_cells.py`, `read_repeat.py`, `analyze_129_m4.py` 0. The 121 probe exits: chrome 1 ×2, firefox 0 ×2. The non-zero exits are all the Chrome halves.
- G1: the Firefox host-segment cell was `NOT_JUDGED` (two PUTs) in the first run, as on the 132 and 134 pages; cause unverified. The one allowed rerun of only that cell gave PASS with the red control red. The cell has been sampled twice; the first sample is not a PASS.
- G3: the driver exits 0 although the Chrome half is fatal; the `report-chrome.json` `fatal` field is where to look.
- G4: the chain copy changed its `PAGE=` line as well as its output directory (same as the 134 chain).
- `static.shellBundle` in the G0/G1/G5 reports is `exit 1` (shell generation v65 not frozen for this page); recorded by the probe, not investigated.
- `ended-utc.txt` / `started-utc.txt` and the trailing `probe exit N` line in `probe.out` are mine (a wrapper I used to detect the end of a detached run); the probe's own output is the rest. `judge-output.txt` in `132-b/` and `c2/` carries my `$ …` and `exit N` lines.
- Not run, by instruction: `make`, `package_m3_engine.py`, `ddev occ upgrade`, anything in `~/Projects/Nextcloud_Apps` (checked at the end: `git status --short` there is still only ` M appinfo/info.xml`); `wasm_sdk_probe/web` and `dist` untouched (`dist/e2-editor-app.js` hashed `b24d754a…` at the start of G0, in the G2 binding file's two lines, in the G4 chain's START line, and at the end of the chain). No `--write` mode, no `git push`.
- I did not read the 136 page diff or SPEC-M3-held-key §16; the criteria are the ones the task and the precedents state.

## Cause of the Chrome hang, found after the chain (main session, appended 2026-10-13T05:35Z; the text above is unchanged)

Raw output: `chrome-wallet-diagnosis.txt`. The cause is a **locked KWallet**, not the page, the host, the probes or Chrome's network stack:

- The Secret Service on this machine is `ksecretd` (KDE); its default collection is `kdewallet`, and that collection reads `Locked: true`.
- The owner's Plasma desktop runs inside a TigerVNC session (`Xtigervnc-session` → `startplasma-x11`). A VNC login does not pass through the PAM module that unlocks the wallet, so after the 2026-10-13 reboot nothing unlocked it.
- Headless Chrome with the default password store asks the Secret Service for its cookie-encryption key before a profile's first network request. With the wallet locked, that call waits for an unlock prompt nobody answers. Browser-internal requests (component updater, variations; the system network context) are not affected, which is why the verbose log shows those completing while the navigation request never opens a socket.
- Paired control, same binary, same fresh-profile shape, same local server, one flag different: default → `rc=124` (timeout 15 s) and **0 requests reached the server**; `--password-store=basic` → the DOM printed, `rc=0`, the request reached the server.
- Firefox and `curl` do not use the wallet, so they were unaffected.

Consequence: every Chrome half of this chain is **not measured** because of the environment. The probes were not changed (adding `--password-store=basic` to the launcher would change hashed instruments and is not done here). The remedy is environmental: unlock `kdewallet` on the owner's desktop, check `Locked: false` and a default-flag `--dump-dom` of a local page, then run the chain again. What the rerun is and what it counts as is written in its own task, before it runs.
