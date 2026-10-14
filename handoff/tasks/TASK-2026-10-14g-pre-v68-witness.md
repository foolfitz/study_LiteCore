# Task 2026-10-14g: 129-B witness on the v68 candidate bytes (finding 140's placeCaret change), before the freeze

This task repeats task 10-14c (`handoff/tasks/TASK-2026-10-14c-pre-v67-witness.md`; read it and its evidence `findings/evidence/link-batch/v67-witness/README.md`). It runs on new bytes. Since v67, exactly one product file differs: `editor-shell-v2/narrow-editor-v2-session.js`, now `fc5ac883…` (finding 140, `6c761117`: `placeCaret` asks the engine first). The client additions in `narrow-editor-v2-client.js` and `paragraph-editor-client.js` are the other part of that commit. The page `web/e2-editor-app.js` is unchanged (`7815e16c…`), so `FINAL_PAGE_SHA256` needs **no re-pin**.

The question: does 129-B (54 click and move cells) still read exactly as it did on v66 and v67, now that every click goes through the engine's `editorPlaceCaretV2`?

## Steps

- **W0.**
  - Run `make -n e2-c-assets` and check that it prints only `cp` lines (or nothing to do). Then run `make e2-c-assets`.
  - Record the sha256 of the five source/dist pairs and check that each pair is equal. The session must be `fc5ac883…`.
  - Check that `check_e1_c_bundle_intact.py` prints `"intact": true`.
  - Check that the page still loads `e2-editor-v19`.
- **W1.** Run 129-B `--final` exactly as 10-14c's W1 did (`tools/run_probe_129_final.sh ../findings/evidence/129/final/round-20261012T092119Z/docs 4 1`), Chrome then Firefox. The criterion is the same as 10-14c:
  - `preflight.final` shows the page `7815e16c…`;
  - the red control behaves as before;
  - 54/54 cells, with 0 differing from the reference rounds, and **also 0 differing from `round-20261014T022210Z`** (the v67 witness).

  Report any differing cell verbatim.

## Rules

They are the same as 10-14c:
- The only `make` allowed is `e2-c-assets`.
- Do not edit `web/`, `editor-shell*/`, `sdk/`, `src/` or the `Makefile`.
- No host, no freeze, no `--write`.
- One browser job at a time.
- Before each browser step, check that the KWallet `Locked` property is not `b true`, record `pgrep -c chrome`, and check that nothing of ours is running.
- A red cell is recorded and the next step goes on; no check is changed.
- Commit only your own paths (`git commit -- <paths>`). Commit messages are in zh-TW and end with your model's `Co-Authored-By` line; never a `Claude-Session` line.

## Output

- `findings/evidence/link-batch/v68-witness/README.md` (English).
- Final reply: a `## SUMMARY` of at most 15 lines.
