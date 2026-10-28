# Witness 02: the v24 Enter replay check's oracle and judge (ruling 1 Addendum 1 §3), before its first run

Tool `wasm_sdk_probe/tools/check_v24_shift_enter.py` (new). Its `paragraph_texts_with_breaks` is E1's function text verbatim (checked by AST source segment against `da556907`'s runner: identical); E1 itself stays reverted and the shared runner is untouched.

- **(i)** `controls.py` = witness-01's with the function imported from the new tool → `results.json` `CONTROLS_HOLD`, every row (old oracle True, True, False, False; new True ×4; n1–n4 False, same flattened paragraphs) identical to witness-01.
- **(ii)** `judge_reds.py` → `judge-reds.json`: the tool's own arm judge on the four diagnostic-02 Shift-arm after-saves → PASS ×4 (v23's span-free XML included); on v24-1 with the break removed → FAIL.
- **(iii)** same script: `--repetitions 0` → refused (argparse error, exit 2) before any output exists; the tool's `main()` with a CDP-less session stub → `NOT_ESTABLISHED`, exit 1 — never PASS.

`REDS_HOLD`, 4/4; with (i), the oracle and its judge are shown red-capable before the check judges anything.
