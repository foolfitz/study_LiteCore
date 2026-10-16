# Item 2: the Chrome re-smoke of M11 after the `#` fix (rerun-2)

**A smoke, a development run: never judged.** Runner as committed in `bd8a97a7` (`runnerSha256` `11e7b2fb…`) [observed], Chrome, N=1, arm `m11`, under the S-9 lock (02:43:25 to 02:43:43, 2026-10-17).

- M11-dirty: `false` → `true`. M11-cancel, both episodes: the dialog closed, the textarea emptied, no request, `enqueueCount` unchanged, the document unchanged; the positive control made one `insertText` [observed].
- **R3 still open**: `typedAsArm: false` in both episodes, the textarea held 7 UTF-16 units before 取消/Escape, not the 9 of `# 打字 A\nB` [observed]. The witness for the next fix.
- Diagnosed with `diag-keys-sequence.py` (development, under the lock): typing the whole sequence and reading the value after each key gave `#`, `# `, … `# 打字 ABC`, then `# 打字 AB` after Backspace, and **no change after ArrowLeft and Enter**; the final value was `# 打字 AB` both key by key and with no pauses [observed]. S-4's `v21_input.key("Enter")` sends a raw keydown with key code 13 and no `char` event; in a textarea Chrome inserts the line break only with the character [inferred]. The 7 units against this diagnostic's 8 are not explained; the next run records the value itself.
