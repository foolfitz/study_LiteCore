# Handoff: host 0.2.39 offline-ready; DDEV slot and K protocol pending

Checkpoint 2026-10-29 ~07:15 +0800. Continues 10-29b. No measurement/build is running.
User asked to execute the next step; original autonomous execution/build authority remains.
Preserve unrelated untracked `codex-claude-code-delegation.md`.

## Prepared candidate (not installed)

- Live host `/home/jiajun/Projects/Nextcloud_Apps/litecore` remains clean main
  **fff18e48bda0a9606319ec5f24148854c9cec281 / 0.2.38**, engine **5ad1f70a8c5f7d2f**.
- Actual predecessor includes the Calc dark-theme fix; earlier 0.2.37 handoff was stale on this point.
- Isolated worktree `wasm_sdk_probe/build/host-0.2.39/litecore`, branch `host-0.2.39`, source
  **4a8b3cd23a746fa6645823be7819bab91cdbbefe**. Only info.xml version differs from the parent.
- Exact engine package/archive **78e841368c9b907f**, 46 files, 38 complete records identical to
  0.2.38. Four existing modules changed (editor app, narrow-v2 client/session, shared SDK), four
  v24 profile files added and four v22 ones removed. Viewer v3, Calc v2, their page identities
  and the complete 0.2.38 dark-theme HTML records are unchanged.
- Exact archive `wasm_sdk_probe/build/archive/host-0.2.39-engine-78e841368c9b907f`, external
  checksums and release record in `findings/evidence/host-0.2.39/`. Every gzip/zstd member decodes
  to current dist. Canonical packaging succeeded in 152.93 s.
- First preparation wrapper failed after successful packaging on an unnormalized ../resources
  lookup. Original source/error committed before correction; run02 normalizes paths, honors the
  declared-not-loaded exclusion, and revalidates all existing canonical bytes before archival.
  No frozen product/count tool or canonical packager was changed.
- Existing offline K0/Z0/H5-1: **PACKAGE_HOLDS**, zero problems, **22/22 red cases**.
- New `install-0.2.39.py --offline-only`: **OFFLINE_INSTALL_READY**. Missing-slot live preflight
  refuses as intended without any service/database mutation. Rollback script is prepared only.

## Actual K premise conflict, now observed

`legacy-v8-gate-01/`: v24 real positive control opens/types with the typed route/completion;
the actual unchanged current page repointed to v8 by the frozen runner expires (v8 hash plus
"typing route not declared"), and three typing attempts send **zero insertText requests**.
Verdict LEGACY_V8_CONTROL_REFUSED. Exact PAGE_BUILD_MISMATCH code is attributed from bound page
source; the UI refusal and absent requests are directly observed. No gate bypass/synthetic manifest.

The old K chain depends on that current-page v8 repoint for product-path and merge-red. Also its
product-path reader assumes 42 checks, whereas the current frozen runner has 46. Updating pins
alone cannot produce an honest K on these bytes. Under AGENTS criterion rule 4, do not build a
gate bypass to preserve a false premise. `handoff/WORKORDER-v24-K-control-protocol.md` records the
witness, fixed constraints and recommended historical-reference protocol A, **not yet adopted**.
No new K criterion/reference was silently substituted; existing finite counts remain valid.

## Binding preparation, not final binding

`k-binding-inventory.json`: generated from actual legacy chain/reader (18 entry points), static
import closure 43 files, 24 pin occurrences, one frozen pin site (run_merge_wasm_shakedown.BINDING).
Contains actual study/host git differences and every engine-member difference since the last
counted 0.2.26. It is explicitly a one-time inventory, not an exhaustive dynamic execution claim.
Proposed merge BINDING was computed by the original bound_values() on actual v24/77, still nine
keys. All old pins and actual frozen BINDING remain unchanged. Do not edit the frozen module.

## DDEV coordination — async question pending

Observed at entry and in offline-preservation.json: **litecore paused; fgp-nc and nc-bridge running**.
No ddev start/pause/stop, occ/SQL, host installation, owner document access or lock write occurred.
Only ddev list was read. The next live install/host verification needs a roughly 30-minute slot.
The user was asked asynchronously to provide a usable shared DDEV window and confirm no opening
of litecore.ddev.site during it. **No answer had arrived at this checkpoint.** The handoff/ruling
J-a P5 explicitly forbids inventing that agreement; do not fill slot.json on the user's behalf.

When an answer arrives, honor the actual wording and coordinate the other active projects. Record
an explicit slot.json with ISO start/end, ownerNoSite true and sharedDdevCoordinated true only when
supported. The new installer itself never starts/stops another project and requires only litecore
running. Its preflight preserves current protected documents and **full current lock rows**;
it never restores old fixture bytes, clears the lock table, or performs automatic rollback.
After exact fast-forward/archive installation it checks upgrade state, current document/lock
preservation and all three unauthenticated routes. Actual host workflow verification follows;
offline success is not installed-host acceptance.

Full K still needs its separately agreed ~8-10 hour no-site window, the adopted replacement
control protocol, final binding/chain/reader and existing P0-P6/PH/J-a/J-b. Do not run the old chain.
No new owner manual F3-hand/H7/V3-SEE requirement is introduced. Nominal shipped host remains0.2.26.

Skill used: nextcloud-dev (packaging/testing references); repository's established exact-engine
archive and local host workflow take precedence over a generic App Store packaging workflow.
English evidence/handoff, zh-TW conversation/spec, no sudo/root action. No agents spawned.
