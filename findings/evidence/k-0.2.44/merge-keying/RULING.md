# Ruling: how K5 (merge count) is read on engine v28

Fable, 2026-10-31 night, at the owner's choice (A, 「請 fable 裁決」). The main session re-checked before adopting: `editorContract.wasmSha256` equals the served wasm on v28, the native `r1-C{15,16,17}-key.odt` content.xml equals `original.odt` (`3e94197f`), `--cases` exists, and the five smoke records are `pass: false`. Text below is the ruling as delivered, condensed only by dropping nothing.

**Verdict in one line.** Instrument defect, not a product red: the three contested cells (C15, C16, C17) are no-ops in native Writer too, and the ordered engine's no-op is the shape SPEC-M3-ordered-commands itself prescribes. The proposal is accepted **with four corrections**: the keying must be tool-closed (manifest ABI bound to the served wasm, never a hard-coded `true`), the new table must be a third keyed table (not the C flag flipped), the report's own `boundaryNoop` record must be overridden by a keying record the reader checks, and the refusal path must be registered as a named limit of this K. K ruling items 1-4 are respected on bytes; item 2 and spec K5 need appended words.

## Premises checked

- MEASURED 1-3 re-verified: smoke 26 records, 21 `pass`, the five with `outcome verified-boundary-noop`, `generation ["1","1"]`, kept only as `-reopened.odt`, no `caretAfterKey`, `toasts null` (`findings/evidence/k-0.2.44/merge-smoke/shakedown-chrome.json`; branch at `run_merge_wasm_shakedown.py:954-972`). `candidate.boundaryNoop.declared` false on v28, true on the v21 count. `editorContract.abiVersion` 6 / 5.
- MEASURED 4 holds by construction: `noop_record` reads `<case>-r<n>-after-key.odt` and `caretAfterKey` (`judge_counted_m2.py:340-363`); the refusal branch writes neither. A reader-only repair (what ordered-commands `:151` pre-authorised) is therefore **insufficient**; the runner's expectation must be overridden in-process as well.
- The runner's keying was always a stand-in: `run_merge_wasm_shakedown.py:205-207` says a manifest field told at link time "would be the better declaration". Reading the manifest is the runner's documented intent, not new machinery.
- "`boundary_noop_declared` true" is not enough. The C flag moves only `nothing-selected`. v23+ moves three classes. That is a **new table keyed on ABI >= 6**, and it must leave ABI 5 on the C table.

## Q1: product or instrument

Instrument. The native R0c key arms for C15, C16, C17 (and C29, C30) have `undoBefore.count 0 == undoAfter.count 0`, and `docs/r1-C{15,16,17}-key.odt` content.xml sha `3e94197f` is byte-equal to `original.odt` (`findings/evidence/merge-native/r0c/round-20261006T144628Z/`). The spec prescribes the no-op for exactly these routes: K1 NONE -> noop (`SPEC-M3-ordered-commands.md:375`, `ordered_engine_delete.inc:107-109`); K1 text with separators -> RESET -> user's key -> undo unchanged -> noop (`:377`). A5 withdrew `key-deadline` (`:110`).

NOT yet measured on v28: the no-op clauses themselves (`unchangedText`, `markerOnce`, `revision`, `generation`, `noToast`, `caretUnchanged`) for C15-C17. `caretUnchanged` catches a mis-restored caret after the RESET. **One measurement must exist before the count**: the mirror proof below, both browsers, those six clauses true on each of the five. Its first red is real, not tuning.

Named limit, not a criterion: the reply does not say whether the user's key was posted. Side observation, not K: the five kept v28 documents differ only by `officeooo:rsid` of the marker's style.

## Q2: how K5 is read

