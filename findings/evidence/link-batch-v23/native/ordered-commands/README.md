# Ordered commands, native arms (v23; fable ruling 1 §2.6): under unipoll, the engine's command sequences land in Writer's order

**Result: `VERDICT C-HOLDS`.**
- Every decision arm D1–D6 (seven arms with D2′) lands under unipoll exactly as Writer's own order does, 5/5 rounds.
- The threaded queued control reorders 5/5 in every arm.
- D8 holds: under unipoll a key's effect is there when the call returns; under the threaded queue it is not.
- 165 processes, all exit 0, load1 ≤ 0.39.
- Reader: `out/reader-output.txt`. Run log: `out/run-log.jsonl`, 2026-10-19T23:45Z – 2026-10-20T00:20Z (07:45–08:20 local).

Ruling 1 §2.6's decision rule: "D1–D6 Writer-order N/N under unipoll, controls reorder N/N, D8 holds both ways → **C is the candidate; the spec is written for C.**"

## What was run

The harness is `tool/oc_native.cpp`, a standalone native LOK client. Its build line, compiler and hashes are in `smoke/build.txt`. It ran against `native-lok-26-8/build/instdir/program`: core 671c848b, built from a clean upstream tree.

Each arm is a trigger key followed by a sequence of the calls today's engine makes. The sequence is issued in three modes, each round its own process:

| mode | topology | how the sequence is issued | role |
|---|---|---|---|
| `seq` | threaded LOK (the product today) | from the driver thread, each op settled (600 ms quiet) before the next | Writer's own order, **measured**, not written down |
| `q` | threaded LOK | inside the trigger's first cursor callback (the LOK main thread, busy), back to back | positive control: must reorder |
| `unipoll` | `SAL_LOK_OPTIONS=unipoll` | from the poll callback inside `Application::Execute`, back to back | candidate C |

