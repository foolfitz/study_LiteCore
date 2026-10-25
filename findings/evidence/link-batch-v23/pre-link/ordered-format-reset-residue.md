# Source audit: format RESET leaves selection-mode residue

## Disposition

**The synchronous format implementation is not ready to certify unchanged.** Its final RESET can produce selection type NONE while leaving Writer's internal selection mode active. The fake-LOK unit test verifies its explicit calls and reply timing, not this internal state. This is a bounded source conclusion about ordinary Writer text selection; it is not a fresh native measurement or a verdict on every selection mode.

No engine code is changed by this audit. Existing native RESET cohort counts and frozen acceptance conditions remain unchanged.

## Actual source chain

Paths below are relative to `libreoffice-26-8/`:

1. `sw/source/uibase/shells/textsh1.cxx:1975`, `FN_SELECT_PARA`, ends in `rWrtSh.EndPara(true)`.
2. `sw/source/uibase/wrtsh/move.cxx:402`, `EndPara`, creates `ShellMoveCursor(this, true)`. Its constructor calls `MoveCursor(true)`, whose selection branch calls `SttSelect()` (`move.cxx:76`). The destructor does not pair it with `EndSelect()`.
3. `sw/source/uibase/wrtsh/select.cxx:407`, `SttSelect()`, returns immediately if `m_bInSelect` is already true. Otherwise it creates a mark when absent and sets `m_bInSelect = true`.
4. `sw/source/uibase/uno/unotxdoc.cxx:4066`, `LOK_SETTEXTSELECTION_RESET`, calls `SetCursorTwipPosition` with `bClearMark=true`.
5. `sw/source/uibase/docvw/edtwin.cxx:7076`, `SetCursorTwipPosition`, clears the mark in that branch but leaves `bCreateSelection=false`. Both `SttSelect` and the trailing `EndSelect` are conditional on `bCreateSelection`, so RESET calls neither.
6. `sw/source/uibase/wrtsh/select.cxx:447`, `EndSelect`, is the missing transition that clears `m_bInSelect` in ordinary non-extended selection mode.

Consequently, SelectText followed by RESET can be markless while still in selection mode. A subsequent selecting movement reaches `SttSelect`, returns before `SetMark`, and may yield NONE instead of a selection. Reading NONE after RESET does not observe this latent state. A matching command result and successful saved-document/undo comparison do not observe it either.

The existing `handleEditorSelect` TEXT_HANDLES branch in `wasm_sdk_probe/src/probe_engine.cpp` already documents this exact SelectText defect and uses RESET→START→END to rescue range selection. The new format include reuses `postFormatBarrierRestore`, which sends RESET alone, and therefore inherits the source defect.

## Historical evidence and its limits

`findings/evidence/sdk-e2/discovery/049-selection-after-format/native-round4/README.md` reports that markless RESET did not rescue selection (AF), while START-based repair survived clean/poisoned and forward/reverse controls (AG–AK). It also preserves the failure of Escape to heal the SelectText case, and retracts a reliable GoLeft-healing claim because one run reversed it. Those probes used fixed waits, and no claim here upgrades them into v23 ordered-command evidence.

In particular, the DELETE fallback's Escape must not be assumed to repair the FORMAT residue. The two obligations are different, and the historical FORMAT evidence already argues against that assumption.

## Candidate for new native measurement

Measure **RESET(recorded point) → START(the same point) → RESET(the same point) → direct NONE read**, synchronously, as a separate candidate:

- The first RESET removes the current mark.
- START sees no mark and sets `bCreateSelection=true`. Its trailing `EndSelect()` runs even if `SttSelect()` itself early-returned on the stale flag.
- In a clean initial mode, START can create a mark. The final RESET removes that mark while retaining the now-cleared ordinary selection-mode flag.

This is a source-derived candidate, not authorization to report a working restoration. Extended/additive/block modes, coordinate reflow, and the correct document point remain explicit limits. The required follow-up must compare direct controls with full format→candidate-restore sequences and test the *next* selecting operation as well as immediate NONE, caret location, undo top, and saved content. Cover both the existing TEXT_HANDLES continuation and real Shift movement; retain RESET-only and deliberately wrong-point negative controls. Register the new cohort and its fixed acceptance conditions before any counted run. Do not rewrite or absorb the current frozen RESET population.

Until that candidate is measured or another bounded remedy is established, keep the format include preparatory and record the internal-mode restoration gap as unresolved. Do not weaken the first-poll reply requirement or add timer-based staging to hide it.

## Bounded adoption after the registered cohort

The new `restore-v2/format/reader-result-01.json` reports `FORMAT-RESTORE-HOLDS` for 40 cells, five rounds, with empty problems and failures. The owner proxy authorized adoption of the measured Q sequence after that result. Commit `41e3f951` replaces the two legacy restoration call sites in `ordered_format.inc` with a local `restoreOrderedFormatPoint` helper: three synchronous RESET→START→RESET calls at the same captured x and vertical midpoint, with no intermediate read, wait, or yield. The final direct NONE confirmation remains after the helper returns.

This supersedes the earlier instruction to keep that RESET-only implementation preparatory, for this bounded restoration mechanism. It does not upgrade the native cohort into HTML postcondition, complete engine integration, or browser gate evidence. The earlier source diagnosis remains valid for RESET alone.

The fake-LOK test now models the distinction between a mark and selection mode, checks both initially clean and poisoned modes, and rejects independently compiled mutations that remove START's repair or insert an intermediate read. The source checker additionally rejects use of the legacy RESET-only helper and a restoration call reachable from the poll reply. These are implementation checks of the adopted sequence, not new native acceptance criteria.
