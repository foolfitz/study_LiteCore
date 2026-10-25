# Original RESET cohort: RESET-FAILS

The owner reported successful compilation of the frozen native harness; no compiler log was supplied. The binary was independently read as SHA256 `5071c808b40033bda709f72dc4e4216cdb473b7e218b5a5f5801535faec1779a`, 135112 bytes. `owner-build-and-inputs-01.json` records this distinction and the actual binary, source, reader, fixture, ARMS and runbook hashes before execution. The agent did not compile anything.

The frozen nine-arm, five-round cohort ran sequentially in fresh `out-01`/`work-01`, from 2026-10-25 13:50:37 UTC until approximately 14:00:29 UTC. All **45** child processes and the runner exited 0. The unmodified `read_reset.py` exited **1**, with **RESET-FAILS**, no cleanliness problems, and **15** restored-landing differences. `reader-result-01.json` is the authoritative original verdict. All input hashes remained unchanged and the owned work directory was empty at completion (`completion-01.json`). No services or live documents were involved.

`comparisons-01.json` separates the compound landing predicate. For all 15 direct/restore pairs, the independently parsed saved document shape, settled cursor rectangle and at-return undo top are equal. In every restored case, however, the existing subsequent Shift+End/Shift+Home locator reads two empty strings. Direct Backspace reads the expected nonempty paragraph suffix (and, for the plain joined paragraph, its prefix). All wrong-line controls differ from the reference. K1 reads a separator in every restore case, and RESET immediately reads NONE.

This is not relabeled as a harmless locator defect. The locator sends actual subsequent Shift keys; a state that has the correct caret rectangle but cannot create the same subsequent selection is not restored Writer state. No criterion is changed and no part of this cohort is counted as RESET-HOLDS.

## Causal source evidence and its limit

The local source explains a plausible selection-mode residue, consistent with all recorded observations:

- `sw/source/uibase/uno/unotxdoc.cxx:4066` routes RESET to `SwEditWin::SetCursorTwipPosition(..., bPoint=true, bClearMark=true)`.
- `sw/source/uibase/docvw/edtwin.cxx:7104` clears the mark and sets the cursor. The clear-mark branch does not call `SwWrtShell::EndSelect`; the `EndSelect` call at the end is conditioned on creating a selection instead.
- `sw/source/uibase/wrtsh/select.cxx:407` makes `SttSelect` return immediately when `m_bInSelect` is already true, before `SetMark`; `EndSelect` at line 447 clears that flag.
- `sw/source/uibase/wrtsh/move.cxx:75` routes subsequent selection movement through `SttSelect`. `DelLeft` in `wrtsh/delete.cxx:139` takes its selection-clearing `EnterStdMode` path only when an actual selection exists; after RESET has cleared the mark, that route is bypassed.

The internal `m_bInSelect` flag was not directly instrumented in this cohort, so the flag diagnosis is a source-supported causal inference, not a recorded field value. The user-visible continuation difference itself is directly measured. Neither equal geometry nor equal saved content can erase it.

## Disposition

Do not adopt the original single RESET engine branch. Preserve this cohort and its original tools unchanged and rerunnable. A separately versioned native harness may measure the specification's exact asynchronous Escape/next-poll fallback and the synchronous RESET→START-at-the-same-point→RESET candidate. Neither is established by this failed run. Pin their finite arms before any counted execution; require the relevant continuation behavior as well as content and undo. The new harness may be shared with the separately bounded format-restoration measurement to avoid repeated owner compilations. No fallback engine implementation is authorized before its own measurement succeeds.
