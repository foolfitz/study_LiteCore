# Caret-delete witness, native (SPEC-M3-ordered-commands §15.1; fable ruling 2 §2.1 item 5): the arms and the reading

Written and committed **before the counted run**. The smoke under `smoke/` is one round (`--rounds 1`, not a counted reading) and decides nothing.

## Why

Spec §5.4 (as pinned) proves a caret delete by the `.uno:Undo` payload at return. Writer merges a run of single-character deletes into one undo action, and its comment saturates. So after about 20 equal characters, the payload stops changing (`../../review/disposition-1/grouping/`). Ruling 2 adopts a paired witness: the undo payload, plus the focused paragraph read synchronously at return, guarded to mid-paragraph positions. It requires a native measurement before any §5.4 engine code.

## What runs

| item | value |
|---|---|
| harness | `../ordered-commands/tool/oc_native.cpp`, with the opt-in `OC_A11Y=1` reads (`build.txt`) |
| runner | `run_arms.py --arms-set g --modes uni1,seq --runs 5` |
| fixtures | `../ordered-commands/fixtures/` (adds `underscores` and `cjk25`; the existing fixtures are byte-identical, `SHA256SUMS`) |

The arms:

| arm | fixture | the step |
|---|---|---|
| g1 | `Name: ` + 30 `_` | trigger End; 25 × Backspace |
| g2 | same | Right ×5, trigger Right; 25 × Delete |
| cjk | 25 distinct CJK characters | trigger End; 25 × Backspace |
| t1 (control) | a one-row table, then `After the table` | Down, End, trigger Home; 3 × Backspace. Writer restores the caret at a paragraph start after a table |
| e1 (control) | `abcd` | Ctrl+End, Left, trigger Right; 3 × Delete at the document end |

Each op records `.uno:Undo` and `getA11yFocusedParagraph` immediately before its call (`atStart`) and at its return (`atReturn`), in the same poll, with nothing in between.

## The reading (`read_g.py`; its docstring is the definition)

- **The deciders**, per op:
  - **undo-only** (spec §5.4 as pinned);
  - **paired** (ruling 2 §2.1 item 3).
- **The oracle**, independent of both: the characters the saved document lost against its fixture.
- **G-W** (hard, form 1 per `uni1` cell): paired = lost. That is 25 for g1, g2 and cjk, and 0 for t1 and e1.
- **G-red** (non-vacuity, per `uni1` cell of g1 and g2): undo-only < lost. Grouping must be reached; if it is not, the reading is NE.
- **G-a11y:** every op has both a11y reads, parseable.
- **seq cells are recorded, not judged.** In the threaded topology the at-return read can precede the posted key; the smoke shows paired 0 on g1 seq.
- **Cleanliness** as the fixed readers: one run-log entry with exit 0, `done`, no fatal, env as asked. An unclean cell gives NE, never FAIL.
- **Verdicts:**
  - **G-HOLDS**: every `uni1` cell clean, G-W everywhere, G-red on g1 and g2;
  - **G-FAILS**: a clean `uni1` cell where G-W fails;
  - otherwise NE.
- **N = 5.** Fewer is not a counted reading (exit 2).

**The reader's red cases** (`smoke/self-test.txt`, 7/7):
- a stale at-return read gives G-FAILS;
- t1's content changed at position 0 still reads noop (the guard);
- the same with the caret inside gives G-FAILS;
- no a11y read gives NE;
- every undo payload differing (grouping not reached) gives NE;
- a duplicate run-log entry gives NE.

## Default if G-HOLDS is not reached (ruling 2 §2.1 item 6)

- §5.4 is not implemented.
- Caret deletes stay on today's barrier path.
- L-C-number-or-indent is re-registered as open.

## Seen on the smoke, before the counted run (one round; recorded, not a reading)

- **g1 and g2 `uni1`:** paired 25 = lost 25, while undo-only gives 19. The red case is as predicted.
- **cjk `uni1`: undo-only 25 = lost 25. The undo payload changed on every press.**
  - The shortened comment keeps the newest characters at its front. Deleting distinct characters changes it every time, so only a run of **equal** characters saturates it: `____`, `……`, `----`, `0000`.
  - Ruling 2 §1's sentence "中文…一句二十幾個字…第 20 下起…會回答「什麼都沒發生」" is therefore **contradicted by this smoke**. The hole is runs of identical characters (fill-in lines), not CJK sentences.
  - The ruling's product-path arm ("25 Backspaces through a 25-character CJK run", §2.1) would not reach the hole as written. The correction is appended to the spec after the counted run, with the counted numbers.
- **The controls t1 and e1:** 0 = 0 in both modes.
