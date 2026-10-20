# Handoff, 2026-10-20j: host 0.2.29 (the ODS viewer in Nextcloud) is built and checked offline; the install and Phase H wait on fable's ruling

**First line:**
- **The owner's goal: 「Nextcloud 裡點 .ods 就能開」.** Spec `specs/SPEC-M4-ods-in-nextcloud.md` (addenda 1–8; A8.9 registers six limitations).
- **O6 is done in code and checked offline.** Host 0.2.29 is on branch `host-0.2.29` (`9a349f6`) of `~/Projects/Nextcloud_Apps/litecore`, checked out in a scratch worktree with its schema-3 engine package built (buildId `1b4d6a1fc905fb8a`). The live app dir still runs 0.2.28. Tool side in study_LiteCore `b70c12b2`.
- **The owner is away and delegated decisions to fable** (「有問題就發給fable，我授權他帶我決定」). Two questions were sent (ddev use tonight; whether Phase H may start with E3 red on 3 files). **The ruling is appended at the end of this file if it arrived before this session ended; if that section is missing, ask fable again with the same brief (it is in this file's §Fable brief).**
- **Install = `handoff/RUNBOOK-install-host-0.2.29.md`** (seven steps; the fast path copies the worktree's `engine/`).
- This session ended at the context soft limit; start fresh from here. The previous handoff (`HANDOFF-2026-10-20i-…` with its Addendum) holds the Phase E story and findings 157–160.

## State in one table

| item | state | where |
| --- | --- | --- |
| Phase E on `ods-viewer-v1` | E1, E2, E4a, E4b, E5, E6, E9 green; E3 red on 3/298 (159 ×2, UDF) — registered limitations (A8.9) | `findings/evidence/m4-ods/phase-e/README.md` |
| 158-A (form controls refused typed) | landed, full corpus 5 refused / 298 open | spec A8, `phase-e/158-a/` |
| 159 cause | found statically: the gcc3_wasm bridge's call table lacks scaddins' signatures; core rebuild (v2 batch) | finding 159, spec A8.8 |
| viewer page `web/ods-viewer-app.js` | reads `liteCoreViewerHost = { load }` once; refuses a host with `save`/`takeLock` (`HOST_ENTRY_INVALID`); `openBytes()` is the one door | `b70c12b2` |
| staging | `make ods-viewer-assets` (cp only) puts the page + `viewer-shell/` into `dist/` as new files; `test-e2-c-static` green after it (E7's premise) | Makefile |
| packager | page table `PAGES`, schema `litecore-engine/3`, `source.pages`, gzip cap 52,428,800 (A2), zstd 45,000,000, `validate_manifest()`, `--selftest` 13/13 | `tools/package_m3_engine.py`, `probe_m3_assets.py` |
| package | 35 files, 340,254,512 B → gzip 116,501,319 / zstd 83,955,910; viewer wasm gz 47,972,102 (under the new cap, over the old one) | worktree `engine/` |
| check_m3_assets | schema 3, `BUILD_ID = 1b4d6a1fc905fb8a`, H5-1 (page table) + 2 red cases; K0/Z0/H5-1 **clean** offline on the worktree package, 22/22 package red cases | `tools/check_m3_assets.py` |
| host app 0.2.29 | one Files action for ODT+ODS routed by mime (`src/files.js`, bundle rebuilt); controller page table, `resolve(fileId, mime)`, `engine()` demands schema 3 with both pages; `templates/viewer.php`; `js/litecore-viewer.js` (`{ load }` only, `data-litecore-viewer`); info.xml 0.2.29; `php -l` clean | branch `host-0.2.29` |
| Phase H runner | `tools/check_m4_host_viewer.py`: H1 (action menus of ODS/ODT/XLSX/PDF), H2 (+ positive control, + `lock-taking-host` red arm), H3, H6; selftest 21/21; **never run** | `b70c12b2` |
| H4 | the 0.2.28 arms' own runners on 0.2.29 — not run | `check_m3_host_entry.py` etc. |
| install | **not done**; runbook written | `handoff/RUNBOOK-install-host-0.2.29.md` |

## Next, in order (after fable's ruling; defaults if the ruling says A for both)

1. Runbook steps 1–4 (install), then step 5 (`check_m4_host_viewer.py --label shakedown`). **The first red is the measurement** — H1's Files action-menu selectors were written from Nextcloud 33's markup without a run; read the recorded `actions` lists before changing anything. If H1's selectors are wrong, that is a runner fix "because of execution" with the report as witness.
2. H4: `check_m3_host_entry.py --label shakedown` on 0.2.29 (the editor unchanged), and the H-154/H-155 arms as 10-20c ran them.
3. Write the Phase H results into the spec (append, A9), the evidence README, and tell the owner how to do H7 (click an `.ods` in Files; `three-sheets-distinct.ods` shows Alpha/Beta/Gamma).
4. The v2 batch for the owner's make: core rebuild with (a) `bridges/CustomTarget_gcc3_wasm.mk` fed scaddins' rdb (159), (b) DB connectivity / forms components (158-B); then the viewer relink with `part_info` (157) and the SelectAll wait (160). Then Phase E again on v2.

## Hazards

- The worktree lives under the session scratchpad (`/tmp/claude-1000/…/scratchpad/litecore-0.2.29`); it may be cleaned. The branch is safe; the built `engine/` is not (runbook step 2b rebuilds it in 2–3 min).
- Merging `host-0.2.29` into the live app's `main` makes the live editor route 500 until the schema-3 package is in `engine/` (runbook step 2). Do steps 1 and 2 back to back.
- `check_m3_assets.py`'s counted run on 0.2.29 will find `PREVIOUS_ADDRESS`/K1 clauses written for the editor only; H5-1 and K0 are the clauses extended this round. A counted assets run is not part of this round (count chain batched).
- `cd` slipped twice more this session (corpus inspections); every command afterwards used absolute paths. Keep doing that.
- `ddev-litecore-web` is up; the owner's other containers too. No timing criterion in H1–H6.

## §34.4

- This stretch (after 10-20i's Addendum): because of execution +0 (the H runner's one selftest fix was before any run; the packager/assets changes are product-side with their own red cases), because of review +0. **Running total since 10-14b: 40 / 27.**
- New tools not yet reviewed: + `package_m3_engine.py --selftest`, `check_m4_host_viewer.py`, the H5-1 clause in `check_m3_assets.py`.

## Fable brief (sent 2026-10-20 night; resend verbatim if no ruling section follows)

Q1 — ddev tonight: A install 0.2.29 now and run H1–H6; B install only; C nothing until the owner names a slot. Main session's inclination A. Q2 — Phase H with E3 red on 3 files (159 ×2, UDF): A start now with the limitations registered; B wait for the v2 core. Inclination A. Q3 — anything else needing a decision tonight. Conditions requested: what makes the install allowed (offline K0/H5 green, branch committed — both hold), what to do on a red H criterion (stop and record, or roll back).

---

## Fable's ruling (2026-10-20 23:30 CST) — Q1 = A, Q2 = A; the next session executes O7 under it

The ruling in full is in spec addendum 9 (zh-TW rendering of fable's English text; the conditions are
binding as written there). Facts fable corrected in the brief: E7/E8 are not "never done" on
`f6ab3cdb` (`o4-post-link/README.md` rows: frozen set 1,430 unchanged, E1-C intact, E8 in the
builder); the restore source is `build/archive/host-0.2.27-engine-817413d5ad5bd502/` (the live
`engine/` differs from it only by ATTRIBUTION.md — checked); ruling 7's "only once" is overridden for
tonight as a fresh explicit delegation.

**First line, in §13.1's terms (as far as this session read them): (a) nothing is installed yet —
the live app is 0.2.28 / engine `817413d5`; (b) 0.2.29 is built and archived, uncounted; (c) nothing is
bound or counted this round; (d) the accumulated-uncounted list gains 0.2.29 (viewer route, ODS Files
action, `litecore-engine/3` page table, gzip cap 52,428,800); K stays batched; `L-ods-editor-redownload-once`
is realised by the new buildId.**

### What the next session does, in this order (each item cites its condition)

0. Read `ddev list` (read-only) and record the set of running projects (Q1-4); `ddev occ app:list`
   recorded (Q1-7); KWallet unlocked (§14.5); no desk gate. The slot starts at the first ddev command
   and ends at the earliest of 07:00 CST 10-21, the owner typing in the session, or +3 h (Q1-2).
1. Runbook steps 1–4 (`handoff/RUNBOOK-install-host-0.2.29.md`): merge `host-0.2.29` (`9a349f6`),
   copy the archived package (or the worktree's `engine/`) in, `ddev occ upgrade`, curl smoke.
   Conditions Q1-1 and Q1-3 already hold (offline gates green; branch and study tree committed;
   `findings/evidence/host-0.2.29/README.md` with the restore recipe; archive
   `host-0.2.29-engine-1b4d6a1fc905fb8a/`).
2. `python3 wasm_sdk_probe/tools/check_m4_host_viewer.py --label shakedown` (H1, H2 + control +
   lock-taking red arm, H3, H6). Re-read `ddev list` before it (Q1-4). The first red is the measurement
   (H1's menu selectors are unrun).
3. H4 = H-154c / H-154o / H-155 as 10-20c ran them (two browsers, N=3), plus
   `check_m3_host_entry.py --label shakedown` for the editor half (Q3-1).
4. Reds: H2 or H4 FAIL → restore tonight per the README's three commands (Q1-6); H1/H3/H5/H6 FAIL →
   leave installed, record, stop before H7; only NE → leave, "not established", the owner decides.
   Errors/permission refusals → stop, restore, hand off (Q1-5).
5. Before H7: `handoff/RELEASE-TEXT-DRAFT-0.2.29.md` naming `L-addin-functions-value-error`,
   `L-no-basic-udf`, `L-hidden-sheet-tabs-enabled`, `FORM_CONTROLS_UNSUPPORTED`, `L-ods-read-only`
   (Q2-4); the H7 message carries the `#VALUE!` caveat (the two files), the hidden-sheet caveat
   (`fdo67682-2.ods`) and the form-control refusal (`tdf134161.ods`) (Q3-4).
6. Append the H results to the spec (A10), the evidence READMEs, and hand off in §13.1's shapes.

### §34.4 (corrected per Q3-2)

- `check_m3_assets.py` and `probe_m3_assets.py` are check changes: because of execution **+2**
  (witness: `findings/evidence/host-0.2.29/README.md`, the pre-change tools' Z0-4 and K0-1 clauses
  against the schema-3 package — stated statically; the run of the old tools was refused by the
  session's permission mode). **Running total since 10-14b: 42 / 27.**
