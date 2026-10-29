# Host 0.2.39 preparation: verified Writer v24, existing viewer/Calc retained

Declared before packaging and new browser diagnostics, SPEC-M3-link-batch-v24 section 21.
The actual predecessor is clean host 0.2.38 / fff18e48, engine build 5ad1f70a8c5f7d2f, including
the accepted Calc dark-theme HTML fix. Preserve it; do not regress to the older 0.2.37 package.

Candidate scope: isolated host worktree from that parent, version 0.2.39, package the current
three-page static import/worker closure with the established package tool, archive exact bytes
and rollback predecessor. Verify both codings and raw identities, complete unchanged-record
preservation, current Writer v24/frozen 77 and the existing viewer v3/Calc v2 identities. Existing
offline K0/Z0/H5-1 checks and package red cases must pass before installation.

No shared DDEV slot is held. At entry litecore is paused, fgp-nc/nc-bridge running. Do not start,
pause, stop or change those projects during offline preparation. Do not alter live host, owner
documents or locks. The final K still needs a named no-site owner window (J-a P5).

## K premise diagnostic (declared before run)

The old 0.2.26 chain's product-path v8 control and merge-red serve the current page repointed to
v8. The current page's typedInsert gate remains after repointing; v8 has no declaration. Test
the actual unchanged repointed page in a standalone observer mirror, Chrome only, against a
positive unmodified v24 page. Expected: v24 opens and types via uno-insert-text; v8 is refused
PAGE_BUILD_MISMATCH with no insertText, including attempts after refusal. No gate bypass, synthetic
manifest declaration, DDEV use or K credit. This is evidence for adapting the count protocol,
not a new product gate. If never measured, the incompatibility remains a source inference only.

## Offline results

Candidate source `4a8b3cd23a746fa6645823be7819bab91cdbbefe`, only info.xml version differs from
the actual 0.2.38 parent. Engine **78e841368c9b907f**, 46 files; **38 complete predecessor records
identical**, four changed existing modules (editor app, narrow-v2 client/session, shared SDK),
four v24 profile files added and four v22 profile files removed. Viewer/Calc page identities and
the complete dark-theme HTML records are unchanged. Both codings decode to exact current dist.
Archive path, external hashes and per-member delta are in `release.json` and `archive.sha256`.

Existing offline K0/Z0/H5-1: **PACKAGE_HOLDS**, zero problems, **22/22** red cases. Guarded install's
offline mode: **OFFLINE_INSTALL_READY**. The live host/source/engine remain unchanged, installed
false; no DDEV lifecycle or database operation has run. Installer requires a recorded owner slot,
no-site agreement and no other running DDEV project. It snapshots current protected documents
and full lock rows, performs no global unlock, and preserves the exact predecessor rollback.

The first canonical packaging succeeded in 152.93 s, but the preparation wrapper's verification
used a non-normalized ../resources path. Its source and error are preserved before correction.
The correction normalizes manifest-relative paths and honors the existing declared-not-loaded
exclusion. Run 02 reuses the already-produced canonical package and verifies the complete live
closure and every gzip/zstd decoded byte before archival; it does not assume packaging success
means validation success. No canonical packager or frozen instrument changed.

`legacy-v8-gate-01`: **LEGACY_V8_CONTROL_REFUSED** with a passing real v24 typing control. The actual
v8 mirror expires and all three typing attempts send zero inserts. This establishes why the old
K control/red protocol cannot be copied by just changing pins. The protocol work order is
`handoff/WORKORDER-v24-K-control-protocol.md`; no gate bypass or replacement count has been adopted.

K inventory: 18 legacy entry points, 43 static-import files, 24 pin occurrences; only the proposed
merge BINDING site's source is in the frozen count sets. The actual old BINDING and all other
pins remain untouched. Git deltas and every package-member difference since host 0.2.26 are
recorded; this is explicitly a one-time inventory, not a new exhaustive-execution claim.

## Live installation, 2026-10-29 (owner slot)

Slot: `slot.json`, 09:21:11 to 10:06:11 +0800. The owner replied to the pending slot question with
"start now, I will not open litecore.ddev.site" and, in the same turn, authorized stopping the other
running DDEV projects. Recorded verbatim (translated) in `slot.json`; nothing inferred from the handoff.
Coordination: fgp-nc and nc-bridge stopped (`ddev stop`), litecore started from paused
(`ddev-before.json`, `ddev-after-coordination.json`). No root command, no global lock write.

