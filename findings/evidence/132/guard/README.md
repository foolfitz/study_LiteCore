# Finding 132 final page — 132-B on the final bytes and the "must not break" set

Task: `handoff/tasks/TASK-2026-10-13-132-guard-chain.md` (SPEC-M3-held-key §5.2, §5.3). Mechanical runs of existing instruments and judges on one page; nothing here changes a check, a judge or an instrument except the two pin edits the task names (G3, G4), each its own commit. Facts only; anything not checked is marked unverified. All times UTC.

## Conditions (common)

- Page under test: `wasm_sdk_probe/dist/e2-editor-app.js` sha256 `abe93f4575c7797db97462f1f0e3a71cf5fc4063205cd6d5877093ca1c248fcf` (= `web/`, checked with `sha256sum` before step 1).
- Host `litecore` 0.2.15 (`appinfo/info.xml`, uncommitted on purpose; host commit `237f2cb`, `hostDirty: ["M appinfo/info.xml"]`), engine package buildId `daf70d77b8facb4b` (`engine/MANIFEST.json`, `source.page` = the page above, `source.profile` e2-editor-v19). Every probe report's `static` and `staticAfter` say `servedPage` = the page above, `buildId` `daf70d77b8facb4b`, `hostVersion` `0.2.15`.
- Chrome 151.0.7922.169, Firefox 157.0.1, one browser at a time, one job at a time; before each browser step `pgrep -af "probe_|check_m3|run_e2_c"` showed none of ours.
- Not done by me, by instruction: no `make`, no edit of `wasm_sdk_probe/web` or `dist`, nothing in `~/Projects/Nextcloud_Apps`.

## G0 — 132-B on the final page: PASS

`132-b-final/` (own README). 2026-10-12 17:41:31–18:15:19Z. `judge_132b.py --page abe93f45…` exit 0 (`132-B PASS`, 12 of 12 holds, wash-control fills Chrome 5 / Firefox 9); `read_hold.py` exit 0. Commit `bcc469f7`.

## G1 — 131-B and 128-B (one probe run): 131-B PASS; 128-B single presses PASS, red control red, host-segment cell NOT_JUDGED

Directory `131b-128b/`. Command: `python3 wasm_sdk_probe/tools/probe_hand_test_0212.py --out findings/evidence/132/guard/131b-128b --browsers chrome,firefox --arms high,low,rapid20,hostseg,hostseg-red --rapid-rounds 6` (exit 0). 2026-10-12 18:16:43–18:28:21Z (Chrome 18:16:43–18:22:27, Firefox 18:22:27–18:28:21). At the start `pgrep -c chrome` = 1, load 0.38 0.63 0.87.

| Clause | Read with | Chrome | Firefox | Verdict |
|---|---|---|---|---|
| 131-B: 6 rapid20 bursts, each `deleted 20`, `refused 0`, `other []` | `judge_131b.py report.json --page abe93f45…` → `judge_131b-output.txt`, exit 0, last line `131-B PASS []` | 6/6 bursts `deleted 20 refused 0 other []` | 6/6 | PASS |
| 131-B: `persistent.differing == 0` in the four high/low arms | same | high 0, low 0 | high 0, low 0 | PASS |
| 128-B: every single press `staleAfterCaretMs` ≤ 40 ms | `read_128b_cells.py report.json` → `read_128b-output.txt` | high 14.8 17.7 18.8 16.0; low 17.4 17.9 16.3 17.9 | high 26.0 19.6 22.7 23.6; low 21.6 26.2 21.9 23.3 | PASS (max 26.2) |
| 128-B: host-segment cell holds | `report.json` → `runs[].hostseg.judged` | `NOT_JUDGED`, why `2 PUTs, 1 keys, save saved` | same string | **not judged** (see below) |
| 128-B: host-segment red control (`hostseg-red`) is red | `runs[].hostsegRed.judged` | `FAIL` (key 326185.8 ms, band fresh 2757.0 ms after the key, PUT answered 328935.5 ms, `heldPaints` 1) | `FAIL` (2755.6 ms, `heldPaints` 1) | red, as required |

- The rapid keys (`rapid` lists in `read_128b-output.txt`: Chrome high 72.5 – 80.1 22.7, low 75.1 – 83.3 9.6; Firefox high 79.9 – 78.2 85.4, low 79.2 – 79.9 79.2; `–` = the caret did not move inside that key's own window) are printed by the reader; the task's criteria do not list the rapid clause, and I did not judge it.
- **Host-segment cell: the probe's own verdict is `NOT_JUDGED`, not PASS.** The cell's verdict function (`hostseg_verdict`, unchanged) requires exactly one PUT; both browsers recorded two. `report.json` → `runs[].hostseg.put.puts`: the first (the manual save the key was typed into) was held and answered normally (Chrome held 317498 → answered 320561 ms; Firefox 321608 → 324669 ms); a second PUT began about 1.1–1.2 s after the first was answered (Chrome 321689, Firefox 325798 ms; the settled toolbar latency reads 「自動儲存 160 ms」 / 「自動儲存 269 ms」) and was still outstanding when the arm ended (`out: 1`, no `sent`/`answered`). The 128-B run on 0.2.13 (`../../128/final-0.2.13-131fix/report.json`) recorded one PUT per arm. I did not establish why this run has the second one (unverified; it looks like the autosave PUT of the key typed during the save, but I did not check the host or page code), and I did not re-run the step.
- For information only, **not the judge's verdict**: `hostseg-recompute-unofficial.txt` runs the unchanged `hostseg_verdict` on the same record with the unanswered second PUT removed. It prints `PASS` for both browsers (the key's caret band fresh 21.1 ms (Chrome) / 26.1 ms (Firefox) after the key, against the first PUT answered 3.06 s / 3.06 s after its hold), and the same `FAIL` as above for the red controls. This recompute is mine, made after reading the verdict; it is not a counted result.
- Output files: `probe.out` (`chrome done`, `firefox done`), `report.json`, the four screenshots, `judge_131b-output.txt`, `read_128b-output.txt`.

