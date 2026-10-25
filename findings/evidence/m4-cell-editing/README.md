# Spreadsheet cell editor v1 verification

Specification: `specs/SPEC-M4-cell-editing-v1.md` (written before the acceptance runs). New profile `ods-editor-v1`, reusing the existing viewer-v3 Calc/forms/dba core. No LibreOffice core rebuild. Existing frozen Writer/viewer files and the E1-C binding remain unchanged.

## Direct native model and geometry

`native/run-03-final/report.json`: **171/171**, three rounds. Direct UNO cell read/write, formula result, literal preservation, text/Chinese/newline/clear, three font families for B/I/U, protected/unlocked cells, nonuniform/merged/hidden-cell geometry, ODS export, independent XML and reopen. `native/run-01` preserves real initial geometry and literal failures (159/171). UNO Position/Size drifted from LOK cursor geometry; the bridge now reads the synchronous LOK cursor/headers at an explicit zoom. UNO text beginning with a formula operator needs a separate safe input representation. `native/run-02` is an intermediate passing run before the mutation-attempt uncertainty flag. Initial compiler errors and geometry discovery remain under `native/`.

## Protocol, session and static net

`worker-red.txt` and `session-red.txt` precede the new worker/session behavior. Their green outputs, `sdk-worker-regression.txt`, `calc-sdk-tests.txt`, `cell-unit-tests.txt`, `host-contract-tests.txt` and `static-gate.txt` retain results. `make test-e2-c-static` exited 0, including E1-C integrity. The owner authorized simple builds this turn; load and existing make processes were checked before compiling/linking. No core build, root operation or full K occurred.

IME Enter/Escape handling is verified by session unit events (`isComposing`/keyCode 229); this does not claim an OS candidate-window observation. Explicit revisions, refusal without capability, readonly/protection, 32767 UTF-16 limit, draft races and failed saves are checked at their appropriate layers.

## Actual browser editing and download

`browser-edit-03-download/report.json`: **Chrome 3 rounds + Firefox 3 rounds, 31 checks each, 186/186**. Real CDP/WebDriver pointers/keys double-click the cell, edit through both fields, Enter/Escape, Chinese/formula/clear/literal/multiline, B/I/U on/off/on, protection, neighbor/other-sheet preservation. Each browser actually downloads ODS to its own download directory; bytes equal the engine export, and independent ZIP/XML plus reopen agree. Screenshots retain the interface.

`browser-edit-01` preserves a reader error: reopen correctly restores the saved active protection sheet, while the runner had assumed sheet 0. The reader now explicitly selects sheet 0. `browser-edit-02` passed 180 checks but extracted exported bytes; it is not evidence of a download to disk. The final six rounds close W-edit; they are not rerun for reassurance.

## Frozen identity

`build-01/archive.json` records `build/archive/ods-editor-v1-d5a081f8-worker-39737ddb`, checksums and attribution. Wasm **d5a081f8b5b55b4fcf6c84fd8026c21b23745831dcb6eee943981f1b1890bc67**, worker **39737ddbb71a5ed18c91c82954290ff80373f8896b77f930c8809770e09053c7**. Wasm 140,193,227 B; gzip 49,535,675 B, below the existing 52,428,800 B limit. Base data/metadata and shared font resources match viewer v3. Do not overwrite or relink this frozen profile.

## Host continuation

Actual H-write, package identity, conflict-copy witness/correction and service cleanup are recorded separately in `findings/evidence/host-0.2.34/`. The first host conflict run exposed a real session mismatch: the host puts `outcome` directly on the error, whereas the new session read `details.outcome`. `host-copy-session-red.txt` reproduces it; `host-copy-session-green.txt` verifies the fix, preserves the conflict notice and keeps stranded content dirty. The engine identity is unchanged; only the new spreadsheet session asset changed. This new feature and its tools add **+0/+0** to section 34.4; cumulative **47/27**. Full K stays deferred/batched, nominal shipped host 0.2.26.
