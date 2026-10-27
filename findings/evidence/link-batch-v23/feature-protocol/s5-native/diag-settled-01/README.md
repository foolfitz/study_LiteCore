# Diagnostic: native S5 deletion cells with every member settled

Executed 2026-10-27 08:35–08:43 (+0800), 8 min, exit 0, by `python3 -I wasm_sdk_probe/tools/diag_v23_native_s5_settled.py --out …/diag-settled-01 --cells <66 ids> --install native-lok-26-8/build/instdir/program` (commit `2d0d6668`'s successor that added the tool). The tool compiled `v23_native_s5_settled.cpp` from captured bytes into `build/` (receipt `build/build-receipt.json`, sources in `build/source/`; the 140 KB binary is not tracked) under the owner's in-session authorization, after the counted S5 run had stopped (no browser run overlapped).

Forced by `../../s5-counted-01/`'s first nonpassing cell. Question: in run-01's back-to-back posting, the first Backspace/Delete after a Shift key that moves nothing removed nothing in all nine such shapes; is that posting rhythm or Writer?

Cells (`cells.txt`): the nine silent Shift members (three native rounds with an empty Shift selection) × the six deletion families = 54, plus `shift-Left@caret-mid` and `shift-Right@range-fwd` × six = 12 controls. Each cell: fresh document, run-01's setup, then each member posted and settled (800 ms quiet / 8000 ms cap) with a state read before the next, then the after-save.

Result (`comparison.json`): **66/66 after-saves have the same paragraph text as run-01's back-to-back saves**; 0 caps. The first deletion after a no-movement Shift removes nothing whether or not the Shift was settled. The mechanism read from source is in `../../s5-silent-shift-deletion-ruling/BRIEF.md` (Writer's `IsSelection()` counts a mark with mark == point).

Diagnostic only: not an oracle run, no order witness, not bound by any plan.
