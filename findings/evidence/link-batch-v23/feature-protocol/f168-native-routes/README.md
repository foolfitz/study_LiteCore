# Finding 168 native step: every text-input route on the S5 table selection

Executed 2026-10-28 on native LibreOffice 26.8 LOK (`native-lok-26-8/build/instdir/program`, core `671c848b`, see `env-snapshot.txt`), with native run-03's environment: `SAL_USE_VCLPLUGIN=svp`, `SAL_LOK_OPTIONS` and `OC_A11Y` removed, `nice -n 10`. No browser, no WASM artifact, no core build, no DDEV. Frozen v23 inputs are untouched; this directory is diagnostic and contributes nothing to any counted result.

## Why

The first counted S5-02 failure (`shift-Right@cell-end/type`) saves A1 `A1 cell textx` / B1 `B1 cell textx#` on the product, against the bound native keyboard reference A1 `` / B1 `x`. The product types with LOK `paste(text/plain;charset=utf-8)`; the reference types with KEYINPUT. The questions were: (1) does native paste do the same, i.e. is the difference the route rather than the WASM build; (2) what produces the later cell's `#`; (3) which non-paste routes reproduce the keyboard reference, as a measured starting point for a product repair.

## Instrument

- Harness `wasm_sdk_probe/tools/f168_native_table_type_routes.cpp`, which includes the archived signature setup `link_native_extend_signatures.cpp` unchanged (sha256 `1e29f73b…ef17`, the same bytes native runs 01–03 used) for discovery, shapes and settle.
- Built with `build_f168_native_owner.py` (single-file g++, 1.6 s): `build-01/`, binary `cd2a3db1…8b91`. Built by the agent after `uptime` (load 0.10) and `pgrep -a make` (none), under the owner's 2026-10-28 decision recorded in `AGENTS.md`. After run-01, the build script's docstring was edited to drop its "OWNER ONLY" wording (owner request); the compiled sources did not change, so run-01's `identity.json` carries the earlier script hash.
- Runner `run_f168_native_table_type_routes.py`: fresh directory, pins binary/build receipt/sources/native libraries/fixture before and after, one execution, no retry. Fixture is native run-03's copy, sha256 `ede9cb03…b7bc`.
- Each arm is a fresh document: open, settle, make the shape, save "before", post the arm's Shift keys (each settled 800 ms quiet / 8000 ms cap, as run-03), read the selection, run the route once, settle, save "after". 15 arms, interleaved, 3 rounds.
- Routes: `key` (KEYINPUT/KEYUP character 120), `paste` (LOK `paste`, `text/plain;charset=utf-8`), `uno-insert-text` (`.uno:InsertText` with `Text`), `ext-text-input` (`postWindowExtTextInputEvent` TEXTINPUT then END, window 0).
- Reader `read_f168_native_table_type_routes.py`: checks every artifact hash, one record per arm and round, every "before" save equal to the fixture, the table2 selection text, and that `table2/key-x` reproduces run-03's bound `shift-Right@cell-end_type-after.odt` (the positive control that this harness makes the oracle's selection). Then per arm the distinct paragraph changes across rounds. It describes; it does not judge the product.
- Reader red cases (on scratch copies, before use): a deleted after-save, the key-x save swapped for the paste-x save with its completion hash updated, and a dropped record each exit 1 with a named problem. The first version crashed on the missing file instead of naming it; it was fixed before any reading was recorded.

## Results, run-01 (default locale zh_TW.UTF-8)

Runner exit 0, protected inputs unchanged, reader 0 problems (`reader-run-01.json`). Every arm gave the same saved paragraphs in all 3 rounds. Paragraph changes against the fixture:

