## SUMMARY

Task: `handoff/tasks/TASK-2026-10-13f-089-threading-arms.md` (commit 47440469). Profile `e2-editor-v12`. Instrument: `wasm_sdk_probe/tools/probe_ods_on_profile.py`, run from `wasm_sdk_probe`.

**Outcome: VOID (stopped at the E0 gate). E1, E2, E3 were not run. No outcome letter (O-T / O-T-off-only / O-G / O-N) was assigned.**

Reason, taken literally from §5 ("every case must be echoed") and §2 ("a case whose `engineEnvEchoed` is not `true` is void"): in E0, `engineEnvEchoed` is `false` for all 7 cases (control + F1..F6) and `engineEnv.everyCaseEchoed` is `false`. The string `[engine-env]` occurs 0 times in `E0-r1-report.json`.

E0 states do match the banked states (F1..F5 as banked 2026-09-07, F6 clean), but those states are void as arm evidence because no case carries the engine's echo.

| E0-r1 case | banked state | E0 state | open ms (`opened.atMs`; timeout: `elapsedMs`) | `engineEnvEchoed` |
|---|---|---|---|---|
| C  d1-anchors.odt (ODT control) | opens | clean | 1541 | false |
| F1 rows35 | opens, worker crashed | crashed (`workerCrashed: true`) | 1173 | false |
| F2 rows36 | TIMEOUT | timeout (`SdkTimeoutError`, `opened` null) | 180879 | false |
| F3 index30-index236 | opens clean | clean | 1056 | false |
| F4 index35-index236 | TIMEOUT | timeout (`SdkTimeoutError`, `opened` null) | 180927 | false |
| F5 index36-index235 | opens, worker crashed | crashed (`workerCrashed: true`) | 1054 | false |
| F6 rows20 | opens | clean | 1684 | false |

Arms not run: E1 (`SC_NO_THREADED_CALCULATION=1`, 3 runs), E2 (`SC_FORCE_CALCULATION=core`, 1 run), E3 (`SC_FORCE_CALCULATION=threads`, 3 runs). Optional native arm (§6): not run (no §5 outcome).

Preconditions at E0 start (2026-10-13T09:37:57Z): kdewallet `Locked` = `b false`; load average 0.38 0.47 0.38; no Chrome other than the run's own (`chrome-others-at-start: []`); wait polls 0. Run finished 09:44:13Z, exit 0, `timedOut: false`, 7 of 7 cases seen, `openTimeoutMs` 180000.

Patched `probe.js` sha256 (E0): `a45491710a580bf6d2dac8933896656ed90a20f0e71e77a29c34f9d3809c19b5` (unpatched `96f18d0c1f6b9b11c7d212bc0e176759ce5d4422e272f59e435c93e0e031364b`).

Default conclusion per §5 stands: 089's cause is still unattributed; H-T is a source reading only and may not be quoted as a cause.

## Details

Files in this directory:

- `E0-r1-report.json` - the full report written by the tool (`--out`).
- `E0-r1-runlog.txt` - wrapper log: arm, engine-env, wallet state, load at start, Chrome check, start/finish times, and the tool's stdout (first 4000 characters of the report).

Command (cwd `wasm_sdk_probe`; fixtures are in `findings/evidence/089/`):

```
python3 tools/probe_ods_on_profile.py --profile e2-editor-v12 --engine-env OXSDK_089_ARM=control --control <abs>/wasm_sdk_probe/dist/e2-fixtures/d1-anchors.odt --fixture <abs>/tdf149752-rows35.ods --fixture <abs>/tdf149752-rows36.ods --fixture <abs>/tdf149752-index30-index236.ods --fixture <abs>/tdf149752-index35-index236.ods --fixture <abs>/tdf149752-index36-index235.ods --fixture <abs>/tdf149752-rows20.ods --open-timeout-ms 180000 --timeout 1380 --out E0-r1-report.json
```

`verdict.spreadsheetsOpened` is in `E0-r1-report.json` under `verdict` (field values, verbatim from the report):

| name | opened | parts | viewReady | workerCrashed | engineEnvEchoed | error |
|---|---|---|---|---|---|---|
| tdf149752-rows35.ods | true | 2 | true | true | false | null |
| tdf149752-rows36.ods | false | null | false | false | false | SdkTimeoutError / TIMEOUT / "open timed out after 180000 ms" |
| tdf149752-index30-index236.ods | true | 2 | true | false | false | null |
| tdf149752-index35-index236.ods | false | null | false | false | false | SdkTimeoutError / TIMEOUT / "open timed out after 180000 ms" |
| tdf149752-index36-index235.ods | true | 2 | true | true | false | null |
| tdf149752-rows20.ods | true | 2 | true | false | false | null |

`verdict.controlOdtOpened`: true. `engineEnv` block in the report: `pairs {"OXSDK_089_ARM": "control"}`, `anchor ENV.MAX_CONCURRENCY="4"`, `everyCaseEchoed false`.

Worker-crash cases (F1, F5) carry the warning `worker sent an error! .../profiles/e2-editor-v12/probe.js:7: Uncaught RuntimeError: memory access out of bounds` (count 1 each). The two timeout cases carry `sal.osl.mutex ... pthread_mutex_unlock failed: EPERM` (count 1 each). No case has a warning starting with `[engine-env] `.

Nothing under `dist/`, `web/`, `sdk/`, any profile, the tool, or finding 089 was edited. No other check or judge was run. Next step belongs to the main session: decide how to get an echoed E0 (the tool/echo path is the open question) before any of E1..E3 is run.