## G2 — 121-B (selection, then Backspace / Delete): PASS in all four cells

Files: `../../121/0.2.15-132-binding.txt` (before 2026-10-12T18:29:57Z, after 18:31:16Z; both lines carry the page sha256 `abe93f45…`, all four exits 0), `../../121/0.2.15-132-<browser>-<key>.json` and `.stderr` (all four stderr files are empty). Command per cell: `python3 findings/evidence/121/select_delete_probe.py <browser> <Key>` (standalone page built from `dist/`, `boundaries.odt`, a drag inside "M01 plain alpha", one real key; no host involved). Criterion (SPEC-M3-autosave §9.13): shape `range-single` before the key, after the key 「刪除選取 N ms」, `ready`, generation 1 → 1, revision 0 → 1, no toast, first paragraph `M01 alpha`.

| Cell | shape before | latency after | state | generation | revision | `toasts` | first paragraph | Verdict |
|---|---|---|---|---|---|---|---|---|
| Chrome Backspace | `range-single` | 「刪除選取 15 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Chrome Delete | `range-single` | 「刪除選取 14 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Backspace | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |
| Firefox Delete | `range-single` | 「刪除選取 9 ms」 | `ready` | 1 → 1 | 0 → 1 | `[]` | `M01 alpha` | PASS |

Compared with `0.2.13-131fix-*.json` (the d761f1ce page): `diff` of each pair, after masking the `定位游標 N ms` figure of the `before` field, shows no difference (the delete latencies 15 / 14 / 9 / 9 ms are the same as in 0.2.13-131fix). The `after.toast` field reads 「已開啟 f.odt」 in all eight files (the toolbar's last message, the same in both sets); the criterion's "no toast" is the `toasts` list, empty in all four.

## G3 — 129-B (arrow keys after a selection): PASS

Pin commit (its own, before the run): `d2349d03` — `FINAL_PAGE_SHA256` in `wasm_sdk_probe/tools/probe_129_m4_wasm.py` from `d761f1ce…` to `abe93f45…`, the old value kept in the comment above it; nothing else in the file changed. Round directory `../../129/final/round-20261012T183200Z/` (its own commit). Driver `wasm_sdk_probe/tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1` run from `wasm_sdk_probe/` (the docs path is `../findings/…` because the script `cd`s into its argument and `findings/` is at the repository root; round label 4, 1 round; exit 0). Chrome 18:32:00–18:44:24Z, Firefox 18:44:25–18:57:56Z, load 0.32 0.32 0.52 at the start (`machine-at-start.txt`), `pgrep -c chrome` = 1. Analysis: `python3 wasm_sdk_probe/tools/analyze_129_m4.py round-20261012T183200Z round-20261012T092119Z` run in `findings/evidence/129/final/`, exit 0, stdout in `analysis-stdout.txt` (the analyzer also wrote `analysis.json` and `summary.md` in the round directory, as in earlier rounds). The page under test is `dist/`; the red control is 0.2.12's page from `build/archive/host-0.2.12-engine-45cdcedfc0fe7e61/`.

`preflight.final` in both `report-chrome.json` and `report-firefox.json`: `pageUnderTestSha256` `abe93f4575c7797d…` (`pageUnderTestIsFinal: true`), `redControlSha256` `8909564eb2316afa…` (`redControlIs0212: true`).

| Clause (§9.4 129-B, as in `../../129/final/README.md`) | Chrome | Firefox | Verdict |
|---|---|---|---|
| 42 brief cells land where native `ref` lands | old 12 = native exact 12/12; S1–S5 30/30 by rule, 28/30 exact (`s1/Down` 195 vs native 201, `s1/End` 194 vs 200: WASM wrap offsets, S1 lines start 101/195/292 vs native 101/201, the same two cells as in every earlier round) | same | PASS |
| toolbar shape after the key is `collapsed` | 54 of 54 m4 arms `collapsed` (before the key: 48 `range-single`, 6 `range-cross`) | 54 of 54 | PASS |
| 0 toasts | analyzer: `toasts in m4 arms … 0 arms []`; pill `stopped` in none | same | PASS |
| key → move done < 400 ms | max 285.0 ms (moving keys 81.3–98.1; the 7 arms whose key does not move the caret 282.1–285.0) | max 299.8 ms (moving 83.7–86.8; the 7 non-moving 285.5–299.8) | PASS |
| Shift+arrow does not move, no toast | `shift` arms: `caretMoved: false`, revision `[0, 0]`, `toasts: []`; range arm `sameCaret`/`sameSelection` true | same | PASS |
| red control refuses | 3 of 3 `red-*` arms `refused: true` with the `EDITOR_FORMAT_GESTURE_UNSUPPORTED` toast | 3 of 3 | red, as required |
| L-129 cells (recorded, not judged) | `s1d`/`m1d` Down follow native `ref` (`dragDownFollowsRef: ["s1d", "m1d"]`) | same | recorded |

Cross-checks printed by the analyzer: Chrome against Firefox landing index equal in 54/54 cells; each browser against `round-20261012T092119Z` (the d761f1ce round): 54 compared, 0 differ, wrap offsets the same.
