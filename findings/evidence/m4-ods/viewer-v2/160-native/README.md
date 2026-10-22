# Finding 160 on native LOK (2026-10-22, diagnostic)

Forced by V2-160's FAIL on `ods-viewer-v2` `e96e01ec` (SPEC-M4-viewer-v2 §7.7): 3 of 1,392 SelectAll reads unconfirmed after the full 10 s, and `tdf125938_anchor_after_copy_paste.ods` read 6 characters of 14 -- the selection was never made. The 10 s deadline rescued nothing (v1 with 3 s: 2 of 1,392).

**Hypothesis from the source** (not measured): `doc_postUnoCommand` (`desktop/source/lib/init.cxx:5514-5525`) dispatches through `comphelper::dispatchCommand(aCommand, args, listener)`, the overload without a frame, which targets `Desktop::getActiveFrame()` (`comphelper/source/misc/dispatchcommand.cxx`). With no active frame (or another one), nothing is dispatched, the listener is never called (no `UNO_COMMAND_RESULT`, ever), the selection is never made, and LOK records `Failed to dispatch .uno:SelectAll` for `getError()`. `SfxLokHelper::setView` is what sets the Desktop's active frame ("Make comphelper::dispatchCommand() find the correct frame", `sfx2/source/view/lokhelper.cxx:231`), but it returns early when the view is already current.

`tools/probe_160_native.cpp` does the engine's sequence natively (paint one tile, then readPartText's order: setPart if needed, post SelectAll with notification, wait up to 10 s, read, reset, switch back) on `build-native-26-8` (built from `libreoffice-26-8`, LOK multi-threaded as on wasm), and records per read whether it was confirmed, the wait, and `getError()` right after the post. Per document it first posts a command nothing provides, as the positive control that `getError()` reports a failed dispatch at all. Five passes over the corpus; stop at five.

Readings, written before the run:

- **Control**: every document's `controlError` contains `Failed to dispatch`. If not, the detector is unproven and an empty `dispatchError` below means nothing.
- **N1** -- unconfirmed reads occur and each carries `Failed to dispatch .uno:SelectAll`: the hypothesis holds natively (LOK itself, not wasm). The fix belongs where the dispatch picks its frame.
- **N2** -- unconfirmed reads occur with an empty `dispatchError` (control holding): the command was dispatched and its result did not come within 10 s; `lateBeforeThisReply` / `lateAfterLastRead` say whether it came later. The hypothesis does not hold for those reads.
- **N3** -- no unconfirmed read in five passes: not reproduced natively (wasm-only, or rarer here). The cause has to be measured on wasm: a link carrying the same `getError()` record.
- A mix is reported as a mix. Nothing here is a gate.

## Result (11:09-11:17 CST; `reads.jsonl`, `probe.err`, `runs.txt`)

1,530 document lines (306 files x 5 rounds; 15 did not load -- three files x five, the corpus's unloadable ones). **Control holds 1,515 of 1,515**: the command nothing provides was reported `Failed to dispatch` every time. **2,410 reads: 0 unconfirmed, 0 with `Failed to dispatch .uno:SelectAll`, 0 other dispatch errors**; confirmed waits at most 182 ms (p99 66); late results 0.

Reading, as written: **N3 -- not reproduced natively.** At wasm's rate (3 of 1,392, about 0.22 %) about 5 would be expected in 2,410; seeing 0 has a probability of about 0.5 % [inferred: Poisson]. So the failed dispatch is wasm's, or far rarer natively; it is not shown to be LOK's own behaviour, and nothing goes upstream on this. The wasm side already carries the signal in the existing reports (LOK's own warning line), and the fix link (spec §8) adds the engine's line beside it.

The probe binary is not kept (rebuilt by `run.sh` from `wasm_sdk_probe/tools/probe_160_native.cpp`).
