# Handoff: cadence reset adopted; host 0.2.56 installed, waiting for the owner's hand test

Checkpoint **2026-11-04 03:30**. Supersedes `HANDOFF-2026-11-03i-ms-formats-frozen-writer-nets-wait-kwallet.md`. One handoff for this session
(the new rule). The owner was away and delegated hard calls to fable; none was needed.

## The owner's decisions this session

- **Adopt fable's advice, A, all six items** (2026-11-04). Written into CLAUDE.md, new section on cadence (`d0c2b8c64`): release only for an
  owner hand-test slot; parametrise release / identity tools; V0' reads two stages; reader bugs fixed by execution, one arm re-run; a host
  bump with an unchanged engine is install + Files 52/52 + the new arm; one handoff per session, section 34.4 is one number. Acceptance
  criteria sections 5, 6, 8-10 scoped down; "工作結論（2026-08-22）" moved to `devlog/`. Memory: `release-only-for-owner-hand-test-slot`,
  `e2b-structural-lessons` lesson 2 rewritten.
- **Remove the "unlock KWallet before measuring" rule** (`f8865e28b`): `pre_run_checks()` and three other tools record the wallet, never
  refuse; `v21_network.ProxiedChrome` got `--password-store=basic`. Witness: 2026-11-03 23:11-23:20 F3's Chrome arm ran with no secrets service
  at all and matched 46/46. Frozen re-reads of `v21_shakedown_common.py`'s sha (v23/v24 cohorts, K live-bound set) now say "moved": expected.

## Done

- Measurement plan re-drafted: `specs/PLAN-2026-11-04-measurement-after-cadence-reset.md` (zh-TW): what stays (a feature's first measurement
  + one red case), what runs once per hand-test slot (the regression nets), what stopped (V0' beyond two stages, derived scripts, frozen re-reads).
- Writer nets re-run, generation 89 (`ms-formats/gen-89/rerun-01/`, `e1217cebb`): P5, P4, S1, Z, P1 hold, F4 24/24.
- `wasm_sdk_probe/tools/host_release.py` (`bab2e0857`): one release tool, inputs in `findings/evidence/host-X/release-inputs.json`.
  Subcommands candidate / gate / package / delta / offline / install / capture / rollback.
- **Host 0.2.56 installed** (`findings/evidence/host-0.2.56/README.md`): host `6def1da`, engine `1b8dda1e`, gate 28/28, DELTA_HOLDS,
  PACKAGE_HOLDS, CANDIDATE_INSTALLED; H8 red on 0.2.55 first, then H8 18/18 both browsers; Files workflow 52/52.
- Finding 130 updated: the burst cap measured on 0.2.56 (8 keys back to back whole, 10 lose 2, 14 keep 8, 150 ms apart whole, both browsers).
- Owner hand-test script in zh-TW: `HANDTEST-2026-11-04-host-0.2.56.md` (repo root).

## Next, in order

1. **The owner's hand test** of 0.2.56 (the script above). This is the slot; nothing else is released before it.
2. After it: the next features are the owner's pick (the 11-02 demo order -- zoom, Calc per-sheet scroll, Microsoft files -- is done).
   Work on dev profiles under `build/`, no freezes until the next named slot.
3. **Before the next freeze** (not now; spec PLAN section 3.1): one parametrised `four_arms_identity.py` reading `generation-NN.json`; V0' with two
   stages; workers derived into `build/` only. Each is required by the cadence rule, so the next freeze must not derive copies again.
4. Candidates for a later slot, not started: finding 130's queue depth (and whether a held key, ~33 ms a key, loses characters); the 5 expired
   lock rows (below).

## Cautions

- **The host repo's working copy IS the live app** (host-stack mounts `STACK_ROOT` at `/var/www/html`). It had been left on `host-0.2.56` since
  2026-11-03, so live served 0.2.56's PHP/JS with 0.2.55's engine. Never check out a candidate branch there; `host_release.py candidate`
  clones into `build/host-X/litecore`. Host repo is on `main` = `6def1da` (0.2.56), clean.
- `capture-after` is red on the lock table only: 5 expired admin locks created during my diagnostics (diag-saveas-01/-02, diag-taken-03),
  none in H8's or the Files workflow's windows. Cause not established (tool left mid-save, or a page path keeps its lock). Worst case if it is
  the product: another user waits up to 300 s.
- H8's Firefox typing is now one key per 150 ms; a single send-keys call bursts faster than the 8-deep input queue (finding 130).
- `tests/test_v21_shakedown_common.py` `test_the_real_mirror_reproduces_the_round_identity` was red on HEAD before this session (an old
  round's page identity); not touched.
- The owner's desktop Chrome (`/opt/google/chrome`, real profile) was running from ~01:15; it held no LiteCore lock (lock table unchanged over
  65 s before the install). Do not touch it.

## Section 34.4

Checks changed because of review: 0.
