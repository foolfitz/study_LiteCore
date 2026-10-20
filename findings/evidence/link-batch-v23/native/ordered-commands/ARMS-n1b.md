# N1, second run (`out-n1b/`): spec §9.1 as amended by §15.2 (ruling 2 §2.2, §2.5, §2.6)

Written and committed **before the run**. The first run (`out-n1/`, N1-HOLDS) stays as it is. Re-read with the fixed reader, it did not move (`../../review/disposition-1/rejudge-out-n1-with-fixed-reader.txt`).

## What changes from the first run

- **N1a's reply types drop `INVALIDATE_TILES`** (§15.2; ruling 2 §2.5).
- **An inline-format command's own state item is reply-dependent** (§15.2; ruling 2 §2.2). For a `U.uno:Bold`, `.uno:Italic`, `.uno:Underline` or `.uno:Strikeout` op, a late `STATE_CHANGED` with that same key is an N1a violation. Under CLAUDE.md §9 condition 1 it applies to this run and not to the first.
- **Three new arms:**
  - `d4i`, `d4u`, `d4s`: d4's shape (Shift+Right, Left, then the format at a collapsed caret), with `.uno:Italic`, `.uno:Underline` and `.uno:Strikeout`;
  - each sends the engine's explicit-true argument.
- **The on-time list is generated from the records** (`read_n1.py --on-time-list`; ruling 2 §2.2, form 2).
- **Readers and harness:**
  - the reader is `tool/read_n1.py` as committed at `1085726b`: F2/F3, N ≥ 5, one late red case per reply type, the format-state rule; self-test 19/19;
  - the binary is `cdda2f0f…` (`../object-click/build.txt`). Its `uni1`/`uni1ai` paths are those of `3fda8963…`; the additions are gated by `OC_A11Y` and `uni1f`.

## How it runs

- `run_arms.py --arms-set n1 --runs 5 --modes uni1ai --out out-n1b`: every arm in `uni1ai`.
- Then `--only join200 --modes uni1` into the same directory. There is one run-log entry per cell (F2).
- **N1c reads `join200` in both modes**, under the corrected label: NE means "some scheduler task ran before the poll; which one is not identified".

## Verdict

- **N1-HOLDS**: N1a PASS, N1b's control present, N1c PASS, every cell clean.
- **N1-FAILS**: an N1a violation in a clean cell, or N1c FAIL.
- Otherwise NOT-ESTABLISHED.

## Default if never run

The first run's N1-HOLDS stands for cursor, selection and command-result callbacks. The format-state rule and the on-time list rest on `a9`/`a10` (Bold only), registered as a one-time measurement (ruling 2 §2.2).
