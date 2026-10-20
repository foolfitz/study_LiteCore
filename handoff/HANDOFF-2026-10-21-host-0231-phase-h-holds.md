# Handoff, 2026-10-21: host 0.2.31 runs on ddev; Phase H holds (H1–H4, H6); two host bugs found by H and fixed (161, 162); H7 is the owner's

**First line, in SPEC-M3-link-batch-v22 §13.1's shapes:**
- **(a) installed:** ddev (`~/Projects/Nextcloud_Apps/litecore`, served live) runs **host 0.2.31** (`421f4b8`, main) on engine package
  **`1b4d6a1fc905fb8a`** (schema `litecore-engine/3`; editor `e2-editor-v22` wasm `f7a40bcc…` + viewer `ods-viewer-v1` wasm `f6ab3cdb…`).
  0.2.28's package is beside it as `engine.old` (git-ignored, 99 MB). It replaces 0.2.28 as the **uncounted candidate for daily use**.
- **(b) built and archived, uncounted:** the same package, `wasm_sdk_probe/build/archive/host-0.2.29-engine-1b4d6a1fc905fb8a/` (+ATTRIBUTION).
  Host branches `host-0.2.29` (`9a349f6`), `host-0.2.30` (`e6e325a`), `host-0.2.31` (`421f4b8`), all merged into main; the scratch worktrees are removed.
- **(c) bound / counted this round:** nothing. The nominal shipped version is still **0.2.26**. K stays batched.
- **(d) accumulated-uncounted list** gains: the viewer route, the ODS Files action, the `litecore-engine/3` page table, the gzip cap 52,428,800,
  and the fixes 161 (page-table module comparison) and 162 (`scopedStyle()` with a comment before `:root`). `L-ods-editor-redownload-once`
  happened once (the 0.2.29 install; 0.2.30/0.2.31 changed PHP only).

