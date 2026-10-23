# Install host 0.2.33 and run its Phase H

Spec: `specs/SPEC-M4-viewer-v3.md` section 16. Candidate evidence, identities and rollback: `findings/evidence/host-0.2.33/README.md`, `release.json`. No command here compiles or relinks an engine.

## Ready before the slot

- Live host main bffc7dc / 0.2.32, engine 80349a1a24cecb17, verified against its archive.
- Candidate branch host-0.2.33 / 4f7f870 (version-only commit), archived engine **a67beefefebe57d6**, viewer **ods-viewer-v3 / ebb7e0cb**, unchanged editor e2-editor-v22 / f7a40bcc.
- K3, v3 post-link checks, Phase E including owner V3-SEE all hold with the existing Basic UDF limitation. Package self-test 13/13, offline K0/Z0/H5-1 clean, 22/22 red cases, old-package negative control red. New archive's 71 files verified.
- Install, rollback and Phase H scripts prepared and syntax-checked; synthetic preflight controls preserve the live host. Use actual observations for the real slot, not those fixtures.

## Slot and install (agent's short steps)

Only use ddev in the owner-authorized slot. Record `ddev list -j` and the wallet state. If another project is running, do not stop it or start this project; record and hand off. If none is running and litecore is stopped, start litecore in this slot and record that it was the agent's start.

Set `WINDOW_END` to the authorized end time (the sleeping owner's autonomous instruction may delegate a bounded execution window; record that interpretation and its boundary before mutations):

```bash
export WINDOW_END='YYYY-MM-DD HH:MM'
bash findings/evidence/host-0.2.33/install-0.2.33.sh
bash findings/evidence/host-0.2.33/chain-phase-h.sh
```

Run from `/home/jiajun/LibreOffice/study_LiteCore`. Install takes seconds; Phase H about 10 minutes. The install's pre-checks run before merge/copy; `--preflight-only` can read those checks without performing mutations. If the slot closes, the chain stops before the next step; it does not cut off a step already running.

## Read the results before deciding

- `install.txt`: host 0.2.33, live buildId a67beefefebe57d6, occ upgrade success, maintenance off, unauthenticated route responses 401/login redirects.
- `chain.log`, `h-viewer.log`, `judge-h155.txt`, `host-entry.log`: H1-H4/H6 hold, two browsers x3 H155 judged with --require-h155, HOST_ENTRY LANDS. The raw paths are printed in each log. Inspect the container Apache access window to confirm it served the v3 profile; record that data before log rotation.
- All machine H clauses hold: leave 0.2.33 as the uncounted candidate; H7 remains pending until the owner opens an ODS from Files. A Phase H red: read raw evidence first, restore the 0.2.32 engine with the rollback script, record and stop. A hard-to-judge result: record uncertainty and stop, as requested by the sleeping owner; do not invent a new criterion or grow a patch chain.
- Keep K batched. Do not launch a five-hour count chain.

## Finish and hand off

Record H7 separately from V3-SEE. If the owner is asleep, leave a precise H7 entry point (the Phase H folder's plain ODS, with Alpha/Beta/Gamma tabs); do not ask for an immediate manual test. Preserve the fixtures until H7.

If the agent started litecore from stopped and the owner requested stopping after the work unit, stop litecore after recording the results, leaving data/package installed. Keep every other ddev project's state unchanged. Stop the agent's now-unneeded 8794 preview server only after matching its recorded PID/command. Keep package archives and the isolated worktree until their status is documented; write a fresh English handoff and end the session.