The decision arms, with the landings the reader compared (paragraph text, list membership, indent, run weights, and the caret's line prefix and suffix):

| arm | sequence after the trigger | seq = unipoll (5/5) | q (5/5) |
|---|---|---|---|
| d1 | numbered P2 start: Ctrl+Home; Backspace | P2 still a list item, caret at the document start | P2 a list header (`Number On/Off` ran first) |
| d2 | `abcd`, caret at end: Left; `.uno:Delete` | `abc` | `abcd` (the Delete ran at the end first) |
| d2p | caret after `b`: Right; `.uno:SwBackspace` | `abd` | `acd` |
| d3 | caret 0: Right; `paste("x")` | `axbcd` | `xabcd` |
| d4 | `a` selected: Left; `.uno:Bold` (the engine's explicit true) | no bold run | `a` bold |
| d5 | caret at end: Shift+Left; `.uno:Delete` | `abc` | `abcd` |
| d6 | caret 0: click at offset 3; `paste("x")` | `abcxd`, caret after `x` | `xabcd` |

**D7** decides nothing. It records the content that SPEC-M3-link-batch.md §15.1 requires of the spec's fixed question 2: the `.uno:Undo` top for the user's own key at each position, 5/5 each.

| position | key | unipoll, at return | seq/q, at return | after the window |
|---|---|---|---|---|
| (i) in front of P1's bullet label (unshifted Left at the document start) | Delete | `Number On/Off` | none (still queued) | `Number On/Off` |
| (ii) document start, bulleted P1 | Backspace | `Number On/Off` | none | `Number On/Off` |
| (iii) document start, first-line indent | Backspace | `Apply attributes` | none | `Apply attributes` |
| plain P1, document start | Backspace | none | none | none |

**D8.** Two checks:
- d5's Shift+Left (the selected text) and d7i/ii/iii's key (the undo payload) show their effect **at return** under unipoll, 5/5 each. Under q they do not, 5/5 each.
- Under unipoll, every measured step's last op already reads at return what the settled window reads.

## Reader and red cases

`tool/read_results.py` applies these rules per arm:
- seq's rounds all land the same, or the arm is NE;
- q's rounds all land the same and differently from seq, or NE (the control does not reorder);
- unipoll's rounds all land the same and as seq, or FAIL;
- every cell is clean: exit 0, `done`, the X step fired, no capped settle, and the env its mode needs;
- D8 holds.

Its self-test (`smoke/self-test.txt`, 5/5) runs on a real one-round run (`smoke/`), as ruling §2.6 required:
- **control**: as recorded → `C-HOLDS`;
- **(a)** q output relabelled as unipoll → `C-FAILS`;
- **(b)** one unipoll landing broken → `C-FAILS`;
- **(c)** unipoll env without `SAL_LOK_OPTIONS` → `NOT-ESTABLISHED`;
- **(d)** unipoll Shift+Left with nothing selected at return → `C-FAILS` (D8).

## Native-only harness changes, and what they mean

Both are recorded in `smoke/NOTES.md`; finding 156 is the upstream side.

1. **The harness does not call `runLoop`.** On this core, `ImplSVMain` returns early when VCL is initialised (upstream `caa4036188ed`), so `lo_runLoop` runs nothing. Natively, the Desktop on `soffice_main`'s stack is then destroyed, and the load crashes. The harness does `lo_runLoop`'s three registrations itself and enters `Application::Execute`.
2. **It calls `SfxApplication::GetOrCreate()`**, the line iOS's LOK init adds, because `Desktop::Main` never runs.

**The harness's initialisation is not the product's.**
- WASM: `runLoop` with a leaked Desktop.
- Here: InitVCL's bare Application.

Neither path runs `Desktop::Main`. The arms measure the dispatch topology: inline posted events, synchronous accelerators, synchronous `postUnoCommand`. By source that does not depend on the Application object; this was not measured.

## Corrections made before the counted run

- **d7i's placement** first put the caret at the end of P2, which gave `Delete paragraph`. It was corrected to review 6's position (i), which gives `Number On/Off` (`smoke/NOTES.md`).

## Not measured here (ruling §2.5, §2.8(e): post-link, on the owner's v23)

- The Emscripten pthread main loop under today's machinery;
- the worker bridge under the tick;
- tick pacing;
- callback latency;
- idle-layout interleaving;
- finding 122's latency;
- `keyToUndoMs` against v20's [30, 32, 33] ms;
- finding 040's two entries under C, with the JS-thread positive control.

Also not measured: IME and ext-text input under unipoll, Calc and Impress, mouse hops after `MouseButtonUp` (ruling §2.10 item 13), and any table or inline-object position (fixed question 3; the spec's arms).

## N1 (SPEC-M3-ordered-commands §9.1, pinned at `b9080313`): `VERDICT N1-HOLDS`

Run 2026-10-20 09:04–09:20 local, 70 processes, all exit 0, load1 ≤ 0.44. Output in `out-n1/`, reader `tool/read_n1.py`, verdict in `out-n1/reader-output.txt`. Smoke and self-test (6/6) are in `smoke-n1/`.

The cells:
- **N1a** and **N1b**: every D arm plus `tleave`, in mode `uni1ai`. One op per poll, with anyInput answering "a reply is pending".
- **N1c**: `join200`, in `uni1` and `uni1ai`.

Each op records the delay from its return to the first poll, and every callback that arrives after that poll within a fixed 1500 ms idle.

- **N1a PASS.** 12 arms × 5 rounds. No `INVALIDATE_VISIBLE_CURSOR`, `TEXT_SELECTION(_START/_END)`, `UNO_COMMAND_RESULT` or `INVALIDATE_TILES` arrived after an op's first poll.
- **N1b (record).** These late callbacks arrived after the first poll:

  | type | n | delay after the first poll (min / median / max) |
  |---|---|---|
  | `STATE_CHANGED` | 253 | 0.5 / 359 / 622 ms |
  | `RULER_UPDATE` | 13 | 459 / 460 / 762 ms |
  | `VERTICAL_RULER_UPDATE` | 5 | 459 / 459 / 460 ms |

  Positive control: `tleave` recorded a late `STATE_CHANGED` in every round. This is the timer class the spec keeps out of reply fields (§5.2, L-timer-class-callbacks).
- **N1c PASS.** join200's first-poll delay:
  - `uni1` (no anyInput): 1.261, 1.203, 1.204, 1.180, 1.216 ms;
  - `uni1ai`: 0.114, 0.098, 0.101, 0.077, 0.102 ms.
  
  The two ranges are strictly separated.
  - **Natively the effect is about 1 ms**, because a native `Yield` loops at once.
  - On WASM every yield is one 10 ms tick of `emscripten_set_main_loop`, so each scheduler task the poll waits behind costs a tick there. That is inferred and not measured; the diagnostic link's tick record measures it.

## Corrections after two-seat review 1 (2026-10-20, appended; the text above is kept)

- **"The X step fired" is a q-mode fact.** `oc_native.cpp:371` initialises `fired = true`, and only the q executor can leave it `false`. For `seq` and `unipoll` the record says nothing.
- **The readers were fixed in their one review** (`../../review/DISPOSITION-two-seat-1.md`):
  - the records-only D7 cells now gate the verdict, and D8 needs all its observations;
  - each cell needs exactly one run-log entry, with exit 0;
  - an unclean cell gives NE, never a FAIL;
  - d4 needs its `.uno:Bold=true` presence witness;
  - fewer than 5 rounds is not a counted reading;
  - N1a no longer counts `INVALIDATE_TILES`.
- **Re-judged with the fixed readers, the verdicts did not move:** C-HOLDS and N1-HOLDS (`../../review/disposition-1/rejudge-*.txt`).
- **N1a is a bounded observation:** within 1500 ms after each op's first poll, and through the step's quiet window for the last op. The committed run has 0 reply-type callbacks beyond it (`../../review/disposition-1/n1-outside-window.txt`).

## N1, second run (`out-n1b/`, criteria `ARMS-n1b.md`, pinned at `ed7666e4`): `VERDICT N1-HOLDS` (2026-10-20, appended)

Run 2026-10-20 09:51:32–10:10:46Z (17:51–18:10 local): 85 processes, all exit 0 (80 `uni1ai`, 5 `uni1`), load1 ≤ 0.95. Binary `cdda2f0f…`, rebuilt in this session from `../object-click/build.txt` with its sha reproduced. Reader `tool/read_n1.py` as committed at `1085726b`; its output is `out-n1b/reader-output.txt`, exit 0, N = 5.

- **N1a PASS.** 15 arms × 5 rounds, the three new `d4i`, `d4u` and `d4s` included. No reply-type callback arrived after an op's first poll. This run applies two rules the first did not: the format command's own state item counts as reply-dependent, and there is no tile clause.
- **N1b (record).** These callbacks arrived late:

  | type | n | delay after the first poll (min / median / max) |
  |---|---|---|
  | `STATE_CHANGED` | 314 | 0.3 / 320 / 622 ms |
  | `RULER_UPDATE` | 14 | 459 / 461 / 762 ms |
  | `VERTICAL_RULER_UPDATE` | 5 | 459 / 460 / 461 ms |

  Control: `tleave` records a late `STATE_CHANGED` in every round.
- **N1c PASS.** join200's first-poll delay:
  - `uni1`: 1.109, 1.681, 1.263, 1.314 and 1.190 ms;
  - `uni1ai`: 0.116, 0.099, 0.093, 0.094 and 0.093 ms.

  Every `uni1` round is longer than every `uni1ai` round. The label is the corrected one: some scheduler task ran before the poll, and which one is not identified.

**The on-time list** (`out-n1b/on-time-list.json`, from `read_n1.py out-n1b --on-time-list`; ruling 2 §2.2, form 2) has 14 on-time and 50 late-or-mixed `(op, state key)` pairs.
- **Each of the four inline formats has its own state item on time in 5 of 5 rounds:** `.uno:Bold`, `.uno:Italic`, `.uno:Underline` and `.uno:Strikeout`. So does `.uno:ModifiedStatus` for every mutating op.
- Late in every round:
  - `.uno:Undo` and `.uno:DocumentRepair` after every mutation;
  - the table states after leaving the table;
  - `.uno:Copy` and `.uno:Cut`;
  - `.uno:LeftRightParaMargin`;
  - the list and indent states after `K9220`.
- `.uno:StateWordCount` is on time after `K1026` and late after the others, so it is mixed across ops.
- The engine's table of what a reply may read, `wasm_sdk_probe/src/reply_state_reads.hpp`, lists exactly the four inline-format items. `wasm_sdk_probe/tests/test_reply_state_reads.py` holds it against this list. It passes, and its three red cases are red: Bold made late, an unlisted key, and an empty list.
