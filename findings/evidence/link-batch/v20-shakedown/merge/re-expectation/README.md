# The merge runner's expectation for C29/C30 under C (task 2026-10-14i)

**§34.4: repaired because of execution, +1. Witness: the eight part-B reports of the v20 merge shakedown (`../shakedown-*.json`, `../control-*.json`, `../m2-1b-*.json`, `../m2-4-*.json`, runner `73b2e9ff4b1e6fbe`, commit `83ea8eb8`), which record `pass: false` on exactly the four C29/C30 records per shakedown and control report because `expectation()` mapped R0c's `nothing-selected` to a refusal on a profile that ships C.** Repaired because of audit: 0.

Runner `wasm_sdk_probe/tools/run_merge_wasm_shakedown.py`: sha256 `73b2e9ff4b1e6fbe45f10c11f67533d7ee65a055c8c3c434eda8d1945023fd11` before, `d185cb50029d76e602b924b11b84240339b0af6c6f6415995c7b13277c78e581` after. `BINDING` is not set here (still v19's values); binding is a later step. No browser was run; nothing under `dist/`, `editor-shell-v2/`, `web/`, `sdk/`, `src/`, the Makefile or the host was touched.

## What changed in the runner

1. **The keying.** `expectation(decision, boundary_noop=False)`: with `boundary_noop` the `nothing-selected` decision expects `("verified-boundary-noop", None, None)`; without it, the refusal `("refused", "nothing-selected", False)` as before. Every other decision is the same under both. `tool_cases(frame_cell, owner_document=False, boundary_noop=False)` passes it through; the population is unchanged (20 M2-1, 5 M2-3, 1 barrier; C29/C30 stay M2-3 cases with a new expectation, as §10.7 puts it). The default is the refusal: `judge_counted_m2.py` (v19-bound, frozen by §34.1) and `run_v20_shakedown.py` call `tool_cases` with no keying and still mean v19.
2. **Where the keying is read.** `boundary_noop_declared(wasm)`: whether the profile's `probe.wasm` contains the byte fragment the engine emits for C's completion, `,"completion":"verified-boundary-noop"` (`probe_engine.cpp`, `finishSelectionBarrierBoundaryNoop`, behind `OXSDK_E2_V20_LINK_BATCH`). `main()` reads it from `dist/profiles/<candidate>/probe.wasm`, the same file `bound_values` hashes as `wasmSha256`, and records it in the report as `candidate.boundaryNoop = {declared, readFrom, fragment, nothingSelectedExpects}`.
3. **The no-op path in `run_case`.** A case whose expectation is the no-op types the marker like a refusal case (the document must read original + marker), presses the key, and then: quiet, the observer's last caret (`caretAfterKey`, new), the key's trace, the generation, the toasts since the key, and one save kept as `<case>-r<n>-after-key.odt` (`afterKeyDocument`). No `toast_window`: nothing reopens and nothing is shown, so the 90 s wait of the refusal branch does not run. A refusal on a no-op case still takes the refusal branch (a refusal does reopen) and is red on `outcome`, as a refusal on a merge case already was.
4. **`noop_clauses`** (§10.5, §10.7): `outcome` = `verified-boundary-noop` (instrument-only, None on the control); `generation` unchanged; `revision` unchanged (`afterKey.revision == beforeKey.revision`, both from `READ_STATE`); `noToast` (`toasts == []`); `unchangedText` (saved document = original + marker); `markerSurvived` (the marker exactly once, B3); `caretUnchanged` (the observer's caret after the key equals `place.engineCaret`, from the same worker generation). No `checkpointRevision`: the checkpoint the page shows after the key is the placement key's (C30's End sets `有（r2）`, C29's click leaves `無`), not anything the no-op did; C30 passing that clause in the witness was that coincidence.
5. `original_plus_marker(spec, marker_at)`: the marker-insertion logic lifted out of the refusal branch unchanged, now shared by both marker-typing paths and by the re-judge here.

Unit tests (`wasm_sdk_probe/tests/test_merge_wasm_clauses.py`, 50 -> 64, all green): the default is the refusal; under C only C29/C30 move and every other decision is identical; the declaration is the emitted fragment and not the bare name; v19's wasm does not declare and v20's does; the no-op passes; a record without `caretAfterKey` leaves that clause open; red cases for a refusal on a C profile, a merge at the boundary, a lost marker, a toast, a missing revision, a moved caret or another worker's caret, and the keying's red case (a real no-op judged as v19 is judged: red on seven refusal clauses).

## Why this keying, and why not the manifest or the name

The brief asked for something the profile declares, its manifest or ABI. **The manifest declares nothing about C.** `editorContract` on v19 and v20 differs only in the three artifact hashes and `pageRectangles` (unrelated: the page-number item); `abiVersion` is 4 on both, `selectionBarrier` is `verified-single-writer-unit-v1` on both, `boundaryRejectionRequiresFreshWorker` is true on both. Every engine behaviour in that block is a flag the profile builder is TOLD at link time (`build_e2_editor_v4_profile.py --page-rectangles`, `--document-outline-geometry`, ...), and no flag was added for C. So the manifest cannot key this, and reading `pageRectangles` as a proxy for C would be judging the proxy (AGENTS.md §7).

What a profile does declare is the completion vocabulary compiled into its engine. The fragment above is in v20's `probe.wasm` and in no earlier profile's (v19: absent; v8: absent). A byte string a binary emits cannot be a comment, which is the drift a source-text match is open to (the redo check that DRIFTED on a worker comment); it is read from the bytes the run serves and binds, so a report's keying is tied to its `wasmSha256`. It fails closed both ways: a profile without the fragment is held to the refusal, one with it to the no-op, and a product that does the other thing is red under either (R2, R3 below). The name (`e2-editor-v20`) would be a convention the runner imposes on an identity label -- right for v20 and v21, wrong for a diagnostic profile minted from an older engine under a newer name -- when the artifact itself can be looked at.

**Noted for the next link (not done here, outside this task's paths and it would re-mint v20):** a manifest field for C, TOLD to the builder at link time like `pageRectangles`, would be the better declaration; the runner could then read the manifest and STOP when the manifest and the wasm disagree.

## The re-judge (`rejudge.py`, output `rejudge-output.txt`, `rejudge.json`)

The runner's per-record judgement is recomputable from the recorded fields and the kept documents, so the eight reports were re-judged offline with the runner's own clause functions, twice per record: under the recorded expectation (must reproduce the recorded `clauses` and `pass` exactly, or the comparison means nothing) and under the expectation the profile's bytes declare. The keying is read as the runner reads it, and the script STOPS unless the wasm's sha256 equals the report's `bound.wasmSha256`. What the refusal path recorded for a no-op is mapped explicitly: `toasts` from `toastWindow.toasts` (the same `READ_TOASTS` after the same `CLEAR_TOASTS`, polled for 90 s instead of read once after quiet -- a longer observation of the same thing); the document from `<stem>.docs/<case>-r<n>-reopened.odt` with its content hash checked against `reopenedDocument.sha`; `caretAfterKey` absent, so `caretUnchanged` reads not established.

| report | records | reproduced under the recorded expectation | verdict changed (red -> green) | verdict unchanged |
|---|---|---|---|---|
| shakedown-chrome | 56 | 56/56 | 4: C29 r1, C30 r1, C29 r2, C30 r2 | 52 |
| shakedown-firefox | 56 | 56/56 | 4: the same | 52 |
| control-chrome | 56 | 56/56 | 4: the same | 52 |
| control-firefox | 56 | 56/56 | 4: the same | 52 |
| m2-1b-chrome | 20 | 20/20 | 0 | 20 |
| m2-1b-firefox | 20 | 20/20 | 0 | 20 |
| m2-4-chrome | 1 | 1/1 | 0 | 1 |
| m2-4-firefox | 1 | 1/1 | 0 | 1 |

The sixteen no-op records: `outcome` true (None on the control), `generation` true, `revision` true, `noToast` true, `unchangedText` true, `markerSurvived` true, `caretUnchanged` **not established** -- runner `73b2e9ff` never read the observer's caret after the key, so these reports cannot establish it; the edited runner records `caretAfterKey` on every no-op from now on. Part A's C1 arm (`../../judge-output.txt`: `c1: PASS` on both browsers) measured the engine's caret and selection 500 ms after the same no-op on the same bytes; it is cited, not substituted. On the control, `outcome` is also not established (instrument-only, as every control record).

The clauses the witness had false -- `outcome`, `stage`, `keyPosted`, `generation`, `toastWindowClosed`, `onlyTheReopenToasts`, and `checkpointRevision` on C29 -- all presupposed a refusal and its reopen; none reported a changed document.

## Red cases

- **R1** -- the four v19 counted reports (`findings/evidence/v19/x7-counted-m2/counted-*.json`, `counted-control-*.json`, 78 records each) under the keying: v19's wasm (`1aafd4f9…`, sha256 equal to each report's `bound.wasmSha256`) does **not** declare C, `nothing-selected` expects the refusal, and all 4 x 78 records reproduce exactly, 0 verdicts changed. The change is not a blanket loosening.
- **R2** -- the v19 C29/C30 records (3 rounds x 2 cases x 2 browsers) judged under C's expectation anyway: all 12 red, on `outcome` (refused), `generation` (1 -> 2), `revision` (reopened to 0), `noToast` (the two reopen toasts).
- **R3** -- the v20 C29/C30 records judged under the refusal anyway (what `73b2e9ff` did): the 4 per report come back red with the recorded clauses, 0 differences.
- **R4** (`--self-red`, `rejudge-selfred-output.txt`) -- the v20 shakedown report keyed on v19's wasm: `STOP: ... is 1aafd4f9da42fd83, the report ran 313b08d5cb085897`, exit 2, nothing judged.

The script also STOPS on a missing report, a record count other than the mode's, a record without clauses, or a kept document whose content hash is not the one the record names.

## Things to know

- **Two tests in `wasm_sdk_probe/tests/test_judge_counted_m2.py` (`V19Witness.test_a_the_witness_passes`, `test_c_one_arm_with_a_single_save_is_red`) are red on this commit, by construction.** They run the frozen counted judge on the real v19 X7 reports, and the judge's `thisRunner` clause requires every report's `runner` (`73b2e9ff…`) to equal the live runner file's hash; the judge's own docstring says re-judging later means checking out the commit the run used. Any edit of the runner reds them; the brief's premise is that this edit moves the hash and lands before `BINDING`. The judge and its tests are outside this task's paths and were not touched. The binding step for v20 must decide this (the judge's own `nothing-selected` table, line 112, also still expects the refusal and needs the same witness-backed change when v20 is bound; the V19 witness tests either pin their commit or skip when the runner has moved). The other 50 tests of that file pass; the judge still imports the runner and orders the list as before.
- The paired control (`pair()`) needs no change: a no-op record has no `toastWindow`, so its `toasts` are compared, and its kept `after-key` document is compared by kind as the merge cases' are.
- A counted run on v20 will take about six minutes less per shakedown/control step than the witness did (4 records x 90 s per report).
