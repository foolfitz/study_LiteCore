# Calc owner passes recorded; direct typing, F2 and cell-range selection next

This is the current handoff. It supersedes the next-work/status portion of `HANDOFF-2026-10-25-calc-format-fixed-collabora-research.md`. The owner requested a handoff because the context is long; **this turn records results and prepares continuation only**, with no new product implementation, build, browser run or ddev operation.

## Latest owner steering — preserve the difference between delivered and researched

Exact owner report:

> 人工測試完成，
> - B／I／U 整格套用 => 測試通過
> - 雙擊：保留原內容，進入文字編輯 => 測試通過
> - 選格後直接打字，F2 進入文字編輯 => 沒反應
>
> 然後我希望加上「區域選取」的功能
> 我們context很長了，請幫我寫交接文件

- **Explicit owner passes:** whole-cell B/I/U; double-click preserving existing content and entering editing. Earlier text/formula input was also explicitly accepted. Record these as accepted and do not ask for them again. Evidence: `findings/evidence/host-0.2.35/owner-test-2026-10-25/confirmation.md`; canonical append-only spec now through **section 12**.
- **Outstanding expected entry points:** selected-cell direct typing and F2 currently do nothing because **neither is implemented**. The preceding answer described Collabora's behavior, not a newly delivered LiteCore feature. Do not treat the report as a regression in an implementation that never existed, and do not stop at telling the owner it is unimplemented: carry these entry points into the next functional batch.
- **New requested feature: cell-range selection.** In this spreadsheet context, interpret it as selecting a rectangular group of cells, not selecting characters inside the textarea. It is not implemented. Specific mouse/keyboard gestures and range operations have not yet been fixed by an acceptance specification.
- **Not delivered:** partial rich-text formatting inside a cell, multi-cell paste/fill and autosave. Do not fold those into this range request silently. The earlier optional question about adding Writer-style autosave was not answered; the latest message does not answer it. Calc remains manual-save only.
- The owner did not separately report tested browser/version, served URL or package identity. Their reply follows the installed 0.2.35 context. This handoff turn freshly verified the clean local host checkout and manifest; that is not a measurement of the browser they tested.

## Current installed candidate and environment

- Study repo: `/home/jiajun/LibreOffice/study_LiteCore`, main. Product fix **4caa253e**; final test-observer lifecycle correction **2b55cca1**. This handoff's changes are documentation/owner-result records only.
- Host repo: `/home/jiajun/Projects/Nextcloud_Apps/litecore`, clean main **858a07cfd83e8d082e22926db6b93ea886125a8c**, version **0.2.35**. Fresh local reads this turn match `release.json`.
- Local package **b007f950b2e18cd2**, manifest sha256 **d4bc5e77f6d38ed8d1b24300c504933c85f0baa4486a3da9f3c6a06c43615252**. 45 files; only the spreadsheet session changed from 0.2.34, 44 prior records identical.
- Frozen **ods-editor-v1**, wasm **d5a081f8b5b55b4fcf6c84fd8026c21b23745831dcb6eee943981f1b1890bc67**, worker **39737ddbb71a5ed18c91c82954290ff80373f8896b77f930c8809770e09053c7**. Core is the existing viewer-v3 Calc/forms/dba build. **Never overwrite/relink this frozen identity**. Writer **e2-editor-v22 / f7a40bcc** and readonly viewer **ods-viewer-v3 / ebb7e0cb** remain unchanged; E1-C intact.
- Profile archive `wasm_sdk_probe/build/archive/ods-editor-v1-d5a081f8-worker-39737ddb`; host archive `wasm_sdk_probe/build/archive/host-0.2.35-engine-b007f950b2e18cd2`; old 0.2.34 archives retained. Isolated host worktrees were verified then removed; branches remain. Historical install scripts intentionally require their recorded predecessors; do not rerun them against current main.
- **Installed, uncounted candidate. Nominal shipped host remains 0.2.26.** Full K stays deferred/batched. No global count pins, merge BINDING or chain repinned. Historical K took 7h48m40s; do not start it as part of this handoff or new feature work. Section 34.4 cumulative **47/27**, this handoff **+0/+0**.
- Last measured service state in the preceding implementation round: **litecore RUNNING as found**, fgp-nc/nc-bridge paused, others stopped. Existing **fileId 24674 lock** was preserved before/after. **No fresh ddev/container read was performed in this handoff turn.** Re-read actual states before changing services; preserve the owner's current state instead of applying older stopped-state handoffs.
- Preserve all owner documents, especially fileId **24920** with owner edits (last preserved 31,008 B / sha a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb). Do not restore its historical fixture or clear unrelated locks. Use new owned folders/files and only their own lock tokens in future tests; **never use old setup that deletes the entire oc_files_lock table**.

