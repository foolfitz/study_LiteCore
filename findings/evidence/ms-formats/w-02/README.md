# W, run 02: W_HOLDS on both browsers

Spec `specs/SPEC-P-ms-formats.md` 10.3-10.4, corrected by 11.3 (fable's ruling, owner-delegated). Tool `wasm_sdk_probe/tools/run_ms_formats_w.py`
at `d328b3836` (sha256 prefix `423b4292b9c0b42f`), one tool for every row below. Development profiles `build/e2/editor-v33/profile`
(wasm `444519df`) and `build/ods/editor-v5/profile` (wasm `4faad0af`), pages from the source tree at `d328b3836`, no host, real downloads.

| Read | Result |
|---|---|
| `r1-read-run01-chrome`, `r1-read-run01-firefox` | R1, the corrected reader on run 01's reports (`../w/`): W3 false, naming `error.code missing` and the open after the refusal not ready. No crash |
| `r1-live-red/` | R1, live (Chrome): the good file after each refusal carries a refused name too. `W3_RED`: Calc state `error` for `formats.red.xls` / `.xlsm`, `INVALID_ARGUMENT`; Writer `recoverable-error` |
| `chrome/`, `read-chrome` | `W_HOLDS`: 26 of 26 open; W1 26/26 (OOXML, equal to M0's own-format round trip; `empty_ext_defined_name.xlsx` differs only in its external link, `L-external-links`); W2 25/25 equal to M0's ODF round trip and 26/26 ODF with the dialog's two choices, ODF first and checked (`forum-mso-en4-134670.xlsx` NOT_ESTABLISHED, finding 184); the truncated DOCX refused with `LOK_ERROR：…`, then a good file opens; W3 5/5 |
| `firefox/`, `read-firefox` | `W_HOLDS`, the same |
| `baseline-chrome/`, `baseline-firefox/` | `W_RED`: the same page sources on `e2-editor-v32` / `ods-editor-v4`, 0 of 26 open (`INVALID_ARGUMENT` at the C ABI) |
| `r2-self-test-chrome`, `r2-self-test-firefox` | R2: the green report, mutated in memory three ways (Calc `error.code` -> `OPEN_FAILED`; the Calc open after a refusal left `opening`; the Writer toast without its code): each turns W3 red, both browsers |

Run 01 (`../w/`, kept as the witness) read W3 the old way and was red on the two Calc cells: the Calc toast carries no code, and a closing session
re-shows its error, which the old predicate took for the next open's failure (spec 11.2).

Evidence is lean: the native dumps are gzipped, screenshots and the mirror live under `wasm_sdk_probe/build/ms-formats-w/` (not in git).
