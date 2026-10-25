# Calc input and range batch complete — host 0.2.36 installed

This supersedes the next-work/status portion of `HANDOFF-2026-10-25-calc-owner-passes-input-range-next.md`. The requested short-term batch is complete. Do not restart v23 or full K automatically, and do not ask the owner to repeat already accepted whole-cell B/I/U, double-click or earlier Writer/viewer manual observations.

## Current identity and environment

- Study repo main; product input/selection corrections through `3ed296ee`, artifact/Files tools `d4686381`. Later commits preserve acceptance, install guards and completion records.
- Host `/home/jiajun/Projects/Nextcloud_Apps/litecore`: clean main **702bad6d72be5a70d9e3aaca3290b99f0d9fc1d5**, installed **0.2.36**, package **2b17a0e790b24eb3**. Exact manifest SHA and page identities are in `findings/evidence/host-0.2.36/release.json`.
- Frozen Calc **ods-editor-v1 / d5a081f8**, worker **39737ddb**; Writer **e2-editor-v22 / f7a40bcc** and readonly viewer **ods-viewer-v3 / ebb7e0cb** remain unchanged. **42/45 complete prior package records identical**; only Calc HTML/app/session changed. No native compile, core build or relink was required. E1-C intact.
- Installed uncounted candidate; nominal shipped host **0.2.26**. Full K/global pins/merge BINDING/chain remain deferred/batched. Section 34.4 **+0/+0**, cumulative **47/27**.
- Actual before/after ddev snapshots match: **litecore running as found**, fgp-nc/nc-bridge paused, others stopped. Preserve actual state on the next task; do not apply older stopped-state handoffs.
- Existing **24674 lock preserved**. Owner file **24920** still 31,008 bytes / sha256 **a84629657cf01ea0adeb26991c6f62932e2df601637ecaee0b1fa6721afa6adb**. No unrelated locks cleared, no old owner fixture restored, no root command. All new test folders/users/shares removed.
- Isolated host worktree was verified clean against exact archive then removed; branch `host-0.2.36` and archive `wasm_sdk_probe/build/archive/host-0.2.36-engine-2b17a0e790b24eb3` remain. Guarded install and functional rollback are committed under host evidence. Historical install guards intentionally reject current main: **do not rerun them**.
- The unrelated untracked `codex-claude-code-delegation.md` predates this task and was preserved, not included in this batch.

## Delivered behavior and finite scope

Direct grid typing starts a replacement draft; F2/double-click preserves safe cell input/formula. Enter commits, Escape cancels; formula/A1 input owns its own text. One actual textarea receives beforeinput/composition without focus migration on the first character. A pending selection buffers the edit intent until its final pointer endpoint resolves, captures the correct explicit target, validates length/writability before transfer, and retains/refuses invalid input rather than writing an empty or wrong cell. Escape also works after refused Save focuses the toolbar. New selection/tab/A1/format/double-click waits/refuses while retained input exists.

Click collapses; mouse drag, Shift-click and Shift-arrows extend a distinct active/anchor/focus address rectangle. Active remains anchor during extension. Ordinary arrows move from focus to the next visible engine cell and collapse; top/left boundary collapses to focus. Typing/F2 collapses to active anchor. Engine geometry drives overlays and keyboard reveal; reads/hits may move the engine cursor, so writes never infer targets from it. Pointer ownership, coalescing, last release point, cancellation/capture and stale replies are guarded. Paint retries the latest viewport after in-flight work.

The rectangle includes **endpoint merged extents**, without recursive expansion for interior/boundary-intersecting merges. Hidden indices remain in the address rectangle but have no invented dimensions. Constant work per step; no selected-area scan. **Multi-cell B/I/U is deliberately refused** by toolbar, shortcut and session. Single merged cells retain ordinary formatting. No native range mutation, full Calc merge closure, drag autoscroll, rich text, multicell paste/fill or autosave. Saving stays manual.

## Established evidence — no reassurance reruns