| Arm | Selection before the route | A1 | B1 | A2 | B2 | Equals key route |
| --- | --- | --- | --- | --- | --- | --- |
| `table2/key-x` | `A1 cell text⇥B1 cell text↵` | `` | `x` | | | — (= run-03) |
| `table2/paste-x` | same | `A1 cell textx` | `B1 cell textx#` | | | no |
| `table2/paste-xy` | same | `A1 cell textxy` | `B1 cell textx#y#` | | | no |
| `table2/paste-hello-world` | same | `A1 cell texthello world` | `B1 cell texthello world` | | | no |
| `table2/paste-e-acute` | same | `A1 cell texté` | unchanged | | | no |
| `table2/paste-cjk` | same | `A1 cell text中` | `B1 cell text-N` | | | no |
| `table2/uno-insert-text-x` | same | `` | `x` | | | **yes** |
| `table2/ext-text-input-x` | same | `` | `x` | | | **yes** |
| `table2/none` | same | unchanged | unchanged | | | (no input) |
| `table4/key-x` | A1:B2 | `` | `` | `` | `x` | — |
| `table4/paste-x` | A1:B2 | `A1 cell textx` | `B1 cell textx#` | `A2 cell textx#` | `B2 cell textx#` | no |
| `cell-caret/paste-x` | caret, A1 end | `A1 cell textx` | unchanged | | | yes |
| `text/paste-x` | `T` in P2 | P2 `P2 ALPHA BExA GAMMA DELTA` | | | | yes |

Every paste returned `true`. `.uno:InsertText` and the ext-text-input posts return immediately (0.12 ms, 0.02 ms) and complete in the following settle.

## Locale perturbation (runs 02 and 03, LC_ALL=C and LANG=C)

The fallback charset of the ASCII reader is the thread text encoding, so the process locale was changed; ICU detection, if it decides, should not care.

- `run-03-lc-all-c`: runner exit 0, protected inputs unchanged; read together with run-01, reader 0 problems (`reader-run-01-run-03.json`). **All 15 arms give the same saved paragraphs as under zh_TW.UTF-8**, stable in all 3 rounds.
- `run-02-lc-all-c` is preserved, not used: its native process also exited 0 with the same 15 outcomes, but the reader's source was edited while it ran (the missing-file fix above), so its completion records `protectedInputsUnchanged: false` and its reading (`reader-run-01-run-02.json`) reports that problem. run-03 is the clean repeat; nothing else changed between them.

## Reading

1. **Native paste reproduces the product exactly** (`A1 cell textx` / `B1 cell textx#`). The S5 mismatch is the route the product uses to type, not something the WASM build adds.
2. **Two separate defects.** (a) Route: over a table selection, paste appends to every selected cell and deletes nothing, while the keyboard, `.uno:InsertText` and ext-text-input all clear the selected cells and put the text in the last one. Over a plain-text selection and at a caret, paste equals the keyboard, which is why the other 401 counted cells passed. (b) Decoding: in every cell after the first, the inserted text is the UTF-16LE byte stream read one byte per character: `78 00` → `x` + NUL shown as `#`; `78 00 79 00` → `x#y#`; `2D 4E` (中) → `-N`; `E9 00` (é) → nothing inserted; the 22-byte `hello world` is correct. Four selected cells give `#` in all three later cells. This is registered separately as finding 169; fixing the typing route does not fix a real Ctrl+V into a multi-cell selection.
3. The locale does not change any outcome (run-03), consistent with the later cells' encoding being chosen by detection rather than by the fallback charset. The code path for (b) — options set to UCS2 once, `SwReader::Read` reusing the stream per PaM, `AsciiReader::Read` resetting the options after each read, later reads going through ICU detection — is a **source reading, not traced**. The byte-level input→output mapping above is measured.
4. **Candidate repair routes reproduce the keyboard reference** on this selection: `.uno:InsertText` (FN_INSERT_STRING → `SwWrtShell::InsertByWord` → `SwWrtShell::Insert`, the same function the keyboard's `FlushInBuffer` calls) and ext-text-input (`StartExtTextInput` does `DelRight` on a selection). This is one selection shape and one character; it is not a census of the type family.

## Not established

No desktop (non-LOK) Writer reproduction, no debugger trace of the charset choice, no WASM measurement of `.uno:InsertText` or ext-text-input, no Up/Down or other S5 shapes through the candidate routes, no autocorrect-triggering input (the keyboard autocorrects at word boundaries; paste and `.uno:InsertText` do not).

## Re-reading

From the repository root, with a fresh output name:

```bash
python3 -I wasm_sdk_probe/tools/read_f168_native_table_type_routes.py findings/evidence/link-batch-v23/feature-protocol/f168-native-routes/run-01 findings/evidence/link-batch-v23/feature-protocol/f168-native-routes/run-03-lc-all-c --output FRESH.json
```

Reader red cases are recorded in `reader-controls.json` (scratch copies of run-01; this directory was not modified by them).
