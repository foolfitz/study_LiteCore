# Cell editor v1 installed; H-write holds; ddev stopped

This supersedes `HANDOFF-2026-10-25-cell-editor-work-in-progress.md`. The owner's cell-editing request is complete: double-click in-place editing, wide input/formula bar, whole-cell B/I/U, ODS save through Files. Latest owner message offered to run a link after this round; **this round's SDK link was already completed under the earlier explicit simple-build authorization, so no further link is required**. No LibreOffice core rebuild occurred. Do not invent a new manual gate or resume v23.

## Installed identity and state

- Host main **2f3ef60972b195096baa3e1dbddd1a70829a6626 / 0.2.34**, clean.
- Engine package **d308e0cc58958d85**, schema 3, 45 files. All 35 previous file records, including encoded metadata, unchanged; ten new cell-editor paths.
- New frozen **ods-editor-v1**, wasm **d5a081f8b5b55b4fcf6c84fd8026c21b23745831dcb6eee943981f1b1890bc67**, worker **39737ddbb71a5ed18c91c82954290ff80373f8896b77f930c8809770e09053c7**. Do not relink/overwrite it. Profile archive `wasm_sdk_probe/build/archive/ods-editor-v1-d5a081f8-worker-39737ddb` has checksums/attribution. Base data and shared font resources match viewer v3.
- Original Writer **e2-editor-v22 / f7a40bcc** and readonly viewer **ods-viewer-v3 / ebb7e0cb** remain unchanged. E1-C intact.
- **Installed, uncounted candidate.** Nominal shipped host stays **0.2.26**. Full K is deferred/batched; no global count pins, merge BINDING or chain changed. Package-only wrapper locally binds the new buildId.
- **litecore stopped**, fgp-nc/nc-bridge paused, all others stopped, matching all initial states. `findings/evidence/host-0.2.34/cleanup.json` and raw snapshots confirm. No K/P5 window was opened. No root commands/global lock clearing occurred.

## Acceptance and preserved failures

Append-only canonical spec: `specs/SPEC-M4-cell-editing-v1.md`, through **8**. User-facing report: `research/2026-10-25-cell-editor-v1.md`. English evidence READMEs: `findings/evidence/m4-cell-editing/README.md`, `findings/evidence/host-0.2.34/README.md`.

- Native direct model/format/geometry/export/reopen **171/171**, final `native/run-03-final/report.json`. First genuine geometry/literal failures remain in run-01. LOK cursor/header geometry replaced drifting UNO millimeter geometry; text formula operators get a safe apostrophe input while raw formula stays direct.
- Real Chrome/Firefox, **N=3 each / 186 checks**, `browser-edit-03-download/report.json`: double-click/input fields/Enter/Escape/Chinese/formula/clear/literal/newline/B-I-U on-off-on/protection/neighbor/sheets, actual downloads, independent XML and reopen. W-edit is closed; do not repeat for reassurance. Intermediate browser-02 exported bytes without proving a disk download; first reader assumed saved active sheet 0 incorrectly and was corrected explicitly.
- Worker/SDK/session/refusal/static gates pass; `make test-e2-c-static` exited 0 after load/make checks under the owner's simple-build authorization. IME Enter guard is unit-event evidence, not an OS candidate-window observation.
- **H-write holds**, using completed named arms: Chrome admin `host-write-03` (23 checks), Chrome readonly `host-readonly-05` (2), Firefox both `host-firefox-07` (27 including setup). The first two reports' unrelated later failures are retained, not relabeled clean. Original conditional PUT + actual DAV lock, independent server bytes/XML + actual Files reopen, ODS conflict copy + continued save to it, readonly sharing/no-lock, and Writer open/save all pass.
- Reread without services: `python3 wasm_sdk_probe/tools/read_calc_editor_acceptance.py --red-cases`. Zero problems; empty population, missing Firefox, real dirty-state mutation each red. It reads disk ODS/XML and raw requests/original hashes too; this is not K.

Two real host failures were fixed with witnesses:

