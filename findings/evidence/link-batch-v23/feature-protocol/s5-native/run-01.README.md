# Native S5 continuation references, run 01

Executed 2026-10-27 01:34–02:08 (+0800) with the runbook's command (`handoff/RUNBOOK-2026-10-26-v23-native-s5.md`) against the owner-requested harness build 01 (`build-01/`, binary `4a6d9c48…3cfa`). The installed native core is `native-lok-26-8/build/instdir/program`. Wall time 33.5 min, exit 0. No browser measurement overlapped it. `completion.json` records `protectedInputsUnchanged: true` and the after-run identities of the build receipt, binary, sources and every loaded native library.

The reader (`read_v23_native_s5.py run-01 --output reader-01.json`, exit 0) reports `NATIVE_S5_SAVES_AVAILABLE`: 392 cells, one native execution per cell, 0 problems. The 392 cells are the source-derived native-capable S5 entries: 196 Left/Right and 196 Home/End, the latter conditional. `saves/` holds the 784 actual before/after ODTs.

What this does and does not supply, per the runbook: these saves are native Writer oracles for the S5 sequences. They are not browser parity. Home/End entries apply only when the browser later shows an actual single-line witness. Up/Down and other layout-dependent members still need fresh same-browser settled-WASM references. No browser S5 cell has run. The runtime-only LibreOffice profile under `run-01/profile/` is excluded from version control.

## Appended 2026-10-27: type entries are not oracles

The 56 type-family entries record "x then Shift" (the native harness processed the character before the earlier-posted Shift key in every cell), so they are not oracles for the declared "Shift then x" sequence (fable ruling 3, `../s5-type-oracle-ruling/RULING.md`). This applies to `reader-01.json`'s type entries as well; that file stays unchanged because the selection config binds its hash. The deletion entries keep `NATIVE_S5_SAVES_AVAILABLE`.

## Appended 2026-10-27: empty-mark deletion entries are not oracles (fable ruling 4)

Deletion entries whose cell is `emptyMark` (Writer's state right after the Shift member is an empty mark, decided per cell by `empty-mark-witness-01/`; 49 of the 66 cells in `diag-settled-01/`) record Writer's empty-mark behaviour: the first Backspace/Delete after a Shift that moves nothing deletes nothing. They are a true record of Writer and evidence for finding 167, not the S5 oracle; those cells compare with the settled-WASM arm. `reader-01.json` is unchanged (the selection config binds its hash). The other deletion entries keep `NATIVE_S5_SAVES_AVAILABLE` under ruling 2.

## Appended 2026-10-27: order-dependent entries in new S5 plans

The owner-delegated Astra decision in `../s5-order-oracle-review/RULING.md` authorizes a distinct `native-every-member-settled` reference for the non-empty-mark partition derived from disagreement between these queued saves and each cell's every-member-settled save. Current complete-population measurement derives two members. For new schema-2 plans, where native comparison is eligible, their queued after-saves remain diagnostic records rather than the target; use `empty-mark-witness-01/`'s own before/after pair certified by `settled-reference-reader-04.json`.

Do not change `nativeOrderIndependent` to true. The native comparator and both before controls retain ruling 2; the actual browser single-line premise still gates Home/End. The exact native continuation settles/reads every member at 800/8000, unlike the existing WASM reference's Shift-only wait. Its setup/save lifecycle is source-bound, not independently timestamped. Missing/invalid evidence is NE or plan refusal. The original `reader-01.json`, historical NE configurations, type and empty-mark notes above remain unchanged. No native execution was repeated for this certification.


## Appended 2026-10-27: final state-payload control and certificate 05

This supersedes the earlier current-certificate reference to `settled-reference-reader-04.json` for future plans only. The final certificate is `s5-native/settled-reference-reader-05.json`, SHA-256 `ad4febf67df932a8eaa3770b43feebbb4c6e8673e1ed54db3498abcbd5257e43`. The complete 336-cell native population still validates and the derived partition still has two members.

Forcing control: `s5-order-oracle-review/state-payload-pre-red.json` removed the last member's state payload from a copied record; the prior reader accepted it. The final reader requires each member's integer selection type and actual string-valued `getTextSelection`, `TEXT_SELECTION`, and `INVALIDATE_VISIBLE_CURSOR` payload, in addition to the already-required settle/read ordering. This enforces the existing every-member state-read claim; it adds no product mechanism or native execution. Missing/malformed payload refuses the plan. Historical certificate 04, the 14/14 uncounted prep-05 observations, and their exact inspections remain preserved. A fresh two-browser prep-06 under certificate 05 precedes counted execution. No preparation contributes a qualifying count, and the first-full-clean-population cutoff is unchanged.
