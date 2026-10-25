# Calc range formatting and committed-change autosave

Decision maker: Astra, canonical agent ID `/root/astra_calc_scope`. The owner has accepted the preceding input/selection batch by manual testing and now explicitly requests multi-cell B/I/U and autosave. No previous manual pass is reopened.

## Range contract

Deliver one explicit rectangle on one visible sheet, at most 65,536 logical cells, counting hidden and empty cells. This is an operation limit, not a limit on visual selection. The SDK and worker reject over-limit requests before dispatch; native code repeats the validation. No selected-area enumeration in JavaScript and no per-cell write loop are permitted.

Use the existing anchor/focus rectangle, including endpoint merged extents. The native preflight applies `collapseToMergedArea` to the requested rectangle. If its bounds change, refuse the entire format operation with `RANGE_MERGE_BOUNDARY`; do not silently enlarge the user's target. Completely contained merged cells are permitted. Hidden rows/columns inside the address rectangle are included. Range reads are independent of engine cursor selection and return explicit bounds, three-state B/I/U, writability, and the refusal reason.

On a protected sheet, allow only a scalar, uniformly unlocked `CellProtection` aggregate. Locked or ambiguous protection refuses the whole range before mutation. This deliberately also refuses a range whose protection structs differ in other fields even if all members might be unlocked. No inference from the active cell's writability is sufficient. Read-only documents and hidden sheets remain refused. Matrix formula contents are not edited; format acceptance must be measured with the actual core.

The native implementation uses one `XMultiPropertySet.setPropertyValues` call for the chosen format; bold and italic include Latin, Asian and Complex properties in that same call. The inspected local core and Collabora reference collect these font items into one pattern and invoke `ApplyAttributes` once. The core checks whole-selection editability before applying that pattern. This supports a single native formatting operation, not a promise of durable rollback after a process crash or exception. Every known preflight refusal has no model/revision side effect. Any failure after entering the mutation is `MUTATION_OUTCOME_UNKNOWN`; advance the revision conservatively and block further writes while preserving recovery state. Never retry an ambiguous mutation automatically.

For each format, `true` means uniformly enabled across cells and relevant scripts, `false` means uniformly disabled, and `null` means mixed or no uniform scalar proof. The toolbar uses `aria-pressed="mixed"` for mixed; mixed/off toggles to enabled, all-on toggles to disabled. Native writes receive an explicit boolean, target rectangle, sheet and expected revision. A stale revision refuses before mutation. Successful changes invalidate tiles before publishing state. Refresh the two endpoint geometries because formatting can change row heights; refresh failure after a successful mutation is conservatively uncertain. Preserve the range and active anchor after formatting.

Frozen `ods-editor-v1` has only single-cell operations 0–5, `cell-editing`, and `save-ods`. It cannot perform this contract. Successor `ods-editor-v2` appends operations 6–9 to the existing cell ABI and adds `cell-range-formatting` capability bit 18. No old operation is reassigned, and no frozen artifact is overwritten. The current v1 host remains usable with multi-cell formatting disabled until a measured v2 candidate exists.

## Autosave contract

Autosave is host-only and saves committed model changes. Use the existing Writer timing: 30 seconds idle, a five-minute dirty cap followed by at least three seconds quiet, and an immediate attempt on hidden visibility when eligible. This does not forcibly confirm an active cell edit. The UI explicitly says that editing must be confirmed before automatic saving.

Defer while editing, composing, holding a pending entry, selecting/dragging, executing an operation, saving, awaiting manual save, uncertain, or showing an unresolved session error. Clean and read-only sessions do not autosave. `committedDirty` compares the model revision with the last successfully stored revision and excludes draft-only changes. `session.save(target, {commitDraft:false})` exports committed state while preserving draft and selection; manual save retains the default `{commitDraft:true}`. New typing during export/host write must remain a dirty draft after the stored revision is acknowledged.

The existing host remains responsible for conditional writes, locks, same-second version safeguards, conflict copies, sticky copy destinations, stranded recovery bytes and leave protection. Automatic calls use `trigger:"auto"`; ordinary successful saves stay quiet. Copy, stranded or other save failure pauses automatic retries, including retries after new edits or visibility changes. A successful explicit manual save to the original resumes; a sticky-copy target remains paused with a visible explanation. Do not repeatedly create copies or retry while offline. Manual save remains available, and no asynchronous unload save is promised. Existing unsaved guards remain authoritative.

## Evidence and closure

New range and autosave criteria are appended to `specs/SPEC-M4-cell-editing-v1.md`; missing native/browser evidence means the corresponding capability is not established. Unit/mutation results are development evidence, not native acceptance. Use fixed fixture-defined browser populations, Chrome and Firefox each N=3, independently inspect saved ODS/XML and reopen, compare actual delivered tiles to direct rendering, and reject empty/missing/false case populations. Preserve all failing attempts.

The final acceptance runs must precede freezing/package/install. Do not install an autosave-only intermediate host simply to avoid the native build boundary. Keep installed host 0.2.36 while completing the combined source, exact build command and reviewable test/runbook. The owner must execute compiling commands unless newly authorizing that work; historical authorization is not assumed. No root commands, shared service changes, global lock writes, full K, global pins or BINDING changes belong to this batch.

## Source basis

