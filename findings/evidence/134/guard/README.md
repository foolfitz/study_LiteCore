# Finding 134 page — the "must not break" set on the final bytes

Task: `handoff/tasks/TASK-2026-10-13-134-guard-chain.md` (SPEC-M3-held-key §14; ruling-1 condition 4). Precedent: `findings/evidence/132/guard/README.md` (task `TASK-2026-10-13-132-guard-chain.md`). Mechanical runs of existing instruments and judges on one page; nothing here changes a check, a judge or an instrument except the pin edits the task names (G3, G4), each its own commit. Facts only; anything not checked is marked unverified. All times UTC (the session's wall clock reads 2026-10-12 evening UTC).

## Conditions (common)

- Page under test: `wasm_sdk_probe/dist/e2-editor-app.js` sha256 `6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b` (= `wasm_sdk_probe/web/e2-editor-app.js`; `sha256sum` of both checked before G0).
- Host `litecore` 0.2.16 (`appinfo/info.xml`, uncommitted on purpose; host HEAD `568608c`, `hostDirty: ["M appinfo/info.xml"]`), engine package buildId `9352fae3aea68b5e` (`engine/MANIFEST.json` read before G0: `source.page` = the page above, `source.profile` e2-editor-v19, `packagedAt` 2026-10-12T22:50:20+00:00). Every probe report's `static` and `staticAfter` say `servedPage` = the page above, `buildId` `9352fae3aea68b5e`, `hostVersion` `0.2.16`.
- What changed from 0.2.15 (`abe93f45…`), per the task: finding 134's B (after a delete this page sent is refused, the rest of that Backspace/Delete hold is not sent) and D (after an automatic reopen the caret is put back). A mid-document hold has no refusal, so the 132 instruments are expected to read as on `abe93f45…`. I did not read the page diff; this is the task's statement.
- Chrome 151.0.7922.169, Firefox 157.0.1, one browser at a time, one job at a time. Before each browser step `pgrep -af "probe_|check_m3|run_e2_c"` showed nothing of ours; `pgrep -c chrome` was 1 each time — the only match is Codex desktop's `chrome_crashpad_handler`, not a Chrome browser. The owner's own Firefox (pid 3932) was open throughout and was left alone.
- Not done by me, by instruction: no `make`, no edit of `wasm_sdk_probe/web` or `dist`, nothing in `~/Projects/Nextcloud_Apps` (no commit, no revert, no `package_m3_engine.py`, no `ddev occ upgrade`), no `--write` mode.

## G0 — 132-B on the 134 page: PASS

`132-b/` (own README). 2026-10-12 23:00:09–23:34:34Z. Command: `probe_hand_test_0212.py --out findings/evidence/134/guard/132-b --browsers chrome,firefox --arms hold-high,hold-low,wash-control --hold-rounds 3` (exit 0). `judge_132b.py --page 6470dec0…` exit 0, last line `132-B PASS` (12 of 12 holds PASS, wash-control fills Chrome 5 / Firefox 9, both PASS); `read_hold.py` exit 0. Read as on `abe93f45…`: deleted per hold 25 (Chrome) / 26 (Firefox), 1–2 deletes after release (last at 61.3–92.4 ms), caret band fresh 73.9–104.0 ms after release, 0 washes, `persistent.differing` 0. Commit `67ba7cf6`.

## G1 — 131-B and 128-B (one probe run, then the host-segment arms once more): 131-B PASS; 128-B single presses PASS; host-segment cell NOT_JUDGED in the first run, PASS in the one rerun; red control red in both

Directory `131b-128b/`. Command: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/134/guard/131b-128b --browsers chrome,firefox --arms high,low,rapid20,hostseg,hostseg-red --rapid-rounds 6` (exit 0, `probe.out` ends `probe exit 0`). Chrome 23:35:41–23:41:24Z, Firefox 23:41:24–23:47:21Z. At the start `pgrep -c chrome` = 1, load 0.38 0.43 0.43 (`started-utc.txt`).

| Clause | Read with | Chrome | Firefox | Verdict |
|---|---|---|---|---|
| 131-B: 6 rapid20 bursts, each `deleted 20`, `refused 0`, `other []` | `judge_131b.py report.json --page 6470dec0…` → `judge_131b-output.txt`, exit 0, last line `131-B PASS []` | 6/6 bursts `deleted 20 refused 0 other []` | 6/6 | PASS |
| 131-B: `persistent.differing == 0` in the four high/low arms | same | high 0, low 0 | high 0, low 0 | PASS |
| 128-B: every single press `staleAfterCaretMs` ≤ 40 ms | `read_128b_cells.py report.json` → `read_128b-output.txt` (exit 0) | high 17.6 15.4 19.7 16.5; low 18.4 17.8 17.9 17.7 | high 19.6 21.7 19.7 20.3; low 24.3 25.7 23.7 24.8 | PASS (max 25.7) |
| 128-B: host-segment cell holds | `report.json` → `runs[].hostseg.judged`, first run | `NOT_JUDGED`, why `2 PUTs, 1 keys, save saved` | same string | **not judged** in the first run; **PASS** in the rerun (below) |
| 128-B: host-segment red control (`hostseg-red`) is red | `runs[].hostsegRed.judged` | `FAIL` (band fresh 2747.7 ms after the key, `heldPaints` 1) | `FAIL` (2819.0 ms, `heldPaints` 1) | red, as required |

- The rapid keys (`rapid` lists in `read_128b-output.txt`: Chrome high 22.1 – 79.4 20.5, low 74.8 – 84.9 12.0; Firefox high 22.1 – 76.6 85.0, low 80.6 – 79.9 80.3; `–` = the caret did not move inside that key's own window) are printed by the reader; the task's criteria do not list the rapid clause, and I did not judge it.
- **First run, host-segment cell `NOT_JUDGED`** — exactly the state the precedent hit on `abe93f45…`. `report.json` → `runs[].hostseg.put.puts`: two PUTs in both browsers. The first (the manual save the key was typed into) was held and answered normally (Chrome held 317433 → answered 320499 ms; Firefox 321760 → 324824 ms); a second PUT was held about 1.13 s after the first was answered (Chrome 321627, Firefox 325956 ms) and was still outstanding when the arm ended (`out: 1`). Cause unverified (the precedent's reading, the autosave of the key typed during the save, was not checked here either).
- **Rerun, as the task's disposition says** — only the two arms once, instrument and verdict function unchanged: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/134/guard/131b-128b-hostseg-rerun --browsers chrome,firefox --arms hostseg,hostseg-red` (exit 0; 2026-10-12 23:47:46–23:48:48Z; served page, buildId and host version as above). One PUT per arm this time (`hostseg.put.puts` has one entry, `out: 0`).

| | Chrome | Firefox |
|---|---|---|
| host-segment cell (`runs[].hostseg.judged`) | **PASS**: PUT held 3249 ms, key at 3562 ms (inside the hold), its caret moved 24.6 ms after the key, caret band fresh 39.5 ms after the key, PUT answered 6313 ms, `heldPaints` 0 | **PASS**: held 3138, key 3452, caret moved 22.0 ms, band fresh 37.5 ms, answered 6202 ms, `heldPaints` 0 |
| red control (`runs[].hostsegRed.judged`) | **FAIL**: band fresh 2764.4 ms after the key, `heldPaints` 1 | **FAIL**: 2777.4 ms, `heldPaints` 1 |

So on `6470dec0…` the host-segment clause holds (in the rerun) and its red control is red (in both runs). `read_128b-output.txt` in the rerun directory is empty: that reader prints the high/low arms only and this run has none. The rerun is a second sample of one cell, taken because the first sample was `NOT_JUDGED`; I did not run anything else more than once.

Output files: `131b-128b/` — `probe.out`, `report.json`, four screenshots, `judge_131b-output.txt`, `read_128b-output.txt`, `started-utc.txt`, `ended-utc.txt`; `131b-128b-hostseg-rerun/` — `probe.out`, `report.json`, `read_128b-output.txt` (empty), `started-utc.txt`, `ended-utc.txt`.

## G2 — 121-B (selection, then Backspace / Delete): PASS in all four cells

Files: `../../121/0.2.16-134-binding.txt` (before 2026-10-12T23:49:34Z, after 23:50:53Z; both lines carry the page sha256 `6470dec0…`, all four exits 0), `../../121/0.2.16-134-<browser>-<key>.json` and `.stderr` (all four stderr files are empty). Command per cell: `python3 findings/evidence/121/select_delete_probe.py <browser> <Key>` (standalone page built from `dist/`, `boundaries.odt`, a drag inside "M01 plain alpha", one real key; no host involved), run sequentially. Criterion (SPEC-M3-autosave §9.13): shape `range-single` before the key, after the key 「刪除選取 N ms」, `ready`, generation 1 → 1, revision 0 → 1, no toast, first paragraph `M01 alpha`.

| Cell | shape before | latency after | state | generation | revision | `toasts` | first paragraph | Verdict |
|---|---|---|---|---|---|---|---|---|
| Chrome Backspace | `range-single` | 「刪除選取 15 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Chrome Delete | `range-single` | 「刪除選取 16 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Backspace | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Delete | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |

Compared with `0.2.15-132-*.json` and `0.2.13-131fix-*.json`: after masking the `定位游標 N ms` figure of the `before` field, three of the four pairs are byte-identical to both earlier sets (Chrome Backspace, Firefox Backspace, Firefox Delete). **One pair differs in a number**: Chrome Delete reads 「刪除選取 16 ms」 here against 14 ms in both earlier sets (the criterion names no threshold for N; every field the criterion names is as required). The `before` latency of Chrome Backspace reads 「定位游標 5 ms」 here (33 / 36 ms earlier); it is the masked figure and not part of the criterion. The `after.toast` field reads 「已開啟 f.odt」 in all four files (the toolbar's last message, the same in the earlier sets); the criterion's "no toast" is the `toasts` list, empty in all four.

## G3 — 129-B (arrow keys after a selection): PASS

Pin commit (its own, before the run): `c0d507cc` — `FINAL_PAGE_SHA256` in `wasm_sdk_probe/tools/probe_129_m4_wasm.py` from `abe93f45…` to `6470dec0…`, the old value kept in the comment above it; nothing else in the file changed (`git diff` was 3 insertions, 1 deletion). Round directory `../../129/final/round-20261012T235136Z/`. Driver `tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1` run from `wasm_sdk_probe/` (same docs directory and arguments as the precedent: round label 4, 1 round; exit 0). Chrome 23:51:36–00:04:02Z, Firefox 00:04:02–00:17:35Z (driver ended 00:17:45Z), load 0.65 0.68 0.53 at the start (`machine-at-start.txt`), `pgrep -c chrome` = 1 (Codex's crashpad handler). Analysis: `python3 wasm_sdk_probe/tools/analyze_129_m4.py round-20261012T235136Z round-20261012T092119Z` run in `findings/evidence/129/final/`, exit 0, stdout in `analysis-stdout.txt` (the analyzer also wrote `analysis.json` and `summary.md` in the round directory, as in earlier rounds). One extra invocation, not in the task: the same analyzer against `round-20261012T183200Z` (the previous page's round), stdout in `analysis-vs-183200Z-stdout.txt`, run first so the final `analysis.json`/`summary.md` are the task's form. The page under test is `dist/`; the red control is 0.2.12's page from `build/archive/host-0.2.12-engine-45cdcedfc0fe7e61/`.

`preflight.final` in both `report-chrome.json` and `report-firefox.json`: `pageUnderTestSha256` `6470dec0cb0e20db46d33d46bfc565893f542b79f7317fcbc421653a562bb94b` (`pageUnderTestIsFinal: true`), `redControlSha256` `8909564eb2316afa6de7868a08b61d27219fabdf49f37326fee0dda2977bd401` (`redControlIs0212: true`).

| Clause (§9.4 129-B, as in `../../129/final/README.md`) | Chrome | Firefox | Verdict |
|---|---|---|---|
| 42 brief cells land where native `ref` lands | old 12 = native exact 12/12; S1–S5 30/30 by rule, 28/30 exact (`s1/Down` 195 vs native 201, `s1/End` 194 vs 200: WASM wrap offsets, S1 lines start 101/195/292 vs native 101/201, the same two cells as in every earlier round) | same | PASS |
| toolbar shape after the key is `collapsed` | 54 of 54 m4 arms `collapsed` | 54 of 54 | PASS |
| 0 toasts | analyzer: `toasts in m4 arms … 0 arms []`; pill `stopped` in none | same | PASS |
| key → move done < 400 ms | max 284.4 ms (moving keys 81.3–84.8; the 7 arms whose key does not move the caret 282.2–284.4) | max 288.5 ms (moving 83.7–86.8; the 7 non-moving 285.7–288.5) | PASS |
| Shift+arrow does not move, no toast | `shift` arms: `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret`/`sameSelection` true | same | PASS |
| red control refuses | 3 of 3 `red-*` arms `refused: true` with the `EDITOR_FORMAT_GESTURE_UNSUPPORTED` toast | 3 of 3 | red, as required |
| L-129 cells (recorded, not judged) | `s1d`/`m1d` Down follow native `ref` (`dragDownFollowsRef: ["s1d", "m1d"]`) | same | recorded |

Cross-checks printed by the analyzer: Chrome against Firefox landing index equal in 54/54 cells; each browser against `round-20261012T092119Z` (the d761f1ce round): 54 compared, 0 differ, wrap offsets the same; against `round-20261012T183200Z` (the abe93f45 round): 54 compared, 0 differ, wrap offsets the same.

## G4 — 122-B / C2 typing latency: PASS (both judges exit 0), with one transient to read

Pin commit (its own, before the run): `e3b9cbfd` — in `findings/evidence/c-prime/c2/judge_c2.py` and `findings/evidence/typing-latency/judge_p2.py` only the `PAGE = "…"` line changed, from `abe93f45…` (kept in a comment above) to `6470dec0…` (`git diff` before the commit: 6 insertions, 2 deletions, all comment lines and the two `PAGE` lines). A consequence, not checked further: the reports in `findings/evidence/132/guard/c2/` (page `abe93f45…`) are now REFUSED by the default pin of those two judges.

Chain: `c2/chain-c2.sh`, a copy of `findings/evidence/132/guard/c2/chain-c2.sh` with two lines changed (`diff` shows exactly these): `E=` (output directory) → `findings/evidence/134/guard/c2`, and `PAGE=` → `6470dec0cb0e20db`. The second one is not an output directory; I changed it for the same reason as in the precedent: the script's first check refuses to run when `dist/e2-editor-app.js` does not hash to its `PAGE`, and the task did not name that line. The header comment of the copy still reads "C2 on the final C′ page (dist 8909564eb2316afa …)" (left as it was). Structure unchanged: ratio 2 wide (`probe_typing_latency_view.py --dpr 2 --window 1400x1000`, owner gap 80 / 20 chars and gap 200 / 10 chars), ratio 1.5 wide (recorded only, owner gap 80), ratio 1 (`probe_typing_latency.py`, owner gap 80, owner gap 200, boundaries gap 200), Chrome first then Firefox, one cell at a time. Started with `nohup` (detached), waited for `DONE`.

Desk at the start (`c2/desk-at-start.txt`, 2026-10-13T00:18:38Z): `pgrep -c chrome` = 1 — the only match is Codex desktop's `chrome_crashpad_handler`, not a Chrome browser; `pgrep -fc '/chrome/chrome( |$)'` = 0 (this is the count the chain script prints as `chrome-procs 0`); `/proc/loadavg` 0.56 0.58 0.59 (the chain's own START line, 5 s later: 0.68 0.60 0.60); the owner's Firefox was open (it is not Chrome; the precedent's desk had no Firefox note). `chain.txt`: `START tree e3b9cbfd dist 6470dec0cb0e20db view 1412e4c863de6fcb probe dbad93c0dcf27fbf`, 12 cells all `exit 0`, `DONE` 2026-10-13T00:23:05Z (started 00:18:43Z). Tool hashes equal the ones both judges bind.

