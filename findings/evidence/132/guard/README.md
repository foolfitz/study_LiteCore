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