- `wasm_sdk_probe/src/calc_cell_bridge.cpp`: v1 operations and new conditional range implementation.
- `libreoffice-26-8/sc/source/ui/unoobj/cellsuno.cxx`, `ScCellRangesBase::setPropertyValues`: font properties are collected into one pattern.
- `libreoffice-26-8/sc/source/ui/operation/ApplyAttributesOperation.cxx`: whole-selection editability preflight and one `ApplySelectionPattern`.
- `cool-26-04/engine/sc/source/ui/unoobj/cellsuno.cxx` and `source/ui/operation/ApplyAttributesOperation.cxx`: matching local read-only reference; no code transplantation or claim of a live Collabora UI measurement.
- `cool-26-04/engine/sc/source/ui/unoobj/cursuno.cxx`: merged-range expansion used as a boundary refusal test.
- `wasm_sdk_probe/web/e2-editor-app.js`: existing timing, eligibility and host trigger contract.
- `/home/jiajun/Projects/Nextcloud_Apps/litecore/js/litecore-editor.js`: host copy/stranded/version/lock ownership.

## Address-input causal correction and finite continuation

This addendum supersedes the provisional explanation that awaiting the public host-ready promise alone explained the failed address-selection setup. `auto-final-04` reproduced the A1/B2 setup symptom after that wait, so the earlier explanation was insufficient. The zero-case setup failures remain failures; they are neither counted autosave successes nor established autosave assertion failures.

The fixed witness in `findings/evidence/calc-range-autosave/address-red-01/report.json` demonstrated an actual product mechanism: while the address field owned focus and contained B2, a session state notification caused `render` to replace it with A1. This proves that focused input could be overwritten; it does not by itself establish that this was the sole cause of every earlier intermittent setup failure.

After the criteria were appended in specification section 18 (`386b74fe`), correction `720adcc6` prevents rendering from replacing the address field while it owns focus and normalizes it to the current active cell on blur. Enter still parses the entered address and follows the existing asynchronous selection path. Source review by `/root/astra_calc_scope` finds that this limited correction matches the demonstrated mechanism, with no new blocker in that change. It does not claim that arbitrary typing during other disabled/busy states has been established.

The runner now includes the executable `focused-address-keeps-input` case, increasing the finite population to 18 checks per run. `auto-final-05` is a new candidate acceptance attempt, not an accepted result at the time of this addendum. Only its completed Chrome/Firefox N=3 artifacts and the reader can establish the final result. Earlier successful rounds are not combined with it. If the same setup symptom recurs after this correction, stop expanding this diagnosis: use explicit session selection as autosave fixture setup and register the separate startup-interaction defect. Native v2 build and range acceptance remain unperformed; installed host 0.2.36 and the owner-build boundary are unchanged.

## Final finite-layer adjudication

After completion, Astra `/root/astra_calc_scope` read `autosave-reader-final.json`: **108/108**, Chrome/Firefox N=3, and all six artifact-reader red controls rejected. It authorized closing committed-change autosave's mirror layer and source preparation without adding further criteria. Native/v2 range formatting, actual Files and installation remain **NOT_ESTABLISHED**. Maintain installed 0.2.36 and stop at the owner-build command in the runbook. This later adjudication supersedes the preceding paragraph's pending-result status, while retaining its chronology and limits.

## Successor review 05: full source-chain disposition

The owner subsequently built the successor. This paragraph addresses the two conditional findings in `claude-successor-review-05.json`; it does not turn a source review into a browser or host pass. Astra `/root/astra_calc_scope` inspected the full `CalcEditorSession` and `ods-editor-app.js`, including direct replacement input, F2, formula focus, pointer selection, sheet switching and the pending-entry transfer.

The first reported direct typing/F2 overwrite sequence does not establish a product bug as written. `_enqueue` sets `_busy` before the range operation's first await, and synchronous state rendering disables the ordinary formula/editor inputs during non-saving busy work. If a selection has been queued and keeps the grid sink enabled, direct replacement and F2 use `pendingEntry`; transfer waits for both busy and selectionPending to clear and for the drag pump to finish. Cell, pointer, arrow and sheet selection all execute through the same chain. An arbitrary direct call to `beginEdit` during a range mutation is not the product route established by this batch. A new general concurrent-SDK-caller contract or native revision architecture is not required by this finding.

The second report's premise that selection bypasses the chain is also false, but inspecting the actual keyboard route exposed a related real gap. The window Ctrl+B/I/U listener calls `toggleFormat` without the toolbar's busy guard. `toggleFormat` computes `enabled` immediately from current metadata, while `setFormat` selects its target when the queued task starts. During a held host save, a pointer selection can be queued before the shortcut. The shortcut then computes from old A1 (bold=false) but runs after E5 (already bold=true) is adopted, setting E5 to true instead of refusing the busy shortcut. `shortcut-queued-selection-source-red.json` records this with the actual page function and session, a fake engine and a held host acknowledgment. It is a source-chain diagnostic, not a browser witness.

The bounded disposition is to make the shared page format entry enforce eligibility before computing or queuing a toggle: ready and writable, no busy work, no pending selection/input/drag, and supported writable metadata for a multiple selection. This aligns keyboard and toolbar availability and requires no native rebuild or new session architecture. Do not freeze/package the page while this demonstrated bypass remains. After the narrow correction and its predeclared finite regression checks, the accepted native/browser evidence and required cell regression may support the existing freeze/package/guarded-install workflow. The 54-case actual Files gate and preservation reader remain mandatory before declaring combined host delivery. This disposition does not reopen unrelated selection, conflict, Writer or K work.