Spec: `specs/SPEC-M4-ods-in-nextcloud.md` **addendum 10** (the whole night in one place). Evidence: `findings/evidence/host-0.2.29/README.md`
("The slot's run" onward; the directory covers 0.2.29→0.2.31, one package). Previous handoff: `HANDOFF-2026-10-20j-…` (fable's ruling, addendum 9).

## What happened, in order

| when (CST) | what | record |
| --- | --- | --- |
| 10-20 23:29 | step 0: `ddev list` set {litecore}; KWallet unlocked; `app:list` (office 1.0.0 = Office overview, no ODS claim); pre-check only ATTRIBUTION.md | README |
| 23:3x | the session's install command refused by the auto-mode classifier ("Production Deploy"); nothing ran. The owner typed (slot over) and offered to run it | README |
| 23:39 | **owner:** `install-0.2.29.sh` → host `9a349f6`, package in, `litecore: 0.2.29` | `install.txt` |
| 23:41–23:51 | H run 1: **RED** — every route 500 (**finding 161**, controller compares `./module` against the manifest's key); H1 polluted (runner clicked the inline action; global query); click null | `phase-h/shakedown/2026-10-20T154120+0000.json` |
| 00:13 | **owner:** `install-0.2.30.sh` (controller one-liner; the owner chose A over restoring) | `install.txt` |
| 00:15–00:29 | H run 2: **RED** — editor 200 (161 gone), viewer 500 (**finding 162**, `scopedStyle()` refuses a comment before `:root`); H1 read right on the lock arm, plain arm lost rows (virtual scroller) | `…T161522+0000.json` |
| 06:19 | **owner:** `install-0.2.31.sh` (scopedStyle fix; editor output byte-identical, replayed) | `install.txt` |
| 06:20–06:21 | H run 3: **VIEWER HOST HOLDS** — H1, H2 (+control, +red case), H3, H6 | `…T222047+0000.json` |
| 06:22–06:30 | H4: H-154c/H-154o/H-155 PASS ×2 browsers ×3 rounds (`judge-h155.txt`); `check_m3_host_entry.py --label shakedown` HOST_ENTRY LANDS | `host-0.2.29/`, `m3-host-entry/shakedown/2026-10-20T222436Z.json` |
| 06:3x | the owner: 「這種很短的指令你就自己跑」 → memory `short-commands-run-them-yourself` | — |

## Next

1. **H7 (owner):** upload `wasm_sdk_probe/test-docs/ods/ladder/three-sheets-distinct.ods`, click it in Files — the viewer with Alpha/Beta/Gamma, Beta
   switches the sheet; ~42 MB download the first time. Caveats (registered limitations, not new bugs): `upstream/date-time-functions.ods` and
   `upstream/functions.ods` show `#VALUE!` in add-in cells (159, v2); `upstream/fdo67682-2.ods` has a hidden sheet whose tab is clickable and refused
   (157, v2); `upstream/tdf134161.ods` is refused `FORM_CONTROLS_UNSUPPORTED` (158-A). Release text: `handoff/RELEASE-TEXT-DRAFT-0.2.29.md`.
2. **Clean-up on the instance (writes; not done in the slot):** the Phase H fixtures `M4 phase-h/` (8 files) and the root-folder eight from runs 1–2
   (`M4 檢視 測試 {plain,lock-taking-host}.{ods,odt,xlsx,pdf}`); `engine.old` in the app dir once 0.2.31 is kept (runbook step 7).
3. **Finding 163** (candidate): four UNLOCKs on leaving the editor, 204 then 500 ×3 (`files_lock` `LockNotFoundException` uncaught). Read the host's
   leave path and count with the browser's network log before deciding; the user path (a real browser) is unmeasured.
4. **The v2 batch** for the owner's make, unchanged from 10-20j Next 4: core rebuild with scaddins' rdb fed to `bridges/CustomTarget_gcc3_wasm.mk` (159)
   and DB connectivity / forms (158-B); viewer relink with `part_info` (157) and the SelectAll wait (160); then Phase E again on v2, then a new
   package (new buildId → `L-ods-editor-redownload-once` again) and Phase H again.
5. K (the count chain) stays batched; the accumulated list is in (d) above.
6. The release text draft's §5/§6 are filled for 0.2.31; it becomes non-draft only after K and H7.

## Hazards

- **The auto-mode classifier refuses deploy-shaped commands** (merge + `occ upgrade` on the live app dir: "Production Deploy"; a sed-derived script +
  `chmod +x`: "Auto-Mode Bypass"). The owner's standing instruction now: run such short commands yourself; if refused, say so at once with the one-liner
  (memory `short-commands-run-them-yourself`); an allow rule in `.claude/settings.local.json` would end the dance — offer it.
- **Two hand-written checks in the host had never met the real artifact** (161: the controller's page table vs the packager's; 162: `scopedStyle()` vs
  the shipped viewer page). Offline gates judge the packager by the packager. The host's own checks are only exercised on the host — H6/H2 are the
  net; keep "the first red is the measurement" for every new host clause.
- `cd` moved the primary working directory once more this session (the DOM probe run); absolute paths everywhere else.
- The H runner's fixtures now live in `M4 phase-h/`; the root-folder copies from runs 1–2 are stale.
- `check_m3_host_entry.py`'s report shows `instance.app.head/version` as null — its identity block did not read the app (not scored; look before a
  counted run).

## §34.4

- This stretch: **because of execution +2** (`check_m4_host_viewer.py`: run 1 forced `row_actions()`/`open_by_click()`/the H1 "not read" key —
  witness `2026-10-20T154120+0000.json`; run 2 forced the fixture folder and the ready-guard — witness `…T161522+0000.json`); selftest 22/22 with
  one new red case. **Because of review +0.** Running total since 10-14b: **44 / 27.**
- Product-side changes with their own witnesses (not check changes): host 0.2.30 (161), host 0.2.31 (162), both replayed with `php -r` red/green on
  the live manifest / the packaged pages.
- Tools still never reviewed: `package_m3_engine.py --selftest`, `check_m4_host_viewer.py`, the H5-1 clause in `check_m3_assets.py`.