- `install-0.2.39.py --preflight-only` -> **LIVE_PREFLIGHT_READY** (`install-20261029T092222+0800/`).
  Fresh before-state: the three protected documents read 200 with the hashes in `before.json`;
  `oc_files_lock` had **zero rows**.
- `install-0.2.39.py` -> **CANDIDATE_INSTALLED** at 09:22:32-09:22:49 (`install-20261029T092237+0800/`):
  fast-forward fff18e4..4a8b3cd (info.xml only), exact engine rsync, `occ upgrade` to 0.2.39 with
  code-integrity check; protected documents and full lock rows equal before/after; maintenance off,
  no pending DB upgrade; e2-editor/ods-viewer/ods-editor unauthenticated routes all **401**.

## Owned-document Files workflow, `files-workflow-01/`

Existing runner `wasm_sdk_probe/tools/run_calc_editor_host.py` (unchanged), both browsers
(Chrome 156.0.8078.47, Firefox 157.0.1), owned folder + temporary user + read-only share, 09:23:57 to
09:25:43. **52/52 PASS**, cleanup: no owned unlocks needed, share/user removed, folder DELETE 204.
Every entry landed on `/r/78e841368c9b907f-90d7bc2c/...`, i.e. the installed build was served.

What it covers: real Files click into ods-editor (writable route, real DAV lock, unrelated write
423, inline/formula input, conditional PUT with If-Match + token, server XML, leave releases lock,
reopen with formats, conflict copy and later save to the same copy), Files click into e2-editor
(Writer v24) with insert + save and the text present in the server's content.xml, and the read-only
share opening ods-viewer with no save surface and no lock.

Limit, stated rather than implied: the Writer arm inserts through the page's insert-text field
(`session.commitText`), not by key events into the sink. Real-key typing on v24 is established by
the S5/R1/A4 cohorts on the mirror, not re-measured on this host. This run is host acceptance of
the installed package, not K and not a count.

## Post-install read, `post-install-identity.json`

`capture-after.py install-20261029T092237+0800 files-workflow-01` -> **holds: true**: host HEAD
4a8b3cd2 clean, installed_version 0.2.39, MANIFEST buildId 78e841368c9b907f, engine equals the exact
archive, protected documents and lock rows (still zero) equal the installer's after-state, owned
folder 404, temporary user absent. Red cases in `post-install-red/`: a flipped workflow check and
a predecessor build id in one Writer entry both exit 1. The second red case first exited 0 -- the
build-id field was computed but not part of `holds`; fixed before this read was recorded
(fixed-by-execution: 1, fixed-by-review: 0).

DDEV after the slot (`ddev-after-slot.json`): fgp-nc and nc-bridge restarted as found. litecore is
left **running** instead of paused: DDEV 1.25.3 has no `pause` command, and the paused state at
entry came from the reboot, not a choice. The owner may `ddev stop litecore` if preferred.

Status: 0.2.39 is **installed as the daily uncounted candidate**, superseding 0.2.38. Nominal
shipped host remains **0.2.26**. K has **not** run; its control protocol is under ruling.

## Engine rollback to 0.2.38, 2026-10-29 10:46-10:50 (owner slot 2)

Why: `k-nine-cells/` showed eight product-path cells regressed in v24 against v21 and v22 under
identical tools and browsers, first shipped by this package. Offered A (roll back) / B (keep); the
owner chose A and gave a 10-minute no-site window. `slot.json` now holds that window
(10:46:54-10:56:54 +0800) with the install slot embedded as `previousSlot`.

fgp-nc/nc-bridge stopped (`ddev-before-rollback.json`); `rollback-run.py` used the installer's own
`slot()`/`snapshot()` and ran the prepared `rollback-package.sh` unchanged
(`rollback-20261029T104705+0800/`): **ENGINE_ROLLED_BACK** in 7 s. Engine equals the exact 0.2.38
archive (buildId 5ad1f70a8c5f7d2f); host source stays 4a8b3cd (label 0.2.39, info.xml only differs);
protected documents and lock rows (zero) equal before/after; no maintenance, no pending upgrade;
unauthenticated routes 401. `files-workflow-02-after-rollback/`: the same owned-file runner,
**52/52 PASS** in both browsers, every entry on `/r/5ad1f70a8c5f7d2f-90d7bc2c/`, complete cleanup;
`post-rollback-identity.json` re-read documents/locks unchanged afterwards. fgp-nc/nc-bridge
restarted; states equal the pre-rollback snapshot (`ddev-after-rollback.json`).

Status now: functional engine = 0.2.38 (Writer v22) under host label 0.2.39. The 0.2.39 engine
archive stays intact for reinstallation. Nominal shipped host remains 0.2.26; K not run.
