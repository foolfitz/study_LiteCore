# Handoff: 0.2.39 candidate ready; no installation, DDEV slot or new K protocol yet

Checkpoint **2026-10-29 09:14 +0800**. Supersedes 10-29c as the current entry point; see 10-29b
for completed feature-count details. The owner requested this handoff after the offline work.
**No measurement/build from this task is running. Do not launch a count or install while reading this file.**

Study HEAD before this handoff: **aa7391142**. Tree clean except unrelated untracked
`codex-claude-code-delegation.md`; preserve it. No agents were spawned.

## Start with these facts

1. Writer v24 selection and A4 are already established: **S5 1,176 + R1 144 + S1-S4 234 = 1,554
   PASS**, A4 **24/24 PASS**, both browsers. No need to repeat them for reassurance.
2. **Installed host is still 0.2.38**, clean main **fff18e48bda0a9606319ec5f24148854c9cec281**,
   engine **5ad1f70a8c5f7d2f**. No live host installation, occ/SQL, document access, lock write,
   DDEV lifecycle change or root command occurred in the 0.2.39 preparation.
3. **0.2.39 is an isolated, verified candidate only.** Do not describe it as installed or counted K.
4. **No owner DDEV slot/no-site answer has arrived.** At 09:13 the actual states were litecore
   paused, fgp-nc/nc-bridge running, all other projects stopped. Do not infer a free shared slot.
5. **Old K cannot be run by only changing pins.** Its current-page v8 control is now refused by
   the deliberate typedInsert page gate. A new control protocol has been proposed, not adopted.

## Candidate identities and artifacts

Host repo: `/home/jiajun/Projects/Nextcloud_Apps/litecore`.
Candidate worktree: `wasm_sdk_probe/build/host-0.2.39/litecore`, clean branch **host-0.2.39**,
commit **4a8b3cd23a746fa6645823be7819bab91cdbbefe**. Only info.xml version changes from the parent.
Keep the worktree and branch: the guarded installer verifies both.

Evidence root: `findings/evidence/host-0.2.39/`.

- `release.json`: engine build **78e841368c9b907f**, 46 files; installed false, K NOT_RUN.
- Exact engine archive: `wasm_sdk_probe/build/archive/host-0.2.39-engine-78e841368c9b907f`.
- Archive MANIFEST SHA: **0ebc2ade1de97eb4bc5975fe73611a4ac13ad2ea07c7f513ec3302a027f47dc8**;
  existence and hash rechecked at this checkpoint. `archive.sha256` binds all 94 archive files.
- Predecessor archive: `wasm_sdk_probe/build/archive/host-0.2.38-engine-5ad1f70a8c5f7d2f`.
- 38 complete raw/gzip/zstd predecessor records identical; four changed existing modules (editor
  app, narrow-v2 client/session, shared SDK), four v24 profile files added, four v22 files removed.
  Viewer v3, Calc v2, their page identities and the **0.2.38 Calc dark-theme HTML** are retained.
  Do not accidentally use 0.2.37 as the predecessor.
- `offline-package-check.json`: **PACKAGE_HOLDS**, zero problems, **22/22** package red cases.
- `offline-install-preflight.json`: **OFFLINE_INSTALL_READY**. `missing-slot-preflight.receipt.json`
  confirms live preflight refuses with no slot and performs no live mutation.

The canonical packager succeeded in 152.93 s. Its first preparation wrapper then failed on an
unnormalized ../resources lookup. Original source/error are committed as run01. The corrected
wrapper normalizes paths, respects the already-declared not-loaded exclusions, reuses the exact
canonical package and checks the complete closure plus both decoded codings before archival.
No canonical packager, product gate or frozen count instrument was changed.

## Safe immediate reads

From the study root, these do not start DDEV or a browser:

```bash
python3 findings/evidence/host-0.2.39/offline-package-check.py wasm_sdk_probe/build/host-0.2.39/litecore
python3 findings/evidence/host-0.2.39/install-0.2.39.py --offline-only
```

Their results already hold; rerun only if current state needs rechecking. Never rerun
`prepare-release.py` into the existing release/archive; it deliberately refuses overwriting.

## First live step: obtain the actual shared DDEV slot

The pending question asked for about **30 minutes** to install and verify the host, with the owner
not opening `litecore.ddev.site`. The owner did not answer it; requesting this handoff is not an
answer. The 10-15 pre-binding ruling J-a P5 and SPEC v24 section21 prohibit inventing the agreement.
The full K needs a **separate ~8-10 hour** no-site window and a settled control protocol.