`run_k_0244_merge.py` and a new `tools/judge_k_0244_merge.py` replace in-process `boundary_noop_declared` and `expectation` with ABI-keyed versions; bytes of runner (`aaee0cda`) and judge stay. Table under ABI >= 6: `nothing-selected`, `key-noop`, `refused-k1-*` -> `("M2-3", BOUNDARY_NOOP, None, None)`; `refused-k2-*` unchanged. Under fragment-only (ABI 5): the C table. Under neither: refusals. `boundary_noop=False` callers must still get the refusal table.

Items 1 and 4 hold on bytes. Item 2 and spec section 2 item 2 / section 6 K5 say the bare `judge_counted_m2.py --uncounted`; those words change (append only). Register under ordered-commands `:151` section 34.1(b): fixed because of execution, 1.

## Q3: what is lost

Zero `reopened` documents: `kept_expected` gives `{after-key 78, follow 63, reopened 0}`, and M2-3's refusal clauses become vacuous. Nothing else K reads exercises an engine refusal -> page reopen on v28. Do not add a criterion tonight. Register **L-K-0244-no-engine-refusal-exercised** with a work item: one fixture position that reaches `EDITOR_BOUNDARY_UNSUPPORTED` on v28, measured natively first, its own criterion in the next batch. The v21 -> v28 change on these cells is a ruled design change, not a K regression.

## Q4: what the override touches

v8 reds, `together()`, `oneRunner`, `--uncounted` exit 4, M2-4, `--pair`, `kept_text`: unaffected or not falsely satisfied (the counted-control pair runs through the same wrapper). The risk that remains is an unkeyed override; hence Q5.

## Q5: tool-closed keying and red cases

Key = `fragment in wasm bytes` OR (`manifest.editorContract.wasmSha256 == sha256(served probe.wasm) == proposedMergeBinding.wasmSha256` AND `editorContract.abiVersion >= 6`). Record as `keying` in `<out>.binding-override.json`; `read_k_0244_merge.py` must require it, with three new mutations: no keying record; `servedWasmSha256 != bound.wasmSha256`; `abiVersion 5` with table `ordered-abi6`.

R1 wrapped runner on v8 -> SystemExit / refusal table, no noop. R2 wrapped judge on `release-0.2.26/merge-m2 --profile e2-editor-v21 --uncounted` -> output identical to the bare judge, exit 4. R3 same with ABI forced to 6 -> M2-3 FAIL on C15-C17. R4 manifest wasm sha != served wasm -> exit before any browser. R5 wrapped judge on the smoke (refusal-branch records) -> the five not PASS. R6 mutations of the mirror proof: marker removed, `generation ["1","2"]`, `toasts ["x"]`, `caretAfterKey.caret.x+1`, `outcome "refused"`. R7 the three reader mutations.

## Q6: other pre-v23 tables in the counted path

`refusal_clauses` / `refusal_record` stage vocabulary: any genuine v28 refusal carries other stages and would FAIL `stage`, which is correct as "red = product question". Nothing else found.

## Prescription

1. Extend `tools/run_k_0244_merge.py` with the keying, assert the sha equalities, write `keying`. Do not touch `BINDING` or any bound file.
2. Write `tools/judge_k_0244_merge.py`; exit code is the judge's.
3. Extend `tools/read_k_0244_merge.py`; `--self-test` must print `ALL_RED`.
4. Run R1-R5, R7 offline; outputs under `merge-keying/red-cases/`.
5. Mirror proof: wrapped runner, `--mode shakedown --rounds 1 --cases C15,C16,C17,C29,C30`, Chrome and Firefox, under `merge-keying/proof/`. Read the ten records, not the verdict. Then R6 on a copy.
6. Commit; append the clause to the spec and the ordered-commands `:151` correction; add the limit to the handoff.
7. Start the chain. If any of the five goes red in the count: product red, K does not hold, finding; do not reread.

**Defaults.** Proof red on any of the six no-op clauses -> STOP, K NOT RUN, nominal stays 0.2.26, open a finding. Firefox proof not run -> STOP. Reader never red -> not evidence.
