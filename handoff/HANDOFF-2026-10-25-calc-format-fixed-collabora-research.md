# Calc format blanking fixed; Collabora research and autosave audit complete

Supersedes the installed-state portion of `HANDOFF-2026-10-25-cell-editor-v1-installed-stopped.md`. The owner manually confirmed text/formula input works, reported a fully blank grid after inline text selection + B/I/U (format survives reopen), and requested local Collabora source analysis. A follow-up asks whether Calc autosaves in alignment with Writer.

## Current outcome

- Installed clean main **858a07cfd83e8d082e22926db6b93ea886125a8c / 0.2.35**, engine package **b007f950b2e18cd2**. The host commit only bumps the version. Package changes only `spreadsheet-shell/calc-editor-session.js`; 44/45 prior records unchanged. Profile **ods-editor-v1 / d5a081f8 / worker 39737ddb**, frozen Writer v22 and viewer v3 all unchanged. No relink or core build.
- **Finding 165 fixed** by root **4caa253e**: invalidate the tile scheduler before `_adopt` synchronously emits a new format revision. Previously the view cleared the DOM and scheduled old-revision/cache work, then the format handler canceled that work; no later revision triggered repaint. First action showed one stale tile; subsequent five actions had zero DOM tiles while model/format remained correct.
- User-facing source report: `research/2026-10-25-collabora-calc-input-format-autosave.md`. Collabora source found at **`cool-26-04`**, HEAD **c64a7343a5c6295623619c80aa7857c4e00e1ddd**, and `/home/jiajun/LibreOffice/collabora_online`. Read-only local source, no claim about latest/deployed version; no code transplanted. Reference hashes in finding evidence.
- Collabora normal direct typing starts replacement input even in a nonempty cell; double-click/first F2 preserves and edits existing text. Same B/I/U UNO commands go through cell/range formatting in normal selection vs EditView attributes during text editing. Our v1 **already supports selected-cell whole-cell B/I/U**, but textarea text selection is **not partial rich text**; direct typing into grid/F2 is not wired. The owner requested research, not automatic implementation of those new input/rich-text features.
- **Calc remains manual-save only.** Writer host autosave has 30 s idle, 5 min cap with 3 s quiet period, background attempt and safe-state gates. Calc has no scheduler; HOST.watchUnsaved is only guarding. Both browsers observed **35,021 real ms** idle after a committed edit with zero saves and dirty=true; subsequent manual save succeeded and server XML contained the edit. This bounded observation supports the source audit, not an infinite-time claim. No autosave was added. An optional scope question offered audit-only (recommended) vs adding autosave; no reply had arrived while this round completed, so do not treat elapsed time/preselection as approval. A later explicit answer can steer the next work.

## Verification and evidence

Spec `SPEC-M4-cell-editing-v1.md` through **11**, append-only. Finding `findings/165-calc-format-notifies-view-before-invalidating-tiles.md`. Evidence `findings/evidence/165-calc-format-blank/README.md`, `findings/evidence/host-0.2.35/README.md`.

- Original red **b3ccca5c** preserved six failed visual paths (one stale tile / five zero-tile views), all model checks pass.
- New session observer red first; final **13/13**. The first post-fix attempt failed on teardown because its observer read a released scheduler, preserved as `session-green-attempt-01.txt`; observer now checks ready states. The initial green filename was not a passing outcome. Product behavior unchanged by that test correction (**2b55cca1**).
- Chrome N=3 + Firefox N=3 **90/90**, **36 views / 936 DOM tiles**, every tile byte-equal to direct engine render of its actual region. Each B/I/U path from inline text selection and selected cell tested; actual downloaded ODS and reopen, plus independent six-file XML read. This closes F165-view; do not repeat it for reassurance.
- Actual Files **24/24**, **12 views / 336 tiles** in both browsers, real idle observation, manual save/server XML/own lock release. `probe_calc_format_host.py` reuses the scoped own-folder/user/share helper; never clears global locks. No unrelated Writer/H7/corpus/K rerun.
- Offline package zero problems, **22/22** red cases; local wrapper binding only. Archive/checksums, guarded install and functional rollback prepared before mutation. Installed 12:17:59–12:18:08 +0800, maintenance disabled, three unauthenticated routes 401. No rollback needed.

Reread existing artifacts, no services/builds:

```bash
python3 wasm_sdk_probe/tools/read_calc_format_view.py findings/evidence/165-calc-format-blank/green-01
python3 findings/evidence/host-0.2.35/read-result.py
```

Actual red/empty controls are preserved for both readers. Full K remains deferred/batched; nominal shipped host 0.2.26, no global pins/BINDING/chain moved. Section 34.4 **+0/+0**, cumulative **47/27**; new product regression/tools, no old judge repair.

## Environment and next work

**litecore is RUNNING as found**, not stopped. The owner had already started it for manual testing. All other ddev states match the starting snapshot (fgp-nc/nc-bridge paused, others stopped). Do not follow the old handoff's stopped assumption or stop it just to mimic that history. Existing lock **fileId 24674** is present unchanged before/after; no unlock/clearing or overwrite of that file occurred. All temporary test folder/user/share resources independently confirmed absent, own locks released normally, browsers/private profiles closed. No root operation. Live source is clean and engine equals archive (`post-test-identity.json`). Worktree was verified then removed; `host-0.2.35` branch and immutable archive remain.

Owner can reopen the spreadsheet to load the corrected package; no mandatory new human gate and no pending link. Earlier manual acceptances (F3-hand, Home/End, dialog, H7/V3-SEE) remain accepted. Preserve owner fileId 24920 edits and all existing documents. Do not resume v23 or start K autonomously. If autosave/direct typing/rich text is next requested, use the source report as design input and pin the new semantics before implementation; these are not already present.

## Later owner results and next feature request

Superseded for current next work by `HANDOFF-2026-10-25-calc-owner-passes-input-range-next.md`. The owner explicitly passed whole-cell B/I/U and double-click preserving content, observed the unimplemented direct-typing/F2 entries do nothing, and requested cell-range selection plus this handoff. No new product or service changes occurred in that handoff turn.
