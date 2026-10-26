# S5 preparation 03 (uncounted): both browsers under the run-03 type oracle

Chrome then Firefox, 11 S5 cells each, 22/22 PASS, runner exit 0, 2026-10-27 07:08:39–07:16:36 (+0800), 7 min 56 s. Command (from `wasm_sdk_probe/`, output in `runner.command-output.txt`):

```bash
timeout 3600 python3 -I tools/run_v23_feature_selection.py --population s5 --preparation-only --keep-going \
  --case-id 'shift-Left@caret-mid/backspace' --case-id 'shift-Right@caret-mid/type' --case-id 'shift-Down@caret-mid/delete' \
  --case-id 'shift-Up@cell-end/backspace-twice' --case-id 'shift-Home@caret-mid/delete-before-and-after' \
  --case-id 'shift-End@wrap-line-end/backspace-before-and-after' --case-id 'shift-Right@range-fwd/delete' \
  --case-id 'shift-Left@range-kbd/delete-twice' --case-id 'shift-Left@range-one/type' --case-id 'shift-Home@caret-mid/type' \
  --case-id 'shift-Up@caret-mid/type' --output ../findings/evidence/link-batch-v23/feature-protocol/s5-prep-03
```

Instrument state: HEAD `13981a0d` (the S5 plan binds native run-03's type saves, `reader-03.json` `30530678…0706`). `report.json` has `foreignCpu.ok: true`, `postConfig` equal to `config`, no `nonpassing`. Raw cells are `.json.gz` written with `gzip -9 -n` (the same bytes prep-02 used; each decompresses to its runner-hashed original).

Cells: the eight of `s5-prep-02` (as the handoff's step 2 asks, now also on Firefox) plus three type cells that exercise each branch of the new oracle: `shift-Left@range-one/type` (native, `settle-only`), `shift-Home@caret-mid/type` (Home/End type with a native save) and `shift-Up@caret-mid/type` (settled-WASM type).

| Cell | Reference (both browsers) | Native order witness | Overlapping |
| --- | --- | --- | --- |
| shift-Left@caret-mid/backspace | native | — | yes |
| shift-Right@caret-mid/type | native | selection-before-x | yes |
| shift-Down@caret-mid/delete | settled-wasm | — | yes |
| shift-Up@cell-end/backspace-twice | settled-wasm | — | yes |
| shift-Home@caret-mid/delete-before-and-after | native | — | no |
| shift-End@wrap-line-end/backspace-before-and-after | settled-wasm | — | no |
| shift-Right@range-fwd/delete | native | — | yes |
| shift-Left@range-kbd/delete-twice | native | — | yes |
| shift-Left@range-one/type | native | settle-only | yes |
| shift-Home@caret-mid/type | native | selection-before-x | yes |
| shift-Up@caret-mid/type | settled-wasm | — | yes |

`shift-Right@caret-mid/type` failed in prep-02 under the withdrawn run-01 oracle; it now passes against run-03's witnessed save in both browsers. This is the first Firefox S5 execution (ruling 2's and ruling 3's Firefox preparation). Per-cell wall time from file times: Chrome 14–19 s, Firefox 22–30 s; cells with a settled-WASM arm take the longer end.

Uncounted: preparation never closes S5.
