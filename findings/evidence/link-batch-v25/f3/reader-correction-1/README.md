# F3 reader, correction 1, exercised before run-02 (2026-10-29)

Spec v25 section 16.1. `wasm_sdk_probe/tools/read_v25_f3.py --rule correction-1` (now the default); `--rule pinned` keeps section 16 as written.

- `--rule pinned` on run-01 reproduces `../read-01.json` byte for byte (checked with `cmp`; not stored twice).
- `run-01-under-correction-1.json`: the corrected rule applied to run-01's reports holds (Chrome P 4, no-regression 33, same-or-pass 4, excluded 4, recovery-pairing 1). **This is a reader exercise, not F3's verdict**: run-01 was taken before the correction was written (section 16.1, CLAUDE.md section 9 (1)). F3's verdict is run-02's read.
- `run-01-self-test.json`: on that input, all eleven mutations red, including the four new ones (pairing `held` false; the record's `noticeAction` disagreeing with the check; the sentinel PASS while bulleting PASSes; the record missing). The `regress` mutation now skips the sentinel (it was the first v24-PASS candidate, which would have tested the pairing rule instead of no-regression).
- `v24-as-v25.json`: v24's T4 given as v25, under correction 1: red on exactly the six P cells, as under the pinned rule (v24's own pairing reads bulleting FAIL / notice PASS, held, consistent).
