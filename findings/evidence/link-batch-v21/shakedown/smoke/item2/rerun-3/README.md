# Item 2: the Chrome re-smoke of M11 after the Enter fix (rerun-3)

**A smoke, a development run: never judged.** Runner as committed in `085503c9` (`runnerSha256` `33007620…`) [observed], Chrome, N=1, arm `m11`, under the S-9 lock (02:45:08 to 02:45:27, 2026-10-17).

- M11-dirty: `false` → `true` [observed].
- M11-cancel, both episodes (取消 and Escape): the textarea held `# 打字 A\nB` before closing (`typedAsArm: true`), the dialog closed, the textarea emptied, no request at the worker, `enqueueCount` 1 → 1, revision 0 → 0, the saved document SAME as before; the positive control's `x` made one `insertText` and revision 0 → 1 [observed]. R3 is closed.