## Already established — do not rerun for reassurance

1. Initial cell native acceptance **171/171**, Chrome/Firefox N=3 actual editing/download/XML/reopen **186/186**. Evidence `findings/evidence/m4-cell-editing/README.md`; v1 host routes/save/conflict/readonly and Writer regression `findings/evidence/host-0.2.34/README.md`. Earlier actual host failures and fixes are preserved, not relabeled clean.
2. **Finding 165 fixed**: `setFormat` originally called `_adopt` (synchronous emit) before `scheduler.invalidateRevision`. The page cleared the DOM and scheduled old-context work, then invalidation canceled it. Model/format survived while tiles became stale/empty. Fix: invalidate before emitting. Do not undo this order when adding range mutations.
3. 165 red before fix: one stale DOM tile, then five zero-tile views; model checks pass, tileErrors=0. Final session units **13/13**. The first post-fix unit attempt failed on teardown because it inspected a released scheduler; preserved as `session-green-attempt-01.txt`, corrected to check ready callbacks only.
4. 165 mirror Chrome N=3 / Firefox N=3 **90/90**, **36 views / 936 tiles** byte-compared with direct engine render; downloaded XML/reopen consistent. Actual Files both browsers **24/24**, **12 views / 336 tiles**, manual save/server XML/own lock release. Evidence READMEs: `findings/evidence/165-calc-format-blank/`, `findings/evidence/host-0.2.35/`.
5. Autosave audit: both browsers idle **35,021 real ms** after a committed edit, no save request, dirty stays true; manual positive control succeeds. The source independently has no Calc autosave scheduler. The bounded observation is not an infinite-time proof. Writer host autosave uses 30 s idle, a 5 min cap / 3 s quiet period, background attempts and safety gates. No autosave was added.
6. Prior owner F3-hand/Home-End/dialog/H7/V3-SEE passes remain accepted. Latest whole-cell formatting and double-click passes are now added; do not request them again or invent a new human gate.

Read existing results without services/builds:

```bash
python3 wasm_sdk_probe/tools/read_calc_format_view.py findings/evidence/165-calc-format-blank/green-01
python3 findings/evidence/host-0.2.35/read-result.py
```

These readers have actual red/empty controls. New range/input paths need their own evidence; prior closed rounds are not evidence of those new paths.

## Code and source references for the next batch

Read `research/2026-10-25-collabora-calc-input-format-autosave.md` first. It contains exact local source links and distinguishes source inference from actual UI tests. Collabora source is already found: **`/home/jiajun/LibreOffice/study_LiteCore/cool-26-04`**, HEAD **c64a7343a5c6295623619c80aa7857c4e00e1ddd**, also `/home/jiajun/LibreOffice/collabora_online`. Read-only reference, no transplantation of its implementation. Reference file hashes: `findings/evidence/165-calc-format-blank/collabora-reference.json`.

- Collabora `engine/sc/source/ui/app/inputhdl.cxx`: KeyInput and extended-text InputCommand clear the old EditEngine for new input from NONE; StartTable/SetMode distinguish replacement typing, TABLE editing and TOP formula input. First F2 enters editing; repeated F2 toggles TYPE/TABLE.
- `engine/sc/source/ui/view/gridwin.cxx`: double-click → SC_INPUT_TABLE + positioning the text cursor.
- `engine/sc/source/ui/view/formatsh.cxx` vs `editsh.cxx`: cell/range ApplyUserItemSet vs text EditView.SetAttribs. Same toolbar UNO commands, different core context. Do not infer partial rich text merely because textarea.selectionStart exists.

Our relevant files:

| Layer | Location / limitation |
| --- | --- |
| UI | `wasm_sdk_probe/web/ods-editor.html`, `ods-editor-app.js`: click selects a cell, dblclick preserves input into inline textarea; formula field/A1 input; global keyboard only handles save and B/I/U. No direct-grid typing, F2, cell navigation/selection model or rectangular range. |
| Session | `spreadsheet-shell/calc-editor-session.js`: single `_cell`, one shared `_draft`, serialized `_chain`, beginEdit/commit/cancel/selectCell/selectAt/setFormat, explicit target/revision. Preserve typed-draft races, IME refusal, dirty and host-copy/stranded behavior. |
| SDK | `spreadsheet-shell/calc-document-sdk.js`: readCell/hitCell/setCellInput/setCellFormat, strict snapshots, 32767 UTF-16 limit. No arbitrary-range mutation API. |
| Worker / C ABI | `sdk/sdk-worker.js`, `src/sdk_api.{h,cpp}`, `src/probe_engine.{hpp,cpp}`: capability gates, explicit expected revision, cell operation dispatch. Old frozen worker bytes are separate from shared source. |
| Native model | `src/calc_cell_bridge.{h,cpp}`: only LIBO_INTERNAL_ONLY TU; synchronous UNO under SolarMutex, protection/readonly, merged-cell origin, direct formula/input/value and three script-font families, operation bounds **0–5**. Mutations report ambiguous outcomes conservatively. |
| Geometry / drawing | LOK CellCursor / ViewRowColumnHeaders at 15 twips per CSS px; `reader-shell/tile-scheduler.js` and `viewer-shell/ods-viewer-session.js`. Do not mutate shared renderer contracts casually or regress 165. |

