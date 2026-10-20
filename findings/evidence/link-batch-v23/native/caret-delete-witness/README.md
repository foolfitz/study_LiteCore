# Caret-delete witness, native: VERDICT G-HOLDS (2026-10-20)

The criteria are `ARMS.md`, pinned at `e129ac42` before this run. The reader is `read_g.py`.

| item | value |
|---|---|
| run | `run_arms.py --arms-set g --modes uni1,seq --runs 5`, 2026-10-20 08:40–09:04Z (16:40–17:04 local) |
| processes | 50, all exit 0 (`out/run-log.jsonl`, `out-runner.log`) |
| binary | sha256 `b857a9b0…` (`build.txt`); core `native-lok-26-8` (671c848b) |
| reading | `out/reader-output.txt` |

| arm | uni1, every one of 5 rounds | seq, rounds 1–5 (recorded, not judged) |
|---|---|---|
| g1: 25 × Backspace through `_` | lost 25, **paired 25**, undo-only **19** | paired 0, 0, 1, 0, 0 |
| g2: 25 × Delete through `_` | lost 25, **paired 25**, undo-only **19** | paired 1, 0, 0, 1, 2 |
| cjk: 25 × Backspace through 25 distinct CJK | lost 25, **paired 25**, undo-only **25** | paired 1, 1, 1, 0, 0 |
| t1 (control): Backspace at a paragraph start after a table | lost 0, paired 0, undo-only 0 | 0 |
| e1 (control): Delete at the document end | lost 0, paired 0, undo-only 0 | 0 |

What the table shows:
- **G-W holds in every uni1 cell.** The paired decider counts exactly the characters the saved document lost.
- **G-red holds in every uni1 cell of g1 and g2.** The undo-only decider misses 6 of 25 every round: the payload is byte-identical after the 19th character.
- **The a11y read at return already carries the key's effect under uni1**, in every op of every round. This is what ruling 2 §2.1 item 5 asked to have measured: until now it rested on reading the source only.
- **seq** in the threaded topology reads mostly before the posted key has run, so both deciders see little. That is the reason the spec's decider is for C only.

## What this changes

- **The precondition of spec §15.1 holds.** The paired decider may be written into the diagnostic engine code (§5.4 as amended by §15.1), with the a11y-available guard from the source check of ruling 2.
- **The hole is narrower than ruling 2 §1 said. In cjk, undo-only is 25/25 in every round.**
  - The shortened undo comment keeps the newest characters in front. Deleting distinct characters changes it on every press.
  - Only a run of identical characters saturates it: fill-in lines such as `____`, `……`, `－－－` or `0000`.
  - Ruling 2 §1's sentence about CJK sentences is contradicted by measurement. The product-path arm it wrote ("25 Backspaces through a 25-character CJK run", §2.1) would not reach the hole; it must include a run of identical characters. This is appended to the spec as §15.7.