1. Session read `error.details.outcome`, actual host uses `error.outcome`; conflict copy succeeded while dirty stayed true. Witness **a25eedb0**, red-first unit then **85ad4e33**. The first **df7f6fe14e395638** package/archive remains immutable; corrected package changes only the new session asset. Engine unchanged.
2. Files' UPDATE hint on a readonly shared file sent it to the editor, although server-resolved writable=false correctly disabled editing/saving. `host-readonly-04` preserves actual URL/body/screenshot. Host **2f3ef60** uses the server permission to redirect to the old viewer before rendering. No package change. Do not claim the mocked client permissions unit proves real sharing.

Early harness failures: DOM node serialization; missing Firefox development CA; external profile under snap-inaccessible /tmp. The final Firefox profile trusts the existing mkcert CA, lives under ignored build and is deleted afterward. No daily profile/trust store changed. A failed-constructor geckodriver was identified by its exact port and cleaned. No owner intervention was required.

## Implementation locations and scope

- `wasm_sdk_probe/src/calc_cell_bridge.{h,cpp}`: sole LIBO_INTERNAL_ONLY TU; synchronous UNO cell model under SolarMutex, protection, merged origin, client zoom, safe literal input, three font families, mutation uncertainty. `sdk_api`/`probe_engine` gated new cell ABI and ODS-only export; explicit expected revision.
- Shared worker source has four gated cell operations; old frozen worker bytes remain unchanged. New profile Makefile has isolated objects on existing viewer-v3 core and refuses rebuilding its frozen profile. `make ods-editor-assets` stages only new UI/shell files.
- `spreadsheet-shell/calc-document-sdk.js`, `calc-editor-session.js`: handle/revision validation; one draft, serialized commit/select/sheet/save; canceled/failed/racing drafts preserved, copy success saved, stranded dirty; protection/readonly and 32767 UTF-16 units.
- `web/ods-editor.html`, `ods-editor-app.js`: pointer selection/doubleclick overlay, wide formula textarea, A1 address, B/I/U, sheet tabs, manual save, unsaved protection, real host load/save. Diagnostics `window.__calcEditor`; exports only in diagnostics. No autosave/full Calc/partial-rich-text/multicell-fill claims.
- Host branch commits separately cover MIME/extensions, new controller page, Files routing+compiled mjs, version bump, final server permission redirect. The main branch contains all. Source worktree `build/host-0.2.34/litecore` was verified clean/package-equal and removed. Branch and archives retained.

## Cleanup, rollback and next work

Actual installed identity: `pre-stop-verification.json`. `release.json` is current; `post-install-identity.json` is a historical snapshot before the final server redirect commit. All temporary users/shares/folders were deleted and independently confirmed absent; lock file-id lists before/after are empty. Early failed dirty arm explicitly UNLOCKed only its own file. **Do not run old setup that deletes the entire oc_files_lock table.**

Owner-edited manual fixture fileId **24920** is preserved: 31,008 B, sha256 **a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb**, `owner-fixture-preserved.json`. Do not restore its historical original. Prior F3-hand/Home-End/dialog/H7/V3-SEE observations remain accepted and must not be re-asked.

Concrete `install-0.2.34.sh`, guarded package refresh, archive checksums, expired-window refusal and `rollback-package.sh` are retained. Rollback restores 0.2.33 source/package while retaining installed version 0.2.34; it was not needed/executed. The refresh script is historical and deliberately rejects the now-advanced main. Do not rerun it.

No required work remains for this request. The owner can start litecore and open a writable ODS from Files; the report has the command. Future feature requests get their own scope/gates. K still needs final identity inventory/repins/merge binding/chain-reader and the owner's existing scheduling/no-site agreement, after more updates accumulate. Historical K ran 7h48m40s; do not start it autonomously here. Existing ODS limitations including Basic UDF and L-E6-leak-sbrk remain. Section 34.4 **+0/+0**, cumulative **47/27**.

Standing instructions: Taiwan Traditional Chinese replies; evidence/handoff/upstream/commits English. No sudo/su/doas/root changes. Compiling make belongs to the owner unless explicitly authorized in context; this turn's simple builds were authorized. Cohesive commits with Codex trailer. No subagents were authorized or used.
