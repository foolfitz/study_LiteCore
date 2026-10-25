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