Once the owner supplies a real slot, coordinate the other active projects according to that reply;
do not pause another session's work based merely on old authorization. Record
`findings/evidence/host-0.2.39/slot.json` with actual timezone-aware ISO start/end and the supported
`ownerNoSite: true`, `sharedDdevCoordinated: true` facts. Do not create it before confirmation.

The prepared installer requires only litecore running and no other running DDEV project; it does
not start/stop services itself. After coordination, its commands are:

```bash
python3 findings/evidence/host-0.2.39/install-0.2.39.py --preflight-only
python3 findings/evidence/host-0.2.39/install-0.2.39.py
```

It verifies clean predecessor/main, candidate ancestry, exact old/new archives and package checks;
captures **current** protected document bytes and **full current** lock rows; fast-forwards the
host/copies the exact engine; upgrades and checks preservation, maintenance/upgrade state and
all three unauthenticated routes. It never clears locks, restores historical fixture bytes,
performs an automatic rollback, or replaces owner files. Protected file IDs come from the earlier
preservation list (24674, 24920, 25391), but their before-state is read afresh, not assumed.

`rollback-package.sh` is prepared only: exact 0.2.38 engine rollback, retaining host label0.2.39,
with slot/current-source/current-engine guards. Do not run without a reason. After installation,
perform a real owned-document Files workflow check on the new host; installer success and
unauthenticated-route checks alone are not full host acceptance. Do not repeat closed F3-hand,
H7, V3-SEE or Calc range/autosave cohorts as new human prerequisites.

## K protocol conflict: read the witness before writing machinery

Work order: `handoff/WORKORDER-v24-K-control-protocol.md`.
Witness: `host-0.2.39/legacy-v8-gate-01/report.json` and its two raw cells.

- Real unmodified v24 positive control opens/types via uno-insert-text with uno-command-result.
- Current page repointed to actual v8 by the frozen runner expires; the UI shows the v8 wasm
  hash plus "typing route not declared". Three subsequent input attempts send **zero inserts**.
- Verdict LEGACY_V8_CONTROL_REFUSED. The UI and wire absence are directly measured; the exact
  PAGE_BUILD_MISMATCH code is source attribution, not a captured wire exception.
- Old chain uses this current-page v8 environment for product-path comparison and merge-red.
  Its product-path reader also expects 42 checks while the actual frozen runner now has46.

Do not fake typedInsert declarations/exports or bypass the shipped page gate to make old K run.
Recommended protocol A in the work order uses an explicitly historical immutable reference
closure with its own identity; it is **not yet adopted**. Settle its role/binding/negative-control
semantics and record the prescription before any new counted run. Dropping old controls without
a replacement is not proposed. Existing J-a/J-b, preflight/shakedown rules and nine BOUND_KEYS stay.

`k-binding-inventory.json` is a read-only preparation inventory: actual old chain/reader ->18 entry
points, static import closure43 files, 24 pin occurrences, one frozen pin site (merge BINDING).
It includes actual study/host git deltas and every engine-member delta since counted0.2.26.
It explicitly does not claim an exhaustive dynamic execution graph. Its proposed nine-key merge
binding was computed on actual v24/77 bytes; **no old pin or actual BINDING has been changed**.

## Frozen facts, authority and limits

- Never edit the original 40-file live-asserted set, original v24 count sources or the remaining
  orchestration source set. Read their declarations before touching a tool. Source-overrides in
  a new named process are distinct from changing frozen file bytes.
- Bundle tool default remains v76 **by design**; generation77 was frozen through --manifest.
  A4's wrapper rebinds it before importing the runner. Do not "fix" that default.
- I-enter-raw-substring remains the declared frozen Chrome Enter oracle limitation, already read
  by the independent span-aware replay. Full product-path still has recorded inherited FAIL/NE;
  selection/A4 PASS does not mean all46 checks passed. S5's no-op-extension/delete-unit limit remains.
- Owner's 2026-10-29 instruction authorizes necessary agent measurements/builds while away and
  supersedes B owner-run. Do not ask that choice again. This does not supply a DDEV/no-site window
  or adopt a new K criterion. Before a build inspect load/make/other measurements; never sudo,
  su, doas or root-level system modifications. No sub-agent delegation is authorized by this file.
- Specs through v24 section21 are append-only. Evidence/upstream/handoff English; user replies
  and internal specs/research zh-TW. Cohesive English commits, no session identifiers.
- Nominal shipped host remains **0.2.26**. Candidate 0.2.39 is not installed; K has not run.

Skill already applied: nextcloud-dev, packaging/testing references. Relevant completed commits:
279a412aa (package), fb967d120 (offline/red checks), 6d4b4c1c4 (v8 witness), daef093e4 (binding
inventory), 9d8b18697 (guarded install/rollback), aa7391142 (prior handoff/work order).
