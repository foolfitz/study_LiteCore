# Review brief 2 — adversarial review of the 0.2.13 IMPLEMENTATION against SPEC-M3-autosave §9 (frozen)

Same rules as brief 1: read-only (write only `findings/evidence/127/review/review-2-implementation.md`), no browsers, no ddev, no builds; English.

The spec is now frozen: `specs/SPEC-M3-autosave.md` §9 (your review 1 dispositioned in §9.9; §9.10 records one deviation found while implementing: finding 128 uses remedy B — give up a BUSY repaint while an `editorAction` is out — instead of deferring invalidations, to keep the line anchored by the product-path mutation `edit-arrows-swapped` verbatim).

The implementation to review:
- page: study_LiteCore commits `c335f5cb` and `8c6b831a` (`git show` them; file `wasm_sdk_probe/web/e2-editor-app.js`, plus two unit-test scope lines);
- host: `~/Projects/Nextcloud_Apps/litecore` commit `84dc3da` (`js/litecore-editor.js`, `templates/editor.php`).

Attack, in this order:
1. **Does the code do what §9.2 / §9.3 say?** Line by line against each bullet. Name every place where it does not (file:line), and what the user would see.
2. **Broken but green, on the product path**: for each §9.4 criterion, is there a defect in THIS code that the criterion as written would not catch? (Construct it from the code, not hypothetically.)
3. **Regressions in existing behaviour** the six counted M3 runners, production UI and the product-path net rely on (`wasm_sdk_probe/tools/check_m3_*.py`, `run_e2_c_product_path.py`): new toasts (finding 130's toast can now fire where it was silent — where?), a changed latency label (autosave uses `自動儲存` / `自動存回`), the O2 label in the title bar, the `run()` `quiet` option, the 128 BUSY give-up (could a repaint now be lost for good? could `busyLeftToAction` stick?), the 129 click (`lastSelectionShape`, the gesture affordance, key repeat), the host's `target` switch (every path that still uses `config.file.davUrl`: is each one right?).
4. Races: autosave vs manual save vs B1 rescue vs finding 109's reopen vs a Worker restart (revision restarting from 0) vs `visibilitychange` during unload.

Do not propose new checks of checks (§34). Output: `## SUMMARY` (≤ 30 lines) with numbered findings tagged BLOCKING / SHOULD / NOTE and the smallest code change for each, then "no defect found" per area, then details with file:line.