**Important range trap:** current `endColumn/endRow` describe a merged cell's extent. They are **not** a user-created multi-cell selection. `readCell`/`hitCell` also select a cell on the engine side to read cursor geometry, so repeated hit testing can move engine selection; mutations must keep their explicit captured target, not infer from that cursor. Current whole-cell XPropertySet write cannot represent a protected/mixed-format arbitrary range contract by itself.

## Proposed continuation, not an already frozen specification

The next agent should make the new work concrete and pin criteria before acceptance runs. A reasonable starting interpretation is contiguous rectangular cell ranges with an active cell + anchor/focus, mouse drag, and keyboard/Shift expansion, then B/I/U on that selection. **Those gesture details and batch-format semantics are proposed implementation defaults, not owner-confirmed individual requirements.** Avoid inventing a long approval flow: inspect source, write a reviewable scope and proceed with reasonable defaults unless a material unresolved choice requires a concise question.

Suggested cohesive sequence:

1. Wire missing direct typing and F2 while preserving the accepted double-click behavior. Direct input starts a replacement draft; F2 starts from `cell.input`; Escape cancels without mutation, Enter commits. Handle `beforeinput`/IME and correct focus ownership; do not capture ordinary typing in the formula/A1 field or shortcut modifiers as new cell content. Keep apostrophe-safe literal input and original formula semantics. Movement/navigation and Shift expansion need explicit behavior, not browser scrolling by accident.
2. Model a rectangular selection separately from the active cell and text selection. Define collapse/extend, sheet switch, merged/hidden row/column handling and offscreen drag/scroll behavior using engine geometry. Do not approximate unequal cell sizes with a guessed uniform grid. Show the selection and active cell honestly.
3. If B/I/U should affect the whole range, first investigate a real UNO range operation with protected-cell and mixed-state handling. Do not silently run per-cell mutations then call them atomic. Define stale revision/no-side-effect refusal and ambiguous/partial mutation outcomes. Mixed ranges may need tri-state UI; do not pretend a scalar boolean proves uniform formatting.
4. Direct typing/F2 and visual selection may be shell-only. Arbitrary range format/write likely needs a new native/ABI/worker/SDK contract and **successor profile**, because v1 is frozen. Check feasibility first, update all operation bounds/capability guards together, preserve old profiles and append exports/identity rather than overwriting. Do not claim a link is necessary for shell-only work or already complete for an unbuilt successor.
5. Add real user-path red cases before green: trusted typing/IME/F2, Escape/Enter, mouse/Shift selection in each direction, varied widths/heights/merges/hidden cells, readonly/protection, explicit range targets/revisions, mixed formatting if in scope, ODS XML/reopen and unaffected neighbors/sheets. For drawing, compare actual delivered tiles to direct engine renders and invalidate before emit. A model-only green would repeat the 165 gap.
6. Package any resulting candidate in an isolated host worktree, archive exact bytes, run appropriate focused/offline checks, prepare concrete guarded install/rollback before live changes. Take a fresh shared ddev/lock snapshot and preserve actual states/documents. Keep K deferred and record this new batch in `research/2026-10-25-count-batching-and-next-work.md`.

No product changes, builds, new range gate, new count or service actions were made in this handoff turn. The next action is the feature scope/implementation work above, not another manual acceptance round for completed behavior.

## Standing instructions

Taiwan Traditional Chinese replies; `handoff/**` and `findings/evidence/**` English, owner quotations/data preserved. Research/specs/devlog zh-TW. Reports are Markdown in this repo. No sudo/su/doas/root changes. Earlier explicit conversation authorization 「簡單的編譯/建置也請你直接做」 permits simple autonomous builds; before any compiling make read uptime/pgrep and avoid other builds/long measurements. It does not authorize a LibreOffice core rebuild. The owner also offered to run a link if needed; give a concrete directory/command/time/result when that becomes necessary, not speculatively. Cohesive small commits, English messages with `Co-Authored-By: Codex <noreply@openai.com>`, no session identifiers. No subagents were requested/authorized. Gate documents append-only; red first, nonvacuous/tool-derived populations, explicit defaults; do not repair judges to preserve a disproven claim.
