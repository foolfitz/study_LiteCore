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
