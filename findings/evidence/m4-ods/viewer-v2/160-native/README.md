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