1. `calc-input-range/final-02`: Chrome N=3 + Firefox N=3, **378/378** (63 checks each), independent downloaded ODS XML/reopen, neighbors/other sheet preserved. **12 views / 312 actual DOM tiles** byte-compared with direct engine render.
2. `pending-validation-05`: **8/8 per browser** for oversized/protected/failed-hit/old-draft buffer preservation, Save refusal and global Escape. Earlier Firefox failures exposed Escape reaching the save button; event traces and all failed attempts are retained.
3. Units **22/22** across session/SDK/host contract. Huge range bounded work, explicit active targets, failed geometry and stale reply controls covered. Existing invalidate-before-emit and save/copy/stranded/dirty guards retained.
4. Offline package zero problems, **22/22 red cases**; exact immutable archive prepared before install. Install 16:55:55–16:56:09 Asia/Taipei, maintenance disabled, three unauthenticated routes 401.
5. Actual Files `host-0.2.36/input-range-host-01`: **28/28**, both browsers, entry URLs bind the new package, F2/replacement/Shift/mouse/range formatting refusal/manual save/server XML/own-lock release. **2 views / 56 tiles** match direct engine render. Normal cleanup released own locks; no fallback owned UNLOCK needed.
6. Host identity, original lock lists, owner-document hash, absent test folder/user and project states are independently recorded. Readers below reject empty/missing/false populations; source reader also rejects wrong tool identity and checks fixture-defined/executable call-site populations.

Read without browsers/services:

```bash
python3 wasm_sdk_probe/tools/read_calc_input_range.py findings/evidence/calc-input-range/final-02 --red-cases
python3 findings/evidence/host-0.2.36/read-result.py
```

Canonical spec is append-only through **section 16**. Owner-facing report: `research/2026-10-25-calc-input-range.md`; count ledger appended. Evidence READMEs preserve red classifications and measurement limits. Prior 165 and cell acceptance were not reset or relabeled.

## Delegation, decisions and remaining follow-up limits

The owner explicitly authorized Astra to decide ambiguity. Canonical reusable agent ID: **`/root/astra_calc_scope`** (the tool exposed no UUID). It supplied the finite range ruling and repeated source audits. Ruling: `handoff/RULING-2026-10-25-calc-input-range.md`. It identified concrete first-input, pointer/reveal and buffer-preservation issues; all cited blockers were corrected and focused tests passed. It authorized finite closure and guarded installation.

English `claude -p` work orders/results/dispositions are preserved under `findings/evidence/calc-input-range/`. Long review attempts 01–03 produced no verdict; 04 protocol review and 05 source-excerpt review completed. Claude sessions **ccb9d702-85c9-484d-9f94-984acc76237c** and **77342402-3585-4653-8bae-97c1226856bd** can be resumed if needed. No timeout was treated as approval. Review 05's save/error blockers had false conditional premises in the full session chain; Astra adjudicated them explicitly.

**Pre-existing unmeasured follow-up:** ordinary cell commit disables the textarea while waiting, so arbitrary-delay continuous keystroke reception during that interval is not established. Actual session draft updates retain `_draftVersion` protection. Astra explicitly left this as follow-up rather than reopening the accepted finite batch; do not claim the limitation does not exist or invent a new current human gate.

IME evidence: Chrome trusted CDP preedit/commit; Firefox synthetic composition lifecycle plus trusted Enter. Neither proves a real OS input method. Collabora reference remains local/read-only `cool-26-04` HEAD c64a7343…; input-mode research and current mouse/selection source references are linked in the research report. No source transplantation or running Collabora UI measurement.

There is **no remaining human blocker or short-term task in this batch**. Future range formatting/full merge semantics/continuous input work needs its own contract and criteria; do not silently expand this selection contract into native range writes. Continue to preserve owner documents, frozen identities and actual shared ddev state. Taiwan Traditional Chinese replies; evidence/upstream/handoff English; no sudo/su/doas/root modification; compiling make belongs to the owner unless explicitly authorized under their standing rules. Cohesive commits, English messages with Codex co-author and no session identifiers.
