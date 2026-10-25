# Finding 165: cell formatting leaves stale or empty tiles

The owner confirmed text/formula input and reported a blank sheet after selecting inline text then pressing B/I/U. The formatting survives reopening. Exact observation: `owner-report.md`. Criteria were appended before reproduction in SPEC-M4-cell-editing-v1 section 9; v1 remains whole-cell formatting, not partial rich text.

## Reproduce and read the evidence

`red-01`: original source, real Chrome mouse/keyboard. Model/format checks pass; all six visual checks fail. First bold/inline has 28 DOM tiles, one different from direct engine render. The following five operations have zero tiles. All have tileErrors=0; cancellations alone did not report an error. Original screenshots and scheduler/raw state snapshots are retained. The probe observes tiles delivered to the existing product callback without changing the renderer/session behavior. Direct renders are comparisons, not substitute product tiles.

`session-red.txt` -> `session-green.txt`: synchronous onState observer catches a revision before the scheduler revision is updated. Fix **4caa253e** moves invalidation before `_adopt` emits; no engine relink, shared scheduler or old profile change.

`green-01`: Chrome N=3 / Firefox N=3, **90/90** checks. Each format × inline-selected-text / selected-cell path: direct model toggle, visible DOM tile, same scheduler/document revision, every delivered tile byte-equal to engine render of the corresponding region, no tile errors. **36 snapshots / 936 compared tiles.** Actual downloaded ODS reopens with the expected content and toggled-off formats. All browser/server processes are closed by the runner.

Read existing artifacts only:

```bash
python3 wasm_sdk_probe/tools/read_calc_format_view.py findings/evidence/165-calc-format-blank/green-01
python3 wasm_sdk_probe/tools/read_calc_format_view.py findings/evidence/165-calc-format-blank/red-01 --repeats 1
```

The second command exits 1 for actual stale/empty views and the intentionally absent Firefox round. `reader-green.txt` and `reader-red.txt` retain both outcomes. Empty tile populations are rejected explicitly. W-edit's original six rounds are not repeated or relabeled as visual evidence.

Host package/retest status is under `../host-0.2.35/`. Collabora source analysis and Writer-vs-Calc autosave audit are in `research/2026-10-25-collabora-calc-input-format-autosave.md`. Current Calc source only saves manually; unsaved-state guarding is not autosave. Collabora source is read-only reference, not imported code. Section 34.4 +0/+0; cumulative 47/27. Full K remains deferred.