Judges, run as the C2 README did with `--dir` at this directory, output in `c2/judge-output.txt` (the file also carries my `$ …` command line and `exit N` line for each judge):

- `python3 findings/evidence/c-prime/c2/judge_c2.py --dir findings/evidence/134/guard/c2` → last line `PASS: both browsers, every cell`, **exit 0** (ratio 2 wide).
- `python3 findings/evidence/typing-latency/judge_p2.py --dir findings/evidence/134/guard/c2/ratio-1` → last line `PASS: both browsers, every cell`, **exit 0** (ratio 1, P2's cells).

| Cell (judge) | Chrome | Firefox | Verdict |
|---|---|---|---|
| ratio 2 wide, owner gap 80: every key committed / on screen | 20 of 20 / 20 of 20 | 20 of 20 / 20 of 20 | PASS |
| ... on-screen median (needs < 70 / < 90) and max (< 150) | 30.5, **max 148.7** | 30.7, max 55.2 | PASS (Chrome max: 1.3 ms under the limit, see below) |
| ... (a) every commit < 2 × gap (< 160) | max 140.3 | max 35.5 | PASS |
| ... (b) median commit < gap (< 80) | 19.7 | 23.2 | PASS |
| ratio 2 wide, owner gap 200: every key committed / on screen | 10 of 10 / 10 of 10 | 10 of 10 / 10 of 10 | PASS |
| ... on-screen median (< 70 / < 90) and max (< 150) | 32.1, max 42.8 | 33.6, max 42.8 | PASS |
| ratio 2 wide (ii), recorded not gated | gap 80 76.6 ms, gap 200 68.2 ms | gap 80 60.6 ms, gap 200 74.1 ms | recorded |
| ratio 1 (P2), owner gap 80: committed / on screen | 20 of 20 / 20 of 20 | 20 of 20 / 20 of 20 | PASS |
| ... on-screen median (< 70 / < 90), max (< 150) | 25.0, max 45.4 | 26.1, max 48.8 | PASS |
| ... (a) max commit (< 160); (b) median commit (< 80) | 36.1; 18.3 | 38.9; 20.7 | PASS |
| ratio 1 (P2), owner gap 200: committed / on screen | 10 of 10 / 10 of 10 | 10 of 10 / 10 of 10 | PASS |
| ... on-screen median (< 70 / < 90), max (< 150) | 29.9, max 39.3 | 33.5, max 39.5 | PASS |
| ratio 1 (P2), boundaries gap 200: committed / on screen | 10 of 10 / 10 of 10 | 10 of 10 / 10 of 10 | PASS |
| ... commit median (≤ 10) | 4.2 | 3.6 | PASS |
| ratio 1.5 wide, owner gap 80 (recorded only, no judge): commit median / max, on-screen median / max | 19.1 / 31.7, 24.0 / 41.5 | 22.2 / 36.0, 27.3 / 44.2 | recorded |

**The transient (read, not judged).** In Chrome, ratio 2 wide, owner gap 80, the keys with index 9–12 were slow: `rows[]` in `c2/c2-candidate-chrome-owner-gap80.json` has `revisionMs` 140.3, 88.5, 41.8, 37.9 and `onScreenMs` 148.7, 97.1, 50.8, 49.7 for i = 9, 10, 11, 12, and 14.9–31.7 / 22.9–43.4 for the other 16 keys. The judge's backlog line shows `b_i` 55.6 and 7.0 at i = 10, 11 (all other keys 0.0). The judge's clauses hold (a: 140.3 < 160; on-screen max 148.7 < 150), but the on-screen margin is 1.3 ms. The same cell in `../../132/guard/c2/` (page `abe93f45…`) had `onScreenMs` max 41.1 and commit max 33.8, backlog 0.0 for all keys; every other cell here (including the Chrome gap-200, ratio-1.5 and ratio-1 cells, which ran in the minutes right after this one) has medians and maxima within about 5 ms of that run's values. I have no cause (unverified: I did not look at what else the machine was doing at 00:18:50Z; load at the start was 0.56–0.68), and I did not re-run the cell: the task says to run the chain once and report. The Firefox half of the same cell has backlog 0.0 for all 20 keys.

## Anything odd, and what was not checked

- G1: the host-segment cell was `NOT_JUDGED` (two PUTs) in the first run, in both browsers, as on `abe93f45…`; the cause is unverified. The one bounded rerun of only that cell (`hostseg,hostseg-red`) gave PASS in both browsers with the red control red. The cell has therefore been sampled twice; the first sample is not a PASS.
- G2: Chrome Delete reads 「刪除選取 16 ms」 against 14 ms in `0.2.15-132` and `0.2.13-131fix`; the criterion fixes no threshold for N and every field it names is as required.
- G4: the Chrome ratio-2 gap-80 cell has a four-key slow stretch (see G4); the judge passes it, with 1.3 ms of margin on the on-screen max. Not re-run, cause not known.
- G4: the chain copy changed its `PAGE=` line as well as its output directory (see G4).
- `static.shellBundle` in the G0/G1 reports is `exit 1` ("manifest is out of date … changed=['web/e2-editor-app.js']", `e2/editor-shell-v2-bundle-v64.json`): the shell generation is not frozen for this page; the probe records it and does not stop on it. Not investigated further.
- G0, G1: `ended-utc.txt` / `started-utc.txt` and the trailing `probe exit N` line in `probe.out` are mine (a wrapper I used to detect the end of a detached run); the probe's own output is the rest of `probe.out`. `judge-output.txt` in `132-b/` ends with an `exit 0` line I appended.
- G3: the docs path given to `run_probe_129_final.sh` is `../findings/…` (as in the precedent, because the script `cd`s into its argument).
- At the start of G3 I ran `analyze_129_m4.py --help` by mistake, expecting an argparse usage; the script takes positional arguments, so it tried to write `--help/analysis.json` and failed with `FileNotFoundError` before creating anything (`git status` afterwards showed no stray file).
- Not run, by instruction: `make`, `package_m3_engine.py`, `ddev occ upgrade`, anything in `~/Projects/Nextcloud_Apps`; nothing was committed or changed there (host HEAD `568608c`, `info.xml` still the uncommitted 0.2.16 edit — checked at the start only, not re-checked at the end). `wasm_sdk_probe/web` and `dist` untouched (`dist/e2-editor-app.js` hashed `6470dec0…` before G0 and in the G2 binding file's two lines and in the G4 chain's START line).
- I did not read the 134 page diff or SPEC-M3-held-key §14; the criteria are the ones the task and the precedent state.
