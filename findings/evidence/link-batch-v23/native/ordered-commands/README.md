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
